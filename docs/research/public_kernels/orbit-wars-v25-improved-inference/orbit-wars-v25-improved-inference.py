"""
Orbit Wars Agent - v25 "Improved Inference"

Based on v22 "Domination" with one targeted improvement:

BETTER FLEET INFERENCE: Use from_planet_id (fleet[5]) to infer fleet targets
more accurately. For non-orbiting source planets, compute expected angle from
the ORIGIN planet to each possible target's intercept. This is more accurate
than angle-from-current-fleet-position because it uses the fixed launch angle.

All v22 features preserved:
1. N-WAY COORDINATED ATTACKS: Instead of just 2-planet coordination, collect
   ships from ALL available planets and time them to arrive simultaneously.

2. PRODUCTION RATIO AWARENESS: Track our production vs enemy production.
   - If we're ahead: aggressive mode (attack everything)
   - If we're behind: defend core + neutralize their best planets

3. BETTER FLEET INFERENCE FOR ORBITING PLANETS: When inferring where an enemy
   fleet is going, also check the intercept point (not just current position).
   This fixes false negatives in enemy-racing logic.

4. RETREAT/ABANDON LOGIC: If a planet is already doomed (enemy in-flight
   force > 2x our ships there + reserve), abandon it rather than throw
   more ships into a losing battle.

5. TIGHT NEUTRAL RACING: Instead of skipping neutrals where enemy arrives
   5 turns earlier, compute exact ship count needed to arrive at same time.
   A slightly larger fleet is faster and can beat a smaller enemy fleet.

6. MULTI-PLANET SURPLUS FLOW: In late game, route surplus ships through the
   graph toward the nearest enemy, using BFS-style routing.

All v20/v21 improvements preserved:
- In-flight fleet tracking (no double-sending)
- Phase-aware defense (3 ships reserve early, production*2 late)
- Multi-neutral flood (send to ALL affordable neutrals)
- ROI-based scoring with GAME_TURNS=500
- Travel-time compensated enemy attack
- Enemy racing (skip unwinnable neutral races)
- Surplus transfer to frontline
"""

import math

SUN_X, SUN_Y = 50.0, 50.0
SUN_RADIUS = 10.0
MAX_SPEED = 6.0
GAME_TURNS = 500
COORD_WINDOW = 15   # Increased from 10 - allow more coordination


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


def _arrival_time(from_x, from_y, target, ships, angular_velocity):
    """Estimate fleet arrival time (turns) from position to target planet."""
    tx, ty = _find_intercept(from_x, from_y, target['x'], target['y'],
                              angular_velocity, ships, target['orbiting'])
    d = _dist(from_x, from_y, tx, ty)
    return d / _fleet_speed(ships)


def _ships_needed_enemy(target, from_x, from_y):
    """Ships needed to capture enemy planet (travel-time compensated)."""
    base = target['ships'] + 1
    for _ in range(8):
        d = _dist(from_x, from_y, target['x'], target['y'])
        travel = d / _fleet_speed(base)
        at_arrival = target['ships'] + target['production'] * travel
        new_base = int(at_arrival) + 2
        if new_base <= base:
            break
        base = new_base
    return base


def _roi_neutral(target, needed, from_x, from_y, turns_left):
    d = _dist(from_x, from_y, target['x'], target['y'])
    travel = d / _fleet_speed(needed)
    prod = max(1, target['production'])
    turns_owned = max(1, turns_left - travel)
    return (prod * turns_owned) / (needed + travel * 0.5)


def _roi_enemy(target, needed, from_x, from_y, turns_left):
    d = _dist(from_x, from_y, target['x'], target['y'])
    travel = d / _fleet_speed(needed)
    prod = max(1, target['production'])
    turns_owned = max(1, turns_left - travel)
    # Double weight: gain our production + deny enemy production
    return (prod * turns_owned * 2.0) / (needed + travel * 0.5)


def _angle_to(x1, y1, x2, y2):
    return math.atan2(y2 - y1, x2 - x1)


def _angle_diff(a1, a2):
    d = a1 - a2
    while d > math.pi:
        d -= 2 * math.pi
    while d < -math.pi:
        d += 2 * math.pi
    return d


