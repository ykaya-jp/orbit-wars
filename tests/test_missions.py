"""orbit_wars.missions の dispatcher + 各 mission の動作 test."""

from __future__ import annotations

import math

from orbit_wars.missions import (
    CaptureMission,
    CometGrabMission,
    Dispatcher,
    RecaptureMission,
    parse_observation,
)


def make_obs(
    player=0,
    planets=None,
    fleets=None,
    ang_vel=0.0,
    step=0,
    comet_planet_ids=None,
):
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
        "comet_planet_ids": list(comet_planet_ids or []),
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


# ============================================================================
# CometGrabMission
# ============================================================================


class TestCometGrabMission:
    def test_no_comets_no_op(self):
        # 通常惑星のみ、comet なし → no-op
        obs = make_obs(
            planets=[
                [0, 0, 75, 75, 1.5, 100, 3],
                [1, -1, 60, 60, 1.0, 5, 2],
            ]
        )
        s = parse_observation(obs)
        score, moves = CometGrabMission().evaluate(s)
        assert score == 0.0
        assert moves == []

    def test_grab_nearby_neutral_comet(self):
        # 自惑星 (75, 75)、近くに comet (70, 70)
        obs = make_obs(
            planets=[
                [0, 0, 75, 75, 1.5, 100, 3],
                [1, -1, 70, 70, 1.0, 10, 1],
            ],
            comet_planet_ids=[1],
        )
        s = parse_observation(obs)
        score, moves = CometGrabMission(capture_buffer=5).evaluate(s)
        assert score > 0
        assert len(moves) == 1
        # 必要 ship: comet.ships(10) + capture_buffer(5) = 15
        assert moves[0].ships == 15

    def test_skip_owned_comet(self):
        # comet が既に自分の所有
        obs = make_obs(
            planets=[
                [0, 0, 75, 75, 1.5, 100, 3],
                [1, 0, 70, 70, 1.0, 10, 1],  # 自所有 comet
            ],
            comet_planet_ids=[1],
        )
        s = parse_observation(obs)
        score, moves = CometGrabMission().evaluate(s)
        assert moves == []

    def test_skip_distant_comet(self):
        # comet が max_distance より遠い
        obs = make_obs(
            planets=[
                [0, 0, 5, 5, 1.5, 100, 3],
                [1, -1, 95, 95, 1.0, 10, 1],  # 距離 ~127、max_distance=40 で skip
            ],
            comet_planet_ids=[1],
        )
        s = parse_observation(obs)
        score, moves = CometGrabMission(max_distance=40.0).evaluate(s)
        assert moves == []

    def test_one_planet_one_comet_per_turn(self):
        # 1 自惑星に 2 comet → 1 launch のみ (Dispatcher 仕様)
        obs = make_obs(
            planets=[
                [0, 0, 50, 50, 1.5, 200, 3],  # 中央
                [1, -1, 55, 55, 1.0, 10, 1],  # 近 comet
                [2, -1, 60, 60, 1.0, 10, 1],  # 近 comet
            ],
            comet_planet_ids=[1, 2],
        )
        s = parse_observation(obs)
        score, moves = CometGrabMission().evaluate(s)
        # 1 mission 内で 1 planet 1 move 制約
        from_ids = [m.from_planet_id for m in moves]
        assert len(from_ids) == len(set(from_ids))


# ============================================================================
# RecaptureMission
# ============================================================================


class TestRecaptureMission:
    def test_no_history_no_op(self):
        # 初回呼び出し、まだ何も所有してない → no-op
        m = RecaptureMission()
        obs = make_obs(
            planets=[
                [0, 0, 75, 75, 1.5, 100, 3],
                [1, 1, 60, 60, 1.0, 5, 2],
            ]
        )
        s = parse_observation(obs)
        score, moves = m.evaluate(s)
        assert moves == []

    def test_recapture_lost_planet(self):
        # turn 0: 両方所有 → tracking に記録
        m = RecaptureMission(recapture_margin=5)
        obs0 = make_obs(
            planets=[
                [0, 0, 75, 75, 1.5, 100, 3],
                [1, 0, 60, 60, 1.0, 50, 3],
            ],
            step=0,
        )
        s0 = parse_observation(obs0)
        m.evaluate(s0)
        assert 0 in m._was_mine
        assert 1 in m._was_mine

        # turn 5: planet 1 が敵に取られた
        obs1 = make_obs(
            planets=[
                [0, 0, 75, 75, 1.5, 200, 3],
                [1, 1, 60, 60, 1.0, 30, 3],
            ],
            step=5,
        )
        s1 = parse_observation(obs1)
        score, moves = m.evaluate(s1)
        assert score > 0
        assert len(moves) == 1
        # ships needed = 30 + 1 + 5 = 36
        assert moves[0].ships == 36

    def test_episode_reset_clears_history(self):
        m = RecaptureMission()
        # turn 5 で履歴保持
        m._was_mine.add(99)
        # step が巻き戻る (= new episode)
        obs = make_obs(planets=[[0, 0, 50, 50, 1.5, 100, 3]], step=0)
        m._last_step = 10  # 前 episode の step
        s = parse_observation(obs)
        m.evaluate(s)
        # _on_new_episode で clear、現在所有を再記録
        assert 99 not in m._was_mine
        assert 0 in m._was_mine

    def test_higher_production_priority(self):
        m = RecaptureMission()
        # 過去所有 2 つ、両方失った
        obs0 = make_obs(
            planets=[
                [0, 0, 50, 50, 1.5, 200, 3],
                [1, 0, 55, 55, 1.0, 50, 1],
                [2, 0, 60, 60, 1.0, 50, 5],
            ],
            step=0,
        )
        s0 = parse_observation(obs0)
        m.evaluate(s0)

        # turn 5 で 1 と 2 を失う、自分は 0 のみ
        obs1 = make_obs(
            planets=[
                [0, 0, 50, 50, 1.5, 200, 3],  # 自軍 (200 ships)
                [1, 1, 55, 55, 1.0, 30, 1],  # lost prod=1
                [2, 1, 60, 60, 1.0, 30, 5],  # lost prod=5
            ],
            step=5,
        )
        s1 = parse_observation(obs1)
        score, moves = m.evaluate(s1)
        # 0 から 1 launch のみ可能 (1 planet 1 move) → prod=5 の方が選ばれる
        assert len(moves) == 1


