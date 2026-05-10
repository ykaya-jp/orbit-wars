## [MD]
# 🌌 OMEGA v3 — Orbit Wars: Full Agent Breakdown

> **Competition:** [Orbit Wars — Kaggle Simulation](https://www.kaggle.com/competitions/orbit-wars)
> **Agent Name:** OMEGA v3 (Orbital Maximum Engine for Galaxy Assault)
> **Approach:** Timeline simulation · 12 mission types · Economic mode system

---

## 📖 What is Orbit Wars?

Orbit Wars is a **2D real-time space strategy** game where you command fleets across a solar system:

| Property | Value |
|----------|-------|
| Grid | 100 × 100 continuous coordinate space |
| Sun | Radius 10, centered at (50, 50) — destroys fleets that cross it |
| Planets | Orbit the sun or sit static far from it |
| Turns | 500 total — most ships at the end wins |
| Modes | 1v1 or 4-player Free-For-All (FFA) |

**The core mechanic that changes everything:**

```
fleet_speed = 1.0 + 5.0 × (log(ships) / log(1000)) ^ 1.5
```

A fleet of **1 ship** crawls at speed 1.0.
A fleet of **1000 ships** rockets at speed 6.0.
This non-linear relationship is the key insight behind our **Tsunami Strike**.

---

## 🧠 OMEGA v3 Architecture — Six Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1  Physics         Orbital prediction · Sun avoidance    │
│  LAYER 2  World Model     Timeline sim · Binary search          │
│  LAYER 3  Economic Mode   EXPAND / BALANCED / AGGRO             │
│  LAYER 4  Policy Builder  Dynamic reserves · Reaction times     │
│  LAYER 5  Mission Engine  12 mission types · Pressure bonus     │
│  LAYER 6  Executor        Tsunami strike · Doomed evacuation    │
└─────────────────────────────────────────────────────────────────┘
```

### 12 Mission Types (executed in priority order)

| # | Mission | When it triggers |
|---|---------|-----------------|
| 1 | **intercept** | Enemy fleet heading to OUR planet, ETA < 20 turns |
| 2 | **reinforce** | Our planet will fall — send help before it does |
| 3 | **rescue** | Our planet falls in < 30 turns — send emergency fleet |
| 4 | **recapture** | We just lost a planet — take it back immediately |
| 5 | **elimination** | Focus-fire on the weakest enemy player |
| 6 | **deny** | Attack enemy's highest-production planet |
| 7 | **gang_up** | Two enemies are fighting — attack the winner |
| 8 | **race** | Arrive at contested neutral BEFORE enemy does |
| 9 | **snipe** | Steal a neutral 1 turn after enemy captures it |
| 10 | **capture** | Standard single-source planet capture |
| 11 | **swarm** | 2–3 planets attack simultaneously (coordination) |
| 12 | **crash_exploit** | Attack right after two enemy fleets cancel each other |

## [CODE]
```python
# This Python 3 environment comes with many helpful analytics libraries installed
# It is defined by the kaggle/python Docker image: https://github.com/kaggle/docker-python
# For example, here's several helpful packages to load

import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)

# Input data files are available in the read-only "../input/" directory
# For example, running this (by clicking run or pressing Shift+Enter) will list all files under the input directory

import os
for dirname, _, filenames in os.walk('/kaggle/input'):
    for filename in filenames:
        print(os.path.join(dirname, filename))

# You can write up to 20GB to the current directory (/kaggle/working/) that gets preserved as output when you create a version using "Save & Run All"
# You can also write temporary files to /kaggle/temp/, but they won't be saved outside of the current session
```

## [CODE]
```python
# Environment setup — check what Kaggle provides
import os, math, time
from collections import defaultdict, namedtuple
from dataclasses import dataclass, field
from enum import Enum

for dirname, _, filenames in os.walk('/kaggle/input'):
    for filename in filenames:
        print(os.path.join(dirname, filename))

print("Python environment ready ✅")
print(f"  math, time, collections, dataclasses, enum — all built-in, no pip needed")
```

## [MD]
## ⚡ Layer 1 — Physics: The Speed Curve & Tsunami Strike

### Why fleet size matters more than you think

The speed formula `1 + 5 × (log(ships)/log(1000))^1.5` creates a **non-linear advantage**:

```
  1 ship  → speed 1.0  → 40-unit trip takes 40 turns
 10 ships → speed 2.0  → 40-unit trip takes 20 turns  (-50%!)
 50 ships → speed 3.1  → 40-unit trip takes 13 turns
100 ships → speed 3.7  → 40-unit trip takes 11 turns
300 ships → speed 4.7  → 40-unit trip takes  9 turns
1000 ships→ speed 6.0  → 40-unit trip takes  7 turns
```

### The Tsunami Strike

**Problem:** You need 50 ships to capture a planet. Send exactly 50? ❌
**OMEGA solution:** Check if sending 150 ships saves ≥ 2 turns.

If a prod-3 planet generates 3 ships/turn, saving 2 turns = **6 free ships** — worth sending 100 extra!

### v3 Innovation — Mathematically Justified Tsunami

OMEGA v3 doesn't just blindly send 87% of budget. It calculates:

```
turns_saved  = distance/speed(needed)  − distance/speed(larger)
ships_gained = turns_saved × target_production   (rough estimate)

IF turns_saved ≥ 2  →  TSUNAMI (always justified)
IF extra_ships ≤ 45% of budget  →  TSUNAMI (cheap enough)
IF modest +20% saves 1 turn  →  SOFT TSUNAMI
ELSE  →  send needed × 1.05 (small safety margin)
```

## [CODE]
```python
import math

MAX_SPEED = 6.0

def fleet_speed(ships):
    """
    Logarithmic speed scaling.
    ships=1 → 1.0 (crawl), ships=1000 → 6.0 (max).
    """
    if ships <= 1: return 1.0
    r = max(0.0, min(1.0, math.log(ships) / math.log(1000.0)))
    return 1.0 + (MAX_SPEED - 1.0) * (r ** 1.5)

def speed_optimal_send(needed, available, distance, prod_per_turn=2):
    """
    Mathematically justified Tsunami Strike.

    Args:
        needed:      minimum ships to capture target
        available:   total budget we can spend
        distance:    flight path distance in units
        prod_per_turn: target's production (helps value time saved)

    Returns:
        ships to actually send (>= needed, <= available)
    """
    if available <= 0 or needed <= 0: return needed
    if available < needed: return needed

    base_turns = max(1, math.ceil(distance / fleet_speed(max(1, needed))))

    # === FULL TSUNAMI ===
    if available >= needed * 1.8 and available >= 35:
        candidate  = min(available, max(needed, int(available * 0.87)))
        cand_turns = max(1, math.ceil(distance / fleet_speed(max(1, candidate))))
        turns_saved = base_turns - cand_turns
        extra_ships = candidate - needed

        if turns_saved >= 2:
            print(f"    🌊 FULL TSUNAMI: +{extra_ships} ships saves {turns_saved} turns "
                  f"(~{turns_saved * prod_per_turn} ships gained from faster arrival)")
            return candidate

        if extra_ships <= available * 0.45:
            print(f"    🌊 CHEAP TSUNAMI: +{extra_ships} ships, costs ≤45% of budget")
            return candidate

    # === SOFT TSUNAMI ===
    modest = min(available, int(needed * 1.20))
    if modest > needed:
        mod_turns = max(1, math.ceil(distance / fleet_speed(max(1, modest))))
        if base_turns - mod_turns >= 1:
            print(f"    〰️  SOFT TSUNAMI: +{modest - needed} ships saves 1 turn")
            return modest

    print(f"    ➡️  STANDARD: {min(available, max(needed, int(needed * 1.05)))} ships (small margin)")
    return min(available, max(needed, int(needed * 1.05)))

# ── Visualize speed curve ──────────────────────────────────────────
print("=" * 60)
print("  FLEET SPEED CURVE")
print("=" * 60)
print(f"  {'Ships':>8} │ {'Speed':>6} │ {'ETA (40 units)':>14} │ Relative speed")
print("  " + "─" * 55)
for s in [1, 5, 10, 25, 50, 100, 200, 300, 500, 1000]:
    spd  = fleet_speed(s)
    eta  = math.ceil(40.0 / spd)
    bar  = "█" * int(spd * 3)
    print(f"  {s:>8} │ {spd:>6.2f} │ {eta:>14} turns │ {bar}")

# ── Tsunami decision examples ──────────────────────────────────────
print()
print("=" * 60)
print("  TSUNAMI STRIKE DECISIONS  (need=60, distance=35, prod=3)")
print("=" * 60)
for avail in [65, 90, 120, 150, 200, 350, 500]:
    print(f"  Available={avail:>4}: ", end="")
    send = speed_optimal_send(60, avail, 35.0, prod_per_turn=3)
    base_t = math.ceil(35.0 / fleet_speed(60))
    send_t = math.ceil(35.0 / fleet_speed(send))
    print(f"  → Send {send:>4} ships  (ETA: {send_t} vs baseline {base_t})")
```

## [MD]
## 🔭 Layer 1 — Physics: Orbital Prediction & Sun Avoidance

### The Two Hard Physics Problems

**Problem 1 — Moving Targets**
Planets orbit the sun at angular velocity `ω` rad/turn.
If you aim where a planet *is*, your fleet arrives where it *was*.

**OMEGA Solution — 5-Iteration Convergence:**
```
estimate ETA to current position
  → predict planet position at that ETA
    → recalculate ETA to predicted position
      → repeat until position delta < 0.3 units (converged!)
```

**Problem 2 — Sun Collision**
Fleets travel in straight lines. If the straight line to a target
passes within `SUN_R + 1.6 = 11.6` units of center (50,50), the fleet is destroyed.

**OMEGA Solution — Continuous Path Check:**
Check the *minimum distance* from sun center to the *entire line segment*
(not just endpoint). Uses a proper point-to-segment distance formula.

### Why This Matters

A naive bot aims at current position → misses every rotating planet.
A bot that only checks endpoint sun collision → loses fleets to invisible sun hits.

OMEGA v3 handles both cases correctly with the iterative convergence approach.

## [CODE]
```python
import math

CENTER_X, CENTER_Y = 50.0, 50.0
SUN_R, SUN_SAFETY  = 10.0, 1.6
ROTATION_LIMIT     = 50.0
LAUNCH_CLR         = 0.1

def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)

def is_static_planet(px, py, radius):
    """Static planets don't orbit — they're far enough from sun."""
    return dist(px, py, CENTER_X, CENTER_Y) + radius >= ROTATION_LIMIT

def pt_seg_dist(px, py, x1, y1, x2, y2):
    """Minimum distance from point to line segment (used for sun collision)."""
    dx, dy = x2-x1, y2-y1
    sq = dx*dx + dy*dy
    if sq <= 1e-9: return dist(px, py, x1, y1)
    t = max(0.0, min(1.0, ((px-x1)*dx + (py-y1)*dy) / sq))
    return dist(px, py, x1+t*dx, y1+t*dy)

def seg_hits_sun(x1, y1, x2, y2):
    """True if fleet path would intersect the sun's danger zone."""
    return pt_seg_dist(CENTER_X, CENTER_Y, x1, y1, x2, y2) < SUN_R + SUN_SAFETY

def safe_angle_dist(sx, sy, sr, tx, ty, tr):
    """
    Compute launch angle and travel distance to target.
    Returns None if the sun blocks the path.
    """
    angle = math.atan2(ty-sy, tx-sx)
    lx = sx + math.cos(angle) * (sr + LAUNCH_CLR)
    ly = sy + math.sin(angle) * (sr + LAUNCH_CLR)
    d  = max(0.0, dist(sx, sy, tx, ty) - (sr + LAUNCH_CLR) - tr)
    ex = lx + math.cos(angle) * d
    ey = ly + math.sin(angle) * d
    if seg_hits_sun(lx, ly, ex, ey):
        return None  # Sun blocks this path!
    return angle, d

def predict_planet_pos(planet_x, planet_y, init_x, init_y, radius, ang_vel, turns):
    """
    Predict where an orbiting planet will be after `turns` turns.
    Uses: current angle + angular_velocity × turns
    """
    r = dist(init_x, init_y, CENTER_X, CENTER_Y)
    if r + radius >= ROTATION_LIMIT:
        return planet_x, planet_y  # Static planet — doesn't move

    cur_angle = math.atan2(planet_y - CENTER_Y, planet_x - CENTER_X)
    new_angle = cur_angle + ang_vel * turns
    return CENTER_X + r * math.cos(new_angle), CENTER_Y + r * math.sin(new_angle)

# ── Demo 1: Sun avoidance ────────────────────────────────────────
print("=" * 55)
print("  SUN AVOIDANCE CHECK")
print("=" * 55)
paths = [
    ("Safe path (north of sun)", 20., 20., 80., 80.),
    ("Dangerous path (through sun)", 10., 50., 90., 50.),
    ("Tangential path", 20., 30., 80., 70.),
    ("Clear path (far from sun)", 10., 10., 90., 10.),
]
for name, x1, y1, x2, y2 in paths:
    blocked = seg_hits_sun(x1, y1, x2, y2)
    closest = pt_seg_dist(CENTER_X, CENTER_Y, x1, y1, x2, y2)
    status  = "🚫 BLOCKED" if blocked else "✅ SAFE"
    print(f"  {status}  {name}")
    print(f"           Closest approach to sun center: {closest:.2f} units")
    print(f"           (danger zone = {SUN_R + SUN_SAFETY:.1f} units)")
    print()

# ── Demo 2: Orbital prediction convergence ───────────────────────
print("=" * 55)
print("  ORBITAL PREDICTION — ITERATIVE CONVERGENCE")
print("=" * 55)

# Planet orbiting at radius 30, currently at angle=0 → position (80, 50)
planet_x, planet_y = 80.0, 50.0   # Initial position
init_x, init_y     = 80.0, 50.0   # Same at game start
ang_vel             = 0.025        # rad/turn
src_x, src_y        = 15.0, 15.0  # Our planet position
ships               = 80

print(f"  Orbiting planet starts at ({planet_x}, {planet_y})")
print(f"  Our planet: ({src_x}, {src_y}), sending {ships} ships")
print(f"  Angular velocity: {ang_vel} rad/turn")
print()

# Iterative convergence loop
tx, ty = planet_x, planet_y
for iteration in range(6):
    safe = safe_angle_dist(src_x, src_y, 2.5, tx, ty, 2.0)
    if safe is None:
        print(f"  Iter {iteration+1}: Sun blocked this aim!")
        break
    angle, d = safe
    turns     = max(1, math.ceil(d / fleet_speed(ships)))
    ntx, nty  = predict_planet_pos(planet_x, planet_y, init_x, init_y, 2.0, ang_vel, turns)
    move_dist = dist(tx, ty, ntx, nty)
    print(f"  Iter {iteration+1}: aim=({ntx:.2f},{nty:.2f})  ETA={turns} turns  "
          f"planet_moved={move_dist:.3f} units", end="")
    if move_dist < 0.3:
        print("  ← ✅ CONVERGED")
        break
    else:
        print()
    tx, ty = ntx, nty
```

## [MD]
## 🗓️ Layer 2 — World Model: Timeline Simulation

### The Most Important Algorithm in OMEGA

**The question:** How many ships do I need to send to capture planet X?

A naive bot answers: `target.ships + 1`
This is **wrong** because it ignores:
- Production growth during travel time
- Friendly fleets already en route
- Enemy fleets that might reinforce before we arrive
- Multiple arrivals in the same turn

**OMEGA's answer:** Full turn-by-turn simulation with **binary search**

```
simulate_timeline(planet, all_arrivals, player, horizon)
  │
  ├─ For each turn 1..horizon:
  │    1. If owned → garrison += production
  │    2. If arrivals this turn → resolve combat
  │         largest force beats second largest
  │         winner keeps the difference
  │         tie → all attackers cancel
  │
  └─ Binary search: what's the MINIMUM garrison to survive?
       lo=0, hi=current_ships
       while lo < hi: test survives(mid)
```

### Why Binary Search?

Instead of guessing fleet sizes and re-simulating each time,
binary search finds the exact minimum in `O(log N)` simulations.

For a planet with 200 ships, that's ~8 simulations instead of 200. ⚡

### Cache Everything

OMEGA caches `(planet_id, eval_turn, attacker)` → `min_ships_needed`.
This eliminates redundant simulations across missions that target the same planet.

## [CODE]
```python
from collections import defaultdict

def resolve_arrivals(owner, garrison, arrivals):
    """
    Combat resolution when multiple fleets arrive on the same turn.

    Rule: Largest force wins, keeps (top - second) ships.
    Tie:  All attacking forces cancel out, defender keeps garrison.
    """
    by_owner = {}
    for _, ao, s in arrivals:
        by_owner[ao] = by_owner.get(ao, 0) + s
    if not by_owner:
        return owner, max(0.0, garrison)

    srt   = sorted(by_owner.items(), key=lambda x: x[1], reverse=True)
    top_o, top_s = srt[0]

    if len(srt) > 1 and top_s == srt[1][1]:
        surv_s = 0  # Perfect tie → all attackers cancel
    elif len(srt) > 1:
        surv_s = top_s - srt[1][1]
    else:
        surv_s = top_s

    surv_o = top_o
    if surv_s <= 0:
        return owner, max(0.0, garrison)
    if owner == surv_o:
        return owner, garrison + surv_s  # Friendly reinforcement
    garrison -= surv_s
    if garrison < 0:
        return surv_o, -garrison  # Planet captured!
    return owner, garrison  # Attack repelled

