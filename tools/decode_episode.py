"""Decode an Orbit Wars replay JSON into a per-step, per-player CSV.

Schema (one row per (step, player)):
    step               int
    player             0 | 1
    ships_total        sum of ships across owned planets + in-flight fleets
    planets_owned      number of planets owned
    fleets_count       number of fleets in flight owned by this player
    biggest_fleet      max fleet ship count (0 if no fleets)
    ships_in_flight    sum of ships across this player's fleets

Planet tuple in observation: (id, owner, x, y, radius, ships, production)
Fleet  tuple in observation: (id, owner, x, y, angle, from_planet_id, ships)

Example
-------
    python -m tools.decode_episode \\
        --json data/replays/episode-76156402-replay.json \\
        --output outputs/episode-76156402.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

# Index into the 7-tuple observations. Source of truth:
# kaggle_environments.envs.orbit_wars.orbit_wars.Planet / Fleet
PLANET_OWNER = 1
PLANET_SHIPS = 5
FLEET_OWNER = 1
FLEET_SHIPS = 6


def _load_replay(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {"steps": data}
    return data


def _decode(steps: list) -> pd.DataFrame:
    rows: list[dict] = []
    for step_idx, step in enumerate(steps):
        # `step` is a list of per-agent dicts. Each carries the same `observation`
        # of the world; we just need one of them (use index 0).
        if not step:
            continue
        obs = step[0].get("observation") or {}
        planets = obs.get("planets") or []
        fleets = obs.get("fleets") or []

        for player in (0, 1):
            owned_planets = [p for p in planets if int(p[PLANET_OWNER]) == player]
            my_fleets = [f for f in fleets if int(f[FLEET_OWNER]) == player]
            ships_on_planets = sum(int(p[PLANET_SHIPS]) for p in owned_planets)
            ships_flying = sum(int(f[FLEET_SHIPS]) for f in my_fleets)
            biggest = max((int(f[FLEET_SHIPS]) for f in my_fleets), default=0)

            rows.append(
                {
                    "step": step_idx,
                    "player": player,
                    "ships_total": ships_on_planets + ships_flying,
                    "planets_owned": len(owned_planets),
                    "fleets_count": len(my_fleets),
                    "biggest_fleet": biggest,
                    "ships_in_flight": ships_flying,
                }
            )
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", dest="json_path", required=True)
    ap.add_argument("--output", required=True, help="output CSV path")
    args = ap.parse_args()

    json_path = Path(args.json_path)
    if not json_path.exists():
        print(f"error: not found: {json_path}", file=sys.stderr)
        return 2

    data = _load_replay(json_path)
    steps = data.get("steps") or []
    if not steps:
        print("error: replay has no 'steps'", file=sys.stderr)
        return 2

    df = _decode(steps)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"wrote {out} ({len(df)} rows, {len(steps)} steps x 2 players)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
