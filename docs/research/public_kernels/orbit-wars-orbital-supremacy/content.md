## [MD]
# Orbit Wars — "Orbital Supremacy" Agent v3.0

## Strategy Summary
| Phase | Function | Priority |
|-------|----------|----------|
| 1 | `plan_defense` — reactive defense of threatened planets | Highest |
| 2 | `plan_evacuations` — evacuate doomed planets | High |
| 3 | `plan_recaptures` — snipe freshly captured enemy planets | High |
| 4 | `plan_single_source_attacks` — scored (src, target) greedy dispatch | Core |
| 5 | `plan_multi_source_swarms` — synchronized multi-fleet arrivals | Optional |
| 6 | `plan_crash_exploits` — exploit mutual enemy fleet cancellations | Optional |
| 7 | `plan_reinforcements` — proactive frontier reinforcement | Optional |
| 8 | `plan_rear_forwarding` — late-game surplus forwarding | Optional |

**Score formula:** `V(planet, t) / C(ships, t)` where
`V = production × remaining_turns × phase_multipliers`
`C = ships_sent + arrival_turns × cost_weight`

## [MD]
## Cell 1 — Install / verify kaggle-environments

## [CODE]
```python
import subprocess, sys
from importlib.metadata import PackageNotFoundError, version

def _parse_version(text):
    parts = []
    for token in text.split('.'):
        digits = ''.join(ch for ch in token if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)

required = (1, 28, 0)
needs_upgrade = False
try:
    needs_upgrade = _parse_version(version('kaggle-environments')) < required
except PackageNotFoundError:
    needs_upgrade = True

if needs_upgrade:
    subprocess.check_call(
        [sys.executable, '-m', 'pip', 'install', '-q', '--upgrade',
         'kaggle-environments>=1.28.0']
    )

import kaggle_environments
print('kaggle-environments', kaggle_environments.__version__)
```

## [MD]
## Cell 2 — Write `submission.py`
This cell writes the complete, self-contained agent to disk.

