## [MD]
# Orbit Wars — EDA & Strategy Parameter Search

**A practical guide to understanding the game and building a competitive agent.**

Orbit Wars is a real-time strategy competition on Kaggle where agents control fleets of ships, capture planets, and try to accumulate the most ships by turn 500. The game runs on a 100×100 continuous board with a central sun, orbiting planets, and comets.

This notebook is structured in four parts:

| Part | What you'll learn |
|------|-------------------|
| **1 — Game Mechanics EDA** | Fleet speed, capture cost, map layout, game dynamics |
| **2 — Strategy Comparison** | How 10 different heuristic strategies compare in head-to-head play |
| **3 — Parameter Search** | Random search over the strategy parameter space to find strong configurations |
| **4 — Validation & Export** | Confirming the winner and writing it to a submittable `main.py` |

> **Tip:** You can run this notebook end-to-end in a Kaggle environment. Part 3 takes the longest (~15–20 min for N=60 trials).

## [CODE]
```python
%%capture
!pip install --upgrade "kaggle-environments>=1.28.0"
```

## [CODE]
```python
import math
import re
import random
import itertools
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import Normalize

from kaggle_environments import make
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet, Fleet

plt.rcParams['figure.dpi'] = 110
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3

print('Setup complete.')
```

## [MD]
---
## Part 1 — Game Mechanics EDA

Before writing any strategy, it helps to build an intuition for the physics of the game. The two most important questions are:

1. **How fast do fleets travel?** — This determines when your ships arrive and how many enemy ships they'll face.
2. **How many ships do I need to capture a planet?** — The target's garrison grows while your fleet is in transit, so naively sending `garrison + 1` ships is always wrong.

## [MD]
### 1.1 Fleet Speed

Speed follows a log-power curve:

$$\text{speed} = 1 + 5 \cdot \left(\frac{\log(\text{ships})}{\log(1000)}\right)^{1.5}$$

Key properties:
- A **single ship** moves at 1 unit/turn — very slow.
- At **~100 ships**, speed reaches ~3.4 units/turn.
- At **1000 ships**, speed maxes out at 6.0 units/turn.
- There are **strongly diminishing returns** above ~200 ships.

This has a direct strategic implication: **splitting your forces into many small fleets makes each one much slower.** Consolidating ships on a single planet before attacking is often better than launching multiple small fleets simultaneously.

## [CODE]
```python
def fleet_speed(ships: int) -> float:
    if ships <= 1:
        return 1.0
    return 1.0 + 5.0 * (math.log(ships) / math.log(1000)) ** 1.5

ships_range = np.arange(1, 1001)
speeds = [fleet_speed(s) for s in ships_range]

fig, axes = plt.subplots(1, 2, figsize=(12, 4))

axes[0].plot(ships_range, speeds, color='steelblue', lw=2)
axes[0].set_xlabel('Fleet size (ships)')
axes[0].set_ylabel('Speed (units/turn)')
axes[0].set_title('Fleet Speed vs. Size')
for s_mark, label in [(1,'1'),(10,'10'),(50,'50'),(100,'100'),(500,'500'),(1000,'1000')]:
    v = fleet_speed(s_mark)
    axes[0].annotate(f'{s_mark}→{v:.1f}', xy=(s_mark, v),
                     xytext=(s_mark+60, v-0.5), fontsize=7,
                     arrowprops=dict(arrowstyle='->', color='gray', lw=0.8))

turns_50 = [50 / fleet_speed(s) for s in ships_range]
axes[1].plot(ships_range, turns_50, color='tomato', lw=2)
axes[1].set_xlabel('Fleet size (ships)')
axes[1].set_ylabel('Turns to travel 50 units')
axes[1].set_title('Travel Time for a 50-unit Journey')
axes[1].axhline(500/6, color='gray', ls='--', lw=1)
axes[1].text(800, 500/6 + 1, 'max speed', fontsize=8, color='gray')

plt.tight_layout()
plt.show()

print('Key speed milestones:')
for s in [1, 5, 10, 50, 100, 200, 500, 1000]:
    turns_across_map = 100 / fleet_speed(s)
    print(f'  {s:>5} ships  speed={fleet_speed(s):.2f}  turns to cross full map={turns_across_map:.1f}')
```

## [MD]
**Takeaways from the speed curve:**

- A fleet of 5 ships (speed ≈ 1.6) takes **64 turns** to cross the map. A fleet of 500 ships (speed ≈ 5.3) takes only **19 turns**. This means patience pays off — let ships accumulate before launching long-range attacks.
- For **nearby planets** (distance 10–20 units), even small fleets arrive quickly, so early expansion to adjacent neutrals is cheap.
- The right panel shows the travel-time curve flattens rapidly above ~200 ships. Sending 400 ships instead of 200 only saves ~3 turns for a 50-unit trip — probably not worth the garrison risk.

## [MD]
### 1.2 Capture Cost: How Many Ships Do You Really Need?

A common mistake is sending `target_ships + 1` ships to capture a planet. This is **almost always too few** because the target keeps producing ships during your fleet's travel time.

The correct capture cost requires solving a fixed-point equation:

$$\text{needed} = \text{garrison} + \text{production} \times \frac{\text{distance}}{\text{speed}(\text{needed})} + 1$$

Since `speed` depends on `needed`, we solve it iteratively. The chart below shows how steeply costs rise with distance for high-production planets.

## [CODE]
```python
def ships_to_capture(dist: float, target_ships: int, target_prod: int) -> int:
    """Iterative fixed-point estimate of the fleet size needed to capture a target."""
    ships = target_ships + 1
    for _ in range(8):  # converges quickly
        turns = dist / fleet_speed(ships)
        ships = int(target_ships + target_prod * turns) + 1
    return ships

distances = np.linspace(5, 100, 200)
prods = [1, 2, 3, 4, 5]
colors = plt.cm.plasma(np.linspace(0.2, 0.85, len(prods)))

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

for prod, c in zip(prods, colors):
    costs = [ships_to_capture(d, 10, prod) for d in distances]
    axes[0].plot(distances, costs, color=c, lw=2, label=f'prod={prod}')
axes[0].set_xlabel('Distance to target (units)')
axes[0].set_ylabel('Ships needed to capture')
axes[0].set_title('Capture Cost vs. Distance\n(target garrison = 10 ships)')
axes[0].legend(title='Target production')

garrisons = np.arange(0, 101, 5)
dist_vals = np.arange(5, 105, 5)
Z = np.array([[ships_to_capture(d, g, 3) for d in dist_vals] for g in garrisons])
im = axes[1].imshow(Z, aspect='auto', origin='lower',
                    extent=[dist_vals[0], dist_vals[-1], garrisons[0], garrisons[-1]],
                    cmap='YlOrRd')
plt.colorbar(im, ax=axes[1], label='Ships needed')
axes[1].set_xlabel('Distance to target')
axes[1].set_ylabel('Target current garrison')
axes[1].set_title('Capture Cost Heatmap  (production = 3)')

plt.tight_layout()
plt.show()

# Concrete example
d, g, p = 40, 15, 3
naive = g + 1
correct = ships_to_capture(d, g, p)
print(f'Example: distance={d}, garrison={g}, prod={p}')
print(f'  Naive estimate (garrison+1): {naive} ships')
print(f'  Correct estimate:            {correct} ships  ({correct-naive} extra needed)')
```

## [MD]
**Key insight:** For a prod-3 planet 40 units away with a 15-ship garrison, the naive estimate (`garrison + 1 = 16`) is badly wrong — you actually need **53 ships**. **If you send the naive amount, your fleet will arrive to find 53 ships waiting and will be crushed.**

The heatmap shows that distance matters more than garrison for high-production planets. A prod-5 planet 80 units away with 0 garrison costs ~150 ships to capture — comparable to a prod-1 planet with 120 garrison.

**Strategic takeaway:** Prioritize **nearby** high-production planets. Long-range attacks on rich planets are expensive; they're only worth it once you have a very large fleet.

## [MD]
### 1.3 Map Visualisation

Let's run a real game and visualise the board at three points in time. A few things to look for:
- Planet size scales with production (larger = more ships per turn)
- The numbers above planets show their current garrison
- Active fleets are shown as arrows
- All planets are placed with **4-fold mirror symmetry**, so the game is fair regardless of starting position

