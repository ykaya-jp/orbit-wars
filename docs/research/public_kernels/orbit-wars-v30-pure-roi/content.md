## [CODE]
```python
"""
Orbit Wars v30 - "Pure ROI"

Key insight: Complex agents (v26-v29) score WORSE on LB than simple v8.
v8 just sends to nearest target. We improve by targeting highest ROI.
No fleet inference, no coordination, no reserves.

Strategy:
1. For each planet: compute ROI for every neutral
2. Greedy: send minimum ships to best neutral first, then next best, etc.
3. Only deduplicate within the same turn (no inference from in-flight)
4. Attack enemy when all neutrals are covered
5. Minimal reserve: just keep 1 ship in very early game

Difference from v8:
- ROI ordering (best production/cost) instead of nearest
- Multi-target per planet (keep sending after first capture)
- Slight reserve to not be wiped out
- Sun-blocking check

Difference from v26:
- NO fleet inference (avoids false positives causing double-sends)
- NO N-way coordination (simple is better)
- NO complex reserve logic (avoids holding ships unnecessarily)
"""

import math

SUN_X, SUN_Y = 50.0, 50.0
SUN_RADIUS = 10.0
MAX_SPEED = 6.0
GAME_TURNS = 500


def _dist(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def _fleet_speed(ships):
    if ships <= 1:
        return 1.0
    return 1.0 + (MAX_SPEED - 1.0) * (math.log(max(1.0, float(ships))) / math.log(1000.0)) ** 1.5


def _seg_min_dist(x1, y1, x2, y2, px, py):
    dx, dy = x2 - x1, y2 - y1
    sq = dx * dx + dy * dy
    if sq < 1e-12:
        return math.hypot(x1 - px, y1 - py)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / sq))
    return math.hypot(x1 + t * dx - px, y1 + t * dy - py)


def _hits_sun(x1, y1, x2, y2):
    return _seg_min_dist(x1, y1, x2, y2, SUN_X, SUN_Y) < SUN_RADIUS + 0.5


def _is_orbiting(px, py, radius):
    return math.hypot(px - SUN_X, py - SUN_Y) + radius < 50.0


def _find_intercept(from_x, from_y, px, py, angular_velocity, ships, orbiting):
    if not orbiting:
        return px, py
    dx, dy = px - SUN_X, py - SUN_Y
    r = math.hypot(dx, dy)
    cur_angle = math.atan2(dy, dx)
    spd = _fleet_speed(ships)
    t = _dist(from_x, from_y, px, py) / spd
    for _ in range(40):
        na = cur_angle + angular_velocity * t
        tx = SUN_X + r * math.cos(na)
        ty = SUN_Y + r * math.sin(na)
        nt = _dist(from_x, from_y, tx, ty) / spd
        if abs(nt - t) < 0.01:
            return tx, ty
        t = 0.55 * t + 0.45 * nt
    na = cur_angle + angular_velocity * t
    return SUN_X + r * math.cos(na), SUN_Y + r * math.sin(na)


def agent(obs):
    """Pure ROI expansion agent."""
    if isinstance(obs, dict):
        player = obs.get("player", 0)
        raw_planets = obs.get("planets", [])
        raw_fleets = obs.get("fleets", [])
        av = obs.get("angular_velocity", 0.03)
        step = obs.get("step", 0)
        comet_ids_set = set(obs.get("comet_planet_ids", []))
    else:
        player = obs.player
        raw_planets = obs.planets
        raw_fleets = getattr(obs, 'fleets', [])
        av = obs.angular_velocity
        step = getattr(obs, 'step', 0)
        comet_ids_set = set(getattr(obs, 'comet_planet_ids', []))

    planets = []
    for p in raw_planets:
        pid, owner, x, y, radius, ships, production = p
        planets.append({
            'id': pid, 'owner': owner,
            'x': float(x), 'y': float(y),
            'radius': float(radius),
            'ships': int(ships),
            'production': int(production),
            'orbiting': _is_orbiting(float(x), float(y), float(radius)),
            'is_comet': pid in comet_ids_set,
        })

    my_planets = [p for p in planets if p['owner'] == player]
    neutrals = [p for p in planets if p['owner'] == -1]
    enemies = [p for p in planets if p['owner'] not in (-1, player)]

    if not my_planets:
        return []

    turns_left = max(50, GAME_TURNS - step)

    # Available ships: very minimal reserve (just keep 1 early, small buffer late)
    available = {}
    for mine in my_planets:
        if mine['is_comet']:
            available[mine['id']] = mine['ships']
            continue
        if step < 30:
            reserve = 1
        elif step < 100:
            reserve = max(2, mine['production'])
        else:
            reserve = max(5, mine['production'] * 2)
        available[mine['id']] = max(0, mine['ships'] - reserve)

    moves = []
    this_turn_covered = {}  # neutral_id -> ships committed this turn

    # For each planet, greedily pick best ROI neutrals
    for mine in sorted(my_planets, key=lambda p: available.get(p['id'], 0), reverse=True):
        budget = available.get(mine['id'], 0)
        if budget <= 0:
            continue

        if mine['is_comet']:
            # Evacuate comet
            stable = [p for p in my_planets if not p['is_comet'] and p['id'] != mine['id']]
            if not stable:
                stable = neutrals
            if stable:
                dest = min(stable, key=lambda p: _dist(mine['x'], mine['y'], p['x'], p['y']))
                if not _hits_sun(mine['x'], mine['y'], dest['x'], dest['y']):
                    angle = math.atan2(dest['y'] - mine['y'], dest['x'] - mine['x'])
                    moves.append([mine['id'], angle, budget])
            continue

        sent = 0
        candidates = []

        for t in neutrals:
            cov = this_turn_covered.get(t['id'], 0)
            if cov >= t['ships'] + 1:
                continue  # already committed this turn

            needed = max(1, t['ships'] + 1 - cov)
            if needed > budget - sent:
                continue

            tx, ty = _find_intercept(mine['x'], mine['y'], t['x'], t['y'],
                                      av, needed, t['orbiting'])
            if _hits_sun(mine['x'], mine['y'], tx, ty):
                continue

            d = _dist(mine['x'], mine['y'], tx, ty)
            travel = d / _fleet_speed(needed)
            turns_owned = max(1, turns_left - travel)
            prod = max(1, t['production'])
            roi = (prod ** 1.2 * turns_owned) / max(1, needed + travel * 0.2)
            candidates.append((roi, t, needed, tx, ty))

        candidates.sort(key=lambda c: c[0], reverse=True)

        for roi, t, needed, tx, ty in candidates:
            if needed > budget - sent:
                continue
            angle = math.atan2(ty - mine['y'], tx - mine['x'])
            moves.append([mine['id'], angle, needed])
            sent += needed
            this_turn_covered[t['id']] = this_turn_covered.get(t['id'], 0) + needed
            if sent >= budget:
                break

        available[mine['id']] = budget - sent

    # Attack enemies when all neutrals covered (or no neutrals)
    if enemies:
        my_prod = sum(p['production'] for p in my_planets)
        enemy_prod = sum(p['production'] for p in enemies)

        # Attack if we have production advantage or neutrals are all gone
        if my_prod >= enemy_prod or not neutrals:
            for t in sorted(enemies, key=lambda p: p['ships']):
                # How much do we have total available?
                total = sum(available.get(p['id'], 0) for p in my_planets)
                needed_e = t['ships'] + t['production'] * 8 + 1
                if total < needed_e:
                    continue

                remaining = needed_e
                for mine in sorted(my_planets,
                                   key=lambda p: available.get(p['id'], 0),
                                   reverse=True):
                    if available.get(mine['id'], 0) <= 0:
                        continue
                    tx, ty = _find_intercept(mine['x'], mine['y'], t['x'], t['y'],
                                              av, available[mine['id']], t['orbiting'])
                    if _hits_sun(mine['x'], mine['y'], tx, ty):
                        continue
                    send = min(remaining, available[mine['id']])
                    if send <= 0:
                        continue
                    angle = math.atan2(ty - mine['y'], tx - mine['x'])
                    moves.append([mine['id'], angle, send])
                    available[mine['id']] -= send
                    remaining -= send
                    if remaining <= 0:
                        break
                if remaining <= 0:
                    break

    return moves

```
