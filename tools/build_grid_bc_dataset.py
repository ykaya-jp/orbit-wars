"""Build BC dataset for SE-ResNet grid encoder (Phase η v2).

Reads bovard top10 replay JSONs, encodes each (step, player) frame via
grid_encoder, and saves arrays for PyTorch training.

Output:
    data/processed/grid_bc/spatial.npy   (N, 14, 64, 64) float16 (= save 2× space)
    data/processed/grid_bc/globals.npy   (N, 9) float32
    data/processed/grid_bc/labels.npy    (N, 64, 64) int8 (-128 = ignore)
    data/processed/grid_bc/meta.parquet  episode_id / step / player / team

Notes:
    - float16 for spatial halves disk size (~14×64×64×4 = 224 KB → 112 KB per sample)
    - 158k samples × 112 KB = 17 GB (vs flat encoder's 0.5 GB) — manageable
    - For Phase η pilot, sample down to top-tier-only ≈ 60k samples (~7 GB)

Usage:
    python -m tools.build_grid_bc_dataset \\
        --replays data/external/top10_replays/episodes/episodes data/external/bovard_full \\
        --output data/processed/grid_bc/ \\
        --top-tier-only
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

from orbit_wars.grid_encoder import (  # noqa: E402
    encode_grid_action,
    encode_grid_state,
)

TOP_TIER_TEAMS = {
    "Erik Kvanli",
    "shomossa",
    "flg",
    "bowwowforeach",
    "Vadasz",
    "Ezra",
    "Isaiah @ Tufa Labs",
    "linrock",
    "Orbit Team",
    "Sliver Legion",
    "NightlyOrbit",
    "ymg_aq",
    "HY2017",
    "Shun_PI",
    "kovi",
    "Erfan Eshratifar",
    "ShunkiKyoya",
    "sash",
    "Ousagi",
    "lookaside",
    "klog",
}


def _process_replay(json_path: Path, top_tier_only: bool):
    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    eid = json_path.stem.replace("episode-", "").replace("-replay", "")
    info = data.get("info") or {}
    teams = info.get("TeamNames") or []
    steps = data.get("steps") or []

    rows = []
    for step_idx, step in enumerate(steps):
        if not step:
            continue
        for player_idx, ps in enumerate(step):
            team = teams[player_idx] if player_idx < len(teams) else f"p{player_idx}"
            if top_tier_only and team not in TOP_TIER_TEAMS:
                continue
            obs = ps.get("observation") or {}
            actions = ps.get("action") or []
            obs_with_player = dict(obs)
            obs_with_player.setdefault("player", player_idx)
            try:
                enc = encode_grid_state(obs_with_player, player=player_idx)
                lbl = encode_grid_action(actions, enc.my_cells)
            except Exception:
                continue
            if not enc.my_cells:
                continue  # no own planets — skip
            rows.append(
                (
                    enc.spatial,
                    enc.globals_,
                    lbl,
                    {
                        "episode_id": eid,
                        "step": step_idx,
                        "player": player_idx,
                        "team_name": team,
                        "n_my_planets": len(enc.my_cells),
                    },
                )
            )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replays", nargs="+", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--top-tier-only", action="store_true")
    ap.add_argument("--max-samples", type=int, default=-1)
    args = ap.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_paths = []
    for r in args.replays:
        rp = Path(r)
        if rp.is_file() and rp.suffix == ".json":
            json_paths.append(rp)
        elif rp.is_dir():
            for p in rp.rglob("*.json"):
                if "_analysis" in p.name:
                    continue
                json_paths.append(p)
    print(f"found {len(json_paths)} replays")

    spatials = []
    globals_list = []
    labels_list = []
    metas = []

    for ip, jp in enumerate(json_paths):
        rows = _process_replay(jp, args.top_tier_only)
        for spatial, glb, lbl, meta in rows:
            spatials.append(spatial.astype(np.float16))
            globals_list.append(glb)
            labels_list.append(lbl.astype(np.int8))
            metas.append(meta)
            if args.max_samples > 0 and len(spatials) >= args.max_samples:
                break
        if args.max_samples > 0 and len(spatials) >= args.max_samples:
            break
        if (ip + 1) % 100 == 0:
            print(f"  processed {ip+1}/{len(json_paths)}, {len(spatials)} samples")

    print(f"total samples: {len(spatials)}")
    if not spatials:
        return 1

    spatial_arr = np.stack(spatials, axis=0)
    globals_arr = np.stack(globals_list, axis=0).astype(np.float32)
    labels_arr = np.stack(labels_list, axis=0)
    print(f"  spatial: {spatial_arr.shape} {spatial_arr.dtype} ({spatial_arr.nbytes/1e9:.2f} GB)")
    print(f"  globals: {globals_arr.shape}")
    print(f"  labels:  {labels_arr.shape}")

    np.save(out_dir / "spatial.npy", spatial_arr)
    np.save(out_dir / "globals.npy", globals_arr)
    np.save(out_dir / "labels.npy", labels_arr)
    pl.DataFrame(metas).write_parquet(out_dir / "meta.parquet")
    print(f"saved {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
