from typing import Any, Dict
from rlgym.api import ActionParser, AgentID, ActionType, EngineActionType, StateType, SpaceType

from rcubed.wrapper.common import BOT_MANAGER_KEY
from rcubed.wrapper.botmanager import BotManager

class WrappedParser(ActionParser[AgentID, ActionType, EngineActionType, StateType, SpaceType]):
    def __init__(self, default: ActionParser):
        self.default = default

    def parse_actions(self, actions: Dict[AgentID, ActionType], state: StateType, shared_info: Dict[str, Any]) -> Dict[AgentID, EngineActionType]:
        parsed_actions = {}
        bot_manager: BotManager = shared_info[BOT_MANAGER_KEY]
        for opp, ids in bot_manager.inv_mapping.items():
            subset = opp.action_parser.parse_actions({k: actions[k] for k in actions.keys() if k in ids}, state, shared_info)
            parsed_actions.update(subset)
        
        default_actions = self.default.parse_actions({k: actions[k] for k in actions.keys() if bot_manager.mapping[k] is None}, state, shared_info)
        parsed_actions.update(default_actions)

        return parsed_actions


    def get_action_space(self, agent: AgentID) -> SpaceType:
        # I think this works, as long as this isn't relied on by anything internal to rlgym
        return self.default.get_action_space(agent)
    
    def reset(self, initial_state: StateType, shared_info: Dict[str, Any]) -> None:
        bot_manager: BotManager = shared_info[BOT_MANAGER_KEY]
        for opp in bot_manager.inv_mapping.keys():
            opp.action_parser.reset(initial_state, shared_info)
        
        self.default.reset(initial_state, shared_info)
        
