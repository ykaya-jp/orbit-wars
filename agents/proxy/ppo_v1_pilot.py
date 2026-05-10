"""PPO pilot agent (Phase 2 — 100k steps vs heuristic v2)。

stable_baselines3 PPO checkpoint (.zip) を load し kaggle_environments 互換の
`agent(observation, configuration)` を export する。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent.parent
_SRC = _PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from orbit_wars.encoders import encode_state  # noqa: E402
from orbit_wars.gym_env import _decode_action_array  # noqa: E402

_WEIGHTS = _THIS_DIR / "ppo_v1_pilot.zip"
if not _WEIGHTS.exists():
    raise FileNotFoundError(
        f"weights not found: {_WEIGHTS}. run `make ppo-train` (TBD) or "
        f"`uv run python -m tools.train_ppo --opponent heuristic --total-steps 100000 "
        f"--output {_WEIGHTS}`"
    )

from stable_baselines3 import PPO  # noqa: E402

_MODEL = PPO.load(_WEIGHTS, device="cpu")


def agent(observation, configuration=None):
    try:
        enc = encode_state(observation)
        if not enc.my_planet_ids:
            return []
        action, _ = _MODEL.predict(enc.state_vec.astype(np.float32), deterministic=True)
        return _decode_action_array(np.asarray(action), observation, enc.my_planet_ids)
    except Exception:
        return []