## [CODE]
```python
GLOBAL_SEED = 42
random.seed(GLOBAL_SEED)
env = make('orbit_wars', debug=False)
env.run(['random', 'random'])
steps = env.steps

def parse_step(step, player_idx=0):
    obs = step[player_idx].observation
    return obs, [Planet(*p) for p in obs.planets], [Fleet(*f) for f in (obs.fleets or [])]

def draw_map(planets, fleets=None, ax=None, title='', comet_ids=None):
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 7))
    pc = {-1: '#888', 0: '#2196F3', 1: '#F44336', 2: '#4CAF50', 3: '#FF9800'}
    comet_ids = comet_ids or set()

    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.set_aspect('equal')
    ax.set_facecolor('#0d1117')
    ax.grid(False)

    # Sun
    ax.add_patch(plt.Circle((50, 50), 10, color='#FFD700', alpha=0.9, zorder=3))
    ax.text(50, 50, '☀', ha='center', va='center', fontsize=14, zorder=4)

    # Planets
    for p in planets:
        edge = 'white' if p.id in comet_ids else 'none'
        ax.add_patch(plt.Circle((p.x, p.y), p.radius, color=pc.get(p.owner,'#888'),
                                alpha=0.85, zorder=4, ec=edge, lw=1.2))
        ax.text(p.x, p.y + p.radius + 1.5, str(p.ships),
                ha='center', va='bottom', fontsize=6, color='white', zorder=5)

    # Fleets
    if fleets:
        for f in fleets:
            col = pc.get(f.owner, '#888')
            dx, dy = math.cos(f.angle)*3, math.sin(f.angle)*3
            ax.annotate('', xy=(f.x+dx, f.y+dy), xytext=(f.x, f.y),
                        arrowprops=dict(arrowstyle='->', color=col, lw=1.2), zorder=5)

    ax.legend(handles=[
        patches.Patch(color='#888',    label='Neutral'),
        patches.Patch(color='#2196F3', label='Player 0'),
        patches.Patch(color='#F44336', label='Player 1'),
    ], loc='upper left', fontsize=7, facecolor='#1a1a2e', labelcolor='white')
    ax.set_title(title, color='white', fontsize=10)
    ax.tick_params(colors='white')
    for sp in ax.spines.values():
        sp.set_edgecolor('#444')
    return ax

fig, axes = plt.subplots(1, 3, figsize=(18, 6), facecolor='#0d1117')
for ax, idx, label in [
    (axes[0],   1, 'Turn 1 — Start'),
    (axes[1], 100, 'Turn 100 — Mid-game'),
    (axes[2],  -1, 'Turn 500 — End'),
]:
    obs, planets, fleets = parse_step(steps[min(idx, len(steps)-1)])
    comet_ids = set(obs.comet_planet_ids or [])
    draw_map(planets, fleets, ax=ax, title=label, comet_ids=comet_ids)
plt.tight_layout()
plt.show()
```

## [MD]
**What to observe:**
- At **Turn 1**, both players start with a single home planet. All other planets are neutral with varying garrisons and sizes.
- By **Turn 100**, the mid-game picture shows contested territory, active fleets, and possibly comets (white-outlined circles) flying through.
- At **Turn 500**, the game ends and the player with the most total ships wins.

**Notice the sun in the center:** Fleets that cross it are destroyed. This is critical for choosing attack angles — sometimes the shortest path is also the deadliest. The `_seg_hits_sun` check must be part of any serious agent.

## [MD]
### 1.4 Game Progression Over Time

Looking at the time series of ship counts reveals the typical arc of a game: early expansion, a contested middle, and then a snowball effect as one player pulls ahead in production.

## [CODE]
```python
def collect_game_stats(env_steps):
    records = []
    for t, step in enumerate(env_steps[1:], start=1):
        obs     = step[0].observation
        planets = [Planet(*p) for p in obs.planets]
        fleets  = [Fleet(*f)  for f in (obs.fleets or [])]

        planet_ships = defaultdict(int)
        fleet_ships  = defaultdict(int)
        planet_count = defaultdict(int)

        for p in planets:
            planet_ships[p.owner] += p.ships
            if p.owner >= 0:
                planet_count[p.owner] += 1
        for f in fleets:
            fleet_ships[f.owner] += f.ships

        records.append({
            'turn': t,
            **{f'planet_ships_{o}': planet_ships[o] for o in range(2)},
            **{f'fleet_ships_{o}':  fleet_ships[o]  for o in range(2)},
            **{f'planets_{o}':      planet_count[o] for o in range(2)},
        })
    return records

stats = collect_game_stats(steps)
turns = [r['turn'] for r in stats]
colors_p = ['#2196F3', '#F44336']
labels   = ['Player 0', 'Player 1']

fig, axes = plt.subplots(1, 3, figsize=(15, 4))

for p, (c, lbl) in enumerate(zip(colors_p, labels)):
    total = [r[f'planet_ships_{p}'] + r[f'fleet_ships_{p}'] for r in stats]
    axes[0].plot(turns, total, color=c, lw=1.5, label=lbl)
axes[0].set_title('Total Ships (planets + fleets)')
axes[0].set_xlabel('Turn'); axes[0].legend()

for p, (c, lbl) in enumerate(zip(colors_p, labels)):
    axes[1].plot(turns, [r[f'fleet_ships_{p}'] for r in stats], color=c, lw=1.5, label=lbl)
axes[1].set_title('Ships in Transit (fleets)')
axes[1].set_xlabel('Turn'); axes[1].legend()

for p, (c, lbl) in enumerate(zip(colors_p, labels)):
    axes[2].plot(turns, [r[f'planets_{p}'] for r in stats], color=c, lw=1.5, label=lbl)
axes[2].set_title('Planets Owned')
axes[2].set_xlabel('Turn'); axes[2].legend()

# Mark the turning point (where one player first gets a sustained lead)
p0_total = [r['planet_ships_0'] + r['fleet_ships_0'] for r in stats]
p1_total = [r['planet_ships_1'] + r['fleet_ships_1'] for r in stats]
winner_turns = [t for t, (a, b) in zip(turns, zip(p0_total, p1_total)) if a > b]
if winner_turns:
    axes[0].axvline(winner_turns[0], color='#2196F3', ls=':', lw=1, alpha=0.6)

plt.tight_layout()
plt.show()
```

## [MD]
**Key observations from the time series:**

1. **Fleet ships spike when attacks are launched** — the dips and spikes in the middle chart correspond to offensive moves.
2. **Planet count drives long-term growth** — more planets = more production = wider gap over time. Capturing even one extra planet early can snowball dramatically.
3. **The game is often decided by turn 200–300**, even though it runs until turn 500. Once a player has a 2× lead in planets, the production advantage compounds.

This suggests that **early aggression and efficient expansion** are more important than defense-focused play in most games.

## [MD]
### 1.5 Orbital Planet Mechanics

Planets whose orbital radius + planet radius is less than 50 units **rotate around the sun** at a constant angular velocity (`angular_velocity` in the observation, typically 0.025–0.05 rad/turn).

This creates a major challenge: **if you aim your fleet at the planet's current position, it will have moved by the time your fleet arrives.** To hit accurately, you need to compute the planet's future position:

$$\theta_{\text{future}} = \theta_0 + \omega \cdot t_{\text{travel}}$$

where $\omega$ is `angular_velocity` and $t_{\text{travel}}$ is your estimated travel time (which itself depends on fleet size). The `initial_planets` field gives planet positions at turn 0, so you can always compute $\theta_0$.

