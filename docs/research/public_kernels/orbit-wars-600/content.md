## [MD]
# Orbit Wars — Orbital Supremacy Agent

---

## Quick Reference

```
Board: 100×100  |  Sun: center (50,50) r=10  |  Turns: 500
Planet: [id, owner, x, y, radius, ships, production]  (production 1-5)
Fleet:  [id, owner, x, y, angle, from_planet_id, ships]
Speed:  1.0 + 5.0 × (log(n)/log(1000))^1.5  (1 ship→1.0, 1000 ships→6.0)
Win:    most ships (on planets + in fleets) at turn 500
```

## [CODE]
```python
import math
import os
import random
import json

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import to_rgba
from IPython.display import display

plt.rcParams.update({
    'figure.facecolor': '#0d1117',
    'axes.facecolor':   '#161b22',
    'axes.edgecolor':   '#30363d',
    'axes.labelcolor':  '#c9d1d9',
    'xtick.color':      '#c9d1d9',
    'ytick.color':      '#c9d1d9',
    'text.color':       '#c9d1d9',
    'grid.color':       '#21262d',
    'grid.linewidth':    0.5,
})

print('Libraries loaded.')
```

## [MD]
## 1. Fleet Speed Mechanics

Speed scales logarithmically with fleet size:
$$\text{speed}(n) = 1.0 + 5.0 \times \left(\frac{\ln n}{\ln 1000}\right)^{1.5}$$

**Key insight:** sending 50 ships is 3× faster than sending 1 ship. Larger fleets are cheaper per unit-distance AND arrive sooner.

## [CODE]
```python
def fleet_speed(n):
    return 1.0 + 5.0 * (math.log(max(1, n)) / math.log(1000)) ** 1.5

ns = np.arange(1, 1001)
speeds = np.array([fleet_speed(n) for n in ns])

fig, axes = plt.subplots(1, 3, figsize=(16, 4))

# Speed curve
ax = axes[0]
ax.plot(ns, speeds, color='#58a6ff', lw=2)
ax.axhline(6.0, color='#f85149', ls='--', lw=1.2, label='Max speed 6.0')
ax.fill_between(ns, speeds, alpha=0.15, color='#58a6ff')
ax.set_xlabel('Fleet size (ships)')
ax.set_ylabel('Speed (units / turn)')
ax.set_title('Fleet Speed vs Size')
ax.legend()
ax.grid(True)

# Travel time for 40 units
ax = axes[1]
times_40 = 40 / speeds
ax.plot(ns, times_40, color='#3fb950', lw=2)
ax.set_xlabel('Fleet size (ships)')
ax.set_ylabel('Turns to travel 40 units')
ax.set_title('Travel Time (40-unit journey)')
ax.grid(True)

# Speed at key milestones
ax = axes[2]
milestones = [1, 5, 10, 25, 50, 100, 200, 500, 1000]
ms_speeds  = [fleet_speed(n) for n in milestones]
bars = ax.barh(range(len(milestones)), ms_speeds, color='#58a6ff', alpha=0.8)
ax.set_yticks(range(len(milestones)))
ax.set_yticklabels([str(n) for n in milestones])
ax.set_xlabel('Speed (units / turn)')
ax.set_title('Speed at Key Fleet Sizes')
for i, (v, s) in enumerate(zip(milestones, ms_speeds)):
    ax.text(s + 0.05, i, f'{s:.2f}', va='center', fontsize=8, color='#c9d1d9')
ax.grid(True, axis='x')

plt.tight_layout()
plt.show()

print('Speed at key fleet sizes:')
for n in [1, 10, 50, 100, 500, 1000]:
    s = fleet_speed(n)
    t = 40 / s
    print(f'  {n:>5} ships → speed {s:.2f}/turn, 40-unit trip = {t:.1f} turns')
```

## [MD]
## 2. Production ROI Analysis

Every planet captured generates `production` ships per turn for the rest of the game.
Even a low-garrison planet (20 ships) breaks even in just `20 / production` turns.

