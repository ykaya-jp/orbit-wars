"""AlphaOrbit-style territorial dominance agent (= Phase alpha.4 = bovard EDA driven).

Reverse-engineered from 7 winning bovard episodes (= AlphaOrbit 7/7 = 100% WR
on 2026-05-13 sample). Real top-tier launch profile diverges entirely from
the "bowwow big-stack" myth used in earlier builds:

  - mean launch ships = 29.4 (P95 = 53) -- NOT 241 as morning research claimed
  - launch_rate per step = 0.557 (= half the steps fire something)
  - target distance median = 21.4 (= short reach, no long-range gambles)
  - target ships median = 22, P95 = 84 (= attack soft planets, not fortresses)
  - target prod median = 3.0 (= prefer high-production planets, "investment")
  - own-target launches = 68% (= ships are circulated for reinforcement)
  - planets owned: 14.3 @ step 100, 23.4 @ step 200 (= explosive expansion)

Strategy translation:

  - launch threshold scales linearly with available ships, not a hard floor.
  - target scoring prefers high prod + short distance + low defender.
  - friendly reinforcement: when an own-front planet has too few ships, ship
    in from a back-line surplus planet.
  - launch fraction is small (1/3 to 1/2 of ships) so multiple sources can
    fire each turn -- frequency over magnitude.
"""

from __future__ import annotations

import math

SUN_X, SUN_Y = 50.0, 50.0
SUN_RADIUS = 10.0
MAX_SPEED = 6.0
ROTATION_RADIUS_LIMIT = 50.0
BOARD = 100.0


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


def _read(obs, key, default):
    if isinstance(obs, dict):
        return obs.get(key, default)
    return getattr(obs, key, default)


def _phase(step):
    """Return (min_ships_to_act, max_send_fraction).

    Tuned to mirror AlphaOrbit's per-step trace:
      step <  80: pure expand, fire 1/2 of ships once owners exceed 15.
      step 80-200: build phase, throttle launches a bit so the planet bank grows.
      step 200-380: combat phase, allow larger sends to break enemy fronts.
      step 380+:   endgame, dump ships at the highest-yield planets.
    """
    if step < 80:
        return 15, 0.50
    if step < 200:
        return 25, 0.50
    if step < 380:
        return 30, 0.60
    return 30, 0.75


def agent(observation, configuration=None):
    try:
        step = int(_read(observation, "step", 0) or 0)
        player = int(_read(observation, "player", 0) or 0)
        planets_raw = _read(observation, "planets", []) or []

        min_ships, send_frac = _phase(step)

        my_planets = []
        targets = []
        for p in planets_raw:
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

        if not my_planets:
            return []

        actions = []
        for pid, x, y, ships, prod in my_planets:
            if ships < min_ships:
                continue

            # AlphaOrbit-style scoring:
            #   - heavy reward for high-prod targets (long-term investment)
            #   - prefer short distance (close = arrive before counter)
            #   - penalise garrisoned defenders
            #   - bonus for neutrals (cheap capture)
            # Note: AB experiment in night session showed adding own-target
            # reinforcement here regressed 3/8 -> 2/8 -- AlphaOrbit's 68%
            # own-target rate works for them because they have 14+ planets by
            # step 100; we have 2, so any ships shipped sideways are ships
            # NOT shipped at a fresh neutral. Keep external-only for now.
            best = None
            best_score = -float("inf")
            for tpid, towner, tx, ty, tships, tprod in targets:
                dist = math.hypot(tx - x, ty - y)
                if dist > 60.0:  # AlphaOrbit P95 = 77, mean 30 -- keep it short
                    continue
                score = 3.0 * tprod - 0.5 * dist - 0.6 * tships
                if towner == -1:
                    score += 8.0  # neutral = easy capture
                if score > best_score:
                    best_score = score
                    best = (tpid, tx, ty, tships, tprod, towner)

            # Friendly reinforcement fallback (= only if no external target).
            if best is None and len(my_planets) >= 2:
                front = None
                front_score = float("inf")
                for tpid, tx, ty, tships, tprod in my_planets:
                    if tpid == pid:
                        continue
                    dist = math.hypot(tx - x, ty - y)
                    if dist > 50.0:
                        continue
                    fscore = tships - 2.0 * tprod
                    if fscore < front_score:
                        front_score = fscore
                        front = (tpid, tx, ty, tships, tprod, player)
                if front is not None:
                    best = front

            if best is None:
                continue
            tpid, tx, ty, _tships, _tprod, _towner = best

            send = max(min_ships, int(ships * send_frac))
            send = min(send, ships - 5)
            if send < min_ships:
                continue

            angle = safe_angle(x, y, tx, ty)
            actions.append([int(pid), float(angle), int(send)])

        return actions
    except Exception:
        return []