## [CODE]
```python
obs0        = steps[1][0].observation
init_pl     = [Planet(*p) for p in obs0.initial_planets]
ang_vel     = obs0.angular_velocity

orbital, static = [], []
for p in init_pl:
    r_orbit = math.hypot(p.x - 50, p.y - 50)
    (orbital if r_orbit + p.radius < 50 else static).append((p, r_orbit))

print(f'Angular velocity : {ang_vel:.4f} rad/turn  = {math.degrees(ang_vel):.3f}°/turn')
print(f'Orbital planets  : {len(orbital)}')
print(f'Static planets   : {len(static)}')
print(f'Full rotation    : {360 / math.degrees(ang_vel):.0f} turns')
print(f'Drift over 500 t : {math.degrees(ang_vel * 500):.1f}°')

fig, axes = plt.subplots(1, 2, figsize=(13, 6), facecolor='#0d1117')
for ax in axes:
    ax.set_facecolor('#0d1117'); ax.set_xlim(0,100); ax.set_ylim(0,100)
    ax.set_aspect('equal'); ax.grid(color='#333', lw=0.5)
    ax.add_patch(plt.Circle((50,50), 10, color='#FFD700', alpha=0.9, zorder=3))

def plot_planets(ax, orbital, static, turn):
    for p, r in static:
        ax.add_patch(plt.Circle((p.x, p.y), p.radius, color='#9E9E9E', alpha=0.7))
    for p, r in orbital:
        theta0 = math.atan2(p.y - 50, p.x - 50)
        theta_t = theta0 + ang_vel * turn
        nx, ny = 50 + r*math.cos(theta_t), 50 + r*math.sin(theta_t)
        # Orbit ring
        ring = [(50+r*math.cos(a), 50+r*math.sin(a)) for a in np.linspace(0, 2*math.pi, 80)]
        ax.plot(*zip(*ring), '--', color='#00BCD4', alpha=0.25, lw=0.8)
        if turn > 0:
            ax.add_patch(plt.Circle((p.x, p.y), p.radius, color='#00BCD4', alpha=0.2))  # ghost
            ax.annotate('', xy=(nx, ny), xytext=(p.x, p.y),
                        arrowprops=dict(arrowstyle='->', color='#00BCD4', lw=1, alpha=0.6))
        ax.add_patch(plt.Circle((nx, ny), p.radius, color='#00BCD4', alpha=0.85))

plot_planets(axes[0], orbital, static, 0)
axes[0].set_title('Turn 1 — initial positions', color='white')

plot_planets(axes[1], orbital, static, 250)
axes[1].set_title(f'Turn 250 — orbital drift ({math.degrees(ang_vel*250):.0f}°)', color='white')

for ax in axes:
    ax.tick_params(colors='white')
    for sp in ax.spines.values(): sp.set_edgecolor('#444')

for ax, lbl in zip(axes, ['Orbital (cyan) / Static (gray)', 'Arrows show movement from turn 1']):
    ax.text(1, 1, lbl, color='#aaa', fontsize=7, transform=ax.transAxes,
            ha='right', va='bottom')

plt.tight_layout()
plt.show()
```

## [MD]
**Strategy implications of orbital planets:**

In this run, `angular_velocity = 0.0410 rad/turn` (≈ 2.35°/turn). A full orbit takes **153 turns**, and
over a 500-turn game the planets drift **1174°** — more than three full rotations.

At this speed, a medium-sized fleet crossing 40 units (~11 turns) arrives to find the target has
moved **≈ 26°** along its orbit. For a planet at orbital radius 20 the arc length is
about 9 units — enough to miss if you aim at the current position.

- **Naive aiming (current position)** will cause fleets to miss or arrive at a bad angle,
  especially for inner orbital planets.
- The correct approach: compute `θ_future = θ_0 + ω × t_travel`, then aim at
  `(sun_x + r·cos(θ_future), sun_y + r·sin(θ_future))`. Since `t_travel` depends on
  fleet size, a few iterations converge quickly.
- `initial_planets` in the observation gives every planet's **turn-0 position**, so you can
  always recompute `θ_0 = atan2(y₀ − 50, x₀ − 50)` regardless of the current turn.

> This is one of the highest-impact improvements available to a baseline agent.

## [MD]
---
## Part 2 — Strategy Comparison

### Framework: The Parametric Agent

Rather than hard-coding a specific strategy, we define a **parametric agent** whose behaviour is controlled by 8 continuous values. Every named strategy in the tournament is just a specific setting of these parameters.

The agent scores each possible `(source_planet, target_planet)` pair and attacks the best one:

$$\text{score}(\text{src}, \text{tgt}) = -w_{\text{dist}} \cdot \frac{d}{141} + w_{\text{prod}} \cdot \frac{p}{5} - w_{\text{weak}} \cdot \frac{g}{500} + b_{\text{neut}} \cdot \mathbb{1}_{\text{neutral}} + b_{\text{enemy}} \cdot \mathbb{1}_{\text{enemy}}$$

| Parameter | Effect when large |
|-----------|------------------|
| `dist_weight` | Prefer nearby planets (less travel time, lower capture cost) |
| `prod_weight` | Prefer high-production planets (better long-term value) |
| `weak_weight` | Prefer planets with few ships (easier to capture) |
| `neutral_bonus` | Prefer neutral planets over enemy (expansion > fighting) |
| `enemy_bonus` | Prefer enemy planets (aggressive, destroys opponent production) |
| `attack_buffer` | Send more ships than minimum (reduces failed attacks, wastes ships) |
| `min_ships` | Only attack from planets with enough ships (conservative) |
| `use_defense` | Reinforce threatened planets before attacking |

Note that `neutral_bonus` and `enemy_bonus` are not mutually exclusive — you can set both high and the agent will weigh all non-owned planets.

## [CODE]
```python
# ── Shared physics helpers ────────────────────────────────────────────────────
SUN_X, SUN_Y, SUN_R = 50.0, 50.0, 10.0
MAX_SPEED  = 6.0
MAX_DIAG   = 141.421
MAX_SHIPS  = 500.0
WAIT_TURNS = 2

def _seg_hits_sun(x1, y1, x2, y2, margin=2.0):
    """True if the line segment (x1,y1)→(x2,y2) passes through the sun."""
    dx, dy = x2-x1, y2-y1
    fx, fy = x1-SUN_X, y1-SUN_Y
    a = dx*dx + dy*dy
    if a == 0: return False
    b = 2*(fx*dx + fy*dy)
    c = fx*fx + fy*fy - (SUN_R + margin)**2
    disc = b*b - 4*a*c
    if disc < 0: return False
    sq = math.sqrt(disc)
    t1, t2 = (-b-sq)/(2*a), (-b+sq)/(2*a)
    return (0 <= t1 <= 1) or (0 <= t2 <= 1)

def _capture_cost(sx, sy, tgt):
    """Iterative estimate of ships needed to capture planet `tgt` from (sx,sy)."""
    dist = math.hypot(sx - tgt.x, sy - tgt.y)
    ships = tgt.ships + 1
    for _ in range(8):
        turns = dist / fleet_speed(ships)
        ships = int(tgt.ships + tgt.production * turns) + 1
    return ships

def _detect_threats(my_planets, fleets, player):
    """Detect enemy fleets heading toward my planets.
    Returns {planet_id: (total_incoming_ships, min_turns_to_arrive)}.
    """
    threats = {}
    for f in fleets:
        if f.owner == player or f.owner < 0:
            continue
        fdx, fdy = math.cos(f.angle), math.sin(f.angle)
        for p in my_planets:
            to_px, to_py = p.x - f.x, p.y - f.y
            dot = fdx*to_px + fdy*to_py
            if dot <= 0: continue
            if abs(fdx*to_py - fdy*to_px) > p.radius + 3: continue
            turns = dot / fleet_speed(f.ships)
            if p.id not in threats:
                threats[p.id] = [0, float('inf')]
            threats[p.id][0] += f.ships
            threats[p.id][1] = min(threats[p.id][1], turns)
    return {pid: tuple(v) for pid, v in threats.items()}

print('Physics helpers loaded.')
```

## [CODE]
```python
@dataclass
class Strategy:
    name:          str
    dist_weight:   float   # penalise distance in target score
    prod_weight:   float   # reward high production in target score
    weak_weight:   float   # reward low garrison (easy target)
    neutral_bonus: float   # extra score for neutral planets
    enemy_bonus:   float   # extra score for enemy planets
    attack_buffer: float   # multiply capture cost before sending (≥1.0)
    min_ships:     int     # minimum ships on source planet before attacking
    use_defense:   bool    # whether to run defensive reinforcement logic

# 10 hand-crafted strategies spanning the major strategic philosophies
NAMED_STRATEGIES: List[Strategy] = [
    #                    name             dist  prod  weak  neut  enmy   buf  min   def
    Strategy('closest',          3.0,  0.0,  0.0,  0.0,  0.0,  1.0,  1, False),  # pure proximity
    Strategy('richest',          0.5,  3.0,  0.0,  0.5,  0.0,  1.0,  1, False),  # value-focused
    Strategy('weakest',          1.0,  0.5,  2.0,  0.0,  0.0,  1.0,  1, False),  # easy targets
    Strategy('blitz',            3.0,  0.5,  0.0,  0.0,  1.0,  1.0,  1, False),  # fast & aggressive
    Strategy('conservative',     2.0,  1.0,  0.0,  1.0,  0.0,  2.0, 10, False),  # 2× margin
    Strategy('expansion',        2.0,  1.5,  0.5,  3.0,  0.0,  1.0,  1, False),  # neutrals first
    Strategy('balanced',         1.5,  1.5,  1.0,  0.5,  0.5,  1.2,  5, False),  # all-rounder
    Strategy('defensive',        2.0,  1.0,  0.5,  0.5,  0.5,  1.3,  5,  True),  # reinforce threatened planets
    Strategy('aggressive',       1.0,  2.0,  0.5,  0.0,  2.0,  1.0,  1, False),  # hunt enemy planets
    Strategy('smart',            2.0,  2.0,  1.0,  1.0,  1.0,  1.2,  5,  True),  # defense + value
]

print(f'{len(NAMED_STRATEGIES)} named strategies.')
print(f'Example — "expansion": {NAMED_STRATEGIES[5]}')
```