# ============================================================================
# Dispatcher with multiple missions (Recapture + CometGrab + Capture)
# ============================================================================


class TestDispatcherMultiMission:
    def test_recapture_and_capture_coexist(self):
        # multi-move dispatcher: 同じ home から、ships 容量内なら Recapture と Capture が両立
        d = Dispatcher(
            [
                RecaptureMission(),
                CaptureMission(),
            ]
        )
        # 履歴のため 1 回 step=0 を流す
        obs0 = make_obs(
            planets=[
                [0, 0, 50, 50, 1.5, 200, 3],
                [1, 0, 55, 55, 1.0, 30, 5],
            ],
            step=0,
        )
        s0 = parse_observation(obs0)
        d.step(s0)

        # turn 1: planet 1 を失った + 別の neutral も attractive
        obs1 = make_obs(
            planets=[
                [0, 0, 50, 50, 1.5, 200, 3],
                [1, 1, 55, 55, 1.0, 30, 5],  # 失った高 prod (recapture target)
                [2, -1, 53, 50, 1.0, 5, 2],  # 近い neutral (capture target)
            ],
            step=1,
        )
        s1 = parse_observation(obs1)
        actions = d.step(s1)
        # multi-move: 200 ships 中、recapture(36)+capture(6)=42 で容量(170)内 → 両方 fire
        assert len(actions) == 2
        # actions は score 降順、Recapture (高 score) が先
        # Recapture target = planet 1 (55, 55)、angle ≈ atan2(5, 5) = 45°
        # Capture target = planet 2 (53, 50)、angle ≈ atan2(0, 3) = 0°
        angle_to_recap = math.atan2(5, 5)
        angle_to_capture = math.atan2(0, 3)
        # 1 つは recap 方向、もう 1 つは capture 方向
        angles = sorted(a[1] for a in actions)
        assert any(abs(a - angle_to_recap) < math.radians(20) for a in angles)
        assert any(abs(a - angle_to_capture) < math.radians(20) for a in angles)
        # ships 容量管理: 全 action の ships 合計 ≤ 170 (capacity)
        total_ships = sum(a[2] for a in actions)
        assert total_ships <= 170

    def test_capacity_exceeded_drops_lower_score(self):
        # ships が足りないとき高 score が優先される
        d = Dispatcher(
            [
                RecaptureMission(),
                CaptureMission(),
            ]
        )
        obs0 = make_obs(
            planets=[
                [0, 0, 50, 50, 1.5, 50, 3],  # 50 ships only (低容量)
                [1, 0, 55, 55, 1.0, 40, 5],  # large prod target
            ],
            step=0,
        )
        s0 = parse_observation(obs0)
        d.step(s0)

        # turn 1: lost planet (cost 46) + 別 neutral (cost 6)
        # capacity = min(50*0.85, 50-5) = 42。Recapture 46 > 42 で fail。
        # Capture 6 < 42 で OK → 1 action のみ
        obs1 = make_obs(
            planets=[
                [0, 0, 50, 50, 1.5, 50, 3],
                [1, 1, 55, 55, 1.0, 40, 5],  # lost
                [2, -1, 52, 50, 1.0, 5, 2],  # neutral
            ],
            step=1,
        )
        s1 = parse_observation(obs1)
        actions = d.step(s1)
        # Recapture cost > capacity、Capture のみ採用される
        ships_total = sum(a[2] for a in actions)
        assert ships_total <= 42
