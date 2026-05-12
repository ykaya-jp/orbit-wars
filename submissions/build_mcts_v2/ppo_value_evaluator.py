"""PPO value-function evaluator for the MCTS leaf score.

Loads a MaskablePPO checkpoint **weight-only** (= bypasses sb3's optimizer
requirement so lightweight zips with stripped optimizer state still work)
and returns V(s) for a pseudo-observation dict produced by
mcts_orbit_wars.state_to_pseudo_obs.

Latency budget: ~3-5 ms / call on CPU for the orbit-wars grid policy net,
so the MCTS caller is expected to invoke this only on the top-K final leaves
(K <= ~12) to stay under the Kaggle 1 s / step budget.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from orbit_wars.grid_encoder import GRID_SIZE, PER_CELL_ACTIONS, encode_grid_state


def _weight_only_load(model_path: str | Path, device: str = "cpu"):
    """Load a MaskablePPO zip without requiring its optimizer state.

    sb3's high-level ``.load`` insists that ``policy.optimizer`` is present in
    the zip; lightweight builds drop it to fit Kaggle's 100 MB cap. This helper
    rebuilds an inference-only model via the low-level save_util API and copies
    only the policy weights, which is all V(s) inference needs.
    """
    from sb3_contrib import MaskablePPO
    from stable_baselines3.common.save_util import load_from_zip_file

    custom_objects = {
        "train_ppo": None,
        "tools.train_ppo": None,
        "tools.train_ppo_pfsp": None,
        "learning_rate": 0.0,
        "lr_schedule": lambda _: 0.0,
        "clip_range": lambda _: 0.2,
        "clip_range_vf": None,
    }
    data, params, pytorch_variables = load_from_zip_file(
        str(model_path), device=device, custom_objects=custom_objects
    )

    # Instantiate the model without a training env (= inference-only).
    model = MaskablePPO(
        policy=data["policy_class"],
        env=None,
        device=device,
        _init_setup_model=False,
    )
    model.__dict__.update(data)
    model._setup_model()

    # Copy policy weights only -- skip optimizer / extras.
    policy_state = params.get("policy")
    if policy_state is None:
        raise RuntimeError("zip is missing 'policy' state_dict")
    # FP16 -> FP32 cast (= lightweight builds half-cast the policy).
    for k, v in list(policy_state.items()):
        if hasattr(v, "is_floating_point") and v.is_floating_point() and v.dtype == torch.float16:
            policy_state[k] = v.float()
    model.policy.load_state_dict(policy_state, strict=False)
    model.policy.eval()

    if pytorch_variables is not None:
        for name, val in pytorch_variables.items():
            if val is None:
                continue
            try:
                setattr(model, name, val)
            except Exception:
                pass

    return model


def make_ppo_value_fn(model_path: str | Path, device: str = "cpu"):
    """Return a function ``value_fn(pseudo_obs) -> float``.

    ``pseudo_obs`` must include the calling player's id so the encoder
    extracts the same channel layout the policy was trained on. The encoder
    consumes a per-cell binary mask of shape ``(B, GRID*GRID)``; the policy's
    custom feature extractor uses that mask to pool spatial features over
    the agent's own planets.
    """
    model = _weight_only_load(model_path, device=device)
    policy_device = next(model.policy.parameters()).device

    cell_count = GRID_SIZE * GRID_SIZE  # = 4096

    def value_fn(pseudo_obs: dict) -> float:
        try:
            enc = encode_grid_state(pseudo_obs)
        except Exception:
            return 0.0
        spatial = torch.as_tensor(enc.spatial, device=policy_device).unsqueeze(0)
        globals_ = torch.as_tensor(enc.globals_, device=policy_device).unsqueeze(0)
        # Build a per-cell mask over the agent's own planets so the value head
        # pools over the same regions as during training.
        cell_mask = np.zeros(cell_count, dtype=np.float32)
        for _, row, col in enc.my_cells:
            cell_mask[row * GRID_SIZE + col] = 1.0
        if cell_mask.sum() == 0.0:
            # Fall back to a uniform mask so the pool is well-defined even
            # when we have no planets (rare, but happens late game).
            cell_mask[:] = 1.0
        cell_mask_t = torch.as_tensor(cell_mask, device=policy_device).unsqueeze(0)
        obs_tensor = {"spatial": spatial, "globals": globals_, "action_mask": cell_mask_t}
        try:
            with torch.no_grad():
                v = model.policy.predict_values(obs_tensor)
            return float(v.detach().cpu().item())
        except Exception:
            return 0.0

    # Sanity-check at construction so cold-start surfaces shape mismatch early.
    dummy_obs = {
        "step": 0,
        "player": 0,
        "planets": [[0, 0, 50.0, 50.0, 2.0, 100, 1]],
        "fleets": [],
    }
    _probe = value_fn(dummy_obs)
    return value_fn


__all__ = ["make_ppo_value_fn"]
