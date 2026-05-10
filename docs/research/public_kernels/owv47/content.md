## [CODE]
```python
# Cell 0: Path Setup
import os

# Define paths directly—no need for kagglehub
orbit_wars_path = "/kaggle/input/competitions/orbit-wars/"
zacharymaronek_neural_ow_agent_training_path = "/kaggle/input/datasets/zacharymaronek/neural-ow-agent-training"

print("Data paths set.")
```

## [CODE]
```python
import kagglehub

# Force download the latest version of the dataset
zacharymaronek_neural_ow_agent_training_path = kagglehub.dataset_download(
    'zacharymaronek/neural-ow-agent-training',
    force_download=True
)

print(f'Updated dataset path: {zacharymaronek_neural_ow_agent_training_path}')
```

## [CODE]
```python
!pip install -e /kaggle/input/competitions/orbit-wars
```

## [MD]
# v47: Curriculum Self-Play RL Agent

## Curriculum Levels (7 levels)
1. **random** - baseline random bot
2. **charybdis** - analytical orbital agent
3. **elite** - competitive v3 agent
4. **simple** - nearest-neighbor heuristic
5. **v34** - strategic expander
6. **v40** - meta crusher
7. **self-play** - against best model so far

Win 85%+ at each level to advance!

## [CODE]
```python
# Cell 1: Imports
import os
os.environ['KAGGLE_ENVELOPES'] = '0'

import torch
import numpy as np
import math
from collections import deque
import random
from copy import deepcopy
import sys

# Updated to point to the newly extracted charybdis source path
sys.path.insert(0, '/content/agents/charybdis/src')

torch.set_float32_matmul_precision('high')
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Device: {DEVICE}")
```

## [CODE]
```python
from kaggle_environments import make, register

def create_env(seed=None):
    # 1. Register the environment directly.
    # If it's already registered, this will generally handle it gracefully
    # or you can wrap it in a try-except block if needed.
    try:
        register("orbit_wars", ENV_PATH)
    except Exception as e:
        # If it's already registered, you might see an error here,
        # which is fine to ignore if you just want to ensure it exists.
        pass

    # 2. Now create the environment
    env = make("orbit_wars", debug=False)
    if seed is not None:
        env.configuration.seed = seed
    return env
```

## [CODE]
```python
!pip install jsonschema==4.17.3

# Note: You may need to restart the runtime (Runtime -> Restart session)
# after installing this for the changes to take effect properly.
```

## [CODE]
```python
# Cell 3: All Agent Definitions

def fleet_speed(ships: int) -> float:
    if ships <= 0:
        return 1.0
    return 1.0 + (MAX_SPEED - 1.0) * (math.log(max(ships, 1)) / math.log(1000)) ** 1.5

def travel_time(x1: float, y1: float, x2: float, y2: float, ships: int) -> float:
    dist = math.hypot(x2 - x1, y2 - y1)
    return dist / fleet_speed(ships) if ships > 0 else 999.0

def line_seg_min_dist(x1: float, y1: float, x2: float, y2: float, px: float, py: float) -> float:
    dx, dy = x2 - x1, y2 - y1
    len_sq = dx * dx + dy * dy
    if len_sq == 0:
        return math.hypot(x1 - px, y1 - py)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / len_sq))
    return math.hypot(x1 + t * dx - px, y1 + t * dy - py)

def path_crosses_sun(x1: float, y1: float, x2: float, y2: float, margin: float = 1.5) -> bool:
    return line_seg_min_dist(x1, y1, x2, y2, SUN_X, SUN_Y) < SUN_RADIUS + margin

def safe_angle(x1: float, y1: float, x2: float, y2: float, margin: float = 1.5) -> float:
    direct = math.atan2(y2 - y1, x2 - x1)
    if not path_crosses_sun(x1, y1, x2, y2, margin=margin):
        return direct
    d = math.hypot(x1 - SUN_X, y1 - SUN_Y)
    if d <= SUN_RADIUS + 1.0:
        return direct
    half = math.asin(min(1.0, (SUN_RADIUS + 1.0) / d))
    to_sun = math.atan2(SUN_Y - y1, SUN_X - x1)
    cw = to_sun + half
    ccw = to_sun - half
    def adiff(a):
        dd = (a - direct) % (2 * math.pi)
        return min(dd, 2 * math.pi - dd)
    return cw if adiff(cw) < adiff(ccw) else ccw

def predict_orbit(x: float, y: float, omega: float, dt: float):
    theta = math.atan2(y - SUN_Y, x - SUN_X)
    r = math.hypot(x - SUN_X, y - SUN_Y)
    return SUN_X + r * math.cos(theta + omega * dt), SUN_Y + r * math.sin(theta + omega * dt)

def solve_intercept(fx: float, fy: float, tx: float, ty: float, orbiting: bool, omega: float, ships: int, iterations: int = 25):
    if not orbiting:
        t = travel_time(fx, fy, tx, ty, ships)
        return tx, ty, t
    t = travel_time(fx, fy, tx, ty, ships)
    ix, iy = tx, ty
    for _ in range(iterations):
        ix, iy = predict_orbit(tx, ty, omega, t)
        t2 = travel_time(fx, fy, ix, iy, ships)
        if abs(t2 - t) < 0.05:
            break
        t = t2
    return ix, iy, t

def simple_agent(obs):
    player = obs.get('player', 0) if isinstance(obs, dict) else getattr(obs, 'player', 0)
    planets_data = obs.get('planets', []) if isinstance(obs, dict) else getattr(obs, 'planets', [])
    my_planets = [p for p in planets_data if p[1] == player]
    if not my_planets:
        return []
    targets = [p for p in planets_data if p[1] != player]
    if not targets:
        return []
    moves = []
    for mine in my_planets:
        if mine[5] < 15:
            continue
        nearest = min(targets, key=lambda t: math.hypot(mine[2] - t[2], mine[3] - t[3]))
        angle = safe_angle(mine[2], mine[3], nearest[2], nearest[3])
        send = min(int(mine[5] * 0.5), 30)
        if send >= 5:
            moves.append([mine[0], angle, send])
    return moves

print("Simple agent defined")
```

