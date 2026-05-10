#!/usr/bin/env bash
# Day 2 submission orchestration — REVISED v3 2026-05-11 07:52 JST
#
# DISCOVERY TIMELINE (Day 2 dawn):
#   05:45 JST: thisisn0mad/Rudra9439 dataset (= LB 1049 public). 24 ep 4P: 58%.
#   07:36 JST: Rudra MS sweep — pure beats variants; multi-axis patch degrades.
#   07:51 JST: zacharymaronek/orbit-wars-heuristic-agent-scored-1000 evaluated.
#              12 ep 4-way (zachary vs Rudra vs konbu17 vs djenk):
#                zachary: 9/12 = 75%
#                Rudra:   3/12 = 25%
#                konbu17: 0/12 =  0%
#                djenk:   0/12 =  0%
#   → zachary > Rudra > konbu17 in 4P. zachary takes slot 1.
#
# Day 2 plan v3:
#   1. zachary (= local 75% 4P, public claim >1000)
#   2. Rudra pure (= local 58% 4P over 24 ep, public LB 1049)
#   3. bovard+topk1 (= LB1017 base + topk1 wrapper)
#   4. bovard+bowwow (= bovard validator + bowwow patches)
#   5. konbu17+topk1 (= author's pure +75 LB recipe, fallback)
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

# 1. PRIMARY BET: zachary (= LOCAL 75% 4P win rate, beats Rudra 75-25)
submit "zachary" \
  "submissions/build_zachary/main.py" \
  "phase-zachary (zacharymaronek pub 2026-05-10, local 75% 4P beats Rudra)"

# 2. SECONDARY: Rudra pure (= local 58% 24ep, LB 1049 author claim)
submit "rudra pure" \
  "submissions/build_rudra/main.py" \
  "phase-rudra-pure (thisisn0mad LB 1049, local 58% 4P over 24 ep)"

# 3. bovard validator + topk1 (= our previous best path, LB1017 base + topk1)
submit "bovard + topk1" \
  "submissions/konbu17_bovard_topk1.tar.gz" \
  "phase-γ-bovard-topk1 (LB1017 base + topk1 wrapper, expect ~1100)"

# 4. bovard validator + bowwow patch
submit "bovard + bowwow" \
  "submissions/konbu17_bovard_bowwow.tar.gz" \
  "phase-γ-bovard-bowwow (bovard validator + WEAK_ENEMY/LONG_TRAVEL/ELIM patches)"

# 5. konbu17 (orig) + topk1 (= author pure recipe, fallback)
submit "konbu17 (orig) + topk1" \
  "submissions/konbu17_topk1.tar.gz" \
  "phase-γ-topk1-pure (konbu17 author pure +75 LB recipe, fallback)"

echo ""
echo "=== Day 2 submissions complete (5/5 daily) ==="
$KAGGLE competitions submissions orbit-wars 2>&1 | head -8
