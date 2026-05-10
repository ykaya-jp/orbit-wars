## [MD]
# Orbit Wars — Phase 1 heuristic agent.
 Use this as one of the refernce to get started with this challenge.

## [MD]
#  Strategy (one turn = one call to `agent(obs)`):
  1. Parse observation into structured form.
  2. Identify incoming threats to each of our planets.
  3. Reserve enough ships on each owned planet to survive predicted attacks.
  4. Score every (source, target) candidate move by ROI:
        production gained over remaining turns / (ships spent + travel time)
  5. Greedy-assign: take highest-ROI moves first, deduct from source pools.

## [MD]
# Key tactical features (each in its own helper, see <fn name> in code):
  - fleet_speed:           exact env speed formula (1 ship -> 1.0; 1000 -> 6.0)
  - is_orbiting:           which planets rotate around the sun
  - predict_position:      lead-targeting for orbiting planets
  - predict_comet_position: lead-targeting for comets, returns None if it'll exit
  - path_clears_sun:       reject any direct shot that would clip the sun
  - ships_needed_to_capture: production-during-transit accounting
  - compute_incoming_threats: identify enemy fleets heading at our planets
  - compute_defense_reserve: how many ships to keep home
  - agent / _act:          orchestration

The full agent is wrapped in try/except so a logic bug returns [] instead of
crashing the episode.  Decision-trace stderr lines fire every 50 turns so
ladder logs are diagnosable post-hoc via `kaggle competitions logs <EID> <IDX>`.

## [CODE]
```python
import math
import sys
from typing import List, Tuple, Dict, Optional

# Fall back to local namedtuples if the env import is unavailable on the
# Kaggle submission host.  Constants are pinned to the published spec.
try:
    from kaggle_environments.envs.orbit_wars.orbit_wars import (
        Planet, Fleet, CENTER, BOARD_SIZE, SUN_RADIUS, ROTATION_RADIUS_LIMIT,
    )
except ImportError:
    from collections import namedtuple
    Planet = namedtuple("Planet", ["id", "owner", "x", "y", "radius", "ships", "production"])
    Fleet = namedtuple("Fleet", ["id", "owner", "x", "y", "angle", "from_planet_id", "ships"])
    CENTER = 50.0
    BOARD_SIZE = 100.0
    SUN_RADIUS = 10.0
    ROTATION_RADIUS_LIMIT = 50.0

MAX_SHIP_SPEED = 6.0
LOG_1000 = math.log(1000.0)
EPISODE_STEPS = 500
MIN_FLEET_SIZE = 5            # ~speed 1.5 — slow but lets the home planet (10 ships) expand on turn 0
SUN_MARGIN = 1.0              # extra clearance beyond SUN_RADIUS
COMET_VALUE_BONUS = 1.4       # comets are cheap, +1 prod, time-limited
THREAT_ANGLE_TOL = 0.35       # ~20°: how aligned a fleet must be to "threaten" a planet
```

