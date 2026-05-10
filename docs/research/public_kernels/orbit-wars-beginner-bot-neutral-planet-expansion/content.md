## [CODE]
```python
%%writefile main.py
import math
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet

def distance(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)

def angle_to(a, b):
    return math.atan2(b.y - a.y, b.x - a.x)

def agent(obs):
    moves = []

    player = obs.get("player", 0)
    raw_planets = obs.get("planets", [])
    planets = [Planet(*p) for p in raw_planets]

    my_planets = [p for p in planets if p.owner == player]
    neutral_planets = [p for p in planets if p.owner == -1]

    if not my_planets or not neutral_planets:
        return moves

    for mine in my_planets:
        if mine.ships < 15:
            continue

        best_target = None
        best_score = -999999

        for target in neutral_planets:
            d = distance(mine, target)

            # High production is good.
            # Low ships is good.
            # Short distance is good.
            score = (target.production * 10) - target.ships - (d * 0.3)

            if score > best_score:
                best_score = score
                best_target = target

        if best_target is None:
            continue

        ships_to_send = int(best_target.ships + 5)

        # Do not send all ships
        if ships_to_send < mine.ships * 0.6:
            angle = angle_to(mine, best_target)
            moves.append([mine.id, angle, ships_to_send])

    return moves
```

## [CODE]
```python
!pip install --upgrade kaggle-environments
```

## [CODE]
```python
from kaggle_environments import make

env = make("orbit_wars", debug=True)
env.run(["main.py", "random"])

final = env.steps[-1]

for i, state in enumerate(final):
    print(f"Player {i}: reward={state.reward}, status={state.status}")
```

## [CODE]
```python

```

## [CODE]
```python

```