## [MD]
### Strategy Descriptions

Each strategy is a different "personality" for the agent. Here is what each one does and the hypothesis behind it:

| Strategy | Tagline | Core idea | Weakness |
|----------|---------|-----------|----------|
| **closest** | *Move fast, attack nearby* | Always attack the nearest non-owned planet. Minimal travel time means less production growth to fight. | Ignores planet value — may chain-capture low-production planets while missing a nearby prod-5 gem. |
| **richest** | *Own the economy* | Score targets primarily by production. A prod-5 planet is worth ~5× a prod-1 planet over the long run. | Long travel time to high-value planets is expensive; the planet grows its garrison while your fleet is in transit. |
| **weakest** | *Pick on the smallest* | Target planets with the fewest current ships — the easiest to capture right now. Minimises failed attacks. | Ignores production value entirely; may capture a useless prod-1 planet instead of a nearby prod-4 one. |
| **blitz** | *Rush attack, no mercy* | Like  but with a bonus for enemy planets. Attacks the opponent directly rather than expanding into neutrals first. | Leaves neutrals uncaptured, so the opponent may grab them for free production while you are fighting. |
| **conservative** | *Never overcommit* | Sends 2× the minimum required ships and only attacks from planets with ≥10 ships. Very low rate of failed attacks. | Slow to expand; high  means you often sit on ships waiting to accumulate enough to meet the threshold. |
| **expansion** | *Land-grab first* | Strong bonus for neutral planets; captures free territory before engaging the enemy. Grows production base quickly in the early game. | Ignores the opponent in the early game — if the enemy rushes you while you expand peacefully, you may be caught under-defended. |
| **balanced** | *All-rounder* | Moderate weights across distance, production, and garrison. No strong preference for neutral vs. enemy. | Jack-of-all-trades; never maximises any single advantage. May be outperformed by specialists in the situations they are designed for. |
| **defensive** | *Attack and protect* | Like  but also monitors incoming enemy fleets and sends reinforcements to threatened planets before launching attacks. | Reinforcement logic can hold ships back from productive attacks; too much defense can hand the opponent the economic lead. |
| **aggressive** | *Destroy the opponent* | Strong bonus for enemy-owned planets and high production weight. Tries to eliminate enemy production rather than expand neutrally. | May ignore nearby cheap neutrals that would pay off faster; very sensitive to the state of the game (only effective once you are roughly equal in strength). |
| **smart** | *Defend + optimise value* | Combines the defense logic of  with a balanced value function that rewards both production and distance. Closest to a "full" heuristic agent. | More parameters = more ways to be wrong; the individual weights are still hand-tuned rather than learned. |

## [CODE]
```python
def make_agent(s: Strategy):
    """Return a stateful agent function for the given Strategy.
    Each call to make_agent() creates a fresh turn counter,
    so the same strategy can play as multiple independent players.
    """
    tc = [0]

    def _agent(obs):
        tc[0] += 1
        if tc[0] <= WAIT_TURNS:
            return []

        player  = obs.get('player', 0)   if isinstance(obs, dict) else obs.player
        raw_p   = obs.get('planets', []) if isinstance(obs, dict) else obs.planets
        raw_f   = obs.get('fleets', [])  if isinstance(obs, dict) else obs.fleets
        planets = [Planet(*p) for p in raw_p]
        fleets  = [Fleet(*f)  for f in (raw_f or [])]
        my_pl   = [p for p in planets if p.owner == player]
        targets = [p for p in planets if p.owner != player]

        if not my_pl:
            return []

        avail = {p.id: p.ships for p in my_pl}
        moves = []

        # ── Defense pass (optional) ───────────────────────────────────────────
        # If use_defense=True, check for incoming enemy fleets and reinforce
        # threatened planets from the nearest friendly planet with spare ships.
        if s.use_defense:
            pby_id = {p.id: p for p in planets}
            for pid, (inc, turns) in sorted(
                    _detect_threats(my_pl, fleets, player).items(),
                    key=lambda x: x[1][1]):
                pl = pby_id.get(pid)
                if pl is None: continue
                deficit = inc - (pl.ships + int(pl.production * turns)) + 1
                if deficit <= 0: continue
                for h in sorted([p for p in my_pl if p.id != pid and avail[p.id] > 10],
                                 key=lambda p: math.hypot(p.x - pl.x, p.y - pl.y)):
                    if deficit <= 0: break
                    if _seg_hits_sun(h.x, h.y, pl.x, pl.y): continue
                    send = min(avail[h.id] - 5, deficit)
                    if send <= 0: continue
                    moves.append([h.id, math.atan2(pl.y - h.y, pl.x - h.x), send])
                    avail[h.id] -= send
                    deficit -= send

        if not targets:
            return moves

        # ── Attack pass ───────────────────────────────────────────────────────
        # For each source planet (richest first), score all valid targets and
        # attack the best one. If we can't afford any target, consolidate ships
        # toward the nearest friendly planet instead.
        targeted = set()
        for src in sorted(my_pl, key=lambda p: -avail[p.id]):
            if avail[src.id] < s.min_ships:
                continue
            scored = []
            for tgt in targets:
                if tgt.id in targeted or _seg_hits_sun(src.x, src.y, tgt.x, tgt.y):
                    continue
                dist = math.hypot(src.x - tgt.x, src.y - tgt.y)
                is_n = float(tgt.owner == -1)
                is_e = float(tgt.owner not in (-1, player) and tgt.owner >= 0)
                score = (
                    -s.dist_weight   * (dist / MAX_DIAG)
                    + s.prod_weight  * (tgt.production / 5.0)
                    - s.weak_weight  * (min(tgt.ships, MAX_SHIPS) / MAX_SHIPS)
                    + s.neutral_bonus * is_n
                    + s.enemy_bonus   * is_e
                )
                scored.append((tgt, score))
            if not scored:
                if avail[src.id] > 15:
                    frn = [p for p in my_pl if p.id != src.id]
                    if frn:
                        dst = min(frn, key=lambda p: math.hypot(p.x-src.x, p.y-src.y))
                        if not _seg_hits_sun(src.x, src.y, dst.x, dst.y):
                            send = avail[src.id] // 2
                            moves.append([src.id, math.atan2(dst.y-src.y, dst.x-src.x), send])
                            avail[src.id] -= send
                continue
            tgt, _ = max(scored, key=lambda x: x[1])
            needed = int(_capture_cost(src.x, src.y, tgt) * s.attack_buffer)
            if avail[src.id] >= needed > 0:
                moves.append([src.id, math.atan2(tgt.y-src.y, tgt.x-src.x), needed])
                avail[src.id] -= needed
                targeted.add(tgt.id)
            elif avail[src.id] > 15:
                frn = [p for p in my_pl if p.id != src.id]
                if frn:
                    dst = min(frn, key=lambda p: math.hypot(p.x-src.x, p.y-src.y))
                    if not _seg_hits_sun(src.x, src.y, dst.x, dst.y):
                        send = avail[src.id] // 2
                        moves.append([src.id, math.atan2(dst.y-src.y, dst.x-src.x), send])
                        avail[src.id] -= send
        return moves

    return _agent


def play_match(s_a: Strategy, s_b: Strategy, game_seed: int = None) -> Tuple[float, float]:
    """Run one game between two strategies and return (reward_a, reward_b)."""
    if game_seed is not None:
        random.seed(game_seed)
    env = make('orbit_wars', debug=False)
    env.run([make_agent(s_a), make_agent(s_b)])
    f = env.steps[-1]
    return f[0].reward, f[1].reward

print('Agent factory ready.  Example: make_agent(NAMED_STRATEGIES[0])')
```

## [MD]
### Round-Robin Tournament

We run a **full round-robin** tournament: every pair of strategies plays `GAMES_PER_PAIR` games. To eliminate position bias (Player 0 / Player 1 may have different starting positions), each pair plays an equal number of games with positions swapped.

