## [CODE]
```python
%%writefile submission.py
import math

def agent(obs):
    moves = []

    player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
    raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
    w = obs.get("angular_velocity", 0) if isinstance(obs, dict) else obs.angular_velocity
    step = obs.get("step", 0) if isinstance(obs, dict) else obs.step

    remaining_steps = 500 - step

    class SimplePlanet:
        def __init__(self, id, owner, x, y, radius, ships, production):
            self.id = id
            self.owner = owner
            self.x = x
            self.y = y
            self.radius = radius
            self.ships = ships
            self.production = production

    planets = [SimplePlanet(*p) for p in raw_planets]
    my_planets = [p for p in planets if p.owner == player]
    targets = [p for p in planets if p.owner != player]

    def get_fleet_speed(ships):
        if ships <= 1:
            return 1.0
        return min(6.0, 1.0 + 5.0 * (math.log(ships) / math.log(1000)) ** 1.5)

    def get_future_pos(p, t, angular_velocity):
        dist_to_sun = math.hypot(p.x - 50, p.y - 50)
        if dist_to_sun + p.radius >= 50 or angular_velocity == 0:
            return p.x, p.y
        current_angle = math.atan2(p.y - 50, p.x - 50)
        new_angle = current_angle + angular_velocity * t
        return (
            50 + dist_to_sun * math.cos(new_angle),
            50 + dist_to_sun * math.sin(new_angle)
        )

    def intersects_sun(x1, y1, x2, y2, sun_x=50, sun_y=50, sun_r=10.5):
        line_len_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
        if line_len_sq == 0:
            return False
        t = max(
            0,
            min(
                1,
                ((sun_x - x1) * (x2 - x1) + (sun_y - y1) * (y2 - y1)) / line_len_sq
            )
        )
        proj_x = x1 + t * (x2 - x1)
        proj_y = y1 + t * (y2 - y1)
        return math.hypot(sun_x - proj_x, sun_y - proj_y) <= sun_r

    for mine in my_planets:
        defense_reserve = 5 + mine.production * 2
        available_ships = mine.ships - defense_reserve

        if available_ships < 30:
            continue

        best_target = None
        best_score = -float("inf")
        best_angle = 0
        ships_to_send = 0

        speed = get_fleet_speed(available_ships)

        for t in targets:
            travel_time = math.hypot(t.x - mine.x, t.y - mine.y) / speed

            for _ in range(3):
                future_x, future_y = get_future_pos(t, travel_time, w)
                travel_time = math.hypot(future_x - mine.x, future_y - mine.y) / speed

            if intersects_sun(mine.x, mine.y, future_x, future_y):
                continue

            future_enemy_ships = t.ships
            if t.owner != -1:
                future_enemy_ships += int(t.production * travel_time)

            required_ships = future_enemy_ships + 3

            if available_ships >= required_ships:
                active_turns = remaining_steps - travel_time
                if active_turns <= 0:
                    continue

                gained_production = t.production * active_turns
                net_profit = gained_production - required_ships

                score = net_profit / (travel_time + 1)

                if score > best_score:
                    best_score = score
                    best_target = t
                    ships_to_send = required_ships
                    best_angle = math.atan2(future_y - mine.y, future_x - mine.x)

        if best_target and best_score > 0:
            moves.append([mine.id, best_angle, ships_to_send])

    return moves
```
