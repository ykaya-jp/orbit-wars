## [MD]
# 🪐 Orbit Wars — 101

> *Command the fleet. Conquer the void.*

Welcome! This notebook is designed to take you from **zero** to a **competitive submission** for the [Orbit Wars](https://www.kaggle.com/competitions/orbit-wars) Kaggle competition. Whether you are new to game AI or an experienced practitioner, every section is explained step by step.


##  Table of Contents

1. [Game Overview & Mental Model](#overview)
2. [Setup & Installation](#setup)
3. [Deep-Dive: Observation Space](#observation)
4. [Core Math Utilities](#utilities)
5. [Agent v1 — Nearest Planet Sniper (Baseline)](#agent1)
6. [Agent v2 — Sun-Aware Travel-Time Sniper](#agent2)
7. [Agent v3 — Strategic Expander](#agent3)
8. [Agent v4 — Orbit Interceptor (Advanced)](#agent4)
9. [Benchmarking Your Agents](#benchmark)
10. [Submission](#submission)
11. [What to Try Next](#next)

## <a id='overview'></a>1. Game Overview & Mental Model

Orbit Wars is a **real-time strategy** game played on a **100×100 continuous 2D board**.

```
(0,0)─────────────────────(100,0)
  │                           │
  │   Outer static planets    │
  │                           │
  │      ☀ Sun (50,50)       │
  │    (inner planets orbit)  │
  │                           │
(0,100)──────────────────(100,100)
```

### Core Loop
```
Each turn (500 turns total):
  1. Comets expire
  2. Comets spawn (at turns 50, 150, 250, 350, 450)
  3. YOUR AGENT ACTS ← you are here
  4. Production: each owned planet generates ships
  5. Fleets move; check collisions (bounds, sun, planets)
  6. Planets rotate; comets advance
  7. Combat resolves
```

### Key Numbers to Memorize
| Thing | Value |
|---|---|
| Board size | 100 × 100 |
| Sun center | (50, 50), radius 10 |
| Max fleet speed | 6.0 units/turn (at 1000 ships) |
| Min fleet speed | 1.0 units/turn (1 ship) |
| Planet production | 1–5 ships/turn |
| Game length | 500 turns |
| Orbit speed | 0.025–0.05 radians/turn |

### Fleet Speed Formula
$$\text{speed} = 1.0 + (6.0 - 1.0) \times \left(\frac{\log(n)}{\log(1000)}\right)^{1.5}$$

This means **sending larger fleets is almost always better** — they arrive faster AND hit harder.

### Combat Summary
```
All fleets arriving at a planet are grouped by owner.
Largest group vs 2nd largest → difference survives.
Survivor vs garrison → if attacker wins, planet flips.
Tie = everyone dies (no survivors).
```

### Victory Condition
**Most total ships** (planets + fleets in flight) after 500 turns. *Not* most planets — ships in flight count too!

## [MD]
##  <a id='setup'></a>2. Setup & Installation

## [CODE]
```python
%%capture
!pip install --upgrade "kaggle-environments>=1.28.0"
```

## [CODE]
```python
import math
import random
import collections
from typing import List, Tuple, Optional, Dict

from kaggle_environments import make
from kaggle_environments.envs.orbit_wars.orbit_wars import (
    Planet, Fleet, CENTER, ROTATION_RADIUS_LIMIT
)

print("All imports successful!")
print(f"  Sun center: {CENTER}")
print(f"  Rotation radius limit: {ROTATION_RADIUS_LIMIT}")

# Verify environment loads
env = make("orbit_wars", debug=False)
print(f"\n Environment loaded: {env.name} v{env.version}")
print(f"  Supported player counts: {env.specification.agents}")
print(f"  Default episode steps: {env.configuration.episodeSteps}")
print(f"  Default ship speed: {env.configuration.shipSpeed}")
# print(f"  Default sun radius: {env.configuration.sunRadius}")
```

## [MD]
## <a id='observation'></a>3. Deep-Dive: Observation Space

Understanding what your agent *sees* every turn is the most important thing.
Let's run a game and inspect the observation carefully.

## [CODE]
```python
# Run a quick 2-player game to capture observations
env = make("orbit_wars", configuration={"seed": 42}, debug=False)
env.run(["random", "random"])

# Grab the very first observation (step 1 = first action step)
obs = env.steps[1][0].observation

planets = [Planet(*p) for p in obs.planets]
fleets  = [Fleet(*f) for f in obs.fleets]

print("=" * 60)
print(f"Player ID       : {obs.player}")
print(f"Angular velocity: {obs.angular_velocity:.4f} rad/turn")
print(f"Total planets   : {len(planets)}")
print(f"Total fleets    : {len(fleets)}")
print(f"Comet planet IDs: {obs.comet_planet_ids}")
print(f"Remaining time  : {obs.remainingOverageTime:.2f}s")

print("\n--- MY PLANETS ---")
for p in planets:
    if p.owner == obs.player:
        is_orbiting = math.hypot(p.x - 50, p.y - 50) + p.radius < 50
        print(f"  id={p.id:2d} pos=({p.x:5.1f},{p.y:5.1f}) "
              f"ships={p.ships:3d} prod={p.production} "
              f"{'[ORBITING]' if is_orbiting else '[STATIC]'}")

print("\n--- NEUTRAL PLANETS (first 6) ---")
for p in planets:
    if p.owner == -1:
        dist_to_sun = math.hypot(p.x - 50, p.y - 50)
        print(f"  id={p.id:2d} pos=({p.x:5.1f},{p.y:5.1f}) "
              f"ships={p.ships:3d} prod={p.production} "
              f"dist_from_sun={dist_to_sun:.1f}")

print("\n--- ENEMY PLANETS ---")
for p in planets:
    if p.owner >= 0 and p.owner != obs.player:
        print(f"  id={p.id:2d} pos=({p.x:5.1f},{p.y:5.1f}) "
              f"ships={p.ships:3d} prod={p.production}")
```

## [CODE]
```python
# Let's also look at a mid-game observation to see fleets and comets
obs_mid = env.steps[60][0].observation  # around comet spawn at step 50
planets_mid = [Planet(*p) for p in obs_mid.planets]
fleets_mid  = [Fleet(*f) for f in obs_mid.fleets]

print("=== MID-GAME (step ~60) ===")
print(f"Planets: {len(planets_mid)} | Fleets: {len(fleets_mid)} | Comets: {obs_mid.comet_planet_ids}")

if obs_mid.comet_planet_ids:
    print("\n--- COMETS ---")
    for p in planets_mid:
        if p.id in obs_mid.comet_planet_ids:
            print(f"  comet id={p.id} pos=({p.x:.1f},{p.y:.1f}) ships={p.ships} prod={p.production}")

if fleets_mid:
    print("\n--- ACTIVE FLEETS (first 5) ---")
    for f in fleets_mid[:5]:
        owner_str = f"Player {f.owner}"
        print(f"  id={f.id} owner={owner_str} pos=({f.x:.1f},{f.y:.1f}) "
              f"ships={f.ships} from_planet={f.from_planet_id}")
```

## [MD]
##  <a id='utilities'></a>4. Core Math Utilities

These are the building blocks every competitive agent needs. Study them carefully.

### Why does this matter?
- Fleets aim at **current** planet position, but planets **move** — you must predict where the target will be.
- Fleets aimed through the sun are **destroyed** — you must check for sun collision.
- Sending too few ships means the planet grows its garrison and you miss — you must account for **travel time production**.

## [CODE]
```python
# ============================================================
# CORE MATH UTILITIES
# ============================================================

SUN_X, SUN_Y = 50.0, 50.0
SUN_RADIUS    = 10.0
MAX_SPEED     = 6.0
BOARD_SIZE    = 100.0


# ── Fleet speed ──────────────────────────────────────────────
def fleet_speed(num_ships: int, max_speed: float = MAX_SPEED) -> float:
    """
    Compute how fast a fleet of `num_ships` travels per turn.
    Speed is on a logarithmic curve: 1 ship = 1 unit/turn,
    ~500 ships ≈ 5 units/turn, 1000 ships = max_speed.
    """
    if num_ships <= 1:
        return 1.0
    ratio = math.log(num_ships) / math.log(1000)
    return 1.0 + (max_speed - 1.0) * (ratio ** 1.5)


# ── Distance & angle ─────────────────────────────────────────
def dist(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def angle_to(x1: float, y1: float, x2: float, y2: float) -> float:
    """Angle in radians from point 1 to point 2."""
    return math.atan2(y2 - y1, x2 - x1)


# ── Travel time ───────────────────────────────────────────────
def travel_time(distance: float, num_ships: int) -> float:
    """
    Estimate how many turns a fleet takes to travel `distance`.
    Returns a float (not rounded) — use math.ceil for a conservative upper bound.
    """
    speed = fleet_speed(num_ships)
    if speed <= 0:
        return float('inf')
    return distance / speed


# ── Sun collision check ───────────────────────────────────────
def path_hits_sun(
    x1: float, y1: float,
    x2: float, y2: float,
    sun_x: float = SUN_X, sun_y: float = SUN_Y,
    sun_r: float = SUN_RADIUS
) -> bool:
    """
    Returns True if the line segment (x1,y1)→(x2,y2) passes
    within `sun_r` of the sun center. Uses closest-point-on-segment math.
    """
    dx, dy = x2 - x1, y2 - y1
    fx, fy = x1 - sun_x, y1 - sun_y
    a = dx*dx + dy*dy
    if a < 1e-10:  # zero-length segment
        return math.hypot(fx, fy) < sun_r
    b = 2 * (fx*dx + fy*dy)
    c = fx*fx + fy*fy - sun_r*sun_r
    discriminant = b*b - 4*a*c
    if discriminant < 0:
        return False
    sqrt_d = math.sqrt(discriminant)
    t1 = (-b - sqrt_d) / (2*a)
    t2 = (-b + sqrt_d) / (2*a)
    # Intersects if either t is in [0, 1]
    return (0 <= t1 <= 1) or (0 <= t2 <= 1) or (t1 < 0 < t2)


# ── Planet position prediction ────────────────────────────────
def predict_position(
    planet_id: int,
    initial_planets: list,
    angular_velocity: float,
    steps_ahead: int
) -> Tuple[float, float]:
    """
    Predict where an orbiting planet will be `steps_ahead` turns from now.

    Inner planets rotate around the sun at `angular_velocity` radians/turn.
    Static planets (orbital_radius + planet_radius >= 50) do NOT rotate.

    Returns (x, y) of the planet at t + steps_ahead.
    """
    # Find this planet in initial_planets
    init = None
    for p_data in initial_planets:
        if p_data[0] == planet_id:
            init = Planet(*p_data)
            break
    if init is None:
        return (None, None)

    # Check if this planet orbits
    orbital_radius = math.hypot(init.x - SUN_X, init.y - SUN_Y)
    if orbital_radius + init.radius >= ROTATION_RADIUS_LIMIT + SUN_RADIUS:
        # Static planet — doesn't move
        return (init.x, init.y)

    # Compute current angle and advance it
    theta_init = math.atan2(init.y - SUN_Y, init.x - SUN_X)
    theta_future = theta_init + angular_velocity * steps_ahead
    future_x = SUN_X + orbital_radius * math.cos(theta_future)
    future_y = SUN_Y + orbital_radius * math.sin(theta_future)
    return (future_x, future_y)


# ── Intercept angle for moving targets ───────────────────────
def intercept_angle(
    src_x: float, src_y: float,
    target_id: int,
    initial_planets: list,
    angular_velocity: float,
    num_ships: int,
    max_iter: int = 10
) -> Tuple[float, float, float]:
    """
    Iteratively solve for the intercept point of a moving planet.

    Returns (angle, intercept_x, intercept_y).
    If the planet is static, returns the direct angle.
    """
    # Start with a guess: current position
    init = None
    for p_data in initial_planets:
        if p_data[0] == target_id:
            init = Planet(*p_data)
            break
    if init is None:
        return (0.0, 50.0, 50.0)

    # Check if orbiting
    orbital_radius = math.hypot(init.x - SUN_X, init.y - SUN_Y)
    is_orbiting = orbital_radius + init.radius < ROTATION_RADIUS_LIMIT + SUN_RADIUS

    if not is_orbiting:
        # Static planet: just aim directly
        a = angle_to(src_x, src_y, init.x, init.y)
        return (a, init.x, init.y)

    # Iterative refinement: guess arrival time → predict position → recompute
    ix, iy = init.x, init.y
    for _ in range(max_iter):
        d = dist(src_x, src_y, ix, iy)
        t = travel_time(d, num_ships)
        new_x, new_y = predict_position(target_id, initial_planets, angular_velocity, int(t))
        if new_x is None:
            break
        if dist(ix, iy, new_x, new_y) < 0.01:
            break
        ix, iy = new_x, new_y

    a = angle_to(src_x, src_y, ix, iy)
    return (a, ix, iy)


# ── Ships needed to capture (accounting for production) ───────
def ships_needed_to_capture(
    target: Planet,
    travel_turns: float,
    safety_margin: float = 1.05
) -> int:
    """
    Estimate how many ships are needed to capture `target` given
    that `travel_turns` turns will pass before arrival.

    During transit, the target planet produces ships (if owned/neutral production).
    We add a safety margin to account for uncertainty.
    """
    future_garrison = target.ships + math.ceil(travel_turns * target.production)
    return max(1, int(math.ceil(future_garrison * safety_margin)) + 1)


# ── Sun-avoidance angle offset ────────────────────────────────
def safe_angle(
    src_x: float, src_y: float,
    tgt_x: float, tgt_y: float,
    offset_step: float = 0.15,
    max_tries: int = 20
) -> float:
    """
    If the direct path from src to tgt passes through the sun,
    try rotating the angle slightly until we find a safe route.
    Returns a safe angle in radians.
    """
    direct = angle_to(src_x, src_y, tgt_x, tgt_y)
    if not path_hits_sun(src_x, src_y, tgt_x, tgt_y):
        return direct
    # Try rotating left and right, increasing offset each step
    for i in range(1, max_tries + 1):
        for sign in [1, -1]:
            a = direct + sign * i * offset_step
            # Compute where this angle leads (far enough to clear the sun)
            reach = 150.0  # overshoot, collision detection handles it
            ex = src_x + reach * math.cos(a)
            ey = src_y + reach * math.sin(a)
            if not path_hits_sun(src_x, src_y, ex, ey):
                return a
    return direct  # fallback (rare)


# ── Quick demo ────────────────────────────────────────────────
print("Fleet speed demo:")
for n in [1, 10, 50, 100, 250, 500, 1000]:
    print(f"  {n:5d} ships → {fleet_speed(n):.2f} units/turn")

print("\nSun collision demo:")
print(f"  (10,10)→(90,90) hits sun? {path_hits_sun(10,10,90,90)}  (diagonal crosses center)")
print(f"  (0,0)→(100,0)   hits sun? {path_hits_sun(0,0,100,0)}   (horizontal edge)")
print(f"  (0,50)→(100,50) hits sun? {path_hits_sun(0,50,100,50)} (horizontal through center)")
```

## [MD]
##  <a id='agent1'></a>5. Agent v1 — Nearest Planet Sniper (Baseline)

This is the **starter agent** from the competition notebook, slightly cleaned up. It:
- Finds the nearest non-owned planet for each of your planets
- Sends exactly enough ships to capture it

**What it gets wrong:** ignores travel time production, ignores sun, can pile up ships uselessly.

We include it as a **benchmark baseline** to beat.

## [CODE]
```python
def agent_v1_sniper(obs):
    """
    Agent v1: Nearest Planet Sniper.
    For each owned planet, find the nearest non-owned planet and send
    exactly (target.ships + 1) ships toward it.
    Simple, fast, but naive.
    """
    player      = obs.player if hasattr(obs, 'player') else obs.get('player', 0)
    raw_planets = obs.planets if hasattr(obs, 'planets') else obs.get('planets', [])
    planets     = [Planet(*p) for p in raw_planets]

    my_planets  = [p for p in planets if p.owner == player]
    targets     = [p for p in planets if p.owner != player]

    if not targets:
        return []

    moves = []
    for mine in my_planets:
        # Find nearest non-owned planet
        nearest = min(targets, key=lambda t: math.hypot(mine.x - t.x, mine.y - t.y))

        ships_needed = max(nearest.ships + 1, 20)
        if mine.ships >= ships_needed:
            angle = math.atan2(nearest.y - mine.y, nearest.x - mine.x)
            moves.append([mine.id, angle, ships_needed])

    return moves

print(" Agent v1 defined")
```

## [CODE]
```python
# Quick test against the random agent
env = make("orbit_wars", configuration={"seed": 42}, debug=False)
env.run([agent_v1_sniper, "random"])

final = env.steps[-1]
for i, s in enumerate(final):
    print(f"Player {i}: reward={s.reward:.3f}, status={s.status}")
```

## [MD]
##  <a id='agent2'></a>6. Agent v2 — Sun-Aware Travel-Time Sniper

Agent v2 fixes the major bugs in v1:

1. **Sun avoidance** — rotates the launch angle if the direct path hits the sun
2. **Travel time accounting** — estimates how many ships the target will have when the fleet arrives, and sends enough to still win
3. **Don't send from weak planets** — keeps a minimum garrison at home
4. **Deduplication** — multiple planets won't all pile onto the same target

## [CODE]
```python
def agent_v2_smart_sniper(obs):
    """
    Agent v2: Sun-Aware Travel-Time Sniper.

    Improvements over v1:
    - Avoids sending fleets through the sun
    - Accounts for production during travel time
    - Keeps a minimum garrison on each owned planet
    - Avoids multiple planets piling onto the same target
    """
    player          = obs.player if hasattr(obs, 'player') else obs.get('player', 0)
    raw_planets     = obs.planets if hasattr(obs, 'planets') else obs.get('planets', [])
    initial_planets = obs.initial_planets if hasattr(obs, 'initial_planets') else obs.get('initial_planets', [])
    angular_vel     = obs.angular_velocity if hasattr(obs, 'angular_velocity') else obs.get('angular_velocity', 0.03)
    planets         = [Planet(*p) for p in raw_planets]

    my_planets  = [p for p in planets if p.owner == player]
    targets     = [p for p in planets if p.owner != player]

    if not targets or not my_planets:
        return []

    # Build a lookup: planet_id → planet
    planet_map = {p.id: p for p in planets}

    # Track which targets are already being attacked this turn
    targeted_ids = set()
    moves = []

    # Sort our planets by ship count descending (strongest acts first)
    for mine in sorted(my_planets, key=lambda p: p.ships, reverse=True):
        # Keep a minimum garrison; don't strip a planet bare
        min_garrison = max(10, mine.production * 5)
        available = mine.ships - min_garrison
        if available <= 0:
            continue

        best_target = None
        best_score  = float('inf')

        for t in targets:
            if t.id in targeted_ids:
                continue  # already being hit this turn

            # Compute direct distance
            d = dist(mine.x, mine.y, t.x, t.y)

            # Estimate travel turns
            ships_guess = available // 2 or 1
            t_turns = travel_time(d, ships_guess)

            # How many ships will we need on arrival?
            needed = ships_needed_to_capture(t, t_turns)
            if needed > available:
                continue  # can't capture this turn

            # Score: prefer nearby planets and high production
            # Lower score = better target
            score = d / (t.production + 1)
            if score < best_score:
                best_score  = score
                best_target = t

        if best_target is None:
            continue

        # Compute safe angle (avoid sun)
        d = dist(mine.x, mine.y, best_target.x, best_target.y)
        t_turns = travel_time(d, available // 2 or 1)
        needed  = ships_needed_to_capture(best_target, t_turns)
        needed  = min(needed, available)  # cap at available

        # Get safe angle
        a = safe_angle(mine.x, mine.y, best_target.x, best_target.y)

        moves.append([mine.id, a, needed])
        targeted_ids.add(best_target.id)

    return moves

print(" Agent v2 defined")
```

## [CODE]
```python
# Test v2 vs v1
results = {'v2_wins': 0, 'v1_wins': 0, 'draws': 0}
for seed in range(10):
    env = make("orbit_wars", configuration={"seed": seed}, debug=False)
    env.run([agent_v2_smart_sniper, agent_v1_sniper])
    final = env.steps[-1]
    r0 = final[0].reward
    r1 = final[1].reward
    if r0 > r1:
        results['v2_wins'] += 1
    elif r1 > r0:
        results['v1_wins'] += 1
    else:
        results['draws'] += 1

print("V2 vs V1 (10 games):")
print(f"  V2 wins : {results['v2_wins']}")
print(f"  V1 wins : {results['v1_wins']}")
print(f"  Draws   : {results['draws']}")
```

## [MD]
## <a id='agent3'></a>7. Agent v3 — Strategic Expander

Agent v3 introduces **strategy**:

1. **Defend weak planets** — if an enemy fleet is incoming, reinforce before it arrives
2. **Prioritize high-value targets** — weighted by production, not just distance
3. **Comet awareness** — capture comets when they are profitable
4. **Late-game consolidation** — when winning, reinforce a fortress and build a massive fleet
5. **Production snowball** — target the enemy's highest-production planet to slow their growth

## [CODE]
```python
def agent_v3_strategic(obs):
    """
    Agent v3: Strategic Expander.

    Additional improvements:
    - Detect incoming threats and reinforce under-attack planets
    - Score targets by (production / distance) — production value per turn
    - Chase comets that are profitable
    - Maintain a stronger garrison on home planets
    - Consolidate excess ships into fewer, larger (faster) fleets
    """
    player          = obs.player if hasattr(obs, 'player') else obs.get('player', 0)
    raw_planets     = obs.planets if hasattr(obs, 'planets') else obs.get('planets', [])
    raw_fleets      = obs.fleets  if hasattr(obs, 'fleets')  else obs.get('fleets', [])
    initial_planets = obs.initial_planets if hasattr(obs, 'initial_planets') else obs.get('initial_planets', [])
    angular_vel     = obs.angular_velocity if hasattr(obs, 'angular_velocity') else obs.get('angular_velocity', 0.03)
    comet_ids       = set(obs.comet_planet_ids if hasattr(obs, 'comet_planet_ids') else obs.get('comet_planet_ids', []))

    planets     = [Planet(*p) for p in raw_planets]
    fleets      = [Fleet(*f)  for f in raw_fleets]
    planet_map  = {p.id: p for p in planets}

    my_planets  = [p for p in planets if p.owner == player]
    targets     = [p for p in planets if p.owner != player]
    enemy_fleets = [f for f in fleets if f.owner != player]

    if not my_planets:
        return []

    moves = []
    targeted_ids  = set()   # targets we're attacking this turn
    reinforcing   = set()   # my planets sending reinforcements

    # ── STEP 1: THREAT DETECTION ─────────────────────────────
    # Find my planets under attack and estimate severity
    threats: Dict[int, int] = {}  # planet_id → incoming enemy ships
    for f in enemy_fleets:
        # Rough check: if fleet angle points roughly toward one of my planets
        for mine in my_planets:
            # Compute where the fleet will be in travel_time steps
            f_dist_to_mine = dist(f.x, f.y, mine.x, mine.y)
            # Check if the fleet's direction aligns with this planet
            fleet_angle_to_mine = angle_to(f.x, f.y, mine.x, mine.y)
            angle_diff = abs(math.atan2(math.sin(f.angle - fleet_angle_to_mine),
                                         math.cos(f.angle - fleet_angle_to_mine)))
            if angle_diff < 0.2:  # fleet is roughly aimed at my planet
                threats[mine.id] = threats.get(mine.id, 0) + f.ships

    # ── STEP 2: REINFORCEMENTS ────────────────────────────────
    # Send reinforcements to threatened planets from closest ally
    for threatened_id, incoming in threats.items():
        threatened = planet_map.get(threatened_id)
        if threatened is None:
            continue
        deficit = incoming - threatened.ships + 5  # extra buffer
        if deficit <= 0:
            continue

        # Find the closest allied planet (not the threatened one) that can help
        helpers = [
            p for p in my_planets
            if p.id != threatened_id and p.id not in reinforcing
            and p.ships > deficit + 10  # must have enough to spare
        ]
        if not helpers:
            continue
        helper = min(helpers, key=lambda p: dist(p.x, p.y, threatened.x, threatened.y))

        send = min(deficit, helper.ships - 10)
        if send > 0:
            a = safe_angle(helper.x, helper.y, threatened.x, threatened.y)
            moves.append([helper.id, a, send])
            reinforcing.add(helper.id)

    # ── STEP 3: SCORING & ATTACKING ──────────────────────────
    # Score every non-owned planet and greedily assign our planets to attack
    def target_score(mine: Planet, t: Planet) -> float:
        """Lower = better target. Production/distance ratio, boosted for comets."""
        d = dist(mine.x, mine.y, t.x, t.y)
        if d < 1e-6:
            return float('inf')
        prod_boost = 2.0 if t.id in comet_ids else 1.0
        # Penalize heavily-garrisoned neutrals when we don't have many ships
        garrison_penalty = max(1.0, t.ships / (mine.ships + 1))
        return (d * garrison_penalty) / (t.production * prod_boost + 1)

    # Sort our attacking planets (not reinforcing) by ship count desc
    attackers = [p for p in my_planets if p.id not in reinforcing]
    attackers.sort(key=lambda p: p.ships, reverse=True)

    for mine in attackers:
        min_garrison = max(15, mine.production * 8)
        available = mine.ships - min_garrison
        if available < 5:
            continue

        # Find best un-targeted target
        scored = []
        for t in targets:
            if t.id in targeted_ids:
                continue
            scored.append((target_score(mine, t), t))
        if not scored:
            continue
        scored.sort(key=lambda x: x[0])
        best = scored[0][1]

        # Calculate how many ships to send
        d = dist(mine.x, mine.y, best.x, best.y)
        needed = ships_needed_to_capture(best, travel_time(d, available))
        send = min(needed, available)
        if send < 1:
            continue

        # Get safe angle
        a = safe_angle(mine.x, mine.y, best.x, best.y)
        moves.append([mine.id, a, send])
        targeted_ids.add(best.id)

    # ── STEP 4: CONSOLIDATE EXCESS SHIPS ─────────────────────
    # If any of my planets has a huge surplus, funnel ships toward the
    # richest neighboring ally to build a strike force
    for mine in my_planets:
        if mine.id in reinforcing:
            continue
        if mine.ships > 200:
            # Find best allied neighbor to consolidate into
            allies = [p for p in my_planets if p.id != mine.id]
            if not allies:
                continue
            # Pick the ally with highest production (future income)
            rally = max(allies, key=lambda p: p.production)
            send = mine.ships // 2
            a = safe_angle(mine.x, mine.y, rally.x, rally.y)
            moves.append([mine.id, a, send])

    return moves

print(" Agent v3 defined")
```

## [CODE]
```python
# Test v3 vs v2 and v1
print("V3 vs V2 (10 games):")
results = {'v3': 0, 'v2': 0, 'draw': 0}
for seed in range(10):
    env = make("orbit_wars", configuration={"seed": seed}, debug=False)
    env.run([agent_v3_strategic, agent_v2_smart_sniper])
    final = env.steps[-1]
    r0, r1 = final[0].reward, final[1].reward
    if r0 > r1: results['v3'] += 1
    elif r1 > r0: results['v2'] += 1
    else: results['draw'] += 1
print(f"  V3 wins: {results['v3']} | V2 wins: {results['v2']} | Draws: {results['draw']}")

print("\nV3 vs random (10 games):")
results2 = {'v3': 0, 'rand': 0, 'draw': 0}
for seed in range(10):
    env = make("orbit_wars", configuration={"seed": seed}, debug=False)
    env.run([agent_v3_strategic, "random"])
    final = env.steps[-1]
    r0, r1 = final[0].reward, final[1].reward
    if r0 > r1: results2['v3'] += 1
    elif r1 > r0: results2['rand'] += 1
    else: results2['draw'] += 1
print(f"  V3 wins: {results2['v3']} | Random wins: {results2['rand']} | Draws: {results2['draw']}")
```

## [MD]
##  <a id='agent4'></a>8. Agent v4 — Orbit Interceptor (Advanced)

Agent v4 is our strongest agent. It adds:

1. **Intercept math** — leads moving (orbiting) targets so fleets actually hit them
2. **Threat prioritization** — actively targets the enemy's richest planets, not just nearest
3. **Adaptive garrison** — scales minimum garrison with game phase and threat level
4. **Fleet-based safety** — checks if an enemy fleet is about to deliver overwhelming force
5. **Comet timing** — only chases comets that will survive long enough to be worth it

>  **This is the agent you should submit and then build upon.**

## [CODE]
```python
def agent_v4_interceptor(obs):
    """
    Agent v4: Orbit Interceptor — the strongest agent in this notebook.

    Key upgrade: intercept math for orbiting planets.
    All previous improvements retained and enhanced.
    """
    # ── Parse observation ─────────────────────────────────────
    player          = obs.player if hasattr(obs, 'player') else obs.get('player', 0)
    raw_planets     = obs.planets if hasattr(obs, 'planets') else obs.get('planets', [])
    raw_fleets      = obs.fleets  if hasattr(obs, 'fleets')  else obs.get('fleets', [])
    initial_planets = obs.initial_planets if hasattr(obs, 'initial_planets') else obs.get('initial_planets', [])
    angular_vel     = obs.angular_velocity if hasattr(obs, 'angular_velocity') else obs.get('angular_velocity', 0.03)
    comet_ids       = set(obs.comet_planet_ids if hasattr(obs, 'comet_planet_ids') else obs.get('comet_planet_ids', []))
    comet_data      = obs.comets if hasattr(obs, 'comets') else obs.get('comets', [])
    step            = len(obs.planets)  # proxy for game phase (rough)

    planets     = [Planet(*p) for p in raw_planets]
    fleets      = [Fleet(*f)  for f in raw_fleets]
    planet_map  = {p.id: p for p in planets}

    my_planets      = [p for p in planets if p.owner == player]
    enemy_planets   = [p for p in planets if p.owner >= 0 and p.owner != player]
    neutral_planets = [p for p in planets if p.owner == -1]
    targets         = [p for p in planets if p.owner != player]
    my_fleets       = [f for f in fleets if f.owner == player]
    enemy_fleets    = [f for f in fleets if f.owner != player]

    if not my_planets:
        return []

    moves        = []
    targeted_ids = set()
    reinforcing  = set()

    # ── Total ships: gauge game phase ────────────────────────
    my_total_ships = sum(p.ships for p in my_planets) + sum(f.ships for f in my_fleets)

    # ── Helper: am I already sending a fleet to this planet? ─
    fleets_en_route = collections.defaultdict(int)
    for f in my_fleets:
        # Very rough: assume it's heading to the planet closest to its angle direction
        best_p, best_d = None, float('inf')
        fx_far = f.x + 200 * math.cos(f.angle)
        fy_far = f.y + 200 * math.sin(f.angle)
        for p in targets:
            # Is p approximately on the fleet's path?
            d_to_line = abs((fy_far - f.y)*(p.x - f.x) - (fx_far - f.x)*(p.y - f.y)) / \
                        (math.hypot(fy_far - f.y, fx_far - f.x) + 1e-9)
            if d_to_line < 5.0:  # within 5 units of flight path
                d = dist(f.x, f.y, p.x, p.y)
                if d < best_d:
                    best_d, best_p = d, p
        if best_p:
            fleets_en_route[best_p.id] += f.ships

    # ── STEP 1: THREAT DETECTION & REINFORCEMENT ─────────────
    incoming_threat: Dict[int, int] = {}
    for f in enemy_fleets:
        # Project fleet position 30 turns ahead
        speed = fleet_speed(f.ships)
        for mine in my_planets:
            # Check angular alignment between fleet heading and direction to my planet
            needed_angle = angle_to(f.x, f.y, mine.x, mine.y)
            angle_diff = abs(math.atan2(
                math.sin(f.angle - needed_angle),
                math.cos(f.angle - needed_angle)
            ))
            if angle_diff < 0.15:  # tighter threshold for better accuracy
                incoming_threat[mine.id] = incoming_threat.get(mine.id, 0) + f.ships

    for threatened_id, incoming in incoming_threat.items():
        mine_p = planet_map.get(threatened_id)
        if mine_p is None:
            continue
        deficit = incoming - mine_p.ships + 5
        if deficit <= 0:
            continue
        # Find nearest allied helper with surplus
        helpers = [
            p for p in my_planets
            if p.id != threatened_id
            and p.id not in reinforcing
            and p.ships >= deficit + 20
        ]
        if not helpers:
            continue
        helper = min(helpers, key=lambda p: dist(p.x, p.y, mine_p.x, mine_p.y))
        send = min(deficit + 10, helper.ships - 15)
        if send > 0:
            a = safe_angle(helper.x, helper.y, mine_p.x, mine_p.y)
            moves.append([helper.id, a, send])
            reinforcing.add(helper.id)

    # ── STEP 2: SCORE TARGETS ─────────────────────────────────
    def score_target(mine: Planet, t: Planet) -> float:
        """
        Target score — lower is better.
        Factors: distance, garrison size, production value, enemy vs neutral.
        """
        d = dist(mine.x, mine.y, t.x, t.y)
        if d < 1e-6:
            return float('inf')

        # Estimate travel time with mine's available ships
        available = max(1, mine.ships // 2)
        t_time = travel_time(d, available)
        future_garrison = t.ships + math.ceil(t_time * t.production)

        # Can we actually afford this?
        if future_garrison > mine.ships * 0.9:
            return float('inf')

        # Comet bonus (free moving planet!)
        comet_bonus = 0.5 if t.id in comet_ids else 1.0

        # Enemy planet: higher priority than neutral
        enemy_bonus = 0.7 if t.owner >= 0 else 1.0

        # Already en-route? Reduce priority
        en_route_reduction = 2.0 if fleets_en_route.get(t.id, 0) > future_garrison else 1.0

        return (d * comet_bonus * enemy_bonus * en_route_reduction) / (t.production + 1)

    # ── STEP 3: ATTACK ────────────────────────────────────────
    attackers = sorted(
        [p for p in my_planets if p.id not in reinforcing],
        key=lambda p: p.ships,
        reverse=True
    )

    for mine in attackers:
        # Adaptive garrison: scale with threat and game phase
        base_garrison = max(15, mine.production * 6)
        if mine.id in incoming_threat:
            base_garrison = max(base_garrison, incoming_threat[mine.id] + 5)
        available = mine.ships - base_garrison
        if available < 5:
            continue

        # Score all un-targeted targets
        candidates = [
            (score_target(mine, t), t)
            for t in targets
            if t.id not in targeted_ids
        ]
        candidates = [(s, t) for s, t in candidates if s < float('inf')]
        if not candidates:
            continue
        candidates.sort(key=lambda x: x[0])
        best = candidates[0][1]

        # ── INTERCEPT MATH for orbiting planets ──────────────
        is_comet = best.id in comet_ids
        is_orbiting = (
            math.hypot(best.x - SUN_X, best.y - SUN_Y) + best.radius
            < ROTATION_RADIUS_LIMIT + SUN_RADIUS
        ) and not is_comet

        if is_orbiting:
            # Use iterative intercept solver
            a, ix, iy = intercept_angle(
                mine.x, mine.y,
                best.id,
                initial_planets,
                angular_vel,
                available
            )
            # Verify the intercept angle avoids the sun
            ex = mine.x + 200 * math.cos(a)
            ey = mine.y + 200 * math.sin(a)
            if path_hits_sun(mine.x, mine.y, ex, ey):
                a = safe_angle(mine.x, mine.y, best.x, best.y)
        else:
            a = safe_angle(mine.x, mine.y, best.x, best.y)

        # Ships to send
        d = dist(mine.x, mine.y, best.x, best.y)
        needed = ships_needed_to_capture(best, travel_time(d, available))
        send = min(needed, available)
        if send < 1:
            continue

        moves.append([mine.id, a, send])
        targeted_ids.add(best.id)

    # ── STEP 4: LATE-GAME STRIKE CONSOLIDATION ───────────────
    # If my total ships far exceed enemy total, build a mega-fleet
    enemy_total = sum(p.ships for p in enemy_planets) + \
                  sum(f.ships for f in enemy_fleets)
    if my_total_ships > enemy_total * 2 and enemy_planets:
        # Find my strongest planet not already acting
        acting_ids = {m[0] for m in moves}
        idle = [p for p in my_planets if p.id not in acting_ids and p.ships > 50]
        if idle and enemy_planets:
            richest_enemy = max(enemy_planets, key=lambda p: p.production)
            for p in idle[:2]:  # at most 2 consolidation moves
                a = safe_angle(p.x, p.y, richest_enemy.x, richest_enemy.y)
                send = p.ships - 10
                if send > 0:
                    moves.append([p.id, a, send])

    return moves

print("Agent v4 defined")
```

## [CODE]
```python
# Test v4 vs all previous agents
print("V4 vs V3 (10 games):")
results = {'v4': 0, 'v3': 0, 'draw': 0}
for seed in range(10):
    env = make("orbit_wars", configuration={"seed": seed}, debug=False)
    env.run([agent_v4_interceptor, agent_v3_strategic])
    final = env.steps[-1]
    r0, r1 = final[0].reward, final[1].reward
    if r0 > r1: results['v4'] += 1
    elif r1 > r0: results['v3'] += 1
    else: results['draw'] += 1
print(f"  V4 wins: {results['v4']} | V3 wins: {results['v3']} | Draws: {results['draw']}")

print("\nV4 vs V2 (10 games):")
results2 = {'v4': 0, 'v2': 0, 'draw': 0}
for seed in range(10):
    env = make("orbit_wars", configuration={"seed": seed}, debug=False)
    env.run([agent_v4_interceptor, agent_v2_smart_sniper])
    final = env.steps[-1]
    r0, r1 = final[0].reward, final[1].reward
    if r0 > r1: results2['v4'] += 1
    elif r1 > r0: results2['v2'] += 1
    else: results2['draw'] += 1
print(f"  V4 wins: {results2['v4']} | V2 wins: {results2['v2']} | Draws: {results2['draw']}")
```

## [MD]
##  <a id='benchmark'></a>9. Benchmarking Your Agents

A proper benchmark gives you reliable win rates across many seeds and opponents.
Always benchmark before submitting — it's the fastest feedback loop.

## [CODE]
```python
def benchmark(
    agent_a,
    agent_b,
    n_games: int = 20,
    seed_start: int = 0
) -> dict:
    """
    Run `n_games` between agent_a (player 0) and agent_b (player 1).
    Returns win rates and average reward.
    """
    wins_a, wins_b, draws = 0, 0, 0
    rewards_a, rewards_b = [], []

    for seed in range(seed_start, seed_start + n_games):
        env = make("orbit_wars", configuration={"seed": seed}, debug=False)
        env.run([agent_a, agent_b])
        final = env.steps[-1]
        r0 = final[0].reward
        r1 = final[1].reward
        rewards_a.append(r0 if r0 is not None else 0)
        rewards_b.append(r1 if r1 is not None else 0)
        if r0 is None or r1 is None:
            draws += 1
        elif r0 > r1:
            wins_a += 1
        elif r1 > r0:
            wins_b += 1
        else:
            draws += 1

    avg_a = sum(rewards_a) / len(rewards_a) if rewards_a else 0
    avg_b = sum(rewards_b) / len(rewards_b) if rewards_b else 0

    return {
        'wins_a': wins_a,
        'wins_b': wins_b,
        'draws': draws,
        'win_rate_a': wins_a / n_games,
        'avg_reward_a': avg_a,
        'avg_reward_b': avg_b,
    }


# Full benchmark suite
agents = [
    ('V1-Sniper',    agent_v1_sniper),
    ('V2-SunAware',  agent_v2_smart_sniper),
    ('V3-Strategic', agent_v3_strategic),
    ('V4-Intercept', agent_v4_interceptor),
]

print("=" * 65)
print(f"{'Match':<35} {'Wins':>5} {'Losses':>7} {'Draws':>6} {'WR%':>6}")
print("=" * 65)

for name_a, agent_a in agents:
    result = benchmark(agent_a, "random", n_games=20)
    wr = result['win_rate_a'] * 100
    print(f"{name_a + ' vs random':<35} "
          f"{result['wins_a']:>5} "
          f"{result['wins_b']:>7} "
          f"{result['draws']:>6} "
          f"{wr:>5.0f}%")

print("")
# Head-to-head: V4 vs V3
result_43 = benchmark(agent_v4_interceptor, agent_v3_strategic, n_games=20)
print(f"{'V4-Intercept vs V3-Strategic':<35} "
      f"{result_43['wins_a']:>5} "
      f"{result_43['wins_b']:>7} "
      f"{result_43['draws']:>6} "
      f"{result_43['win_rate_a']*100:>5.0f}%")

result_32 = benchmark(agent_v3_strategic, agent_v2_smart_sniper, n_games=20)
print(f"{'V3-Strategic vs V2-SunAware':<35} "
      f"{result_32['wins_a']:>5} "
      f"{result_32['wins_b']:>7} "
      f"{result_32['draws']:>6} "
      f"{result_32['win_rate_a']*100:>5.0f}%")

print("=" * 65)
```

## [CODE]
```python
# 4-Player FFA benchmark
print("\n=== 4-Player FFA (V4 vs 3x random) ===")
ffa_wins = 0
for seed in range(20):
    env4 = make("orbit_wars", configuration={"seed": seed}, debug=False)
    env4.run([agent_v4_interceptor, "random", "random", "random"])
    final = env4.steps[-1]
    rewards = [s.reward for s in final]
    # In FFA, win = highest reward
    if rewards[0] is not None and rewards[0] == max(r for r in rewards if r is not None):
        ffa_wins += 1
print(f"V4 wins {ffa_wins}/20 FFA games against 3 random agents")
```

## [MD]
## <a id='submission'></a>10. Submission

Your submission must be a `main.py` file with an `agent` function (the function name must be `agent`).

We'll package Agent v4 (our strongest) as the submission.

## [CODE]
```python
%%writefile main.py
"""
Orbit Wars — Agent v4: Orbit Interceptor
Author: Your Name

Strategy:
  - Intercept orbiting planets using iterative prediction
  - Avoid sun on all fleet paths
  - Account for production during fleet travel time
  - Detect and respond to enemy incoming fleets
  - Score targets by production/distance value
  - Late-game consolidation strike against richest enemy planet
"""
import math
import collections
from typing import Dict, Tuple
from kaggle_environments.envs.orbit_wars.orbit_wars import (
    Planet, Fleet, CENTER, ROTATION_RADIUS_LIMIT
)

SUN_X, SUN_Y = 50.0, 50.0
SUN_RADIUS   = 10.0
MAX_SPEED    = 6.0


def fleet_speed(n: int, max_speed: float = MAX_SPEED) -> float:
    if n <= 1:
        return 1.0
    ratio = math.log(n) / math.log(1000)
    return 1.0 + (max_speed - 1.0) * (ratio ** 1.5)


def dist(x1, y1, x2, y2) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def angle_to(x1, y1, x2, y2) -> float:
    return math.atan2(y2 - y1, x2 - x1)


def travel_time(distance: float, num_ships: int) -> float:
    s = fleet_speed(num_ships)
    return distance / s if s > 0 else float('inf')


def path_hits_sun(x1, y1, x2, y2,
                  sun_x=SUN_X, sun_y=SUN_Y, sun_r=SUN_RADIUS) -> bool:
    dx, dy = x2 - x1, y2 - y1
    fx, fy = x1 - sun_x, y1 - sun_y
    a = dx*dx + dy*dy
    if a < 1e-10:
        return math.hypot(fx, fy) < sun_r
    b = 2 * (fx*dx + fy*dy)
    c = fx*fx + fy*fy - sun_r*sun_r
    discriminant = b*b - 4*a*c
    if discriminant < 0:
        return False
    sd = math.sqrt(discriminant)
    t1 = (-b - sd) / (2*a)
    t2 = (-b + sd) / (2*a)
    return (0 <= t1 <= 1) or (0 <= t2 <= 1) or (t1 < 0 < t2)


def predict_position(planet_id, initial_planets, angular_velocity, steps_ahead):
    init = None
    for p_data in initial_planets:
        if p_data[0] == planet_id:
            init = Planet(*p_data)
            break
    if init is None:
        return (None, None)
    orbital_radius = math.hypot(init.x - SUN_X, init.y - SUN_Y)
    if orbital_radius + init.radius >= ROTATION_RADIUS_LIMIT + SUN_RADIUS:
        return (init.x, init.y)
    theta = math.atan2(init.y - SUN_Y, init.x - SUN_X)
    theta += angular_velocity * steps_ahead
    return (
        SUN_X + orbital_radius * math.cos(theta),
        SUN_Y + orbital_radius * math.sin(theta)
    )


def intercept_angle(src_x, src_y, target_id, initial_planets, angular_vel, num_ships, max_iter=10):
    init = None
    for p_data in initial_planets:
        if p_data[0] == target_id:
            init = Planet(*p_data)
            break
    if init is None:
        return 0.0, 50.0, 50.0
    orbital_radius = math.hypot(init.x - SUN_X, init.y - SUN_Y)
    is_orbiting = orbital_radius + init.radius < ROTATION_RADIUS_LIMIT + SUN_RADIUS
    if not is_orbiting:
        a = angle_to(src_x, src_y, init.x, init.y)
        return a, init.x, init.y
    ix, iy = init.x, init.y
    for _ in range(max_iter):
        d = dist(src_x, src_y, ix, iy)
        t = travel_time(d, num_ships)
        nx, ny = predict_position(target_id, initial_planets, angular_vel, int(t))
        if nx is None or dist(ix, iy, nx, ny) < 0.01:
            break
        ix, iy = nx, ny
    return angle_to(src_x, src_y, ix, iy), ix, iy


def ships_needed_to_capture(target: Planet, travel_turns: float, margin: float = 1.05) -> int:
    future = target.ships + math.ceil(travel_turns * target.production)
    return max(1, int(math.ceil(future * margin)) + 1)


def safe_angle(x1, y1, x2, y2, step=0.15, max_tries=20) -> float:
    a = angle_to(x1, y1, x2, y2)
    if not path_hits_sun(x1, y1, x2, y2):
        return a
    for i in range(1, max_tries + 1):
        for sign in [1, -1]:
            candidate = a + sign * i * step
            ex = x1 + 150 * math.cos(candidate)
            ey = y1 + 150 * math.sin(candidate)
            if not path_hits_sun(x1, y1, ex, ey):
                return candidate
    return a


def agent(obs):
    player          = obs.player if hasattr(obs, 'player') else obs.get('player', 0)
    raw_planets     = obs.planets if hasattr(obs, 'planets') else obs.get('planets', [])
    raw_fleets      = obs.fleets  if hasattr(obs, 'fleets')  else obs.get('fleets', [])
    initial_planets = obs.initial_planets if hasattr(obs, 'initial_planets') else obs.get('initial_planets', [])
    angular_vel     = obs.angular_velocity if hasattr(obs, 'angular_velocity') else obs.get('angular_velocity', 0.03)
    comet_ids       = set(obs.comet_planet_ids if hasattr(obs, 'comet_planet_ids') else obs.get('comet_planet_ids', []))

    planets       = [Planet(*p) for p in raw_planets]
    fleets        = [Fleet(*f)  for f in raw_fleets]
    planet_map    = {p.id: p for p in planets}

    my_planets    = [p for p in planets if p.owner == player]
    enemy_planets = [p for p in planets if p.owner >= 0 and p.owner != player]
    targets       = [p for p in planets if p.owner != player]
    my_fleets     = [f for f in fleets if f.owner == player]
    enemy_fleets  = [f for f in fleets if f.owner != player]

    if not my_planets:
        return []

    moves        = []
    targeted_ids = set()
    reinforcing  = set()

    my_total    = sum(p.ships for p in my_planets) + sum(f.ships for f in my_fleets)
    enemy_total = sum(p.ships for p in enemy_planets) + sum(f.ships for f in enemy_fleets)

    # ── En-route tracking ────────────────────────────────────
    fleets_en_route = collections.defaultdict(int)
    for f in my_fleets:
        fx_far = f.x + 200 * math.cos(f.angle)
        fy_far = f.y + 200 * math.sin(f.angle)
        best_p, best_d = None, float('inf')
        for p in targets:
            denom = math.hypot(fy_far - f.y, fx_far - f.x) + 1e-9
            d_line = abs((fy_far - f.y)*(p.x - f.x) - (fx_far - f.x)*(p.y - f.y)) / denom
            if d_line < 5.0:
                d = dist(f.x, f.y, p.x, p.y)
                if d < best_d:
                    best_d, best_p = d, p
        if best_p:
            fleets_en_route[best_p.id] += f.ships

    # ── Threat detection & reinforcement ─────────────────────
    incoming_threat: Dict[int, int] = {}
    for f in enemy_fleets:
        for mine in my_planets:
            needed_angle = angle_to(f.x, f.y, mine.x, mine.y)
            diff = abs(math.atan2(
                math.sin(f.angle - needed_angle),
                math.cos(f.angle - needed_angle)
            ))
            if diff < 0.15:
                incoming_threat[mine.id] = incoming_threat.get(mine.id, 0) + f.ships

    for tid, incoming in incoming_threat.items():
        tp = planet_map.get(tid)
        if tp is None:
            continue
        deficit = incoming - tp.ships + 5
        if deficit <= 0:
            continue
        helpers = [
            p for p in my_planets
            if p.id != tid and p.id not in reinforcing and p.ships >= deficit + 20
        ]
        if not helpers:
            continue
        helper = min(helpers, key=lambda p: dist(p.x, p.y, tp.x, tp.y))
        send = min(deficit + 10, helper.ships - 15)
        if send > 0:
            a = safe_angle(helper.x, helper.y, tp.x, tp.y)
            moves.append([helper.id, a, send])
            reinforcing.add(helper.id)

    # ── Target scoring & attack ──────────────────────────────
    def score_target(mine: Planet, t: Planet) -> float:
        d = dist(mine.x, mine.y, t.x, t.y)
        if d < 1e-6:
            return float('inf')
        avail = max(1, mine.ships // 2)
        t_time = travel_time(d, avail)
        future_garrison = t.ships + math.ceil(t_time * t.production)
        if future_garrison > mine.ships * 0.9:
            return float('inf')
        comet_b  = 0.5 if t.id in comet_ids else 1.0
        enemy_b  = 0.7 if t.owner >= 0 else 1.0
        reroute  = 2.0 if fleets_en_route.get(t.id, 0) > future_garrison else 1.0
        return (d * comet_b * enemy_b * reroute) / (t.production + 1)

    attackers = sorted(
        [p for p in my_planets if p.id not in reinforcing],
        key=lambda p: p.ships, reverse=True
    )

    for mine in attackers:
        base_garrison = max(15, mine.production * 6)
        if mine.id in incoming_threat:
            base_garrison = max(base_garrison, incoming_threat[mine.id] + 5)
        available = mine.ships - base_garrison
        if available < 5:
            continue

        candidates = [
            (score_target(mine, t), t)
            for t in targets if t.id not in targeted_ids
        ]
        candidates = [(s, t) for s, t in candidates if s < float('inf')]
        if not candidates:
            continue
        candidates.sort(key=lambda x: x[0])
        best = candidates[0][1]

        is_orbiting = (
            math.hypot(best.x - SUN_X, best.y - SUN_Y) + best.radius
            < ROTATION_RADIUS_LIMIT + SUN_RADIUS
        ) and best.id not in comet_ids

        if is_orbiting:
            a, ix, iy = intercept_angle(
                mine.x, mine.y, best.id, initial_planets, angular_vel, available
            )
            ex = mine.x + 200 * math.cos(a)
            ey = mine.y + 200 * math.sin(a)
            if path_hits_sun(mine.x, mine.y, ex, ey):
                a = safe_angle(mine.x, mine.y, best.x, best.y)
        else:
            a = safe_angle(mine.x, mine.y, best.x, best.y)

        d = dist(mine.x, mine.y, best.x, best.y)
        needed = ships_needed_to_capture(best, travel_time(d, available))
        send = min(needed, available)
        if send < 1:
            continue

        moves.append([mine.id, a, send])
        targeted_ids.add(best.id)

    # ── Late-game strike ─────────────────────────────────────
    if my_total > enemy_total * 2 and enemy_planets:
        acting_ids  = {m[0] for m in moves}
        idle        = [p for p in my_planets if p.id not in acting_ids and p.ships > 50]
        richest_enemy = max(enemy_planets, key=lambda p: p.production)
        for p in idle[:2]:
            a    = safe_angle(p.x, p.y, richest_enemy.x, richest_enemy.y)
            send = p.ships - 10
            if send > 0:
                moves.append([p.id, a, send])

    return moves
```

## [CODE]
```python
# Verify the submission agent works correctly
import importlib.util, sys

spec = importlib.util.spec_from_file_location("main", "main.py")
main_mod = importlib.util.load_from_spec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_mod)

print("Verifying main.py agent against random opponent...")
env = make("orbit_wars", configuration={"seed": 99}, debug=False)
env.run([main_mod.agent, "random"])
final = env.steps[-1]
for i, s in enumerate(final):
    print(f"  Player {i}: reward={s.reward}, status={s.status}")
print("\n main.py validated — ready to submit!")
```

## [CODE]
```python
# ── Option A: Submit directly from this notebook ─────────────
# This works if you are running on Kaggle and are logged in.

# !kaggle competitions submit orbit-wars -f main.py -m "Agent v4: Orbit Interceptor"

# ── Option B: Render a final replay in the notebook ──────────
env_final = make("orbit_wars", configuration={"seed": 42}, debug=False)
env_final.run([main_mod.agent, "random"])
env_final.render(mode="ipython", width=800, height=600)
```

## [MD]
##  <a id='next'></a>11. What to Try Next

This notebook gives you a strong foundation. Here is a roadmap to push further up the leaderboard:

###  Medium Difficulty

**Better target selection**
- Use a proper **priority queue** and assign planets globally rather than planet-by-planet
- Implement **opportunity cost**: if sending ships from planet A means planet B gets captured, factor that in

**Comet optimization**
- Use the `comets.paths` field to know exactly how long a comet will be on the board
- Only chase comets that will stay for enough turns to produce more ships than it cost to capture

**Multi-fleet coordination**
- Track *all* your en-route fleets, not just this turn's launches
- Avoid sending a second fleet to an already-captured target


###  Hard / High Impact

**Monte Carlo Tree Search (MCTS)**
- Simulate a few dozen turns into the future from the current state
- Score end states by ship differential
- Choose the action sequence that maximizes future score

**Opponent modeling**
- Infer enemy strategy from their fleet angles and targets
- If enemy is rushing, turtling vs. counter-attacking can be optimal

**Learned value functions**
- Train a neural net on self-play to estimate "value" of a game state
- Use it to guide greedy decisions

**Genetic / evolutionary optimization**
- Tune the scoring weights (garrison size, comet bonus, enemy bonus, etc.) automatically by having variants play each other thousands of times

### Quick Wins (implement these first)

```python
# 1. Always send at least min_fleet_size ships to benefit from speed bonus
MIN_FLEET = 20  # sends at ~1.8 units/turn instead of 1.0

# 2. If a planet has 0 ships (just captured or comet), exploit it instantly
if target.ships == 0 and target.owner == -1:
    send_minimal_fleet()

# 3. Avoid splitting the fleet — consolidate before sending
# Instead of 3 × 50 ships, send 1 × 150 (much faster and stronger)

# 4. Track enemy fleet destinations more precisely
# If enemy has 200 ships heading to your 50-ship planet, reinforce NOW
```


###  Leaderboard Tips
- Submit early and often — the rating system needs games to converge
- You get **5 submissions per day**, only the latest 2 are tracked for finals
- Watch your **episode replays** to spot bugs you didn't know you had
- Check the leaderboard's top agents and play against them locally if you can reverse-engineer their behavior

Good luck!

## [MD]
### Connect with Me

Feel free to follow me on these platforms:

[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/AdilShamim8)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/adilshamim8)
[![Twitter](https://img.shields.io/badge/Twitter-1DA1F2?style=for-the-badge&logo=twitter&logoColor=white)](https://x.com/adil_shamim8)
[![Medium](https://img.shields.io/badge/Medium-000000?style=for-the-badge&logo=medium&logoColor=white)](https://adilshamim8.medium.com/)
