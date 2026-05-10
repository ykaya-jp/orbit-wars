"""IL v2 (fire-weighted, Phase 0.4 retrain)。

bovard top10 dataset (158k samples × 8 top tier teams) で 10 epoch 学習した
SimpleMLPPolicy。ローカル goldcheck で proxy 役を担う + 自家 agent の指標として使う。

Notes:
  - val acc 93.5% だが no-op の majority bias を含む可能性 → launch class へ
    class weight を入れた retrain (Phase 0.4 v2) が next step
"""

from __future__ import annotations

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent.parent
_SRC = _PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from orbit_wars.nn_agent import make_nn_agent  # noqa: E402

_WEIGHTS = _THIS_DIR / "il_v2.pt"
if not _WEIGHTS.exists():
    raise FileNotFoundError(f"weights not found: {_WEIGHTS}. run: make il-train")

agent = make_nn_agent(_WEIGHTS, device="cpu")
