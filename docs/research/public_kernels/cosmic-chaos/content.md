## [CODE]
```python
%%writefile submission.py

import math

def get_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def agent(obs, conf):
    my_id = obs.player
    actions = []

    my_ships = [s for s in obs.ships if s.player == my_id]
    # Planets that are either unowned or owned by enemies
    target_planets = [p for p in obs.planets if p.player != my_id]

    if not my_ships or not target_planets:
        return []

    # Track which planets we are already heading to
    assigned_planets = []

    for ship in my_ships:
        # If the ship is already docking, let it finish
        if ship.status == "docking":
            continue

        # Find the closest planet that hasn't been over-assigned
        # We filter target_planets to find the best one for THIS ship
        closest_planet = min(target_planets, key=lambda p: get_distance(ship.x, ship.y, p.x, p.y))
        dist = get_distance(ship.x, ship.y, closest_planet.x, closest_planet.y)

        # Logic: If close enough, DOCK. If far, MOVE.
        # Note: '3.0' is a placeholder distance; check your game's docking radius.
        if dist < 3.0:
            actions.append({
                "action": "dock",
                "ship_id": ship.id,
                "planet_id": closest_planet.id
            })
        else:
            actions.append({
                "action": "move",
                "ship_id": ship.id,
                "x": closest_planet.x,
                "y": closest_planet.y
            })

    return actions
```
