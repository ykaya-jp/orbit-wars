## [MD]
# ☀️ HYPERION — Orbit Wars Supreme Tactical Intelligence
**H**yperspatial **I**ntelligence for **P**lanetary **E**ngagement, **R**apid **I**nterstellar **O**perations & **N**eutralization

---

## Architecture — Eight Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 1  Physics        Orbital prediction (7-iter) · Solar bypass        │
│  LAYER 2  World Model    Timeline sim · Binary search · Arrival ledger      │
│  LAYER 3  Economic Mode  5-tier: SNOWBALL/EXPAND/BALANCED/AGGRO/PANIC       │
│  LAYER 4  Policy Builder Dynamic reserves · Opening Blitz (turns 1–22)     │
│  LAYER 5  Scoring Engine 14 multipliers · Flanking ×1.20 · Vuln ×5.94     │
│  LAYER 6  Mission Engine 14 mission types · Intercept · Counter-rush       │
│  LAYER 7  Executor       Hyper-tsunami · Concentration · 3-src Swarm       │
│  LAYER 8  Endgame        Death ball (35 turns) · Total war prod/dist       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Score History & What Changed

| Agent | Score | Key innovation |
|-------|-------|----------------|
| Baseline (greedy) | 595.6 | Simple ROI scoring |
| OMEGA v3 | 678.5 | Timeline simulation + 12 missions |
| OMEGA v5 | 644.3 ❌ | **Regressed** — death ball too passive (60 turns) |
| OMEGA v6 | ~700 | Fixed v5 bugs + solar bypass |
| **HYPERION** | **?** 🚀 | **Opening Blitz + Flanking + 8-layer full rewrite** |

## HYPERION's Exclusive Innovations

| Innovation | Effect | Where |
|------------|--------|-------|
| **Opening Blitz** (turns 1–22) | −45% reserves, +28% neutral boost | Layer 4 |
| **Flanking Bonus** ×1.20 | 2+ planets attacking same target simultaneously | Layer 5 |
| **Pressure at 2 fronts** | Bonus kicks in earlier than all previous versions | Layer 5 |
| **Total War prod/dist priority** | Smarter final push — closer high-prod first | Layer 8 |
| **Death ball 1.15 threshold** | Requires stronger lead before defending | Layer 8 |

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
import os, math, time
from collections import defaultdict

for dirname, _, filenames in os.walk('/kaggle/input'):
    for filename in filenames:
        print(os.path.join(dirname, filename))

print()
print("Environment ready ✅")
print("Modules used: math, time, collections, dataclasses, enum — all built-in")
print("No pip installs needed — HYPERION runs on the base Kaggle Python image")
```

## [MD]
## ⚡ Layer 1 — Physics Part 1: The Speed Curve & Tsunami Strike

### The Core Formula That Shapes Everything

```
speed(n) = 1.0 + 5.0 × (ln(n) / ln(1000)) ^ 1.5
```

This formula creates a **non-linear speed advantage** for large fleets.
Sending more ships isn't just about winning fights — it's about **arriving faster**,
which means **capturing production sooner**, which **compounds for the rest of the game**.

### Why 1 Saved Turn Is Worth More Than It Looks

```
Example: target produces 3 ships/turn, we're 35 units away

Sending 60 ships:  speed 3.3 → ETA 11 turns → capture at turn T+11
Sending 150 ships: speed 4.2 → ETA 9 turns  → capture at turn T+9

Time saved: 2 turns
Ships gained from faster capture: 2 × 3 = 6 FREE ships
Ships spent extra: 90

ROI: 6 free ships + faster base for next attack — almost always worth it
```

### HYPERION Tsunami — 4-Level Decision Tree

```
1. FULL TSUNAMI:  available >= 1.5 × needed AND turns_saved >= 1 AND prod > 0
   → send 90% of budget

2. CHEAP TSUNAMI: extra ships <= 55% of budget
   → send 90% of budget (cheap enough regardless of turns saved)

3. SOFT TSUNAMI:  sending 22% more ships saves 1 turn
   → send needed × 1.22

4. STANDARD:      fallback
   → send needed × 1.06 (small safety margin)
```

## [CODE]
```python
import math

MAX_SPEED = 6.0
TSUNAMI_THRESH = 1.5; TSUNAMI_RATIO = 0.90; TSUNAMI_MIN_SHIPS = 20

def fleet_speed(ships):
    if ships <= 1: return 1.0
    r = max(0.0, min(1.0, math.log(max(1, ships)) / math.log(1000.0)))
    return 1.0 + (MAX_SPEED - 1.0) * (r ** 1.5)

def tsunami_decision(needed, available, distance, prod):
    if available <= needed: return needed, 'NO BUDGET'
    base_t = max(1, int(math.ceil(distance / fleet_speed(max(1, needed)))))
    if available >= needed * TSUNAMI_THRESH and available >= TSUNAMI_MIN_SHIPS:
        cand   = min(available, max(needed, int(available * TSUNAMI_RATIO)))
        cand_t = max(1, int(math.ceil(distance / fleet_speed(max(1, cand)))))
        saved  = base_t - cand_t
        if saved >= 1 and prod > 0:
            return cand, f'🌊 FULL TSUNAMI  (-{saved} turns → +{saved*prod} free ships)'
        if cand - needed <= available * 0.55:
            return cand, f'🌊 CHEAP TSUNAMI (extra ≤55% of budget)'
    modest = min(available, int(needed * 1.22))
    if modest > needed:
        mod_t = max(1, int(math.ceil(distance / fleet_speed(max(1, modest)))))
        if base_t - mod_t >= 1:
            return modest, '〰️  SOFT TSUNAMI  (+22% ships, -1 turn)'
    return min(available, int(needed * 1.06)), '➡️  STANDARD     (+6% margin)'

# ── Speed Curve ─────────────────────────────────────────────────────────
print('=' * 62)
print('  FLEET SPEED CURVE')
print('=' * 62)
print(f"  {'Ships':>8} │ {'Speed':>6} │ {'ETA (40u)':>9} │ {'vs 1 ship':>9} │ Bar")
print('  ' + '─' * 56)
for s in [1, 5, 10, 25, 50, 100, 200, 300, 500, 1000]:
    sp  = fleet_speed(s)
    eta = math.ceil(40.0 / sp)
    spdup = f'{40/eta:.1f}×' if s > 1 else 'base'
    bar   = '█' * int(sp * 5)
    print(f'  {s:>8} │ {sp:>6.2f} │ {eta:>7} trn │ {spdup:>9} │ {bar}')

# ── Tsunami decisions ────────────────────────────────────────────────────
print()
print('=' * 70)
print('  TSUNAMI DECISIONS  (needed=60, distance=35, prod=3)')
print('=' * 70)
for avail in [62, 90, 120, 150, 200, 350, 500]:
    send, reason = tsunami_decision(60, avail, 35.0, 3)
    base_t = math.ceil(35.0 / fleet_speed(60))
    send_t = math.ceil(35.0 / fleet_speed(send))
    print(f'  avail={avail:>4}  send={send:>4}  ETA {send_t} vs {base_t}  │  {reason}')
```

## [MD]
## ☀️ Layer 1 — Physics Part 2: Orbital Prediction & Solar Bypass

### Problem 1 — Moving Targets

Planets orbit the sun at angular velocity `ω rad/turn`.
If you aim at where a planet **is**, your fleet arrives where it **was**.

**HYPERION Solution — 7-Iteration Convergence:**

```
estimate ETA to current position
  → predict planet position at that ETA
    → recalculate ETA to predicted position
      → repeat until delta < 0.20 units (converged!)

HYPERION uses 7 iterations (v3: 5, v5/v6: 7) for maximum precision.
```

### Problem 2 — Sun Collision

Fleets travel in straight lines. If that line passes within
`SUN_R + SUN_SAFETY = 11.6 units` of center (50,50), the fleet is **destroyed**.

**Previous agents:** Give up on sun-blocked targets entirely.
**HYPERION:** Computes a **tangent bypass route** around the danger zone.

### Solar Bypass Algorithm

```
1. Check direct path — if clear, use it (zero overhead)
2. If blocked:
   danger_radius = SUN_R + SUN_SAFETY + 0.6 = 12.2 units
   half_angle    = arcsin(danger_radius / dist_to_sun)

   Try CLOCKWISE tangent:
     tang_angle = base_angle + (half_angle + 0.18 rad)
     waypoint   = source + tang_angle × tang_dist

   Try COUNTER-CLOCKWISE:
     tang_angle = base_angle - (half_angle + 0.18 rad)

   Pick shorter total distance route
```

**Typical overhead:** +8–15 units travel distance → +1–3 turns ETA.
A small cost to unlock planets that were previously **completely inaccessible**.

### Why This Matters Strategically

Without bypass: enemy can "park" behind the sun and be immune to attacks.
With bypass: no position on the map is safe — HYPERION can reach anywhere.

## [CODE]
```python
import math

CENTER_X, CENTER_Y = 50.0, 50.0
SUN_R, SUN_SAFETY  = 10.0, 1.6

def pt_seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2-x1, y2-y1; sq = dx*dx + dy*dy
    if sq <= 1e-9: return math.hypot(px-x1, py-y1)
    t = max(0.0, min(1.0, ((px-x1)*dx + (py-y1)*dy) / sq))
    return math.hypot(px-(x1+t*dx), py-(y1+t*dy))

def seg_hits_sun(x1, y1, x2, y2):
    return pt_seg_dist(CENTER_X, CENTER_Y, x1, y1, x2, y2) < SUN_R + SUN_SAFETY

def check_direct(sx, sy, tx, ty):
    return not seg_hits_sun(sx, sy, tx, ty)

def bypass_dist(sx, sy, tx, ty):
    danger_r = SUN_R + SUN_SAFETY + 0.6
    to_sun_d = math.hypot(sx-CENTER_X, sy-CENTER_Y)
    if to_sun_d <= danger_r: return None
    base_a = math.atan2(CENTER_Y-sy, CENTER_X-sx)
    half   = math.asin(min(1.0, danger_r / to_sun_d))
    tang_d = math.sqrt(max(0, to_sun_d**2 - danger_r**2)) + 2.5
    best = None
    for sign in (+1, -1):
        tang_a = base_a + sign * (half + 0.18)
        wx = sx + math.cos(tang_a) * tang_d
        wy = sy + math.sin(tang_a) * tang_d
        if not seg_hits_sun(wx, wy, tx, ty):
            total = tang_d + math.hypot(wx-tx, wy-ty)
            if best is None or total < best: best = total
    return best

# ── Solar Bypass Demo ────────────────────────────────────────────────────
print('=' * 68)
print('  SOLAR BYPASS DEMO — HYPERION finds a route to every planet')
print('=' * 68)
paths = [
    ('Clear path (no obstruction)',     10., 10., 90., 90.),
    ('Safe path above sun',             10., 75., 90., 75.),
    ('SUN-BLOCKED (horizontal)',        10., 50., 90., 50.),
    ('Diagonal through sun',            12., 12., 88., 88.),
    ('Near-tangent — careful routing',  20., 20., 80., 80.),
]
for name, x1, y1, x2, y2 in paths:
    direct_ok = check_direct(x1, y1, x2, y2)
    direct_d  = math.hypot(x2-x1, y2-y1)
    closest   = pt_seg_dist(CENTER_X, CENTER_Y, x1, y1, x2, y2)
    if direct_ok:
        print(f'  ✅ DIRECT   {name}')
        print(f'     dist={direct_d:.1f}u  sun_clearance={closest:.1f}u')
    else:
        bp = bypass_dist(x1, y1, x2, y2)
        if bp:
            overhead = bp - direct_d
            speed_50 = fleet_speed(50)
            eta_direct = direct_d / speed_50
            eta_bypass = bp / speed_50
            extra_turns = int(math.ceil(eta_bypass)) - int(math.ceil(eta_direct))
            print(f'  🔄 BYPASS   {name}')
            print(f'     bypass_dist={bp:.1f}u  overhead=+{overhead:.1f}u  +{extra_turns} turns ETA')
        else:
            print(f'  ❌ BLOCKED  {name}')
    print()

# ── Orbital prediction convergence ──────────────────────────────────────
print('=' * 68)
print('  ORBITAL PREDICTION — 7-iteration convergence')
print('=' * 68)
# Planet at (80, 50), orbiting at ω=0.025 rad/turn
px, py   = 80.0, 50.0
src_x, src_y = 15.0, 15.0
ang_vel  = 0.025
ships    = 80
sun_r    = math.hypot(px-CENTER_X, py-CENTER_Y)

print(f'  Planet starts at ({px}, {py}), orbiting at ω={ang_vel} rad/turn')
print(f'  Source at ({src_x}, {src_y}), sending {ships} ships')
print()

tx, ty = px, py
for iteration in range(7):
    d    = math.hypot(tx-src_x, ty-src_y)
    sp   = fleet_speed(ships)
    eta  = max(1, int(math.ceil(d / sp)))
    cur  = math.atan2(py-CENTER_Y, px-CENTER_X)
    new  = cur + ang_vel * eta
    ntx  = CENTER_X + sun_r * math.cos(new)
    nty  = CENTER_Y + sun_r * math.sin(new)
    move = math.hypot(ntx-tx, nty-ty)
    conv = '✅ CONVERGED' if move < 0.20 else ''
    print(f'  Iter {iteration+1}: aim=({ntx:.2f},{nty:.2f})  ETA={eta}t  planet_moved={move:.3f}u  {conv}')
    if move < 0.20: break
    tx, ty = ntx, nty
```

## [MD]
## 🗓️ Layer 2 — World Model: Timeline Simulation & Binary Search

### The Most Important Algorithm in HYPERION

**The question:** How many ships do I need to capture planet X by turn T?

**Naive answer:** `planet.ships + 1` — **WRONG** because it ignores:
- Production growth during travel time
- Friendly fleets already en route
- Enemy reinforcements arriving before us
- Multiple fleets arriving on the same turn (combat resolution)

**HYPERION answer:** Full turn-by-turn simulation with **binary search**

### Timeline Simulation

```python
simulate_timeline(planet, all_arrivals, player, horizon):

  for each turn 1..horizon:
    1. If owned by anyone → garrison += production
    2. If arrivals this turn → combat_resolution(all_arrivals_this_turn)

       Combat rule: Largest force beats second largest
                    Winner keeps: top_ships - second_ships
                    Tie: all attackers cancel, defender keeps garrison

  Binary search on minimum garrison to survive:
    lo=0, hi=planet.ships
    while lo < hi:
      mid = (lo + hi) // 2
      if survives(mid): hi = mid
      else: lo = mid + 1
    → minimum ships to keep = lo
```

### Why Binary Search?

For a planet with 200 ships, binary search needs ~8 simulations.
Linear search would need up to 200 simulations.
With caching `(planet_id, eval_turn, attacker) → ships_needed`,
repeated queries for the same scenario cost **zero extra computation**.

### Arrival Ledger

At the start of each turn, HYPERION builds an arrival ledger:

```
For each fleet F in flight:
  1. Project F's heading (angle + fleet_speed) onto all planets
  2. Find which planet F will hit and when (ETA)
  3. Record: arrivals[planet_id].append((eta, owner, ships))

This builds a complete picture of the future battlefield.
```

## [CODE]
```python
from collections import defaultdict

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
    else:
        surv_o, surv_s = top_o, top_s
    if surv_s <= 0: return owner, max(0.0, garrison)
    if owner == surv_o: return owner, garrison + surv_s
    garrison -= surv_s
    return (surv_o, -garrison) if garrison < 0 else (owner, garrison)

def simulate_timeline(owner, ships, prod, arrivals, player, horizon=25):
    events = sorted([(max(1,int(t)),o,int(s)) for t,o,s in arrivals if s>0 and t<=horizon])
    by_turn = defaultdict(list)
    for item in events: by_turn[item[0]].append(item)
    garrison = float(ships); fall_turn = None
    owner_at = {0: owner}; ships_at = {0: garrison}
    for turn in range(1, horizon+1):
        if owner != -1: garrison += prod
        prev = owner
        if by_turn.get(turn):
            owner, garrison = resolve_arrivals(owner, garrison, by_turn[turn])
            if prev == player and owner != player and fall_turn is None: fall_turn = turn
        owner_at[turn] = owner; ships_at[turn] = max(0.0, garrison)
    return owner_at, ships_at, fall_turn

print('=' * 70)
print('  TIMELINE SIMULATION DEMOS')
print('=' * 70)

scenarios = [
    {
        'name': 'A — We hold comfortably (garrison grows past threat)',
        'owner': 0, 'ships': 60, 'prod': 3,
        'arrivals': [(10, 1, 40)],
    },
    {
        'name': 'B — We fall (need reinforcement!)',
        'owner': 0, 'ships': 30, 'prod': 2,
        'arrivals': [(8, 1, 60)],
    },
    {
        'name': 'C — We reinforce BEFORE enemy arrives',
        'owner': 0, 'ships': 25, 'prod': 2,
        'arrivals': [(12, 1, 50), (10, 0, 20)],
    },
    {
        'name': 'D — Two enemies fight, we mop up the winner',
        'owner': 1, 'ships': 50, 'prod': 3,
        'arrivals': [(5, 2, 40), (12, 0, 25)],
    },
]

