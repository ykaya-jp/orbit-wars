"""IL Lakhindar with aggressive inference (= no_op_temperature=5, min_ship_floor=20)."""

from __future__ import annotations

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent.parent
_SRC = _PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from orbit_wars.grid_agent import make_grid_agent  # noqa: E402

_WEIGHTS = _THIS_DIR / "grid_il_lakhindar.pt"
if not _WEIGHTS.exists():
    raise FileNotFoundError(f"weights not found: {_WEIGHTS}")

# Down-weight no_op heavily (= force more firing) + force min 20 ships per launch
agent = make_grid_agent(
    _WEIGHTS,
    device="cpu",
    no_op_temperature=5.0,  # 5x harder for model to choose no_op
    min_ship_floor=20,  # min 20 ships per launch (= top tier kovi/Shun_PI median)
)