## [CODE]
```python
# ---------- Helpers ---------------------------------------------------------

def _get(obs, key, default):
    """Read a field from either a dict or a SimpleNamespace-style obs."""
    if isinstance(obs, dict):
        return obs.get(key, default)
    return getattr(obs, key, default)


def fleet_speed(ships: int) -> float:
    """Exact fleet speed formula from the env source."""
    if ships <= 1:
        return 1.0
    s = 1.0 + (MAX_SHIP_SPEED - 1.0) * (math.log(ships) / LOG_1000) ** 1.5
    return min(s, MAX_SHIP_SPEED)


def is_orbiting(p: Planet) -> bool:
    """True if planet rotates around the sun."""
    r = math.hypot(p.x - CENTER, p.y - CENTER)
    return r + p.radius < ROTATION_RADIUS_LIMIT


def predict_position(p: Planet, angular_velocity: float, turns_ahead: int) -> Tuple[float, float]:
    """Position of an orbiting planet after `turns_ahead` turns."""
    if turns_ahead == 0 or not is_orbiting(p):
        return (p.x, p.y)
    dx, dy = p.x - CENTER, p.y - CENTER
    r = math.hypot(dx, dy)
    new_angle = math.atan2(dy, dx) + angular_velocity * turns_ahead
    return (CENTER + r * math.cos(new_angle), CENTER + r * math.sin(new_angle))


def predict_comet_position(comet_pid: int, comets: list, turns_ahead: int) -> Optional[Tuple[float, float]]:
    """Comet position after `turns_ahead` turns; None if it will have left the board."""
    for group in comets:
        pids = group.get("planet_ids", [])
        if comet_pid in pids:
            i = pids.index(comet_pid)
            new_idx = group["path_index"] + turns_ahead
            paths = group["paths"][i]
            if 0 <= new_idx < len(paths):
                return (paths[new_idx][0], paths[new_idx][1])
            return None
    return None




def path_clears_sun(x1: float, y1: float, x2: float, y2: float) -> bool:
    """Does the segment (x1,y1)->(x2,y2) stay outside SUN_RADIUS+SUN_MARGIN?"""
    px, py = x2 - x1, y2 - y1
    norm2 = px * px + py * py
    if norm2 < 1e-9:
        d = math.hypot(x1 - CENTER, y1 - CENTER)
    else:
        t = ((CENTER - x1) * px + (CENTER - y1) * py) / norm2
        t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
        cx, cy = x1 + t * px, y1 + t * py
        d = math.hypot(cx - CENTER, cy - CENTER)
    return d >= SUN_RADIUS + SUN_MARGIN


def lead_target(source: Planet, target: Planet, angular_velocity: float,
                comets: list, fleet_ships: int, is_comet: bool,
                max_iters: int = 4) -> Optional[Tuple[float, int, Tuple[float, float]]]:
    """Compute (angle, eta_turns, predicted_position) to intercept target.

    For static targets this is just straight-line geometry.  For orbiting
    planets and comets we iterate: predict where the target will be at our
    current ETA estimate, recompute angle/ETA, repeat until ETA is stable
    (usually 2-3 iterations).
    """
    speed = fleet_speed(fleet_ships)
    static = (not is_comet) and (not is_orbiting(target))

    tx, ty = target.x, target.y
    eta = max(1, int(math.ceil(math.hypot(tx - source.x, ty - source.y) / speed)))

    if static:
        return (math.atan2(ty - source.y, tx - source.x), eta, (tx, ty))

    future = (tx, ty)
    for _ in range(max_iters):
        if is_comet:
            future = predict_comet_position(target.id, comets, eta)
            if future is None:
                return None
        else:
            future = predict_position(target, angular_velocity, eta)
        new_eta = max(1, int(math.ceil(
            math.hypot(future[0] - source.x, future[1] - source.y) / speed
        )))
        if new_eta == eta:
            break
        eta = new_eta

    if eta > EPISODE_STEPS:
        return None
    return (math.atan2(future[1] - source.y, future[0] - source.x), eta, future)


def ships_needed_to_capture(target: Planet, eta: int, my_player: int) -> int:
    """Minimum fleet size to flip `target` arriving in `eta` turns.

    Combat rule (from env): planet flips when surviving_attackers > planet.ships.
    Production happens once per turn before fleet movement, so an enemy planet
    will have grown by production * eta ships by arrival time.  Neutrals don't
    produce.  Sending to a friendly planet is a reinforcement (no minimum).
    """
    if target.owner == my_player:
        return 0
    if target.owner == -1:
        future_garrison = target.ships
    else:
        future_garrison = target.ships + target.production * eta
    return future_garrison + 1


def compute_incoming_threats(my_planets: List[Planet], fleets: List[Fleet],
                             my_player: int) -> Dict[int, List[Tuple[int, int, int]]]:
    """For each owned planet, list incoming enemy fleets as (eta, ships, owner).

    A fleet "threatens" a planet if its heading is roughly aimed at it
    (within THREAT_ANGLE_TOL).  This is approximate but cheap; Phase 2 will
    do exact path-intersection checks via simulation.
    """
    threats = {p.id: [] for p in my_planets}
    for f in fleets:
        if f.owner == my_player:
            continue
        speed = fleet_speed(f.ships)
        for mp in my_planets:
            d = math.hypot(mp.x - f.x, mp.y - f.y)
            if d < 1e-6:
                continue
            target_angle = math.atan2(mp.y - f.y, mp.x - f.x)
            diff = abs(((f.angle - target_angle + math.pi) % (2 * math.pi)) - math.pi)
            if diff < THREAT_ANGLE_TOL:
                eta = max(1, int(math.ceil(d / speed)))
                threats[mp.id].append((eta, int(f.ships), int(f.owner)))
    for pid in threats:
        threats[pid].sort()
    return threats


def compute_defense_reserve(planet: Planet,
                            threats: List[Tuple[int, int, int]]) -> int:
    """Ships to keep home so this planet survives all incoming threats."""
    if not threats:
        return 0
    garrison = planet.ships
    last_t = 0
    deficit = 0
    for (eta, ships, _owner) in threats:
        garrison += planet.production * (eta - last_t)
        garrison -= ships
        if garrison < 0:
            deficit = max(deficit, -garrison + 1)
            garrison = 0
        last_t = eta
    return deficit
```