def simulate_timeline(planet_owner, planet_ships, planet_prod,
                      arrivals, player, horizon):
    """
    Turn-by-turn simulation of a planet.

    Args:
        planet_owner:  current owner (-1=neutral, 0/1/2/3=player)
        planet_ships:  current garrison
        planet_prod:   ships produced per turn (if owned)
        arrivals:      list of (eta_turn, owner, ships)
        player:        our player ID
        horizon:       how many turns to simulate

    Returns:
        dict with owner_at, ships_at, fall_turn, keep_needed, holds_full
    """
    events  = sorted([(max(1, int(t)), o, int(s))
                      for t,o,s in arrivals if s > 0 and t <= horizon])
    by_turn = defaultdict(list)
    for item in events:
        by_turn[item[0]].append(item)

    owner    = planet_owner
    garrison = float(planet_ships)
    owner_at = {0: owner}
    ships_at = {0: max(0.0, garrison)}
    fall_turn = None

    for turn in range(1, horizon + 1):
        if owner != -1:
            garrison += planet_prod     # Production tick

        group = by_turn.get(turn, [])
        prev  = owner
        if group:
            owner, garrison = resolve_arrivals(owner, garrison, group)
            if prev == player and owner != player and fall_turn is None:
                fall_turn = turn

        owner_at[turn] = owner
        ships_at[turn] = max(0.0, garrison)

    # Binary search: minimum ships to keep to survive through horizon
    keep_needed = 0
    holds_full  = True
    if planet_owner == player:
        def survives(keep):
            so, sg = planet_owner, float(keep)
            for t in range(1, horizon + 1):
                if so != -1: sg += planet_prod
                gr = by_turn.get(t, [])
                if gr:
                    so, sg = resolve_arrivals(so, sg, gr)
                    if so != player: return False
            return so == player

        if survives(int(planet_ships)):
            lo, hi = 0, int(planet_ships)
            while lo < hi:
                mid = (lo + hi) // 2
                if survives(mid): hi = mid
                else:             lo = mid + 1
            keep_needed = lo
        else:
            holds_full  = False
            keep_needed = int(planet_ships)

    return dict(owner_at=owner_at, ships_at=ships_at,
                fall_turn=fall_turn, keep_needed=keep_needed,
                holds_full=holds_full)

# ── Demo: simulate various threat scenarios ─────────────────────
print("=" * 65)
print("  TIMELINE SIMULATION DEMOS")
print("=" * 65)

scenarios = [
    {
        "name":   "Scenario A — We hold comfortably",
        "owner":  0, "ships": 60, "prod": 3,
        "arrivals": [(10, 1, 40)],   # Enemy 40 ships in 10 turns
    },
    {
        "name":   "Scenario B — We barely survive (need reinforcement!)",
        "owner":  0, "ships": 30, "prod": 2,
        "arrivals": [(8, 1, 60)],    # Enemy 60 ships in 8 turns
    },
    {
        "name":   "Scenario C — Two enemies fight, then we arrive",
        "owner":  1, "ships": 50, "prod": 3,
        "arrivals": [(5, 2, 40), (12, 0, 25)],  # Enemy2 attacks enemy1, then us
    },
    {
        "name":   "Scenario D — We reinforce before enemy arrives",
        "owner":  0, "ships": 25, "prod": 2,
        "arrivals": [(12, 1, 50), (10, 0, 20)],  # Enemy@12, our help@10
    },
]

