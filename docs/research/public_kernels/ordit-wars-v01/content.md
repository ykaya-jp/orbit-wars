## [CODE]
```python
!pip install -q "kaggle-environments>=1.28.0"
```

## [CODE]
```python
import kaggle_environments
print("kaggle-environments version:", kaggle_environments.version)

# Confirm orbit_wars module is available
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet, Fleet, CENTER, ROTATION_RADIUS_LIMIT
print("CENTER:", CENTER)
print("ROTATION_RADIUS_LIMIT:", ROTATION_RADIUS_LIMIT)
```

## [CODE]
```python
%%writefile main.py
"""
Orbit Wars Agent v2
Improvements over v1:
- Per-planet ETA-based combat simulation (knows who arrives when)
- Global target allocation (best fleet/target pairs first)
- Coordinated multi-source attacks
- Profitability check (only attack if production payoff beats ship cost)
- Tighter ship sizing (no over-commit)
- Smarter defense reservation
"""
import math
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet, Fleet, ROTATION_RADIUS_LIMIT

SUN_X, SUN_Y = 50.0, 50.0
SUN_RADIUS = 10.0
SAFETY = 1.5
MAX_SPEED = 6.0
GAME_LEN = 500


# -------- Geometry --------
def _d(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def fleet_speed(ships):
    if ships <= 1:
        return 1.0
    return 1.0 + (MAX_SPEED - 1.0) * (math.log(ships) / math.log(1000)) ** 1.5


def line_hits_sun(x1, y1, x2, y2, r=SUN_RADIUS + SAFETY):
    dx, dy = x2 - x1, y2 - y1
    fx, fy = x1 - SUN_X, y1 - SUN_Y
    a = dx * dx + dy * dy
    if a == 0:
        return _d(x1, y1, SUN_X, SUN_Y) < r
    b = 2 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - r * r
    disc = b * b - 4 * a * c
    if disc < 0:
        return False
    sd = math.sqrt(disc)
    t1, t2 = (-b - sd) / (2 * a), (-b + sd) / (2 * a)
    return (0 <= t1 <= 1) or (0 <= t2 <= 1)


def safe_angle(fx, fy, tx, ty):
    direct = math.atan2(ty - fy, tx - fx)
    if not line_hits_sun(fx, fy, tx, ty):
        return direct
    d = _d(fx, fy, tx, ty)
    for off in (15, -15, 30, -30, 45, -45, 60, -60, 90, -90):
        a = direct + math.radians(off)
        wx, wy = fx + math.cos(a) * d, fy + math.sin(a) * d
        if not line_hits_sun(fx, fy, wx, wy):
            return a
    return direct


# -------- Orbital Prediction --------
def predict_pos(planet, init_map, ang_vel, turns):
    init = init_map.get(planet.id)
    if init is None:
        return planet.x, planet.y
    orbit_r = _d(init[2], init[3], SUN_X, SUN_Y)
    if orbit_r + planet.radius >= ROTATION_RADIUS_LIMIT:
        return planet.x, planet.y
    cur = math.atan2(planet.y - SUN_Y, planet.x - SUN_X)
    fut = cur + ang_vel * turns
    return SUN_X + orbit_r * math.cos(fut), SUN_Y + orbit_r * math.sin(fut)


def travel_turns(src, tgt, init_map, ang_vel, ships):
    """Iteratively converge on actual ETA accounting for orbital motion."""
    spd = fleet_speed(ships)
    tx, ty = tgt.x, tgt.y
    turns = 1
    for _ in range(5):
        d = _d(src.x, src.y, tx, ty)
        turns = max(1, int(math.ceil(d / max(spd, 0.1))))
        tx, ty = predict_pos(tgt, init_map, ang_vel, turns)
    return turns, tx, ty


# -------- Per-Planet ETA Simulation --------
def fleet_eta_to_planet(fleet, planet, init_map, ang_vel):
    """Estimate which turn the fleet hits the planet (or None if it doesn't)."""
    spd = fleet_speed(fleet.ships)
    # Quick check: is the fleet flying roughly toward this planet?
    fx, fy = fleet.x, fleet.y
    bearing = math.atan2(planet.y - fy, planet.x - fx)
    diff = abs((fleet.angle - bearing + math.pi) % (2 * math.pi) - math.pi)
    if diff > 0.45:  # ~25 degrees off — not headed here
        return None
    d = _d(fx, fy, planet.x, planet.y)
    turns = int(round(d / max(spd, 0.1)))
    if turns < 0 or turns > 200:
        return None
    # Verify: project fleet forward, check intersection with predicted planet
    proj_x = fx + math.cos(fleet.angle) * spd * turns
    proj_y = fy + math.sin(fleet.angle) * spd * turns
    px, py = predict_pos(planet, init_map, ang_vel, turns)
    if _d(proj_x, proj_y, px, py) < planet.radius + 2.5:
        return turns
    return None


def simulate_planet(planet, fleets, player, init_map, ang_vel, horizon=120):
    """
    Simulate the planet's owner & garrison turn by turn.
    Returns list of (turn, owner, ships) up to horizon, plus final state.
    """
    # Build event list: turn -> list of (owner, ships) arrivals
    events = {}
    for f in fleets:
        eta = fleet_eta_to_planet(f, planet, init_map, ang_vel)
        if eta is not None and 0 <= eta <= horizon:
            events.setdefault(eta, []).append((f.owner, f.ships))

    owner = planet.owner
    ships = planet.ships
    prod = planet.production
    timeline = []  # (turn, owner, ships)

    for t in range(horizon + 1):
        # Production
        if owner != -1 and t > 0:
            ships += prod
        # Combat at this turn
        if t in events:
            arrivals = events[t]
            by_owner = {}
            for o, s in arrivals:
                by_owner[o] = by_owner.get(o, 0) + s
            # Add garrison as defender
            by_owner[owner] = by_owner.get(owner, 0) + ships
            # Largest vs second-largest
            sorted_forces = sorted(by_owner.items(), key=lambda x: -x[1])
            if len(sorted_forces) >= 2 and sorted_forces[0][1] == sorted_forces[1][1]:
                # Tie - everyone dies
                owner = -1
                ships = 0
            else:
                winner_o, winner_s = sorted_forces[0]
                runner_s = sorted_forces[1][1] if len(sorted_forces) >= 2 else 0
                owner = winner_o
                ships = winner_s - runner_s
        timeline.append((t, owner, ships))
    return timeline


def required_to_capture(planet, fleets, player, init_map, ang_vel, arrival_turn):
    """How many ships do we need to send arriving at `arrival_turn` to flip ownership?"""
    timeline = simulate_planet(planet, fleets, player, init_map, ang_vel,
                               horizon=arrival_turn)
    if arrival_turn >= len(timeline):
        return planet.ships + 1
    _, owner_at, ships_at = timeline[arrival_turn - 1] if arrival_turn > 0 else (0, planet.owner, planet.ships)
    # We need to beat the garrison at arrival turn (after their production)
    # Account for one turn of their production happening at arrival_turn
    if owner_at == player:
        return 0  # already ours by then
    needed = ships_at + (planet.production if owner_at != -1 else 0) + 1
    return max(1, needed)


# -------- Threat Detection --------
def planet_threat(planet, fleets, player, init_map, ang_vel):
    """Net hostile ships arriving in next ~30 turns."""
    timeline = simulate_planet(planet, fleets, player, init_map, ang_vel, horizon=30)
    # Find the worst (lowest) ship count while we're owner
    min_ships = planet.ships
    lost = False
    for _, o, s in timeline:
        if o != player:
            lost = True
            break
        min_ships = min(min_ships, s)
    if lost:
        return planet.ships + 50  # need significant reinforcement
    return max(0, planet.ships - min_ships)


# -------- Target Scoring --------
def target_score(target, source, comet_ids, step, ships_needed, eta):
    """Higher = better attack. ROI = future production gained per ship spent."""
    if ships_needed <= 0:
        return -1e9
    turns_left = max(1, GAME_LEN - step - eta)
    if target.id in comet_ids:
        # Comets: bounded life remaining
        comet_life = max(20, min(100, GAME_LEN - step))
        future_prod = target.production * min(turns_left, comet_life)
    else:
        future_prod = target.production * turns_left
    # If currently enemy-owned, we also deny them production = double benefit
    if target.owner not in (-1, source.owner):
        future_prod *= 1.5
    roi = future_prod / (ships_needed + eta * 0.5 + 1)
    return roi


# -------- Agent --------
def agent(obs):
    try:
        return _impl(obs)
    except Exception as e:
        print(f"[agent error] {e}")
        return []


def _impl(obs):
    g = (lambda k, d=None: obs.get(k, d)) if isinstance(obs, dict) else (lambda k, d=None: getattr(obs, k, d))
    player = g("player", 0)
    raw_planets = g("planets", []) or []
    raw_fleets = g("fleets", []) or []
    ang_vel = g("angular_velocity", 0.03) or 0.03
    init_planets = g("initial_planets", []) or []
    comet_ids = set(g("comet_planet_ids", []) or [])
    step = g("step", 0) or 0

    planets = [Planet(*p) for p in raw_planets]
    fleets = [Fleet(*f) for f in raw_fleets]
    init_map = {ip[0]: ip for ip in init_planets}

    my_planets = [p for p in planets if p.owner == player]
    targets = [p for p in planets if p.owner != player]
    if not my_planets or not targets:
        return []

    available = {p.id: int(p.ships) for p in my_planets}

    # ---- DEFENSE: reserve ships for threatened planets ----
    for mp in my_planets:
        threat = planet_threat(mp, fleets, player, init_map, ang_vel)
        reserve = min(available[mp.id], threat)
        available[mp.id] -= reserve

    # ---- OFFENSE: build (source, target, eta, needed, score) candidates ----
    candidates = []
    for src in my_planets:
        for tgt in targets:
            eta, tx, ty = travel_turns(src, tgt, init_map, ang_vel, max(2, available[src.id] // 4))
            needed = required_to_capture(tgt, fleets, player, init_map, ang_vel, eta)
            if needed <= 0 or needed > 800:
                continue
            score = target_score(tgt, src, comet_ids, step, needed, eta)
            candidates.append((score, src, tgt, eta, needed, tx, ty))

    # Sort globally by ROI — best deals first
    candidates.sort(key=lambda x: -x[0])

    moves = []
    used_target_quota = {}  # target_id -> total ships already committed
    for score, src, tgt, eta, needed, tx, ty in candidates:
        if score <= 0:
            break
        avail = available[src.id]
        if avail < 2:
            continue
        already = used_target_quota.get(tgt.id, 0)
        still_needed = max(0, needed - already)
        if still_needed <= 0:
            continue
        # How much can/should we send from this source?
        keep = max(1, src.ships // 6)  # small home reserve
        max_send = max(0, avail - keep)
        if max_send < 2:
            continue
        send = min(max_send, still_needed)
        if send < 2:
            continue
        # Recompute angle with actual send size for accurate intercept
        eta2, tx2, ty2 = travel_turns(src, tgt, init_map, ang_vel, send)
        angle = safe_angle(src.x, src.y, tx2, ty2)
        moves.append([src.id, angle, int(send)])
        available[src.id] -= send
        used_target_quota[tgt.id] = already + send

    return moves
```

