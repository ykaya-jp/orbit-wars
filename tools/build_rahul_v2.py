"""Rebuild Rahul Chauhan's ELITE-BOT v5 — v2 with proper redefinition handling.

Previous version concatenated all cells in order, which left earlier
definitions (= e.g. fleet_speed v1) shadowed by later redefinitions in the
same file. Result: silent broken behavior, 0/29 vs konbu17 in tournament.

This v2 takes the LAST definition of each named class/function from the
notebook cells via regex, in CLASSES dependency order, producing a clean
linear submission.
"""

from __future__ import annotations

import json
import re
import sys
import traceback
from pathlib import Path

NB_PATH = Path(
    "docs/research/public_kernels/orbit-wars-target-score-2000-4/orbit-wars-target-score-2000-4.ipynb"
)
OUT_PATH = Path("experiments/rahul_2000/main.py")

CLASSES = [
    "fleet_speed",
    "hits_sun",
    "Planet",
    "Fleet",
    "GameState",
    "Predictor",
    "SimP",
    "SimF",
    "sim_step",
    "clone",
    "eval_sim",
    "run_actions",
    "EliteEval",
    "MCTSNode",
    "MCTSEngine",
    "OpponentModel",
    "FleetInterceptor",
    "CometOpp",
    "DiplomacyEngine",
    "BeamSearch",
    "CounterfactualRisk",
    "budget",
    "StrategyEngine",
    "elite_bot_v5",
]


def _extract_last_def(src_full: str, name: str) -> str | None:
    """Find the LAST `def name(` or `class name` block in src_full and return
    its source code (until the next top-level def/class/CONST or EOF)."""
    # Match top-level def/class for `name`
    pattern = re.compile(rf"(?m)^(def {re.escape(name)}\(|class {re.escape(name)}\b)")
    matches = list(pattern.finditer(src_full))
    if not matches:
        return None
    last = matches[-1]
    start = last.start()
    # Find the next top-level statement after this match (= same column 0,
    # excluding decorators and comments at top-level which look like CODE).
    rest = src_full[last.end() :]
    # Search for next top-level (column 0) statement.
    # - def func(   : start of next function
    # - class Foo   : start of next class
    # - TOP_CONST = : top-level constant (>= 2 uppercase chars to avoid matching
    #   single-letter type annotations like `P: dict` inside a function signature)
    # Exclude `==` (comparison) by negative lookahead.
    end_pattern = re.compile(
        r"(?m)^(?:def [a-zA-Z_]\w*\(|class [A-Z][\w]*[\(:]|[A-Z_]{2,}[A-Z0-9_]*\s*=(?!=))"
    )
    em = end_pattern.search(rest)
    if em:
        end = last.end() + em.start()
    else:
        end = len(src_full)
    block = src_full[start:end].rstrip()
    return block


def main() -> int:
    if not NB_PATH.exists():
        print(f"notebook not found: {NB_PATH}")
        return 1

    with NB_PATH.open() as f:
        nb = json.load(f)

    # Concatenate ALL code cell sources into a single string.
    # Filter out cells that are only viz/test runs (= contain plt.show, env0.run, etc.)
    SKIP_PATTERNS = (
        "plt.show",
        "plt.figure",
        "plt.subplot",
        "%%capture",
        "from IPython",
        "display(",
        "%matplotlib",
        "imshow",
    )

    big_src_parts: list[str] = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", "")
        if isinstance(src, list):
            src = "".join(src)
        s = src.strip()
        if not s:
            continue
        first = s.split("\n", 1)[0]
        if first.startswith(("!", "%")):
            continue
        # Skip cells that are pure visualization/training/benchmark
        if any(p in src for p in SKIP_PATTERNS):
            # but keep cells that ALSO define classes/funcs we need
            if not any(re.search(rf"(?m)^(def {c}\(|class {c}\b)", src) for c in CLASSES):
                continue
        big_src_parts.append(src)
    big_src = "\n\n".join(big_src_parts)
    print(f"merged {len(big_src_parts)} cells → {len(big_src)} bytes")

    # Extract last def of each class/func
    extracted: dict[str, str] = {}
    missing: list[str] = []
    for name in CLASSES:
        block = _extract_last_def(big_src, name)
        if block is None:
            missing.append(name)
            continue
        extracted[name] = block
        print(f"  {name}: {len(block)} bytes")

    if missing:
        print(f"\nMISSING: {missing}")
        return 2

    # Build final submission
    header = (
        "# ELITE-BOT v5 (Rahul Chauhan, public notebook target-score-2000-4)\n"
        "# v2 build: last-definition-per-name regex extraction (redef-safe)\n"
        "# Source: kaggle.com/code/rahulchauhan016/orbit-wars-target-score-2000-4\n\n"
        "import math, time, random\n"
        "from collections import defaultdict\n"
        "from dataclasses import dataclass, field\n"
        "from typing import List, Tuple, Dict, Optional\n\n"
        "SUN_X, SUN_Y = 50.0, 50.0\n"
        "SUN_RADIUS = 5.0\n"
        "INNER_ORBIT_R = 30.0\n"
        "MAX_TIME_MS = 900\n"
        "PHASE_THRESHOLDS = (0.22, 0.58)\n\n"
    )

    body_parts = [extracted[name] for name in CLASSES]
    body = "\n\n".join(body_parts)

    footer = (
        "\n\n# === agent entrypoint ===\n"
        "_OPP_V5 = OpponentModel()\n\n"
        "def agent(obs, config=None):\n"
        "    global _OPP_V5\n"
        "    return elite_bot_v5(obs, config)\n"
    )

    out = header + body + footer
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(out, encoding="utf-8")
    print(f"\nwrote {OUT_PATH} ({len(out)} bytes, ~{out.count(chr(10))} lines)")

    # Compile sanity
    try:
        compile(out, str(OUT_PATH), "exec")
        print("syntax OK")
    except SyntaxError as e:
        print(f"SYNTAX ERROR: {e}")
        return 4
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except Exception:
        traceback.print_exc()
        rc = 99
    sys.exit(rc)
