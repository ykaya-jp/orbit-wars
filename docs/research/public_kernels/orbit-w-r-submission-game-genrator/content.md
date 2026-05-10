## [CODE]
```python
# %% [markdown]
# # Orbit Wars Submission Generator
#
# This notebook creates a `main.py` file that implements a competitive agent for the Kaggle Orbit Wars environment.
# The agent uses a **nearest‑planet sniper** strategy with adaptive fleet sizing.
#
# Run this notebook once, then submit the generated `main.py` to Kaggle.

# %% [code]
import os

submission_code = '''import math
from typing import List, Dict, Any

def agent(observation: Dict[str, Any], configuration: Dict[str, Any]) -> List[List[float]]:
    """
    Orbit Wars agent – Nearest Planet Sniper with adaptive fleet size.

    For each owned planet, find the closest non‑owned planet.
    Send enough ships to capture it (target ships + 1), but capped at half the source planet's ships.
    Avoid sending if the target is a comet about to leave (optional).
    """
    # Unpack observation
    planets_raw = observation.get("planets", [])
    fleets_raw = observation.get("fleets", [])
    player = observation.get("player", 0)

    # Convert to list of (id, owner, x, y, radius, ships, production)
    planets = []
    for p in planets_raw:
        planets.append({
            "id": p[0],
            "owner": p[1],
            "x": p[2],
            "y": p[3],
            "radius": p[4],
            "ships": p[5],
            "production": p[6]
        })

    # Separate my planets and targets (enemy + neutral)
    my_planets = [p for p in planets if p["owner"] == player]
    targets = [p for p in planets if p["owner"] != player]

    moves = []

    # Pre‑compute distances for efficiency (small number of planets)
    for src in my_planets:
        # Skip if source has too few ships
        if src["ships"] < 10:
            continue

        # Find nearest target
        best_dist = float("inf")
        best_target = None
        for tgt in targets:
            dx = src["x"] - tgt["x"]
            dy = src["y"] - tgt["y"]
            dist = math.hypot(dx, dy)
            if dist < best_dist:
                best_dist = dist
                best_target = tgt

        if best_target is None:
            continue

        # Required ships = target garrison + 1 (to flip ownership)
        required = best_target["ships"] + 1
        # Limit to half of source ships (leave defense)
        send = min(required, src["ships"] // 2)
        if send < 1:
            continue

        # Direction angle
        angle = math.atan2(best_target["y"] - src["y"], best_target["x"] - src["x"])
        moves.append([src["id"], angle, send])

    return moves
'''

# Write the submission file
with open("main.py", "w") as f:
    f.write(submission_code)

print("main.py generated successfully – ready for Kaggle submission.")
print("File content:")
print(submission_code)

# %% [markdown]
# ## How to submit
# 1. Download `main.py` from the notebook output.
# 2. On the Kaggle competition page, go to **Submit**.
# 3. Upload `main.py` as your submission.
# 4. The agent will be evaluated against the environment.
```

## [CODE]
```python

```