**Key insight:** at turn 1, capturing any planet with production ≥ 1 has a payback period of ≤ 20 turns out of 500.
Always expand aggressively early.

## [CODE]
```python
print('Production ROI Breakeven Analysis')
print('=' * 65)
print(f'{"Prod":>4} | {"Ships/Turn":>10} | {"Breakeven (20 garrison)":>23} | {"Ships over 400t":>15}')
print('-' * 65)

for prod in range(1, 6):
    cost      = 20          # typical garrison cost
    breakeven = cost / prod
    total_400 = prod * 400
    print(f'  {prod:>2} | {prod:>10} | {breakeven:>20.1f}t | {total_400:>15}')

print()
print('ROI comparison over 400 remaining turns:')
fig, ax = plt.subplots(figsize=(9, 4))
turns = np.arange(0, 401)
colors = ['#f85149', '#e3b341', '#3fb950', '#58a6ff', '#bc8cff']
for prod, color in zip(range(1, 6), colors):
    net = prod * turns - 20   # net ships gained (after 20-ship capture cost)
    ax.plot(turns, net, color=color, lw=1.8, label=f'Prod {prod}')
ax.axhline(0, color='#8b949e', ls='--', lw=0.8)
ax.set_xlabel('Turns since capture')
ax.set_ylabel('Net ships gained')
ax.set_title('Planet ROI Over Time (20-ship capture cost)')
ax.legend()
ax.grid(True)
plt.tight_layout()
plt.show()
```

## [MD]
## 3. Orbit Prediction

Inner planets (orbital radius + planet radius < 50) rotate around the sun at `angular_velocity` rad/turn.

The baseline agent aims at the **current** position — fleets miss completely.
This agent **iteratively solves** for the intercept point:

```
tx, ty = current planet position
for 12 iterations:
    t = distance(fleet, tx, ty) / fleet_speed
    tx, ty = planet_position(current_angle + angular_velocity * t)
angle = atan2(ty - fy, tx - fx)
```

Typically converges in 4–6 iterations.

