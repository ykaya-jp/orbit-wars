#!/usr/bin/env bash
# Auto-eval PPO checkpoint + package as Kaggle submission tarball.
#
# Usage: bash tools/eval_ppo_checkpoint.sh <ppo_zip> <agent_name>
#   ppo_zip   = path to MaskablePPO checkpoint (e.g. agents/proxy/ppo_v2_theta2.zip)
#   agent_name = unique name for the agent (e.g. ppo_v2_theta2)

set -e
cd "$(dirname "$0")/.."

PPO_ZIP=${1:-agents/proxy/ppo_v2_theta2.zip}
AGENT_NAME=${2:-ppo_v2_theta2}

if [ ! -f "$PPO_ZIP" ]; then
  echo "ERROR: PPO checkpoint not found: $PPO_ZIP"
  exit 1
fi

echo "=== Step 1: Build inference wrapper ==="
mkdir -p submissions/build_$AGENT_NAME

# Copy PPO weights into submission dir
cp "$PPO_ZIP" "submissions/build_$AGENT_NAME/$AGENT_NAME.zip"

# Build wrapper main.py (= self-contained for kaggle submission)
cat > "submissions/build_$AGENT_NAME/main.py" <<EOF
"""MaskablePPO agent wrapper (= $AGENT_NAME)."""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# Embed inference logic (= grid_agent.py + grid_encoder.py + ppo_agent.py)
# For Kaggle submission, we need everything in main.py or co-located files

from ppo_inference import make_ppo_agent

_WEIGHTS = _HERE / "$AGENT_NAME.zip"
agent = make_ppo_agent(_WEIGHTS, device="cpu", deterministic=True)
EOF

# Copy required source files
mkdir -p submissions/build_$AGENT_NAME/orbit_wars
cp src/orbit_wars/grid_encoder.py submissions/build_$AGENT_NAME/orbit_wars/
cp src/orbit_wars/grid_model.py submissions/build_$AGENT_NAME/orbit_wars/
cp src/orbit_wars/grid_agent.py submissions/build_$AGENT_NAME/orbit_wars/
cp src/orbit_wars/physics.py submissions/build_$AGENT_NAME/orbit_wars/
cp src/orbit_wars/__init__.py submissions/build_$AGENT_NAME/orbit_wars/ 2>/dev/null || touch submissions/build_$AGENT_NAME/orbit_wars/__init__.py

# Make ppo_inference.py — adapter that finds orbit_wars relative to itself
cat > "submissions/build_$AGENT_NAME/ppo_inference.py" <<'EOF'
"""PPO inference adapter for Kaggle submission."""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import math
import numpy as np
import torch

# Import from local copy of orbit_wars
from orbit_wars import physics
from orbit_wars.grid_encoder import (
    ANGLE_BINS, GRID_SIZE, NO_OP_CLASS, PER_CELL_ACTIONS,
    SHIP_FRAC_BINS, encode_grid_state,
)


def _decode(class_id, home_capacity):
    if class_id == NO_OP_CLASS:
        return None
    cls = class_id - 1
    angle_bin = cls // SHIP_FRAC_BINS
    frac_bin = cls % SHIP_FRAC_BINS
    angle = (angle_bin + 0.5) * (2 * math.pi / ANGLE_BINS)
    if angle > math.pi:
        angle -= 2 * math.pi
    frac_to_ships = {0: 5, 1: 20, 2: 60, 3: 200, 4: 500}
    ships = min(frac_to_ships.get(frac_bin, 5), max(home_capacity, 1))
    return angle, int(ships)


def _home_capacity(ships, max_fraction=0.85, reserve=5):
    return max(0, min(int(ships * max_fraction), ships - reserve))


