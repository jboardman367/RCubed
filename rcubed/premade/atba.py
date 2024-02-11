from typing import Any, Dict, List, Tuple
from rcubed.wrapper import Opponent
from rlgym.api import ObsBuilder, ActionParser
from rlgym.rocket_league.api import GameState
import numpy as np

class LeftRightObs(ObsBuilder):
    def reset(self, initial_state: Any, shared_info: Dict[str, Any]) -> None:
        pass

    def build_obs(self, agents: List, state: Any, shared_info: Dict[str, Any]) -> Dict:
        return {agent: self._build_obs(agent, state) for agent in agents}

    def _build_obs(self, agent, state: GameState):
        car_right = state.cars[agent].physics.right
        car_to_ball = state.ball.position - state.cars[agent].physics.position
        return np.array([1 if np.dot(car_right, car_to_ball) > 0 else -1])
    
    def get_obs_space(self, agent: Any) -> Any:
        return 1
    
class LeftRightAction(ActionParser):
    def reset(self, initial_state: Any, shared_info: Dict[str, Any]) -> None:
        pass

    def parse_actions(self, actions: Dict, state: Any, shared_info: Dict[str, Any]) -> Dict:
        return {k: np.stack([np.array([1, vv[0], 0, 0, 0, 0, 1, 0]) for vv in v]) for k, v in actions.items()}
    
    def get_action_space(self, agent: Any) -> Any:
        return 1

class ATBA(Opponent):
    def __init__(self):
        self.obs = LeftRightObs()
        self.action = LeftRightAction()

    def act(self, obs: Dict) -> Dict:
        return obs

    @property
    def obs_builder(self):
        return self.obs
    
    @property
    def action_parser(self):
        return self.action

    @staticmethod
    def get_filter() -> Dict[str, Tuple[str, ...]]:
        return {"atba": ["atba"]}

    @classmethod
    def load_from_location(cls, location: str, location_type: str, bot_name: str, run_name: str):
        return cls()
