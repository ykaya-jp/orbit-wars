"""GridSEResNet IL agent (Phase η v2 pilot).

Loads agents/proxy/grid_il_v1.pt and exposes `agent(observation, configuration)`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent.parent
_SRC = _PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from orbit_wars.grid_agent import make_grid_agent  # noqa: E402

_WEIGHTS = _THIS_DIR / "grid_il_v1.pt"
if not _WEIGHTS.exists():
    raise FileNotFoundError(
        f"weights not found: {_WEIGHTS}. run: make grid-il-train (TBD) or "
        f"python -m tools.train_grid_il --bc-dir data/processed/grid_bc/ "
        f"--output {_WEIGHTS}"
    )

agent = make_grid_agent(_WEIGHTS, device="cpu", suppress_no_op=False)
