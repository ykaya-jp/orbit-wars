## [MD]
# Orbit Wars - Galactic Fusion Agent v4

All-notebook fusion: merges the best strategies from 5+ public approaches into a unified adaptive commander.

## Strategy Sources

| Source | Key Features Borrowed |
|--------|----------------------|
| **Tactical Heuristic** (sigmaborov) | Sun-safe waypoint routing, iterative intercept aiming, doomed evacuation, forward funneling, indirect wealth scoring |
| **Elite Macro Physics** (gwongwilliam/lakhindarpal #2 LB) | Adaptive aggression, synchronized swarm attacks, tempo bleeding plays |
| **Forward Sim + Snipe** (keithtyser/aidensong123) | Mission-based scoring, snipe interception, sigmoid retaliation discount |
| **Structured Baseline v6** | Binary-search reserve, binary-search capture, settle_aim re-aim loop, defense missions, static planet bonus |
| **OrbitIQ-LB** | Production-weighted hub selection for evacuation |

## v4 Enhancements over v3

1. **Binary-search `_keep_needed`** - Precise minimum garrison to survive all incoming attacks
2. **Binary-search `_min_ships_to_capture`** - Exact capture requirements via forward simulation
3. **`_settle_aim` re-aim loop** - Iterates aim->ETA->need->re-size until convergent
4. **Defense as scored missions** - Defense competes with captures on same scoring surface
5. **Swarm re-aim** - Re-aims each swarm source with actual send amount after allocation
6. **Static/inner planet bonus** - Static planets get 1.15x value bonus
7. **Proactive defense reserve** - Reserves ships against nearby enemy threats
8. **Hub selection with production weight** - Evacuation targets highest-production safe planet

## [CODE]
```python
%%writefile submission.py
"""
Orbit Wars - Galactic Fusion Agent v4
All-notebook fusion: v3 base + Structured v6 settle_plan/binary-search/defense
+ OrbitIQ inner-bonus + sun-dodging ROI insights.

Key v4 additions over v3:
  1. Binary-search _keep_needed for precise reserve (Structured v6)
  2. Binary-search _min_ships_to_capture for exact capture requirements
  3. _settle_aim: re-aim after send sizing for angle/ETA consistency
  4. Defense as scored missions (compete with captures on same surface)
  5. Swarm re-aim verification after allocation
  6. Static/inner planet identification and scoring bonus
  7. Proactive defense reserve against nearby enemies
"""

import math
from collections import defaultdict
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet, Fleet

# ======================================================================
# CONSTANTS
# ======================================================================
BOARD = 100.0
CX, CY = 50.0, 50.0
SUN_R = 10.0
ROT_LIMIT = 50.0
MAX_SPEED = 6.0
SPEED_REF = 1000.0
TOTAL_STEPS = 500
SUN_MARGIN = 1.3
PLANET_HIT = 1.0
SIM_HORIZON = 80
BASE_ENDGAME_TURN = 460
SYNC_WINDOW_SHORT = 2
SYNC_WINDOW_LONG = 4

# v4: defense mission constants (from Structured v6)
DEFENSE_LOOKAHEAD = 28
DEFENSE_SCORE_FRONTIER_MULT = 1.12
DEFENSE_SHIP_VALUE = 0.55
PROACTIVE_HORIZON = 14
PROACTIVE_RATIO = 0.20

# ======================================================================
# PERSISTENT STATE
# ======================================================================
_S = {"step": 0, "init_pos": {}, "omega": 0.0}


# ======================================================================
# GEOMETRY
# ======================================================================
def _dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def _hypot2(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _pt_seg_dist(p, v, w):
    l2 = (v[0] - w[0]) ** 2 + (v[1] - w[1]) ** 2
    if l2 == 0.0:
        return _hypot2(p, v)
    t = max(0.0, min(1.0, ((p[0] - v[0]) * (w[0] - v[0]) + (p[1] - v[1]) * (w[1] - v[1])) / l2))
    return math.hypot(p[0] - (v[0] + t * (w[0] - v[0])), p[1] - (v[1] + t * (w[1] - v[1])))


def _crosses_sun(x1, y1, x2, y2, margin=SUN_MARGIN):
    return _pt_seg_dist((CX, CY), (x1, y1), (x2, y2)) < SUN_R + margin


def _fleet_speed(ships):
    if ships <= 1:
        return 1.0
    r = math.log(max(1, min(ships, 1000))) / math.log(SPEED_REF)
    return min(MAX_SPEED, 1.0 + (MAX_SPEED - 1.0) * max(0.0, r) ** 1.5)


def _is_orbiting(p):
    return _dist(p.x, p.y, CX, CY) + p.radius < ROT_LIMIT


# v4: static planet identification (from Structured v6)
def _is_static(p):
    return _dist(p.x, p.y, CX, CY) + p.radius >= ROT_LIMIT


# ======================================================================
# SUN-SAFE ANGLE (waypoint search)
# ======================================================================
def _safe_angle(sx, sy, tx, ty):
    if not _crosses_sun(sx, sy, tx, ty):
        return math.atan2(ty - sy, tx - sx), _dist(sx, sy, tx, ty)
    vx, vy = tx - sx, ty - sy
    norm = math.hypot(vx, vy)
    if norm < 1e-9:
        return math.atan2(ty - sy, tx - sx), norm
    nx, ny = -vy / norm, vx / norm
    best = None
    for sign in (1.0, -1.0):
        for mult in (1.8, 2.3, 3.0, 4.0):
            wx = CX + sign * nx * (SUN_R * mult)
            wy = CY + sign * ny * (SUN_R * mult)
            if _crosses_sun(sx, sy, wx, wy, margin=SUN_MARGIN) or \
               _crosses_sun(wx, wy, tx, ty, margin=SUN_MARGIN):
                continue
            d = _dist(sx, sy, wx, wy) + _dist(wx, wy, tx, ty)
            if best is None or d < best[0]:
                best = (d, wx, wy)
            break
    if best is None:
        return math.atan2(ty - sy, tx - sx), _dist(sx, sy, tx, ty) * 1.8
    _, wx, wy = best
    return math.atan2(wy - sy, wx - sx), best[0]


# ======================================================================
# POSITION PREDICTION
# ======================================================================
def _predict_orbit(init_xy, delta, omega, cur_step):
    ix, iy = init_xy
    dx, dy = ix - CX, iy - CY
    r = math.hypot(dx, dy)
    if r < 1e-6:
        return (ix, iy)
    th = math.atan2(dy, dx) + omega * (cur_step + delta)
    return (CX + r * math.cos(th), CY + r * math.sin(th))


def _predict_comet(path, idx, delta):
    fi = int(round(idx + delta))
    if fi < 0 or fi >= len(path):
        return None
    return (float(path[fi][0]), float(path[fi][1]))


def _predict_pos(planet, delta, ctx):
    cdata = ctx["comet_data"].get(planet.id)
    if cdata is not None:
        path, idx = cdata
        return _predict_comet(path, idx, delta)
    if not _is_orbiting(planet):
        return (planet.x, planet.y)
    init = _S["init_pos"].get(planet.id)
    if init is None:
        return (planet.x, planet.y)
    return _predict_orbit((init[0], init[1]), delta, ctx["omega"], ctx["step"])


def _intercept(src_xy, target, ships, ctx, max_iter=5, tol=0.04):
    v = _fleet_speed(ships)
    tx, ty = target.x, target.y
    t = _hypot2(src_xy, (tx, ty)) / max(v, 0.01)
    for _ in range(max_iter):
        pred = _predict_pos(target, t, ctx)
        if pred is None:
            return None, None, v
        tx, ty = pred
        _, d = _safe_angle(src_xy[0], src_xy[1], tx, ty)
        nt = d / max(v, 0.01)
        if abs(nt - t) < tol:
            t = nt
            break
        t = nt
    return t, (tx, ty), v


def _comet_life(planet_id, ctx):
    cdata = ctx["comet_data"].get(planet_id)
    if cdata is None:
        return 999
    path, idx = cdata
    return max(0, len(path) - idx)


def _reaction_est(xy, target):
    return _hypot2(xy, (target.x, target.y)) / max(_fleet_speed(50), 0.01)


# ======================================================================
# SPEED-AWARE FLEET SIZING
# ======================================================================
def _optimal_fleet_size(base_needed, src_ships, target_prod, src_xy, target_xy):
    if base_needed <= 0:
        return max(1, base_needed)
    d = _hypot2(src_xy, target_xy)
    best_send, best_total_cost = base_needed, float("inf")
    base_speed = _fleet_speed(base_needed)
    base_arrival = d / max(base_speed, 0.01)
    for send in range(base_needed, min(base_needed + 40, src_ships + 1), 5):
        speed = _fleet_speed(send)
        arrival_t = d / max(speed, 0.01)
        extra_prod = target_prod * max(0, base_arrival - arrival_t)
        total_cost = send - extra_prod
        if total_cost < best_total_cost:
            best_total_cost = total_cost
            best_send = send
    return min(best_send, src_ships)


# ======================================================================
# FLEET DESTINATION PROJECTION
# ======================================================================
def _fleet_dest(fleet, planets):
    dx, dy = math.cos(fleet.angle), math.sin(fleet.angle)
    speed = _fleet_speed(fleet.ships)
    best_pid, best_t = None, float("inf")
    for p in planets:
        if p.id == fleet.from_planet_id:
            continue
        tp = (p.x - fleet.x) * dx + (p.y - fleet.y) * dy
        if tp < 0:
            continue
        cx = fleet.x + tp * dx
        cy = fleet.y + tp * dy
        if math.hypot(cx - p.x, cy - p.y) < p.radius + PLANET_HIT:
            tt = tp / speed
            if tt < best_t:
                best_t = tt
                best_pid = p.id
    if best_pid is None:
        return None
    return best_pid, best_t


def _build_ledger(fleets, planets):
    ledger = defaultdict(list)
    for f in fleets:
        dest = _fleet_dest(f, planets)
        if dest is None:
            continue
        pid, tt = dest
        if tt <= TOTAL_STEPS:
            ledger[pid].append((tt, f.owner, f.ships))
    for pid in ledger:
        ledger[pid].sort()
    return ledger


# ======================================================================
# FORWARD SIMULATION (per-planet timeline)
# ======================================================================
def _resolve_arrival(owner, garrison, arrivals_at_turn):
    """Resolve same-turn multi-faction combat (from Structured v6)."""
    by_owner = defaultdict(int)
    for o, s in arrivals_at_turn:
        by_owner[o] += s
    if not by_owner:
        return owner, max(0.0, garrison)
    so = sorted(by_owner.items(), key=lambda x: -x[1])
    if len(so) >= 2 and so[0][1] == so[1][1]:
        surv_o, surv_s = -1, 0
    elif len(so) >= 2:
        surv_o, surv_s = so[0][0], so[0][1] - so[1][1]
    else:
        surv_o, surv_s = so[0][0], so[0][1]
    if surv_s <= 0:
        return owner, max(0.0, garrison)
    if surv_o == owner:
        return owner, garrison + surv_s
    garrison -= surv_s
    if garrison < 0:
        return surv_o, -garrison
    return owner, garrison


def _simulate_planet(planet, arrivals, player, horizon=SIM_HORIZON):
    owner = planet.owner
    ships = float(planet.ships)
    prod = planet.production

    arr_by_turn = defaultdict(list)
    for t, o, s in arrivals:
        arr_by_turn[max(1, int(math.ceil(t)))].append((o, s))

    owner_at = {0: owner}
    ships_at = {0: ships}
    deficit = 0
    first_enemy = None
    fall_turn = None

    for T in range(1, horizon + 1):
        if owner != -1:
            ships += prod
        if T in arr_by_turn:
            prev_owner = owner
            if prev_owner == player and first_enemy is None:
                for o, _ in arr_by_turn[T]:
                    if o != player and o != -1:
                        first_enemy = T
                        break
            owner, ships = _resolve_arrival(owner, ships, arr_by_turn[T])
            if prev_owner == player and owner != player and fall_turn is None:
                fall_turn = T
            if prev_owner == player and ships < 0:
                deficit = max(deficit, int(-ships + 1))
        owner_at[T] = owner
        ships_at[T] = max(0.0, ships)

    return owner_at, ships_at, deficit, first_enemy, fall_turn


# v4: Binary-search keep_needed (from Structured v6)
def _keep_needed(planet, arrivals, player, horizon=SIM_HORIZON):
    """Find minimum garrison that keeps planet owned through all incoming attacks."""
    if planet.owner != player:
        return 0, True

    arr_by_turn = defaultdict(list)
    for t, o, s in arrivals:
        arr_by_turn[max(1, int(math.ceil(t)))].append((o, s))

    def survives_with(keep):
        sim_owner = planet.owner
        sim_garrison = float(keep)
        for T in range(1, horizon + 1):
            if sim_owner != -1:
                sim_garrison += planet.production
            if T in arr_by_turn:
                sim_owner, sim_garrison = _resolve_arrival(sim_owner, sim_garrison, arr_by_turn[T])
                if sim_owner != player:
                    return False
        return sim_owner == player

    if survives_with(int(planet.ships)):
        lo, hi = 0, int(planet.ships)
        while lo < hi:
            mid = (lo + hi) // 2
            if survives_with(mid):
                hi = mid
            else:
                lo = mid + 1
        return lo, True
    return int(planet.ships), False


# v4: Binary-search min_ships_to_capture (from Structured v6)
def _min_ships_to_capture(ctx, target_id, arrival_turn, extra_arrivals=None):
    """Binary search for minimum ships needed to own target at arrival_turn."""
    T = min(SIM_HORIZON, max(1, int(math.ceil(arrival_turn))))
    target = ctx["pid2p"][target_id]
    player = ctx["player"]

    base_arrivals = list(ctx["ledger"].get(target_id, []))
    if extra_arrivals:
        base_arrivals = base_arrivals + list(extra_arrivals)

    # Quick check: do we already own it?
    oa, sa, _, _, _ = _simulate_planet(target, base_arrivals, player, T)
    if oa.get(T, target.owner) == player:
        return 0

    ships_at_T = max(0.0, sa.get(T, sa.get(0, 0)))

    def owns_with(n):
        test_arrivals = base_arrivals + [(arrival_turn, player, int(n))]
        test_oa, _, _, _, _ = _simulate_planet(target, test_arrivals, player, T)
        return test_oa.get(T, target.owner) == player

    # Start with simple estimate, then binary search
    hi = max(1, int(math.ceil(ships_at_T)) + 1)
    cap = int(ships_at_T + target.production * T + 50)
    while hi <= cap and not owns_with(hi):
        hi *= 2
    if hi > cap:
        return cap + 1

    lo = 1
    while lo < hi:
        mid = (lo + hi) // 2
        if owns_with(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


# ======================================================================
# CONTEXT BUILDER
# ======================================================================
def _obs_get(obs, key, default=None):
    return obs.get(key, default) if isinstance(obs, dict) else getattr(obs, key, default)


def _build_context(obs):
    player = _obs_get(obs, "player", 0)
    raw_planets = _obs_get(obs, "planets", []) or []
    raw_fleets = _obs_get(obs, "fleets", []) or []
    omega = float(_obs_get(obs, "angular_velocity", 0.0) or 0.0)
    raw_initial = _obs_get(obs, "initial_planets", []) or []
    raw_comets = _obs_get(obs, "comets", []) or []
    comet_ids = set(_obs_get(obs, "comet_planet_ids", []) or [])
    obs_step = _obs_get(obs, "step", None)

    planets = [Planet(*p) for p in raw_planets]
    fleets = [Fleet(*f) for f in raw_fleets]
    pid2p = {p.id: p for p in planets}

    if not _S["init_pos"] and raw_initial:
        for ip in raw_initial:
            _S["init_pos"][ip[0]] = (ip[2], ip[3], ip[4])
    _S["omega"] = omega
    cur_step = int(obs_step) if obs_step is not None else _S["step"]

    comet_data = {}
    for group in raw_comets:
        if not isinstance(group, dict):
            continue
        pids = group.get("planet_ids") or []
        paths = group.get("paths") or []
        idx = int(group.get("path_index", 0) or 0)
        for pid, path in zip(pids, paths):
            comet_data[pid] = (path, idx)

    my_planets = [p for p in planets if p.owner == player]
    enemies = [p for p in planets if p.owner != player and p.owner != -1]

    enemy_dist = {}
    for p in planets:
        if not enemies:
            enemy_dist[p.id] = 200.0
        else:
            enemy_dist[p.id] = min(_hypot2((p.x, p.y), (e.x, e.y)) for e in enemies)

    ledger = _build_ledger(fleets, planets)

    owner_at, ships_at, deficit_map, first_enemy, fall_turn_map = {}, {}, {}, {}, {}
    for p in planets:
        oa, sa, d, fe, ft = _simulate_planet(p, ledger.get(p.id, []), player)
        owner_at[p.id] = oa
        ships_at[p.id] = sa
        deficit_map[p.id] = d
        first_enemy[p.id] = fe
        fall_turn_map[p.id] = ft

    # v4: Binary-search reserve + proactive defense (from Structured v6)
    keep_map = {}
    holds_map = {}
    for p in my_planets:
        kn, holds = _keep_needed(p, ledger.get(p.id, []), player)
        keep_map[p.id] = kn
        holds_map[p.id] = holds

    # v4: Proactive defense reserve against nearby enemies
    proactive_keep = {}
    for p in my_planets:
        best_proactive = 0
        for e in enemies:
            d = _hypot2((p.x, p.y), (e.x, e.y))
            eta_est = d / max(_fleet_speed(max(1, e.ships)), 0.01)
            if eta_est <= PROACTIVE_HORIZON:
                best_proactive = max(best_proactive, int(e.ships * PROACTIVE_RATIO))
        proactive_keep[p.id] = best_proactive

    reserve = {}
    available = {}
    for p in my_planets:
        exact = keep_map.get(p.id, 0)
        proactive = proactive_keep.get(p.id, 0)
        reserve[p.id] = min(int(p.ships), max(exact, proactive))
        available[p.id] = max(0, int(p.ships) - reserve[p.id])

    my_total = sum(p.ships for p in my_planets) + sum(f.ships for f in fleets if f.owner == player)
    enemy_total = sum(p.ships for p in enemies) + \
                  sum(f.ships for f in fleets if f.owner != player and f.owner != -1)
    my_prod = sum(p.production for p in my_planets)
    enemy_prod = sum(p.production for p in enemies)
    domination = (my_total - enemy_total) / max(1, my_total + enemy_total)

    attack_margin = 1.12
    if my_total > enemy_total * 1.3:
        attack_margin += 0.10
    elif my_total < enemy_total * 0.8:
        attack_margin -= 0.05

    remaining = max(1, TOTAL_STEPS - cur_step)

    endgame_turn = BASE_ENDGAME_TURN
    if domination > 0.3 and my_prod > enemy_prod:
        endgame_turn = 475
    elif domination < -0.3:
        endgame_turn = 480

    inbound_friendly = {}
    inbound_enemy = {}
    for pid, entries in ledger.items():
        for _, owner, ships in entries:
            if owner == player:
                inbound_friendly[pid] = inbound_friendly.get(pid, 0) + ships
            elif owner != -1:
                inbound_enemy[pid] = inbound_enemy.get(pid, 0) + ships

    indirect_w = {}
    for p in planets:
        w = 0.0
        for q in planets:
            if q.id == p.id:
                continue
            d = _dist(p.x, p.y, q.x, q.y)
            if d < 1:
                continue
            factor = q.production / (d + 10.0)
            if q.owner == player:
                w += factor * 0.5
            elif q.owner == -1:
                w += factor * 1.0
            else:
                w += factor * 1.3
        indirect_w[p.id] = w

    is_emergency = domination < -0.5 and cur_step > 50

    return {
        "player": player, "planets": planets, "fleets": fleets, "pid2p": pid2p,
        "my_planets": my_planets, "enemies": enemies,
        "omega": omega, "step": cur_step, "remaining": remaining,
        "comet_ids": comet_ids, "comet_data": comet_data,
        "enemy_dist": enemy_dist, "ledger": ledger,
        "owner_at": owner_at, "ships_at": ships_at,
        "deficit": deficit_map, "first_enemy": first_enemy,
        "fall_turn": fall_turn_map,
        "reserve": reserve, "available": available,
        "keep_map": keep_map, "holds_map": holds_map,
        "inbound_friendly": inbound_friendly, "inbound_enemy": inbound_enemy,
        "my_total": my_total, "enemy_total": enemy_total,
        "my_prod": my_prod, "enemy_prod": enemy_prod,
        "domination": domination, "attack_margin": attack_margin,
        "indirect_w": indirect_w,
        "is_early": cur_step < 35, "is_late": remaining < 60,
        "is_very_late": remaining < 25,
        "is_endgame": cur_step >= endgame_turn,
        "endgame_turn": endgame_turn,
        "finishing": domination > 0.35 and my_prod > enemy_prod * 1.3 and cur_step > 100,
        "behind": domination < -0.25,
        "is_emergency": is_emergency,
    }


def _state_at(ctx, target_id, arrival_turn):
    T = min(SIM_HORIZON, max(0, int(math.ceil(arrival_turn))))
    return (ctx["owner_at"][target_id].get(T, ctx["owner_at"][target_id][0]),
            max(0.0, ctx["ships_at"][target_id].get(T, ctx["ships_at"][target_id][0])))


# ======================================================================
# SCORING (sigmoid retaliation + indirect wealth + v4 static/inner bonus)
# ======================================================================
def _value(target, arrival_turn, ctx, is_reinforce=False, is_defense=False):
    remaining = max(1.0, ctx["remaining"] - arrival_turn)
    if target.id in ctx["comet_ids"]:
        life = _comet_life(target.id, ctx)
        remaining = min(remaining, max(0, life - arrival_turn))
        if remaining <= 0:
            return 0.0
    base = target.production * remaining
    iw = ctx["indirect_w"].get(target.id, 0.0)
    base += iw * remaining * 0.15
    if target.owner != ctx["player"] and target.owner != -1:
        base *= 1.9
    # v4: static planet bonus (from Structured v6 - STATIC_NEUTRAL_VALUE_MULT)
    if _is_static(target):
        base *= 1.15
    d = ctx["enemy_dist"].get(target.id, 100.0)
    discount = 1.0 / (1.0 + math.exp(-(d - 22.0) / 7.0))
    if is_reinforce:
        discount *= 0.9
    if is_defense:
        discount = 1.0  # defense value is not discounted by enemy distance
    return base * discount


def _launchable(mine, ctx):
    """Ships available for attack, respecting v4 binary-search reserve."""
    if ctx["is_emergency"]:
        return max(0, mine.ships - 1)
    return ctx["available"].get(mine.id, max(0, mine.ships - 2))


# v4: settle_aim - re-aim after sizing for angle/ETA consistency (from Structured v6)
def _settle_aim(mine, target, send_guess, ctx, max_iter=3):
    """Iterate: aim -> ETA -> re-check need -> re-size -> re-aim until stable."""
    current_send = send_guess
    for _ in range(max_iter):
        t, pos, _ = _intercept((mine.x, mine.y), target, current_send, ctx)
        if t is None or pos is None:
            return None
        if _crosses_sun(mine.x, mine.y, pos[0], pos[1]):
            return None

        need = _min_ships_to_capture(ctx, target.id, t)
        if need <= 0:
            return None

        new_send = _optimal_fleet_size(
            need, current_send, target.production,
            (mine.x, mine.y), (pos[0], pos[1])
        )
        new_send = max(need, new_send)
        if new_send == current_send:
            angle, _ = _safe_angle(mine.x, mine.y, pos[0], pos[1])
            return {"angle": angle, "eta": t, "pos": pos, "need": need, "send": current_send}
        current_send = new_send

    # Final attempt with last value
    t, pos, _ = _intercept((mine.x, mine.y), target, current_send, ctx)
    if t is None or pos is None:
        return None
    if _crosses_sun(mine.x, mine.y, pos[0], pos[1]):
        return None
    need = _min_ships_to_capture(ctx, target.id, t)
    if need <= 0 or need > current_send:
        return None
    angle, _ = _safe_angle(mine.x, mine.y, pos[0], pos[1])
    return {"angle": angle, "eta": t, "pos": pos, "need": need, "send": current_send}


# ======================================================================
# MISSION BUILDERS
# ======================================================================
def _build_capture(mine, target, ctx):
    if target.owner == ctx["player"] or target.id == mine.id:
        return None
    launchable = _launchable(mine, ctx)
    if launchable < 3:
        return None

    # Initial probe
    probe = max(5, min(int(mine.ships * 0.7), int(target.ships) + 20))
    t, pos, _ = _intercept((mine.x, mine.y), target, probe, ctx)
    if t is None or pos is None or t > ctx["remaining"]:
        return None
    if _crosses_sun(mine.x, mine.y, pos[0], pos[1]):
        return None

    owner_arr, ships_arr = _state_at(ctx, target.id, t)
    if owner_arr == ctx["player"]:
        return None

    # v4: use binary-search for precise capture need
    ships_needed = _min_ships_to_capture(ctx, target.id, t)
    if ships_needed <= 0 or ships_needed > launchable:
        return None

    # v4: settle_aim for consistency
    result = _settle_aim(mine, target, ships_needed, ctx)
    if result is None:
        return None

    ships_needed = result["send"]
    t_f = result["eta"]
    pos_f = result["pos"]
    angle = result["angle"]

    if ships_needed > launchable:
        return None
    if target.id in ctx["comet_ids"] and t_f >= _comet_life(target.id, ctx):
        return None

    mtype = "expand" if target.owner == -1 else "attack"
    value = _value(target, t_f, ctx)
    if ctx["is_early"] and mtype == "expand" and ships_needed <= 18:
        value *= 1.5
    if mtype == "expand" and ctx["enemies"]:
        my_react = min((_reaction_est((m.x, m.y), target) for m in ctx["my_planets"]), default=999)
        en_react = min((_reaction_est((e.x, e.y), target) for e in ctx["enemies"]), default=999)
        if my_react <= en_react - 2:
            value *= 1.2
        elif abs(my_react - en_react) <= 2:
            value *= 0.75
    if mtype == "attack" and ctx["finishing"]:
        value *= 1.4
    if target.id in ctx["comet_ids"]:
        life = _comet_life(target.id, ctx)
        if life > 60:
            value *= 1.3
    return {
        "type": mtype, "target_id": target.id,
        "sources": [(mine.id, ships_needed, angle)],
        "arrival_turn": t_f, "cost": ships_needed, "value": value,
    }


def _build_snipe(mine, target, enemy_arr, ctx):
    if target.owner != -1 or target.id == mine.id:
        return None
    launchable = _launchable(mine, ctx)
    if launchable < 3:
        return None
    probe = max(10, int(target.ships) + 40)
    t, pos, _ = _intercept((mine.x, mine.y), target, probe, ctx)
    if t is None or pos is None:
        return None
    if t > enemy_arr + 1.5 or t < enemy_arr - 1.5:
        return None
    if _crosses_sun(mine.x, mine.y, pos[0], pos[1]):
        return None

    sync = max(t, enemy_arr)
    # v4: binary-search capture need at sync turn
    need = _min_ships_to_capture(ctx, target.id, sync)
    if need <= 0 or need > launchable:
        return None

    # v4: re-aim with actual need
    t_f, pos_f, _ = _intercept((mine.x, mine.y), target, need, ctx)
    if t_f is None or pos_f is None:
        return None
    if _crosses_sun(mine.x, mine.y, pos_f[0], pos_f[1]):
        return None
    # Re-verify sync
    if abs(t_f - enemy_arr) > 1.5:
        return None
    angle, _ = _safe_angle(mine.x, mine.y, pos_f[0], pos_f[1])
    value = _value(target, t_f, ctx)
    return {
        "type": "snipe", "target_id": target.id,
        "sources": [(mine.id, need, angle)],
        "arrival_turn": t_f, "cost": need, "value": value,
    }


def _build_reinforce(ally, threatened, ctx):
    if ally.id == threatened.id:
        return None
    deficit = ctx["deficit"].get(threatened.id, 0)
    if deficit <= 0:
        return None
    crit = ctx["first_enemy"].get(threatened.id)
    if crit is None or crit <= 0:
        return None

    probe = max(5, deficit + 3)
    t, pos, _ = _intercept((ally.x, ally.y), threatened, probe, ctx)
    if t is None or pos is None or t >= crit:
        return None
    if _crosses_sun(ally.x, ally.y, pos[0], pos[1]):
        return None

    ships = min(max(deficit + 2, 3), max(1, ally.ships - 2))
    if ships < 1:
        return None
    angle, _ = _safe_angle(ally.x, ally.y, pos[0], pos[1])
    value = _value(threatened, t, ctx, is_reinforce=True)
    return {
        "type": "reinforce", "target_id": threatened.id,
        "sources": [(ally.id, ships, angle)],
        "arrival_turn": t, "cost": ships, "value": value,
    }


# v4: Defense missions (from Structured v6)
def _build_defense(src, threatened, ctx):
    """Build a defense mission to save a threatened planet."""
    if src.id == threatened.id:
        return None
    fall_turn = ctx["fall_turn"].get(threatened.id)
    if fall_turn is None or fall_turn > DEFENSE_LOOKAHEAD:
        return None
    src_avail = _launchable(src, ctx)
    if src_avail < 3:
        return None

    probe = max(3, threatened.production + 3)
    t, pos, _ = _intercept((src.x, src.y), threatened, probe, ctx)
    if t is None or pos is None:
        return None
    if t >= fall_turn:
        return None
    if _crosses_sun(src.x, src.y, pos[0], pos[1]):
        return None

    # How many ships needed to survive at fall_turn?
    need = _min_ships_to_capture(ctx, threatened.id, fall_turn,
                                  extra_arrivals=[(t, ctx["player"], probe)])
    # We want 0 need (we already own it), so we need enough to tip the balance
    # Actually for defense, we send ships that arrive before fall_turn to reinforce
    deficit = ctx["deficit"].get(threatened.id, 0)
    if deficit <= 0:
        return None
    send = min(src_avail, deficit + 3)
    if send < 1:
        return None

    # Re-aim with actual send
    t_f, pos_f, _ = _intercept((src.x, src.y), threatened, send, ctx)
    if t_f is None or pos_f is None or t_f >= fall_turn:
        return None
    if _crosses_sun(src.x, src.y, pos_f[0], pos_f[1]):
        return None

    angle, _ = _safe_angle(src.x, src.y, pos_f[0], pos_f[1])
    saved_turns = max(1, ctx["remaining"] - fall_turn)
    value = threatened.production * saved_turns + max(0, threatened.ships) * DEFENSE_SHIP_VALUE
    # Frontier bonus
    if ctx["enemies"]:
        d_to_enemy = min(_hypot2((threatened.x, threatened.y), (e.x, e.y)) for e in ctx["enemies"])
        if d_to_enemy < 22:
            value *= DEFENSE_SCORE_FRONTIER_MULT
    return {
        "type": "defense", "target_id": threatened.id,
        "sources": [(src.id, send, angle)],
        "arrival_turn": t_f, "cost": send, "value": value,
    }


# ======================================================================
# SYNCHRONIZED SWARM (from Elite - sliding window + v4 re-aim)
# ======================================================================
def _build_swarm(target, front_planets, ctx):
    if target.owner == ctx["player"]:
        return None
    potential = []
    for f in front_planets:
        avail = _launchable(f, ctx)
        if avail <= 0:
            continue
        t, pos, _ = _intercept((f.x, f.y), target, avail, ctx)
        if t is None or pos is None:
            continue
        if _crosses_sun(f.x, f.y, pos[0], pos[1]):
            continue
        angle, _ = _safe_angle(f.x, f.y, pos[0], pos[1])
        potential.append({"id": f.id, "t_a": t, "angle": angle, "ships": avail, "pos": pos})

    if not potential:
        return None
    potential.sort(key=lambda x: x["t_a"])

    best_window, best_ships, best_t = [], 0, potential[0]["t_a"]
    sync_w = SYNC_WINDOW_SHORT if best_t < 15 else (SYNC_WINDOW_LONG if best_t > 40 else 3)
    for anchor in potential:
        window = [p for p in potential if anchor["t_a"] <= p["t_a"] <= anchor["t_a"] + sync_w]
        gathered = sum(p["ships"] for p in window)
        if gathered > best_ships:
            best_ships, best_window, best_t = gathered, window, anchor["t_a"]

    # v4: binary-search for precise need
    needed = _min_ships_to_capture(ctx, target.id, best_t)
    if needed <= 0:
        return None

    if best_ships >= needed:
        sources = []
        gathered = 0
        for p in sorted(best_window, key=lambda x: x["t_a"]):
            amt = min(p["ships"], needed - gathered)
            if amt > 0:
                # v4: re-aim with actual send amount
                src = ctx["pid2p"][p["id"]]
                t_r, pos_r, _ = _intercept((src.x, src.y), target, amt, ctx)
                if t_r is not None and pos_r is not None and not _crosses_sun(src.x, src.y, pos_r[0], pos_r[1]):
                    angle_r, _ = _safe_angle(src.x, src.y, pos_r[0], pos_r[1])
                    sources.append((p["id"], amt, angle_r))
                else:
                    sources.append((p["id"], amt, p["angle"]))
                gathered += amt
            if gathered >= needed:
                break
        value = _value(ctx["pid2p"][target.id], best_t, ctx)
        if ctx["finishing"]:
            value *= 1.3
        return {
            "type": "swarm", "target_id": target.id,
            "sources": sources,
            "arrival_turn": best_t, "cost": gathered, "value": value,
        }

    # Tempo play: 70% threshold
    if best_ships >= 0.7 * needed and not ctx["is_late"]:
        sources = []
        for p in best_window:
            amt = int(p["ships"] * 0.85)
            if amt > 0:
                sources.append((p["id"], amt, p["angle"]))
        total_cost = sum(s for _, s, _ in sources)
        value = _value(ctx["pid2p"][target.id], best_t, ctx) * 0.6
        return {
            "type": "tempo", "target_id": target.id,
            "sources": sources,
            "arrival_turn": best_t, "cost": total_cost, "value": value,
        }

    return None


# ======================================================================
# DOOMED EVACUATION
# ======================================================================
def _evacuation_moves(ctx, allocated):
    moves = []
    player = ctx["player"]
    my_planets = ctx["my_planets"]
    doomed = set()

    for p in my_planets:
        if not ctx["holds_map"].get(p.id, True):
            ft = ctx["fall_turn"].get(p.id)
            if ft is not None and ft <= 24 and ctx["deficit"].get(p.id, 0) >= p.ships:
                doomed.add(p.id)

    safe_planets = [p for p in my_planets if p.id not in doomed and p.id not in allocated]
    for pid in doomed:
        p = ctx["pid2p"][pid]
        avail = p.ships - allocated.get(pid, 0)
        if avail <= 0 or not safe_planets:
            continue
        best_tgt = None
        best_score = -1
        for e in ctx["enemies"]:
            d = _dist(p.x, p.y, e.x, e.y)
            if d > 100:
                continue
            t_est = d / max(_fleet_speed(avail), 0.01)
            if t_est >= ctx["remaining"] - 2:
                continue
            score = e.production * max(1, ctx["remaining"] - t_est) * 0.8 / (t_est + 1)
            if score > best_score:
                best_score = score
                best_tgt = e

        if best_tgt is None:
            nearby = sorted(safe_planets, key=lambda q: _dist(p.x, p.y, q.x, q.y))
            # v4: hub selection with production weight (from OrbitIQ-LB)
            best_tgt = max(nearby[:3], key=lambda q: q.production + q.ships * 0.1) if len(nearby) >= 3 else nearby[0]

        angle, _ = _safe_angle(p.x, p.y, best_tgt.x, best_tgt.y)
        if not _crosses_sun(p.x, p.y, p.x + math.cos(angle) * 3, p.y + math.sin(angle) * 3, margin=0.4):
            moves.append([pid, float(angle), int(avail)])
            allocated[pid] = allocated.get(pid, 0) + avail

    return moves, doomed


# ======================================================================
# FORWARD FUNNEL (production-weighted)
# ======================================================================
def _funnel_moves(ctx, allocated, doomed):
    moves = []
    player = ctx["player"]
    my_planets = ctx["my_planets"]
    enemies = ctx["enemies"]
    neutrals = [p for p in ctx["planets"] if p.owner == -1]

    if not my_planets or len(my_planets) < 2 or ctx["is_very_late"]:
        return moves
    if not enemies and not neutrals:
        return moves

    ref_set = enemies if enemies else neutrals
    front_dist = {p.id: min((_dist(p.x, p.y, e.x, e.y) for e in ref_set), default=200) for p in my_planets}

    front_candidates = sorted(my_planets, key=lambda p: front_dist[p.id])[:3]
    front = max(front_candidates, key=lambda p: p.production) if front_candidates else my_planets[0]

    send_ratio = 0.8 if ctx["finishing"] else 0.6
    if ctx["is_emergency"]:
        send_ratio = 0.9

    for r in sorted(my_planets, key=lambda p: -front_dist[p.id]):
        if r.id == front.id or r.id in doomed:
            continue
        if front_dist[r.id] < front_dist[front.id] * 1.2:
            continue
        avail = max(0, r.ships - allocated.get(r.id, 0))
        if avail < 15:
            continue
        mid = [p for p in my_planets if p.id != r.id and p.id not in doomed
               and front_dist[p.id] < front_dist[r.id] * 0.75]
        if mid:
            mid.sort(key=lambda p: _dist(r.x, r.y, p.x, p.y))
            fwd = max(mid[:3], key=lambda p: p.production) if len(mid) >= 3 else mid[0]
        else:
            fwd = front
        if fwd.id == r.id:
            continue
        send = int(avail * send_ratio)
        if send < 10:
            continue
        t, pos, _ = _intercept((r.x, r.y), fwd, send, ctx)
        if t is None or pos is None or t > 40:
            continue
        angle, _ = _safe_angle(r.x, r.y, pos[0], pos[1])
        if _crosses_sun(r.x, r.y, r.x + math.cos(angle) * 3, r.y + math.sin(angle) * 3, margin=0.4):
            continue
        moves.append([r.id, float(angle), int(send)])
        allocated[r.id] = allocated.get(r.id, 0) + send

    return moves


# ======================================================================
# MISSION SCORING
# ======================================================================
def _score(m, ctx):
    s = m["value"] / (m["cost"] + 1.0)
    s -= 0.015 * m["arrival_turn"]
    if m["type"] == "snipe":
        s *= 1.4
    elif m["type"] in ("reinforce", "defense"):
        s *= 2.0
    elif m["type"] == "swarm":
        s *= 1.2
    elif m["type"] == "tempo":
        s *= 0.8
    if m["target_id"] in ctx["comet_ids"]:
        s *= 1.15
    if ctx["is_endgame"] and m["type"] not in ("reinforce", "defense", "swarm"):
        s *= 0.25
    if ctx["is_emergency"] and m["type"] == "attack":
        s *= 1.5
    # v4: static target bonus in scoring (from Structured v6)
    if _is_static(ctx["pid2p"][m["target_id"]]):
        s *= 1.15
    return s


# ======================================================================
# ALLOCATION
# ======================================================================
def _allocate(missions, ctx, allocated):
    missions.sort(key=lambda m: -m["score"])
    target_committed = {}
    targeted = set()
    moves = []
    pid2p = ctx["pid2p"]
    player = ctx["player"]

    for m in missions:
        if m["score"] <= 0.01:
            break
        tid = m["target_id"]
        if m["type"] in ("reinforce", "defense", "swarm", "tempo"):
            if tid in targeted:
                continue
            ok = True
            for src_id, need, _ in m["sources"]:
                src = pid2p.get(src_id)
                if src is None or src.owner != player:
                    ok = False
                    break
                free = src.ships - allocated.get(src_id, 0)
                if free < need:
                    ok = False
                    break
            if not ok:
                continue
            for src_id, need, angle in m["sources"]:
                moves.append([src_id, float(angle), int(need)])
                allocated[src_id] = allocated.get(src_id, 0) + need
            targeted.add(tid)
            continue

        already = target_committed.get(tid, 0)
        total_needed = m["cost"]
        missing = max(0, total_needed - already)
        if missing <= 0:
            targeted.add(tid)
            continue

        for src_id, need, angle in m["sources"]:
            src = pid2p.get(src_id)
            if src is None or src.owner != player:
                continue
            free = src.ships - allocated.get(src_id, 0)
            send = min(free, missing)
            if send < 1:
                continue
            moves.append([src_id, float(angle), int(send)])
            allocated[src_id] = allocated.get(src_id, 0) + send
            target_committed[tid] = target_committed.get(tid, 0) + send
            missing -= send
            if missing <= 0:
                targeted.add(tid)
                break

    return moves, targeted


# ======================================================================
# SUPPLEMENT ATTACKS (cooperative second pass)
# ======================================================================
def _supplement_attacks(ctx, allocated, targeted):
    moves = []
    player = ctx["player"]

    for target in ctx["planets"]:
        if target.owner == player or target.id in targeted:
            continue
        inbound = sum(s for _, o, s in ctx["ledger"].get(target.id, []) if o == player)
        if inbound == 0:
            continue
        friend_etas = [t for t, o, _ in ctx["ledger"].get(target.id, []) if o == player]
        if not friend_etas:
            continue
        ref_eta = min(friend_etas)
        # v4: binary-search need
        needed = _min_ships_to_capture(ctx, target.id, ref_eta)
        if needed <= 0:
            continue
        missing = needed - inbound
        if missing <= 0 or missing > 100:
            continue
        for mine in sorted(ctx["my_planets"], key=lambda p: _hypot2((p.x, p.y), (target.x, target.y))):
            avail = mine.ships - allocated.get(mine.id, 0)
            if avail < missing or avail < 5:
                continue
            t, pos, _ = _intercept((mine.x, mine.y), target, missing, ctx)
            if t is None or pos is None or t > ctx["remaining"]:
                continue
            if _crosses_sun(mine.x, mine.y, pos[0], pos[1]):
                continue
            angle, _ = _safe_angle(mine.x, mine.y, pos[0], pos[1])
            moves.append([mine.id, float(angle), int(missing)])
            allocated[mine.id] = allocated.get(mine.id, 0) + missing
            targeted.add(target.id)
            break

    return moves


# ======================================================================
# FINISHING CLEANUP (target weakest enemies)
# ======================================================================
def _finishing_cleanup(ctx, allocated):
    moves = []
    if not ctx["finishing"] or not ctx["enemies"]:
        return moves

    player = ctx["player"]
    weak_enemies = sorted(ctx["enemies"], key=lambda p: p.ships + p.production * 10)

    for src in ctx["my_planets"]:
        avail = src.ships - allocated.get(src.id, 0)
        if avail < 25:
            continue
        for tgt in weak_enemies[:3]:
            d = _dist(src.x, src.y, tgt.x, tgt.y)
            if d > 120:
                continue
            t, pos, _ = _intercept((src.x, src.y), tgt, avail, ctx)
            if t is None or pos is None or t > ctx["remaining"] - 5:
                continue
            if _crosses_sun(src.x, src.y, pos[0], pos[1]):
                continue
            owner_arr, ships_arr = _state_at(ctx, tgt.id, t)
            if owner_arr == player:
                continue
            needed = _min_ships_to_capture(ctx, tgt.id, t)
            if needed <= 0:
                continue
            inbound = sum(s for _, o, s in ctx["ledger"].get(tgt.id, []) if o == player)
            missing = max(0, needed - inbound)
            if missing <= 0:
                continue
            send = min(avail, missing + 5)
            if send < 10:
                continue
            angle, _ = _safe_angle(src.x, src.y, pos[0], pos[1])
            moves.append([src.id, float(angle), int(send)])
            allocated[src.id] = allocated.get(src.id, 0) + send
            break

    return moves


# ======================================================================
# MAIN AGENT
# ======================================================================
def agent(obs, config=None):
    ctx = _build_context(obs)
    player = ctx["player"]
    planets = ctx["planets"]
    my_planets = ctx["my_planets"]

    if not my_planets:
        _S["step"] = ctx["step"] + 1
        return []

    allocated = {}
    all_moves = []

    # Phase 1: Doomed evacuation
    evac_moves, doomed = _evacuation_moves(ctx, allocated)
    all_moves.extend(evac_moves)

    # Phase 2: Build missions
    missions = []

    # v4: Defense missions (from Structured v6)
    for threatened in my_planets:
        ft = ctx["fall_turn"].get(threatened.id)
        if ft is None or ft > DEFENSE_LOOKAHEAD:
            continue
        if threatened.id in doomed:
            continue
        for src in my_planets:
            m = _build_defense(src, threatened, ctx)
            if m is not None:
                missions.append(m)

    # Capture missions
    for mine in my_planets:
        if mine.id in doomed:
            continue
        for target in planets:
            m = _build_capture(mine, target, ctx)
            if m is not None:
                missions.append(m)

    # Snipe missions
    for target in planets:
        if target.owner != -1:
            continue
        enemy_arrs = [t for t, o, _ in ctx["ledger"].get(target.id, [])
                      if o != player and o != -1]
        if not enemy_arrs:
            continue
        ea = min(enemy_arrs)
        for mine in my_planets:
            if mine.id in doomed:
                continue
            m = _build_snipe(mine, target, ea, ctx)
            if m is not None:
                missions.append(m)

    # Reinforce missions
    threatened = [p for p in my_planets if ctx["deficit"].get(p.id, 0) > 0 and p.id not in doomed]
    safe = [p for p in my_planets if ctx["deficit"].get(p.id, 0) == 0 and p.id not in doomed]
    for t_planet in threatened:
        for ally in sorted(safe, key=lambda a: _hypot2((a.x, a.y), (t_planet.x, t_planet.y)))[:3]:
            m = _build_reinforce(ally, t_planet, ctx)
            if m is not None:
                missions.append(m)

    # Synchronized swarm
    front = [p for p in my_planets if p.id not in doomed
             and ctx["enemy_dist"].get(p.id, 200) < 50]
    if not front:
        front = [p for p in my_planets if p.id not in doomed]
    for target in planets:
        if target.owner == player:
            continue
        if target.owner == -1 and target.production < 3:
            continue
        m = _build_swarm(target, front, ctx)
        if m is not None:
            missions.append(m)

    # Score all missions
    for m in missions:
        m["score"] = _score(m, ctx)

    # Allocate missions
    mission_moves, targeted = _allocate(missions, ctx, allocated)
    all_moves.extend(mission_moves)

    # Phase 2b: Supplement cooperative attacks
    supplement_moves = _supplement_attacks(ctx, allocated, targeted)
    all_moves.extend(supplement_moves)

    # Phase 2c: Finishing cleanup
    cleanup_moves = _finishing_cleanup(ctx, allocated)
    all_moves.extend(cleanup_moves)

    # Phase 3: Forward funnel
    funnel_moves = _funnel_moves(ctx, allocated, doomed)
    all_moves.extend(funnel_moves)

    # Deduplicate & validate
    dedup = {}
    for sid, ang, sh in all_moves:
        key = (sid, round(ang, 4))
        if key in dedup:
            dedup[key] = (sid, ang, dedup[key][2] + sh)
        else:
            dedup[key] = (sid, ang, sh)

    final_moves = []
    used = {}
    for sid, ang, sh in dedup.values():
        src = ctx["pid2p"].get(sid)
        if src is None:
            continue
        max_ok = src.ships - used.get(sid, 0)
        send = min(sh, max_ok)
        if send >= 1:
            final_moves.append([sid, float(ang), int(send)])
            used[sid] = used.get(sid, 0) + send

    _S["step"] = ctx["step"] + 1
    return final_moves
```

## [MD]
## Execution Pipeline

```
Turn N:
  1. Build context (parse obs, predict positions, simulate planet futures)
     - Binary-search reserve per planet (keep_needed)
     - Proactive defense reserve against nearby enemies
  2. Phase 1: Evacuate doomed planets (attack enemy or retreat to best hub)
  3. Phase 2: Generate missions -> Score -> Greedy allocate
     - Defense (binary-search: save threatened planets before fall)
     - Capture (expand neutral / attack enemy, with settle_aim)
     - Snipe (intercept enemy fleet at neutral)
     - Reinforce (send ships to planets with deficit)
     - Swarm (multi-source synchronized attack, with re-aim)
  4. Phase 2b: Supplement cooperative attacks
  5. Phase 2c: Finishing cleanup (target weakest enemies)
  6. Phase 3: Forward funnel (rear -> front logistics)
  7. Deduplicate & validate all moves
```

## [MD]
## Credits

Built on the shoulders of these excellent public notebooks:
- [Orbit Wars 2026: Tactical Heuristic](https://www.kaggle.com/code/sigmaborov/orbit-wars-2026-tactical-heuristic) by sigmaborov
- [Orbit Wars: Elite Macro Physics Agent](https://www.kaggle.com/code/gwongwilliam/orbit-wars-elite-macro-physics-agent) by gwongwilliam / lakhindarpal
- [Orbit Wars: Forward Sim + Snipe Missions](https://www.kaggle.com/code/keithtyser/orbit-wars-forward-sim-snipe-missions) by keithtyser / aidensong123
- [Structured Baseline for Orbit Wars](https://www.kaggle.com/code/structured-baseline-for-orbit-wars-modules) (modules concept)
- [OrbitIQ Baseline](https://www.kaggle.com/code/orbit-wars-orbitiq-baseline-lb-529-7) (hub selection)

If you find this useful, please upvote! Good luck in the competition!