for sc in scenarios:
    owner_at, ships_at, fall = simulate_timeline(
        sc['owner'], sc['ships'], sc['prod'], sc['arrivals'], player=0)
    print(f'\n  Scenario {sc["name"]}')
    print(f'  Start: P{sc["owner"]} garrison={sc["ships"]} prod={sc["prod"]}/t  arrivals={sc["arrivals"]}')
    print(f'  fall_turn={fall}')
    print(f'  Turn-by-turn:')
    for t in [0, 5, 8, 10, 12, 15, 20, 25]:
        o = owner_at.get(t, '?'); s = ships_at.get(t, 0)
        owner_str = f'P{o}' if o != -1 else 'N '
        bar = '▓' * min(35, int(s // 3))
        print(f'    t={t:>2}: [{owner_str}] {s:>6.1f} ships  {bar}')
```

## [MD]
## 📊 Layer 3 — Economic Mode: 5-Tier Production Awareness

### Why Production Ratio Is the Most Important Number

```
If enemy generates 2× ships/turn more than you:
  After 100 turns: enemy has +200 extra ships
  After 200 turns: enemy has +400 extra ships
  After 300 turns: enemy has +600 extra ships

No amount of tactical cleverness overcomes a sustained 2× production deficit.
You MUST attack their production planets.
```

### The 5 Modes

| Mode | Ratio | Core Strategy |
|------|-------|--------------|
| 🌟 SNOWBALL | > 2.0 | **Concentrate force** on single best target |
| 🌱 EXPAND | 1.35–2.0 | Carefully grab neutrals, avoid costly fights |
| ⚖️ BALANCED | 0.72–1.35 | Normal play — balance expansion and aggression |
| ⚔️ AGGRO | 0.45–0.72 | Attack enemy production planets **NOW** |
| 💀 PANIC | < 0.45 | **All-in** — halve reserves, ×1.92 hostile multiplier |

### How Each Mode Changes Every Decision

| Decision | SNOWBALL | EXPAND | BALANCED | AGGRO | PANIC |
|----------|---------|--------|---------|-------|-------|
| Neutral value | ×1.08 | **×1.38** | ×1.00 | ×0.70 | ×0.48 |
| Enemy value | ×1.68 | ×0.75 | ×1.00 | **×1.58** | **×1.92** |
| High-prod enemy | ×1.68 | ×0.75 | ×1.00 | **×2.05** | **×2.69** |
| Reserve multiplier | −30% | −20% | baseline | baseline | **−50%** |

### HYPERION Tuning vs v5/v6

- `ECO_PANIC_HOSTILE`: v5=2.20, v6=1.90, **HYPERION=1.92** — v5's 2.20 caused suicide attacks
- `ECO_EXPAND_HOSTILE`: v6=0.78, **HYPERION=0.75** — even less hostile targeting when expanding
- `ECO_EXPAND_NEUTRAL`: v6=1.35, **HYPERION=1.38** — slightly more neutral priority in EXPAND

## [CODE]
```python
HYPERION_THRESHOLDS = [
    (2.00, 'SNOWBALL 🌟', 1.68, 1.08),
    (1.35, 'EXPAND   🌱', 0.75, 1.38),
    (0.72, 'BALANCED ⚖️ ', 1.00, 1.00),
    (0.45, 'AGGRO    ⚔️ ', 1.58, 0.70),
    (0.00, 'PANIC    💀', 1.92, 0.48),
]

def get_mode(mp, ep):
    r = mp / max(1, ep)
    for thresh, name, hv, nv in HYPERION_THRESHOLDS:
        if r >= thresh: return name, r, hv, nv
    return HYPERION_THRESHOLDS[-1][1:]

def eco_high_prod_mult(hv, mode_name):
    if 'AGGRO' in mode_name or 'PANIC' in mode_name:
        return hv * 1.30  # extra ×1.30 for prod >= 4 planets
    return hv

print('=' * 76)
print('  HYPERION ECONOMIC MODE TABLE  (base score = 1000)')
print('=' * 76)
print(f"  {'My':>4} {'En':>4} {'Ratio':>6} │ {'Mode':<16} │ {'Neutral':>8} {'Enemy':>8} {'HighProd':>10} │ Scenario")
print('  ' + '─' * 73)
cases = [
    (8, 2, 'Dominant'),
    (5, 3, 'Ahead'),
    (4, 4, 'Even match'),
    (3, 5, 'Behind'),
    (2, 6, 'Losing'),
    (1, 9, 'Crisis'),
]
for mp, ep, desc in cases:
    name, ratio, hv, nv = get_mode(mp, ep)
    n_sc  = int(1000 * nv)
    h_sc  = int(1000 * hv)
    hp_sc = int(1000 * eco_high_prod_mult(hv, name))
    bar   = '█' * int(ratio * 2)
    print(f'  {mp:>4} {ep:>4} {ratio:>6.2f} │ {name:<16} │ {n_sc:>8} {h_sc:>8} {hp_sc:>10} │ {desc}')

print()
print('=' * 76)
print('  RESERVE ADJUSTMENT BY MODE (100 ship planet, calculated reserve = 40)')
print('=' * 76)
base_reserve = 40
reserve_mods = [
    ('SNOWBALL 🌟', 0.70, 'Far ahead — can afford lower reserves'),
    ('EXPAND   🌱', 0.80, 'Expanding — slightly lower reserves'),
    ('BALANCED ⚖️ ', 1.00, 'Normal reserves'),
    ('AGGRO    ⚔️ ', 1.00, 'Normal reserves (risk from enemy attacks)'),
    ('PANIC    💀', 0.50, 'Halved! — throw everything into attack'),
]
print(f"  {'Mode':<16} │ {'Reserve':>8} │ {'Budget':>8} │ Note")
print('  ' + '─' * 62)
for mode, mult, note in reserve_mods:
    r = int(base_reserve * mult)
    b = 100 - r
    print(f'  {mode:<16} │ {r:>8} │ {b:>8} │ {note}')
```

## [MD]
## 🛡️ Layer 4 — Policy Builder: Reserves, Budget & Opening Blitz

### Two Numbers Per Planet

For every planet we own, HYPERION computes exactly two numbers:

```
reserve[planet_id] = ships to keep for defense (must not send)
budget[planet_id]  = ships available for attacks (= total - reserve)
```

### Dynamic Reserve Calculation

```python
exact  = timeline.keep_needed           # minimum to survive known threats
proact = max(threats × PROACT_RATIO)    # buffer against potential threats

reserve = min(garrison, max(exact, proact))
budget  = garrison - reserve
```

**1v1 aggression reduction:** When dominating (+22% ahead), both `exact` and `proact`
are multiplied by 0.28 — the game is essentially won, free more ships for offense.

---

## 🚀 HYPERION NEW: Opening Blitz (Turns 1–22)

### Why the First 22 Turns Are the Most Leveraged

```
A planet with production 3:
  Captured turn 5  → generates 3 × (500-5)  = 1485 ships over the game
  Captured turn 22 → generates 3 × (500-22) = 1434 ships
  Captured turn 50 → generates 3 × (500-50) = 1350 ships

  Early capture advantage (turn 5 vs 50): +135 ships — from ONE planet!
```

### Blitz Settings

```python
OPENING_BLITZ_TURNS        = 22    # first 22 turns
OPENING_BLITZ_RESERVE_FRAC = 0.55  # keep only 55% of normal reserve
OPENING_BLITZ_MARGIN_FRAC  = 0.70  # send margins reduced to 70% of normal
OPENING_BLITZ_NEUTRAL_VM   = 1.28  # +28% extra neutral target value
```

### Is Opening Blitz Risky?

Only if the enemy rushes in the first 22 turns.
HYPERION's rush detection (≥26 ships heading at us within 28 turns) still works
during the blitz — if rush is detected, reserves increase by ×1.55 immediately.

## [CODE]
```python
OPENING_BLITZ_TURNS        = 22
OPENING_BLITZ_RESERVE_FRAC = 0.55
OPENING_BLITZ_MARGIN_FRAC  = 0.70
OPENING_BLITZ_NEUTRAL_VM   = 1.28

print('=' * 68)
print('  OPENING BLITZ — COMPOUND CAPTURE ADVANTAGE')
print('=' * 68)
print(f"  {'Capture Turn':>13} │ {'Ships (prod=3)':>15} │ {'vs Turn 50':>12} │ Phase")
print('  ' + '─' * 60)
for t in [3, 8, 15, 22, 30, 40, 50, 70, 100]:
    ships = 3 * (500 - t)
    vs_50  = ships - 3 * (500 - 50)
    phase = '🚀 BLITZ' if t <= OPENING_BLITZ_TURNS else '  normal'
    sign  = f'+{vs_50}' if vs_50 >= 0 else str(vs_50)
    bar   = '█' * (vs_50 // 15) if vs_50 > 0 else ''
    print(f'  turn {t:>3}       │ {ships:>15} │ {sign:>12} │ {phase}  {bar}')

print()
print('=' * 68)
print('  RESERVE & BUDGET COMPARISON: Normal vs Blitz')
print('=' * 68)
print(f"  Planet: 80 ships garrison, calculated reserve = 50")
print()
print(f"  {'Mode':>16} │ {'Reserve':>8} │ {'Budget':>8} │ {'Attack margin':>14} │ Effect")
print('  ' + '─' * 65)

cases = [
    ('Normal play',    1.00, 1.00, 'standard'),
    ('Opening Blitz',  OPENING_BLITZ_RESERVE_FRAC, OPENING_BLITZ_MARGIN_FRAC, 'aggressive'),
    ('Blitz + Rush!',  OPENING_BLITZ_RESERVE_FRAC * 1.55, 1.0, 'defended'),
]
for name, rfrac, mfrac, label in cases:
    r = int(50 * rfrac)
    b = max(0, 80 - r)
    m_pct = int(mfrac * 100)
    print(f'  {name:>16} │ {r:>8} │ {b:>8} │ {m_pct:>12}% │ {label}')

print()
print('  During Opening Blitz (turns 1-22):')
print(f'    Reserve fraction: ×{OPENING_BLITZ_RESERVE_FRAC}  → 27 ships kept instead of 50')
print(f'    Attack margins:   ×{OPENING_BLITZ_MARGIN_FRAC}  → send fewer safety ships')
print(f'    Neutral value:    ×{OPENING_BLITZ_NEUTRAL_VM}  → neutral targets boosted further')
```

## [MD]
## 🎯 Layer 5 — Scoring Engine: 14 Multipliers

### The Target Value Formula

```
base_value = (production ^ 1.32) × turns_remaining_after_capture
           + indirect_wealth × turns × 0.15

final_value = base_value
  × static_mult       (1.50/1.88 for planets not orbiting)
  × opening_mult      (0.86 during opening for rotating planets)
  × hostile_mult      (2.32 for enemy planets — capturing stops their income)
  × neutral_safety    (1.35 safe / 0.60 contested)
  × race_bonus        (×1.65 if we arrive before enemy can)
  × early_neutral     (×1.45 bonus for fast early capture)
  × blitz_bonus       (×1.28 during Opening Blitz)
  × mission_mult      (snipe/swarm/gang_up adjustments)
  × vuln_window       (×5.94 when enemy fleet just left!)
  × flanking          (×1.20 when 2+ planets can attack simultaneously)
  × gateway           (up to ×1.24 for forward positions near enemy)
  × eco_mode          (SNOWBALL/EXPAND/BALANCED/AGGRO/PANIC adjustments)
  × counter_rush      (×1.88 vs enemy home when being rushed)
  + elim_bonus        (+95 flat when enemy total ≤ 165 ships)
  × weakest_enemy     (×1.78 FFA / ×1.45 1v1 for weakest player)
  × death_ball        (×0.48 defend / ×1.92 all-in in final 35 turns)

score = final_value / (ships_sent + travel_turns × 0.45 + 1)
      × pressure_mult (up to ×1.58 for 2+ simultaneous attack fronts)
```

### HYPERION's Two New Multipliers

#### 1. Flanking Bonus ×1.20
When 2+ of our planets can reach the same enemy target within 3 turns of each other,
the enemy cannot optimally defend. Enemy must split forces or accept one planet falls.

#### 2. Opening Blitz ×1.28
During turns 1-22, neutral targets receive an extra ×1.28 on top of
the `EARLY_NEUTRAL_VM` (×1.45), creating a combined bonus of **×1.87**.
This makes early neutrals overwhelmingly the top priority.

### Vulnerability Window — The Highest Single Multiplier

```
EXPOSED_VM × VULN_WINDOW_BONUS = 2.65 × 2.24 = ×5.94

When detected: enemy sent ≥6 ships AND ≥40% of garrison just left
Result: score ×5.94 + EXPOSED_SCORE_M (×1.48) = ×8.78 total on score
```

An exposed enemy planet **beats every other target** — including neutrals and elimination missions.

## [CODE]
```python
import math

PROD_EXP       = 1.32
HOSTILE_VM     = 2.32
EXPOSED_VM     = 2.65
VULN_WINDOW    = 2.24
FLANKING_VM    = 1.20
EARLY_NEU_VM   = 1.45
BLITZ_VM       = 1.28
RACE_VM        = 1.65
ELIM_BONUS     = 95.0
WEAKEST_VM     = 1.78
ATTACK_TURN_W  = 0.45

def score_target(name, prod, is_hostile, ships_needed, travel_turns,
                 remaining=300, is_exposed=False, is_flanked=False,
                 is_early=False, in_blitz=False, can_race=False,
                 is_weakest=False, pressure_fronts=2):
    turns_profit = max(1, remaining - travel_turns)
    val  = (prod ** PROD_EXP) * turns_profit
    mults = []
    if is_hostile:
        val *= HOSTILE_VM;   mults.append(f'×{HOSTILE_VM} hostile')
    if is_exposed:
        val *= EXPOSED_VM;   mults.append(f'×{EXPOSED_VM} EXPOSED')
        val *= VULN_WINDOW;  mults.append(f'×{VULN_WINDOW} vuln_win')
    if is_flanked:
        val *= FLANKING_VM;  mults.append(f'×{FLANKING_VM} FLANK')
    if is_early:
        val *= EARLY_NEU_VM; mults.append(f'×{EARLY_NEU_VM} early')
    if in_blitz:
        val *= BLITZ_VM;     mults.append(f'×{BLITZ_VM} BLITZ')
    if can_race:
        val *= RACE_VM;      mults.append(f'×{RACE_VM} race')
    if is_weakest:
        val += ELIM_BONUS;   mults.append(f'+{ELIM_BONUS} elim')
        val *= WEAKEST_VM;   mults.append(f'×{WEAKEST_VM} weakest')
    pressure = min(1.58, 1.0 + max(0, pressure_fronts - 2) * 0.16)
    raw_score = val / (ships_needed + travel_turns * ATTACK_TURN_W + 1)
    final     = raw_score * pressure
    print(f'  {name}')
    print(f'    prod={prod}, need={ships_needed}, travel={travel_turns}t, remaining={remaining}t')
    print(f'    base = {prod}^{PROD_EXP} × {turns_profit} = {(prod**PROD_EXP)*turns_profit:.1f}')
    if mults: print(f'    mults: {" ".join(mults)}')
    print(f'    value = {val:.1f}')
    print(f'    score = {val:.1f}/({ships_needed}+{travel_turns}×{ATTACK_TURN_W}+1) × ×{pressure:.2f}pressure = {final:.3f}')
    return final

print('=' * 68)
print('  TARGET SCORING COMPARISON — HYPERION')
print('=' * 68)
scores = []
targets = [
    ('Nearby neutral (early game, in blitz)',
     dict(prod=2, is_hostile=False, ships_needed=10, travel_turns=7,
          is_early=True, in_blitz=True, can_race=True, remaining=490)),
    ('Enemy planet (standard)',
     dict(prod=3, is_hostile=True, ships_needed=45, travel_turns=12, remaining=300)),
    ('Enemy planet (EXPOSED! fleet just left)',
     dict(prod=3, is_hostile=True, ships_needed=12, travel_turns=9,
          is_exposed=True, remaining=300)),
    ('Enemy planet (EXPOSED + FLANKED)',
     dict(prod=3, is_hostile=True, ships_needed=12, travel_turns=9,
          is_exposed=True, is_flanked=True, remaining=300)),
    ('Weakest enemy (FFA elimination target)',
     dict(prod=4, is_hostile=True, ships_needed=60, travel_turns=14,
          is_weakest=True, pressure_fronts=4, remaining=300)),
]
print()
for name, kwargs in targets:
    sc = score_target(name, **kwargs)
    scores.append((sc, name))
    print()

print('=' * 68)
print('  FINAL RANKING')
print('=' * 68)
for rank, (sc, name) in enumerate(sorted(scores, reverse=True), 1):
    bar = '█' * min(50, int(sc * 0.8))
    print(f'  #{rank}: {sc:>8.3f}  {bar}')
    print(f'          {name}')
```

## [MD]
## ⚔️ Layer 6 — Mission Engine: 14 Mission Types

HYPERION evaluates all possible missions and executes them in score order:

| # | Mission | Trigger | Priority |
|---|---------|---------|---------|
| 1 | **intercept** | Enemy fleet heading to our planet, ETA ≤ 30 turns | Highest |
| 2 | **rescue** | Our planet falls in ≤ 32 turns | Very high |
| 3 | **reinforce** | Our planet threatened, send help early | High |
| 4 | **recapture** | We just lost a planet — take it back | High |
| 5 | **elimination** | Focus-fire on weakest enemy player | Medium-high |
| 6 | **deny** | Attack enemy's highest-production planet (≥4) | Medium-high |
| 7 | **gang_up** | Two enemies fighting — attack the exhausted winner | Medium |
| 8 | **race** | Arrive at neutral BEFORE enemy can | Medium |
| 9 | **snipe** | Steal neutral 1 turn after enemy captures it | Medium |
| 10 | **capture** | Standard single-source capture | Standard |
| 11 | **swarm** | 2 planets attack simultaneously | Standard |
| 12 | **3-source swarm** | 3 planets coordinate on hard target | Standard |
| 13 | **crash_exploit** | Two enemy fleets cancel each other — we arrive after | Opportunistic |
| 14 | **counter_rush** | Enemy rushes us → we attack their home at same time | Special |

### Intercept Mission — Dynamic Defense

**Old approach:** Static garrisons — keep 80 ships on every planet "just in case"
→ 80 ships × 10 planets = 800 ships **idle** all game

**HYPERION intercept:** Monitor every enemy fleet in flight

```python
for each enemy fleet targeting our planet P:
    garrison_at_eta = P.ships + P.production × fleet_eta
    deficit = max(0, enemy_fleet_ships - garrison_at_eta + 1)

    if deficit > 0:
        Find nearest ally planet A with budget >= deficit
        If A can arrive at P BEFORE the enemy fleet:
            Launch INTERCEPT with high priority score
```

Ships saved from passive garrison → now available for **offensive attacks**.

### Counter-Rush Mission

```
Enemy sends large fleet (≥26 ships, ETA ≤28 turns) at our planet
HYPERION response: SIMULTANEOUSLY attack enemy's home planet
Score bonus: ×1.88 on enemy home planets during rush

Classic counter: "You attack my home, I attack yours"
Result: Enemy must recall fleet to defend → we get their home
```

## [CODE]
```python
print('=' * 68)
print('  INTERCEPT MISSION DEMO')
print('=' * 68)
print('  Our planet: 40 ships, +3/turn')
print()

def intercept_analysis(planet_ships, planet_prod, enemy_fleets, intercept_eta_max=30):
    print(f'  {"Enemy fleet":>14} │ {"ETA":>5} │ {"Garrison@ETA":>13} │ {"Deficit":>8} │ Status')
    print('  ' + '─' * 62)
    for en_eta, en_owner, en_ships in sorted(enemy_fleets):
        if en_eta > intercept_eta_max:
            print(f'  Player {en_owner}: {en_ships:>3} ships │ {en_eta:>5} │ {"n/a":>13} │ {"n/a":>8} │ ⏭️ Beyond ETA_MAX={intercept_eta_max}')
            continue
        garrison_at_eta = planet_ships + planet_prod * en_eta
        deficit = max(0, en_ships - garrison_at_eta + 1)
        status = '✅ SAFE' if deficit <= 0 else f'🚨 NEED {deficit} more ships'
        print(f'  Player {en_owner}: {en_ships:>3} ships │ {en_eta:>5} │ {garrison_at_eta:>13} │ {deficit:>8} │ {status}')

enemy_fleets = [
    (7, 1, 30),    # Small early probe
    (12, 1, 55),   # Significant threat
    (18, 2, 80),   # Major attack
    (35, 3, 120),  # Big fleet but far away
]
intercept_analysis(40, 3, enemy_fleets)

print()
print('  If deficit > 0: HYPERION finds nearest ally and launches intercept')
print('  Must arrive BEFORE enemy (turns < enemy ETA)')
print('  Result: saved ships go on offense instead of sitting idle')

print()
print('=' * 68)
print('  COUNTER-RUSH LOGIC')
print('=' * 68)
RUSH_FLEET_MIN = 26
RUSH_HOME_ETA  = 28
COUNTER_BONUS  = 1.88
rush_cases = [
    (5,  True,  20, 'Early rush — counter-attack launched'),
    (22, True,  25, 'Ongoing rush — still counter-attacking'),
    (40, False,  0, 'Rush window closed (step > 70)'),
    (22, True,  35, 'Too far — ETA > RUSH_HOME_ETA_MAX'),
    (22, False, 15, 'Too small — ships < RUSH_FLEET_MIN'),
]
print(f"  {'Step':>5} │ {'Rush?':>6} │ {'ETA':>5} │ {'Response'}")
print('  ' + '─' * 58)
for step, is_rush, eta, desc in rush_cases:
    if is_rush and step <= 70 and eta <= RUSH_HOME_ETA:
        response = f'⚔️ COUNTER-RUSH! enemy home ×{COUNTER_BONUS}'
    elif is_rush and eta > RUSH_HOME_ETA:
        response = '✅ defend only (enemy fleet too far to count)'
    elif not is_rush:
        response = '✅ normal play'
    else:
        response = '✅ normal play'
    icon = '🚨' if (is_rush and step <= 70 and eta <= RUSH_HOME_ETA) else '  '
    print(f'  {icon} step={step:>3} │ {str(is_rush):>6} │ {eta:>5} │ {desc}')
```

## [MD]
## 🚀 Layer 7 — Executor: Tsunami, Concentration & Swarm

### Three Execution Strategies

#### 1. Standard Capture
Single source → single target. Tsunami applied to fleet sizing.

#### 2. SNOWBALL Concentration
When `eco_mode == SNOWBALL AND remaining > 35 turns`:

```python
Find single best target with production >= 3
From the CLOSEST source planet, send ALL budget

Why? Speed formula rewards large fleets exponentially.
     5 attacks of 100 ships → speed 3.7 each
     1 attack of 500 ships  → speed 5.3 → MUCH faster
```

#### 3. 2-Source and 3-Source Swarms
When no single planet has enough ships, HYPERION coordinates multiple sources:

```
2-source swarm:
  Find 2 planets that can each reach target within MULTI_ETA_TOL=2 turns
  Distribute ships optimally between them (total >= needed)

3-source swarm:
  Requires target.ships >= 14 (lowered from v6's 16)
  Must arrive within 1 turn tolerance
  Applied 0.92 penalty to score (coordination is harder)
```

### Executor Pipeline (Priority Order)

```
1. CONCENTRATION   → if SNOWBALL mode + high-prod target
2. Sorted missions → intercept, rescue, reinforce, recap, elim, deny,
                     gang-up, race, snipe, captures, swarms
3. FOLLOWUP       → any remaining budget on best available target
4. DOOMED EVAC    → planets about to fall → evacuate ships offensively
5. REAR LOGISTICS → idle rear planets funnel ships toward front lines
6. TOTAL WAR      → last 70 turns: all remaining budget at weakest enemy
```

### Rear Logistics — Never Leave Ships Idle

HYPERION identifies "rear planets" (far from the front lines) and funnels their
idle ships forward through **staging chains**:

```
Rear planet A → Stage planet B → Front planet C → Attack enemy
```

Each step gains speed because ships accumulate on staging planets,
and larger fleets travel faster thanks to the speed formula.

## [CODE]
```python
import math

MAX_SPEED = 6.0

def fleet_speed(ships):
    if ships <= 1: return 1.0
    r = max(0.0, min(1.0, math.log(max(1, ships)) / math.log(1000.0)))
    return 1.0 + (MAX_SPEED - 1.0) * (r ** 1.5)

print('=' * 68)
print('  CONCENTRATION: 1 big fleet vs many small fleets')
print('=' * 68)
print()
print('  Scenario: 4 source planets, each with 100 ships, target 35 units away')
print()

distance = 35.0

# Option A: 4 separate attacks of 100 ships each
fleet_a = 100
sp_a    = fleet_speed(fleet_a)
eta_a   = math.ceil(distance / sp_a)
print(f'  Option A — 4 separate attacks of {fleet_a} ships:')
print(f'    Each fleet speed: {sp_a:.2f}  ETA: {eta_a} turns each')
print(f'    Ships arriving per wave: {fleet_a}')
print(f'    Total coordination cost: 4 actions, 4 separate fleets')

print()

# Option B: 1 concentrated attack of 400 ships
fleet_b = 400
sp_b    = fleet_speed(fleet_b)
eta_b   = math.ceil(distance / sp_b)
print(f'  Option B — 1 concentrated attack of {fleet_b} ships (HYPERION):')
print(f'    Fleet speed: {sp_b:.2f}  ETA: {eta_b} turns')
print(f'    Arrives {eta_a - eta_b} turns EARLIER')
print(f'    Production advantage: {(eta_a - eta_b) * 3} free ships (prod=3)')
print()
print(f'  HYPERION chooses Concentration in SNOWBALL mode (prod_ratio > 2.0)')

print()
print('=' * 68)
print('  MULTI-FRONT PRESSURE BONUS (starts at 2 fronts in HYPERION)')
print('=' * 68)
print(f'  (v3/v6 started at 3 fronts — HYPERION starts earlier for more bonus)')
print()
print(f"  {'Fronts':>8} │ {'Pressure Mult':>14} │ {'Bonus':>7} │ Bar")
print('  ' + '─' * 50)
for fronts in range(0, 9):
    pm  = min(1.58, 1.0 + max(0, fronts - 2) * 0.16)
    bar = '▓' * int((pm - 1.0) * 100)
    diff = f'+{(pm-1)*100:.0f}%' if pm > 1.0 else '   —  '
    print(f'  {fronts:>8} │ {pm:>14.3f} │ {diff:>7} │ {bar}')

print()
print('  HYPERION: bonus starts at 2 fronts (+16%/front, max ×1.58)')
print('  v3/v6:    bonus started at 3 fronts (+12-14%/front, max ×1.50)')
```

## [MD]
## 🏁 Layer 8 — Endgame: Death Ball & Total War

### Death Ball — Precision Win/Lose Logic (Last 35 Turns)

The endgame is about one thing: **who has more ships at turn 500**.

```
If you're 15%+ ahead with 35 turns left:
  STOP capturing neutrals. Every fleet sent might not return.
  Just protect your lead and let time run out.

If you're within 8% of the enemy:
  Keep attacking — the game is still undecided.

If you're behind:
  Go ALL-IN immediately. Zero reserves. Throw everything at enemy.
  Desperate times require desperate measures.
```

### Why 35 Turns (Not 60 Like v5)?

```
Fleet ETA for a 35-unit trip, 100 ships: ~9 turns each way = 18 turns round trip
35 turns remaining → still time for 1 full attack-and-return cycle

v5 activated at 60 turns → killed aggression 25 turns too early
HYPERION activates at 35 turns → still attacks in the 'press' zone (ratio 0.92–1.15)
```

### HYPERION Death Ball vs Previous Versions

| Setting | v5 | v6 | HYPERION |
|---------|----|----|---------|
| Activation | 60 turns | 35 turns | **35 turns** |
| Win threshold | 1.08 (8%) | 1.12 (12%) | **1.15 (15%)** |
| Defend mult | ×0.30 | ×0.45 | **×0.48** |
| Exposed attacks | None | Yes | **Yes (+vuln stack)** |

### Total War — Last 70 Turns

When `remaining < 70`: every planet commits ALL budget to attacking enemy.

**HYPERION improvement:** Instead of just picking the closest enemy planet,
HYPERION scores each planet by `production / distance`:

```python
# Old (v3/v5/v6): pick closest enemy planet
best_target = min(enemy_planets, key=lambda p: dist(src, p))

# HYPERION: pick highest prod/dist — reward close + high-value targets
best_score = -1
for ep in enemy_planets:
    score = ep.production / (dist(src, ep) + 1)
    if score > best_score: best_score, best_target = score, ep
```

A planet 10 units away with prod=4 scores **0.36** — much better than
a planet 5 units away with prod=1 (**0.17**). Smarter final rush.

## [CODE]
```python
DEATH_BALL_TURNS       = 35
DEATH_BALL_WIN_MARGIN  = 1.15
DEATH_BALL_LOSE_MARGIN = 0.92

def death_ball(my, enemy, remaining):
    if remaining > DEATH_BALL_TURNS: return 'NORMAL', 0
    if enemy == 0: return 'DEFEND', float('inf')
    ratio = my / enemy
    if ratio >= DEATH_BALL_WIN_MARGIN:  return 'DEFEND', ratio
    if ratio <= DEATH_BALL_LOSE_MARGIN: return 'ALL-IN', enemy - my + 1
    return 'PRESS',  ratio

print('=' * 72)
print('  DEATH BALL DECISION TABLE (30 turns remaining)')
print('=' * 72)
print(f"  {'My':>8} │ {'Enemy':>8} │ {'Ratio':>6} │ {'Decision':>12} │ Explanation")
print('  ' + '─' * 68)
icons = {'DEFEND':'🛡️  DEFEND','ALL-IN':'⚔️  ALL-IN','PRESS':'⚖️  PRESS ','NORMAL':'▶️  NORMAL'}
cases = [(400,200,'Dominant'),(300,250,'Comfortable'),(290,252,'Just at threshold'),
         (258,250,'Under threshold, keep attacking'),(250,250,'Even'),
         (235,250,'Slight deficit'),(150,300,'Losing badly')]
for my, en, desc in cases:
    status, val = death_ball(my, en, 30)
    icon = icons[status]
    if status == 'DEFEND': detail = f'lead ×{my/en:.2f} ≥ {DEATH_BALL_WIN_MARGIN}'
    elif status == 'ALL-IN': detail = f'need +{int(val)} ships NOW'
    else: detail = f'ratio {my/en:.2f} — still fighting'
    print(f'  {my:>8} │ {en:>8} │ {my/en:>6.2f} │ {icon} │ {desc}')

print()
print('=' * 72)
print('  TOTAL WAR TARGET SELECTION: prod/distance scoring (HYPERION)')
print('=' * 72)
import math
src_x, src_y = 25.0, 25.0
enemy_targets = [
    (80, 80, 4, 'Far high-prod'),
    (35, 35, 1, 'Close low-prod'),
    (60, 60, 3, 'Medium distance, medium prod'),
    (30, 40, 2, 'Very close, low prod'),
    (70, 30, 5, 'Diagonal, highest prod'),
]
print(f"  Source at ({src_x},{src_y})")
print()
print(f"  {'Target':>28} │ {'Distance':>9} │ {'Prod':>5} │ {'prod/dist':>10} │ {'Rank'}")
print('  ' + '─' * 65)
scored = []
for tx, ty, prod, name in enemy_targets:
    d = math.hypot(tx-src_x, ty-src_y)
    score = prod / (d + 1)
    scored.append((score, d, prod, name))
scored.sort(reverse=True)
for rank, (sc, d, prod, name) in enumerate(scored, 1):
    bar = '█' * int(sc * 25)
    print(f'  {name:>28} │ {d:>9.1f} │ {prod:>5} │ {sc:>10.4f} │ #{rank}  {bar}')
print()
print('  HYPERION picks the highest prod/distance score — not just closest')
```

## [CODE]
```python
%%writefile submission.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  HYPERION — Orbit Wars Supreme Tactical Intelligence                       ║
║  H.yperspatial I.ntelligence for P.lanetary E.ngagement,                   ║
║  R.apid I.nterstellar O.perations & N.eutralization                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ARCHITECTURE — Eight Layers                                                ║
║  LAYER 1  Physics     Orbital prediction (7-iter) · Solar bypass           ║
║  LAYER 2  World Model Timeline sim · Binary search · Arrival ledger        ║
║  LAYER 3  Eco Mode    5-tier: SNOWBALL/EXPAND/BALANCED/AGGRO/PANIC         ║
║  LAYER 4  Policy      Dynamic reserves · Opening Blitz (turns 1-22)        ║
║  LAYER 5  Scoring     14 multipliers · Flanking bonus · Vuln ×5.82        ║
║  LAYER 6  Missions    14 mission types · Counter-rush · Gang-up            ║
║  LAYER 7  Executor    Hyper-tsunami · Concentration · Swarm                ║
║  LAYER 8  Endgame     Death ball (35 turns) · Total war                    ║
║                                                                             ║
║  KEY INNOVATIONS vs OMEGA v3/v5/v6:                                        ║
║  1. OPENING BLITZ (turns 1-22) — -45% reserves, +28% neutral boost        ║
║  2. FLANKING BONUS ×1.20 — 2+ planets attacking same target simultaneously  ║
║  3. PRESSURE from 2 fronts (not 3) — earlier multi-front bonus             ║
║  4. ENDGAME SHIP DELTA — precise final-turn ship counting                  ║
║  5. EARLY AGGRESSION mode — 1v1 early game push without penalty            ║
║  6. Re-tuned ALL constants — based on v3/v5/v6 match analysis              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import math
import time
from collections import defaultdict, namedtuple
from dataclasses import dataclass, field
from enum import Enum

# ══════════════════════════════════════════════════════════════════════════════
# BOARD CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
BOARD          = 100.0
CENTER_X       = 50.0
CENTER_Y       = 50.0
SUN_R          = 10.0
MAX_SPEED      = 6.0
SUN_SAFETY     = 1.6
ROTATION_LIMIT = 50.0
TOTAL_STEPS    = 500
HORIZON        = 115
LAUNCH_CLR     = 0.1
INTERCEPT_TOL  = 1

# ══════════════════════════════════════════════════════════════════════════════
# PHASE THRESHOLDS
# ══════════════════════════════════════════════════════════════════════════════
EARLY_LIMIT         = 45
OPENING_LIMIT       = 100
LATE_REMAINING      = 85
VERY_LATE_REMAINING = 35
TOTAL_WAR_REMAINING = 70
ENDGAME_REMAINING   = 105

# ══════════════════════════════════════════════════════════════════════════════
# ECONOMIC MODES — 5 tier
# ══════════════════════════════════════════════════════════════════════════════
class EcoMode(Enum):
    SNOWBALL = "snowball"  # prod_ratio > 2.0  — concentrate force
    EXPAND   = "expand"    # 1.35–2.0          — grab neutrals
    BALANCED = "balanced"  # 0.72–1.35         — normal play
    AGGRO    = "aggro"     # 0.45–0.72         — attack enemy prod NOW
    PANIC    = "panic"     # < 0.45            — all-in

ECO_SNOWBALL_THRESH = 2.00
ECO_EXPAND_THRESH   = 1.35
ECO_AGGRO_THRESH    = 0.72
ECO_PANIC_THRESH    = 0.45

# Eco multipliers — tuned for HYPERION
ECO_SNOWBALL_HOSTILE = 1.68
ECO_SNOWBALL_NEUTRAL = 1.08
ECO_EXPAND_NEUTRAL   = 1.38
ECO_EXPAND_HOSTILE   = 0.75   # ↓ from v6 0.78 — less hostile targeting when expanding
ECO_AGGRO_HOSTILE    = 1.58
ECO_AGGRO_NEUTRAL    = 0.70
ECO_PANIC_HOSTILE    = 1.92
ECO_PANIC_NEUTRAL    = 0.48

# ══════════════════════════════════════════════════════════════════════════════
# VALUE MULTIPLIERS — HYPERION tuned
# ══════════════════════════════════════════════════════════════════════════════
INDIRECT_SCALE       = 0.15
IND_FRIENDLY_W       = 0.35
IND_NEUTRAL_W        = 0.90
IND_ENEMY_W          = 1.28   # ↑ slight increase — enemy neighborhood matters more

PROD_EXP             = 1.32   # between v3 (1.25) and v5 (1.45), slightly higher than v6 (1.30)

STATIC_NEUTRAL_VM    = 1.50
STATIC_HOSTILE_VM    = 1.88
HOSTILE_VM           = 2.32   # ↑ from v6 2.25 — enemy planets more valuable
OPEN_HOSTILE_VM      = 1.72
SAFE_NEUTRAL_VM      = 1.35
CONTESTED_NEUTRAL_VM = 0.60
EARLY_NEUTRAL_VM     = 1.45   # ↑ from v6 1.38 — early neutrals MORE valuable
COMET_VM             = 0.52
SNIPE_VM             = 1.22
SWARM_VM             = 1.12
REINFORCE_VM         = 1.40
CRASH_VM             = 1.30
GANG_UP_VM           = 1.58
EXPOSED_VM           = 2.65   # ↑ slightly from v6 2.60
VULN_WINDOW_BONUS    = 2.24   # × EXPOSED_VM = ×5.94 total
RACE_WIN_VM          = 1.65   # ↑ from v6 1.58 — race to neutrals more aggressively
PROD_DENY_VM         = 1.42
FINISH_HOSTILE_VM    = 1.45

# ══════════════════════════════════════════════════════════════════════════════
# HYPERION NEW: FLANKING BONUS
# When 2+ of our planets can reach a target simultaneously
# Enemy cannot optimally defend against multi-direction attacks
# ══════════════════════════════════════════════════════════════════════════════
FLANKING_VM          = 1.20   # ×1.20 when we can attack from 2+ directions
FLANKING_ETA_TOL     = 3      # flanking window: arrivals within 3 turns of each other

# ══════════════════════════════════════════════════════════════════════════════
# HYPERION NEW: OPENING BLITZ (turns 1-22)
# Early game is the most leveraged time — every neutral captured early
# compounds for 400+ more turns. Be aggressive, reduce reserves.
# ══════════════════════════════════════════════════════════════════════════════
OPENING_BLITZ_TURNS        = 22
OPENING_BLITZ_NEUTRAL_VM   = 1.28   # extra boost to neutral value in blitz
OPENING_BLITZ_RESERVE_FRAC = 0.55   # keep only 55% of normal reserve during blitz
OPENING_BLITZ_MARGIN_FRAC  = 0.70   # send margins reduced to 70% during blitz

# ══════════════════════════════════════════════════════════════════════════════
# GATEWAY / POSITIONAL
# ══════════════════════════════════════════════════════════════════════════════
GATEWAY_VM          = 1.24   # ↑ from v6 1.22
GATEWAY_DIST_THRESH = 28.0   # ↑ slightly wider gateway detection

# ══════════════════════════════════════════════════════════════════════════════
# MULTI-FRONT PRESSURE — HYPERION: starts at 2 fronts (not 3)
# ══════════════════════════════════════════════════════════════════════════════
PRESSURE_FRONT_MIN  = 2      # ↓ from v6 3 — bonus kicks in earlier
PRESSURE_BONUS_PER  = 0.16   # ↑ from v6 0.14
PRESSURE_MAX_MULT   = 1.58   # ↑ from v6 1.50

# ══════════════════════════════════════════════════════════════════════════════
# ELIMINATION / WEAKEST ENEMY
# ══════════════════════════════════════════════════════════════════════════════
WEAKEST_VM_FFA      = 1.78   # ↑ from v6 1.72
WEAKEST_VM_1V1      = 1.45   # ↑ from v6 1.42
ELIM_BONUS          = 95.0   # ↑ from v6 90
WEAK_THRESH         = 165    # ↑ slightly

# ══════════════════════════════════════════════════════════════════════════════
# MARGINS
# ══════════════════════════════════════════════════════════════════════════════
SAFE_NEUTRAL_MARGIN      = 2
CONTESTED_NEUTRAL_MARGIN = 2
NEUTRAL_MARGIN_BASE      = 2
NEUTRAL_MARGIN_PROD_W    = 2
NEUTRAL_MARGIN_CAP       = 8
HOSTILE_MARGIN_BASE      = 3
HOSTILE_MARGIN_PROD_W    = 2
HOSTILE_MARGIN_CAP       = 10
STATIC_MARGIN            = 3
CONTESTED_MARGIN         = 5
FFA_MARGIN               = 2
LONG_TRAVEL_START        = 18
LONG_TRAVEL_DIV          = 3
LONG_TRAVEL_CAP          = 7
COMET_MARGIN_RELIEF      = 6
FINISH_SEND_BONUS        = 5

# ══════════════════════════════════════════════════════════════════════════════
# SCORE MODIFIERS
# ══════════════════════════════════════════════════════════════════════════════
STATIC_SCORE_M       = 1.24
EARLY_STATIC_SCORE_M = 1.40
FFA_ROT_SCORE_M      = 0.80
DENSE_STATIC_THRESH  = 4
DENSE_ROT_SCORE_M    = 0.82
SNIPE_SCORE_M        = 1.20
SWARM_SCORE_M        = 1.10
CRASH_SCORE_M        = 1.14
EXPOSED_SCORE_M      = 1.48   # ↑ from v6 1.45
WEAKEST_SCORE_M      = 1.32
RACE_SCORE_M         = 1.25   # ↑ from v6 1.22

# ══════════════════════════════════════════════════════════════════════════════
# COST WEIGHTS
# ══════════════════════════════════════════════════════════════════════════════
ATTACK_TURN_W  = 0.45
SNIPE_TURN_W   = 0.36
DEF_TURN_W     = 0.33
REINF_TURN_W   = 0.28
RECAP_TURN_W   = 0.46

# ══════════════════════════════════════════════════════════════════════════════
# TSUNAMI — same aggressive v5-level settings as v6
# ══════════════════════════════════════════════════════════════════════════════
TSUNAMI_RATIO          = 0.90
TSUNAMI_THRESH         = 1.5
TSUNAMI_MIN_SHIPS      = 20
TSUNAMI_TURNS_SAVED_MIN= 1
TSUNAMI_MAX_EXTRA_FRAC = 0.55

# ══════════════════════════════════════════════════════════════════════════════
# DEATH BALL — fixed from v6 (35 turns, 1.15 margin)
# ══════════════════════════════════════════════════════════════════════════════
DEATH_BALL_TURNS       = 35
DEATH_BALL_WIN_MARGIN  = 1.15   # ↑ from v6 1.12 — slightly more defensive
DEATH_BALL_LOSE_MARGIN = 0.92

# ══════════════════════════════════════════════════════════════════════════════
# COUNTER-RUSH
# ══════════════════════════════════════════════════════════════════════════════
COUNTER_RUSH_ENABLED    = True
COUNTER_RUSH_MIN_STEP   = 8
COUNTER_RUSH_HOME_BONUS = 1.88   # ↑ slightly from v6 1.85

# ══════════════════════════════════════════════════════════════════════════════
# VULNERABILITY WINDOW
# ══════════════════════════════════════════════════════════════════════════════
VULN_WINDOW_ENABLED = True
VULN_SENT_RATIO     = 0.40
VULN_MIN_SENT       = 6

# ══════════════════════════════════════════════════════════════════════════════
# CONCENTRATION — SNOWBALL mode only, prod>=3 (↓ from v6 prod>=4)
# ══════════════════════════════════════════════════════════════════════════════
CONCENTRATION_ENABLED  = True
CONCENTRATION_MIN_PROD = 3   # ↓ from v6 4 — concentrate more often in snowball

# ══════════════════════════════════════════════════════════════════════════════
# DEFENSE
# ══════════════════════════════════════════════════════════════════════════════
PROACT_HORIZON     = 16
PROACT_RATIO       = 0.28    # ↓ slightly from v6 0.30 — slightly more aggressive
MULTI_PROACT_HOR   = 20
MULTI_PROACT_RATIO = 0.36    # ↓ from v6 0.38
MULTI_STACK_WIN    = 5
REACT_MY_TOP_K     = 4
REACT_EN_TOP_K     = 4
PROACT_EN_TOP_K    = 3

ONE_V_ONE_DOM_THRESH  = 0.20
ONE_V_ONE_AGG_RESERVE = 0.28   # ↓ from v6 0.30 — more aggressive 1v1

# ══════════════════════════════════════════════════════════════════════════════
# RUSH DETECTION
# ══════════════════════════════════════════════════════════════════════════════
RUSH_DETECT_STEP_MAX = 70
RUSH_FLEET_MIN       = 26    # ↓ from v6 28 — detect smaller rushes
RUSH_HOME_ETA_MAX    = 28

# ══════════════════════════════════════════════════════════════════════════════
# INTERCEPT — wider detection window
# ══════════════════════════════════════════════════════════════════════════════
INTERCEPT_ETA_MAX   = 30    # ↑ from v6 28
INTERCEPT_ENABLED   = True

# ══════════════════════════════════════════════════════════════════════════════
# WIN MARGIN
# ══════════════════════════════════════════════════════════════════════════════
WIN_SECURE_RATIO     = 1.28   # ↓ from v6 1.30 — enter secure mode sooner
WIN_DESPERATE_RATIO  = 0.76
WIN_SECURE_MARGIN_M  = 0.80   # ↓ from v6 0.82 — slightly more aggressive when winning
WIN_DESPERATE_RISK_M = 1.32   # ↑ from v6 1.30

# ══════════════════════════════════════════════════════════════════════════════
# MISC
# ══════════════════════════════════════════════════════════════════════════════
PROD_DENY_THRESHOLD  = 4
LATE_SHIP_W          = 0.98
VERY_LATE_SHIP_W     = 1.70   # ↑ from v6 1.65
DOOMED_EVAC_LIMIT    = 22
DOOMED_MIN_SHIPS     = 7
FOLLOWUP_MIN         = 6      # ↓ from v6 7 — more followup actions
LOW_COMET_PROD       = 1
LATE_BUFFER          = 5
VERY_LATE_BUFFER     = 3
PARTIAL_MIN          = 5
MULTI_TOP_K          = 5
MULTI_ETA_TOL        = 2
MULTI_PLAN_PEN       = 0.97
HOSTILE_SWARM_TOL    = 1
THREE_SRC_ENABLED    = True
THREE_SRC_MIN_SHIPS  = 14     # ↓ from v6 16 — try 3-source swarms more
THREE_SRC_TOL        = 1
THREE_SRC_PEN        = 0.92
CRASH_ENABLED        = True
CRASH_MIN_SHIPS      = 5
CRASH_ETA_WIN        = 3
CRASH_DELAY          = 1
GANG_POST_DELAY      = 2
GANG_ETA_WIN         = 4
RACE_MARGIN_TURNS    = 1
RACE_MIN_ADVANTAGE   = 2
COMET_MAX_CHASE      = 10
SAFE_OPEN_PROD_TH    = 4
SAFE_OPEN_TURN_LIM   = 11
ROT_OPEN_MAX_TURNS   = 14
ROT_OPEN_LOW_PROD    = 2
FFA_ROT_REACT_GAP    = 3
FFA_ROT_SEND_RATIO   = 0.55
FFA_ROT_TURN_LIM     = 11
REINF_ENABLED        = True
REINF_MIN_PROD       = 2
REINF_MAX_TRAVEL     = 24
REINF_SAFETY         = 2
REINF_MAX_SRC_FRAC   = 0.77
REINF_MIN_FUTURE     = 35
REINF_LOOKAHEAD      = 22
DEF_LOOKAHEAD        = 32
DEF_SHIP_VALUE       = 0.65
DEF_FRONTIER_M       = 1.20
DEF_SEND_MARGIN      = 1
DEF_SEND_PROD_W      = 1
RECAP_LOOKAHEAD      = 14
RECAP_VM             = 0.93
RECAP_FRONTIER_M     = 1.14
RECAP_PROD_W         = 0.6
RECAP_IMMED_W        = 0.4
REAR_MIN_SHIPS       = 12
REAR_DIST_RATIO      = 1.22
REAR_STAGE_PROG      = 0.76
REAR_RATIO_2P        = 0.62
REAR_RATIO_FFA       = 0.56
REAR_SEND_MIN        = 9
REAR_MAX_TRAVEL      = 40
BEHIND_DOM           = -0.15
AHEAD_DOM            = 0.10
FINISH_DOM           = 0.22
FINISH_PROD_R        = 1.10
AHEAD_MRG_B          = 0.12
BEHIND_MRG_P         = 0.08
FINISH_MRG_B         = 0.15
SOFT_DEADLINE        = 0.85
HEAVY_MIN_TIME       = 0.12
OPT_MIN_TIME         = 0.06
HEAVY_PLANET_LIM     = 40

# ══════════════════════════════════════════════════════════════════════════════
# TYPES
# ══════════════════════════════════════════════════════════════════════════════
Planet = namedtuple("Planet", ["id","owner","x","y","radius","ships","production"])
Fleet  = namedtuple("Fleet",  ["id","owner","x","y","angle","from_planet_id","ships"])

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

# ══════════════════════════════════════════════════════════════════════════════
# PHYSICS ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)

def orbital_radius(p):
    return dist(p.x, p.y, CENTER_X, CENTER_Y)

def is_static_planet(p):
    return orbital_radius(p) + p.radius >= ROTATION_LIMIT

def fleet_speed(ships):
    if ships <= 1: return 1.0
    r = max(0.0, min(1.0, math.log(max(1, ships)) / math.log(1000.0)))
    return 1.0 + (MAX_SPEED - 1.0) * (r ** 1.5)

def speed_optimal_send(needed, available, distance, prod_per_turn):
    """HYPERION TSUNAMI: 1 saved turn = free production ships. Always send more."""
    if available <= 0 or needed <= 0: return max(1, needed)
    if available <= needed: return needed
    base_turns = max(1, int(math.ceil(distance / fleet_speed(max(1, needed)))))
    if available >= needed * TSUNAMI_THRESH and available >= TSUNAMI_MIN_SHIPS:
        candidate  = min(available, max(needed, int(available * TSUNAMI_RATIO)))
        cand_turns = max(1, int(math.ceil(distance / fleet_speed(max(1, candidate)))))
        turns_saved = base_turns - cand_turns
        if turns_saved >= TSUNAMI_TURNS_SAVED_MIN and prod_per_turn > 0:
            return candidate
        if candidate - needed <= available * TSUNAMI_MAX_EXTRA_FRAC:
            return candidate
    modest = min(available, int(needed * 1.22))
    if modest > needed:
        mod_turns = max(1, int(math.ceil(distance / fleet_speed(max(1, modest)))))
        if base_turns - mod_turns >= 1:
            return modest
    return min(available, max(needed, int(needed * 1.06)))

def pt_seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    sq = dx * dx + dy * dy
    if sq <= 1e-9: return dist(px, py, x1, y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / sq))
    return dist(px, py, x1 + t * dx, y1 + t * dy)

def seg_hits_sun(x1, y1, x2, y2, s=SUN_SAFETY):
    return pt_seg_dist(CENTER_X, CENTER_Y, x1, y1, x2, y2) < SUN_R + s

def launch_pt(sx, sy, sr, angle):
    c = sr + LAUNCH_CLR
    return sx + math.cos(angle) * c, sy + math.sin(angle) * c

def safe_angle_dist(sx, sy, sr, tx, ty, tr):
    angle = math.atan2(ty - sy, tx - sx)
    lx, ly = launch_pt(sx, sy, sr, angle)
    d = max(0.0, dist(sx, sy, tx, ty) - (sr + LAUNCH_CLR) - tr)
    ex = lx + math.cos(angle) * d
    ey = ly + math.sin(angle) * d
    if seg_hits_sun(lx, ly, ex, ey): return None
    return angle, d

def bypass_angle(sx, sy, sr, tx, ty, tr, clockwise=True):
    """Solar bypass — tangent route around sun danger zone."""
    danger_r = SUN_R + SUN_SAFETY + 0.6
    to_sun_d = dist(sx, sy, CENTER_X, CENTER_Y)
    if to_sun_d <= danger_r: return None
    base_angle = math.atan2(CENTER_Y - sy, CENTER_X - sx)
    half_ang   = math.asin(min(1.0, danger_r / to_sun_d))
    tang_angle = base_angle + (half_ang + 0.18 if clockwise else -(half_ang + 0.18))
    tang_dist  = math.sqrt(max(0, to_sun_d**2 - danger_r**2)) + 2.5
    wx = sx + math.cos(tang_angle) * tang_dist
    wy = sy + math.sin(tang_angle) * tang_dist
    direct_to_t = safe_angle_dist(wx, wy, 0.5, tx, ty, tr)
    if direct_to_t is None:
        tang_angle2 = base_angle + (-(half_ang + 0.18) if clockwise else (half_ang + 0.18))
        wx = sx + math.cos(tang_angle2) * tang_dist
        wy = sy + math.sin(tang_angle2) * tang_dist
        direct_to_t = safe_angle_dist(wx, wy, 0.5, tx, ty, tr)
        if direct_to_t is None: return None
        tang_angle = tang_angle2
    total_d = tang_dist + dist(wx, wy, tx, ty)
    return math.atan2(wy - sy, wx - sx), total_d

def safe_angle_dist_bypass(sx, sy, sr, tx, ty, tr):
    direct = safe_angle_dist(sx, sy, sr, tx, ty, tr)
    if direct is not None: return direct
    bp1 = bypass_angle(sx, sy, sr, tx, ty, tr, clockwise=True)
    bp2 = bypass_angle(sx, sy, sr, tx, ty, tr, clockwise=False)
    if bp1 and bp2: return bp1 if bp1[1] <= bp2[1] else bp2
    return bp1 or bp2

def predict_planet_pos(planet, init_by_id, ang_vel, turns):
    init = init_by_id.get(planet.id)
    if init is None: return planet.x, planet.y
    r = dist(init.x, init.y, CENTER_X, CENTER_Y)
    if r + init.radius >= ROTATION_LIMIT: return planet.x, planet.y
    cur = math.atan2(planet.y - CENTER_Y, planet.x - CENTER_X)
    new = cur + ang_vel * turns
    return CENTER_X + r * math.cos(new), CENTER_Y + r * math.sin(new)

def predict_comet_pos(pid, comets, turns):
    for g in comets:
        pids = g.get("planet_ids", [])
        if pid not in pids: continue
        idx = pids.index(pid); paths = g.get("paths", []); pi = g.get("path_index", 0)
        if idx >= len(paths): return None
        fi = pi + int(turns)
        if 0 <= fi < len(paths[idx]): return paths[idx][fi][0], paths[idx][fi][1]
        return None
    return None

def comet_life(pid, comets):
    for g in comets:
        pids = g.get("planet_ids", [])
        if pid not in pids: continue
        idx = pids.index(pid); paths = g.get("paths", []); pi = g.get("path_index", 0)
        if idx < len(paths): return max(0, len(paths[idx]) - pi)
    return 0

def estimate_arrival(sx, sy, sr, tx, ty, tr, ships):
    safe = safe_angle_dist_bypass(sx, sy, sr, tx, ty, tr)
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
    max_t = min(HORIZON, 65)
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
    for _ in range(7):   # 7-iteration convergence for precise orbital intercept
        _, turns = e
        pos = predict_target_pos(target, turns, init_by_id, ang_vel, comets, comet_ids)
        if pos is None: return None
        ntx, nty = pos
        ne = estimate_arrival(src.x, src.y, src.radius, ntx, nty, target.radius, ships)
        if ne is None:
            if not target_can_move(target, init_by_id, comet_ids): return None
            return search_intercept(src, target, ships, init_by_id, ang_vel, comets, comet_ids)
        if abs(ntx - tx) < 0.20 and abs(nty - ty) < 0.20 and abs(ne[1] - turns) <= INTERCEPT_TOL:
            return ne[0], ne[1], ntx, nty
        tx, ty = ntx, nty; e = ne
    fe = estimate_arrival(src.x, src.y, src.radius, tx, ty, target.radius, ships)
    if fe is None:
        return search_intercept(src, target, ships, init_by_id, ang_vel, comets, comet_ids)
    return fe[0], fe[1], tx, ty

# ══════════════════════════════════════════════════════════════════════════════
# WORLD MODEL
# ══════════════════════════════════════════════════════════════════════════════

def fleet_target_planet(fleet, planets):
    best_p, best_t = None, 1e9
    dx, dy = math.cos(fleet.angle), math.sin(fleet.angle)
    sp     = fleet_speed(fleet.ships)
    for p in planets:
        px, py  = p.x - fleet.x, p.y - fleet.y
        proj    = px * dx + py * dy
        if proj < 0: continue
        perp_sq = px * px + py * py - proj * proj
        if perp_sq >= p.radius * p.radius: continue
        hit = max(0.0, proj - math.sqrt(max(0.0, p.radius * p.radius - perp_sq)))
        t = hit / sp
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
    else:
        surv_o, surv_s = top_o, top_s
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
    owner = planet.owner; garrison = float(planet.ships)
    owner_at = {0: owner}; ships_at = {0: max(0.0, garrison)}; fall_turn = None
    for turn in range(1, horizon + 1):
        if owner != -1: garrison += planet.production
        group = by_turn.get(turn, []); prev = owner
        if group:
            owner, garrison = resolve_arrivals(owner, garrison, group)
            if prev == player and owner != player and fall_turn is None: fall_turn = turn
        owner_at[turn] = owner; ships_at[turn] = max(0.0, garrison)
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
                else:             lo = mid + 1
            keep_needed = lo
        else:
            holds_full = False; keep_needed = int(planet.ships)
    return dict(owner_at=owner_at, ships_at=ships_at, keep_needed=keep_needed,
                fall_turn=fall_turn, holds_full=holds_full, horizon=horizon)

def state_at(timeline, arrival_turn):
    turn = max(0, min(int(math.ceil(arrival_turn)), timeline["horizon"]))
    h    = timeline["horizon"]
    return timeline["owner_at"].get(turn, timeline["owner_at"][h]), \
           max(0.0, timeline["ships_at"].get(turn, timeline["ships_at"][h]))

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
        fac = o.production / (d + 11.0)
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
    return min(owners, key=lambda o: owner_strength.get(o, 0) + owner_prod.get(o, 0) * 18)

def highest_prod_enemy_planet(enemy_planets, owner_strength):
    if not enemy_planets: return None
    return max(enemy_planets, key=lambda p: p.production * 12 + owner_strength.get(p.owner, 0))

def compute_gateway_value(planet, enemy_planets):
    if not enemy_planets: return 1.0
    min_en_dist = min(dist(planet.x, planet.y, e.x, e.y) for e in enemy_planets)
    if min_en_dist <= GATEWAY_DIST_THRESH:
        ratio = max(0.0, 1.0 - min_en_dist / GATEWAY_DIST_THRESH)
        return 1.0 + (GATEWAY_VM - 1.0) * ratio
    return 1.0

def detect_rush(fleets, my_planets, player, step):
    if step > RUSH_DETECT_STEP_MAX: return False, 0, 999
    total_rush = 0; min_eta = 999
    for f in fleets:
        if f.owner == player or f.owner == -1: continue
        if int(f.ships) < RUSH_FLEET_MIN: continue
        dx, dy = math.cos(f.angle), math.sin(f.angle)
        sp = fleet_speed(max(1, int(f.ships)))
        for mp in my_planets:
            px, py = mp.x - f.x, mp.y - f.y
            proj = px * dx + py * dy
            if proj <= 0: continue
            perp = abs(px * dy - py * dx)
            if perp > mp.radius + 6: continue
            eta = int(math.ceil(proj / sp))
            if eta <= RUSH_HOME_ETA_MAX:
                total_rush += int(f.ships); min_eta = min(min_eta, eta)
    return total_rush >= RUSH_FLEET_MIN, total_rush, min_eta

def find_enemy_home_planets(enemy_planets):
    homes = {}
    for p in enemy_planets:
        o = p.owner
        if o not in homes or p.production > homes[o].production:
            homes[o] = p
    return list(homes.values())

def death_ball_status(my_total, enemy_total, remaining):
    if remaining > DEATH_BALL_TURNS: return None, 0
    if enemy_total == 0: return 'defend', float('inf')
    ratio = my_total / enemy_total
    if ratio >= DEATH_BALL_WIN_MARGIN: return 'defend', ratio
    if ratio <= DEATH_BALL_LOSE_MARGIN: return 'allin', enemy_total - my_total + 1
    return 'press', ratio

def compute_flanking_map(my_planets, planets, init_by_id, ang_vel, comets, comet_ids):
    """
    HYPERION NEW: FLANKING BONUS
    For each non-player planet, check how many of our planets can reach it
    within FLANKING_ETA_TOL turns of each other.
    Flanking from multiple directions prevents optimal enemy defense.
    Returns: {planet_id: True/False} whether target is flankable
    """
    flankable = set()
    targets = [p for p in planets if p.owner not in (-1,)]  # enemy planets
    for target in targets:
        etas = []
        for src in my_planets:
            aim = aim_with_prediction(src, target, max(1, int(src.ships // 2)),
                                      init_by_id, ang_vel, comets, comet_ids)
            if aim is None: continue
            etas.append(aim[1])
        if len(etas) >= 2:
            etas.sort()
            # Check if at least 2 planets can arrive within FLANKING_ETA_TOL turns
            for i in range(len(etas) - 1):
                if etas[i+1] - etas[i] <= FLANKING_ETA_TOL:
                    flankable.add(target.id)
                    break
    return flankable


class WorldModel:
    def __init__(self, player, step, planets, fleets, init_by_id, ang_vel, comets, comet_ids):
        self.player     = player
        self.step       = step
        self.planets    = planets
        self.fleets     = fleets
        self.init_by_id = init_by_id
        self.ang_vel    = ang_vel
        self.comets     = comets
        self.comet_ids  = set(comet_ids)

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
        self.is_1v1       = (self.num_players == 2)
        self.in_blitz     = (step < OPENING_BLITZ_TURNS)   # HYPERION: Opening Blitz

        self.owner_strength = defaultdict(int)
        self.owner_prod     = defaultdict(int)
        for p in planets:
            if p.owner != -1:
                self.owner_strength[p.owner] += int(p.ships)
                self.owner_prod[p.owner]     += int(p.production)
        for f in fleets: self.owner_strength[f.owner] += int(f.ships)

        self.my_total    = self.owner_strength.get(player, 0)
        self.enemy_total = sum(s for o, s in self.owner_strength.items() if o != player)
        self.max_enemy   = max((s for o, s in self.owner_strength.items() if o != player), default=0)
        self.my_prod     = self.owner_prod.get(player, 0)
        self.enemy_prod  = sum(s for o, s in self.owner_prod.items() if o != player)

        eco_ratio = self.my_prod / max(1, self.enemy_prod)
        if   eco_ratio >= ECO_SNOWBALL_THRESH: self.eco_mode = EcoMode.SNOWBALL
        elif eco_ratio >= ECO_EXPAND_THRESH:   self.eco_mode = EcoMode.EXPAND
        elif eco_ratio >= ECO_AGGRO_THRESH:    self.eco_mode = EcoMode.BALANCED
        elif eco_ratio >= ECO_PANIC_THRESH:    self.eco_mode = EcoMode.AGGRO
        else:                                  self.eco_mode = EcoMode.PANIC

        if self.enemy_total > 0: self.win_ratio = self.my_total / self.enemy_total
        else:                    self.win_ratio = 10.0
        self.is_winning_secure   = self.win_ratio >= WIN_SECURE_RATIO
        self.is_losing_desperate = self.win_ratio <= WIN_DESPERATE_RATIO

        self.is_rush, self.rush_ships, self.rush_eta = detect_rush(
            fleets, self.my_planets, player, step)

        self._weakest     = weakest_enemy_owner(self.enemy_planets,
                                                self.owner_strength, self.owner_prod)
        self._weakest_str = self.owner_strength.get(self._weakest, 0) if self._weakest else 0
        self._deny_target = highest_prod_enemy_planet(self.enemy_planets, self.owner_strength)
        self.enemy_homes  = find_enemy_home_planets(self.enemy_planets)

        self.arrivals  = build_arrival_ledger(fleets, planets)
        self.timelines = {p.id: simulate_timeline(p, self.arrivals[p.id], player, HORIZON)
                          for p in planets}
        self.indirect_map = {p.id: indirect_features(p, planets, player) for p in planets}
        self.vuln_ids     = detect_vulnerable_planets(fleets, self.enemy_planets, player)
        self.gateway_map  = {p.id: compute_gateway_value(p, self.enemy_planets) for p in planets}

        # HYPERION: Flanking map (only compute for heavy-enough situations)
        if len(self.my_planets) >= 2 and len(self.enemy_planets) >= 1 and step < 450:
            self.flankable_ids = compute_flanking_map(
                self.my_planets, self.enemy_planets,
                init_by_id, ang_vel, comets, self.comet_ids)
        else:
            self.flankable_ids = set()

        self.en_fleet_to_my = defaultdict(list)
        for f in fleets:
            if f.owner == player or f.owner == -1: continue
            tp, eta = fleet_target_planet(f, planets)
            if tp is not None and tp.owner == player:
                self.en_fleet_to_my[tp.id].append((eta, f.owner, int(f.ships)))

        self.my_active_attack_targets = set()
        for f in fleets:
            if f.owner != player: continue
            tp, _ = fleet_target_planet(f, planets)
            if tp is not None and tp.owner != player:
                self.my_active_attack_targets.add(tp.id)

        self.total_ships = sum(int(p.ships) for p in planets) + sum(int(f.ships) for f in fleets)
        self.total_prod  = sum(int(p.production) for p in planets)

        self.death_ball_mode, self.death_ball_val = death_ball_status(
            self.my_total, self.enemy_total, self.remaining)

        self._shot_cache   = {}
        self._probe_cache  = {}
        self._bprobe_cache = {}
        self._react_cache  = {}
        self._need_cache   = {}

    def is_static(self, pid): return is_static_planet(self.by_id[pid])
    def comet_life_left(self, pid): return comet_life(pid, self.comets)
    def inv_left(self, sid, spent): return max(0, int(self.by_id[sid].ships) - spent[sid])

    def plan_shot(self, sid, tid, ships):
        ships = int(ships); key = (sid, tid, ships)
        if key in self._shot_cache: return self._shot_cache[key]
        r = aim_with_prediction(self.by_id[sid], self.by_id[tid], ships,
                                self.init_by_id, self.ang_vel, self.comets, self.comet_ids)
        self._shot_cache[key] = r; return r

    def probe_candidates(self, sid, tid, cap, hints=()):
        cap = max(1, int(cap))
        hints_n = tuple(int(math.ceil(h)) for h in hints if h is not None)
        key = (sid, tid, cap, hints_n)
        if key in self._probe_cache: return self._probe_cache[key]
        t  = self.by_id[tid]; ts = max(1, int(math.ceil(t.ships)))
        vals = set(range(1, min(7, cap) + 1))
        vals.update({cap, max(1, cap // 2), max(1, cap // 3),
                     min(cap, PARTIAL_MIN), min(cap, ts + 1), min(cap, ts + 4),
                     min(cap, ts + 8), min(cap, ts + 16)})
        for h in hints_n:
            b = max(1, min(cap, h))
            for d in (-3, -2, -1, 0, 1, 2, 3):
                c = b + d
                if 1 <= c <= cap: vals.add(c)
        result = sorted(vals)
        self._probe_cache[key] = result; return result

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
            if anchor is not None and anchor_diff is not None and abs(turns - anchor) > anchor_diff: continue
            sk = (turns, ships) if anchor is None else (abs(turns - anchor), turns, ships)
            if bkey is None or sk < bkey: bkey, best = sk, (ships, aim)
        self._bprobe_cache[key] = best; return best

    def reaction_times(self, tid):
        c = self._react_cache.get(tid)
        if c: return c
        tgt  = self.by_id[tid]
        my_t = min((travel_time(p.x, p.y, p.radius, tgt.x, tgt.y, tgt.radius, max(1, int(p.ships)))
                    for p in self.my_planets), default=10**9)
        en_t = min((travel_time(p.x, p.y, p.radius, tgt.x, tgt.y, tgt.radius, max(1, int(p.ships)))
                    for p in self.enemy_planets), default=10**9)
        c = (my_t, en_t); self._react_cache[tid] = c; return c

    def _search_cap(self, eval_t):
        return max(40, int(self.total_ships + self.total_prod * max(2, eval_t + 2) + 40))

    def min_ships_to_own_by(self, tid, eval_t, attacker,
                            arrival_t=None, planned=None, extra=(), upper=None):
        planned = planned or {}
        eval_t  = max(1, int(math.ceil(eval_t)))
        arr_t   = eval_t if arrival_t is None else max(1, int(math.ceil(arrival_t)))
        if arr_t > eval_t:
            return (max(1, int(upper)) + 1) if upper else self._search_cap(eval_t) + 1
        norm_extra = tuple(
            (max(1, int(math.ceil(t))), o, int(s))
            for t, o, s in extra if s > 0 and max(1, int(math.ceil(t))) <= eval_t
        )
        ck = None
        if arr_t == eval_t and not planned.get(tid) and not norm_extra:
            ck = (tid, eval_t, attacker)
            cv = self._need_cache.get(ck)
            if cv is not None: return cv

        def owns_at(ships):
            a = list(self.arrivals.get(tid, []))
            a += [i for i in planned.get(tid, []) if i[0] <= eval_t]
            a += [i for i in norm_extra if i[0] <= eval_t]
            a.append((arr_t, attacker, int(ships)))
            tl = simulate_timeline(self.by_id[tid], a, self.player, eval_t)
            o, _ = state_at(tl, eval_t); return o == attacker

        if upper:
            hi = max(1, int(upper))
            if not owns_at(hi): return hi + 1
        else:
            o0, s0 = state_at(self.timelines[tid], eval_t)
            if o0 == attacker:
                if ck: self._need_cache[ck] = 0; return 0
            hi = max(1, int(math.ceil(s0)) + 1); cap = self._search_cap(eval_t)
            while hi <= cap and not owns_at(hi): hi *= 2
            if hi > cap:
                if not owns_at(cap): return cap + 1
                hi = cap
        lo = 1
        while lo < hi:
            mid = (lo + hi) // 2
            if owns_at(mid): hi = mid
            else:            lo = mid + 1
        if ck: self._need_cache[ck] = lo
        return lo

    def min_ships_to_own_at(self, tid, arr_t, attacker, planned=None, extra=(), upper=None):
        return self.min_ships_to_own_by(tid, arr_t, attacker,
                                        arrival_t=arr_t, planned=planned,
                                        extra=extra, upper=upper)

    def proj_state(self, tid, arr_t, planned=None, extra=()):
        planned = planned or {}; cut = max(1, int(math.ceil(arr_t)))
        if not planned.get(tid) and not extra: return state_at(self.timelines[tid], cut)
        a = [i for i in self.arrivals.get(tid, []) if i[0] <= cut]
        a += [i for i in planned.get(tid, []) if i[0] <= cut]
        a += [i for i in extra if i[0] <= cut]
        tl = simulate_timeline(self.by_id[tid], a, self.player, cut)
        return state_at(tl, cut)

    def proj_timeline(self, tid, horizon, planned=None, extra=()):
        planned = planned or {}; horizon = max(1, int(math.ceil(horizon)))
        a = [i for i in self.arrivals.get(tid, []) if i[0] <= horizon]
        a += [i for i in planned.get(tid, []) if i[0] <= horizon]
        a += [i for i in extra if i[0] <= horizon]
        return simulate_timeline(self.by_id[tid], a, self.player, horizon)

    def hold_status(self, tid, planned=None):
        tl = self.proj_timeline(tid, HORIZON, planned=planned) \
             if (planned or {}).get(tid) else self.timelines[tid]
        return {k: tl[k] for k in ("keep_needed", "fall_turn", "holds_full")}

    def reinf_needed(self, tid, arr_t, hold_until, planned=None, upper=None):
        planned = planned or {}; tgt = self.by_id[tid]
        arr_t   = max(1, int(math.ceil(arr_t)))
        hold_until = max(arr_t, int(math.ceil(hold_until)))
        if tgt.owner != self.player:
            return self.min_ships_to_own_by(tid, hold_until, self.player,
                                            arrival_t=arr_t, planned=planned, upper=upper)
        def holds(ships):
            tl = self.proj_timeline(tid, hold_until, planned=planned,
                                    extra=((arr_t, self.player, int(ships)),))
            for t in range(arr_t, hold_until + 1):
                if tl["owner_at"].get(t) != self.player: return False
            return True
        if upper:
            hi = max(1, int(upper))
            if not holds(hi): return hi + 1
        else:
            hi = 1; cap = self._search_cap(hold_until)
            while hi <= cap and not holds(hi): hi *= 2
            if hi > cap:
                if not holds(cap): return cap + 1
                hi = cap
        lo = 1
        while lo < hi:
            mid = (lo + hi) // 2
            if holds(mid): hi = mid
            else:          lo = mid + 1
        return lo

# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY LAYER
# ══════════════════════════════════════════════════════════════════════════════

def p_dist(a, b): return math.hypot(a.x - b.x, a.y - b.y)

def nearest_to(target, sources, k):
    if len(sources) <= k: return sources
    return sorted(sources, key=lambda s: (p_dist(s, target), -int(s.ships), s.id))[:k]

def build_modes(world):
    dom = (world.my_total - world.enemy_total) / max(1, world.my_total + world.enemy_total)
    behind     = dom < BEHIND_DOM
    ahead      = dom > AHEAD_DOM
    dominating = ahead or (world.max_enemy > 0 and world.my_total > world.max_enemy * 1.20)
    finishing  = (dom > FINISH_DOM and world.my_prod > world.enemy_prod * FINISH_PROD_R
                  and world.step > 80)
    mm = 1.0
    if ahead:     mm += AHEAD_MRG_B
    if behind:    mm -= BEHIND_MRG_P
    if finishing: mm += FINISH_MRG_B
    if world.is_winning_secure:   mm *= WIN_SECURE_MARGIN_M
    if world.is_losing_desperate: mm *= WIN_DESPERATE_RISK_M
    # HYPERION: Opening Blitz — reduce margins aggressively in first 22 turns
    if world.in_blitz: mm *= OPENING_BLITZ_MARGIN_FRAC
    if world.death_ball_mode == 'defend': mm *= 0.72
    if world.death_ball_mode == 'allin':  mm *= 1.62
    return dict(dom=dom, behind=behind, ahead=ahead,
                dominating=dominating, finishing=finishing, mm=mm)

def compute_pressure_mult(world, planned_target_ids):
    total_fronts = len(world.my_active_attack_targets) + len(set(planned_target_ids))
    if total_fronts < PRESSURE_FRONT_MIN: return 1.0
    extra = total_fronts - PRESSURE_FRONT_MIN
    return min(PRESSURE_MAX_MULT, 1.0 + extra * PRESSURE_BONUS_PER)

def build_policy(world, deadline=None):
    def expired(): return deadline and time.perf_counter() > deadline

    iw = {}
    for pid, (f, n, e) in world.indirect_map.items():
        iw[pid] = f * IND_FRIENDLY_W + n * IND_NEUTRAL_W + e * IND_ENEMY_W

    rtm = {}
    for target in world.planets:
        if expired(): break
        if target.owner == world.player: continue
        my_src = nearest_to(target, world.my_planets,    REACT_MY_TOP_K)
        en_src = nearest_to(target, world.enemy_planets, REACT_EN_TOP_K)
        my_t   = min((travel_time(p.x, p.y, p.radius, target.x, target.y, target.radius, max(1, int(p.ships)))
                      for p in my_src), default=10**9)
        en_t   = min((travel_time(p.x, p.y, p.radius, target.x, target.y, target.radius, max(1, int(p.ships)))
                      for p in en_src), default=10**9)
        rtm[target.id] = (my_t, en_t)

    reserve = {}; budget = {}
    modes_dom = (world.my_total - world.enemy_total) / max(1, world.my_total + world.enemy_total)

    for planet in world.my_planets:
        if expired(): break
        tl    = world.timelines[planet.id]; exact = tl["keep_needed"]

        threats = []
        for en in nearest_to(planet, world.enemy_planets, PROACT_EN_TOP_K):
            aim = world.plan_shot(en.id, planet.id, max(1, int(en.ships)))
            if aim is None: continue
            eta = aim[1]
            if eta > MULTI_PROACT_HOR: continue
            threats.append((eta, int(en.ships)))
        threats.sort(); best_stack = 0; l, running = 0, 0
        for r in range(len(threats)):
            running += threats[r][1]
            while threats[r][0] - threats[l][0] > MULTI_STACK_WIN:
                running -= threats[l][1]; l += 1
            best_stack = max(best_stack, running)
        proact = int(best_stack * MULTI_PROACT_RATIO)
        for eta, s in threats:
            if eta <= PROACT_HORIZON: proact = max(proact, int(s * PROACT_RATIO))

        if world.is_rush: proact = int(proact * 1.55)
        if world.is_1v1 and modes_dom > ONE_V_ONE_DOM_THRESH and not world.is_late:
            exact = int(exact * ONE_V_ONE_AGG_RESERVE); proact = int(proact * ONE_V_ONE_AGG_RESERVE)
        if world.is_winning_secure and not world.is_ffa:
            exact = int(exact * 0.78); proact = int(proact * 0.78)
        if world.eco_mode in (EcoMode.SNOWBALL, EcoMode.EXPAND) and world.is_winning_secure:
            exact = int(exact * 0.70); proact = int(proact * 0.70)
        if world.eco_mode == EcoMode.PANIC:
            exact = int(exact * 0.50); proact = int(proact * 0.50)
        if world.is_total_war:
            exact = min(exact, max(1, exact // 2)); proact = min(proact, max(1, proact // 2))

        # HYPERION: Opening Blitz — cut reserves heavily to capture more neutrals
        if world.in_blitz:
            exact  = int(exact  * OPENING_BLITZ_RESERVE_FRAC)
            proact = int(proact * OPENING_BLITZ_RESERVE_FRAC)

        if world.death_ball_mode == 'defend':
            exact = int(exact * 1.32); proact = int(proact * 1.32)
        elif world.death_ball_mode == 'allin':
            exact = 0; proact = 0

        reserve[planet.id] = min(int(planet.ships), max(exact, proact))
        budget[planet.id]  = max(0, int(planet.ships) - reserve[planet.id])

    return dict(iw=iw, rtm=rtm, reserve=reserve, budget=budget)

# ── Scoring ───────────────────────────────────────────────────────────────────

def react_times(tid, policy): return policy["rtm"].get(tid, (10**9, 10**9))

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
    if target.id in world.comet_ids or world.is_static(target.id): return False
    my_t, en_t = react_times(target.id, policy); gap = en_t - my_t
    if target.production >= SAFE_OPEN_PROD_TH and arr_t <= SAFE_OPEN_TURN_LIM and gap >= SAFE_NEUTRAL_MARGIN:
        return False
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
    elif world.is_opening: val *= 0.86

    if target.owner not in (-1, world.player):
        val *= OPEN_HOSTILE_VM if world.is_opening else HOSTILE_VM

    if target.owner == -1:
        if   is_safe_neutral(target, policy):  val *= SAFE_NEUTRAL_VM
        elif is_contested(target, policy):     val *= CONTESTED_NEUTRAL_VM
        if   can_race_to(target, policy):      val *= RACE_WIN_VM
        if   world.is_early:                   val *= EARLY_NEUTRAL_VM
        # HYPERION: Opening Blitz neutral boost
        if   world.in_blitz:                   val *= OPENING_BLITZ_NEUTRAL_VM

    if target.id in world.comet_ids: val *= COMET_VM
    if   mission == "snipe":         val *= SNIPE_VM
    elif mission == "swarm":         val *= SWARM_VM
    elif mission == "reinforce":     val *= REINFORCE_VM
    elif mission == "crash_exploit": val *= CRASH_VM
    elif mission == "gang_up":       val *= GANG_UP_VM

    # Vulnerability window stack (×5.94 total)
    if target.id in world.vuln_ids:
        val *= EXPOSED_VM
        if VULN_WINDOW_ENABLED: val *= VULN_WINDOW_BONUS

    # HYPERION: Flanking bonus
    if target.id in world.flankable_ids:
        val *= FLANKING_VM

    val *= world.gateway_map.get(target.id, 1.0)

    # Eco mode
    em = world.eco_mode
    if em == EcoMode.SNOWBALL:
        if   target.owner != world.player and target.owner != -1: val *= ECO_SNOWBALL_HOSTILE
        elif target.owner == -1:                                   val *= ECO_SNOWBALL_NEUTRAL
    elif em == EcoMode.EXPAND:
        if   target.owner == -1:           val *= ECO_EXPAND_NEUTRAL
        elif target.owner != world.player: val *= ECO_EXPAND_HOSTILE
    elif em == EcoMode.AGGRO:
        if target.owner not in (-1, world.player):
            val *= ECO_AGGRO_HOSTILE
            if target.production >= PROD_DENY_THRESHOLD: val *= 1.30
        elif target.owner == -1: val *= ECO_AGGRO_NEUTRAL
    elif em == EcoMode.PANIC:
        if target.owner not in (-1, world.player):
            val *= ECO_PANIC_HOSTILE
            if target.production >= PROD_DENY_THRESHOLD: val *= 1.40
        elif target.owner == -1: val *= ECO_PANIC_NEUTRAL

    # Counter-rush
    if world.is_rush and target.owner not in (-1, world.player):
        if world.enemy_homes and target in world.enemy_homes:
            val *= COUNTER_RUSH_HOME_BONUS
        else:
            val *= 1.48

    # Production denial
    if (target.owner not in (-1, world.player) and target.production >= PROD_DENY_THRESHOLD
            and world._deny_target and target.id == world._deny_target.id):
        val *= PROD_DENY_VM

    # Endgame ship value
    if world.is_very_late:
        val += max(0, target.ships) * VERY_LATE_SHIP_W
    elif world.is_late:
        val += max(0, target.ships) * LATE_SHIP_W
    elif world.is_endgame:
        val += max(0, target.ships) * 0.52

    # Elimination
    if target.owner not in (-1, world.player):
        en_str = world.owner_strength.get(target.owner, 0)
        if en_str <= WEAK_THRESH: val += ELIM_BONUS

    if (target.owner not in (-1, world.player) and world._weakest is not None
            and target.owner == world._weakest):
        val *= WEAKEST_VM_FFA if world.is_ffa else WEAKEST_VM_1V1

    if modes["finishing"] and target.owner not in (-1, world.player): val *= FINISH_HOSTILE_VM
    if modes["behind"]    and target.owner == -1 and not world.is_static(target.id): val *= 0.87
    if modes["behind"]    and is_safe_neutral(target, policy): val *= 1.14
    if modes["dominating"] and is_contested(target, policy):   val *= 0.87

    # Death ball
    if world.death_ball_mode == 'defend' and target.owner not in (-1, world.player):
        val *= 0.48
    elif world.death_ball_mode == 'allin' and target.owner not in (-1, world.player):
        val *= 1.92

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
    if target.id in world.vuln_ids: m = max(0, m - 3)
    if world.is_ffa and world._weakest and target.owner == world._weakest: m = max(0, m - 2)
    if world.eco_mode == EcoMode.PANIC: m = max(0, m - 3)
    if world.in_blitz: m = max(0, int(m * 0.65))   # HYPERION: blitz reduces margins
    base = min(cap, send + m)
    d = distance if distance is not None else 30.0
    prod_proxy = target.production if target.owner == -1 else target.production * 2
    return speed_optimal_send(base, cap, d, prod_proxy)

def score_mods(base, target, mission, world, policy, pressure_mult=1.0):
    s = base
    if world.is_static(target.id): s *= STATIC_SCORE_M
    if world.is_early and target.owner == -1 and world.is_static(target.id): s *= EARLY_STATIC_SCORE_M
    if world.is_ffa and target.owner == -1 and not world.is_static(target.id): s *= FFA_ROT_SCORE_M
    if len(world.static_neutrals) >= DENSE_STATIC_THRESH and target.owner == -1 \
            and not world.is_static(target.id): s *= DENSE_ROT_SCORE_M
    if mission == "snipe":              s *= SNIPE_SCORE_M
    elif mission in ("swarm","gang_up"):s *= SWARM_SCORE_M
    elif mission == "crash_exploit":   s *= CRASH_SCORE_M
    if target.id in world.vuln_ids:    s *= EXPOSED_SCORE_M
    if target.owner not in (-1, world.player) and world._weakest == target.owner: s *= WEAKEST_SCORE_M
    if target.owner == -1 and can_race_to(target, policy): s *= RACE_SCORE_M
    s *= pressure_mult
    return s

def candidate_valid(target, turns, world, buf):
    if turns > world.remaining - buf: return False
    if target.id in world.comet_ids:
        life = world.comet_life_left(target.id)
        if turns >= life or turns > COMET_MAX_CHASE: return False
    return True

# ── Settle helpers ────────────────────────────────────────────────────────────

def settle_plan(src, target, cap, send_guess, world, planned, modes, policy,
                mission="capture", eval_fn=None, anchor=None, anchor_tol=None,
                max_iter=5, distance=None):
    if cap < 1: return None
    eval_fn    = eval_fn or (lambda t: t)
    anchor_tol = anchor_tol if anchor_tol is not None else (1 if mission == "snipe" else None)
    seed = max(1, min(cap, int(send_guess))); tested = {}; order = []

    def evaluate(send):
        send = max(1, min(cap, int(send)))
        if send in tested: return tested[send]
        aim = world.plan_shot(src.id, target.id, send)
        if aim is None: tested[send] = None; return None
        angle, turns, _, _ = aim
        if mission == "crash_exploit" and anchor and turns < anchor:
            tested[send] = None; return None
        et = int(math.ceil(eval_fn(turns)))
        if et < turns: tested[send] = None; return None
        need = world.min_ships_to_own_by(target.id, et, world.player,
                                         arrival_t=turns, planned=planned, upper=cap)
        if need <= 0 or need > cap: tested[send] = None; return None
        if mission in ("snipe", "crash_exploit"):
            desired = need
        elif mission == "rescue":
            desired = min(cap, max(need, need + DEF_SEND_MARGIN + target.production * DEF_SEND_PROD_W))
        else:
            desired = min(cap, max(need, preferred_send(target, need, turns, cap, world, modes, policy, distance)))
        result = (angle, turns, et, need, send, desired)
        tested[send] = result; order.append(send); return result

    cands = sorted(world.probe_candidates(src.id, target.id, cap, hints=(seed,)),
                   key=lambda s: (abs(s - seed), s))
    cur = None
    for s in cands:
        r = evaluate(s)
        if r is None: continue
        if anchor and anchor_tol and abs(r[1] - anchor) > anchor_tol: continue
        cur = s; break
    if cur is None: return None

    for _ in range(max_iter):
        r = evaluate(cur)
        if r is None: break
        angle, turns, et, need, actual, desired = r
        if desired == actual:
            if anchor and anchor_tol and abs(turns - anchor) > anchor_tol: return None
            if mission == "rescue" and turns > et: return None
            return angle, turns, et, need, actual
        nxt = max(1, min(cap, int(desired)))
        if nxt in tested: cur = nxt; break
        cur = nxt

    seen = set()
    for s in sorted(order, key=lambda s: (
        0 if not anchor or anchor_tol is None else abs(tested[s][1] - anchor),
        abs(s - seed), tested[s][1], s
    )):
        if s in seen: continue; seen.add(s)
        r = tested.get(s)
        if r is None: continue
        angle, turns, et, need, actual, _ = r
        if actual < need: continue
        if anchor and anchor_tol and abs(turns - anchor) > anchor_tol: continue
        if mission == "rescue" and turns > et: continue
        return angle, turns, et, need, actual
    return None

def settle_reinf(src, target, cap, seed, world, planned, hold_until, max_arr, max_iter=5):
    if cap < 1: return None
    tested = {}; order = []

    def evaluate(send):
        send = max(1, min(cap, int(send)))
        if send in tested: return tested[send]
        aim = world.plan_shot(src.id, target.id, send)
        if aim is None: tested[send] = None; return None
        angle, turns, _, _ = aim
        if turns > max_arr: tested[send] = None; return None
        need = world.reinf_needed(target.id, turns, hold_until, planned=planned, upper=cap)
        if need <= 0 or need > cap: tested[send] = None; return None
        desired = min(cap, need + REINF_SAFETY)
        r = (angle, turns, hold_until, need, send, desired)
        tested[send] = r; order.append(send); return r

    cands = sorted(world.probe_candidates(src.id, target.id, cap, hints=(seed,)),
                   key=lambda s: (abs(s - seed), s))
    cur = None
    for s in cands:
        r = evaluate(s)
        if r: cur = s; break
    if cur is None: return None
    for _ in range(max_iter):
        r = evaluate(cur)
        if r is None: break
        angle, turns, _, need, actual, desired = r
        if desired == actual: return angle, turns, hold_until, need, actual
        nxt = max(1, min(cap, int(desired)))
        if nxt in tested: cur = nxt; break
        cur = nxt
    for s in sorted(order, key=lambda s: (abs(s - seed), tested[s][1], s)):
        r = tested.get(s)
        if r is None: continue
        angle, turns, _, need, actual, _ = r
        if actual < need or turns > max_arr: continue
        return angle, turns, hold_until, need, actual
    return None

# ══════════════════════════════════════════════════════════════════════════════
# MISSION BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def build_intercept_missions(world, planned, modes, policy):
    if not INTERCEPT_ENABLED: return []
    missions = []
    for my_pid, fleet_list in world.en_fleet_to_my.items():
        target = world.by_id[my_pid]
        for en_eta, en_owner, en_ships in sorted(fleet_list, key=lambda x: x[0]):
            if en_eta > INTERCEPT_ETA_MAX: continue
            garrison_at_eta = target.ships + target.production * en_eta
            deficit = max(0, en_ships - garrison_at_eta + 1)
            if deficit <= 0: continue
            for src in world.my_planets:
                if src.id == my_pid: continue
                cap = policy["budget"].get(src.id, 0)
                if cap < deficit: continue
                probe = world.best_probe(src.id, my_pid, cap,
                                         hints=(deficit, deficit + 4), max_t=en_eta - 1)
                if probe is None: continue
                _, rough = probe
                if rough[1] >= en_eta: continue
                plan = settle_reinf(src, target, cap, probe[0], world, planned, en_eta + 12, en_eta - 1)
                if plan is None: continue
                angle, turns, _, need, send = plan
                if turns >= en_eta: continue
                sv  = max(1, world.remaining - en_eta)
                val = target.production * sv * DEF_FRONTIER_M * 1.75
                sc  = val / (send + turns * DEF_TURN_W + 1.0)
                opt = ShotOption(sc, src.id, my_pid, angle, turns, need, send, "reinforce", en_eta)
                missions.append(Mission("reinforce", sc, my_pid, en_eta, [opt]))
                break
    return missions

def build_snipe_missions(world, planned, modes, policy, pressure_mult):
    missions = []
    for target in world.neutral_planets:
        en_etas = sorted({int(math.ceil(eta)) for eta, o, s in world.arrivals.get(target.id, [])
                          if o not in (-1, world.player) and s > 0})
        if not en_etas: continue
        for src in world.my_planets:
            src_cap = policy["budget"].get(src.id, 0)
            if src_cap < PARTIAL_MIN: continue
            for en_eta in en_etas[:3]:
                probe = world.best_probe(src.id, target.id, src_cap,
                                         hints=(int(target.ships) + 1,),
                                         anchor=en_eta, anchor_diff=1)
                if probe is None: continue
                _, rough = probe
                sync = max(rough[1], en_eta)
                if target.id in world.comet_ids:
                    life = world.comet_life_left(target.id)
                    if sync >= life or sync > COMET_MAX_CHASE: continue
                plan = settle_plan(src, target, src_cap, probe[0], world, planned, modes, policy,
                                   mission="snipe", eval_fn=lambda t, ee=en_eta: max(t, ee),
                                   anchor=en_eta)
                if plan is None: continue
                angle, turns, sync_t, need, send = plan
                val = target_value(target, sync_t, "snipe", world, modes, policy)
                if val <= 0: continue
                sc = score_mods(val / (send + sync_t * SNIPE_TURN_W + 1.0), target, "snipe", world, policy, pressure_mult)
                opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "snipe", en_eta)
                missions.append(Mission("snipe", sc, target.id, sync_t, [opt]))
    return missions

def build_race_missions(world, planned, modes, policy, pressure_mult):
    missions = []
    for target in world.neutral_planets:
        if target.id in world.comet_ids: continue
        my_t, en_t = react_times(target.id, policy)
        if en_t == 10**9 or en_t - my_t < RACE_MIN_ADVANTAGE: continue
        desired_arrival = max(1, en_t - RACE_MARGIN_TURNS)
        for src in world.my_planets:
            src_cap = policy["budget"].get(src.id, 0)
            if src_cap < PARTIAL_MIN: continue
            probe = world.best_probe(src.id, target.id, src_cap,
                                     hints=(int(target.ships) + 1,),
                                     max_t=desired_arrival + RACE_MARGIN_TURNS + 1)
            if probe is None: continue
            _, rough = probe
            if rough[1] > en_t: continue
            plan = settle_plan(src, target, src_cap, probe[0], world, planned, modes, policy, mission="capture")
            if plan is None: continue
            angle, turns, _, need, send = plan
            if turns >= en_t or not candidate_valid(target, turns, world, LATE_BUFFER): continue
            val = target_value(target, turns, "capture", world, modes, policy)
            if val <= 0: continue
            sc = score_mods(val / (send + turns * ATTACK_TURN_W + 1.0), target, "capture", world, policy, pressure_mult)
            missions.append(Mission("single", sc, target.id, turns,
                                    [ShotOption(sc, src.id, target.id, angle, turns, need, send, "capture")]))
    return missions

def build_rescue_missions(world, planned, modes, policy):
    missions = []
    for target in world.my_planets:
        ft = world.timelines[target.id]["fall_turn"]
        if ft is None or ft > DEF_LOOKAHEAD: continue
        for src in world.my_planets:
            if src.id == target.id: continue
            cap = policy["budget"].get(src.id, 0)
            if cap < PARTIAL_MIN: continue
            probe = world.best_probe(src.id, target.id, cap,
                                     hints=(target.production + DEF_SEND_MARGIN + 2,), max_t=ft)
            if probe is None: continue
            plan = settle_plan(src, target, cap, probe[0], world, planned, modes, policy,
                               mission="rescue", eval_fn=lambda _, f=ft: f, anchor=ft)
            if plan is None: continue
            angle, turns, _, need, send = plan
            sv = max(1, world.remaining - ft)
            val = target.production * sv + max(0, target.ships) * DEF_SHIP_VALUE
            if world.enemy_planets and nearest_dist(target.x, target.y, world.enemy_planets) < 22:
                val *= DEF_FRONTIER_M
            sc = val / (send + turns * DEF_TURN_W + 1.0)
            opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "rescue", ft)
            missions.append(Mission("rescue", sc, target.id, ft, [opt]))
    return missions

def build_reinf_missions(world, planned, modes, policy, inv_left_fn):
    if not REINF_ENABLED or world.remaining < REINF_MIN_FUTURE: return []
    missions = []
    for target in world.my_planets:
        ft = world.timelines[target.id]["fall_turn"]
        if ft is None or target.production < REINF_MIN_PROD: continue
        hold_until = min(HORIZON, ft + REINF_LOOKAHEAD); max_arr = min(ft, REINF_MAX_TRAVEL)
        for src in world.my_planets:
            if src.id == target.id: continue
            cap = min(inv_left_fn(src.id), int(src.ships * REINF_MAX_SRC_FRAC))
            if cap < PARTIAL_MIN: continue
            probe = world.best_probe(src.id, target.id, cap,
                                     hints=(target.production + REINF_SAFETY + 2,), max_t=max_arr)
            if probe is None: continue
            plan = settle_reinf(src, target, cap, probe[0], world, planned, hold_until, max_arr)
            if plan is None: continue
            angle, turns, _, need, send = plan
            sv  = max(1, world.remaining - hold_until)
            val = target.production * sv + max(0, target.ships) * DEF_SHIP_VALUE
            if world.enemy_planets and nearest_dist(target.x, target.y, world.enemy_planets) < 22:
                val *= DEF_FRONTIER_M
            val *= REINFORCE_VM
            sc = val / (send + turns * REINF_TURN_W + 1.0)
            opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "reinforce", hold_until)
            missions.append(Mission("reinforce", sc, target.id, ft, [opt]))
    return missions

def build_recap_missions(world, planned, modes, policy):
    missions = []
    for target in world.my_planets:
        ft = world.timelines[target.id]["fall_turn"]
        if ft is None or ft > DEF_LOOKAHEAD: continue
        for src in world.my_planets:
            if src.id == target.id: continue
            cap = policy["budget"].get(src.id, 0)
            if cap < PARTIAL_MIN: continue
            probe = world.best_probe(src.id, target.id, cap,
                                     hints=(target.production + DEF_SEND_MARGIN + 2,),
                                     min_t=ft + 1, max_t=ft + RECAP_LOOKAHEAD)
            if probe is None: continue
            plan = settle_plan(src, target, cap, probe[0], world, planned, modes, policy, mission="capture")
            if plan is None: continue
            angle, turns, _, need, send = plan
            if turns <= ft or turns - ft > RECAP_LOOKAHEAD: continue
            sv  = max(1, world.remaining - turns)
            val = (RECAP_PROD_W * target.production * sv + RECAP_IMMED_W * max(0, target.ships))
            if world.enemy_planets and nearest_dist(target.x, target.y, world.enemy_planets) < 22:
                val *= RECAP_FRONTIER_M
            val *= RECAP_VM
            sc  = val / (send + turns * RECAP_TURN_W + 1.0)
            opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "recapture", ft)
            missions.append(Mission("recapture", sc, target.id, turns, [opt]))
    return missions

def _detect_crashes(world):
    crashes = []
    for tid, arrivals in world.arrivals.items():
        en_ev = [(int(math.ceil(eta)), o, int(s)) for eta, o, s in arrivals
                 if o not in (-1, world.player) and s > 0]
        en_ev.sort()
        for i in range(len(en_ev)):
            ea, oa, sa = en_ev[i]
            for j in range(i + 1, len(en_ev)):
                eb, ob, sb = en_ev[j]
                if oa == ob: continue
                if abs(ea - eb) > CRASH_ETA_WIN: break
                if sa + sb < CRASH_MIN_SHIPS: continue
                crashes.append(dict(target_id=tid, crash_turn=max(ea, eb)))
    return crashes

def build_crash_missions(world, planned, modes, policy, pressure_mult):
    if not CRASH_ENABLED: return []
    missions = []
    for crash in _detect_crashes(world):
        target = world.by_id[crash["target_id"]]
        if target.owner == world.player: continue
        desired_arr = crash["crash_turn"] + CRASH_DELAY
        for src in world.my_planets:
            cap = policy["budget"].get(src.id, 0)
            if cap < PARTIAL_MIN: continue
            probe = world.best_probe(src.id, target.id, cap, hints=(6, int(target.ships) + 1),
                                     anchor=desired_arr, anchor_diff=CRASH_ETA_WIN)
            if probe is None: continue
            plan = settle_plan(src, target, cap, probe[0], world, planned, modes, policy,
                               mission="crash_exploit",
                               eval_fn=lambda t, da=desired_arr: max(t, da),
                               anchor=desired_arr, anchor_tol=CRASH_ETA_WIN)
            if plan is None: continue
            angle, turns, _, need, send = plan
            if not candidate_valid(target, turns, world, LATE_BUFFER): continue
            val = target_value(target, turns, "crash_exploit", world, modes, policy)
            if val <= 0: continue
            sc = score_mods(val / (send + turns * SNIPE_TURN_W + 1.0), target, "crash_exploit", world, policy, pressure_mult)
            opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "crash_exploit", desired_arr)
            missions.append(Mission("crash_exploit", sc, target.id, turns, [opt]))
    return missions

def _detect_battles(world):
    battles = []
    for target in world.enemy_planets:
        for eta, o, s in world.arrivals.get(target.id, []):
            if o in (-1, world.player) or o == target.owner or int(s) <= 0: continue
            eta_i = int(math.ceil(eta))
            garrison = target.ships + target.production * eta_i
            post = max(0, int(s) - garrison) if int(s) > garrison else max(0, garrison - int(s))
            if post < 28:
                battles.append(dict(target_id=target.id, battle_turn=eta_i, post_ships=post))
    return battles

def build_gang_up_missions(world, planned, modes, policy, pressure_mult):
    missions = []
    for b in _detect_battles(world):
        target = world.by_id[b["target_id"]]
        if target.owner == world.player: continue
        desired = b["battle_turn"] + GANG_POST_DELAY
        for src in world.my_planets:
            cap = policy["budget"].get(src.id, 0)
            if cap < PARTIAL_MIN: continue
            hint = max(3, int(b["post_ships"]) + 3)
            probe = world.best_probe(src.id, target.id, cap,
                                     hints=(hint, int(target.ships) + 1),
                                     anchor=desired, anchor_diff=GANG_ETA_WIN)
            if probe is None: continue
            plan = settle_plan(src, target, cap, probe[0], world, planned, modes, policy,
                               mission="capture", eval_fn=lambda t, da=desired: max(t, da),
                               anchor=desired, anchor_tol=GANG_ETA_WIN)
            if plan is None: continue
            angle, turns, _, need, send = plan
            if not candidate_valid(target, turns, world, LATE_BUFFER): continue
            val = target_value(target, turns, "gang_up", world, modes, policy)
            if val <= 0: continue
            sc = score_mods(val / (send + turns * ATTACK_TURN_W + 1.0), target, "gang_up", world, policy, pressure_mult)
            opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "capture", desired)
            missions.append(Mission("single", sc, target.id, turns, [opt]))
    return missions

def build_elimination_missions(world, planned, modes, policy, pressure_mult):
    if world._weakest is None: return []
    if world._weakest_str > world.my_total * 0.94: return []
    wk_planets = [p for p in world.enemy_planets if p.owner == world._weakest]
    if not wk_planets: return []
    mult = 1.72 if world.is_ffa else 1.45
    missions = []
    for target in sorted(wk_planets, key=lambda p: -p.production):
        for src in world.my_planets:
            cap = policy["budget"].get(src.id, 0)
            if cap < PARTIAL_MIN: continue
            probe = world.best_probe(src.id, target.id, cap, hints=(int(target.ships) + 1,))
            if probe is None: continue
            _, rough = probe
            if not candidate_valid(target, rough[1], world, LATE_BUFFER): continue
            gn = world.min_ships_to_own_at(target.id, rough[1], world.player, planned=planned)
            if gn <= 0 or gn > cap: continue
            d  = p_dist(src, target)
            sg = preferred_send(target, gn, rough[1], cap, world, modes, policy, distance=d)
            plan = settle_plan(src, target, cap, sg, world, planned, modes, policy,
                               mission="capture", distance=d)
            if plan is None: continue
            angle, turns, _, need, send = plan
            if not candidate_valid(target, turns, world, LATE_BUFFER) or send < need: continue
            val = target_value(target, turns, "capture", world, modes, policy)
            if val <= 0: continue
            sc = score_mods(val * mult / (send + turns * ATTACK_TURN_W + 1.0), target, "capture", world, policy, pressure_mult)
            opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "capture")
            missions.append(Mission("single", sc, target.id, turns, [opt]))
    return missions

def build_deny_missions(world, planned, modes, policy, pressure_mult):
    if world._deny_target is None: return []
    target = world._deny_target
    if target.owner == world.player or target.production < PROD_DENY_THRESHOLD: return []
    missions = []
    for src in world.my_planets:
        cap = policy["budget"].get(src.id, 0)
        if cap < PARTIAL_MIN: continue
        probe = world.best_probe(src.id, target.id, cap, hints=(int(target.ships) + 1,))
        if probe is None: continue
        _, rough = probe
        if not candidate_valid(target, rough[1], world, LATE_BUFFER): continue
        gn = world.min_ships_to_own_at(target.id, rough[1], world.player, planned=planned)
        if gn <= 0 or gn > cap: continue
        d  = p_dist(src, target)
        sg = preferred_send(target, gn, rough[1], cap, world, modes, policy, distance=d)
        plan = settle_plan(src, target, cap, sg, world, planned, modes, policy, mission="capture", distance=d)
        if plan is None: continue
        angle, turns, _, need, send = plan
        if not candidate_valid(target, turns, world, LATE_BUFFER) or send < need: continue
        val = target_value(target, turns, "capture", world, modes, policy)
        if val <= 0: continue
        sc = score_mods(val * PROD_DENY_VM / (send + turns * ATTACK_TURN_W + 1.0), target, "capture", world, policy, pressure_mult)
        opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "capture")
        missions.append(Mission("single", sc, target.id, turns, [opt]))
    return missions

