## [MD]
# Orbit Wars - Expert Dataset Generator
### Goal: Kickstarting Reinforcement Learning via Imitation Learning
Reinforcement Learning (RL) in complex environments like Orbit Wars often suffers from a "cold start" problem. **Imitation Learning (Behavioral Cloning)** allows us to bootstrap our RL agent by training it to predict the actions of an existing expert agent.

This notebook provides a bridge between heuristic agents and neural networks by generating a high-quality dataset of expert decisions in an efficient **Parquet** format.

## [MD]
### Inverse Targeting Resolution
Expert agents in Orbit Wars communicate via raw launch angles. To train a neural network effectively, we map these continuous angles back to the intended **Target Planet ID**.

## [CODE]
```python
submission_path = '/kaggle/input/notebooks/pilkwang/orbit-wars-structured-baseline/submission.py'
```

## [CODE]
```python
%%capture
# ignore output, too verbose
!pip install --upgrade 'kaggle-environments>1.28'
```

## [CODE]
```python
%%capture
# ignore output, too verbose
from kaggle_environments import make
```

## [CODE]
```python
import os
import importlib.util
import math

import json
import numpy as np
import pandas as pd
from tqdm.notebook import tqdm
```

## [MD]
The `resolve_target` function performs a ray-casting intersection test to identify which planet the expert was aiming at, transforming the complex trajectory into a clean `[source, target, ships]` action model.

## [CODE]
```python
def resolve_target(sid, ang, ships, planets, v_ang):
    """
    High-Fidelity Trajectory Resolver:
    Maps a continuous launch angle back to a discrete Target Planet ID by
    simulating the actual physics of the Orbit Wars engine.

    Physics logic:
    1. Ships move at a constant speed: min(1.0 + ships // 20, 6.0).
    2. Planets rotate around the center (50,50) based on angular_velocity.
    3. Collision occurs if distance(ship, planet) < planet_radius + tolerance.

    Args:
        sid (int): Source planet ID where ships originated.
        ang (float): Launch angle in radians.
        ships (int): Ship count (determines fleet velocity).
        planets (list): Current environment planet state.
        v_ang (float): System angular velocity (radians per turn).

    Returns:
        int: The ID of the planet hit by the fleet, or -1 if no hit detected.
    """
    # 1. Locate source planet position safely
    s = next((p for p in planets if p[0] == sid), None)
    if not s: return -1

    fx, fy = s[2], s[3]  # Initial fleet position (planet center)
    dx, dy = math.cos(ang), math.sin(ang)
    speed = min(1.0 + ships // 20, 6.0)

    # 2. Iterative Step-by-Step Simulation
    # We simulate up to 250 turns to catch even the longest cross-map shots.
    for t in range(1, 251):
        # Move fleet forward
        fx += dx * speed
        fy += dy * speed

        # Check against every other planet at its predicted position at turn 't'
        for p in planets:
            if p[0] == sid: continue

            px, py, pr = p[2]-50, p[3]-50, p[4]
            r_orb = math.hypot(px, py)

            if r_orb + pr >= 50:
                # Stationary/Outer planets do not rotate
                tx, ty = p[2], p[3]
            else:
                # Circular orbital prediction
                a_t = math.atan2(py, px) + (v_ang * t)
                tx, ty = 50 + r_orb * math.cos(a_t), 50 + r_orb * math.sin(a_t)

            # 3. Collision Detection
            # Uses a 2.0 unit tolerance to account for engine float precision
            # and slight variations in how different agents predict positions.
            if math.hypot(fx - tx, fy - ty) < pr + 2.0:
                return p[0]

    return -1
```