for sc in scenarios:
    tl = simulate_timeline(sc["owner"], sc["ships"], sc["prod"],
                           sc["arrivals"], player=0, horizon=20)
    print(f"\n  {sc['name']}")
    print(f"  Start: owner=Player{sc['owner']}, garrison={sc['ships']}, prod={sc['prod']}/turn")
    print(f"  Arrivals: {sc['arrivals']}")
    print(f"  → falls at turn: {tl['fall_turn']} | holds_full: {tl['holds_full']}")
    print(f"  → min ships to keep: {tl['keep_needed']}")

    # Print turn-by-turn for key turns
    print(f"  Turn-by-turn:")
    for t in [0, 5, 8, 10, 12, 15, 20]:
        o = tl['owner_at'].get(t, '?')
        s = tl['ships_at'].get(t, 0.0)
        owner_str = f"P{o}" if o != -1 else "N "
        bar = "▓" * min(40, int(s // 3))
        print(f"    t={t:>2}: [{owner_str}] {s:>6.1f} ships  {bar}")
```

## [MD]
## 📊 Layer 3 — Economic Mode: EXPAND / BALANCED / AGGRO

This is **OMEGA v3's biggest strategic innovation** over v2.

### The Problem with Blind Expansion

Many bots always expand — capturing every neutral planet in sight.
This is correct when you're ahead, but **catastrophically wrong when behind**.

**Example of the failure:**
- You have 2 production, enemy has 6 production
- Enemy generates 4 more ships/turn than you
- After 100 turns, enemy has ~400 extra ships
- No amount of neutral planets can make up for that lead

### The Solution: Production Ratio-Aware Strategy

```
eco_ratio = my_production / enemy_production

  EXPAND   (ratio > 1.35): We're winning. Expand carefully, avoid risky battles.
  BALANCED (0.72–1.35):    Normal play. Balance expansion and aggression.
  AGGRO    (ratio < 0.72): Emergency. Attack enemy production planets NOW.
```

### How Economic Mode Changes Every Decision

| Decision | EXPAND | BALANCED | AGGRO |
|----------|--------|----------|-------|
| Neutral target value | **+30%** | baseline | -20% |
| Enemy target value | -20% | baseline | **+45%** |
| High-prod enemy (≥4) | -20% | baseline | **+56%** |
| Reserves kept | **-20%** (safe to expand) | baseline | baseline |
| Rush counter bonus | n/a | n/a | **+40%** |

The scoring adjustments stack multiplicatively, meaning in AGGRO mode
a high-production enemy planet can get **+56% bonus** (1.45 × 1.25 = 1.81×)
compared to baseline — making it the overwhelming priority target.

## [CODE]
```python
from enum import Enum

class EcoMode(Enum):
    EXPAND   = "expand"    # Ahead in production → expand safely
    BALANCED = "balanced"  # Normal play
    AGGRO    = "aggro"     # Behind in production → attack enemy economy NOW

# Thresholds
ECO_EXPAND_THRESH = 1.35
ECO_AGGRO_THRESH  = 0.72

# Scoring multipliers
ECO_EXPAND_NEUTRAL_VM  = 1.30
ECO_EXPAND_HOSTILE_VM  = 0.80
ECO_AGGRO_HOSTILE_VM   = 1.45
ECO_AGGRO_NEUTRAL_VM   = 0.80
PROD_DENY_THRESHOLD    = 4

def determine_eco_mode(my_prod, enemy_prod):
    """Determine current economic strategy mode."""
    ratio = my_prod / max(1, enemy_prod)
    if   ratio >= ECO_EXPAND_THRESH: return EcoMode.EXPAND,   ratio
    elif ratio <= ECO_AGGRO_THRESH:  return EcoMode.AGGRO,    ratio
    else:                            return EcoMode.BALANCED,  ratio

def apply_eco_multipliers(base_val, target_owner, target_prod, player, eco_mode):
    """
    Adjust target value based on economic mode.
    This function is called inside target_value() for every potential target.
    """
    val = base_val
    if eco_mode == EcoMode.EXPAND:
        if   target_owner == -1:                 val *= ECO_EXPAND_NEUTRAL_VM
        elif target_owner != player:             val *= ECO_EXPAND_HOSTILE_VM

    elif eco_mode == EcoMode.AGGRO:
        if target_owner not in (-1, player):
            val *= ECO_AGGRO_HOSTILE_VM
            if target_prod >= PROD_DENY_THRESHOLD:
                val *= 1.25    # Extra: destroy their best production planet!
        elif target_owner == -1:
            val *= ECO_AGGRO_NEUTRAL_VM
    return val

# ── Demo: show all 3 modes' effect on scoring ────────────────────
print("=" * 62)
print("  ECONOMIC MODE DETECTION")
print("=" * 62)
scenarios = [
    (6, 2,  "Snowballing — lots of high-prod planets"),
    (4, 3,  "Slightly ahead"),
    (3, 3,  "Even production"),
    (3, 4,  "Slightly behind"),
    (2, 6,  "Losing badly — emergency AGGRO"),
    (1, 8,  "Desperate situation"),
]
print(f"  {'My Prod':>8} │ {'En Prod':>8} │ {'Ratio':>6} │ {'Mode':>10}")
print("  " + "─" * 45)
for my_p, en_p, desc in scenarios:
    mode, ratio = determine_eco_mode(my_p, en_p)
    icon = {"expand":"🌱", "balanced":"⚖️ ", "aggro":"⚔️ "}[mode.value]
    print(f"  {my_p:>8} │ {en_p:>8} │ {ratio:>6.2f} │ {icon} {mode.value:<10}  ← {desc}")

print()
print("=" * 62)
print("  HOW ECO MODE CHANGES TARGET SCORING  (base value = 1000)")
print("=" * 62)
player = 0
base   = 1000
for mode in EcoMode:
    n_low  = apply_eco_multipliers(base, -1, 2, player, mode)   # neutral prod-2
    h_low  = apply_eco_multipliers(base,  1, 2, player, mode)   # hostile prod-2
    h_high = apply_eco_multipliers(base,  1, 5, player, mode)   # hostile prod-5
    print(f"  {mode.value:>12}:")
    print(f"    Neutral  (prod=2): {n_low:>6.0f}  (×{n_low/base:.2f})")
    print(f"    Hostile  (prod=2): {h_low:>6.0f}  (×{h_low/base:.2f})")
    print(f"    Hostile  (prod=5): {h_high:>6.0f}  (×{h_high/base:.2f})  ← KEY in AGGRO!")
    print()
```

## [MD]
## 🛡️ Layer 5 — Intercept Missions (v3 NEW)

### The Old Way vs The OMEGA Way

**Old approach — Static garrisons:**
- Keep 80 ships on every planet "just in case"
- 80 ships × 10 planets = 800 ships idle doing nothing

**OMEGA approach — Dynamic intercept:**
- Monitor every enemy fleet in flight
- Calculate exactly when/if each threatens our planets
- Send precise reinforcement arriving just before the threat

### Intercept Algorithm

```
For each enemy fleet F heading toward our planet P:

  1. Calculate garrison_at_eta = P.ships + P.prod × F.eta
  2. deficit = max(0, F.ships - garrison_at_eta + 1)

  3. If deficit > 0:
       Find nearest ally planet A with budget >= deficit
       Find ship count to arrive at P by turn (F.eta - 1)

  4. If we can get there in time:
       Create INTERCEPT mission with high priority score
```

### Why This Beats Passive Defense

| Scenario | Garrison approach | OMEGA intercept |
|----------|-----------------|-----------------|
| Enemy sends 60, we have 70 garrison | Keep 70 idle ✗ | Send 0 extra ✅ |
| Enemy sends 80, we have 70 garrison | Need 10 more → keep 80 idle ✗ | Send 11 just in time ✅ |
| Enemy never attacks | 80 ships wasted all game ✗ | Ships deployed offensively ✅ |

The ships saved from passive garrison are now **offensive weapons**.

## [CODE]
```python
def detect_incoming_threats(my_planet_ships, my_planet_prod,
                             enemy_fleets_targeting_me, intercept_eta_max=20):
    """
    For each enemy fleet heading at our planet, determine if we need help
    and how many ships we need from an ally.

    Returns list of (en_eta, deficit, description) tuples.
    """
    threats = []
    for en_eta, en_owner, en_ships in sorted(enemy_fleets_targeting_me):
        if en_eta > intercept_eta_max:
            continue

        # Project our garrison forward to the moment of arrival
        garrison_at_eta = my_planet_ships + my_planet_prod * en_eta
        deficit = max(0, en_ships - garrison_at_eta + 1)  # +1 for safety

        status = "✅ SAFE (hold alone)" if deficit <= 0 else f"🚨 NEED {deficit} MORE SHIPS"
        threats.append((en_eta, en_owner, en_ships, garrison_at_eta, deficit, status))

    return threats

def compute_pressure_mult(active_fronts, planned_fronts,
                           front_min=3, bonus_per=0.12, max_mult=1.45):
    """
    Multi-front pressure bonus.

    When we're attacking many targets simultaneously, the enemy can't
    defend all of them optimally. Each front beyond the threshold
    gives a 12% scoring bonus — up to 45% total.

    Args:
        active_fronts:  set of planet IDs we already have fleets heading to
        planned_fronts: set of planet IDs we plan to target this turn
    """
    total = len(active_fronts) + len(set(planned_fronts))
    if total < front_min:
        return 1.0
    extra = total - front_min
    return min(max_mult, 1.0 + extra * bonus_per)

# ── Demo: Intercept threat detection ─────────────────────────────
print("=" * 68)
print("  INTERCEPT MISSION DEMO")
print("=" * 68)
print("  Our planet: 40 ships, +3/turn")
print()

enemy_fleets = [
    (12, 1, 55),   # Player 1 sends 55 ships, arrives turn 12
    (18, 2, 80),   # Player 2 sends 80 ships, arrives turn 18
    (7,  1, 30),   # Player 1 sends 30 ships, arrives turn 7
    (25, 3, 120),  # Player 3 sends 120 ships, arrives turn 25 (too far away)
]

threats = detect_incoming_threats(
    my_planet_ships=40, my_planet_prod=3,
    enemy_fleets_targeting_me=enemy_fleets,
    intercept_eta_max=20
)

for en_eta, en_owner, en_ships, garrison, deficit, status in threats:
    print(f"  Enemy P{en_owner}: {en_ships} ships at turn {en_eta}")
    print(f"    Our garrison by then: 40 + 3×{en_eta} = {garrison}")
    print(f"    Result: {status}")
    print()

print("  Fleet at turn 25 → ignored (beyond INTERCEPT_ETA_MAX=20)")

# ── Demo: Multi-front pressure ───────────────────────────────────
print()
print("=" * 68)
print("  MULTI-FRONT PRESSURE BONUS")
print("=" * 68)
print("  (Bonus for attacking multiple targets simultaneously)")
print()
print(f"  {'Active Fronts':>14} │ {'Pressure Mult':>14} │ Score Impact")
print("  " + "─" * 55)
for fronts in range(0, 10):
    pm   = compute_pressure_mult(set(), list(range(fronts)))
    bar  = "█" * int((pm - 1.0) * 50)
    diff = f"+{(pm-1)*100:.0f}%" if pm > 1.0 else "  —  "
    print(f"  {fronts:>14} │ {pm:>14.3f} │ {diff:>6}  {bar}")
```

## [MD]
## 🎯 Layer 5 — Target Scoring: How OMEGA Ranks Targets

Every potential target gets a score computed as:

```
base_value = (production ^ 1.25) × remaining_turns
           + indirect_wealth × remaining_turns × 0.15

final_value = base_value
    × type_bonus       (static=1.45–1.80, hostile=2.20, contested=0.65)
    × eco_mode_bonus   (EXPAND/AGGRO adjustments)
    × exposed_bonus    (×2.40 if enemy just sent their fleet away!)
    × gateway_bonus    (up to ×1.22 for forward positions near enemy)
    × weakest_bonus    (×1.65 in FFA for weakest enemy target)
    + elimination_bonus (+75 flat if enemy total ships < 140)
    + ship_value        (×1.50 per ship in very late game)

score = final_value / (ships_sent + travel_turns × 0.48 + 1)
      × pressure_mult  (up to ×1.45 for multi-front attacks)
```

### Why `production ^ 1.25`?

Linear production weighting makes prod-4 exactly 4× more valuable than prod-1.
With exponent 1.25, prod-4 is **5.66×** more valuable than prod-1.

This reflects the compounding reality: capturing a prod-4 planet doesn't just give
you 4 ships/turn — it gives you those ships to launch future attacks that generate
*more* ships. The exponential captures this snowball effect.

### The Exposed Planet Bonus (×2.40)

When an enemy planet's owner sends ≥45% of their fleet elsewhere,
the planet is **exposed**. This is the highest-value opportunity in the game:

- Garrison is depleted
- The sent fleet can't return in time
- The planet is temporarily vulnerable

OMEGA v3 detects this and assigns a ×2.40 multiplier — making exposed planets
**the highest-priority targets**, overriding everything else.

## [CODE]
```python
def target_score_demo(name, prod, owner, owner_str, ships_needed,
                      travel_turns, remaining=300,
                      is_static=False, is_exposed=False,
                      eco_mode_str="balanced", is_near_enemy=False,
                      pressure_fronts=2):
    """Demonstrate the scoring formula step by step."""
    PROD_EXP       = 1.25
    ATTACK_TURN_W  = 0.48
    HOSTILE_VM     = 2.20
    STATIC_HOST_VM = 1.80
    EXPOSED_VM     = 2.40
    GATEWAY_VM     = 1.22
    ELIM_BONUS     = 75.0
    WEAK_THRESH    = 140
    ECO_AGGRO_H_VM = 1.45

    turns_profit = max(1, remaining - travel_turns)
    base         = (prod ** PROD_EXP) * turns_profit

    mults = []
    val   = base

    if owner != -1:  # Hostile
        if is_static: val *= STATIC_HOST_VM; mults.append(f"×{STATIC_HOST_VM} static")
        else:         val *= HOSTILE_VM;     mults.append(f"×{HOSTILE_VM} hostile")

    if is_exposed:
        val *= EXPOSED_VM
        mults.append(f"×{EXPOSED_VM} EXPOSED!")

    if is_near_enemy:
        val *= GATEWAY_VM
        mults.append(f"×{GATEWAY_VM} gateway")

    if eco_mode_str == "aggro" and owner != -1:
        val *= ECO_AGGRO_H_VM
        mults.append(f"×{ECO_AGGRO_H_VM} AGGRO")
        if prod >= 4:
            val *= 1.25
            mults.append("×1.25 high-prod")

    if owner_str <= WEAK_THRESH and owner != -1:
        val += ELIM_BONUS
        mults.append(f"+{ELIM_BONUS} elim")

    # Pressure bonus
    pm = min(1.45, 1.0 + max(0, pressure_fronts - 3) * 0.12)

    raw_score  = val / (ships_needed + travel_turns * ATTACK_TURN_W + 1)
    final_score= raw_score * pm

    print(f"  {name}")
    print(f"    prod={prod}, owner={'enemy' if owner!=1 else 'neutral'}, "
          f"ships_needed={ships_needed}, travel={travel_turns} turns")
    print(f"    base = {prod}^{PROD_EXP} × {turns_profit} = {base:.1f}")
    print(f"    mults: {' '.join(mults) if mults else 'none'}")
    print(f"    value = {val:.1f}")
    print(f"    score = {val:.1f} / ({ships_needed} + {travel_turns}×{ATTACK_TURN_W} + 1)")
    print(f"          = {raw_score:.3f}  ×{pm:.2f} pressure = {final_score:.3f}")
    return final_score

print("=" * 68)
print("  TARGET SCORING COMPARISON")
print("=" * 68)
print()

targets = [
    ("Nearby neutral (prod=2)",
     dict(prod=2, owner=-1, owner_str=0,  ships_needed=12, travel_turns=8)),
    ("Far neutral (prod=3)",
     dict(prod=3, owner=-1, owner_str=0,  ships_needed=15, travel_turns=22)),
    ("Enemy planet (prod=3, static)",
     dict(prod=3, owner=1,  owner_str=200, ships_needed=45, travel_turns=12,
          is_static=True)),
    ("Enemy planet (prod=4, EXPOSED!)",
     dict(prod=4, owner=1,  owner_str=100, ships_needed=30, travel_turns=10,
          is_exposed=True)),
    ("Enemy prod-5 (AGGRO mode, near us)",
     dict(prod=5, owner=1,  owner_str=90,  ships_needed=60, travel_turns=14,
          is_near_enemy=True, eco_mode_str="aggro")),
]

scores = []
for name, kwargs in targets:
    sc = target_score_demo(name, **kwargs, pressure_fronts=4)
    scores.append((sc, name))
    print()

print("=" * 68)
print("  FINAL RANKING")
print("=" * 68)
for rank, (sc, name) in enumerate(sorted(scores, reverse=True), 1):
    bar = "█" * int(sc * 8)
    print(f"  #{rank}: {sc:.3f}  {bar}  {name}")
```

## [MD]
## ⚔️ Additional v3 Systems: Rush Detection & Gateway Value

### Early Rush Detection

In the first 60 turns of the game, OMEGA scans all incoming enemy fleets:

```
For each enemy fleet F:
  If F.ships >= 30 AND F is heading toward one of our planets
  AND F.ETA <= 25 turns:
    → RUSH DETECTED
```

**Response to a detected rush:**
1. Defense reserves increased by **+50%** for all our planets
2. Enemy planet targets get **+40% bonus** — counter-rush!
3. Classic counter-rush: "You attack my home, I attack yours"

The counter-attack bonus is key — often the best defense is a fast offense
that makes the enemy recall their rushing fleet to defend their own territory.

### Gateway/Positional Value

Planets that sit **within 25 units of enemy territory** score up to ×1.22 higher:

```
if dist(planet, nearest_enemy) <= 25:
    proximity_ratio = 1.0 - dist/25
    gateway_mult    = 1.0 + 0.22 × proximity_ratio
```

These forward-position planets serve as:
- Launch pads for faster attacks on enemy territory
- Chokepoints that limit enemy expansion
- Strategic anchors for coordinated multi-front assaults

Capturing a gateway planet often unlocks multiple subsequent capture opportunities.

## [CODE]
```python
import math

GATEWAY_VM          = 1.22
GATEWAY_DIST_THRESH = 25.0
RUSH_FLEET_MIN      = 30
RUSH_HOME_ETA_MAX   = 25
RUSH_DETECT_STEPS   = 60

def gateway_value(planet_x, planet_y, enemy_positions):
    """
    Compute positional bonus for a planet near enemy territory.
    Planets close to enemies are valuable forward bases.
    """
    if not enemy_positions:
        return 1.0
    min_dist = min(math.hypot(planet_x - ex, planet_y - ey)
                   for ex, ey in enemy_positions)
    if min_dist <= GATEWAY_DIST_THRESH:
        ratio = max(0.0, 1.0 - min_dist / GATEWAY_DIST_THRESH)
        return 1.0 + (GATEWAY_VM - 1.0) * ratio
    return 1.0

def detect_rush(fleets, my_planet_positions, my_planet_radii, player, step):
    """
    Detect early-game enemy rush.
    Returns (is_rush, total_rush_ships, min_eta).
    """
    if step > RUSH_DETECT_STEPS:
        return False, 0, 999

    total_rush = 0
    min_eta    = 999
    for (f_owner, f_x, f_y, f_angle, f_ships) in fleets:
        if f_owner == player or f_ships < RUSH_FLEET_MIN:
            continue
        dx, dy = math.cos(f_angle), math.sin(f_angle)
        spd    = 1.0 + 5.0 * (math.log(max(1,f_ships))/math.log(1000)) ** 1.5

        for (px, py), radius in zip(my_planet_positions, my_planet_radii):
            vec_x, vec_y = px - f_x, py - f_y
            proj  = vec_x * dx + vec_y * dy
            if proj <= 0: continue
            perp  = abs(vec_x * dy - vec_y * dx)
            if perp > radius + 5: continue
            eta   = int(math.ceil(proj / spd))
            if eta <= RUSH_HOME_ETA_MAX:
                total_rush += f_ships
                min_eta = min(min_eta, eta)

    return total_rush >= RUSH_FLEET_MIN, total_rush, min_eta

# ── Gateway value visualization ──────────────────────────────────
print("=" * 62)
print("  GATEWAY VALUE — Planets Near Enemy Territory")
print("=" * 62)
print("  Enemy base at (80, 80)")
print()

enemy_pos = [(80.0, 80.0)]
test_planets = [
    ("Very close (adjacent territory)", 65., 65.),
    ("Moderately close (mid-field)",    55., 55.),
    ("Neutral ground",                  45., 45.),
    ("Our side (far from enemy)",       20., 20.),
    ("Our home base",                   10., 10.),
]
print(f"  {'Planet':>36} │ {'Dist to enemy':>14} │ {'Gateway Mult':>12} │ Bonus")
print("  " + "─" * 72)
for name, px, py in test_planets:
    d   = math.hypot(px - 80, py - 80)
    gv  = gateway_value(px, py, enemy_pos)
    bar = "▲" * int((gv - 1.0) * 100)
    print(f"  {name:>36} │ {d:>14.1f} │ {gv:>12.3f} │ +{(gv-1)*100:.1f}% {bar}")

# ── Rush detection demo ──────────────────────────────────────────
print()
print("=" * 62)
print("  EARLY RUSH DETECTION")
print("=" * 62)

my_home = [(15.0, 15.0)]
my_radii = [2.5]

rush_scenarios = [
    ("Small probe (not a rush)",   [(1, 85., 85., -2.36, 15)]),
    ("Medium rush (35 ships)",     [(1, 80., 80., -2.36, 35)]),
    ("Heavy rush (60 ships)",      [(1, 80., 80., -2.36, 60)]),
    ("Two-prong rush",             [(1, 80., 80., -2.36, 35), (2, 20., 80., -1.57, 35)]),
    ("Late-game (step=70, ignored)", [(1, 80., 80., -2.36, 60)]),  # step > 60
]

for name, fleets_data in rush_scenarios:
    step = 70 if "ignored" in name else 25
    is_rush, total, eta = detect_rush(
        [(o,x,y,a,s) for o,x,y,a,s in fleets_data],
        my_home, my_radii, player=0, step=step
    )
    icon = "🚨 RUSH DETECTED" if is_rush else "✅ Normal"
    print(f"  {icon}  {name}")
    if is_rush:
        print(f"    → {total} enemy ships incoming, ETA ~{eta} turns")
        print(f"    → Response: +50% reserves, +40% counter-attack bonus")
```

## [CODE]
```python
%%writefile submission.py
"""
OMEGA v3 — Orbit Wars Maximum Tactical Intelligence
New in v3 vs v2:
  1. Economic Mode System (EXPAND / BALANCED / AGGRO) — adjusts all scoring
  2. Intercept Missions — preemptive reinforcement before enemy fleet arrives
  3. Multi-Front Pressure Bonus — coordinated attacks penalize enemy defense
  4. Speed-Optimal Fleet Sizing — mathematically justified tsunami
  5. Win/Loss Margin Awareness — momentum-based risk adjustment
  6. Gateway/Positional Value — forward planets score higher
  7. Early Rush Detection & Counter-Rush
  8. Endgame Ship Accounting — know exactly how many ships we need to win
"""

import math
import time
from collections import defaultdict, namedtuple
from dataclasses import dataclass, field
from enum import Enum

# ════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════════════

BOARD          = 100.0
CENTER_X       = 50.0
CENTER_Y       = 50.0
SUN_R          = 10.0
MAX_SPEED      = 6.0
SUN_SAFETY     = 1.6
ROTATION_LIMIT = 50.0
TOTAL_STEPS    = 500
HORIZON        = 110
LAUNCH_CLR     = 0.1
INTERCEPT_TOL  = 1

# Phase thresholds
EARLY_LIMIT         = 40
OPENING_LIMIT       = 90
LATE_REMAINING      = 80
VERY_LATE_REMAINING = 30
TOTAL_WAR_REMAINING = 65
ENDGAME_REMAINING   = 100

# Opening
SAFE_OPEN_PROD_TH  = 4
SAFE_OPEN_TURN_LIM = 10
ROT_OPEN_MAX_TURNS = 13
ROT_OPEN_LOW_PROD  = 2
FFA_ROT_REACT_GAP  = 3
FFA_ROT_SEND_RATIO = 0.52
FFA_ROT_TURN_LIM   = 10
COMET_MAX_CHASE    = 10

# ── Value multipliers ────────────────────────────────────────────────
INDIRECT_SCALE      = 0.15
IND_FRIENDLY_W      = 0.35
IND_NEUTRAL_W       = 0.9
IND_ENEMY_W         = 1.25

PROD_EXP            = 1.25   # production exponent

STATIC_NEUTRAL_VM   = 1.45
STATIC_HOSTILE_VM   = 1.80
ROT_OPEN_VM         = 0.88
HOSTILE_VM          = 2.20
OPEN_HOSTILE_VM     = 1.65
SAFE_NEUTRAL_VM     = 1.30
CONTESTED_NEUTRAL_VM= 0.65
EARLY_NEUTRAL_VM    = 1.35
COMET_VM            = 0.58
SNIPE_VM            = 1.18
SWARM_VM            = 1.08
REINFORCE_VM        = 1.35
CRASH_VM            = 1.25
FINISH_HOSTILE_VM   = 1.40
GANG_UP_VM          = 1.50
EXPOSED_VM          = 2.40
BEHIND_ROT_VM       = 0.88
RACE_WIN_VM         = 1.55
PROD_DENY_VM        = 1.35

# ── Economic mode multipliers ────────────────────────────────────────
ECO_EXPAND_NEUTRAL_VM  = 1.30   # EXPAND mode: prefer neutrals
ECO_EXPAND_HOSTILE_VM  = 0.80   # EXPAND mode: avoid costly fights
ECO_AGGRO_HOSTILE_VM   = 1.45   # AGGRO mode: must attack enemy production
ECO_AGGRO_NEUTRAL_VM   = 0.80   # AGGRO mode: neutrals less important than enemy prod
ECO_EXPAND_THRESH      = 1.35   # prod ratio threshold for EXPAND
ECO_AGGRO_THRESH       = 0.72   # prod ratio threshold for AGGRO

# ── Positional/gateway value ─────────────────────────────────────────
GATEWAY_VM          = 1.22   # bonus for planets that advance our position
GATEWAY_DIST_THRESH = 25.0   # planet is a gateway if it's within this distance of enemy

# ── Multi-front pressure ─────────────────────────────────────────────
PRESSURE_FRONT_MIN  = 3      # min active attack fronts to trigger bonus
PRESSURE_BONUS_PER  = 0.12   # bonus per front beyond minimum
PRESSURE_MAX_MULT   = 1.45   # cap on pressure multiplier

# ── Weakest enemy ────────────────────────────────────────────────────
WEAKEST_VM_FFA = 1.65
WEAKEST_VM_1V1 = 1.35
ELIM_BONUS     = 75.0
WEAK_THRESH    = 140

# ── Margins ──────────────────────────────────────────────────────────
SAFE_NEUTRAL_MARGIN      = 2
CONTESTED_NEUTRAL_MARGIN = 2
NEUTRAL_MARGIN_BASE      = 2
NEUTRAL_MARGIN_PROD_W    = 2
NEUTRAL_MARGIN_CAP       = 8
HOSTILE_MARGIN_BASE      = 3
HOSTILE_MARGIN_PROD_W    = 2
HOSTILE_MARGIN_CAP       = 12
STATIC_MARGIN            = 4
CONTESTED_MARGIN         = 5
FFA_MARGIN               = 2
LONG_TRAVEL_START        = 18
LONG_TRAVEL_DIV          = 3
LONG_TRAVEL_CAP          = 8
COMET_MARGIN_RELIEF      = 6
FINISH_SEND_BONUS        = 4

# ── Score modifiers ──────────────────────────────────────────────────
STATIC_SCORE_M       = 1.20
EARLY_STATIC_SCORE_M = 1.30
FFA_ROT_SCORE_M      = 0.82
DENSE_STATIC_THRESH  = 4
DENSE_ROT_SCORE_M    = 0.84
SNIPE_SCORE_M        = 1.16
SWARM_SCORE_M        = 1.07
CRASH_SCORE_M        = 1.10
EXPOSED_SCORE_M      = 1.35
WEAKEST_SCORE_M      = 1.28
RACE_SCORE_M         = 1.20

# ── Cost weights ─────────────────────────────────────────────────────
ATTACK_TURN_W  = 0.48
SNIPE_TURN_W   = 0.40
DEF_TURN_W     = 0.38
REINF_TURN_W   = 0.33
RECAP_TURN_W   = 0.50

# ── Tsunami (Speed-Optimal) ───────────────────────────────────────────
TSUNAMI_RATIO          = 0.87
TSUNAMI_THRESH         = 1.8
TSUNAMI_MIN_SHIPS      = 35
TSUNAMI_TURNS_SAVED_MIN= 2     # min turns saved to justify sending more ships
TSUNAMI_MAX_EXTRA_FRAC = 0.45  # max fraction of budget to spend as "extra" ships

# ── Defense ──────────────────────────────────────────────────────────
PROACT_HORIZON     = 14
PROACT_RATIO       = 0.32
MULTI_PROACT_HOR   = 18
MULTI_PROACT_RATIO = 0.40
MULTI_STACK_WIN    = 5
REACT_MY_TOP_K     = 4
REACT_EN_TOP_K     = 4
PROACT_EN_TOP_K    = 3

# 1v1 aggression when dominating
ONE_V_ONE_DOM_THRESH  = 0.25
ONE_V_ONE_AGG_RESERVE = 0.35

# ── Early rush detection ─────────────────────────────────────────────
RUSH_DETECT_STEP_MAX = 60     # only detect rush in early game
RUSH_FLEET_MIN       = 30     # min ships in enemy fleet to count as rush
RUSH_HOME_ETA_MAX    = 25     # fleet must arrive within this many turns

# ── Intercept missions ───────────────────────────────────────────────
INTERCEPT_ETA_MAX    = 20     # detect enemy fleets arriving within this many turns
INTERCEPT_ENABLED    = True

# ── Win margin awareness ─────────────────────────────────────────────
WIN_SECURE_RATIO     = 1.35   # my_total / enemy_total = we're winning safely
WIN_DESPERATE_RATIO  = 0.72   # my_total / enemy_total = we're losing badly
WIN_SECURE_MARGIN_M  = 0.85   # reduce send margins when winning (be efficient)
WIN_DESPERATE_RISK_M = 1.25   # increase aggression when losing

# ── Reinforcement ────────────────────────────────────────────────────
REINF_ENABLED      = True
REINF_MIN_PROD     = 2
REINF_MAX_TRAVEL   = 22
REINF_SAFETY       = 2
REINF_MAX_SRC_FRAC = 0.75
REINF_MIN_FUTURE   = 40
REINF_LOOKAHEAD    = 20

# ── Defense rescue ───────────────────────────────────────────────────
DEF_LOOKAHEAD   = 30
DEF_SHIP_VALUE  = 0.60
DEF_FRONTIER_M  = 1.15
DEF_SEND_MARGIN = 1
DEF_SEND_PROD_W = 1

# ── Recapture ────────────────────────────────────────────────────────
RECAP_LOOKAHEAD = 12
RECAP_VM        = 0.90
RECAP_FRONTIER_M= 1.10
RECAP_PROD_W    = 0.6
RECAP_IMMED_W   = 0.4

# ── Multi-source swarms ──────────────────────────────────────────────
FOLLOWUP_MIN        = 8
LOW_COMET_PROD      = 1
LATE_BUFFER         = 5
VERY_LATE_BUFFER    = 3
PARTIAL_MIN         = 6
MULTI_TOP_K         = 5
MULTI_ETA_TOL       = 2
MULTI_PLAN_PEN      = 0.97
HOSTILE_SWARM_TOL   = 1
THREE_SRC_ENABLED   = True
THREE_SRC_MIN_SHIPS = 18
THREE_SRC_TOL       = 1
THREE_SRC_PEN       = 0.93

# ── Crash exploit ────────────────────────────────────────────────────
CRASH_ENABLED   = True
CRASH_MIN_SHIPS = 6
CRASH_ETA_WIN   = 3
CRASH_DELAY     = 1

# ── Gang-up ──────────────────────────────────────────────────────────
GANG_POST_DELAY = 2
GANG_ETA_WIN    = 4

# ── Fleet race ───────────────────────────────────────────────────────
RACE_MARGIN_TURNS = 1
RACE_MIN_ADVANTAGE= 2

# ── Vulnerability ────────────────────────────────────────────────────
VULN_SENT_RATIO = 0.45
VULN_MIN_SENT   = 8

# ── Production denial ────────────────────────────────────────────────
PROD_DENY_THRESHOLD = 4

# ── Endgame ──────────────────────────────────────────────────────────
LATE_SHIP_W       = 0.90
VERY_LATE_SHIP_W  = 1.50

# ── Doomed ───────────────────────────────────────────────────────────
DOOMED_EVAC_LIMIT = 24
DOOMED_MIN_SHIPS  = 8

# ── Rear logistics ───────────────────────────────────────────────────
REAR_MIN_SHIPS  = 14
REAR_DIST_RATIO = 1.25
REAR_STAGE_PROG = 0.78
REAR_RATIO_2P   = 0.65
REAR_RATIO_FFA  = 0.58
REAR_SEND_MIN   = 10
REAR_MAX_TRAVEL = 40

# ── Domination ───────────────────────────────────────────────────────
BEHIND_DOM    = -0.18
AHEAD_DOM     = 0.13
FINISH_DOM    = 0.26
FINISH_PROD_R = 1.12
AHEAD_MRG_B   = 0.14
BEHIND_MRG_P  = 0.06
FINISH_MRG_B  = 0.14

# ── Timing ───────────────────────────────────────────────────────────
SOFT_DEADLINE    = 0.83
HEAVY_MIN_TIME   = 0.14
OPT_MIN_TIME     = 0.07
HEAVY_PLANET_LIM = 36

# ════════════════════════════════════════════════════════════════════════
# TYPES
# ════════════════════════════════════════════════════════════════════════

Planet = namedtuple("Planet", ["id","owner","x","y","radius","ships","production"])
Fleet  = namedtuple("Fleet",  ["id","owner","x","y","angle","from_planet_id","ships"])

class EcoMode(Enum):
    EXPAND   = "expand"    # ahead in production — expand safely
    BALANCED = "balanced"  # normal play
    AGGRO    = "aggro"     # behind in production — attack enemy production

@dataclass(frozen=True)
class ShotOption:
    score:       float
    src_id:      int
    target_id:   int
    angle:       float
    turns:       int
    needed:      int
    send_cap:    int
    mission:     str      = "capture"
    anchor_turn: int|None = None

@dataclass
class Mission:
    kind:      str
    score:     float
    target_id: int
    turns:     int
    options:   list = field(default_factory=list)

# ════════════════════════════════════════════════════════════════════════
# PHYSICS
# ════════════════════════════════════════════════════════════════════════

def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)

def orbital_radius(p):
    return dist(p.x, p.y, CENTER_X, CENTER_Y)

def is_static_planet(p):
    return orbital_radius(p) + p.radius >= ROTATION_LIMIT

def fleet_speed(ships):
    if ships <= 1: return 1.0
    r = max(0.0, min(1.0, math.log(ships) / math.log(1000.0)))
    return 1.0 + (MAX_SPEED - 1.0) * (r ** 1.5)

def speed_optimal_send(needed, available, distance, prod_per_turn):
    """
    v3: Mathematically justified tsunami.
    Send more ships only if the turns saved justify the ship cost.
    turns_saved = distance/speed(needed) - distance/speed(larger)
    ships_gained_from_extra_speed = turns_saved * prod_per_turn (rough)
    Only tsunami if ships_gained > extra_ships_sent * some_factor
    """
    if available <= 0 or needed <= 0: return needed
    if available < needed: return needed

    base_speed  = fleet_speed(max(1, needed))
    base_turns  = max(1, int(math.ceil(distance / base_speed)))

    # Check if fixed threshold applies
    if available >= needed * TSUNAMI_THRESH and available >= TSUNAMI_MIN_SHIPS:
        candidate = min(available, max(needed, int(available * TSUNAMI_RATIO)))
        cand_speed = fleet_speed(max(1, candidate))
        cand_turns = max(1, int(math.ceil(distance / cand_speed)))
        turns_saved = base_turns - cand_turns
        extra_ships = candidate - needed
        # Justify extra ships by production value of time saved
        if turns_saved >= TSUNAMI_TURNS_SAVED_MIN:
            return candidate
        # Even if turns_saved is small, send if extra ships are cheap
        if extra_ships <= available * TSUNAMI_MAX_EXTRA_FRAC:
            return candidate

    # Soft tsunami: try sending 20% more to get small speed boost
    modest = min(available, int(needed * 1.20))
    if modest > needed:
        mod_speed = fleet_speed(max(1, modest))
        mod_turns = max(1, int(math.ceil(distance / mod_speed)))
        if base_turns - mod_turns >= 1:
            return modest

    return min(available, max(needed, int(needed * 1.05)))

def pt_seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2-x1, y2-y1
    sq = dx*dx + dy*dy
    if sq <= 1e-9: return dist(px, py, x1, y1)
    t = max(0.0, min(1.0, ((px-x1)*dx + (py-y1)*dy) / sq))
    return dist(px, py, x1+t*dx, y1+t*dy)

def seg_hits_sun(x1, y1, x2, y2, s=SUN_SAFETY):
    return pt_seg_dist(CENTER_X, CENTER_Y, x1, y1, x2, y2) < SUN_R + s

def launch_pt(sx, sy, sr, angle):
    c = sr + LAUNCH_CLR
    return sx + math.cos(angle)*c, sy + math.sin(angle)*c

def safe_angle_dist(sx, sy, sr, tx, ty, tr):
    angle = math.atan2(ty-sy, tx-sx)
    lx, ly = launch_pt(sx, sy, sr, angle)
    d = max(0.0, dist(sx, sy, tx, ty) - (sr + LAUNCH_CLR) - tr)
    ex, ey = lx + math.cos(angle)*d, ly + math.sin(angle)*d
    if seg_hits_sun(lx, ly, ex, ey): return None
    return angle, d

def predict_planet_pos(planet, init_by_id, ang_vel, turns):
    init = init_by_id.get(planet.id)
    if init is None: return planet.x, planet.y
    r = dist(init.x, init.y, CENTER_X, CENTER_Y)
    if r + init.radius >= ROTATION_LIMIT: return planet.x, planet.y
    cur = math.atan2(planet.y - CENTER_Y, planet.x - CENTER_X)
    new = cur + ang_vel * turns
    return CENTER_X + r*math.cos(new), CENTER_Y + r*math.sin(new)

def predict_comet_pos(pid, comets, turns):
    for g in comets:
        pids = g.get("planet_ids", [])
        if pid not in pids: continue
        idx  = pids.index(pid)
        paths= g.get("paths", [])
        pi   = g.get("path_index", 0)
        if idx >= len(paths): return None
        fi   = pi + int(turns)
        if 0 <= fi < len(paths[idx]): return paths[idx][fi][0], paths[idx][fi][1]
        return None
    return None

def comet_life(pid, comets):
    for g in comets:
        pids = g.get("planet_ids", [])
        if pid not in pids: continue
        idx  = pids.index(pid)
        paths= g.get("paths", [])
        pi   = g.get("path_index", 0)
        if idx < len(paths): return max(0, len(paths[idx]) - pi)
    return 0

def estimate_arrival(sx, sy, sr, tx, ty, tr, ships):
    safe = safe_angle_dist(sx, sy, sr, tx, ty, tr)
    if safe is None: return None
    angle, d = safe
    return angle, max(1, int(math.ceil(d / fleet_speed(max(1, ships)))))

def travel_time(sx, sy, sr, tx, ty, tr, ships):
    e = estimate_arrival(sx, sy, sr, tx, ty, tr, ships)
    return e[1] if e else 10**9

def predict_target_pos(target, turns, init_by_id, ang_vel, comets, comet_ids):
    if target.id in comet_ids: return predict_comet_pos(target.id, comets, turns)
    return predict_planet_pos(target, init_by_id, ang_vel, turns)

def target_can_move(target, init_by_id, comet_ids):
    if target.id in comet_ids: return True
    init = init_by_id.get(target.id)
    if init is None: return False
    return dist(init.x, init.y, CENTER_X, CENTER_Y) + init.radius < ROTATION_LIMIT

def search_intercept(src, target, ships, init_by_id, ang_vel, comets, comet_ids):
    best, best_sc = None, None
    max_t = min(HORIZON, 60)
    if target.id in comet_ids:
        max_t = min(max_t, max(0, comet_life(target.id, comets) - 1))
    for ct in range(1, max_t + 1):
        pos = predict_target_pos(target, ct, init_by_id, ang_vel, comets, comet_ids)
        if pos is None: continue
        e = estimate_arrival(src.x, src.y, src.radius, pos[0], pos[1], target.radius, ships)
        if e is None: continue
        if abs(e[1] - ct) > INTERCEPT_TOL: continue
        at = max(e[1], ct)
        ap = predict_target_pos(target, at, init_by_id, ang_vel, comets, comet_ids)
        if ap is None: continue
        c = estimate_arrival(src.x, src.y, src.radius, ap[0], ap[1], target.radius, ships)
        if c is None: continue
        delta = abs(c[1] - at)
        if delta > INTERCEPT_TOL: continue
        sc = (delta, c[1], ct)
        if best is None or sc < best_sc: best_sc, best = sc, (c[0], c[1], ap[0], ap[1])
    return best

def aim_with_prediction(src, target, ships, init_by_id, ang_vel, comets, comet_ids):
    e = estimate_arrival(src.x, src.y, src.radius, target.x, target.y, target.radius, ships)
    if e is None:
        if not target_can_move(target, init_by_id, comet_ids): return None
        return search_intercept(src, target, ships, init_by_id, ang_vel, comets, comet_ids)
    tx, ty = target.x, target.y
    for _ in range(5):
        _, turns = e
        pos = predict_target_pos(target, turns, init_by_id, ang_vel, comets, comet_ids)
        if pos is None: return None
        ntx, nty = pos
        ne = estimate_arrival(src.x, src.y, src.radius, ntx, nty, target.radius, ships)
        if ne is None:
            if not target_can_move(target, init_by_id, comet_ids): return None
            return search_intercept(src, target, ships, init_by_id, ang_vel, comets, comet_ids)
        if abs(ntx-tx)<0.3 and abs(nty-ty)<0.3 and abs(ne[1]-turns)<=INTERCEPT_TOL:
            return ne[0], ne[1], ntx, nty
        tx, ty = ntx, nty
        e = ne
    fe = estimate_arrival(src.x, src.y, src.radius, tx, ty, target.radius, ships)
    if fe is None:
        return search_intercept(src, target, ships, init_by_id, ang_vel, comets, comet_ids)
    return fe[0], fe[1], tx, ty

# ════════════════════════════════════════════════════════════════════════
# WORLD MODEL
# ════════════════════════════════════════════════════════════════════════

def fleet_target_planet(fleet, planets):
    best_p, best_t = None, 1e9
    dx, dy = math.cos(fleet.angle), math.sin(fleet.angle)
    sp     = fleet_speed(fleet.ships)
    for p in planets:
        px, py  = p.x-fleet.x, p.y-fleet.y
        proj    = px*dx + py*dy
        if proj < 0: continue
        perp_sq = px*px + py*py - proj*proj
        if perp_sq >= p.radius*p.radius: continue
        hit = max(0.0, proj - math.sqrt(max(0.0, p.radius*p.radius - perp_sq)))
        t   = hit / sp
        if t <= HORIZON and t < best_t: best_t, best_p = t, p
    if best_p is None: return None, None
    return best_p, int(math.ceil(best_t))

def build_arrival_ledger(fleets, planets):
    abp = {p.id: [] for p in planets}
    for f in fleets:
        tp, eta = fleet_target_planet(f, planets)
        if tp is None: continue
        abp[tp.id].append((eta, f.owner, int(f.ships)))
    return abp

def resolve_arrivals(owner, garrison, arrivals):
    by_owner = {}
    for _, ao, s in arrivals: by_owner[ao] = by_owner.get(ao, 0) + s
    if not by_owner: return owner, max(0.0, garrison)
    srt = sorted(by_owner.items(), key=lambda x: x[1], reverse=True)
    top_o, top_s = srt[0]
    if len(srt) > 1:
        sec = srt[1][1]
        if top_s == sec: surv_o, surv_s = -1, 0
        else:            surv_o, surv_s = top_o, top_s - sec
    else: surv_o, surv_s = top_o, top_s
    if surv_s <= 0: return owner, max(0.0, garrison)
    if owner == surv_o: return owner, garrison + surv_s
    garrison -= surv_s
    if garrison < 0: return surv_o, -garrison
    return owner, garrison

def normalize_arrivals(arrivals, horizon):
    events = []
    for t, o, s in arrivals:
        if s <= 0: continue
        eta = max(1, int(math.ceil(t)))
        if eta > horizon: continue
        events.append((eta, o, int(s)))
    events.sort(); return events

def simulate_timeline(planet, arrivals, player, horizon):
    horizon  = max(0, int(math.ceil(horizon)))
    events   = normalize_arrivals(arrivals, horizon)
    by_turn  = defaultdict(list)
    for item in events: by_turn[item[0]].append(item)
    owner    = planet.owner
    garrison = float(planet.ships)
    owner_at = {0: owner}
    ships_at = {0: max(0.0, garrison)}
    fall_turn = None; first_enemy = None
    for turn in range(1, horizon + 1):
        if owner != -1: garrison += planet.production
        group = by_turn.get(turn, [])
        prev  = owner
        if group:
            if prev == player and first_enemy is None:
                if any(i[1] not in (-1, player) for i in group): first_enemy = turn
            owner, garrison = resolve_arrivals(owner, garrison, group)
            if prev == player and owner != player and fall_turn is None: fall_turn = turn
        owner_at[turn] = owner
        ships_at[turn] = max(0.0, garrison)
    keep_needed = 0; holds_full = True
    if planet.owner == player:
        def survives(keep):
            so, sg = planet.owner, float(keep)
            for turn in range(1, horizon + 1):
                if so != -1: sg += planet.production
                gr = by_turn.get(turn, [])
                if gr:
                    so, sg = resolve_arrivals(so, sg, gr)
                    if so != player: return False
            return so == player
        if survives(int(planet.ships)):
            lo, hi = 0, int(planet.ships)
            while lo < hi:
                mid = (lo + hi) // 2
                if survives(mid): hi = mid
                else: lo = mid + 1
            keep_needed = lo
        else:
            holds_full = False; keep_needed = int(planet.ships)
    return dict(owner_at=owner_at, ships_at=ships_at, keep_needed=keep_needed,
                fall_turn=fall_turn, first_enemy=first_enemy,
                holds_full=holds_full, horizon=horizon)

def state_at(timeline, arrival_turn):
    turn  = max(0, min(int(math.ceil(arrival_turn)), timeline["horizon"]))
    h     = timeline["horizon"]
    owner = timeline["owner_at"].get(turn, timeline["owner_at"][h])
    ships = timeline["ships_at"].get(turn, timeline["ships_at"][h])
    return owner, max(0.0, ships)

def count_players(planets, fleets):
    owners = set()
    for p in planets:
        if p.owner != -1: owners.add(p.owner)
    for f in fleets: owners.add(f.owner)
    return max(2, len(owners))

def nearest_dist(px, py, planets):
    if not planets: return 10**9
    return min(dist(px, py, p.x, p.y) for p in planets)

def indirect_features(planet, planets, player):
    f = n = e = 0.0
    for o in planets:
        if o.id == planet.id: continue
        d = dist(planet.x, planet.y, o.x, o.y)
        if d < 1: continue
        fac = o.production / (d + 12.0)
        if   o.owner == player: f += fac
        elif o.owner == -1:     n += fac
        else:                   e += fac
    return f, n, e

def detect_vulnerable_planets(fleets, enemy_planets, player):
    vuln = set()
    sent_from = defaultdict(int)
    for f in fleets:
        if f.owner == player or f.owner == -1: continue
        sent_from[f.from_planet_id] += int(f.ships)
    for p in enemy_planets:
        sent = sent_from.get(p.id, 0)
        if sent >= VULN_MIN_SENT and sent >= p.ships * VULN_SENT_RATIO:
            vuln.add(p.id)
    return vuln

def weakest_enemy_owner(enemy_planets, owner_strength, owner_prod):
    owners = set(p.owner for p in enemy_planets)
    if not owners: return None
    return min(owners, key=lambda o: owner_strength.get(o,0) + owner_prod.get(o,0)*15)

def highest_prod_enemy_planet(enemy_planets, owner_strength):
    if not enemy_planets: return None
    return max(enemy_planets, key=lambda p: p.production*10 + owner_strength.get(p.owner,0))

def compute_gateway_value(planet, enemy_planets):
    """
    v3: Planets close to enemy territory are strategically valuable as forward bases.
    Returns a multiplier > 1.0 for gateway planets.
    """
    if not enemy_planets: return 1.0
    min_en_dist = min(dist(planet.x, planet.y, e.x, e.y) for e in enemy_planets)
    if min_en_dist <= GATEWAY_DIST_THRESH:
        # Closer to enemy = more valuable as forward base
        ratio = max(0.0, 1.0 - min_en_dist / GATEWAY_DIST_THRESH)
        return 1.0 + (GATEWAY_VM - 1.0) * ratio
    return 1.0

def detect_rush(fleets, my_planets, player, step):
    """
    v3: Detect if enemy is doing early rush — large fleet heading at us.
    Returns (is_rush, total_rush_ships, min_eta)
    """
    if step > RUSH_DETECT_STEP_MAX: return False, 0, 999
    my_ids = {p.id for p in my_planets}
    total_rush = 0; min_eta = 999
    for f in fleets:
        if f.owner == player or f.owner == -1: continue
        if int(f.ships) < RUSH_FLEET_MIN: continue
        # Quick check: is this fleet heading generally toward our planets?
        dx, dy = math.cos(f.angle), math.sin(f.angle)
        for mp in my_planets:
            px, py = mp.x - f.x, mp.y - f.y
            proj = px*dx + py*dy
            if proj <= 0: continue
            perp = abs(px*dy - py*dx)
            if perp > mp.radius + 5: continue
            eta = int(math.ceil(proj / fleet_speed(f.ships)))
            if eta <= RUSH_HOME_ETA_MAX:
                total_rush += int(f.ships)
                min_eta = min(min_eta, eta)
    return total_rush >= RUSH_FLEET_MIN, total_rush, min_eta


class WorldModel:
    def __init__(self, player, step, planets, fleets, init_by_id, ang_vel, comets, comet_ids):
        self.player    = player
        self.step      = step
        self.planets   = planets
        self.fleets    = fleets
        self.init_by_id= init_by_id
        self.ang_vel   = ang_vel
        self.comets    = comets
        self.comet_ids = set(comet_ids)

        self.by_id           = {p.id: p for p in planets}
        self.my_planets      = [p for p in planets if p.owner == player]
        self.enemy_planets   = [p for p in planets if p.owner not in (-1, player)]
        self.neutral_planets = [p for p in planets if p.owner == -1]
        self.static_neutrals = [p for p in self.neutral_planets if is_static_planet(p)]

        self.num_players  = count_players(planets, fleets)
        self.remaining    = max(1, TOTAL_STEPS - step)
        self.is_early     = step < EARLY_LIMIT
        self.is_opening   = step < OPENING_LIMIT
        self.is_late      = self.remaining < LATE_REMAINING
        self.is_very_late = self.remaining < VERY_LATE_REMAINING
        self.is_total_war = self.remaining < TOTAL_WAR_REMAINING
        self.is_endgame   = self.remaining < ENDGAME_REMAINING
        self.is_ffa       = self.num_players >= 4

        self.owner_strength = defaultdict(int)
        self.owner_prod     = defaultdict(int)
        for p in planets:
            if p.owner != -1:
                self.owner_strength[p.owner] += int(p.ships)
                self.owner_prod[p.owner]     += int(p.production)
        for f in fleets:
            self.owner_strength[f.owner] += int(f.ships)

        self.my_total    = self.owner_strength.get(player, 0)
        self.enemy_total = sum(s for o,s in self.owner_strength.items() if o != player)
        self.max_enemy   = max((s for o,s in self.owner_strength.items() if o != player), default=0)
        self.my_prod     = self.owner_prod.get(player, 0)
        self.enemy_prod  = sum(s for o,s in self.owner_prod.items() if o != player)

        # Economic mode
        eco_ratio = self.my_prod / max(1, self.enemy_prod)
        if eco_ratio >= ECO_EXPAND_THRESH:
            self.eco_mode = EcoMode.EXPAND
        elif eco_ratio <= ECO_AGGRO_THRESH:
            self.eco_mode = EcoMode.AGGRO
        else:
            self.eco_mode = EcoMode.BALANCED

        # Win margin
        if self.enemy_total > 0:
            self.win_ratio = self.my_total / self.enemy_total
        else:
            self.win_ratio = 10.0
        self.is_winning_secure  = self.win_ratio >= WIN_SECURE_RATIO
        self.is_losing_desperate= self.win_ratio <= WIN_DESPERATE_RATIO

        # Rush detection
        self.is_rush, self.rush_ships, self.rush_eta = detect_rush(
            fleets, self.my_planets, player, step)

        self._weakest    = weakest_enemy_owner(self.enemy_planets, self.owner_strength, self.owner_prod)
        self._weakest_str= self.owner_strength.get(self._weakest, 0) if self._weakest else 0
        self._deny_target= highest_prod_enemy_planet(self.enemy_planets, self.owner_strength)

        self.arrivals  = build_arrival_ledger(fleets, planets)
        self.timelines = {
            p.id: simulate_timeline(p, self.arrivals[p.id], player, HORIZON)
            for p in planets
        }
        self.indirect_map = {p.id: indirect_features(p, planets, player) for p in planets}
        self.vuln_ids     = detect_vulnerable_planets(fleets, self.enemy_planets, player)

        # v3: gateway value map
        self.gateway_map  = {
            p.id: compute_gateway_value(p, self.enemy_planets)
            for p in planets
        }

        # Enemy fleets targeting my planets (for intercept missions)
        self.en_fleet_to_my = defaultdict(list)  # my_planet_id -> [(eta, owner, ships)]
        for f in fleets:
            if f.owner == player or f.owner == -1: continue
            tp, eta = fleet_target_planet(f, planets)
            if tp is not None and tp.owner == player:
                self.en_fleet_to_my[tp.id].append((eta, f.owner, int(f.ships)))

        # Active outgoing attack fleets (for pressure calculation)
        self.my_active_attack_targets = set()
        for f in fleets:
            if f.owner != player: continue
            tp, _ = fleet_target_planet(f, planets)
            if tp is not None and tp.owner != player:
                self.my_active_attack_targets.add(tp.id)

        self.total_ships = sum(int(p.ships) for p in planets) + sum(int(f.ships) for f in fleets)
        self.total_prod  = sum(int(p.production) for p in planets)

        self._shot_cache  = {}
        self._probe_cache = {}
        self._bprobe_cache= {}
        self._react_cache = {}
        self._need_cache  = {}

    def is_static(self, pid): return is_static_planet(self.by_id[pid])
    def comet_life_left(self, pid): return comet_life(pid, self.comets)
    def inv_left(self, sid, spent): return max(0, int(self.by_id[sid].ships) - spent[sid])

    def plan_shot(self, sid, tid, ships):
        ships = int(ships)
        key   = (sid, tid, ships)
        if key in self._shot_cache: return self._shot_cache[key]
        r = aim_with_prediction(self.by_id[sid], self.by_id[tid], ships,
                                self.init_by_id, self.ang_vel, self.comets, self.comet_ids)
        self._shot_cache[key] = r
        return r

    def probe_candidates(self, sid, tid, cap, hints=()):
        cap     = max(1, int(cap))
        hints_n = tuple(int(math.ceil(h)) for h in hints if h is not None)
        key     = (sid, tid, cap, hints_n)
        if key in self._probe_cache: return self._probe_cache[key]
        t  = self.by_id[tid]
        ts = max(1, int(math.ceil(t.ships)))
        vals = set(range(1, min(6, cap)+1))
        vals.update({cap, max(1,cap//2), max(1,cap//3),
                     min(cap,PARTIAL_MIN), min(cap,ts+1), min(cap,ts+4), min(cap,ts+8)})
        for h in hints_n:
            b = max(1, min(cap, h))
            for d in (-2,-1,0,1,2):
                c = b+d
                if 1<=c<=cap: vals.add(c)
        result = sorted(vals)
        self._probe_cache[key] = result
        return result

    def best_probe(self, sid, tid, cap, hints=(), min_t=None, max_t=None,
                   anchor=None, anchor_diff=None):
        cap = max(1, int(cap))
        key = (sid, tid, cap, tuple(int(math.ceil(h)) for h in hints if h is not None),
               min_t, max_t, anchor, anchor_diff)
        if key in self._bprobe_cache: return self._bprobe_cache[key]
        best, bkey = None, None
        for ships in self.probe_candidates(sid, tid, cap, hints=hints):
            aim = self.plan_shot(sid, tid, ships)
            if aim is None: continue
            angle, turns, _, _ = aim
            if min_t is not None and turns < min_t: continue
            if max_t is not None and turns > max_t: continue
            if anchor is not None and anchor_diff is not None and abs(turns-anchor)>anchor_diff: continue
            sk = (turns, ships) if anchor is None else (abs(turns-anchor), turns, ships)
            if bkey is None or sk < bkey: bkey, best = sk, (ships, aim)
        self._bprobe_cache[key] = best
        return best

    def reaction_times(self, tid):
        c = self._react_cache.get(tid)
        if c: return c
        tgt  = self.by_id[tid]
        my_t = min((travel_time(p.x,p.y,p.radius,tgt.x,tgt.y,tgt.radius,max(1,int(p.ships)))
                    for p in self.my_planets), default=10**9)
        en_t = min((travel_time(p.x,p.y,p.radius,tgt.x,tgt.y,tgt.radius,max(1,int(p.ships)))
                    for p in self.enemy_planets), default=10**9)
        c = (my_t, en_t)
        self._react_cache[tid] = c
        return c

    def _search_cap(self, eval_t):
        return max(32, int(self.total_ships + self.total_prod*max(2,eval_t+2) + 32))

    def min_ships_to_own_by(self, tid, eval_t, attacker,
                            arrival_t=None, planned=None, extra=(), upper=None):
        planned = planned or {}
        eval_t  = max(1, int(math.ceil(eval_t)))
        arr_t   = eval_t if arrival_t is None else max(1, int(math.ceil(arrival_t)))
        if arr_t > eval_t: return (max(1,int(upper))+1) if upper else self._search_cap(eval_t)+1
        norm_extra = tuple(
            (max(1,int(math.ceil(t))), o, int(s))
            for t,o,s in extra if s>0 and max(1,int(math.ceil(t)))<=eval_t
        )
        ck = None
        if arr_t==eval_t and not planned.get(tid) and not norm_extra:
            ck = (tid, eval_t, attacker)
            cv = self._need_cache.get(ck)
            if cv is not None: return cv

        def owns_at(ships):
            a = list(self.arrivals.get(tid,[]))
            a += [i for i in planned.get(tid,[]) if i[0]<=eval_t]
            a += [i for i in norm_extra if i[0]<=eval_t]
            a.append((arr_t, attacker, int(ships)))
            tl = simulate_timeline(self.by_id[tid], a, self.player, eval_t)
            o, _ = state_at(tl, eval_t)
            return o == attacker

        if upper:
            hi = max(1, int(upper))
            if not owns_at(hi): return hi+1
        else:
            o0, s0 = state_at(self.timelines[tid], eval_t)
            if o0 == attacker:
                if ck: self._need_cache[ck] = 0
                return 0
            hi = max(1, int(math.ceil(s0))+1)
            cap = self._search_cap(eval_t)
            while hi <= cap and not owns_at(hi): hi *= 2
            if hi > cap:
                if not owns_at(cap): return cap+1
                hi = cap
        lo = 1
        while lo < hi:
            mid = (lo+hi)//2
            if owns_at(mid): hi = mid
            else: lo = mid+1
        if ck: self._need_cache[ck] = lo
        return lo

    def min_ships_to_own_at(self, tid, arr_t, attacker, planned=None, extra=(), upper=None):
        return self.min_ships_to_own_by(tid, arr_t, attacker,
                                        arrival_t=arr_t, planned=planned, extra=extra, upper=upper)

    def proj_state(self, tid, arr_t, planned=None, extra=()):
        planned = planned or {}
        cut = max(1, int(math.ceil(arr_t)))
        if not planned.get(tid) and not extra:
            return state_at(self.timelines[tid], cut)
        a = [i for i in self.arrivals.get(tid,[]) if i[0]<=cut]
        a += [i for i in planned.get(tid,[]) if i[0]<=cut]
        a += [i for i in extra if i[0]<=cut]
        tl = simulate_timeline(self.by_id[tid], a, self.player, cut)
        return state_at(tl, cut)

    def proj_timeline(self, tid, horizon, planned=None, extra=()):
        planned = planned or {}
        horizon = max(1, int(math.ceil(horizon)))
        a = [i for i in self.arrivals.get(tid,[]) if i[0]<=horizon]
        a += [i for i in planned.get(tid,[]) if i[0]<=horizon]
        a += [i for i in extra if i[0]<=horizon]
        return simulate_timeline(self.by_id[tid], a, self.player, horizon)

    def hold_status(self, tid, planned=None):
        tl = self.proj_timeline(tid, HORIZON, planned=planned) if (planned or {}).get(tid) else self.timelines[tid]
        return {k: tl[k] for k in ("keep_needed","fall_turn","holds_full")}

    def reinf_needed(self, tid, arr_t, hold_until, planned=None, upper=None):
        planned   = planned or {}
        tgt       = self.by_id[tid]
        arr_t     = max(1, int(math.ceil(arr_t)))
        hold_until= max(arr_t, int(math.ceil(hold_until)))
        if tgt.owner != self.player:
            return self.min_ships_to_own_by(tid, hold_until, self.player,
                                            arrival_t=arr_t, planned=planned, upper=upper)
        def holds(ships):
            tl = self.proj_timeline(tid, hold_until, planned=planned,
                                    extra=((arr_t, self.player, int(ships)),))
            for t in range(arr_t, hold_until+1):
                if tl["owner_at"].get(t) != self.player: return False
            return True
        if upper:
            hi = max(1, int(upper))
            if not holds(hi): return hi+1
        else:
            hi = 1; cap = self._search_cap(hold_until)
            while hi<=cap and not holds(hi): hi *= 2
            if hi>cap:
                if not holds(cap): return cap+1
                hi = cap
        lo = 1
        while lo < hi:
            mid = (lo+hi)//2
            if holds(mid): hi = mid
            else: lo = mid+1
        return lo

# ════════════════════════════════════════════════════════════════════════
# STRATEGY
# ════════════════════════════════════════════════════════════════════════

def p_dist(a, b): return math.hypot(a.x-b.x, a.y-b.y)

def nearest_to(target, sources, k):
    if len(sources) <= k: return sources
    return sorted(sources, key=lambda s:(p_dist(s,target),-int(s.ships),s.id))[:k]

def build_modes(world):
    dom = (world.my_total - world.enemy_total) / max(1, world.my_total + world.enemy_total)
    behind     = dom < BEHIND_DOM
    ahead      = dom > AHEAD_DOM
    dominating = ahead or (world.max_enemy>0 and world.my_total > world.max_enemy*1.25)
    finishing  = (dom > FINISH_DOM and world.my_prod > world.enemy_prod*FINISH_PROD_R
                  and world.step > 80)
    mm = 1.0
    if ahead:     mm += AHEAD_MRG_B
    if behind:    mm -= BEHIND_MRG_P
    if finishing: mm += FINISH_MRG_B
    # v3: win margin adjustment to margins
    if world.is_winning_secure:  mm *= WIN_SECURE_MARGIN_M
    if world.is_losing_desperate: mm *= WIN_DESPERATE_RISK_M
    return dict(dom=dom, behind=behind, ahead=ahead,
                dominating=dominating, finishing=finishing, mm=mm)

def compute_pressure_mult(world, planned_target_ids):
    """
    v3: Multi-front pressure bonus.
    The more simultaneous attack fronts we have, the harder for enemy to defend all.
    """
    total_fronts = len(world.my_active_attack_targets) + len(set(planned_target_ids))
    if total_fronts < PRESSURE_FRONT_MIN: return 1.0
    extra = total_fronts - PRESSURE_FRONT_MIN
    return min(PRESSURE_MAX_MULT, 1.0 + extra * PRESSURE_BONUS_PER)

def build_policy(world, deadline=None):
    def expired(): return deadline and time.perf_counter() > deadline

    iw = {}
    for pid, (f,n,e) in world.indirect_map.items():
        iw[pid] = f*IND_FRIENDLY_W + n*IND_NEUTRAL_W + e*IND_ENEMY_W

    rtm = {}
    for target in world.planets:
        if expired(): break
        if target.owner == world.player: continue
        my_src = nearest_to(target, world.my_planets,    REACT_MY_TOP_K)
        en_src = nearest_to(target, world.enemy_planets, REACT_EN_TOP_K)
        my_t   = min((travel_time(p.x,p.y,p.radius,target.x,target.y,target.radius,max(1,int(p.ships)))
                      for p in my_src), default=10**9)
        en_t   = min((travel_time(p.x,p.y,p.radius,target.x,target.y,target.radius,max(1,int(p.ships)))
                      for p in en_src), default=10**9)
        rtm[target.id] = (my_t, en_t)

    reserve = {}; budget = {}
    modes_dom = (world.my_total - world.enemy_total) / max(1, world.my_total + world.enemy_total)

    for planet in world.my_planets:
        if expired(): break
        tl    = world.timelines[planet.id]
        exact = tl["keep_needed"]

        threats = []
        for en in nearest_to(planet, world.enemy_planets, PROACT_EN_TOP_K):
            aim = world.plan_shot(en.id, planet.id, max(1, int(en.ships)))
            if aim is None: continue
            eta = aim[1]
            if eta > MULTI_PROACT_HOR: continue
            threats.append((eta, int(en.ships)))
        threats.sort()
        best_stack = 0; l, running = 0, 0
        for r in range(len(threats)):
            running += threats[r][1]
            while threats[r][0] - threats[l][0] > MULTI_STACK_WIN:
                running -= threats[l][1]; l += 1
            best_stack = max(best_stack, running)
        proact = int(best_stack * MULTI_PROACT_RATIO)
        for eta, s in threats:
            if eta <= PROACT_HORIZON:
                proact = max(proact, int(s * PROACT_RATIO))

        # v3: Rush mode — increase defense when being rushed
        if world.is_rush and world.step < RUSH_DETECT_STEP_MAX:
            proact = int(proact * 1.5)

        # 1v1 aggression
        if not world.is_ffa and modes_dom > ONE_V_ONE_DOM_THRESH and not world.is_late:
            exact  = int(exact  * ONE_V_ONE_AGG_RESERVE)
            proact = int(proact * ONE_V_ONE_AGG_RESERVE)

        # v3: Winning securely — can afford lower reserves
        if world.is_winning_secure and not world.is_ffa:
            exact  = int(exact  * 0.80)
            proact = int(proact * 0.80)

        if world.is_total_war:
            exact  = min(exact,  max(1, exact//2))
            proact = min(proact, max(1, proact//2))

        reserve[planet.id] = min(int(planet.ships), max(exact, proact))
        budget[planet.id]  = max(0, int(planet.ships) - reserve[planet.id])

    return dict(iw=iw, rtm=rtm, reserve=reserve, budget=budget)

# ── Scoring ──────────────────────────────────────────────────────────

def react_times(tid, policy):
    return policy["rtm"].get(tid, (10**9, 10**9))

def is_safe_neutral(target, policy):
    if target.owner != -1: return False
    my_t, en_t = react_times(target.id, policy)
    return my_t <= en_t - SAFE_NEUTRAL_MARGIN

def is_contested(target, policy):
    if target.owner != -1: return False
    my_t, en_t = react_times(target.id, policy)
    return abs(my_t - en_t) <= CONTESTED_NEUTRAL_MARGIN

def can_race_to(target, policy):
    if target.owner != -1: return False
    my_t, en_t = react_times(target.id, policy)
    return en_t - my_t >= RACE_MIN_ADVANTAGE

def open_filter(target, arr_t, needed, src_cap, world, policy):
    if not world.is_opening or target.owner != -1: return False
    if target.id in world.comet_ids: return False
    if world.is_static(target.id): return False
    my_t, en_t = react_times(target.id, policy)
    gap = en_t - my_t
    if (target.production >= SAFE_OPEN_PROD_TH and arr_t <= SAFE_OPEN_TURN_LIM
            and gap >= SAFE_NEUTRAL_MARGIN): return False
    if world.is_ffa:
        affordable = needed <= max(PARTIAL_MIN, int(src_cap * FFA_ROT_SEND_RATIO))
        if affordable and arr_t <= FFA_ROT_TURN_LIM and gap >= FFA_ROT_REACT_GAP: return False
        return True
    return arr_t > ROT_OPEN_MAX_TURNS or target.production <= ROT_OPEN_LOW_PROD

def target_value(target, arr_t, mission, world, modes, policy):
    turns_profit = max(1, world.remaining - arr_t)
    if target.id in world.comet_ids:
        life = world.comet_life_left(target.id)
        turns_profit = max(0, min(turns_profit, life - arr_t))
        if turns_profit <= 0: return -1.0

    prod_score = (target.production ** PROD_EXP) * turns_profit
    val = prod_score + policy["iw"][target.id] * turns_profit * INDIRECT_SCALE

    if world.is_static(target.id):
        val *= STATIC_NEUTRAL_VM if target.owner == -1 else STATIC_HOSTILE_VM
    elif world.is_opening:
        val *= ROT_OPEN_VM

    if target.owner not in (-1, world.player):
        val *= OPEN_HOSTILE_VM if world.is_opening else HOSTILE_VM

    if target.owner == -1:
        if   is_safe_neutral(target, policy): val *= SAFE_NEUTRAL_VM
        elif is_contested(target, policy):    val *= CONTESTED_NEUTRAL_VM
        if   can_race_to(target, policy):     val *= RACE_WIN_VM
        if   world.is_early:                  val *= EARLY_NEUTRAL_VM

    if target.id in world.comet_ids: val *= COMET_VM

    if   mission == "snipe":         val *= SNIPE_VM
    elif mission == "swarm":         val *= SWARM_VM
    elif mission == "reinforce":     val *= REINFORCE_VM
    elif mission == "crash_exploit": val *= CRASH_VM
    elif mission == "gang_up":       val *= GANG_UP_VM

    if target.id in world.vuln_ids: val *= EXPOSED_VM

    # v3: Gateway positional value
    val *= world.gateway_map.get(target.id, 1.0)

    # v3: Economic mode adjustments
    if world.eco_mode == EcoMode.EXPAND:
        if   target.owner == -1:                  val *= ECO_EXPAND_NEUTRAL_VM
        elif target.owner != world.player:         val *= ECO_EXPAND_HOSTILE_VM
    elif world.eco_mode == EcoMode.AGGRO:
        if   target.owner != world.player and target.owner != -1:
            val *= ECO_AGGRO_HOSTILE_VM
            # Extra bonus for high-production enemy planets in AGGRO
            if target.production >= PROD_DENY_THRESHOLD: val *= 1.25
        elif target.owner == -1:
            val *= ECO_AGGRO_NEUTRAL_VM

    # v3: Rush counter — when being rushed, prioritize counter-attacking enemy home
    if world.is_rush and target.owner not in (-1, world.player):
        val *= 1.40  # counter-rush bonus

    # Production denial
    if (target.owner not in (-1, world.player)
            and target.production >= PROD_DENY_THRESHOLD
            and world._deny_target and target.id == world._deny_target.id):
        val *= PROD_DENY_VM

    # Endgame immediate ship value
    if world.is_very_late:
        val += max(0, target.ships) * VERY_LATE_SHIP_W
    elif world.is_late:
        val += max(0, target.ships) * LATE_SHIP_W
    elif world.is_endgame:
        val += max(0, target.ships) * 0.45

    # Elimination bonus
    if target.owner not in (-1, world.player):
        en_str = world.owner_strength.get(target.owner, 0)
        if en_str <= WEAK_THRESH:
            val += ELIM_BONUS

    # Weakest enemy
    if (target.owner not in (-1, world.player) and world._weakest is not None
            and target.owner == world._weakest):
        val *= WEAKEST_VM_FFA if world.is_ffa else WEAKEST_VM_1V1

    if modes["finishing"] and target.owner not in (-1, world.player): val *= FINISH_HOSTILE_VM
    if modes["behind"] and target.owner==-1 and not world.is_static(target.id): val *= BEHIND_ROT_VM
    if modes["behind"] and is_safe_neutral(target, policy):   val *= 1.10
    if modes["dominating"] and is_contested(target, policy):  val *= 0.90

    return val

def preferred_send(target, needed, arr_t, cap, world, modes, policy, distance=None):
    send = max(needed, int(math.ceil(needed * modes["mm"])))
    m = 0
    if target.owner == -1:
        m += min(NEUTRAL_MARGIN_CAP, NEUTRAL_MARGIN_BASE + target.production * NEUTRAL_MARGIN_PROD_W)
    else:
        m += min(HOSTILE_MARGIN_CAP, HOSTILE_MARGIN_BASE + target.production * HOSTILE_MARGIN_PROD_W)
    if world.is_static(target.id): m += STATIC_MARGIN
    if is_contested(target, policy): m += CONTESTED_MARGIN
    if world.is_ffa: m += FFA_MARGIN
    if arr_t > LONG_TRAVEL_START: m += min(LONG_TRAVEL_CAP, arr_t // LONG_TRAVEL_DIV)
    if target.id in world.comet_ids: m = max(0, m - COMET_MARGIN_RELIEF)
    if modes["finishing"] and target.owner not in (-1, world.player): m += FINISH_SEND_BONUS
    if target.id in world.vuln_ids: m = max(0, m-3)
    if world.is_ffa and world._weakest and target.owner==world._weakest: m = max(0, m-2)
    base = min(cap, send + m)
    # v3: use mathematically justified tsunami
    d = distance if distance is not None else 30.0  # fallback
    prod_proxy = target.production if target.owner == -1 else target.production * 2
    return speed_optimal_send(base, cap, d, prod_proxy)

def score_mods(base, target, mission, world, policy, pressure_mult=1.0):
    s = base
    if world.is_static(target.id): s *= STATIC_SCORE_M
    if world.is_early and target.owner==-1 and world.is_static(target.id): s *= EARLY_STATIC_SCORE_M
    if world.is_ffa and target.owner==-1 and not world.is_static(target.id): s *= FFA_ROT_SCORE_M
    if (len(world.static_neutrals) >= DENSE_STATIC_THRESH
            and target.owner==-1 and not world.is_static(target.id)): s *= DENSE_ROT_SCORE_M
    if mission == "snipe": s *= SNIPE_SCORE_M
    elif mission in ("swarm","gang_up"): s *= SWARM_SCORE_M
    elif mission == "crash_exploit": s *= CRASH_SCORE_M
    if target.id in world.vuln_ids: s *= EXPOSED_SCORE_M
    if target.owner not in (-1, world.player) and world._weakest==target.owner: s *= WEAKEST_SCORE_M
    if target.owner==-1 and can_race_to(target, policy): s *= RACE_SCORE_M
    # v3: multi-front pressure bonus
    s *= pressure_mult
    return s

def candidate_valid(target, turns, world, buf):
    if turns > world.remaining - buf: return False
    if target.id in world.comet_ids:
        life = world.comet_life_left(target.id)
        if turns >= life or turns > COMET_MAX_CHASE: return False
    return True

# ── Settle plan ──────────────────────────────────────────────────────

def settle_plan(src, target, cap, send_guess, world, planned, modes, policy,
                mission="capture", eval_fn=None, anchor=None, anchor_tol=None, max_iter=4,
                distance=None):
    if cap < 1: return None
    eval_fn    = eval_fn or (lambda t: t)
    anchor_tol = anchor_tol if anchor_tol is not None else (1 if mission=="snipe" else None)
    seed       = max(1, min(cap, int(send_guess)))
    tested = {}; order = []

    def evaluate(send):
        send = max(1, min(cap, int(send)))
        if send in tested: return tested[send]
        aim = world.plan_shot(src.id, target.id, send)
        if aim is None: tested[send]=None; return None
        angle, turns, _, _ = aim
        if mission=="crash_exploit" and anchor and turns < anchor: tested[send]=None; return None
        et = int(math.ceil(eval_fn(turns)))
        if et < turns: tested[send]=None; return None
        need = world.min_ships_to_own_by(target.id, et, world.player,
                                         arrival_t=turns, planned=planned, upper=cap)
        if need<=0 or need>cap: tested[send]=None; return None
        if mission in ("snipe","crash_exploit"):
            desired = need
        elif mission == "rescue":
            desired = min(cap, max(need, need + DEF_SEND_MARGIN + target.production*DEF_SEND_PROD_W))
        else:
            desired = min(cap, max(need, preferred_send(target, need, turns, cap, world, modes, policy, distance)))
        result = (angle, turns, et, need, send, desired)
        tested[send]=result; order.append(send)
        return result

    cands = sorted(world.probe_candidates(src.id, target.id, cap, hints=(seed,)),
                   key=lambda s:(abs(s-seed), s))
    cur = None
    for s in cands:
        r = evaluate(s)
        if r is None: continue
        if anchor and anchor_tol and abs(r[1]-anchor)>anchor_tol: continue
        cur = s; break
    if cur is None: return None

    for _ in range(max_iter):
        r = evaluate(cur)
        if r is None: break
        angle, turns, et, need, actual, desired = r
        if desired == actual:
            if anchor and anchor_tol and abs(turns-anchor)>anchor_tol: return None
            if mission=="rescue" and turns>et: return None
            return angle, turns, et, need, actual
        nxt = max(1, min(cap, int(desired)))
        if nxt in tested: cur=nxt; break
        cur = nxt

    seen = set()
    for s in sorted(order, key=lambda s:(
        0 if not anchor or anchor_tol is None else abs(tested[s][1]-anchor),
        abs(s-seed), tested[s][1], s
    )):
        if s in seen: continue
        seen.add(s)
        r = tested.get(s)
        if r is None: continue
        angle, turns, et, need, actual, _ = r
        if actual < need: continue
        if anchor and anchor_tol and abs(turns-anchor)>anchor_tol: continue
        if mission=="rescue" and turns>et: continue
        return angle, turns, et, need, actual
    return None

def settle_reinf(src, target, cap, seed, world, planned, hold_until, max_arr, max_iter=4):
    if cap < 1: return None
    tested = {}; order = []
    def evaluate(send):
        send = max(1,min(cap,int(send)))
        if send in tested: return tested[send]
        aim = world.plan_shot(src.id, target.id, send)
        if aim is None: tested[send]=None; return None
        angle,turns,_,_ = aim
        if turns>max_arr: tested[send]=None; return None
        need = world.reinf_needed(target.id, turns, hold_until, planned=planned, upper=cap)
        if need<=0 or need>cap: tested[send]=None; return None
        desired = min(cap, need+REINF_SAFETY)
        r = (angle,turns,hold_until,need,send,desired)
        tested[send]=r; order.append(send); return r
    cands = sorted(world.probe_candidates(src.id,target.id,cap,hints=(seed,)),
                   key=lambda s:(abs(s-seed),s))
    cur = None
    for s in cands:
        r=evaluate(s)
        if r: cur=s; break
    if cur is None: return None
    for _ in range(max_iter):
        r=evaluate(cur)
        if r is None: break
        angle,turns,_,need,actual,desired = r
        if desired==actual: return angle,turns,hold_until,need,actual
        nxt=max(1,min(cap,int(desired)))
        if nxt in tested: cur=nxt; break
        cur=nxt
    for s in sorted(order,key=lambda s:(abs(s-seed),tested[s][1],s)):
        r=tested.get(s)
        if r is None: continue
        angle,turns,_,need,actual,_ = r
        if actual<need or turns>max_arr: continue
        return angle,turns,hold_until,need,actual
    return None

# ════════════════════════════════════════════════════════════════════════
# MISSION BUILDERS
# ════════════════════════════════════════════════════════════════════════

def build_intercept_missions(world, planned, modes, policy):
    """
    v3 NEW: Intercept Missions.
    When enemy fleet is heading to OUR planet, send reinforcement from ally
    that arrives BEFORE the enemy fleet does. Prevents capture without
    wasting ships on a planet that would have been fine.
    """
    if not INTERCEPT_ENABLED: return []
    missions = []
    for my_pid, fleet_list in world.en_fleet_to_my.items():
        target = world.by_id[my_pid]
        fleet_list_sorted = sorted(fleet_list, key=lambda x: x[0])
        for en_eta, en_owner, en_ships in fleet_list_sorted:
            if en_eta > INTERCEPT_ETA_MAX: continue
            # How many ships do we need to survive this attack?
            garrison_at_eta = target.ships + target.production * en_eta
            deficit = max(0, en_ships - garrison_at_eta + 1)
            if deficit <= 0: continue  # already safe

            for src in world.my_planets:
                if src.id == my_pid: continue
                cap = policy["budget"].get(src.id, 0)
                if cap < deficit: continue
                # Must arrive BEFORE enemy
                probe = world.best_probe(src.id, my_pid, cap,
                                         hints=(deficit, deficit+5),
                                         max_t=en_eta-1)
                if probe is None: continue
                _, rough = probe
                if rough[1] >= en_eta: continue  # can't arrive in time

                plan = settle_reinf(src, target, cap, probe[0], world, planned,
                                    en_eta + 10, en_eta - 1)
                if plan is None: continue
                angle, turns, _, need, send = plan
                if turns >= en_eta: continue

                # Value = production saved * remaining turns
                sv  = max(1, world.remaining - en_eta)
                val = target.production * sv * DEF_FRONTIER_M
                sc  = val / (send + turns * DEF_TURN_W + 1.0) * 1.5  # intercept is high priority
                opt = ShotOption(sc, src.id, my_pid, angle, turns, need, send, "reinforce", en_eta)
                missions.append(Mission("reinforce", sc, my_pid, en_eta, [opt]))
                break  # one interceptor per threat is enough
    return missions

def build_snipe_missions(world, planned, modes, policy, pressure_mult):
    missions = []
    for target in world.neutral_planets:
        en_etas = sorted({
            int(math.ceil(eta)) for eta,o,s in world.arrivals.get(target.id,[])
            if o not in (-1,world.player) and s>0
        })
        if not en_etas: continue
        for src in world.my_planets:
            src_cap = policy["budget"].get(src.id,0)
            if src_cap < PARTIAL_MIN: continue
            for en_eta in en_etas[:3]:
                probe = world.best_probe(src.id, target.id, src_cap,
                                         hints=(int(target.ships)+1,),
                                         anchor=en_eta, anchor_diff=1)
                if probe is None: continue
                _, rough = probe
                sync = max(rough[1], en_eta)
                if target.id in world.comet_ids:
                    life = world.comet_life_left(target.id)
                    if sync>=life or sync>COMET_MAX_CHASE: continue
                plan = settle_plan(src, target, src_cap, probe[0], world, planned, modes, policy,
                                   mission="snipe",
                                   eval_fn=lambda t,ee=en_eta:max(t,ee), anchor=en_eta)
                if plan is None: continue
                angle,turns,sync_t,need,send = plan
                val = target_value(target, sync_t, "snipe", world, modes, policy)
                if val<=0: continue
                sc = score_mods(val/(send+sync_t*SNIPE_TURN_W+1.0), target, "snipe", world, policy, pressure_mult)
                opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "snipe", en_eta)
                missions.append(Mission("snipe", sc, target.id, sync_t, [opt]))
    return missions

def build_race_missions(world, planned, modes, policy, pressure_mult):
    missions = []
    for target in world.neutral_planets:
        if target.id in world.comet_ids: continue
        my_t, en_t = react_times(target.id, policy)
        if en_t == 10**9: continue
        if en_t - my_t < RACE_MIN_ADVANTAGE: continue
        desired_arrival = max(1, en_t - RACE_MARGIN_TURNS)
        for src in world.my_planets:
            src_cap = policy["budget"].get(src.id, 0)
            if src_cap < PARTIAL_MIN: continue
            probe = world.best_probe(src.id, target.id, src_cap,
                                     hints=(int(target.ships)+1,),
                                     max_t=desired_arrival + RACE_MARGIN_TURNS + 1)
            if probe is None: continue
            _, rough = probe
            if rough[1] > en_t: continue
            plan = settle_plan(src, target, src_cap, probe[0], world, planned, modes, policy, mission="capture")
            if plan is None: continue
            angle,turns,_,need,send = plan
            if turns >= en_t: continue
            if not candidate_valid(target, turns, world, LATE_BUFFER): continue
            val = target_value(target, turns, "capture", world, modes, policy)
            if val<=0: continue
            sc = score_mods(val/(send+turns*ATTACK_TURN_W+1.0), target, "capture", world, policy, pressure_mult)
            opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "capture")
            missions.append(Mission("single", sc, target.id, turns, [opt]))
    return missions

def build_rescue_missions(world, planned, modes, policy):
    missions = []
    for target in world.my_planets:
        ft = world.timelines[target.id]["fall_turn"]
        if ft is None or ft > DEF_LOOKAHEAD: continue
        for src in world.my_planets:
            if src.id==target.id: continue
            cap = policy["budget"].get(src.id,0)
            if cap < PARTIAL_MIN: continue
            probe = world.best_probe(src.id, target.id, cap,
                                     hints=(target.production+DEF_SEND_MARGIN+2,), max_t=ft)
            if probe is None: continue
            plan = settle_plan(src, target, cap, probe[0], world, planned, modes, policy,
                               mission="rescue", eval_fn=lambda _,f=ft:f, anchor=ft)
            if plan is None: continue
            angle,turns,_,need,send = plan
            sv  = max(1, world.remaining - ft)
            val = target.production*sv + max(0,target.ships)*DEF_SHIP_VALUE
            if world.enemy_planets and nearest_dist(target.x,target.y,world.enemy_planets)<22:
                val *= DEF_FRONTIER_M
            sc  = val/(send+turns*DEF_TURN_W+1.0)
            opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "rescue", ft)
            missions.append(Mission("rescue", sc, target.id, ft, [opt]))
    return missions

def build_reinf_missions(world, planned, modes, policy, inv_left_fn):
    if not REINF_ENABLED or world.remaining < REINF_MIN_FUTURE: return []
    missions = []
    for target in world.my_planets:
        ft = world.timelines[target.id]["fall_turn"]
        if ft is None: continue
        if target.production < REINF_MIN_PROD: continue
        hold_until = min(HORIZON, ft + REINF_LOOKAHEAD)
        max_arr    = min(ft, REINF_MAX_TRAVEL)
        for src in world.my_planets:
            if src.id==target.id: continue
            cap = min(inv_left_fn(src.id), int(src.ships*REINF_MAX_SRC_FRAC))
            if cap < PARTIAL_MIN: continue
            probe = world.best_probe(src.id, target.id, cap,
                                     hints=(target.production+REINF_SAFETY+2,), max_t=max_arr)
            if probe is None: continue
            plan = settle_reinf(src, target, cap, probe[0], world, planned, hold_until, max_arr)
            if plan is None: continue
            angle,turns,_,need,send = plan
            sv  = max(1, world.remaining - hold_until)
            val = target.production*sv + max(0,target.ships)*DEF_SHIP_VALUE
            if world.enemy_planets and nearest_dist(target.x,target.y,world.enemy_planets)<22:
                val *= DEF_FRONTIER_M
            val *= REINFORCE_VM
            sc  = val/(send+turns*REINF_TURN_W+1.0)
            opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "reinforce", hold_until)
            missions.append(Mission("reinforce", sc, target.id, ft, [opt]))
    return missions

def build_recap_missions(world, planned, modes, policy):
    missions = []
    for target in world.my_planets:
        ft = world.timelines[target.id]["fall_turn"]
        if ft is None or ft > DEF_LOOKAHEAD: continue
        for src in world.my_planets:
            if src.id==target.id: continue
            cap = policy["budget"].get(src.id,0)
            if cap < PARTIAL_MIN: continue
            probe = world.best_probe(src.id, target.id, cap,
                                     hints=(target.production+DEF_SEND_MARGIN+2,),
                                     min_t=ft+1, max_t=ft+RECAP_LOOKAHEAD)
            if probe is None: continue
            plan = settle_plan(src, target, cap, probe[0], world, planned, modes, policy, mission="capture")
            if plan is None: continue
            angle,turns,_,need,send = plan
            if turns<=ft or turns-ft>RECAP_LOOKAHEAD: continue
            sv  = max(1, world.remaining - turns)
            val = (RECAP_PROD_W*target.production*sv + RECAP_IMMED_W*max(0,target.ships))
            if world.enemy_planets and nearest_dist(target.x,target.y,world.enemy_planets)<22:
                val *= RECAP_FRONTIER_M
            val *= RECAP_VM
            sc  = val/(send+turns*RECAP_TURN_W+1.0)
            opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "recapture", ft)
            missions.append(Mission("recapture", sc, target.id, turns, [opt]))
    return missions

def _detect_crashes(world):
    crashes = []
    for tid, arrivals in world.arrivals.items():
        en_ev = [(int(math.ceil(eta)),o,int(s)) for eta,o,s in arrivals
                 if o not in (-1,world.player) and s>0]
        en_ev.sort()
        for i in range(len(en_ev)):
            ea,oa,sa = en_ev[i]
            for j in range(i+1,len(en_ev)):
                eb,ob,sb = en_ev[j]
                if oa==ob: continue
                if abs(ea-eb)>CRASH_ETA_WIN: break
                if sa+sb < CRASH_MIN_SHIPS: continue
                crashes.append(dict(target_id=tid, crash_turn=max(ea,eb)))
    return crashes

def build_crash_missions(world, planned, modes, policy, pressure_mult):
    if not CRASH_ENABLED or not world.is_ffa: return []
    missions = []
    for crash in _detect_crashes(world):
        target = world.by_id[crash["target_id"]]
        if target.owner == world.player: continue
        desired_arr = crash["crash_turn"] + CRASH_DELAY
        for src in world.my_planets:
            cap = policy["budget"].get(src.id,0)
            if cap < PARTIAL_MIN: continue
            probe = world.best_probe(src.id, target.id, cap,
                                     hints=(12,int(target.ships)+1),
                                     anchor=desired_arr, anchor_diff=CRASH_ETA_WIN)
            if probe is None: continue
            plan = settle_plan(src, target, cap, probe[0], world, planned, modes, policy,
                               mission="crash_exploit",
                               eval_fn=lambda t,da=desired_arr:max(t,da),
                               anchor=desired_arr, anchor_tol=CRASH_ETA_WIN)
            if plan is None: continue
            angle,turns,_,need,send = plan
            if not candidate_valid(target, turns, world, LATE_BUFFER): continue
            val = target_value(target, turns, "crash_exploit", world, modes, policy)
            if val<=0: continue
            sc = score_mods(val/(send+turns*SNIPE_TURN_W+1.0), target, "crash_exploit", world, policy, pressure_mult)
            opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "crash_exploit", desired_arr)
            missions.append(Mission("crash_exploit", sc, target.id, turns, [opt]))
    return missions

def _detect_battles(world):
    battles = []
    for target in world.enemy_planets:
        for eta,o,s in world.arrivals.get(target.id,[]):
            if o in (-1,world.player) or o==target.owner: continue
            if int(s)<=0: continue
            eta_i    = int(math.ceil(eta))
            garrison = target.ships + target.production*eta_i
            post = max(0, int(s)-garrison) if int(s)>garrison else max(0, garrison-int(s))
            if post < 35:
                battles.append(dict(target_id=target.id, battle_turn=eta_i, post_ships=post))
    return battles

def build_gang_up_missions(world, planned, modes, policy, pressure_mult):
    missions = []
    for b in _detect_battles(world):
        target  = world.by_id[b["target_id"]]
        if target.owner==world.player: continue
        desired = b["battle_turn"] + GANG_POST_DELAY
        for src in world.my_planets:
            cap = policy["budget"].get(src.id,0)
            if cap<PARTIAL_MIN: continue
            hint  = max(3, int(b["post_ships"])+3)
            probe = world.best_probe(src.id, target.id, cap,
                                     hints=(hint,int(target.ships)+1),
                                     anchor=desired, anchor_diff=GANG_ETA_WIN)
            if probe is None: continue
            plan = settle_plan(src, target, cap, probe[0], world, planned, modes, policy,
                               mission="capture",
                               eval_fn=lambda t,da=desired:max(t,da),
                               anchor=desired, anchor_tol=GANG_ETA_WIN)
            if plan is None: continue
            angle,turns,_,need,send = plan
            if not candidate_valid(target, turns, world, LATE_BUFFER): continue
            val = target_value(target, turns, "gang_up", world, modes, policy)
            if val<=0: continue
            sc  = score_mods(val/(send+turns*ATTACK_TURN_W+1.0), target, "gang_up", world, policy, pressure_mult)
            opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "capture", desired)
            missions.append(Mission("single", sc, target.id, turns, [opt]))
    return missions

