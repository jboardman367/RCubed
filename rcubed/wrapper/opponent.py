from abc import ABC, abstractmethod
from typing import Dict, Tuple

from rlgym.api import AgentID, ObsType, ActionType, ActionParser, ObsBuilder


class Opponent(ABC):
    @property
    @abstractmethod
    def obs_builder(self) -> ObsBuilder:
        raise NotImplementedError()
    
    @property
    @abstractmethod
    def action_parser(self) -> ActionParser:
        raise NotImplementedError()
    
    @abstractmethod
    def act(self, obs: Dict[AgentID, ObsType]) -> Dict[AgentID, ActionType]:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_filter() -> Dict[str, Tuple[str, ...]]:
        """
        Filter for matching models. A dictionary where keys are bot names
        and values are tuples of run names.
        """
        raise NotImplementedError()
    
    @classmethod
    @abstractmethod
    def load_from_location(cls, location: str, location_type: str, bot_name: str, run_name: str):
        raise NotImplementedError()
    