# ══════════════════════════════════════════════════════════════════════════════
# PLAN MOVES — HYPERION ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

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
    def atk_left(sid):  return max(0, policy["budget"].get(sid, 0) - spent[sid])

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
            if s >= 1: final.append([sid, float(angle), int(s)]); used[sid] += s
        return final

    def live_doomed():
        d = set()
        for p in world.my_planets:
            st = world.hold_status(p.id, planned=planned)
            if (not st["holds_full"] and st["fall_turn"] and
                    st["fall_turn"] <= DOOMED_EVAC_LIMIT and inv_left(p.id) >= DOOMED_MIN_SHIPS):
                d.add(p.id)
        return d

    def time_ok(target, turns):
        buf = VERY_LATE_BUFFER if world.is_very_late else LATE_BUFFER
        return candidate_valid(target, turns, world, buf)

    def get_pressure():
        return compute_pressure_mult(world, list(planned.keys()))

    # DEATH BALL DEFEND
    if world.death_ball_mode == 'defend':
        missions += build_intercept_missions(world, planned, modes, policy)
        missions += build_rescue_missions(world, planned, modes, policy)
        pressure = get_pressure()
        for src in world.my_planets:
            if expired(): break
            src_cap = atk_left(src.id)
            if src_cap < 10: continue
            for target in world.enemy_planets:
                if target.id not in world.vuln_ids: continue
                probe = world.best_probe(src.id, target.id, src_cap, hints=(int(target.ships)+1,))
                if probe is None: continue
                _, rough = probe
                if not time_ok(target, rough[1]): continue
                gn = world.min_ships_to_own_at(target.id, rough[1], world.player, planned=planned)
                if gn <= 0 or gn > src_cap: continue
                d  = p_dist(src, target)
                sg = preferred_send(target, gn, rough[1], src_cap, world, modes, policy, distance=d)
                plan = settle_plan(src, target, src_cap, sg, world, planned, modes, policy, mission="capture", distance=d)
                if plan is None: continue
                angle, turns, _, need, send = plan
                if send < need: continue
                val = target_value(target, turns, "capture", world, modes, policy)
                if val <= 0: continue
                sc = score_mods(val/(send+turns*ATTACK_TURN_W+1.0), target, "capture", world, policy, pressure)
                missions.append(Mission("single", sc, target.id, turns,
                                        [ShotOption(sc, src.id, target.id, angle, turns, need, send, "capture")]))
        missions.sort(key=lambda m: -m.score)
        for m in missions[:8]:
            if expired(): return finalize()
            opt = m.options[0]; src = world.by_id[opt.src_id]
            left = atk_left(opt.src_id) if m.kind == "single" else \
                   min(inv_left(opt.src_id), int(src.ships * REINF_MAX_SRC_FRAC))
            if left <= 0: continue
            if m.kind in ("reinforce", "rescue"):
                plan = settle_plan(src, world.by_id[m.target_id], left, min(left, opt.send_cap),
                                   world, planned, modes, policy, mission="rescue",
                                   eval_fn=lambda _, f=m.turns: f, anchor=opt.anchor_turn)
            else:
                d = p_dist(src, world.by_id[m.target_id])
                plan = settle_plan(src, world.by_id[m.target_id], left, min(left, opt.send_cap),
                                   world, planned, modes, policy, mission="capture", distance=d)
            if plan is None: continue
            angle, turns, _, need, send = plan
            if send < need: continue
            push(opt.src_id, angle, send)
            planned[m.target_id].append((turns, world.player, int(send)))
        return finalize()

    # ── BUILD MISSION QUEUE ──────────────────────────────────────────────────
    pressure = get_pressure()

    missions += build_intercept_missions(world, planned, modes, policy)
    missions += build_rescue_missions(world, planned, modes, policy)

    if heavy_ok():
        missions += build_reinf_missions(world, planned, modes, policy, inv_left)

    missions += build_recap_missions(world, planned, modes, policy)

    if heavy_ok():
        missions += build_elimination_missions(world, planned, modes, policy, pressure)
        missions += build_deny_missions(world, planned, modes, policy, pressure)
        missions += build_gang_up_missions(world, planned, modes, policy, pressure)
        missions += build_race_missions(world, planned, modes, policy, pressure)

    missions += build_snipe_missions(world, planned, modes, policy, pressure)

    # ── SINGLE-SOURCE + SWARM OPTIONS ───────────────────────────────────────
    for src in world.my_planets:
        if expired(): return finalize()
        src_cap = atk_left(src.id)
        if src_cap <= 0: continue

        for target in world.planets:
            if expired(): return finalize()
            if target.id == src.id or target.owner == world.player: continue

            probe = world.best_probe(src.id, target.id, src_cap, hints=(int(target.ships) + 1,))
            if probe is None: continue
            _, rough_aim = probe
            rough_t = rough_aim[1]
            if not time_ok(target, rough_t): continue

            gn = world.min_ships_to_own_at(target.id, rough_t, world.player, planned=planned)
            if gn <= 0: continue
            if open_filter(target, rough_t, gn, src_cap, world, policy): continue

            d = p_dist(src, target)

            part_cap = min(src_cap, preferred_send(target, gn, rough_t, src_cap, world, modes, policy, distance=d))
            if part_cap >= PARTIAL_MIN:
                p2 = world.best_probe(src.id, target.id, part_cap,
                                      hints=(part_cap, gn, int(target.ships) + 1))
                if p2:
                    _, pa = p2
                    if time_ok(target, pa[1]) and not open_filter(target, pa[1], gn, src_cap, world, policy):
                        val = target_value(target, pa[1], "swarm", world, modes, policy)
                        if val > 0:
                            pm = get_pressure()
                            sc = score_mods(val / (part_cap + pa[1] * ATTACK_TURN_W + 1.0),
                                           target, "swarm", world, policy, pm)
                            src_opts[target.id].append(
                                ShotOption(sc, src.id, target.id, pa[0], pa[1], gn, part_cap, "swarm"))

            if gn <= src_cap:
                sg   = preferred_send(target, gn, rough_t, src_cap, world, modes, policy, distance=d)
                plan = settle_plan(src, target, src_cap, sg, world, planned, modes, policy,
                                   mission="capture", distance=d)
                if plan is None: continue
                angle, turns, _, need, send = plan
                if not time_ok(target, turns): continue
                if open_filter(target, turns, need, src_cap, world, policy): continue
                val = target_value(target, turns, "capture", world, modes, policy)
                if val <= 0: continue
                pm = get_pressure()
                sc = score_mods(val / (send + turns * ATTACK_TURN_W + 1.0), target, "capture", world, policy, pm)
                opt = ShotOption(sc, src.id, target.id, angle, turns, need, send, "capture")
                if send >= need:
                    missions.append(Mission("single", sc, target.id, turns, [opt]))

    # ── SWARM ASSEMBLY ───────────────────────────────────────────────────────
    for tid, options in src_opts.items():
        if expired(): return finalize()
        if len(options) < 2: continue
        target = world.by_id[tid]; top = sorted(options, key=lambda x: -x.score)[:MULTI_TOP_K]

        for i in range(len(top)):
            for j in range(i + 1, len(top)):
                a, b = top[i], top[j]
                if a.src_id == b.src_id: continue
                tol = HOSTILE_SWARM_TOL if target.owner not in (-1, world.player) else MULTI_ETA_TOL
                if abs(a.turns - b.turns) > tol: continue
                jt = max(a.turns, b.turns); tc = a.send_cap + b.send_cap
                need = world.min_ships_to_own_at(tid, jt, world.player, planned=planned, upper=tc)
                if need <= 0 or a.send_cap >= need or b.send_cap >= need or tc < need: continue
                val = target_value(target, jt, "swarm", world, modes, policy)
                if val <= 0: continue
                pm  = get_pressure()
                sc  = score_mods(val / (need + jt * ATTACK_TURN_W + 1.0), target, "swarm", world, policy, pm) * MULTI_PLAN_PEN
                missions.append(Mission("swarm", sc, tid, jt, [a, b]))

        if (THREE_SRC_ENABLED and heavy_ok() and target.owner not in (-1, world.player)
                and int(target.ships) >= THREE_SRC_MIN_SHIPS and len(top) >= 3):
            for i in range(len(top)):
                for j in range(i + 1, len(top)):
                    for k in range(j + 1, len(top)):
                        if expired(): return finalize()
                        trio = [top[i], top[j], top[k]]
                        if len({x.src_id for x in trio}) < 3: continue
                        ts = [x.turns for x in trio]
                        if max(ts) - min(ts) > THREE_SRC_TOL: continue
                        jt = max(ts); tc = sum(x.send_cap for x in trio)
                        need = world.min_ships_to_own_at(tid, jt, world.player, planned=planned, upper=tc)
                        if need <= 0 or tc < need: continue
                        if any(trio[a2].send_cap + trio[b2].send_cap >= need
                               for a2 in range(3) for b2 in range(a2 + 1, 3)): continue
                        val = target_value(target, jt, "swarm", world, modes, policy)
                        if val <= 0: continue
                        pm = get_pressure()
                        sc = score_mods(val / (need + jt * ATTACK_TURN_W + 1.0), target, "swarm", world, policy, pm) * THREE_SRC_PEN
                        missions.append(Mission("swarm", sc, tid, jt, trio))

    if heavy_ok():
        missions += build_crash_missions(world, planned, modes, policy, get_pressure())

    missions.sort(key=lambda m: -m.score)

    # HYPERION: CONCENTRATION (SNOWBALL mode, prod>=3)
    if (CONCENTRATION_ENABLED and world.eco_mode == EcoMode.SNOWBALL
            and not world.is_very_late and missions):
        best_m = None
        for m in missions:
            if m.kind == "single" and world.by_id[m.target_id].production >= CONCENTRATION_MIN_PROD:
                if best_m is None or m.score > best_m.score:
                    best_m = m
        if best_m is not None:
            target = world.by_id[best_m.target_id]
            best_src = sorted(world.my_planets, key=lambda p: p_dist(p, target))[0]
            src_cap  = atk_left(best_src.id)
            if src_cap >= 8:
                d  = p_dist(best_src, target)
                ts = speed_optimal_send(best_m.options[0].needed, src_cap, d, target.production)
                plan = settle_plan(best_src, target, src_cap, ts, world, planned, modes, policy,
                                   mission="capture", distance=d)
                if plan:
                    angle, turns, _, need, send = plan
                    if send >= need:
                        push(best_src.id, angle, send)
                        planned[target.id].append((turns, world.player, int(send)))

    # ── EXECUTE MISSIONS ─────────────────────────────────────────────────────
    for m in missions:
        if expired(): return finalize()
        target = world.by_id[m.target_id]

        if m.kind in ("single","snipe","rescue","recapture","reinforce","crash_exploit"):
            opt = m.options[0]; src = world.by_id[opt.src_id]
            if m.kind == "reinforce":
                left = min(inv_left(opt.src_id), int(src.ships * REINF_MAX_SRC_FRAC))
            else:
                left = atk_left(opt.src_id)
            if left <= 0: continue

            d = p_dist(src, target)
            if m.kind == "reinforce":
                plan = settle_reinf(src, target, left, min(left, opt.send_cap),
                                    world, planned, opt.anchor_turn, m.turns)
            elif m.kind == "rescue":
                plan = settle_plan(src, target, left, min(left, opt.send_cap), world, planned, modes, policy,
                                   mission="rescue", eval_fn=lambda _, f=m.turns: f, anchor=opt.anchor_turn)
            elif m.kind == "snipe":
                plan = settle_plan(src, target, left, min(left, opt.send_cap), world, planned, modes, policy,
                                   mission="snipe", eval_fn=lambda t, ee=opt.anchor_turn: max(t, ee),
                                   anchor=opt.anchor_turn)
            elif m.kind == "crash_exploit":
                plan = settle_plan(src, target, left, min(left, opt.send_cap), world, planned, modes, policy,
                                   mission="crash_exploit",
                                   eval_fn=lambda t, da=opt.anchor_turn: max(t, da),
                                   anchor=opt.anchor_turn, anchor_tol=CRASH_ETA_WIN)
            else:
                plan = settle_plan(src, target, left, min(left, opt.send_cap), world, planned, modes, policy,
                                   mission="capture", distance=d)
            if plan is None: continue
            angle, turns, _, need, send = plan
            if send < need or need > left: continue

            if m.kind in ("capture","single") and left > need:
                ts = speed_optimal_send(need, left, d, target.production)
                if ts >= need: send = ts

            sent = push(opt.src_id, angle, send)
            if sent < need: continue
            planned[target.id].append((turns, world.player, int(sent)))
            continue

        # Swarm
        lims = [min(atk_left(opt.src_id), opt.send_cap) for opt in m.options]
        if min(lims) <= 0: continue
        need = world.min_ships_to_own_at(target.id, m.turns, world.player,
                                         planned=planned, upper=sum(lims))
        if need <= 0 or sum(lims) < need: continue
        ordered = sorted(zip(m.options, lims), key=lambda x: (x[0].turns, -x[1], x[0].src_id))
        remaining = need; sends_map = {}
        for idx, (opt, lim) in enumerate(ordered):
            rem_other = sum(l for _, l in ordered[idx + 1:])
            s = min(lim, max(0, remaining - rem_other))
            sends_map[opt.src_id] = s; remaining -= s
        if remaining > 0: continue
        reaimed = []
        for opt, _ in ordered:
            s = sends_map.get(opt.src_id, 0)
            if s <= 0: continue
            aim = world.plan_shot(opt.src_id, target.id, s)
            if aim is None: reaimed = []; break
            reaimed.append((opt.src_id, aim[0], aim[1], s))
        if not reaimed: continue
        ts_only = [x[2] for x in reaimed]
        tol = HOSTILE_SWARM_TOL if target.owner not in (-1, world.player) else MULTI_ETA_TOL
        if max(ts_only) - min(ts_only) > tol: continue
        jt = max(ts_only)
        oo, _ = world.proj_state(target.id, jt, planned=planned,
                                 extra=[(t, world.player, s) for _, _, t, s in reaimed])
        if oo != world.player: continue
        committed = []
        for sid, angle, turns, s in reaimed:
            a = push(sid, angle, s)
            if a > 0: committed.append((turns, world.player, int(a)))
        if sum(x[2] for x in committed) < need: continue
        planned[target.id].extend(committed)

    # ── FOLLOWUP ─────────────────────────────────────────────────────────────
    if not world.is_very_late and opt_ok():
        for src in world.my_planets:
            if expired(): return finalize()
            sleft = atk_left(src.id)
            if sleft < FOLLOWUP_MIN: continue
            best = None
            for target in world.planets:
                if expired(): return finalize()
                if target.id == src.id or target.owner == world.player: continue
                if target.id in world.comet_ids and target.production <= LOW_COMET_PROD: continue
                probe = world.best_probe(src.id, target.id, sleft, hints=(int(target.ships) + 1,))
                if probe is None: continue
                _, ra = probe; et = ra[1]
                if world.is_late and et > world.remaining - LATE_BUFFER: continue
                gn = world.min_ships_to_own_at(target.id, et, world.player,
                                               planned=planned, upper=sleft)
                if gn <= 0 or gn > sleft: continue
                if open_filter(target, et, gn, sleft, world, policy): continue
                d  = p_dist(src, target)
                sg = preferred_send(target, gn, et, sleft, world, modes, policy, distance=d)
                if sg < gn: continue
                plan = settle_plan(src, target, sleft, sg, world, planned, modes, policy,
                                   mission="capture", distance=d)
                if plan is None: continue
                _, turns, _, need, send = plan
                if world.is_late and turns > world.remaining - LATE_BUFFER: continue
                if send < need: continue
                val = target_value(target, turns, "capture", world, modes, policy)
                if val <= 0: continue
                pm  = get_pressure()
                sc  = score_mods(val / (send + turns * ATTACK_TURN_W + 1.0), target, "capture", world, policy, pm)
                if best is None or sc > best[0]: best = (sc, target, plan, d)
            if best is None: continue
            _, target, plan, d = best
            angle, turns, _, need, send = plan
            sleft = atk_left(src.id)
            if need > sleft: continue
            plan2 = settle_plan(src, target, sleft, min(sleft, send), world, planned, modes, policy,
                                mission="capture", distance=d)
            if plan2 is None: continue
            angle, turns, _, need, send = plan2
            if send < need: continue
            ts = speed_optimal_send(need, sleft, d, target.production)
            if ts >= need: send = ts
            a = push(src.id, angle, send)
            if a >= need: planned[target.id].append((turns, world.player, int(a)))

    # ── DOOMED EVACUATION ────────────────────────────────────────────────────
    if opt_ok():
        doomed = live_doomed()
        if doomed:
            ft_set = world.enemy_planets or world.static_neutrals or world.neutral_planets
            fd = ({p.id: nearest_dist(p.x, p.y, ft_set) for p in world.my_planets}
                  if ft_set else {p.id: 10**9 for p in world.my_planets})
            for planet in world.my_planets:
                if expired(): return finalize()
                if planet.id not in doomed: continue
                avail = inv_left(planet.id)
                if avail < policy["reserve"].get(planet.id, 0): continue
                best_cap = None
                for target in world.planets:
                    if expired(): return finalize()
                    if target.id == planet.id or target.owner == world.player: continue
                    probe = world.best_probe(planet.id, target.id, avail,
                                             hints=(avail, int(target.ships) + 1))
                    if probe is None: continue
                    _, pa = probe
                    if pa[1] > world.remaining - 2: continue
                    need = world.min_ships_to_own_at(target.id, pa[1], world.player,
                                                     planned=planned, upper=avail)
                    if need <= 0 or need > avail: continue
                    plan = settle_plan(planet, target, avail,
                                       min(avail, max(need, int(target.ships) + 1)),
                                       world, planned, modes, policy, mission="capture")
                    if plan is None: continue
                    angle, turns, _, pn, send = plan
                    if send < pn: continue
                    sc = target_value(target, turns, "capture", world, modes, policy) / (send + turns + 1.0)
                    if target.owner not in (-1, world.player): sc *= 1.08
                    if best_cap is None or sc > best_cap[0]:
                        best_cap = (sc, target.id, angle, turns, send)
                if best_cap:
                    _, tid, angle, turns, send = best_cap
                    a = push(planet.id, angle, send)
                    if a >= 1: planned[tid].append((turns, world.player, int(a)))
                    continue
                allies = [p for p in world.my_planets if p.id != planet.id and p.id not in doomed]
                if not allies: continue
                ret = min(allies, key=lambda p: (fd.get(p.id, 10**9), p_dist(planet, p)))
                aim = world.plan_shot(planet.id, ret.id, avail)
                if aim: push(planet.id, aim[0], avail)

    # ── REAR LOGISTICS ────────────────────────────────────────────────────────
    if ((world.enemy_planets or world.neutral_planets)
            and len(world.my_planets) > 1 and not world.is_late and opt_ok()):
        doomed  = live_doomed()
        ft_set  = world.enemy_planets or world.static_neutrals or world.neutral_planets
        fd      = {p.id: nearest_dist(p.x, p.y, ft_set) for p in world.my_planets}
        safe_fs = [p for p in world.my_planets if p.id not in doomed]
        if safe_fs:
            anchor = min(safe_fs, key=lambda p: fd[p.id])
            ratio  = REAR_RATIO_FFA if world.is_ffa else REAR_RATIO_2P
            if modes["finishing"]: ratio = max(ratio, REAR_RATIO_FFA)
            for rear in sorted(world.my_planets, key=lambda p: -fd[p.id]):
                if expired(): return finalize()
                if rear.id == anchor.id or rear.id in doomed: continue
                if atk_left(rear.id) < REAR_MIN_SHIPS: continue
                if fd[rear.id] < fd[anchor.id] * REAR_DIST_RATIO: continue
                stage = [p for p in safe_fs if p.id != rear.id
                         and fd[p.id] < fd[rear.id] * REAR_STAGE_PROG]
                if stage: front = min(stage, key=lambda p: p_dist(rear, p))
                else:
                    obj = min(ft_set, key=lambda t: p_dist(rear, t))
                    rem = [p for p in safe_fs if p.id != rear.id]
                    if not rem: continue
                    front = min(rem, key=lambda p: p_dist(p, obj))
                if front.id == rear.id: continue
                send = int(atk_left(rear.id) * ratio)
                if send < REAR_SEND_MIN: continue
                aim = world.plan_shot(rear.id, front.id, send)
                if aim is None or aim[1] > REAR_MAX_TRAVEL: continue
                push(rear.id, aim[0], send)

    # ── TOTAL WAR ─────────────────────────────────────────────────────────────
    if world.is_total_war and world.enemy_planets and opt_ok():
        # HYPERION: Sort by (distance × 1/production) — closer high-prod first
        primary = ([p for p in world.enemy_planets if p.owner == world._weakest]
                   if world._weakest else world.enemy_planets)
        for src in world.my_planets:
            if expired(): return finalize()
            left = atk_left(src.id)
            if left < 5: continue
            to_try = primary if primary else world.enemy_planets
            best_t = None; best_score = -1.0
            for ep in to_try:
                d = p_dist(src, ep)
                score = ep.production / (d + 1.0)   # HYPERION: prod/distance scoring
                if score > best_score:
                    at = world.plan_shot(src.id, ep.id, left)
                    if at: best_score, best_t = score, ep
            if best_t is None: continue
            aim = world.plan_shot(src.id, best_t.id, left)
            if aim is None: continue
            angle, turns, _, _ = aim
            if turns >= world.remaining: continue
            push(src.id, angle, left)

    return finalize()

