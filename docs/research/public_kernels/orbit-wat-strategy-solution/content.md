## [MD]
# ORBIT WARS - MONTE CARLO PRO AGENT

## [CODE]
```python
%%writefile submission.py
import math
from collections import defaultdict

# ============================================================
# ORBIT WARS - MONTE CARLO PRO AGENT (SINGLE FILE SUBMISSION)
# ============================================================

import math
import random
import copy
from collections import defaultdict

# ============================================================
# DATA STRUCTURES
# ============================================================

class Planet:
    def __init__(self, id, owner, x, y, radius, ships, production):
        self.id = id
        self.owner = owner
        self.x = x
        self.y = y
        self.radius = radius
        self.ships = ships
        self.production = production

class Fleet:
    def __init__(self, id, owner, x, y, angle, from_planet_id, ships):
        self.id = id
        self.owner = owner
        self.x = x
        self.y = y
        self.angle = angle
        self.from_planet_id = from_planet_id
        self.ships = ships

# ============================================================
# UTILITY
# ============================================================

def distance(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

def angle_to(a, b):
    return math.atan2(b[1]-a[1], b[0]-a[0])

# ============================================================
# SIMULATION ENGINE (CRITICAL)
# ============================================================

FLEET_SPEED = 3.0

def simulate_step(planets, fleets):
    # Production
    for p in planets:
        if p.owner != -1:
            p.ships += p.production

    # Move fleets
    for f in fleets:
        f.x += math.cos(f.angle) * FLEET_SPEED
        f.y += math.sin(f.angle) * FLEET_SPEED

    # Handle arrivals
    new_fleets = []
    for f in fleets:
        arrived = False

        for p in planets:
            d = distance((f.x, f.y), (p.x, p.y))
            if d <= p.radius:
                # Combat
                if p.owner == f.owner:
                    p.ships += f.ships
                else:
                    if f.ships > p.ships:
                        p.owner = f.owner
                        p.ships = f.ships - p.ships
                    else:
                        p.ships -= f.ships

                arrived = True
                break

        if not arrived:
            new_fleets.append(f)

    return planets, new_fleets


def simulate(planets, fleets, moves, steps=20):
    planets = copy.deepcopy(planets)
    fleets = copy.deepcopy(fleets)

    # Apply moves
    for m in moves:
        source = next((p for p in planets if p.id == m[0]), None)
        if source is None or source.ships < m[2]:
            continue

        fleets.append(Fleet(
            id=0,
            owner=source.owner,
            x=source.x,
            y=source.y,
            angle=m[1],
            from_planet_id=source.id,
            ships=m[2]
        ))

        source.ships -= m[2]

    # Run simulation
    for _ in range(steps):
        planets, fleets = simulate_step(planets, fleets)

    return planets, fleets

# ============================================================
# EVALUATION FUNCTION
# ============================================================

def evaluate(planets, fleets, player):
    my_ships = 0
    enemy_ships = 0
    my_prod = 0
    enemy_prod = 0

    for p in planets:
        if p.owner == player:
            my_ships += p.ships
            my_prod += p.production
        else:
            enemy_ships += p.ships
            enemy_prod += p.production

    for f in fleets:
        if f.owner == player:
            my_ships += f.ships
        else:
            enemy_ships += f.ships

    return (
        (my_ships - enemy_ships) +
        (my_prod - enemy_prod) * 60.0
    )

# ============================================================
# MOVE GENERATION (SMART SAMPLING)
# ============================================================

def generate_candidates(my_planets, enemy_planets):
    candidates = []

    if not enemy_planets:
        return [[]]

    for _ in range(25):  # number of samples
        moves = []

        for p in my_planets:
            if p.ships < 25:
                continue

            # Bias toward high ROI targets
            if random.random() < 0.7:
                target = max(
                    enemy_planets,
                    key=lambda e: e.production / (e.ships + 1)
                )
            else:
                target = random.choice(enemy_planets)

            angle = angle_to((p.x, p.y), (target.x, target.y))
            ships = int(p.ships * random.uniform(0.3, 0.7))

            if ships >= 20:
                moves.append([p.id, angle, ships])

        candidates.append(moves)

    return candidates

# ============================================================
# MONTE CARLO CORE
# ============================================================

def monte_carlo_decision(planets, fleets, player):
    my_planets = [p for p in planets if p.owner == player]
    enemy_planets = [p for p in planets if p.owner != player]

    if not my_planets or not enemy_planets:
        return []

    candidates = generate_candidates(my_planets, enemy_planets)

    best_score = -1e9
    best_moves = []

    for moves in candidates:
        sim_p, sim_f = simulate(planets, fleets, moves, steps=20)
        score = evaluate(sim_p, sim_f, player)

        if score > best_score:
            best_score = score
            best_moves = moves

    return best_moves

# ============================================================
# SAFE FALLBACK (HEURISTIC)
# ============================================================

def fallback_strategy(planets, player):
    moves = []

    my_planets = [p for p in planets if p.owner == player]
    enemy_planets = [p for p in planets if p.owner != player]

    for p in my_planets:
        if p.ships < 30 or not enemy_planets:
            continue

        target = min(enemy_planets,
                     key=lambda e: distance((p.x, p.y), (e.x, e.y)))

        angle = angle_to((p.x, p.y), (target.x, target.y))
        ships = int(p.ships * 0.5)

        if ships >= 20:
            moves.append([p.id, angle, ships])

    return moves

# ============================================================
# FINAL AGENT (SUBMIT THIS)
# ============================================================

def agent(obs):
    try:
        if isinstance(obs, dict):
            player = obs.get("player", 0)
            raw_planets = obs.get("planets", [])
            raw_fleets = obs.get("fleets", [])
        else:
            player = obs.player
            raw_planets = obs.planets
            raw_fleets = obs.fleets

        planets = [Planet(*p) for p in raw_planets]
        fleets = [Fleet(*f) for f in raw_fleets]

        # Monte Carlo decision
        moves = monte_carlo_decision(planets, fleets, player)

        if moves:
            return moves

        # fallback
        return fallback_strategy(planets, player)

    except:
        return []
```
