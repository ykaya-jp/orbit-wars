## [CODE]
```python
"""



Design overview
---------------
  1. Exact orbital/comet prediction (uses env's exact formulas)
  2. Per-fleet destination projection via ray-planet intersection
  3. Per-planet forward simulation → arrival-time owner & garrison
  4. Mission types, all scored uniformly:
       EXPAND    capture a neutral
       ATTACK    take an enemy planet (production-adjusted cost)
       SNIPE     arrive at a neutral same turn as an enemy fleet,
                 paying only enough to beat their combined force
       REINFORCE send ships to our threatened planets before worst wave
  5. Sun-aware launch: every path checked with env's point-to-segment
     formula plus a small margin
  6. Endgame: after ENDGAME_TURN, stop speculative expansion and
     consolidate onto our highest-production planets
  7. Per-mission score = expected production / ships spent, with
     retaliation discount (sigmoid of nearest-enemy distance), small
     travel-time penalty, and strong defense priority

"""

import math
from collections import defaultdict

from kaggle_environments.envs.orbit_wars.orbit_wars import Planet, Fleet


# =====================================================================
# CONSTANTS — must mirror environment
# =====================================================================
BOARD_SIZE = 100.0
CENTER = (BOARD_SIZE / 2, BOARD_SIZE / 2)
SUN_RADIUS = 10.0
ROTATION_RADIUS_LIMIT = 50.0
MAX_SHIP_SPEED = 6.0
SPEED_REF = 1000.0
TOTAL_STEPS = 500
SUN_MARGIN = 1.2
PLANET_HIT_MARGIN = 1.0
ENDGAME_TURN = 465
SIM_HORIZON = 80


# =====================================================================
# PERSISTENT STATE (reset at module load → fresh every game)
# =====================================================================
_S = {"step": 0, "init_pos": {}, "omega": 0.0}


# =====================================================================
# GEOMETRY
# =====================================================================
def _hypot(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _point_to_segment(p, v, w):
    vx, vy = v
    wx, wy = w
    l2 = (vx - wx) ** 2 + (vy - wy) ** 2
    if l2 == 0.0:
        return _hypot(p, v)
    t = ((p[0] - vx) * (wx - vx) + (p[1] - vy) * (wy - vy)) / l2
    t = max(0.0, min(1.0, t))
    px = vx + t * (wx - vx)
    py = vy + t * (wy - vy)
    return math.hypot(p[0] - px, p[1] - py)


def _crosses_sun(x1, y1, x2, y2, margin=SUN_MARGIN):
    return _point_to_segment(CENTER, (x1, y1), (x2, y2)) < SUN_RADIUS + margin


def _fleet_speed(ships):
    if ships <= 1:
        return 1.0
    r = math.log(ships) / math.log(SPEED_REF)
    return min(MAX_SHIP_SPEED, 1.0 + (MAX_SHIP_SPEED - 1.0) * max(0.0, r) ** 1.5)


def _is_orbiting(p):
    return _hypot((p.x, p.y), CENTER) + p.radius < ROTATION_RADIUS_LIMIT


# =====================================================================
# POSITION PREDICTION
# =====================================================================
def _predict_orbit(init_xy, delta, omega, cur_step):
    ix, iy = init_xy
    dx, dy = ix - CENTER[0], iy - CENTER[1]
    r = math.hypot(dx, dy)
    if r < 1e-6:
        return (ix, iy)
    th0 = math.atan2(dy, dx)
    th = th0 + omega * (cur_step + delta)
    return (CENTER[0] + r * math.cos(th), CENTER[1] + r * math.sin(th))


def _predict_comet(path, idx, delta):
    fi = int(round(idx + delta))
    if fi < 0 or fi >= len(path):
        return None
    p = path[fi]
    return (float(p[0]), float(p[1]))


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
    t = _hypot(src_xy, (tx, ty)) / v
    for _ in range(max_iter):
        pred = _predict_pos(target, t, ctx)
        if pred is None:
            return None, None, v
        tx, ty = pred
        nt = _hypot(src_xy, (tx, ty)) / v
        if abs(nt - t) < tol:
            t = nt
            break
        t = nt
    return t, (tx, ty), v


# =====================================================================
# FLEET DESTINATION PROJECTION
# =====================================================================
def _fleet_destination(fleet, planets):
    fx, fy = fleet.x, fleet.y
    dx, dy = math.cos(fleet.angle), math.sin(fleet.angle)
    speed = _fleet_speed(fleet.ships)
    best_pid = None
    best_t = float("inf")
    for p in planets:
        if p.id == fleet.from_planet_id:
            continue
        tp = (p.x - fx) * dx + (p.y - fy) * dy
        if tp < 0:
            continue
        cx = fx + tp * dx
        cy = fy + tp * dy
        if math.hypot(cx - p.x, cy - p.y) < p.radius + PLANET_HIT_MARGIN:
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
        dest = _fleet_destination(f, planets)
        if dest is None:
            continue
        pid, tt = dest
        if tt <= TOTAL_STEPS:
            ledger[pid].append((tt, f.owner, f.ships))
    for pid in ledger:
        ledger[pid].sort(key=lambda x: x[0])
    return ledger


# =====================================================================
# FORWARD SIMULATION — per-planet owner/garrison timeline
# =====================================================================
def _simulate_planet(planet, arrivals, player, horizon=SIM_HORIZON):
    """Returns (owner_at, ships_at, deficit, first_enemy_arr).
      deficit: worst garrison gap while owned by us (ships we must reinforce)
      first_enemy_arr: earliest turn a hostile wave lands on this planet (or None)
    """
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

    for T in range(1, horizon + 1):
        if owner != -1:
            ships += prod
        if T in arr_by_turn:
            # track first hostile wave at currently-owned planet
            if planet.owner == player and first_enemy is None:
                for o, _ in arr_by_turn[T]:
                    if o != player and o != -1:
                        first_enemy = T
                        break
            by_owner = defaultdict(int)
            for o, s in arr_by_turn[T]:
                by_owner[o] += s
            so = sorted(by_owner.items(), key=lambda x: -x[1])
            if len(so) >= 2 and so[0][1] == so[1][1]:
                surv_o, surv_s = -1, 0
            elif len(so) >= 2:
                surv_o = so[0][0]
                surv_s = so[0][1] - so[1][1]
            else:
                surv_o = so[0][0]
                surv_s = so[0][1]
            if surv_s > 0:
                if surv_o == owner:
                    ships += surv_s
                else:
                    ships -= surv_s
                    if owner == player and ships < 0:
                        deficit = max(deficit, int(-ships + 1))
                    if ships < 0:
                        owner = surv_o
                        ships = -ships
        owner_at[T] = owner
        ships_at[T] = ships

    return owner_at, ships_at, deficit, first_enemy


# =====================================================================
# CONTEXT
# =====================================================================
def _obs_get(obs, key, default=None):
    if isinstance(obs, dict):
        return obs.get(key, default)
    return getattr(obs, key, default)


def _build_context(obs):
    player      = _obs_get(obs, "player", 0)
    raw_planets = _obs_get(obs, "planets", []) or []
    raw_fleets  = _obs_get(obs, "fleets", []) or []
    omega       = float(_obs_get(obs, "angular_velocity", 0.0) or 0.0)
    raw_initial = _obs_get(obs, "initial_planets", []) or []
    raw_comets  = _obs_get(obs, "comets", []) or []
    comet_ids   = set(_obs_get(obs, "comet_planet_ids", []) or [])
    obs_step    = _obs_get(obs, "step", None)

    planets = [Planet(*p) for p in raw_planets]
    fleets  = [Fleet(*f)  for f in raw_fleets]
    pid2p   = {p.id: p for p in planets}

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

    enemies = [p for p in planets if p.owner != player and p.owner != -1]
    enemy_dist = {}
    for p in planets:
        if not enemies:
            enemy_dist[p.id] = 200.0
        else:
            enemy_dist[p.id] = min(_hypot((p.x, p.y), (e.x, e.y)) for e in enemies)

    ledger = _build_ledger(fleets, planets)

    owner_at, ships_at, deficit, first_enemy = {}, {}, {}, {}
    for p in planets:
        oa, sa, d, fe = _simulate_planet(p, ledger.get(p.id, []), player)
        owner_at[p.id] = oa
        ships_at[p.id] = sa
        deficit[p.id] = d
        first_enemy[p.id] = fe

    return {
        "player": player, "planets": planets, "fleets": fleets, "pid2p": pid2p,
        "omega": omega, "step": cur_step,
        "comet_ids": comet_ids, "comet_data": comet_data,
        "enemy_dist": enemy_dist, "ledger": ledger,
        "owner_at": owner_at, "ships_at": ships_at,
        "deficit": deficit, "first_enemy": first_enemy,
        "remaining": max(1, TOTAL_STEPS - cur_step),
    }


def _state_at_arrival(ctx, target_id, arrival_turn):
    T = min(SIM_HORIZON, max(0, int(math.ceil(arrival_turn))))
    return (ctx["owner_at"][target_id].get(T, ctx["owner_at"][target_id][0]),
            max(0.0, ctx["ships_at"][target_id].get(T, ctx["ships_at"][target_id][0])))


# =====================================================================
# SCORING HELPERS
# =====================================================================
def _value(target, arrival_turn, ctx, is_reinforce=False):
    """Expected production value over remaining lifetime, with retaliation
    discount."""
    remaining = max(1.0, ctx["remaining"] - arrival_turn)
    if target.id in ctx["comet_ids"]:
        cdata = ctx["comet_data"].get(target.id)
        if cdata is not None:
            path, idx = cdata
            life = max(0.0, len(path) - idx - arrival_turn)
        else:
            life = 20.0
        base = target.production * min(life, remaining)
    else:
        base = target.production * remaining
    # sigmoid retaliation discount: d=22 → ~0.5x, d=40+ → ~1x
    d = ctx["enemy_dist"].get(target.id, 100.0)
    discount = 1.0 / (1.0 + math.exp(-(d - 22.0) / 7.0))
    if is_reinforce:
        discount *= 0.9
    return base * discount


def _launchable(mine, ctx):
    """How many ships can we safely send out from `mine` this turn?"""
    danger = 1.0 / (1.0 + math.exp((ctx["enemy_dist"].get(mine.id, 100.0) - 20.0) / 6.0))
    # keep more ships home when enemies are close
    min_keep = int(max(2, mine.ships * (0.05 + 0.25 * danger)))
    return max(0, mine.ships - min_keep - ctx["deficit"].get(mine.id, 0))


# =====================================================================
# MISSION BUILDERS
# =====================================================================
def _build_capture(mine, target, ctx):
    if target.owner == ctx["player"] or target.id == mine.id:
        return None

    probe = max(5, min(int(mine.ships * 0.7), int(target.ships) + 20))
    t_prov, pos_prov, _ = _intercept((mine.x, mine.y), target, probe, ctx)
    if t_prov is None or pos_prov is None or t_prov > ctx["remaining"]:
        return None
    if _crosses_sun(mine.x, mine.y, pos_prov[0], pos_prov[1]):
        return None

    owner_arr, ships_arr = _state_at_arrival(ctx, target.id, t_prov)
    if owner_arr == ctx["player"]:
        return None

    ships_needed = int(math.ceil(ships_arr)) + 1
    launchable = _launchable(mine, ctx)
    if ships_needed > launchable or ships_needed < 1:
        return None

    t_final, pos_final, _ = _intercept((mine.x, mine.y), target, ships_needed, ctx)
    if t_final is None or pos_final is None:
        return None
    if _crosses_sun(mine.x, mine.y, pos_final[0], pos_final[1]):
        return None
    owner_f, ships_f = _state_at_arrival(ctx, target.id, t_final)
    if owner_f == ctx["player"]:
        return None
    ships_needed = max(ships_needed, int(math.ceil(ships_f)) + 1)
    if ships_needed > launchable:
        return None

    mtype = "expand" if target.owner == -1 else "attack"
    value = _value(target, t_final, ctx)
    angle = math.atan2(pos_final[1] - mine.y, pos_final[0] - mine.x)
    return {
        "type": mtype, "target_id": target.id,
        "sources": [(mine.id, ships_needed, angle)],
        "arrival_turn": t_final, "cost": ships_needed, "value": value,
    }


def _build_snipe(mine, target, enemy_arr, ctx):
    if target.owner != -1 or target.id == mine.id:
        return None

    probe = max(10, int(target.ships) + 40)
    t, pos, _ = _intercept((mine.x, mine.y), target, probe, ctx)
    if t is None or pos is None:
        return None
    # must arrive within 1 turn of the enemy wave
    if t > enemy_arr + 1.5 or t < enemy_arr - 1.5:
        return None
    if _crosses_sun(mine.x, mine.y, pos[0], pos[1]):
        return None

    sync = max(t, enemy_arr)
    owner_s, ships_s = _state_at_arrival(ctx, target.id, sync)
    if owner_s == ctx["player"]:
        return None

    need = int(math.ceil(ships_s)) + 1
    launchable = _launchable(mine, ctx)
    if need > launchable or need < 1:
        return None

    t_f, pos_f, _ = _intercept((mine.x, mine.y), target, need, ctx)
    if t_f is None or pos_f is None:
        return None
    if _crosses_sun(mine.x, mine.y, pos_f[0], pos_f[1]):
        return None
    angle = math.atan2(pos_f[1] - mine.y, pos_f[0] - mine.x)
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
    if t is None or pos is None:
        return None
    if t >= crit:
        return None
    if _crosses_sun(ally.x, ally.y, pos[0], pos[1]):
        return None

    ships = min(max(deficit + 2, 3), max(1, ally.ships - 2))
    if ships < 1:
        return None
    angle = math.atan2(pos[1] - ally.y, pos[0] - ally.x)
    value = _value(threatened, t, ctx, is_reinforce=True)
    return {
        "type": "reinforce", "target_id": threatened.id,
        "sources": [(ally.id, ships, angle)],
        "arrival_turn": t, "cost": ships, "value": value,
    }


# =====================================================================
# MISSION SCORING
# =====================================================================
def _score(m, ctx):
    s = m["value"] / (m["cost"] + 5.0)
    s -= 0.015 * m["arrival_turn"]
    if m["type"] == "snipe":
        s *= 1.4
    elif m["type"] == "reinforce":
        s *= 2.0      # defense strongly prioritized
    if m["target_id"] in ctx["comet_ids"]:
        s *= 1.15
    if ctx["step"] >= ENDGAME_TURN and m["type"] != "reinforce":
        s *= 0.25
    return s


# =====================================================================
# ALLOCATION
# =====================================================================
def _allocate(missions, ctx):
    missions.sort(key=lambda m: -m["score"])
    allocated = defaultdict(int)
    targeted = set()
    moves = []
    pid2p = ctx["pid2p"]
    player = ctx["player"]
    for m in missions:
        if m["score"] <= 0.01:
            break
        if m["target_id"] in targeted:
            continue
        ok = True
        for src_id, need, _ in m["sources"]:
            src = pid2p.get(src_id)
            if src is None or src.owner != player:
                ok = False
                break
            free = src.ships - allocated[src_id]
            if free < need:
                ok = False
                break
        if not ok:
            continue
        for src_id, need, angle in m["sources"]:
            moves.append([src_id, float(angle), int(need)])
            allocated[src_id] += need
        targeted.add(m["target_id"])
    return moves


# =====================================================================
# MAIN
# =====================================================================
def agent(obs, config=None):
    ctx = _build_context(obs)
    player = ctx["player"]
    planets = ctx["planets"]
    my_planets = [p for p in planets if p.owner == player]

    if not my_planets:
        _S["step"] = ctx["step"] + 1
        return []

    missions = []

    # --- expand / attack ---
    for mine in my_planets:
        for target in planets:
            m = _build_capture(mine, target, ctx)
            if m is not None:
                missions.append(m)

    # --- snipe ---
    for target in planets:
        if target.owner != -1:
            continue
        enemy_arrs = [t for t, o, _ in ctx["ledger"].get(target.id, [])
                      if o != player and o != -1]
        if not enemy_arrs:
            continue
        ea = min(enemy_arrs)
        for mine in my_planets:
            m = _build_snipe(mine, target, ea, ctx)
            if m is not None:
                missions.append(m)

    # --- reinforce ---
    threatened = [p for p in my_planets if ctx["deficit"].get(p.id, 0) > 0]
    safe = [p for p in my_planets if ctx["deficit"].get(p.id, 0) == 0]
    for t_planet in threatened:
        for ally in sorted(safe, key=lambda a: _hypot((a.x, a.y), (t_planet.x, t_planet.y)))[:3]:
            m = _build_reinforce(ally, t_planet, ctx)
            if m is not None:
                missions.append(m)

    # --- score & commit ---
    for m in missions:
        m["score"] = _score(m, ctx)

    moves = _allocate(missions, ctx)

    _S["step"] = ctx["step"] + 1
    return moves
```