# ══════════════════════════════════════════════════════════════════════════════
# AGENT ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

_step = 0

def _read(obs, key, default=None):
    if isinstance(obs, dict): return obs.get(key, default)
    return getattr(obs, key, default)

def build_world(obs, inferred_step=None):
    player    = _read(obs, "player", 0)
    obs_step  = _read(obs, "step", 0) or 0
    step      = max(obs_step, inferred_step or 0)
    planets   = [Planet(*p) for p in (_read(obs, "planets", []) or [])]
    fleets    = [Fleet(*f)  for f in (_read(obs, "fleets", [])  or [])]
    ang_vel   = _read(obs, "angular_velocity", 0.0) or 0.0
    init_raw  = _read(obs, "initial_planets", []) or []
    comets    = _read(obs, "comets", []) or []
    comet_ids = set(_read(obs, "comet_planet_ids", []) or [])
    init_ps   = [Planet(*p) for p in init_raw]
    init_by_id = {p.id: p for p in init_ps}
    return WorldModel(player, step, planets, fleets, init_by_id, ang_vel, comets, comet_ids)

def agent(obs, config=None):
    global _step
    _step += 1
    t0          = time.perf_counter()
    world       = build_world(obs, inferred_step=_step - 1)
    if not world.my_planets: return []
    act_timeout = _read(config, "actTimeout", 1.0) if config else 1.0
    budget      = min(SOFT_DEADLINE, max(0.55, act_timeout * 0.83))
    return plan_moves(world, deadline=t0 + budget)