## [CODE]
```python
def test_resolution(submission_path, num_actions=10):
    """
    Verification Tool:
    Runs a few game turns to verify that the trajectory resolver is
    correctly identifying the expert's intended targets.

    Args:
        submission_path (str): Path to submission.py
        num_actions (int): Number of actions to capture before stopping.
    """
    print(f"--- Verifying Resolver with {os.path.basename(submission_path)} ---")
    spec = importlib.util.spec_from_file_location('test_agent', submission_path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    agent = mod.agent

    env = make("orbit_wars")
    obs_list = env.reset(2)
    hits, total = 0, 0

    while total < num_actions:
        moves_list = []
        for i in range(2):
            p_obs = obs_list[i].observation
            moves = agent(p_obs)
            moves_list.append(moves)
            for sid, ang, ships in (moves or []):
                total += 1
                tid = resolve_target(sid, ang, ships, p_obs['planets'], p_obs['angular_velocity'])
                status = "✅" if tid != -1 else "❌"
                print(f"  Action {total}: Source {sid} -> Target {tid} [{status}]")
                if tid != -1: hits += 1

        obs_list = env.step(moves_list)
        if all(o.status != "ACTIVE" for o in obs_list): break

    if total > 0:
        print(f"\nFinal Verification: {hits}/{total} resolved ({(hits/total)*100:.1f}%)")
    else:
        print("\nNo actions taken by agent to verify.")
```

## [CODE]
```python
test_resolution(submission_path)
```

## [MD]
# Simulation & Data Collection Loop

To create a robust dataset, we simulate matches across different player counts (2p and 4p) using the expert agent.

Key Logic of this Loop:

* Expert Self-Play: Every player in the match uses the same submission.py logic. This maximizes the density of high-quality interactions and
     ensures the model learns how to handle expert-level opponents.
* Tactical Data Balancing: Orbit Wars is a game of timing; in many steps, the expert correctly chooses to do nothing. However, training on 100% of
     these "passive" steps would bias a neural network towards inactivity. We downsample empty steps by 95%, forcing the model to focus its learning
     capacity on active tactical maneuvers.
* Information Preservation: We store the raw observation as a JSON blob to ensure no state information is lost, while resolving the actions into a
     clean, discrete format ready for Reinforcement Learning.
* High-Performance Storage: The results are saved as a Parquet file. This format uses columnar compression, making the dataset significantly
     smaller and faster to load than CSV or JSON when you start your training session.

## [CODE]
```python
def run_gen(submission_path, configs=None):
    """
    Expert Dataset Generator (Trajectory Harvester):
    Generates a balanced imitation dataset by running self-play competitions.

    Key Features:
    - Self-Play: Maximizes high-quality expert-vs-expert interactions.
    - Inverse Targeting: Uses resolve_target to create clean Source->Target labels.
    - Data Balancing: Keeps 100% of action turns, but only 5% of passive turns
      to prevent the neural network from learning a bias toward doing nothing.
    """
    if configs is None:
        configs = [(2, 100), (4, 50)]

    data = []
    # Dynamic loader to import any submission.py
    spec = importlib.util.spec_from_file_location('submission', submission_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    agent_fn = mod.agent

    for players, episodes in configs:
        env = make('orbit_wars')
        for _ in tqdm(range(episodes), desc=f"{players}p matches"):
            env.run([agent_fn] * players)

            for step_idx, states in enumerate(env.steps):
                if step_idx == 0: continue

                for p_id in range(players):
                    obs, act = states[p_id]['observation'], states[p_id]['action']
                    # DATA BALANCING: 95% drop on idle steps
                    if not act and np.random.rand() > 0.05: continue

                    v_ang = obs.get('angular_velocity', 0)
                    resolved = []
                    for sid, a, s in (act or []):
                        tid = resolve_target(sid, a, s, obs['planets'], v_ang)
                        if tid != -1: resolved.append([sid, tid, int(s)])

                    data.append({
                        'step': obs.get('step', step_idx),
                        'players': players,
                        'player_id': p_id,
                        'obs_json': json.dumps(obs),
                        'acts_json': json.dumps(resolved)
                    })
    return data
```

## [CODE]
```python
obs_actions = run_gen(submission_path)
```

## [CODE]
```python
df = pd.DataFrame(obs_actions)
df.to_parquet('imitation_data.parquet', index=False, compression='snappy')
df.head()
```

## [CODE]
```python

```

## [CODE]
```python

```
