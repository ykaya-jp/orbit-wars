## [CODE]
```python
"""
Orbit Wars Baseline Agent - Distance-Priority Greedy Strategy

A solid baseline agent for the Orbit Wars simulation competition.
Strategy:
  1. Prioritize capturing nearby planets (distance-weighted scoring).
  2. Account for planet orbital motion when targeting moving planets.
  3. Send enough ships to capture (planet.ships + production * travel_time + margin).
  4. Avoid sending to targets already being attacked by our fleets.
  5. Defend frontier planets by keeping a garrison reserve.
  6. Sun avoidance: skip targets where the flight path crosses the sun.
"""

import math

# Game constants
BOARD = 100.0
CENTER_X = 50.0
CENTER_Y = 50.0
SUN_RADIUS = 10.0
SUN_SAFETY = 1.5
MAX_SPEED = 6.0
ROTATION_LIMIT = 50.0
TOTAL_STEPS = 500

# Track which planets our fleets are already targeting
active_fleet_targets = set()


def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def fleet_speed(ships):
    """Calculate fleet speed based on number of ships (matches game engine)."""
    if ships <= 1:
        return 1.0
    ratio = math.log(ships) / math.log(1000.0)
    ratio = max(0.0, min(1.0, ratio))
    return 1.0 + (MAX_SPEED - 1.0) * (ratio ** 1.5)


def point_to_segment_distance(px, py, x1, y1, x2, y2):
    """Distance from point to line segment."""
    dx = x2 - x1
    dy = y2 - y1
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq <= 1e-9:
        return dist(px, py, x1, y1)
    t = ((px - x1) * dx + (py - y1) * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return dist(px, py, proj_x, proj_y)


def path_hits_sun(x1, y1, x2, y2):
    """Check if a flight path crosses the sun."""
    return point_to_segment_distance(CENTER_X, CENTER_Y, x1, y1, x2, y2) < SUN_RADIUS + SUN_SAFETY


def is_static_planet(px, py, radius):
    """Check if a planet is static (doesn't orbit)."""
    orbital_r = dist(px, py, CENTER_X, CENTER_Y)
    return orbital_r + radius >= ROTATION_LIMIT


def predict_planet_pos(planet, initial_planet, angular_velocity, turns):
    """Predict where a planet will be after 'turns' steps."""
    if initial_planet is None:
        return planet[2], planet[3]  # x, y

    init_x, init_y = initial_planet[2], initial_planet[3]
    r = dist(init_x, init_y, CENTER_X, CENTER_Y)
    init_radius = initial_planet[4]

    # Static planets don't move
    if r + init_radius >= ROTATION_LIMIT:
        return planet[2], planet[3]

    cur_angle = math.atan2(planet[3] - CENTER_Y, planet[2] - CENTER_X)
    new_angle = cur_angle + angular_velocity * turns
    return CENTER_X + r * math.cos(new_angle), CENTER_Y + r * math.sin(new_angle)


def estimate_arrival(sx, sy, sr, tx, ty, tr, ships):
    """Estimate the angle and travel time to reach a target planet."""
    angle = math.atan2(ty - sy, tx - sx)

    # Launch from source boundary
    clearance = sr + 0.1
    start_x = sx + math.cos(angle) * clearance
    start_y = sy + math.sin(angle) * clearance

    # Flight distance (boundary to boundary)
    total_dist = max(0.0, dist(sx, sy, tx, ty) - clearance - tr)
    end_x = start_x + math.cos(angle) * total_dist
    end_y = start_y + math.sin(angle) * total_dist

    # Check sun collision
    if path_hits_sun(start_x, start_y, end_x, end_y):
        return None, None

    speed = fleet_speed(max(1, ships))
    turns = max(1, int(math.ceil(total_dist / speed)))
    return angle, turns


def aim_at_moving_target(source, target, ships, initial_by_id, angular_velocity):
    """
    Iteratively predict where a moving target will be and compute intercept.
    """
    sx, sy, sr = source[2], source[3], source[4]
    tx, ty, tr = target[2], target[3], target[4]
    target_id = target[0]
    init = initial_by_id.get(target_id)

    # First estimate: aim directly at current position
    angle, turns = estimate_arrival(sx, sy, sr, tx, ty, tr, ships)
    if angle is None:
        return None, None

    # Iterate to find intercept
    for _ in range(5):
        px, py = predict_planet_pos(target, init, angular_velocity, turns)
        new_angle, new_turns = estimate_arrival(sx, sy, sr, px, py, tr, ships)
        if new_angle is None:
            return None, None
        if abs(new_turns - turns) <= 1:
            return new_angle, new_turns
        turns = new_turns
        angle = new_angle

    return angle, turns


def score_target(target, source, turns, player, remaining_steps):
    """Score a potential target for capture priority."""
    target_owner = target[1]
    target_prod = target[6]
    target_ships = target[5]

    sx, sy = source[2], source[3]
    tx, ty = target[2], target[3]
    distance = dist(sx, sy, tx, ty)

    # Base value: production * remaining turns to produce
    turns_of_production = max(1, remaining_steps - turns)
    value = target_prod * turns_of_production

    # Bonus for enemy planets (take away their production too)
    if target_owner != -1:
        value *= 1.8

    # Bonus for static planets (easier to hit, don't move)
    if is_static_planet(tx, ty, target[4]):
        value *= 1.3

    # Penalty for high-ship targets (cost more to capture)
    cost = target_ships + target_prod * turns + 3  # margin of 3
    if cost <= 0:
        cost = 1

    # Score = value / (cost + distance_penalty)
    score = value / (cost + turns * 0.5 + 1.0)

    return score


def agent(obs, config=None):
    global active_fleet_targets

    player = obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0)
    step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
    raw_planets = obs.get("planets", []) if isinstance(obs, dict) else getattr(obs, "planets", [])
    raw_fleets = obs.get("fleets", []) if isinstance(obs, dict) else getattr(obs, "fleets", [])
    angular_velocity = obs.get("angular_velocity", 0.0) if isinstance(obs, dict) else getattr(obs, "angular_velocity", 0.0)
    raw_initial = obs.get("initial_planets", []) if isinstance(obs, dict) else getattr(obs, "initial_planets", [])

    planets = raw_planets or []
    fleets = raw_fleets or []
    initial_planets = raw_initial or []
    initial_by_id = {}
    for ip in initial_planets:
        initial_by_id[ip[0]] = ip

    my_planets = [p for p in planets if p[1] == player]
    targets = [p for p in planets if p[1] != player]
    remaining_steps = max(1, TOTAL_STEPS - step)

    if not my_planets or not targets:
        return []

    # Update fleet tracking: remove fleet targets that are no longer in-flight
    current_fleet_from_ids = set()
    for f in fleets:
        if f[1] == player:  # our fleets
            current_fleet_from_ids.add(f[5])  # from_planet_id

    # Track which targets already have inbound friendly fleets
    targeted_planets = set()
    for f in fleets:
        if f[1] == player:
            # Estimate which planet this fleet is heading toward
            fx, fy = f[2], f[3]
            f_angle = f[4]
            f_dir_x = math.cos(f_angle)
            f_dir_y = math.sin(f_angle)

            best_target_id = None
            best_dist = 1e9
            for p in planets:
                dx = p[2] - fx
                dy = p[3] - fy
                proj = dx * f_dir_x + dy * f_dir_y
                if proj < 0:
                    continue
                perp_sq = dx * dx + dy * dy - proj * proj
                if perp_sq < p[4] * p[4]:  # within planet radius
                    hit_d = max(0, proj - math.sqrt(max(0, p[4] * p[4] - perp_sq)))
                    if hit_d < best_dist:
                        best_dist = hit_d
                        best_target_id = p[0]

            if best_target_id is not None:
                targeted_planets.add(best_target_id)

    moves = []

    # Calculate garrison reserves for frontier planets
    enemy_planets = [p for p in planets if p[1] not in (-1, player)]
    reserves = {}
    for mp in my_planets:
        min_enemy_dist = 1e9
        for ep in enemy_planets:
            d = dist(mp[2], mp[3], ep[2], ep[3])
            if d < min_enemy_dist:
                min_enemy_dist = d

        # Keep a reserve on frontier planets (close to enemies)
        if min_enemy_dist < 30:
            reserves[mp[0]] = max(6, int(mp[6] * 4))  # production * 4, min 6
        else:
            reserves[mp[0]] = 0

    # Sort my planets by available ships (most ships first) for more impactful moves
    my_planets_sorted = sorted(my_planets, key=lambda p: p[5] - reserves.get(p[0], 0), reverse=True)

    used_targets = set()

    for source in my_planets_sorted:
        src_id = source[0]
        src_ships = source[5]
        reserve = reserves.get(src_id, 0)
        available = src_ships - reserve

        if available <= 2:
            continue

        # Score all available targets
        scored = []
        for target in targets:
            target_id = target[0]

            # Skip if already targeted by us (unless late game with few targets)
            if target_id in targeted_planets and len(targets) > 6:
                continue
            if target_id in used_targets:
                continue

            # Estimate travel
            if is_static_planet(target[2], target[3], target[4]):
                angle, turns = estimate_arrival(
                    source[2], source[3], source[4],
                    target[2], target[3], target[4],
                    available
                )
            else:
                angle, turns = aim_at_moving_target(
                    source, target, available, initial_by_id, angular_velocity
                )

            if angle is None:
                continue

            # Skip if we can't capture before game ends
            if turns >= remaining_steps - 3:
                continue

            # Calculate ships needed
            target_ships = target[5]
            target_prod = target[6]
            ships_on_arrival = target_ships
            if target[1] != -1:  # enemy planet produces ships
                ships_on_arrival += target_prod * turns
            needed = int(ships_on_arrival) + 3  # margin of 3

            if needed > available:
                continue

            # Recalculate with actual send count for correct speed
            if is_static_planet(target[2], target[3], target[4]):
                final_angle, final_turns = estimate_arrival(
                    source[2], source[3], source[4],
                    target[2], target[3], target[4],
                    needed
                )
            else:
                final_angle, final_turns = aim_at_moving_target(
                    source, target, needed, initial_by_id, angular_velocity
                )

            if final_angle is None:
                continue

            # Recheck ships needed with updated travel time
            ships_on_arrival2 = target_ships
            if target[1] != -1:
                ships_on_arrival2 += target_prod * final_turns
            needed = int(ships_on_arrival2) + 3

            if needed > available:
                continue

            s = score_target(target, source, final_turns, player, remaining_steps)
            scored.append((s, target_id, final_angle, needed))

        if not scored:
            continue

        # Pick best target
        scored.sort(reverse=True)
        best_score, best_target_id, best_angle, best_needed = scored[0]

        moves.append([src_id, best_angle, best_needed])
        used_targets.add(best_target_id)

    return moves

```
