#!/usr/bin/env bash
# Day 4 submission orchestration — 2026-05-13 09:00 JST reset
#
# Plan ref: .criteria/kaggle-orbit-wars-day4-submit-2026-05-13.yaml
# Roadmap: docs/strategy/2026-05-11-victory-roadmap.md (= P1 Day 4)
# Handoff: docs/dev/HANDOFF-2026-05-12.md §6
#
# Day 3 results (= 5/12 09:30+ JST 反映後) を踏まえ Day 4 5 件 submit:
#   1. ${DAY3_BEST_FILE:-submissions/submission_v2.tar.gz}
#        — Day 3 best 再 submit (= 24h resample + ratio drift calibrate)
#        — 環境 var DAY3_BEST_FILE で override 可能 (= 09:30 LB 反映後 user 上書き)
#   2. submissions/fleet_angle_zachary_v3.tar.gz
#        — fleet.angle + end-game pile-up + Let-them-fight (= main rule paradigm)
#   3. submissions/fleet_angle_zachary_v5.tar.gz
#        — v3 + step 300+ fleet boost (= bovard 数値駆動 ablation)
#   4. submissions/marcodg_topk1.tar.gz
#        — marcodg LB 1060 claim + 我家 topk1 wrapper (= 別 paradigm)
#   5. submissions/ppo_v4_theta4.tar.gz ★
#        — Colab Pro+ A100 200k step PFSP 完走 (= explained_variance 0.95、 IL+RL paradigm)
#        — LB 1100-1400 期待 (= bowwowforeach 1698 への path 1st datapoint)
#
# Day 3 教訓 (= 5/12 18:00 JST 反映時 update):
#   - Day 3 LB best → 本 script slot 1 file を 09:30 後に env で上書き
#   - ratio drift σ < 0.02 確認 OR re-calibrate
#   - fleet_angle_zachary が Day 3 で勝った場合は v3/v5 で +ROI が見込める

set -e
cd "$(dirname "$0")/.."

SHA=$(git rev-parse --short HEAD)
KAGGLE=.venv/bin/kaggle

# 09:30 JST LB 反映後 user 上書き可能:
#   DAY3_BEST_FILE=submissions/fleet_angle_zachary.tar.gz bash tools/day4_submit.sh
DAY3_BEST_FILE="${DAY3_BEST_FILE:-submissions/submission_v2.tar.gz}"
DAY3_BEST_LB="${DAY3_BEST_LB:-TBD}"

submit() {
  local name=$1
  local file=$2
  local desc=$3
  echo ""
  echo "=== $name ==="
  echo "  file: $file ($(du -h "$file" | cut -f1))"
  echo "  desc: $desc"
  $KAGGLE competitions submit orbit-wars -f "$file" -m "$SHA $desc"
  echo "submitted, sleeping 30s before next..."
  sleep 30
}

# Pre-build single-file packages (= main.py only, identical to day3_submit.sh approach)
echo "=== Pre-build Day 4 variant packages ==="
(cd submissions/build_fleet_angle_zachary_v3 && tar --exclude='__pycache__' -czf ../fleet_angle_zachary_v3.tar.gz main.py)
echo "  built submissions/fleet_angle_zachary_v3.tar.gz ($(du -h submissions/fleet_angle_zachary_v3.tar.gz | cut -f1))"
(cd submissions/build_fleet_angle_zachary_v5 && tar --exclude='__pycache__' -czf ../fleet_angle_zachary_v5.tar.gz main.py)
echo "  built submissions/fleet_angle_zachary_v5.tar.gz ($(du -h submissions/fleet_angle_zachary_v5.tar.gz | cut -f1))"
(cd submissions/build_marcodg_topk1 && tar --exclude='__pycache__' -czf ../marcodg_topk1.tar.gz main.py)
echo "  built submissions/marcodg_topk1.tar.gz ($(du -h submissions/marcodg_topk1.tar.gz | cut -f1))"

# 1. Day 3 best 再 submit (= 24h resample + ratio drift calibrate)
submit "1. Day 3 best resubmit (24h resample)" \
  "$DAY3_BEST_FILE" \
  "phase-day4-resample (Day 3 best LB ${DAY3_BEST_LB} 24h TrueSkill resample + ratio drift calibration)"

# 2. fleet_angle_zachary_v3 (= main rule paradigm)
submit "2. fleet_angle_zachary_v3 NEW" \
  "submissions/fleet_angle_zachary_v3.tar.gz" \
  "phase-day4-v3 (zachary + fleet.angle defense + end-game pile-up + Let-them-fight, main rule paradigm)"

# 3. fleet_angle_zachary_v5 (= bovard 数値駆動 ablation = step 300+ fleet boost)
submit "3. fleet_angle_zachary_v5 NEW" \
  "submissions/fleet_angle_zachary_v5.tar.gz" \
  "phase-day4-v5 (v3 + step 300+ 3.4x fleet boost, bovard 280万row 数値駆動 ablation)"

# 4. marcodg + topk1 (= 別 paradigm = beam search + 我家 topk1 lift)
submit "4. marcodg+topk1 NEW" \
  "submissions/marcodg_topk1.tar.gz" \
  "phase-day4-marcodg (marcodg LB 1060 claim + topk1 wrapper, 別 paradigm)"

# 5. PPO θ.4 200k step PFSP ★ (= IL+RL paradigm 1st mainstream datapoint)
submit "5. PPO θ.4 200k PFSP ★" \
  "submissions/ppo_v4_theta4.tar.gz" \
  "phase-theta4 (MaskablePPO 200k step PFSP, explained_variance 0.95, A100 Colab Pro+ 7h, LB 1100-1400 期待)"

echo ""
echo "=== Day 4 submissions complete ==="
echo "Run 'kaggle competitions submissions orbit-wars' to check status"
$KAGGLE competitions submissions orbit-wars 2>&1 | head -10
echo ""
echo "Append LB initial to docs/research/2026-05-13-submission-analyses.md within 30 min."
echo "After 09:30 JST: compute ratio drift sigma over Day 3 + Day 4 = 10 submit (AC-7)."