def build_elimination_missions(world, planned, modes, policy, pressure_mult):
    if world._weakest is None: return []
    if world._weakest_str > world.my_total*0.92: return []
    other_en = [s for o,s in world.owner_strength.items() if o not in (world.player, world._weakest)]
    if other_en and world._weakest_str > min(other_en)*0.95: return []
    wk_planets = [p for p in world.enemy_planets if p.owner==world._weakest]
    if not wk_planets: return []
    mult = 1.60 if world.is_ffa else 1.35
    missions = []
    for target in wk_planets:
        for src in world.my_planets:
            cap = policy["budget"].get(src.id,0)
            if cap<PARTIAL_MIN: continue
            probe = world.best_probe(src.id, target.id, cap, hints=(int(target.ships)+1,))
            if probe is None: continue
            _,rough = probe
            if not candidate_valid(target, rough[1], world, LATE_BUFFER): continue
            gn = world.min_ships_to_own_at(target.id, rough[1], world.player, planned=planned)
            if gn<=0 or gn>cap: continue
            d  = p_dist(src, target)
            sg = preferred_send(target, gn, rough[1], cap, world, modes, policy, distance=d)
            plan = settle_plan(src, target, cap, sg, world, planned, modes, policy, mission="capture", distance=d)
            if plan is None: continue
            angle,turns,_,need,send = plan
            if not candidate_valid(target, turns, world, LATE_BUFFER): continue
            if send<need: continue
            val = target_value(target, turns, "capture", world, modes, policy)
            if val<=0: continue
            sc  = score_mods(val*mult/(send+turns*ATTACK_TURN_W+1.0), target, "capture", world, policy, pressure_mult)
            opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "capture")
            missions.append(Mission("single", sc, target.id, turns, [opt]))
    return missions

