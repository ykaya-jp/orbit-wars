#!/usr/bin/env bash
# Day 2 submission orchestration (refined after late-night discovery).
#
# CRITICAL discovery (Day 1 evening): konbu17 + bovard-trained validator
# resampled to LB 1017.0 (vs konbu17 original validator at 989.2).
# Our bovard 59k-shot retrain was actually +28 over the author's 8.8k-shot
# weights once LB resampling settled.
#
# Day 2 priority: stack our LB-best base (bovard validator) with the new
# topk1 trick from konbu17/train-submit-v4-ml-validator-topk1-tutorial
# (author claim +75 LB) and our own bowwow/Vadasz patches.
#
# Run:  bash tools/day2_submit.sh
# Each submission consumes one daily limit (5/day).

set -e
cd "$(dirname "$0")/.."

SHA=$(git rev-parse --short HEAD)
KAGGLE=/home/yusuke_kaya/projects/kaggle/orbit-wars/.venv/bin/kaggle

submit() {
  local name=$1
  local file=$2
  local desc=$3
  echo ""
  echo "=== $name ==="
  $KAGGLE competitions submit orbit-wars -f "$file" -m "$SHA $desc"
  echo "submitted, sleeping 30s before next..."
  sleep 30
}

# 1. bovard validator + topk1: stack LB-best base (1017) with author's topk1 (+75 claim)
submit "bovard + topk1" \
  "submissions/konbu17_bovard_topk1.tar.gz" \
  "phase-γ-bovard-topk1 (LB1017 base + topk1 wrapper, expect ~1100)"

# 2. all-in: bovard validator + bowwow patch + topk1
submit "bovard + bowwow + topk1" \
  "submissions/konbu17_bovard_topk1_bowwow.tar.gz" \
  "phase-γ-all-in (bovard+bowwow patch+topk1, expect 1050-1150)"

# 3. bovard validator + bowwow patch (no topk1)
submit "bovard + bowwow patch" \
  "submissions/konbu17_bovard_bowwow.tar.gz" \
  "phase-γ-bovard-bowwow (bovard validator + WEAK_ENEMY/LONG_TRAVEL/ELIM patches)"

# 4. original konbu17 validator + topk1 (author's pure recipe)
submit "konbu17 (orig) + topk1" \
  "submissions/konbu17_topk1.tar.gz" \
  "phase-γ-topk1-pure (konbu17 author's pure +75 LB recipe)"

# 5. original konbu17 validator + bowwow patch
submit "konbu17 (orig) + bowwow" \
  "submissions/konbu17_weak_enemy_aggressive.tar.gz" \
  "phase-γ-bowwow-pure (konbu17 + our bowwow/Vadasz patches)"

echo ""
echo "=== Day 2 submissions complete (5/5 daily) ==="
$KAGGLE competitions submissions orbit-wars 2>&1 | head -8
