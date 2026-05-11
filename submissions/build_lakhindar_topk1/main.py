"""Lakhindar IL + topk1 wrapper (= keep only LARGEST-SHIPS move per turn).

Hypothesis: top-tier (kovi 0.10 launch/step) use few decisive large-fleet moves.
Source: konbu17/train-submit-v4-ml-validator-topk1-tutorial (+75 LB claim).
Day 2 ablation: konbu17+topk1 LB 922 vs base 989 (= -67, but isolation ambiguous);
Lakhindar IL has not been LB-tested yet → this submit isolates IL+topk1 effect.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from orbit_wars.grid_agent import make_grid_agent

_WEIGHTS = _HERE / "grid_il_lakhindar.pt"
_base_agent = make_grid_agent(_WEIGHTS, device="cpu", suppress_no_op=False)


def agent(observation, configuration=None):
    moves = _base_agent(observation, configuration)
    if not moves or len(moves) <= 1:
        return moves
    try:
        best = max(moves, key=lambda m: m[2] if len(m) > 2 else 0)
        return [best]
    except Exception:
        return moves
