"""IL v2 with no-op suppression (Phase 0.4 fix)。

train_il_proxy が no-op majority bias に陥った workaround として、inference 時に
NO_OP_CLASS の logit を -inf にして必ず fire class を選ばせる。capacity 不足は
decode_action が natural に skip。
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

agent = make_nn_agent(_WEIGHTS, device="cpu", suppress_no_op=True)