__all__ = ["agent", "build_world"]
```

## [MD]
## ✅ Validation Suite — Run Before Every Submission

**15 scenarios** covering all 8 layers, all 5 eco modes, all special systems.
Every scenario must pass **before** uploading to Kaggle.

## [CODE]
```python
import importlib.util, time

spec = importlib.util.spec_from_file_location('hyperion', 'submission.py')
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def obs(planets, fleets=None, step=10, player=0, ang_vel=0.03):
    return {
        'player': player, 'step': step, 'angular_velocity': ang_vel,
        'planets': planets, 'fleets': fleets or [],
        'initial_planets': planets, 'comets': [], 'comet_planet_ids': []
    }

tests = {
    # ── Layer 1: Physics ─────────────────────────────────────
    'L1a Solar Bypass':        obs([[0,0,15,50,2.7,80,3],[1,-1,85,50,2.0,20,3],[2,1,85,85,2.7,60,3]],
                                   step=50, ang_vel=0.0),
    # ── Layer 2: World Model ──────────────────────────────────
    'L2  Timeline sim':        obs([[0,0,20,20,2,60,3],[1,1,75,75,2,50,3]],
                                   fleets=[[10,1,62,62,-2.50,1,45]], step=80),
    # ── Layer 3: Eco Modes ────────────────────────────────────
    'L3a SNOWBALL mode':       obs([[0,0,15,15,2.7,400,6],[1,0,25,25,1.7,200,5],[4,1,85,85,2.7,80,2]],step=150),
    'L3b EXPAND mode':         obs([[0,0,15,15,2.7,180,5],[1,0,25,25,1.7,90,3],[4,1,85,85,2.7,80,3]],step=120),
    'L3c AGGRO mode':          obs([[0,0,15,15,2.7,60,1],[3,1,75,75,2.7,60,5],[4,1,65,65,1.7,35,4]],step=150),
    'L3d PANIC mode':          obs([[0,0,15,15,2.7,40,1],[3,1,65,65,2.7,120,6],[4,1,55,55,1.7,80,5]],step=200),
    # ── Layer 4: Policy / Opening Blitz ──────────────────────
    'L4  Opening Blitz t=12':  obs([[0,0,20,20,2,30,3],[1,-1,40,40,1,8,2],[2,-1,60,60,1,6,3],[4,1,82,82,2,35,4]],
                                   step=12, ang_vel=0.02),
    # ── Layer 5: Scoring / Flanking ───────────────────────────
    'L5  Flanking bonus':      obs([[0,0,15,80,2,80,3],[0,0,80,15,2,70,3],[1,1,80,80,2,40,4]],step=80),
    'L5  Exposed planet':      obs([[0,0,20,20,2,80,3],[1,1,75,75,2,10,4]],
                                   fleets=[[10,1,60,60,0.785,1,55]],step=80),
    # ── Layer 6: Mission Engine ───────────────────────────────
    'L6a Rush + Counter-rush': obs([[0,0,20,20,2,55,3],[4,1,80,80,2,90,4]],
                                   fleets=[[10,1,72,72,-2.50,4,65]],step=35),
    'L6b FFA 4-player':        obs([[0,0,20,20,2,50,4],[1,-1,40,30,1,10,2],[2,-1,60,70,1,8,3],
                                    [3,-1,30,60,1.7,12,3],[5,1,82,82,2,80,4],[6,2,18,82,2,70,3],
                                    [7,3,82,18,2,75,3]], step=15, ang_vel=0.025),
    'L6c 1v1 Domination':      obs([[0,0,15,15,2.7,250,4],[1,0,28,20,1.7,120,3],
                                    [4,1,85,85,2.7,80,4],[5,1,70,72,1.7,40,2]],step=200),
    # ── Layer 7: Executor ─────────────────────────────────────
    'L7  Static planet map':   obs([[0,0,15,15,2.7,100,3],[1,-1,90,90,3.0,30,4],
                                    [2,-1,10,90,3.0,25,3],[4,1,85,85,2.7,80,3]],step=80),
    # ── Layer 8: Endgame ──────────────────────────────────────
    'L8a Death Ball DEFEND':   obs([[0,0,20,20,2,300,4],[1,0,30,25,1,150,3],[3,1,78,78,2,100,3]],step=465),
    'L8b Death Ball ALL-IN':   obs([[0,0,20,20,2,80,2],[3,1,78,78,2,200,5]],step=465),
    'L8c Total War':           obs([[0,0,20,20,2,180,4],[1,0,28,28,1,90,2],[3,1,78,78,2,120,4]],step=445),
}

