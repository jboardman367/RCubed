from rlgym.api import RLGym

from typing import Any, List, Dict, Tuple, Generic, Optional, Type

from rlgym.api.config import ActionParser, DoneCondition, ObsBuilder, RewardFunction, StateMutator, Renderer, TransitionEngine
from rlgym.api.typing import AgentID, ObsType, ActionType, EngineActionType, RewardType, StateType, SpaceType

from rlgym.rocket_league.state_mutators import MutatorSequence
from rlgym.rocket_league.action_parsers import RepeatAction

from rcubed.wrapper.mutator import WrapperMutator
from rcubed.wrapper.common import BOT_MANAGER_KEY
from rcubed.wrapper.botmanager import BotManager
from rcubed.wrapper.obs import WrappedObs
from rcubed.wrapper.action import WrappedParser
from rcubed.wrapper.opponent import Opponent

class RCubed(RLGym[AgentID, ObsType, ActionType, EngineActionType, RewardType, StateType, SpaceType]):

    def __init__(self,
                 # rlgym args
                 state_mutator: StateMutator[StateType],
                 obs_builder: ObsBuilder[AgentID, ObsType, StateType, SpaceType],
                 action_parser: ActionParser[AgentID, ActionType, EngineActionType, StateType, SpaceType],
                 reward_fn: RewardFunction[AgentID, StateType, RewardType],
                 termination_cond: DoneCondition[AgentID, StateType],
                 truncation_cond: DoneCondition[AgentID, StateType],
                 transition_engine: TransitionEngine[AgentID, StateType, EngineActionType],
                 renderer: Optional[Renderer[StateType]],
                 # rcubed args
                 opponent_chance: float=0,
                 opponent_base_url: str='http://localhost:5151',
                 bot_name: str=None,
                 run_name: str=None,
                 opponent_refresh_eps=1e6,
                 opponent_pool_size=5,
                 ):
        if isinstance(state_mutator, MutatorSequence):
            wrapped_state_mutator = state_mutator
            state_mutator.mutators = (*state_mutator.mutators, WrapperMutator())
        else:
            wrapped_state_mutator = MutatorSequence(state_mutator, WrapperMutator())

        if isinstance(action_parser, RepeatAction):
            wrapped_action_parser = action_parser
            action_parser.parser = WrappedParser(action_parser.parser)
        else:
            wrapped_action_parser = WrappedParser(action_parser)
        
        # This can't be super() because we mess with self.agents
        self.rlgym = RLGym(
            state_mutator=wrapped_state_mutator,
            obs_builder=WrappedObs(obs_builder),
            action_parser=wrapped_action_parser,
            reward_fn=reward_fn,
            termination_cond=termination_cond,
            truncation_cond=truncation_cond,
            transition_engine=transition_engine,
            renderer=renderer
        )

        self.bot_manager = BotManager(
            opponent_chance=opponent_chance,
            base_url=opponent_base_url,
            bot_name=bot_name,
            run_name=run_name,
        )
        self.rlgym.shared_info[BOT_MANAGER_KEY] = self.bot_manager

        self.managed_obs: Dict[AgentID, ObsType] = None

        self.opponent_refresh_eps = opponent_refresh_eps
        self.ep_remaining = 0
        self.opponent_pool_size = opponent_pool_size

    def register(self, bot: Type[Opponent]) -> None:
        self.bot_manager.register(bot)

    def step(self, actions: Dict[AgentID, ActionType]) -> Tuple[Dict[AgentID, ObsType], Dict[AgentID, RewardType], Dict[AgentID, bool], Dict[AgentID, bool]]:
        for opp, ids in self.bot_manager.inv_mapping.items():
            actions.update(opp.act({k:v for k, v in self.managed_obs.items() if k in ids}))
        step_return = self.rlgym.step(actions)
        self.managed_obs = {k:v for k, v in step_return[0].items() if self.bot_manager.mapping[k] is not None}
        return tuple(({k:v for k, v in ret.items() if self.bot_manager.mapping[k] is None} for ret in step_return))
    
    def reset(self) -> Dict[AgentID, ObsType]:
        self.ep_remaining -= 1
        if self.ep_remaining <= 0:
            self.ep_remaining = self.opponent_refresh_eps
            self.bot_manager.refresh_opponents()
        all_obs = self.rlgym.reset()
        self.managed_obs = {k:v for k, v in all_obs.items() if self.bot_manager.mapping[k] is not None}
        return {k:v for k, v in all_obs.items() if self.bot_manager.mapping[k] is None}
    
    @property
    def agents(self) -> List[AgentID]:
        return [agent for agent in self.rlgym.agents if self.bot_manager.mapping[agent] is None]

    @property
    def action_spaces(self) -> Dict[AgentID, SpaceType]:
        return {agent: space for agent, space in self.rlgym.action_spaces.items() if self.bot_manager.mapping[agent] is None}

    @property
    def observation_spaces(self) -> Dict[AgentID, SpaceType]:
        return {agent: space for agent, space in self.rlgym.observation_spaces.items() if self.bot_manager.mapping[agent] is None}

    @property
    def state(self) -> StateType:
        return self.rlgym.state

    def action_space(self, agent: AgentID) -> SpaceType:
        return self.rlgym.action_space(agent)

    def observation_space(self, agent: AgentID) -> SpaceType:
        return self.rlgym.action_space(agent)

    def set_state(self, desired_state: StateType) -> Dict[AgentID, ObsType]:
        all_obs = self.rlgym.set_state(desired_state)
        self.managed_obs = {k:v for k, v in all_obs.items() if self.bot_manager.mapping[k] is not None}
        return {k:v for k, v in all_obs.items() if self.bot_manager.mapping[k] is None}

    def render(self):
        return self.rlgym.render()

    def close(self) -> None:
        self.rlgym.close()
