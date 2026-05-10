## [CODE]
```python
%%capture
!pip install --upgrade "kaggle-environments>=1.28.0"
```

## [CODE]
```python
import math
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet, Fleet

BOARD = 100.0
CENTER_X, CENTER_Y = 50.0, 50.0
SUN_R = 10.0
MAX_SPEED = 6.0
SUN_SAFETY = 1.5
ROTATION_LIMIT = 50.0

def dist_heuristic(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)

def fleet_speed_heuristic(ships):
    if ships <= 1:
        return 1.0
    ratio = math.log(ships) / math.log(1000.0)
    ratio = max(0.0, min(1.0, ratio))
    return 1.0 + (MAX_SPEED - 1.0) * (ratio ** 1.5)

def segment_hits_sun_heuristic(x1, y1, x2, y2, safety=SUN_SAFETY):
    r = SUN_R + safety
    dx, dy = x2 - x1, y2 - y1
    fx, fy = x1 - CENTER_X, y1 - CENTER_Y
    a = dx * dx + dy * dy
    if a < 1e-9:
        return dist_heuristic(x1, y1, CENTER_X, CENTER_Y) < r
    b = 2 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - r * r
    disc = b * b - 4 * a * c
    if disc < 0:
        return False
    disc = math.sqrt(disc)
    t1 = (-b - disc) / (2 * a)
    t2 = (-b + disc) / (2 * a)
    return (0 <= t1 <= 1) or (0 <= t2 <= 1)

def safe_angle_and_distance_heuristic(sx, sy, tx, ty):
    if not segment_hits_sun_heuristic(sx, sy, tx, ty):
        return math.atan2(ty - sy, tx - sx), dist_heuristic(sx, sy, tx, ty)

    vx, vy = tx - sx, ty - sy
    norm = math.hypot(vx, vy)
    if norm < 1e-9:
        return math.atan2(ty - sy, tx - sx), dist_heuristic(sx, sy, tx, ty)
    nx, ny = -vy / norm, vx / norm
    best = None
    for sign in (1.0, -1.0):
        wx = CENTER_X + sign * nx * (SUN_R * 2)
        wy = CENTER_Y + sign * ny * (SUN_R * 2)
        if segment_hits_sun_heuristic(sx, sy, wx, wy) or segment_hits_sun_heuristic(wx, wy, tx, ty):
            wx = CENTER_X + sign * nx * (SUN_R * 3)
            wy = CENTER_Y + sign * ny * (SUN_R * 3)
            if segment_hits_sun_heuristic(sx, sy, wx, wy) or segment_hits_sun_heuristic(wx, wy, tx, ty):
                continue
        d = dist_heuristic(sx, sy, wx, wy) + dist_heuristic(wx, wy, tx, ty)
        if best is None or d < best[0]:
            best = (d, wx, wy)
    if best is None:
        ang = math.atan2(ty - sy, tx - sx)
        return ang, dist_heuristic(sx, sy, tx, ty) * 1.5
    _, wx, wy = best
    ang = math.atan2(wy - sy, wx - sx)
    return ang, best[0]

def predict_planet_position_heuristic(planet, initial_planets_by_id, angular_velocity, turns):
    init = initial_planets_by_id.get(planet.id)
    if init is None:
        return planet.x, planet.y
    ix, iy = init.x, init.y
    orbital_r = dist_heuristic(ix, iy, CENTER_X, CENTER_Y)
    if orbital_r + init.radius >= ROTATION_LIMIT:
        return planet.x, planet.y
    cur_ang = math.atan2(planet.y - CENTER_Y, planet.x - CENTER_X)
    new_ang = cur_ang + angular_velocity * turns
    return (CENTER_X + orbital_r * math.cos(new_ang),
            CENTER_Y + orbital_r * math.sin(new_ang))

def predict_comet_position_heuristic(planet_id, comets, turns):
    for g in comets:
        pids = g.get("planet_ids", [])
        if planet_id not in pids:
            continue
        idx = pids.index(planet_id)
        paths = g.get("paths", [])
        path_index = g.get("path_index", 0)
        if idx >= len(paths):
            return None
        path = paths[idx]
        future_idx = path_index + int(turns)
        if 0 <= future_idx < len(path):
            return path[future_idx][0], path[future_idx][1]
        return None
    return None

def estimate_arrival_heuristic(src_x, src_y, tgt_x, tgt_y, ships):
    angle, d = safe_angle_and_distance_heuristic(src_x, src_y, tgt_x, tgt_y)
    sp = fleet_speed_heuristic(ships)
    turns = d / sp
    return angle, max(1, int(math.ceil(turns)))

def aim_with_prediction_heuristic(src, target, ships, initial_by_id, ang_vel,
                                  comets, comet_ids_set):
    tx, ty = target.x, target.y
    for _ in range(4):
        angle, turns = estimate_arrival_heuristic(src.x, src.y, tx, ty, ships)
        if target.id in comet_ids_set:
            pos = predict_comet_position_heuristic(target.id, comets, turns)
            if pos is None:
                return None
            ntx, nty = pos
        else:
            ntx, nty = predict_planet_position_heuristic(target, initial_by_id, ang_vel, turns)
        if abs(ntx - tx) < 0.5 and abs(nty - ty) < 0.5:
            tx, ty = ntx, nty
            break
        tx, ty = ntx, nty
    angle, turns = estimate_arrival_heuristic(src.x, src.y, tx, ty, ships)
    return angle, turns, tx, ty

def incoming_threats_heuristic(planet, fleets, player, initial_by_id, ang_vel,
                                comets, comet_ids_set):
    arrivals = []
    for f in fleets:
        fvx = math.cos(f.angle)
        fvy = math.sin(f.angle)
        dx = planet.x - f.x
        dy = planet.y - f.y
        proj = dx * fvx + dy * fvy
        if proj <= 0:
            continue
        perp = abs(dx * fvy - dy * fvx)
        if perp > planet.radius + 1.5:
            continue
        sp = fleet_speed_heuristic(f.ships)
        turns = proj / sp
        if turns > 60:
            continue
        arrivals.append((int(math.ceil(turns)), f.owner, int(f.ships)))
    return arrivals

def net_defense_needed_heuristic(planet, arrivals, player):
    if not arrivals:
        return 0
    arrivals = sorted(arrivals, key=lambda a: a[0])
    garrison = planet.ships
    prod = planet.production if planet.owner == player else 0
    last_t = 0
    deficit = 0
    for t, owner, ships in arrivals:
        garrison += prod * (t - last_t)
        last_t = t
        if owner == player:
            garrison += ships
        else:
            garrison -= ships
            if garrison < 0:
                deficit = max(deficit, -garrison)
    return deficit
```

## [CODE]
```python
def heuristic_agent(obs):
    """
    Kaggle environment entry point.
    Internal logic renamed to include _heuristic.
    """
    if isinstance(obs, dict):
        get = obs.get
    else:
        get = lambda k, d=None: getattr(obs, k, d)

    player = get("player", 0)
    raw_planets = get("planets", []) or []
    raw_fleets = get("fleets", []) or []
    ang_vel = get("angular_velocity", 0.0) or 0.0
    raw_init = get("initial_planets", []) or []
    comets = get("comets", []) or []
    comet_ids = set(get("comet_planet_ids", []) or [])

    planets = [Planet(*p) for p in raw_planets]
    fleets = [Fleet(*f) for f in raw_fleets]
    initial_by_id = {Planet(*p).id: Planet(*p) for p in raw_init}

    my_planets = [p for p in planets if p.owner == player]
    if not my_planets:
        return []

    reserve = {p.id: 0 for p in my_planets}
    for p in my_planets:
        arrivals = incoming_threats_heuristic(p, fleets, player, initial_by_id, ang_vel,
                                               comets, comet_ids)
        need = net_defense_needed_heuristic(p, arrivals, player)
        reserve[p.id] = min(p.ships, need)

    available = {p.id: max(0, p.ships - reserve[p.id]) for p in my_planets}

    inbound_friendly = {}
    inbound_enemy = {}
    for f in fleets:
        for p in planets:
            fvx, fvy = math.cos(f.angle), math.sin(f.angle)
            dx, dy = p.x - f.x, p.y - f.y
            proj = dx * fvx + dy * fvy
            if proj <= 0:
                continue
            perp = abs(dx * fvy - dy * fvx)
            if perp > p.radius + 1.2:
                continue
            if f.owner == player:
                inbound_friendly[p.id] = inbound_friendly.get(p.id, 0) + int(f.ships)
            else:
                inbound_enemy[p.id] = inbound_enemy.get(p.id, 0) + int(f.ships)
            break

    moves = []

    def target_score_heuristic(src, tgt, ships_to_send, arrival_turns):
        prod = tgt.production
        if tgt.owner == -1:
            defender = tgt.ships
        else:
            defender = tgt.ships + prod * arrival_turns
        defender += inbound_enemy.get(tgt.id, 0) if tgt.owner == player else 0
        defender -= inbound_friendly.get(tgt.id, 0) if tgt.owner != player else 0
        defender = max(0, defender)

        needed = defender + 1
        if ships_to_send < needed:
            return -1.0, needed
        value = prod * 60.0
        if tgt.id in comet_ids:
            value = prod * 25.0
        if tgt.owner != player and tgt.owner != -1:
            value += prod * 40.0
        cost = ships_to_send + arrival_turns * 0.8
        score = value / (cost + 1.0)
        return score, needed

    candidates = []
    for src in my_planets:
        if available[src.id] <= 0:
            continue
        for tgt in planets:
            if tgt.id == src.id:
                continue
            if tgt.owner == player:
                continue
            d0 = dist_heuristic(src.x, src.y, tgt.x, tgt.y)
            if d0 > 140:
                continue

            _, turns0 = estimate_arrival_heuristic(src.x, src.y, tgt.x, tgt.y, max(10, available[src.id]))
            est_defender = tgt.ships + (tgt.production * turns0 if tgt.owner != -1 else 0)
            est_needed = est_defender + 1 - inbound_friendly.get(tgt.id, 0) \
                         if tgt.owner != player else est_defender + 1
            est_needed = max(1, est_needed)
            if est_needed > available[src.id]:
                continue

            aim = aim_with_prediction_heuristic(src, tgt, est_needed, initial_by_id,
                                                 ang_vel, comets, comet_ids)
            if aim is None:
                continue
            angle, turns, _, _ = aim

            if tgt.owner == -1:
                defender = tgt.ships
            else:
                defender = tgt.ships + tgt.production * turns
            defender -= inbound_friendly.get(tgt.id, 0)
            defender = max(0, defender)
            ships_needed = defender + 1
            if ships_needed > available[src.id]:
                continue

            if segment_hits_sun_heuristic(src.x, src.y,
                                           src.x + math.cos(angle) * 5,
                                           src.y + math.sin(angle) * 5,
                                           safety=0.5):
                continue

            score, _ = target_score_heuristic(src, tgt, ships_needed, turns)
            if score <= 0:
                continue
            candidates.append((score, src.id, tgt.id, angle, ships_needed))

    candidates.sort(key=lambda x: -x[0])
    taken_targets = set()
    for score, sid, tid, angle, ships in candidates:
        if tid in taken_targets:
            continue
        if available[sid] < ships:
            continue
        moves.append([sid, float(angle), int(ships)])
        available[sid] -= ships
        taken_targets.add(tid)
        inbound_friendly[tid] = inbound_friendly.get(tid, 0) + ships

    enemy_planets = [p for p in planets if p.owner != player and p.owner != -1]
    if enemy_planets and len(my_planets) > 1:
        front_dist = {}
        for mp in my_planets:
            front_dist[mp.id] = min(dist_heuristic(mp.x, mp.y, e.x, e.y) for e in enemy_planets)
        rear = sorted(my_planets, key=lambda p: -front_dist[p.id])
        front = min(my_planets, key=lambda p: front_dist[p.id])
        for r in rear:
            if r.id == front.id:
                continue
            if available[r.id] < 15:
                continue
            send = int(available[r.id] * 0.6)
            if send < 10:
                continue
            aim = aim_with_prediction_heuristic(r, front, send, initial_by_id,
                                                 ang_vel, comets, comet_ids)
            if aim is None:
                continue
            angle, turns, _, _ = aim
            if turns > 40:
                continue
            moves.append([r.id, float(angle), int(send)])
            available[r.id] -= send

    return moves
```

