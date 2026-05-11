"""Unit tests for ExpansionPriorityMission (P3 = bovard 真因解析の expansion gap solver)."""

from __future__ import annotations

import pytest
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet

from orbit_wars.missions import (
    ExpansionPriorityMission,
    GameState,
)


def _make_state(
    step: int,
    planets: list[tuple[int, int, float, float, float, float, float]],
    *,
    player: int = 0,
    fleets: list = None,
    comet_planet_ids: set | None = None,
) -> GameState:
    """Helper: construct GameState from tuples (id, owner, x, y, radius, ships, prod)."""
    return GameState(
        player=player,
        step=step,
        planets=[Planet(*p) for p in planets],
        fleets=fleets or [],
        angular_velocity=0.0,
        initial_planets=[Planet(*p) for p in planets],
        comet_planet_ids=comet_planet_ids or set(),
    )


@pytest.mark.unit
def test_expansion_active_in_early_game():
    """Early game (step ≤ early_game_steps) で nearby neutral を target."""
    mission = ExpansionPriorityMission(early_game_steps=150, max_distance=35.0)
    state = _make_state(
        step=50,
        planets=[
            (0, 0, 50.0, 50.0, 3.0, 100.0, 1.0),
            (1, -1, 65.0, 55.0, 2.0, 10.0, 0.5),
        ],
    )
    score, moves = mission.evaluate(state)
    assert score > 0, "Should produce score > 0 in early game with viable target"
    assert len(moves) == 1, "Single mine + single nearby neutral = 1 move"
    assert moves[0].from_planet_id == 0
    assert moves[0].ships >= 10 + 1 + 8


@pytest.mark.unit
def test_expansion_deactive_after_early_game():
    """Late game (step > early_game_steps) で score=0、 0 moves。"""
    mission = ExpansionPriorityMission(early_game_steps=150)
    state = _make_state(
        step=200,
        planets=[
            (0, 0, 50.0, 50.0, 3.0, 100.0, 1.0),
            (1, -1, 65.0, 55.0, 2.0, 10.0, 0.5),
        ],
    )
    score, moves = mission.evaluate(state)
    assert score == 0.0, "Should return 0 score after early_game_steps"
    assert len(moves) == 0, "Should return no moves after early_game_steps"


@pytest.mark.unit
def test_expansion_skips_far_targets():
    """max_distance を超える neutral は target にしない (= nearby cluster 限定)."""
    mission = ExpansionPriorityMission(early_game_steps=150, max_distance=20.0)
    state = _make_state(
        step=10,
        planets=[
            (0, 0, 50.0, 50.0, 3.0, 100.0, 1.0),
            (1, -1, 90.0, 90.0, 2.0, 10.0, 0.5),
        ],
    )
    score, moves = mission.evaluate(state)
    assert score == 0.0, "Far target (dist > max_distance) should be skipped"
    assert len(moves) == 0


@pytest.mark.unit
def test_expansion_capture_buffer_applied():
    """capture_buffer が ships_needed に上乗せされる (= post-capture garrison 確保)."""
    mission = ExpansionPriorityMission(early_game_steps=150, max_distance=50.0, capture_buffer=15)
    state = _make_state(
        step=20,
        planets=[
            (0, 0, 50.0, 50.0, 3.0, 100.0, 1.0),
            (1, -1, 65.0, 50.0, 2.0, 10.0, 0.5),
        ],
    )
    _score, moves = mission.evaluate(state)
    assert len(moves) == 1
    expected_min_ships = 10 + 1 + 15
    assert (
        moves[0].ships >= expected_min_ships
    ), f"ships {moves[0].ships} should include capture_buffer 15"


@pytest.mark.unit
def test_expansion_respects_capacity():
    """home cap (= ships * 0.85 - reserve) を超える target は skip。"""
    mission = ExpansionPriorityMission(early_game_steps=150, capture_buffer=8)
    state = _make_state(
        step=10,
        planets=[
            (0, 0, 50.0, 50.0, 3.0, 10.0, 1.0),
            (1, -1, 65.0, 50.0, 2.0, 200.0, 0.5),
        ],
    )
    score, moves = mission.evaluate(state)
    assert score == 0.0, "Target with ships > home cap should be skipped"
    assert len(moves) == 0


@pytest.mark.unit
def test_expansion_skips_comet_planets():
    """comet_planet_ids に含まれる neutral は CometGrabMission に任せる。"""
    mission = ExpansionPriorityMission(early_game_steps=150)
    state = _make_state(
        step=10,
        planets=[
            (0, 0, 50.0, 50.0, 3.0, 100.0, 1.0),
            (1, -1, 65.0, 50.0, 2.0, 10.0, 0.5),
        ],
        comet_planet_ids={1},
    )
    score, moves = mission.evaluate(state)
    assert score == 0.0, "Comet planet should be skipped"
    assert len(moves) == 0


@pytest.mark.unit
def test_expansion_no_my_planets():
    """自分の planet がない場合は no-op (= defensive guard)."""
    mission = ExpansionPriorityMission()
    state = _make_state(
        step=10,
        planets=[(1, -1, 50.0, 50.0, 2.0, 10.0, 0.5)],
    )
    score, moves = mission.evaluate(state)
    assert score == 0.0
    assert len(moves) == 0


@pytest.mark.unit
def test_expansion_score_multiplier_applied():
    """score_multiplier がない場合と 2x 比較で 2 倍になる。"""
    base = ExpansionPriorityMission(score_multiplier=1.0)
    boosted = ExpansionPriorityMission(score_multiplier=2.0)
    state = _make_state(
        step=10,
        planets=[
            (0, 0, 50.0, 50.0, 3.0, 100.0, 1.0),
            (1, -1, 65.0, 50.0, 2.0, 10.0, 0.5),
        ],
    )
    score_base, _ = base.evaluate(state)
    score_boost, _ = boosted.evaluate(state)
    assert score_boost == pytest.approx(2.0 * score_base, rel=1e-6)
