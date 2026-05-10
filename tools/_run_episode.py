"""Internal subprocess entry: run a single Orbit Wars episode and emit a JSON line.

Used by tools.tournament for memory isolation (one OS process per episode).

Stdout: a single JSON object with keys
  reward_left, reward_right, status_left, status_right,
  step_count, duration_sec
Stderr: any kaggle_environments noise.
"""

from __future__ import annotations

import argparse
import json
import sys
import time


def _resolve(spec: str) -> object:
    """Map an agent spec string to whatever kaggle_environments.run() accepts.

    - "random" / "starter": built-in baseline names
    - any other string: filesystem path to an agent .py file
    """
    if spec in ("random", "starter", "reaction", "self"):
        return spec
    return spec  # treat as path; kaggle_environments handles it


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--left", required=True, help="agent spec for player 0")
    ap.add_argument("--right", required=True, help="agent spec for player 1")
    ap.add_argument("--p3", default=None, help="agent spec for player 2 (4P mode)")
    ap.add_argument("--p4", default=None, help="agent spec for player 3 (4P mode)")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--env", default="orbit_wars")
    args = ap.parse_args()

    from kaggle_environments import make

    env = make(args.env, configuration={"seed": args.seed}, debug=False)
    agents = [_resolve(args.left), _resolve(args.right)]
    if args.p3 and args.p4:
        agents.append(_resolve(args.p3))
        agents.append(_resolve(args.p4))
    t0 = time.perf_counter()
    env.run(agents)
    duration = time.perf_counter() - t0

    last = env.steps[-1]
    out: dict = {
        "step_count": len(env.steps),
        "duration_sec": round(duration, 3),
        "n_players": len(last),
    }
    for i, ps in enumerate(last):
        r = ps.reward
        s = ps.status
        out[f"reward_p{i}"] = float(r) if r is not None else 0.0
        out[f"status_p{i}"] = str(s)
    # backward-compat 2P keys
    out["reward_left"] = out.get("reward_p0", 0.0)
    out["reward_right"] = out.get("reward_p1", 0.0)
    out["status_left"] = out.get("status_p0", "?")
    out["status_right"] = out.get("status_p1", "?")
    sys.stdout.write(json.dumps(out))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
