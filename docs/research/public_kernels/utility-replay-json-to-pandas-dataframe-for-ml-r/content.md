## [MD]
# 🚀 Orbit Wars: JSON to Pandas DataFrame for ML/RL

Hi everyone!
With the recent update allowing us to download episode replays (JSON) and the extension of `overageTime` to 60 seconds, **Training ML/RL models (like XGBoost, LightGBM, or Neural Networks) has become totally viable!**

However, parsing the complex nested JSON replays into a tabular format can be a headache. If you are familiar with tabular competitions (like the Titanic), you probably just want a clean Pandas DataFrame.

This notebook provides a utility script to convert Kaggle's Replay JSON into a **Machine Learning-ready Pandas DataFrame**.
Each row represents a specific action (a fleet launch) along with the global board state at that moment.

If you find this useful for your imitation learning or RL pipelines, **please consider giving an upvote!** ⭐

---

### 🛠️ 1. Setup & Functions

## [CODE]
```python
import json
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def extract_global_features(obs, player_id):
    """
    Extracts global board state features from the observation.
    """
    planets = obs.get('planets', [])
    fleets = obs.get('fleets', [])

    my_planets = [p for p in planets if p[1] == player_id]
    enemy_planets = [p for p in planets if p[1] not in [-1, player_id]]
    neutral_planets = [p for p in planets if p[1] == -1]

    my_fleets = [f for f in fleets if f[1] == player_id]
    enemy_fleets = [f for f in fleets if f[1] != player_id]

    features = {
        'my_total_planets': len(my_planets),
        'enemy_total_planets': len(enemy_planets),
        'neutral_total_planets': len(neutral_planets),
        'my_total_ships_on_planets': sum(p[5] for p in my_planets),
        'enemy_total_ships_on_planets': sum(p[5] for p in enemy_planets),
        'my_total_fleets_in_air': len(my_fleets),
        'enemy_total_fleets_in_air': len(enemy_fleets),
        'my_total_ships_in_air': sum(f[6] for f in my_fleets),
        'enemy_total_ships_in_air': sum(f[6] for f in enemy_fleets),
    }
    return features

def extract_planet_features(obs, planet_id):
    """
    Extracts specific features for the source planet.
    [id, owner, x, y, radius, ships, production]
    """
    planets = obs.get('planets', [])
    for p in planets:
        if p[0] == planet_id:
            return {
                'src_x': p[2],
                'src_y': p[3],
                'src_radius': p[4],
                'src_ships_available': p[5],
                'src_production': p[6]
            }
    return {}

def replay_to_dataframe(json_path):
    """
    Parses a single episode JSON and returns a Pandas DataFrame.
    """
    with open(json_path, 'r') as f:
        replay = json.load(f)

    steps = replay.get('steps', [])
    data_rows = []

    # Iterate through all turns
    for step_idx, step in enumerate(steps):
        # step is a list of agent data, e.g., [agent0_data, agent1_data]
        for agent_id, agent_data in enumerate(step):
            action = agent_data.get('action')
            obs = agent_data.get('observation', {})

            # Skip if no action was taken or no observation
            if not action or not obs:
                continue

            player_id = obs.get('player', agent_id)

            # action format: [[from_planet_id, direction_angle, num_ships], ...]
            for single_act in action:
                if len(single_act) != 3:
                    continue

                from_planet_id, angle, num_ships = single_act

                # 1. Base info
                row = {
                    'step': step_idx,
                    'player_id': player_id,
                }

                # 2. Global State Features (X)
                global_feats = extract_global_features(obs, player_id)
                row.update(global_feats)

                # 3. Source Planet Features (X)
                planet_feats = extract_planet_features(obs, from_planet_id)
                row.update(planet_feats)

                # 4. Action Targets (y) - What the ML model should predict!
                row['target_action_angle'] = angle
                row['target_action_ships'] = num_ships

                data_rows.append(row)

    df = pd.DataFrame(data_rows)
    return df
```

## [MD]
### 📊 2. Example Usage (Mock Data)
Since we can't fetch JSON directly from the internet inside this notebook without internet access, let's create a small dummy JSON to demonstrate how the DataFrame looks.

*In your local environment or with an uploaded dataset, just pass your actual `episode.json` to the `replay_to_dataframe()` function!*

## [CODE]
```python
# --- Dummy Data Generation for Demonstration ---
dummy_replay = {
    "steps": [
        [
            {
                "observation": {
                    "player": 0,
                    "planets": [[0, 0, 10.0, 10.0, 1.5, 50, 3], [1, 1, 90.0, 90.0, 1.5, 50, 3]],
                    "fleets": []
                },
                "action": [[0, 0.785, 20]] # Send 20 ships from planet 0 at 45 degrees
            },
            {
                "observation": {
                    "player": 1,
                    "planets": [[0, 0, 10.0, 10.0, 1.5, 50, 3], [1, 1, 90.0, 90.0, 1.5, 50, 3]],
                    "fleets": []
                },
                "action": [[1, 3.92, 10]]
            }
        ]
    ]
}

with open('dummy_episode.json', 'w') as f:
    json.dump(dummy_replay, f)
# -----------------------------------------------

# Convert to DataFrame!
df = replay_to_dataframe('dummy_episode.json')

print(f"Data Shape: {df.shape}")
display(df.head())
```

## [MD]
### 🧠 3. How to use this for ML (Imitation Learning)?

With this clean tabular format, you can easily train models to imitate the top bots!
For example, you can build two models:
1. **Regression Model (XGBoost / LightGBM)**: Predict the `target_action_ships` (How many ships should I send?).
2. **Regression/Classification Model**: Predict the `target_action_angle` (Where should I aim?).

**Next Steps for you:**
* Use the Kaggle CLI (`kaggle competitions replay <EPISODE_ID>`) to download top players' matches.
* Run them through this script and concatenate the DataFrames.
* Add more advanced features (e.g., Distance to nearest enemy, Sun collision flags).
* Train your model!

Good luck, and please **Upvote** if you found this helpful! 🚀