## [CODE]
```python
import os

zip_path = '/content/v47.zip'
extract_dir = '/content/agents'

if os.path.exists(zip_path):
    !unzip -o {zip_path} -d {extract_dir}
    print(f"\nSuccessfully extracted to {extract_dir}")
else:
    print(f"Warning: {zip_path} not found. Please upload it to the /content/ directory.")
```

## [CODE]
```python
# Cell 4: Load Other Agents (v34, v40, elite, charybdis)

def load_agent_from_file(filepath, func_name='agent'):
    import importlib.util
    import os
    if not os.path.exists(filepath):
        print(f"Warning: Could not find agent file at {filepath}. Using simple_agent as fallback.")
        return simple_agent
    spec = importlib.util.spec_from_file_location("agent_module", filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules["agent_module"] = module
    spec.loader.exec_module(module)
    return getattr(module, func_name)

import os
# Updated to use the extracted agents folder
base_path = '/kaggle/input/datasets/zacharymaronek/neural-ow-agent-training'

print("Loading v34...")
v34_agent = load_agent_from_file(os.path.join(base_path, 'main_v34.py'))

print("Loading v40...")
v40_agent = load_agent_from_file(os.path.join(base_path, 'main_v40.py'))

print("Loading elite...")
elite_agent = load_agent_from_file(os.path.join(base_path, 'main_elite.py'))

print("Loading charybdis...")
try:
    from charybdis import agent as charybdis_agent_raw
    charybdis_state = {'step': 0, 'my_id': None, 'omega': 0.03, 'initial_planets': {}, 'vulture_cooldowns': {}}

    def charybdis_agent(obs):
        global charybdis_state
        charybdis_state['step'] += 1
        if charybdis_state['my_id'] is None:
            charybdis_state['my_id'] = obs.get('player', 0)
            charybdis_state['omega'] = obs.get('angular_velocity', 0.03)
            for p in obs.get('initial_planets', []):
                charybdis_state['initial_planets'][p[0]] = p
        return charybdis_agent_raw(obs, {}, charybdis_state)
except ImportError:
    print("Warning: charybdis module not found. Using simple_agent as fallback.")
    charybdis_agent = simple_agent

print("Agent loading process complete (check warnings for missing files).")
```

