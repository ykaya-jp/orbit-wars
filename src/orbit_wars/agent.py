"""Orbit Wars — exp001: nearest-planet sniper baseline.

Strategy (improvements over the starter):
  1. For each owned planet, find the nearest non-owned target.
  2. Compute ships_needed:
       - For neutrals (owner == -1): exactly garrison + 1
       - For enemy planets: garrison + 1 + MARGIN
  3. Don't drain a planet completely — keep `RESERVE` ships behind for defense.
  4. Skip launches that would take more than `MAX_FRACTION` of the source
     planet's garrison (over-commit guard).

Intentionally simple — beats the textbook starter in self-play by not
suiciding home planets.
"""

from __future__ import annotations

import math

from kaggle_environments.envs.orbit_wars.orbit_wars import Planet

# Tunable params (module-level so they show up cleanly in replay logs)
RESERVE = 5
MAX_FRACTION = 0.85
MARGIN = 1


def _capacity(p: Planet) -> int:
    """Max launchable ships from this planet under our reserve / fraction rules."""
    return max(0, min(int(p.ships * MAX_FRACTION), p.ships - RESERVE))


def _distance(a: Planet, b: Planet) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def agent(observation, configuration=None):
    if isinstance(observation, dict):
        get = observation.get
    else:

        def get(key, default=None):
            return getattr(observation, key, default)

    raw_planets = get("planets", []) or []
    player = get("player", 0) or 0

    planets = [Planet(*p) for p in raw_planets]
    my_planets = [p for p in planets if p.owner == player]
    targets = [p for p in planets if p.owner != player]
    if not my_planets or not targets:
        return []

    moves: list[list[float]] = []
    for mine in my_planets:
        cap = _capacity(mine)
        if cap <= 0:
            continue

        nearest = min(targets, key=lambda t: _distance(mine, t))
        if nearest.owner == -1:
            ships_needed = nearest.ships + 1
        else:
            ships_needed = nearest.ships + 1 + MARGIN

        if ships_needed > cap:
            continue

        angle = math.atan2(nearest.y - mine.y, nearest.x - mine.x)
        moves.append([mine.id, angle, int(ships_needed)])

    return moves
