## [MD]
## Overview

`main.py` implements a **dominance-based redistribution** agent for Kaggle Orbit Wars. Each turn it:
1. Estimates how contested each region of the board is (dominance index).
2. Derives a desired ship distribution that concentrates force near contested planets.
3. Sends surplus ships from safe planets toward targets with the largest unmet need.

## Decision Pipeline

### 1. Dominance Index

For every planet `p`, sum a signed, distance-weighted ship count over all planets and in-flight fleets:

```
net_p = Σ  signed(owner, ships) × (1 / max(dist(q, p), 1.0))
dom_p = |net_p|
```

- `signed`: `+ships` if mine, `0` if neutral, `−ships` if opponent
- The `1/d` weight (capped at distance 1) means nearby objects dominate; far objects barely register
- High `dom_p` → area firmly controlled (mine or theirs); low `dom_p` → contested

### 2. Desired Distribution

```
w_p       = 1 / (dom_p + 1)          # low dominance → high priority
desired_p = S × w_p / Σ w_q          # proportional share of my total fleet S
```

`S` includes ships on my planets plus ships in my in-flight fleets.

### 3. Move Generation

For each of my planets with a surplus (`current > desired`):

- `ships_to_send = min(surplus, ships − 1)` — always leave a 1-ship garrison
- Scan all planets within `RANGE` for candidates where `deficit = desired − current > 0`
- **Capture guard**: skip non-player targets if `ships_to_send ≤ t.ships` (can't capture)
- Compute intercept angle for orbiting targets via `intercept_pos` (iterative lead-target)
- Verify with `will_hit` (discrete sim matching the engine's step order): sun avoidance + actual collision check
- Pick the candidate with the largest deficit; break ties by distance

## Physics Helpers

| Function | Purpose |
|----------|---------|
| `fleet_speed(ships)` | Logarithmic speed formula: `1 + 5 × (log(n)/log(1000))^1.5` |
| `is_orbiting(planet)` | True if orbital radius + planet radius < 50 |
| `planet_pos_at_step(planet, av, k)` | Planet's (x, y) after k rotation ticks |
| `intercept_pos(src, dst, ships, av)` | Iterative lead-target for orbiting planets (30-step convergence) |
| `will_hit(src, dst, angle, ships, av)` | Discrete fleet simulation; returns True if collision occurs within 40 turns |
| `point_to_segment_distance` | Segment–point distance used in collision and sun checks |

## Constraints Enforced

- **Sun avoidance**: fleet path checked against sun circle every step
- **Board bounds**: fleet discarded if it exits the 100×100 grid
- **Comet exclusion**: `comet_planet_ids` are never targeted
- **Capture feasibility**: won't attack a planet the fleet can't overpower
- **Range limit**: only targets within 30 units are considered

## [CODE]
```python
%%writefile main.py
import math
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet

SUN_X, SUN_Y, SUN_R = 50.0, 50.0, 10.0
BOARD = 100.0
MAX_SPEED = 6.0
RANGE = 30.0
ROTATION_LIMIT = 50.0  # orbital_radius + planet_radius < this => planet orbits
WEIGHT_SCALE = 50.0  # scales dominance weight so the +1 regularizer in 1/(dom+1) doesn't drown out signal


def fleet_speed(ships):
    if ships <= 1:
        return 1.0
    return 1.0 + (MAX_SPEED - 1.0) * (math.log(ships) / math.log(1000)) ** 1.5


def is_orbiting(planet):
    orb_r = math.sqrt((planet.x - SUN_X) ** 2 + (planet.y - SUN_Y) ** 2)
    return orb_r + planet.radius < ROTATION_LIMIT


def point_to_segment_distance(p, v, w):
    l2 = (v[0] - w[0]) ** 2 + (v[1] - w[1]) ** 2
    if l2 == 0.0:
        return math.sqrt((p[0] - v[0]) ** 2 + (p[1] - v[1]) ** 2)
    t = max(
        0.0,
        min(1.0, ((p[0] - v[0]) * (w[0] - v[0]) + (p[1] - v[1]) * (w[1] - v[1])) / l2),
    )
    px = v[0] + t * (w[0] - v[0])
    py = v[1] + t * (w[1] - v[1])
    return math.sqrt((p[0] - px) ** 2 + (p[1] - py) ** 2)


def planet_pos_at_step(planet, angular_velocity, k):
    """Planet (x, y) after k rotation ticks past its observed position."""
    if not is_orbiting(planet) or angular_velocity == 0.0 or k == 0:
        return planet.x, planet.y
    orb_r = math.sqrt((planet.x - SUN_X) ** 2 + (planet.y - SUN_Y) ** 2)
    theta = math.atan2(planet.y - SUN_Y, planet.x - SUN_X) + angular_velocity * k
    return SUN_X + orb_r * math.cos(theta), SUN_Y + orb_r * math.sin(theta)


def intercept_pos(planet_from, planet_to, ships, angular_velocity):
    """Lead-target for an orbiting planet under the sim's discrete turn order.

    Fleet's k-th movement hits the planet at angle theta0 + (k-1)*av (the
    pre-rotation position of that turn), with dist(launch, target) ~= k*speed.
    """
    if not is_orbiting(planet_to) or angular_velocity == 0.0:
        return planet_to.x, planet_to.y

    speed = fleet_speed(ships)
    orb_r = math.sqrt((planet_to.x - SUN_X) ** 2 + (planet_to.y - SUN_Y) ** 2)
    theta0 = math.atan2(planet_to.y - SUN_Y, planet_to.x - SUN_X)

    aim_x, aim_y = planet_to.x, planet_to.y
    launch_r = planet_from.radius + 0.1
    for _ in range(30):
        dx = aim_x - planet_from.x
        dy = aim_y - planet_from.y
        norm = math.sqrt(dx * dx + dy * dy) or 1.0
        launch_x = planet_from.x + launch_r * dx / norm
        launch_y = planet_from.y + launch_r * dy / norm

        d = math.sqrt((launch_x - aim_x) ** 2 + (launch_y - aim_y) ** 2)
        t = d / speed
        rot = angular_velocity * max(0.0, t - 1.0)
        new_angle = theta0 + rot
        new_aim_x = SUN_X + orb_r * math.cos(new_angle)
        new_aim_y = SUN_Y + orb_r * math.sin(new_angle)
        if abs(new_aim_x - aim_x) < 1e-3 and abs(new_aim_y - aim_y) < 1e-3:
            aim_x, aim_y = new_aim_x, new_aim_y
            break
        aim_x, aim_y = new_aim_x, new_aim_y

    return aim_x, aim_y


def will_hit(planet_from, planet_to, angle, ships, angular_velocity, max_turns=40):
    """Discrete simulation: does a fleet launched from planet_from at `angle`
    collide with planet_to? Mirrors the engine's fleet-move -> collision ->
    planet-rotate -> sweep ordering ([orbit_wars.py:519-590])."""
    speed = fleet_speed(ships)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    fx = planet_from.x + cos_a * (planet_from.radius + 0.1)
    fy = planet_from.y + sin_a * (planet_from.radius + 0.1)
    rotating = is_orbiting(planet_to) and angular_velocity != 0.0
    r_target = planet_to.radius

    for j in range(max_turns):
        new_fx = fx + cos_a * speed
        new_fy = fy + sin_a * speed

        if not (0.0 <= new_fx <= BOARD and 0.0 <= new_fy <= BOARD):
            return False
        if point_to_segment_distance((SUN_X, SUN_Y), (fx, fy), (new_fx, new_fy)) < SUN_R:
            return False

        px, py = planet_pos_at_step(planet_to, angular_velocity, j)
        if point_to_segment_distance((px, py), (fx, fy), (new_fx, new_fy)) < r_target:
            return True

        if rotating:
            npx, npy = planet_pos_at_step(planet_to, angular_velocity, j + 1)
            if point_to_segment_distance((new_fx, new_fy), (px, py), (npx, npy)) < r_target:
                return True

        fx, fy = new_fx, new_fy

    return False


def pdist(p1, p2):
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


def agent(obs):
    player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
    raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
    raw_fleets = obs.get("fleets", []) if isinstance(obs, dict) else obs.fleets
    angular_velocity = obs.get("angular_velocity", 0.0) if isinstance(obs, dict) else obs.angular_velocity
    comet_ids = set(obs.get("comet_planet_ids", []) if isinstance(obs, dict) else obs.comet_planet_ids)

    planets = [Planet(*p) for p in raw_planets]

    def signed(owner, ships):
        if owner == player:
            return ships
        if owner == -1:
            return 0
        return -ships

    def weight(dx, dy):
        d = math.sqrt(dx * dx + dy * dy)
        return WEIGHT_SCALE / max(d, 1.0)

    dom = {}
    for p in planets:
        net = 0.0
        for q in planets:
            net += signed(q.owner, q.ships) * weight(q.x - p.x, q.y - p.y)
        for f in raw_fleets:
            fx, fy, fowner, fships = f[2], f[3], f[1], f[6]
            net += signed(fowner, fships) * weight(fx - p.x, fy - p.y)
        dom[p.id] = abs(net)

    weights = {pid: 1.0 / (d + 1.0) for pid, d in dom.items()}
    total_w = sum(weights.values()) or 1.0
    my_total = sum(p.ships for p in planets if p.owner == player) + \
               sum(f[6] for f in raw_fleets if f[1] == player)
    desired = {pid: my_total * w / total_w for pid, w in weights.items()}
    current = {p.id: signed(p.owner, p.ships) for p in planets}

    moves = []
    for mine in planets:
        if mine.owner != player or mine.ships < 2:
            continue
        surplus = int(mine.ships - desired[mine.id])
        if surplus < 1:
            continue
        ships_to_send = min(surplus, mine.ships - 1)

        best = None
        for t in planets:
            if t.id == mine.id or t.id in comet_ids:
                continue
            if pdist(mine, t) > RANGE:
                continue
            deficit = desired[t.id] - current[t.id]
            if deficit <= 0:
                continue
            if t.owner != player and ships_to_send <= t.ships:
                continue
            tx, ty = intercept_pos(mine, t, ships_to_send, angular_velocity)
            angle = math.atan2(ty - mine.y, tx - mine.x)
            if not will_hit(mine, t, angle, ships_to_send, angular_velocity):
                continue
            key = (-deficit, pdist(mine, t))
            if best is None or key < best[0]:
                best = (key, angle)

        if best is None:
            continue
        moves.append([mine.id, best[1], ships_to_send])

    return moves
```

## [CODE]
```python
!pip install --upgrade "kaggle-environments>=1.28.0"
```

## [CODE]
```python
from kaggle_environments import make
from main import agent

env = make("orbit_wars", debug=True)
print(f"Environment: {env.name} v{env.version}")
```

## [CODE]
```python
# Test it against the random agent
env = make("orbit_wars", debug=True)
env.run([agent, "random"])

final = env.steps[-1]
for i, s in enumerate(final):
    print(f"Player {i}: reward={s.reward}, status={s.status}")

env.render(mode="ipython", width=700, height=500)
```
