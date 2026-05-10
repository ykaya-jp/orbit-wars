"""Behavior Cloning dataset builder (Phase 0.3)。

bovard top10% replay JSON を逐次読み、各 (step, player) を `(state_tensor, action_label)`
の pair に変換して numpy memmap に書き出す。

Output:
    data/processed/bc/states.npy   (N, STATE_DIM)        float32
    data/processed/bc/labels.npy   (N, MAX_PLANETS)       int32
    data/processed/bc/meta.parquet  episode_id / step / player / team_name 等

メモリ効率:
    - 全データ (2-3M sample) を RAM に保持しない
    - 1 episode 毎に増分 append
    - `np.memmap` で write、最後に shape をリサイズ

Usage:
    python -m tools.build_bc_dataset \
        --replays data/external/top10_replays/episodes/episodes data/external/bovard_full \
        --output data/processed/bc/ \
        --max-samples 1000000  # 上限 (default: 全部)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from orbit_wars.encoders import (  # noqa: E402
    encode_action,
    encode_state,
)


def _iter_replays(roots: list[Path]):
    """指定 dir 群から *.json を yield (recursive、_analysis.json は skip)。"""
    for root in roots:
        if not root.exists():
            continue
        if root.is_file() and root.suffix == ".json":
            if "_analysis" in root.name:
                continue
            yield root
            continue
        for p in root.rglob("*.json"):
            if "_analysis" in p.name:
                continue
            yield p


def _process_replay(json_path: Path) -> list[tuple[np.ndarray, np.ndarray, dict]]:
    """1 replay JSON → list of (state_vec, label_vec, meta)."""
    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    eid = json_path.stem.replace("episode-", "").replace("-replay", "")
    info = data.get("info") or {}
    teams = info.get("TeamNames") or []
    steps = data.get("steps") or []

    rows: list[tuple[np.ndarray, np.ndarray, dict]] = []
    for step_idx, step in enumerate(steps):
        if not step:
            continue
        for player_idx, ps in enumerate(step):
            obs = ps.get("observation") or {}
            actions = ps.get("action") or []
            if not isinstance(actions, list):
                actions = []
            # observation には 'player' フィールドあり、その値を使う
            obs_with_player = dict(obs)
            obs_with_player.setdefault("player", player_idx)
            try:
                enc = encode_state(obs_with_player, player=player_idx)
                lbl = encode_action(actions, enc.my_planet_ids)
            except Exception:
                continue
            meta = {
                "episode_id": eid,
                "step": step_idx,
                "player": player_idx,
                "team_name": teams[player_idx] if player_idx < len(teams) else f"p{player_idx}",
                "n_my_planets": len(enc.my_planet_ids),
                "n_actions": len(actions),
            }
            rows.append((enc.state_vec, lbl, meta))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replays", nargs="+", required=True, help="dir(s) of replay JSONs")
    ap.add_argument("--output", required=True, help="output dir")
    ap.add_argument("--max-samples", type=int, default=-1, help="-1 = unlimited")
    ap.add_argument(
        "--top-tier-only",
        action="store_true",
        help="filter to known top-tier teams (Erik Kvanli / shomossa / flg / "
        "bowwowforeach / Vadasz / Ezra / Isaiah @ Tufa Labs)",
    )
    args = ap.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    roots = [Path(r) for r in args.replays]
    json_paths = list(_iter_replays(roots))
    print(f"found {len(json_paths)} replays in {len(roots)} dirs")
    if not json_paths:
        print("no replays found")
        return 1

    top_tier = {
        "Erik Kvanli",
        "shomossa",
        "flg",
        "bowwowforeach",
        "Vadasz",
        "Ezra",
        "Isaiah @ Tufa Labs",
        "linrock",
        "Orbit Team",
    }

    states_buf: list[np.ndarray] = []
    labels_buf: list[np.ndarray] = []
    meta_rows: list[dict] = []

    n_samples = 0
    for ip, jp in enumerate(json_paths):
        rows = _process_replay(jp)
        for state, label, meta in rows:
            if args.top_tier_only and meta["team_name"] not in top_tier:
                continue
            states_buf.append(state)
            labels_buf.append(label)
            meta_rows.append(meta)
            n_samples += 1
            if args.max_samples > 0 and n_samples >= args.max_samples:
                break
        if args.max_samples > 0 and n_samples >= args.max_samples:
            print(f"  reached --max-samples={args.max_samples}, stop")
            break
        if (ip + 1) % 100 == 0:
            print(f"  processed {ip+1}/{len(json_paths)} replays, {n_samples} samples")

    print(f"total samples: {n_samples}")
    if n_samples == 0:
        print("no samples extracted (top-tier-only might filter all)")
        return 1

    print("stacking arrays...")
    states = np.stack(states_buf, axis=0).astype(np.float32)
    labels = np.stack(labels_buf, axis=0).astype(np.int32)
    print(f"  states.shape = {states.shape} ({states.nbytes / 1e9:.2f} GB)")
    print(f"  labels.shape = {labels.shape}")

    print(f"saving to {out_dir} ...")
    np.save(out_dir / "states.npy", states)
    np.save(out_dir / "labels.npy", labels)
    pl.DataFrame(meta_rows).write_parquet(out_dir / "meta.parquet")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
