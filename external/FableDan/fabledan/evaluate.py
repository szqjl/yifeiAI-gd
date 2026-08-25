# -*- coding: utf-8 -*-
"""Head-to-head evaluation: team A (seats 0,2) vs team B (seats 1,3),
seat-swapped halfway for fairness."""

import argparse
import random

from .agents import RandomAgent, RuleAgent, NumpyAgent
from .engine import play_round


def make_agent(spec, seed=None):
    if spec == "random":
        return lambda: RandomAgent(seed)
    if spec == "rule":
        return lambda: RuleAgent()
    if spec.endswith(".npz"):
        from .model_np import NumpyModel
        m = NumpyModel(spec)
        return lambda: NumpyAgent(m)
    if spec.endswith(".pt"):
        from .model_torch import load_ckpt
        from .agents import TorchAgent
        model, _ = load_ckpt(spec)
        return lambda: TorchAgent(model)
    raise ValueError(spec)


def evaluate(make_a, make_b, games=200, seed=42, log_every=0):
    rng = random.Random(seed)
    wins = 0
    total_reward = 0
    for g in range(games):
        a_seats = (0, 2) if g % 2 == 0 else (1, 3)
        agents = [make_a() if p in a_seats else make_b() for p in range(4)]
        rewards, ranking, _ = play_round(agents, rng=random.Random(rng.getrandbits(48)))
        ra = rewards[a_seats[0]]
        total_reward += ra
        if ra > 0:
            wins += 1
        if log_every and (g + 1) % log_every == 0:
            print("  %d/%d  win %.1f%%  avg reward %.3f"
                  % (g + 1, games, 100.0 * wins / (g + 1),
                     total_reward / (g + 1)))
    return wins / games, total_reward / games


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="random|rule|<ckpt.npz>|<ckpt.pt>")
    ap.add_argument("--b", default="random")
    ap.add_argument("--games", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--log-every", type=int, default=50)
    args = ap.parse_args()
    wr, avg = evaluate(make_agent(args.a), make_agent(args.b),
                       args.games, args.seed, args.log_every)
    print("A=%s vs B=%s : win rate %.1f%%, avg reward %.3f"
          % (args.a, args.b, wr * 100, avg))


if __name__ == "__main__":
    main()
