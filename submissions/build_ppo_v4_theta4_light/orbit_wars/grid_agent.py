"""Inference wrapper for GridSEResNet IL agent (Phase η v2).

Loads a trained GridSEResNet checkpoint and exposes a kaggle_environments
compatible `agent(observation, configuration)` callable.

Pipeline:
  1. encode_grid_state(observation) → spatial (14, 64, 64) + globals (9,)
  2. model.forward(spatial, globals) → logits (64, 64, 81)
  3. For each my_planet at (row, col):
       - extract logits[row, col] (= 81 vec)
       - mask cells without my_planet (= -inf)
       - argmax (or sample) → action class
       - decode → (angle, ships)
  4. Filter capacity-exceeding actions, apply sun-cone safety
  5. Return list[[from_id, angle, ships], ...]

Optional: 8-fold TTA at inference (= average logits over rotations/reflections)
"""

from __future__ import annotations

import math
from pathlib import Path

import torch

try:
    from . import physics
    from .grid_encoder import (
        ANGLE_BINS,
        NO_OP_CLASS,
        SHIP_FRAC_BINS,
        encode_grid_state,
    )
    from .grid_model import GridSEResNet
except (ImportError, KeyError):
    import physics  # type: ignore[no-redef]
    from grid_encoder import (  # type: ignore[no-redef]
        ANGLE_BINS,
        NO_OP_CLASS,
        SHIP_FRAC_BINS,
        encode_grid_state,
    )
    from grid_model import GridSEResNet  # type: ignore[no-redef]


def _decode_grid_action(class_id: int, home_capacity: int) -> tuple[float, int] | None:
    """class id → (angle, ships) or None for no_op."""
    if class_id == NO_OP_CLASS:
        return None
    cls = class_id - 1
    angle_bin = cls // SHIP_FRAC_BINS
    frac_bin = cls % SHIP_FRAC_BINS
    angle_center = (angle_bin + 0.5) * (2 * math.pi / ANGLE_BINS)
    if angle_center > math.pi:
        angle_center -= 2 * math.pi
    frac_to_ships = {0: 5, 1: 20, 2: 60, 3: 200, 4: 500}
    ships = min(frac_to_ships.get(frac_bin, 5), max(home_capacity, 1))
    return angle_center, int(ships)


def _home_capacity(ships: int, max_fraction: float = 0.85, reserve: int = 5) -> int:
    return max(0, min(int(ships * max_fraction), ships - reserve))


def make_grid_agent(
    model_path: str | Path,
    device: str = "cpu",
    suppress_no_op: bool = False,
    sun_safety_margin_rad: float = 0.035,
    no_op_temperature: float = 1.0,
    fire_threshold: float = 0.0,
    min_ship_floor: int = 0,
):
    """Returns a kaggle_environments compatible agent function.

    Args:
        no_op_temperature: divide no_op logit by this (>1 = down-weight no_op,
            < 1 = up-weight). 1.0 = no change, 5.0 = strongly suppress no_op.
        fire_threshold: only fire if (1 - softmax(no_op_prob)) > threshold.
        min_ship_floor: minimum ships to actually launch (override decoded value).
    """
    model = GridSEResNet()
    ckpt = torch.load(model_path, map_location=device, weights_only=True)
    if isinstance(ckpt, dict) and "state_dict" in ckpt:
        model.load_state_dict(ckpt["state_dict"])
    else:
        model.load_state_dict(ckpt)
    model.eval()
    model.to(device)

    def agent(observation, configuration=None):
        try:
            enc = encode_grid_state(observation)
            if not enc.my_cells:
                return []

            spatial = torch.from_numpy(enc.spatial).unsqueeze(0).to(device)
            globals_ = torch.from_numpy(enc.globals_).unsqueeze(0).to(device)
            with torch.no_grad():
                logits, _value = model(spatial, globals_)  # (1, 64, 64, 81)
            logits = logits.squeeze(0)  # (64, 64, 81)

            actions: list[list[float]] = []
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

                cell_logits = logits[row, col].clone()
                # Down-weight no_op via temperature: divide its logit by temperature.
                # > 1.0 = make no_op less likely (= more aggressive firing).
                if no_op_temperature != 1.0:
                    cell_logits[NO_OP_CLASS] = cell_logits[NO_OP_CLASS] / no_op_temperature
                if suppress_no_op:
                    cell_logits[NO_OP_CLASS] = float("-inf")

                # Optional: fire only if confidence high enough
                if fire_threshold > 0.0:
                    probs = torch.softmax(cell_logits, dim=-1)
                    fire_prob = 1.0 - float(probs[NO_OP_CLASS])
                    if fire_prob < fire_threshold:
                        continue

                cls = int(cell_logits.argmax().item())
                decoded = _decode_grid_action(cls, home_cap)
                if decoded is None:
                    continue
                angle, ships = decoded
                if min_ship_floor > 0 and ships < min_ship_floor:
                    ships = min(min_ship_floor, home_cap)
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