Win rate is computed as `(wins + 0.5 * draws) / games_played`.

> **Runtime estimate:** With 10 strategies and 4 games/pair, this is 45 pairs × 4 games = **180 games**. Each game takes ~15–30 seconds on Kaggle's CPU environment, so expect **45–90 minutes** total. Set `GAMES_PER_PAIR = 2` for a faster (~25 min) run.

## [CODE]
```python
GAMES_PER_PAIR = 4  # set to 2 for a faster run
GLOBAL_SEED    = 42  # fix this for reproducible results

wins   = defaultdict(int)
draws  = defaultdict(int)
played = defaultdict(int)

strats = NAMED_STRATEGIES
pairs  = list(itertools.combinations(range(len(strats)), 2))
total  = len(pairs) * GAMES_PER_PAIR
done   = 0
t0     = time.time()

print(f'Running {len(strats)}-way round-robin: {total} games total  (seed={GLOBAL_SEED})')

for i, j in pairs:
    sa, sb = strats[i], strats[j]
    half = GAMES_PER_PAIR // 2
    for k in range(half):
        seed = GLOBAL_SEED + i * 1000 + j * 100 + k
        ra, rb = play_match(sa, sb, game_seed=seed)
        played[sa.name] += 1; played[sb.name] += 1
        if ra > rb:   wins[sa.name] += 1
        elif rb > ra: wins[sb.name] += 1
        else:         draws[sa.name] += 1; draws[sb.name] += 1
        done += 1
    for k in range(GAMES_PER_PAIR - half):
        seed = GLOBAL_SEED + i * 1000 + j * 100 + half + k
        rb, ra = play_match(sb, sa, game_seed=seed)   # positions swapped
        played[sa.name] += 1; played[sb.name] += 1
        if ra > rb:   wins[sa.name] += 1
        elif rb > ra: wins[sb.name] += 1
        else:         draws[sa.name] += 1; draws[sb.name] += 1
        done += 1
    eta = (time.time()-t0)/done*(total-done) if done else 0
    print(f'  [{done:>3}/{total}]  {sa.name:>15} vs {sb.name:<15}  ETA {eta:.0f}s')

print('\nTournament complete!')
```

## [CODE]
```python
results = []
for s in strats:
    p  = played[s.name]; w = wins[s.name]; d = draws[s.name]
    wr = (w + 0.5*d) / p if p > 0 else 0.0
    results.append({'strategy': s, 'win_rate': wr, 'wins': w, 'draws': d, 'losses': p-w-d, 'played': p})
results.sort(key=lambda x: -x['win_rate'])
best_strategy = results[0]['strategy']

print(f"{'Strategy':>15}  {'WR':>7}  {'W':>4}  {'D':>4}  {'L':>4}  {'GP':>4}")
print('-' * 52)
for r in results:
    mark = ' ◀ WINNER' if r['strategy'].name == best_strategy.name else ''
    print(f"{r['strategy'].name:>15}  {r['win_rate']:>6.1%}  "
          f"{r['wins']:>4}  {r['draws']:>4}  {r['losses']:>4}  {r['played']:>4}{mark}")

fig, ax = plt.subplots(figsize=(9, 5))
names     = [r['strategy'].name for r in results]
wrs       = [r['win_rate'] for r in results]
bar_colors = ['#2196F3' if n == best_strategy.name else '#90CAF9' for n in names]
bars = ax.barh(names, wrs, color=bar_colors)
ax.set_xlabel('Win Rate')
ax.set_title('Round-Robin Tournament Results (position-balanced)')
ax.axvline(0.5, color='red', lw=1, ls='--', alpha=0.6, label='50% baseline')
ax.legend(fontsize=8)
for bar, wr in zip(bars, wrs):
    ax.text(wr + 0.005, bar.get_y() + bar.get_height()/2,
            f'{wr:.1%}', va='center', fontsize=8)
plt.tight_layout()
plt.show()
```

## [MD]
**How to read these results:**

- A win rate significantly above 50% means that strategy wins *on average* against the pool —
  not that it beats every opponent.
- Win rates close to 50% suggest roughly average performance.
- There can be **non-transitive** results (A beats B, B beats C, but C beats A).
  The round-robin format averages these out.

**Results from this run (seed=42):**

| Rank | Strategy | Win Rate | Key observation |
|------|----------|----------|-----------------|
| 1 | **blitz** | **72.2%** | Fast nearby-first attack with enemy preference dominates — minimum travel time, maximum capture rate |
| 2 | **weakest** | 66.7% | Targeting lightly-defended planets is also strong; both blitz and weakest share the "low friction" philosophy |
| 3 | **balanced** | 65.3% | Multi-objective scoring is competitive when parameters are well-tuned |
| 4= | **richest / expansion** | 58.3% | Production and land-grab strategies are above average |
| 6 | **aggressive** | 50.0% | Hunting enemies directly is average — neutrals are often cheaper |
| 7 | **closest** | 44.4% | Ignoring planet value hurts; nearby but low-production planets waste effort |
| 8 | **smart** | 37.5% | Most complex strategy, below-average result — overfitting to multiple signals |
| 9 | **defensive** | 30.6% | Spending ships on reinforcement instead of expansion is a net loss |
| 10 | **conservative** | 16.7% | 2× attack buffer is fatal — every turn waiting, opponents claim free neutrals |

**Notable findings:**

- **blitz** wins convincingly (72.2%). The key insight: prioritising nearby planets minimises
  travel time and keeps the attack rate high. The enemy bonus ensures it doesn't ignore
  contested territory.
- **defensive** (30.6%) confirms that explicit protection logic is a net loss in this game —
  **tempo beats defence**. Reinforcing a planet costs ships that could have captured a new one.
- **conservative** (16.7%) confirms that hoarding ships is catastrophic. Every turn you wait,
  opponents are claiming free neutral planets and compounding their production lead.
- **smart** (37.5%) underperforms despite the most complex logic — more signals can mean
  more noise when each sub-weight is not carefully tuned.

## [MD]
---
## Part 3 — Parameter Search

The 10 named strategies explored a small, hand-chosen slice of the parameter space. In reality, the best agent likely lives somewhere in the continuous space between these strategies. We use **random search** to explore it.

### Why random search instead of grid search?

With 8 parameters and even 3 values each, a grid search would require 3⁸ = 6,561 evaluations — completely impractical. Random search has been shown empirically to be surprisingly effective because:
1. Not all parameters matter equally. By sampling randomly, we get more coverage of the *important* dimensions.
2. It's trivially parallelizable.
3. With 60 trials, we can still identify the most impactful parameters from the scatter plots.

### Evaluation setup

Each candidate is evaluated against the **tournament winner** from Part 2 (`blitz`) in `EVAL_GAMES` games (position-swapped for fairness). The result is its win rate against that baseline. A candidate that wins >50% of games is potentially better than our current best.

> **Runtime estimate:** 60 trials × 4 games = **240 games**, taking roughly **60–120 minutes** on Kaggle's CPU. Set `N_TRIALS = 20` for a faster (~25 min) exploratory run.

## [CODE]
```python
SEARCH_SPACE = {
    'dist_weight':   (0.0, 4.0),
    'prod_weight':   (0.0, 4.0),
    'weak_weight':   (0.0, 3.0),
    'neutral_bonus': (0.0, 4.0),
    'enemy_bonus':   (0.0, 3.0),
    'attack_buffer': (1.0, 2.5),
    'min_ships':     (1,   20),
    'use_defense':   (False, True),
}

N_TRIALS       = 60   # set lower (e.g. 20) for a quick experiment
EVAL_GAMES     = 4    # games per candidate (2 as P0, 2 as P1)
BASELINE_STRAT = best_strategy

print(f'Search space: {len(SEARCH_SPACE)} parameters')
print(f'Trials: {N_TRIALS}  ×  {EVAL_GAMES} games each  =  {N_TRIALS * EVAL_GAMES} games total')
print(f'Baseline strategy: "{BASELINE_STRAT.name}"')

def sample_strategy(seed: int) -> Strategy:
    """Sample a random strategy using a fixed seed for reproducibility."""
    rng = random.Random(seed)
    return Strategy(
        name          = f'trial_{seed:03d}',
        dist_weight   = round(rng.uniform(*SEARCH_SPACE['dist_weight']),   2),
        prod_weight   = round(rng.uniform(*SEARCH_SPACE['prod_weight']),   2),
        weak_weight   = round(rng.uniform(*SEARCH_SPACE['weak_weight']),   2),
        neutral_bonus = round(rng.uniform(*SEARCH_SPACE['neutral_bonus']), 2),
        enemy_bonus   = round(rng.uniform(*SEARCH_SPACE['enemy_bonus']),   2),
        attack_buffer = round(rng.uniform(*SEARCH_SPACE['attack_buffer']), 2),
        min_ships     = rng.randint(*SEARCH_SPACE['min_ships']),
        use_defense   = rng.choice([False, True]),
    )

def evaluate(candidate: Strategy, baseline: Strategy, n_games: int = EVAL_GAMES,
             base_seed: int = GLOBAL_SEED) -> float:
    """Return win rate of candidate vs. baseline (position-balanced)."""
    w = d = 0
    half = n_games // 2
    for k in range(half):
        ra, rb = play_match(candidate, baseline, game_seed=base_seed + k)
        if ra > rb: w += 1
        elif ra == rb: d += 1
    for k in range(n_games - half):
        rb, ra = play_match(baseline, candidate, game_seed=base_seed + half + k)
        if ra > rb: w += 1
        elif ra == rb: d += 1
    return (w + 0.5 * d) / n_games

print('\nSearch setup complete.')
```

