#!/usr/bin/env bash
# Score each konbu17 variant against (konbu17 base + Marco + orbitbotnext) in 4P FFA.
# Used to pick top 5 candidates for Day 2's 5-daily submission budget.
#
# Each test: 4 rotations × 2 seeds = 8 episodes, ~4 min per variant.

set -e
cd "$(dirname "$0")/.."

UV="uv run"
declare -A VARIANTS=(
  ["t030"]="submissions/build_konbu_t030/main.py"
  ["t035"]="submissions/build_konbu_t035/main.py"
  ["t045"]="submissions/build_konbu_t045/main.py"
  ["t050"]="submissions/build_konbu_t050/main.py"
  ["weak_enemy_high"]="submissions/build_konbu_weak_enemy_high/main.py"
  ["long_travel_loose"]="submissions/build_konbu_long_travel_loose/main.py"
  ["weak_enemy_aggressive"]="submissions/build_konbu_weak_enemy_aggressive/main.py"
)

OUT=/tmp/variants_4p_results.csv
echo "variant,wins,games,win_rate" > "$OUT"

for label in "${!VARIANTS[@]}"; do
  agent="${VARIANTS[$label]}"
  if [ ! -f "$agent" ]; then
    echo "skip $label (file missing)"
    continue
  fi
  echo ""
  echo "=== testing $label vs (konbu17, Marco, orbitbotnext) ==="
  csv=/tmp/variant_$label.csv
  rm -f "$csv"
  $UV python -m tools.tournament_4p \
    --agents "$agent" \
              experiments/konbu17_hybrid/main.py \
              experiments/marco_1060/main.py \
              experiments/orbitbotnext/main.py \
    --seeds 1,2 --rotations 4 --episodes 1 \
    --output "$csv" 2>&1 | tail -2 || true
  # extract win rate for the variant (= match by full path containing the build dir slug)
  uv run python -c "
import polars as pl
df = pl.read_csv('$csv')
n = 0; w = 0
key = '$label'
for r in df.iter_rows(named=True):
    for i in range(4):
        if key in r[f'agent_p{i}']:
            n += 1
            if r[f'reward_p{i}'] > 0: w += 1
wr = w/max(n,1)
print(f'$label: W={w}/{n}  ({wr*100:.0f}%)')
with open('$OUT', 'a') as f:
    f.write(f'$label,{w},{n},{wr:.3f}\n')
"
done

echo ""
echo "=== Final ranking (sorted by win rate) ==="
sort -t',' -k4 -nr "$OUT" | head -10