## [CODE]
```python
# Cell 5: v45 Agent (baseline teacher)

def v45_agent(obs):
    if isinstance(obs, dict):
        player = obs.get('player', 0)
        planets_data = obs.get('planets', [])
        fleets_data = obs.get('fleets', [])
        omega = obs.get('angular_velocity', 0.03)
    else:
        player = getattr(obs, 'player', 0)
        planets_data = getattr(obs, 'planets', [])
        fleets_data = getattr(obs, 'fleets', [])
        omega = getattr(obs, 'angular_velocity', 0.03)

    planets = {}
    for p in planets_data:
        pid, owner, x, y, radius, ships, prod = p[:7]
        r = math.hypot(x - SUN_X, y - SUN_Y)
        planets[pid] = {'id': pid, 'owner': owner, 'x': x, 'y': y,
            'radius': radius, 'ships': float(ships), 'prod': float(prod),
            'is_orb': (r + radius) < 48.0}

    fleets = {}
    for f in fleets_data:
        fleets[f[0]] = {'id': f[0], 'owner': f[1], 'x': f[2], 'y': f[3],
            'angle': f[4], 'from': f[5], 'ships': float(f[6])}

    my = [p for p in planets.values() if p['owner'] == player]
    if not my:
        return []

    enemy = [p for p in planets.values() if p['owner'] != player and p['owner'] != -1]
    neutrals = [p for p in planets.values() if p['owner'] == -1]

    my_prod = sum(p['prod'] for p in my)
    my_ships = sum(p['ships'] for p in my)
    enemy_prod = sum(p['prod'] for p in enemy) if enemy else 0
    enemy_ships = sum(p['ships'] for p in enemy) if enemy else 0

    prod_ratio = my_prod / enemy_prod if enemy_prod > 0 else 999
    ship_ratio = my_ships / enemy_ships if enemy_ships > 0 else 999

    my_planet_count = len(my)
    neighbor_count = sum(1 for t in neutrals if any(math.hypot(t['x'] - p['x'], t['y'] - p['y']) < 35 for p in my))

    nearby_larger_planets = []
    for src in my:
        for t in (neutrals + enemy):
            d = math.hypot(t['x'] - src['x'], t['y'] - src['y'])
            if d < 40 and t['prod'] >= src['prod'] * 0.8 and t['radius'] >= src['radius'] * 0.8:
                nearby_larger_planets.append((src['id'], t['id'], d))

    in_flight_from = set()
    in_flight_to = set()
    for f in fleets.values():
        if f['owner'] == player and f['from'] is not None:
            in_flight_from.add(f['from'])
            best_tgt, best_d = None, float('inf')
            for p in planets.values():
                if p['id'] == f['from']:
                    continue
                d = math.hypot(f['x'] - p['x'], f['y'] - p['y'])
                if d < best_d:
                    best_d = d
                    best_tgt = p['id']
            if best_tgt:
                in_flight_to.add(best_tgt)

    threats = {}
    for f in fleets.values():
        if f['owner'] == player:
            continue
        best_tgt, best_d = None, float('inf')
        for p in planets.values():
            if p['owner'] != player:
                continue
            d = math.hypot(f['x'] - p['x'], f['y'] - p['y'])
            if d < best_d:
                best_d = d
                best_tgt = p['id']
        if best_tgt:
            threats[best_tgt] = threats.get(best_tgt, 0) + f['ships']

    smash_targets = set()
    for e in enemy:
        nearby_my_ships = sum(p['ships'] for p in my if math.hypot(p['x'] - e['x'], p['y'] - e['y']) < 50)
        if nearby_my_ships > e['ships'] * 1.3:
            smash_targets.add(e['id'])

    if smash_targets:
        phase = 'smash'
    elif my_ships > 150 and my_planet_count < 4 and enemy:
        phase = 'rush'
    elif my_planet_count < 3 or (neighbor_count > 0 and my_planet_count < 5):
        phase = 'expand'
    elif threats and any(t > my_ships * 0.4 for t in threats.values()):
        phase = 'counter_attack'
    elif prod_ratio > 5 and my_ships > 100 and my_planet_count >= 4:
        phase = 'crush'
    elif prod_ratio > 2.5 or ship_ratio > 3:
        phase = 'aggressive'
    elif my_prod < enemy_prod * 0.7:
        phase = 'defend'
    else:
        phase = 'grow'

    moves = []
    targeted_this_turn = set()

    for src in my:
        if src['id'] in in_flight_from or src['ships'] < 10:
            continue

        if phase == 'expand':
            nearby_larger = {nl[1] for nl in nearby_larger_planets if nl[0] == src['id']}
            best_target = None
            best_score = -1e9
            for t in neutrals:
                if t['id'] == src['id'] or t['id'] in in_flight_to or t['id'] in targeted_this_turn:
                    continue
                d = math.hypot(t['x'] - src['x'], t['y'] - src['y'])
                score = -d * 3 + t['prod'] * 3
                if nearby_larger and t['radius'] < src['radius'] * 0.7 and d > 25:
                    score -= 50
                if score > best_score:
                    best_score = score
                    best_target = t
            if best_target:
                r = math.hypot(best_target['x'] - SUN_X, best_target['y'] - SUN_Y)
                is_orbiting = (r + best_target['radius']) < 48.0
                ix, iy, tt = solve_intercept(src['x'], src['y'], best_target['x'], best_target['y'], is_orbiting, omega, int(src['ships']))
                if not path_crosses_sun(src['x'], src['y'], ix, iy, margin=1.5):
                    send = int(best_target['ships'] + 1)
                    if src['ships'] >= send:
                        angle = safe_angle(src['x'], src['y'], ix, iy)
                        moves.append([src['id'], angle, send])
                        targeted_this_turn.add(best_target['id'])
                        src['ships'] -= send
                        if src['ships'] < 5:
                            break

        need_defense = threats.get(src['id'], 0) > 0 and src['ships'] < threats.get(src['id'], 0) + 5
        if need_defense and phase != 'counter_attack':
            continue

        if phase == 'counter_attack':
            best_enemy = None
            best_score = -1e9
            for t in enemy:
                if t['id'] in targeted_this_turn:
                    continue
                d = math.hypot(t['x'] - src['x'], t['y'] - src['y'])
                score = t['ships'] * 0.5 + t['prod'] * 5 - d
                if score > best_score:
                    best_score = score
                    best_enemy = t
            if best_enemy:
                r = math.hypot(best_enemy['x'] - SUN_X, best_enemy['y'] - SUN_Y)
                is_orbiting = (r + best_enemy['radius']) < 48.0
                ix, iy, tt = solve_intercept(src['x'], src['y'], best_enemy['x'], best_enemy['y'], is_orbiting, omega, int(src['ships']))
                if not path_crosses_sun(src['x'], src['y'], ix, iy, margin=1.5):
                    send = int(src['ships'] * 0.7)
                    send = max(send, int(best_enemy['ships'] + 1))
                    send = min(send, int(src['ships'] * 0.9))
                    if src['ships'] > send + 5:
                        angle = safe_angle(src['x'], src['y'], ix, iy)
                        moves.append([src['id'], angle, send])
                        targeted_this_turn.add(best_enemy['id'])
                        src['ships'] -= send

        best_tgt = None
        best_score = -1e9

        if phase == 'smash':
            candidates = [t for t in enemy if t['id'] in smash_targets]
        elif phase == 'rush':
            candidates = enemy
        elif phase in ('expand', 'opportunistic', 'aggressive'):
            candidates = neutrals if phase != 'aggressive' else (enemy + neutrals)
        elif phase == 'grow':
            candidates = [t for t in neutrals if threats.get(t['id'], 0) == 0]
        else:
            candidates = []

        for t in candidates:
            if t['id'] == src['id'] or t['id'] in in_flight_to or t['id'] in targeted_this_turn:
                continue
            if threats.get(t['id'], 0) > 0:
                continue
            r = math.hypot(t['x'] - SUN_X, t['y'] - SUN_Y)
            is_orbiting = t['is_orb']
            ix, iy, tt = solve_intercept(src['x'], src['y'], t['x'], t['y'], is_orbiting, omega, int(src['ships']))
            if path_crosses_sun(src['x'], src['y'], ix, iy, margin=1.5):
                continue
            if is_orbiting:
                planet_future = predict_orbit(t['x'], t['y'], omega, tt)
                to_planet = math.atan2(planet_future[1] - src['y'], planet_future[0] - src['x'])
                to_target = math.atan2(t['y'] - src['y'], t['x'] - src['x'])
                diff = abs((to_planet - to_target) % (2 * math.pi))
                if diff > 0.5 and diff < (2 * math.pi - 0.5):
                    continue
            score = t['prod'] * 15 - tt * 3
            if t['owner'] == -1:
                score += 20
            if phase == 'aggressive' and t['owner'] != -1:
                score += 30 - t['ships'] * 0.15
            if is_orbiting:
                score -= 8
            if src['ships'] > 50 and t['owner'] == -1:
                score += 10
            if score > best_score:
                best_score = score
                best_tgt = (t, ix, iy)

        if best_tgt is None:
            continue

        tgt, ix, iy = best_tgt
        if phase == 'smash':
            send = int(src['ships'] * 0.85)
            send = max(send, int(tgt['ships'] * 1.2))
        elif phase == 'rush':
            send = int(src['ships'] * 0.8)
        elif phase == 'aggressive':
            send = int(src['ships'] * 0.4)
            send = max(send, int(tgt['ships'] * 1.1))
            send = min(send, int(src['ships'] * 0.7))
        else:
            send = int(tgt['ships'] + 1)

        if src['ships'] < send:
            continue
        angle = safe_angle(src['x'], src['y'], ix, iy)
        moves.append([src['id'], angle, send])
        targeted_this_turn.add(tgt['id'])

    return moves

print("v45 agent defined")
```