## [CODE]
```python
search_results = []
t0 = time.time()

for trial in range(N_TRIALS):
    cand = sample_strategy(trial)
    wr   = evaluate(cand, BASELINE_STRAT, base_seed=GLOBAL_SEED + trial * 10)
    search_results.append({'strategy': cand, 'win_rate': wr})

    elapsed = time.time() - t0
    eta     = elapsed / (trial+1) * (N_TRIALS - trial - 1)
    # ★ = clearly better than baseline, △ = about even, (space) = worse
    flag = '★' if wr > 0.6 else ('△' if wr >= 0.5 else ' ')
    print(
        f'  [{trial+1:>3}/{N_TRIALS}] {flag} WR={wr:.2f}  ETA {eta:.0f}s  '
        f'dist={cand.dist_weight} prod={cand.prod_weight} '
        f'neut={cand.neutral_bonus} buf={cand.attack_buffer} def={cand.use_defense}'
    )

search_results.sort(key=lambda x: -x['win_rate'])
best_found = search_results[0]['strategy']

n_above_50 = sum(1 for r in search_results if r['win_rate'] > 0.5)
print(f'\nTrials above 50% WR: {n_above_50} / {N_TRIALS}')
print(f'Best candidate: {best_found.name}  WR={search_results[0]["win_rate"]:.2f}')
```

## [MD]
### Visualising the Search Results

For each parameter, we scatter-plot its sampled value (x-axis) against the resulting win
rate (y-axis). **Gold circles highlight the top 5 trials.**

What to look for:
- **A clear upward or downward slope** → this parameter matters and has a preferred direction.
- **A flat cloud of points** → this parameter has little effect (or a non-linear relationship).
- **High-WR points clustered in one region** → that region of parameter space is promising.

**What we observe in this run (baseline = blitz):**
Most points cluster at WR = 0.00–0.25 — only 3 of 60 trials exceeded 0.5 WR,
confirming that `blitz` is a strong and difficult-to-beat baseline.
The `attack_buffer` column shows a mild downward trend: high-buffer (conservative)
strategies tend to be beaten. The `dist_weight` column shows a mild positive trend —
strategies that strongly prefer nearby planets tend to do better against `blitz`,
which itself relies heavily on proximity.

## [CODE]
```python
param_keys = ['dist_weight','prod_weight','weak_weight','neutral_bonus',
              'enemy_bonus','attack_buffer','min_ships']
param_vals  = {k: [getattr(r['strategy'], k) for r in search_results] for k in param_keys}
win_rates   = [r['win_rate'] for r in search_results]

fig, axes = plt.subplots(2, 4, figsize=(16, 7))
axes = axes.ravel()
cmap = plt.cm.RdYlGn
norm = Normalize(vmin=0.0, vmax=1.0)

for ax, key in zip(axes[:7], param_keys):
    vals = param_vals[key]
    ax.scatter(vals, win_rates, c=win_rates, cmap=cmap, norm=norm,
               s=30, alpha=0.75, edgecolors='none')
    top5 = sorted(zip(vals, win_rates), key=lambda x: -x[1])[:5]
    ax.scatter([v for v,_ in top5], [w for _,w in top5],
               s=80, facecolors='none', edgecolors='gold', lw=1.5, zorder=5, label='Top 5')
    # Trend line
    z = np.polyfit(vals, win_rates, 1)
    xr = np.linspace(min(vals), max(vals), 50)
    ax.plot(xr, np.poly1d(z)(xr), 'k--', lw=1, alpha=0.5)
    ax.axhline(0.5, color='gray', lw=0.8, ls=':')
    ax.set_xlabel(key, fontsize=8)
    ax.set_ylabel('Win Rate', fontsize=8)
    ax.set_title(key, fontsize=9)
    ax.legend(fontsize=7)

# use_defense as grouped bar chart
ax = axes[7]
def_vals   = [getattr(r['strategy'], 'use_defense') for r in search_results]
wr_false   = [w for d, w in zip(def_vals, win_rates) if not d]
wr_true    = [w for d, w in zip(def_vals, win_rates) if d]
ax.bar(['No defense\n(n=%d)' % len(wr_false), 'With defense\n(n=%d)' % len(wr_true)],
       [np.mean(wr_false) if wr_false else 0, np.mean(wr_true) if wr_true else 0],
       color=['#90CAF9','#2196F3'], yerr=
           [np.std(wr_false) if wr_false else 0, np.std(wr_true) if wr_true else 0],
       capsize=5)
ax.axhline(0.5, color='gray', lw=0.8, ls=':')
ax.set_ylabel('Mean Win Rate')
ax.set_title('use_defense', fontsize=9)
ax.set_ylim(0, 1)

plt.suptitle(f'Parameter Search — Each dot is one trial  (N={N_TRIALS}, baseline="{BASELINE_STRAT.name}")',
             fontsize=11)
plt.tight_layout()
plt.show()
```

## [MD]
### Parameter Importance (Correlation Analysis)

The scatter plots above are visual — Pearson correlation gives a single-number
summary of how much each parameter matters and in which direction.

- **Strong positive correlation** → higher values of this parameter tend to win more.
- **Strong negative correlation** → lower values tend to win more.
- **Near-zero** → this parameter is unimportant (or has a non-linear effect).

> Pearson only captures *linear* relationships. A parameter could have a sweet-spot
> in the middle and still show low correlation.

**Results from this run (baseline = blitz, seed=42):**

| Parameter | r | Interpretation |
|-----------|---|----------------|
| `weak_weight` | **+0.126** | Strongest signal. Targeting lightly-defended planets helps — consistent with `blitz` and `weakest` both ranking high in the tournament. |
| `prod_weight` | +0.083 | Mild positive effect. Preferring high-production planets is directionally correct but not dominant. |
| `attack_buffer` | −0.044 | Mild negative. Higher buffers (more cautious) tend to lose — tempo matters more than safety margin. |
| `dist_weight`, `min_ships`, `neutral_bonus`, `enemy_bonus` | ≈ 0 | Near-zero correlation across all sampled values. No clear linear signal with this sample size. |

**Key takeaway:** With `blitz` as baseline, the parameter landscape is very flat — most
random configurations score 0.00–0.25 WR. The clearest signal is that **targeting
weak garrisons** (high `weak_weight`) and **attacking quickly** (low `attack_buffer`)
are the most reliable improvements. With only 60 trials and noisy 4-game evaluations,
larger sample sizes would be needed to confirm finer distinctions.

## [CODE]
```python
corrs = {k: np.corrcoef(param_vals[k], win_rates)[0, 1] for k in param_keys}

fig, ax = plt.subplots(figsize=(8, 4))
sorted_corrs = sorted(corrs.items(), key=lambda x: x[1])
names_c = [k for k,_ in sorted_corrs]
vals_c  = [v for _,v in sorted_corrs]
colors_c = ['#2196F3' if v > 0 else '#F44336' for v in vals_c]
bars = ax.barh(names_c, vals_c, color=colors_c)
ax.axvline(0, color='black', lw=0.8)
ax.axvline(+0.2, color='gray', lw=0.8, ls='--', alpha=0.5)
ax.axvline(-0.2, color='gray', lw=0.8, ls='--', alpha=0.5)
ax.set_xlabel('Pearson correlation with win rate')
ax.set_title('Parameter Importance\n(dashed lines = ±0.2 threshold)')
for bar, v in zip(bars, vals_c):
    ax.text(v + (0.005 if v >= 0 else -0.005),
            bar.get_y() + bar.get_height()/2,
            f'{v:+.3f}', va='center', ha='left' if v >= 0 else 'right', fontsize=8)
plt.tight_layout()
plt.show()

print('Correlation summary (sorted by |r|):')
for k, v in sorted(corrs.items(), key=lambda x: -abs(x[1])):
    direction = '↑ higher is better' if v > 0.1 else ('↓ lower is better' if v < -0.1 else '→ unclear')
    print(f'  {k:<20} r={v:+.3f}  {direction}')
```

