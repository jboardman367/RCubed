from typing import Any, Dict, List
from rlgym.api import ObsBuilder, AgentID, ObsType, StateType, SpaceType

from rcubed.wrapper.botmanager import BotManager
from rcubed.wrapper.common import BOT_MANAGER_KEY


class WrappedObs(ObsBuilder[AgentID, ObsType, StateType, SpaceType]):
    def __init__(self, default: ObsBuilder):
        self.default = default

    def build_obs(self, agents: List[AgentID], state: StateType, shared_info: Dict[str, Any]) -> Dict[AgentID, ObsType]:
        obss = {}
        bot_manager: BotManager = shared_info[BOT_MANAGER_KEY]
        for opp, ids in bot_manager.inv_mapping.items():
            subset = opp.obs_builder.build_obs([agent for agent in agents if agent in ids], state, shared_info)
            obss.update(subset)
        
        default_actions = self.default.build_obs([agent for agent in agents if bot_manager.mapping[agent] is None], state, shared_info)
        obss.update(default_actions)

        return obss
    
    def get_obs_space(self, agent: AgentID) -> SpaceType:
        return self.default.get_obs_space(agent)
    
    def reset(self, initial_state: StateType, shared_info: Dict[str, Any]) -> None:
        bot_manager: BotManager = shared_info[BOT_MANAGER_KEY]
        for opp in bot_manager.inv_mapping.keys():
            opp.obs_builder.reset(initial_state, shared_info)
        
        self.default.reset(initial_state, shared_info)