## [CODE]
```python
# Cell 6: State Encoding

class GameState:
    def __init__(self, obs, player=None):
        if player is None:
            player = obs.get('player', 0) if isinstance(obs, dict) else getattr(obs, 'player', 0)
        self.player = player
        raw_planets = obs.get('planets', []) if isinstance(obs, dict) else getattr(obs, 'planets', [])
        raw_fleets = obs.get('fleets', []) if isinstance(obs, dict) else getattr(obs, 'fleets', [])
        self.omega = obs.get('angular_velocity', OMEGA_DEFAULT) if isinstance(obs, dict) else getattr(obs, 'angular_velocity', OMEGA_DEFAULT)

        self.planets = []
        for p in raw_planets:
            r = math.hypot(p[2] - SUN_X, p[3] - SUN_Y)
            is_orb = (r + p[4]) < 48.0
            self.planets.append({'id': p[0], 'owner': p[1], 'x': p[2], 'y': p[3],
                'radius': p[4], 'ships': p[5], 'prod': p[6], 'is_orb': is_orb})

        self.fleets = []
        for f in raw_fleets:
            self.fleets.append({'id': f[0], 'owner': f[1], 'x': f[2], 'y': f[3],
                'angle': f[4], 'from': f[5], 'ships': f[6]})

        self.my_planets = [p for p in self.planets if p['owner'] == player]
        self.enemy_planets = [p for p in self.planets if p['owner'] != player and p['owner'] != -1]
        self.neutral_planets = [p for p in self.planets if p['owner'] == -1]
        self.all_targets = [p for p in self.planets if p['owner'] != player]

        self.my_ships = sum(p['ships'] for p in self.my_planets)
        self.enemy_ships = sum(p['ships'] for p in self.enemy_planets)
        self.my_prod = sum(p['prod'] for p in self.my_planets)
        self.enemy_prod = sum(p['prod'] for p in self.enemy_planets)

    def encode(self, max_planets=20, max_fleets=20):
        planet_feats = []
        for p in self.planets:
            feat = np.array([
                p['x'] / BOARD, p['y'] / BOARD,
                p['owner'] / 3.0,
                p['ships'] / 100.0,
                p['prod'] / 5.0,
                p['radius'] / 10.0,
                1.0 if p['is_orb'] else 0.0,
                self.omega / 0.1
            ], dtype=np.float32)
            planet_feats.append(feat)
        while len(planet_feats) < max_planets:
            planet_feats.append(np.zeros(8, dtype=np.float32))
        planet_feats = np.stack(planet_feats[:max_planets])

        fleet_feats = []
        for f in self.fleets:
            feat = np.array([
                f['x'] / BOARD, f['y'] / BOARD,
                f['owner'] / 3.0,
                f['ships'] / 50.0,
                math.cos(f['angle']), math.sin(f['angle']),
                1.0 if f['from'] is not None else 0.0
            ], dtype=np.float32)
            fleet_feats.append(feat)
        while len(fleet_feats) < max_fleets:
            fleet_feats.append(np.zeros(8, dtype=np.float32))
        fleet_feats = np.stack(fleet_feats[:max_fleets])

        global_feat = np.array([
            len(self.my_planets) / 10.0,
            len(self.enemy_planets) / 10.0,
            len(self.neutral_planets) / 10.0,
            self.my_ships / 200.0,
            self.enemy_ships / 200.0,
            self.my_prod / 20.0,
            self.enemy_prod / 20.0,
            self.omega / 0.1
        ], dtype=np.float32)

        return planet_feats, fleet_feats, global_feat

    def get_candidate_moves(self):
        moves = []
        for src in self.my_planets:
            for tgt in self.all_targets:
                src_idx = self.planets.index(src)
                tgt_idx = self.planets.index(tgt)
                moves.append({
                    'source_id': src['id'], 'target_id': tgt['id'],
                    'source_idx': src_idx, 'target_idx': tgt_idx,
                    'source_ships': src['ships'],
                    'target_ships': tgt['ships'],
                    'dist': math.hypot(src['x'] - tgt['x'], src['y'] - tgt['y']),
                    'crosses_sun': path_crosses_sun(src['x'], src['y'], tgt['x'], tgt['y'])
                })
        return moves

print("GameState ready")
```