def _infer_fleet_target(fleet_x, fleet_y, fleet_angle, planets, angular_velocity, fleet_ships,
                        from_planet=None):
    """Infer which planet a fleet is targeting.

    If from_planet is provided and NOT orbiting, use origin-based inference for
    higher accuracy: compute expected angle from origin to target intercept.
    For orbiting source (or no from_planet), use fleet's current position.

    Returns (planet, estimated_arrival_turns) or (None, inf).
    """
    best_p = None
    best_cos = 0.85   # slightly lower threshold to catch orbiting intercepts
    best_arrival = float('inf')

    # Decide reference point
    use_origin = (from_planet is not None and not from_planet['orbiting'])
    ref_x = from_planet['x'] if use_origin else fleet_x
    ref_y = from_planet['y'] if use_origin else fleet_y
    origin_threshold = 0.93 if use_origin else 0.85

    for p in planets:
        if from_planet is not None and p['id'] == from_planet['id']:
            continue

        if use_origin:
            # Compute expected angle from origin to target's intercept
            try:
                tx, ty = _find_intercept(ref_x, ref_y, p['x'], p['y'],
                                         angular_velocity, fleet_ships, p['orbiting'])
                dx, dy = tx - ref_x, ty - ref_y
                d = math.hypot(dx, dy)
                if d < 0.5:
                    continue
                ta = math.atan2(dy, dx)
                diff = _angle_diff(fleet_angle, ta)
                cos_a = math.cos(diff)
                if cos_a > origin_threshold and cos_a > best_cos:
                    best_cos = cos_a
                    best_p = p
                    # Estimate arrival from current fleet position
                    fd = _dist(fleet_x, fleet_y, tx, ty)
                    best_arrival = fd / _fleet_speed(fleet_ships)
            except Exception:
                pass
        else:
            # Fallback: use current fleet position
            dx, dy = p['x'] - fleet_x, p['y'] - fleet_y
            d = math.hypot(dx, dy)
            if d < 0.5:
                continue
            ta = math.atan2(dy, dx)
            diff = _angle_diff(fleet_angle, ta)
            cos_a = math.cos(diff)
            if cos_a > best_cos:
                best_cos = cos_a
                best_p = p
                best_arrival = d / _fleet_speed(fleet_ships)

            # Also check intercept point for orbiting planets
            if p['orbiting']:
                try:
                    tx, ty = _find_intercept(fleet_x, fleet_y, p['x'], p['y'],
                                             angular_velocity, fleet_ships, True)
                    dx2, dy2 = tx - fleet_x, ty - fleet_y
                    d2 = math.hypot(dx2, dy2)
                    if d2 < 0.5:
                        continue
                    ta2 = math.atan2(dy2, dx2)
                    diff2 = _angle_diff(fleet_angle, ta2)
                    cos_a2 = math.cos(diff2)
                    if cos_a2 > best_cos:
                        best_cos = cos_a2
                        best_p = p
                        best_arrival = d2 / _fleet_speed(fleet_ships)
                except Exception:
                    pass

    return best_p, best_arrival