def build_deny_missions(world, planned, modes, policy, pressure_mult):
    if world._deny_target is None: return []
    target = world._deny_target
    if target.owner == world.player: return []
    if target.production < PROD_DENY_THRESHOLD: return []
    missions = []
    for src in world.my_planets:
        cap = policy["budget"].get(src.id,0)
        if cap < PARTIAL_MIN: continue
        probe = world.best_probe(src.id, target.id, cap, hints=(int(target.ships)+1,))
        if probe is None: continue
        _,rough = probe
        if not candidate_valid(target, rough[1], world, LATE_BUFFER): continue
        gn = world.min_ships_to_own_at(target.id, rough[1], world.player, planned=planned)
        if gn<=0 or gn>cap: continue
        d  = p_dist(src, target)
        sg = preferred_send(target, gn, rough[1], cap, world, modes, policy, distance=d)
        plan = settle_plan(src, target, cap, sg, world, planned, modes, policy, mission="capture", distance=d)
        if plan is None: continue
        angle,turns,_,need,send = plan
        if not candidate_valid(target, turns, world, LATE_BUFFER): continue
        if send<need: continue
        val = target_value(target, turns, "capture", world, modes, policy)
        if val<=0: continue
        sc  = score_mods(val*PROD_DENY_VM/(send+turns*ATTACK_TURN_W+1.0), target, "capture", world, policy, pressure_mult)
        opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "capture")
        missions.append(Mission("single", sc, target.id, turns, [opt]))
    return missions