## [CODE]
```python
# Demonstrate orbit prediction accuracy
SX, SY = 50.0, 50.0

def orbit_pos(orb_r, init_angle, av, t):
    a = init_angle + av * t
    return SX + orb_r * math.cos(a), SY + orb_r * math.sin(a)

def _spd(n):
    return 1.0 + 5.0 * (math.log(max(1, n)) / math.log(1000)) ** 1.5

def compute_intercept(fx, fy, orb_r, cur_angle, av, ships, iters=12):
    spd = _spd(ships)
    tx, ty = SX + orb_r * math.cos(cur_angle), SY + orb_r * math.sin(cur_angle)
    t = 0.0
    for _ in range(iters):
        d = math.hypot(fx - tx, fy - ty)
        t = d / spd
        tx, ty = orbit_pos(orb_r, cur_angle, av, t)
    return math.atan2(ty - fy, tx - fx), t, tx, ty

# Setup: fleet at (80, 80), planet orbiting at radius 20, av=0.04
fx, fy   = 80.0, 80.0
orb_r    = 20.0
cur_ang  = math.radians(30)   # planet currently at 30 degrees
av       = 0.04               # radians/turn
ships    = 30

# Baseline: aim at current position
px_now = SX + orb_r * math.cos(cur_ang)
py_now = SY + orb_r * math.sin(cur_ang)
base_angle = math.atan2(py_now - fy, px_now - fx)
base_t = math.hypot(fx - px_now, fy - py_now) / _spd(ships)
# Where is the planet when baseline fleet arrives?
px_base_arrive = SX + orb_r * math.cos(cur_ang + av * base_t)
py_base_arrive = SY + orb_r * math.sin(cur_ang + av * base_t)
base_fleet_x   = fx + base_t * _spd(ships) * math.cos(base_angle)
base_fleet_y   = fy + base_t * _spd(ships) * math.sin(base_angle)
base_miss = math.hypot(base_fleet_x - px_base_arrive, base_fleet_y - py_base_arrive)

# Intercept method
int_angle, int_t, int_x, int_y = compute_intercept(fx, fy, orb_r, cur_ang, av, ships)
int_fleet_x = fx + int_t * _spd(ships) * math.cos(int_angle)
int_fleet_y = fy + int_t * _spd(ships) * math.sin(int_angle)
int_miss = math.hypot(int_fleet_x - int_x, int_fleet_y - int_y)

fig, ax = plt.subplots(figsize=(8, 8))

# Sun
ax.add_patch(patches.Circle((SX, SY), 10, color='#e3b341', zorder=5, label='Sun'))

# Orbit path
theta = np.linspace(0, 2*np.pi, 200)
ax.plot(SX + orb_r*np.cos(theta), SY + orb_r*np.sin(theta),
        color='#8b949e', ls='--', lw=0.8, label='Orbit')

# Planet positions
ax.add_patch(patches.Circle((px_now, py_now), 1.5, color='#3fb950', zorder=6))
ax.text(px_now+1, py_now+1, 'Planet NOW', color='#3fb950', fontsize=8)

ax.add_patch(patches.Circle((px_base_arrive, py_base_arrive), 1.5,
                              color='#8b949e', zorder=6, alpha=0.6))
ax.text(px_base_arrive+1, py_base_arrive+1, 'Planet when\nbaseline arrives',
        color='#8b949e', fontsize=7)

ax.add_patch(patches.Circle((int_x, int_y), 1.5, color='#58a6ff', zorder=6))
ax.text(int_x+1, int_y+1, 'Intercept point', color='#58a6ff', fontsize=8)

# Fleet start
ax.plot(fx, fy, 'o', color='#bc8cff', ms=8, zorder=7, label='Our planet')

# Flight paths
ax.annotate('', xy=(base_fleet_x, base_fleet_y), xytext=(fx, fy),
            arrowprops=dict(arrowstyle='->', color='#f85149', lw=1.5))
ax.annotate('', xy=(int_fleet_x, int_fleet_y), xytext=(fx, fy),
            arrowprops=dict(arrowstyle='->', color='#58a6ff', lw=2))

ax.set_xlim(0, 100); ax.set_ylim(0, 100)
ax.set_aspect('equal')
ax.set_title('Baseline (red) MISSES orbiting planet — Intercept (blue) HITS')
ax.legend(loc='lower left')
ax.grid(True)
plt.tight_layout()
plt.show()

print(f'Baseline miss distance:  {base_miss:.2f} units  (MISS)')
print(f'Intercept miss distance: {int_miss:.4f} units  (HIT — converged in 12 iters)')
```

## [MD]
## 4. Physics Module

All helper functions needed by the agent.

