"""Ensemble agent: rudra + zachary + konbu17 (topk1 wrapper).

Strategy: each base agent generates moves; we pick the one with the LARGEST
ships per launch (= aggregate across all 3 sub-agents, take topk1).
"""

import importlib.util
import sys
from pathlib import Path

# Embed all 3 agents inline for self-contained submission
# Submission file is ~85 KB total

_HERE = Path(__file__).resolve().parent

# Load each as a separate module
def _load(name: str, src_path: Path):
    spec = importlib.util.spec_from_file_location(name, str(src_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Find the embedded agents (they should be co-located after build)
_RUDRA_PATH = _HERE / "rudra_agent.py"
_ZACHARY_PATH = _HERE / "zachary_agent.py"
_KONBU17_PATH = _HERE / "konbu17_agent.py"

# Lazy load on first call
_agents_loaded = []


def _ensure_loaded():
    if _agents_loaded:
        return _agents_loaded
    if _RUDRA_PATH.exists():
        try:
            m = _load("ensemble_rudra", _RUDRA_PATH)
            _agents_loaded.append(("rudra", m.agent))
        except Exception:
            pass
    if _ZACHARY_PATH.exists():
        try:
            m = _load("ensemble_zachary", _ZACHARY_PATH)
            _agents_loaded.append(("zachary", m.agent))
        except Exception:
            pass
    if _KONBU17_PATH.exists():
        try:
            m = _load("ensemble_konbu17", _KONBU17_PATH)
            _agents_loaded.append(("konbu17", m.agent))
        except Exception:
            pass
    return _agents_loaded


def agent(obs, *args, **kwargs):
    """Combine moves from all sub-agents, keep top-1 by ship size."""
    sub_agents = _ensure_loaded()
    all_moves = []
    for _name, fn in sub_agents:
        try:
            moves = fn(obs, *args, **kwargs)
            if moves:
                all_moves.extend(moves)
        except Exception:
            continue
    if not all_moves:
        return []
    # topk1: pick the move with largest ships
    try:
        # Deduplicate by (from_id, similar_angle): keep largest ships per source planet
        per_source = {}
        for m in all_moves:
            if len(m) < 3:
                continue
            src = int(m[0])
            ships = m[2] if len(m) > 2 else 0
            if src not in per_source or ships > per_source[src][2]:
                per_source[src] = m
        best_moves = list(per_source.values())
        best_moves.sort(key=lambda m: -m[2])
        return [best_moves[0]]  # topk1
    except Exception:
        return [all_moves[0]]