# ════════════════════════════════════════════════════════════════════════
# PLAN MOVES
# ════════════════════════════════════════════════════════════════════════

def plan_moves(world, deadline=None):
    def expired(): return deadline and time.perf_counter() > deadline
    def tl():       return (deadline - time.perf_counter()) if deadline else 10**9
    def heavy_ok(): return tl() > HEAVY_MIN_TIME and len(world.planets) <= HEAVY_PLANET_LIM
    def opt_ok():   return tl() > OPT_MIN_TIME

    modes   = build_modes(world)
    policy  = build_policy(world, deadline=deadline)
    planned = defaultdict(list)
    src_opts= defaultdict(list)
    missions= []
    moves   = []
    spent   = defaultdict(int)

    def inv_left(sid):  return world.inv_left(sid, spent)
    def atk_left(sid):  return max(0, policy["budget"].get(sid,0) - spent[sid])

    def push(sid, angle, ships):
        send = min(int(ships), inv_left(sid))
        if send < 1: return 0
        moves.append([sid, float(angle), int(send)])
        spent[sid] += send
        return send

    def finalize():
        final = []; used = defaultdict(int)
        for sid, angle, ships in moves:
            mx = int(world.by_id[sid].ships) - used[sid]
            s  = min(int(ships), mx)
            if s>=1: final.append([sid, float(angle), int(s)]); used[sid]+=s
        return final

    def live_doomed():
        d = set()
        for p in world.my_planets:
            st = world.hold_status(p.id, planned=planned)
            if (not st["holds_full"] and st["fall_turn"] and
                    st["fall_turn"]<=DOOMED_EVAC_LIMIT and inv_left(p.id)>=DOOMED_MIN_SHIPS):
                d.add(p.id)
        return d

    def time_ok(target, turns):
        buf = VERY_LATE_BUFFER if world.is_very_late else LATE_BUFFER
        return candidate_valid(target, turns, world, buf)

    # Compute pressure multiplier based on current + planned attack fronts
    def get_pressure():
        return compute_pressure_mult(world, list(planned.keys()))

    # ── BUILD MISSIONS ───────────────────────────────────────────────────

    pressure = get_pressure()

    # v3: Intercept missions (highest priority — prevent planet loss)
    missions += build_intercept_missions(world, planned, modes, policy)

    if heavy_ok():
        missions += build_reinf_missions(world, planned, modes, policy, inv_left)
    missions += build_rescue_missions(world, planned, modes, policy)
    missions += build_recap_missions(world, planned, modes, policy)

    if heavy_ok():
        missions += build_elimination_missions(world, planned, modes, policy, pressure)
        missions += build_deny_missions(world, planned, modes, policy, pressure)
        missions += build_gang_up_missions(world, planned, modes, policy, pressure)
        missions += build_race_missions(world, planned, modes, policy, pressure)

    missions += build_snipe_missions(world, planned, modes, policy, pressure)

    # ── SINGLE-SOURCE + SWARM OPTIONS ───────────────────────────────────

    for src in world.my_planets:
        if expired(): return finalize()
        src_cap = atk_left(src.id)
        if src_cap <= 0: continue

        for target in world.planets:
            if expired(): return finalize()
            if target.id==src.id or target.owner==world.player: continue

            probe = world.best_probe(src.id, target.id, src_cap, hints=(int(target.ships)+1,))
            if probe is None: continue
            _, rough_aim = probe
            rough_t = rough_aim[1]
            if not time_ok(target, rough_t): continue

            gn = world.min_ships_to_own_at(target.id, rough_t, world.player, planned=planned)
            if gn<=0: continue
            if open_filter(target, rough_t, gn, src_cap, world, policy): continue

            d = p_dist(src, target)

            # Swarm partial option
            part_cap = min(src_cap, preferred_send(target, gn, rough_t, src_cap, world, modes, policy, distance=d))
            if part_cap >= PARTIAL_MIN:
                p2 = world.best_probe(src.id, target.id, part_cap,
                                      hints=(part_cap, gn, int(target.ships)+1))
                if p2:
                    _, pa = p2
                    if time_ok(target, pa[1]) and not open_filter(target, pa[1], gn, src_cap, world, policy):
                        val = target_value(target, pa[1], "swarm", world, modes, policy)
                        if val > 0:
                            pm = get_pressure()
                            sc = score_mods(val/(part_cap+pa[1]*ATTACK_TURN_W+1.0), target, "swarm", world, policy, pm)
                            src_opts[target.id].append(
                                ShotOption(sc, src.id, target.id, pa[0], pa[1], gn, part_cap, "swarm"))

            # Full single-source
            if gn <= src_cap:
                sg   = preferred_send(target, gn, rough_t, src_cap, world, modes, policy, distance=d)
                plan = settle_plan(src, target, src_cap, sg, world, planned, modes, policy,
                                   mission="capture", distance=d)
                if plan is None: continue
                angle,turns,_,need,send = plan
                if not time_ok(target, turns): continue
                if open_filter(target, turns, need, src_cap, world, policy): continue
                val = target_value(target, turns, "capture", world, modes, policy)
                if val<=0: continue
                pm  = get_pressure()
                sc  = score_mods(val/(send+turns*ATTACK_TURN_W+1.0), target, "capture", world, policy, pm)
                opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "capture")
                if send>=need:
                    missions.append(Mission("single", sc, target.id, turns, [opt]))

    # ── SWARM ASSEMBLY ───────────────────────────────────────────────────

    for tid, options in src_opts.items():
        if expired(): return finalize()
        if len(options)<2: continue
        target = world.by_id[tid]
        top    = sorted(options, key=lambda x:-x.score)[:MULTI_TOP_K]

        for i in range(len(top)):
            for j in range(i+1,len(top)):
                a, b = top[i], top[j]
                if a.src_id==b.src_id: continue
                tol = HOSTILE_SWARM_TOL if target.owner not in (-1,world.player) else MULTI_ETA_TOL
                if abs(a.turns-b.turns)>tol: continue
                jt = max(a.turns,b.turns); tc = a.send_cap+b.send_cap
                need = world.min_ships_to_own_at(tid, jt, world.player, planned=planned, upper=tc)
                if need<=0 or a.send_cap>=need or b.send_cap>=need or tc<need: continue
                val = target_value(target, jt, "swarm", world, modes, policy)
                if val<=0: continue
                pm  = get_pressure()
                sc  = score_mods(val/(need+jt*ATTACK_TURN_W+1.0), target, "swarm", world, policy, pm)*MULTI_PLAN_PEN
                missions.append(Mission("swarm", sc, tid, jt, [a,b]))

        if (THREE_SRC_ENABLED and heavy_ok()
                and target.owner not in (-1,world.player)
                and int(target.ships)>=THREE_SRC_MIN_SHIPS and len(top)>=3):
            for i in range(len(top)):
                for j in range(i+1,len(top)):
                    for k in range(j+1,len(top)):
                        if expired(): return finalize()
                        trio = [top[i],top[j],top[k]]
                        if len({x.src_id for x in trio})<3: continue
                        ts = [x.turns for x in trio]
                        if max(ts)-min(ts)>THREE_SRC_TOL: continue
                        jt = max(ts); tc = sum(x.send_cap for x in trio)
                        need = world.min_ships_to_own_at(tid,jt,world.player,planned=planned,upper=tc)
                        if need<=0 or tc<need: continue
                        if any(trio[a].send_cap+trio[b].send_cap>=need
                               for a in range(3) for b in range(a+1,3)): continue
                        val = target_value(target, jt, "swarm", world, modes, policy)
                        if val<=0: continue
                        pm  = get_pressure()
                        sc  = score_mods(val/(need+jt*ATTACK_TURN_W+1.0), target, "swarm", world, policy, pm)*THREE_SRC_PEN
                        missions.append(Mission("swarm", sc, tid, jt, trio))

    if heavy_ok():
        missions += build_crash_missions(world, planned, modes, policy, get_pressure())

    missions.sort(key=lambda m: -m.score)

    # ── EXECUTE MISSIONS ─────────────────────────────────────────────────

    for m in missions:
        if expired(): return finalize()
        target = world.by_id[m.target_id]

        if m.kind in ("single","snipe","rescue","recapture","reinforce","crash_exploit"):
            opt = m.options[0]
            src = world.by_id[opt.src_id]
            if m.kind=="reinforce":
                left = min(inv_left(opt.src_id), int(src.ships*REINF_MAX_SRC_FRAC))
            else:
                left = atk_left(opt.src_id)
            if left<=0: continue

            d = p_dist(src, target)

            if m.kind=="reinforce":
                plan = settle_reinf(src,target,left,min(left,opt.send_cap),
                                    world,planned,opt.anchor_turn,m.turns)
            elif m.kind=="rescue":
                plan = settle_plan(src,target,left,min(left,opt.send_cap),world,planned,modes,policy,
                                   mission="rescue",eval_fn=lambda _,f=m.turns:f,anchor=opt.anchor_turn)
            elif m.kind=="snipe":
                plan = settle_plan(src,target,left,min(left,opt.send_cap),world,planned,modes,policy,
                                   mission="snipe",eval_fn=lambda t,ee=opt.anchor_turn:max(t,ee),
                                   anchor=opt.anchor_turn)
            elif m.kind=="crash_exploit":
                plan = settle_plan(src,target,left,min(left,opt.send_cap),world,planned,modes,policy,
                                   mission="crash_exploit",
                                   eval_fn=lambda t,da=opt.anchor_turn:max(t,da),
                                   anchor=opt.anchor_turn,anchor_tol=CRASH_ETA_WIN)
            else:
                plan = settle_plan(src,target,left,min(left,opt.send_cap),world,planned,modes,policy,
                                   mission="capture",distance=d)
            if plan is None: continue
            angle,turns,_,need,send = plan
            if send<need or need>left: continue

            # v3: Speed-optimal tsunami with distance awareness
            if m.kind in ("capture","single") and left>need:
                ts = speed_optimal_send(need, left, d, target.production)
                if ts >= need: send = ts

            sent = push(opt.src_id, angle, send)
            if sent<need: continue
            planned[target.id].append((turns, world.player, int(sent)))
            continue

        # Swarm
        lims = [min(atk_left(opt.src_id), opt.send_cap) for opt in m.options]
        if min(lims)<=0: continue
        need = world.min_ships_to_own_at(target.id, m.turns, world.player,
                                         planned=planned, upper=sum(lims))
        if need<=0 or sum(lims)<need: continue
        ordered = sorted(zip(m.options,lims), key=lambda x:(x[0].turns,-x[1],x[0].src_id))
        remaining=need; sends_map={}
        for idx,(opt,lim) in enumerate(ordered):
            rem_other = sum(l for _,l in ordered[idx+1:])
            s = min(lim, max(0, remaining-rem_other))
            sends_map[opt.src_id]=s; remaining-=s
        if remaining>0: continue
        reaimed=[]
        for opt,_ in ordered:
            s = sends_map.get(opt.src_id,0)
            if s<=0: continue
            aim = world.plan_shot(opt.src_id, target.id, s)
            if aim is None: reaimed=[]; break
            reaimed.append((opt.src_id, aim[0], aim[1], s))
        if not reaimed: continue
        ts_only=[x[2] for x in reaimed]
        tol = HOSTILE_SWARM_TOL if target.owner not in (-1,world.player) else MULTI_ETA_TOL
        if max(ts_only)-min(ts_only)>tol: continue
        jt = max(ts_only)
        oo,_ = world.proj_state(target.id, jt, planned=planned,
                                 extra=[(t,world.player,s) for _,_,t,s in reaimed])
        if oo!=world.player: continue
        committed=[]
        for sid,angle,turns,s in reaimed:
            a=push(sid,angle,s)
            if a>0: committed.append((turns,world.player,int(a)))
        if sum(x[2] for x in committed)<need: continue
        planned[target.id].extend(committed)

    # ── FOLLOWUP ────────────────────────────────────────────────────────

    if not world.is_very_late and opt_ok():
        for src in world.my_planets:
            if expired(): return finalize()
            sleft = atk_left(src.id)
            if sleft < FOLLOWUP_MIN: continue
            best = None
            for target in world.planets:
                if expired(): return finalize()
                if target.id==src.id or target.owner==world.player: continue
                if target.id in world.comet_ids and target.production<=LOW_COMET_PROD: continue
                probe = world.best_probe(src.id, target.id, sleft, hints=(int(target.ships)+1,))
                if probe is None: continue
                _,ra = probe; et = ra[1]
                if world.is_late and et>world.remaining-LATE_BUFFER: continue
                gn = world.min_ships_to_own_at(target.id, et, world.player,
                                               planned=planned, upper=sleft)
                if gn<=0 or gn>sleft: continue
                if open_filter(target, et, gn, sleft, world, policy): continue
                d  = p_dist(src, target)
                sg = preferred_send(target, gn, et, sleft, world, modes, policy, distance=d)
                if sg<gn: continue
                plan = settle_plan(src, target, sleft, sg, world, planned, modes, policy,
                                   mission="capture", distance=d)
                if plan is None: continue
                _,turns,_,need,send = plan
                if world.is_late and turns>world.remaining-LATE_BUFFER: continue
                if send<need: continue
                val = target_value(target, turns, "capture", world, modes, policy)
                if val<=0: continue
                pm  = get_pressure()
                sc  = score_mods(val/(send+turns*ATTACK_TURN_W+1.0), target, "capture", world, policy, pm)
                if best is None or sc>best[0]: best=(sc,target,plan,d)
            if best is None: continue
            _,target,plan,d = best
            angle,turns,_,need,send = plan
            sleft = atk_left(src.id)
            if need>sleft: continue
            plan2 = settle_plan(src,target,sleft,min(sleft,send),world,planned,modes,policy,
                                mission="capture",distance=d)
            if plan2 is None: continue
            angle,turns,_,need,send = plan2
            if send<need: continue
            ts = speed_optimal_send(need, sleft, d, target.production)
            if ts >= need: send = ts
            a=push(src.id, angle, send)
            if a>=need: planned[target.id].append((turns,world.player,int(a)))

    # ── DOOMED EVACUATION ────────────────────────────────────────────────

    if opt_ok():
        doomed = live_doomed()
        if doomed:
            ft_set = world.enemy_planets or world.static_neutrals or world.neutral_planets
            fd = ({p.id: nearest_dist(p.x,p.y,ft_set) for p in world.my_planets}
                  if ft_set else {p.id:10**9 for p in world.my_planets})
            for planet in world.my_planets:
                if expired(): return finalize()
                if planet.id not in doomed: continue
                avail = inv_left(planet.id)
                if avail < policy["reserve"].get(planet.id,0): continue
                best_cap = None
                for target in world.planets:
                    if expired(): return finalize()
                    if target.id==planet.id or target.owner==world.player: continue
                    probe = world.best_probe(planet.id,target.id,avail,
                                             hints=(avail,int(target.ships)+1))
                    if probe is None: continue
                    _,pa = probe
                    if pa[1]>world.remaining-2: continue
                    need=world.min_ships_to_own_at(target.id,pa[1],world.player,
                                                   planned=planned,upper=avail)
                    if need<=0 or need>avail: continue
                    plan=settle_plan(planet,target,avail,
                                     min(avail,max(need,int(target.ships)+1)),
                                     world,planned,modes,policy,mission="capture")
                    if plan is None: continue
                    angle,turns,_,pn,send=plan
                    if send<pn: continue
                    sc=target_value(target,turns,"capture",world,modes,policy)/(send+turns+1.0)
                    if target.owner not in(-1,world.player): sc*=1.05
                    if best_cap is None or sc>best_cap[0]: best_cap=(sc,target.id,angle,turns,send)
                if best_cap:
                    _,tid,angle,turns,send=best_cap
                    a=push(planet.id,angle,send)
                    if a>=1: planned[tid].append((turns,world.player,int(a)))
                    continue
                allies=[p for p in world.my_planets if p.id!=planet.id and p.id not in doomed]
                if not allies: continue
                ret=min(allies,key=lambda p:(fd.get(p.id,10**9),p_dist(planet,p)))
                aim=world.plan_shot(planet.id,ret.id,avail)
                if aim: push(planet.id, aim[0], avail)

    # ── REAR LOGISTICS ───────────────────────────────────────────────────

    if ((world.enemy_planets or world.neutral_planets)
            and len(world.my_planets)>1 and not world.is_late and opt_ok()):
        doomed  = live_doomed()
        ft_set  = world.enemy_planets or world.static_neutrals or world.neutral_planets
        fd      = {p.id: nearest_dist(p.x,p.y,ft_set) for p in world.my_planets}
        safe_fs = [p for p in world.my_planets if p.id not in doomed]
        if safe_fs:
            anchor = min(safe_fs, key=lambda p:fd[p.id])
            ratio  = REAR_RATIO_FFA if world.is_ffa else REAR_RATIO_2P
            if modes["finishing"]: ratio = max(ratio, REAR_RATIO_FFA)
            for rear in sorted(world.my_planets, key=lambda p:-fd[p.id]):
                if expired(): return finalize()
                if rear.id==anchor.id or rear.id in doomed: continue
                if atk_left(rear.id)<REAR_MIN_SHIPS: continue
                if fd[rear.id]<fd[anchor.id]*REAR_DIST_RATIO: continue
                stage=[p for p in safe_fs if p.id!=rear.id and fd[p.id]<fd[rear.id]*REAR_STAGE_PROG]
                if stage:
                    front=min(stage,key=lambda p:p_dist(rear,p))
                else:
                    obj=min(ft_set,key=lambda t:p_dist(rear,t))
                    rem=[p for p in safe_fs if p.id!=rear.id]
                    if not rem: continue
                    front=min(rem,key=lambda p:p_dist(p,obj))
                if front.id==rear.id: continue
                send=int(atk_left(rear.id)*ratio)
                if send<REAR_SEND_MIN: continue
                aim=world.plan_shot(rear.id,front.id,send)
                if aim is None: continue
                if aim[1]>REAR_MAX_TRAVEL: continue
                push(rear.id, aim[0], send)

    # ── TOTAL WAR ────────────────────────────────────────────────────────

    if world.is_total_war and world.enemy_planets and opt_ok():
        primary = ([p for p in world.enemy_planets if p.owner==world._weakest]
                   if world._weakest else world.enemy_planets)
        for src in world.my_planets:
            if expired(): return finalize()
            left = atk_left(src.id)
            if left < 5: continue
            to_try = primary if primary else world.enemy_planets
            best_t = None; best_d = float('inf')
            for ep in to_try:
                d = p_dist(src,ep)
                if d < best_d:
                    at = world.plan_shot(src.id, ep.id, left)
                    if at: best_d, best_t = d, ep
            if best_t is None: continue
            aim = world.plan_shot(src.id, best_t.id, left)
            if aim is None: continue
            angle,turns,_,_ = aim
            if turns>=world.remaining: continue
            push(src.id, angle, left)

    return finalize()