## [CODE]
```python
# Confirm the file was written and imports cleanly
import importlib.util
spec = importlib.util.spec_from_file_location("main", "main.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print("Agent function loaded:", m.agent)
print("Returns empty list on empty obs:", m.agent({}))
```

## [CODE]
```python
# Self-play check (mimics Kaggle validation)
from kaggle_environments import make
env = make("orbit_wars", configuration={"seed": 42}, debug=True)
env.run(["main.py", "main.py"])
print("Self-play OK:", [(s.reward, s.status) for s in env.steps[-1]])
```

## [CODE]
```python
%%writefile baseline.py

"""
Orbit Wars - Heuristic Agent
Strategy: sun-aware routing, orbital intercept, threat-based defense, value-based offense.
"""

import math
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet, Fleet, ROTATION_RADIUS_LIMIT

# ---- Constants ----
SUN_X, SUN_Y = 50.0, 50.0
SUN_RADIUS = 10.0
SAFETY_MARGIN = 1.5
MAX_SHIP_SPEED = 6.0


# ---- Geometry ----
def _dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def fleet_speed(ships):
    if ships <= 1:
        return 1.0
    return 1.0 + (MAX_SHIP_SPEED - 1.0) * (math.log(ships) / math.log(1000)) ** 1.5


def line_hits_sun(x1, y1, x2, y2, r=SUN_RADIUS + SAFETY_MARGIN):
    dx, dy = x2 - x1, y2 - y1
    fx, fy = x1 - SUN_X, y1 - SUN_Y
    a = dx * dx + dy * dy
    if a == 0:
        return _dist(x1, y1, SUN_X, SUN_Y) < r
    b = 2 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - r * r
    disc = b * b - 4 * a * c
    if disc < 0:
        return False
    disc = math.sqrt(disc)
    t1 = (-b - disc) / (2 * a)
    t2 = (-b + disc) / (2 * a)
    return (0 <= t1 <= 1) or (0 <= t2 <= 1)


def safe_angle_to(fx, fy, tx, ty):
    direct = math.atan2(ty - fy, tx - fx)
    if not line_hits_sun(fx, fy, tx, ty):
        return direct
    d = _dist(fx, fy, tx, ty)
    for off_deg in (15, -15, 30, -30, 45, -45, 60, -60, 90, -90):
        ang = direct + math.radians(off_deg)
        wx = fx + math.cos(ang) * d
        wy = fy + math.sin(ang) * d
        if not line_hits_sun(fx, fy, wx, wy):
            return ang
    return direct


# ---- Orbital Prediction ----
def predict_planet_position(planet, init_map, ang_vel, turns):
    init = init_map.get(planet.id)
    if init is None:
        return planet.x, planet.y
    init_x, init_y = init[2], init[3]
    orbit_r = _dist(init_x, init_y, SUN_X, SUN_Y)
    if orbit_r + planet.radius >= ROTATION_RADIUS_LIMIT:
        return planet.x, planet.y
    cur_ang = math.atan2(planet.y - SUN_Y, planet.x - SUN_X)
    fut_ang = cur_ang + ang_vel * turns
    return SUN_X + orbit_r * math.cos(fut_ang), SUN_Y + orbit_r * math.sin(fut_ang)


def iterative_intercept(src, tgt, init_map, ang_vel, ships):
    tx, ty = tgt.x, tgt.y
    spd = fleet_speed(ships)
    for _ in range(4):
        d = _dist(src.x, src.y, tx, ty)
        turns = max(1, int(math.ceil(d / max(spd, 0.1))))
        tx, ty = predict_planet_position(tgt, init_map, ang_vel, turns)
    return tx, ty


# ---- Threat Analysis ----
def incoming_threat(planet, fleets, player, init_map, ang_vel):
    threat = 0
    reinforce = 0
    for f in fleets:
        d = _dist(f.x, f.y, planet.x, planet.y)
        spd = fleet_speed(f.ships)
        turns = d / max(spd, 0.1)
        proj_x = f.x + math.cos(f.angle) * spd * turns
        proj_y = f.y + math.sin(f.angle) * spd * turns
        px, py = predict_planet_position(planet, init_map, ang_vel, int(turns))
        if _dist(proj_x, proj_y, px, py) < planet.radius + 2.0:
            if f.owner == player:
                reinforce += f.ships
            else:
                threat += f.ships
    return threat, reinforce


# ---- Valuation ----
def planet_value(planet, src, comet_ids, step):
    d = _dist(src.x, src.y, planet.x, planet.y)
    if planet.id in comet_ids:
        remaining = max(50, 500 - step)
        base = planet.production * min(40.0, remaining * 0.3)
    else:
        base = planet.production * 50.0
    cost = planet.ships + 1
    return base / (cost + d * 0.5 + 1)


# ---- Agent Entry Point ----
def agent(obs):
    try:
        return _agent_impl(obs)
    except Exception as e:
        print(f"[agent error] {e}")
        return []


def _agent_impl(obs):
    moves = []
    g = (lambda k, d=None: obs.get(k, d)) if isinstance(obs, dict) else (lambda k, d=None: getattr(obs, k, d))

    player = g("player", 0)
    raw_planets = g("planets", []) or []
    raw_fleets = g("fleets", []) or []
    ang_vel = g("angular_velocity", 0.03) or 0.03
    init_planets = g("initial_planets", []) or []
    comet_ids = set(g("comet_planet_ids", []) or [])
    step = g("step", 0) or 0

    planets = [Planet(*p) for p in raw_planets]
    fleets = [Fleet(*f) for f in raw_fleets]
    init_map = {ip[0]: ip for ip in init_planets}

    my_planets = [p for p in planets if p.owner == player]
    targets = [p for p in planets if p.owner != player]
    if not my_planets or not targets:
        return moves

    available = {p.id: int(p.ships) for p in my_planets}

    # Defense: reserve ships against incoming threats
    for mp in my_planets:
        threat, reinforce = incoming_threat(mp, fleets, player, init_map, ang_vel)
        net = max(0, threat - reinforce)
        reserve = min(available[mp.id], net)
        available[mp.id] -= reserve

    # Offense: attack high-value targets
    for mp in sorted(my_planets, key=lambda p: -available[p.id]):
        if available[mp.id] < 2:
            continue

        scored = []
        for t in targets:
            already = sum(f.ships for f in fleets
                          if f.owner == player and _dist(f.x, f.y, t.x, t.y) < 30)
            eff_garrison = max(0, t.ships - already) if t.owner != player else t.ships
            v = planet_value(t, mp, comet_ids, step)
            scored.append((v, t, eff_garrison))
        scored.sort(key=lambda x: -x[0])

        for _, target, eff_garrison in scored[:3]:
            need = eff_garrison + 2
            keep = max(2, mp.ships // 5)
            max_send = max(1, available[mp.id] - keep)
            send = min(max_send, max(need, available[mp.id] // 2))
            if send < 2 or send > available[mp.id]:
                continue

            tx, ty = iterative_intercept(mp, target, init_map, ang_vel, send)
            angle = safe_angle_to(mp.x, mp.y, tx, ty)
            moves.append([mp.id, angle, int(send)])
            available[mp.id] -= send
            if available[mp.id] < 2:
                break

    return moves
```

## [CODE]
```python
# Then in next cell:
from kaggle_environments import make
wins = 0
N = 10
for seed in range(N):
    env = make("orbit_wars", configuration={"seed": seed}, debug=False)
    env.run(["main.py", "baseline.py"])
    final = env.steps[-1]
    r0 = final[0].reward or 0
    r1 = final[1].reward or 0
    if r0 > r1: wins += 1
    print(f"Seed {seed}: v2={r0} vs v1={r1} -> {'WIN' if r0>r1 else 'LOSS' if r0<r1 else 'TIE'}")
print(f"\nv2 win rate vs v1: {wins}/{N}")
```

## [CODE]
```python
from kaggle_environments import make
wins = 0
N = 5
for seed in range(N):
    env = make("orbit_wars", configuration={"seed": seed}, debug=False)
    env.run(["main.py", "random"])
    r0 = env.steps[-1][0].reward or 0
    r1 = env.steps[-1][1].reward or 0
    if r0 > r1: wins += 1
print(f"v2 vs random: {wins}/{N}")
```

## [CODE]
```python

```