## [CODE]
```python
# ---------- Agent ----------------------------------------------------------

def agent(obs):
    """Phase-1 heuristic agent.  Wrapped to never crash the episode."""
    try:
        return _act(obs)
    except Exception as e:
        sys.stderr.write(f"[agent ERROR] {type(e).__name__}: {e}\n")
        return []


def _act(obs):
    player = _get(obs, "player", 0)
    raw_planets = _get(obs, "planets", [])
    raw_fleets = _get(obs, "fleets", [])
    angular_velocity = _get(obs, "angular_velocity", 0.0)
    comets = _get(obs, "comets", [])
    comet_pids = set(_get(obs, "comet_planet_ids", []))
    step = _get(obs, "step", 0)

    planets = [Planet(*p) for p in raw_planets]
    fleets = [Fleet(*f) for f in raw_fleets]

    my_planets = [p for p in planets if p.owner == player]
    if not my_planets:
        return []
    targets = [p for p in planets if p.owner != player]
    if not targets:
        return []

    # 1. Defense first: how many ships are committed to staying home?
    threats = compute_incoming_threats(my_planets, fleets, player)
    available: Dict[int, int] = {}
    for mp in my_planets:
        reserve = compute_defense_reserve(mp, threats[mp.id])
        available[mp.id] = max(0, mp.ships - reserve)

    # 2. Build candidate moves: (score, source_id, target_id, angle, ships).
    sources_by_id = {p.id: p for p in my_planets}
    candidates = []
    for target in targets:
        is_comet = target.id in comet_pids
        comet_mult = COMET_VALUE_BONUS if is_comet else 1.0
        for source in my_planets:
            pool = available[source.id]
            if pool < MIN_FLEET_SIZE:
                continue

            # Pre-estimate ETA using full available pool's speed (refined below).
            est_speed = fleet_speed(min(pool, 100))
            est_dist = math.hypot(target.x - source.x, target.y - source.y)
            est_eta = max(1, int(math.ceil(est_dist / est_speed)))
            est_ships = max(MIN_FLEET_SIZE,
                            ships_needed_to_capture(target, est_eta, player))
            if est_ships > pool:
                continue

            lead = lead_target(source, target, angular_velocity, comets,
                               est_ships, is_comet)
            if lead is None:
                continue
            angle, eta, future = lead

            # Sun-avoidance: launch point is just outside the source planet.
            sx = source.x + math.cos(angle) * (source.radius + 0.1)
            sy = source.y + math.sin(angle) * (source.radius + 0.1)
            if not path_clears_sun(sx, sy, future[0], future[1]):
                continue

            # Refine ship count with the now-known ETA.
            ships = max(MIN_FLEET_SIZE,
                        ships_needed_to_capture(target, eta, player))
            if ships > pool:
                continue

            # Score: production gained over the rest of the game per ship spent.
            remaining = max(1, EPISODE_STEPS - step - eta)
            value = target.production * remaining * comet_mult
            cost = ships + 0.5 * eta
            score = value / cost
            # Mild bonus for taking neutrals over enemies (less likely to be defended).
            if target.owner == -1:
                score *= 1.15

            candidates.append((score, source.id, target.id, angle, ships))

    # 3. Greedy assignment.  Two passes:
    #    Pass 1: each target gets at most one source (same as before, takes the
    #            highest-ROI moves first, builds breadth).
    #    Pass 2: re-allow targets to get a second source IF their first allocation
    #            wasn't enough to overpower a likely tied-attacker (the +SAFETY
    #            term).  This lets two of our planets coordinate on tough targets
    #            and is the single biggest win against equally-strong opponents.
    #
    # Symmetry break: in self-play and on the ladder, two identical agents must
    # not pick exactly equal-ranked candidates the same way or fleets cancel out
    # in head-on combat (env rule: ties annihilate both attackers, see
    # orbit_wars.py line ~636).  We add a tiny per-player tiebreaker derived from
    # hash((player, target.id)) — keeps decisions deterministic per player but
    # divergent across players.

    def jitter(tid: int) -> float:
        # Stable, signed value in roughly [-0.5, 0.5], tied to (player, target).
        h = hash((player, tid)) & 0xFFFF
        return (h / 0xFFFF) - 0.5

    # Apply jitter — small enough to only break ties, not reorder real differences.
    candidates = [(s + 1e-3 * jitter(tid), sid, tid, ang, sh)
                  for (s, sid, tid, ang, sh) in candidates]
    candidates.sort(key=lambda c: -c[0])

    SAFETY_MARGIN = 1.20  # if our first fleet doesn't exceed garrison*1.2, allow a 2nd source
    moves = []
    target_committed: Dict[int, int] = {}   # tid -> total ships committed
    target_required: Dict[int, int] = {}    # tid -> ships needed for safe capture

    for score, sid, tid, angle, ships in candidates:
        if available[sid] < ships:
            continue
        # Skip if this target is already safely overpowered.
        committed = target_committed.get(tid, 0)
        if tid in target_required and committed >= target_required[tid]:
            continue
        # First commitment to this target: record its required-with-margin total.
        if tid not in target_required:
            # ships passed in is the bare-minimum capture cost, scale up for safety
            target_required[tid] = int(ships * SAFETY_MARGIN)
        moves.append([sid, float(angle), int(ships)])
        available[sid] -= ships
        target_committed[tid] = committed + ships

    # Periodic decision-trace for ladder log analysis.
    if step % 50 == 0:
        my_total = sum(p.ships for p in my_planets) + \
                   sum(f.ships for f in fleets if f.owner == player)
        sys.stderr.write(
            f"[t={step}] p={player} planets={len(my_planets)} "
            f"ships={my_total} moves={len(moves)} "
            f"targets={len(target_required)}/{len(targets)}\n"
        )

    return moves
```
