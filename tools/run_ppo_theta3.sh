#!/usr/bin/env bash
# PPO θ.3: stronger opponent mix (= top-tier IL + best rule-base)
# Run AFTER θ.2 completes (= ~14:00 JST 5/11).
#
# Opponent pool:
#   - agents/proxy/grid_il_lakhindar.py (= top-tier IL trained on kovi/Shun_PI replays)
#   - submissions/build_rudra_topk1_proper/main.py (= local 50% strong rule-base)
#   - submissions/build_zachary_topk1/main.py (= local 50% another strong)
#
# Hypothesis: PPO learns to beat top-tier-mimic IL + best rule-base.
# If win rate > 30% in tournament after training, this is strong LB candidate.

set -e
cd "$(dirname "$0")/.."

# Wait for θ.2 if still running
while pgrep -f "train_ppo.*ppo_v2_theta2" > /dev/null; do
    echo "$(date '+%H:%M:%S'): θ.2 still training, waiting 60s..."
    sleep 60
done

echo "$(date '+%H:%M:%S'): θ.2 done, starting θ.3"

uv run python -m tools.train_ppo \
    --total-timesteps 50000 \
    --n-envs 4 \
    --n-steps 256 \
    --batch-size 128 \
    --opponents agents/proxy/grid_il_lakhindar.py \
                submissions/build_rudra_topk1_proper/main.py \
                submissions/build_zachary_topk1/main.py \
    --reward-shaping \
    --device cuda \
    --output agents/proxy/ppo_v3_theta3.zip \
    > outputs/ppo_v3_theta3.log 2>&1
echo "$(date '+%H:%M:%S'): θ.3 done, output saved"
