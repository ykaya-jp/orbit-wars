"""orbit-wars 物理エンジンの数学関数群。

`docs/strategy/first-principles.dense.md` の数理解析を実装。
すべての公式は engine source (`.venv/.../orbit_wars/orbit_wars.py`) と一致を test で検証。

Functions:
    fleet_speed(ships, max_speed=6.0)
    predict_orbital_position(x0, y0, ang_vel, t, center=(50,50))
    is_orbiting(x0, y0, planet_radius, center, rotation_radius_limit=50)
    forbidden_cone(from_x, from_y, sun_xy=(50,50), sun_radius=10)
    is_safe_angle(from_x, from_y, fire_angle, sun_xy, sun_radius)
    safe_angle_around(from_x, from_y, desired_angle, ..., margin)
    lead_angle_static(from_x, from_y, target_x, target_y, ships, max_speed)
    lead_angle_orbital(from_x, from_y, orbital_radius, target_initial_angle,
                       angular_velocity, ships, ...)
    roi(production, capture_cost, travel_time)
"""

from __future__ import annotations

import math

# Engine constants (orbit_wars.py:17-25)
CENTER: tuple[float, float] = (50.0, 50.0)
SUN_RADIUS: float = 10.0
ROTATION_RADIUS_LIMIT: float = 50.0
DEFAULT_MAX_SPEED: float = 6.0
DEFAULT_COMET_SPEED: float = 4.0
BOARD_SIZE: float = 100.0


# ============================================================================
# Fleet speed (orbit_wars.py:577-578)
# ============================================================================


def fleet_speed(ships: int, max_speed: float = DEFAULT_MAX_SPEED) -> float:
    """艦隊速度。

    `speed = 1.0 + (max_speed - 1.0) * (log(ships) / log(1000))^1.5`、`max_speed` で clamp。
    凸性により、N 隻の単一艦隊は常に N/2 隻 × 2 艦隊より速い。

    Args:
        ships: 艦隊隻数 (>= 1)
        max_speed: コンペデフォルト 6.0

    Returns:
        単位/turn の移動速度
    """
    if ships <= 1:
        return 1.0
    s = 1.0 + (max_speed - 1.0) * (math.log(ships) / math.log(1000)) ** 1.5
    return min(s, max_speed)


# ============================================================================
# Orbital prediction (orbit_wars.py:541-546)
# ============================================================================


def predict_orbital_position(
    initial_x: float,
    initial_y: float,
    angular_velocity: float,
    t: int,
    center: tuple[float, float] = CENTER,
) -> tuple[float, float]:
    """orbiting 惑星の `t` turn 後の位置を予測。

    `angle_t = angle_0 + angular_velocity * t` を極座標で評価。
    """
    cx, cy = center
    dx = initial_x - cx
    dy = initial_y - cy
    r = math.hypot(dx, dy)
    if r < 1e-9:
        return (cx, cy)
    angle_0 = math.atan2(dy, dx)
    angle_t = angle_0 + angular_velocity * t
    return (cx + r * math.cos(angle_t), cy + r * math.sin(angle_t))


def is_orbiting(
    initial_x: float,
    initial_y: float,
    planet_radius: float,
    center: tuple[float, float] = CENTER,
    rotation_radius_limit: float = ROTATION_RADIUS_LIMIT,
) -> bool:
    """この惑星が公転するか (= `orbital_radius + planet_radius < limit`)。"""
    cx, cy = center
    orbital_radius = math.hypot(initial_x - cx, initial_y - cy)
    return orbital_radius + planet_radius < rotation_radius_limit


# ============================================================================
# Forbidden cone (= 発射すると太陽通過で全滅する角度範囲)
# ============================================================================


def forbidden_cone(
    from_x: float,
    from_y: float,
    sun_x: float = CENTER[0],
    sun_y: float = CENTER[1],
    sun_radius: float = SUN_RADIUS,
) -> tuple[float, float] | None:
    """`from_xy` から発射した直線が太陽半径内を通過する角度範囲。

    Returns:
        `(low_angle, high_angle)` を radians で。`from_xy` が太陽内なら `None`。

    幾何: 半角 = asin(sun_radius / dist_to_sun)、cone 中心 = 太陽方向。
    """
    dx = sun_x - from_x
    dy = sun_y - from_y
    d = math.hypot(dx, dy)
    if d <= sun_radius:
        return None  # 異常: from_xy が太陽内
    center_angle = math.atan2(dy, dx)
    half_angle = math.asin(sun_radius / d)
    return (center_angle - half_angle, center_angle + half_angle)


def _angular_diff(a: float, b: float) -> float:
    """`a - b` を `(-pi, pi]` に正規化した角度差。"""
    return math.atan2(math.sin(a - b), math.cos(a - b))


def is_safe_angle(
    from_x: float,
    from_y: float,
    fire_angle: float,
    sun_x: float = CENTER[0],
    sun_y: float = CENTER[1],
    sun_radius: float = SUN_RADIUS,
) -> bool:
    """指定発射角が太陽通過しないか。"""
    cone = forbidden_cone(from_x, from_y, sun_x, sun_y, sun_radius)
    if cone is None:
        return True  # 異常時は safe 扱い
    low, high = cone
    center = 0.5 * (low + high)
    half = 0.5 * (high - low)
    diff = abs(_angular_diff(fire_angle, center))
    return diff > half