## [CODE]
```python
%%writefile submission.py
"""
Orbit Wars — "Orbital Supremacy" Agent  v3.0
==============================================
Architecture:
  1. Physics layer  – exact intercept / sun-safe routing for orbiting planets
  2. World model    – timeline-based ownership simulation with commitment tracking
  3. Policy engine  – reserve / budget / reaction-time analysis
  4. Mission planner– ranked attack / defense / swarm / crash-exploit / evacuate
  5. Agent          – time-budgeted dispatch loop
"""

import math
import time
from collections import defaultdict, namedtuple
from dataclasses import dataclass, field

# ============================================================
# Configuration
# ============================================================

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
HORIZON = SIM_HORIZON
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
FOUR_PLAYER_ROTATING_REACTION_GAP = 3
FOUR_PLAYER_ROTATING_SEND_RATIO = 0.62
FOUR_PLAYER_ROTATING_TURN_LIMIT = 10

COMET_MAX_CHASE_TURNS = 10

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
FOUR_PLAYER_TARGET_MARGIN = 3
LONG_TRAVEL_MARGIN_START = 18
LONG_TRAVEL_MARGIN_DIVISOR = 3
LONG_TRAVEL_MARGIN_CAP = 8
COMET_MARGIN_RELIEF = 6
FINISHING_HOSTILE_SEND_BONUS = 3

STATIC_TARGET_SCORE_MULT = 1.18
EARLY_STATIC_NEUTRAL_SCORE_MULT = 1.25
FOUR_PLAYER_ROTATING_NEUTRAL_SCORE_MULT = 0.84
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
MULTI_SOURCE_TOP_K = 5
MULTI_SOURCE_ETA_TOLERANCE = 2
MULTI_SOURCE_PLAN_PENALTY = 0.97
HOSTILE_SWARM_ETA_TOLERANCE = 1
THREE_SOURCE_SWARM_ENABLED = True
THREE_SOURCE_MIN_TARGET_SHIPS = 20
THREE_SOURCE_ETA_TOLERANCE = 1
THREE_SOURCE_PLAN_PENALTY = 0.93

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


# ============================================================
# Shared Types
# ============================================================

Planet = namedtuple(
    "Planet", ["id", "owner", "x", "y", "radius", "ships", "production"]
)
Fleet = namedtuple(
    "Fleet", ["id", "owner", "x", "y", "angle", "from_planet_id", "ships"]
)


@dataclass(frozen=True)
class ShotOption:
    score: float
    src_id: int
    target_id: int
    angle: float
    turns: int
    needed: int
    send_cap: int
    mission: str = "capture"
    anchor_turn: int | None = None


@dataclass
class Mission:
    kind: str
    score: float
    target_id: int
    turns: int
    options: list = field(default_factory=list)


# ============================================================
# Physics
# ============================================================

def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def orbital_radius(planet):
    return dist(planet.x, planet.y, CENTER_X, CENTER_Y)


def is_static_planet(planet):
    return orbital_radius(planet) + planet.radius >= ROTATION_LIMIT


def fleet_speed(ships):
    if ships <= 1:
        return 1.0
    ratio = math.log(ships) / math.log(1000.0)
    ratio = max(0.0, min(1.0, ratio))
    return 1.0 + (MAX_SPEED - 1.0) * (ratio ** 1.5)


def point_to_segment_distance(px, py, x1, y1, x2, y2):
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


def segment_hits_sun(x1, y1, x2, y2, safety=SUN_SAFETY):
    return point_to_segment_distance(CENTER_X, CENTER_Y, x1, y1, x2, y2) < SUN_R + safety


def launch_point(sx, sy, sr, angle):
    clearance = sr + LAUNCH_CLEARANCE
    return sx + math.cos(angle) * clearance, sy + math.sin(angle) * clearance


def actual_path_geometry(sx, sy, sr, tx, ty, tr):
    angle = math.atan2(ty - sy, tx - sx)
    start_x, start_y = launch_point(sx, sy, sr, angle)
    hit_distance = max(0.0, dist(sx, sy, tx, ty) - (sr + LAUNCH_CLEARANCE) - tr)
    end_x = start_x + math.cos(angle) * hit_distance
    end_y = start_y + math.sin(angle) * hit_distance
    return angle, start_x, start_y, end_x, end_y, hit_distance


def safe_angle_and_distance(sx, sy, sr, tx, ty, tr):
    angle, start_x, start_y, end_x, end_y, hit_distance = actual_path_geometry(
        sx, sy, sr, tx, ty, tr
    )
    if segment_hits_sun(start_x, start_y, end_x, end_y):
        return None
    return angle, hit_distance


def predict_planet_position(planet, initial_by_id, angular_velocity, turns):
    init = initial_by_id.get(planet.id)
    if init is None:
        return planet.x, planet.y
    r = dist(init.x, init.y, CENTER_X, CENTER_Y)
    if r + init.radius >= ROTATION_LIMIT:
        return planet.x, planet.y
    cur_ang = math.atan2(planet.y - CENTER_Y, planet.x - CENTER_X)
    new_ang = cur_ang + angular_velocity * turns
    return (
        CENTER_X + r * math.cos(new_ang),
        CENTER_Y + r * math.sin(new_ang),
    )


def predict_comet_position(planet_id, comets, turns):
    for group in comets:
        pids = group.get("planet_ids", [])
        if planet_id not in pids:
            continue
        idx = pids.index(planet_id)
        paths = group.get("paths", [])
        path_index = group.get("path_index", 0)
        if idx >= len(paths):
            return None
        path = paths[idx]
        future_idx = path_index + int(turns)
        if 0 <= future_idx < len(path):
            return path[future_idx][0], path[future_idx][1]
        return None
    return None


def comet_remaining_life(planet_id, comets):
    for group in comets:
        pids = group.get("planet_ids", [])
        if planet_id not in pids:
            continue
        idx = pids.index(planet_id)
        paths = group.get("paths", [])
        path_index = group.get("path_index", 0)
        if idx < len(paths):
            return max(0, len(paths[idx]) - path_index)
    return 0


def estimate_arrival(sx, sy, sr, tx, ty, tr, ships):
    safe = safe_angle_and_distance(sx, sy, sr, tx, ty, tr)
    if safe is None:
        return None
    angle, total_d = safe
    turns = max(1, int(math.ceil(total_d / fleet_speed(max(1, ships)))))
    return angle, turns


def travel_time(sx, sy, sr, tx, ty, tr, ships):
    est = estimate_arrival(sx, sy, sr, tx, ty, tr, ships)
    if est is None:
        return 10 ** 9
    return est[1]


def predict_target_position(target, turns, initial_by_id, ang_vel, comets, comet_ids):
    if target.id in comet_ids:
        return predict_comet_position(target.id, comets, turns)
    return predict_planet_position(target, initial_by_id, ang_vel, turns)


def target_can_move(target, initial_by_id, comet_ids):
    if target.id in comet_ids:
        return True
    init = initial_by_id.get(target.id)
    if init is None:
        return False
    r = dist(init.x, init.y, CENTER_X, CENTER_Y)
    return r + init.radius < ROTATION_LIMIT


def search_safe_intercept(src, target, ships, initial_by_id, ang_vel, comets, comet_ids):
    best = None
    best_score = None
    max_turns = min(HORIZON, ROUTE_SEARCH_HORIZON)
    if target.id in comet_ids:
        max_turns = min(max_turns, max(0, comet_remaining_life(target.id, comets) - 1))

    for candidate_turns in range(1, max_turns + 1):
        pos = predict_target_position(
            target, candidate_turns, initial_by_id, ang_vel, comets, comet_ids
        )
        if pos is None:
            continue
        est = estimate_arrival(src.x, src.y, src.radius, pos[0], pos[1], target.radius, ships)
        if est is None:
            continue
        _, turns = est
        if abs(turns - candidate_turns) > INTERCEPT_TOLERANCE:
            continue

        actual_turns = max(turns, candidate_turns)
        actual_pos = predict_target_position(
            target, actual_turns, initial_by_id, ang_vel, comets, comet_ids
        )
        if actual_pos is None:
            continue

        confirm = estimate_arrival(
            src.x, src.y, src.radius,
            actual_pos[0], actual_pos[1], target.radius, ships
        )
        if confirm is None:
            continue

        delta = abs(confirm[1] - actual_turns)
        if delta > INTERCEPT_TOLERANCE:
            continue

        score = (delta, confirm[1], candidate_turns)
        if best is None or score < best_score:
            best_score = score
            best = (confirm[0], confirm[1], actual_pos[0], actual_pos[1])

    return best


def aim_with_prediction(src, target, ships, initial_by_id, ang_vel, comets, comet_ids):
    est = estimate_arrival(src.x, src.y, src.radius, target.x, target.y, target.radius, ships)
    if est is None:
        if not target_can_move(target, initial_by_id, comet_ids):
            return None
        return search_safe_intercept(src, target, ships, initial_by_id, ang_vel, comets, comet_ids)

    tx, ty = target.x, target.y
    for _ in range(5):
        _, turns = est
        pos = predict_target_position(target, turns, initial_by_id, ang_vel, comets, comet_ids)
        if pos is None:
            return None
        ntx, nty = pos
        next_est = estimate_arrival(src.x, src.y, src.radius, ntx, nty, target.radius, ships)
        if next_est is None:
            if not target_can_move(target, initial_by_id, comet_ids):
                return None
            return search_safe_intercept(src, target, ships, initial_by_id, ang_vel, comets, comet_ids)
        if (
            abs(ntx - tx) < 0.3
            and abs(nty - ty) < 0.3
            and abs(next_est[1] - turns) <= INTERCEPT_TOLERANCE
        ):
            return next_est[0], next_est[1], ntx, nty
        tx, ty = ntx, nty
        est = next_est

    final_est = estimate_arrival(src.x, src.y, src.radius, tx, ty, target.radius, ships)
    if final_est is None:
        return search_safe_intercept(src, target, ships, initial_by_id, ang_vel, comets, comet_ids)
    return final_est[0], final_est[1], tx, ty


# ============================================================
# World Model
# ============================================================

def fleet_target_planet(fleet, planets):
    best_planet = None
    best_time = 1e9
    dir_x = math.cos(fleet.angle)
    dir_y = math.sin(fleet.angle)
    speed = fleet_speed(fleet.ships)

    for planet in planets:
        dx = planet.x - fleet.x
        dy = planet.y - fleet.y
        proj = dx * dir_x + dy * dir_y
        if proj < 0:
            continue
        perp_sq = dx * dx + dy * dy - proj * proj
        radius_sq = planet.radius * planet.radius
        if perp_sq >= radius_sq:
            continue
        hit_d = max(0.0, proj - math.sqrt(max(0.0, radius_sq - perp_sq)))
        turns = hit_d / speed
        if turns <= HORIZON and turns < best_time:
            best_time = turns
            best_planet = planet

    if best_planet is None:
        return None, None
    return best_planet, int(math.ceil(best_time))


def build_arrival_ledger(fleets, planets):
    arrivals_by_planet = {planet.id: [] for planet in planets}
    for fleet in fleets:
        target, eta = fleet_target_planet(fleet, planets)
        if target is None:
            continue
        arrivals_by_planet[target.id].append((eta, fleet.owner, int(fleet.ships)))
    return arrivals_by_planet


def resolve_arrival_event(owner, garrison, arrivals):
    by_owner = {}
    for _, attacker_owner, ships in arrivals:
        by_owner[attacker_owner] = by_owner.get(attacker_owner, 0) + ships

    if not by_owner:
        return owner, max(0.0, garrison)

    sorted_players = sorted(by_owner.items(), key=lambda item: item[1], reverse=True)
    top_owner, top_ships = sorted_players[0]

    if len(sorted_players) > 1:
        second_ships = sorted_players[1][1]
        if top_ships == second_ships:
            survivor_owner = -1
            survivor_ships = 0
        else:
            survivor_owner = top_owner
            survivor_ships = top_ships - second_ships
    else:
        survivor_owner = top_owner
        survivor_ships = top_ships

    if survivor_ships <= 0:
        return owner, max(0.0, garrison)

    if owner == survivor_owner:
        return owner, garrison + survivor_ships

    garrison -= survivor_ships
    if garrison < 0:
        return survivor_owner, -garrison
    return owner, garrison


def normalize_arrivals(arrivals, horizon):
    events = []
    for turns, owner, ships in arrivals:
        if ships <= 0:
            continue
        eta = max(1, int(math.ceil(turns)))
        if eta > horizon:
            continue
        events.append((eta, owner, int(ships)))
    events.sort(key=lambda item: item[0])
    return events


def simulate_planet_timeline(planet, arrivals, player, horizon):
    horizon = max(0, int(math.ceil(horizon)))
    events = normalize_arrivals(arrivals, horizon)
    by_turn = defaultdict(list)
    for item in events:
        by_turn[item[0]].append(item)

    owner = planet.owner
    garrison = float(planet.ships)
    owner_at = {0: owner}
    ships_at = {0: max(0.0, garrison)}
    min_owned = garrison if owner == player else 0.0
    first_enemy = None
    fall_turn = None

    for turn in range(1, horizon + 1):
        if owner != -1:
            garrison += planet.production

        group = by_turn.get(turn, [])
        prev_owner = owner
        if group:
            if prev_owner == player and first_enemy is None:
                if any(item[1] not in (-1, player) for item in group):
                    first_enemy = turn
            owner, garrison = resolve_arrival_event(owner, garrison, group)
            if prev_owner == player and owner != player and fall_turn is None:
                fall_turn = turn

        owner_at[turn] = owner
        ships_at[turn] = max(0.0, garrison)
        if owner == player:
            min_owned = min(min_owned, garrison)

    keep_needed = 0
    holds_full = True

    if planet.owner == player:

        def survives_with_keep(keep):
            sim_owner = planet.owner
            sim_garrison = float(keep)
            for turn in range(1, horizon + 1):
                if sim_owner != -1:
                    sim_garrison += planet.production
                group = by_turn.get(turn, [])
                if group:
                    sim_owner, sim_garrison = resolve_arrival_event(sim_owner, sim_garrison, group)
                    if sim_owner != player:
                        return False
            return sim_owner == player

        if survives_with_keep(int(planet.ships)):
            lo, hi = 0, int(planet.ships)
            while lo < hi:
                mid = (lo + hi) // 2
                if survives_with_keep(mid):
                    hi = mid
                else:
                    lo = mid + 1
            keep_needed = lo
        else:
            holds_full = False
            keep_needed = int(planet.ships)

    return {
        "owner_at": owner_at,
        "ships_at": ships_at,
        "keep_needed": keep_needed,
        "min_owned": max(0, int(math.floor(min_owned))) if planet.owner == player else 0,
        "first_enemy": first_enemy,
        "fall_turn": fall_turn,
        "holds_full": holds_full,
        "horizon": horizon,
    }


def state_at_timeline(timeline, arrival_turn):
    turn = max(0, int(math.ceil(arrival_turn)))
    turn = min(turn, timeline["horizon"])
    owner = timeline["owner_at"].get(turn, timeline["owner_at"][timeline["horizon"]])
    ships = timeline["ships_at"].get(turn, timeline["ships_at"][timeline["horizon"]])
    return owner, max(0.0, ships)


def count_players(planets, fleets):
    owners = set()
    for planet in planets:
        if planet.owner != -1:
            owners.add(planet.owner)
    for fleet in fleets:
        owners.add(fleet.owner)
    return max(2, len(owners))


def nearest_distance_to_set(px, py, planets):
    if not planets:
        return 10 ** 9
    return min(dist(px, py, planet.x, planet.y) for planet in planets)


def indirect_features(planet, planets, player):
    friendly = 0.0
    neutral = 0.0
    enemy = 0.0
    for other in planets:
        if other.id == planet.id:
            continue
        d = dist(planet.x, planet.y, other.x, other.y)
        if d < 1:
            continue
        factor = other.production / (d + 12.0)
        if other.owner == player:
            friendly += factor
        elif other.owner == -1:
            neutral += factor
        else:
            enemy += factor
    return friendly, neutral, enemy


class WorldModel:
    def __init__(self, player, step, planets, fleets, initial_by_id, ang_vel, comets, comet_ids):
        self.player = player
        self.step = step
        self.planets = planets
        self.fleets = fleets
        self.initial_by_id = initial_by_id
        self.ang_vel = ang_vel
        self.comets = comets
        self.comet_ids = set(comet_ids)

        self.planet_by_id = {planet.id: planet for planet in planets}
        self.my_planets = [planet for planet in planets if planet.owner == player]
        self.enemy_planets = [planet for planet in planets if planet.owner not in (-1, player)]
        self.neutral_planets = [planet for planet in planets if planet.owner == -1]
        self.static_neutral_planets = [
            planet for planet in self.neutral_planets if is_static_planet(planet)
        ]

        self.num_players = count_players(planets, fleets)
        self.remaining_steps = max(1, TOTAL_STEPS - step)
        self.is_early = step < EARLY_TURN_LIMIT
        self.is_opening = step < OPENING_TURN_LIMIT
        self.is_late = self.remaining_steps < LATE_REMAINING_TURNS
        self.is_very_late = self.remaining_steps < VERY_LATE_REMAINING_TURNS
        self.is_four_player = self.num_players >= 4

        self.owner_strength = defaultdict(int)
        self.owner_production = defaultdict(int)
        for planet in planets:
            if planet.owner != -1:
                self.owner_strength[planet.owner] += int(planet.ships)
                self.owner_production[planet.owner] += int(planet.production)
        for fleet in fleets:
            self.owner_strength[fleet.owner] += int(fleet.ships)

        self.my_total = self.owner_strength.get(player, 0)
        self.enemy_total = sum(
            s for o, s in self.owner_strength.items() if o != player
        )
        self.max_enemy_strength = max(
            (s for o, s in self.owner_strength.items() if o != player), default=0
        )
        self.my_prod = self.owner_production.get(player, 0)
        self.enemy_prod = sum(
            p for o, p in self.owner_production.items() if o != player
        )

        self.arrivals_by_planet = build_arrival_ledger(fleets, planets)
        self.base_timeline = {
            planet.id: simulate_planet_timeline(
                planet, self.arrivals_by_planet[planet.id], player, HORIZON
            )
            for planet in planets
        }
        self.keep_needed_map = {
            planet.id: self.base_timeline[planet.id]["keep_needed"] for planet in planets
        }
        self.min_owned_map = {
            planet.id: self.base_timeline[planet.id]["min_owned"] for planet in planets
        }
        self.first_enemy_map = {
            planet.id: self.base_timeline[planet.id]["first_enemy"] for planet in planets
        }
        self.fall_turn_map = {
            planet.id: self.base_timeline[planet.id]["fall_turn"] for planet in planets
        }
        self.holds_full_map = {
            planet.id: self.base_timeline[planet.id]["holds_full"] for planet in planets
        }
        self.indirect_feature_map = {
            planet.id: indirect_features(planet, planets, player) for planet in planets
        }
        self.shot_cache = {}
        self.probe_candidate_cache = {}
        self.best_probe_cache = {}
        self.reaction_cache = {}
        self.exact_need_cache = {}

        self.total_visible_ships = sum(int(p.ships) for p in planets) + sum(
            int(f.ships) for f in fleets
        )
        self.total_production = sum(int(p.production) for p in planets)

    def is_static(self, planet_id):
        return is_static_planet(self.planet_by_id[planet_id])

    def comet_life(self, planet_id):
        return comet_remaining_life(planet_id, self.comets)

    def source_inventory_left(self, source_id, spent_total):
        return max(0, int(self.planet_by_id[source_id].ships) - spent_total[source_id])

    def plan_shot(self, src_id, target_id, ships):
        ships = int(ships)
        key = (src_id, target_id, ships)
        if key in self.shot_cache:
            return self.shot_cache[key]
        src = self.planet_by_id[src_id]
        target = self.planet_by_id[target_id]
        result = aim_with_prediction(
            src, target, ships, self.initial_by_id, self.ang_vel, self.comets, self.comet_ids
        )
        self.shot_cache[key] = result
        return result

    def probe_ship_candidates(self, src_id, target_id, source_cap, hints=()):
        source_cap = max(1, int(source_cap))
        normalized_hints = tuple(int(math.ceil(h)) for h in hints if h is not None)
        cache_key = (src_id, target_id, source_cap, normalized_hints)
        cached = self.probe_candidate_cache.get(cache_key)
        if cached is not None:
            return cached
        target = self.planet_by_id[target_id]
        target_ships = max(1, int(math.ceil(target.ships)))

        values = set(range(1, min(6, source_cap) + 1))
        values.update({
            source_cap,
            max(1, source_cap // 2),
            max(1, source_cap // 3),
            min(source_cap, PARTIAL_SOURCE_MIN_SHIPS),
            min(source_cap, target_ships + 1),
            min(source_cap, target_ships + 2),
            min(source_cap, target_ships + 4),
            min(source_cap, target_ships + 8),
        })
        for hint in normalized_hints:
            base = max(1, min(source_cap, hint))
            for delta in (-2, -1, 0, 1, 2):
                candidate = base + delta
                if 1 <= candidate <= source_cap:
                    values.add(candidate)

        result = sorted(values)
        self.probe_candidate_cache[cache_key] = result
        return result

    def best_probe_aim(
        self, src_id, target_id, source_cap, hints=(),
        min_turn=None, max_turn=None, anchor_turn=None, max_anchor_diff=None,
    ):
        cache_key = (
            src_id, target_id, max(1, int(source_cap)),
            tuple(hints), min_turn, max_turn, anchor_turn, max_anchor_diff,
        )
        cached = self.best_probe_cache.get(cache_key)
        if cached is not None:
            return cached

        best = None
        best_key = None

        for ships in self.probe_ship_candidates(src_id, target_id, source_cap, hints=hints):
            aim = self.plan_shot(src_id, target_id, ships)
            if aim is None:
                continue
            angle, turns, _tx, _ty = aim
            if min_turn is not None and turns < min_turn:
                continue
            if max_turn is not None and turns > max_turn:
                continue
            if (
                anchor_turn is not None
                and max_anchor_diff is not None
                and abs(turns - anchor_turn) > max_anchor_diff
            ):
                continue

            if anchor_turn is None:
                key = (turns, ships)
            else:
                key = (abs(turns - anchor_turn), turns, ships)

            if best_key is None or key < best_key:
                best_key = key
                best = (ships, (angle, turns, _tx, _ty))

        self.best_probe_cache[cache_key] = best
        return best

    def reaction_times(self, target_id):
        cached = self.reaction_cache.get(target_id)
        if cached is not None:
            return cached
        target = self.planet_by_id[target_id]
        my_t = 10 ** 9
        for planet in self.my_planets:
            seeded = self.best_probe_aim(planet.id, target.id, max(1, int(planet.ships)))
            if seeded is None:
                continue
            _, aim = seeded
            my_t = min(my_t, aim[1])
        enemy_t = 10 ** 9
        for planet in self.enemy_planets:
            seeded = self.best_probe_aim(planet.id, target.id, max(1, int(planet.ships)))
            if seeded is None:
                continue
            _, aim = seeded
            enemy_t = min(enemy_t, aim[1])
        cached = (my_t, enemy_t)
        self.reaction_cache[target_id] = cached
        return cached

    def projected_state(self, target_id, arrival_turn, planned_commitments=None, extra_arrivals=()):
        planned_commitments = planned_commitments or {}
        cutoff = max(1, int(math.ceil(arrival_turn)))
        if not planned_commitments.get(target_id) and not extra_arrivals:
            return state_at_timeline(self.base_timeline[target_id], cutoff)

        arrivals = [
            item for item in self.arrivals_by_planet.get(target_id, []) if item[0] <= cutoff
        ]
        arrivals.extend(
            item for item in planned_commitments.get(target_id, []) if item[0] <= cutoff
        )
        arrivals.extend(item for item in extra_arrivals if item[0] <= cutoff)
        target = self.planet_by_id[target_id]
        dyn = simulate_planet_timeline(target, arrivals, self.player, cutoff)
        return state_at_timeline(dyn, cutoff)

    def projected_timeline(self, target_id, horizon, planned_commitments=None, extra_arrivals=()):
        planned_commitments = planned_commitments or {}
        horizon = max(1, int(math.ceil(horizon)))
        arrivals = [
            item for item in self.arrivals_by_planet.get(target_id, []) if item[0] <= horizon
        ]
        arrivals.extend(
            item for item in planned_commitments.get(target_id, []) if item[0] <= horizon
        )
        arrivals.extend(item for item in extra_arrivals if item[0] <= horizon)
        target = self.planet_by_id[target_id]
        return simulate_planet_timeline(target, arrivals, self.player, horizon)

    def hold_status(self, target_id, planned_commitments=None, horizon=HORIZON):
        planned_commitments = planned_commitments or {}
        if planned_commitments.get(target_id):
            tl = self.projected_timeline(target_id, horizon, planned_commitments=planned_commitments)
        else:
            tl = self.base_timeline[target_id]
        return {
            "keep_needed": tl["keep_needed"],
            "min_owned": tl["min_owned"],
            "first_enemy": tl["first_enemy"],
            "fall_turn": tl["fall_turn"],
            "holds_full": tl["holds_full"],
        }

    def _ownership_search_cap(self, eval_turn):
        productive_cap = self.total_production * max(2, eval_turn + 2)
        return max(32, int(self.total_visible_ships + productive_cap + 32))

    def min_ships_to_own_by(
        self, target_id, eval_turn, attacker_owner, arrival_turn=None,
        planned_commitments=None, extra_arrivals=(), upper_bound=None,
    ):
        planned_commitments = planned_commitments or {}
        eval_turn = max(1, int(math.ceil(eval_turn)))
        arrival_turn = eval_turn if arrival_turn is None else max(1, int(math.ceil(arrival_turn)))
        if arrival_turn > eval_turn:
            if upper_bound is not None:
                return max(1, int(upper_bound)) + 1
            return self._ownership_search_cap(eval_turn) + 1

        normalized_extra = tuple(
            (max(1, int(math.ceil(t))), o, int(s))
            for t, o, s in extra_arrivals
            if s > 0 and max(1, int(math.ceil(t))) <= eval_turn
        )

        cache_key = None
        if arrival_turn == eval_turn and not planned_commitments.get(target_id) and not normalized_extra:
            cache_key = (target_id, eval_turn, attacker_owner)
            cached = self.exact_need_cache.get(cache_key)
            if cached is not None:
                return cached

        owner_before, ships_before = self.projected_state(
            target_id, eval_turn, planned_commitments=planned_commitments, extra_arrivals=normalized_extra
        )
        if owner_before == attacker_owner:
            if cache_key is not None:
                self.exact_need_cache[cache_key] = 0
            return 0

        def owns_at(ships):
            owner_after, _ = self.projected_state(
                target_id, eval_turn, planned_commitments=planned_commitments,
                extra_arrivals=normalized_extra + ((arrival_turn, attacker_owner, int(ships)),),
            )
            return owner_after == attacker_owner

        if upper_bound is not None:
            hi = max(1, int(upper_bound))
            if not owns_at(hi):
                return hi + 1
        else:
            hi = max(1, int(math.ceil(ships_before)) + 1)
            search_cap = self._ownership_search_cap(eval_turn)
            while hi <= search_cap and not owns_at(hi):
                hi *= 2
            if hi > search_cap:
                hi = search_cap
                if not owns_at(hi):
                    return hi + 1

        lo = 1
        while lo < hi:
            mid = (lo + hi) // 2
            if owns_at(mid):
                hi = mid
            else:
                lo = mid + 1

        if cache_key is not None:
            self.exact_need_cache[cache_key] = lo
        return lo

    def min_ships_to_own_at(
        self, target_id, arrival_turn, attacker_owner,
        planned_commitments=None, extra_arrivals=(), upper_bound=None,
    ):
        return self.min_ships_to_own_by(
            target_id, arrival_turn, attacker_owner,
            arrival_turn=arrival_turn, planned_commitments=planned_commitments,
            extra_arrivals=extra_arrivals, upper_bound=upper_bound,
        )

    def reinforcement_needed_to_hold_until(
        self, planet_id, arrival_turn, hold_until, planned_commitments=None, upper_bound=None,
    ):
        planned_commitments = planned_commitments or {}
        target = self.planet_by_id[planet_id]
        arrival_turn = max(1, int(math.ceil(arrival_turn)))
        hold_until = max(arrival_turn, int(math.ceil(hold_until)))

        if target.owner != self.player:
            return self.min_ships_to_own_by(
                planet_id, hold_until, self.player, arrival_turn=arrival_turn,
                planned_commitments=planned_commitments, upper_bound=upper_bound,
            )

        def holds_with_reinforcement(ships):
            timeline = self.projected_timeline(
                planet_id, hold_until, planned_commitments=planned_commitments,
                extra_arrivals=((arrival_turn, self.player, int(ships)),),
            )
            for turn in range(arrival_turn, hold_until + 1):
                if timeline["owner_at"].get(turn) != self.player:
                    return False
            return True

        if upper_bound is not None:
            hi = max(1, int(upper_bound))
            if not holds_with_reinforcement(hi):
                return hi + 1
        else:
            hi = 1
            search_cap = self._ownership_search_cap(hold_until)
            while hi <= search_cap and not holds_with_reinforcement(hi):
                hi *= 2
            if hi > search_cap:
                hi = search_cap
                if not holds_with_reinforcement(hi):
                    return hi + 1

        lo = 1
        while lo < hi:
            mid = (lo + hi) // 2
            if holds_with_reinforcement(mid):
                hi = mid
            else:
                lo = mid + 1
        return lo

    def ships_needed_to_capture(
        self, target_id, arrival_turn, planned_commitments=None, extra_arrivals=()
    ):
        return self.min_ships_to_own_at(
            target_id, arrival_turn, self.player,
            planned_commitments=planned_commitments, extra_arrivals=extra_arrivals,
        )


# ============================================================
# Strategy Helpers
# ============================================================

def planet_distance(first, second):
    return math.hypot(first.x - second.x, first.y - second.y)


def nearest_sources_to_target(target, sources, top_k):
    if top_k <= 0 or len(sources) <= top_k:
        return sources
    return sorted(
        sources, key=lambda src: (planet_distance(src, target), -int(src.ships), src.id)
    )[:top_k]


def min_legal_reaction_time(target, sources, world):
    best = 10 ** 9
    for src in sources:
        seeded = world.best_probe_aim(src.id, target.id, max(1, int(src.ships)))
        if seeded is None:
            continue
        _, aim = seeded
        best = min(best, aim[1])
    return best


def policy_reaction_times(target_id, policy):
    return policy["reaction_time_map"].get(target_id, (10 ** 9, 10 ** 9))


def candidate_time_valid(target, turns, world, remaining_buffer):
    if turns > world.remaining_steps - remaining_buffer:
        return False
    if target.id in world.comet_ids:
        life = world.comet_life(target.id)
        if turns >= life or turns > COMET_MAX_CHASE_TURNS:
            return False
    return True


def stacked_enemy_proactive_keep(planet, world):
    threats = []
    for enemy in world.enemy_planets:
        seeded = world.best_probe_aim(enemy.id, planet.id, max(1, int(enemy.ships)))
        if seeded is None:
            continue
        _, aim = seeded
        eta = aim[1]
        if eta > MULTI_ENEMY_PROACTIVE_HORIZON:
            continue
        threats.append((eta, int(enemy.ships)))

    if not threats:
        return 0

    threats.sort()
    best_stacked = 0
    left = 0
    running = 0
    for right in range(len(threats)):
        running += threats[right][1]
        while threats[right][0] - threats[left][0] > MULTI_ENEMY_STACK_WINDOW:
            running -= threats[left][1]
            left += 1
        best_stacked = max(best_stacked, running)

    return int(best_stacked * MULTI_ENEMY_PROACTIVE_RATIO)


def swarm_eta_tolerance(options, target, world):
    if len(options) >= 3:
        return THREE_SOURCE_ETA_TOLERANCE
    if target.owner not in (-1, world.player):
        return HOSTILE_SWARM_ETA_TOLERANCE
    return MULTI_SOURCE_ETA_TOLERANCE


def detect_enemy_crashes(world):
    crashes = []
    for target_id, arrivals in world.arrivals_by_planet.items():
        enemy_events = [
            (int(math.ceil(eta)), owner, int(ships))
            for eta, owner, ships in arrivals
            if owner not in (-1, world.player) and ships > 0
        ]
        enemy_events.sort()
        for i in range(len(enemy_events)):
            eta_a, owner_a, ships_a = enemy_events[i]
            for j in range(i + 1, len(enemy_events)):
                eta_b, owner_b, ships_b = enemy_events[j]
                if owner_a == owner_b:
                    continue
                if abs(eta_a - eta_b) > CRASH_EXPLOIT_ETA_WINDOW:
                    break
                if ships_a + ships_b < CRASH_EXPLOIT_MIN_TOTAL_SHIPS:
                    continue
                crashes.append({
                    "target_id": target_id,
                    "crash_turn": max(eta_a, eta_b),
                    "owners": (owner_a, owner_b),
                    "ships": (ships_a, ships_b),
                })
    return crashes


def build_policy_state(world, deadline=None):
    def expired():
        return deadline is not None and time.perf_counter() > deadline

    indirect_wealth_map = {}
    for target_id, features in world.indirect_feature_map.items():
        friendly, neutral, enemy = features
        indirect_wealth_map[target_id] = (
            friendly * INDIRECT_FRIENDLY_WEIGHT
            + neutral * INDIRECT_NEUTRAL_WEIGHT
            + enemy * INDIRECT_ENEMY_WEIGHT
        )

    reserve = {}
    attack_budget = {}
    reaction_time_map = {}

    for target in world.planets:
        if expired():
            break
        if target.owner == world.player:
            continue
        my_sources = nearest_sources_to_target(target, world.my_planets, REACTION_SOURCE_TOP_K_MY)
        enemy_sources = nearest_sources_to_target(target, world.enemy_planets, REACTION_SOURCE_TOP_K_ENEMY)
        my_t = min_legal_reaction_time(target, my_sources, world)
        enemy_t = min_legal_reaction_time(target, enemy_sources, world)
        reaction_time_map[target.id] = (my_t, enemy_t)

    for planet in world.my_planets:
        if expired():
            break
        exact_keep = world.keep_needed_map.get(planet.id, 0)

        proactive_keep = 0
        for enemy in nearest_sources_to_target(planet, world.enemy_planets, PROACTIVE_ENEMY_TOP_K):
            enemy_aim = world.plan_shot(enemy.id, planet.id, max(1, int(enemy.ships)))
            if enemy_aim is None:
                continue
            enemy_eta = enemy_aim[1]
            if enemy_eta > PROACTIVE_DEFENSE_HORIZON:
                continue
            proactive_keep = max(proactive_keep, int(enemy.ships * PROACTIVE_DEFENSE_RATIO))
        proactive_keep = max(proactive_keep, stacked_enemy_proactive_keep(planet, world))

        reserve[planet.id] = min(int(planet.ships), max(exact_keep, proactive_keep))
        attack_budget[planet.id] = max(0, int(planet.ships) - reserve[planet.id])

    return {
        "indirect_wealth_map": indirect_wealth_map,
        "reserve": reserve,
        "attack_budget": attack_budget,
        "reaction_time_map": reaction_time_map,
    }


def build_modes(world):
    domination = (world.my_total - world.enemy_total) / max(1, world.my_total + world.enemy_total)
    is_behind = domination < BEHIND_DOMINATION
    is_ahead = domination > AHEAD_DOMINATION
    is_dominating = is_ahead or (
        world.max_enemy_strength > 0 and world.my_total > world.max_enemy_strength * 1.25
    )
    is_finishing = (
        domination > FINISHING_DOMINATION
        and world.my_prod > world.enemy_prod * FINISHING_PROD_RATIO
        and world.step > 100
    )

    attack_margin_mult = 1.0
    if is_ahead:
        attack_margin_mult += AHEAD_ATTACK_MARGIN_BONUS
    if is_behind:
        attack_margin_mult -= BEHIND_ATTACK_MARGIN_PENALTY
    if is_finishing:
        attack_margin_mult += FINISHING_ATTACK_MARGIN_BONUS

    return {
        "domination": domination,
        "is_behind": is_behind,
        "is_ahead": is_ahead,
        "is_dominating": is_dominating,
        "is_finishing": is_finishing,
        "attack_margin_mult": attack_margin_mult,
    }


def is_safe_neutral(target, policy):
    if target.owner != -1:
        return False
    my_t, enemy_t = policy_reaction_times(target.id, policy)
    return my_t <= enemy_t - SAFE_NEUTRAL_MARGIN


def is_contested_neutral(target, policy):
    if target.owner != -1:
        return False
    my_t, enemy_t = policy_reaction_times(target.id, policy)
    return abs(my_t - enemy_t) <= CONTESTED_NEUTRAL_MARGIN


def opening_filter(target, arrival_turns, needed, src_available, world, policy):
    if not world.is_opening or target.owner != -1:
        return False
    if target.id in world.comet_ids:
        return False
    if world.is_static(target.id):
        return False

    my_t, enemy_t = policy_reaction_times(target.id, policy)
    reaction_gap = enemy_t - my_t
    if (
        target.production >= SAFE_OPENING_PROD_THRESHOLD
        and arrival_turns <= SAFE_OPENING_TURN_LIMIT
        and reaction_gap >= SAFE_NEUTRAL_MARGIN
    ):
        return False

    if world.is_four_player:
        affordable = needed <= max(
            PARTIAL_SOURCE_MIN_SHIPS,
            int(src_available * FOUR_PLAYER_ROTATING_SEND_RATIO),
        )
        if (
            affordable
            and arrival_turns <= FOUR_PLAYER_ROTATING_TURN_LIMIT
            and reaction_gap >= FOUR_PLAYER_ROTATING_REACTION_GAP
        ):
            return False
        return True

    return arrival_turns > ROTATING_OPENING_MAX_TURNS or target.production <= ROTATING_OPENING_LOW_PROD


def target_value(target, arrival_turns, mission, world, modes, policy):
    turns_profit = max(1, world.remaining_steps - arrival_turns)
    if target.id in world.comet_ids:
        life = world.comet_life(target.id)
        turns_profit = max(0, min(turns_profit, life - arrival_turns))
        if turns_profit <= 0:
            return -1.0

    value = target.production * turns_profit
    value += policy["indirect_wealth_map"][target.id] * turns_profit * INDIRECT_VALUE_SCALE

    if world.is_static(target.id):
        value *= STATIC_NEUTRAL_VALUE_MULT if target.owner == -1 else STATIC_HOSTILE_VALUE_MULT
    else:
        value *= ROTATING_OPENING_VALUE_MULT if world.is_opening else 1.0

    if target.owner not in (-1, world.player):
        value *= OPENING_HOSTILE_TARGET_VALUE_MULT if world.is_opening else HOSTILE_TARGET_VALUE_MULT

    if target.owner == -1:
        if is_safe_neutral(target, policy):
            value *= SAFE_NEUTRAL_VALUE_MULT
        elif is_contested_neutral(target, policy):
            value *= CONTESTED_NEUTRAL_VALUE_MULT
        if world.is_early:
            value *= EARLY_NEUTRAL_VALUE_MULT

    if target.id in world.comet_ids:
        value *= COMET_VALUE_MULT

    if mission == "snipe":
        value *= SNIPE_VALUE_MULT
    elif mission == "swarm":
        value *= SWARM_VALUE_MULT
    elif mission == "reinforce":
        value *= REINFORCE_VALUE_MULT
    elif mission == "crash_exploit":
        value *= CRASH_EXPLOIT_VALUE_MULT

    if world.is_late:
        value += max(0, target.ships) * LATE_IMMEDIATE_SHIP_VALUE
        if target.owner not in (-1, world.player):
            enemy_strength = world.owner_strength.get(target.owner, 0)
            if enemy_strength <= WEAK_ENEMY_THRESHOLD:
                value += ELIMINATION_BONUS

    if modes["is_finishing"] and target.owner not in (-1, world.player):
        value *= FINISHING_HOSTILE_VALUE_MULT
    if modes["is_behind"] and target.owner == -1 and not world.is_static(target.id):
        value *= BEHIND_ROTATING_NEUTRAL_VALUE_MULT
    if modes["is_behind"] and target.owner == -1 and is_safe_neutral(target, policy):
        value *= 1.08
    if modes["is_dominating"] and target.owner == -1 and is_contested_neutral(target, policy):
        value *= 0.92

    return value


def reinforce_value(target, hold_until, world, policy):
    saved_turns = max(1, world.remaining_steps - hold_until)
    value = target.production * saved_turns + max(0, target.ships) * DEFENSE_SHIP_VALUE
    if world.enemy_planets and nearest_distance_to_set(target.x, target.y, world.enemy_planets) < 22:
        value *= DEFENSE_FRONTIER_SCORE_MULT
    value += policy["indirect_wealth_map"][target.id] * saved_turns * INDIRECT_VALUE_SCALE * 0.35
    return value * REINFORCE_VALUE_MULT


def preferred_send(target, base_needed, arrival_turns, src_available, world, modes, policy):
    """Compute preferred fleet size: base capture need + strategic margin, capped by budget."""
    send = max(base_needed, int(math.ceil(base_needed * modes["attack_margin_mult"])))
    margin = 0
    if target.owner == -1:
        margin += min(
            NEUTRAL_MARGIN_CAP,
            NEUTRAL_MARGIN_BASE + target.production * NEUTRAL_MARGIN_PROD_WEIGHT,
        )
    else:
        margin += min(
            HOSTILE_MARGIN_CAP,
            HOSTILE_MARGIN_BASE + target.production * HOSTILE_MARGIN_PROD_WEIGHT,
        )
    if world.is_static(target.id):
        margin += STATIC_TARGET_MARGIN
    if is_contested_neutral(target, policy):
        margin += CONTESTED_TARGET_MARGIN
    if world.is_four_player:
        margin += FOUR_PLAYER_TARGET_MARGIN
    if arrival_turns > LONG_TRAVEL_MARGIN_START:
        margin += min(LONG_TRAVEL_MARGIN_CAP, arrival_turns // LONG_TRAVEL_MARGIN_DIVISOR)
    if target.id in world.comet_ids:
        margin = max(0, margin - COMET_MARGIN_RELIEF)
    if modes["is_finishing"] and target.owner not in (-1, world.player):
        margin += FINISHING_HOSTILE_SEND_BONUS
    send = min(src_available, send + margin)
    return max(base_needed, send)


# ============================================================
# Score Computation
# ============================================================

def score_single_shot(
    src, target, ships, aim, needed, mission, world, modes, policy
):
    """Unified shot scoring: value / (ship_cost + turn_cost)."""
    angle, turns, _tx, _ty = aim
    value = target_value(target, turns, mission, world, modes, policy)
    if value <= 0:
        return -1.0

    cost_weight = SNIPE_COST_TURN_WEIGHT if mission == "snipe" else ATTACK_COST_TURN_WEIGHT
    cost = ships + turns * cost_weight
    score = value / max(1.0, cost)

    if world.is_static(target.id):
        score *= STATIC_TARGET_SCORE_MULT
        if world.is_early and target.owner == -1:
            score *= EARLY_STATIC_NEUTRAL_SCORE_MULT
    elif not world.is_static(target.id) and world.is_four_player and target.owner == -1:
        score *= FOUR_PLAYER_ROTATING_NEUTRAL_SCORE_MULT

    # Dense static neutral bonus: reward agents that accumulate static planets
    if target.owner == -1 and world.is_static(target.id):
        static_count = len(world.static_neutral_planets)
        if static_count >= DENSE_STATIC_NEUTRAL_COUNT:
            score *= DENSE_ROTATING_NEUTRAL_SCORE_MULT

    if mission == "snipe":
        score *= SNIPE_SCORE_MULT
    elif mission == "swarm":
        score *= SWARM_SCORE_MULT
    elif mission == "crash_exploit":
        score *= CRASH_EXPLOIT_SCORE_MULT

    return score


# ============================================================
# Mission Planning: Defense
# ============================================================

def plan_defense(world, policy, modes, spent, commitments, deadline):
    """Respond to imminent threats on own planets; return list of [src_id, angle, ships]."""
    actions = []
    threatened = []

    for planet in world.my_planets:
        fall_turn = world.fall_turn_map.get(planet.id)
        if fall_turn is None:
            continue
        if fall_turn > DEFENSE_LOOKAHEAD_TURNS:
            continue
        threatened.append((fall_turn, planet))

    threatened.sort(key=lambda t: t[0])

    for fall_turn, planet in threatened:
        if time.perf_counter() > deadline:
            break

        needed = world.reinforcement_needed_to_hold_until(
            planet.id, 1, fall_turn, planned_commitments=commitments
        )
        if needed <= 0:
            continue

        best_src = None
        best_score = -1.0
        best_aim = None
        best_send = 0

        for src in world.my_planets:
            if src.id == planet.id:
                continue
            budget = policy["attack_budget"].get(src.id, 0) - spent.get(src.id, 0)
            if budget < 1:
                continue

            seeded = world.best_probe_aim(src.id, planet.id, budget)
            if seeded is None:
                continue
            aim_ships, aim = seeded
            angle, turns, _tx, _ty = aim

            if turns > fall_turn + 2:
                continue

            send_needed = world.reinforcement_needed_to_hold_until(
                planet.id, turns, fall_turn, planned_commitments=commitments
            )
            if send_needed > budget:
                continue

            margin = DEFENSE_SEND_MARGIN_BASE + planet.production * DEFENSE_SEND_MARGIN_PROD_WEIGHT
            send = min(budget, send_needed + margin)

            saved_turns = max(1, world.remaining_steps - fall_turn)
            value = reinforce_value(planet, fall_turn, world, policy)
            cost = send + turns * DEFENSE_COST_TURN_WEIGHT
            score = value / max(1.0, cost)

            if score > best_score:
                best_score = score
                best_src = src
                best_aim = (angle, turns)
                best_send = send

        if best_src is not None and best_send >= 1:
            angle, turns = best_aim
            actions.append([best_src.id, angle, int(best_send)])
            spent[best_src.id] = spent.get(best_src.id, 0) + best_send
            commitments[planet.id].append((turns, world.player, int(best_send)))

    return actions


# ============================================================
# Mission Planning: Evacuation from Doomed Planets
# ============================================================

def plan_evacuations(world, policy, modes, spent, commitments, deadline):
    """Evacuate ships from planets that will fall and cannot be saved."""
    actions = []

    for planet in world.my_planets:
        if time.perf_counter() > deadline:
            break

        fall_turn = world.fall_turn_map.get(planet.id)
        if fall_turn is None or fall_turn > DOOMED_EVAC_TURN_LIMIT:
            continue

        keep = world.keep_needed_map.get(planet.id, 0)
        available = int(planet.ships) - keep - spent.get(planet.id, 0)
        if available < DOOMED_MIN_SHIPS:
            continue

        # Can we save it?
        if world.holds_full_map.get(planet.id, True):
            continue

        # Find best nearby destination
        best_dst = None
        best_score = -1.0
        best_aim = None
        best_send = 0

        candidates = sorted(
            world.my_planets + world.neutral_planets,
            key=lambda p: planet_distance(planet, p),
        )[:8]

        for dst in candidates:
            if dst.id == planet.id:
                continue
            if dst.id in world.comet_ids:
                continue

            seeded = world.best_probe_aim(planet.id, dst.id, available)
            if seeded is None:
                continue
            aim_ships, aim = seeded
            angle, turns, _tx, _ty = aim

            if not candidate_time_valid(dst, turns, world, LATE_CAPTURE_BUFFER):
                continue

            if dst.owner == world.player:
                value = planet.production * max(1, world.remaining_steps - turns)
                score = value / max(1.0, available + turns * REINFORCE_COST_TURN_WEIGHT)
            else:
                needed = world.ships_needed_to_capture(dst.id, turns, planned_commitments=commitments)
                if needed > available:
                    continue
                send = preferred_send(dst, needed, turns, available, world, modes, policy)
                value = target_value(dst, turns, "capture", world, modes, policy)
                score = value / max(1.0, send + turns * ATTACK_COST_TURN_WEIGHT)
                best_send = send

            if score > best_score:
                best_score = score
                best_dst = dst
                best_aim = (angle, turns)
                best_send = available if dst.owner == world.player else best_send

        if best_dst is not None and best_send >= 1:
            angle, turns = best_aim
            send = min(available, best_send)
            actions.append([planet.id, angle, int(send)])
            spent[planet.id] = spent.get(planet.id, 0) + send
            if best_dst.owner != world.player:
                commitments[best_dst.id].append((turns, world.player, int(send)))

    return actions


# ============================================================
# Mission Planning: Single-Source Attacks
# ============================================================

def plan_single_source_attacks(world, policy, modes, spent, commitments, deadline):
    """Score all (source, target) pairs and greedily select best non-conflicting shots."""
    capture_buffer = VERY_LATE_CAPTURE_BUFFER if world.is_very_late else LATE_CAPTURE_BUFFER

    all_shots = []
    targets = world.neutral_planets + world.enemy_planets

    for src in world.my_planets:
        if time.perf_counter() > deadline:
            break
        budget = policy["attack_budget"].get(src.id, 0) - spent.get(src.id, 0)
        if budget < 1:
            continue

        for target in targets:
            if target.id in world.comet_ids and target.production <= LOW_VALUE_COMET_PRODUCTION:
                if world.is_late:
                    continue

            seeded = world.best_probe_aim(src.id, target.id, budget)
            if seeded is None:
                continue
            aim_ships, aim = seeded
            angle, turns, _tx, _ty = aim

            if not candidate_time_valid(target, turns, world, capture_buffer):
                continue

            if opening_filter(target, turns, aim_ships, budget, world, policy):
                continue

            needed = world.ships_needed_to_capture(
                target.id, turns, planned_commitments=commitments
            )
            if needed > budget:
                continue
            if needed <= 0 and target.owner == world.player:
                continue

            send = preferred_send(target, max(1, needed), turns, budget, world, modes, policy)
            mission_type = "snipe" if send <= 6 and target.owner != -1 else "capture"
            score = score_single_shot(src, target, send, aim, needed, mission_type, world, modes, policy)
            if score <= 0:
                continue

            all_shots.append(ShotOption(
                score=score, src_id=src.id, target_id=target.id,
                angle=angle, turns=turns, needed=needed, send_cap=send, mission=mission_type,
            ))

    all_shots.sort(key=lambda s: -s.score)

    actions = []
    committed_targets = set()
    committed_sources = set()

    for shot in all_shots:
        if time.perf_counter() > deadline:
            break
        if shot.target_id in committed_targets:
            continue
        if shot.src_id in committed_sources:
            continue

        budget = policy["attack_budget"].get(shot.src_id, 0) - spent.get(shot.src_id, 0)
        if budget < shot.needed:
            continue

        send = min(shot.send_cap, budget)
        if send < shot.needed:
            continue

        # Re-verify needed with current commitments
        needed_now = world.ships_needed_to_capture(
            shot.target_id, shot.turns, planned_commitments=commitments
        )
        if needed_now > send:
            # Maybe a partial from another source already covers some
            if needed_now > budget:
                continue
            send = min(preferred_send(
                world.planet_by_id[shot.target_id], needed_now, shot.turns,
                budget, world, modes, policy,
            ), budget)
            if send < needed_now:
                continue

        actions.append([shot.src_id, shot.angle, int(send)])
        spent[shot.src_id] = spent.get(shot.src_id, 0) + send
        commitments[shot.target_id].append((shot.turns, world.player, int(send)))
        committed_targets.add(shot.target_id)
        committed_sources.add(shot.src_id)

    return actions


# ============================================================
# Mission Planning: Multi-Source Swarms
# ============================================================

def plan_multi_source_swarms(world, policy, modes, spent, commitments, deadline):
    """Coordinate simultaneous arrivals from multiple sources for hard targets."""
    capture_buffer = VERY_LATE_CAPTURE_BUFFER if world.is_very_late else LATE_CAPTURE_BUFFER
    actions = []

    targets = []
    for target in world.neutral_planets + world.enemy_planets:
        if target.id in world.comet_ids:
            continue
        if not candidate_time_valid(target, 1, world, capture_buffer):
            continue
        total_ships = int(target.ships)
        if total_ships < THREE_SOURCE_MIN_TARGET_SHIPS and target.owner == -1:
            continue
        targets.append(target)

    targets.sort(key=lambda t: (
        -target_value(t, 1, "swarm", world, modes, policy),
        t.id,
    ))

    for target in targets:
        if time.perf_counter() > deadline:
            break

        # Gather candidate sources
        sources_with_budget = []
        for src in world.my_planets:
            budget = policy["attack_budget"].get(src.id, 0) - spent.get(src.id, 0)
            if budget < PARTIAL_SOURCE_MIN_SHIPS:
                continue
            seeded = world.best_probe_aim(src.id, target.id, budget)
            if seeded is None:
                continue
            _, aim = seeded
            angle, turns, _tx, _ty = aim
            if not candidate_time_valid(target, turns, world, capture_buffer):
                continue
            sources_with_budget.append((turns, src, budget, angle))

        if len(sources_with_budget) < 2:
            continue

        sources_with_budget.sort()
        top_sources = sources_with_budget[:MULTI_SOURCE_TOP_K]

        # Find anchor turn (earliest turn where total budget exceeds need)
        best_plan = None
        best_score = -1.0

        for anchor_idx, (anchor_turns, anchor_src, anchor_budget, anchor_angle) in enumerate(top_sources):
            tol = swarm_eta_tolerance(top_sources, target, world)

            cohort = [(anchor_turns, anchor_src, anchor_budget, anchor_angle)]
            for turns_i, src_i, budget_i, angle_i in top_sources:
                if src_i.id == anchor_src.id:
                    continue
                if abs(turns_i - anchor_turns) > tol:
                    continue
                cohort.append((turns_i, src_i, budget_i, angle_i))

            if len(cohort) < 2:
                continue
            if not THREE_SOURCE_SWARM_ENABLED and len(cohort) >= 3:
                cohort = cohort[:2]

            total_budget = sum(b for _, _, b, _ in cohort)
            needed = world.ships_needed_to_capture(
                target.id, anchor_turns, planned_commitments=commitments
            )
            if needed > total_budget:
                continue
            if needed <= 0:
                continue

            value = target_value(target, anchor_turns, "swarm", world, modes, policy)
            penalty = MULTI_SOURCE_PLAN_PENALTY if len(cohort) == 2 else THREE_SOURCE_PLAN_PENALTY
            cost = needed + anchor_turns * ATTACK_COST_TURN_WEIGHT
            score = value / max(1.0, cost) * penalty

            if score > best_score:
                best_score = score
                best_plan = (needed, cohort, anchor_turns)

        if best_plan is None or best_score <= 0:
            continue

        needed, cohort, anchor_turns = best_plan

        # Distribute needed ships proportionally
        total_budget = sum(b for _, _, b, _ in cohort)
        distributed = []
        remaining_need = needed
        for i, (turns_i, src_i, budget_i, angle_i) in enumerate(cohort):
            if i == len(cohort) - 1:
                alloc = remaining_need
            else:
                alloc = max(1, int(needed * budget_i / total_budget))
            alloc = min(alloc, budget_i)
            alloc = max(1, alloc)
            distributed.append((src_i, angle_i, turns_i, alloc))
            remaining_need = max(0, remaining_need - alloc)

        if remaining_need > 0:
            continue

        for src_i, angle_i, turns_i, alloc in distributed:
            actions.append([src_i.id, angle_i, int(alloc)])
            spent[src_i.id] = spent.get(src_i.id, 0) + alloc
        commitments[target.id].append((anchor_turns, world.player, int(needed)))

    return actions


# ============================================================
# Mission Planning: Crash Exploitation
# ============================================================

def plan_crash_exploits(world, policy, modes, spent, commitments, deadline):
    """Attack planets where two enemy fleets will cancel each other out."""
    if not CRASH_EXPLOIT_ENABLED:
        return []

    actions = []
    crashes = detect_enemy_crashes(world)
    capture_buffer = VERY_LATE_CAPTURE_BUFFER if world.is_very_late else LATE_CAPTURE_BUFFER

    for crash in crashes:
        if time.perf_counter() > deadline:
            break

        target_id = crash["target_id"]
        crash_turn = crash["crash_turn"]
        exploit_turn = crash_turn + CRASH_EXPLOIT_POST_CRASH_DELAY

        target = world.planet_by_id.get(target_id)
        if target is None:
            continue
        if not candidate_time_valid(target, exploit_turn, world, capture_buffer):
            continue

        best_src = None
        best_score = -1.0
        best_aim_data = None
        best_send = 0

        for src in world.my_planets:
            budget = policy["attack_budget"].get(src.id, 0) - spent.get(src.id, 0)
            if budget < 1:
                continue

            seeded = world.best_probe_aim(
                src.id, target_id, budget,
                min_turn=exploit_turn, max_turn=exploit_turn + CRASH_EXPLOIT_ETA_WINDOW,
            )
            if seeded is None:
                continue
            aim_ships, aim = seeded
            angle, turns, _tx, _ty = aim

            needed = world.ships_needed_to_capture(
                target_id, turns, planned_commitments=commitments,
                extra_arrivals=[(crash_turn, crash["owners"][0], -crash["ships"][0]),
                                (crash_turn, crash["owners"][1], -crash["ships"][1])],
            )
            needed = max(1, needed)
            if needed > budget:
                continue

            send = preferred_send(target, needed, turns, budget, world, modes, policy)
            value = target_value(target, turns, "crash_exploit", world, modes, policy)
            score = value / max(1.0, send + turns * ATTACK_COST_TURN_WEIGHT)
            score *= CRASH_EXPLOIT_SCORE_MULT

            if score > best_score:
                best_score = score
                best_src = src
                best_aim_data = (angle, turns)
                best_send = send

        if best_src is not None and best_send >= 1:
            angle, turns = best_aim_data
            budget = policy["attack_budget"].get(best_src.id, 0) - spent.get(best_src.id, 0)
            send = min(best_send, budget)
            if send >= 1:
                actions.append([best_src.id, angle, int(send)])
                spent[best_src.id] = spent.get(best_src.id, 0) + send
                commitments[target_id].append((turns, world.player, int(send)))

    return actions


# ============================================================
# Mission Planning: Proactive Reinforcement
# ============================================================

def plan_reinforcements(world, policy, modes, spent, commitments, deadline):
    """Reinforce frontier planets that are weakening but not yet under attack."""
    if not REINFORCE_ENABLED:
        return []
    if world.remaining_steps < REINFORCE_MIN_FUTURE_TURNS:
        return []

    actions = []

    for target in world.my_planets:
        if time.perf_counter() > deadline:
            break
        if target.production < REINFORCE_MIN_PRODUCTION:
            continue
        if world.holds_full_map.get(target.id, True):
            continue  # Already safe

        hold_until = min(REINFORCE_HOLD_LOOKAHEAD, world.remaining_steps)

        best_src = None
        best_score = -1.0
        best_aim_data = None
        best_send = 0

        for src in world.my_planets:
            if src.id == target.id:
                continue
            budget = policy["attack_budget"].get(src.id, 0) - spent.get(src.id, 0)
            if budget < 1:
                continue

            max_send = min(budget, int(src.ships * REINFORCE_MAX_SOURCE_FRACTION))
            if max_send < 1:
                continue

            seeded = world.best_probe_aim(
                src.id, target.id, max_send, max_turn=REINFORCE_MAX_TRAVEL_TURNS
            )
            if seeded is None:
                continue
            aim_ships, aim = seeded
            angle, turns, _tx, _ty = aim
            if turns > REINFORCE_MAX_TRAVEL_TURNS:
                continue

            needed = world.reinforcement_needed_to_hold_until(
                target.id, turns, hold_until, planned_commitments=commitments
            )
            needed += REINFORCE_SAFETY_MARGIN
            if needed > max_send:
                continue

            value = reinforce_value(target, hold_until, world, policy)
            cost = needed + turns * REINFORCE_COST_TURN_WEIGHT
            score = value / max(1.0, cost)

            if score > best_score:
                best_score = score
                best_src = src
                best_aim_data = (angle, turns)
                best_send = needed

        if best_src is not None and best_send >= 1:
            angle, turns = best_aim_data
            budget = policy["attack_budget"].get(best_src.id, 0) - spent.get(best_src.id, 0)
            send = min(best_send, budget)
            if send >= 1:
                actions.append([best_src.id, angle, int(send)])
                spent[best_src.id] = spent.get(best_src.id, 0) + send
                commitments[target.id].append((turns, world.player, int(send)))

    return actions


# ============================================================
# Mission Planning: Rear-Area Forwarding
# ============================================================

def plan_rear_forwarding(world, policy, modes, spent, commitments, deadline):
    """Move surplus ships from safe rear planets toward the frontline."""
    if not world.my_planets or not (world.enemy_planets or world.neutral_planets):
        return []
    if world.step / TOTAL_STEPS < REAR_STAGE_PROGRESS:
        return []

    actions = []
    game_progress = world.step / TOTAL_STEPS

    send_ratio = (
        REAR_SEND_RATIO_FOUR_PLAYER if world.is_four_player else REAR_SEND_RATIO_TWO_PLAYER
    )

    # Identify rear sources: far from enemies, large garrison
    front_planets = world.enemy_planets + world.neutral_planets
    if not front_planets:
        return []

    avg_enemy_x = sum(p.x for p in world.enemy_planets) / max(1, len(world.enemy_planets))
    avg_enemy_y = sum(p.y for p in world.enemy_planets) / max(1, len(world.enemy_planets))

    my_frontier = sorted(
        world.my_planets,
        key=lambda p: dist(p.x, p.y, avg_enemy_x, avg_enemy_y),
    )
    if len(my_frontier) < 2:
        return []

    # Forward-most half are frontline; rear-most are candidates
    n_front = max(1, len(my_frontier) // 2)
    front_set = my_frontier[:n_front]
    rear_candidates = my_frontier[n_front:]

    for src in rear_candidates:
        if time.perf_counter() > deadline:
            break

        budget = policy["attack_budget"].get(src.id, 0) - spent.get(src.id, 0)
        if budget < REAR_SOURCE_MIN_SHIPS:
            continue

        # Don't strip rear planet entirely
        send = int(budget * send_ratio)
        send = max(REAR_SEND_MIN_SHIPS, min(send, budget))
        if send < REAR_SEND_MIN_SHIPS:
            continue

        # Find the best frontline target
        best_dst = None
        best_score = -1.0
        best_aim_data = None
        best_final_send = 0

        for dst in front_set:
            seeded = world.best_probe_aim(src.id, dst.id, send, max_turn=REAR_MAX_TRAVEL_TURNS)
            if seeded is None:
                continue
            aim_ships, aim = seeded
            angle, turns, _tx, _ty = aim
            if turns > REAR_MAX_TRAVEL_TURNS:
                continue

            value = reinforce_value(dst, turns, world, policy)
            cost = send + turns * REINFORCE_COST_TURN_WEIGHT
            score = value / max(1.0, cost)

            if score > best_score:
                best_score = score
                best_dst = dst
                best_aim_data = (angle, turns)
                best_final_send = send

        if best_dst is not None and best_final_send >= 1:
            angle, turns = best_aim_data
            budget = policy["attack_budget"].get(src.id, 0) - spent.get(src.id, 0)
            final_send = min(best_final_send, budget)
            if final_send >= 1:
                actions.append([src.id, angle, int(final_send)])
                spent[src.id] = spent.get(src.id, 0) + final_send
                commitments[best_dst.id].append((turns, world.player, int(final_send)))

    return actions


# ============================================================
# Recapture Planning
# ============================================================

def plan_recaptures(world, policy, modes, spent, commitments, deadline):
    """Quickly recapture planets that just fell or are about to fall."""
    actions = []
    capture_buffer = VERY_LATE_CAPTURE_BUFFER if world.is_very_late else LATE_CAPTURE_BUFFER

    recently_lost = []
    for planet in world.enemy_planets:
        # Heuristic: low ship count suggests recently captured
        if int(planet.ships) <= 3:
            recently_lost.append(planet)

    recently_lost.sort(key=lambda p: (
        -target_value(p, 1, "snipe", world, modes, policy), p.id
    ))

    for target in recently_lost:
        if time.perf_counter() > deadline:
            break

        best_src = None
        best_score = -1.0
        best_aim_data = None
        best_send = 0

        for src in world.my_planets:
            budget = policy["attack_budget"].get(src.id, 0) - spent.get(src.id, 0)
            if budget < 1:
                continue

            seeded = world.best_probe_aim(src.id, target.id, budget, max_turn=RECAPTURE_LOOKAHEAD_TURNS)
            if seeded is None:
                continue
            aim_ships, aim = seeded
            angle, turns, _tx, _ty = aim
            if turns > RECAPTURE_LOOKAHEAD_TURNS:
                continue
            if not candidate_time_valid(target, turns, world, capture_buffer):
                continue

            needed = world.ships_needed_to_capture(target.id, turns, planned_commitments=commitments)
            if needed > budget or needed <= 0:
                continue

            send = preferred_send(target, needed, turns, budget, world, modes, policy)
            value = target_value(target, turns, "snipe", world, modes, policy) * RECAPTURE_VALUE_MULT
            if world.enemy_planets and nearest_distance_to_set(target.x, target.y, world.enemy_planets) < 20:
                value *= RECAPTURE_FRONTIER_MULT
            cost = send + turns * RECAPTURE_COST_TURN_WEIGHT
            score = value / max(1.0, cost)

            if score > best_score:
                best_score = score
                best_src = src
                best_aim_data = (angle, turns)
                best_send = send

        if best_src is not None and best_send >= 1:
            angle, turns = best_aim_data
            budget = policy["attack_budget"].get(best_src.id, 0) - spent.get(best_src.id, 0)
            send = min(best_send, budget)
            if send >= 1:
                actions.append([best_src.id, angle, int(send)])
                spent[best_src.id] = spent.get(best_src.id, 0) + send
                commitments[target.id].append((turns, world.player, int(send)))

    return actions


# ============================================================
# Agent Entry Point
# ============================================================

def agent(obs):
    t_start = time.perf_counter()

    # ── Parse observation ──────────────────────────────────
    planets_raw = obs.get("planets", [])
    fleets_raw = obs.get("fleets", [])
    player = obs.get("player", 0)
    step = obs.get("step", 0)
    ang_vel = obs.get("angular_velocity", 0.0)
    initial_planets_raw = obs.get("initial_planets", [])
    comets_raw = obs.get("comets", [])
    comet_ids = obs.get("comet_planet_ids", [])
    remaining_overage = obs.get("remainingOverageTime", 1.0)

    planets = [Planet(*p) for p in planets_raw]
    fleets = [Fleet(*f) for f in fleets_raw]
    initial_by_id = {p[0]: Planet(*p) for p in initial_planets_raw}

    if not planets:
        return []

    # ── Time budget ────────────────────────────────────────
    # Use at most SOFT_ACT_DEADLINE of the remaining overage + 0.82 s base
    budget_seconds = 0.82 + min(0.15, remaining_overage * 0.05)
    hard_deadline = t_start + budget_seconds

    # ── World model ────────────────────────────────────────
    world = WorldModel(player, step, planets, fleets, initial_by_id, ang_vel, comets_raw, comet_ids)

    if not world.my_planets:
        return []

    # ── Policy & mode ──────────────────────────────────────
    policy_deadline = t_start + budget_seconds * HEAVY_PHASE_MIN_TIME
    policy = build_policy_state(world, deadline=policy_deadline)
    modes = build_modes(world)

    # ── Mission planning ───────────────────────────────────
    spent = defaultdict(int)       # ships spent per source planet this turn
    commitments = defaultdict(list)  # (turn, owner, ships) arrivals we've planned

    all_actions = []

    def remaining_time():
        return hard_deadline - time.perf_counter()

    # Phase 1 – Defense (highest priority, must run)
    if remaining_time() > 0:
        actions = plan_defense(world, policy, modes, spent, commitments, hard_deadline)
        all_actions.extend(actions)

    # Phase 2 – Evacuate doomed planets
    if remaining_time() > HEAVY_PHASE_MIN_TIME:
        actions = plan_evacuations(world, policy, modes, spent, commitments, hard_deadline)
        all_actions.extend(actions)

    # Phase 3 – Recapture recently lost planets
    if remaining_time() > HEAVY_PHASE_MIN_TIME:
        actions = plan_recaptures(world, policy, modes, spent, commitments, hard_deadline)
        all_actions.extend(actions)

    # Phase 4 – Single-source captures (main attack loop)
    if remaining_time() > HEAVY_PHASE_MIN_TIME:
        actions = plan_single_source_attacks(world, policy, modes, spent, commitments, hard_deadline)
        all_actions.extend(actions)

    # Phase 5 – Multi-source swarms for hard targets
    if remaining_time() > OPTIONAL_PHASE_MIN_TIME:
        actions = plan_multi_source_swarms(world, policy, modes, spent, commitments, hard_deadline)
        all_actions.extend(actions)

    # Phase 6 – Crash exploitation
    if remaining_time() > OPTIONAL_PHASE_MIN_TIME:
        actions = plan_crash_exploits(world, policy, modes, spent, commitments, hard_deadline)
        all_actions.extend(actions)

    # Phase 7 – Reinforcement of weakening planets
    if remaining_time() > OPTIONAL_PHASE_MIN_TIME:
        actions = plan_reinforcements(world, policy, modes, spent, commitments, hard_deadline)
        all_actions.extend(actions)

    # Phase 8 – Rear forwarding (late game only)
    if remaining_time() > OPTIONAL_PHASE_MIN_TIME:
        actions = plan_rear_forwarding(world, policy, modes, spent, commitments, hard_deadline)
        all_actions.extend(actions)

    # ── Sanitize: never send 0 ships or from a planet we don't own ─────────
    valid_actions = []
    for act in all_actions:
        if len(act) != 3:
            continue
        src_id, angle, ships = act
        if ships <= 0:
            continue
        src = world.planet_by_id.get(src_id)
        if src is None or src.owner != player:
            continue
        if ships > int(src.ships):
            ships = int(src.ships)
        if ships <= 0:
            continue
        valid_actions.append([src_id, float(angle), int(ships)])

    return valid_actions
```

