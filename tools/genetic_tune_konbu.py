"""Genetic tuning of konbu17 hybrid constants (Phase ε).

Approach:
  - Pick K candidate constants from konbu17 main.py (high-impact ones identified
    by Tamrazov v4 lineage diff).
  - Each generation: spawn N mutants (Gaussian perturbation around current best),
    score them via 4P tournament against fixed opponents (= konbu17 base / Marco
    / SPNE / orbitbotnext).
  - Keep the best mutant as next generation's seed.
  - After G generations, dump tuned weights and constants.

Default operates on a small list of high-impact constants. Extend the list
manually after each generation as you learn what moves the needle.

Usage:
    python -m tools.genetic_tune_konbu \\
        --base experiments/konbu17_hybrid \\
        --output experiments/konbu_tuned/ \\
        --opponents experiments/marco_1060/main.py random \\
        --generations 3 --mutants 4 --eps-per-mutant 8

Notes:
  - 1 generation = N mutants × M episodes / mutant. Plan budget accordingly.
  - 4P tournament 1 episode = ~30s wallclock.
  - Genetic tuner is exploratory; escape early on regression.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent

# High-impact constants identified by reading konbu17 main.py.
# (name, lo, hi, type=int|float)
CONSTANTS = [
    ("_VAL_THRESHOLD", 0.20, 0.55, "float"),
    ("ATTACK_COST_TURN_WEIGHT", 0.30, 0.70, "float"),
    ("SNIPE_COST_TURN_WEIGHT", 0.30, 0.65, "float"),
    ("HOSTILE_TARGET_VALUE_MULT", 1.5, 2.5, "float"),
    ("OPENING_HOSTILE_TARGET_VALUE_MULT", 1.2, 2.0, "float"),
    ("REINFORCE_VALUE_MULT", 1.0, 1.7, "float"),
    ("FOUR_PLAYER_TARGET_MARGIN", 1, 5, "int"),
    ("WEAK_ENEMY_THRESHOLD", 60, 200, "int"),
    ("ELIMINATION_BONUS", 20.0, 80.0, "float"),
    ("PROACTIVE_DEFENSE_RATIO", 0.15, 0.45, "float"),
    ("MULTI_ENEMY_PROACTIVE_RATIO", 0.20, 0.50, "float"),
    ("CRASH_EXPLOIT_MIN_TOTAL_SHIPS", 5, 20, "int"),
]


@dataclass
class Mutant:
    label: str
    overrides: dict
    main_py_path: Path
    weights_path: Path
    fitness: float = 0.0
    n_games: int = 0


def _read_value(text: str, name: str) -> float:
    m = re.search(rf"^{re.escape(name)}\s*=\s*([\d.]+)", text, re.M)
    if not m:
        raise ValueError(f"constant {name} not found")
    return float(m.group(1))


def _patch_constant(text: str, name: str, value: float | int) -> str:
    if isinstance(value, int):
        repl = f"{name} = {value}"
    else:
        repl = f"{name} = {value:.4f}"
    new, n = re.subn(rf"^{re.escape(name)}\s*=\s*[\d.]+", repl, text, count=1, flags=re.M)
    if n != 1:
        raise ValueError(f"failed to patch {name}")
    return new


def _materialize_mutant(base_dir: Path, out_dir: Path, label: str, overrides: dict) -> Mutant:
    out_dir.mkdir(parents=True, exist_ok=True)
    text = (base_dir / "main.py").read_text(encoding="utf-8")
    for name, val in overrides.items():
        text = _patch_constant(text, name, val)
    (out_dir / "main.py").write_text(text, encoding="utf-8")
    weights = base_dir / "weights.npz"
    if weights.exists():
        shutil.copy(weights, out_dir / "weights.npz")
    return Mutant(
        label=label,
        overrides=overrides,
        main_py_path=out_dir / "main.py",
        weights_path=out_dir / "weights.npz",
    )


def _spawn_mutants(
    base_dir: Path,
    work_dir: Path,
    current: dict,
    n: int,
    rng: np.random.Generator,
    sigma: float = 0.15,
) -> list[Mutant]:
    """Generate n mutants with Gaussian perturbation around current."""
    mutants: list[Mutant] = []
    for i in range(n):
        overrides = {}
        for name, lo, hi, kind in CONSTANTS:
            cur = current[name]
            scale = (hi - lo) * sigma
            val = float(cur) + rng.normal(0, scale)
            val = max(lo, min(hi, val))
            if kind == "int":
                val = int(round(val))
            overrides[name] = val
        label = f"mut_{i:03d}"
        mut_dir = work_dir / label
        mutants.append(_materialize_mutant(base_dir, mut_dir, label, overrides))
    return mutants


def _evaluate_mutant(mutant: Mutant, opponents: list[str], seeds: list[int]) -> float:
    """Run 4P FFA: mutant + 3 opponents, multiple seeds & rotations.

    Returns win rate (0-1) for the mutant.
    """
    if len(opponents) < 3:
        # pad with random
        opponents = opponents + ["random"] * (3 - len(opponents))
    elif len(opponents) > 3:
        opponents = opponents[:3]

    agents = [str(mutant.main_py_path)] + opponents
    csv_path = REPO_ROOT / f"/tmp/genetic_{mutant.label}.csv"
    if csv_path.exists():
        csv_path.unlink()

    cmd = [
        sys.executable,
        "-m",
        "tools.tournament_4p",
        "--agents",
        *agents,
        "--episodes",
        "1",
        "--seeds",
        ",".join(str(s) for s in seeds),
        "--rotations",
        "4",
        "--output",
        str(csv_path),
    ]
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(f"  evaluate {mutant.label}: ERROR")
        return 0.0

    import polars as pl

    if not csv_path.exists():
        return 0.0
    df = pl.read_csv(csv_path)
    if len(df) == 0:
        return 0.0
    # mutant is at p0 of `agents`, but rotation shifts it. Find mutant rows.
    # Path may be relative; resolve before comparing to REPO_ROOT.
    mutant_norm = str(mutant.main_py_path.resolve().relative_to(REPO_ROOT))
    n = 0
    w = 0
    for row in df.iter_rows(named=True):
        for i in range(4):
            if row[f"agent_p{i}"] == mutant_norm:
                n += 1
                if row[f"reward_p{i}"] > 0:
                    w += 1
    mutant.n_games = n
    mutant.fitness = w / max(n, 1)
    return mutant.fitness


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="experiments/konbu17_hybrid")
    ap.add_argument("--output", default="experiments/konbu_tuned/")
    ap.add_argument(
        "--opponents",
        nargs="+",
        default=[
            "experiments/marco_1060/main.py",
            "experiments/orbitbotnext/main.py",
            "random",
        ],
    )
    ap.add_argument("--generations", type=int, default=3)
    ap.add_argument("--mutants", type=int, default=4)
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--sigma", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    base_dir = Path(args.base)
    base_text = (base_dir / "main.py").read_text(encoding="utf-8")

    # Read current values for all constants
    current = {name: _read_value(base_text, name) for name, _, _, _ in CONSTANTS}
    print("base constants:")
    for k, v in current.items():
        print(f"  {k} = {v}")

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir = out_dir / "work"
    work_dir.mkdir(exist_ok=True)

    rng = np.random.default_rng(args.seed)
    seeds = [int(s) for s in args.seeds.split(",")]

    history: list[dict] = []
    for g in range(1, args.generations + 1):
        print(f"\n=== generation {g}/{args.generations} ===")
        # Always include the un-mutated current as a baseline mutant
        baseline = _materialize_mutant(base_dir, work_dir / "baseline", "baseline", dict(current))
        mutants = [baseline] + _spawn_mutants(
            base_dir, work_dir, current, args.mutants, rng, args.sigma
        )

        for m in mutants:
            wr = _evaluate_mutant(m, args.opponents, seeds)
            print(f"  {m.label}: WR={wr:.2f} ({m.n_games} games)  overrides={m.overrides}")

        # pick best
        best = max(mutants, key=lambda x: x.fitness)
        print(f"  best: {best.label} WR={best.fitness:.2f}")
        history.append(
            {
                "gen": g,
                "best": best.label,
                "fitness": best.fitness,
                "constants": best.overrides,
            }
        )
        current = best.overrides

    # save final
    (out_dir / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    _materialize_mutant(base_dir, out_dir, "final", current)
    print(f"\nfinal saved to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