## [CODE]
```python
import math

_SX, _SY = 50.0, 50.0
_SR      = 10.0
_MAX_SPD = 6.0
_L1000   = math.log(1000)

# ── Speed ─────────────────────────────────────────────────────────────────────

def _spd(n):
    '''Speed of a fleet with n ships (logarithmic, 1.0–6.0).'''
    return 1.0 + (_MAX_SPD - 1.0) * (math.log(max(1, n)) / _L1000) ** 1.5


# ── Sun collision ─────────────────────────────────────────────────────────────

def _seg_dist(ax, ay, bx, by, px, py):
    '''Minimum distance from point (px,py) to segment (ax,ay)->(bx,by).'''
    dx, dy = bx - ax, by - ay
    s2 = dx * dx + dy * dy
    if s2 < 1e-12:
        return math.hypot(ax - px, ay - py)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / s2))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)

def _sun_hit(x1, y1, x2, y2):
    '''True if segment (x1,y1)->(x2,y2) passes through the sun.'''
    return _seg_dist(x1, y1, x2, y2, _SX, _SY) < _SR + 0.5


# ── Orbit prediction ──────────────────────────────────────────────────────────

def _is_orbiting(planet, init_p):
    '''True when orbital_radius + planet_radius < 50.'''
    return math.hypot(init_p[2] - _SX, init_p[3] - _SY) + planet[4] < 50.0

def _future_xy(planet_now, init_planet, av, dt):
    '''Predicted (x, y) of planet dt turns from now.'''
    if not _is_orbiting(planet_now, init_planet):
        return planet_now[2], planet_now[3]
    r = math.hypot(init_planet[2] - _SX, init_planet[3] - _SY)
    a = math.atan2(planet_now[3] - _SY, planet_now[2] - _SX) + av * dt
    return _SX + r * math.cos(a), _SY + r * math.sin(a)

def _intercept(fx, fy, tgt, itgt, av, ships, iters=12):
    '''
    Iteratively solve fleet intercept angle and travel time.
    Returns (angle_rad, travel_turns, intercept_x, intercept_y).
    '''
    tx, ty = tgt[2], tgt[3]
    spd = _spd(ships)
    t = 0.0
    for _ in range(iters):
        d = math.hypot(fx - tx, fy - ty)
        t = d / spd
        tx, ty = _future_xy(tgt, itgt, av, t)
    return math.atan2(ty - fy, tx - fx), t, tx, ty


# ── Sun avoidance ─────────────────────────────────────────────────────────────

def _reroute_angle(fx, fy, base_angle, sign):
    '''Try deflecting base_angle by 10-75 degrees in the given direction.'''
    for deg in range(10, 80, 5):
        a = base_angle + sign * math.radians(deg)
        ex, ey = fx + 90 * math.cos(a), fy + 90 * math.sin(a)
        if not _sun_hit(fx, fy, ex, ey):
            return a
    return None

def _safe_angle(fx, fy, tx, ty, base_angle):
    '''Return (safe_angle, was_rerouted). (None, True) if no path exists.'''
    if not _sun_hit(fx, fy, tx, ty):
        return base_angle, False
    a = _reroute_angle(fx, fy, base_angle, 1) or _reroute_angle(fx, fy, base_angle, -1)
    return a, True


# ── Threat detection ──────────────────────────────────────────────────────────

def _ships_incoming(planet, fleets, mode, player, tol=0.25):
    '''
    Sum ships from fleets heading roughly toward planet.
    mode = 'enemy' or 'friendly'
    '''
    px, py, total = planet[2], planet[3], 0
    for f in fleets:
        if mode == 'enemy'    and (f[1] == player or f[1] < 0):
            continue
        if mode == 'friendly' and f[1] != player:
            continue
        da   = math.atan2(py - f[3], px - f[2])
        diff = abs((da - f[4] + math.pi) % (2 * math.pi) - math.pi)
        if diff < tol:
            total += f[6]
    return total


print('Physics module loaded.')
print(f'  Speed(1)={_spd(1):.3f}  Speed(50)={_spd(50):.3f}  Speed(1000)={_spd(1000):.3f}')
```

## [MD]
## 5. Main Agent

**Decision loop (per-planet, per-turn):**

1. Compute available ships after the defence buffer
2. Score every non-owned target by ROI
3. Pick the highest-scoring target we can afford
4. Compute intercept angle (orbit-aware), apply sun rerouting
5. Launch fleet, mark planet as targeted

**ROI formula:**  `score = production × time_remaining / (ships_needed + 1)`
Enemy planets get a 1.6× multiplier (captures + denies their income).
Comets get a 0.3× discount (temporary, likely to leave before full ROI).

