## [MD]
This agents is dumb: it shoots at planets at random. But, it **never misses**.

The main contribution here is the `aim_for_planet` function. It works by iteratively refining the predicted planet position and shoots at the current best prediction.

## [CODE]
```python
%%writefile main.py
import random
import math
from kaggle_environments.envs.orbit_wars.orbit_wars import CENTER, ROTATION_RADIUS_LIMIT, SUN_RADIUS, Planet, point_to_segment_distance



def get_fleet_speed(ships):
    if ships <= 1:
        return 1.0
    return 1.0 + 5.0 * (math.log(ships) / math.log(1000.0)) ** 1.5


def predict_planet_position(planet, turns_ahead, angular_velocity):
    """
    Predict the position of a planet after a certain number of turns.

    Args:
        planet: The Planet object.
        turns_ahead: Number of turns to predict ahead.
        angular_velocity: The angular velocity of the planet.

    Returns:
        Tuple (x, y) representing the predicted position.
    """
    dx = planet.x - CENTER
    dy = planet.y - CENTER
    orbital_r = math.sqrt(dx * dx + dy * dy)
    if orbital_r + planet.radius >= ROTATION_RADIUS_LIMIT:
        return planet.x, planet.y
    initial_angle = math.atan2(dy, dx)
    current_angle = initial_angle + angular_velocity * turns_ahead
    return CENTER + orbital_r * math.cos(current_angle), CENTER + orbital_r * math.sin(current_angle)


def ships_to_capture_needed(target, turns_ahead):
    """
    Calculate the number of ships needed to capture a target planet.

    Args:
        target_ships: Current ships on the target planet.
        target_production: Production rate of the target planet.
        turns_ahead: Number of turns until arrival.

    Returns:
        Number of ships needed to capture the target.
    """
    if turns_ahead <= 0:
        turns_ahead = 1
    needed = target.ships + (target.owner >= 0) * target.production * turns_ahead + 1
    return max(1, int(needed))


def aim_for_planet(target: Planet, my_planet: Planet, angular_velocity, is_my: bool=False) -> tuple[float, int, bool, int] | None:
    """
    Determine the angle and number of ships to send to a target planet.

    Args:
        target: The target Planet object.
        my_planet: The source Planet object.
        angular_velocity: The angular velocity of the planets.

    Returns:
        Tuple (angle, ships_to_send) if valid, None otherwise.
    """
    my_x, my_y = my_planet.x, my_planet.y
    max_available: int = my_planet.ships

    # Initial guess for position and ships
    predicted_x, predicted_y = target.x, target.y
    est_ships: int = max(10, max_available // 2)
    can_capture = False

    # Iterative refinement to predict target position accurately
    conveged = False
    for _ in range(10):
        # Current assumption
        dx = predicted_x - my_x
        dy = predicted_y - my_y
        distance = math.sqrt(dx * dx + dy * dy) - my_planet.radius
        est_speed = get_fleet_speed(est_ships)
        turns_to_arrive = max(1.0, int(distance / est_speed))

        # Update estimated ships
        if not is_my:
            new_est_ships = ships_to_capture_needed(target, turns_to_arrive)
        else:
            new_est_ships = max(1, max_available // 2)

        # Can we capture?
        if new_est_ships < max_available:
            can_capture = True
        else:
            new_est_ships = max_available - 1
            can_capture = False

        # Update position
        est_speed = get_fleet_speed(new_est_ships)
        turns_to_arrive = max(1.0, int(distance / est_speed))
        new_predicted_x, new_predicted_y = predict_planet_position(target, turns_to_arrive, angular_velocity)

        # Stopping criteria
        error = math.sqrt((predicted_x - new_predicted_x) ** 2 + (predicted_y - new_predicted_y) ** 2)
        delta_ships = abs(new_est_ships - est_ships)
        est_ships = new_est_ships
        predicted_x, predicted_y = new_predicted_x, new_predicted_y

        if error < 0.01 and delta_ships == 0:
            conveged = True
            break

    # Chack reacheability
    if not conveged:
        return None

    # Check sun collision
    if point_to_segment_distance((CENTER, CENTER), (my_x, my_y), (predicted_x, predicted_y)) < SUN_RADIUS + 1:
        return None

    angle: float = math.atan2(predicted_y - my_y, predicted_x - my_x)

    return angle, est_ships, can_capture, turns_to_arrive


def agent(obs):
    """
    Main agent function for the Orbit Wars environment.

    Args:
        obs: Observation dictionary from the environment.

    Returns:
        List of moves to execute.
    """
    moves = []
    player = obs.get("player", 0)
    planets = [Planet(*p) for p in obs.get("planets", [])]
    comet_ids = set(obs['comet_planet_ids'])
    angular_velocity = obs["angular_velocity"]

    my_planets = [p for p in planets if p.owner == player]
    targets = [p for p in planets if p.owner != player]

    if not my_planets or not targets:
        return moves

    for mp in my_planets:
        my_is_comet = mp.id in comet_ids

        # Select random target from the closest
        defend = (random.random() < 0.1 or my_is_comet) and len(my_planets) > 1
        if defend:
            targets_to_choose = [p for p in my_planets if p.id != mp.id]
        else:
            targets_to_choose = targets
        targets_to_choose = sorted(targets_to_choose, key=lambda t: (mp.x - t.x)**2 + (mp.y - t.y)**2)

        # Limit numer of targets
        if random.random() < 0.9:
            targets_to_choose = targets_to_choose[:max(1, len(targets) // 2)]

        # Choose target, with bias to closer planets
        n = len(targets_to_choose)
        target_i = min(random.randint(0, n - 1), random.randint(0, n - 1))
        target = targets_to_choose[target_i]

        target_is_comet = target.id in comet_ids
        if target_is_comet:
            continue # i can't aim at comet

        # Aim
        result = aim_for_planet(target, mp, angular_velocity, defend)

        if result is not None:
            angle, ships, can_capture, turns_to_arrive = result
            if can_capture or random.random() < 0.1 or my_is_comet:
                cost = turns_to_arrive * (2 - can_capture)
                moves.append([mp.id, angle, ships, cost])

    # Sort by closeness (turns_to_arrive), take max_moves
    max_moves = random.randint(0, 4)
    moves = sorted(moves, key=lambda m: m[-1])
    moves = moves[:max_moves]
    moves = [m[:3] for m in moves]

    return moves
```

## [MD]
## Showcase

## [CODE]
```python
!pip install --upgrade "kaggle-environments>=1.28.0"
```

## [CODE]
```python
from kaggle_environments import make
```

## [CODE]
```python
from main import agent

env = make("orbit_wars", debug=True)
env.run([agent, agent])

env.render(mode="ipython", width=800, height=600)
```

## [CODE]
```python

```
