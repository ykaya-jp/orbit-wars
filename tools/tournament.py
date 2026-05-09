"""Round-robin tournament runner for Orbit Wars agents.

Runs every (agent_i, agent_j, seed) combination as a *separate subprocess* so
crashes/leaks in one episode do not contaminate the rest. Logs one CSV row per
episode.

Built-in opponents: pass `random` or `starter` literally. Anything else is
treated as a filesystem path to an agent `.py` file.

Example
-------
    python -m tools.tournament \\
        --agents src/orbit_wars/agent.py random starter \\
        --episodes 5 --seeds 1,2,3 \\
        --output tournament_log.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILTINS = {"random", "starter"}
EPISODE_TIMEOUT_SEC = 600


def _normalize(spec: str) -> str:
    """Return a canonical key for the ELO ledger / CSV.

    - built-in names stay as-is
    - paths are resolved relative to repo root, then made repo-relative if possible
    """
    if spec in BUILTINS:
        return spec
    p = Path(spec)
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    else:
        p = p.resolve()
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def _validate(spec: str) -> None:
    if spec in BUILTINS:
        return
    p = Path(spec)
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    if not p.exists():
        raise FileNotFoundError(f"agent file not found: {spec} (resolved: {p})")


def _run_one(
    left: str,
    right: str,
    seed: int,
) -> dict:
    """Run a single episode in a subprocess. Returns parsed result dict."""
    cmd = [
        sys.executable,
        "-m",
        "tools._run_episode",
        "--left",
        left,
        "--right",
        right,
        "--seed",
        str(seed),
    ]
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=EPISODE_TIMEOUT_SEC,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "reward_left": 0.0,
            "reward_right": 0.0,
            "status_left": "TIMEOUT",
            "status_right": "TIMEOUT",
            "step_count": 0,
            "duration_sec": round(time.perf_counter() - t0, 3),
            "error": "subprocess timeout",
        }

    if proc.returncode != 0:
        return {
            "reward_left": 0.0,
            "reward_right": 0.0,
            "status_left": "ERROR",
            "status_right": "ERROR",
            "step_count": 0,
            "duration_sec": round(time.perf_counter() - t0, 3),
            "error": (proc.stderr or "")[-2000:],
        }

    # Subprocess prints exactly one JSON object on stdout.
    line = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "{}"
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return {
            "reward_left": 0.0,
            "reward_right": 0.0,
            "status_left": "PARSE_ERROR",
            "status_right": "PARSE_ERROR",
            "step_count": 0,
            "duration_sec": round(time.perf_counter() - t0, 3),
            "error": f"could not parse: {line[:200]}",
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--agents",
        nargs="+",
        required=True,
        help="agent specs (paths or 'random'/'starter')",
    )
    ap.add_argument(
        "--episodes",
        type=int,
        default=1,
        help="episodes per (left, right, seed) combination",
    )
    ap.add_argument(
        "--seeds",
        default="1",
        help="comma-separated list of seeds, e.g. '1,2,3'",
    )
    ap.add_argument(
        "--output",
        default="tournament_log.csv",
        help="CSV file to write (relative to repo root)",
    )
    ap.add_argument(
        "--include-self",
        action="store_true",
        help="also pit each agent against a copy of itself",
    )
    args = ap.parse_args()

    if len(args.agents) < 2 and not args.include_self:
        print("error: need at least 2 agents (or use --include-self)", file=sys.stderr)
        return 2

    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    if not seeds:
        print("error: --seeds parsed empty", file=sys.stderr)
        return 2

    for a in args.agents:
        _validate(a)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = REPO_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "timestamp",
        "seed",
        "agent_left_path",
        "agent_right_path",
        "agent_left_reward",
        "agent_right_reward",
        "step_count",
        "episode_duration_sec",
        "status_left",
        "status_right",
        "error",
    ]
    write_header = not output_path.exists()

    pairs = []
    for i, left in enumerate(args.agents):
        for j, right in enumerate(args.agents):
            if i == j and not args.include_self:
                continue
            pairs.append((left, right))

    total_combinations = len(pairs) * len(seeds) * args.episodes
    print(
        f"running {total_combinations} episodes "
        f"({len(pairs)} pairings * {len(seeds)} seeds * {args.episodes} eps)"
    )

    rows_written = 0
    with output_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()

        for left, right in pairs:
            for seed in seeds:
                for _ep in range(args.episodes):
                    res = _run_one(left, right, seed)
                    row = {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "seed": seed,
                        "agent_left_path": _normalize(left),
                        "agent_right_path": _normalize(right),
                        "agent_left_reward": res.get("reward_left", 0.0),
                        "agent_right_reward": res.get("reward_right", 0.0),
                        "step_count": res.get("step_count", 0),
                        "episode_duration_sec": res.get("duration_sec", 0.0),
                        "status_left": res.get("status_left", "?"),
                        "status_right": res.get("status_right", "?"),
                        "error": res.get("error", ""),
                    }
                    writer.writerow(row)
                    f.flush()
                    rows_written += 1
                    print(
                        f"  [{rows_written}/{total_combinations}] "
                        f"{row['agent_left_path']} vs {row['agent_right_path']} "
                        f"seed={seed}: "
                        f"L={row['agent_left_reward']:+.0f} R={row['agent_right_reward']:+.0f} "
                        f"steps={row['step_count']} ({row['episode_duration_sec']:.1f}s)"
                    )

    print(f"\nwrote {rows_written} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