## [CODE]
```python
# Cell 7: Neural Network

class ResBlock(torch.nn.Module):
    def __init__(self, d, dropout=0.1):
        super().__init__()
        self.ln = torch.nn.LayerNorm(d)
        self.net = torch.nn.Sequential(
            torch.nn.Linear(d, d * 4),
            torch.nn.GELU(),
            torch.nn.Dropout(dropout),
            torch.nn.Linear(d * 4, d),
            torch.nn.Dropout(dropout)
        )
    def forward(self, x):
        return x + self.net(self.ln(x))

class RLAgent(torch.nn.Module):
    def __init__(self, d_model=128, num_res_blocks=3):
        super().__init__()
        self.d_model = d_model

        self.planet_encoder = torch.nn.Sequential(
            torch.nn.Linear(8, d_model),
            torch.nn.GELU(),
            torch.nn.Linear(d_model, d_model)
        )
        self.fleet_encoder = torch.nn.Sequential(
            torch.nn.Linear(8, d_model),
            torch.nn.GELU(),
            torch.nn.Linear(d_model, d_model)
        )
        self.global_encoder = torch.nn.Sequential(
            torch.nn.Linear(8, d_model // 2),
            torch.nn.GELU(),
            torch.nn.Linear(d_model // 2, d_model // 2)
        )
        self.res_blocks = torch.nn.ModuleList([ResBlock(d_model) for _ in range(num_res_blocks)])

        self.policy_head = torch.nn.Sequential(
            torch.nn.Linear(d_model * 2 + d_model // 2, d_model),
            torch.nn.LayerNorm(d_model),
            torch.nn.GELU(),
            torch.nn.Linear(d_model, 1)
        )
        self.value_head = torch.nn.Sequential(
            torch.nn.Linear(d_model + d_model // 2, d_model),
            torch.nn.LayerNorm(d_model),
            torch.nn.GELU(),
            torch.nn.Linear(d_model, 1)
        )

        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, torch.nn.Linear):
            torch.nn.init.orthogonal_(m.weight, gain=1.414)
            if m.bias is not None:
                torch.nn.init.zeros_(m.bias)

    def encode(self, planet_feats, fleet_feats, global_feat):
        planet_enc = self.planet_encoder(planet_feats)
        fleet_enc = self.fleet_encoder(fleet_feats)
        global_enc = self.global_encoder(global_feat)

        planet_mask = planet_feats.abs().sum(dim=1) > 0
        fleet_mask = fleet_feats.abs().sum(dim=1) > 0
        planet_pool = planet_enc[planet_mask].mean(dim=0) if planet_mask.sum() > 0 else torch.zeros(self.d_model, device=planet_feats.device)
        fleet_pool = fleet_enc[fleet_mask].mean(dim=0) if fleet_mask.sum() > 0 else torch.zeros(self.d_model, device=fleet_feats.device)

        ctx = torch.cat([planet_pool, fleet_pool, global_enc], dim=-1)
        return planet_enc, fleet_enc, ctx

    def get_logits_and_value(self, planet_feats, fleet_feats, global_feat, move_indices=None):
        planet_enc, fleet_enc, ctx = self.encode(planet_feats, fleet_feats, global_feat)

        for block in self.res_blocks:
            planet_enc = block(planet_enc)

        planet_mask = planet_feats.abs().sum(dim=1) > 0
        planet_pool = planet_enc[planet_mask].mean(dim=0) if planet_mask.sum() > 0 else torch.zeros(self.d_model, device=planet_feats.device)

        value = self.value_head(torch.cat([planet_pool, ctx], dim=-1)).squeeze(-1)

        if move_indices is None:
            return None, value

        src_idx = move_indices[:, 0]
        tgt_idx = move_indices[:, 1]
        batch_size = src_idx.shape[0]

        src_enc = planet_enc[src_idx]
        tgt_enc = planet_enc[tgt_idx]

        move_ctx = torch.cat([src_enc, tgt_enc], dim=-1)
        full_ctx = torch.cat([move_ctx, ctx.expand(batch_size, -1)], dim=-1)

        logits = self.policy_head(full_ctx).squeeze(-1)
        return logits, value

    def get_value(self, planet_feats, fleet_feats, global_feat):
        _, value = self.get_logits_and_value(planet_feats, fleet_feats, global_feat, None)
        return value

model = RLAgent().to(DEVICE)
target_model = RLAgent().to(DEVICE)
target_model.load_state_dict(model.state_dict())
print(f"Model params: {sum(p.numel() for p in model.parameters()):,}")
```