## [CODE]
```python
# ── Top 10 candidates ─────────────────────────────────────────────────────────
print('Top 10 configurations from random search:\n')
print(f"{'Name':>12} {'WR':>6}  "
      f"{'dist':>5} {'prod':>5} {'weak':>5} {'neut':>5} {'enmy':>5} "
      f"{'buf':>5} {'min':>4} {'def':>5}")
print('-' * 82)
for r in search_results[:10]:
    s = r['strategy']
    print(f"{s.name:>12} {r['win_rate']:>6.2f}  "
          f"{s.dist_weight:>5.2f} {s.prod_weight:>5.2f} {s.weak_weight:>5.2f} "
          f"{s.neutral_bonus:>5.2f} {s.enemy_bonus:>5.2f} "
          f"{s.attack_buffer:>5.2f} {s.min_ships:>4d} {str(s.use_defense):>5}")
```

## [MD]
**Reading the top-10 table:**

- `trial_047` is the top outlier at WR=1.00, winning all 4 evaluation games against `blitz`.
  Its parameters: moderate `dist_weight` (1.41), moderate `prod_weight` (1.72), moderate
  `weak_weight` (1.36), balanced bonuses, `attack_buffer` (1.59), and `use_defense=True`.
  A perfect 4-game score is suspicious — with such a small sample, this is likely map-luck.
- Two trials (`trial_001`, `trial_038`) scored WR=0.75. Both share `def=False` and
  moderate `dist_weight`, suggesting that avoiding defensive overhead helps.
- All other successful trials scored exactly 0.50 (2 wins, 2 losses against `blitz`).
  This flat distribution confirms the parameter landscape around `blitz` is very competitive
  — it is hard to reliably beat a strategy that already plays aggressively nearby.
- **Important caveat:** 4 games is a very small sample. A WR=1.00 from 4 games has a
  very wide confidence interval — it could easily be 0.50 with a larger sample. The final
  validation step in Part 4 tests this hypothesis.

## [MD]
---
## Part 4 — Final Validation & Export

The best candidate from random search (`trial_047`, WR=1.00) was chosen based on only
4 games against one specific baseline (`blitz`). Before trusting it:

1. **Validate against all 10 named strategies** — not just `blitz`. A candidate that
   happens to beat `blitz` on a particular map may be fragile against other play styles.
2. **Write the winning parameters to `main.py`** — the competition submission file.

If the best-found candidate's overall WR across all named strategies is < 50%, we fall
back to the tournament winner (`blitz`) instead.

> **Spoiler from this run:** `trial_047` collapses in broad validation (overall WR = 0.23).
> It beats only `closest`, `conservative`, and `defensive` — the slower strategies —
> while losing badly to every fast strategy including `blitz` itself (WR = 0.00).
> This confirms the 4-game perfect score was noise. The fallback to `blitz` is triggered.

## [CODE]
```python
print(f'Validating "{best_found.name}" against all 10 named strategies (4 games each)...\n')
print(f'Candidate parameters:')
for f_name in ['dist_weight','prod_weight','weak_weight','neutral_bonus',
               'enemy_bonus','attack_buffer','min_ships','use_defense']:
    print(f'  {f_name:<20} = {getattr(best_found, f_name)}')
print()

validation = []
for s in NAMED_STRATEGIES:
    wr = evaluate(best_found, s, n_games=4)
    validation.append({'vs': s.name, 'win_rate': wr})
    icon = '✓' if wr >= 0.5 else '✗'
    print(f'  {icon} vs {s.name:<15}  WR = {wr:.2f}')

overall_wr = np.mean([r['win_rate'] for r in validation])
wins_above = sum(1 for r in validation if r['win_rate'] >= 0.5)
print(f'\nOverall WR vs all named strategies: {overall_wr:.2f}')
print(f'Beats or ties: {wins_above} / {len(NAMED_STRATEGIES)} strategies')

# Decide whether to use best_found or fall back to tournament winner
final_strategy = best_found if overall_wr >= 0.5 else best_strategy
print(f'\n→ Using: "{final_strategy.name}"' +
      (' (random search winner)' if final_strategy is best_found else ' (tournament winner — search did not improve)'))

fig, ax = plt.subplots(figsize=(9, 4))
vs_names = [r['vs'] for r in validation]
vs_wrs   = [r['win_rate'] for r in validation]
ax.bar(vs_names, vs_wrs, color=['#4CAF50' if w >= 0.5 else '#F44336' for w in vs_wrs])
ax.axhline(0.5, color='black', lw=1, ls='--')
ax.set_ylim(0, 1)
ax.set_ylabel('Win Rate')
ax.set_title(f'Final validation: "{best_found.name}" vs. each named strategy')
ax.tick_params(axis='x', rotation=30)
ax.axhline(overall_wr, color='blue', lw=1.5, ls=':', label=f'Mean WR = {overall_wr:.2f}')
ax.legend(fontsize=9)
plt.tight_layout()
plt.show()
```

