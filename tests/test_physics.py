"""orbit_wars.physics の境界値 + 数式整合性 test."""

from __future__ import annotations

import math

import pytest

from orbit_wars import physics

# ============================================================================
# fleet_speed
# ============================================================================


class TestFleetSpeed:
    def test_one_ship_speed_one(self):
        assert physics.fleet_speed(1) == 1.0

    def test_zero_ship_handled(self):
        assert physics.fleet_speed(0) == 1.0

    def test_thousand_ships_max_speed(self):
        assert abs(physics.fleet_speed(1000) - 6.0) < 1e-9

    def test_clamped_above_thousand(self):
        # > 1000 でも max_speed=6.0 で clamp
        assert physics.fleet_speed(2000) == pytest.approx(6.0, abs=1e-9)

    def test_monotonic(self):
        speeds = [physics.fleet_speed(n) for n in [1, 10, 100, 500, 1000]]
        assert speeds == sorted(speeds)

    def test_convex_split_advantage(self):
        """凸性: N 隻 1 艦隊は N/2 隻 × 2 艦隊より速い (or 等しい)。"""
        for n in [10, 50, 100, 500]:
            v_single = physics.fleet_speed(n)
            v_half = physics.fleet_speed(max(1, n // 2))
            assert v_single >= v_half

    def test_custom_max_speed(self):
        # max_speed=10.0 を与えれば clamp 値も 10.0
        assert abs(physics.fleet_speed(1000, max_speed=10.0) - 10.0) < 1e-9


# ============================================================================
# orbital prediction
# ============================================================================


class TestOrbitalPrediction:
    def test_static_when_zero_angvel(self):
        x, y = physics.predict_orbital_position(70, 50, 0.0, 100)
        assert abs(x - 70) < 1e-9
        assert abs(y - 50) < 1e-9

    def test_at_center_returns_center(self):
        # 中心点は orbital radius 0、回転しても中心
        x, y = physics.predict_orbital_position(50, 50, 0.04, 50)
        assert abs(x - 50) < 1e-9
        assert abs(y - 50) < 1e-9

    def test_full_revolution_returns_near_initial(self):
        ang_vel = 0.04
        # 整数 t = round(2*pi/ang_vel) でほぼ初期位置
        t = round(2 * math.pi / ang_vel)
        x_init, y_init = 70, 50
        x, y = physics.predict_orbital_position(x_init, y_init, ang_vel, t)
        assert abs(x - x_init) < 1.0
        assert abs(y - y_init) < 1.0

    def test_quarter_revolution(self):
        ang_vel = 0.04
        t = round(0.5 * math.pi / ang_vel)
        x_init, y_init = 70, 50  # angle 0 from (50,50)
        x, y = physics.predict_orbital_position(x_init, y_init, ang_vel, t)
        # 90° 回転 = (50, 70) 付近
        assert abs(x - 50) < 1.0
        assert abs(y - 70) < 1.0


class TestIsOrbiting:
    def test_inner_planet_orbits(self):
        # (70, 50): orbital radius 20、planet radius 1.5 → 21.5 < 50
        assert physics.is_orbiting(70, 50, 1.5) is True

    def test_outer_planet_static(self):
        # (95, 50): orbital radius 45、planet radius 2.5 → 47.5 < 50 (実は orbiting)
        # 上限ギリギリ: (99, 50): orbital radius 49、+ planet radius 2 → 51 > 50 (static)
        assert physics.is_orbiting(99, 50, 2.0) is False

    def test_at_limit_static(self):
        # orbital_radius + planet_radius == 50 ぴったりは static (strict < で判定)
        # (97, 50): orbital_radius=47, planet_radius=3 → 50 == limit → static
        assert physics.is_orbiting(97, 50, 3.0) is False
        # (96, 50): orbital_radius=46, + 3 = 49 < 50 → orbiting
        assert physics.is_orbiting(96, 50, 3.0) is True


# ============================================================================
# forbidden cone (sun crossing prevention)
# ============================================================================


class TestForbiddenCone:
    def test_cone_from_corner(self):
        cone = physics.forbidden_cone(75, 25)
        assert cone is not None
        low, high = cone
        center = 0.5 * (low + high)
        half = 0.5 * (high - low)
        # Center 角度: (75,25) → (50,50) = atan2(25, -25) = 3π/4
        expected_center = math.atan2(50 - 25, 50 - 75)
        assert abs(center - expected_center) < 1e-9
        # Half angle: asin(10 / sqrt(25^2 + 25^2)) = asin(10/35.355) ≈ 16.43°
        expected_half = math.asin(10 / math.hypot(25, 25))
        assert abs(half - expected_half) < 1e-9

    def test_inside_sun_returns_none(self):
        assert physics.forbidden_cone(50, 50) is None
        # Within sun radius (= 10)
        assert physics.forbidden_cone(55, 50) is None

    def test_far_from_sun_narrow_cone(self):
        # 遠くから見ると cone は narrow
        cone = physics.forbidden_cone(0, 0)
        assert cone is not None
        low, high = cone
        half = 0.5 * (high - low)
        # asin(10 / sqrt(50^2 + 50^2)) = asin(10/70.71) ≈ 8.13°
        expected_half = math.asin(10 / math.hypot(50, 50))
        assert abs(half - expected_half) < 1e-9


class TestIsSafeAngle:
    def test_directly_at_sun_unsafe(self):
        # (75, 25) → 太陽方向に発射
        sun_dir = math.atan2(50 - 25, 50 - 75)
        assert physics.is_safe_angle(75, 25, sun_dir) is False

    def test_perpendicular_safe(self):
        sun_dir = math.atan2(50 - 25, 50 - 75)
        assert physics.is_safe_angle(75, 25, sun_dir + math.pi / 2) is True

    def test_opposite_direction_safe(self):
        sun_dir = math.atan2(50 - 25, 50 - 75)
        assert physics.is_safe_angle(75, 25, sun_dir + math.pi) is True


class TestSafeAngleAround:
    def test_safe_angle_passthrough(self):
        sun_dir = math.atan2(50 - 25, 50 - 75)
        safe = sun_dir + math.pi / 2
        assert abs(physics.safe_angle_around(75, 25, safe) - safe) < 1e-9

    def test_unsafe_deflected(self):
        # 太陽直撃方向 → 安全な角度に変換
        sun_dir = math.atan2(50 - 25, 50 - 75)
        new_angle = physics.safe_angle_around(75, 25, sun_dir, margin=math.radians(2.0))
        # 変換後は forbidden cone の外
        assert physics.is_safe_angle(75, 25, new_angle) is True


# ============================================================================
# lead-shot
# ============================================================================


class TestLeadAngleStatic:
    def test_target_on_x_axis(self):
        angle, t = physics.lead_angle_static(0, 0, 10, 0, 100)
        assert abs(angle) < 1e-9  # +x 方向
        v = physics.fleet_speed(100)
        assert abs(t - 10 / v) < 1e-9

    def test_target_on_y_axis(self):
        angle, _t = physics.lead_angle_static(0, 0, 0, 10, 100)
        assert abs(angle - math.pi / 2) < 1e-9


class TestLeadAngleOrbital:
    def test_zero_ang_vel_matches_static(self):
        # ang_vel=0 では orbital == static
        a_static, t_static = physics.lead_angle_static(0, 0, 80, 50, 100)
        # target at (80, 50) → orbital_radius from center (50,50) = 30, init_angle = 0
        result = physics.lead_angle_orbital(0, 0, 30, 0.0, 0.0, 100)
        assert result is not None
        a_orb, t_orb = result
        assert abs(a_static - a_orb) < 1e-2
        assert abs(t_static - t_orb) < 1.0

    def test_lead_correction_for_orbiting(self):
        # ang_vel > 0 では fire_angle が naive aim より lead する
        # (80, 50) を狙う場合、target が時計回りに動くなら angle は naive より + 方向
        cx, cy = 50.0, 50.0
        target_init_angle = math.atan2(50 - cy, 80 - cx)  # = 0
        result = physics.lead_angle_orbital(0, 0, 30.0, target_init_angle, 0.04, 100)
        assert result is not None
        fire_angle, t_arr = result
        # naive aim: atan2(50-0, 80-0) = atan2(50, 80) ≈ 32°
        naive = math.atan2(50, 80)
        # lead でズレる (符号は ang_vel と target 位置に依存)
        assert abs(fire_angle - naive) > math.radians(0.5)
        assert t_arr > 0


# ============================================================================
# ROI
# ============================================================================


class TestROI:
    def test_higher_production_higher_roi(self):
        r1 = physics.roi(1, 50, 20)
        r3 = physics.roi(3, 50, 20)
        assert r3 > r1

    def test_higher_cost_lower_roi(self):
        r_cheap = physics.roi(3, 30, 10)
        r_pricey = physics.roi(3, 100, 10)
        assert r_cheap > r_pricey

    def test_higher_travel_lower_roi(self):
        r_near = physics.roi(3, 30, 5)
        r_far = physics.roi(3, 30, 50)
        assert r_near > r_far

    def test_zero_cost_handled(self):
        # max(travel_time, 1.0) で ZeroDivisionError 回避
        assert physics.roi(3, 0, 0) == 3.0


# ============================================================================
# distance
# ============================================================================


class TestDistance:
    def test_origin_to_3_4(self):
        assert physics.distance((0, 0), (3, 4)) == pytest.approx(5.0)

    def test_same_point(self):
        assert physics.distance((10, 10), (10, 10)) == 0.0
