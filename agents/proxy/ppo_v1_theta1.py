"""MaskablePPO θ.1 agent (= 50k step training vs random opponents)."""

from __future__ import annotations

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent.parent
_SRC = _PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from orbit_wars.ppo_agent import make_ppo_agent  # noqa: E402

_WEIGHTS = _THIS_DIR / "ppo_v1_theta1.zip"
if not _WEIGHTS.exists():
    raise FileNotFoundError(f"weights not found: {_WEIGHTS}")

agent = make_ppo_agent(_WEIGHTS, device="cpu", deterministic=True)
