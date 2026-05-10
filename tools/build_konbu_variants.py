"""Build threshold-swept variants of konbu17 hybrid for Day 2 submissions.

Creates submissions/build_konbu_t{th}/ each with main.py + weights.npz where
the only diff is `_VAL_THRESHOLD = <th>` patched into main.py.

Default thresholds: 0.30, 0.35, 0.45, 0.50 (vs konbu17 default 0.40 = LB 989.2).

Usage:
    python -m tools.build_konbu_variants
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

THRESHOLDS = [0.30, 0.35, 0.45, 0.50]

# bowwow/Vadasz-inspired patches (= constants from konbu17 main.py)
# - WEAK_ENEMY_THRESHOLD ↑ : detect more enemies as "weak" → finish them
# - ELIMINATION_BONUS ↑    : value of eliminating an enemy from the game
# - LONG_TRAVEL_MARGIN_*   : keep more ships when traveling far (more long-distance snipes)
BOWWOW_PATCHES = {
    "weak_enemy_high": {
        "WEAK_ENEMY_THRESHOLD": 110,  # default 45 → broader weak detection
        "ELIMINATION_BONUS": 55.0,  # default 18 → strong reward for elim
    },
    "long_travel_loose": {
        "LONG_TRAVEL_MARGIN_START": 28,  # default 18 → trigger long-distance snipe sooner
        "LONG_TRAVEL_MARGIN_DIVISOR": 4,  # default 3 → smaller per-distance penalty
    },
    "weak_enemy_aggressive": {
        "WEAK_ENEMY_THRESHOLD": 110,
        "ELIMINATION_BONUS": 55.0,
        "LONG_TRAVEL_MARGIN_START": 28,
        "AHEAD_ATTACK_MARGIN_BONUS": 0.20,  # default 0.08
    },
}

SRC_MAIN = Path("experiments/konbu17_hybrid/main.py")
SRC_WEIGHTS = Path("experiments/konbu17_hybrid/weights.npz")
OUT_BASE = Path("submissions")


def main() -> int:
    if not SRC_MAIN.exists() or not SRC_WEIGHTS.exists():
        print("missing konbu17 source")
        return 1

    main_text = SRC_MAIN.read_text(encoding="utf-8")

    for th in THRESHOLDS:
        th_label = f"{th:.2f}".replace(".", "")  # 030, 035, 045, 050
        build_dir = OUT_BASE / f"build_konbu_t{th_label}"
        build_dir.mkdir(parents=True, exist_ok=True)

        # patch threshold
        new_text, n = re.subn(
            r"_VAL_THRESHOLD\s*=\s*[\d.]+",
            f"_VAL_THRESHOLD = {th:.4f}",
            main_text,
            count=1,
        )
        if n != 1:
            print(f"  threshold {th}: failed to patch (no match)")
            continue
        (build_dir / "main.py").write_text(new_text, encoding="utf-8")
        shutil.copy(SRC_WEIGHTS, build_dir / "weights.npz")

        tar_path = OUT_BASE / f"konbu17_t{th_label}.tar.gz"
        subprocess.run(
            ["tar", "-czf", str(tar_path), "-C", str(build_dir), "main.py", "weights.npz"],
            check=True,
        )
        sz = tar_path.stat().st_size
        print(f"  threshold {th}: {tar_path} ({sz} bytes)")

    # bowwow/Vadasz-inspired patches
    print("\n=== bowwow patches ===")
    for label, overrides in BOWWOW_PATCHES.items():
        build_dir = OUT_BASE / f"build_konbu_{label}"
        build_dir.mkdir(parents=True, exist_ok=True)
        text = main_text
        ok = True
        for name, val in overrides.items():
            if isinstance(val, int):
                repl = f"{name} = {val}"
            else:
                repl = f"{name} = {val:.4f}"
            new, n = re.subn(rf"^{re.escape(name)}\s*=\s*[\d.]+", repl, text, count=1, flags=re.M)
            if n != 1:
                print(f"  {label}: failed to patch {name}")
                ok = False
                break
            text = new
        if not ok:
            continue
        (build_dir / "main.py").write_text(text, encoding="utf-8")
        shutil.copy(SRC_WEIGHTS, build_dir / "weights.npz")
        tar_path = OUT_BASE / f"konbu17_{label}.tar.gz"
        subprocess.run(
            ["tar", "-czf", str(tar_path), "-C", str(build_dir), "main.py", "weights.npz"],
            check=True,
        )
        sz = tar_path.stat().st_size
        print(f"  {label}: {tar_path} ({sz} bytes)  overrides={overrides}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
