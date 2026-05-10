## [MD]
# -HTML

## [CODE]
```python
from IPython.display import HTML, display

display(HTML(r"""
<div style="max-width: 1480px; margin: 0 auto; padding: 18px 6px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #243042;">
  <div style="background: linear-gradient(180deg, #f7f9fc 0%, #eef4fb 100%); border: 1px solid #d9e2ef; border-radius: 30px; padding: 28px 30px 24px 30px; box-shadow: 0 16px 36px rgba(36, 48, 66, 0.08); overflow: hidden;">
    <div style="font-size: 40px; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 10px;">
      🛰️ Structured System Map
    </div>
    <div style="font-size: 20px; line-height: 1.5; color: #5a6b84; max-width: 1180px; margin-bottom: 10px;">
      v11 combines arrival-time ownership forecasting, reinforce-to-hold defense, rescue-versus-recapture timing, multi-source swarm pressure, and crash-window opportunism inside one structured baseline.
    </div>
    <div style="font-size: 17px; line-height: 1.55; color: #6a7890; max-width: 1180px; margin-bottom: 22px;">
      Ships are spent only after three things agree: one direct shot is legal, the target still looks good at the true arrival turn, and the mission remains valid after earlier launches are written into the future.
    </div>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; margin-bottom: 18px;">
      <div style="background: #eef4ff; border: 2px solid #7aa4ff; border-radius: 24px; padding: 18px 20px;">
        <div style="display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; border-radius: 999px; background: #dbe8ff; color: #233246; font-size: 18px; font-weight: 800; margin-bottom: 12px;">1</div>
        <div style="font-size: 21px; font-weight: 800; color: #233246; margin-bottom: 8px;">🧱 Legal Shot</div>
        <div style="font-size: 15px; line-height: 1.65; color: #607089;">Probe several realistic fleet sizes, reject sun-crossing segments, and keep only one direct launch that the rules can actually execute.</div>
      </div>
      <div style="background: #eefaf6; border: 2px solid #6bc38b; border-radius: 24px; padding: 18px 20px;">
        <div style="display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; border-radius: 999px; background: #d7f1e0; color: #233246; font-size: 18px; font-weight: 800; margin-bottom: 12px;">2</div>
        <div style="font-size: 21px; font-weight: 800; color: #233246; margin-bottom: 8px;">🛡️ Future State</div>
        <div style="font-size: 15px; line-height: 1.65; color: #607089;">Replay arrivals, production, and same-turn combat at that ETA so ownership, garrison, and exact need are forecasted instead of guessed.</div>
      </div>
      <div style="background: #fff6ec; border: 2px solid #f2af52; border-radius: 24px; padding: 18px 20px;">
        <div style="display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; border-radius: 999px; background: #ffe2bc; color: #233246; font-size: 18px; font-weight: 800; margin-bottom: 12px;">3</div>
        <div style="font-size: 21px; font-weight: 800; color: #233246; margin-bottom: 8px;">🧯 Hold Logic</div>
        <div style="font-size: 15px; line-height: 1.65; color: #607089;">Split owned-planet decisions into reinforce-to-hold, rescue, and recapture so defense respects fall timing instead of collapsing into one shortcut.</div>
      </div>
      <div style="background: #fff0f6; border: 2px solid #f08cb2; border-radius: 24px; padding: 18px 20px;">
        <div style="display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; border-radius: 999px; background: #ffd6e6; color: #233246; font-size: 18px; font-weight: 800; margin-bottom: 12px;">4</div>
        <div style="font-size: 21px; font-weight: 800; color: #233246; margin-bottom: 8px;">🚀 Mission Layer</div>
        <div style="font-size: 15px; line-height: 1.65; color: #607089;">Spend ships on the best forecasted conversion: single capture, snipe, compact swarm, hostile swarm, post-crash exploit, or one more clean follow-up.</div>
      </div>
      <div style="background: #f7f3ff; border: 2px solid #b79cf7; border-radius: 24px; padding: 18px 20px;">
        <div style="display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; border-radius: 999px; background: #e7dcff; color: #233246; font-size: 18px; font-weight: 800; margin-bottom: 12px;">5</div>
        <div style="font-size: 21px; font-weight: 800; color: #233246; margin-bottom: 8p x;">🔁 Commit Loop</div>
        <div style="font-size: 15px; line-height: 1.65; color: #607089;">Re-aim final sends, append ETA-aware commitments, refresh live doomed checks, and use leftover ships for salvage or rear-to-front staging.</div>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 14px;">
      <div style="background: rgba(122, 164, 255, 0.08); border: 1px solid #cddcff; border-radius: 22px; padding: 16px 18px;">
        <div style="font-size: 18px; font-weight: 800; margin-bottom: 8px;">☀️ Direct Means Direct</div>
        <div style="font-size: 15px; line-height: 1.6; color: #5f7088;">Sun-crossing lines are discarded. No waypoint route is invented beyond what the game allows.</div>
      </div>
      <div style="background: rgba(107, 195, 139, 0.08); border: 1px solid #cbe9d7; border-radius: 22px; padding: 16px 18px;">
        <div style="font-size: 18px; font-weight: 800; margin-bottom: 8px;">⚔️ Ownership At ETA</div>
        <div style="font-size: 15px; line-height: 1.6; color: #5f7088;">Same-turn arrivals cancel by owner before the garrison fight, so need and hold logic are always arrival-time questions.</div>
      </div>
      <div style="background: rgba(240, 140, 178, 0.08); border: 1px solid #f3cade; border-radius: 22px; padding: 16px 18px;">
        <div style="font-size: 18px; font-weight: 800; margin-bottom: 8px;">🤝 Partial Sources Matter</div>
        <div style="font-size: 15px; line-height: 1.6; color: #5f7088;">Small contributors stay alive long enough to assemble two-source and three-source swarms at one synchronized arrival window.</div>
      </div>
      <div style="background: rgba(183, 156, 247, 0.08); border: 1px solid #d8c8ff; border-radius: 22px; padding: 16px 18px;">
        <div style="font-size: 18px; font-weight: 800; margin-bottom: 8px;">🧭 Refresh The Future</div>
        <div style="font-size: 15px; line-height: 1.6; color: #5f7088;">Every accepted launch rewrites the future. Later missions, salvage, and rear staging all read that updated commitment-aware state.</div>
      </div>
    </div>
  </div>
</div>
"""))
```