## [CODE]
```python
# ══════════════════════════════════════════════════════════════════════════════
# CELL 1 · SETUP  ─ v5
# ══════════════════════════════════════════════════════════════════════════════
"""
KEY CHANGES vs v4:
  [FEAT]  N_EF 16→20: ships_ratio, heur_score, dist_rank, is_nearest_capturable
          These 4 features give the model EXACTLY what the heuristic uses to pick targets.
  [FIX]   Ships cap: send min(frac_ships, ships_needed * OVERSEND_CAP) — ends oversending.
  [FIX]   LAM 0.95→0.98: fleet takes ~50 steps to arrive; credit now propagates further back.
  [NEW]   Fleet arrival tracking: delayed reward fires when fleet reaches (or misses) target.
          This closes the 50-step credit assignment gap that was starving the launch decision.
  [FIX]   Dispatch info returned from _decode_actions so _collect_episode_impl can track.
"""
import math, random, collections, os, copy
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.distributions import Categorical, Beta
from kaggle_environments import make
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet, Fleet

BOARD       = 100.0
CX, CY      = 50.0, 50.0
SUN_R       = 10.0
MAX_SPEED   = 6.0
SUN_SAFETY  = 1.5
ROT_LIMIT   = 50.0
TOTAL_STEPS = 500

MAX_P = 44
N_PF  = 14
N_GF  =  8

# ── CHANGED: N_EF 16 → 20 ─────────────────────────────────────────────────
# 4 new features: ships_ratio, heur_score, dist_rank, is_nearest_capturable
N_EF  = 20

# ── Beta action space ─────────────────────────────────────────────────────
BETA_EPS = 1e-4
MIN_FRAC = 0.05
MAX_FRAC = 0.95

# NEW: hard cap on oversending — never send more than this multiple of ships_needed
OVERSEND_CAP = 1.35

# ── Self-play ─────────────────────────────────────────────────────────────
SELF_PLAY_RATIO = 0.5
LAG_UPDATE_FREQ = 5

# ── PPO hyper-parameters ──────────────────────────────────────────────────
GAMMA      = 0.99
LAM        = 0.98   # CHANGED 0.95 → 0.98: fleet takes ~50 steps; longer credit horizon
CLIP       = 0.2
V_COEFF    = 0.5
ENT_COEFF  = 0.02
PPO_EPOCHS = 8
BATCH_SZ   = 128
MAX_GRAD   = 0.5
RET_CLIP   = 50.0
ADV_CLIP   = 5.0

# NEW: Fleet arrival delayed reward weights
FLEET_HIT_BONUS   =  0.4   # per production point when fleet captures
FLEET_MISS_PENALTY = -0.15  # flat penalty when fleet fails to capture target
FLEET_MAX_WAIT     = 80     # don't track beyond this many steps

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"device={device}  N_EF={N_EF}  LAM={LAM}")
```

## [CODE]
```python
# ══════════════════════════════════════════════════════════════════════════════
# CELL 2 · PHYSICS ENGINE  (unchanged from v4)
# ══════════════════════════════════════════════════════════════════════════════

def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)

def fleet_speed(n):
    if n <= 1: return 1.0
    r = max(0.0, min(1.0, math.log(n) / math.log(1000.0)))
    return 1.0 + (MAX_SPEED - 1.0) * r ** 1.5

def segment_hits_sun(x1, y1, x2, y2, safety=SUN_SAFETY):
    r = SUN_R + safety
    dx, dy = x2-x1, y2-y1
    fx, fy = x1-CX, y1-CY
    a = dx*dx + dy*dy
    if a < 1e-9: return dist(x1, y1, CX, CY) < r
    b = 2*(fx*dx + fy*dy)
    c = fx*fx + fy*fy - r*r
    disc = b*b - 4*a*c
    if disc < 0: return False
    sq = math.sqrt(disc)
    t1, t2 = (-b-sq)/(2*a), (-b+sq)/(2*a)
    return (0 <= t1 <= 1) or (0 <= t2 <= 1)

def safe_angle_dist(sx, sy, tx, ty):
    if not segment_hits_sun(sx, sy, tx, ty):
        return math.atan2(ty-sy, tx-sx), dist(sx, sy, tx, ty)
    vx, vy = tx-sx, ty-sy
    norm = math.hypot(vx, vy)
    if norm < 1e-9: return math.atan2(ty-sy, tx-sx), dist(sx, sy, tx, ty)
    nx, ny = -vy/norm, vx/norm
    best = None
    for sign in (1.0, -1.0):
        for m in (2.0, 3.0, 4.0):
            wx = CX + sign*nx*(SUN_R*m); wy = CY + sign*ny*(SUN_R*m)
            if segment_hits_sun(sx,sy,wx,wy) or segment_hits_sun(wx,wy,tx,ty): continue
            d = dist(sx,sy,wx,wy) + dist(wx,wy,tx,ty)
            if best is None or d < best[0]: best = (d, wx, wy)
            break
    if best is None: return math.atan2(ty-sy, tx-sx), dist(sx,sy,tx,ty)*1.5
    return math.atan2(best[2]-sy, best[1]-sx), best[0]

def predict_planet_pos(planet, init_by_id, ang_vel, turns):
    init = init_by_id.get(planet.id)
    if init is None: return planet.x, planet.y
    orb_r = dist(init.x, init.y, CX, CY)
    if orb_r + init.radius >= ROT_LIMIT: return planet.x, planet.y
    ang = math.atan2(planet.y-CY, planet.x-CX) + ang_vel*turns
    return CX + orb_r*math.cos(ang), CY + orb_r*math.sin(ang)

def predict_comet_pos(pid, comets, turns):
    for g in comets:
        pids = g.get("planet_ids", [])
        if pid not in pids: continue
        idx = pids.index(pid); paths = g.get("paths", []); pi = g.get("path_index", 0)
        if idx < len(paths):
            fi = pi + int(turns)
            if 0 <= fi < len(paths[idx]): return paths[idx][fi][0], paths[idx][fi][1]
        return None
    return None

def comet_life(pid, comets):
    for g in comets:
        pids = g.get("planet_ids", [])
        if pid not in pids: continue
        idx = pids.index(pid); paths = g.get("paths", []); pi = g.get("path_index", 0)
        if idx < len(paths): return max(0, len(paths[idx]) - pi)
    return 0

def estimate_arrival(sx, sy, tx, ty, ships):
    angle, d = safe_angle_dist(sx, sy, tx, ty)
    return angle, max(1, int(math.ceil(d / fleet_speed(ships))))

def aim_pred(src, tgt, ships, init_by_id, ang_vel, comets, comet_ids):
    tx, ty = tgt.x, tgt.y
    for _ in range(4):
        angle, turns = estimate_arrival(src.x, src.y, tx, ty, ships)
        if tgt.id in comet_ids:
            pos = predict_comet_pos(tgt.id, comets, turns)
            if pos is None: return None
            ntx, nty = pos
        else:
            ntx, nty = predict_planet_pos(tgt, init_by_id, ang_vel, turns)
        if abs(ntx-tx) < 0.5 and abs(nty-ty) < 0.5:
            tx, ty = ntx, nty; break
        tx, ty = ntx, nty
    a, t = estimate_arrival(src.x, src.y, tx, ty, ships)
    return a, t, tx, ty

def fleet_hits_planet(fleet, planets):
    best_p, best_t = None, 1e9
    fvx = math.cos(fleet.angle); fvy = math.sin(fleet.angle)
    sp = fleet_speed(fleet.ships)
    for p in planets:
        dx, dy = p.x-fleet.x, p.y-fleet.y
        proj = dx*fvx + dy*fvy
        if proj <= 0: continue
        perp = abs(dx*fvy - dy*fvx)
        if perp > p.radius + 1.2: continue
        t = proj / sp
        if t < best_t and t <= 80: best_t, best_p = t, p
    return best_p, int(math.ceil(best_t)) if best_p else (None, None)

def incoming_to(planet, fleets):
    arrivals = []
    for f in fleets:
        fvx, fvy = math.cos(f.angle), math.sin(f.angle)
        dx, dy = planet.x-f.x, planet.y-f.y
        proj = dx*fvx + dy*fvy
        if proj <= 0: continue
        perp = abs(dx*fvy - dy*fvx)
        if perp > planet.radius + 1.5: continue
        t = proj / fleet_speed(f.ships)
        if t > 80: continue
        arrivals.append((int(math.ceil(t)), f.owner, int(f.ships)))
    return arrivals

def net_defense_needed(planet, arrivals, player):
    if not arrivals: return 0
    events = sorted(arrivals)
    garrison = planet.ships; prod = planet.production if planet.owner == player else 0
    last_t = 0; deficit = 0; i = 0
    while i < len(events):
        t = events[i][0]; garrison += (t - last_t) * prod; group = []
        while i < len(events) and events[i][0] == t:
            group.append(events[i]); i += 1
        garrison += sum(s for _, o, s in group if o == player)
        garrison -= sum(s for _, o, s in group if o != player)
        if garrison < 0: deficit = max(deficit, -garrison)
        last_t = t
    return deficit

def _batch_hits_sun(sx, sy, txs, tys, safety=SUN_SAFETY):
    r = SUN_R + safety
    dx = txs - sx; dy = tys - sy
    fx = sx - CX; fy = sy - CY
    a = dx*dx + dy*dy; b = 2.0*(fx*dx + fy*dy); c = fx*fx + fy*fy - r*r
    disc = b*b - 4.0*a*c
    hits = np.zeros(len(txs), dtype=bool)
    ok = (a > 1e-9) & (disc >= 0.0)
    if ok.any():
        sq = np.sqrt(np.where(ok, disc, 0.0)); denom = 2.0 * a; denom[~ok] = 1.0
        t1 = (-b - sq) / denom; t2 = (-b + sq) / denom
        hits[ok] = (((t1[ok] >= 0.0) & (t1[ok] <= 1.0)) | ((t2[ok] >= 0.0) & (t2[ok] <= 1.0)))
    return hits
```

