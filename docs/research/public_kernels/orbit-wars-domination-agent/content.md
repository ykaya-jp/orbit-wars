## [MD]
# 🪐 Orbit Wars — Domination Agent

**Strategy**: ROI-based target evaluation with orbital intercept prediction, sun-hazard avoidance, defensive garrison management, and front-line reinforcement.

| Phase | Module | Purpose |
|-------|--------|---------|
| 1 | State Management | Parse observation → GameState objects |
| 2 | Physics Engine | Fleet speed, orbital prediction, intercept solver |
| 3 | Strategic Heuristics | ROI-based planet valuation & target ranking |
| 4 | Tactical Execution | Fleet dispatch with sun-safe pathing |

## [CODE]
```python
%%capture
!pip install --upgrade "kaggle-environments>=1.28.0"
```

## [CODE]
```python
from kaggle_environments import make

env = make("orbit_wars", debug=True)
print(f"Environment: {env.name} v{env.version}")
print(f"Players: {env.specification.agents}")
print(f"Max steps: {env.configuration.episodeSteps}")
```

## [CODE]
```python
%%writefile main.py

import math
from typing import List, Tuple, Optional, Dict

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════
SUN_X, SUN_Y = 50.0, 50.0
SUN_RADIUS   = 10.0
SUN_SAFETY   = 2.0
BOARD_SIZE   = 100.0
MAX_TURNS    = 500
MAX_FLEET_SPEED = 6.0
MIN_FLEET_SPEED = 1.0
NEUTRAL_OWNER   = -1

PI_ID, PI_OWNER, PI_X, PI_Y, PI_RADIUS, PI_SHIPS, PI_PROD = range(7)
FI_ID, FI_OWNER, FI_X, FI_Y, FI_ANGLE, FI_FROM, FI_SHIPS = range(7)


# ═══════════════════════════════════════════════════════════════
# PHASE 1 — STATE MANAGEMENT & PARSING
# ═══════════════════════════════════════════════════════════════

class Planet:
    __slots__ = (
        'id', 'owner', 'x', 'y', 'radius', 'ships', 'production',
        'is_comet', 'is_orbiting', 'orbital_radius', 'initial_angle',
        'angular_velocity',
    )

    def __init__(self, raw, comet_ids, angular_velocity, initial_map=None, step=0):
        self.id         = int(raw[PI_ID])
        self.owner      = int(raw[PI_OWNER]) if raw[PI_OWNER] is not None else NEUTRAL_OWNER
        self.x          = float(raw[PI_X])
        self.y          = float(raw[PI_Y])
        self.radius     = float(raw[PI_RADIUS])
        self.ships      = float(raw[PI_SHIPS])
        self.production = float(raw[PI_PROD])
        self.is_comet   = self.id in comet_ids
        self.angular_velocity = angular_velocity

        dx = self.x - SUN_X
        dy = self.y - SUN_Y
        self.orbital_radius = math.hypot(dx, dy)

        self.is_orbiting = (
            not self.is_comet
            and self.orbital_radius > 0.5
            and self.orbital_radius + self.radius < 48.0
        )

        if self.is_orbiting and initial_map and self.id in initial_map:
            init = initial_map[self.id]
            ix, iy = float(init[PI_X]), float(init[PI_Y])
            self.initial_angle = math.atan2(iy - SUN_Y, ix - SUN_X)
        else:
            self.initial_angle = math.atan2(dy, dx)

    @property
    def pos(self):
        return (self.x, self.y)


class Fleet:
    __slots__ = ('id', 'owner', 'x', 'y', 'angle', 'from_planet', 'ships')

    def __init__(self, raw):
        self.id          = int(raw[FI_ID])
        self.owner       = int(raw[FI_OWNER]) if raw[FI_OWNER] is not None else NEUTRAL_OWNER
        self.x           = float(raw[FI_X])
        self.y           = float(raw[FI_Y])
        self.angle       = float(raw[FI_ANGLE])
        self.from_planet = int(raw[FI_FROM])
        self.ships       = float(raw[FI_SHIPS])


class GameState:
    def __init__(self, obs, cfg):
        self.player  = int(obs['player'])
        self.step    = int(obs.get('step', 0))
        self.angular_velocity = float(obs.get('angular_velocity', 0.0))

        comet_ids = set(int(c) for c in obs.get('comet_planet_ids', []))

        initial_map = {}
        for raw in (obs.get('initial_planets') or []):
            initial_map[int(raw[PI_ID])] = raw

        self.planets = [
            Planet(p, comet_ids, self.angular_velocity, initial_map, self.step)
            for p in obs.get('planets', [])
        ]
        self.planet_by_id = {p.id: p for p in self.planets}
        self.fleets = [Fleet(f) for f in obs.get('fleets', [])]

        self.my_planets      = [p for p in self.planets if p.owner == self.player]
        self.enemy_planets   = [p for p in self.planets if p.owner not in (self.player, NEUTRAL_OWNER)]
        self.neutral_planets = [p for p in self.planets if p.owner == NEUTRAL_OWNER]
        self.target_planets  = self.enemy_planets + self.neutral_planets

        self.my_fleets    = [f for f in self.fleets if f.owner == self.player]
        self.enemy_fleets = [f for f in self.fleets if f.owner != self.player]
        self.remaining_turns = MAX_TURNS - self.step


# ═══════════════════════════════════════════════════════════════
# PHASE 2 — PHYSICS & KINEMATICS ENGINE
# ═══════════════════════════════════════════════════════════════

def get_fleet_speed(num_ships):
    if num_ships <= 1:
        return MIN_FLEET_SPEED
    ratio = math.log(num_ships) / math.log(1000)
    ratio = min(ratio, 1.0)
    speed = MIN_FLEET_SPEED + (MAX_FLEET_SPEED - MIN_FLEET_SPEED) * (ratio ** 1.5)
    return min(speed, MAX_FLEET_SPEED)


def predict_planet_position(planet, turns_ahead, step):
    if not planet.is_orbiting:
        return (planet.x, planet.y)
    total_time = step + turns_ahead
    theta = planet.initial_angle + planet.angular_velocity * total_time
    return (SUN_X + planet.orbital_radius * math.cos(theta),
            SUN_Y + planet.orbital_radius * math.sin(theta))


def d(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def is_path_safe(x1, y1, x2, y2, margin=SUN_SAFETY):
    dx, dy = x2 - x1, y2 - y1
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq < 1e-9:
        return d(x1, y1, SUN_X, SUN_Y) > (SUN_RADIUS + margin)
    t = ((SUN_X - x1) * dx + (SUN_Y - y1) * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))
    return d(x1 + t * dx, y1 + t * dy, SUN_X, SUN_Y) > (SUN_RADIUS + margin)


def calculate_intercept(sx, sy, target, num_ships, step, max_iter=12):
    speed = get_fleet_speed(num_ships)
    if speed < 1e-6:
        return None
    tx, ty = target.x, target.y
    t_est = d(sx, sy, tx, ty) / speed
    for _ in range(max_iter):
        tx, ty = predict_planet_position(target, t_est, step)
        t_new = d(sx, sy, tx, ty) / speed
        if abs(t_new - t_est) < 0.05:
            return (tx, ty, t_new)
        t_est = t_new
    return (tx, ty, t_est)


def angle_to(x1, y1, x2, y2):
    return math.atan2(y2 - y1, x2 - x1)


# ═══════════════════════════════════════════════════════════════
# PHASE 3 — STRATEGIC HEURISTICS & PLANET VALUATION
# ═══════════════════════════════════════════════════════════════

def compute_incoming_threats(state):
    threats = {p.id: 0.0 for p in state.my_planets}
    for fleet in state.enemy_fleets:
        fx, fy = fleet.x, fleet.y
        best_pid, best_d = -1, 1e18
        for p in state.my_planets:
            dd = d(fx, fy, p.x, p.y)
            if dd < best_d:
                ad = abs(angle_to(fx, fy, p.x, p.y) - fleet.angle) % (2*math.pi)
                if ad > math.pi: ad = 2*math.pi - ad
                if ad < math.pi/3:
                    best_d = dd
                    best_pid = p.id
        if best_pid >= 0:
            threats[best_pid] += fleet.ships
    return threats


def garrison_needed(planet, threats):
    return threats.get(planet.id, 0.0) + max(1.0, planet.production * 1.5)


def already_sent(state, target_id):
    tgt = state.planet_by_id.get(target_id)
    if tgt is None: return 0.0
    total = 0.0
    for f in state.my_fleets:
        ad = abs(angle_to(f.x, f.y, tgt.x, tgt.y) - f.angle) % (2*math.pi)
        if ad > math.pi: ad = 2*math.pi - ad
        if ad < math.pi/6: total += f.ships
    return total


def evaluate_targets(state, threats):
    evals = []
    for src in state.my_planets:
        gn = garrison_needed(src, threats)
        avail = src.ships - gn
        if avail <= 2: continue

        for tgt in state.target_planets:
            if tgt.id == src.id: continue
            ic = calculate_intercept(src.x, src.y, tgt, avail, state.step)
            if ic is None: continue
            ix, iy, travel = ic
            if travel >= state.remaining_turns - 1 or travel > 80: continue
            if not is_path_safe(src.x, src.y, ix, iy): continue

            g = max(tgt.ships, 0)
            pdt = tgt.production * travel if tgt.owner != NEUTRAL_OWNER else 0.0
            need = g + pdt + 1.0
            sent = already_sent(state, tgt.id)
            adj = max(need - sent, 1.0)
            if adj > avail: continue

            rpt = state.remaining_turns - travel
            if rpt <= 0: continue
            prod = tgt.production
            if tgt.is_comet:
                prod = max(prod, 1.0)
                rpt = min(rpt, 60)

            val = prod * rpt
            if tgt.owner != NEUTRAL_OWNER:
                val += prod * travel * 0.5

            roi = val / max(adj, 1.0)
            if state.step < 60 and tgt.owner == NEUTRAL_OWNER:
                roi *= 1.3
            if travel > 40:
                roi *= 0.7

            evals.append((roi, src.id, tgt.id, ix, iy, adj))

    evals.sort(key=lambda e: e[0], reverse=True)
    return evals


# ═══════════════════════════════════════════════════════════════
# PHASE 4 — TACTICAL EXECUTION
# ═══════════════════════════════════════════════════════════════

def reinforce_frontline(state, threats, actions, spent):
    if not state.enemy_planets and not state.neutral_planets:
        return
    enemies = state.enemy_planets + state.neutral_planets
    for src in state.my_planets:
        gn = garrison_needed(src, threats)
        avail = src.ships - gn - spent.get(src.id, 0.0)
        if avail <= 5: continue

        best_ally, best_score = None, -1e18
        my_ed = min((d(src.x, src.y, ep.x, ep.y) for ep in enemies), default=1e18)

        for ally in state.my_planets:
            if ally.id == src.id: continue
            d_sa = d(src.x, src.y, ally.x, ally.y)
            if d_sa < 5.0: continue
            ally_ed = min((d(ally.x, ally.y, ep.x, ep.y) for ep in enemies), default=1e18)
            if ally_ed >= my_ed: continue
            score = (my_ed - ally_ed) / max(d_sa, 1.0)
            if score > best_score:
                best_score = score
                best_ally = ally

        if best_ally and best_score > 0.05:
            send = int(avail * 0.5)
            if send >= 3:
                ic = calculate_intercept(src.x, src.y, best_ally, send, state.step)
                if ic:
                    ix, iy, _ = ic
                    if is_path_safe(src.x, src.y, ix, iy):
                        actions.append([src.id, angle_to(src.x, src.y, ix, iy), send])
                        spent[src.id] = spent.get(src.id, 0.0) + send


def agent(observation, configuration):
    try:
        state = GameState(observation, configuration)
    except Exception:
        return []

    if not state.my_planets:
        return []

    actions = []
    spent = {p.id: 0.0 for p in state.my_planets}
    threats = compute_incoming_threats(state)
    evals = evaluate_targets(state, threats)

    targeted = set()
    for roi, src_id, tgt_id, ix, iy, adj_need in evals:
        if tgt_id in targeted: continue
        src = state.planet_by_id.get(src_id)
        if src is None: continue

        gn = garrison_needed(src, threats)
        avail = src.ships - gn - spent.get(src.id, 0.0)
        if avail < adj_need: continue

        send = int(math.ceil(adj_need * 1.10))
        send = min(send, int(avail))
        if send < 1: continue

        actions.append([src_id, angle_to(src.x, src.y, ix, iy), send])
        spent[src_id] = spent.get(src_id, 0.0) + send
        targeted.add(tgt_id)

    if state.step > 20:
        reinforce_frontline(state, threats, actions, spent)

    return actions
```

