"""Gold release gate (Phase 0.5)。

agent vs proxy を N episodes 走らせて win rate を計算、threshold 以上なら PASS、
未満なら FAIL を exit code で返す。submit 前のリリースゲート。

Usage:
    python -m tools.goldcheck \
        --agent src/orbit_wars/agent.py \
        --proxy agents/proxy/il_v1.py \
        --episodes 30 \
        --threshold 0.70
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="src/orbit_wars/agent.py")
    ap.add_argument("--proxy", default="agents/proxy/il_v1.py")
    ap.add_argument(
        "--episodes", type=int, default=30, help="episodes per pairing × seed (= 2 sides × seeds)"
    )
    ap.add_argument("--seeds", default="1,2,3,4,5,6,7,8,9,10")
    ap.add_argument("--threshold", type=float, default=0.70)
    ap.add_argument("--output", default=None, help="output CSV path (default: temp file)")
    args = ap.parse_args()

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path(tempfile.mkstemp(suffix=".csv", prefix="goldcheck_")[1])

    cmd = [
        sys.executable,
        "-m",
        "tools.tournament",
        "--agents",
        args.agent,
        args.proxy,
        "--episodes",
        str(args.episodes),
        "--seeds",
        args.seeds,
        "--output",
        str(out_path),
    ]
    print(f"running: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), check=False)
    if res.returncode != 0:
        print(f"tournament failed (exit {res.returncode})")
        return 2

    df = pl.read_csv(out_path)
    agent_norm = args.agent
    # tournament uses repo-relative paths, normalize same way
    agent_path = Path(args.agent)
    if not agent_path.is_absolute():
        agent_path = (REPO_ROOT / agent_path).resolve()
    try:
        agent_norm = str(agent_path.relative_to(REPO_ROOT))
    except ValueError:
        agent_norm = str(agent_path)

    wins = 0
    losses = 0
    draws = 0
    for row in df.iter_rows(named=True):
        if row["agent_left_path"] == agent_norm:
            r = row["agent_left_reward"]
        elif row["agent_right_path"] == agent_norm:
            r = row["agent_right_reward"]
        else:
            continue
        if r > 0:
            wins += 1
        elif r < 0:
            losses += 1
        else:
            draws += 1

    total = wins + losses + draws
    if total == 0:
        print("no rows for agent in tournament output")
        return 2
    win_rate = wins / total

    print("\n=== goldcheck result ===")
    print(f"  agent  : {args.agent}")
    print(f"  proxy  : {args.proxy}")
    print(f"  W={wins} L={losses} D={draws} (total {total})")
    print(f"  win rate: {win_rate:.3f}")
    print(f"  threshold: {args.threshold}")
    if win_rate >= args.threshold:
        print("  PASS — gate cleared, safe to submit")
        return 0
    print("  FAIL — improve agent before submitting")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
