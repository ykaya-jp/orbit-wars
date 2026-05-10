"""
Orbit Wars v29 - "Defender"

Key insight: Top agents likely detect and respond to incoming enemy fleets.
We've been pure offense - losing planets to sneak attacks.

Strategy:
1. DEFENSE FIRST: Detect enemy fleets targeting my planets
   a. Can defend → reinforce (send ships from nearest ally)
   b. Can't defend → evacuate ships + counter-attack source
2. EXPANSION: ROI-based neutral capture (same as v26, cleaner)
3. ATTACK: Hit enemy when they're weak (just sent ships away)

New in v29:
- Enemy fleet target inference (angle-match with from_planet_id)
- Per-planet threat assessment (net ships at arrival)
- Dynamic reserve based on actual threat, not fixed formula
- Counter-attack on weakened source planets
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


def _angle_diff(a1, a2):
    d = a1 - a2
    while d > math.pi: d -= 2 * math.pi
    while d < -math.pi: d += 2 * math.pi
    return d


def _infer_fleet_targets(fleets, planets_by_id, candidate_planets, av, threshold=0.90):
    """Infer which planet each fleet is heading to. Returns {planet_id: total_ships}."""
    covered = {}
    for fleet in fleets:
        fx, fy = fleet['x'], fleet['y']
        fangle = fleet['angle']
        fships = fleet['ships']
        from_pid = fleet.get('from_pid')

        from_planet = planets_by_id.get(from_pid) if from_pid else None
        if from_planet and not from_planet['orbiting']:
            ref_x, ref_y = from_planet['x'], from_planet['y']
            thr = 0.95
        else:
            ref_x, ref_y = fx, fy
            thr = threshold

        best_p = None
        best_cos = thr

        for p in candidate_planets:
            if from_planet and p['id'] == from_planet['id']:
                continue
            try:
                tx, ty = _find_intercept(ref_x, ref_y, p['x'], p['y'],
                                          av, fships, p['orbiting'])
                dx, dy = tx - ref_x, ty - ref_y
                d = math.hypot(dx, dy)
                if d < 0.5:
                    continue
                ta = math.atan2(dy, dx)
                diff = _angle_diff(fangle, ta)
                cos_a = math.cos(diff)
                if cos_a > best_cos:
                    best_cos = cos_a
                    best_p = p
            except Exception:
                pass

        if best_p is not None:
            pid = best_p['id']
            covered[pid] = covered.get(pid, 0) + fships

    return covered


def _infer_fleet_targets_with_turns(fleets, planets_by_id, candidate_planets, av, threshold=0.90):
    """Like _infer_fleet_targets but also returns estimated arrival turns."""
    result = {}  # planet_id -> {'ships': N, 'turns': T}
    for fleet in fleets:
        fx, fy = fleet['x'], fleet['y']
        fangle = fleet['angle']
        fships = fleet['ships']
        from_pid = fleet.get('from_pid')

        from_planet = planets_by_id.get(from_pid) if from_pid else None
        if from_planet and not from_planet['orbiting']:
            ref_x, ref_y = from_planet['x'], from_planet['y']
            thr = 0.95
        else:
            ref_x, ref_y = fx, fy
            thr = threshold

        best_p = None
        best_cos = thr
        best_tx, best_ty = fx, fy

        for p in candidate_planets:
            if from_planet and p['id'] == from_planet['id']:
                continue
            try:
                tx, ty = _find_intercept(ref_x, ref_y, p['x'], p['y'],
                                          av, fships, p['orbiting'])
                dx, dy = tx - ref_x, ty - ref_y
                d = math.hypot(dx, dy)
                if d < 0.5:
                    continue
                ta = math.atan2(dy, dx)
                diff = _angle_diff(fangle, ta)
                cos_a = math.cos(diff)
                if cos_a > best_cos:
                    best_cos = cos_a
                    best_p = p
                    best_tx, best_ty = tx, ty
            except Exception:
                pass

        if best_p is not None:
            pid = best_p['id']
            # Estimate turns to arrive: distance from current fleet pos to target
            d = _dist(fx, fy, best_tx, best_ty)
            turns = max(1, d / _fleet_speed(fships))
            if pid not in result:
                result[pid] = {'ships': 0, 'turns': turns}
            result[pid]['ships'] += fships
            result[pid]['turns'] = min(result[pid]['turns'], turns)  # earliest arrival

    return result


def agent(obs):
    """Defender agent: respond to threats, then expand."""
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
    early_game = step < 150

    my_prod = sum(p['production'] for p in my_planets)
    enemy_prod = sum(p['production'] for p in enemies)
    my_ships_total = sum(p['ships'] for p in my_planets)

    planets_by_id = {p['id']: p for p in planets}
    my_planets_by_id = {p['id']: p for p in my_planets}

    # Parse fleets
    own_fleets = []
    enemy_fleets = []
    for f in raw_fleets:
        if len(f) < 7:
            continue
        fowner = int(f[1])
        fleet_data = {
            'x': float(f[2]), 'y': float(f[3]),
            'angle': float(f[4]), 'ships': int(f[-1]),
            'from_pid': int(f[5]),
        }
        if fowner == player:
            own_fleets.append(fleet_data)
        else:
            enemy_fleets.append(fleet_data)

    # --- THREAT ASSESSMENT ---
    # Infer where enemy fleets are heading (only to my planets)
    enemy_threats = _infer_fleet_targets_with_turns(
        enemy_fleets, planets_by_id, my_planets, av, threshold=0.88
    )

    # Track own fleets heading to my planets (reinforcements in flight)
    own_to_mine = _infer_fleet_targets_with_turns(
        own_fleets, planets_by_id, my_planets, av, threshold=0.88
    )

    # Track own fleets to neutrals (don't re-send)
    own_to_neutrals = _infer_fleet_targets(own_fleets, planets_by_id, neutrals, av)

    # Compute defense reserve per planet based on actual threats
    # If enemy threat T arrives in K turns, I'll have garrison + production*K ships
    # I need garrison + production*K >= T+1 to survive
    defense_reserve = {}
    threatened_planets = set()
    counter_attack_targets = {}  # planet_id -> source enemy planet

    for pid, threat in enemy_threats.items():
        planet = my_planets_by_id.get(pid)
        if not planet:
            continue
        t_ships = threat['ships']
        t_turns = threat['turns']
        # Ships I'll have when threat arrives (without reinforcement)
        projected = planet['ships'] + planet['production'] * int(t_turns)
        own_reinf = own_to_mine.get(pid, {}).get('ships', 0)
        if projected + own_reinf < t_ships + 1:
            # THREATENED: need reinforcement or evacuation
            needed = t_ships + 1 - projected - own_reinf
            defense_reserve[pid] = needed  # we need this many MORE ships to survive
            threatened_planets.add(pid)

    # Available ships: garrison for production, plus defense reserve
    available = {}
    for mine in my_planets:
        if mine['is_comet']:
            available[mine['id']] = mine['ships']  # evacuate comets
            continue

        # Base reserve: enough to not lose production momentum
        if early_game:
            base_reserve = max(1, mine['production'])
        else:
            prod_r = my_prod / max(1, enemy_prod)
            if prod_r >= 2.0:
                base_reserve = max(2, mine['production'])
            else:
                base_reserve = max(5, mine['production'] * 2)

        # Add threat reserve if this planet is threatened
        threat_r = defense_reserve.get(mine['id'], 0)

        reserve = max(base_reserve, threat_r)
        available[mine['id']] = max(0, mine['ships'] - reserve)

    moves = []
    this_turn_sent = {}  # planet_id of destination -> ships sent this turn

    # --- PHASE 1: DEFEND THREATENED PLANETS ---
    for pid in threatened_planets:
        planet = my_planets_by_id.get(pid)
        if not planet:
            continue

        threat = enemy_threats[pid]
        t_ships = threat['ships']
        t_turns = threat['turns']
        projected = planet['ships'] + planet['production'] * int(t_turns)
        own_reinf = own_to_mine.get(pid, {}).get('ships', 0)

        needed = max(0, t_ships + 1 - projected - own_reinf)
        if needed <= 0:
            continue

        # Find closest friendly planet with available ships (not the threatened one)
        allies = sorted(
            [p for p in my_planets if p['id'] != pid and available.get(p['id'], 0) > 0],
            key=lambda p: _dist(p['x'], p['y'], planet['x'], planet['y'])
        )

        sent_defense = 0
        for ally in allies:
            budget = available.get(ally['id'], 0)
            if budget <= 0:
                continue

            # Check if reinforcement can arrive in time
            d = _dist(ally['x'], ally['y'], planet['x'], planet['y'])
            travel = d / _fleet_speed(budget)
            if travel > t_turns * 1.2:  # won't make it in time
                # Try counter-attack instead: attack source planet
                # Find the source planet of the threat
                # We'll handle this after neutrals
                continue

            send = min(budget, needed - sent_defense)
            if send <= 0:
                continue

            if _hits_sun(ally['x'], ally['y'], planet['x'], planet['y']):
                continue

            angle = math.atan2(planet['y'] - ally['y'], planet['x'] - ally['x'])
            moves.append([ally['id'], angle, send])
            available[ally['id']] -= send
            sent_defense += send

            if sent_defense >= needed:
                break

    # --- PHASE 2: EXPAND TO NEUTRALS ---
    # Sort my planets by available ships (richest first)
    for mine in sorted(my_planets, key=lambda p: available.get(p['id'], 0), reverse=True):
        budget = available.get(mine['id'], 0)
        if budget <= 0:
            continue

        if mine['is_comet']:
            continue  # handle comets separately

        sent = 0
        candidates = []

        for t in neutrals:
            # How many ships already going there this turn + in-flight
            this_cov = this_turn_sent.get(t['id'], 0)
            inflight_cov = own_to_neutrals.get(t['id'], 0)

            total_cov = this_cov + inflight_cov
            if total_cov >= t['ships'] + 1:
                continue  # already covered

            needed = max(1, t['ships'] + 1 - total_cov)
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
            # ROI: production benefit over remaining turns minus cost
            roi = (prod ** 1.2 * turns_owned) / max(1, needed + travel * 0.3)
            candidates.append((roi, t, needed, tx, ty))

        candidates.sort(key=lambda c: c[0], reverse=True)

        for roi, t, needed, tx, ty in candidates:
            remaining = budget - sent
            if needed > remaining:
                continue

            angle = math.atan2(ty - mine['y'], tx - mine['x'])
            moves.append([mine['id'], angle, needed])
            sent += needed
            this_turn_sent[t['id']] = this_turn_sent.get(t['id'], 0) + needed

            if sent >= budget:
                break

        available[mine['id']] = budget - sent

    # --- N-WAY COORDINATION for uncovered expensive neutrals ---
    cx = sum(p['x'] for p in my_planets) / len(my_planets)
    cy = sum(p['y'] for p in my_planets) / len(my_planets)

    uncovered = []
    for t in neutrals:
        cov = this_turn_sent.get(t['id'], 0) + own_to_neutrals.get(t['id'], 0)
        if cov >= t['ships'] + 1:
            continue
        needed = max(1, t['ships'] + 1 - cov)
        total_avail = sum(available.get(p['id'], 0) for p in my_planets)
        if total_avail < needed:
            continue

        travel = _dist(cx, cy, t['x'], t['y']) / _fleet_speed(needed)
        turns_owned = max(1, turns_left - travel)
        prod = max(1, t['production'])
        roi = (prod ** 1.2 * turns_owned) / max(1, needed + travel * 0.3)
        uncovered.append((roi, t, needed))

    uncovered.sort(key=lambda x: x[0], reverse=True)

    for roi, t, needed in uncovered[:3]:
        cov = this_turn_sent.get(t['id'], 0) + own_to_neutrals.get(t['id'], 0)
        needed_now = max(1, t['ships'] + 1 - cov)
        if needed_now <= 0:
            continue

        # Find single planet that can do it alone
        for mine in sorted(my_planets,
                           key=lambda p: (available.get(p['id'], 0) >= needed_now,
                                         -_dist(p['x'], p['y'], t['x'], t['y'])),
                           reverse=True):
            budget = available.get(mine['id'], 0)
            if budget < needed_now:
                continue

            tx, ty = _find_intercept(mine['x'], mine['y'], t['x'], t['y'],
                                      av, needed_now, t['orbiting'])
            if _hits_sun(mine['x'], mine['y'], tx, ty):
                continue

            angle = math.atan2(ty - mine['y'], tx - mine['x'])
            moves.append([mine['id'], angle, needed_now])
            available[mine['id']] -= needed_now
            this_turn_sent[t['id']] = this_turn_sent.get(t['id'], 0) + needed_now
            break

    # --- PHASE 3: ATTACK ENEMIES ---
    if enemies:
        # Attack when we have production advantage and all neutrals covered
        prod_ratio = my_prod / max(1, enemy_prod)
        can_attack = prod_ratio >= 1.2 or not neutrals

        if can_attack:
            # Find weakest enemy (recent target or just sent ships = low garrison)
            for t in sorted(enemies, key=lambda p: p['ships'] + p['production'] * 5):
                # Estimate how many ships needed to capture
                needed_e = t['ships'] + t['production'] * 8 + 1
                # Check if enemy fleet just left here (making it weaker)
                enemy_from_here = sum(
                    f['ships'] for f in enemy_fleets
                    if f.get('from_pid') == t['id']
                )
                # Adjust for ships that left
                effective_garrison = max(1, t['ships'] - enemy_from_here)
                needed_e = effective_garrison + t['production'] * 5 + 1

                total_avail = sum(available.get(p['id'], 0) for p in my_planets)
                if total_avail < needed_e:
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
                break  # Attack one at a time

    # --- COMET EVACUATION ---
    for mine in my_planets:
        if not mine['is_comet']:
            continue
        budget = available.get(mine['id'], 0)
        if budget <= 0:
            continue
        stable = [p for p in my_planets if not p['is_comet'] and p['id'] != mine['id']]
        if not stable:
            stable = neutrals
        if not stable:
            continue
        dest = min(stable, key=lambda p: _dist(mine['x'], mine['y'], p['x'], p['y']))
        if not _hits_sun(mine['x'], mine['y'], dest['x'], dest['y']):
            angle = math.atan2(dest['y'] - mine['y'], dest['x'] - mine['x'])
            moves.append([mine['id'], angle, budget])

    return moves
