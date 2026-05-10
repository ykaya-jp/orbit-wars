## [CODE]
```python
import math
from collections import defaultdict
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet, Fleet

CENTER = (50.0, 50.0)
SUN_RADIUS = 10.0
BOARD_SIZE = 100.0
ROTATION_RADIUS_LIMIT = 50.0
MAX_SPEED = 6.0
EPS = 1e-9


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def norm_angle(a):
    while a <= -math.pi:
        a += 2 * math.pi
    while a > math.pi:
        a -= 2 * math.pi
    return a


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def speed_for_ships(ships, max_speed=MAX_SPEED):
    ships = max(1, int(ships))
    if ships <= 1:
        return 1.0
    return 1.0 + (max_speed - 1.0) * (math.log(ships) / math.log(1000.0)) ** 1.5


def point_segment_distance(px, py, ax, ay, bx, by):
    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay
    ab2 = abx * abx + aby * aby
    if ab2 <= EPS:
        return math.hypot(px - ax, py - ay)
    t = clamp((apx * abx + apy * aby) / ab2, 0.0, 1.0)
    qx = ax + t * abx
    qy = ay + t * aby
    return math.hypot(px - qx, py - qy)


def segment_hits_circle(a, b, c, r):
    return point_segment_distance(c[0], c[1], a[0], a[1], b[0], b[1]) <= r + 1e-6


def in_bounds(x, y):
    return 0.0 <= x <= BOARD_SIZE and 0.0 <= y <= BOARD_SIZE


def rotate_about_center(x, y, angle):
    cx, cy = CENTER
    dx, dy = x - cx, y - cy
    ca, sa = math.cos(angle), math.sin(angle)
    return cx + dx * ca - dy * sa, cy + dx * sa + dy * ca


def build_initial_lookup(obs):
    raw = obs.get("initial_planets", []) if isinstance(obs, dict) else obs.initial_planets
    return {p[0]: Planet(*p) for p in raw}


def comet_position_lookup(obs):
    lookup = {}
    raw_comets = obs.get("comets", []) if isinstance(obs, dict) else getattr(obs, "comets", [])
    for grp in raw_comets or []:
        pids = grp.get("planet_ids", []) if isinstance(grp, dict) else getattr(grp, "planet_ids", [])
        paths = grp.get("paths", []) if isinstance(grp, dict) else getattr(grp, "paths", [])
        idx = grp.get("path_index", 0) if isinstance(grp, dict) else getattr(grp, "path_index", 0)
        for pid, path in zip(pids, paths):
            lookup[pid] = (path, idx)
    return lookup


def predict_planet_position(planet, t, init_lookup, angular_velocity, comet_lookup, comet_ids):
    if planet.id in comet_ids and planet.id in comet_lookup:
        path, idx = comet_lookup[planet.id]
        j = idx + max(0, int(round(t)))
        if j < len(path):
            return float(path[j][0]), float(path[j][1])
        return None
    base = init_lookup.get(planet.id, planet)
    cx, cy = CENTER
    r = math.hypot(base.x - cx, base.y - cy)
    if r + planet.radius < ROTATION_RADIUS_LIMIT:
        return rotate_about_center(base.x, base.y, angular_velocity * t)
    return (planet.x, planet.y)


def launch_point(planet, angle, pos=None):
    x, y = pos if pos is not None else (planet.x, planet.y)
    return (x + math.cos(angle) * (planet.radius + 1e-3), y + math.sin(angle) * (planet.radius + 1e-3))


def travel_time(src_planet, dst_planet, ships, init_lookup, angular_velocity, comet_lookup, comet_ids, horizon=80):
    v = speed_for_ships(ships)
    src_pos = predict_planet_position(src_planet, 0, init_lookup, angular_velocity, comet_lookup, comet_ids)
    if src_pos is None:
        return None
    best = None
    for t in range(1, horizon + 1):
        dst_pos = predict_planet_position(dst_planet, t, init_lookup, angular_velocity, comet_lookup, comet_ids)
        if dst_pos is None:
            continue
        d = dist(src_pos, dst_pos) - src_planet.radius - dst_planet.radius
        if d <= v * t + 0.75:
            best = t
            break
    return best


def safe_shot(src_planet, dst_pos, dst_radius, angle, planets, init_lookup, angular_velocity, comet_lookup, comet_ids, exclude_ids):
    s0 = predict_planet_position(src_planet, 0, init_lookup, angular_velocity, comet_lookup, comet_ids)
    if s0 is None:
        return False
    a = launch_point(src_planet, angle, s0)
    b = (dst_pos[0] - math.cos(angle) * dst_radius * 0.25, dst_pos[1] - math.sin(angle) * dst_radius * 0.25)
    if not in_bounds(*a) or not in_bounds(*b):
        return False
    if segment_hits_circle(a, b, CENTER, SUN_RADIUS + 0.35):
        return False
    for p in planets:
        if p.id in exclude_ids:
            continue
        pp = predict_planet_position(p, 0, init_lookup, angular_velocity, comet_lookup, comet_ids)
        if pp is None:
            continue
        if segment_hits_circle(a, b, pp, max(0.5, p.radius - 0.1)):
            return False
    return True


def estimate_future_garrison(target, eta, player, planets_by_id, my_fleets, enemy_fleets):
    owner = target.owner
    ships = target.ships
    if owner >= 0:
        ships += target.production * eta
    arrivals = []
    for t, owner_id, s in my_fleets.get(target.id, []):
        if t <= eta:
            arrivals.append((owner_id, s))
    for t, owner_id, s in enemy_fleets.get(target.id, []):
        if t <= eta:
            arrivals.append((owner_id, s))
    if not arrivals:
        return owner, ships
    grouped = defaultdict(int)
    for own, s in arrivals:
        grouped[own] += s
    if owner >= 0:
        grouped[owner] += ships
    pairs = sorted(grouped.items(), key=lambda kv: kv[1], reverse=True)
    if len(pairs) == 1:
        return pairs[0][0], pairs[0][1]
    if pairs[0][1] == pairs[1][1]:
        return -1, 0
    top_owner, top_ships = pairs[0]
    second = pairs[1][1]
    return top_owner, top_ships - second


def infer_fleet_targets(planets, fleets, init_lookup, angular_velocity, comet_lookup, comet_ids):
    targets = {}
    for f in fleets:
        vx, vy = math.cos(f.angle), math.sin(f.angle)
        best = None
        best_t = None
        for p in planets:
            if p.id == f.from_planet_id:
                continue
            pos = predict_planet_position(p, 0, init_lookup, angular_velocity, comet_lookup, comet_ids)
            if pos is None:
                continue
            rx, ry = pos[0] - f.x, pos[1] - f.y
            proj = rx * vx + ry * vy
            if proj <= 0:
                continue
            perp = abs(rx * vy - ry * vx)
            if perp <= p.radius + 0.5:
                t = proj / speed_for_ships(f.ships)
                if best_t is None or t < best_t:
                    best_t = t
                    best = p.id
        if best is not None:
            targets[f.id] = (best, max(1, int(round(best_t))))
    return targets


def agent(obs):
    player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
    angular_velocity = obs.get("angular_velocity", 0.0) if isinstance(obs, dict) else getattr(obs, "angular_velocity", 0.0)
    raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
    raw_fleets = obs.get("fleets", []) if isinstance(obs, dict) else obs.fleets
    comet_ids = set(obs.get("comet_planet_ids", []) if isinstance(obs, dict) else getattr(obs, "comet_planet_ids", []))

    planets = [Planet(*p) for p in raw_planets]
    fleets = [Fleet(*f) for f in raw_fleets]
    init_lookup = build_initial_lookup(obs)
    comet_lookup = comet_position_lookup(obs)
    planets_by_id = {p.id: p for p in planets}
    my_planets = [p for p in planets if p.owner == player]
    enemy_planets = [p for p in planets if p.owner >= 0 and p.owner != player]
    neutral_planets = [p for p in planets if p.owner == -1]

    if not my_planets:
        return []

    inferred = infer_fleet_targets(planets, fleets, init_lookup, angular_velocity, comet_lookup, comet_ids)
    inbound_my = defaultdict(list)
    inbound_enemy = defaultdict(list)
    for f in fleets:
        hit = inferred.get(f.id)
        if hit is None:
            continue
        pid, eta = hit
        if f.owner == player:
            inbound_my[pid].append((eta, f.owner, f.ships))
        else:
            inbound_enemy[pid].append((eta, f.owner, f.ships))

    reserved = defaultdict(int)
    targeted = defaultdict(int)
    moves = []
    max_moves = 12 if len(my_planets) < 8 else 18

    my_planets_sorted = sorted(my_planets, key=lambda p: (-p.production, -p.ships, p.id))

    def projected_defense(planet, horizon=18):
        owner, ships = estimate_future_garrison(planet, horizon, player, planets_by_id, inbound_my, inbound_enemy)
        if owner != player:
            return 0
        return ships

    def available_ships(planet):
        keep = max(planet.production * 3, 6)
        if enemy_planets:
            near_enemy = min(math.hypot(planet.x - e.x, planet.y - e.y) for e in enemy_planets)
            if near_enemy < 25:
                keep += 5
        future = projected_defense(planet, 14)
        return max(0, min(planet.ships - reserved[planet.id], future - keep))

    candidates = []
    all_targets = neutral_planets + enemy_planets
    for src in my_planets_sorted:
        avail = available_ships(src)
        if avail <= 0:
            continue
        for dst in all_targets:
            if dst.id == src.id:
                continue
            eta_guess = travel_time(src, dst, max(1, min(avail, 60)), init_lookup, angular_velocity, comet_lookup, comet_ids)
            if eta_guess is None:
                continue
            future_pos = predict_planet_position(dst, eta_guess, init_lookup, angular_velocity, comet_lookup, comet_ids)
            if future_pos is None:
                continue
            angle = math.atan2(future_pos[1] - src.y, future_pos[0] - src.x)
            if not safe_shot(src, future_pos, dst.radius, angle, planets, init_lookup, angular_velocity, comet_lookup, comet_ids, {src.id, dst.id}):
                continue
            own2, ships2 = estimate_future_garrison(dst, eta_guess, player, planets_by_id, inbound_my, inbound_enemy)
            need = ships2 + 1
            if own2 == player:
                continue
            if dst.owner == -1:
                growth_bonus = 6.0 * dst.production
                cost_pen = 0.9 * need
                dist_pen = 0.9 * eta_guess
                comet_bonus = 6.0 if dst.id in comet_ids else 0.0
                widespread = 1.5 if targeted[dst.id] == 0 else -6.0
                score = growth_bonus + comet_bonus + widespread - cost_pen - dist_pen
            else:
                vulnerability = max(0.0, dst.production * 4 + 8 - ships2)
                early_bonus = max(0.0, 14 - eta_guess) * 0.7
                comet_bonus = 3.0 if dst.id in comet_ids else 0.0
                score = vulnerability + early_bonus + comet_bonus - 1.15 * need - 0.75 * eta_guess
            if dst.id in comet_ids:
                score += 2.5
            if targeted[dst.id] > 0:
                score -= 8.0
            candidates.append((score, src.id, dst.id, angle, need, eta_guess, dst.owner))

    candidates.sort(reverse=True)

    used_pairs = set()
    for score, src_id, dst_id, angle, need, eta, owner in candidates:
        if len(moves) >= max_moves:
            break
        if (src_id, dst_id) in used_pairs:
            continue
        src = planets_by_id[src_id]
        dst = planets_by_id[dst_id]
        avail = available_ships(src)
        if avail <= 0:
            continue
        extra_margin = 0
        if owner >= 0:
            extra_margin = 2 + dst.production
        send = need + extra_margin - targeted[dst_id]
        if dst_id in comet_ids:
            send += 1
        if send <= 0 or send > avail:
            continue
        if owner == -1 and send > max(need + 3, int(avail * 0.65)):
            continue
        if owner >= 0 and score < -1.5:
            continue
        if owner == -1 and score < -3.0:
            continue
        moves.append([src_id, angle, int(send)])
        reserved[src_id] += int(send)
        targeted[dst_id] += int(send)
        used_pairs.add((src_id, dst_id))

    if not moves:
        for src in my_planets_sorted:
            avail = available_ships(src)
            if avail <= 0:
                continue
            targets = sorted(neutral_planets, key=lambda p: (p.ships, math.hypot(src.x - p.x, src.y - p.y)))
            for dst in targets:
                eta = travel_time(src, dst, max(1, min(avail, 40)), init_lookup, angular_velocity, comet_lookup, comet_ids)
                if eta is None:
                    continue
                pos = predict_planet_position(dst, eta, init_lookup, angular_velocity, comet_lookup, comet_ids)
                if pos is None:
                    continue
                angle = math.atan2(pos[1] - src.y, pos[0] - src.x)
                if not safe_shot(src, pos, dst.radius, angle, planets, init_lookup, angular_velocity, comet_lookup, comet_ids, {src.id, dst.id}):
                    continue
                own2, ships2 = estimate_future_garrison(dst, eta, player, planets_by_id, inbound_my, inbound_enemy)
                if own2 == -1 and avail >= ships2 + 1:
                    moves.append([src.id, angle, int(ships2 + 1)])
                    break
            if moves:
                break

    return moves
```