## [CODE]
```python
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version


def parse_version(text):
    parts = []
    for token in text.split('.'):
        digits = ''.join(ch for ch in token if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)


required_version = (1, 28, 0)
needs_upgrade = False

try:
    installed_version = parse_version(version('kaggle-environments'))
    needs_upgrade = installed_version < required_version
except PackageNotFoundError:
    needs_upgrade = True

if needs_upgrade:
    subprocess.check_call(
        [sys.executable, '-m', 'pip', 'install', '-q', '--upgrade', 'kaggle-environments>=1.28.0']
    )

import kaggle_environments  # noqa: F401
```

## [MD]
# -Setup

## [CODE]
```python
import math
import time
from collections import defaultdict, namedtuple

# --- Constants ---
BOARD = 100.0
MAX_SPEED = 6.0
TOTAL_STEPS = 500
PARTIAL_SOURCE_MIN_SHIPS = 3
LATE_CAPTURE_BUFFER = 5

Planet = namedtuple("Planet", ["id", "owner", "x", "y", "radius", "ships", "production"])

def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)

def fleet_speed(ships):
    if ships <= 1:
        return 1.0
    ratio = math.log(max(1.1, ships)) / math.log(1000.0)
    ratio = max(0.0, min(1.0, ratio))
    return 1.0 + (MAX_SPEED - 1.0) * (ratio**1.5)

class WorldModel:
    def __init__(self, player, step, planets):
        self.player = player
        self.step = step
        self.planets = planets
        self.my_planets = [p for p in planets if p.owner == player]
        self.enemy_planets = [p for p in planets if p.owner not in (-1, player)]
        self.planet_by_id = {p.id: p for p in planets}
        self.remaining_steps = TOTAL_STEPS - step

    def best_probe_aim(self, src_id, target_id, ships):
        src = self.planet_by_id[src_id]
        target = self.planet_by_id[target_id]
        angle = math.atan2(target.y - src.y, target.x - src.x)
        d = dist(src.x, src.y, target.x, target.y) - src.radius - target.radius
        turns = max(1, int(math.ceil(d / fleet_speed(ships))))
        return ships, (angle, turns)

    def min_ships_to_own_at(self, target_id, turns, commitments):
        target = self.planet_by_id.get(target_id)
        if not target: return 999
        ships = target.ships + (target.production * turns if target.owner != -1 else 0)
        for t, owner, s in commitments.get(target_id, []):
            if t <= turns:
                ships = ships + s if owner == target.owner else ships - s
        return max(1, int(ships + 1))

def plan_moves(world, deadline=None):
    def expired():
        return deadline is not None and time.perf_counter() > deadline

    planned_commitments = defaultdict(list)
    moves, spent_total = [], defaultdict(int)
    intercept_cache = {}

    def get_aim(s_id, t_id, sh):
        if (s_id, t_id) not in intercept_cache:
            intercept_cache[(s_id, t_id)] = world.best_probe_aim(s_id, t_id, sh)
        return intercept_cache[(s_id, t_id)]

    for src in world.my_planets:
        if expired(): break
        src_avail = max(0, int(src.ships) - spent_total[src.id])
        if src_avail < PARTIAL_SOURCE_MIN_SHIPS: continue

        for target in sorted(world.planets, key=lambda t: dist(src.x, src.y, t.x, t.y)):
            if target.id == src.id or target.owner == world.player: continue

            aim_info = get_aim(src.id, target.id, src_avail)
            turns = aim_info[1][1]
            if turns > world.remaining_steps - LATE_CAPTURE_BUFFER: continue

            needed = world.min_ships_to_own_at(target.id, turns, planned_commitments)
            if 0 < needed <= src_avail:
                angle = aim_info[1][0]
                moves.append([src.id, float(angle), int(needed)])
                spent_total[src.id] += needed
                planned_commitments[target.id].append((turns, world.player, int(needed)))
    return moves

def agent(obs, config=None):
    start_time = time.perf_counter()
    player = obs.get("player", 0)
    step = obs.get("step", 0)
    planets = [Planet(*p) for p in obs.get("planets", [])]
    world = WorldModel(player, step, planets)
    if not world.my_planets: return []

    timeout = config.get("actTimeout", 1.0) if config else 1.0
    deadline = start_time + (timeout * 0.8)
    return plan_moves(world, deadline)
```

