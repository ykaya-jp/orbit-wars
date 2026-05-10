## [CODE]
```python
"""
Orbit Wars - Elite Competitive Agent v6.1
Based on v5 aggressive style but with guaranteed capture validation.
Attacks aggressively but validates we have a reasonable chance of winning.
"""
import os
os.environ['KAGGLE_ENVELOPES'] = '0'

import math
from typing import List, Tuple

SUN_X, SUN_Y = 50.0, 50.0
SUN_RADIUS = 10.0
MAX_SPEED = 6.0
BOARD = 100.0
GAME_STEPS = 500

def fleet_speed(ships: int) -> float:
    if ships <= 0:
        return 1.0
    return 1.0 + (MAX_SPEED - 1.0) * (math.log(max(ships, 1)) / math.log(1000)) ** 1.5

def travel_time(x1: float, y1: float, x2: float, y2: float, ships: int) -> float:
    dist = math.hypot(x2 - x1, y2 - y1)
    return dist / fleet_speed(ships) if ships > 0 else 999.0

def line_seg_min_dist(x1: float, y1: float, x2: float, y2: float, px: float, py: float) -> float:
    dx, dy = x2 - x1, y2 - y1
    len_sq = dx * dx + dy * dy
    if len_sq == 0:
        return math.hypot(x1 - px, y1 - py)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / len_sq))
    return math.hypot(x1 + t * dx - px, y1 + t * dy - py)

def path_crosses_sun(x1: float, y1: float, x2: float, y2: float, margin: float = 1.5) -> bool:
    return line_seg_min_dist(x1, y1, x2, y2, SUN_X, SUN_Y) < SUN_RADIUS + margin

def safe_angle(x1: float, y1: float, x2: float, y2: float) -> float:
    direct = math.atan2(y2 - y1, x2 - x1)
    if not path_crosses_sun(x1, y1, x2, y2):
        return direct
    d = math.hypot(x1 - SUN_X, y1 - SUN_Y)
    if d <= SUN_RADIUS + 3.0:
        return direct
    half_ang = math.asin(min(1.0, (SUN_RADIUS + 3.0) / d))
    to_sun = math.atan2(SUN_Y - y1, SUN_X - x1)
    cw = to_sun + half_ang
    ccw = to_sun - half_ang
    def ang_diff(a: float, b: float) -> float:
        d = (a - b) % (2 * math.pi)
        return min(d, 2 * math.pi - d)
    return cw if ang_diff(cw, direct) < ang_diff(ccw, direct) else ccw

def predict_orbit(x: float, y: float, omega: float, dt: float) -> Tuple[float, float]:
    theta = math.atan2(y - SUN_Y, x - SUN_X)
    r = math.hypot(x - SUN_X, y - SUN_Y)
    return SUN_X + r * math.cos(theta + omega * dt), SUN_Y + r * math.sin(theta + omega * dt)

def solve_intercept(fx: float, fy: float, tx: float, ty: float,
                    orbiting: bool, omega: float, ships: int,
                    iterations: int = 30) -> Tuple[float, float, float]:
    if not orbiting:
        t = travel_time(fx, fy, tx, ty, ships)
        return tx, ty, t
    t = travel_time(fx, fy, tx, ty, ships)
    ix, iy = tx, ty
    for _ in range(iterations):
        ix, iy = predict_orbit(tx, ty, omega, t)
        t_new = travel_time(fx, fy, ix, iy, ships)
        if abs(t_new - t) < 0.05:
            break
        t = t_new
    return ix, iy, t

def ships_required(target_ships: float, owner: int, prod: float, travel_t: float) -> int:
    if owner == -1:
        return max(5, int(target_ships) + 2)
    return max(5, int(target_ships) + int(prod * travel_t) + 3)

def angle_diff(a: float, b: float) -> float:
    d = (a - b) % (2 * math.pi)
    return min(d, 2 * math.pi - d)

class Planet:
    __slots__ = ('id', 'owner', 'x', 'y', 'radius', 'ships', 'production',
                 'orbital_radius', 'is_orbiting', 'is_comet')
    def __init__(self, data: List, comet_ids: set):
        self.id = data[0]
        self.owner = data[1]
        self.x = data[2]
        self.y = data[3]
        self.radius = data[4]
        self.ships = float(data[5])
        self.production = float(data[6])
        self.orbital_radius = math.hypot(self.x - SUN_X, self.y - SUN_Y)
        self.is_orbiting = (self.orbital_radius + self.radius) < 48.0
        self.is_comet = self.id in comet_ids

class Fleet:
    __slots__ = ('id', 'owner', 'x', 'y', 'angle', 'from_planet', 'ships')
    def __init__(self, data: List):
        self.id = data[0]
        self.owner = data[1]
        self.x = data[2]
        self.y = data[3]
        self.angle = data[4]
        self.from_planet = data[5]
        self.ships = float(data[6])

def planet_strategic_value(p: Planet) -> float:
    dist_from_center = math.hypot(p.x - SUN_X, p.y - SUN_Y)
    central_bonus = max(0, 15 - dist_from_center) * 0.3
    return central_bonus + p.production * 2

def agent(obs):
    step = obs.get('step', 0) if isinstance(obs, dict) else getattr(obs, 'step', 0)
    player = obs.get('player', 0) if isinstance(obs, dict) else getattr(obs, 'player', 0)
    raw_planets = obs.get('planets', []) if isinstance(obs, dict) else getattr(obs, 'planets', [])
    raw_fleets = obs.get('fleets', []) if isinstance(obs, dict) else getattr(obs, 'fleets', [])
    omega = obs.get('angular_velocity', 0.03) if isinstance(obs, dict) else getattr(obs, 'angular_velocity', 0.03)
    comet_ids = set(obs.get('comet_planet_ids', []) if isinstance(obs, dict) else getattr(obs, 'comet_planet_ids', []))

    planets = [Planet(p, comet_ids) for p in raw_planets]
    fleets = [Fleet(f) for f in raw_fleets]

    my_planets = [p for p in planets if p.owner == player]
    if not my_planets:
        return []

    if step < 80:
        phase = 'early'
    elif step < 280:
        phase = 'mid'
    elif step < 420:
        phase = 'late'
    else:
        phase = 'endgame'

    my_total = sum(p.ships for p in my_planets)
    my_prod = sum(p.production for p in my_planets)
    enemy_planets = [p for p in planets if p.owner not in (-1, player)]
    enemy_total = sum(p.ships for p in enemy_planets)
    enemy_prod = sum(p.production for p in enemy_planets)
    all_planets = [p for p in planets if p.owner != player]

    is_winning = my_total > enemy_total * 0.85
    is_strong = my_total > enemy_total * 1.15
    is_desperate = my_total < enemy_total * 0.5

    threats = {}
    for f in fleets:
        if f.owner == player:
            continue
        for p in my_planets:
            dx, dy = p.x - f.x, p.y - f.y
            dot = math.cos(f.angle) * dx + math.sin(f.angle) * dy
            if dot <= 0:
                continue
            cross = abs(math.cos(f.angle) * dy - math.sin(f.angle) * dx)
            if cross < p.radius + 6.0:
                threats[p.id] = threats.get(p.id, 0.0) + f.ships

    in_flight = {}
    for f in fleets:
        if f.owner != player:
            continue
        best_pid, best_score = None, float('inf')
        for p in planets:
            if p.id == f.from_planet:
                continue
            dx, dy = p.x - f.x, p.y - f.y
            ang_diff_val = angle_diff(f.angle, math.atan2(dy, dx))
            dist = math.hypot(dx, dy)
            score = ang_diff_val * 8 + dist * 0.01
            if score < best_score:
                best_score, best_pid = score, p.id
        if best_pid is not None and best_score < 1.5:
            in_flight[best_pid] = in_flight.get(best_pid, 0.0) + f.ships

    enemy_fleets = [f for f in fleets if f.owner != player and f.owner != -1]

    garrison_size = {}
    for p in my_planets:
        base = max(5, int(p.production * 3.5))
        threat_level = threats.get(p.id, 0.0)
        if threat_level > 0:
            base = max(base, int(threat_level) + 10)
        if phase == 'endgame':
            base = max(3, int(base * 0.6))
        elif phase == 'early':
            base = max(3, int(base * 0.8))
        garrison_size[p.id] = base

    available = {}
    for p in my_planets:
        available[p.id] = max(0, int(p.ships) - garrison_size[p.id])

    committed = {p.id: 0 for p in my_planets}
    moves = []

    # Phase 1: Reinforce threatened planets
    for p in my_planets:
        threat = threats.get(p.id, 0.0)
        if threat > 0:
            need = int(threat) + 5 - int(p.ships)
            if need > 0:
                donors = sorted(
                    [x for x in my_planets if x.id != p.id and available[x.id] - committed[x.id] > 4],
                    key=lambda x: math.hypot(x.x - p.x, x.y - p.y)
                )
                for d in donors:
                    can = available[d.id] - committed[d.id]
                    send = min(can, need)
                    if send < 4:
                        continue
                    ix, iy, _ = solve_intercept(d.x, d.y, p.x, p.y, p.is_orbiting, omega, send)
                    moves.append([d.id, safe_angle(d.x, d.y, ix, iy), send])
                    committed[d.id] += send
                    need -= send
                    if need <= 0:
                        break

    if not all_planets:
        return moves

    # Phase 2: Vulture mode
    for ef in enemy_fleets:
        if ef.ships < 10:
            continue
        for tgt in all_planets:
            if tgt.owner == player:
                continue
            dx, dy = tgt.x - ef.x, tgt.y - ef.y
            dot = math.cos(ef.angle) * dx + math.sin(ef.angle) * dy
            if dot <= 0:
                continue
            cross = abs(math.cos(ef.angle) * dy - math.sin(ef.angle) * dx)
            if cross < tgt.radius + 8.0:
                dist = math.hypot(dx, dy)
                tt = dist / fleet_speed(int(ef.ships))
                if tt > 20:
                    continue

                if tgt.owner == -1 and tgt.ships < ef.ships * 0.9:
                    if is_desperate or ef.ships > 25:
                        continue
                    for dp in my_planets:
                        if dp.id == tgt.id:
                            continue
                        can = available[dp.id] - committed[dp.id]
                        if can < 12:
                            continue
                        d = math.hypot(dp.x - tgt.x, dp.y - tgt.y)
                        my_tt = d / fleet_speed(can)
                        if my_tt < tt - 3:
                            send = min(can, int(ef.ships * 0.55) + 10)
                            if send >= 12:
                                ix, iy, _ = solve_intercept(dp.x, dp.y, tgt.x, tgt.y, tgt.is_orbiting, omega, send)
                                moves.append([dp.id, safe_angle(dp.x, dp.y, ix, iy), send])
                                committed[dp.id] += send
                                break

    # Phase 3: Target selection with value scoring - IMPROVED
    candidates_by_planet = {}
    for mine in my_planets:
        budget = available[mine.id] - committed[mine.id]
        if budget < 5:
            continue

        candidates = []
        for tgt in all_planets:
            est_send = max(5, int(tgt.ships) + 2)
            ix, iy, t = solve_intercept(mine.x, mine.y, tgt.x, tgt.y, tgt.is_orbiting, omega, est_send)
            dist = math.hypot(mine.x - ix, mine.y - iy)

            is_neutral = tgt.owner == -1
            is_enemy = tgt.owner not in (-1, player)

            # IMPROVED: Better production weighting
            base_value = (tgt.production * 12) / (max(dist, 5) ** 0.6)  # Increased production weight
            base_value += planet_strategic_value(tgt) * 0.3

            if is_neutral:
                value = base_value + 30
            elif is_enemy:
                value = base_value + 35
                if is_strong:
                    value += 25
                elif is_desperate:
                    value += 15
            else:
                value = base_value

            # IMPROVED: Higher value for high production planets
            if tgt.production >= 3:
                value *= 1.2

            value -= tgt.ships * 0.035  # Slightly less penalty for defender ships

            if phase == 'early':
                if is_neutral:
                    value *= 1.5
            elif phase == 'mid':
                value *= 1.0
            elif phase == 'late':
                if not is_neutral:
                    value *= 1.2  # Increased from 1.15
            else:
                value *= 1.25
                value += tgt.production * 4  # Increased from 3

            needed = ships_required(tgt.ships, tgt.owner, tgt.production, t)
            effective_needed = max(1, needed - in_flight.get(tgt.id, 0))
            value -= effective_needed * 0.02  # Less penalty for needed ships

            if path_crosses_sun(mine.x, mine.y, ix, iy):
                value *= 0.75  # Less penalty for sun crossing (was 0.78)

            if tgt.is_comet:
                if phase == 'endgame' and not is_enemy:
                    value += 25
                elif phase != 'endgame':
                    value += 12

            candidates.append((tgt, value, ix, iy, t, needed))

        candidates.sort(key=lambda x: x[1], reverse=True)
        candidates_by_planet[mine.id] = candidates

    # Phase 4: Coordinated attacks when strong
    if is_strong and candidates_by_planet:
        all_candidates = []
        for pid, cands in candidates_by_planet.items():
            if cands:
                all_candidates.extend([(pid, c) for c in cands[:2]])

        if all_candidates:
            all_candidates.sort(key=lambda x: x[1][1], reverse=True)
            best_target = all_candidates[0][1][0]

            coordinated = []
            for pid, cands in candidates_by_planet.items():
                if cands and cands[0][0].id == best_target.id:
                    coordinated.append(pid)

            if len(coordinated) >= 2:
                total_available = sum(available[pid] - committed.get(pid, 0) for pid in coordinated)
                needed_total = ships_required(best_target.ships, best_target.owner, best_target.production, 12)

                if total_available > needed_total * 0.7:
                    for pid in coordinated:
                        budget = available[pid] - committed[pid]
                        if budget < 6:
                            continue
                        tgt, val, ix, iy, t, needed = candidates_by_planet[pid][0]
                        effective = max(1, needed - int(in_flight.get(tgt.id, 0)))
                        send = min(effective, budget)
                        send = min(send, int(tgt.ships * 1.2) + 10)
                        if send >= 6:
                            ang = safe_angle(planets[pid].x, planets[pid].y, ix, iy)
                            moves.append([pid, ang, send])
                            committed[pid] += send
                            in_flight[tgt.id] = in_flight.get(tgt.id, 0.0) + send
                    return moves

    # Phase 5: Regular attacks - aggressive like v5
    for mine in my_planets:
        budget = available[mine.id] - committed[mine.id]
        if budget < 5:
            continue

        candidates = candidates_by_planet.get(mine.id, [])
        for tgt, value, ix, iy, t, needed in candidates:
            if budget < 5:
                break

            effective = max(1, needed - int(in_flight.get(tgt.id, 0)))
            send = min(effective, budget)

            if is_strong and tgt.owner not in (-1, player):
                max_send = min(send, int(tgt.ships * 1.2) + 10)
                send = min(send, max_send)

            if send < 5:
                continue

            ang = safe_angle(mine.x, mine.y, ix, iy)
            moves.append([mine.id, ang, send])
            committed[mine.id] += send
            budget -= send
            in_flight[tgt.id] = in_flight.get(tgt.id, 0.0) + send
            break

    # Phase 6: Endgame consolidation
    if phase == 'endgame':
        best_prod = max(my_planets, key=lambda p: p.production)

        for mine in my_planets:
            if mine.id == best_prod.id:
                continue

            budget = available[mine.id] - committed[mine.id]
            if budget >= 10:
                ix, iy, _ = solve_intercept(mine.x, mine.y, best_prod.x, best_prod.y,
                                           best_prod.is_orbiting, omega, budget)
                ang = safe_angle(mine.x, mine.y, ix, iy)
                moves.append([mine.id, ang, budget])
                committed[mine.id] += budget

    return moves

if __name__ == '__main__':
    print("Elite Orbit Wars Agent v6.1 loaded successfully!")
    print("Based on v5 aggressive style with v5 structure")
```