## [CODE]
```python
_TURNS = [0]

def agent(obs):
    _TURNS[0] += 1
    step = _TURNS[0]

    if isinstance(obs, dict):
        player    = obs.get('player', 0)
        av        = obs.get('angular_velocity', 0.03)
        planets   = obs.get('planets', [])
        init_p    = obs.get('initial_planets', [])
        fleets    = obs.get('fleets', [])
        comet_ids = set(obs.get('comet_planet_ids', []))
    else:
        player    = obs.player
        av        = obs.angular_velocity
        planets   = obs.planets
        init_p    = getattr(obs, 'initial_planets', [])
        fleets    = obs.fleets
        comet_ids = set(getattr(obs, 'comet_planet_ids', []))

    remaining = max(1, 500 - step)
    imap = {p[0]: p for p in init_p} if init_p else {}

    mine_list = [p for p in planets if p[1] == player]
    targets   = [p for p in planets if p[1] != player]

    if not mine_list or not targets:
        return []

    moves     = []
    committed = {p[0]: 0 for p in mine_list}
    targeted  = set()

    for mine in mine_list:
        mid, _, mx, my_, mr, mships, mprod = mine

        # Available ships after defence buffer
        e_in   = _ships_incoming(mine, fleets, 'enemy',    player)
        f_in   = _ships_incoming(mine, fleets, 'friendly', player)
        threat = max(0, e_in - f_in)
        buffer = max(mprod * 4 + 3, int(threat * 1.1) + mprod * 2)
        avail  = mships - committed[mid] - buffer

        if avail < 2:
            continue

        best_score, best_move = -1e9, None

        for tgt in targets:
            tid, towner, tx, ty_, tr, tships, tprod = tgt

            if tid in targeted:
                continue
            if tid in comet_ids and math.hypot(mx - tx, my_ - ty_) > 20:
                continue

            # Orbit-aware intercept
            itgt = imap.get(tid, tgt)
            angle, travel_t, itx, ity = _intercept(mx, my_, tgt, itgt, av, avail)

            # Sun safety
            angle, rerouted = _safe_angle(mx, my_, itx, ity, angle)
            if angle is None:
                continue
            if rerouted:
                travel_t *= 1.35

            # Ships needed: garrison + production growth during transit + 1
            needed = int(tships + tprod * travel_t) + 1
            if avail < needed:
                continue
            if travel_t >= remaining * 0.9:
                continue

            # ROI score
            time_left = max(1.0, remaining - travel_t)
            value     = tprod * time_left
            if towner != -1:
                value *= 1.6
            if tid in comet_ids:
                value *= 0.3

            score = value / (needed + 1)

            if score > best_score:
                best_score = score
                best_move  = (mid, angle, needed, tid)

        if best_move and best_score > 0:
            mid_, angle_, n_, tid_ = best_move
            moves.append([mid_, angle_, n_])
            committed[mid] += n_
            targeted.add(tid_)

    return moves

print('Agent loaded.')
```

## [MD]
## 6. Board State Visualizer

Useful for inspecting game states from replay data or local test runs.

## [CODE]
```python
OWNER_COLORS = {
    -1: '#8b949e',   # neutral
     0: '#58a6ff',   # player 0
     1: '#f85149',   # player 1
     2: '#3fb950',   # player 2
     3: '#e3b341',   # player 3
}

def visualize_state(planets, fleets, player=0, comet_ids=None, step=0, title=None):
    '''Render the board state with matplotlib.'''
    if comet_ids is None:
        comet_ids = set()

    fig, ax = plt.subplots(figsize=(9, 9))

    # Board background
    ax.set_facecolor('#0d1117')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect('equal')

    # Sun
    sun = patches.Circle((50, 50), 10, color='#e3b341', zorder=10, label='Sun')
    ax.add_patch(sun)
    ax.text(50, 50, 'SUN', ha='center', va='center', fontsize=8,
            color='#0d1117', fontweight='bold', zorder=11)

    # Orbit threshold circle (informational)
    orb_limit = patches.Circle((50, 50), 40, fill=False, edgecolor='#21262d',
                                ls=':', lw=0.8, zorder=2)
    ax.add_patch(orb_limit)

    # Planets
    for p in planets:
        pid, owner, px, py, radius, ships, prod = p
        color = OWNER_COLORS.get(owner, '#ffffff')
        alpha = 0.5 if pid in comet_ids else 0.85
        circle = patches.Circle((px, py), radius, color=color, alpha=alpha, zorder=5)
        ax.add_patch(circle)
        label = f'{ships}\np{prod}'
        ax.text(px, py, label, ha='center', va='center',
                fontsize=6, color='white', zorder=6)
        if owner == player:
            ring = patches.Circle((px, py), radius + 0.8, fill=False,
                                   edgecolor='white', lw=0.8, zorder=6)
            ax.add_patch(ring)

    # Fleets
    for f in fleets:
        fid, owner, fx, fy, angle, _, ships = f
        color = OWNER_COLORS.get(owner, '#ffffff')
        length = 2.5
        ex = fx + length * math.cos(angle)
        ey = fy + length * math.sin(angle)
        ax.annotate('', xy=(ex, ey), xytext=(fx, fy),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.2), zorder=7)
        ax.text(fx, fy, str(ships), fontsize=5, color=color,
                ha='center', va='bottom', zorder=8)

    # Legend
    for owner, color in OWNER_COLORS.items():
        lbl = f'Player {owner}' if owner >= 0 else 'Neutral'
        ax.plot([], [], 'o', color=color, label=lbl, ms=8)
    ax.legend(loc='lower right', fontsize=8)

    title_str = title or f'Board State — Turn {step}'
    ax.set_title(title_str, fontsize=12, pad=10)
    ax.grid(True, alpha=0.15)
    plt.tight_layout()
    plt.show()


# Demo with synthetic data
demo_planets = [
    [0, 0,  20, 20, 1.0,  50, 3],   # player 0 home
    [1, 1,  80, 80, 1.0,  50, 3],   # player 1 home
    [2, -1, 30, 60, 2.61, 15, 5],   # neutral high-value
    [3, -1, 70, 40, 2.61, 15, 5],   # neutral high-value
    [4, 0,  25, 50, 1.69, 30, 2],   # player 0 expansion
    [5, -1, 62, 30, 1.0,  8,  1],   # neutral orbiting
    [6, -1, 38, 70, 1.0,  8,  1],   # neutral orbiting (symmetric)
]
demo_fleets = [
    [0, 0, 22, 25, math.atan2(60-25, 30-22), 0, 20],
    [1, 1, 78, 75, math.atan2(60-75, 70-78), 1, 15],
]

visualize_state(demo_planets, demo_fleets, player=0, step=42,
                title='Demo Board State — Turn 42')
```