## [CODE]
```python
# ══════════════════════════════════════════════════════════════════════════════
# CELL 3 · STATE FEATURE EXTRACTION  ─ v5
# ══════════════════════════════════════════════════════════════════════════════

def _fleet_influence(planets, fleets, player):
    inf_f, inf_e = {}, {}
    for f in fleets:
        hp, _ = fleet_hits_planet(f, planets)
        if hp is None: continue
        if f.owner == player: inf_f[hp.id] = inf_f.get(hp.id, 0) + f.ships
        else: inf_e[hp.id] = inf_e.get(hp.id, 0) + f.ships
    return inf_f, inf_e

def _predict_pos_batch(tgts, tgt_ids, init_by_id, ang_vel, turns_arr, comet_ids, comets):
    n = len(tgts)
    cur_xs = np.array([t.x for t in tgts], np.float64)
    cur_ys = np.array([t.y for t in tgts], np.float64)
    init_xs = np.empty(n, np.float64); init_ys = np.empty(n, np.float64); init_rs = np.empty(n, np.float64)
    for k, tid in enumerate(tgt_ids):
        p = init_by_id.get(tid)
        if p is not None: init_xs[k], init_ys[k], init_rs[k] = p.x, p.y, p.radius
        else: init_xs[k], init_ys[k], init_rs[k] = cur_xs[k], cur_ys[k], 1.0
    d2c = np.hypot(init_xs - CX, init_ys - CY); orbiting = (d2c + init_rs) < ROT_LIMIT
    base_ang = np.arctan2(init_ys - CY, init_xs - CX); new_ang = base_ang + ang_vel * turns_arr
    ptxs = np.where(orbiting, CX + d2c * np.cos(new_ang), cur_xs)
    ptys = np.where(orbiting, CY + d2c * np.sin(new_ang), cur_ys)
    for k, tid in enumerate(tgt_ids):
        if tid in comet_ids:
            pos = predict_comet_pos(tid, comets, int(turns_arr[k]))
            if pos: ptxs[k], ptys[k] = pos
    return ptxs, ptys


def compute_edge_features(planets, pids, smsk, init_by_id, ang_vel, comets, comet_ids,
                           inf_f, inf_e, player) -> np.ndarray:
    """
    N_EF = 20 edge features per (src, tgt).

    Features 0-15 are IDENTICAL to v4 (preserved).
    NEW features 16-19 are designed to teach the model EXACTLY what the
    heuristic uses to pick targets and calibrate ship counts:

      16  ships_ratio         ships_needed / src.ships  ∈ [0, 1.5]
                              → directly encodes "what fraction to send"
                              → Beta head can anchor to this value
      17  heur_score          heuristic target-quality score, normalized [0, 1]
                              = prod*60 / (ships_needed + turns*0.8 + 1) / 50
                              → same formula heuristic uses; highest = best target
      18  dist_rank_norm      rank by raw_dist among all targets from this src,
                              normalized 0 (nearest) → 1 (farthest)
                              → explicit proximity ranking the model can read
      19  is_nearest_capturable  1.0 for the single nearest target that
                              can_capture==1 (enough ships right now),
                              0 elsewhere
                              → "just capture this one" signal for early game
    """
    ef = np.zeros((MAX_P, MAX_P, N_EF), dtype=np.float32)
    pb = {p.id: p for p in planets}

    for si in range(MAX_P):
        if not smsk[si] or pids[si] == -1: continue
        src = pb.get(pids[si])
        if src is None: continue

        sx, sy = src.x, src.y
        sp = fleet_speed(max(10, src.ships))

        ti_list, tgts, tgt_ids = [], [], []
        for ti in range(MAX_P):
            if ti == si or pids[ti] == -1: continue
            tgt = pb.get(pids[ti])
            if tgt is not None:
                ti_list.append(ti); tgts.append(tgt); tgt_ids.append(pids[ti])
        if not tgts: continue

        txs = np.array([t.x for t in tgts], np.float64)
        tys = np.array([t.y for t in tgts], np.float64)

        raw_dists = np.hypot(txs - sx, tys - sy)
        turns_est = np.maximum(1, np.ceil(raw_dists / sp))

        ptxs, ptys = _predict_pos_batch(tgts, tgt_ids, init_by_id, ang_vel, turns_est, comet_ids, comets)
        pdx = ptxs - sx; pdy = ptys - sy
        pred_dists = np.hypot(pdx, pdy)
        pred_ang = np.arctan2(pdy, pdx)
        pred_turns = np.maximum(1, np.ceil(pred_dists / sp))

        sun_blocked = _batch_hits_sun(sx, sy, ptxs, ptys).astype(np.float32)

        defenders = np.array([t.ships for t in tgts], np.float64)
        prods = np.array([t.production for t in tgts], np.float64)
        owners = np.array([t.owner for t in tgts], int)

        for k, tgt in enumerate(tgts):
            if owners[k] != -1: defenders[k] += prods[k] * pred_turns[k]
            if owners[k] != player: defenders[k] -= inf_f.get(tgt.id, 0)
            else: defenders[k] += inf_e.get(tgt.id, 0)
        defenders = np.maximum(0.0, defenders)
        ships_needed = defenders + 1.0

        log_need = (np.log(ships_needed + 1.0) / np.log(1001.0)).astype(np.float32)
        can_capture = (src.ships >= ships_needed).astype(np.float32)
        is_enemy = ((owners != player) & (owners != -1)).astype(np.float32)
        is_mine = (owners == player).astype(np.float32)

        efficiency = np.clip(
            prods / (pred_turns * np.maximum(defenders, 1.0) + 1.0) / 0.5, 0.0, 1.0
        ).astype(np.float32)
        comfort = np.clip(src.ships / (ships_needed + 1.0), 0.0, 1.0).astype(np.float32)
        raw_dist_n = (raw_dists / 141.4).astype(np.float32)

        inbound_f = np.array([inf_f.get(t.id, 0) for t in tgts], np.float64)
        coverage = np.clip(inbound_f / (ships_needed + 1e-6), 0.0, 1.5).astype(np.float32)
        prox_score = ((1.0 - raw_dist_n) * can_capture * (prods / 5.0)).astype(np.float32)

        # ── NEW FEATURE 16: ships_ratio ───────────────────────────────────────
        # What fraction of src.ships is needed to capture each target?
        # Model can directly read this to calibrate its Beta sample.
        # Clamped to [0, 1.5] — >1 means "you can't afford this target"
        ships_ratio = np.clip(
            ships_needed / max(float(src.ships), 1.0), 0.0, 1.5
        ).astype(np.float32)

        # ── NEW FEATURE 17: heur_score ────────────────────────────────────────
        # Mirrors heuristic's target_score: prod*60 / (ships_needed + turns*0.8 + 1)
        # Normalized by /50 to roughly [0,1]. High = best target to attack.
        # Extra bonus for enemy planets (like heuristic's +40 prod).
        heur_val = prods * 60.0 + is_enemy * prods * 40.0
        heur_cost = ships_needed + pred_turns * 0.8
        heur_score = np.clip(
            heur_val / (heur_cost + 1.0) / 50.0, 0.0, 1.0
        ).astype(np.float32)
        heur_score *= (1.0 - sun_blocked)     # zero-out sun-blocked paths
        heur_score *= (1.0 - is_mine)         # zero-out own planets

        # ── NEW FEATURE 18: dist_rank_norm ────────────────────────────────────
        # Rank each target by raw distance from this src (0=nearest, 1=farthest).
        # Model should learn: attack rank-0 first.
        n_tgts = len(tgts)
        dist_rank = np.zeros(n_tgts, np.float32)
        if n_tgts > 1:
            order = np.argsort(raw_dists)
            dist_rank[order] = np.linspace(0.0, 1.0, n_tgts).astype(np.float32)

        # ── NEW FEATURE 19: is_nearest_capturable ─────────────────────────────
        # Binary flag: 1 only for the CLOSEST target the src can currently capture.
        # This is the "just do the easy thing" signal for early/simple strategy.
        is_nearest_cap = np.zeros(n_tgts, np.float32)
        capturable_mask = can_capture.astype(bool) & ~sun_blocked.astype(bool)
        non_mine_mask = is_mine.astype(bool) == False
        valid_cap = capturable_mask & non_mine_mask
        if valid_cap.any():
            dists_cap = raw_dists.copy()
            dists_cap[~valid_cap] = np.inf
            nearest_cap_idx = np.argmin(dists_cap)
            is_nearest_cap[nearest_cap_idx] = 1.0

        # ── Write features ────────────────────────────────────────────────────
        for k, ti in enumerate(ti_list):
            ef[si, ti, 0]  = (ptxs[k] - sx) / 100.0
            ef[si, ti, 1]  = (ptys[k] - sy) / 100.0
            ef[si, ti, 2]  = np.cos(pred_ang[k])
            ef[si, ti, 3]  = np.sin(pred_ang[k])
            ef[si, ti, 4]  = pred_turns[k] / 100.0
            ef[si, ti, 5]  = log_need[k]
            ef[si, ti, 6]  = can_capture[k]
            ef[si, ti, 7]  = sun_blocked[k]
            ef[si, ti, 8]  = prods[k] / 5.0
            ef[si, ti, 9]  = is_enemy[k]
            ef[si, ti, 10] = efficiency[k]
            ef[si, ti, 11] = comfort[k]
            ef[si, ti, 12] = raw_dist_n[k]
            ef[si, ti, 13] = is_mine[k]
            ef[si, ti, 14] = coverage[k]
            ef[si, ti, 15] = prox_score[k]
            ef[si, ti, 16] = ships_ratio[k]   # NEW
            ef[si, ti, 17] = heur_score[k]    # NEW
            ef[si, ti, 18] = dist_rank[k]     # NEW
            ef[si, ti, 19] = is_nearest_cap[k] # NEW

    return ef


def extract_state(obs, cached_init_by_id=None, cached_ang_vel=None):
    player = obs.get("player", 0); step = obs.get("step", 0) or 0
    raw_p = obs.get("planets", []) or []; raw_f = obs.get("fleets", []) or []
    comet_ids = set(obs.get("comet_planet_ids", []) or [])
    comets = obs.get("comets", []) or []
    planets = [Planet(*p) for p in raw_p]; fleets = [Fleet(*f) for f in raw_f]
    if cached_init_by_id is not None:
        init_by_id = cached_init_by_id; ang_vel = cached_ang_vel
    else:
        raw_init = obs.get("initial_planets", []) or []
        ang_vel = obs.get("angular_velocity", 0.0) or 0.0
        init_by_id = {Planet(*p).id: Planet(*p) for p in raw_init}
    inf_f, inf_e = _fleet_influence(planets, fleets, player)
    orbiting_ids = {i.id for i in init_by_id.values() if dist(i.x, i.y, CX, CY) + i.radius < ROT_LIMIT}
    pf = np.zeros((MAX_P, N_PF), dtype=np.float32)
    emsk = np.zeros(MAX_P, dtype=bool); smsk = np.zeros(MAX_P, dtype=bool); pids = [-1] * MAX_P
    for i, p in enumerate(planets):
        if i >= MAX_P: break
        d2c = dist(p.x, p.y, CX, CY) / 70.71; lsh = math.log(p.ships + 1) / math.log(1001)
        l_if = math.log(inf_f.get(p.id, 0) + 1) / math.log(1001)
        l_ie = math.log(inf_e.get(p.id, 0) + 1) / math.log(1001)
        raw_thr = inf_e.get(p.id, 0) - p.ships - inf_f.get(p.id, 0)
        net_thr = max(-1.0, min(1.0, raw_thr / max(1.0, p.ships + 1)))
        pf[i] = [p.x/100.0, p.y/100.0, d2c, float(p.owner == player),
                 float(p.owner not in (player, -1)), float(p.owner == -1),
                 lsh, p.production/5.0, float(p.id in comet_ids),
                 float(p.id in orbiting_ids), l_if, l_ie, net_thr, p.radius/5.0]
        emsk[i] = True; smsk[i] = (p.owner == player); pids[i] = p.id
    my_sh = sum(p.ships for p in planets if p.owner == player)
    en_sh = sum(p.ships for p in planets if p.owner not in (player, -1))
    my_pr = sum(p.production for p in planets if p.owner == player)
    en_pr = sum(p.production for p in planets if p.owner not in (player, -1))
    n = len(planets); nm = sum(1 for p in planets if p.owner == player)
    ne = sum(1 for p in planets if p.owner not in (player, -1))
    nn_ = sum(1 for p in planets if p.owner == -1); tot = my_sh + en_sh
    gf = np.array([step / TOTAL_STEPS, math.log(my_sh + 1) / math.log(10001),
                   math.log(en_sh + 1) / math.log(10001), my_sh / (tot + 1),
                   nm / max(1, n), ne / max(1, n), nn_ / max(1, n),
                   (my_pr - en_pr) / 25.0], dtype=np.float32)
    ef = compute_edge_features(planets, pids, smsk, init_by_id, ang_vel,
                                comets, comet_ids, inf_f, inf_e, player)
    return pf, gf, ef, emsk, smsk, pids
```