## [CODE]
```python
# Cell 8: Inference Agent

class InferenceAgent:
    def __init__(self, model, epsilon=0.0, use_fallback=True):
        self.model = model
        self.epsilon = epsilon
        self.use_fallback = use_fallback

    def __call__(self, obs):
        return self.agent_fn(obs)

    def agent_fn(self, obs):
        gs = GameState(obs)
        if not gs.my_planets:
            return v45_agent(obs) if self.use_fallback else []

        planet_feats, fleet_feats, global_feat = gs.encode()
        planet_t = torch.from_numpy(planet_feats).to(DEVICE)
        fleet_t = torch.from_numpy(fleet_feats).to(DEVICE)
        global_t = torch.from_numpy(global_feat).to(DEVICE)

        moves = gs.get_candidate_moves()
        if not moves:
            return v45_agent(obs) if self.use_fallback else []

        move_indices = torch.tensor([[m['source_idx'], m['target_idx']] for m in moves], dtype=torch.long, device=DEVICE)

        with torch.no_grad():
            logits, _ = self.model.get_logits_and_value(planet_t, fleet_t, global_t, move_indices)
            probs = torch.softmax(logits, dim=0)

        if random.random() < self.epsilon:
            idx = random.randrange(len(moves))
        else:
            idx = torch.argmax(probs).item()

        best_move = moves[idx]
        src_planet = gs.my_planets[[p['id'] for p in gs.my_planets].index(best_move['source_id'])]
        tgt_planet = gs.planets[best_move['target_idx']]

        send = max(5, int(src_planet['ships'] * 0.5))
        send = min(send, int(src_planet['ships'] - 3))
        send = max(send, int(tgt_planet['ships'] + 1))

        angle = safe_angle(src_planet['x'], src_planet['y'], tgt_planet['x'], tgt_planet['y'])

        return [[best_move['source_id'], angle, send]]

print("Inference agent ready")
```

