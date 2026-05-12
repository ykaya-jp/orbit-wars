"""64×64 multi-channel grid state encoder for SE-ResNet (Phase η v2).

Lux S3 winner Frog Parade uses a 24×24 grid + SE-ResNet for orbit-wars-like
game state. We adapt to orbit-wars (100×100 board) with a 64×64 grid where
each cell aggregates planets/fleets within its bin.

Channels (14 total):
    0: planet_self_ships   (log-normalized, 1.0 = 1000 ships)
    1: planet_enemy_ships
    2: planet_neutral_ships
    3: planet_production   (= prod / 5)
    4: planet_orbiting     (binary, = is_orbiting)
    5: planet_comet        (binary)
    6: fleet_self_ships    (log-normalized)
    7: fleet_enemy_ships
    8: fleet_self_dx       (= cos(angle), in [-1, 1])
    9: fleet_self_dy       (= sin(angle))
    10: fleet_enemy_dx
    11: fleet_enemy_dy
    12: sun_mask           (gaussian centered at (50,50), constant per game)
    13: home_distance_self (radial from center, constant per game)

Spatial tensor shape: (14, 64, 64).

Global features (separate from grid, fed via late-fusion MLP):
    [step / 500, angular_velocity, my_ships_total / 5000,
     enemy_ships_total / 5000, my_planet_count / 30, enemy_planet_count / 30,
     phase (early/mid/late one-hot)]

Action head (per cell — spatial output):
    Each grid cell contains at most one of MY planets. The policy outputs
    a logits map (64, 64, K) where K = ANGLE_BINS * SHIP_FRAC_BINS + 1 (= 81).
    At inference we mask cells without my_planet → set logits to -inf,
    then softmax-sample the action for each my_planet's cell.

4-fold symmetry augmentation:
    Rotate state grid by 90°/180°/270° + reflect along x/y axes (= 4 + 4 = 8)
    During BC training, each batch uses random one of 8 augmentations.
    At inference, average logits over all 8 (= TTA).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

GRID_SIZE = 64
N_CHANNELS = 14
GLOBAL_FEAT_DIM = 9
ANGLE_BINS = 16
SHIP_FRAC_BINS = 5
PER_CELL_ACTIONS = 1 + ANGLE_BINS * SHIP_FRAC_BINS  # = 81
NO_OP_CLASS = 0
BOARD_SIZE = 100.0
SUN_X = 50.0
SUN_Y = 50.0


@dataclass
class GridEncoding:
    spatial: np.ndarray  # (N_CHANNELS, GRID_SIZE, GRID_SIZE)
    globals_: np.ndarray  # (GLOBAL_FEAT_DIM,)
    my_cells: list[tuple[int, int, int]]  # [(planet_id, row, col), ...]


def _board_to_cell(x: float, y: float) -> tuple[int, int]:
    """Board coord (0-100) → grid cell (row, col)."""
    col = min(int(x * GRID_SIZE / BOARD_SIZE), GRID_SIZE - 1)
    row = min(int(y * GRID_SIZE / BOARD_SIZE), GRID_SIZE - 1)
    return row, col


def _build_sun_mask() -> np.ndarray:
    """Gaussian mask centered at (50, 50) with sigma 5 (= sun radius)."""
    rows = np.arange(GRID_SIZE)[:, None]
    cols = np.arange(GRID_SIZE)[None, :]
    cx = SUN_X * GRID_SIZE / BOARD_SIZE
    cy = SUN_Y * GRID_SIZE / BOARD_SIZE
    d2 = (rows - cy) ** 2 + (cols - cx) ** 2
    return np.exp(-d2 / (2 * 5.0**2)).astype(np.float32)


def _build_home_distance() -> np.ndarray:
    """Radial distance from board center, normalized to [0, 1]."""
    rows = np.arange(GRID_SIZE)[:, None]
    cols = np.arange(GRID_SIZE)[None, :]
    cx = SUN_X * GRID_SIZE / BOARD_SIZE
    cy = SUN_Y * GRID_SIZE / BOARD_SIZE
    d = np.sqrt((rows - cy) ** 2 + (cols - cx) ** 2) / (GRID_SIZE / 2)
    return d.astype(np.float32)


_SUN_MASK = _build_sun_mask()
_HOME_DIST = _build_home_distance()


def encode_grid_state(observation: dict, player: int | None = None) -> GridEncoding:
    """observation dict → 14×64×64 grid + 9-dim global feature vector."""
    if player is None:
        player = int(observation.get("player", 0) or 0)

    planets = observation.get("planets") or []
    fleets = observation.get("fleets") or []
    comet_ids = set(observation.get("comet_planet_ids") or [])
    ang_vel = float(observation.get("angular_velocity", 0.0) or 0.0)
    step = int(observation.get("step", 0) or 0)

    spatial = np.zeros((N_CHANNELS, GRID_SIZE, GRID_SIZE), dtype=np.float32)
    spatial[12] = _SUN_MASK
    spatial[13] = _HOME_DIST

    my_cells: list[tuple[int, int, int]] = []

    # planet tuple: (id, owner, x, y, radius, ships, production)
    for p in planets:
        pid = int(p[0])
        owner = int(p[1])
        x = float(p[2])
        y = float(p[3])
        radius = float(p[4])
        ships = int(p[5])
        prod = int(p[6])
        row, col = _board_to_cell(x, y)
        ship_norm = math.log1p(ships) / math.log(1000.0)
        is_orbit = 1.0 if math.hypot(x - SUN_X, y - SUN_Y) + radius < 50.0 else 0.0
        is_comet = 1.0 if pid in comet_ids else 0.0
        if owner == player:
            spatial[0, row, col] = ship_norm
            my_cells.append((pid, row, col))
        elif owner == -1:
            spatial[2, row, col] = ship_norm
        else:
            spatial[1, row, col] = ship_norm
        spatial[3, row, col] = prod / 5.0
        spatial[4, row, col] = is_orbit
        spatial[5, row, col] = is_comet

    # fleet tuple: (id, owner, x, y, angle, from_planet_id, ships)
    for f in fleets:
        owner = int(f[1])
        x = float(f[2])
        y = float(f[3])
        angle = float(f[4])
        ships = int(f[6])
        row, col = _board_to_cell(x, y)
        ship_norm = math.log1p(ships) / math.log(1000.0)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        if owner == player:
            spatial[6, row, col] += ship_norm
            spatial[8, row, col] = cos_a
            spatial[9, row, col] = sin_a
        else:
            spatial[7, row, col] += ship_norm
            spatial[10, row, col] = cos_a
            spatial[11, row, col] = sin_a

    # global features
    my_ships = sum(int(p[5]) for p in planets if int(p[1]) == player)
    enemy_ships = sum(int(p[5]) for p in planets if int(p[1]) >= 0 and int(p[1]) != player)
    my_count = sum(1 for p in planets if int(p[1]) == player)
    enemy_count = sum(1 for p in planets if int(p[1]) >= 0 and int(p[1]) != player)
    phase_early = 1.0 if step < 100 else 0.0
    phase_mid = 1.0 if 100 <= step < 350 else 0.0
    phase_late = 1.0 if step >= 350 else 0.0

    globals_ = np.array(
        [
            step / 500.0,
            ang_vel,
            my_ships / 5000.0,
            enemy_ships / 5000.0,
            my_count / 30.0,
            enemy_count / 30.0,
            phase_early,
            phase_mid,
            phase_late,
        ],
        dtype=np.float32,
    )

    return GridEncoding(spatial=spatial, globals_=globals_, my_cells=my_cells)


def encode_grid_action(actions: list, my_cells: list[tuple[int, int, int]]) -> np.ndarray:
    """observation の action list → grid-shaped action label.

    Returns:
        labels: (GRID_SIZE, GRID_SIZE) int32. Each cell containing a my_planet
        gets:
            0 = no_op
            1 + a * SHIP_FRAC_BINS + s = fire(angle_bin a, ship_frac_bin s)
        Cells without my_planet are -1 (= ignore in loss).
    """
    labels = np.full((GRID_SIZE, GRID_SIZE), -1, dtype=np.int32)
    pid_to_cell = {pid: (r, c) for pid, r, c in my_cells}

    # Mark all my_cells as no_op by default
    for _pid, r, c in my_cells:
        labels[r, c] = NO_OP_CLASS

    for a in actions:
        if not isinstance(a, list) or len(a) < 3:
            continue
        from_id = int(a[0])
        if from_id not in pid_to_cell:
            continue
        r, c = pid_to_cell[from_id]
        angle = float(a[1])
        ships = int(a[2])
        angle_norm = (angle + 2 * math.pi) % (2 * math.pi)
        angle_bin = min(int(angle_norm / (2 * math.pi / ANGLE_BINS)), ANGLE_BINS - 1)
        if ships < 10:
            frac_bin = 0
        elif ships < 30:
            frac_bin = 1
        elif ships < 100:
            frac_bin = 2
        elif ships < 300:
            frac_bin = 3
        else:
            frac_bin = 4
        labels[r, c] = 1 + angle_bin * SHIP_FRAC_BINS + frac_bin

    return labels


def augment_grid(
    spatial: np.ndarray, labels: np.ndarray, mode: int
) -> tuple[np.ndarray, np.ndarray]:
    """4-fold rotation × 2 reflections = 8 symmetry augmentations.

    Args:
        spatial: (C, H, W)
        labels:  (H, W) int (= NO_OP or fire-class with angle_bin/frac_bin)
        mode: 0-7 (0=identity, 1-3=rotate 90/180/270, 4-7=reflect+rotate)

    Returns:
        (augmented_spatial, augmented_labels) both rotated; angle_bin in
        labels is *adjusted* to match the rotation.
    """
    aug_spatial = spatial.copy()
    aug_labels = labels.copy()

    # rotation count k: 0..3
    k = mode % 4
    flip = mode >= 4

    if flip:
        aug_spatial = aug_spatial[:, :, ::-1].copy()
        aug_labels = aug_labels[:, ::-1].copy()
    aug_spatial = np.rot90(aug_spatial, k=k, axes=(1, 2)).copy()
    aug_labels = np.rot90(aug_labels, k=k).copy()

    # angle_bin adjustment in labels: rotate by k*90° + flip
    if k > 0 or flip:
        # extract angle_bin / frac_bin from labels
        valid = aug_labels >= 1
        cls = aug_labels[valid] - 1
        ang_bin = cls // SHIP_FRAC_BINS
        frac_bin = cls % SHIP_FRAC_BINS
        # adjust angle: rotation + flip
        ang_rad = ang_bin * (2 * math.pi / ANGLE_BINS)
        ang_rad = ang_rad + k * math.pi / 2  # rotation
        if flip:
            ang_rad = math.pi - ang_rad  # reflect around y-axis (x → -x)
        ang_rad = ang_rad % (2 * math.pi)
        new_ang_bin = (ang_rad / (2 * math.pi / ANGLE_BINS)).astype(np.int32) % ANGLE_BINS
        aug_labels[valid] = 1 + new_ang_bin * SHIP_FRAC_BINS + frac_bin

    # Adjust fleet direction channels (8/9 self, 10/11 enemy)
    # Rotation: (dx, dy) → (cos*dx - sin*dy, sin*dx + cos*dy)
    if k > 0 or flip:
        for ch in (8, 10):
            dx_ch = aug_spatial[ch].copy()
            dy_ch = aug_spatial[ch + 1].copy()
            if flip:
                dx_ch = -dx_ch
            theta = k * math.pi / 2
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            new_dx = cos_t * dx_ch - sin_t * dy_ch
            new_dy = sin_t * dx_ch + cos_t * dy_ch
            aug_spatial[ch] = new_dx
            aug_spatial[ch + 1] = new_dy

    return aug_spatial, aug_labels
