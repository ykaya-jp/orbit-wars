#!/usr/bin/env bash
# Day 2 submission orchestration — REVISED 2026-05-11 06:10 JST
#
# CRITICAL discovery (Day 2 dawn, 05:45 JST):
#   thisisn0mad/Rudra9439 published rule-based submission (kaggle dataset 2026-05-10 16:22).
#   4P tournament (24 ep combined) vs konbu17/Marco/orbitbotnext:
#     Rudra:        14/24 = 58%
#     orbitbotnext:  8/24 = 33%
#     konbu17:       2/24 = 8%
#     Marco:         0/24 = 0%
#   → Rudra is decisively stronger than our LB-best (konbu17 hybrid @ 990).
#   Day 2 priority shifted: Rudra base + variants take 3 of 5 slots.
#
# Run:  bash tools/day2_submit.sh
# Each submission consumes one daily limit (5/day).
#
# Backup of original Day 2 plan is in git: see commit 5231610.

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

# 1. PRIMARY BET: Rudra pure (= 58% local 4P win rate, public kernel CC0-1.0)
submit "rudra pure" \
  "submissions/build_rudra/main.py" \
  "phase-rudra-pure (thisisn0mad/Rudra9439 publish 2026-05-10, local 58% 4P)"

# 2. Rudra ms=15 (lightweight 1D variation; ms=15 ≈ ms=25 tied 50/50 in self-play,
#    aggressive 3-axis patch was 25% vs pure 75% so single-axis is safer)
submit "rudra ms15" \
  "submissions/build_rudra_ms15/main.py" \
  "phase-rudra-ms15 (MIN_SHIPS_MINE_ATTACK 10→15, single-axis variant)"

# 3. bovard validator + topk1 (= our previous best path, LB1017 base + topk1 wrapper)
submit "bovard + topk1" \
  "submissions/konbu17_bovard_topk1.tar.gz" \
  "phase-γ-bovard-topk1 (LB1017 base + topk1 wrapper, expect ~1100)"

# 4. bovard validator + bowwow patch
submit "bovard + bowwow" \
  "submissions/konbu17_bovard_bowwow.tar.gz" \
  "phase-γ-bovard-bowwow (bovard validator + WEAK_ENEMY/LONG_TRAVEL/ELIM patches)"

# 5. Rudra + bovard validator stacking attempt
# Note: Rudra is self-contained rule-base, not validator-based. Stacking would
# require deep refactor. Save slot for a 4th Rudra-variant or konbu17_topk1 fallback.
submit "konbu17 (orig) + topk1" \
  "submissions/konbu17_topk1.tar.gz" \
  "phase-γ-topk1-pure (konbu17 author pure +75 LB recipe, fallback if Rudra fails)"

echo ""
echo "=== Day 2 submissions complete (5/5 daily) ==="
$KAGGLE competitions submissions orbit-wars 2>&1 | head -8