## [MD]
## Unit Tests — Physics Engine Sanity Checks

## [CODE]
```python
from main import get_fleet_speed, is_path_safe, predict_planet_position, Planet, PI_ID
import math

# --- Fleet Speed Curve ---
print('Fleet Speed Tests:')
for n in [1, 10, 50, 100, 500, 1000, 5000]:
    s = get_fleet_speed(n)
    print(f'  {n:>5} ships → {s:.2f} units/turn')

assert abs(get_fleet_speed(1) - 1.0) < 0.01, 'Speed(1) should be 1.0'
assert get_fleet_speed(1000) <= 6.01, 'Speed(1000) should be ≤ 6.0'
print('  ✅ All fleet speed tests passed\n')

# --- Sun Safety ---
print('Sun Safety Tests:')
assert is_path_safe(10, 10, 90, 90) == False, 'Diagonal through center should be unsafe'
assert is_path_safe(10, 10, 20, 10) == True, 'Far from sun should be safe'
assert is_path_safe(10, 50, 90, 50) == False, 'Horizontal through sun should be unsafe'
assert is_path_safe(10, 10, 10, 90) == True, 'Left edge vertical should be safe'
print('  ✅ All sun safety tests passed')
```

## [MD]
## Local Validation Match

## [CODE]
```python
from kaggle_environments import make
from main import agent

print('🚀 Running validation match vs reaction bot...')
env = make('orbit_wars', debug=True)
result = env.run([agent, 'random'])

final = result[-1]
print(f'\n{"="*50}')
print('MATCH COMPLETE')
print(f'{"="*50}')
for i, p in enumerate(final):
    status = p.get('status', 'UNKNOWN')
    reward = p.get('reward', 0)
    tag = '⭐ (US)' if i == 0 else ''
    print(f'  Player {i}: status={status}, reward={reward} {tag}')
```

## [MD]
## Render Replay

## [CODE]
```python
from IPython.display import HTML
html = env.render(mode='html', width=600, height=600)
HTML(html)
```

## [CODE]
```python

```