## [CODE]
```python
# ══════════════════════════════════════════════════════════════════════════════
# CELL 4 · NEURAL NETWORK  ─ v5 (N_EF=20, frac_head sees ships_ratio directly)
# ══════════════════════════════════════════════════════════════════════════════

class OrbitPolicyNet(nn.Module):
    """
    Same architecture as v4 with two changes:
    1. N_EF=20 → edge_score MLP now sees ships_ratio + heur_score + dist_rank +
       is_nearest_capturable, which are the exact signals the heuristic uses.
    2. frac_head now receives the edge context twice the size (because N_EF grew)
       — frac head can directly read feature 16 (ships_ratio) to anchor Beta mean.
    """
    def __init__(self, max_p=MAX_P, d=192, nhead=6, nlayers=4, dropout=0.1):
        super().__init__()
        self.max_p = max_p; self.d = d
        dh = d // 2; dq = d // 4

        self.p_embed = nn.Sequential(
            nn.Linear(N_PF, d), nn.LayerNorm(d), nn.GELU(),
            nn.Linear(d, d), nn.LayerNorm(d),
        )
        self.g_embed = nn.Sequential(nn.Linear(N_GF, dh), nn.GELU(), nn.Linear(dh, d))

        enc_layer = nn.TransformerEncoderLayer(
            d_model=d, nhead=nhead, dim_feedforward=d*4,
            dropout=dropout, batch_first=True, activation='gelu', norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(enc_layer, num_layers=nlayers)
        self.tgt_q = nn.Linear(d + d, dh); self.tgt_k = nn.Linear(d, dh)
        self._scale = math.sqrt(dh)

        # edge_score sees all N_EF=20 features — heur_score (f17) and
        # is_nearest_capturable (f19) directly guide target selection
        self.edge_score = nn.Sequential(
            nn.Linear(N_EF, dq), nn.GELU(),
            nn.Linear(dq, dq), nn.GELU(),
            nn.Linear(dq, 1),
        )
        self.edge_ctx = nn.Sequential(nn.Linear(N_EF, dq), nn.GELU())

        self.frac_head = nn.Sequential(
            nn.Linear(d + d + dq * 2, d), nn.GELU(),
            nn.Linear(d, d // 2), nn.GELU(),
            nn.Linear(d // 2, 2),
        )
        self.val_head = nn.Sequential(nn.Linear(d * 3, d), nn.GELU(), nn.Linear(d, 1))
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=np.sqrt(2))
                if m.bias is not None: nn.init.zeros_(m.bias)
        nn.init.zeros_(self.frac_head[-1].weight); nn.init.zeros_(self.frac_head[-1].bias)
        nn.init.zeros_(self.val_head[-1].weight);  nn.init.zeros_(self.val_head[-1].bias)

    def forward(self, pf, gf, ef, emsk, smsk):
        B = pf.size(0); P = self.max_p
        p_emb = self.p_embed(pf); g_emb = self.g_embed(gf)
        seq = torch.cat([g_emb.unsqueeze(1), p_emb], dim=1)
        pad = torch.cat([torch.zeros(B, 1, dtype=torch.bool, device=pf.device), ~emsk], dim=1)
        enc = self.transformer(seq, src_key_padding_mask=pad)
        g_enc = enc[:, 0, :]; p_enc = enc[:, 1:, :]
        g_exp = g_enc.unsqueeze(1).expand(-1, P, -1)
        q = self.tgt_q(torch.cat([p_enc, g_exp], dim=-1)); k = self.tgt_k(p_enc)
        dot = torch.bmm(q, k.transpose(1, 2)) / self._scale
        edge_b = self.edge_score(ef).squeeze(-1)
        tgt_logits = dot + edge_b
        eye = torch.eye(P, dtype=torch.bool, device=pf.device).unsqueeze(0)
        tgt_mask = emsk.unsqueeze(1).expand(B, P, P)
        tgt_logits = tgt_logits.masked_fill(eye | ~tgt_mask, float('-inf'))
        e_raw = self.edge_ctx(ef)
        t_m = emsk.unsqueeze(1).unsqueeze(-1).float()
        e_mean = (e_raw * t_m).sum(2) / t_m.sum(2).clamp(min=1)
        e_max = e_raw.amax(dim=2)
        e_ctx = torch.cat([e_mean, e_max], dim=-1)
        frac_raw = self.frac_head(torch.cat([p_enc, g_exp, e_ctx], dim=-1))
        alpha = F.softplus(frac_raw[..., 0]).clamp(max=50.0) + 1.0
        beta_ = F.softplus(frac_raw[..., 1]).clamp(max=50.0) + 1.0
        w = smsk.float().unsqueeze(-1); cnt = smsk.float().sum(1, keepdim=True).clamp(min=1)
        pool_mean = (p_enc * w).sum(1) / cnt
        pool_max = (p_enc * w + (1 - w) * (-10000.0)).amax(1)
        has_planets = smsk.any(dim=1, keepdim=True).float()
        pool_max = pool_max * has_planets
        value = self.val_head(torch.cat([pool_mean, pool_max, g_enc], dim=-1))
        return tgt_logits, (alpha, beta_), value


policy    = OrbitPolicyNet(d=192, nhead=6, nlayers=4).to(device)
optimizer = optim.AdamW(policy.parameters(), lr=5e-4, weight_decay=1e-4)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=1000, eta_min=1e-5)
print(f"Parameters: {sum(p.numel() for p in policy.parameters()):,}")
```

## [CODE]
```python
# ══════════════════════════════════════════════════════════════════════════════
# CELL 5 · PPO INFRASTRUCTURE  ─ v5 (LAM=0.98, same bug fixes as v4)
# ══════════════════════════════════════════════════════════════════════════════

class RolloutBuffer:
    def __init__(self): self.clear()
    def clear(self):
        self.pf=[]; self.gf=[]; self.ef=[]; self.em=[]; self.sm=[]
        self.actions=[]; self.log_probs=[]; self.values=[]; self.rewards=[]; self.dones=[]
    def store(self, pf, gf, ef, em, sm, acts, lp, val, rew, done):
        self.pf.append(pf); self.gf.append(gf); self.ef.append(ef)
        self.em.append(em); self.sm.append(sm)
        self.actions.append(acts); self.log_probs.append(lp)
        self.values.append(val); self.rewards.append(rew); self.dones.append(done)
    def gae(self, last_val=0.0):
        N = len(self.rewards)
        adv = np.zeros(N, np.float32); ret = np.zeros(N, np.float32)
        g = 0.0; nv = last_val
        for t in reversed(range(N)):
            mask = 1.0 - self.dones[t]
            delta = self.rewards[t] + GAMMA * nv * mask - self.values[t]
            g = delta + GAMMA * LAM * mask * g  # LAM=0.98 here
            adv[t] = g; ret[t] = g + self.values[t]; nv = self.values[t]
        ret = np.clip(ret, -RET_CLIP, RET_CLIP)
        return ret, adv


def dense_reward(prev_p, curr_p, player, done, kaggle_r, step=0, max_steps=500):
    if done:
        s_ratio = step / max_steps
        if kaggle_r > 0:   return 20.0 + (1.0 - s_ratio) * 10.0
        elif kaggle_r < 0: return -30.0 + (s_ratio * 10.0)
        else: return 0.0
    prev_pl = {p[0]: p for p in prev_p}; curr_pl = {p[0]: p for p in curr_p}
    my = lambda o: o == player; en = lambda o: o not in (player, -1)
    prev_my_pr = sum(p[6] for p in prev_p if my(p[1])); prev_en_pr = sum(p[6] for p in prev_p if en(p[1]))
    prev_tot = prev_my_pr + prev_en_pr; prev_ratio = prev_my_pr / prev_tot if prev_tot > 0 else 0.5
    curr_my_pr = sum(p[6] for p in curr_p if my(p[1])); curr_en_pr = sum(p[6] for p in curr_p if en(p[1]))
    curr_tot = curr_my_pr + curr_en_pr; curr_ratio = curr_my_pr / curr_tot if curr_tot > 0 else 0.5
    prod_delta_adv = (curr_ratio - prev_ratio) * 2.0
    cap_bonus = 0.0; loss_pen = 0.0
    for pid, cp in curr_pl.items():
        pp = prev_pl.get(pid)
        if pp is None: continue
        if pp[1] != player and cp[1] == player: cap_bonus += cp[6] * 0.4
        if pp[1] == player and cp[1] != player: loss_pen -= pp[6] * 0.4
    return prod_delta_adv + cap_bonus + loss_pen


def ppo_update(buf, returns, advantages, ent_coeff=ENT_COEFF):
    N = len(buf.rewards)
    if N == 0: return 0.0
    adv_t = torch.FloatTensor(advantages).to(device)
    ret_t = torch.FloatTensor(returns).to(device)
    adv_mean = adv_t.mean(); adv_std = adv_t.std()
    adv_t = (adv_t - adv_mean) / (adv_std + 1.0)
    adv_t = adv_t.clamp(-ADV_CLIP, ADV_CLIP)
    pf_all = torch.FloatTensor(np.stack(buf.pf)).to(device)
    gf_all = torch.FloatTensor(np.stack(buf.gf)).to(device)
    ef_all = torch.FloatTensor(np.stack(buf.ef)).to(device)
    em_all = torch.BoolTensor(np.stack(buf.em)).to(device)
    sm_all = torch.BoolTensor(np.stack(buf.sm)).to(device)
    total_loss = 0.0; idx = np.arange(N)
    for _ in range(PPO_EPOCHS):
        np.random.shuffle(idx)
        for start in range(0, N, BATCH_SZ):
            bi = idx[start:start + BATCH_SZ]
            tgt_l, (alpha_t, beta_t), vals = policy(pf_all[bi], gf_all[bi], ef_all[bi], em_all[bi], sm_all[bi])
            new_lps, entrs, valid = [], [], []
            for j, t in enumerate(bi):
                acts = buf.actions[t]; n_a = len(acts)
                if not n_a:
                    valid.append(False); new_lps.append(torch.zeros((), device=device))
                    entrs.append(torch.zeros((), device=device)); continue
                lp = torch.zeros((), device=device); en = torch.zeros((), device=device)
                for si, ti, frac in acts:
                    mt = Categorical(logits=tgt_l[j, si])
                    mb = Beta(alpha_t[j, si], beta_t[j, si])
                    fc = torch.tensor(frac, device=device).clamp(BETA_EPS, 1 - BETA_EPS)
                    lp = lp + mt.log_prob(torch.tensor(ti, device=device)) + mb.log_prob(fc)
                    en = en + mt.entropy() + mb.entropy()
                lp = lp / n_a; en = en / n_a
                new_lps.append(lp); entrs.append(en); valid.append(True)
            if not any(valid): continue
            new_lps_t = torch.stack(new_lps); entrs_t = torch.stack(entrs)
            old_lps_t = torch.FloatTensor([buf.log_probs[t] for t in bi]).to(device)
            v_mask = torch.BoolTensor(valid).to(device)
            ratios = torch.exp((new_lps_t - old_lps_t).clamp(-3.0, 3.0))
            adv_b = adv_t[bi]; ret_b = ret_t[bi]
            pl = -torch.min(ratios * adv_b, torch.clamp(ratios, 1-CLIP, 1+CLIP) * adv_b)
            old_vals = torch.FloatTensor([buf.values[t] for t in bi]).to(device)
            vals_sq = vals.squeeze(-1)
            vals_clip = old_vals + (vals_sq - old_vals).clamp(-CLIP*5, CLIP*5)
            vl = torch.max(F.mse_loss(vals_sq, ret_b), F.mse_loss(vals_clip, ret_b))
            loss = pl[v_mask].mean() + V_COEFF * vl - ent_coeff * entrs_t[v_mask].mean()
            if not torch.isfinite(loss): continue
            optimizer.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(), MAX_GRAD)
            optimizer.step(); total_loss += loss.item()
    return total_loss / max(1, PPO_EPOCHS * max(1, N // BATCH_SZ))
```

