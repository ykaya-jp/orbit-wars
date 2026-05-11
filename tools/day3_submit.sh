#!/usr/bin/env bash
# Day 3 submission orchestration — 2026-05-12 09:00 JST reset
#
# Plan ref: .criteria/kaggle-orbit-wars-day3-submit-2026-05-12.yaml
# Roadmap: docs/strategy/2026-05-11-victory-roadmap.md (= P1 phase)
#
# 戦略 (= 2026-05-11 fleet.angle pivot): 真因 (= zachary が fleet.angle 未使用、 LB +100-200 機会損失)
# を最優先で解消。 Lakhindar 2 件は Day 4 へ延期 (= Day 2 review で 4P 0/8 = risky)。
# Slot 構成 (P1 5 件 改訂版):
#   1. submission_v2.tar.gz             — 5/10 LB 989/1017、 safety net (NO topk1)
#   2. konbu17_topk1.tar.gz             — 5/11 best LB 922、 24h resampling 確認
#   3. ppo_v3_theta3.tar.gz             — PPO θ.3 新規 RL paradigm datapoint
#   4. fleet_angle_zachary.tar.gz       — NEW: zachary + fleet.angle defense backport (LB +100-200 期待)
#   5. rudra_topk1_bowwow.tar.gz        — rudra MIN_SHIPS=15 + FRAC=0.85 + topk1 (kovi-tier 大 fleet)
#
# Day 2 教訓 (= docs/research/2026-05-11-submission-analyses.md):
#   - ratio σ=0.13 = systematic over-optimistic、 expected を local 4P win rate × 800-900 で校正
#   - 5 submit 全部 < 989 (= 既存 best 超えず)、 「local high → LB low」 transfer 失敗確認
#   - Lakhindar は val acc 0.967 だが LB 未 submit = 本 batch で生死判明

set -e
cd "$(dirname "$0")/.."

SHA=$(git rev-parse --short HEAD)
KAGGLE=.venv/bin/kaggle

submit() {
  local name=$1
  local file=$2
  local desc=$3
  echo ""
  echo "=== $name ==="
  echo "  file: $file"
  echo "  desc: $desc"
  $KAGGLE competitions submit orbit-wars -f "$file" -m "$SHA $desc"
  echo "submitted, sleeping 30s before next..."
  sleep 30
}

# Build new variant tar.gz packages (= ensure latest main.py only、 these are single-file agents)
echo "=== Pre-build fleet_angle + rudra_bowwow packages ==="
(cd submissions/build_fleet_angle_zachary && tar --exclude='__pycache__' -czf ../fleet_angle_zachary.tar.gz main.py)
echo "  built submissions/fleet_angle_zachary.tar.gz ($(du -h submissions/fleet_angle_zachary.tar.gz | cut -f1))"
(cd submissions/build_rudra_topk1_bowwow && tar --exclude='__pycache__' -czf ../rudra_topk1_bowwow.tar.gz main.py)
echo "  built submissions/rudra_topk1_bowwow.tar.gz ($(du -h submissions/rudra_topk1_bowwow.tar.gz | cut -f1))"

# 1. SAFETY NET: 5/10 our true LB best (= 989/1017) 再 submit (NO topk1)
submit "1. safety net (5/10 best)" \
  "submissions/submission_v2.tar.gz" \
  "phase-γ-resubmit (5/10 LB 989/1017 base = konbu17 hybrid + bovard validator, NO topk1)"

# 2. konbu17 + topk1 (= 5/11 best 922 再 submit, 24h resampling 確認)
submit "2. konbu17+topk1 resubmit" \
  "submissions/konbu17_topk1.tar.gz" \
  "phase-γ-topk1-resubmit (5/11 LB 922 = konbu17 author pure +75 LB recipe, 24h resampling check)"

# 3. PPO θ.3 (= top-tier IL + rule-base mix opponent で 50k step training)
submit "3. PPO θ.3 NEW paradigm" \
  "submissions/ppo_v3_theta3.tar.gz" \
  "phase-θ.3 (MaskablePPO 50k step vs Lakhindar IL + rudra_topk1 + zachary_topk1, RL paradigm datapoint)"

# 4. fleet_angle_zachary (= NEW: zachary + fleet.angle defense backport, LB +100-200 期待)
submit "4. fleet_angle_zachary NEW" \
  "submissions/fleet_angle_zachary.tar.gz" \
  "phase-α-fleet-angle-backport (zachary + base agent.py:649 fleet.angle defense, Day 2 review +ROI 最大)"

# 5. rudra + topk1 + bowwow (= 大 fleet 戦術 + rudra paradigm 強化)
submit "5. rudra+topk1+bowwow NEW" \
  "submissions/rudra_topk1_bowwow.tar.gz" \
  "phase-rudra-topk1-bowwow (rudra MIN_SHIPS=15 + FRAC=0.85 + topk1, kovi-tier 大 fleet match)"

echo ""
echo "=== Day 3 submissions complete ==="
echo "Run 'kaggle competitions submissions orbit-wars' to check status"
$KAGGLE competitions submissions orbit-wars 2>&1 | head -10
echo ""
echo "Append LB initial to docs/research/2026-05-12-submission-analyses.md within 30 min."
