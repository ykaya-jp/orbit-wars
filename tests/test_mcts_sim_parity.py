"""Parity fixtures for tools/mcts_orbit_wars.py combat resolution.

Codex review (2026-05-13) flagged that the original ``_resolve_arrivals``
mixed phase-1 (arriving fleets fight each other) and phase-2 (survivor vs
defender) into a single sort, so a small fleet could "capture" a defended
neutral that should have absorbed it. The fix re-implements both phases
verbatim against ``kaggle_environments/envs/orbit_wars/orbit_wars.py:634-674``.

Each scenario constructs a SimState by hand, fires one ``sim_step`` with no
launches, and asserts the (owner, ships) pair on the target planet matches
what the real engine would produce. Run with ``pytest tests/test_mcts_sim_parity.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent.parent / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))


from mcts_orbit_wars import Fleet, Planet, SimState, sim_step  # noqa: E402


def _build_state(planets: list[tuple], fleets: list[tuple], step: int = 0) -> SimState:
    """planets: (pid, owner, x, y, radius, ships, prod, is_orbit=False)
    fleets:  (owner, ships, target_pid, eta)
    """
    p_dict = {}
    for spec in planets:
        if len(spec) == 7:
            pid, owner, x, y, r, ships, prod = spec
            is_orb = False
        else:
            pid, owner, x, y, r, ships, prod, is_orb = spec
        p_dict[pid] = Planet(pid, owner, x, y, r, float(ships), float(prod), is_orb)
    f_list = [Fleet(o, float(s), t, float(e)) for (o, s, t, e) in fleets]
    return SimState(planets=p_dict, fleets=f_list, step=step)


def _step_no_launches(state: SimState) -> SimState:
    """Advance one turn with no agent actions (= grow + fleet arrival only)."""
    sim_step(state, actions_by_player={})
    return state


# ----- Phase 2 fixtures: single arriving fleet vs defender -----


def test_single_fleet_undershoots_neutral_garrison():
    """30 ships into a 50-ship neutral: still neutral, 20 ships left."""
    state = _build_state(
        planets=[(0, 0, 50.0, 50.0, 2.0, 100, 0), (1, -1, 30.0, 30.0, 2.0, 50, 0)],
        fleets=[(0, 30, 1, 1.0)],
    )
    _step_no_launches(state)
    p1 = state.planets[1]
    assert p1.owner == -1, f"expected neutral, got owner={p1.owner}"
    assert p1.ships == 20.0, f"expected 20 ships, got {p1.ships}"


def test_single_fleet_overruns_neutral_garrison():
    """80 ships into a 50-ship neutral: captured, 30 ships left over."""
    state = _build_state(
        planets=[(0, 0, 50.0, 50.0, 2.0, 100, 0), (1, -1, 30.0, 30.0, 2.0, 50, 0)],
        fleets=[(0, 80, 1, 1.0)],
    )
    _step_no_launches(state)
    p1 = state.planets[1]
    assert p1.owner == 0, f"expected owner=0, got owner={p1.owner}"
    assert p1.ships == 30.0, f"expected 30 ships, got {p1.ships}"


def test_single_fleet_exactly_ties_neutral_garrison():
    """50 ships into a 50-ship neutral: garrison absorbs all, planet still neutral, 0 ships."""
    state = _build_state(
        planets=[(0, 0, 50.0, 50.0, 2.0, 100, 0), (1, -1, 30.0, 30.0, 2.0, 50, 0)],
        fleets=[(0, 50, 1, 1.0)],
    )
    _step_no_launches(state)
    p1 = state.planets[1]
    # Engine: planet[5] -= 50 -> 0 (not negative); owner unchanged.
    assert p1.owner == -1
    assert p1.ships == 0.0


def test_friendly_reinforcement_adds_ships():
    """40 ships reinforcing my 60-ship planet -> 100 ships, plus growth."""
    state = _build_state(
        planets=[(0, 0, 50.0, 50.0, 2.0, 60, 2)],
        fleets=[(0, 40, 0, 1.0)],
    )
    _step_no_launches(state)
    p0 = state.planets[0]
    # 60 + 40 = 100, then growth +2 = 102.
    assert p0.owner == 0
    assert p0.ships == 102.0


# ----- Phase 1 fixtures: arriving fleets fight each other first -----


def test_two_fleets_cancel_on_tie():
    """Player 0 and player 1 each send 40 ships to a neutral with 10 ships.
    Phase 1: 40 vs 40 -> 0 survivors. Phase 2: skipped. Defender intact + growth."""
    state = _build_state(
        planets=[
            (0, 0, 10.0, 50.0, 2.0, 100, 0),
            (1, 1, 90.0, 50.0, 2.0, 100, 0),
            (2, -1, 50.0, 50.0, 2.0, 10, 1),
        ],
        fleets=[(0, 40, 2, 1.0), (1, 40, 2, 1.0)],
    )
    _step_no_launches(state)
    p2 = state.planets[2]
    assert p2.owner == -1
    # Neutral planets don't grow (engine: only owner >= 0 grows).
    assert p2.ships == 10.0


def test_two_fleets_top_minus_second_attacks_defender():
    """P0 sends 100, P1 sends 30 to a P2-owned planet with 50 ships.
    Phase 1: top=100 - second=30 = 70 survivors, owner=0.
    Phase 2: 70 vs 50 defender -> capture, 20 ships left.
    Then growth +1 on captured planet -> 21."""
    state = _build_state(
        planets=[
            (0, 0, 10.0, 50.0, 2.0, 200, 0),
            (1, 1, 90.0, 50.0, 2.0, 200, 0),
            (2, 2, 50.0, 50.0, 2.0, 50, 1),
        ],
        fleets=[(0, 100, 2, 1.0), (1, 30, 2, 1.0)],
    )
    _step_no_launches(state)
    p2 = state.planets[2]
    assert p2.owner == 0
    assert p2.ships == 21.0


def test_arriving_fleet_smaller_than_defender_does_not_capture():
    """P0 sends 20 ships to P1's planet with 50 garrison.
    Phase 1: single fleet, 20 survivors. Phase 2: 20 vs 50 -> defender keeps 30."""
    state = _build_state(
        planets=[(0, 0, 10.0, 50.0, 2.0, 100, 0), (1, 1, 90.0, 50.0, 2.0, 50, 2)],
        fleets=[(0, 20, 1, 1.0)],
    )
    _step_no_launches(state)
    p1 = state.planets[1]
    # 50 - 20 = 30, plus growth 2 = 32. Owner unchanged (P1).
    assert p1.owner == 1
    assert p1.ships == 32.0


def test_pending_fleet_not_yet_arrived():
    """Fleet with ETA=3 should remain in flight after one step (ETA decremented to 2)."""
    state = _build_state(
        planets=[(0, 0, 50.0, 50.0, 2.0, 100, 0), (1, -1, 30.0, 30.0, 2.0, 50, 0)],
        fleets=[(0, 30, 1, 3.0)],
    )
    _step_no_launches(state)
    p1 = state.planets[1]
    assert p1.owner == -1
    assert p1.ships == 50.0  # untouched (neutrals don't grow but garrison stays)
    assert len(state.fleets) == 1
    assert state.fleets[0].eta == 2.0