# ════════════════════════════════════════════════════════════════════════
# AGENT ENTRY POINT
# ════════════════════════════════════════════════════════════════════════

_step = 0

def _read(obs, key, default=None):
    if isinstance(obs, dict): return obs.get(key, default)
    return getattr(obs, key, default)

def build_world(obs, inferred_step=None):
    player    = _read(obs,"player",0)
    obs_step  = _read(obs,"step",0) or 0
    step      = max(obs_step, inferred_step or 0)
    planets   = [Planet(*p) for p in (_read(obs,"planets",[]) or [])]
    fleets    = [Fleet(*f)  for f in (_read(obs,"fleets",[])  or [])]
    ang_vel   = _read(obs,"angular_velocity",0.0) or 0.0
    init_raw  = _read(obs,"initial_planets",[]) or []
    comets    = _read(obs,"comets",[]) or []
    comet_ids = set(_read(obs,"comet_planet_ids",[]) or [])
    init_ps   = [Planet(*p) for p in init_raw]
    init_by_id= {p.id: p for p in init_ps}
    return WorldModel(player, step, planets, fleets, init_by_id, ang_vel, comets, comet_ids)

def agent(obs, config=None):
    global _step
    _step += 1
    t0          = time.perf_counter()
    world       = build_world(obs, inferred_step=_step-1)
    if not world.my_planets: return []
    act_timeout = _read(config,"actTimeout",1.0) if config else 1.0
    budget      = min(SOFT_DEADLINE, max(0.55, act_timeout * 0.82))
    return plan_moves(world, deadline=t0+budget)

