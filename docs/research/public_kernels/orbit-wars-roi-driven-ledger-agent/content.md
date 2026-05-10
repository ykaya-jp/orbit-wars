## [MD]
# 🪐 Orbit Wars - ROI-Driven Ledger Agent

**Strategy:** Cost-Benefit Greedy Optimizer + Ledger Tracking

## Core Mechanics
1. **Fast Ledger Tracking:** Maps all inbound fleets to calculate exact defense needs and prevent sending multiple fleets to capture the same target (Double-dispatch prevention).
2. **Strict Neutral vs. Hostile Math:** Neutrals do not accumulate ships in transit. The bot calculates the exact mathematical minimum to capture.
3. **ROI Scoring:** Prioritizes targets based on `(Production * Time Alive) / (Required Ships + ETA)`.
4. **Anti-Paralysis Execution:** Attempts to send a small safety margin, but gracefully falls back to the bare minimum if the budget is tight, ensuring continuous aggressive expansion.

## [CODE]
```python
%%capture
!pip install --upgrade "kaggle-environments>=1.28.0"
```

## [CODE]
```python
%%writefile submission.py
import math
from collections import defaultdict

# =====================================================================
# Configuration & Constants
# =====================================================================
SUN_X, SUN_Y = 50.0, 50.0
SUN_RADIUS = 10.0
SUN_SAFE_ZONE = SUN_RADIUS + 1.5
MAX_SPEED = 6.0
BOARD_SIZE = 100.0

MIN_GARRISON_PCT = 0.15
MIN_GARRISON_ABS = 5
SAFETY_MARGIN = 3

# =====================================================================
# Physics & Navigation
# =====================================================================
def get_distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)

def get_fleet_speed(ships):
    ships = max(1, int(ships))
    ratio = min(1.0, math.log(ships) / math.log(1000.0))
    return 1.0 + (MAX_SPEED - 1.0) * (ratio ** 1.5)

def is_path_safe(x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx**2 + dy**2
    if length_sq == 0: return True
    t = max(0, min(1, ((SUN_X - x1) * dx + (SUN_Y - y1) * dy) / length_sq))
    return get_distance(SUN_X, SUN_Y, x1 + t * dx, y1 + t * dy) >= SUN_SAFE_ZONE

def predict_pos(target, turns, ang_vel, initial_state):
    """Predicts future position for both planets and comets."""
    if target.get('is_comet', False):
        idx = target['comet_index'] + int(turns)
        if idx < len(target['comet_path']):
            return target['comet_path'][idx][0], target['comet_path'][idx][1]
        return None, None

    init_p = initial_state.get(target['id'])
    if not init_p: return target['x'], target['y']
    r = get_distance(init_p['x'], init_p['y'], SUN_X, SUN_Y)
    if r >= 40.0: return target['x'], target['y']

    current_angle = math.atan2(target['y'] - SUN_Y, target['x'] - SUN_X)
    future_angle = current_angle + (ang_vel * turns)
    return SUN_X + r * math.cos(future_angle), SUN_Y + r * math.sin(future_angle)

def calculate_intercept(src_x, src_y, target, ships, ang_vel, initial_state):
    speed = get_fleet_speed(ships)
    tx, ty = target['x'], target['y']
    for _ in range(3):
        eta = get_distance(src_x, src_y, tx, ty) / speed
        px, py = predict_pos(target, eta, ang_vel, initial_state)
        if px is None: return None, None, None
        tx, ty = px, py

    eta = math.ceil(get_distance(src_x, src_y, tx, ty) / speed)
    angle = math.atan2(ty - src_y, tx - src_x)
    return angle, eta, (tx, ty)

# =====================================================================
# Strategic Commander
# =====================================================================
def agent(obs):
    # 1. Parse Observation
    if not isinstance(obs, dict): obs = obs.__dict__
    player_id = obs.get("player", 0)
    ang_vel = obs.get("angular_velocity", 0.0)
    turns_left = max(1, 500 - obs.get("step", 0))

    planets = {p[0]: {'id': p[0], 'owner': p[1], 'x': p[2], 'y': p[3], 'radius': p[4], 'ships': p[5], 'production': p[6], 'is_comet': False} for p in obs.get("planets", [])}
    initial_state = {p[0]: {'x': p[2], 'y': p[3]} for p in obs.get("initial_planets", [])}
    fleets = [{'owner': f[1], 'x': f[2], 'y': f[3], 'target_id': None, 'ships': f[6], 'angle': f[4]} for f in obs.get("fleets", [])]

    for c in obs.get("comets", []):
        for i, p_id in enumerate(c.get("planet_ids", [])):
            if p_id in planets:
                planets[p_id].update({'is_comet': True, 'comet_path': c["paths"][i], 'comet_index': c["path_index"]})

    # 2. Build Ledger (Track in-flight ships)
    inbound_ally = defaultdict(int)
    inbound_enemy = defaultdict(int)

    for f in fleets:
        # Infer target based on angle and position
        best_target, best_err = None, 0.5
        for p in planets.values():
            dx, dy = p['x'] - f['x'], p['y'] - f['y']
            dist = math.hypot(dx, dy)
            if dist == 0: continue

            # Dot product to check if fleet is moving towards planet
            f_dx, f_dy = math.cos(f['angle']), math.sin(f['angle'])
            dot = (dx * f_dx + dy * f_dy) / dist
            if dot > 0.9: # Very tight cone
                err = 1.0 - dot
                if err < best_err:
                    best_err = err
                    best_target = p['id']

        if best_target is not None:
            if f['owner'] == player_id: inbound_ally[best_target] += f['ships']
            else: inbound_enemy[best_target] += f['ships']

    # 3. Calculate Budgets (Defense First)
    attack_budget = {}
    my_planets = [p for p in planets.values() if p['owner'] == player_id]

    for p in my_planets:
        net_ships = p['ships'] + inbound_ally[p['id']] - inbound_enemy[p['id']]

        # If we are under attack, keep everything we can to survive
        if net_ships < 0:
            attack_budget[p['id']] = 0
            continue

        # Base garrison to prevent cheap snipes
        garrison = max(MIN_GARRISON_ABS, int(p['ships'] * MIN_GARRISON_PCT))

        # If total war (last 30 turns), abandon garrison
        if turns_left < 30: garrison = 0

        attack_budget[p['id']] = max(0, int(p['ships']) - garrison)

    # 4. Generate & Score Missions (ROI)
    missions = []
    for target in planets.values():
        if target['owner'] == player_id: continue

        for source in my_planets:
            avail = attack_budget[source['id']]
            if avail <= 0: continue

            angle, eta, pred = calculate_intercept(source['x'], source['y'], target, avail, ang_vel, initial_state)
            if angle is None or not is_path_safe(source['x'], source['y'], pred[0], pred[1]): continue

            # Mathematical Minimum Cost
            if target['owner'] == -1:
                # Neutrals do NOT produce ships in transit
                base_cost = target['ships'] + 1
            else:
                # Enemies DO produce ships in transit
                base_cost = target['ships'] + (target['production'] * eta) + 1

            # Adjust based on fleets already in flight
            net_cost = base_cost + inbound_enemy[target['id']] - inbound_ally[target['id']]
            needed = max(1, int(net_cost))

            if needed > avail: continue # We can't afford it

            # ROI Score
            multiplier = 1.0
            if target['owner'] != -1: multiplier = 2.0 # Denying enemy prod is worth 2x
            if target['is_comet']: multiplier = 0.8

            value = (target['production'] * turns_left) * multiplier
            if turns_left < 30: value += target['ships'] # Late game: raw ship capture matters

            score = value / (needed + (eta * 0.5) + 1)

            missions.append({
                'src': source['id'],
                'tgt': target['id'],
                'ang': angle,
                'need': needed,
                'eta': eta,
                'score': score
            })

    # 5. Execute Greedy Selection
    missions.sort(key=lambda x: x['score'], reverse=True)
    moves = []
    targeted = set()

    for m in missions:
        if m['tgt'] in targeted: continue

        src, need = m['src'], m['need']
        avail = attack_budget[src]

        if avail >= need:
            # FLEXIBLE SENDING: Try to send safety margin, but fallback to minimum if needed
            desired = need + SAFETY_MARGIN
            actual_send = min(avail, desired)

            moves.append([src, m['ang'], actual_send])

            # Update state to prevent double-spending
            attack_budget[src] -= actual_send
            inbound_ally[m['tgt']] += actual_send
            targeted.add(m['tgt'])

    return moves
```

## [MD]
## Validating

## [CODE]
```python
from kaggle_environments import make

# Setup 10 validation matches
wins, losses, draws = 0, 0, 0
N_GAMES = 10

print(f"Running {N_GAMES} matches: submission.py (Agent) vs random (Baseline)...\n")

for game in range(N_GAMES):
    # Initialize the Orbit Wars environment
    env = make("orbit_wars", debug=False)

    # Run the match
    env.run(["submission.py", "random"])

    # Determine the winner
    final_step = env.steps[-1]
    r0 = final_step[0].get('reward', 0)
    r1 = final_step[1].get('reward', 0)

    if r0 > r1:
        outcome = "WIN"
        wins += 1
    elif r0 < r1:
        outcome = "LOSS"
        losses += 1
    else:
        outcome = "DRAW"
        draws += 1

    print(f"  Match {game+1}: Agent={r0:+.2f} | Baseline={r1:+.2f}  -> {outcome}")

print(f"\nFinal Results: {wins}W / {losses}L / {draws}D  (Win Rate: {wins/N_GAMES:.0%})")
```
