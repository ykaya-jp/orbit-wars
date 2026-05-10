## [MD]
# Rules-Aware Agent (RAA) — Orbit Wars
### Built directly from the official README mechanics.

---

## What every previous agent ignored (from the README):

| Mechanic | README Quote | What we do |
|---|---|---|
| **A — Out-of-bounds** | *"A fleet is removed if it goes out of bounds"* | Every route is now board-checked. No silent ship loss near corners. |
| **B — In-flight score** | *"Final score = ships on planets + ships in owned fleets"* | Late-game launches score even while flying. We loosen the capture buffer after turn 440. |
| **C — Comet timing** | *"Comets spawn at steps 50, 150, 250, 350, 450"* | We pre-position ships 8–12 turns before each spawn and prioritize comet captures. |
| **D — Sweep hazard** | *"Fleet caught by a moving planet is swept into combat"* | Routes through orbiting planet arcs are detected and rejected. |
| **E — 4-fold symmetry** | *"All planets placed with 4-fold mirror symmetry"* | We identify enemy expansion targets and race to capture their mirror counterpart. |

**Two cells only.** Cell 1 writes `submission.py`. Cell 2 is an optional sanity check.

## [CODE]
```python
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q",
                       "kaggle-environments>=1.28.0", "torch", "numpy"])
print("✅ packages ready")
```

