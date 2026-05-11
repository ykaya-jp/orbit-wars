#!/usr/bin/env bash
# Day 3 submission orchestration — 2026-05-12 09:00 JST reset
#
# Plan ref: .criteria/kaggle-orbit-wars-day3-submit-2026-05-12.yaml
# Roadmap: docs/strategy/2026-05-11-victory-roadmap.md (= P1 phase)
#
# 戦略: Lakhindar IL paradigm の LB 生死判明 (= datapoint isolation) + safety net
# Slot 構成 (P1 5 件):
#   1. submission_v2.tar.gz       — 5/10 LB 989/1017、 safety net (NO topk1)
#   2. konbu17_topk1.tar.gz       — 5/11 best LB 922、 24h resampling 確認
#   3. ppo_v3_theta3.tar.gz       — PPO θ.3 新規 RL paradigm datapoint
#   4. lakhindar_pure.tar.gz      — Lakhindar IL passive (val acc 0.967)、 IL 生死判明
#   5. lakhindar_topk1.tar.gz     — Lakhindar IL + topk1 wrapper、 IL+topk1 ablation
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

# Build Lakhindar tar.gz packages (= ensure latest main.py + weights + orbit_wars/)
echo "=== Pre-build Lakhindar packages ==="
(cd submissions/build_lakhindar_pure && tar --exclude='__pycache__' -czf ../lakhindar_pure.tar.gz main.py orbit_wars/ grid_il_lakhindar.pt)
echo "  built submissions/lakhindar_pure.tar.gz ($(du -h submissions/lakhindar_pure.tar.gz | cut -f1))"
(cd submissions/build_lakhindar_topk1 && tar --exclude='__pycache__' -czf ../lakhindar_topk1.tar.gz main.py orbit_wars/ grid_il_lakhindar.pt)
echo "  built submissions/lakhindar_topk1.tar.gz ($(du -h submissions/lakhindar_topk1.tar.gz | cut -f1))"

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

# 4. Lakhindar IL pure (= kovi/Shun_PI rank1 BC, val acc 0.967, IL paradigm 生死判明)
submit "4. Lakhindar IL pure NEW" \
  "submissions/lakhindar_pure.tar.gz" \
  "phase-η-lakhindar-pure (kovi LB ~1480 + Shun_PI LB ~1515 replay BC, val acc 0.967, IL paradigm 1st LB test)"

# 5. Lakhindar IL + topk1 (= IL + largest-move wrapper ablation)
submit "5. Lakhindar IL + topk1 NEW" \
  "submissions/lakhindar_topk1.tar.gz" \
  "phase-η-lakhindar-topk1 (Lakhindar IL + topk1 wrapper, IL+topk1 ablation vs konbu17+topk1)"

echo ""
echo "=== Day 3 submissions complete ==="
echo "Run 'kaggle competitions submissions orbit-wars' to check status"
$KAGGLE competitions submissions orbit-wars 2>&1 | head -10
echo ""
echo "Append LB initial to docs/research/2026-05-12-submission-analyses.md within 30 min."
