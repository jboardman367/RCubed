import time
import numpy as np
from itertools import chain

from rlgym.api import RLGym
from rlgym.rocket_league.action_parsers import LookupTableAction, RepeatAction
from rlgym.rocket_league.done_conditions import GoalCondition, AnyCondition, TimeoutCondition, NoTouchTimeoutCondition
from rlgym.rocket_league.obs_builders import DefaultObs
from rlgym.rocket_league.reward_functions import CombinedReward, GoalReward, TouchReward
from rlgym.rocket_league.sim import RocketSimEngine, RLViserRenderer
from rlgym.rocket_league.state_mutators import MutatorSequence, FixedTeamSizeMutator, KickoffMutator

from rcubed.premade.atba import ATBA

atba = ATBA()

env = RLGym(
    state_mutator=MutatorSequence(
        FixedTeamSizeMutator(blue_size=2, orange_size=2),
        KickoffMutator()
    ),
    obs_builder=atba.obs_builder,
    action_parser=RepeatAction(atba.action_parser, repeats=8),
    reward_fn=CombinedReward(
        (GoalReward(), 10.),
        (TouchReward(), 0.1)
    ),
    termination_cond=GoalCondition(),
    truncation_cond=AnyCondition(
        TimeoutCondition(timeout=300.),
    ),
    transition_engine=RocketSimEngine(),
    renderer=RLViserRenderer()
)

render = False

while True:
    obs_dict = env.reset()
    steps = 0
    ep_reward = {agent_id: 0 for agent_id in env.agents}
    t0 = time.time()
    while True:
        if render:
            env.render()
            time.sleep(6/120)

        actions = atba.act(obs_dict)

        obs_dict, reward_dict, terminated_dict, truncated_dict = env.step(actions)

        steps += 1
        for agent_id, reward in reward_dict.items():
            ep_reward[agent_id] += reward

        if any(chain(terminated_dict.values(), truncated_dict.values())):
            break

    ep_time = time.time() - t0
    print("Steps per second: {:.0f} | Episode time: {:.2f} | Episode Reward: {:.2f}".format(
        steps / ep_time, ep_time, max(ep_reward.values())))