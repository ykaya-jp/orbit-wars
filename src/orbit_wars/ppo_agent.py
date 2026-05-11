"""Inference wrapper for MaskablePPO agent (Phase θ).

Loads a saved MaskablePPO checkpoint and exposes a kaggle_environments
compatible `agent(observation, configuration)` callable.

Strategy:
  - Encode obs → spatial + globals + cell_mask
  - Forward through MaskablePPO policy
  - Decode action int → (cell, action_class) → (planet_id, angle, ships)
  - Apply this action to the corresponding my_planet
  - Repeat forward for **all my_planets** (predict an action for each)
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import torch

try:
    from . import physics
    from .grid_encoder import (
        ANGLE_BINS,
        GRID_SIZE,
        NO_OP_CLASS,
        PER_CELL_ACTIONS,
        SHIP_FRAC_BINS,
        encode_grid_state,
    )
except (ImportError, KeyError):
    _SRC = Path(__file__).resolve().parent.parent
    if str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))
    import physics  # type: ignore[no-redef]
    from grid_encoder import (  # type: ignore[no-redef]
        ANGLE_BINS,
        GRID_SIZE,
        NO_OP_CLASS,
        PER_CELL_ACTIONS,
        SHIP_FRAC_BINS,
        encode_grid_state,
    )


def _decode_action_class(class_id: int, home_capacity: int) -> tuple[float, int] | None:
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


def _home_capacity(ships: int, max_fraction: float = 0.85, reserve: int = 5) -> int:
    return max(0, min(int(ships * max_fraction), ships - reserve))


def make_ppo_agent(
    model_path: str | Path,
    device: str = "cpu",
    deterministic: bool = True,
    sun_safety_margin_rad: float = 0.035,
):
    """Load MaskablePPO checkpoint and return kaggle_environments compatible agent."""
    from sb3_contrib import MaskablePPO

    model = MaskablePPO.load(str(model_path), device=device)
    model.policy.eval()

    def agent(observation, configuration=None):
        try:
            enc = encode_grid_state(observation)
            if not enc.my_cells:
                return []

            actions: list[list[float]] = []
            planets_dict = {int(p[0]): p for p in observation.get("planets", [])}
            player = int(observation.get("player", 0) or 0)

            # For each my_planet, query the policy with action_mask = single cell
            for pid, row, col in enc.my_cells:
                planet = planets_dict.get(pid)
                if planet is None or int(planet[1]) != player:
                    continue
                home_ships = int(planet[5])
                home_cap = _home_capacity(home_ships)
                if home_cap <= 0:
                    continue

                # Build observation with mask = only this cell
                cell_mask = np.zeros((GRID_SIZE * GRID_SIZE,), dtype=np.float32)
                cell_mask[row * GRID_SIZE + col] = 1.0
                obs = {
                    "spatial": enc.spatial.astype(np.float32),
                    "globals": enc.globals_.astype(np.float32),
                    "action_mask": cell_mask,
                }

                # Action mask for sb3-contrib: per-cell × per-action
                action_mask_full = np.repeat(cell_mask, PER_CELL_ACTIONS).astype(bool)
                # Always allow no_op (class 0) for current cell as fallback
                action_mask_full[(row * GRID_SIZE + col) * PER_CELL_ACTIONS] = True

                with torch.no_grad():
                    action, _ = model.predict(
                        obs, deterministic=deterministic, action_masks=action_mask_full
                    )

                cell_id, action_class = divmod(int(action), PER_CELL_ACTIONS)
                if cell_id != row * GRID_SIZE + col:
                    continue
                decoded = _decode_action_class(action_class, home_cap)
                if decoded is None:
                    continue
                angle, ships = decoded
                if ships <= 0 or ships > home_cap:
                    continue
                home_x, home_y = float(planet[2]), float(planet[3])
                safe = physics.safe_angle_around(
                    home_x, home_y, angle, margin=sun_safety_margin_rad
                )
                actions.append([float(pid), float(safe), int(ships)])
            return actions
        except Exception:
            return []

    return agent
