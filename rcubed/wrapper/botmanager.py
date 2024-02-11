"""
This is for dealing with loading/unloading of bots
"""
from typing import Dict, Optional, List, Type
import requests
from urllib.parse import urljoin
import random

from rlgym.api import AgentID

from rcubed.wrapper.opponent import Opponent

class BotManager:
    mapping: Dict[AgentID, Optional[Opponent]]
    inv_mapping: Dict[Opponent, List[AgentID]]
    bots: List[Type[Opponent]]
    loaded_models: List[Opponent]
    def __init__(self,
                 opponent_chance: float,
                 base_url: str,
                 bot_name: str=None,
                 run_name: str=None,
                 ):
        self.opponent_chance = opponent_chance
        self.bots = []
        self.mapping = {}
        self.inv_mapping = {}
        self.base_url = base_url
        self.bot_name = bot_name
        self.run_name = run_name
        self.loaded_models = []

    def register(self, bot: Type[Opponent]):
        self.bots.append(bot)

    def map_match(self, agents: List[AgentID]) -> None:
        # We want to use probs here, then set _mapping and _inv_mapping
        self.mapping.clear()
        self.inv_mapping.clear()
        # First agent is always the training agent
        self.mapping[agents[0]] = None
        for agent in agents[1:]:
            if random.random() < self.opponent_chance:
                self.mapping[agent] = random.choice(self.loaded_models)
                self.inv_mapping[self.mapping[agent]] = self.inv_mapping.get(self.mapping[agent], []) + [agent]
            else:
                self.mapping[agent] = None

    def refresh_opponents(self, n=5) -> None:
        """
        Used to fetch a new set of opponents from the server, to use until this method is called again.
        """
            
        req_body = {
            "bots": {},
            "numOpponents": n,
            "for": {
                "mu": 25,
                "sigma": 8.333
            }
        }

        # If we have a bot and run name, we can find a better match
        if self.bot_name and self.run_name:
            last_ts = self.get_own_model()["ts"]
            if last_ts:
                req_body["for"] = last_ts

        for opp in self.bots:
            for bot, runs in opp.get_filter().items():
                existing_entry = req_body["bots"].get(bot, [])
                req_body["bots"][bot] = [*existing_entry, *runs]

        patch_url = urljoin(self.base_url, '/ts/opponents')
        r = requests.post(patch_url, json=req_body, headers={
            'Accept': 'application/json'
        })

        matched_ids: List[str] = r.json()
        self.loaded_models.clear()
        for m_id in matched_ids:
            r = requests.get(urljoin(self.base_url, f'/models/{m_id}'))
            model = r.json()
            cls = next(b for b in self.bots if model["runName"] in b.get_filter().get(model["botName"], ()))
            self.loaded_models.append(cls.load_from_location(
                model["location"]["value"],
                model["location"]["type"],
                model["botName"],
                model["runName"]
            ))

    def get_own_model(self) -> dict:
        # Get models
        models = []
        page_num = 0
        while True:
            get_url = urljoin(self.base_url, '/models')
            r = requests.get(get_url, params={
                "page": page_num,
                "bot": self.bot_name,
                "run": self.run_name,
            }, headers= {
                'Accept': 'application/json'
            })
            resp_data = r.json()
            for d in resp_data["data"]:
                models.append(d)
            
            if "nextPage" in resp_data.keys():
                page_num = resp_data["nextPage"]
            else:
                break
        if len(models) == 0:
            return None
        return max(models, key=lambda m: (m.get("steps", 0), m["created"]))

