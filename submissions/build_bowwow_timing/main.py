"""Bowwow timing rule agent (= Phase alpha.3 first cut).

Reverse-engineered timing policy from bovard 2.8M-row top-10 episode dataset
(see docs/research/2026-05-12-bowwow-reverse.md):

  - mean launch_ships = 241 (= 1.9x of next contender flg)
  - launch / step = 0.43 (= mid-pack rate, NOT spam)
  - p99 launch_ships = 3647 (= sustained big-stack timing)
  - step 300 planets = 9.5, ships_total = 3751

Translation to four phase-keyed policies:

  step <  50:  early expansion  (min_ships=15,  frac=0.50)
  step <  200: build-up         (min_ships=80,  frac=0.70)
  step <  400: big-stack window (min_ships=150, frac=0.85)
  step >= 400: late consolidation(min_ships=80,  frac=0.70)

Target selection weights distance, defense, and production. Sun-safe angle
correction is borrowed from build_fleet_angle_zachary_v3.
"""

from __future__ import annotations

import math

SUN_X, SUN_Y = 50.0, 50.0
SUN_RADIUS = 10.0
MAX_SPEED = 6.0


def fleet_speed(ships: int) -> float:
    if ships <= 0:
        return 1.0
    return 1.0 + (MAX_SPEED - 1.0) * (math.log(max(ships, 1)) / math.log(1000)) ** 1.5


def _line_seg_min_dist(x1, y1, x2, y2, px, py):
    dx, dy = x2 - x1, y2 - y1
    len_sq = dx * dx + dy * dy
    if len_sq == 0:
        return math.hypot(x1 - px, y1 - py)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / len_sq))
    return math.hypot(x1 + t * dx - px, y1 + t * dy - py)


def _path_crosses_sun(x1, y1, x2, y2, margin=1.5):
    return _line_seg_min_dist(x1, y1, x2, y2, SUN_X, SUN_Y) < SUN_RADIUS + margin


def safe_angle(x1, y1, x2, y2):
    direct = math.atan2(y2 - y1, x2 - x1)
    if not _path_crosses_sun(x1, y1, x2, y2):
        return direct
    d = math.hypot(x1 - SUN_X, y1 - SUN_Y)
    if d <= SUN_RADIUS + 1.0:
        return direct
    half = math.asin(min(1.0, (SUN_RADIUS + 1.0) / d))
    to_sun = math.atan2(SUN_Y - y1, SUN_X - x1)
    cw, ccw = to_sun + half, to_sun - half

    def adiff(a):
        dd = (a - direct) % (2 * math.pi)
        return min(dd, 2 * math.pi - dd)

    return cw if adiff(cw) < adiff(ccw) else ccw


def _phase_policy(step):
    """Return (min_ships, launch_frac, defense_weight).

    Bowwow's data is misleading if read literally: a *mean* of 241 ships per
    launch hides the early-game where every winner is still firing 10-40 ship
    expansion fleets. Translation to phase policy keeps expansion aggressive
    and reserves the big-stack discipline for the mid/late window where it
    actually matters.
    """
    if step < 80:
        # Early expansion: don't outpace starter on planet count.
        return 10, 0.70, 0.3
    if step < 250:
        # Build-up: still expand, but start saving for one good blow.
        return 40, 0.75, 0.5
    if step < 420:
        # Big-stack window: this is where bowwow's 241-mean shows up.
        return 120, 0.85, 0.7
    # Endgame: dump ships at the highest-yield neutrals / weakest enemies.
    return 60, 0.85, 0.5


def _read(obs, key, default):
    if isinstance(obs, dict):
        return obs.get(key, default)
    return getattr(obs, key, default)


def agent(observation, configuration=None):
    try:
        step = int(_read(observation, "step", 0) or 0)
        player = int(_read(observation, "player", 0) or 0)
        planets = _read(observation, "planets", []) or []

        min_ships, frac, defense_weight = _phase_policy(step)

        my_planets = []
        targets = []
        for p in planets:
            pid = int(p[0])
            owner = int(p[1])
            x = float(p[2])
            y = float(p[3])
            ships = int(p[5])
            prod = int(p[6])
            if owner == player:
                my_planets.append((pid, x, y, ships, prod))
            else:
                targets.append((pid, owner, x, y, ships, prod))

        if not my_planets or not targets:
            return []

        actions = []
        for pid, x, y, ships, prod in my_planets:
            if ships < min_ships:
                continue

            best = None
            best_score = float("inf")
            for tpid, towner, tx, ty, tships, tprod in targets:
                dist = math.hypot(tx - x, ty - y)
                # Production gives a long-term reward; defense a short-term cost.
                cost = dist + tships * defense_weight - tprod * 8.0
                if towner == -1:
                    cost -= 20.0  # neutrals are basically free expansion
                if cost < best_score:
                    best_score = cost
                    best = (tpid, tx, ty, tships)

            if best is None:
                continue
            tpid, tx, ty, _tships = best

            send = max(int(min_ships * 0.85), int(ships * frac))
            send = min(send, ships - 5)
            if send < int(min_ships * 0.85):
                continue

            angle = safe_angle(x, y, tx, ty)
            actions.append([int(pid), float(angle), int(send)])

        return actions
    except Exception:
        return []
