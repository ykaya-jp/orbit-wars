"""MCTS v2 = MCTS beam search + PPO theta.4 leaf value evaluator hybrid.

Phase alpha x beta hybrid (= score 2000+ roadmap §α x β):
- beam search depth=3, width=24, bowwow big-stack + step-dependent prune.
- final leaf top_k=6 rescored with PPO V(s) (handcrafted_weight=1.0,
  ppo_value_weight=0.05 -- scale ~ matches handcrafted score magnitude).

Cold-start ~1-2 s (sb3 model load); per-step latency target < 600 ms.

Fallback: if PPO load fails the agent degrades gracefully to handcrafted-only
MCTS v0 behaviour (= submissions/build_mcts_v1).
"""

from __future__ import annotations

import sys
from pathlib import Path

# kaggle_environments loads agents via exec() (= local smoke path), which does
# NOT define __file__. On Kaggle production workers the tar.gz is extracted to
# a normal directory and __file__ is defined. Support both.
try:
    _HERE = Path(__file__).resolve().parent
except NameError:
    cwd = Path.cwd()
    candidates = [
        cwd / "submissions" / "build_mcts_v2",
        cwd / "build_mcts_v2",
        cwd.parent / "submissions" / "build_mcts_v2",
        cwd,
    ]
    _HERE = next(
        (c for c in candidates if (c / "ppo_value_evaluator.py").exists()),
        cwd,
    )
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from mcts_orbit_wars import BeamConfig, select_action

_CFG = BeamConfig(
    # Reverting to the depth=1 + alpha=10 + ppo_weight=200 config that hit
    # 2/8 vs starter post sim-parity fix. Tried alpha=50 to over-weight
    # planet capture and saw 1/8 -- ship cost dominated, search starved
    # itself out. The 6-fix list in docs/research/2026-05-13-mcts-loss-
    # analysis.md needs careful per-fix AB measurement, not a stacked
    # attempt in one shot.
    depth=1,
    beam_width=32,
    fractions=(0.5, 0.85, 1.0),
    min_launch_ships=40,
    min_send_fraction=0.5,
    leaf_alpha=10.0,
    leaf_beta=1.0,
    leaf_gamma=1.0,
    leaf_delta=8.0,
    terminal_bonus=1000.0,
    max_top_actions_per_step=50,
    handcrafted_weight=1.0,
    ppo_value_weight=200.0,
    leaf_top_k_ppo=12,
    step_dependent_prune=True,
    phase_mid_start=50,
    phase_late_start=300,
    min_launch_early=40,
    min_launch_mid=60,
    min_launch_late=80,
)

import os

_PPO_VALUE_FN = None
_PPO_LOAD_ERROR = None
try:
    from ppo_value_evaluator import make_ppo_value_fn

    _PPO_VALUE_FN = make_ppo_value_fn(_HERE / "ppo_v4_theta4.zip", device="cpu")
except Exception as _exc:
    # Submission must still run as handcrafted-only MCTS if torch / sb3 / load fails.
    _PPO_VALUE_FN = None
    _PPO_LOAD_ERROR = f"{type(_exc).__name__}: {_exc}"
    # Emit one line to stderr so silent fallback is visible during smoke tests.
    if os.environ.get("MCTS_V2_DEBUG", "1") != "0":
        import sys as _sys

        _sys.stderr.write(f"[mcts_v2] PPO load FAILED -> handcrafted-only: {_PPO_LOAD_ERROR}\n")
        _sys.stderr.flush()


def agent(observation, configuration=None):
    try:
        return select_action(observation, cfg=_CFG, ppo_value_fn=_PPO_VALUE_FN)
    except Exception:
        return []