## [CODE]
```python
# ══════════════════════════════════════════════════════════════════════════════
# CELL 6 · RL AGENT + ROLLOUT  ─ v5
# ══════════════════════════════════════════════════════════════════════════════

def _decode_actions(obs, tl, alpha, beta, pids, sm,
                    init_by_id, ang_vel, comets, comet_ids, training=True):
    """
    Changes vs v4:
    1. Ships capped at OVERSEND_CAP × ships_needed — ends the "send 80% of garrison"
       behaviour. The Beta fraction now controls headroom ABOVE ships_needed,
       not the absolute count.
    2. Returns a 4th value: `dispatches` — list of (tgt_pid, travel_turns, ships_sent, prod)
       used by _collect_episode_impl to give delayed fleet-arrival rewards.
    3. Coverage masking + targeting logic unchanged.
    """
    player = obs.get("player", 0)
    planets = [Planet(*p) for p in (obs.get("planets", []) or [])]
    fleets  = [Fleet(*f)  for f in (obs.get("fleets",   []) or [])]
    pb = {p.id: p for p in planets}

    inbound_friendly = {}
    for f in fleets:
        if f.owner == player:
            hp, _ = fleet_hits_planet(f, planets)
            if hp: inbound_friendly[hp.id] = inbound_friendly.get(hp.id, 0) + f.ships

    ships_needed_map = {}
    for p in planets:
        if p.owner != player:
            ships_needed_map[p.id] = max(1, int(p.ships + 1))

    moves, acts, lp_sum = [], [], 0.0
    targeted_this_step = set()
    pending_inf = {}
    dispatches = []   # NEW: [(tgt_pid, travel_turns, ships_sent, prod)]

    for si in range(MAX_P):
        if not sm[si] or pids[si] == -1: continue
        src = pb.get(pids[si])
        if src is None or src.ships < 2: continue

        logits_masked = tl[si].clone()
        for ti in range(MAX_P):
            if pids[ti] == -1: continue
            tgt_id = pids[ti]
            if tgt_id in targeted_this_step:
                logits_masked[ti] = float('-inf'); continue
            tgt = pb.get(tgt_id)
            if tgt is None or tgt.owner == player: continue
            needed = ships_needed_map.get(tgt_id, 1)
            total_inbound = inbound_friendly.get(tgt_id, 0) + pending_inf.get(tgt_id, 0)
            if total_inbound >= needed * 1.5:
                logits_masked[ti] = float('-inf')

        valid_mask = logits_masked != float('-inf')
        if not valid_mask.any(): continue

        mt = Categorical(logits=logits_masked)
        mb = Beta(alpha[si], beta[si])

        if training:
            ti_idx = mt.sample().item()
            frac   = mb.sample().clamp(MIN_FRAC, MAX_FRAC).item()
        else:
            ti_idx = logits_masked.argmax().item()
            frac   = (alpha[si] / (alpha[si] + beta[si])).item()
            frac   = max(MIN_FRAC, min(MAX_FRAC, frac))

        fc = torch.tensor(frac, device=device).clamp(BETA_EPS, 1 - BETA_EPS)
        lp_sum += (mt.log_prob(torch.tensor(ti_idx, device=device)) + mb.log_prob(fc)).item()
        acts.append((si, ti_idx, frac))

        tgt_pid = pids[ti_idx]
        if tgt_pid == -1: continue
        tgt = pb.get(tgt_pid)
        if tgt is None: continue

        needed  = ships_needed_map.get(tgt_pid, 1)
        already = inbound_friendly.get(tgt_pid, 0) + pending_inf.get(tgt_pid, 0)
        net_need = max(1, needed - int(already))

        # ── CHANGED: ships capped at OVERSEND_CAP × net_need ────────────────
        # Old: max(frac_ships, net_need)  → could send 80% of garrison
        # New: frac controls headroom [1.0, OVERSEND_CAP] × net_need
        #      so the model still has freedom but can't wildly oversend
        frac_ships = max(1, min(int(frac * src.ships), src.ships - 1))
        ships = max(net_need, min(frac_ships, int(net_need * OVERSEND_CAP)))
        ships = min(ships, src.ships - 1)

        if ships <= 0: continue

        aim = aim_pred(src, tgt, ships, init_by_id, ang_vel, comets, comet_ids)
        if aim is None: continue
        angle, travel_turns, _, _ = aim

        if segment_hits_sun(src.x, src.y,
                            src.x + math.cos(angle) * 3,
                            src.y + math.sin(angle) * 3, safety=0.3):
            continue

        moves.append([src.id, float(angle), int(ships)])
        targeted_this_step.add(tgt_pid)
        pending_inf[tgt_pid] = pending_inf.get(tgt_pid, 0) + ships

        # NEW: record for delayed arrival reward
        dispatches.append((tgt_pid, travel_turns, ships, tgt.production))

    n_acts = max(1, len(acts))
    lp_norm = lp_sum / n_acts

    return moves, acts, lp_norm, dispatches   # NOTE: now 4 return values


def rl_agent(obs):
    raw_init   = obs.get("initial_planets", []) or []
    ang_vel    = obs.get("angular_velocity", 0.0) or 0.0
    comets     = obs.get("comets",           []) or []
    comet_ids  = set(obs.get("comet_planet_ids", []) or [])
    init_by_id = {Planet(*p).id: Planet(*p) for p in raw_init}
    pf, gf, ef, em, sm, pids = extract_state(obs, init_by_id, ang_vel)
    with torch.inference_mode():
        tl, (alpha, beta), _ = policy(
            torch.FloatTensor(pf).unsqueeze(0).to(device),
            torch.FloatTensor(gf).unsqueeze(0).to(device),
            torch.FloatTensor(ef).unsqueeze(0).to(device),
            torch.BoolTensor(em).unsqueeze(0).to(device),
            torch.BoolTensor(sm).unsqueeze(0).to(device),
        )
    moves, _, _, _ = _decode_actions(obs, tl[0], alpha[0], beta[0], pids, sm,
                                      init_by_id, ang_vel, comets, comet_ids,
                                      training=False)
    return moves


def make_lagged_opponent(state_dict):
    lag_pol = OrbitPolicyNet(d=192, nhead=6, nlayers=4).to(device)
    lag_pol.load_state_dict(state_dict); lag_pol.eval()
    def agent(obs):
        raw_init   = obs.get("initial_planets", []) or []
        ang_vel    = obs.get("angular_velocity", 0.0) or 0.0
        comets     = obs.get("comets",           []) or []
        comet_ids  = set(obs.get("comet_planet_ids", []) or [])
        init_by_id = {Planet(*p).id: Planet(*p) for p in raw_init}
        pf, gf, ef, em, sm, pids = extract_state(obs, init_by_id, ang_vel)
        with torch.inference_mode():
            tl, (alpha, beta), _ = lag_pol(
                torch.FloatTensor(pf).unsqueeze(0).to(device),
                torch.FloatTensor(gf).unsqueeze(0).to(device),
                torch.FloatTensor(ef).unsqueeze(0).to(device),
                torch.BoolTensor(em).unsqueeze(0).to(device),
                torch.BoolTensor(sm).unsqueeze(0).to(device),
            )
        moves, _, _, _ = _decode_actions(obs, tl[0], alpha[0], beta[0], pids, sm,
                                          init_by_id, ang_vel, comets, comet_ids,
                                          training=False)
        return moves
    return agent, lag_pol


def _collect_episode_impl(pol, env, opponent):
    """
    v5 changes:
    - _decode_actions now returns `dispatches`; we feed them into `pending_arrivals`
    - pending_arrivals: list of (tgt_pid, expected_arrival_step, ships_sent, prod)
    - At each step, resolved arrivals fire their delayed reward:
        +FLEET_HIT_BONUS × prod if we now own the planet
        +FLEET_MISS_PENALTY      if we don't (intercepted, missed, or target defended)
    - This gives credit/blame to the LAUNCH DECISION rather than just the step
      of capture (which dense_reward already handles separately).
    """
    trainer = env.train([None, opponent])
    obs = trainer.reset(); obs_d = dict(obs); obs_d.setdefault('step', 0)
    player = obs_d.get('player', 0)
    raw_init   = obs_d.get("initial_planets", []) or []
    ang_vel    = obs_d.get("angular_velocity", 0.0) or 0.0
    init_by_id = {Planet(*p).id: Planet(*p) for p in raw_init}
    prev_d = obs_d

    rec_pf, rec_gf, rec_ef, rec_em, rec_sm = [], [], [], [], []
    rec_acts, rec_lp, rec_val, rec_rew, rec_done = [], [], [], [], []

    total_r = 0.0; step = 0

    # ── NEW: fleet arrival tracker ────────────────────────────────────────────
    # Each entry: (tgt_pid, arrival_step, ships_sent, prod)
    # We check on the expected arrival step whether the planet is ours.
    pending_arrivals = []

    while True:
        comets    = obs_d.get("comets",           []) or []
        comet_ids = set(obs_d.get("comet_planet_ids", []) or [])

        pf, gf, ef, em, sm, pids = extract_state(obs_d, init_by_id, ang_vel)
        with torch.inference_mode():
            tl, (alpha, beta), val_t = pol(
                torch.FloatTensor(pf).unsqueeze(0).to(device),
                torch.FloatTensor(gf).unsqueeze(0).to(device),
                torch.FloatTensor(ef).unsqueeze(0).to(device),
                torch.BoolTensor(em).unsqueeze(0).to(device),
                torch.BoolTensor(sm).unsqueeze(0).to(device),
            )
        val = val_t.item()

        # Note: now 4-tuple return
        moves, acts, lp, dispatches = _decode_actions(
            obs_d, tl[0], alpha[0], beta[0], pids, sm,
            init_by_id, ang_vel, comets, comet_ids, training=True
        )

        # Register new dispatches into pending tracker
        # We need the current state of planets to check who owns the target NOW
        curr_state_planets = {p[0]: p for p in (obs_d.get("planets", []) or [])}

        for tgt_pid, travel_turns, ships_sent, prod in dispatches:
            if travel_turns <= FLEET_MAX_WAIT:
                # Find who owns the target at the moment of launch
                tgt_info = curr_state_planets.get(tgt_pid)
                original_owner = tgt_info[1] if tgt_info else -1

                pending_arrivals.append((tgt_pid, step + travel_turns, ships_sent, prod, original_owner))

        obs, kgr, done, _ = trainer.step(moves)
        obs_d = dict(obs); obs_d['step'] = step + 1; kgr = kgr or 0.0

        # Current planet state for arrival checks
        curr_pb = {p[0]: p for p in (obs_d.get("planets", []) or [])}

        # ── Resolve pending fleet arrivals ────────────────────────────────────
        arrival_r = 0.0
        still_pending = []
        for entry in pending_arrivals:
            tgt_pid, arr_step, ships_sent, prod, original_owner = entry
            if step + 1 >= arr_step:
                # Fleet should have arrived — check planet ownership now
                tgt_state = curr_pb.get(tgt_pid)
                if tgt_state is None:
                    # Planet no longer exists (comet left) — no penalty, just ignore
                    pass
                elif tgt_state[1] == player:
                    # SUCCESS: we own this planet — give bonus proportional to its value
                    arrival_r += FLEET_HIT_BONUS * prod
                else:
                    # MISS: fleet arrived but didn't capture (intercepted, undersent, etc.)
                    arrival_r += FLEET_MISS_PENALTY
            else:
                still_pending.append(entry)
        pending_arrivals = still_pending

        rew = dense_reward(
            prev_d.get("planets", []) or [],
            obs_d.get("planets",  []) or [],
            player, done, kgr, step=step, max_steps=500
        ) + arrival_r

        total_r += rew

        rec_pf.append(pf); rec_gf.append(gf); rec_ef.append(ef)
        rec_em.append(em); rec_sm.append(sm)
        rec_acts.append(acts); rec_lp.append(lp)
        rec_val.append(val); rec_rew.append(rew); rec_done.append(float(done))

        prev_d = obs_d; step += 1
        if done: break

    return {
        'pf':        np.array(rec_pf,   dtype=np.float32),
        'gf':        np.array(rec_gf,   dtype=np.float32),
        'ef':        np.array(rec_ef,   dtype=np.float32),
        'em':        np.array(rec_em,   dtype=bool),
        'sm':        np.array(rec_sm,   dtype=bool),
        'actions':   rec_acts,
        'log_probs': np.array(rec_lp,   dtype=np.float32),
        'values':    np.array(rec_val,  dtype=np.float32),
        'rewards':   np.array(rec_rew,  dtype=np.float32),
        'dones':     np.array(rec_done, dtype=np.float32),
    }, total_r, step


def collect_episode(buf, env, opponent=None):
    rdata, total_r, steps = _collect_episode_impl(
        policy, env, opponent or heuristic_agent
    )
    for t in range(len(rdata['rewards'])):
        buf.store(
            rdata['pf'][t], rdata['gf'][t], rdata['ef'][t],
            rdata['em'][t], rdata['sm'][t],
            rdata['actions'][t],
            float(rdata['log_probs'][t]),
            float(rdata['values'][t]),
            float(rdata['rewards'][t]),
            float(rdata['dones'][t]),
        )
    return total_r, steps
```

