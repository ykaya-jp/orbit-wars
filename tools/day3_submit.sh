#!/usr/bin/env bash
# Day 3 submission orchestration — 2026-05-12 09:00 JST reset
#
# CRITICAL CONTEXT (from Day 2 = 2026-05-11):
#   - 5 submits all underperformed (= 600-961 LB vs 1100+ expected)
#   - Best of Day 2: konbu17_topk1.tar.gz at LB 947-971
#   - Our true best ever: submission_v2.tar.gz (= 5/10) at LB 989/1017
#   - Day 2 episode analysis: 'Reexel' = anonymized our submission
#   - Win factor: LARGE FLEET MAINTENANCE (= avg ship size > opp)
#   - topk1 wrapper helps when base agent generates many small moves
#
# Day 3 plan v1: focus on PROVEN + new topk1 variants + safety net
#   1. submission_v2.tar.gz (= 5/10 LB 1017 best, NO topk1, safety net)
#   2. konbu17_topk1.tar.gz (= 5/11 LB 961 today's best, re-submit)
#   3. submissions/build_rudra_topk1_proper/main.py (= local 50%, NEW)
#   4. submissions/build_zachary_topk1/main.py (= local 50%, NEW)
#   5. PPO θ.2 (= when training completes by 14:00 JST 5/11)
#
# Note: ensemble agent FAILED (0/8 local), DO NOT submit.
# Note: konbu17_bovard_topk1 FAILED (LB 679 from 1017 base = -338 regression).
#       Bovard validator + topk1 incompatible; use author weights for topk1.

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

# 1. SAFETY NET: re-submit our true LB best (= 989/1017) to escape 600 trap
submit "safety net (5/10 best)" \
  "submissions/submission_v2.tar.gz" \
  "phase-γ-resubmit (5/10 LB 989/1017 base = konbu17 hybrid + bovard validator, NO topk1)"

# 2. konbu17 + topk1 author recipe re-submit (= today's best 961)
submit "konbu17+topk1 re-submit" \
  "submissions/konbu17_topk1.tar.gz" \
  "phase-γ-topk1-pure-resubmit (LB 947-971 yesterday, expect ~1000 with resampling)"

# 3. rudra + topk1 (= NEW, local 50% in 16 ep, LB 1049 base + topk1 wrapper)
submit "rudra+topk1 NEW" \
  "submissions/build_rudra_topk1_proper/main.py" \
  "phase-rudra-topk1 (rudra LB 1049 base + largest-move-only wrapper, expect 1100-1200)"

# 4. zachary + topk1 (= NEW, local 50%, LB ~1000 base)
submit "zachary+topk1 NEW" \
  "submissions/build_zachary_topk1/main.py" \
  "phase-zachary-topk1 (zachary LB ~1000 base + largest-move wrapper)"

# 5. rudra + topk1 + bowwow (MIN_SHIPS_MINE_ATTACK 10→15, FRAC 0.7→0.85, +topk1)
submit "rudra+topk1+bowwow NEW" \
  "submissions/build_rudra_topk1_bowwow/main.py" \
  "phase-rudra-topk1-bowwow (rudra+MIN_SHIPS=15+FRAC=0.85+topk1, kovi-tier fleet match)"

echo ""
echo "=== Day 3 submissions complete ==="
$KAGGLE competitions submissions orbit-wars 2>&1 | head -8
