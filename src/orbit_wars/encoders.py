"""orbit-wars 用の state / action encoder (NN policy / BC dataset の前段)。

Design (Phase 0 minimum):
    - State: per-entity feature の flat tensor (CNN は後の改善)
        - per-planet: 10 dim × MAX_PLANETS = 300 dim
        - per-fleet: 7 dim × MAX_FLEETS = 210 dim
        - global: 4 dim
        - total: 514 dim
    - Action (per home): {no_op, fire(angle_bin × ship_fraction_bin)}
        - angle: ANGLE_BINS=16 (22.5° ずつ)
        - ship_fraction: SHIP_FRAC_BINS=5 (20/40/60/80/100% of capacity)
        - per-home: 1 + 16*5 = 81 classes
        - max homes: 30
    - 4-fold symmetry (orbit-wars の対称性): center (50,50) 周りの π/2 回転 + 反転 = 4
        - data augmentation で適用 (4× データ量)

このモジュールは pure numpy/torch で、game state (= GameState dataclass) と
action list を相互変換する。BC dataset / NN agent の両方が利用する。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# Constants (engine 仕様)
BOARD_SIZE = 100.0
SUN_X, SUN_Y = 50.0, 50.0
MAX_PLANETS = 32  # 28 typical + buffer
MAX_FLEETS = 64  # 多めに余裕
PLANET_FEAT_DIM = 10
FLEET_FEAT_DIM = 7
GLOBAL_FEAT_DIM = 4
STATE_DIM = MAX_PLANETS * PLANET_FEAT_DIM + MAX_FLEETS * FLEET_FEAT_DIM + GLOBAL_FEAT_DIM

# Action discretization
ANGLE_BINS = 16  # 22.5° ずつ
SHIP_FRAC_BINS = 5  # 20%, 40%, 60%, 80%, 100% of capacity
PER_HOME_ACTIONS = 1 + ANGLE_BINS * SHIP_FRAC_BINS  # = 81
NO_OP_CLASS = 0  # action class 0 = no fire


@dataclass
class StateEncoding:
    """numpy array container."""

    state_vec: np.ndarray  # (STATE_DIM,)
    my_planet_ids: list[int]  # この turn に launch 候補となる planet id (昇順)


def encode_state(observation: dict, player: int | None = None) -> StateEncoding:
    """observation dict を flat numpy vector に encode する。

    Args:
        observation: kaggle_environments の observation dict (planets, fleets, ...)
        player: 自陣営 player id (0 or 1)。`None` なら observation['player'] を使う。

    Returns:
        StateEncoding (state_vec + my_planet_ids).

    State レイアウト:
        [planet0 (10dim), planet1, ..., planet31,         # 320 dim
         fleet0 (7dim), fleet1, ..., fleet63,             # 448 dim
         global (4dim)]                                   # = 4 dim
        合計 STATE_DIM = 772 dim
    """
    if player is None:
        player = int(observation.get("player", 0) or 0)
    planets = observation.get("planets") or []
    fleets = observation.get("fleets") or []
    ang_vel = float(observation.get("angular_velocity", 0.0) or 0.0)
    step = int(observation.get("step", 0) or 0)

    # planet feature: [is_mine, is_enemy, is_neutral, is_comet, x_norm, y_norm, ships_log, production, dist_from_sun_norm, in_orbit?]
    comet_ids = set(observation.get("comet_planet_ids") or [])
    planet_feats = np.zeros((MAX_PLANETS, PLANET_FEAT_DIM), dtype=np.float32)
    my_planet_ids: list[int] = []
    for i, p in enumerate(planets):
        if i >= MAX_PLANETS:
            break
        # planet tuple = (id, owner, x, y, radius, ships, production)
        pid, owner, x, y, radius, ships, prod = (
            p[0],
            int(p[1]),
            float(p[2]),
            float(p[3]),
            float(p[4]),
            int(p[5]),
            int(p[6]),
        )
        is_mine = 1.0 if owner == player else 0.0
        is_enemy = 1.0 if owner != -1 and owner != player else 0.0
        is_neutral = 1.0 if owner == -1 else 0.0
        is_comet = 1.0 if pid in comet_ids else 0.0
        dist_sun = math.hypot(x - SUN_X, y - SUN_Y) / BOARD_SIZE  # ~ [0, 0.7]
        # in_orbit: planet が公転するか (= sun から < 50 - radius)
        in_orbit = 1.0 if dist_sun * BOARD_SIZE + radius < 50.0 else 0.0
        planet_feats[i] = [
            is_mine,
            is_enemy,
            is_neutral,
            is_comet,
            x / BOARD_SIZE,
            y / BOARD_SIZE,
            math.log1p(ships) / math.log(1000),  # ships log-normalized
            prod / 5.0,  # production [1,5] → [0.2, 1.0]
            dist_sun,
            in_orbit,
        ]
        if owner == player:
            my_planet_ids.append(int(pid))

    # fleet feature: [is_mine, is_enemy, x_norm, y_norm, angle_sin, angle_cos, ships_log]
    fleet_feats = np.zeros((MAX_FLEETS, FLEET_FEAT_DIM), dtype=np.float32)
    for i, f in enumerate(fleets):
        if i >= MAX_FLEETS:
            break
        # fleet tuple = (id, owner, x, y, angle, from_planet_id, ships)
        owner, x, y, angle, ships = int(f[1]), float(f[2]), float(f[3]), float(f[4]), int(f[6])
        is_mine = 1.0 if owner == player else 0.0
        is_enemy = 1.0 if owner != player else 0.0
        fleet_feats[i] = [
            is_mine,
            is_enemy,
            x / BOARD_SIZE,
            y / BOARD_SIZE,
            math.sin(angle),
            math.cos(angle),
            math.log1p(ships) / math.log(1000),
        ]

    # global feature: [step_norm, ang_vel, my_planet_count_norm, enemy_planet_count_norm]
    my_count = sum(1 for p in planets if int(p[1]) == player)
    enemy_count = sum(1 for p in planets if int(p[1]) != player and int(p[1]) != -1)
    global_feats = np.array(
        [
            step / 500.0,
            ang_vel,
            my_count / 30.0,
            enemy_count / 30.0,
        ],
        dtype=np.float32,
    )

    state_vec = np.concatenate([planet_feats.flatten(), fleet_feats.flatten(), global_feats])
    return StateEncoding(state_vec=state_vec, my_planet_ids=sorted(my_planet_ids))


def encode_action(actions: list, my_planet_ids: list[int]) -> np.ndarray:
    """observation の action list を per-home class label に encode する。

    Args:
        actions: `[[from_id, angle_rad, ships], ...]` の list (replay の action 列)
        my_planet_ids: encode_state が返した sorted my_planet_ids

    Returns:
        labels (MAX_PLANETS,) int32 array. 各要素は class id ∈ [0, PER_HOME_ACTIONS).
        index は `my_planet_ids` の順序、その他は 0 (no_op) で padding。
        各 home が 1 turn に複数 launch した場合は **最初の launch のみ** 採用。

    Class encoding (action class id):
        0                  → no_op
        1 + a * SHIP_FRAC_BINS + s → fire at angle_bin=a, ship_frac_bin=s
        ただし a ∈ [0, ANGLE_BINS), s ∈ [0, SHIP_FRAC_BINS)
    """
    labels = np.zeros(MAX_PLANETS, dtype=np.int32)
    seen_planets: set[int] = set()
    pid_to_idx = {pid: i for i, pid in enumerate(my_planet_ids)}

    for a in actions:
        if not isinstance(a, list) or len(a) < 3:
            continue
        from_id = int(a[0])
        angle = float(a[1])
        ships = int(a[2])
        if from_id in seen_planets:
            continue  # 同 home の 2 回目以降は skip (= max 1/home in this encoder)
        if from_id not in pid_to_idx:
            continue  # my_planet ではない (= バグ or replay quirk)
        seen_planets.add(from_id)

        # angle を 0-2π に正規化 → bin に
        angle_norm = (angle + 2 * math.pi) % (2 * math.pi)
        angle_bin = min(int(angle_norm / (2 * math.pi / ANGLE_BINS)), ANGLE_BINS - 1)

        # ships fraction を bin に (ship 数の正確な capacity 比は計算困難なので、
        # log scale で近似的に bin)
        # 簡易: ships ∈ {1-9, 10-29, 30-99, 100-299, 300+} を 0-4 にマップ
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

        cls = 1 + angle_bin * SHIP_FRAC_BINS + frac_bin
        labels[pid_to_idx[from_id]] = cls

    return labels


def decode_action(
    class_id: int,
    home_capacity: int,
) -> tuple[float, int] | None:
    """class id を (angle_radians, ships) に decode する。NN inference 用。

    Returns:
        (angle, ships) or None (= no_op)
    """
    if class_id == NO_OP_CLASS:
        return None
    cls = class_id - 1
    angle_bin = cls // SHIP_FRAC_BINS
    frac_bin = cls % SHIP_FRAC_BINS

    angle_center = (angle_bin + 0.5) * (2 * math.pi / ANGLE_BINS)
    if angle_center > math.pi:
        angle_center -= 2 * math.pi  # [-π, π] に正規化

    # ship 数 bin → 中央値 (encoder の bin と一致)
    frac_to_ships = {0: 5, 1: 20, 2: 60, 3: 200, 4: 500}
    ships = frac_to_ships.get(frac_bin, 5)
    # capacity を超えないように clamp
    ships = min(ships, max(home_capacity, 1))

    return angle_center, int(ships)


def mirror_state(state_vec: np.ndarray, axis: str = "x") -> np.ndarray:
    """4-fold symmetry の data augmentation 用 mirror。

    orbit-wars の盤面は (50,50) 中心の **π/2 回転対称ではない** が、
    `(75,25)/(25,75)` の home 配置は **対角線 mirror** で player 0/1 を入替できる。
    本格的 augmentation は周回方向の調整が必要なので Phase 0.4 で実装。
    現時点は plumbing のみ (raise NotImplementedError).

    Returns:
        Augmented state vector with the same shape.
    """
    raise NotImplementedError("symmetry augmentation will be added in Phase 0.4")