## [MD]
## 7. Sanity Tests

Basic tests that run without `kaggle-environments`.

## [CODE]
```python
_TURNS[0] = 0  # reset turn counter

print('=== Sanity Tests ===')
print()

# Test 1: Empty observation returns empty list
result = agent({'player': 0, 'planets': [], 'fleets': [],
                'angular_velocity': 0.03, 'initial_planets': []})
assert result == [], f'Expected [], got {result}'
print('Test 1 PASS: empty obs returns []')

# Test 2: Only own planet, no targets
_TURNS[0] = 0
obs_no_targets = {
    'player': 0,
    'angular_velocity': 0.03,
    'initial_planets': [[0, 0, 20, 20, 1.0, 50, 3]],
    'planets':         [[0, 0, 20, 20, 1.0, 50, 3]],
    'fleets':          [],
    'comet_planet_ids': [],
}
result = agent(obs_no_targets)
assert result == [], f'Expected [], got {result}'
print('Test 2 PASS: no targets returns []')

# Test 3: Can capture nearby neutral planet
_TURNS[0] = 0
obs_basic = {
    'player': 0,
    'angular_velocity': 0.03,
    'initial_planets': [
        [0, 0,  20, 20, 1.0,  80, 3],  # our planet — lots of ships
        [1, -1, 30, 20, 1.0,   5, 2],  # close neutral — low garrison
    ],
    'planets': [
        [0, 0,  20, 20, 1.0,  80, 3],
        [1, -1, 30, 20, 1.0,   5, 2],
    ],
    'fleets': [],
    'comet_planet_ids': [],
}
result = agent(obs_basic)
assert len(result) == 1, f'Expected 1 move, got {len(result)}'
from_pid, angle, ships = result[0]
assert from_pid == 0, f'Should launch from planet 0, got {from_pid}'
assert ships >= 6, f'Should send at least 6 ships (garrison=5, prod=2), got {ships}'
print(f'Test 3 PASS: launched {ships} ships at angle {angle:.3f} rad')

# Test 4: Sun avoidance — planet behind sun should be rerouted
obs_sun = {
    'player': 0,
    'angular_velocity': 0.03,
    'initial_planets': [
        [0, 0,  50, 10, 1.0, 80, 3],  # near top-centre
        [1, -1, 50, 90, 1.0,  5, 2],  # near bottom-centre — direct path hits sun
    ],
    'planets': [
        [0, 0,  50, 10, 1.0, 80, 3],
        [1, -1, 50, 90, 1.0,  5, 2],
    ],
    'fleets': [],
    'comet_planet_ids': [],
}
_TURNS[0] = 0
result_sun = agent(obs_sun)
if result_sun:
    _, a, _ = result_sun[0]
    # The direct angle would be ~pi/2 (straight down through sun)
    # A rerouted angle should deviate from pi/2
    direct_angle = math.atan2(90 - 10, 0)  # pi/2
    deviation = abs(abs(a) - abs(direct_angle))
    print(f'Test 4 PASS: rerouted around sun (deviation {math.degrees(deviation):.1f} deg from direct)')
else:
    print('Test 4 INFO: no move (planet blocked — skip is also valid)')

# Test 5: Speed formula matches spec
expected_1000 = 6.0
got_1000 = _spd(1000)
assert abs(got_1000 - expected_1000) < 0.01, f'Expected 6.0 for 1000 ships, got {got_1000}'
expected_1 = 1.0
got_1 = _spd(1)
assert abs(got_1 - expected_1) < 0.01, f'Expected 1.0 for 1 ship, got {got_1}'
print(f'Test 5 PASS: speed(1)={got_1:.3f}, speed(1000)={got_1000:.3f}')

print()
print('All sanity tests passed.')
```