## [MD]
*   Physics Boundaries

## [CODE]
```python
%%writefile -a submission.py

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
    return 1.0 + (MAX_SPEED - 1.0) * (ratio**1.5)
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
    # Launch from the source boundary and time the route to the first hit on
    # the target circle.
    angle, start_x, start_y, end_x, end_y, hit_distance = actual_path_geometry(
        sx,
        sy,
        sr,
        tx,
        ty,
        tr,
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
    # Use one boundary-aware ETA model for routing, ranking, reserve, and
    # launch decisions.
    safe = safe_angle_and_distance(sx, sy, sr, tx, ty, tr)
    if safe is None:
        return None
    angle, total_d = safe
    turns = max(1, int(math.ceil(total_d / fleet_speed(max(1, ships)))))
    return angle, turns


def travel_time(sx, sy, sr, tx, ty, tr, ships):
    est = estimate_arrival(sx, sy, sr, tx, ty, tr, ships)
    if est is None:
        return 10**9
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
    # If the direct line is unsafe, scan future positions and keep the earliest
    # viable intercept window.
    best = None
    best_score = None
    max_turns = min(HORIZON, ROUTE_SEARCH_HORIZON)
    if target.id in comet_ids:
        max_turns = min(max_turns, max(0, comet_remaining_life(target.id, comets) - 1))

    for candidate_turns in range(1, max_turns + 1):
        pos = predict_target_position(
            target,
            candidate_turns,
            initial_by_id,
            ang_vel,
            comets,
            comet_ids,
        )
        if pos is None:
            continue
        est = estimate_arrival(src.x, src.y, src.radius, pos[0], pos[1], target.radius, ships)
        if est is None:
            continue
        _, turns = est
        if abs(turns - candidate_turns) > INTERCEPT_TOLERANCE:
            continue
        score = candidate_turns
        continue

        actual_turns = max(turns, candidate_turns)
        actual_pos = predict_target_position(
            target,
            actual_turns,
            initial_by_id,
            ang_vel,
            comets,
            comet_ids,
        )
        if actual_pos is None:
            continue

        confirm = estimate_arrival(
            src.x,
            src.y,
            src.radius,
            actual_pos[0],
            actual_pos[1],
            target.radius,
            ships,
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
    # Iterate toward a self-consistent moving-target intercept, then fall back
    # to a later safe window if needed.
    est = estimate_arrival(src.x, src.y, src.radius, target.x, target.y, target.radius, ships)
    if est is None:
        if not target_can_move(target, initial_by_id, comet_ids):
            return None
        return search_safe_intercept(
            src,
            target,
            ships,
            initial_by_id,
            ang_vel,
            comets,
            comet_ids,
        )
         initial_by_id,
            ang_vel,
            comets,
            comet_ids,
        )

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
            return search_safe_intercept(
                src,
                target,
                ships,
                initial_by_id,
                ang_vel,
                comets,
                comet_ids,
            )
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
        return search_safe_intercept(
            src,
            target,
            ships,
            initial_by_id,
            ang_vel,
            comets,
            comet_ids,
        )
    return final_est[0], final_est[1], tx, ty
```

