"""Local play loop — pit your agent against opponents using kaggle_environments.

Usage:
    uv run python -m orbit_wars.play
    uv run python -m orbit_wars.play --opponent self
    uv run python -m orbit_wars.play --opponent random --seed 7 --episodes 10

Override the comp slug via env (`KAGGLE_ENV_NAME=<name>`) or edit ENV_NAME below.
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
from pathlib import Path

ENV_NAME = os.environ.get("KAGGLE_ENV_NAME", "orbit_wars")


def _resolve_agent(spec: str, my_agent_path: str) -> object:
    """Map an opponent spec to something kaggle_environments.run() accepts."""
    if spec == "self":
        return my_agent_path
    if spec in ("random", "reaction"):
        # built-in baselines provided by some envs
        return spec
    # treat as path to a python file
    return spec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--opponent", default="random", help="self | random | reaction | <path-to-py>")
    ap.add_argument("--episodes", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--render", action="store_true", help="save HTML render of last episode")
    args = ap.parse_args()

    try:
        from kaggle_environments import make
    except ImportError as e:
        print(
            "error: kaggle-environments not installed (`uv add kaggle-environments`)",
            file=sys.stderr,
        )
        raise SystemExit(1) from e

    here = Path(__file__).resolve().parent
    my_agent = str(here / "agent.py")
    opp = _resolve_agent(args.opponent, my_agent)

    print(f"env={ENV_NAME}  episodes={args.episodes}  me={my_agent}  opp={opp}  seed={args.seed}")

    rewards: list[float] = []
    wins = 0
    for i in range(args.episodes):
        env = make(ENV_NAME, configuration={"seed": args.seed + i}, debug=True)
        env.run([my_agent, opp])
        last = env.steps[-1]
        my_reward = float(last[0].reward) if last[0].reward is not None else 0.0
        opp_reward = float(last[1].reward) if last[1].reward is not None else 0.0
        rewards.append(my_reward)
        if my_reward > opp_reward:
            wins += 1
        print(f"  ep {i}: me={my_reward:.2f}  opp={opp_reward:.2f}  status[me]={last[0].status}")

        if args.render and i == args.episodes - 1:
            html_out = Path("outputs") / f"replay_{ENV_NAME}_ep{i}.html"
            html_out.parent.mkdir(parents=True, exist_ok=True)
            html_out.write_text(env.render(mode="html"))
            print(f"  saved {html_out}")

    if rewards:
        print(
            f"summary: wins={wins}/{len(rewards)}  mean_reward={statistics.mean(rewards):.2f}  std={statistics.pstdev(rewards):.2f}"
        )
    return 0 if wins >= len(rewards) // 2 else 1


if __name__ == "__main__":
    raise SystemExit(main())