## [CODE]
```python
# ══════════════════════════════════════════════════════════════════════════════
# CELL 7 · TRAINING LOOP  ─ v5 (unchanged structure)
# ══════════════════════════════════════════════════════════════════════════════
#CHECKPOINT_PATH = "/kaggle/working/orbit_policy_last.pt"
ep = 0
if os.path.exists(CHECKPOINT_PATH):
    print(f"Loading weights from {CHECKPOINT_PATH}...")
    try:
        policy.load_state_dict(torch.load(CHECKPOINT_PATH, map_location=device))
        print("Loaded successfully.")
    except Exception as e:
        print(f"Could not load checkpoint (N_EF changed 16→20): {e}")
        print("Starting from scratch with v5 architecture.")
else:
    print("No checkpoint found, starting fresh.")

N_EPISODES  = 100
EVAL_EVERY  = 50
EVAL_GAMES  = 20

ENT_START   = 0.03
ENT_END     = 0.005
ENT_DECAY   = N_EPISODES

SELF_PLAY_MAX = 0.3
SELF_PLAY_MIN = 0.2

best_wins   = -1
min_loss    = float('inf')
wins_history = []

train_env = make("orbit_wars", configuration={"episodeSteps": 500})
eval_env  = make("orbit_wars", configuration={"episodeSteps": 500})

lag_agent, lag_pol = make_lagged_opponent(policy.state_dict())
print(f"Training {N_EPISODES} eps | v5: N_EF=20, LAM=0.98, fleet tracking, ship cap={OVERSEND_CAP}x")
print(f"Entropy: {ENT_START} → {ENT_END}  |  Self-play: {SELF_PLAY_MIN} → {SELF_PLAY_MAX}")

try:
    while ep < N_EPISODES:
        t_frac     = ep / max(1, N_EPISODES)
        ent_coeff  = ENT_START + (ENT_END - ENT_START) * t_frac
        sp_ratio   = SELF_PLAY_MIN + (SELF_PLAY_MAX - SELF_PLAY_MIN) * t_frac
        use_self   = random.random() < sp_ratio
        opponent   = lag_agent if use_self else heuristic_agent

        buf = RolloutBuffer()
        total_r, steps = collect_episode(buf, train_env, opponent)
        ret, adv       = buf.gae()
        current_loss   = ppo_update(buf, ret, adv, ent_coeff=ent_coeff)
        scheduler.step()

        if ep % LAG_UPDATE_FREQ == 0:
            lag_pol.load_state_dict(policy.state_dict())

        if ep % 1 == 0:
            lr  = scheduler.get_last_lr()[0]
            opp = "self " if use_self else "heur "
            loss_flag = " ⚠️ LARGE" if current_loss > 1000 else ""
            print(f"[{ep:4d}] steps={steps:3d}  r={total_r:7.2f}  "
                  f"loss={current_loss:.4f}{loss_flag}  "
                  f"ent={ent_coeff:.4f}  lr={lr:.1e}  opp={opp}  "
                  f"buf={len(buf.rewards)}")

        torch.save(policy.state_dict(), "/kaggle/working/orbit_policy_last.pt")
        if current_loss < min_loss and current_loss < 1e6:
            min_loss = current_loss
            torch.save(policy.state_dict(), "/kaggle/working/orbit_policy_best_loss.pt")

        if ep % EVAL_EVERY == 0 and ep > 0:
            torch.save(policy.state_dict(), f"/kaggle/working/orbit_policy_ep{ep}.pt")
            wins = 0
            for _ in range(EVAL_GAMES):
                out = eval_env.run([rl_agent, heuristic_agent])
                p1 = out[-1][0]['reward'] or 0; p2 = out[-1][1]['reward'] or 0
                if p1 > p2: wins += 1
            win_rate = wins / EVAL_GAMES; wins_history.append((ep, win_rate))
            print(f"\n>>> EVAL ep={ep}: RL wins {wins}/{EVAL_GAMES} "
                  f"({win_rate*100:.0f}%) vs Heuristic <<<")
            if wins > best_wins:
                best_wins = wins
                torch.save(policy.state_dict(), "/kaggle/working/orbit_policy_best_wins.pt")
                print(f"--- NEW BEST: {wins}/{EVAL_GAMES} saved ---\n")
            else:
                print(f"--- (best so far: {best_wins}/{EVAL_GAMES}) ---\n")

        ep += 1

except KeyboardInterrupt:
    print("\n[!] Stopped early.")
finally:
    torch.save(policy.state_dict(), "/kaggle/working/orbit_policy_last.pt")
    print(f"\nDone. ep={ep}  best_wins={best_wins}/{EVAL_GAMES}  min_loss={min_loss:.4f}")
    print("Win history:", wins_history)
```

