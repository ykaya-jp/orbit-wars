#!/usr/bin/env bash
# PPO curriculum training (Phase 2 stage)。
# vs random → vs starter → vs heuristic → vs il_v2_active を順に。
# 各 stage の結果を agents/proxy/ppo_curr_<n>.zip に保存し、次 stage は --init-from で resume。
#
# Usage:
#   bash tools/run_ppo_curriculum.sh [steps_per_stage]
# Default: 200000 steps/stage × 4 stages = 800k total

set -e

cd "$(dirname "$0")/.."

STEPS="${1:-200000}"
DEVICE="${PPO_DEVICE:-cuda}"
N_ENVS="${PPO_N_ENVS:-4}"

echo "=== PPO curriculum: $STEPS steps/stage on $DEVICE ==="

# Stage 1: vs random
echo ""
echo "--- stage 1: vs random ---"
uv run python -m tools.train_ppo \
    --opponent random --total-steps $STEPS \
    --output agents/proxy/ppo_curr_1.zip \
    --device $DEVICE --n-envs $N_ENVS --shaped-reward 1.0

# Stage 2: vs starter (resume from stage 1)
echo ""
echo "--- stage 2: vs starter (resume from stage 1) ---"
uv run python -m tools.train_ppo \
    --opponent starter --total-steps $STEPS \
    --output agents/proxy/ppo_curr_2.zip \
    --init-from agents/proxy/ppo_curr_1.zip \
    --device $DEVICE --n-envs $N_ENVS --shaped-reward 1.0

# Stage 3: vs heuristic (resume from stage 2)
echo ""
echo "--- stage 3: vs heuristic (resume from stage 2) ---"
uv run python -m tools.train_ppo \
    --opponent heuristic --total-steps $STEPS \
    --output agents/proxy/ppo_curr_3.zip \
    --init-from agents/proxy/ppo_curr_2.zip \
    --device $DEVICE --n-envs $N_ENVS --shaped-reward 2.0

# Stage 4: vs il_v2_active (resume from stage 3)
echo ""
echo "--- stage 4: vs il_v2_active (resume from stage 3) ---"
uv run python -m tools.train_ppo \
    --opponent il_v2_active --total-steps $STEPS \
    --output agents/proxy/ppo_curr_4.zip \
    --init-from agents/proxy/ppo_curr_3.zip \
    --device $DEVICE --n-envs $N_ENVS --shaped-reward 2.0

echo ""
echo "=== curriculum complete ==="
ls -la agents/proxy/ppo_curr_*.zip