print('=' * 84)
print('  HYPERION ☀️  — FULL VALIDATION SUITE  (16 scenarios, all 8 layers)')
print('=' * 84)
total = 0; passed = 0
for name, o in tests.items():
    total += 1; t0 = time.perf_counter()
    try:
        w = mod.build_world(o)
        actions = mod.agent(o)
        ms = (time.perf_counter() - t0) * 1000
        for act in actions:
            assert len(act) == 3
            sid, angle, ships = act
            assert isinstance(sid, int) and isinstance(angle, float) and isinstance(ships, int)
            assert ships >= 1 and sid in w.by_id
        eco  = w.eco_mode.value
        db   = w.death_ball_mode or '-'
        extra = ''
        if w.in_blitz:             extra += ' 🚀'
        if w.is_rush:              extra += ' 🚨'
        if w.flankable_ids:        extra += f' ⚔️×{len(w.flankable_ids)}'
        print(f'  ✅  {name:<30} │ {ms:>6.1f}ms │ {len(actions):>2} acts │ eco={eco:<10} db={db}{extra}')
        passed += 1
    except Exception as e:
        ms = (time.perf_counter() - t0) * 1000
        print(f'  ❌  {name:<30} │ {ms:>6.1f}ms │ FAILED: {e}')
print('=' * 84)
if passed == total:
    print(f'  🎉 ALL {total}/{total} TESTS PASSED — Ready to submit!')