## [MD]
* World Model

## [CODE]
```python
%%writefile -a submission.py
# World Model

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
        if proj < 0: continue
        perp_sq = dx * dx + dy * dy - proj * proj
        radius_sq = planet.radius * planet.radius
        if perp_sq >= radius_sq: continue
        hit_d = max(0.0, proj - math.sqrt(max(0.0, radius_sq - perp_sq)))
        turns = hit_d / speed
        if turns <= HORIZON and turns < best_time:
            best_time = turns
            best_planet = planet
    return best_planet, int(math.ceil(best_time)) if best_planet else (None, None)

def resolve_arrival_event(owner, garrison, arrivals):
    by_owner = {}
    for _, attacker_owner, ships in arrivals:
        by_owner[attacker_owner] = by_owner.get(attacker_owner, 0) + ships
    if not by_owner: return owner, max(0.0, garrison)
    sorted_players = sorted(by_owner.items(), key=lambda item: item[1], reverse=True)
    top_owner, top_ships = sorted_players[0]
    second_ships = sorted_players[1][1] if len(sorted_players) > 1 else 0
    if top_ships == second_ships:
        survivor_owner, survivor_ships = -1, 0
    else:
        survivor_owner, survivor_ships = top_owner, top_ships - second_ships
    if survivor_ships <= 0: return owner, max(0.0, garrison)
    if owner == survivor_owner: return owner, garrison + survivor_ships
    garrison -= survivor_ships
    if garrison < 0: return survivor_owner, -garrison
    return owner, garrison

def simulate_planet_timeline(planet, arrivals, player, horizon):
    horizon = max(0, int(math.ceil(horizon)))
    events = sorted([(max(1, int(math.ceil(t))), o, s) for t, o, s in arrivals if s > 0], key=lambda x: x[0])
    by_turn = defaultdict(list)
    for e in events: by_turn[e[0]].append(e)
    owner, garrison = planet.owner, float(planet.ships)
    owner_at, ships_at = {0: owner}, {0: max(0.0, garrison)}
    fall_turn, first_enemy = None, None
    for turn in range(1, horizon + 1):
        if owner != -1: garrison += planet.production
        group = by_turn.get(turn, [])
        if group:
            if owner == player and any(e[1] not in (-1, player) for e in group): first_enemy = first_enemy or turn
            prev_owner = owner
            owner, garrison = resolve_arrival_event(owner, garrison, group)
            if prev_owner == player and owner != player: fall_turn = fall_turn or turn
        owner_at[turn], ships_at[turn] = owner, max(0.0, garrison)
    return {"owner_at": owner_at, "ships_at": ships_at, "fall_turn": fall_turn, "first_enemy": first_enemy, "horizon": horizon}
```

## [MD]
* Strategy

