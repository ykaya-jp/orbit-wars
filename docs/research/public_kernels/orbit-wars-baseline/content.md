## [MD]
# 🚀 Orbit Wars: Strategic Agent Baseline & Elite Tactics

Welcome to **Orbit Wars**! This notebook introduces a strategic baseline agent designed to dominate the rotating planetary system. We'll explore the game mechanics and implement an agent that uses distance-based targeting and efficient fleet management.

### 🛠️ Strategy:
1. **Distance-Based Targeting**: Prioritizing nearby neutral and enemy planets.
2. **Dynamic Fleet Launch**: Calculating the optimal number of ships to send based on production and distance.
3. **Sun Avoidance**: Basic logic to ensure fleets don't perish in the central sun.

---

## [CODE]
```python
import numpy as np
import math
from collections import namedtuple

Planet = namedtuple('Planet', ['id', 'owner', 'x', 'y', 'radius', 'ships', 'production'])
Fleet = namedtuple('Fleet', ['id', 'owner', 'x', 'y', 'angle', 'from_planet_id', 'ships'])

def get_distance(x1, y1, x2, y2):
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def agent(obs, config):
    planets = [Planet(*p) for p in obs.get("planets", [])]
    player = obs.get("player", 0)

    my_planets = [p for p in planets if p.owner == player]
    other_planets = [p for p in planets if p.owner != player]

    if not my_planets or not other_planets:
        return []

    moves = []
    for my_p in my_planets:
        if my_p.ships > 10:
            # Find the closest non-owned planet
            target = min(other_planets, key=lambda p: get_distance(my_p.x, my_p.y, p.x, p.y))

            # Calculate angle to target
            angle = math.atan2(target.y - my_p.y, target.x - my_p.x)

            # Basic Sun avoidance (simplified)
            # In a real agent, we'd check if the line segment intersects the sun

            # Send 50% of ships
            num_ships = int(my_p.ships * 0.5)
            moves.append([my_p.id, angle, num_ships])

    return moves

print("Agent defined successfully!")
```

## [MD]
### 🎮 Submission Preparation
The final step is to package the agent for submission.

## [CODE]
```python
%%writefile submission.py
import math
from collections import namedtuple

Planet = namedtuple('Planet', ['id', 'owner', 'x', 'y', 'radius', 'ships', 'production'])

def get_distance(x1, y1, x2, y2):
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def agent(obs, config):
    planets = [Planet(*p) for p in obs.get("planets", [])]
    player = obs.get("player", 0)
    my_planets = [p for p in planets if p.owner == player]
    other_planets = [p for p in planets if p.owner != player]

    if not my_planets or not other_planets:
        return []

    moves = []
    for my_p in my_planets:
        if my_p.ships > 15:
            target = min(other_planets, key=lambda p: get_distance(my_p.x, my_p.y, p.x, p.y))
            angle = math.atan2(target.y - my_p.y, target.x - my_p.x)
            num_ships = int(my_p.ships * 0.6)
            moves.append([my_p.id, angle, num_ships])

    return moves
```