## [CODE]
```python
%%writefile main.py
import math
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet, Fleet

# BEGIN_STRATEGY
STRATEGY = {
    "dist_weight":   1.0,
    "prod_weight":   1.0,
    "weak_weight":   1.0,
    "neutral_bonus": 1.0,
    "enemy_bonus":   1.0,
    "attack_buffer": 1,
    "min_ships":     10,
    "use_defense":   False,
}
# END_STRATEGY

# ── Physics constants ────────────────────────────────────────────────────────
SUN_X, SUN_Y, SUN_R = 50.0, 50.0, 10.0
MAX_SPEED  = 6.0
MAX_DIAG   = 141.421
MAX_SHIPS  = 500.0
WAIT_TURNS = 2

def fleet_speed(ships):
    if ships <= 1:
        return 1.0
    return 1.0 + 5.0 * (math.log(ships) / math.log(1000)) ** 1.5

def _seg_hits_sun(x1, y1, x2, y2, margin=2.0):
    dx, dy = x2-x1, y2-y1
    fx, fy = x1-SUN_X, y1-SUN_Y
    a = dx*dx + dy*dy
    if a == 0: return False
    b = 2*(fx*dx + fy*dy)
    c = fx*fx + fy*fy - (SUN_R + margin)**2
    disc = b*b - 4*a*c
    if disc < 0: return False
    sq = math.sqrt(disc)
    t1, t2 = (-b-sq)/(2*a), (-b+sq)/(2*a)
    return (0 <= t1 <= 1) or (0 <= t2 <= 1)

def _capture_cost(sx, sy, tgt):
    dist = math.hypot(sx - tgt.x, sy - tgt.y)
    ships = tgt.ships + 1
    for _ in range(8):
        turns = dist / fleet_speed(ships)
        ships = int(tgt.ships + tgt.production * turns) + 1
    return ships

def _detect_threats(my_planets, fleets, player):
    threats = {}
    for f in fleets:
        if f.owner == player or f.owner < 0:
            continue
        fdx, fdy = math.cos(f.angle), math.sin(f.angle)
        for p in my_planets:
            to_px, to_py = p.x - f.x, p.y - f.y
            dot = fdx*to_px + fdy*to_py
            if dot <= 0: continue
            if abs(fdx*to_py - fdy*to_px) > p.radius + 3: continue
            turns = dot / fleet_speed(f.ships)
            if p.id not in threats:
                threats[p.id] = [0, float('inf')]
            threats[p.id][0] += f.ships
            threats[p.id][1] = min(threats[p.id][1], turns)
    return {pid: tuple(v) for pid, v in threats.items()}

def make_fresh_agent():
    """Return a fresh agent instance (resets turn counter)."""
    s_dict = STRATEGY
    tc = [0]

    def _agent(obs):
        tc[0] += 1
        if tc[0] <= WAIT_TURNS:
            return []

        player  = obs.get('player', 0)   if isinstance(obs, dict) else obs.player
        raw_p   = obs.get('planets', []) if isinstance(obs, dict) else obs.planets
        raw_f   = obs.get('fleets', [])  if isinstance(obs, dict) else obs.fleets
        planets = [Planet(*p) for p in raw_p]
        fleets  = [Fleet(*f)  for f in (raw_f or [])]
        my_pl   = [p for p in planets if p.owner == player]
        targets = [p for p in planets if p.owner != player]

        if not my_pl:
            return []

        avail = {p.id: p.ships for p in my_pl}
        moves = []

        if s_dict["use_defense"]:
            pby_id = {p.id: p for p in planets}
            for pid, (inc, turns) in sorted(
                    _detect_threats(my_pl, fleets, player).items(),
                    key=lambda x: x[1][1]):
                pl = pby_id.get(pid)
                if pl is None: continue
                deficit = inc - (pl.ships + int(pl.production * turns)) + 1
                if deficit <= 0: continue
                for h in sorted([p for p in my_pl if p.id != pid and avail[p.id] > 10],
                                 key=lambda p: math.hypot(p.x - pl.x, p.y - pl.y)):
                    if deficit <= 0: break
                    if _seg_hits_sun(h.x, h.y, pl.x, pl.y): continue
                    send = min(avail[h.id] - 5, deficit)
                    if send <= 0: continue
                    moves.append([h.id, math.atan2(pl.y - h.y, pl.x - h.x), send])
                    avail[h.id] -= send
                    deficit -= send

        if not targets:
            return moves

        targeted = set()
        for src in sorted(my_pl, key=lambda p: -avail[p.id]):
            if avail[src.id] < s_dict["min_ships"]:
                continue
            scored = []
            for tgt in targets:
                if tgt.id in targeted or _seg_hits_sun(src.x, src.y, tgt.x, tgt.y):
                    continue
                dist = math.hypot(src.x - tgt.x, src.y - tgt.y)
                is_n = float(tgt.owner == -1)
                is_e = float(tgt.owner not in (-1, player) and tgt.owner >= 0)
                score = (
                    -s_dict["dist_weight"]   * (dist / MAX_DIAG)
                    + s_dict["prod_weight"]  * (tgt.production / 5.0)
                    - s_dict["weak_weight"]  * (min(tgt.ships, MAX_SHIPS) / MAX_SHIPS)
                    + s_dict["neutral_bonus"] * is_n
                    + s_dict["enemy_bonus"]   * is_e
                )
                scored.append((tgt, score))
            if not scored:
                if avail[src.id] > 15:
                    frn = [p for p in my_pl if p.id != src.id]
                    if frn:
                        dst = min(frn, key=lambda p: math.hypot(p.x-src.x, p.y-src.y))
                        if not _seg_hits_sun(src.x, src.y, dst.x, dst.y):
                            send = avail[src.id] // 2
                            moves.append([src.id, math.atan2(dst.y-src.y, dst.x-src.x), send])
                            avail[src.id] -= send
                continue
            tgt, _ = max(scored, key=lambda x: x[1])
            needed = int(_capture_cost(src.x, src.y, tgt) * s_dict["attack_buffer"])
            if avail[src.id] >= needed > 0:
                moves.append([src.id, math.atan2(tgt.y-src.y, tgt.x-src.x), needed])
                avail[src.id] -= needed
                targeted.add(tgt.id)
            elif avail[src.id] > 15:
                frn = [p for p in my_pl if p.id != src.id]
                if frn:
                    dst = min(frn, key=lambda p: math.hypot(p.x-src.x, p.y-src.y))
                    if not _seg_hits_sun(src.x, src.y, dst.x, dst.y):
                        send = avail[src.id] // 2
                        moves.append([src.id, math.atan2(dst.y-src.y, dst.x-src.x), send])
                        avail[src.id] -= send
        return moves

    return _agent

# Kaggle submission entrypoint
_agent_instance = make_fresh_agent()

def agent(obs):
    return _agent_instance(obs)
```

## [CODE]
```python
# ── Write winning params to main.py ──────────────────────────────────────────
# main.py has a BEGIN_STRATEGY / END_STRATEGY block.
# We replace it with the winning parameters found in Part 3.
# The agent inside main.py reads from STRATEGY dict at runtime.
MAIN_PY = 'main.py'
s = final_strategy

new_block = (
    '# BEGIN_STRATEGY\n'
    f'STRATEGY = {{\n'
    f'    "dist_weight":   {s.dist_weight},\n'
    f'    "prod_weight":   {s.prod_weight},\n'
    f'    "weak_weight":   {s.weak_weight},\n'
    f'    "neutral_bonus": {s.neutral_bonus},\n'
    f'    "enemy_bonus":   {s.enemy_bonus},\n'
    f'    "attack_buffer": {s.attack_buffer},\n'
    f'    "min_ships":     {s.min_ships},\n'
    f'    "use_defense":   {s.use_defense},\n'
    f'}}\n'
    '# END_STRATEGY'
)

with open(MAIN_PY) as f:
    src = f.read()

updated = re.sub(
    r'# BEGIN_STRATEGY.*?# END_STRATEGY',
    new_block, src, flags=re.DOTALL,
)

with open(MAIN_PY, 'w') as f:
    f.write(updated)

print(f'Written to {MAIN_PY}:')
print(new_block)
```

## [MD]
**What just happened:**

The `BEGIN_STRATEGY` / `END_STRATEGY` block in `main.py` was replaced with the winning
parameters from the tournament. The agent reads from this `STRATEGY` dict at runtime.

**Parameters written in this run (`blitz` strategy — tournament winner with WR=72.2%):**
```python
STRATEGY = {
    "dist_weight":   3.0,   # strong preference for nearby planets
    "prod_weight":   0.5,   # mild production bonus
    "weak_weight":   0.0,   # no preference for lightly-defended planets
    "neutral_bonus": 0.0,   # no preference for neutrals vs enemies
    "enemy_bonus":   1.0,   # prefers attacking enemy planets over neutrals
    "attack_buffer": 1.0,   # sends exactly the minimum ships needed
    "min_ships":     1,     # attacks from any planet regardless of size
    "use_defense":   False, # no defensive reinforcement
}
```

The `main.py` architecture:
```
agent(obs)
  └─ make_fresh_agent()     ← creates a stateful agent with its own turn counter
       └─ _defense_moves()  ← reinforce threatened planets (skipped: use_defense=False)
       └─ _attack_pass()    ← scores all (src, tgt) pairs, attacks the best one
            └─ _capture_cost()   ← iterative estimate accounting for travel time
            └─ _seg_hits_sun()   ← avoids routing fleets through the sun
```

> **Why `blitz` and not the random search winner?**
> `trial_047` scored WR=1.00 in 4 games against a single baseline, but only WR=0.23
> when validated against all 10 named strategies — a clear sign of overfitting to noise.
> `blitz` won the full 180-game round-robin and proved more robust.

## [CODE]
```python
# Quick sanity check: reimport main.py and run one game against 'random'
import importlib, sys

if 'main' in sys.modules:
    importlib.reload(sys.modules['main'])
import main as main_mod

print(f'STRATEGY loaded from main.py: {main_mod.STRATEGY}\n')

results_sanity = []
for _ in range(4):
    env = make('orbit_wars', debug=False)
    env.run([main_mod.make_fresh_agent(), 'random'])
    r = env.steps[-1][0].reward
    results_sanity.append(r)
    print(f'  Game result vs random: reward={r}')

wins_vs_random = sum(1 for r in results_sanity if r == 1)
print(f'\nRecord vs random: {wins_vs_random} / {len(results_sanity)} wins')
print('\nmain.py is ready to submit!')
```

## [MD]
---
## Summary & Next Steps

### What this notebook found

- **Fleet speed** grows logarithmically — accumulate ships before long-range attacks.
- **Capture cost** must account for travel time — the naive `garrison + 1` estimate is always too low.
- **Orbital planets** drift significantly over the course of a game — aiming at current position wastes many fleets.
- The **parameter search** identified which weighting dimensions matter most for the scoring function.

### Suggested improvements to explore next

| Idea | Expected impact |
|------|-----------------|
| **Orbital planet position prediction** — aim at predicted future position instead of current | High |
| **Comet targeting** — comets are free production; capturing them early is pure upside | Medium |
| **Multi-agent tournament** (4-player) — the dynamics are very different from 2-player | Medium |
| **Bayesian optimisation** (e.g. with Optuna) instead of random search | Medium |
| **REINFORCE / PPO self-play** — a learned policy can express complex conditional strategies | High (but slow) |

Good luck! 🚀