def agent(obs):
    """
    Domination agent: N-way coordination + production ratio awareness + retreat logic.
    """
    if isinstance(obs, dict):
        player = obs.get("player", 0)
        raw_planets = obs.get("planets", [])
        raw_fleets = obs.get("fleets", [])
        angular_velocity = obs.get("angular_velocity", 0.03)
        step = obs.get("step", 0)
    else:
        player = obs.player
        raw_planets = obs.planets
        raw_fleets = getattr(obs, 'fleets', [])
        angular_velocity = obs.angular_velocity
        step = getattr(obs, 'step', 0)

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
        })

    my_planets = [p for p in planets if p['owner'] == player]
    neutrals = [p for p in planets if p['owner'] == -1]
    enemy_planets = [p for p in planets if p['owner'] not in (-1, player)]
    enemy_players = {p['owner'] for p in enemy_planets}

    if not my_planets:
        return []

    turns_left = max(50, GAME_TURNS - step)
    early_game = len(neutrals) > 0
    very_early = step < 8

    # === Production ratio ===
    my_prod = sum(p['production'] for p in my_planets)
    enemy_prod = sum(p['production'] for p in enemy_planets)
    # True production advantage (0 = even, positive = we're ahead)
    prod_ratio = my_prod / max(1, enemy_prod)
    aggressive = prod_ratio >= 1.5 or (not enemy_planets)
    defensive = prod_ratio < 0.7

    # === STEP 1: Parse all fleets ===
    threat_map = {}          # planet_id -> total incoming enemy ships
    enemy_fleets_list = []
    own_fleets_list = []

    planets_by_id = {p['id']: p for p in planets}

    for fleet in raw_fleets:
        if len(fleet) < 7:
            continue
        fleet_owner = int(fleet[1])
        fleet_x, fleet_y = float(fleet[2]), float(fleet[3])
        fleet_angle = float(fleet[4])
        from_pid = int(fleet[5])
        fleet_ships = int(fleet[-1])
        from_planet = planets_by_id.get(from_pid)

        if fleet_owner == player:
            own_fleets_list.append({
                'x': fleet_x, 'y': fleet_y,
                'angle': fleet_angle, 'ships': fleet_ships,
                'from_planet': from_planet,
            })
        elif fleet_owner in enemy_players:
            enemy_fleets_list.append({
                'x': fleet_x, 'y': fleet_y,
                'angle': fleet_angle, 'ships': fleet_ships,
                'owner': fleet_owner,
                'from_planet': from_planet,
            })
            # Classify threat to our planets using improved inference
            threat_p, _ = _infer_fleet_target(
                fleet_x, fleet_y, fleet_angle, my_planets, angular_velocity,
                fleet_ships, from_planet=from_planet
            )
            if threat_p:
                threat_map[threat_p['id']] = threat_map.get(threat_p['id'], 0) + fleet_ships

    # === STEP 2: Enemy fleet -> neutral mapping (for racing logic) ===
    neutral_enemy_info = {}  # neutral_id -> (earliest_arrival, total_ships_incoming)
    for ef in enemy_fleets_list:
        target, arrival = _infer_fleet_target(
            ef['x'], ef['y'], ef['angle'], neutrals, angular_velocity, ef['ships'],
            from_planet=ef.get('from_planet')
        )
        if target is None:
            continue
        nid = target['id']
        prev_arrival, prev_ships = neutral_enemy_info.get(nid, (float('inf'), 0))
        if arrival < prev_arrival:
            neutral_enemy_info[nid] = (arrival, prev_ships + ef['ships'])
        else:
            neutral_enemy_info[nid] = (prev_arrival, prev_ships + ef['ships'])

    # === STEP 3: Own in-flight fleet tracking ===
    neutrals_covered = {}   # neutral_id -> our ships en route
    own_to_enemies = {}     # enemy_planet_id -> our ships en route
    all_planet_list = planets  # for inference

    for of_ in own_fleets_list:
        fp = of_.get('from_planet')
        # Check neutrals first
        target_n, arr_n = _infer_fleet_target(
            of_['x'], of_['y'], of_['angle'], neutrals, angular_velocity, of_['ships'],
            from_planet=fp
        )
        if target_n is not None:
            nid = target_n['id']
            neutrals_covered[nid] = neutrals_covered.get(nid, 0) + of_['ships']
            continue
        # Check enemy planets
        target_e, arr_e = _infer_fleet_target(
            of_['x'], of_['y'], of_['angle'], enemy_planets, angular_velocity, of_['ships'],
            from_planet=fp
        )
        if target_e is not None:
            eid = target_e['id']
            own_to_enemies[eid] = own_to_enemies.get(eid, 0) + of_['ships']

    # === STEP 4: RETREAT LOGIC - abandon doomed planets ===
    # A planet is "doomed" if incoming enemy force > 2.5x our ships there
    doomed_planets = set()
    for mine in my_planets:
        incoming = threat_map.get(mine['id'], 0)
        if incoming > mine['ships'] * 2.5 and incoming > 20:
            doomed_planets.add(mine['id'])

    # === STEP 5: Defense reserves (phase-aware) ===
    available = {}
    for mine in my_planets:
        incoming = threat_map.get(mine['id'], 0)
        if mine['id'] in doomed_planets:
            # Doomed: evacuate all ships (don't waste defending)
            available[mine['id']] = mine['ships']
        elif incoming > 0:
            reserve = max(5, int(incoming * 1.3))
            available[mine['id']] = max(0, mine['ships'] - reserve)
        elif very_early:
            reserve = 2   # minimal reserve very early: maximize expansion speed
        elif early_game:
            reserve = 3
        else:
            if defensive:
                reserve = max(8, mine['production'] * 3)
            else:
                reserve = max(4, mine['production'] * 2)
            available[mine['id']] = max(0, mine['ships'] - reserve)
        if mine['id'] not in available:
            available[mine['id']] = max(0, mine['ships'] - reserve)

    moves = []

    # === STEP 6: MULTI-NEUTRAL FLOOD with tight racing + in-flight awareness ===
    for mine in sorted(my_planets, key=lambda p: p['ships'], reverse=True):
        if mine['id'] in doomed_planets:
            continue
        budget = available[mine['id']]
        if budget <= 0:
            continue

        candidates = []
        for t in neutrals:
            already_incoming = neutrals_covered.get(t['id'], 0)

            # If already fully covered, skip
            if already_incoming >= t['ships'] + 1:
                continue

            # Ships needed (deficit)
            needed = max(1, t['ships'] + 1 - already_incoming)

            # TIGHT RACING: can we send enough ships to race the enemy?
            enemy_arrival, enemy_ships = neutral_enemy_info.get(t['id'], (float('inf'), 0))
            if enemy_arrival < float('inf'):
                my_arrival = _arrival_time(mine['x'], mine['y'], t, needed, angular_velocity)
                if my_arrival > enemy_arrival + 3:
                    # We'd arrive too late with minimum ships
                    # Try sending more ships (faster fleet) to win the race
                    # Binary search for ship count that gets us there in time
                    lo, hi = needed, budget
                    best_ships = None
                    while lo <= hi:
                        mid = (lo + hi) // 2
                        arr = _arrival_time(mine['x'], mine['y'], t, mid, angular_velocity)
                        if arr <= enemy_arrival + 1:
                            best_ships = mid
                            hi = mid - 1
                        else:
                            lo = mid + 1
                    if best_ships is None:
                        continue  # Can't win even with all ships
                    needed = best_ships

            if needed > budget:
                continue

            tx, ty = _find_intercept(
                mine['x'], mine['y'], t['x'], t['y'],
                angular_velocity, needed, t['orbiting']
            )
            if _hits_sun(mine['x'], mine['y'], tx, ty):
                continue

            roi = _roi_neutral(t, needed, mine['x'], mine['y'], turns_left)
            # Boost ROI for high-production planets
            roi *= (max(1, t['production']) ** 0.6)
            # In very early game, boost nearby targets
            if very_early:
                d = _dist(mine['x'], mine['y'], t['x'], t['y'])
                roi *= (50.0 / max(10.0, d))

            candidates.append((roi, t, needed, tx, ty))

        candidates.sort(key=lambda c: c[0], reverse=True)
        for roi, t, needed, tx, ty in candidates:
            if needed > budget:
                continue
            angle = math.atan2(ty - mine['y'], tx - mine['x'])
            moves.append([mine['id'], angle, needed])
            budget -= needed
            neutrals_covered[t['id']] = neutrals_covered.get(t['id'], 0) + needed
        available[mine['id']] = budget

    if not enemy_planets:
        # SURPLUS TRANSFER: Move idle ships toward highest-threat friendly planet
        if not early_game:
            threatened = sorted(my_planets, key=lambda p: -threat_map.get(p['id'], 0))
            if threatened and threat_map.get(threatened[0]['id'], 0) > 0:
                dest = threatened[0]
                for mine in my_planets:
                    if mine['id'] == dest['id']:
                        continue
                    budget = available[mine['id']]
                    if budget <= 5:
                        continue
                    send = budget // 2
                    if send <= 0:
                        continue
                    if not _hits_sun(mine['x'], mine['y'], dest['x'], dest['y']):
                        angle = math.atan2(dest['y'] - mine['y'], dest['x'] - mine['x'])
                        moves.append([mine['id'], angle, send])
                        available[mine['id']] -= send
        return moves

    # === STEP 7: N-WAY COORDINATED ENEMY ATTACKS ===
    # Score all enemy planets by ROI (from centroid of our planets)
    cx = sum(p['x'] for p in my_planets) / len(my_planets)
    cy = sum(p['y'] for p in my_planets) / len(my_planets)

    enemy_scores = []
    for enemy in enemy_planets:
        roi = _roi_enemy(enemy, max(1, enemy['ships']), cx, cy, turns_left)
        enemy_scores.append((roi, enemy))
    enemy_scores.sort(key=lambda x: x[0], reverse=True)

    attacked_enemies = set()

    for _, enemy in enemy_scores:
        if enemy['id'] in attacked_enemies:
            continue

        # Already covered by in-flight?
        already_sent = own_to_enemies.get(enemy['id'], 0)

        # Collect ALL planets with a clear path to enemy
        contributors = []
        for mine in my_planets:
            if mine['id'] in doomed_planets:
                continue
            budget = available[mine['id']]
            if budget <= 0:
                continue
            tx, ty = _find_intercept(
                mine['x'], mine['y'], enemy['x'], enemy['y'],
                angular_velocity, budget, enemy['orbiting']
            )
            if _hits_sun(mine['x'], mine['y'], tx, ty):
                continue
            travel_time = _dist(mine['x'], mine['y'], tx, ty) / _fleet_speed(budget)
            contributors.append({
                'mine': mine, 'send': budget,
                'travel_time': travel_time, 'tx': tx, 'ty': ty,
            })

        if not contributors:
            continue

        contributors.sort(key=lambda c: c['travel_time'])

        # Find smallest winning N-way group:
        # Try adding contributors one by one (fastest first) until we can win.
        best_group = None
        for i in range(1, len(contributors) + 1):
            group = contributors[:i]
            # Reference: fastest fleet's arrival time
            ref_time = group[0]['travel_time']
            # Worst case: enemy has grown to arrival of fastest fleet
            enemy_at_ref = int(enemy['ships'] + enemy['production'] * ref_time) + 1
            # Subtract already in-flight
            need = max(1, enemy_at_ref - already_sent)
            total = sum(c['send'] for c in group)
            if total >= need:
                best_group = group
                best_need = need
                break

        if best_group is None:
            continue

        # Skip if already fully covered
        ref_time = best_group[0]['travel_time']
        enemy_at_ref = int(enemy['ships'] + enemy['production'] * ref_time) + 1
        if already_sent >= enemy_at_ref:
            continue

        # Solo attack: send exact ships needed (faster than full budget)
        if len(best_group) == 1:
            c = best_group[0]
            needed = _ships_needed_enemy(enemy, c['mine']['x'], c['mine']['y'])
            if needed > c['send']:
                continue  # Can't win solo
            # Recompute intercept with actual needed ships
            tx2, ty2 = _find_intercept(
                c['mine']['x'], c['mine']['y'], enemy['x'], enemy['y'],
                angular_velocity, needed, enemy['orbiting']
            )
            if _hits_sun(c['mine']['x'], c['mine']['y'], tx2, ty2):
                continue
            angle = math.atan2(ty2 - c['mine']['y'], tx2 - c['mine']['x'])
            moves.append([c['mine']['id'], angle, needed])
            available[c['mine']['id']] -= needed
            attacked_enemies.add(enemy['id'])
            own_to_enemies[enemy['id']] = own_to_enemies.get(enemy['id'], 0) + needed
            continue

        # Multi-planet coordinated attack: distribute ships proportionally
        # Need exactly best_need ships total (integer)
        best_need_int = int(best_need)
        total_available = sum(c['send'] for c in best_group)

        ships_sent = 0
        attack_moves = []
        for j, c in enumerate(best_group):
            if j == len(best_group) - 1:
                send = best_need_int - ships_sent
            else:
                frac = c['send'] / max(1, total_available)
                send = max(1, int(frac * best_need_int))
            send = min(int(send), c['send'])
            if send <= 0:
                continue
            angle = math.atan2(c['ty'] - c['mine']['y'], c['tx'] - c['mine']['x'])
            attack_moves.append([c['mine']['id'], angle, send])
            available[c['mine']['id']] -= send
            ships_sent += send
            if ships_sent >= best_need_int:
                break

        if ships_sent > 0:
            moves.extend(attack_moves)
            attacked_enemies.add(enemy['id'])

    # === STEP 8: SURPLUS FLOW to frontline ===
    if not early_game:
        # Compute average enemy position
        if enemy_planets:
            ex = sum(e['x'] for e in enemy_planets) / len(enemy_planets)
            ey = sum(e['y'] for e in enemy_planets) / len(enemy_planets)

            # Sort our planets by distance to enemy center
            sorted_planets = sorted(my_planets,
                                    key=lambda p: _dist(p['x'], p['y'], ex, ey))
            frontline = sorted_planets[:max(1, len(sorted_planets)//2)]
            rear = sorted_planets[max(1, len(sorted_planets)//2):]

            for src in rear:
                if src['id'] in doomed_planets:
                    continue
                budget = available.get(src['id'], 0)
                if budget <= 8:
                    continue
                # Send to closest frontline planet
                dest = min(frontline, key=lambda p: _dist(src['x'], src['y'], p['x'], p['y']))
                send = budget // 2
                if send <= 0:
                    continue
                if not _hits_sun(src['x'], src['y'], dest['x'], dest['y']):
                    angle = math.atan2(dest['y'] - src['y'], dest['x'] - src['x'])
                    moves.append([src['id'], angle, send])
                    available[src['id']] -= send

    return moves
