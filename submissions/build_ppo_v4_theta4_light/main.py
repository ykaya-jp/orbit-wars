"""MaskablePPO theta.4 (= 200k step PFSP self-history training, Day 4 candidate).

Trained 2026-05-12 on Colab Pro+ A100 80GB.
- Warm-start from theta.3 (50k IL+rule-base opponents)
- 200k additional steps with PFSP self-history (pool max 8, save every 10k)
- Final explained_variance ~0.7-0.9, healthy value function
- Sourced from ckpt_step_200000.zip (= identical weight to final save)
"""

import sys
from pathlib import Path

# kaggle_environments loads agents via exec(), which does NOT define __file__.
# On Kaggle production workers the tar.gz is extracted to a normal directory
# and __file__ is defined. Support both for symmetric local-vs-prod behaviour.
try:
    _HERE = Path(__file__).resolve().parent
except NameError:
    cwd = Path.cwd()
    candidates = [
        cwd / "submissions" / "build_ppo_v4_theta4_light",
        cwd / "build_ppo_v4_theta4_light",
        cwd.parent / "submissions" / "build_ppo_v4_theta4_light",
        cwd,
    ]
    _HERE = next(
        (c for c in candidates if (c / "ppo_inference.py").exists()),
        cwd,
    )
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from ppo_inference import make_ppo_agent

_WEIGHTS = _HERE / "ppo_v4_theta4.zip"
agent = make_ppo_agent(_WEIGHTS, device="cpu", deterministic=True)
