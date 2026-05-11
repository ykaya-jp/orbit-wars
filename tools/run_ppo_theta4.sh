#!/usr/bin/env bash
# PPO θ.4 — true PFSP self-history training 100k step (Phase θ.4 本 training)
#
# Plan: .criteria/kaggle-orbit-wars-ppo-theta4-pfsp.yaml
# Roadmap: docs/strategy/2026-05-11-victory-roadmap.md (= P2 phase)
#
# Warm-start: agents/proxy/ppo_v3_theta3.zip (= 50k step vs Lakhindar IL + rule-base)
# Self-history pool: max 8 entries, save every 10k step (= θ.4 単独で 10 ckpt → 8 keep)
# External opponents: Lakhindar IL + konbu17+topk1 + rudra+topk1 (= rule + IL mix)
# Sample probability: 60% self-history (PFSP) / 30% external / 10% random
#
# Expected: ~5-10 hour on RTX 3090, n_envs=8
# Output: agents/proxy/ppo_v4_theta4.zip + outputs/ppo_pfsp_pool_theta4/ckpt_step_*.zip

set -e
cd "$(dirname "$0")/.."

OUTPUT_LOG="outputs/ppo_v4_theta4_real.log"
START_TIME=$(date -Is)

echo "=== PPO θ.4 真 PFSP training start ${START_TIME} ===" | tee "$OUTPUT_LOG"
nvidia-smi --query-gpu=name,memory.free --format=csv,noheader | head -1 | tee -a "$OUTPUT_LOG"

uv run python -m tools.train_ppo_pfsp \
    --total-timesteps 100000 \
    --n-envs 8 \
    --n-steps 256 \
    --batch-size 128 \
    --device cuda \
    --warm-start agents/proxy/ppo_v3_theta3.zip \
    --external-opponents agents/proxy/grid_il_lakhindar.py \
                         submissions/build_konbu_topk1/main.py \
                         submissions/build_rudra_topk1_proper/main.py \
    --pool-max 8 \
    --save-interval 10000 \
    --pool-dir outputs/ppo_pfsp_pool_theta4 \
    --self-play-prob 0.6 \
    --external-prob 0.3 \
    --reward-shaping \
    --output agents/proxy/ppo_v4_theta4.zip \
    >> "$OUTPUT_LOG" 2>&1

END_TIME=$(date -Is)
echo "=== PPO θ.4 done ${END_TIME} (start ${START_TIME}) ===" | tee -a "$OUTPUT_LOG"
ls -la agents/proxy/ppo_v4_theta4.zip outputs/ppo_pfsp_pool_theta4/ | tee -a "$OUTPUT_LOG"