## [MD]
## Cell 3 — Validate agent locally

## [CODE]
```python
# ── Quick sanity-check: run one turn locally ─────────────────────────────
import math
from submission import agent

obs_test = {
    'player': 0, 'step': 100, 'angular_velocity': 0.03,
    'remainingOverageTime': 60.0, 'comet_planet_ids': [], 'comets': [],
    'initial_planets': [
        [0, 0, 15., 15., 2., 80, 3], [1, 0, 25., 85., 2., 60, 2],
        [2, 1, 85., 15., 2., 50, 4], [3, 1, 85., 85., 2., 40, 3],
        [4,-1, 50., 10., 2., 10, 5], [5,-1, 10., 50., 2.,  8, 4],
    ],
    'planets': [
        [0, 0, 15., 15., 2., 80, 3], [1, 0, 25., 85., 2., 60, 2],
        [2, 1, 85., 15., 2., 50, 4], [3, 1, 85., 85., 2., 40, 3],
        [4,-1, 50., 10., 2., 10, 5], [5,-1, 10., 50., 2.,  8, 4],
    ],
    'fleets': [],
}

actions = agent(obs_test)
assert isinstance(actions, list), 'agent must return a list'
for a in actions:
    assert len(a) == 3 and a[2] > 0, f'bad action: {a}'
print(f'OK — {len(actions)} action(s) this turn:')
for a in actions:
    print(f'  planet {a[0]} → {a[2]} ships at {math.degrees(a[1]):.1f}°')
```
