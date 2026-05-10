## [CODE]
```python
%%writefile observation.py
class GameState:
    def __init__(self, obs):
        # Add your initialization logic here
        self.obs = obs
        # Example parsing:
        self.my_planets = obs.get("my_planets", [])

    # Add your helper methods for state analysis here
```

## [CODE]
```python
%%writefile strategy.py
class Strategy:
    def __init__(self, state):
        self.state = state

    def calculate(self):
        # Add your strategy logic here
        # Return a list of moves, e.g., [[planet_id, angle, ships], ...]
        return []
```

## [CODE]
```python
from observation import GameState
from strategy import Strategy

def agent(obs):
    state = GameState(obs)

    if not state.my_planets:
        return []

    strategy = Strategy(state)
    moves = strategy.calculate()

    sanitized_moves = []
    for move in moves:
        if len(move) == 3:
            planet_id = int(move[0])
            angle = float(move[1])
            ships = int(move[2])

            my_planet = next((p for p in state.my_planets if p.id == planet_id), None)
            if my_planet and my_planet.ships >= ships and ships > 0:
                sanitized_moves.append([planet_id, angle, ships])

    return sanitized_moves
```

## [CODE]
```python
from observation import GameState
from strategy import Strategy

def agent(obs):
    state = GameState(obs)

    # Check if we have planets to play with
    if not hasattr(state, 'my_planets') or not state.my_planets:
        return []

    strategy = Strategy(state)
    moves = strategy.calculate()

    sanitized_moves = []
    for move in moves:
        if len(move) == 3:
            planet_id = int(move[0])
            angle = float(move[1])
            ships = int(move[2])

            # Validation logic
            my_planet = next((p for p in state.my_planets if p.id == planet_id), None)
            if my_planet and my_planet.ships >= ships and ships > 0:
                sanitized_moves.append([planet_id, angle, ships])

    return sanitized_moves
```

## [CODE]
```python

```

## [CODE]
```python

```

## [CODE]
```python

```