## [CODE]
```python
import json

class Visualizer:
    def __init__(self):
        self._frames = []   # list of {obs, lines, texts}
        self._frame_map = {}  # step -> index
        self._recording = True

    def record(self, obs):
        """Call once per turn with the raw obs dict."""
        if hasattr(obs, '__dict__'):
            obs = vars(obs)
        if not isinstance(obs, dict):
            raise TypeError(f"obs must be a dict, got {type(obs)}")
        # obs.step=N means the engine has completed N-1 rotations, so planets sit at N-1.
        step = obs['step'] - 1
        if 'planets' not in obs:
            raise KeyError(f"obs missing 'planets' at step {step}")
        if 'fleets' not in obs:
            raise KeyError(f"obs missing 'fleets' at step {step}")
        if not obs['planets']:
            return  # step 0 init call has empty state; skip it
        self._recording = obs.get('player') == 0
        if not self._recording:
            return
        entry = {'obs': _serialize(obs), 'lines': [], 'texts': [], 'labels': []}
        self._frame_map[step] = len(self._frames)
        self._frames.append(entry)

    def _get_or_create(self, step):
        if step in self._frame_map:
            return self._frames[self._frame_map[step]]
        entry = {'obs': {}, 'lines': [], 'texts': [], 'labels': []}
        self._frame_map[step] = len(self._frames)
        self._frames.append(entry)
        return entry

    def add_line(self, step, x1, y1, x2, y2, color='yellow', width=1):
        """Add a colored line segment overlay to a specific frame."""
        if not self._recording:
            return
        self._get_or_create(step)['lines'].append(
            {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'color': color, 'width': width}
        )

    def add_arrow(self, step, x1, y1, x2, y2, color='yellow', width=1, length_frac=0.5, head_size=6):
        """Add a directed arrow: drawn from x1,y1 toward x2,y2 but only length_frac of the way."""
        if not self._recording:
            return
        self._get_or_create(step)['lines'].append({
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'color': color, 'width': width,
            'arrow': True, 'length_frac': length_frac, 'head_size': head_size,
        })

    def add_text(self, step, text):
        """Add a debug text string shown when that frame is active."""
        if not self._recording:
            return
        self._get_or_create(step)['texts'].append(str(text))

    def add_label(self, step, x, y, text, color='#ffffff', font='13px monospace'):
        """Draw a text label at canvas position (x, y) in game-world coordinates."""
        if not self._recording:
            return
        self._get_or_create(step)['labels'].append(
            {'x': x, 'y': y, 'text': str(text), 'color': color, 'font': font}
        )

    def save(self, path):
        """Write the interactive HTML visualizer to path."""
        html = _build_html(self._frames)
        with open(path, 'w') as f:
            f.write(html)
        print(f"Visualizer saved to {path} ({len(self._frames)} frames)")


_PLANET_FIELDS = ('id', 'owner', 'x', 'y', 'radius', 'ships', 'production')
_FLEET_FIELDS  = ('id', 'owner', 'x', 'y', 'angle', 'from_planet_id', 'ships')

def _serialize(obj, _key=None):
    """Recursively convert Namespace/objects to plain dicts/lists."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            out[k] = _serialize(v, _key=k)
        return out
    if isinstance(obj, (list, tuple)):
        # Detect Planet/Fleet objects stored as list elements and normalize them
        result = []
        for item in obj:
            result.append(_serialize(item, _key=_key))
        return result
    if hasattr(obj, '__dict__'):
        d = vars(obj)
        # Planet-like object: has all planet fields
        if all(f in d for f in _PLANET_FIELDS):
            return [d[f] for f in _PLANET_FIELDS]
        # Fleet-like object: has all fleet fields
        if all(f in d for f in _FLEET_FIELDS):
            return [d[f] for f in _FLEET_FIELDS]
        return _serialize(d)
    return obj


def _build_html(frames):
    frames_json = json.dumps(frames)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Orbit Wars Visualizer</title>
<style>
  body {{ margin: 0; background: #0a0a12; color: #ccc; font-family: monospace; display: flex; flex-direction: column; align-items: center; }}
#controls {{ display: flex; align-items: center; gap: 8px; margin: 4px 0; flex-wrap: wrap; justify-content: center; }}
  button {{ background: #1e2a3a; color: #7af; border: 1px solid #345; padding: 4px 12px; cursor: pointer; border-radius: 3px; }}
  button:hover {{ background: #2a3f55; }}
  #frameLabel {{ color: #fa8; min-width: 80px; text-align: center; }}
  #slider {{ width: 500px; max-width: 90vw; accent-color: #7af; }}
  #speedLabel {{ min-width: 60px; }}
  #main {{ display: flex; gap: 12px; align-items: flex-start; }}
  canvas {{ border: 1px solid #334; background: #05050f; }}
  #sidebar {{ width: 520px; max-height: 640px; overflow-y: auto; font-size: 0.75rem; }}
  .panel {{ background: #0f1520; border: 1px solid #234; border-radius: 4px; padding: 6px 8px; margin-bottom: 8px; }}
  .panel h3 {{ margin: 0 0 4px; color: #7af; font-size: 0.8rem; border-bottom: 1px solid #234; padding-bottom: 2px; }}
  .item {{ margin: 2px 0; }}
  .planet-owner-0 {{ color: #4af; }}
  .planet-owner-1 {{ color: #f84; }}
  .planet-owner-2 {{ color: #4f8; }}
  .planet-owner-3 {{ color: #f4f; }}
  .planet-owner-neutral {{ color: #888; }}
  .fleet-owner-0 {{ color: #4af; }}
  .fleet-owner-1 {{ color: #f84; }}
  .fleet-owner-2 {{ color: #4f8; }}
  .fleet-owner-3 {{ color: #f4f; }}
  #debugText {{ white-space: pre-wrap; color: #ff8; }}
  #playBtn.playing {{ color: #fa0; }}
</style>
</head>
<body>
<div id="controls">
  <button id="prevBtn">&#9664; Prev</button>
  <button id="playBtn">&#9654; Play</button>
  <button id="nextBtn">Next &#9654;</button>
  <span id="frameLabel">Frame 0</span>
  <input type="range" id="slider" min="0" value="0">
  <label>Speed: <input type="range" id="speedSlider" min="1" max="30" value="4" style="width:80px">
    <span id="speedLabel">4 fps</span></label>
</div>
<div id="main">
  <canvas id="canvas" width="640" height="640"></canvas>
  <div id="sidebar">
    <div class="panel" id="metaPanel"><h3>Status (⯇⯈ step, ⯅⯆ speed)</h3><div id="metaContent"></div></div>
    <div class="panel" id="textPanel" style="display:none"><h3>Debug Text</h3><pre id="debugText"></pre></div>
    <div class="panel"><h3>Planets</h3><div id="planetContent"></div></div>
    <div class="panel"><h3>Fleets</h3><div id="fleetContent"></div></div>
  </div>
</div>
<script>
const FRAMES = {frames_json};
const COLORS = ['#44aaff','#ff8844','#44ff88','#ff44ff'];
const NEUTRAL_COLOR = '#666';
const COMET_COLOR = '#fc8';

const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const slider = document.getElementById('slider');
const frameLabel = document.getElementById('frameLabel');
const playBtn = document.getElementById('playBtn');
const speedSlider = document.getElementById('speedSlider');
const speedLabel = document.getElementById('speedLabel');

slider.max = FRAMES.length - 1;
let current = 0;
let playing = false;
let playInterval = null;

function ownerColor(owner) {{
  if (owner === -1 || owner === undefined) return NEUTRAL_COLOR;
  return COLORS[owner % COLORS.length];
}}

// board is 100x100, canvas is 640x640
function tx(x) {{ return x * 6.4; }}
function ty(y) {{ return y * 6.4; }}
function tr(r) {{ return r * 6.4; }}

function drawFrame(idx) {{
  const frame = FRAMES[idx];
  const obs = frame.obs;
  ctx.clearRect(0, 0, 640, 640);

  // Background grid (faint)
  ctx.strokeStyle = '#1e2e40';
  ctx.lineWidth = 0.8;
  for (let i = 0; i <= 10; i++) {{
    ctx.beginPath(); ctx.moveTo(i*64, 0); ctx.lineTo(i*64, 640); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, i*64); ctx.lineTo(640, i*64); ctx.stroke();
  }}

  // Sun
  const sunRadius = 10;
  ctx.beginPath();
  ctx.arc(tx(50), ty(50), tr(sunRadius), 0, Math.PI*2);
  ctx.fillStyle = '#888888';
  ctx.fill();

  const cometIds = new Set(obs.comet_planet_ids || []);
  const planets = obs.planets || [];
  const fleets = obs.fleets || [];

  // Planets
  for (const p of planets) {{
    const [id, owner, x, y, radius, ships, production] = p;
    const cx = tx(x), cy = ty(y), cr = tr(radius);
    const isComet = cometIds.has(id);
    const col = ownerColor(owner);

    // Glow
    if (owner >= 0) {{
      const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, cr*2.5);
      glow.addColorStop(0, col + '55');
      glow.addColorStop(1, col + '00');
      ctx.beginPath();
      ctx.arc(cx, cy, cr*2.5, 0, Math.PI*2);
      ctx.fillStyle = glow;
      ctx.fill();
    }}

    ctx.beginPath();
    ctx.arc(cx, cy, cr, 0, Math.PI*2);
    ctx.fillStyle = isComet ? COMET_COLOR : (owner >= 0 ? col : '#334');
    ctx.fill();
    ctx.strokeStyle = isComet ? '#fd0' : col;
    ctx.lineWidth = isComet ? 1.5 : (owner >= 0 ? 1.5 : 0.8);
    ctx.stroke();

  }}

  // Fleets
  for (const f of fleets) {{
    const [id, owner, x, y, angle, from_id, ships] = f;
    const fx = tx(x), fy = ty(y);
    const col = ownerColor(owner);

    // Arrow body
    const len = (6 + Math.log1p(ships) * 1.5) * 1.5;
    const dx = Math.cos(angle), dy = Math.sin(angle);
    ctx.strokeStyle = col;
    ctx.lineWidth = 2.25;
    ctx.beginPath();
    ctx.moveTo(fx - dx*len*0.5, fy - dy*len*0.5);
    ctx.lineTo(fx + dx*len*0.5, fy + dy*len*0.5);
    ctx.stroke();

    // Arrowhead
    ctx.fillStyle = col;
    ctx.beginPath();
    const hx = fx + dx*len*0.5, hy = fy + dy*len*0.5;
    const px = -dy, py = dx; // perpendicular
    ctx.moveTo(hx, hy);
    ctx.lineTo(hx - dx*7.5 + px*4.5, hy - dy*7.5 + py*4.5);
    ctx.lineTo(hx - dx*7.5 - px*4.5, hy - dy*7.5 - py*4.5);
    ctx.closePath();
    ctx.fill();

    // Ship count
    ctx.fillStyle = '#fff';
    ctx.font = '13px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(ships, fx + px*9, fy + py*9);
  }}

  // Debug overlay lines / arrows
  for (const line of (frame.lines || [])) {{
    const ax = tx(line.x1), ay = ty(line.y1);
    const bx = tx(line.x2), by = ty(line.y2);
    const col = line.color || 'yellow';
    const lw = line.width || 1;
    if (line.arrow) {{
      const frac = line.length_frac !== undefined ? line.length_frac : 0.5;
      const hs = line.head_size !== undefined ? line.head_size : 6;
      const ex = ax + (bx - ax) * frac, ey = ay + (by - ay) * frac;
      const dx = (bx - ax), dy = (by - ay);
      const len = Math.sqrt(dx*dx + dy*dy) || 1;
      const ux = dx/len, uy = dy/len;
      const px = -uy, py = ux;
      ctx.strokeStyle = col; ctx.lineWidth = lw;
      ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(ex, ey); ctx.stroke();
      ctx.fillStyle = col;
      ctx.beginPath();
      ctx.moveTo(ex, ey);
      ctx.lineTo(ex - ux*hs*2 + px*hs, ey - uy*hs*2 + py*hs);
      ctx.lineTo(ex - ux*hs*2 - px*hs, ey - uy*hs*2 - py*hs);
      ctx.closePath(); ctx.fill();
    }} else {{
      ctx.beginPath();
      ctx.moveTo(ax, ay); ctx.lineTo(bx, by);
      ctx.strokeStyle = col; ctx.lineWidth = lw;
      ctx.stroke();
    }}
  }}

  // Planet ship counts and ID labels on top of everything
  for (const p of planets) {{
    const [id, owner, x, y, radius, ships] = p;
    const cx = tx(x), cy = ty(y), cr = tr(radius);
    ctx.fillStyle = '#fff';
    ctx.font = `bold ${{Math.max(9, cr*0.9)}}px monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(ships, cx, cy);
    ctx.fillStyle = '#ffffff';
    ctx.font = '13px monospace';
    ctx.fillText('P' + id, cx, cy - cr - 5);
  }}

  // Canvas labels (e.g. future-position planet markers)
  for (const lbl of (frame.labels || [])) {{
    ctx.font = lbl.font || '13px monospace';
    ctx.fillStyle = lbl.color || '#ffffff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(lbl.text, tx(lbl.x), ty(lbl.y));
  }}

  // Update sidebar
  frameLabel.textContent = 'Frame ' + idx + ' / ' + (FRAMES.length - 1);

  // Meta
  const step = obs.step !== undefined ? obs.step : idx;
  const player = obs.player !== undefined ? obs.player : '?';
  const av = obs.angular_velocity !== undefined ? obs.angular_velocity.toFixed(4) : '?';
  const ot = obs.remainingOverageTime !== undefined ? obs.remainingOverageTime.toFixed(2) : '?';
  document.getElementById('metaContent').innerHTML =
    `<div class="item">Step: <b>${{step}}</b> &nbsp; Player: <b>${{player}}</b></div>
     <div class="item">Angular vel: ${{av}} &nbsp; Overage: ${{ot}}s</div>
     <div class="item">Comets: ${{(obs.comet_planet_ids||[]).join(', ') || 'none'}}</div>`;

  // Debug texts
  const texts = frame.texts || [];
  const textPanel = document.getElementById('textPanel');
  if (texts.length > 0) {{
    textPanel.style.display = '';
    document.getElementById('debugText').textContent = texts.join('\\n');
  }} else {{
    textPanel.style.display = 'none';
  }}

  // Planets list
  let pHtml = '';
  for (const p of planets) {{
    const [id, owner, x, y, radius, ships, production] = p;
    const cls = owner >= 0 ? `planet-owner-${{owner}}` : 'planet-owner-neutral';
    const isComet = cometIds.has(id);
    pHtml += `<div class="item ${{cls}}">[P${{id}}${{isComet?'*':''}}] owner=${{owner}} ships=${{ships}} prod=${{production}} (${{x.toFixed(1)}},${{y.toFixed(1)}})</div>`;
  }}
  document.getElementById('planetContent').innerHTML = pHtml || '<div class="item">none</div>';

  // Fleets list
  let fHtml = '';
  for (const f of fleets) {{
    const [id, owner, x, y, angle, from_id, ships] = f;
    const cls = `fleet-owner-${{owner}}`;
    fHtml += `<div class="item ${{cls}}">[F${{id}}] owner=${{owner}} ships=${{ships}} from=P${{from_id}} (${{x.toFixed(1)}},${{y.toFixed(1)}}) ang=${{angle.toFixed(2)}}</div>`;
  }}
  document.getElementById('fleetContent').innerHTML = fHtml || '<div class="item">none</div>';
}}

function go(idx) {{
  current = Math.max(0, Math.min(FRAMES.length - 1, idx));
  slider.value = current;
  drawFrame(current);
}}

document.getElementById('prevBtn').onclick = () => {{ stopPlay(); go(current - 1); }};
document.getElementById('nextBtn').onclick = () => {{ stopPlay(); go(current + 1); }};
slider.oninput = () => {{ go(parseInt(slider.value)); }};

document.addEventListener('keydown', e => {{
  if (e.key === 'ArrowLeft') {{ stopPlay(); go(current - 1); }}
  if (e.key === 'ArrowRight') {{ stopPlay(); go(current + 1); }}
  if (e.key === 'ArrowUp') {{ e.preventDefault(); speedSlider.value = Math.min(30, parseInt(speedSlider.value) + 1); speedSlider.dispatchEvent(new Event('input')); }}
  if (e.key === 'ArrowDown') {{ e.preventDefault(); speedSlider.value = Math.max(1, parseInt(speedSlider.value) - 1); speedSlider.dispatchEvent(new Event('input')); }}
  if (e.key === ' ') {{ e.preventDefault(); togglePlay(); }}
}});

function togglePlay() {{
  playing ? stopPlay() : startPlay();
}}

function startPlay() {{
  playing = true;
  playBtn.textContent = '⏸ Pause';
  playBtn.classList.add('playing');
  const fps = parseInt(speedSlider.value);
  playInterval = setInterval(() => {{
    if (current >= FRAMES.length - 1) {{ stopPlay(); return; }}
    go(current + 1);
  }}, 1000 / fps);
}}

function stopPlay() {{
  playing = false;
  playBtn.textContent = '▶ Play';
  playBtn.classList.remove('playing');
  clearInterval(playInterval);
  playInterval = null;
}}

playBtn.onclick = togglePlay;
canvas.onclick = togglePlay;

speedSlider.oninput = () => {{
  const fps = parseInt(speedSlider.value);
  speedLabel.textContent = fps + ' fps';
  if (playing) {{ stopPlay(); startPlay(); }}
}};

