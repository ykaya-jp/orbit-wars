#!/usr/bin/env bash
# Continuous orbit-wars asset watcher.
# Run at session start (or via cron) to incrementally pull:
#   1. New public kernels (high-vote + recent)
#   2. New bovard daily replay datasets (top10 FFA games)
#   3. LB top-30 snapshot
#   4. Our submission status
#   5. New discussions (limited — kaggle CLI requires topic IDs)
#
# Usage:
#   bash tools/watch_orbit_wars.sh           # full run
#   bash tools/watch_orbit_wars.sh --kernels # kernels only
#   bash tools/watch_orbit_wars.sh --data    # bovard only
#   bash tools/watch_orbit_wars.sh --lb      # leaderboard only

set -euo pipefail
cd "$(dirname "$0")/.."

KAGGLE=/home/yusuke_kaya/projects/kaggle/orbit-wars/.venv/bin/kaggle
TS=$(date -u +%Y-%m-%dT%H%M%SZ)
DAY_UTC=$(date -u +%Y-%m-%d)
LOG_DIR=docs/research/watch_log
mkdir -p "$LOG_DIR"

mode="${1:---all}"

run_kernels() {
  echo ""
  echo "=== [$TS] new kernels watch ==="
  CSV=$LOG_DIR/kernels_$TS.csv
  $KAGGLE kernels list --competition orbit-wars --sort-by dateRun --page-size 100 -v > "$CSV" 2>&1 || true
  # Find kernels not yet pulled (skip header line, extract slug)
  EXISTING=$(ls docs/research/public_kernels/ 2>/dev/null | sort -u)
  LATEST=$(awk -F',' 'NR>1 && $1 != "" {n=split($1, parts, "/"); print parts[n]}' "$CSV" | sort -u)
  NEW=$(comm -13 <(echo "$EXISTING") <(echo "$LATEST"))
  if [ -z "$NEW" ]; then
    echo "  no new kernels"
  else
    echo "$NEW" | while read -r slug; do
      [ -z "$slug" ] && continue
      # Look up author for this slug (= ref before /slug)
      author=$(awk -F',' -v s="$slug" 'NR>1 && index($1, "/" s) > 0 {n=split($1, p, "/"); print p[n-1]; exit}' "$CSV")
      [ -z "$author" ] && continue
      ref="$author/$slug"
      echo "  pulling $ref"
      $KAGGLE kernels pull "$ref" -p "docs/research/public_kernels/$slug" -m 2>&1 | tail -1 || true
      # Convert ipynb → content.md
      .venv/bin/python -c "
import json
from pathlib import Path
slug='$slug'
nb = Path(f'docs/research/public_kernels/{slug}/{slug}.ipynb')
py = Path(f'docs/research/public_kernels/{slug}/{slug}.py')
md = Path(f'docs/research/public_kernels/{slug}/content.md')
if md.exists(): exit(0)
if py.exists():
    md.write_text(f'## [CODE]\n\`\`\`python\n{py.read_text(encoding=\"utf-8\")}\n\`\`\`\n', encoding='utf-8')
    exit(0)
if not nb.exists(): exit(0)
with nb.open() as f: data=json.load(f)
out=[]
for cell in data.get('cells', []):
    ct=cell.get('cell_type'); src=cell.get('source','')
    if isinstance(src, list): src=''.join(src)
    if ct=='markdown': out.append('## [MD]\n'+src.strip()+'\n')
    elif ct=='code': out.append('## [CODE]\n\`\`\`python\n'+src.strip()+'\n\`\`\`\n')
md.write_text('\n'.join(out), encoding='utf-8')
" 2>/dev/null || true
    done
  fi
}

run_data() {
  echo ""
  echo "=== [$TS] bovard data watch ==="
  # bovard publishes one dataset per UTC day, named bovard/orbit-wars-top10-episodes-YYYY-MM-DD
  # Probe yesterday + today (their pipeline lags a day). Skip if already present.
  for offset in 1 0; do
    d=$(date -u -d "$DAY_UTC -$offset day" +%Y-%m-%d 2>/dev/null || \
        date -u -v "-${offset}d" +%Y-%m-%d 2>/dev/null || echo "")
    [ -z "$d" ] && continue
    target="data/external/bovard_full/$d"
    if [ -d "$target" ] && [ -n "$(ls "$target" 2>/dev/null)" ]; then
      echo "  $d: already present"
      continue
    fi
    echo "  trying bovard/orbit-wars-top10-episodes-$d ..."
    mkdir -p "$target"
    $KAGGLE datasets download "bovard/orbit-wars-top10-episodes-$d" --unzip -p "$target" 2>&1 | tail -1 || \
      { rmdir "$target" 2>/dev/null; echo "    not yet published"; }
  done
}

run_lb() {
  echo ""
  echo "=== [$TS] LB top-30 watch ==="
  CSV=$LOG_DIR/lb_$TS.csv
  $KAGGLE competitions leaderboard orbit-wars -s --csv 2>&1 | head -32 > "$CSV"
  echo "  saved $CSV"
  head -10 "$CSV"
}

run_subs() {
  echo ""
  echo "=== [$TS] my submissions ==="
  $KAGGLE competitions submissions orbit-wars 2>&1 | head -10
}

case "$mode" in
  --kernels) run_kernels ;;
  --data)    run_data ;;
  --lb)      run_lb ;;
  --subs)    run_subs ;;
  --all|*)
    run_lb
    run_subs
    run_kernels
    run_data
    ;;
esac

echo ""
echo "=== watch run complete at $TS ==="
