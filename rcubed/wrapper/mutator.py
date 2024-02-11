from typing import Any, Dict
from rlgym.api import StateMutator
from rlgym.rocket_league.api import GameState

from rcubed.wrapper.botmanager import BotManager

from rcubed.wrapper.common import BOT_MANAGER_KEY

class WrapperMutator(StateMutator[GameState]):
    
    def apply(self, state: GameState, shared_info: Dict[str, Any]) -> None:
        bot_manger: BotManager = shared_info[BOT_MANAGER_KEY]
        bot_manger.map_match(list(state.cars.keys()))