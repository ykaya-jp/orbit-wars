"""Smoke test 用の random-init NN agent (Phase 0.2)。

`agents/proxy/nn_random.pt` を load して `agent(observation, configuration)` を export する。
tournament で動くかの sanity check 用 — 学習されていないので random play 並みの強さ。

Usage:
    make tournament TOURN_AGENTS="src/orbit_wars/agent.py agents/proxy/nn_random.py random"
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `orbit_wars` importable. kaggle_environments の path-style agent では
# exec_dir が `agents/proxy/` なので、project の src/ 配下を sys.path に追加する。
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent.parent  # orbit-wars/
_SRC = _PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from orbit_wars.nn_agent import make_nn_agent  # noqa: E402

_WEIGHTS = _THIS_DIR / "nn_random.pt"
if not _WEIGHTS.exists():
    raise FileNotFoundError(
        f"weights not found: {_WEIGHTS}. "
        f"run `python -c 'from orbit_wars.nn_agent import save_random_init; "
        f'save_random_init("{_WEIGHTS}")\'`'
    )

# Module top-level agent function (= what kaggle_environments will call).
agent = make_nn_agent(_WEIGHTS, device="cpu")
