"""Replay JSON → per-(step, player) action CSV を抽出する小型 ETL。

decode_episode.py が ship totals サマリだけ出すのに対し、本 script は **action 列**
(=`[[from_planet_id, angle, ships], ...]`) を保存する。後段の Behavior Cloning
データセット構築 (`tools/build_bc_dataset.py`) の前段。

Usage:
    python -m tools.extract_actions \
        --json data/replays/episode-76155725-replay.json \
        --output data/processed/actions/episode-76155725.parquet

    # bulk mode: data/replays/*.json を全部
    python -m tools.extract_actions --bulk data/replays --output data/processed/actions/

Output schema (parquet):
    episode_id     str
    step           int
    player         int (0|1)
    team_name      str        # observation 外、replay top-level rewards/info から
    n_actions      int        # この turn の発射数
    actions        list[list[float]]   # [[from_id, angle, ships], ...]
    n_my_planets   int
    n_my_fleets    int
    my_ships_total int
    enemy_ships_total int
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl


def _extract_one_replay(json_path: Path) -> list[dict]:
    """1 replay JSON から step × player の row を抽出。"""
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    eid = json_path.stem.replace("episode-", "").replace("-replay", "")
    info = data.get("info", {}) or {}
    teams = info.get("TeamNames") or [f"player_{i}" for i in range(len(data.get("rewards", [])))]
    steps = data.get("steps") or []

    rows: list[dict] = []
    for step_idx, step in enumerate(steps):
        if not step:
            continue
        for player_idx, ps in enumerate(step):
            obs = ps.get("observation") or {}
            actions = ps.get("action") or []
            if not isinstance(actions, list):
                actions = []

            planets = obs.get("planets") or []
            fleets = obs.get("fleets") or []
            # planet tuple: (id, owner, x, y, radius, ships, production)
            # fleet tuple:  (id, owner, x, y, angle, from_planet_id, ships)
            my_planets = [p for p in planets if int(p[1]) == player_idx]
            my_fleets = [f for f in fleets if int(f[1]) == player_idx]
            enemy_planets = [p for p in planets if int(p[1]) != player_idx and int(p[1]) != -1]
            enemy_fleets = [f for f in fleets if int(f[1]) != player_idx]

            my_ships = sum(int(p[5]) for p in my_planets) + sum(int(f[6]) for f in my_fleets)
            enemy_ships = sum(int(p[5]) for p in enemy_planets) + sum(
                int(f[6]) for f in enemy_fleets
            )

            rows.append(
                {
                    "episode_id": eid,
                    "step": step_idx,
                    "player": player_idx,
                    "team_name": teams[player_idx]
                    if player_idx < len(teams)
                    else f"player_{player_idx}",
                    "n_actions": len(actions),
                    "actions": [
                        [float(x) for x in a]
                        for a in actions
                        if isinstance(a, list) and len(a) >= 3
                    ],
                    "n_my_planets": len(my_planets),
                    "n_my_fleets": len(my_fleets),
                    "my_ships_total": my_ships,
                    "enemy_ships_total": enemy_ships,
                }
            )
    return rows


def _process(json_paths: list[Path], output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    for jp in json_paths:
        try:
            all_rows.extend(_extract_one_replay(jp))
        except Exception as e:  # noqa: BLE001
            print(f"  skip {jp.name}: {e}")
    if not all_rows:
        print("no rows extracted")
        return 1
    df = pl.DataFrame(all_rows)
    if output.suffix == ".parquet":
        df.write_parquet(output)
    elif output.suffix == ".csv":
        # CSV は list 列が苦手。actions を JSON 文字列化。
        df = df.with_columns(pl.col("actions").map_elements(json.dumps, return_dtype=pl.Utf8))
        df.write_csv(output)
    else:
        raise ValueError(f"unsupported output suffix: {output.suffix}")
    print(f"wrote {output} ({len(df)} rows from {len(json_paths)} replays)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="single replay JSON path")
    ap.add_argument("--bulk", help="directory of replay JSONs (recursive *.json)")
    ap.add_argument("--output", required=True, help="output .parquet or .csv path")
    args = ap.parse_args()

    if not args.json and not args.bulk:
        print("error: need --json or --bulk")
        return 2

    if args.json:
        return _process([Path(args.json)], Path(args.output))

    bulk_dir = Path(args.bulk)
    if not bulk_dir.is_dir():
        print(f"error: not a directory: {bulk_dir}")
        return 2
    json_paths = sorted(p for p in bulk_dir.rglob("*.json") if "_analysis" not in p.name)
    if not json_paths:
        print(f"no json files in {bulk_dir}")
        return 2
    return _process(json_paths, Path(args.output))


if __name__ == "__main__":
    raise SystemExit(main())
