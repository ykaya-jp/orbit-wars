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

# 1. orbitbotnext (single-file, untested LB, 4P 20%, 2P 85%)
submit "orbitbotnext" "experiments/orbitbotnext/main.py" "phase-α'' orbitbotnext (pascalledesma, untested LB)"

# 2-5. konbu17 hybrid threshold sweep (vs LB 989.2 default)
submit "konbu17 t=0.30" "submissions/konbu17_t030.tar.gz" "phase-γ-thresh-0.30 (validator looser)"
submit "konbu17 t=0.35" "submissions/konbu17_t035.tar.gz" "phase-γ-thresh-0.35"
submit "konbu17 t=0.45" "submissions/konbu17_t045.tar.gz" "phase-γ-thresh-0.45"
submit "konbu17 t=0.50" "submissions/konbu17_t050.tar.gz" "phase-γ-thresh-0.50 (validator stricter)"

echo ""
echo "=== Day 2 submissions complete (5/5 daily) ==="
$KAGGLE competitions submissions orbit-wars 2>&1 | head -8