def make_ppo_agent(model_path, device="cpu", deterministic=True, sun_safety_margin_rad=0.035):
    from sb3_contrib import MaskablePPO
    model = MaskablePPO.load(str(model_path), device=device)
    model.policy.eval()

    def agent(observation, configuration=None):
        try:
            enc = encode_grid_state(observation)
            if not enc.my_cells:
                return []
            actions = []
            planets_dict = {int(p[0]): p for p in observation.get("planets", [])}
            player = int(observation.get("player", 0) or 0)
            for pid, row, col in enc.my_cells:
                planet = planets_dict.get(pid)
                if planet is None or int(planet[1]) != player:
                    continue
                home_ships = int(planet[5])
                home_cap = _home_capacity(home_ships)
                if home_cap <= 0:
                    continue
                cell_mask = np.zeros((GRID_SIZE * GRID_SIZE,), dtype=np.float32)
                cell_mask[row * GRID_SIZE + col] = 1.0
                obs = {
                    "spatial": enc.spatial.astype(np.float32),
                    "globals": enc.globals_.astype(np.float32),
                    "action_mask": cell_mask,
                }
                action_mask_full = np.repeat(cell_mask, PER_CELL_ACTIONS).astype(bool)
                action_mask_full[(row * GRID_SIZE + col) * PER_CELL_ACTIONS] = True
                with torch.no_grad():
                    action, _ = model.predict(obs, deterministic=deterministic, action_masks=action_mask_full)
                cell_id, action_class = divmod(int(action), PER_CELL_ACTIONS)
                if cell_id != row * GRID_SIZE + col:
                    continue
                decoded = _decode(action_class, home_cap)
                if decoded is None:
                    continue
                angle, ships = decoded
                if ships <= 0 or ships > home_cap:
                    continue
                home_x, home_y = float(planet[2]), float(planet[3])
                safe = physics.safe_angle_around(home_x, home_y, angle, margin=sun_safety_margin_rad)
                actions.append([float(pid), float(safe), int(ships)])
            return actions
        except Exception:
            return []
    return agent
EOF

echo "submission dir: submissions/build_$AGENT_NAME/"
ls -la submissions/build_$AGENT_NAME/

echo ""
echo "=== Step 2: Quick smoke test ==="
uv run python -c "
import sys; sys.path.insert(0, 'submissions/build_$AGENT_NAME')
import main as m
print('agent loaded:', type(m.agent).__name__)
" 2>&1 | tail -3

echo ""
echo "=== Step 3: 8 ep tournament vs strong opponents ==="
uv run python -m tools.tournament_4p \
    --agents submissions/build_$AGENT_NAME/main.py submissions/build_rudra_topk1_proper/main.py experiments/marco_1060/main.py experiments/orbitbotnext/main.py \
    --episodes 2 --seeds 91,92,93,94 --rotations 1 \
    --output /tmp/${AGENT_NAME}_eval.csv 2>&1 | tail -10

echo ""
echo "=== Step 4: Win rate ==="
.venv/bin/python -c "
import polars as pl
df = pl.read_csv('/tmp/${AGENT_NAME}_eval.csv')
print(f'episodes: {len(df)}')
agents = set()
for c in ['agent_p0','agent_p1','agent_p2','agent_p3']:
    agents.update(df[c].to_list())
ranking = []
for a in sorted(agents):
    n = 0; w = 0
    for row in df.iter_rows(named=True):
        for i in range(4):
            if row[f'agent_p{i}'] == a:
                n += 1
                if row[f'reward_p{i}'] > 0: w += 1
    if n > 0:
        ranking.append((w/n, a, w, n))
for wr, a, w, t in sorted(ranking, reverse=True):
    print(f'  {a:55s}: {w}/{t} ({wr*100:.0f}%)')
"

echo ""
echo "=== Step 5: Package as tarball ==="
cd submissions/build_$AGENT_NAME
tar czf ../${AGENT_NAME}.tar.gz main.py ppo_inference.py orbit_wars/ ${AGENT_NAME}.zip
cd ../..
ls -la submissions/${AGENT_NAME}.tar.gz
echo ""
echo "DONE: submissions/${AGENT_NAME}.tar.gz ready for Day 3 submit"
