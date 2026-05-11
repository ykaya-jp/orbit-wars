"""Lakhindar IL pure (= TRUE Top 10 LB players kovi/Shun_PI replay BC, val acc 0.967)."""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from orbit_wars.grid_agent import make_grid_agent

_WEIGHTS = _HERE / "grid_il_lakhindar.pt"
agent = make_grid_agent(_WEIGHTS, device="cpu", suppress_no_op=False)
