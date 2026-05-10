#!/usr/bin/env bash
# Day 2 submission orchestration.
#
# Submits 5 candidates with 5-min spacing so we get distinct LB scores
# (Kaggle resamples per-submission). Run from project root:
#
#     bash tools/day2_submit.sh
#
# Each submission consumes one daily limit; we have 5/day so this uses all.
# Do not run in parallel — submit one at a time and let LB resample between.

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
  echo "$KAGGLE competitions submit orbit-wars -f $file -m \"$SHA $desc\""
  $KAGGLE competitions submit orbit-wars -f "$file" -m "$SHA $desc"
  echo "submitted, sleeping 30s before next..."
  sleep 30
}

# Day 2 priority order (refined after evening research):
# 1. konbu17 + topk1: konbu17 author's own +75 LB claim ("LB ~1049")
#    Source: konbu17/train-submit-v4-ml-validator-topk1-tutorial
# 2. konbu17 + weak_enemy_aggressive: our bowwow/Vadasz strategy patch
# 3. konbu17 t=0.35: safe threshold tweak from default 0.40 (LB 989)
# 4. orbitbotnext: untested LB, 4P 25% locally, 2P 85% — datapoint
# 5. konbu17 t=0.45: opposite threshold direction

submit "konbu17 + topk1" "submissions/konbu17_topk1.tar.gz" "phase-γ-topk1 (konbu17 author +75 LB claim)"
submit "konbu17 weak-enemy-aggressive" "submissions/konbu17_weak_enemy_aggressive.tar.gz" "phase-γ-bowwow-patch (our weak-enemy + long-travel + ahead-attack)"
submit "konbu17 t=0.35" "submissions/konbu17_t035.tar.gz" "phase-γ-thresh-0.35"
submit "orbitbotnext" "experiments/orbitbotnext/main.py" "phase-α'' orbitbotnext (pascalledesma, 4P 25%)"
submit "konbu17 t=0.45" "submissions/konbu17_t045.tar.gz" "phase-γ-thresh-0.45"

echo ""
echo "=== Day 2 submissions complete (5/5 daily) ==="
$KAGGLE competitions submissions orbit-wars 2>&1 | head -8
