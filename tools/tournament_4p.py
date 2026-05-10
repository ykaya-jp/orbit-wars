"""4-player FFA tournament runner.

bovard top10 dataset is 4P FFA — our 2P tournament misled us about agent strength
(SPNE was 0/24 in 2P but encodes genuine 4P strategies). This runs proper 4P
matches with position rotation to remove start-position bias.

Each (seed, ep) round: 4 agents take 4 distinct rotation positions (= 4 separate
matches at the same seed). Aggregate win rate = total wins / total matches.

Usage:
    python -m tools.tournament_4p \\
        --agents experiments/konbu17_hybrid/main.py \\
                 experiments/orbitbotnext/main.py \\
                 experiments/marco_1060/main.py \\
                 experiments/emanuellcs_spne/main.py \\
        --episodes 2 --seeds 1,2,3 \\
        --output tournament_4p_log.csv
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
EPISODE_TIMEOUT_SEC = 900


def _normalize(spec: str) -> str:
    BUILTINS = {"random", "starter"}
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
    if spec in ("random", "starter"):
        return
    p = Path(spec)
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    if not p.exists():
        raise FileNotFoundError(f"agent file not found: {spec} (resolved: {p})")


def _run_4p(agents: list[str], seed: int) -> dict:
    """Run a single 4P FFA episode in subprocess. agents must be length 4."""
    assert len(agents) == 4
    cmd = [
        sys.executable,
        "-m",
        "tools._run_episode",
        "--left",
        agents[0],
        "--right",
        agents[1],
        "--p3",
        agents[2],
        "--p4",
        agents[3],
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
            "rewards": [0.0, 0.0, 0.0, 0.0],
            "statuses": ["TIMEOUT"] * 4,
            "step_count": 0,
            "duration_sec": round(time.perf_counter() - t0, 3),
            "error": "subprocess timeout",
        }

    if proc.returncode != 0:
        return {
            "rewards": [0.0, 0.0, 0.0, 0.0],
            "statuses": ["ERROR"] * 4,
            "step_count": 0,
            "duration_sec": round(time.perf_counter() - t0, 3),
            "error": (proc.stderr or "")[-2000:],
        }

    line = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "{}"
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return {
            "rewards": [0.0, 0.0, 0.0, 0.0],
            "statuses": ["PARSE_ERROR"] * 4,
            "step_count": 0,
            "duration_sec": round(time.perf_counter() - t0, 3),
            "error": f"could not parse: {line[:200]}",
        }

    return {
        "rewards": [data.get(f"reward_p{i}", 0.0) for i in range(4)],
        "statuses": [data.get(f"status_p{i}", "?") for i in range(4)],
        "step_count": data.get("step_count", 0),
        "duration_sec": data.get("duration_sec", 0.0),
        "error": data.get("error", ""),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", nargs=4, required=True, help="exactly 4 agent specs")
    ap.add_argument("--episodes", type=int, default=1, help="episodes per (seed, rotation)")
    ap.add_argument("--seeds", default="1", help="comma-separated seeds")
    ap.add_argument("--output", default="tournament_4p_log.csv")
    ap.add_argument(
        "--rotations",
        type=int,
        default=4,
        choices=[1, 4],
        help="1=fixed positions, 4=rotate through all 4 positions per seed",
    )
    args = ap.parse_args()

    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    if not seeds:
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
        "rotation",
        "ep",
        "agent_p0",
        "agent_p1",
        "agent_p2",
        "agent_p3",
        "reward_p0",
        "reward_p1",
        "reward_p2",
        "reward_p3",
        "step_count",
        "episode_duration_sec",
        "status_p0",
        "status_p1",
        "status_p2",
        "status_p3",
        "error",
    ]
    write_header = not output_path.exists()

    base = list(args.agents)
    n_total = len(seeds) * args.rotations * args.episodes
    print(
        f"running {n_total} episodes ({len(seeds)} seeds × {args.rotations} rotations × {args.episodes} eps)"
    )

    rows_written = 0
    with output_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        for seed in seeds:
            for rot in range(args.rotations):
                rotated = base[rot:] + base[:rot]
                for ep in range(args.episodes):
                    res = _run_4p(rotated, seed)
                    row = {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "seed": seed,
                        "rotation": rot,
                        "ep": ep,
                    }
                    for i in range(4):
                        row[f"agent_p{i}"] = _normalize(rotated[i])
                        row[f"reward_p{i}"] = res["rewards"][i]
                        row[f"status_p{i}"] = res["statuses"][i]
                    row["step_count"] = res["step_count"]
                    row["episode_duration_sec"] = res["duration_sec"]
                    row["error"] = res.get("error", "")
                    writer.writerow(row)
                    f.flush()
                    rows_written += 1
                    rewards = res["rewards"]
                    print(
                        f"  [{rows_written}/{n_total}] seed={seed} rot={rot} ep={ep}: "
                        f"rewards={rewards} steps={res['step_count']} ({res['duration_sec']:.0f}s)"
                    )

    print(f"\nwrote {rows_written} rows to {output_path}")
    print()
    print("=== aggregate ===")
    # per-agent total wins
    import polars as pl

    df = pl.read_csv(output_path)
    agent_set = set()
    for c in ["agent_p0", "agent_p1", "agent_p2", "agent_p3"]:
        agent_set.update(df[c].to_list())
    for a in sorted(agent_set):
        n = 0
        w = 0
        for row in df.iter_rows(named=True):
            for i in range(4):
                if row[f"agent_p{i}"] == a:
                    n += 1
                    if row[f"reward_p{i}"] > 0:
                        w += 1
        if n > 0:
            print(f"  {a:55s}: {w}/{n}  ({w/n*100:.0f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