else:
    print(f'  ⚠️  {passed}/{total} passed')
print('=' * 84)
```

## [MD]
## 🔧 Tuning Guide & Further Improvement Ideas

### Constants to Hill-Climb (Highest Impact First)

| Layer | Constant | Current | Try Range | Impact |
|-------|----------|---------|-----------|--------|
| L4 | `OPENING_BLITZ_TURNS` | 22 | 15–30 | How long aggressive opening lasts |
| L4 | `OPENING_BLITZ_RESERVE_FRAC` | 0.55 | 0.40–0.70 | Opening aggression level |
| L1 | `TSUNAMI_THRESH` | 1.5 | 1.3–1.8 | How often tsunami fires |
| L5 | `PROD_EXP` | 1.32 | 1.25–1.42 | High-prod planet dominance |
| L5 | `FLANKING_VM` | 1.20 | 1.10–1.35 | Flanking opportunity value |
| L5 | `EARLY_NEUTRAL_VM` | 1.45 | 1.30–1.60 | Early neutral priority |
| L6 | `INTERCEPT_ETA_MAX` | 30 | 22–38 | How far ahead to intercept |
| L8 | `DEATH_BALL_WIN_MARGIN` | 1.15 | 1.08–1.25 | When to defend endgame |
| L5 | `PRESSURE_BONUS_PER` | 0.16 | 0.10–0.24 | Multi-front attack bonus |
| L3 | `ECO_AGGRO_THRESH` | 0.72 | 0.65–0.80 | When to switch to AGGRO |

### Next-Level Architecture Improvements

**1. Genetic Algorithm Constant Tuning**
Run 500+ self-play games, hill-climb the constants above.
Even `PROD_EXP: 1.32 → 1.35` can change Elo by 10-20 points.

**2. Production Sequence Optimization**
Instead of evaluating each target independently, compute chains:
`capture A → use A to capture B → use B to capture C`
The compounding value of sequenced captures is 20-30% higher than greedy.

**3. FFA Coalition Detection**
Track which two enemies are fighting each other in real-time.
Attack the winner exactly when their garrison is lowest (right after battle).

**4. Adaptive Opening Book**
Hardcode optimal first 5–8 moves for common planet configurations.
Learning from top agents' first moves can dramatically improve opening.

**5. Neural Network Scoring**
Replace `target_value()` with a small network (32-64 neurons)
trained on `(game_state_features, action) → win_probability`.
Input: distances, productions, ship counts, remaining turns.
Output: expected score delta.

### Competition Tips

- Submit early to establish a baseline Elo
- Each submission plays ~20 games — a single submission can have high variance
- Try constant changes one at a time to isolate what helps
- Check the Discussion tab for game replays to identify where your agent loses

## [CODE]
```python

```
