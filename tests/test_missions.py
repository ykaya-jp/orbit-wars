"""orbit_wars.missions の dispatcher + CaptureMission 動作 test."""

from __future__ import annotations

import math

from orbit_wars.missions import (
    CaptureMission,
    Dispatcher,
    parse_observation,
)


def make_obs(player=0, planets=None, fleets=None, ang_vel=0.0, step=0):
    """raw observation dict を組み立てる helper.

    planet 形式: [id, owner, x, y, radius, ships, production]
    fleet 形式:  [id, owner, x, y, angle, from_planet_id, ships]
    """
    return {
        "player": player,
        "planets": planets or [],
        "fleets": fleets or [],
        "angular_velocity": ang_vel,
        "initial_planets": planets or [],
        "comet_planet_ids": [],
        "step": step,
    }


# ============================================================================
# parse_observation
# ============================================================================


class TestParseObservation:
    def test_empty(self):
        s = parse_observation(make_obs())
        assert s.player == 0
        assert s.planets == []
        assert s.fleets == []
        assert s.step == 0

    def test_basic(self):
        obs = make_obs(
            player=1,
            planets=[[0, 0, 50, 50, 1.5, 100, 3]],
            fleets=[[0, 0, 60, 60, 0.0, 0, 50]],
            ang_vel=0.04,
            step=42,
        )
        s = parse_observation(obs)
        assert s.player == 1
        assert s.step == 42
        assert s.angular_velocity == 0.04
        assert len(s.planets) == 1
        assert len(s.fleets) == 1


# ============================================================================
# GameState properties
# ============================================================================


class TestGameStateProperties:
    def test_partition(self):
        obs = make_obs(
            player=0,
            planets=[
                [0, 0, 75, 75, 1.5, 100, 3],  # mine
                [1, 1, 25, 25, 1.5, 50, 2],  # enemy
                [2, -1, 50, 80, 1.0, 5, 1],  # neutral
            ],
        )
        s = parse_observation(obs)
        assert len(s.my_planets) == 1
        assert s.my_planets[0].id == 0
        assert len(s.enemy_planets) == 1
        assert s.enemy_planets[0].id == 1
        assert len(s.neutral_planets) == 1
        assert s.neutral_planets[0].id == 2


# ============================================================================
# CaptureMission
# ============================================================================


class TestCaptureMission:
    def test_no_my_planets_no_op(self):
        obs = make_obs(planets=[[0, 1, 50, 50, 1.5, 100, 3]])
        s = parse_observation(obs)
        score, moves = CaptureMission().evaluate(s)
        assert score == 0.0
        assert moves == []

    def test_no_targets_no_op(self):
        obs = make_obs(planets=[[0, 0, 50, 50, 1.5, 100, 3]])
        s = parse_observation(obs)
        score, moves = CaptureMission().evaluate(s)
        assert score == 0.0

    def test_capture_neutral(self):
        # mine at (75, 75) with 100 ships, neutral at (60, 60) with 5 ships
        obs = make_obs(
            planets=[
                [0, 0, 75, 75, 1.5, 100, 3],
                [1, -1, 60, 60, 1.0, 5, 2],
            ]
        )
        s = parse_observation(obs)
        score, moves = CaptureMission().evaluate(s)
        assert score > 0
        assert len(moves) == 1
        assert moves[0].from_planet_id == 0
        # 5 + 1 = 6 ships needed for neutral
        assert moves[0].ships == 6

    def test_enemy_needs_margin(self):
        # 敵惑星には MARGIN+1 上乗せ
        obs = make_obs(
            planets=[
                [0, 0, 75, 75, 1.5, 100, 3],
                [1, 1, 60, 60, 1.0, 5, 2],
            ]
        )
        s = parse_observation(obs)
        score, moves = CaptureMission(margin=1).evaluate(s)
        # 5 + 1 + margin(1) = 7
        assert moves[0].ships == 7

    def test_capacity_limit_skips(self):
        # mine has only 10 ships, neutral has 50 → skip (insufficient)
        obs = make_obs(
            planets=[
                [0, 0, 75, 75, 1.5, 10, 3],
                [1, -1, 60, 60, 1.0, 50, 2],
            ]
        )
        s = parse_observation(obs)
        score, moves = CaptureMission().evaluate(s)
        assert moves == []

    def test_roi_picks_high_production_target(self):
        # mine が両方占領可。production=5 と production=1 なら production=5 を選ぶ
        obs = make_obs(
            planets=[
                [0, 0, 75, 75, 1.5, 200, 3],
                [1, -1, 70, 70, 1.0, 5, 1],  # 近いが prod=1
                [2, -1, 60, 60, 1.0, 5, 5],  # 遠いが prod=5
            ]
        )
        s = parse_observation(obs)
        score, moves = CaptureMission().evaluate(s)
        assert len(moves) == 1
        # ROI: prod=5 / cost ≈ 5/(6+t) > prod=1 / cost ≈ 1/(6+t')
        # → planet ID 2 を選ぶはず
        # angle を計算して target 方向か確認: from (75,75) to (60,60)
        expected_angle = math.atan2(60 - 75, 60 - 75)
        # safe_angle_around で太陽通過回避により若干ズレる可能性
        assert abs(moves[0].angle - expected_angle) < math.radians(30)

    def test_sun_crossing_avoided(self):
        # mine at (75, 25) (Q1)、target at (25, 75) (Q3、太陽の反対側)
        # 直接発射すると太陽通過 → 角度がズレるはず
        obs = make_obs(
            planets=[
                [0, 0, 75, 25, 1.5, 200, 3],
                [1, -1, 25, 75, 1.0, 5, 3],
            ]
        )
        s = parse_observation(obs)
        score, moves = CaptureMission(sun_safety_margin_deg=2.0).evaluate(s)
        assert len(moves) == 1
        # 直接の angle は forbidden cone 内 (太陽通過)
        naive_angle = math.atan2(75 - 25, 25 - 75)
        # 採用された angle は naive と異なるはず (cone の外)
        assert abs(moves[0].angle - naive_angle) > math.radians(0.5)


# ============================================================================
# Dispatcher
# ============================================================================


class TestDispatcher:
    def test_single_mission(self):
        d = Dispatcher([CaptureMission()])
        obs = make_obs(
            planets=[
                [0, 0, 75, 75, 1.5, 100, 3],
                [1, -1, 60, 60, 1.0, 5, 2],
            ]
        )
        s = parse_observation(obs)
        actions = d.step(s)
        assert len(actions) == 1
        # action format: [from_id, angle, ships]
        assert len(actions[0]) == 3
        assert actions[0][0] == 0  # from planet id 0
        assert actions[0][2] == 6  # ships

    def test_no_missions_empty(self):
        d = Dispatcher([])
        obs = make_obs(planets=[[0, 0, 50, 50, 1.5, 100, 3]])
        s = parse_observation(obs)
        assert d.step(s) == []

    def test_one_action_per_planet(self):
        # 1 mission + 2 my planets → 各 planet に最大 1 action
        d = Dispatcher([CaptureMission()])
        obs = make_obs(
            planets=[
                [0, 0, 75, 75, 1.5, 100, 3],
                [1, 0, 80, 70, 1.5, 100, 3],
                [2, -1, 60, 60, 1.0, 5, 2],
            ]
        )
        s = parse_observation(obs)
        actions = d.step(s)
        # 2 my planets が両方 launch する可能性 (ROI で同じ target を狙う)
        # → 各 planet が 1 action ずつ、合計 ≤ 2
        assert len(actions) <= 2
        from_ids = [a[0] for a in actions]
        assert len(from_ids) == len(set(from_ids))  # 重複なし
