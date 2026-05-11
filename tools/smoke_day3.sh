#!/usr/bin/env bash
# Day 3 5 件 submit の local smoke test
#
# Plan ref: .criteria/kaggle-orbit-wars-day3-submit-2026-05-12.yaml AC-5
#
# 各 build を 4P FFA 1 episode (= vs starter × 3) で完走確認:
#   - exception なし
#   - status = DONE
#   - duration_sec < 60s (= Kaggle 評価 timeout の安全 margin)
#
# 失敗 = exit 1 + 該当 build 名を stderr に出力

set -uo pipefail
cd "$(dirname "$0")/.."

PYTHON=.venv/bin/python

# 5 件 (= 2026-05-11 fleet.angle pivot): name → agent path
# Lakhindar 2 件は Day 4 へ延期 (= Day 2 review で 4P 0/8 で risky)、
# Slot 4-5 を fleet.angle defense + rudra 大 fleet に置換
declare -a BUILDS=(
  "submission_v2:submissions/build_v2/main.py"
  "konbu17_topk1:submissions/build_konbu_topk1/main.py"
  "ppo_v3_theta3:submissions/build_ppo_v3_theta3/main.py"
  "fleet_angle_zachary:submissions/build_fleet_angle_zachary/main.py"
  "rudra_topk1_bowwow:submissions/build_rudra_topk1_bowwow/main.py"
)

OVERALL_OK=0
FAILED=()

for entry in "${BUILDS[@]}"; do
  name="${entry%%:*}"
  agent_path="${entry#*:}"

  echo ""
  echo "=== smoke: $name ==="
  echo "  agent: $agent_path"

  if [[ ! -f "$agent_path" ]]; then
    echo "  FAIL: agent file not found"
    OVERALL_OK=1
    FAILED+=("$name (file missing)")
    continue
  fi

  # 4P FFA: agent vs starter × 3, seed=42
  output=$("$PYTHON" -m tools._run_episode \
    --left "$agent_path" \
    --right starter \
    --p3 starter \
    --p4 starter \
    --seed 42 2>&1)
  rc=$?

  if [[ $rc -ne 0 ]]; then
    echo "  FAIL: _run_episode exit $rc"
    echo "$output" | tail -20
    OVERALL_OK=1
    FAILED+=("$name (exit $rc)")
    continue
  fi

  # Parse JSON last line
  json_line=$(echo "$output" | tail -1)
  status_p0=$(echo "$json_line" | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin).get('status_p0','?'))" 2>/dev/null || echo "PARSE_ERR")
  duration=$(echo "$json_line" | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin).get('duration_sec',-1))" 2>/dev/null || echo "-1")
  step_count=$(echo "$json_line" | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin).get('step_count',-1))" 2>/dev/null || echo "-1")

  echo "  status_p0=$status_p0 duration_sec=$duration step_count=$step_count"

  if [[ "$status_p0" != "DONE" ]]; then
    echo "  FAIL: status_p0 != DONE"
    OVERALL_OK=1
    FAILED+=("$name (status=$status_p0)")
    continue
  fi

  # Kaggle 評価互換: 1 episode 全体で 60s 以内 (= per-step 余裕 margin、 評価は per-step 1s 別物だが episode 全体 stability check)
  is_under=$("$PYTHON" -c "print(1 if float('$duration') < 60.0 else 0)")
  if [[ "$is_under" != "1" ]]; then
    echo "  FAIL: duration ${duration}s >= 60s (Kaggle timeout margin breach)"
    OVERALL_OK=1
    FAILED+=("$name (slow ${duration}s)")
    continue
  fi

  echo "  PASS"
done

echo ""
echo "==================================="
if [[ $OVERALL_OK -eq 0 ]]; then
  echo "ALL 5 builds smoke PASS"
else
  echo "FAILED builds:"
  for f in "${FAILED[@]}"; do echo "  - $f"; done
fi
echo "==================================="

exit $OVERALL_OK