## [CODE]
```python
# Cell 9: Curriculum Training Setup
OPPONENTS = {'random': 'random', 'charybdis': charybdis_agent, 'elite': elite_agent, 'simple': simple_agent, 'v34': v34_agent, 'v40': v40_agent, 'selfplay': None}
CURRICULUM_LEVELS = ['random', 'charybdis', 'elite', 'simple', 'v34', 'v40', 'selfplay']
WIN_THRESHOLD = 0.85
EVAL_GAMES = 20
EPISODES_PER_ROUND = 50
BATCH_SIZE = 32
UPDATES_PER_ROUND = 30

replay = deque(maxlen=50000)
optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.01)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=3000)

def collect_episode(nn_agent, opponent_fn, epsilon=0.1, seed=None):
    env = create_env(seed)
    def wrap_nn(obs): return nn_agent(obs)

    if isinstance(opponent_fn, str):
        opp = opponent_fn
    else:
        def wrap_opp(obs): return opponent_fn(obs)
        opp = wrap_opp

    # Removed try...except block to allow errors to surface
    results = env.run([wrap_nn, opp])

    final = results[-1]
    p0 = getattr(final[0], 'reward', 0) or 0
    p1 = getattr(final[1], 'reward', 0) or 0
    winner = 0 if p0 > p1 else (1 if p1 > p0 else -1)

    transitions = []
    for step in results:
        for agent_idx, state in enumerate(step):
            if state.status != 'active': continue
            obs = state.observation
            gs = GameState(obs)
            planet_feats, fleet_feats, global_feat = gs.encode()
            reward = 1.0 if agent_idx == winner else (-1.0 if winner >= 0 else 0.0)
            transitions.append({
                'planet_feats': planet_feats,
                'fleet_feats': fleet_feats,
                'global_feat': global_feat,
                'reward': reward
            })
    return transitions, winner, (p0, p1)

def training_step(batch):
    # Ensure your training logic is defined here or imported
    pass
```

