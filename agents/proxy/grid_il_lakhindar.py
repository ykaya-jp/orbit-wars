"""GridSEResNet IL agent trained on Lakhindar (= TRUE Top 10 LB players).

Source: kovi (LB ~1480) 102 replays + Shun_PI (LB ~1515) 76 replays.
Training: 20 ep, fire_weight=5.0, val acc 0.967 (vs bovard IL v2 0.923).
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

_WEIGHTS = _THIS_DIR / "grid_il_lakhindar.pt"
if not _WEIGHTS.exists():
    raise FileNotFoundError(f"weights not found: {_WEIGHTS}")

agent = make_grid_agent(_WEIGHTS, device="cpu", suppress_no_op=False)