def safe_angle_around(
    from_x: float,
    from_y: float,
    desired_angle: float,
    sun_x: float = CENTER[0],
    sun_y: float = CENTER[1],
    sun_radius: float = SUN_RADIUS,
    margin: float = math.radians(2.0),
) -> float:
    """`desired_angle` が forbidden cone 内なら、cone の最寄り edge + `margin` の方向を返す。

    安全な角度ならそのまま返す。`margin` は radians。
    """
    if is_safe_angle(from_x, from_y, desired_angle, sun_x, sun_y, sun_radius):
        return desired_angle
    cone = forbidden_cone(from_x, from_y, sun_x, sun_y, sun_radius)
    assert cone is not None  # is_safe_angle が False なら cone は存在
    low, high = cone
    d_low = abs(_angular_diff(desired_angle, low))
    d_high = abs(_angular_diff(desired_angle, high))
    # 最寄りの edge から margin だけ離す方向
    if d_low < d_high:
        return low - margin
    return high + margin


# ============================================================================
# Lead-shot (静止 / orbiting target への命中角度)
# ============================================================================


def lead_angle_static(
    from_x: float,
    from_y: float,
    target_x: float,
    target_y: float,
    ships: int,
    max_speed: float = DEFAULT_MAX_SPEED,
) -> tuple[float, float]:
    """静止 target への発射角と arrival turn 数。

    Returns:
        `(fire_angle_radians, t_arrival_turns)`
    """
    fire_angle = math.atan2(target_y - from_y, target_x - from_x)
    distance = math.hypot(target_x - from_x, target_y - from_y)
    v = fleet_speed(ships, max_speed)
    t_arr = distance / v if v > 0 else float("inf")
    return fire_angle, t_arr


def lead_angle_orbital(
    from_x: float,
    from_y: float,
    target_orbital_radius: float,
    target_initial_angle: float,
    angular_velocity: float,
    ships: int,
    center: tuple[float, float] = CENTER,
    max_speed: float = DEFAULT_MAX_SPEED,
    max_iter: int = 60,
    tol: float = 1e-3,
) -> tuple[float, float] | None:
    """orbiting target への lead-shot 発射角と arrival turn を bisection で解く。

    Equation: `v * t = distance(from, target_at_t)` を t について解く。
    `t \\in (0.5, 1000]` で sign change を探索。

    Args:
        target_orbital_radius: 公転半径 (= `hypot(tx - cx, ty - cy)`)
        target_initial_angle: 観測時の角度 (radians)。`atan2(ty - cy, tx - cx)`
        angular_velocity: 観測の `angular_velocity` フィールド

    Returns:
        `(fire_angle, t_arrival)` または解が見つからなければ `None`
    """
    cx, cy = center
    v = fleet_speed(ships, max_speed)
    if v <= 0:
        return None

    def residual(t: float) -> float:
        ang_t = target_initial_angle + angular_velocity * t
        tx = cx + target_orbital_radius * math.cos(ang_t)
        ty = cy + target_orbital_radius * math.sin(ang_t)
        d = math.hypot(tx - from_x, ty - from_y)
        return v * t - d  # 正なら fleet が target より先回りしすぎ

    t_lo, t_hi = 0.5, 1000.0
    r_lo = residual(t_lo)
    r_hi = residual(t_hi)
    if r_lo * r_hi > 0:
        return None  # bracket できない (target unreachable)

    for _ in range(max_iter):
        t_mid = 0.5 * (t_lo + t_hi)
        r_mid = residual(t_mid)
        if abs(r_mid) < tol:
            t_lo = t_mid
            break
        if r_mid * r_lo < 0:
            t_hi = t_mid
        else:
            t_lo = t_mid
            r_lo = r_mid

    t_arr = 0.5 * (t_lo + t_hi)
    ang_t = target_initial_angle + angular_velocity * t_arr
    target_x = cx + target_orbital_radius * math.cos(ang_t)
    target_y = cy + target_orbital_radius * math.sin(ang_t)
    fire_angle = math.atan2(target_y - from_y, target_x - from_x)
    return fire_angle, t_arr


# ============================================================================
# ROI (planet 攻撃の費用対効果)
# ============================================================================


def roi(production: int, capture_cost: int, travel_time: float) -> float:
    """惑星 ROI = `production / (capture_cost + travel_time)`。

    高 ROI = 効率的な攻撃対象。`production >= 3` は travel_time <= 33 turn で正の ROI。

    Args:
        production: 占領後の毎 turn ship 生産量 (1-5)
        capture_cost: 占領に必要な ship 数 (= `target.ships + 1` etc)
        travel_time: 到着 turn 数

    Returns:
        ROI スコア (大きいほど良い)
    """
    total_cost = capture_cost + max(travel_time, 1.0)
    if total_cost <= 0:
        return 0.0
    return production / total_cost


# ============================================================================
# Distance helpers
# ============================================================================


def distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """2 点間ユークリッド距離。"""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])