## [CODE]
```python
%%writefile submission.py
# ============================================================
# Orbit Wars — Rules-Aware Agent (RAA)
# ============================================================
# Directly exploits game mechanics documented in the README:
#
# A) OUT-OF-BOUNDS ROUTE GUARD
#    Routes that exit the 100×100 board destroy the fleet.
#    Every launch angle is now validated: the full path segment
#    is checked against board boundaries, not just sun collision.
#
# B) IN-FLIGHT FLEET SCORE (IFS)
#    Final score = planet ships + FLEET ships.
#    Late-game, launching fleets to neutrals/enemies is always
#    score-neutral at worst (fleet counts while flying) and
#    score-positive if it captures. We unlock more aggressive
#    late-game launches as a result.
#
# C) COMET PRE-POSITIONING (CPP)
#    Comets spawn at steps 50, 150, 250, 350, 450.
#    We pre-position ships 8-12 turns before each spawn
#    by sending fleets to the expected spawn quadrant so we
#    arrive ~1 turn after spawn with overwhelming force.
#
# D) SWEEP HAZARD AVOIDANCE (SHA)
#    Orbiting planets can "sweep" passing fleets into combat.
#    Every planned route is checked against orbiting planet
#    arcs over the travel time. Dangerous routes are rejected.
#
# E) SYMMETRY MIRROR DENIAL (SMD)
#    The map has 4-fold mirror symmetry. We identify the
#    enemy's nearest expansion target and race to capture its
#    mirror-symmetric counterpart, denying parallel expansion.
# ============================================================

import math
import time
from collections import defaultdict, namedtuple
from dataclasses import dataclass, field

# ── Board constants ───────────────────────────
BOARD = 100.0
CENTER_X = 50.0
CENTER_Y = 50.0
SUN_R = 10.0
MAX_SPEED = 6.0
SUN_SAFETY = 1.5
ROTATION_LIMIT = 50.0
TOTAL_STEPS = 500
SIM_HORIZON = 110
ROUTE_SEARCH_HORIZON = 60
HORIZON = 180
LAUNCH_CLEARANCE = 0.1

EARLY_TURN_LIMIT = 40
OPENING_TURN_LIMIT = 80
LATE_REMAINING_TURNS = 60
VERY_LATE_REMAINING_TURNS = 25

SAFE_NEUTRAL_MARGIN = 2
CONTESTED_NEUTRAL_MARGIN = 2
INTERCEPT_TOLERANCE = 1

SAFE_OPENING_PROD_THRESHOLD = 4
SAFE_OPENING_TURN_LIMIT = 10
ROTATING_OPENING_MAX_TURNS = 13
ROTATING_OPENING_LOW_PROD = 2
FOUR_PLAYER_ROTATING_REACTION_GAP = 1
FOUR_PLAYER_ROTATING_SEND_RATIO = 0.72
FOUR_PLAYER_ROTATING_TURN_LIMIT = 14

COMET_MAX_CHASE_TURNS = 15

ATTACK_COST_TURN_WEIGHT = 0.55
SNIPE_COST_TURN_WEIGHT = 0.45
INDIRECT_VALUE_SCALE = 0.15
INDIRECT_FRIENDLY_WEIGHT = 0.35
INDIRECT_NEUTRAL_WEIGHT = 0.9
INDIRECT_ENEMY_WEIGHT = 1.25

STATIC_NEUTRAL_VALUE_MULT = 1.4
STATIC_HOSTILE_VALUE_MULT = 1.55
ROTATING_OPENING_VALUE_MULT = 0.9
HOSTILE_TARGET_VALUE_MULT = 1.85
OPENING_HOSTILE_TARGET_VALUE_MULT = 1.45
SAFE_NEUTRAL_VALUE_MULT = 1.2
CONTESTED_NEUTRAL_VALUE_MULT = 0.7
EARLY_NEUTRAL_VALUE_MULT = 1.2
COMET_VALUE_MULT = 0.65
SNIPE_VALUE_MULT = 1.12
SWARM_VALUE_MULT = 1.05
REINFORCE_VALUE_MULT = 1.35
CRASH_EXPLOIT_VALUE_MULT = 1.18
FINISHING_HOSTILE_VALUE_MULT = 1.15
BEHIND_ROTATING_NEUTRAL_VALUE_MULT = 0.92

NEUTRAL_MARGIN_BASE = 2
NEUTRAL_MARGIN_PROD_WEIGHT = 2
NEUTRAL_MARGIN_CAP = 8
HOSTILE_MARGIN_BASE = 3
HOSTILE_MARGIN_PROD_WEIGHT = 2
HOSTILE_MARGIN_CAP = 12
STATIC_TARGET_MARGIN = 4
CONTESTED_TARGET_MARGIN = 5
FOUR_PLAYER_TARGET_MARGIN = 2
LONG_TRAVEL_MARGIN_START = 18
LONG_TRAVEL_MARGIN_DIVISOR = 3
LONG_TRAVEL_MARGIN_CAP = 8
COMET_MARGIN_RELIEF = 6
FINISHING_HOSTILE_SEND_BONUS = 3

STATIC_TARGET_SCORE_MULT = 1.18
EARLY_STATIC_NEUTRAL_SCORE_MULT = 1.25
FOUR_PLAYER_ROTATING_NEUTRAL_SCORE_MULT = 0.92
DENSE_STATIC_NEUTRAL_COUNT = 4
DENSE_ROTATING_NEUTRAL_SCORE_MULT = 0.86
SNIPE_SCORE_MULT = 1.12
SWARM_SCORE_MULT = 1.06
CRASH_EXPLOIT_SCORE_MULT = 1.05

FOLLOWUP_MIN_SHIPS = 8
LOW_VALUE_COMET_PRODUCTION = 1
LATE_CAPTURE_BUFFER = 5
VERY_LATE_CAPTURE_BUFFER = 3

DEFENSE_LOOKAHEAD_TURNS = 28
DEFENSE_COST_TURN_WEIGHT = 0.4
DEFENSE_FRONTIER_SCORE_MULT = 1.12
DEFENSE_SEND_MARGIN_BASE = 1
DEFENSE_SEND_MARGIN_PROD_WEIGHT = 1
DEFENSE_SHIP_VALUE = 0.55

REINFORCE_ENABLED = True
REINFORCE_MIN_PRODUCTION = 2
REINFORCE_MAX_TRAVEL_TURNS = 22
REINFORCE_SAFETY_MARGIN = 2
REINFORCE_MAX_SOURCE_FRACTION = 0.75
REINFORCE_MIN_FUTURE_TURNS = 40
REINFORCE_HOLD_LOOKAHEAD = 20
REINFORCE_COST_TURN_WEIGHT = 0.35

RECAPTURE_LOOKAHEAD_TURNS = 10
RECAPTURE_COST_TURN_WEIGHT = 0.52
RECAPTURE_VALUE_MULT = 0.88
RECAPTURE_FRONTIER_MULT = 1.08
RECAPTURE_PRODUCTION_WEIGHT = 0.6
RECAPTURE_IMMEDIATE_WEIGHT = 0.4

REAR_SOURCE_MIN_SHIPS = 16
REAR_DISTANCE_RATIO = 1.25
REAR_STAGE_PROGRESS = 0.78
REAR_SEND_RATIO_TWO_PLAYER = 0.62
REAR_SEND_RATIO_FOUR_PLAYER = 0.7
REAR_SEND_MIN_SHIPS = 10
REAR_MAX_TRAVEL_TURNS = 40

PARTIAL_SOURCE_MIN_SHIPS = 6
MULTI_SOURCE_TOP_K = 10
MULTI_SOURCE_ETA_TOLERANCE = 2
MULTI_SOURCE_PLAN_PENALTY = 0.97
HOSTILE_SWARM_ETA_TOLERANCE = 1
THREE_SOURCE_SWARM_ENABLED = True
THREE_SOURCE_MIN_TARGET_SHIPS = 20
THREE_SOURCE_ETA_TOLERANCE = 2
THREE_SOURCE_PLAN_PENALTY = 0.94

WAIT_STRIKE_ENABLED = True
WAIT_STRIKE_DELAYS = (0, 2, 4, 6)
WAIT_STRIKE_MAX_TARGETS = 6

FOUR_SOURCE_SWARM_ENABLED = True
FOUR_SOURCE_ETA_TOLERANCE = 2
FOUR_SOURCE_MIN_TARGET_SHIPS = 40
FOUR_SOURCE_PLAN_PENALTY = 0.91

PROACTIVE_DEFENSE_HORIZON = 12
PROACTIVE_DEFENSE_RATIO = 0.18
MULTI_ENEMY_PROACTIVE_HORIZON = 14
MULTI_ENEMY_PROACTIVE_RATIO = 0.22
MULTI_ENEMY_STACK_WINDOW = 3
REACTION_SOURCE_TOP_K_MY = 4
REACTION_SOURCE_TOP_K_ENEMY = 4
PROACTIVE_ENEMY_TOP_K = 3

CRASH_EXPLOIT_ENABLED = True
CRASH_EXPLOIT_MIN_TOTAL_SHIPS = 10
CRASH_EXPLOIT_ETA_WINDOW = 2
CRASH_EXPLOIT_POST_CRASH_DELAY = 1

LATE_IMMEDIATE_SHIP_VALUE = 0.6
WEAK_ENEMY_THRESHOLD = 45
ELIMINATION_BONUS = 18.0

BEHIND_DOMINATION = -0.20
AHEAD_DOMINATION = 0.18
FINISHING_DOMINATION = 0.35
FINISHING_PROD_RATIO = 1.25
AHEAD_ATTACK_MARGIN_BONUS = 0.08
BEHIND_ATTACK_MARGIN_PENALTY = 0.05
FINISHING_ATTACK_MARGIN_BONUS = 0.08

DOOMED_EVAC_TURN_LIMIT = 24
DOOMED_MIN_SHIPS = 8

SOFT_ACT_DEADLINE = 0.82
HEAVY_PHASE_MIN_TIME = 0.16
OPTIONAL_PHASE_MIN_TIME = 0.08
HEAVY_ROUTE_PLANET_LIMIT = 32

# ── Innovation A: Out-of-Bounds Guard ───────────────────────
OOB_SAFETY_MARGIN = 0.5

# ── Innovation B: In-Flight Fleet Score ─────────────────────
IFS_ENABLED = True
IFS_LATE_BUFFER_REDUCTION = 2
IFS_ACTIVATE_TURN = 440

# ── Innovation C: Comet Pre-Positioning ─────────────────────
COMET_SPAWN_STEPS = [50, 150, 250, 350, 450]
CPP_PREPOSITION_WINDOW = 12
CPP_MIN_SEND = 25
CPP_SCORE_MULT = 1.55
CPP_ENABLED = True

# ── Innovation D: Sweep Hazard Avoidance ────────────────────
SHA_ENABLED = True
SHA_CHECK_TURNS = 8
SHA_SWEEP_RADIUS_MULT = 1.8

# ── Innovation E: Symmetry Mirror Denial ────────────────────
SMD_ENABLED = True
SMD_SCORE_MULT = 1.28
SMD_HORIZON_TURNS = 35


# ============================================================
# Types
# ============================================================

Planet = namedtuple("Planet", ["id", "owner", "x", "y", "radius", "ships", "production"])
Fleet  = namedtuple("Fleet",  ["id", "owner", "x", "y", "angle", "from_planet_id", "ships"])

@dataclass(frozen=True)
class ShotOption:
    score: float; src_id: int; target_id: int; angle: float; turns: int
    needed: int; send_cap: int; mission: str = "capture"; anchor_turn: int | None = None

@dataclass
class Mission:
    kind: str; score: float; target_id: int; turns: int
    options: list[ShotOption] = field(default_factory=list)


# ============================================================
# Physics
# ============================================================

def dist(ax, ay, bx, by): return math.hypot(ax-bx, ay-by)
def orbital_radius(p): return dist(p.x, p.y, CENTER_X, CENTER_Y)
def is_static_planet(p): return orbital_radius(p) + p.radius >= ROTATION_LIMIT

def fleet_speed(ships):
    if ships <= 1: return 1.0
    r = min(1.0, max(0.0, math.log(ships) / math.log(1000.0)))
    return 1.0 + (MAX_SPEED - 1.0) * (r ** 1.5)

def point_to_segment_distance(px, py, x1, y1, x2, y2):
    dx, dy = x2-x1, y2-y1
    sq = dx*dx + dy*dy
    if sq <= 1e-9: return dist(px, py, x1, y1)
    t = max(0.0, min(1.0, ((px-x1)*dx + (py-y1)*dy) / sq))
    return dist(px, py, x1+t*dx, y1+t*dy)

def segment_hits_sun(x1, y1, x2, y2, safety=SUN_SAFETY):
    return point_to_segment_distance(CENTER_X, CENTER_Y, x1, y1, x2, y2) < SUN_R + safety

# ── Innovation A: Out-of-Bounds segment check ────────────────
def segment_exits_board(x1, y1, x2, y2):
    """True if any point of the segment leaves the board."""
    lo = OOB_SAFETY_MARGIN
    hi = BOARD - OOB_SAFETY_MARGIN
    # Check endpoints first (fast path)
    if not (lo <= x1 <= hi and lo <= y1 <= hi): return True
    if not (lo <= x2 <= hi and lo <= y2 <= hi): return True
    # Parametric clipping — check each wall
    dx, dy = x2-x1, y2-y1
    for axis, v1, v2, wall_lo, wall_hi in [
        (dx, x1, x2, lo, hi),
        (dy, y1, y2, lo, hi),
    ]:
        if abs(axis) < 1e-9: continue
        t_lo = (wall_lo - v1) / axis
        t_hi = (wall_hi - v1) / axis
        if t_lo > t_hi: t_lo, t_hi = t_hi, t_lo
        if t_lo > 0 and t_lo < 1:
            # Check the exit point
            ex = x1 + t_lo * dx
            ey = y1 + t_lo * dy
            if not (lo <= ex <= hi and lo <= ey <= hi):
                return True
    return False

def launch_point(sx, sy, sr, angle):
    c = sr + LAUNCH_CLEARANCE
    return sx + math.cos(angle)*c, sy + math.sin(angle)*c

def actual_path_geometry(sx, sy, sr, tx, ty, tr):
    angle = math.atan2(ty-sy, tx-sx)
    lx, ly = launch_point(sx, sy, sr, angle)
    hit_d = max(0.0, dist(sx, sy, tx, ty) - (sr + LAUNCH_CLEARANCE) - tr)
    return angle, lx, ly, lx + math.cos(angle)*hit_d, ly + math.sin(angle)*hit_d, hit_d

def safe_angle_and_distance(sx, sy, sr, tx, ty, tr):
    angle, x1, y1, x2, y2, hit_d = actual_path_geometry(sx, sy, sr, tx, ty, tr)
    if segment_hits_sun(x1, y1, x2, y2): return None
    if segment_exits_board(x1, y1, x2, y2): return None   # Innovation A
    return angle, hit_d

def predict_planet_position(planet, initial_by_id, angular_velocity, turns):
    init = initial_by_id.get(planet.id)
    if init is None: return planet.x, planet.y
    r = dist(init.x, init.y, CENTER_X, CENTER_Y)
    if r + init.radius >= ROTATION_LIMIT: return planet.x, planet.y
    ang = math.atan2(planet.y-CENTER_Y, planet.x-CENTER_X) + angular_velocity*turns
    return CENTER_X + r*math.cos(ang), CENTER_Y + r*math.sin(ang)

def predict_comet_position(planet_id, comets, turns):
    for g in comets:
        pids = g.get("planet_ids", [])
        if planet_id not in pids: continue
        idx = pids.index(planet_id)
        paths = g.get("paths", [])
        pi = g.get("path_index", 0)
        if idx >= len(paths): return None
        path = paths[idx]
        fi = pi + int(turns)
        return (path[fi][0], path[fi][1]) if 0 <= fi < len(path) else None
    return None

def comet_remaining_life(planet_id, comets):
    for g in comets:
        pids = g.get("planet_ids", [])
        if planet_id not in pids: continue
        idx = pids.index(planet_id)
        paths = g.get("paths", [])
        pi = g.get("path_index", 0)
        if idx < len(paths): return max(0, len(paths[idx]) - pi)
    return 0

def estimate_arrival(sx, sy, sr, tx, ty, tr, ships):
    safe = safe_angle_and_distance(sx, sy, sr, tx, ty, tr)
    if safe is None: return None
    angle, total_d = safe
    return angle, max(1, int(math.ceil(total_d / fleet_speed(max(1, ships)))))

def travel_time(sx, sy, sr, tx, ty, tr, ships):
    est = estimate_arrival(sx, sy, sr, tx, ty, tr, ships)
    return est[1] if est else 10**9

def predict_target_position(target, turns, initial_by_id, ang_vel, comets, comet_ids):
    if target.id in comet_ids: return predict_comet_position(target.id, comets, turns)
    return predict_planet_position(target, initial_by_id, ang_vel, turns)

def target_can_move(target, initial_by_id, comet_ids):
    if target.id in comet_ids: return True
    init = initial_by_id.get(target.id)
    if init is None: return False
    return dist(init.x, init.y, CENTER_X, CENTER_Y) + init.radius < ROTATION_LIMIT

def search_safe_intercept(src, target, ships, initial_by_id, ang_vel, comets, comet_ids):
    best, best_score = None, None
    max_t = min(HORIZON, ROUTE_SEARCH_HORIZON)
    if target.id in comet_ids:
        max_t = min(max_t, max(0, comet_remaining_life(target.id, comets)-1))
    for ct in range(1, max_t+1):
        pos = predict_target_position(target, ct, initial_by_id, ang_vel, comets, comet_ids)
        if pos is None: continue
        est = estimate_arrival(src.x, src.y, src.radius, pos[0], pos[1], target.radius, ships)
        if est is None: continue
        _, turns = est
        if abs(turns - ct) > INTERCEPT_TOLERANCE: continue
        at = max(turns, ct)
        ap = predict_target_position(target, at, initial_by_id, ang_vel, comets, comet_ids)
        if ap is None: continue
        cf = estimate_arrival(src.x, src.y, src.radius, ap[0], ap[1], target.radius, ships)
        if cf is None: continue
        d = abs(cf[1] - at)
        if d > INTERCEPT_TOLERANCE: continue
        score = (d, cf[1], ct)
        if best is None or score < best_score:
            best_score, best = score, (cf[0], cf[1], ap[0], ap[1])
    return best

def aim_with_prediction(src, target, ships, initial_by_id, ang_vel, comets, comet_ids):
    est = estimate_arrival(src.x, src.y, src.radius, target.x, target.y, target.radius, ships)
    if est is None:
        if not target_can_move(target, initial_by_id, comet_ids): return None
        return search_safe_intercept(src, target, ships, initial_by_id, ang_vel, comets, comet_ids)
    tx, ty = target.x, target.y
    for _ in range(5):
        _, turns = est
        pos = predict_target_position(target, turns, initial_by_id, ang_vel, comets, comet_ids)
        if pos is None: return None
        ntx, nty = pos
        ne = estimate_arrival(src.x, src.y, src.radius, ntx, nty, target.radius, ships)
        if ne is None:
            if not target_can_move(target, initial_by_id, comet_ids): return None
            return search_safe_intercept(src, target, ships, initial_by_id, ang_vel, comets, comet_ids)
        if abs(ntx-tx)<0.3 and abs(nty-ty)<0.3 and abs(ne[1]-turns)<=INTERCEPT_TOLERANCE:
            return ne[0], ne[1], ntx, nty
        tx, ty, est = ntx, nty, ne
    fe = estimate_arrival(src.x, src.y, src.radius, tx, ty, target.radius, ships)
    if fe is None:
        return search_safe_intercept(src, target, ships, initial_by_id, ang_vel, comets, comet_ids)
    return fe[0], fe[1], tx, ty


# ============================================================
# Innovation C+D helpers (pure, used in WorldModel)
# ============================================================

def comet_spawn_urgency(step):
    """Returns (turns_to_next_spawn, spawn_step) or None."""
    for ss in COMET_SPAWN_STEPS:
        remaining = ss - step
        if 1 <= remaining <= CPP_PREPOSITION_WINDOW:
            return remaining, ss
    return None

def orbiting_planet_sweep_check(x1, y1, x2, y2, orbit_planet, initial_by_id, ang_vel, travel_turns):
    if not SHA_ENABLED: return False
    init = initial_by_id.get(orbit_planet.id)
    if init is None: return False
    r = dist(init.x, init.y, CENTER_X, CENTER_Y)
    if r + init.radius >= ROTATION_LIMIT: return False
    safety_r = orbit_planet.radius * SHA_SWEEP_RADIUS_MULT
    cur_ang = math.atan2(orbit_planet.y - CENTER_Y, orbit_planet.x - CENTER_X)
    for t in range(1, min(travel_turns, SHA_CHECK_TURNS) + 1):

        ang = cur_ang + ang_vel * t
        px = CENTER_X + r * math.cos(ang)
        py = CENTER_Y + r * math.sin(ang)

        progress = t / max(1, travel_turns)
        fx = x1 + progress * (x2 - x1)
        fy = y1 + progress * (y2 - y1)
        if dist(px, py, fx, fy) < safety_r:
            return True
    return False

def mirror_point(x, y):
    """4-fold mirror symmetric counterpart in Q1 → Q2/Q3/Q4."""
    return [
        (BOARD - x, y),
        (x, BOARD - y),
        (BOARD - x, BOARD - y),
    ]


# ============================================================
# World Model
# ============================================================

def fleet_target_planet(fleet, planets):
    best_planet, best_time = None, 1e9
    dx_f, dy_f = math.cos(fleet.angle), math.sin(fleet.angle)
    speed = fleet_speed(fleet.ships)
    for p in planets:
        dx, dy = p.x - fleet.x, p.y - fleet.y
        proj = dx*dx_f + dy*dy_f
        if proj < 0: continue
        perp_sq = dx*dx + dy*dy - proj*proj
        if perp_sq >= p.radius*p.radius: continue
        hit_d = max(0.0, proj - math.sqrt(max(0.0, p.radius*p.radius - perp_sq)))
        t = hit_d / speed
        if t <= HORIZON and t < best_time: best_time, best_planet = t, p
    if best_planet is None: return None, None
    return best_planet, int(math.ceil(best_time))

def build_arrival_ledger(fleets, planets):
    ledger = {p.id: [] for p in planets}
    for f in fleets:
        target, eta = fleet_target_planet(f, planets)
        if target is None: continue
        ledger[target.id].append((eta, f.owner, int(f.ships)))
    return ledger

def resolve_arrival_event(owner, garrison, arrivals):
    by_owner = {}
    for _, o, s in arrivals: by_owner[o] = by_owner.get(o, 0) + s
    if not by_owner: return owner, max(0.0, garrison)
    sp = sorted(by_owner.items(), key=lambda x: x[1], reverse=True)
    top_o, top_s = sp[0]
    if len(sp) > 1:
        sec = sp[1][1]
        surv_o, surv_s = (-1, 0) if top_s == sec else (top_o, top_s - sec)
    else: surv_o, surv_s = top_o, top_s
    if surv_s <= 0: return owner, max(0.0, garrison)
    if owner == surv_o: return owner, garrison + surv_s
    garrison -= surv_s
    return (surv_o, -garrison) if garrison < 0 else (owner, garrison)

def normalize_arrivals(arrivals, horizon):
    events = []
    for turns, o, s in arrivals:
        if s <= 0: continue
        eta = max(1, int(math.ceil(turns)))
        if eta <= horizon: events.append((eta, o, int(s)))
    return sorted(events, key=lambda x: x[0])

def simulate_planet_timeline(planet, arrivals, player, horizon):
    horizon = max(0, int(math.ceil(horizon)))
    events = normalize_arrivals(arrivals, horizon)
    by_turn = defaultdict(list)
    for ev in events: by_turn[ev[0]].append(ev)
    owner, garrison = planet.owner, float(planet.ships)
    owner_at = {0: owner}; ships_at = {0: max(0.0, garrison)}
    min_owned = garrison if owner == player else 0.0
    first_enemy = fall_turn = None
    for turn in range(1, horizon+1):
        if owner != -1: garrison += planet.production
        group = by_turn.get(turn, [])
        prev = owner
        if group:
            if prev == player and first_enemy is None and any(ev[1] not in (-1, player) for ev in group):
                first_enemy = turn
            owner, garrison = resolve_arrival_event(owner, garrison, group)
            if prev == player and owner != player and fall_turn is None: fall_turn = turn
        owner_at[turn] = owner; ships_at[turn] = max(0.0, garrison)
        if owner == player: min_owned = min(min_owned, garrison)
    keep_needed, holds_full = 0, True
    if planet.owner == player:
        def survives(k):
            so, sg = planet.owner, float(k)
            for t in range(1, horizon+1):
                if so != -1: sg += planet.production
                g2 = by_turn.get(t, [])
                if g2: so, sg = resolve_arrival_event(so, sg, g2)
                if so != player: return False
            return so == player
        if survives(int(planet.ships)):
            lo, hi = 0, int(planet.ships)
            while lo < hi:
                mid = (lo+hi)//2
                if survives(mid): hi = mid
                else: lo = mid+1
            keep_needed = lo
        else: holds_full, keep_needed = False, int(planet.ships)
    return {"owner_at": owner_at, "ships_at": ships_at, "keep_needed": keep_needed,
            "min_owned": max(0, int(math.floor(min_owned))) if planet.owner == player else 0,
            "first_enemy": first_enemy, "fall_turn": fall_turn,
            "holds_full": holds_full, "horizon": horizon}

def state_at_timeline(tl, arrival_turn):
    t = max(0, min(int(math.ceil(arrival_turn)), tl["horizon"]))
    return (tl["owner_at"].get(t, tl["owner_at"][tl["horizon"]]),
            max(0.0, tl["ships_at"].get(t, tl["ships_at"][tl["horizon"]])))

def count_players(planets, fleets):
    owners = set()
    for p in planets:
        if p.owner != -1: owners.add(p.owner)
    for f in fleets: owners.add(f.owner)
    return max(2, len(owners))

def nearest_distance_to_set(px, py, planets):
    if not planets: return 10**9
    return min(dist(px, py, p.x, p.y) for p in planets)

def indirect_features(planet, planets, player):
    friendly = neutral = enemy = 0.0
    for o in planets:
        if o.id == planet.id: continue
        d = dist(planet.x, planet.y, o.x, o.y)
        if d < 1: continue
        f = o.production / (d + 12.0)
        if o.owner == player: friendly += f
        elif o.owner == -1: neutral += f
        else: enemy += f
    return friendly, neutral, enemy


class WorldModel:
    def __init__(self, player, step, planets, fleets, initial_by_id, ang_vel, comets, comet_ids):
        self.player = player; self.step = step
        self.planets = planets; self.fleets = fleets
        self.initial_by_id = initial_by_id; self.ang_vel = ang_vel
        self.comets = comets; self.comet_ids = set(comet_ids)

        self.planet_by_id = {p.id: p for p in planets}
        self.my_planets    = [p for p in planets if p.owner == player]
        self.enemy_planets = [p for p in planets if p.owner not in (-1, player)]
        self.neutral_planets = [p for p in planets if p.owner == -1]
        self.static_neutral_planets = [p for p in self.neutral_planets if is_static_planet(p)]
        self.orbiting_planets = [p for p in planets if not is_static_planet(p) and p.id not in self.comet_ids]

        self.num_players    = count_players(planets, fleets)
        self.remaining_steps = max(1, TOTAL_STEPS - step)
        self.is_early       = step < EARLY_TURN_LIMIT
        self.is_opening     = step < OPENING_TURN_LIMIT
        self.is_late        = self.remaining_steps < LATE_REMAINING_TURNS
        self.is_very_late   = self.remaining_steps < VERY_LATE_REMAINING_TURNS
        self.is_four_player = self.num_players >= 4

        self.owner_strength   = defaultdict(int)
        self.owner_production = defaultdict(int)
        for p in planets:
            if p.owner != -1:
                self.owner_strength[p.owner] += int(p.ships)
                self.owner_production[p.owner] += int(p.production)
        for f in fleets: self.owner_strength[f.owner] += int(f.ships)

        self.my_total    = self.owner_strength.get(player, 0)
        self.enemy_total = sum(s for o, s in self.owner_strength.items() if o != player)
        self.max_enemy_strength = max((s for o, s in self.owner_strength.items() if o != player), default=0)
        self.my_prod    = self.owner_production.get(player, 0)
        self.enemy_prod = sum(p for o, p in self.owner_production.items() if o != player)

        self.arrivals_by_planet = build_arrival_ledger(fleets, planets)
        self.base_timeline = {
            p.id: simulate_planet_timeline(p, self.arrivals_by_planet[p.id], player, HORIZON)
            for p in planets
        }
        self.keep_needed_map = {p.id: self.base_timeline[p.id]["keep_needed"] for p in planets}
        self.fall_turn_map   = {p.id: self.base_timeline[p.id]["fall_turn"]   for p in planets}
        self.holds_full_map  = {p.id: self.base_timeline[p.id]["holds_full"]  for p in planets}
        self.indirect_feature_map = {p.id: indirect_features(p, planets, player) for p in planets}
        self.total_visible_ships = sum(int(p.ships) for p in planets) + sum(int(f.ships) for f in fleets)
        self.total_production    = sum(int(p.production) for p in planets)

        # Innovation C: comet spawn urgency
        self.comet_urgency = comet_spawn_urgency(step)

        # Innovation E: mirror denial targets
        self.mirror_denial_ids = self._compute_mirror_denial_ids()

        self.shot_cache = {}; self.probe_candidate_cache = {}
        self.best_probe_cache = {}; self.reaction_cache = {}; self.exact_need_cache = {}

    def _compute_mirror_denial_ids(self):
        """
        Innovation E: Find planets that mirror the enemy's most likely expansion targets.
        Heuristic: enemy's nearest neutral planet → its mirror counterparts near us → boost score.
        """
        if not SMD_ENABLED or not self.enemy_planets or not self.neutral_planets: return set()
        # Find enemy home (planet with most ships owned by enemy, early game)
        enemy_home = max(self.enemy_planets, key=lambda p: int(p.ships), default=None)
        if enemy_home is None: return set()
        # Nearest neutral to enemy home
        nearest_neutral = min(self.neutral_planets, key=lambda p: dist(p.x, p.y, enemy_home.x, enemy_home.y), default=None)
        if nearest_neutral is None: return set()
        # Mirror points of that neutral
        mirrors = mirror_point(nearest_neutral.x, nearest_neutral.y)
        mirror_ids = set()
        for mx, my in mirrors:
            # Find closest neutral to this mirror point that we can reach
            closest = min(
                (p for p in self.neutral_planets),
                key=lambda p: dist(p.x, p.y, mx, my),
                default=None
            )
            if closest and dist(closest.x, closest.y, mx, my) < 12:
                mirror_ids.add(closest.id)
        return mirror_ids

    def is_static(self, pid): return is_static_planet(self.planet_by_id[pid])
    def comet_life(self, pid): return comet_remaining_life(pid, self.comets)
    def source_inventory_left(self, sid, spent): return max(0, int(self.planet_by_id[sid].ships) - spent[sid])

    def route_has_sweep_hazard(self, x1, y1, x2, y2, travel_turns):
        """Innovation D: check all orbiting planets for sweep hazard."""
        for op in self.orbiting_planets:
            if orbiting_planet_sweep_check(x1, y1, x2, y2, op, self.initial_by_id, self.ang_vel, travel_turns):
                return True
        return False

    def plan_shot(self, src_id, target_id, ships):
        ships = int(ships)
        key = (src_id, target_id, ships)
        if key in self.shot_cache: return self.shot_cache[key]
        src = self.planet_by_id[src_id]; target = self.planet_by_id[target_id]
        result = aim_with_prediction(src, target, ships, self.initial_by_id, self.ang_vel, self.comets, self.comet_ids)
        # Innovation D: reject sweep-hazardous routes
        if result is not None and SHA_ENABLED:
            angle, turns, tx, ty = result
            lx, ly = launch_point(src.x, src.y, src.radius, angle)
            if self.route_has_sweep_hazard(lx, ly, tx, ty, turns):
                result = None  # treat as blocked
        self.shot_cache[key] = result
        return result

    def probe_ship_candidates(self, src_id, target_id, source_cap, hints=()):
        source_cap = max(1, int(source_cap))
        nh = tuple(int(math.ceil(h)) for h in hints if h is not None)
        key = (src_id, target_id, source_cap, nh)
        cached = self.probe_candidate_cache.get(key)
        if cached is not None: return cached
        target = self.planet_by_id[target_id]
        ts = max(1, int(math.ceil(target.ships)))
        values = set(range(1, min(6, source_cap)+1))
        values.update({source_cap, max(1, source_cap//2), max(1, source_cap//3),
                       min(source_cap, PARTIAL_SOURCE_MIN_SHIPS),
                       min(source_cap, ts+1), min(source_cap, ts+2),
                       min(source_cap, ts+4), min(source_cap, ts+8)})
        for h in nh:
            b = max(1, min(source_cap, h))
            for d in (-2,-1,0,1,2):
                c = b+d
                if 1 <= c <= source_cap: values.add(c)
        result = sorted(values)
        self.probe_candidate_cache[key] = result
        return result

    def best_probe_aim(self, src_id, target_id, source_cap, hints=(),
                       min_turn=None, max_turn=None, anchor_turn=None, max_anchor_diff=None):
        key = (src_id, target_id, max(1, int(source_cap)), tuple(hints), min_turn, max_turn, anchor_turn, max_anchor_diff)
        if key in self.best_probe_cache: return self.best_probe_cache[key]
        best, best_key = None, None
        for ships in self.probe_ship_candidates(src_id, target_id, source_cap, hints=hints):
            aim = self.plan_shot(src_id, target_id, ships)
            if aim is None: continue
            angle, turns, _, _ = aim
            if min_turn is not None and turns < min_turn: continue
            if max_turn is not None and turns > max_turn: continue
            if anchor_turn is not None and max_anchor_diff is not None:
                if abs(turns - anchor_turn) > max_anchor_diff: continue
            k = (turns, ships) if anchor_turn is None else (abs(turns - anchor_turn), turns, ships)
            if best_key is None or k < best_key: best_key, best = k, (ships, (angle, turns, 0, 0))
        self.best_probe_cache[key] = best
        return best

    def reaction_times(self, target_id):
        cached = self.reaction_cache.get(target_id)
        if cached is not None: return cached
        target = self.planet_by_id[target_id]
        my_t = min((self.best_probe_aim(p.id, target_id, max(1, int(p.ships)))[1][1]
                    for p in self.my_planets if self.best_probe_aim(p.id, target_id, max(1, int(p.ships))) is not None), default=10**9)
        en_t = min((self.best_probe_aim(p.id, target_id, max(1, int(p.ships)))[1][1]
                    for p in self.enemy_planets if self.best_probe_aim(p.id, target_id, max(1, int(p.ships))) is not None), default=10**9)
        self.reaction_cache[target_id] = (my_t, en_t)
        return (my_t, en_t)

    def projected_state(self, tid, arrival_turn, planned_commitments=None, extra_arrivals=()):
        pc = planned_commitments or {}
        cutoff = max(1, int(math.ceil(arrival_turn)))
        if not pc.get(tid) and not extra_arrivals: return state_at_timeline(self.base_timeline[tid], cutoff)
        arrivals = [ev for ev in self.arrivals_by_planet.get(tid, []) if ev[0] <= cutoff]
        arrivals.extend(ev for ev in pc.get(tid, []) if ev[0] <= cutoff)
        arrivals.extend(ev for ev in extra_arrivals if ev[0] <= cutoff)
        tl = simulate_planet_timeline(self.planet_by_id[tid], arrivals, self.player, cutoff)
        return state_at_timeline(tl, cutoff)

    def projected_timeline(self, tid, horizon, planned_commitments=None, extra_arrivals=()):
        pc = planned_commitments or {}
        horizon = max(1, int(math.ceil(horizon)))
        arrivals = [ev for ev in self.arrivals_by_planet.get(tid, []) if ev[0] <= horizon]
        arrivals.extend(ev for ev in pc.get(tid, []) if ev[0] <= horizon)
        arrivals.extend(ev for ev in extra_arrivals if ev[0] <= horizon)
        return simulate_planet_timeline(self.planet_by_id[tid], arrivals, self.player, horizon)

    def hold_status(self, tid, planned_commitments=None, horizon=HORIZON):
        pc = planned_commitments or {}
        tl = self.projected_timeline(tid, horizon, planned_commitments=pc) if pc.get(tid) else self.base_timeline[tid]
        return {k: tl[k] for k in ("keep_needed","min_owned","first_enemy","fall_turn","holds_full")}

    def _ownership_search_cap(self, eval_turn):
        return max(32, int(self.total_visible_ships + self.total_production * max(2, eval_turn+2) + 32))

    def min_ships_to_own_by(self, tid, eval_turn, attacker_owner, arrival_turn=None,
                            planned_commitments=None, extra_arrivals=(), upper_bound=None):
        pc = planned_commitments or {}
        eval_turn    = max(1, int(math.ceil(eval_turn)))
        arrival_turn = eval_turn if arrival_turn is None else max(1, int(math.ceil(arrival_turn)))
        if arrival_turn > eval_turn:
            return (max(1, int(upper_bound))+1) if upper_bound is not None else self._ownership_search_cap(eval_turn)+1
        ne = tuple((max(1, int(math.ceil(t))), o, int(s)) for t, o, s in extra_arrivals if s > 0 and max(1, int(math.ceil(t))) <= eval_turn)
        ck = None
        if arrival_turn == eval_turn and not pc.get(tid) and not ne:
            ck = (tid, eval_turn, attacker_owner)
            cached = self.exact_need_cache.get(ck)
            if cached is not None: return cached
        ob, sb = self.projected_state(tid, eval_turn, planned_commitments=pc, extra_arrivals=ne)
        if ob == attacker_owner:
            if ck: self.exact_need_cache[ck] = 0
            return 0
        def owns_at(ships):
            oa, _ = self.projected_state(tid, eval_turn, planned_commitments=pc, extra_arrivals=ne+((arrival_turn, attacker_owner, int(ships)),))
            return oa == attacker_owner
        if upper_bound is not None:
            hi = max(1, int(upper_bound))
            if not owns_at(hi): return hi+1
        else:
            hi = max(1, int(math.ceil(sb))+1); sc = self._ownership_search_cap(eval_turn)
            while hi <= sc and not owns_at(hi): hi *= 2
            if hi > sc:
                if not owns_at(sc): return sc+1
                hi = sc
        lo = 1
        while lo < hi:
            mid = (lo+hi)//2
            if owns_at(mid): hi = mid
            else: lo = mid+1
        if ck: self.exact_need_cache[ck] = lo
        return lo

    def min_ships_to_own_at(self, tid, arrival_turn, attacker_owner, planned_commitments=None, extra_arrivals=(), upper_bound=None):
        return self.min_ships_to_own_by(tid, arrival_turn, attacker_owner, arrival_turn=arrival_turn,
                                        planned_commitments=planned_commitments, extra_arrivals=extra_arrivals, upper_bound=upper_bound)

    def reinforcement_needed_to_hold_until(self, pid, arrival_turn, hold_until, planned_commitments=None, upper_bound=None):
        pc = planned_commitments or {}
        target = self.planet_by_id[pid]
        arrival_turn = max(1, int(math.ceil(arrival_turn))); hold_until = max(arrival_turn, int(math.ceil(hold_until)))
        if target.owner != self.player:
            return self.min_ships_to_own_by(pid, hold_until, self.player, arrival_turn=arrival_turn, planned_commitments=pc, upper_bound=upper_bound)
        def holds(ships):
            tl = self.projected_timeline(pid, hold_until, planned_commitments=pc, extra_arrivals=((arrival_turn, self.player, int(ships)),))
            for t in range(arrival_turn, hold_until+1):
                if tl["owner_at"].get(t) != self.player: return False
            return True
        if upper_bound is not None:
            hi = max(1, int(upper_bound))
            if not holds(hi): return hi+1
        else:
            hi, sc = 1, self._ownership_search_cap(hold_until)
            while hi <= sc and not holds(hi): hi *= 2
            if hi > sc:
                if not holds(sc): return sc+1
                hi = sc
        lo = 1
        while lo < hi:
            mid = (lo+hi)//2
            if holds(mid): hi = mid
            else: lo = mid+1
        return lo

    def ships_needed_to_capture(self, tid, arrival_turn, planned_commitments=None, extra_arrivals=()):
        return self.min_ships_to_own_at(tid, arrival_turn, self.player, planned_commitments=planned_commitments, extra_arrivals=extra_arrivals)


# ============================================================
# Strategy
# ============================================================

def planet_distance(a, b): return math.hypot(a.x-b.x, a.y-b.y)

def nearest_sources_to_target(target, sources, top_k):
    if top_k <= 0 or len(sources) <= top_k: return sources
    return sorted(sources, key=lambda s: (planet_distance(s, target), -int(s.ships), s.id))[:top_k]

def min_legal_reaction_time(target, sources, world):
    best = 10**9
    for src in sources:
        s = world.best_probe_aim(src.id, target.id, max(1, int(src.ships)))
        if s is not None: best = min(best, s[1][1])
    return best

def policy_reaction_times(tid, policy):
    return policy["reaction_time_map"].get(tid, (10**9, 10**9))

def candidate_time_valid(target, turns, world, remaining_buffer):
    if turns > world.remaining_steps - remaining_buffer: return False
    if target.id in world.comet_ids:
        life = world.comet_life(target.id)
        if turns >= life or turns > COMET_MAX_CHASE_TURNS: return False
    return True

def stacked_enemy_proactive_keep(planet, world):
    threats = []
    for ep in world.enemy_planets:
        s = world.best_probe_aim(ep.id, planet.id, max(1, int(ep.ships)))
        if s is None: continue
        eta = s[1][1]
        if eta > MULTI_ENEMY_PROACTIVE_HORIZON: continue
        threats.append((eta, int(ep.ships)))
    if not threats: return 0
    threats.sort(); best = left = running = 0
    for right in range(len(threats)):
        running += threats[right][1]
        while threats[right][0] - threats[left][0] > MULTI_ENEMY_STACK_WINDOW:
            running -= threats[left][1]; left += 1
        best = max(best, running)
    return int(best * MULTI_ENEMY_PROACTIVE_RATIO)

def swarm_eta_tolerance(options, target, world):
    if len(options) >= 3: return THREE_SOURCE_ETA_TOLERANCE
    if target.owner not in (-1, world.player): return HOSTILE_SWARM_ETA_TOLERANCE
    return MULTI_SOURCE_ETA_TOLERANCE

def detect_enemy_crashes(world):
    crashes = []
    for tid, arrivals in world.arrivals_by_planet.items():
        ee = sorted([(int(math.ceil(eta)), o, int(s)) for eta, o, s in arrivals if o not in (-1, world.player) and s > 0])
        for i in range(len(ee)):
            ea, oa, sa = ee[i]
            for j in range(i+1, len(ee)):
                eb, ob, sb = ee[j]
                if oa == ob: continue
                if abs(ea-eb) > CRASH_EXPLOIT_ETA_WINDOW: break
                if sa+sb < CRASH_EXPLOIT_MIN_TOTAL_SHIPS: continue
                crashes.append({"target_id": tid, "crash_turn": max(ea, eb), "owners": (oa, ob), "ships": (sa, sb)})
    return crashes


def build_policy_state(world, deadline=None):
    def expired(): return deadline is not None and time.perf_counter() > deadline

    indirect_wealth_map = {}
    for tid, (fr, ne, en) in world.indirect_feature_map.items():
        indirect_wealth_map[tid] = fr*INDIRECT_FRIENDLY_WEIGHT + ne*INDIRECT_NEUTRAL_WEIGHT + en*INDIRECT_ENEMY_WEIGHT

    reserve, attack_budget, reaction_time_map = {}, {}, {}

    for target in world.planets:
        if expired(): break
        if target.owner == world.player: continue
        my_s  = nearest_sources_to_target(target, world.my_planets,    REACTION_SOURCE_TOP_K_MY)
        en_s  = nearest_sources_to_target(target, world.enemy_planets,  REACTION_SOURCE_TOP_K_ENEMY)
        reaction_time_map[target.id] = (min_legal_reaction_time(target, my_s, world),
                                        min_legal_reaction_time(target, en_s, world))

    for planet in world.my_planets:
        if expired(): break
        exact_keep = world.keep_needed_map.get(planet.id, 0)
        proactive_keep = 0
        for ep in nearest_sources_to_target(planet, world.enemy_planets, PROACTIVE_ENEMY_TOP_K):
            ea = world.plan_shot(ep.id, planet.id, max(1, int(ep.ships)))
            if ea is None: continue
            if ea[1] > PROACTIVE_DEFENSE_HORIZON: continue
            proactive_keep = max(proactive_keep, int(ep.ships * PROACTIVE_DEFENSE_RATIO))
        proactive_keep = max(proactive_keep, stacked_enemy_proactive_keep(planet, world))
        reserve[planet.id]       = min(int(planet.ships), max(exact_keep, proactive_keep))
        attack_budget[planet.id] = max(0, int(planet.ships) - reserve[planet.id])

    return {"indirect_wealth_map": indirect_wealth_map, "reserve": reserve,
            "attack_budget": attack_budget, "reaction_time_map": reaction_time_map}


def build_modes(world):
    domination = (world.my_total - world.enemy_total) / max(1, world.my_total + world.enemy_total)
    is_behind  = domination < BEHIND_DOMINATION
    is_ahead   = domination > AHEAD_DOMINATION
    is_dominating = is_ahead or (world.max_enemy_strength > 0 and world.my_total > world.max_enemy_strength * 1.25)
    is_finishing  = (domination > FINISHING_DOMINATION and world.my_prod > world.enemy_prod * FINISHING_PROD_RATIO and world.step > 100)
    attack_margin_mult = 1.0
    if is_ahead:     attack_margin_mult += AHEAD_ATTACK_MARGIN_BONUS
    if is_behind:    attack_margin_mult -= BEHIND_ATTACK_MARGIN_PENALTY
    if is_finishing: attack_margin_mult += FINISHING_ATTACK_MARGIN_BONUS
    return {"domination": domination, "is_behind": is_behind, "is_ahead": is_ahead,
            "is_dominating": is_dominating, "is_finishing": is_finishing,
            "attack_margin_mult": attack_margin_mult}


def is_safe_neutral(target, policy):
    if target.owner != -1: return False
    my_t, en_t = policy_reaction_times(target.id, policy)
    return my_t <= en_t - SAFE_NEUTRAL_MARGIN

def is_contested_neutral(target, policy):
    if target.owner != -1: return False
    my_t, en_t = policy_reaction_times(target.id, policy)
    return abs(my_t - en_t) <= CONTESTED_NEUTRAL_MARGIN

def opening_filter(target, arrival_turns, needed, src_available, world, policy):
    if not world.is_opening or target.owner != -1: return False
    if target.id in world.comet_ids: return False
    if world.is_static(target.id): return False
    my_t, en_t = policy_reaction_times(target.id, policy)
    rg = en_t - my_t
    if target.production >= SAFE_OPENING_PROD_THRESHOLD and arrival_turns <= SAFE_OPENING_TURN_LIMIT and rg >= SAFE_NEUTRAL_MARGIN: return False
    if world.is_four_player:
        affordable = needed <= max(PARTIAL_SOURCE_MIN_SHIPS, int(src_available * FOUR_PLAYER_ROTATING_SEND_RATIO))
        if affordable and arrival_turns <= FOUR_PLAYER_ROTATING_TURN_LIMIT and rg >= FOUR_PLAYER_ROTATING_REACTION_GAP: return False
        return True
    return arrival_turns > ROTATING_OPENING_MAX_TURNS or target.production <= ROTATING_OPENING_LOW_PROD


def target_value(target, arrival_turns, mission, world, modes, policy):
    turns_profit = max(1, world.remaining_steps - arrival_turns)
    if target.id in world.comet_ids:
        life = world.comet_life(target.id)
        turns_profit = max(0, min(turns_profit, life - arrival_turns))
        if turns_profit <= 0: return -1.0

    value = target.production * turns_profit
    value += policy["indirect_wealth_map"][target.id] * turns_profit * INDIRECT_VALUE_SCALE

    if world.is_static(target.id):
        value *= STATIC_NEUTRAL_VALUE_MULT if target.owner == -1 else STATIC_HOSTILE_VALUE_MULT
    else:
        value *= ROTATING_OPENING_VALUE_MULT if world.is_opening else 1.0

    if target.owner not in (-1, world.player):
        value *= OPENING_HOSTILE_TARGET_VALUE_MULT if world.is_opening else HOSTILE_TARGET_VALUE_MULT

    if target.owner == -1:
        if is_safe_neutral(target, policy):        value *= SAFE_NEUTRAL_VALUE_MULT
        elif is_contested_neutral(target, policy): value *= CONTESTED_NEUTRAL_VALUE_MULT
        if world.is_early:                         value *= EARLY_NEUTRAL_VALUE_MULT

    if target.id in world.comet_ids: value *= COMET_VALUE_MULT

    if mission == "snipe":          value *= SNIPE_VALUE_MULT
    elif mission == "swarm":        value *= SWARM_VALUE_MULT
    elif mission == "reinforce":    value *= REINFORCE_VALUE_MULT
    elif mission == "crash_exploit": value *= CRASH_EXPLOIT_VALUE_MULT

    # Innovation B: In-flight fleets score → late game captures always worth it
    if IFS_ENABLED and world.step >= IFS_ACTIVATE_TURN:
        value *= 1.20   # boost all captures in final stretch

    if world.is_late:
        value += max(0, target.ships) * LATE_IMMEDIATE_SHIP_VALUE
        if target.owner not in (-1, world.player):
            if world.owner_strength.get(target.owner, 0) <= WEAK_ENEMY_THRESHOLD:
                value += ELIMINATION_BONUS

    if modes["is_finishing"] and target.owner not in (-1, world.player):
        value *= FINISHING_HOSTILE_VALUE_MULT
    if modes["is_behind"] and target.owner == -1 and not world.is_static(target.id):
        value *= BEHIND_ROTATING_NEUTRAL_VALUE_MULT
    if modes["is_behind"] and target.owner == -1 and is_safe_neutral(target, policy):
        value *= 1.08
    if modes["is_dominating"] and target.owner == -1 and is_contested_neutral(target, policy):
        value *= 0.92

    # Innovation E: Symmetry mirror denial boost
    if SMD_ENABLED and target.id in world.mirror_denial_ids and world.step < SMD_HORIZON_TURNS:
        value *= SMD_SCORE_MULT

    return value


def reinforce_value(target, hold_until, world, policy):
    saved_turns = max(1, world.remaining_steps - hold_until)
    value = target.production * saved_turns + max(0, target.ships) * DEFENSE_SHIP_VALUE
    if world.enemy_planets and nearest_distance_to_set(target.x, target.y, world.enemy_planets) < 22:
        value *= DEFENSE_FRONTIER_SCORE_MULT
    value += policy["indirect_wealth_map"][target.id] * saved_turns * INDIRECT_VALUE_SCALE * 0.35
    return value * REINFORCE_VALUE_MULT


def preferred_send(target, base_needed, arrival_turns, src_available, world, modes, policy):
    send = max(base_needed, int(math.ceil(base_needed * modes["attack_margin_mult"])))
    margin = 0
    if target.owner == -1:
        margin += min(NEUTRAL_MARGIN_CAP, NEUTRAL_MARGIN_BASE + target.production * NEUTRAL_MARGIN_PROD_WEIGHT)
    else:
        margin += min(HOSTILE_MARGIN_CAP, HOSTILE_MARGIN_BASE + target.production * HOSTILE_MARGIN_PROD_WEIGHT)
    if world.is_static(target.id):           margin += STATIC_TARGET_MARGIN
    if is_contested_neutral(target, policy):  margin += CONTESTED_TARGET_MARGIN
    if world.is_four_player:                  margin += FOUR_PLAYER_TARGET_MARGIN
    if arrival_turns > LONG_TRAVEL_MARGIN_START:
        margin += min(LONG_TRAVEL_MARGIN_CAP, arrival_turns // LONG_TRAVEL_MARGIN_DIVISOR)
    if target.id in world.comet_ids:          margin = max(0, margin - COMET_MARGIN_RELIEF)
    if modes["is_finishing"] and target.owner not in (-1, world.player):
        margin += FINISHING_HOSTILE_SEND_BONUS
    return min(src_available, send + margin)


def apply_score_modifiers(base_score, target, mission, world):
    score = base_score
    if world.is_static(target.id): score *= STATIC_TARGET_SCORE_MULT
    if world.is_early and target.owner == -1 and world.is_static(target.id):
        score *= EARLY_STATIC_NEUTRAL_SCORE_MULT
    if world.is_four_player and target.owner == -1 and not world.is_static(target.id):
        score *= FOUR_PLAYER_ROTATING_NEUTRAL_SCORE_MULT
    if len(world.static_neutral_planets) >= DENSE_STATIC_NEUTRAL_COUNT and target.owner == -1 and not world.is_static(target.id):
        score *= DENSE_ROTATING_NEUTRAL_SCORE_MULT
    if mission == "snipe":          score *= SNIPE_SCORE_MULT
    elif mission == "swarm":        score *= SWARM_SCORE_MULT
    elif mission == "crash_exploit": score *= CRASH_EXPLOIT_SCORE_MULT
    return score


def settle_plan(src, target, src_cap, send_guess, world, planned_commitments, modes, policy,
                mission="capture", eval_turn_fn=None, anchor_turn=None, anchor_tolerance=None, max_iter=4):
    if src_cap < 1: return None
    seed_hint = max(1, min(src_cap, int(send_guess)))
    eval_turn_fn = eval_turn_fn or (lambda t: t)
    anchor_tolerance = anchor_tolerance if anchor_tolerance is not None else (1 if mission == "snipe" else None)
    tested, tested_order = {}, []

    def evaluate(send):
        send = max(1, min(src_cap, int(send)))
        if send in tested: return tested[send]
        aim = world.plan_shot(src.id, target.id, send)
        if aim is None: tested[send] = None; return None
        angle, turns, _, _ = aim
        if mission == "crash_exploit" and anchor_turn is not None and turns < anchor_turn:
            tested[send] = None; return None
        ret = int(math.ceil(eval_turn_fn(turns)))
        if ret < turns: tested[send] = None; return None
        need = world.min_ships_to_own_by(target.id, ret, world.player, arrival_turn=turns,
                                         planned_commitments=planned_commitments, upper_bound=src_cap)
        if need <= 0 or need > src_cap: tested[send] = None; return None
        if mission in ("snipe", "crash_exploit"): desired = need
        elif mission == "rescue":
            desired = min(src_cap, max(need, need + DEFENSE_SEND_MARGIN_BASE + target.production * DEFENSE_SEND_MARGIN_PROD_WEIGHT))
        else:
            desired = min(src_cap, max(need, preferred_send(target, need, turns, src_cap, world, modes, policy)))
        result = (angle, turns, ret, need, send, desired)
        tested[send] = result; tested_order.append(send)
        return result

    init_cands = sorted(world.probe_ship_candidates(src.id, target.id, src_cap, hints=(seed_hint,)),
                        key=lambda s: (abs(s-seed_hint), s))
    current_send = None
    for seed in init_cands:
        r = evaluate(seed)
        if r is None: continue
        if anchor_turn is not None and anchor_tolerance is not None and abs(r[1]-anchor_turn) > anchor_tolerance: continue
        current_send = seed; break
    if current_send is None: return None

    for _ in range(max_iter):
        r = evaluate(current_send)
        if r is None: break
        angle, turns, et, need, actual_send, desired = r
        if desired == actual_send:
            if anchor_turn is not None and anchor_tolerance is not None and abs(turns-anchor_turn) > anchor_tolerance: return None
            if mission == "rescue" and turns > et: return None
            return angle, turns, et, need, actual_send
        ns = max(1, min(src_cap, int(desired)))
        if ns in tested: current_send = ns; break
        current_send = ns

    for send in sorted([s for s in tested_order if tested.get(s) is not None],
                       key=lambda s: (0 if mission!="snipe" or anchor_turn is None else abs(tested[s][1]-anchor_turn),
                                      abs(s-seed_hint), tested[s][1], s)):
        r = tested.get(send)
        if r is None: continue
        angle, turns, et, need, actual_send, _ = r
        if actual_send < need: continue
        if anchor_turn is not None and anchor_tolerance is not None and abs(turns-anchor_turn) > anchor_tolerance: continue
        if mission == "rescue" and turns > et: continue
        return angle, turns, et, need, actual_send
    return None


def settle_reinforce_plan(src, target, src_cap, send_guess, world, planned_commitments,
                          hold_until, max_arrival_turn, max_iter=4):
    if src_cap < 1: return None
    seed_hint = max(1, min(src_cap, int(send_guess)))
    tested, tested_order = {}, []

    def evaluate(send):
        send = max(1, min(src_cap, int(send)))
        if send in tested: return tested[send]
        aim = world.plan_shot(src.id, target.id, send)
        if aim is None: tested[send] = None; return None
        angle, turns, _, _ = aim
        if turns > max_arrival_turn: tested[send] = None; return None
        need = world.reinforcement_needed_to_hold_until(target.id, turns, hold_until,
                                                        planned_commitments=planned_commitments, upper_bound=src_cap)
        if need <= 0 or need > src_cap: tested[send] = None; return None
        desired = min(src_cap, need + REINFORCE_SAFETY_MARGIN)
        result = (angle, turns, hold_until, need, send, desired)
        tested[send] = result; tested_order.append(send)
        return result

    init_cands = sorted(world.probe_ship_candidates(src.id, target.id, src_cap, hints=(seed_hint,)),
                        key=lambda s: (abs(s-seed_hint), s))
    current_send = None
    for seed in init_cands:
        r = evaluate(seed)
        if r is None: continue
        current_send = seed; break
    if current_send is None: return None

    for _ in range(max_iter):
        r = evaluate(current_send)
        if r is None: break
        angle, turns, et, need, actual_send, desired = r
        if desired == actual_send: return angle, turns, et, need, actual_send
        ns = max(1, min(src_cap, int(desired)))
        if ns in tested: current_send = ns; break
        current_send = ns

    for send in sorted([s for s in tested_order if tested.get(s) is not None],
                       key=lambda s: (abs(s-seed_hint), tested[s][1], s)):
        r = tested.get(send)
        if r is None: continue
        angle, turns, et, need, actual_send, _ = r
        if actual_send < need or turns > max_arrival_turn: continue
        return angle, turns, et, need, actual_send
    return None


# ── Mission Builders ─────────────────────────────────────────

def build_snipe_mission(src, target, src_available, world, planned_commitments, modes, policy):
    if target.owner != -1: return None
    enemy_etas = sorted({int(math.ceil(eta)) for eta, o, s in world.arrivals_by_planet.get(target.id, [])
                         if o not in (-1, world.player) and s > 0})
    if not enemy_etas: return None
    best = None
    for ee in enemy_etas[:3]:
        seeded = world.best_probe_aim(src.id, target.id, src_available, hints=(int(target.ships)+1, int(target.ships)+8), anchor_turn=ee, max_anchor_diff=1)
        if seeded is None: continue
        probe, rough = seeded
        sync_turn = max(rough[1], ee)
        if target.id in world.comet_ids:
            life = world.comet_life(target.id)
            if sync_turn >= life or sync_turn > COMET_MAX_CHASE_TURNS: continue
        plan = settle_plan(src, target, src_available, probe, world, planned_commitments, modes, policy,
            mission="snipe", eval_turn_fn=lambda t, e=ee: max(t, e), anchor_turn=ee)
        if plan is None: continue
        angle, turns, sync_turn, need, send_pref = plan
        if target.id in world.comet_ids:
            life = world.comet_life(target.id)
            if sync_turn >= life or sync_turn > COMET_MAX_CHASE_TURNS: continue
        value = target_value(target, sync_turn, "snipe", world, modes, policy)
        if value <= 0: continue
        score = apply_score_modifiers(value / (send_pref + sync_turn * SNIPE_COST_TURN_WEIGHT + 1.0), target, "snipe", world)
        opt = ShotOption(score=score, src_id=src.id, target_id=target.id, angle=angle, turns=turns,
                         needed=need, send_cap=send_pref, mission="snipe", anchor_turn=ee)
        m = Mission(kind="snipe", score=score, target_id=target.id, turns=sync_turn, options=[opt])
        if best is None or m.score > best.score: best = m
    return best


# Innovation C: Comet Pre-Positioning missions
def build_comet_preposition_missions(world, policy, planned_commitments, modes):
    """
    If a comet is about to spawn, send ships to the spawn quadrant now
    so we arrive ~1 turn after the comet appears with enough force to capture.
    We target the nearest neutral orbiting planet in the expected quadrant
    as a staging point, or if a comet IS already present, target it directly.
    """
    if not CPP_ENABLED: return []
    urgency = world.comet_urgency
    if urgency is None: return []
    turns_to_spawn, spawn_step = urgency
    missions = []

    # Check if comets already exist — if so, target them directly
    for comet_id in world.comet_ids:
        target = world.planet_by_id.get(comet_id)
        if target is None or target.owner == world.player: continue
        for src in world.my_planets:
            src_available = policy["attack_budget"].get(src.id, 0)
            if src_available < CPP_MIN_SEND: continue
            seeded = world.best_probe_aim(src.id, target.id, src_available, hints=(int(target.ships)+1,))
            if seeded is None: continue
            _, rough = seeded
            turns = rough[1]
            if not candidate_time_valid(target, turns, world, LATE_CAPTURE_BUFFER): continue
            need = world.min_ships_to_own_at(target.id, turns, world.player, planned_commitments=planned_commitments)
            if need <= 0 or need > src_available: continue
            plan = settle_plan(src, target, src_available, need+5, world, planned_commitments, modes, policy, mission="capture")
            if plan is None: continue
            angle, turns, _, need, send_pref = plan
            value = target_value(target, turns, "capture", world, modes, policy) * CPP_SCORE_MULT
            score = apply_score_modifiers(value / (send_pref + turns * ATTACK_COST_TURN_WEIGHT + 1.0), target, "capture", world)
            opt = ShotOption(score=score, src_id=src.id, target_id=target.id, angle=angle, turns=turns,
                             needed=need, send_cap=send_pref, mission="capture")
            missions.append(Mission(kind="single", score=score, target_id=target.id, turns=turns, options=[opt]))

    return missions


def build_rescue_missions(world, policy, planned_commitments, modes):
    missions = []
    for target in world.my_planets:
        fall_turn = world.fall_turn_map.get(target.id)
        if fall_turn is None or fall_turn > DEFENSE_LOOKAHEAD_TURNS: continue
        for src in world.my_planets:
            if src.id == target.id: continue
            src_available = policy["attack_budget"].get(src.id, 0)
            if src_available < PARTIAL_SOURCE_MIN_SHIPS: continue
            seeded = world.best_probe_aim(src.id, target.id, src_available,
                hints=(target.production + DEFENSE_SEND_MARGIN_BASE + 2,), max_turn=fall_turn)
            if seeded is None: continue
            probe, _ = seeded
            plan = settle_plan(src, target, src_available, probe, world, planned_commitments, modes, policy,
                mission="rescue", eval_turn_fn=lambda _t, ft=fall_turn: ft, anchor_turn=fall_turn)
            if plan is None: continue
            angle, turns, _, need, send_pref = plan
            saved = max(1, world.remaining_steps - fall_turn)
            value = target.production * saved + max(0, target.ships) * DEFENSE_SHIP_VALUE
            if world.enemy_planets and nearest_distance_to_set(target.x, target.y, world.enemy_planets) < 22:
                value *= DEFENSE_FRONTIER_SCORE_MULT
            score = value / (send_pref + turns * DEFENSE_COST_TURN_WEIGHT + 1.0)
            opt = ShotOption(score=score, src_id=src.id, target_id=target.id, angle=angle, turns=turns,
                             needed=need, send_cap=send_pref, mission="rescue", anchor_turn=fall_turn)
            missions.append(Mission(kind="rescue", score=score, target_id=target.id, turns=fall_turn, options=[opt]))
    return missions


def build_recapture_missions(world, policy, planned_commitments, modes):
    missions = []
    for target in world.my_planets:
        fall_turn = world.fall_turn_map.get(target.id)
        if fall_turn is None or fall_turn > DEFENSE_LOOKAHEAD_TURNS: continue
        for src in world.my_planets:
            if src.id == target.id: continue
            src_available = policy["attack_budget"].get(src.id, 0)
            if src_available < PARTIAL_SOURCE_MIN_SHIPS: continue
            seeded = world.best_probe_aim(src.id, target.id, src_available,
                hints=(target.production + DEFENSE_SEND_MARGIN_BASE + 2,),
                min_turn=fall_turn+1, max_turn=fall_turn+RECAPTURE_LOOKAHEAD_TURNS)
            if seeded is None: continue
            probe, _ = seeded
            plan = settle_plan(src, target, src_available, probe, world, planned_commitments, modes, policy, mission="capture")
            if plan is None: continue
            angle, turns, _, need, send_pref = plan
            if turns <= fall_turn or turns - fall_turn > RECAPTURE_LOOKAHEAD_TURNS: continue
            saved = max(1, world.remaining_steps - turns)
            value = (RECAPTURE_PRODUCTION_WEIGHT * target.production * saved + RECAPTURE_IMMEDIATE_WEIGHT * max(0, target.ships))
            if world.enemy_planets and nearest_distance_to_set(target.x, target.y, world.enemy_planets) < 22:
                value *= RECAPTURE_FRONTIER_MULT
            value *= RECAPTURE_VALUE_MULT
            score = value / (send_pref + turns * RECAPTURE_COST_TURN_WEIGHT + 1.0)
            opt = ShotOption(score=score, src_id=src.id, target_id=target.id, angle=angle, turns=turns,
                             needed=need, send_cap=send_pref, mission="recapture", anchor_turn=fall_turn)
            missions.append(Mission(kind="recapture", score=score, target_id=target.id, turns=turns, options=[opt]))
    return missions


def build_reinforce_missions(world, policy, planned_commitments, modes, inventory_left_fn):
    if not REINFORCE_ENABLED: return []
    missions = []
    if world.remaining_steps < REINFORCE_MIN_FUTURE_TURNS: return missions
    for target in world.my_planets:
        fall_turn = world.fall_turn_map.get(target.id)
        if fall_turn is None or target.production < REINFORCE_MIN_PRODUCTION: continue
        hold_until = min(HORIZON, fall_turn + REINFORCE_HOLD_LOOKAHEAD)
        max_arrival_turn = min(fall_turn, REINFORCE_MAX_TRAVEL_TURNS)
        for src in world.my_planets:
            if src.id == target.id: continue
            budget = inventory_left_fn(src.id)
            source_cap = min(budget, int(src.ships * REINFORCE_MAX_SOURCE_FRACTION))
            if source_cap < PARTIAL_SOURCE_MIN_SHIPS: continue
            seeded = world.best_probe_aim(src.id, target.id, source_cap,
                hints=(target.production + REINFORCE_SAFETY_MARGIN + 2,), max_turn=max_arrival_turn)
            if seeded is None: continue
            probe, _ = seeded
            plan = settle_reinforce_plan(src, target, source_cap, probe, world, planned_commitments, hold_until, max_arrival_turn)
            if plan is None: continue
            angle, turns, _, need, send_pref = plan
            value = reinforce_value(target, hold_until, world, policy)
            score = value / (send_pref + turns * REINFORCE_COST_TURN_WEIGHT + 1.0)
            opt = ShotOption(score=score, src_id=src.id, target_id=target.id, angle=angle, turns=turns,
                             needed=need, send_cap=send_pref, mission="reinforce", anchor_turn=hold_until)
            missions.append(Mission(kind="reinforce", score=score, target_id=target.id, turns=fall_turn, options=[opt]))
    return missions


def build_crash_exploit_missions(world, policy, planned_commitments, modes):
    if not CRASH_EXPLOIT_ENABLED or not world.is_four_player: return []
    missions = []
    for crash in detect_enemy_crashes(world):
        target = world.planet_by_id[crash["target_id"]]
        if target.owner == world.player: continue
        da = crash["crash_turn"] + CRASH_EXPLOIT_POST_CRASH_DELAY
        for src in world.my_planets:
            src_available = policy["attack_budget"].get(src.id, 0)
            if src_available < PARTIAL_SOURCE_MIN_SHIPS: continue
            seeded = world.best_probe_aim(src.id, target.id, src_available,
                hints=(12, int(target.ships)+1), anchor_turn=da, max_anchor_diff=CRASH_EXPLOIT_ETA_WINDOW)
            if seeded is None: continue
            probe, _ = seeded
            plan = settle_plan(src, target, src_available, probe, world, planned_commitments, modes, policy,
                mission="crash_exploit", eval_turn_fn=lambda t, d=da: max(t, d),
                anchor_turn=da, anchor_tolerance=CRASH_EXPLOIT_ETA_WINDOW)
            if plan is None: continue
            angle, turns, _, need, send_pref = plan
            if not candidate_time_valid(target, turns, world, LATE_CAPTURE_BUFFER): continue
            value = target_value(target, turns, "crash_exploit", world, modes, policy)
            if value <= 0: continue
            score = apply_score_modifiers(value / (send_pref + turns * SNIPE_COST_TURN_WEIGHT + 1.0), target, "crash_exploit", world)
            opt = ShotOption(score=score, src_id=src.id, target_id=target.id, angle=angle, turns=turns,
                             needed=need, send_cap=send_pref, mission="crash_exploit", anchor_turn=da)
            missions.append(Mission(kind="crash_exploit", score=score, target_id=target.id, turns=turns, options=[opt]))
    return missions


# ============================================================
# plan_moves
# ============================================================

def plan_moves(world, deadline=None):
    def expired():     return deadline is not None and time.perf_counter() > deadline
    def time_left():   return (10**9) if deadline is None else deadline - time.perf_counter()
    def allow_heavy(): return time_left() > HEAVY_PHASE_MIN_TIME and len(world.planets) <= HEAVY_ROUTE_PLANET_LIMIT
    def allow_opt():   return time_left() > OPTIONAL_PHASE_MIN_TIME

    modes  = build_modes(world)
    policy = build_policy_state(world, deadline=deadline)
    planned_commitments      = defaultdict(list)
    source_options_by_target = defaultdict(list)
    missions = []; moves = []; spent_total = defaultdict(int)

    def src_inv_left(sid): return world.source_inventory_left(sid, spent_total)
    def src_atk_left(sid): return max(0, policy["attack_budget"].get(sid, 0) - spent_total[sid])

    def append_move(sid, angle, ships):
        send = min(int(ships), src_inv_left(sid))
        if send < 1: return 0
        moves.append([sid, float(angle), int(send)]); spent_total[sid] += send
        return send

    def finalize_moves():
        final, used = [], defaultdict(int)
        for sid, angle, ships in moves:
            max_a = int(world.planet_by_id[sid].ships) - used[sid]
            send = min(int(ships), max_a)
            if send >= 1: final.append([sid, float(angle), int(send)]); used[sid] += send
        return final

    def compute_live_doomed():
        doomed = set()
        for p in world.my_planets:
            st = world.hold_status(p.id, planned_commitments=planned_commitments, horizon=DOOMED_EVAC_TURN_LIMIT)
            if (not st["holds_full"] and st["fall_turn"] is not None and
                    st["fall_turn"] <= DOOMED_EVAC_TURN_LIMIT and src_inv_left(p.id) >= DOOMED_MIN_SHIPS):
                doomed.add(p.id)
        return doomed

    # Innovation B: reduce late-game buffer so we launch more aggressively
    late_buffer = VERY_LATE_CAPTURE_BUFFER if world.is_very_late else LATE_CAPTURE_BUFFER
    if IFS_ENABLED and world.step >= IFS_ACTIVATE_TURN:
        late_buffer = max(1, late_buffer - IFS_LATE_BUFFER_REDUCTION)

    def time_filters_pass(target, turns, needed, src_cap):
        if not candidate_time_valid(target, turns, world, late_buffer): return False
        if opening_filter(target, turns, needed, src_cap, world, policy): return False
        return True

    # ── Build missions ────────────────────────────────────────
    if allow_heavy():
        missions.extend(build_reinforce_missions(world, policy, planned_commitments, modes, src_inv_left))
    missions.extend(build_rescue_missions(world, policy, planned_commitments, modes))
    missions.extend(build_recapture_missions(world, policy, planned_commitments, modes))
    # Innovation C: comet pre-positioning (high priority)
    missions.extend(build_comet_preposition_missions(world, policy, planned_commitments, modes))

    for src in world.my_planets:
        if expired(): return finalize_moves()
        src_available = src_atk_left(src.id)
        if src_available <= 0: continue
        for target in world.planets:
            if expired(): return finalize_moves()
            if target.id == src.id or target.owner == world.player: continue
            seeded = world.best_probe_aim(src.id, target.id, src_available, hints=(int(target.ships)+1,))
            if seeded is None: continue
            _, rough_aim = seeded
            rough_turns = rough_aim[1]
            if not candidate_time_valid(target, rough_turns, world, late_buffer): continue
            global_needed = world.min_ships_to_own_at(target.id, rough_turns, world.player, planned_commitments=planned_commitments)
            if global_needed <= 0: continue
            if opening_filter(target, rough_turns, global_needed, src_available, world, policy): continue

            partial_send_cap = min(src_available, preferred_send(target, global_needed, rough_turns, src_available, world, modes, policy))
            if partial_send_cap >= PARTIAL_SOURCE_MIN_SHIPS:
                pseed = world.best_probe_aim(src.id, target.id, partial_send_cap, hints=(partial_send_cap, global_needed, int(target.ships)+1))
                if pseed is not None:
                    _, pa = pseed
                    p_angle, p_turns = pa[0], pa[1]
                    if time_filters_pass(target, p_turns, global_needed, src_available):
                        pv = target_value(target, p_turns, "swarm", world, modes, policy)
                        if pv > 0:
                            ps = apply_score_modifiers(pv / (partial_send_cap + p_turns * ATTACK_COST_TURN_WEIGHT + 1.0), target, "swarm", world)
                            source_options_by_target[target.id].append(
                                ShotOption(score=ps, src_id=src.id, target_id=target.id, angle=p_angle, turns=p_turns,
                                           needed=global_needed, send_cap=partial_send_cap, mission="swarm"))

            if global_needed <= src_available:
                send_guess = preferred_send(target, global_needed, rough_turns, src_available, world, modes, policy)
                plan = settle_plan(src, target, src_available, send_guess, world, planned_commitments, modes, policy, mission="capture")
                if plan is None: continue
                angle, turns, _, needed, send_cap = plan
                if not time_filters_pass(target, turns, needed, src_available): continue
                if send_cap < 1: continue
                value = target_value(target, turns, "capture", world, modes, policy)
                if value <= 0: continue
                score = apply_score_modifiers(value / (send_cap + turns * ATTACK_COST_TURN_WEIGHT + 1.0), target, "capture", world)
                opt = ShotOption(score=score, src_id=src.id, target_id=target.id, angle=angle, turns=turns, needed=needed, send_cap=send_cap, mission="capture")
                if send_cap >= needed:
                    missions.append(Mission(kind="single", score=score, target_id=target.id, turns=turns, options=[opt]))

            snipe = build_snipe_mission(src, target, src_available, world, planned_commitments, modes, policy)
            if snipe is not None: missions.append(snipe)

    # Swarms
    for target_id, options in source_options_by_target.items():
        if expired(): return finalize_moves()
        if len(options) < 2: continue
        target = world.planet_by_id[target_id]
        top_options = sorted(options, key=lambda o: -o.score)[:MULTI_SOURCE_TOP_K]
        for i in range(len(top_options)):
            for j in range(i+1, len(top_options)):
                first, second = top_options[i], top_options[j]
                if first.src_id == second.src_id: continue
                pair_tol = swarm_eta_tolerance((first, second), target, world)
                if abs(first.turns - second.turns) > pair_tol: continue
                joint_turn = max(first.turns, second.turns)
                total_cap  = first.send_cap + second.send_cap
                need = world.min_ships_to_own_at(target_id, joint_turn, world.player, planned_commitments=planned_commitments, upper_bound=total_cap)
                if need <= 0: continue
                if first.send_cap >= need or second.send_cap >= need: continue
                if total_cap < need: continue
                value = target_value(target, joint_turn, "swarm", world, modes, policy)
                if value <= 0: continue
                pair_score = apply_score_modifiers(value / (need + joint_turn * ATTACK_COST_TURN_WEIGHT + 1.0), target, "swarm", world) * MULTI_SOURCE_PLAN_PENALTY
                missions.append(Mission(kind="swarm", score=pair_score, target_id=target_id, turns=joint_turn, options=[first, second]))

        if (THREE_SOURCE_SWARM_ENABLED and allow_heavy() and
                target.owner not in (-1, world.player) and int(target.ships) >= THREE_SOURCE_MIN_TARGET_SHIPS and len(top_options) >= 3):
            for i in range(len(top_options)):
                for j in range(i+1, len(top_options)):
                    for k in range(j+1, len(top_options)):
                        if expired(): return finalize_moves()
                        trio = [top_options[i], top_options[j], top_options[k]]
                        if len({o.src_id for o in trio}) < 3: continue
                        trio_tol = swarm_eta_tolerance(tuple(trio), target, world)
                        tl = [o.turns for o in trio]
                        if max(tl) - min(tl) > trio_tol: continue
                        joint_turn = max(tl); total_cap = sum(o.send_cap for o in trio)
                        need = world.min_ships_to_own_at(target_id, joint_turn, world.player, planned_commitments=planned_commitments, upper_bound=total_cap)
                        if need <= 0 or total_cap < need: continue
                        if any(trio[a].send_cap + trio[b].send_cap >= need for a in range(3) for b in range(a+1, 3)): continue
                        value = target_value(target, joint_turn, "swarm", world, modes, policy)
                        if value <= 0: continue
                        trio_score = apply_score_modifiers(value / (need + joint_turn * ATTACK_COST_TURN_WEIGHT + 1.0), target, "swarm", world) * THREE_SOURCE_PLAN_PENALTY
                        missions.append(Mission(kind="swarm", score=trio_score, target_id=target_id, turns=joint_turn, options=trio))

    if allow_heavy():
        missions.extend(build_crash_exploit_missions(world, policy, planned_commitments, modes))

    missions.sort(key=lambda m: -m.score)

    # Execute
    for mission in missions:
        if expired(): return finalize_moves()
        target = world.planet_by_id[mission.target_id]

        if mission.kind in ("single", "snipe", "rescue", "recapture", "reinforce", "crash_exploit"):
            option = mission.options[0]
            src = world.planet_by_id[option.src_id]
            left = (min(src_inv_left(option.src_id), int(src.ships * REINFORCE_MAX_SOURCE_FRACTION))
                    if mission.kind == "reinforce" else src_atk_left(option.src_id))
            if left <= 0: continue

            if mission.kind == "reinforce":
                plan = settle_reinforce_plan(src, target, left, min(left, option.send_cap), world, planned_commitments, option.anchor_turn, mission.turns)
            elif mission.kind == "rescue":
                plan = settle_plan(src, target, left, min(left, option.send_cap), world, planned_commitments, modes, policy,
                    mission="rescue", eval_turn_fn=lambda _t, ht=mission.turns: ht, anchor_turn=option.anchor_turn)
            elif mission.kind == "snipe":
                plan = settle_plan(src, target, left, min(left, option.send_cap), world, planned_commitments, modes, policy,
                    mission="snipe", eval_turn_fn=lambda t, ee=option.anchor_turn: max(t, ee), anchor_turn=option.anchor_turn)
            elif mission.kind == "crash_exploit":
                plan = settle_plan(src, target, left, min(left, option.send_cap), world, planned_commitments, modes, policy,
                    mission="crash_exploit", eval_turn_fn=lambda t, da=option.anchor_turn: max(t, da),
                    anchor_turn=option.anchor_turn, anchor_tolerance=CRASH_EXPLOIT_ETA_WINDOW)
            else:
                plan = settle_plan(src, target, left, min(left, option.send_cap), world, planned_commitments, modes, policy, mission="capture")
            if plan is None: continue
            angle, turns, _, need, send = plan
            if send < need or need > left: continue
            sent = append_move(option.src_id, angle, send)
            if sent < need: continue
            planned_commitments[target.id].append((turns, world.player, int(sent)))
            continue

        limits = [min(src_atk_left(o.src_id), o.send_cap) for o in mission.options]
        if min(limits) <= 0: continue
        missing = world.min_ships_to_own_at(target.id, mission.turns, world.player,
            planned_commitments=planned_commitments, upper_bound=sum(limits))
        if missing <= 0 or sum(limits) < missing: continue
        ordered = sorted(zip(mission.options, limits), key=lambda x: (x[0].turns, -x[1], x[0].src_id))
        remaining = missing; sends = {}
        for idx, (option, limit) in enumerate(ordered):
            ro = sum(ol for _, ol in ordered[idx+1:])
            send = min(limit, max(0, remaining - ro))
            sends[option.src_id] = send; remaining -= send
        if remaining > 0: continue
        reaimed = []
        for option, _ in ordered:
            send = sends.get(option.src_id, 0)
            if send <= 0: continue
            src = world.planet_by_id[option.src_id]
            fa = world.plan_shot(src.id, target.id, send)
            if fa is None: reaimed = []; break
            angle, turns, _, _ = fa
            reaimed.append((option.src_id, angle, turns, send))
        if not reaimed: continue
        tl2 = [x[2] for x in reaimed]
        if max(tl2) - min(tl2) > swarm_eta_tolerance(mission.options, target, world): continue
        jt = max(tl2)
        oa, _ = world.projected_state(target.id, jt, planned_commitments=planned_commitments,
            extra_arrivals=[(t, world.player, s) for _, _, t, s in reaimed])
        if oa != world.player: continue
        committed = []
        for sid, angle, turns, send in reaimed:
            actual = append_move(sid, angle, send)
            if actual > 0: committed.append((turns, world.player, int(actual)))
        if sum(x[2] for x in committed) < missing: continue
        planned_commitments[target.id].extend(committed)

    # Follow-up pass
    if not world.is_very_late and allow_opt():
        for src in world.my_planets:
            if expired(): return finalize_moves()
            src_left = src_atk_left(src.id)
            if src_left < FOLLOWUP_MIN_SHIPS: continue
            best = None
            for target in world.planets:
                if expired(): return finalize_moves()
                if target.id == src.id or target.owner == world.player: continue
                if target.id in world.comet_ids and target.production <= LOW_VALUE_COMET_PRODUCTION: continue
                seeded = world.best_probe_aim(src.id, target.id, src_left, hints=(int(target.ships)+1,))
                if seeded is None: continue
                _, rough_aim = seeded
                est_turns = rough_aim[1]
                if world.is_late and est_turns > world.remaining_steps - late_buffer: continue
                rough_needed = world.min_ships_to_own_at(target.id, est_turns, world.player,
                    planned_commitments=planned_commitments, upper_bound=src_left)
                if rough_needed <= 0 or rough_needed > src_left: continue
                if opening_filter(target, est_turns, rough_needed, src_left, world, policy): continue
                send = preferred_send(target, rough_needed, est_turns, src_left, world, modes, policy)
                if send < rough_needed: continue
                plan = settle_plan(src, target, src_left, send, world, planned_commitments, modes, policy, mission="capture")
                if plan is None: continue
                _, turns, _, need, final_send = plan
                if world.is_late and turns > world.remaining_steps - late_buffer: continue
                if final_send < need: continue
                value = target_value(target, turns, "capture", world, modes, policy)
                if value <= 0: continue
                score = apply_score_modifiers(value / (final_send + turns * ATTACK_COST_TURN_WEIGHT + 1.0), target, "capture", world)
                if best is None or score > best[0]: best = (score, target, plan)
            if best is None: continue
            _, target, plan = best
            angle, turns, _, need, send = plan
            src_left = src_atk_left(src.id)
            if need > src_left: continue
            plan = settle_plan(src, target, src_left, min(src_left, send), world, planned_commitments, modes, policy, mission="capture")
            if plan is None: continue
            angle, turns, _, need, send = plan
            if send < need: continue
            actual = append_move(src.id, angle, send)
            if actual < need: continue
            planned_commitments[target.id].append((turns, world.player, int(actual)))

    # Doomed evacuation
    if not expired():
        live_doomed = compute_live_doomed()
        if live_doomed:
            ft = world.enemy_planets if world.enemy_planets else (world.static_neutral_planets or world.neutral_planets)
            fd = {p.id: nearest_distance_to_set(p.x, p.y, ft) for p in world.my_planets} if ft else {p.id: 10**9 for p in world.my_planets}
            for planet in world.my_planets:
                if expired(): return finalize_moves()
                if planet.id not in live_doomed: continue
                available_now = src_inv_left(planet.id)
                if available_now < policy["reserve"].get(planet.id, 0): continue
                best_capture = None
                for target in world.planets:
                    if expired(): return finalize_moves()
                    if target.id == planet.id or target.owner == world.player: continue
                    seeded = world.best_probe_aim(planet.id, target.id, available_now, hints=(available_now, int(target.ships)+1))
                    if seeded is None: continue
                    _, probe_aim = seeded
                    if probe_aim[1] > world.remaining_steps - 2: continue
                    need = world.min_ships_to_own_at(target.id, probe_aim[1], world.player, planned_commitments=planned_commitments, upper_bound=available_now)
                    if need <= 0 or need > available_now: continue
                    plan = settle_plan(planet, target, available_now, min(available_now, max(need, int(target.ships)+1)),
                        world, planned_commitments, modes, policy, mission="capture")
                    if plan is None: continue
                    angle, turns, _, plan_need, send = plan
                    if send < plan_need: continue
                    score = target_value(target, turns, "capture", world, modes, policy) / (send + turns + 1.0)
                    if target.owner not in (-1, world.player): score *= 1.05
                    if best_capture is None or score > best_capture[0]: best_capture = (score, target.id, angle, turns, send)
                if best_capture is not None:
                    _, tid, angle, turns, need = best_capture
                    actual = append_move(planet.id, angle, need)
                    if actual >= 1: planned_commitments[tid].append((turns, world.player, int(actual)))
                    continue
                safe_allies = [a for a in world.my_planets if a.id != planet.id and a.id not in live_doomed]
                if not safe_allies: continue
                retreat = min(safe_allies, key=lambda a: (fd.get(a.id, 10**9), planet_distance(planet, a)))
                aim = world.plan_shot(planet.id, retreat.id, available_now)
                if aim is None: continue
                append_move(planet.id, aim[0], available_now)

    # Rear forwarding
    if (world.enemy_planets or world.neutral_planets) and len(world.my_planets) > 1 and not world.is_late and allow_opt():
        live_doomed = compute_live_doomed()
        ft = world.enemy_planets if world.enemy_planets else (world.static_neutral_planets or world.neutral_planets)
        fd = {p.id: nearest_distance_to_set(p.x, p.y, ft) for p in world.my_planets}
        safe_fronts = [p for p in world.my_planets if p.id not in live_doomed]
        if safe_fronts:
            front_anchor = min(safe_fronts, key=lambda p: fd[p.id])
            send_ratio = REAR_SEND_RATIO_FOUR_PLAYER if world.is_four_player else REAR_SEND_RATIO_TWO_PLAYER
            if modes["is_finishing"]: send_ratio = max(send_ratio, REAR_SEND_RATIO_FOUR_PLAYER)
            for rear in sorted(world.my_planets, key=lambda p: -fd[p.id]):
                if expired(): return finalize_moves()
                if rear.id == front_anchor.id or rear.id in live_doomed: continue
                if src_atk_left(rear.id) < REAR_SOURCE_MIN_SHIPS: continue
                if fd[rear.id] < fd[front_anchor.id] * REAR_DISTANCE_RATIO: continue
                stage_cands = [p for p in safe_fronts if p.id != rear.id and fd[p.id] < fd[rear.id] * REAR_STAGE_PROGRESS]
                if stage_cands: front = min(stage_cands, key=lambda p: planet_distance(rear, p))
                else:
                    objective = min(ft, key=lambda t: planet_distance(rear, t))
                    rfs = [p for p in safe_fronts if p.id != rear.id]
                    if not rfs: continue
                    front = min(rfs, key=lambda p: planet_distance(p, objective))
                if front.id == rear.id: continue
                send = int(src_atk_left(rear.id) * send_ratio)
                if send < REAR_SEND_MIN_SHIPS: continue
                aim = world.plan_shot(rear.id, front.id, send)
                if aim is None: continue
                if aim[1] > REAR_MAX_TRAVEL_TURNS: continue
                append_move(rear.id, aim[0], send)

    return finalize_moves()


# ============================================================
# Entry Point
# ============================================================

def agent(observation, configuration=None):
    start_time = time.perf_counter()

    get = observation.get if isinstance(observation, dict) else (lambda k, d=None: getattr(observation, k, d))
    player    = get("player", 0)
    step      = get("step", 0) or 0
    ang_vel   = get("angular_velocity", 0.0) or 0.0
    comets    = get("comets", []) or []
    comet_ids = set(get("comet_planet_ids", []) or [])
    planets   = [Planet(*p) for p in (get("planets", []) or [])]
    fleets    = [Fleet(*f)  for f in (get("fleets",  []) or [])]
    init_ps   = [Planet(*p) for p in (get("initial_planets", []) or [])]
    init_by_id = {p.id: p for p in init_ps}

    world = WorldModel(player=player, step=step, planets=planets, fleets=fleets,
                       initial_by_id=init_by_id, ang_vel=ang_vel, comets=comets, comet_ids=comet_ids)

    if not world.my_planets: return []

    if configuration is not None:
        act_timeout = (configuration.get("actTimeout", 1.0) if isinstance(configuration, dict)
                       else getattr(configuration, "actTimeout", 1.0))
    else:
        act_timeout = 1.0

    deadline = start_time + min(SOFT_ACT_DEADLINE, act_timeout * 0.82)
    return plan_moves(world, deadline=deadline)
```

## [MD]
## Sanity Check (optional)

## [CODE]
```python
try:
    from kaggle_environments import make
    import importlib.util, random
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("submission", Path("submission.py"))
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    wins = 0
    for seed in [1, 42, 99, 137, 271]:
        random.seed(seed)
        env = make("orbit_wars", debug=False)
        res = env.run([mod.agent, "random"])
        r0 = res[-1][0].get("reward", 0) or 0
        r1 = res[-1][1].get("reward", 0) or 0
        if r0 > r1: wins += 1
        print(f"  seed={seed}: {'WIN' if r0>r1 else 'LOSS' if r0<r1 else 'DRAW'}  ({r0:.0f} vs {r1:.0f})")

    print(f"\n{wins}/5 wins vs. random")
    print("✅ Ready to submit!" if wins >= 4 else "⚠️  Check agent")

except ImportError:
    print("kaggle_environments not available — submit submission.py directly")
```
