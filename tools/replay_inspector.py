"""Step-by-step replay inspector for human (Claude) reading.

Print each turn's compact state in plain text so the reader can build intuition
about top-tier play. Designed for studying bowwowforeach / flg / Vadasz games.

Usage:
    python -m tools.replay_inspector \
        --json data/external/top10_replays/episodes/episodes/<EP>.json \
        --player 0 \
        --steps 0,25,50,100,150,200,300,400,499 \
        --players-detail
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def _fleet_speed(ships: int) -> float:
    if ships <= 1:
        return 1.0
    s = 1.0 + 5.0 * (math.log(ships) / math.log(1000.0)) ** 1.5
    return min(s, 6.0)


def _format_step(steps: list, step_idx: int, focus_player: int = 0) -> str:
    if step_idx >= len(steps):
        return f"step {step_idx}: out of range"
    step = steps[step_idx]
    if not step:
        return f"step {step_idx}: empty"
    obs = step[focus_player].get("observation") or {}
    planets = obs.get("planets") or []
    fleets = obs.get("fleets") or []
    omega = obs.get("angular_velocity", 0.0)

    n_players = len(step)
    out: list[str] = [
        f"\n{'='*70}\nstep {step_idx}  (focus = player {focus_player}, omega={omega:.4f})"
    ]

    # planets summary by owner
    owners: dict[int, list] = {}
    for p in planets:
        o = int(p[1])
        owners.setdefault(o, []).append(p)
    for o in sorted(owners):
        plist = owners[o]
        ships_total = sum(int(p[5]) for p in plist)
        prod_total = sum(int(p[6]) for p in plist)
        tag = "neutral" if o == -1 else f"player {o}"
        out.append(
            f"  {tag:>10s}: {len(plist):2d} planets, ships={ships_total:>5d}, prod/turn={prod_total:>2d}"
        )

    # fleets summary by owner
    fleet_by_owner: dict[int, list] = {}
    for f in fleets:
        fleet_by_owner.setdefault(int(f[1]), []).append(f)
    for o in sorted(fleet_by_owner):
        flist = fleet_by_owner[o]
        ships_total = sum(int(f[6]) for f in flist)
        biggest = max((int(f[6]) for f in flist), default=0)
        out.append(
            f"  player {o} fleets: {len(flist):2d} flying, ships={ships_total:>5d}, biggest={biggest:>4d}"
        )

    # actions per player at this step
    for pi in range(n_players):
        actions = step[pi].get("action") or []
        if not isinstance(actions, list) or not actions:
            continue
        for a in actions:
            if not isinstance(a, list) or len(a) < 3:
                continue
            from_id = int(a[0])
            angle = float(a[1])
            ships = int(a[2])
            v = _fleet_speed(ships)
            # find from planet to compute target line direction
            from_p = next((p for p in planets if int(p[0]) == from_id), None)
            tgt_text = ""
            if from_p:
                fx, fy = float(from_p[2]), float(from_p[3])
                cos_a, sin_a = math.cos(angle), math.sin(angle)
                # find planet on the ray
                best_pid = -1
                best_t = 200
                for p2 in planets:
                    if int(p2[0]) == from_id:
                        continue
                    dx = float(p2[2]) - fx
                    dy = float(p2[3]) - fy
                    t = dx * cos_a + dy * sin_a
                    if t <= 0:
                        continue
                    perp = abs(-dx * sin_a + dy * cos_a)
                    if perp <= float(p2[4]) + 1.0 and t < best_t:
                        best_t = t
                        best_pid = int(p2[0])
                if best_pid >= 0:
                    tgt_p = next(p for p in planets if int(p[0]) == best_pid)
                    eta = best_t / v
                    tgt_text = f" → target planet {best_pid} (owner={int(tgt_p[1])}, ships={int(tgt_p[5])}, prod={int(tgt_p[6])}, eta={eta:.0f}t)"
            angle_deg = math.degrees(angle)
            out.append(
                f"  player {pi} LAUNCH: from_planet {from_id} → angle={angle_deg:+6.1f}° ships={ships} (v={v:.1f}){tgt_text}"
            )

    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True, help="replay JSON path")
    ap.add_argument("--player", type=int, default=0, help="focus player ID")
    ap.add_argument(
        "--steps",
        default="0,5,10,25,50,75,100,150,200,250,300,350,400,450,499",
        help="comma-separated step indices to print (default: a sparse cross-section)",
    )
    ap.add_argument("--all", action="store_true", help="print all steps (verbose)")
    ap.add_argument(
        "--actions-only",
        action="store_true",
        help="print all steps where any player launched at least one fleet",
    )
    args = ap.parse_args()

    path = Path(args.json)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    teams = (data.get("info") or {}).get("TeamNames") or []
    rewards = data.get("rewards") or []
    steps = data.get("steps") or []

    print(f"replay: {path.name}")
    print(f"teams: {teams}")
    print(f"rewards: {rewards}")
    print(f"n_steps: {len(steps)}")

    if args.actions_only:
        for i, step in enumerate(steps):
            if not step:
                continue
            has_action = any(isinstance(ps.get("action"), list) and ps.get("action") for ps in step)
            if has_action:
                print(_format_step(steps, i, args.player))
    elif args.all:
        for i in range(len(steps)):
            print(_format_step(steps, i, args.player))
    else:
        for s in args.steps.split(","):
            i = int(s.strip())
            print(_format_step(steps, i, args.player))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
