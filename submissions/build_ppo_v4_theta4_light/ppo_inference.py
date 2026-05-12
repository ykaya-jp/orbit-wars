"""PPO inference adapter for Kaggle submission."""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import math
import numpy as np
import torch

# Import from local copy of orbit_wars
from orbit_wars import physics
from orbit_wars.grid_encoder import (
    ANGLE_BINS, GRID_SIZE, NO_OP_CLASS, PER_CELL_ACTIONS,
    SHIP_FRAC_BINS, encode_grid_state,
)


def _decode(class_id, home_capacity):
    if class_id == NO_OP_CLASS:
        return None
    cls = class_id - 1
    angle_bin = cls // SHIP_FRAC_BINS
    frac_bin = cls % SHIP_FRAC_BINS
    angle = (angle_bin + 0.5) * (2 * math.pi / ANGLE_BINS)
    if angle > math.pi:
        angle -= 2 * math.pi
    frac_to_ships = {0: 5, 1: 20, 2: 60, 3: 200, 4: 500}
    ships = min(frac_to_ships.get(frac_bin, 5), max(home_capacity, 1))
    return angle, int(ships)


def _home_capacity(ships, max_fraction=0.85, reserve=5):
    return max(0, min(int(ships * max_fraction), ships - reserve))


def _weight_only_load(model_path, device="cpu"):
    """Load policy weights only -- the lightweight zip drops optimizer state,
    which sb3's default loader requires. Reconstruct the model and copy the
    policy state_dict directly."""
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
    model = MaskablePPO(
        policy=data["policy_class"],
        env=None,
        device=device,
        _init_setup_model=False,
    )
    model.__dict__.update(data)
    model._setup_model()
    policy_state = params.get("policy")
    if policy_state is None:
        raise RuntimeError("zip is missing 'policy' state_dict")
    for k, v in list(policy_state.items()):
        if hasattr(v, "is_floating_point") and v.is_floating_point() and v.dtype == torch.float16:
            policy_state[k] = v.float()
    model.policy.load_state_dict(policy_state, strict=False)
    model.policy.eval()
    return model


def make_ppo_agent(model_path, device="cpu", deterministic=True, sun_safety_margin_rad=0.035):
    model = _weight_only_load(model_path, device=device)

    def agent(observation, configuration=None):
        try:
            enc = encode_grid_state(observation)
            if not enc.my_cells:
                return []
            actions = []
            planets_dict = {int(p[0]): p for p in observation.get("planets", [])}
            player = int(observation.get("player", 0) or 0)
            for pid, row, col in enc.my_cells:
                planet = planets_dict.get(pid)
                if planet is None or int(planet[1]) != player:
                    continue
                home_ships = int(planet[5])
                home_cap = _home_capacity(home_ships)
                if home_cap <= 0:
                    continue
                cell_mask = np.zeros((GRID_SIZE * GRID_SIZE,), dtype=np.float32)
                cell_mask[row * GRID_SIZE + col] = 1.0
                obs = {
                    "spatial": enc.spatial.astype(np.float32),
                    "globals": enc.globals_.astype(np.float32),
                    "action_mask": cell_mask,
                }
                action_mask_full = np.repeat(cell_mask, PER_CELL_ACTIONS).astype(bool)
                action_mask_full[(row * GRID_SIZE + col) * PER_CELL_ACTIONS] = True
                with torch.no_grad():
                    action, _ = model.predict(obs, deterministic=deterministic, action_masks=action_mask_full)
                cell_id, action_class = divmod(int(action), PER_CELL_ACTIONS)
                if cell_id != row * GRID_SIZE + col:
                    continue
                decoded = _decode(action_class, home_cap)
                if decoded is None:
                    continue
                angle, ships = decoded
                if ships <= 0 or ships > home_cap:
                    continue
                home_x, home_y = float(planet[2]), float(planet[3])
                safe = physics.safe_angle_around(home_x, home_y, angle, margin=sun_safety_margin_rad)
                actions.append([float(pid), float(safe), int(ships)])
            return actions
        except Exception:
            return []
    return agent