## [CODE]
```python
def evaluate(agent1, agent2, num_games=20):
    wins = 0
    losses = 0
    draws = 0

    for _ in range(num_games):
        # We can reuse collect_episode to get the winner
        # Note: We don't care about the transitions here, just the outcome
        _, winner, _ = collect_episode(agent1, agent2, epsilon=0.0)

        if winner == 0:
            wins += 1
        elif winner == 1:
            losses += 1
        else:
            draws += 1

    win_rate = wins / num_games
    loss_rate = losses / num_games
    draw_rate = draws / num_games

    return win_rate, loss_rate, draw_rate
```

## [CODE]
```python
# Cell 10: Run Curriculum Training

print("="*60)
print("Starting 7-Level Curriculum Self-Play Training")
print("="*60)

best_model_state = None

for level_idx, level_name in enumerate(CURRICULUM_LEVELS):
    opponent = OPPONENTS[level_name]
    is_selfplay = (level_name == 'selfplay')

    print(f"\n{'='*60}")
    print(f"LEVEL {level_idx+1}/{len(CURRICULUM_LEVELS)}: vs {level_name.upper()}")
    print(f"{'='*60}")

    eps = 0.3 if level_idx == 0 else (0.25 if level_idx == 1 else 0.15)
    win_rate = 0.0
    round_num = 0

    while win_rate < WIN_THRESHOLD:
        round_num += 1
        eps = max(0.05, eps - 0.002)

        nn_agent = InferenceAgent(model, epsilon=eps)

        if is_selfplay:
            current_opponent = InferenceAgent(model, epsilon=eps * 0.5)
        else:
            current_opponent = opponent

        for ep in range(EPISODES_PER_ROUND):
            seed = level_idx * 1000 + round_num * EPISODES_PER_ROUND + ep
            transitions, winner, scores = collect_episode(nn_agent, current_opponent, epsilon=eps, seed=seed)
            if transitions is not None:
                replay.extend(transitions)

        for _ in range(UPDATES_PER_ROUND):
            batch = random.sample(replay, min(BATCH_SIZE, len(replay)))
            training_step(batch)

        scheduler.step()

        if round_num % 5 == 0:
            if is_selfplay:
                eval_opponent = InferenceAgent(model, epsilon=0.0)
            else:
                eval_opponent = opponent
            win_rate, _, _ = evaluate(InferenceAgent(model, epsilon=0.0), eval_opponent, num_games=EVAL_GAMES)
            print(f"  Round {round_num}: win_rate={win_rate:.1%}, eps={eps:.3f}, replay={len(replay)}")

    best_model_state = deepcopy(model.state_dict())
    torch.save(best_model_state, f'v47_level{level_idx}_{level_name}.pt')
    target_model.load_state_dict(best_model_state)
    print(f"\n  LEVEL {level_idx+1} COMPLETE! Beating {level_name} with {win_rate:.1%} win rate")
    print(f"  Saved: v47_level{level_idx}_{level_name}.pt")

torch.save(model.state_dict(), 'v47_final.pt')
print("\n" + "="*60)
print("CURRICULUM TRAINING COMPLETE!")
print("="*60)

# Cell 11: Final Evaluation

print("\n" + "="*60)
print("FINAL EVALUATION: v47 vs v45")
print("="*60)

final_agent = InferenceAgent(model, epsilon=0.0)
win_rate, loss_rate, draw_rate = evaluate(final_agent, v45_agent, num_games=30)
print(f"Results over 30 games:")
print(f"  v47 wins: {win_rate:.1%}")
print(f"  v45 wins: {loss_rate:.1%}")
print(f"  Draws: {draw_rate:.1%}")

if win_rate > loss_rate:
    print(">>> v47 BEATS v45! <<<")
elif loss_rate > win_rate:
    print("v45 still ahead - need more training")
else:
    print("About equal - competitive!")
```

## [CODE]
```python
# Cell 12: Save Model

torch.save(model.state_dict(), 'v47_rl_agent.pt')
print("Model saved to v47_rl_agent.pt")
```