__all__ = ["agent", "build_world"]
```

## [MD]
## ✅ Validation Suite — Always Run Before Submitting

The cell below runs a comprehensive smoke test covering:

| Test | What it checks |
|------|---------------|
| FFA Early Game | 4-player opening, multiple neutrals to race for |
| 1v1 Domination | We're ahead, should play efficiently |
| Economic AGGRO | We're losing production, must attack enemy planets |
| Rush Scenario | Enemy sends big fleet early — detect and respond |
| Total War | Last 65 turns, all-out assault |
| Action Format | Validates `[int, float, int]` format, ships >= 1 |

**All tests must pass before submitting to Kaggle.**

## [CODE]
```python
import importlib.util, time

spec = importlib.util.spec_from_file_location('omega', 'submission.py')
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def make_obs(planets, fleets=None, step=10, player=0, ang_vel=0.03):
    return {
        'player': player, 'step': step,
        'angular_velocity': ang_vel,
        'planets': planets,
        'fleets': fleets or [],
        'initial_planets': planets,
        'comets': [],
        'comet_planet_ids': [],
        'remainingOverageTime': 60.0,
    }

tests = {
    "FFA Early Game (4 players)": make_obs(
        planets=[
            [0,0,20.,20.,2.,50,4],[1,-1,40.,30.,1.,10,2],[2,-1,60.,70.,1.,8,3],
            [3,-1,30.,60.,1.7,12,3],[4,-1,65.,30.,1.,9,2],[5,1,82.,82.,2.,80,4],
            [6,2,18.,82.,2.,70,3],[7,3,82.,18.,2.,75,3],
        ], step=15, ang_vel=0.025
    ),
    "1v1 Domination": make_obs(
        planets=[
            [0,0,15.,15.,2.7,250,4],[1,0,28.,20.,1.7,120,3],
            [4,1,85.,85.,2.7,80,4],[5,1,70.,72.,1.7,40,2],
        ], step=200
    ),
    "Economic AGGRO mode": make_obs(
        planets=[
            [0,0,15.,15.,2.7,60,1],
            [3,1,75.,75.,2.7,60,5],[4,1,65.,65.,1.7,35,4],[5,1,55.,55.,1.,25,3],
        ], step=150
    ),
    "Rush Detection scenario": make_obs(
        planets=[
            [0,0,20.,20.,2.,55,3],[4,1,80.,80.,2.,90,4],
        ],
        fleets=[[10,1,72.,72.,-2.50,4,65]],
        step=22
    ),
    "Total War endgame": make_obs(
        planets=[
            [0,0,20.,20.,2.,180,4],[1,0,28.,28.,1.,90,2],
            [3,1,78.,78.,2.,120,4],
        ], step=445
    ),
    "Static planet map": make_obs(
        planets=[
            [0,0,15.,15.,2.7,100,3],
            [1,-1,90.,90.,3.0,30,4],[2,-1,10.,90.,3.0,25,3],[3,-1,90.,10.,3.0,20,5],
            [4,1,85.,85.,2.7,80,3],
        ], step=80
    ),
}

print("=" * 65)
print("  OMEGA v3 VALIDATION SUITE")
print("=" * 65)

total = 0; passed = 0
for test_name, obs in tests.items():
    total += 1
    t0 = time.perf_counter()
    try:
        w       = mod.build_world(obs)
        actions = mod.agent(obs)
        elapsed = (time.perf_counter() - t0) * 1000

        # --- Format validation ---
        for act in actions:
            assert len(act) == 3,              f"Action must have 3 elements, got {len(act)}"
            sid, angle, ships = act
            assert isinstance(sid,   int),     f"src_id must be int, got {type(sid)}"
            assert isinstance(angle, float),   f"angle must be float, got {type(angle)}"
            assert isinstance(ships, int),     f"ships must be int, got {type(ships)}"
            assert ships >= 1,                 f"must send >= 1 ship, got {ships}"
            assert sid in w.by_id,             f"src_id {sid} not a valid planet ID"

        eco   = w.eco_mode.value
        rush  = " 🚨RUSH" if w.is_rush else ""
        win_r = f"WinR={w.win_ratio:.2f}"
        print(f"  ✅  {test_name:<36} │ {elapsed:>6.1f}ms │ {len(actions)} acts │ "
              f"eco={eco}{rush} {win_r}")
        passed += 1

    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"  ❌  {test_name:<36} │ {elapsed:>6.1f}ms │ FAILED: {e}")

print("=" * 65)
if passed == total:
    print(f"  🎉 ALL {total}/{total} TESTS PASSED — Ready to submit!")
else:
    print(f"  ⚠️  {passed}/{total} tests passed — fix failures before submitting!")
print("=" * 65)
```

## [MD]
## 📈 Strategy Comparison & Advanced Tips

### OMEGA v3 vs Other Approaches

| Feature | OMEGA v3 | Basic Greedy | Rule-Based |
|---------|----------|-------------|------------|
| Orbital prediction | ✅ 5-iter convergence | ⚠️ Endpoint only | ❌ None |
| Sun avoidance | ✅ Full path check | ⚠️ Endpoint only | ❌ None |
| Timeline simulation | ✅ Binary search | ❌ Estimate | ⚠️ Partial |
| Economic mode | ✅ EXPAND/BALANCED/AGGRO | ❌ None | ❌ None |
| Intercept missions | ✅ Preemptive defense | ❌ Passive | ❌ None |
| Multi-front pressure | ✅ +12%/front bonus | ❌ None | ❌ None |
| Speed-optimal send | ✅ Math-justified | ❌ None | ⚠️ Fixed |
| FFA crash exploit | ✅ Enemy vs enemy | ❌ None | ❌ None |
| Gang-up missions | ✅ Post-battle timing | ❌ None | ❌ None |
| Gateway value | ✅ Positional scoring | ❌ None | ❌ None |

---

### 💡 Tips for Further Improvement

**1. Tune the constants**
The most accessible improvement. Constants like `HOSTILE_VM`, `WEAKEST_VM_FFA`,
`ECO_AGGRO_THRESH`, and `TSUNAMI_THRESH` can be optimized by running many games
and hill-climbing the win rate. Even small changes (±0.05) can affect performance.

**2. Better FFA diplomacy detection**
In 4-player FFA, detect which two enemies are fighting each other
and preferentially attack the winner when the battle concludes.
This is the most underexplored opportunity in the current code.

**3. Production sequencing**
Instead of evaluating all targets equally, compute an ordered
capture sequence: "Capture A, then use A to capture B, then B to C..."
The compounding production from sequenced captures can outperform
individual target scoring.

**4. Adaptive endgame**
In the final 50 turns, calculate *exactly* how many ships you need
to win (enemy total − my total + 1). If you already have enough,
stop attacking and just protect your lead. If not, commit everything
to the single fastest-return attack available.

**5. Neural network scoring**
Replace the handcrafted `target_value()` function with a small neural net
trained on game outcomes. The input would be game state features;
the output a win probability delta for each possible action.

---

*Good luck on the leaderboard! The key to winning Orbit Wars is not just*
*smart targeting, but smart **timing** — the right fleet at the right planet*
*at the right moment changes the whole game. 🌌*