go(0);
</script>
</body>
</html>"""
```

## [CODE]
```python
import torch
import math

# 1. Load the specific model weights
MODEL_PATH = "/kaggle/working/orbit_policy_ep50.pt"
policy.load_state_dict(torch.load(MODEL_PATH, map_location=device))
policy.eval()

# Initialize the visualizer provided in your prompt
viz = Visualizer()

def viz_rl_agent_wrapper(obs, config=None):
    obs_dict = dict(obs)

    # Calculate the normalized step once
    viz_step = obs_dict['step'] - 1

    # Record board state
    viz.record(obs_dict)

    # Call your actual agent
    moves = rl_agent(obs_dict)

    # Use 'viz_step' here so the text attaches to the map frame!
    planets = {p[0]: p for p in obs_dict.get('planets', [])}
    for move in moves:
        src_id, angle, ships = move
        if src_id in planets:
            src = planets[src_id]
            viz.add_arrow(viz_step, src[2], src[3], src[2]+5, src[3]+5, color='#00ffff')
            viz.add_text(viz_step, f"P{src_id} sending {ships} ships") # Fixed step

    return moves
# 2. Run a match against the Heuristic Agent
from kaggle_environments import make
env = make("orbit_wars", debug=False)
# viz_rl_agent_wrapper
# heuristic_agent
# We put our model as Player 0 so the visualizer records it
env.run([viz_rl_agent_wrapper, heuristic_agent])

# 3. Save and Render
VIZ_OUTPUT = "orbit_debug_replay.html"
viz.save(VIZ_OUTPUT)

from IPython.display import IFrame

# Set width to 1200 to fit both the canvas and the sidebar
IFrame(src='orbit_debug_replay.html', width=1200, height=700)
```

## [CODE]
```python
import matplotlib.pyplot as plt

def analyze_match_rewards(env, player_id):
    history = []
    max_steps = len(env.steps) - 1

    # Итерируемся по шагам (пропускаем первый, так как нужен prev_p)
    for i in range(1, len(env.steps)):
        prev_obs = env.steps[i-1][0]['observation']
        curr_obs = env.steps[i][0]['observation']

        prev_p = prev_obs['planets']
        curr_p = curr_obs['planets']
        done = (i == max_steps)

        # В Kaggle env награда в steps — это финальный результат
        kaggle_r = env.steps[i][player_id]['reward'] if done else 0

        # --- Вызов твоей новой функции dense_reward ---
        # Чтобы видеть разбивку, вычисляем компоненты внутри цикла
        # или возвращаем их из функции. Здесь мы вычислим их для логов:

        # Логика компоненты награды:
        prev_pl = {p[0]: p for p in prev_p}
        curr_pl = {p[0]: p for p in curr_p}
        my = lambda o: o == player_id
        en = lambda o: o not in (player_id, -1)

        # Вычисляем составляющие (дублируем логику для отчетности)
        if done:
            s_ratio = i / max_steps
            total = 20.0 + (1.0 - s_ratio) * 10.0 if kaggle_r > 0 else \
                    (-30.0 + (s_ratio * 10.0) if kaggle_r < 0 else 0.0)
            comp = {'terminal': total}
        else:
            prev_my_pr = sum(p[6] for p in prev_p if my(p[1]))
            prev_en_pr = sum(p[6] for p in prev_p if en(p[1]))
            prev_tot = prev_my_pr + prev_en_pr
            prev_ratio = prev_my_pr / prev_tot if prev_tot > 0 else 0.5

            curr_my_pr = sum(p[6] for p in curr_p if my(p[1]))
            curr_en_pr = sum(p[6] for p in curr_p if en(p[1]))
            curr_tot = curr_my_pr + curr_en_pr
            curr_ratio = curr_my_pr / curr_tot if curr_tot > 0 else 0.5

            prod_delta_adv = (curr_ratio - prev_ratio) * 2.0

            cap_bonus = 0.0
            loss_pen = 0.0
            for pid, cp in curr_pl.items():
                pp = prev_pl.get(pid)
                if pp:
                    if pp[1] != player_id and cp[1] == player_id: cap_bonus += cp[6] * 0.4
                    if pp[1] == player_id and cp[1] != player_id: loss_pen -= pp[6] * 0.4

            total = prod_delta_adv + cap_bonus + loss_pen
            comp = {'prod_delta': prod_delta_adv, 'cap_bonus': cap_bonus, 'loss_pen': loss_pen}

        # Сохраняем в историю
        record = {'step': i, 'total': total}
        record.update(comp)
        history.append(record)

    return history
```

## [CODE]
```python
# Собираем данные для обоих игроков
data_p0 = analyze_match_rewards(env, 0)
data_p1 = analyze_match_rewards(env, 1)

def plot_metrics(p0_metrics, p1_metrics):
    # Updated keys based on your new dense_reward function
    metrics = ['prod_delta', 'cap_bonus', 'loss_pen', 'total']

    fig, axes = plt.subplots(len(metrics), 1, figsize=(12, 16), sharex=True)

    steps = [m['step'] for m in p0_metrics]

    for ax, key in zip(axes, metrics):
        # We use .get(key, 0) because 'prod_delta', 'cap_bonus', etc.,
        # only exist on non-terminal steps
        ax.plot(steps, [m.get(key, 0) for m in p0_metrics], label='Player 0', color='cyan', alpha=0.8)
        ax.plot(steps, [m.get(key, 0) for m in p1_metrics], label='Player 1', color='magenta', alpha=0.8)

        ax.set_title(f'Metric: {key.upper()}')
        ax.grid(True, alpha=0.3)
        ax.legend()

        if key == 'total':
            ax.set_ylabel('Reward Value')
            # Cumulative sum remains a great way to see the agent's progress
            p0_cum = [sum(m.get('total', 0) for m in p0_metrics[:i+1]) for i in range(len(p0_metrics))]
            p1_cum = [sum(m.get('total', 0) for m in p1_metrics[:i+1]) for i in range(len(p1_metrics))]

            # Create a secondary axis or plot on the same to show cumulative
            ax2 = ax.twinx()
            ax2.plot(steps, p0_cum, '--', color='cyan', label='P0 Cumulative', alpha=0.5)
            ax2.plot(steps, p1_cum, '--', color='magenta', label='P1 Cumulative', alpha=0.5)
            ax2.set_ylabel('Cumulative Reward')
            ax2.legend(loc='upper left')

    plt.xlabel('Steps')
    plt.tight_layout()
    plt.show()

# Usage remains the same:

plot_metrics(data_p0, data_p1)
```

## [CODE]
```python
import numpy as np
import matplotlib.pyplot as plt

def plot_reward_distribution(data, start_step, end_step):
    # 1. Фильтруем данные по диапазону
    segment = [d for d in data if start_step <= d['step'] <= end_step]

    if not segment:
        print(f"Нет данных в диапазоне от {start_step} до {end_step}")
        return

    # 2. Обновленные ключи для новой логики
    # Исключаем 'step' и 'total', чтобы анализировать только компоненты
    keys = ['prod_delta', 'cap_bonus', 'loss_pen', 'terminal']

    # Суммируем каждую метрику, безопасно получая значения
    sums = {k: sum(d.get(k, 0) for d in segment) for k in keys}

    # Считаем "общую массу" для процентов
    total_abs_mass = sum(abs(v) for v in sums.values())

    labels = []
    values = []
    percents = []
    colors = []

    # Обновленные цвета для метрик
    color_map = {
        'prod_delta': '#2ecc71', # Зеленый
        'cap_bonus': '#f1c40f',  # Желтый
        'loss_pen': '#e74c3c',   # Красный
        'terminal': '#34495e'    # Темный
    }

    for k in keys:
        val = sums[k]
        # Пропускаем ключи, если они вообще не встречались (сумма 0)
        if val == 0 and total_abs_mass > 0:
            continue

        perc = (abs(val) / total_abs_mass * 100) if total_abs_mass > 0 else 0
        labels.append(k)
        values.append(val)
        percents.append(perc)
        colors.append(color_map.get(k, '#95a5a6')) # Серый по умолчанию

    # 3. Рисуем график
    plt.figure(figsize=(10, 6))
    bars = plt.barh(labels, values, color=colors)

    # Добавляем текст с процентами и чистыми значениями
    for i, (bar, p, v) in enumerate(zip(bars, percents, values)):
        x_pos = bar.get_width() if v >= 0 else bar.get_width()
        # Корректируем положение текста для видимости
        align = 'left' if v >= 0 else 'right'
        offset = 0.5 if v >= 0 else -0.5

        plt.text(x_pos + offset, bar.get_y() + bar.get_height()/2,
                 f' {v:.2f} ({p:.1f}%)',
                 va='center', ha=align, fontweight='bold')

    plt.axvline(0, color='black', linewidth=0.8)
    plt.title(f'Анализ структуры ревардов (Шаги {start_step} - {end_step})')
    plt.xlabel('Суммарное значение метрики')
    plt.grid(axis='x', linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.show()

# ИСПОЛЬЗОВАНИЕ:
# Допустим, ты уже запустил симуляцию и вызвал data_p0 = analyze_match_rewards(env, 0)
# Посмотрим на "абузы" в середине игры (с 10 по 100 шаг):
plot_reward_distribution(data_p0, start_step=2, end_step=500)
```

## [CODE]
```python
# ══════════════════════════════════════════════════════════════════════════════
# CELL 8 · INFERENCE, VISUALIZATION & REWARD ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
import torch
import os
import matplotlib.pyplot as plt
from kaggle_environments import make
from IPython.display import IFrame, display

# 1. Load the specific model weights (Fallback to last if a specific epoch isn't found)
MODEL_PATH = "/kaggle/working/orbit_policy_last.pt"
if os.path.exists(MODEL_PATH):
    print(f"Loading weights from {MODEL_PATH}...")
    policy.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    policy.eval()
else:
    print(f"⚠️ Warning: {MODEL_PATH} not found. Using current policy weights in memory.")

# 2. Initialize Visualizer and Wrapper
viz = Visualizer()

def viz_rl_agent_wrapper(obs, config=None):
    obs_dict = dict(obs)
    viz_step = obs_dict['step'] - 1 # Calculate the normalized step once

    viz.record(obs_dict) # Record board state
    moves = rl_agent(obs_dict) # Call your actual agent

    # Attach visual hints to the map frame
    planets = {p[0]: p for p in obs_dict.get('planets', [])}
    for move in moves:
        src_id, angle, ships = move
        if src_id in planets:
            src = planets[src_id]
            viz.add_arrow(viz_step, src[2], src[3], src[2]+5, src[3]+5, color='#00ffff')
            viz.add_text(viz_step, f"P{src_id} sending {ships} ships")

    return moves

# 3. Run a match against the Heuristic Agent
print("\n⚔️ Running Match: RL Agent (P0) vs Heuristic Agent (P1)...")
env = make("orbit_wars", debug=False, configuration={"episodeSteps": 500})
env.run([viz_rl_agent_wrapper, heuristic_agent])

# Print final outcome
p0_reward = env.steps[-1][0]['reward']
p1_reward = env.steps[-1][1]['reward']
print(f"Match Finished! Final Rewards -> P0 (RL): {p0_reward}, P1 (Heur): {p1_reward}")

# 4. Save and Render Replay
VIZ_OUTPUT = "orbit_debug_replay.html"
viz.save(VIZ_OUTPUT)
print(f"Saved replay to {VIZ_OUTPUT}")

# Display the iframe (Using display() ensures it renders correctly in the middle of a cell output)
display(IFrame(src=VIZ_OUTPUT, width=1200, height=700))

# 5. Extract and Plot Rewards
print("\n📊 Analyzing Match Rewards...")
data_p0 = analyze_match_rewards(env, 0)
data_p1 = analyze_match_rewards(env, 1)

# Plot step-by-step line charts for both players
plot_metrics(data_p0, data_p1)

# Plot the total distribution bar chart for the RL agent (entire game)
max_steps_played = len(data_p0)
plot_reward_distribution(data_p0, start_step=1, end_step=max_steps_played)
```

## [CODE]
```python
# ══════════════════════════════════════════════════════════════════════════════
# CELL 9 · DENSE REWARD REPLICATION & DIAGNOSTICS
# ══════════════════════════════════════════════════════════════════════════════

# 1. We use the data_p0 we generated in the previous inference cell
# (If you haven't run it, make sure to run: data_p0 = analyze_match_rewards(env, 0))

total_dense_reward = sum(m.get('total', 0) for m in data_p0)
total_cap_bonus = sum(m.get('cap_bonus', 0) for m in data_p0)
total_loss_pen = sum(m.get('loss_pen', 0) for m in data_p0)
total_prod_delta = sum(m.get('prod_delta', 0) for m in data_p0)

# Terminal reward is only on the last step
terminal_reward = data_p0[-1].get('terminal', 0) if data_p0 else 0

print("=== REWARD INFLATION DIAGNOSTIC ===")
print(f"Kaggle Final Score: {p0_reward} (Win=1, Loss=-1)")
print(f"Cumulative Dense Reward (What PPO saw): {total_dense_reward:.2f}")
print("-----------------------------------")
print(f"Sum of Capture Bonuses:  +{total_cap_bonus:.2f}")
print(f"Sum of Loss Penalties:    {total_loss_pen:.2f}")
print(f"Net Capture/Loss Score:   {(total_cap_bonus + total_loss_pen):.2f}")
print(f"Sum of Production Delta:  {total_prod_delta:.2f}")
print(f"Terminal Dense Bonus:     {terminal_reward:.2f}")
print("===================================")

if total_cap_bonus > 1000 or total_loss_pen < -1000:
    print("\n⚠️ WARNING: Massive Capture/Loss numbers detected.")
    print("Your agent might be 'farming' planet captures by trading them back and forth with the enemy.")
```