## [CODE]
```python
%%writefile -a submission.py

def plan_moves(world, deadline=None):
    def expired():
        return deadline is not None and time.perf_counter() > deadline

    modes = build_modes(world)
    policy = build_policy_state(world, deadline=deadline)
    planned_commitments = defaultdict(list)
    moves = []
    spent_total = defaultdict(int)

    # Optimization: Use a local cache for intercept calculations within this turn
    intercept_cache = {}

    def get_aim(src_id, target_id, ships):
        key = (src_id, target_id)
        if key not in intercept_cache:
            intercept_cache[key] = world.best_probe_aim(src_id, target_id, ships)
        return intercept_cache[key]

    def source_inventory_left(source_id):
        return world.source_inventory_left(source_id, spent_total)

    def source_attack_left(source_id):
        # Budget check optimized
        return max(0, policy['attack_budget'].get(source_id, 0) - spent_total[source_id])

    def append_move(src_id, angle, ships):
        send = min(int(ships), source_inventory_left(src_id))
        if send < 1: return 0
        moves.append([src_id, float(angle), int(send)])
        spent_total[src_id] += send
        return send

    # Phase 1: High Priority Defense (Rescue/Recapture)
    missions = []
    missions.extend(build_rescue_missions(world, policy, planned_commitments, modes))
    missions.extend(build_recapture_missions(world, policy, planned_commitments, modes))

    # Phase 2: Capture Missions with early-exit pruning
    for src in world.my_planets:
        if expired(): break
        src_avail = source_attack_left(src.id)
        if src_avail < PARTIAL_SOURCE_MIN_SHIPS: continue

        # Filter targets by distance to save CPU on far-flung impossible routes
        sorted_targets = sorted(world.planets, key=lambda t: dist(src.x, src.y, t.x, t.y))

        for target in sorted_targets:
            if target.id == src.id or target.owner == world.player: continue

            seeded = get_aim(src.id, target.id, src_avail)
            if not seeded: continue

            _, rough_aim = seeded
            turns = rough_aim[1]

            # Fast-path time validation
            if turns > world.remaining_steps - LATE_CAPTURE_BUFFER: continue

            needed = world.min_ships_to_own_at(target.id, turns, world.player, planned_commitments)
            if 0 < needed <= src_avail:
                plan = settle_plan(src, target, src_avail, needed, world, planned_commitments, modes, policy)
                if plan:
                    score = target_value(target, plan[1], "capture", world, modes, policy) / (plan[4] + plan[1])
                    missions.append(Mission("capture", score, target.id, plan[1], [ShotOption(score, src.id, target.id, plan[0], plan[1], plan[3], plan[4], "capture")]))

    missions.sort(key=lambda m: m.score, reverse=True)

    for m in missions:
        if expired(): break
        # Standard commitment loop
        opt = m.options[0]
        if source_attack_left(opt.src_id) >= opt.needed:
            sent = append_move(opt.src_id, opt.angle, opt.send_cap)
            if sent >= opt.needed:
                planned_commitments[m.target_id].append((opt.turns, world.player, int(sent)))

    return moves
```

## [MD]
* Entry Point for Agents

## [CODE]
```python
%%writefile -a submission.py

# Agent Entry Point
from typing import Any, Dict, List, Optional, Set, Union

def _read(obs: Union[Dict[str, Any], Any], key: str, default: Any = None) -> Any:
    if isinstance(obs, dict):
        return obs.get(key, default)
    return getattr(obs, key, default)

def build_world(obs: Dict[str, Any]) -> WorldModel:
    player: int = _read(obs, "player", 0)
    step: int = _read(obs, "step", 0) or 0
    raw_planets: List[List[Any]] = _read(obs, "planets", []) or []
    raw_fleets: List[List[Any]] = _read(obs, "fleets", []) or []
    ang_vel: float = _read(obs, "angular_velocity", 0.0) or 0.0
    raw_init: List[List[Any]] = _read(obs, "initial_planets", []) or []
    comets: List[Dict[str, Any]] = _read(obs, "comets", []) or []
    comet_ids: Set[int] = set(_read(obs, "comet_planet_ids", []) or [])

    planets = [Planet(*planet) for planet in raw_planets]
    fleets = [Fleet(*fleet) for fleet in raw_fleets]
    initial_planets = [Planet(*planet) for planet in raw_init]
    initial_by_id = {planet.id: planet for planet in initial_planets}

    return WorldModel(
        player=player,
        step=step,
        planets=planets,
        fleets=fleets,
        initial_by_id=initial_by_id,
        ang_vel=ang_vel,
        comets=comets,
        comet_ids=comet_ids,
    )

def agent(obs: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> List[List[Union[int, float]]]:
    start_time = time.perf_counter()
    world = build_world(obs)
    if not world.my_planets:
        return []
    act_timeout = _read(config, "actTimeout", 1.0) if config is not None else 1.0
    soft_budget = min(SOFT_ACT_DEADLINE, max(0.55, act_timeout * 0.82))
    deadline = start_time + soft_budget
    return plan_moves(world, deadline=deadline)

__all__ = ["agent", "build_world"]
```
