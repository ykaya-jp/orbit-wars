## [MD]
# You can use this temlate to ask LLM to create grid search factory with your agent and parameters (constants in this case). There are NUM_GAMES parameters - how many games with each combination of parameters will be played between the agent inside the factory and the agent with whom he will compete (the strong_agent variable in which you need to put the path to the opponent agent). You can optionally add parallelization.

## [CODE]
```python
%%writefile grid.py
"""
Parameter sweep for agent_2 — finding optimal values for:
  MIN_SHIPS_MINE_ATTACK, MIN_SHIPS_TARGET_COOP_ATTACK,
  COOP_PLANET_CAP, COLLIDE_TICK_THOLD

CPU-only. No CuPy/GPU dependencies.
Each combination is tested over 30 games against strong_agent.
Top-5 results by winrate are printed at the end.
"""

import math
import itertools
from kaggle_environments import make
import kaggle_environments.envs.orbit_wars.orbit_wars as ow

# ── базовые (текущие) значения констант ──────────────────────────────
BASE_MIN_SHIPS_MINE_ATTACK        = 10
BASE_MIN_SHIPS_TARGET_COOP_ATTACK = 20
BASE_COOP_PLANET_CAP              = 8
BASE_COLLIDE_TICK_THOLD           = 1

# ── сетка параметров: 1 меньше, 1 базовое, 1 больше ────────────────
param_grid = {
    "MIN_SHIPS_MINE_ATTACK":        [6, 8, 10],
    "MIN_SHIPS_TARGET_COOP_ATTACK": [24, 28, 32],
    "COOP_PLANET_CAP":              [4, 5, 6],
    "COLLIDE_TICK_THOLD":           [1],     # 0 = точное совпадение
}

# ── фабрика агента с заданными константами ───────────────────────────
def make_agent_2(
    MIN_SHIPS_MINE_ATTACK,
    MIN_SHIPS_TARGET_COOP_ATTACK,
    COOP_PLANET_CAP,
    COLLIDE_TICK_THOLD,
):
    """Возвращает функцию-агента agent_2 с конкретными значениями констант."""

    MAX_SPEED = 6.0
    _fleet_trajectories = []
    _moving_planets = []
    _steps = [0]  # mutable int в замыкании

    # ── вспомогательные функции (те же, что в оригинале) ─────────────
    def get_custom_score_2(m, t):
        dist = math.sqrt((m.x - t.x)**2 + (m.y - t.y)**2)
        min_ships = t.ships + 1
        fleet_speed = 1.0 + (MAX_SPEED - 1.0) * (math.log(max(1, min_ships)) / math.log(1000)) ** 1.5
        eta = dist / fleet_speed
        enemy_produced = 0
        enemy_bonus = 0
        if t.owner != -1:
            enemy_produced = eta * t.production
            enemy_bonus = t.production
        total_ships = min_ships + enemy_produced
        return (100 - dist) + (15 * t.production) + (10 * enemy_bonus) - (0.7 * total_ships) - (2 * eta)

    def sun_collision_2(m, fleet_speed, angle, ticks=60):
        start_x, start_y = m.x, m.y
        min_dist = 100
        for tick in range(1, ticks):
            x = start_x + math.cos(angle) * fleet_speed * tick
            y = start_y + math.sin(angle) * fleet_speed * tick
            dist_to_sun = math.sqrt((x - 50)**2 + (y - 50)**2)
            if dist_to_sun <= 10:
                return True
        return False

    def get_planet_trajectories_2(p, vel):
        planet_trajectories = []
        angle = math.atan2(p.y - 50, p.x - 50)
        r = math.sqrt((p.x - 50)**2 + (p.y - 50)**2)
        for t in range(60):
            angle_t = angle + vel * t
            x_t = 50 + r * math.cos(angle_t)
            y_t = 50 + r * math.sin(angle_t)
            planet_trajectories.append((x_t, y_t))
        return planet_trajectories

    def calculate_req_ships_moving_2(attacking_planets, t, base_ships, vel):
        required_ships = base_ships
        planet_trajectories = get_planet_trajectories_2(t, vel)
        for _ in range(3):
            remainder = required_ships
            max_tick = 0
            for a_p in attacking_planets:
                p = a_p["planet"]
                p_ships = min(a_p["ships"], remainder)
                if p_ships > 0:
                    p_ships = min(a_p["ships"], max(p_ships, MIN_SHIPS_MINE_ATTACK))
                if p_ships <= 0:
                    continue
                fleet_speed = 1.0 + (MAX_SPEED - 1.0) * (math.log(max(1, p_ships)) / math.log(1000)) ** 1.5
                found_tick = 0
                for tick, (tx, ty) in enumerate(planet_trajectories[1:], start=1):
                    dist = math.sqrt((p.x - tx)**2 + (p.y - ty)**2)
                    turns_to_arrive = math.floor(dist / fleet_speed)
                    if abs(turns_to_arrive - tick) <= 1:
                        found_tick = tick
                        break
                if found_tick > max_tick:
                    max_tick = found_tick
                remainder -= p_ships
            new_req = base_ships + (max_tick * t.production)
            if new_req == required_ships:
                break
            required_ships = new_req
        return required_ships

    def calculate_req_ships_2(attacking_planets, t, base_ships):
        required_ships = base_ships
        for _ in range(3):
            remainder = required_ships
            max_tick = 0
            for a_p in attacking_planets:
                p = a_p["planet"]
                p_ships = min(a_p["ships"], remainder)
                if p_ships > 0:
                    p_ships = min(a_p["ships"], max(p_ships, MIN_SHIPS_MINE_ATTACK))
                if p_ships <= 0:
                    continue
                ships_for_speed = max(1, p_ships)
                fleet_speed = 1.0 + (MAX_SPEED - 1.0) * (math.log(ships_for_speed) / math.log(1000)) ** 1.5
                dist = math.sqrt((p.x - t.x)**2 + (p.y - t.y)**2)
                tick_arrival = math.floor(dist / fleet_speed)
                if tick_arrival > max_tick:
                    max_tick = tick_arrival
                remainder -= p_ships
            new_req = base_ships + (max_tick * t.production)
            if new_req == required_ships:
                break
            required_ships = new_req
        return required_ships

    def calculate_angle_2(m, t):
        return math.atan2(t.y - m.y, t.x - m.x)

    def get_closest_planets_to_target_2(mine, t):
        planets = []
        for m in mine:
            dist = math.sqrt((m.x - t.x)**2 + (m.y - t.y)**2)
            planets.append((m, dist))
        planets = sorted(planets, key=lambda k: k[1])
        return planets

    def refresh_local_obs_2(obs):
        planets = [ow.Planet(*p) for p in obs.get("planets", [])]
        mine = [p for p in planets if p.owner == obs.get("player", [])]
        targets = [p for p in planets if p.owner != obs.get("player", [])]
        player = obs.get("player", [])
        fleets = [ow.Fleet(*f) for f in obs.get("fleets", [])]
        return {"planets": planets, "mine": mine, "targets": targets, "player": player, "fleets": fleets}

    def optimize_targets_2(mine, targets):
        temp = []
        for m in mine:
            for t in targets:
                score = get_custom_score_2(m, t)
                temp.append((m, t, score))
        return sorted(temp, key=lambda t: t[2], reverse=True)

    def update_fleet_trajectories_2(fleets):
        for f_t in _fleet_trajectories[:]:
            found = False
            for f in fleets:
                if f.from_planet_id == f_t["mine"].id and abs(f.angle - f_t["angle"]) < 1e-6:
                    found = True
                    break
            if not found:
                _fleet_trajectories.remove(f_t)

    def fill_moving_planets_2(obs):
        planets = [ow.Planet(*p) for p in obs.get("planets", [])]
        initial_by_id = {i[0]: ow.Planet(*i) for i in obs.get("initial_planets", [])}
        for p in planets:
            i = initial_by_id[p.id]
            if (p.x, p.y) != (i.x, i.y):
                if p.id not in _moving_planets:
                    _moving_planets.append(p.id)

    # ── сам агент ────────────────────────────────────────────────────
    def agent_2(obs):
        if _steps[0] < 2:
            _steps[0] += 1
            return []
        if _steps[0] == 2:
            fill_moving_planets_2(obs)
            _steps[0] = 3

        lobs = refresh_local_obs_2(obs)
        update_fleet_trajectories_2(lobs.get("fleets", []))
        optimal_targets = optimize_targets_2(lobs.get("mine", []), lobs.get("targets", []))
        comet_planet_ids = obs.get("comet_planet_ids", [])

        if not lobs.get("targets", []):
            return []

        moves = []
        for m, t, s in optimal_targets[:10]:
            if m.ships < MIN_SHIPS_MINE_ATTACK:
                continue
            if t.id in comet_planet_ids:
                continue

            nearest_planets = get_closest_planets_to_target_2(lobs.get("mine", []), t)
            for row in nearest_planets:
                p, _ = row
                if p.id == m.id:
                    nearest_planets.remove(row)
                    break

            owned_count = len(lobs.get("mine", []))
            total_count = len(lobs.get("planets", []))

            en_route = 0
            if _fleet_trajectories:
                en_route = sum(
                    f["total_ships"]
                    for f in _fleet_trajectories
                    if f["target"].id == t.id
                )

            needed_now = t.ships + 1
            if t.owner != -1:
                needed_now += 3 * t.production

            if owned_count < total_count * 0.75:
                if en_route >= needed_now:
                    continue

            base_ships = max(10, needed_now - en_route)
            extra_ships = 0
            fleet_speed = 0
            angle = None

            if m.ships >= base_ships:
                if t.id in _moving_planets:
                    planet_trajectories = get_planet_trajectories_2(t, obs.angular_velocity)
                    for tick, (px, py) in enumerate(planet_trajectories[1:], start=1):
                        if t.owner != -1:
                            extra_ships = tick * t.production
                        if base_ships + extra_ships > m.ships:
                            continue
                        fleet_speed = 1.0 + (MAX_SPEED - 1.0) * (math.log(base_ships + extra_ships) / math.log(1000)) ** 1.5
                        angle_t = math.atan2(py - m.y, px - m.x)
                        dist = math.sqrt((px - m.x)**2 + (py - m.y)**2)
                        turns_to_arrive = math.floor(dist / fleet_speed)
                        if abs(turns_to_arrive - tick) > COLLIDE_TICK_THOLD:
                            continue
                        collides_sun = sun_collision_2(m, fleet_speed=fleet_speed, angle=angle_t)
                        if collides_sun:
                            continue
                        angle = angle_t
                        break
                else:
                    angle = calculate_angle_2(m, t)
                    if t.owner != -1:
                        dist = math.sqrt((t.x - m.x)**2 + (t.y - m.y)**2)
                        fleet_speed = 1.0 + (MAX_SPEED - 1.0) * (math.log(base_ships) / math.log(1000)) ** 1.5
                        turns_to_arrive = math.floor(dist / fleet_speed)
                        extra_ships = turns_to_arrive * t.production
                        total_ships = base_ships + extra_ships
                        fleet_speed = 1.0 + (MAX_SPEED - 1.0) * (math.log(total_ships) / math.log(1000)) ** 1.5
                        turns_to_arrive = math.floor(dist / fleet_speed)
                        extra_ships = turns_to_arrive * t.production

                if angle is not None:
                    total_ships = base_ships + extra_ships
                    fleet_speed = 1.0 + (MAX_SPEED - 1.0) * (math.log(max(1, total_ships)) / math.log(1000)) ** 1.5
                    collides_sun = sun_collision_2(m, fleet_speed=fleet_speed, angle=angle)
                    if collides_sun:
                        continue
                    moves.append([m.id, angle, total_ships])
                    _fleet_trajectories.append({
                        "mine": m, "target": t, "angle": angle, "total_ships": total_ships
                    })

            elif m.ships < base_ships and len(lobs.get("mine", [])) > 1 and t.ships >= MIN_SHIPS_TARGET_COOP_ATTACK:
                accum = m.ships
                attacking_planets = [{"planet": m, "ships": m.ships}]
                for p, dist in nearest_planets:
                    if p.id == m.id or p.ships < MIN_SHIPS_MINE_ATTACK:
                        continue
                    attacking_planets.append({"planet": p, "ships": p.ships})
                    accum += p.ships
                    if len(attacking_planets) > COOP_PLANET_CAP:
                        break
                    if accum < base_ships:
                        continue
                    attacking_planets = sorted(attacking_planets, key=lambda x: x["ships"])
                    if t.id not in _moving_planets:
                        if t.owner == -1:
                            remainder = base_ships
                            planned = []
                            for a_p in attacking_planets:
                                p = a_p["planet"]
                                p_ships = min(a_p["ships"], remainder)
                                if p_ships > 0:
                                    p_ships = min(a_p["ships"], max(p_ships, MIN_SHIPS_MINE_ATTACK))
                                if p_ships <= 0:
                                    continue
                                angle = calculate_angle_2(p, t)
                                fleet_speed = 1.0 + (MAX_SPEED - 1.0) * (math.log(p_ships) / math.log(1000)) ** 1.5
                                collides_sun = sun_collision_2(p, fleet_speed=fleet_speed, angle=angle)
                                if collides_sun:
                                    break
                                remainder -= p_ships
                                planned.append([p, angle, p_ships])
                            if remainder > 0:
                                continue
                            for move in planned:
                                _fleet_trajectories.append({"mine": move[0], "target": t, "angle": move[1], "total_ships": move[2]})
                                move[0] = move[0].id
                                moves.append(move)
                        else:
                            required_ships = calculate_req_ships_2(attacking_planets, t, base_ships)
                            remainder = required_ships
                            if accum < required_ships:
                                continue
                            planned = []
                            for a_p in attacking_planets:
                                p = a_p["planet"]
                                p_ships = min(a_p["ships"], remainder)
                                if p_ships > 0:
                                    p_ships = min(a_p["ships"], max(p_ships, MIN_SHIPS_MINE_ATTACK))
                                if p_ships <= 0:
                                    continue
                                angle = calculate_angle_2(p, t)
                                fleet_speed = 1.0 + (MAX_SPEED - 1.0) * (math.log(p_ships) / math.log(1000)) ** 1.5
                                collides_sun = sun_collision_2(p, fleet_speed=fleet_speed, angle=angle)
                                if collides_sun:
                                    continue
                                remainder -= p_ships
                                planned.append([p, angle, p_ships])
                            if remainder > 0:
                                continue
                            for move in planned:
                                _fleet_trajectories.append({"mine": move[0], "target": t, "angle": move[1], "total_ships": move[2]})
                                move[0] = move[0].id
                                moves.append(move)
                    else:
                        planet_trajectories = get_planet_trajectories_2(t, obs.angular_velocity)
                        if t.owner == -1:
                            remainder = base_ships
                            planned = []
                            for a_p in attacking_planets:
                                p = a_p["planet"]
                                p_ships = min(a_p["ships"], remainder)
                                if p_ships > 0:
                                    p_ships = min(a_p["ships"], max(p_ships, MIN_SHIPS_MINE_ATTACK))
                                if p_ships <= 0:
                                    continue
                                angle = None
                                for tick, (tx, ty) in enumerate(planet_trajectories[1:], start=1):
                                    fleet_speed = 1.0 + (MAX_SPEED - 1.0) * (math.log(p_ships) / math.log(1000)) ** 1.5
                                    angle_t = math.atan2(ty - p.y, tx - p.x)
                                    dist = math.sqrt((tx - p.x)**2 + (ty - p.y)**2)
                                    turns_to_arrive = math.floor(dist / fleet_speed)
                                    if abs(turns_to_arrive - tick) > COLLIDE_TICK_THOLD:
                                        continue
                                    collides_sun = sun_collision_2(p, fleet_speed=fleet_speed, angle=angle_t)
                                    if collides_sun:
                                        continue
                                    angle = angle_t
                                    break
                                if angle is None:
                                    continue
                                planned.append([p, angle_t, p_ships])
                                remainder -= p_ships
                            if remainder > 0:
                                continue
                            for move in planned:
                                _fleet_trajectories.append({"mine": move[0], "target": t, "angle": move[1], "total_ships": move[2]})
                                move[0] = move[0].id
                                moves.append(move)
                        else:
                            required_ships = calculate_req_ships_moving_2(attacking_planets, t, base_ships, obs.angular_velocity)
                            remainder = required_ships
                            planned = []
                            if accum < required_ships:
                                continue
                            for a_p in attacking_planets:
                                p = a_p["planet"]
                                p_ships = min(a_p["ships"], remainder)
                                if p_ships > 0:
                                    p_ships = min(a_p["ships"], max(p_ships, MIN_SHIPS_MINE_ATTACK))
                                if p_ships <= 0:
                                    continue
                                fleet_speed = 1.0 + (MAX_SPEED - 1.0) * (math.log(max(1, p_ships)) / math.log(1000)) ** 1.5
                                angle = None
                                for tick, (tx, ty) in enumerate(planet_trajectories[1:], start=1):
                                    angle_t = math.atan2(ty - p.y, tx - p.x)
                                    dist = math.sqrt((p.x - tx)**2 + (p.y - ty)**2)
                                    turns_to_arrive = math.floor(dist / fleet_speed)
                                    if abs(turns_to_arrive - tick) > COLLIDE_TICK_THOLD:
                                        continue
                                    collides_sun = sun_collision_2(p, fleet_speed=fleet_speed, angle=angle_t)
                                    if collides_sun:
                                        continue
                                    angle = angle_t
                                    break
                                if angle is None:
                                    continue
                                remainder -= p_ships
                                planned.append([p, angle, p_ships])
                            if remainder > 0:
                                continue
                            for move in planned:
                                _fleet_trajectories.append({"mine": move[0], "target": t, "angle": move[1], "total_ships": move[2]})
                                move[0] = move[0].id
                                moves.append(move)
        return moves

    # сброс внутреннего состояния при пересоздании
    def reset():
        _fleet_trajectories.clear()
        _moving_planets.clear()
        _steps[0] = 0

    agent_2.reset = reset
    return agent_2


# ══════════════════════════════════════════════════════════════════════
#  ОСНОВНОЙ ЦИКЛ ПЕРЕБОРА ПАРАМЕТРОВ
# ══════════════════════════════════════════════════════════════════════

# Загрузите strong_agent (путь к вашему файлу или имя агента)
# Например: strong_agent = "orbit_wars/strong_agent"
# Или из файла:  exec(open("strong_agent.py").read()); strong_agent = strong_agent_func
strong_agent = "/content/main.py"  # ← замените на актуальное имя/функцию

NUM_GAMES   = 100
results     = {}   # ключ — кортёж параметров, значение — winrate

# Генерируем все комбинации (3^4 = 81)
keys = list(param_grid.keys())
value_lists = list(param_grid.values())
total_combos = 1
for vl in value_lists:
    total_combos *= len(vl)

print(f"Всего комбинаций: {total_combos}")
print(f"Игр на комбинацию: {NUM_GAMES}")
print(f"Всего игр: {total_combos * NUM_GAMES}")
print("=" * 60)

combo_idx = 0
for combo in itertools.product(*value_lists):
    combo_idx += 1
    params = dict(zip(keys, combo))
    params_key = tuple(combo)  # хешируемый ключ для словаря

    # Создаём agent_2 с текущими параметрами
    agent_2 = make_agent_2(
        MIN_SHIPS_MINE_ATTACK       =params["MIN_SHIPS_MINE_ATTACK"],
        MIN_SHIPS_TARGET_COOP_ATTACK=params["MIN_SHIPS_TARGET_COOP_ATTACK"],
        COOP_PLANET_CAP             =params["COOP_PLANET_CAP"],
        COLLIDE_TICK_THOLD          =params["COLLIDE_TICK_THOLD"],
    )
    agent_1 = make_agent_2(10, 20, 8, 1)

    winrate_agent_2 = 0

    for game_i in range(NUM_GAMES):
        # Сброс внутреннего состояния агента перед каждой игрой
        agent_2.reset()

        env = make("orbit_wars", debug=True)
        env.run([strong_agent, agent_2])

        final = env.steps[-1]
        # agent_2 — второй игрок (индекс 1)
        if final[1].reward == 1:
            winrate_agent_2 += 1

    winrate_agent_2 /= NUM_GAMES
    results[params_key] = winrate_agent_2

    print(f"[{combo_idx}/{total_combos}]  "
          f"MIN_SHIPS_MINE={params['MIN_SHIPS_MINE_ATTACK']}, "
          f"MIN_COOP={params['MIN_SHIPS_TARGET_COOP_ATTACK']}, "
          f"COOP_CAP={params['COOP_PLANET_CAP']}, "
          f"COLLIDE_THOLD={params['COLLIDE_TICK_THOLD']}  →  "
          f"winrate={winrate_agent_2:.2f}")

# ── Топ-5 по убыванию winrate ────────────────────────────────────────
print("\n" + "=" * 60)
print("ТОП-5 ЛУЧШИХ КОМБИНАЦИЙ ПАРАМЕТРОВ")
print("=" * 60)

sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)[:5]

for rank, (params_key, wr) in enumerate(sorted_results, 1):
    print(f"\n#{rank}  winrate = {wr:.2f}")
    print(f"    MIN_SHIPS_MINE_ATTACK        = {params_key[0]}")
    print(f"    MIN_SHIPS_TARGET_COOP_ATTACK = {params_key[1]}")
    print(f"    COOP_PLANET_CAP              = {params_key[2]}")
    print(f"    COLLIDE_TICK_THOLD           = {params_key[3]}")
```