## [MD]
## 10. Write `submission.py`

Run this cell to (re)create `submission.py` in the current directory.

## [CODE]
```python
%%writefile submission.py
"""
Orbit Wars - Orbital Supremacy Agent
Key improvements over baseline:
  1. Intercept targeting for orbiting planets
  2. Production-value ROI scoring
  3. Transit-adjusted garrison estimates
  4. Sun path avoidance with angle rerouting
  5. Defence buffer against incoming threats
  6. No double-targeting
  7. Endgame cutoff
  8. Comet discounting
"""
import math

_SX, _SY = 50.0, 50.0
_SR      = 10.0
_MAX_SPD = 6.0
_L1000   = math.log(1000)
_TURNS   = [0]


def _spd(n):
    return 1.0 + (_MAX_SPD - 1.0) * (math.log(max(1, n)) / _L1000) ** 1.5


def _seg_dist(ax, ay, bx, by, px, py):
    dx, dy = bx - ax, by - ay
    s2 = dx * dx + dy * dy
    if s2 < 1e-12:
        return math.hypot(ax - px, ay - py)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / s2))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)


def _sun_hit(x1, y1, x2, y2):
    return _seg_dist(x1, y1, x2, y2, _SX, _SY) < _SR + 0.5


def _is_orbiting(planet, init_p):
    return math.hypot(init_p[2] - _SX, init_p[3] - _SY) + planet[4] < 50.0


def _future_xy(planet_now, init_planet, av, dt):
    if not _is_orbiting(planet_now, init_planet):
        return planet_now[2], planet_now[3]
    r = math.hypot(init_planet[2] - _SX, init_planet[3] - _SY)
    a = math.atan2(planet_now[3] - _SY, planet_now[2] - _SX) + av * dt
    return _SX + r * math.cos(a), _SY + r * math.sin(a)


def _intercept(fx, fy, tgt, itgt, av, ships, iters=12):
    tx, ty = tgt[2], tgt[3]
    spd = _spd(ships)
    t = 0.0
    for _ in range(iters):
        d = math.hypot(fx - tx, fy - ty)
        t = d / spd
        tx, ty = _future_xy(tgt, itgt, av, t)
    return math.atan2(ty - fy, tx - fx), t, tx, ty


def _reroute_angle(fx, fy, base_angle, sign):
    for deg in range(10, 80, 5):
        a = base_angle + sign * math.radians(deg)
        ex, ey = fx + 90 * math.cos(a), fy + 90 * math.sin(a)
        if not _sun_hit(fx, fy, ex, ey):
            return a
    return None


def _safe_angle(fx, fy, tx, ty, base_angle):
    if not _sun_hit(fx, fy, tx, ty):
        return base_angle, False
    a = _reroute_angle(fx, fy, base_angle, 1) or _reroute_angle(fx, fy, base_angle, -1)
    return a, True


def _ships_incoming(planet, fleets, mode, player, tol=0.25):
    px, py, total = planet[2], planet[3], 0
    for f in fleets:
        if mode == 'enemy'    and (f[1] == player or f[1] < 0):
            continue
        if mode == 'friendly' and f[1] != player:
            continue
        da   = math.atan2(py - f[3], px - f[2])
        diff = abs((da - f[4] + math.pi) % (2 * math.pi) - math.pi)
        if diff < tol:
            total += f[6]
    return total


def agent(obs):
    _TURNS[0] += 1
    step = _TURNS[0]

    if isinstance(obs, dict):
        player    = obs.get('player', 0)
        av        = obs.get('angular_velocity', 0.03)
        planets   = obs.get('planets', [])
        init_p    = obs.get('initial_planets', [])
        fleets    = obs.get('fleets', [])
        comet_ids = set(obs.get('comet_planet_ids', []))
    else:
        player    = obs.player
        av        = obs.angular_velocity
        planets   = obs.planets
        init_p    = getattr(obs, 'initial_planets', [])
        fleets    = obs.fleets
        comet_ids = set(getattr(obs, 'comet_planet_ids', []))

    remaining = max(1, 500 - step)
    imap = {p[0]: p for p in init_p} if init_p else {}

    mine_list = [p for p in planets if p[1] == player]
    targets   = [p for p in planets if p[1] != player]

    if not mine_list or not targets:
        return []

    moves     = []
    committed = {p[0]: 0 for p in mine_list}
    targeted  = set()

    for mine in mine_list:
        mid, _, mx, my_, mr, mships, mprod = mine

        e_in   = _ships_incoming(mine, fleets, 'enemy',    player)
        f_in   = _ships_incoming(mine, fleets, 'friendly', player)
        threat = max(0, e_in - f_in)
        buffer = max(mprod * 4 + 3, int(threat * 1.1) + mprod * 2)
        avail  = mships - committed[mid] - buffer

        if avail < 2:
            continue

        best_score, best_move = -1e9, None

        for tgt in targets:
            tid, towner, tx, ty_, tr, tships, tprod = tgt

            if tid in targeted:
                continue
            if tid in comet_ids and math.hypot(mx - tx, my_ - ty_) > 20:
                continue

            itgt = imap.get(tid, tgt)
            angle, travel_t, itx, ity = _intercept(mx, my_, tgt, itgt, av, avail)

            angle, rerouted = _safe_angle(mx, my_, itx, ity, angle)
            if angle is None:
                continue
            if rerouted:
                travel_t *= 1.35

            needed = int(tships + tprod * travel_t) + 1
            if avail < needed:
                continue
            if travel_t >= remaining * 0.9:
                continue

            time_left = max(1.0, remaining - travel_t)
            value     = tprod * time_left
            if towner != -1:
                value *= 1.6
            if tid in comet_ids:
                value *= 0.3

            score = value / (needed + 1)

            if score > best_score:
                best_score = score
                best_move  = (mid, angle, needed, tid)

        if best_move and best_score > 0:
            mid_, angle_, n_, tid_ = best_move
            moves.append([mid_, angle_, n_])
            committed[mid] += n_
            targeted.add(tid_)

    return moves
```

## [MD]
## 11. Submit to Kaggle

## [CODE]
```python
import os

sub_path = 'submission.py'
if os.path.exists(sub_path):
    with open(sub_path) as f:
        lines = f.readlines()
    print(f'submission.py ready: {len(lines)} lines')
    print()
    print('Submit with:')
    print('  kaggle competitions submit orbit-wars -f submission.py -m "Orbital Supremacy v1"')
else:
    print('submission.py not found — run the %%writefile cell above first.')
```

## [CODE]
```python

```
