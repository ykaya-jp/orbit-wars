"""Build (24-dim shot feature, success label) dataset from bovard top10 replays.

Replicates konbu17 hybrid's `_encode_shot_np` and label semantics:
  - feature: 24-dim float32 (source/target/shot/in-flight/meta)
  - label:   1 iff target.owner == src_owner at any turn in [arrival, arrival+10]
             excluded: self-reinforcement (target already owned by src_owner)

Output:
    data/processed/validator/feats.npy   (N, 24) float32
    data/processed/validator/labels.npy  (N,) int8
    data/processed/validator/meta.parquet  episode_id, step, player, team_name

Usage:
    python -m tools.build_validator_dataset \
        --replays data/external/top10_replays/episodes/episodes data/external/bovard_full \
        --output data/processed/validator/ \
        --top-tier-only
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import polars as pl

BOARD = 100.0
MAX_SPEED = 6.0
ARRIVAL_LOOKAHEAD = 10  # turns after arrival to check target ownership

# planet tuple: (id, owner, x, y, radius, ships, production)
# fleet  tuple: (id, owner, x, y, angle, from_planet_id, ships)
P_ID, P_OWNER, P_X, P_Y, P_R, P_SHIPS, P_PROD = 0, 1, 2, 3, 4, 5, 6
F_ID, F_OWNER, F_X, F_Y, F_ANGLE, F_FROM, F_SHIPS = 0, 1, 2, 3, 4, 5, 6


def _encode_shot(obs: dict, src_id: int, target_id: int, ships_sent: int) -> np.ndarray | None:
    """konbu17 _encode_shot_np と同じ feature."""
    planets = obs.get("planets") or []
    fleets = obs.get("fleets") or []
    me = int(obs.get("player", 0) or 0)
    pdict = {int(p[P_ID]): p for p in planets}
    if src_id not in pdict or target_id not in pdict:
        return None
    src = pdict[src_id]
    tgt = pdict[target_id]
    sx, sy, sr, ss, sp = (
        float(src[P_X]),
        float(src[P_Y]),
        float(src[P_R]),
        int(src[P_SHIPS]),
        int(src[P_PROD]),
    )
    tgt_owner = int(tgt[P_OWNER])
    tx, ty, tr, ts, tp = (
        float(tgt[P_X]),
        float(tgt[P_Y]),
        float(tgt[P_R]),
        int(tgt[P_SHIPS]),
        int(tgt[P_PROD]),
    )

    my_ships = sum(int(p[P_SHIPS]) for p in planets if int(p[P_OWNER]) == me)
    enemy_ships = sum(
        int(p[P_SHIPS]) for p in planets if int(p[P_OWNER]) >= 0 and int(p[P_OWNER]) != me
    )
    my_pl = sum(1 for p in planets if int(p[P_OWNER]) == me)
    enemy_pl = sum(1 for p in planets if int(p[P_OWNER]) >= 0 and int(p[P_OWNER]) != me)

    dist = max(math.hypot(tx - sx, ty - sy) - sr - tr, 0.0)
    if ships_sent <= 0:
        speed = 1.0
    else:
        speed = 1.0 + (MAX_SPEED - 1.0) * (math.log(max(ships_sent, 1)) / math.log(1000.0)) ** 1.5
    eta = dist / max(speed, 0.5)

    own_self = 1.0 if tgt_owner == me else 0.0
    own_neutral = 1.0 if tgt_owner < 0 else 0.0
    own_enemy = 1.0 if (tgt_owner >= 0 and tgt_owner != me) else 0.0

    ship_frac = ships_sent / max(ss, 1)
    ally_n = sum(1 for f in fleets if int(f[F_OWNER]) == me)
    ally_s = sum(int(f[F_SHIPS]) for f in fleets if int(f[F_OWNER]) == me)
    enemy_n = sum(1 for f in fleets if int(f[F_OWNER]) != me)
    enemy_s = sum(int(f[F_SHIPS]) for f in fleets if int(f[F_OWNER]) != me)

    turn = int(obs.get("step", 0) or 0)

    return np.array(
        [
            ss / 100.0,
            sp / 5.0,
            sr / 4.0,
            ts / 100.0,
            tp / 5.0,
            tr / 4.0,
            own_self,
            own_neutral,
            own_enemy,
            ships_sent / 100.0,
            ship_frac,
            dist / BOARD,
            eta / 60.0,
            speed / MAX_SPEED,
            ally_n / 10.0,
            ally_s / 100.0,
            enemy_n / 10.0,
            enemy_s / 100.0,
            turn / 500.0,
            my_ships / 200.0,
            enemy_ships / 200.0,
            (my_ships - enemy_ships) / 200.0,
            my_pl / 20.0,
            enemy_pl / 20.0,
        ],
        dtype=np.float32,
    )


def _find_target_id(action: list, planets: list) -> int | None:
    """fleet が向かう target を line trajectory で推定 (konbu17 _find_target_ray と同様)."""
    if len(action) < 3:
        return None
    src_id = int(action[0])
    angle = float(action[1])
    pdict = {int(p[P_ID]): p for p in planets}
    if src_id not in pdict:
        return None
    src = pdict[src_id]
    sx, sy = float(src[P_X]), float(src[P_Y])
    fx, fy = math.cos(angle), math.sin(angle)
    best_pid: int | None = None
    best_perp = 1e9
    for p in planets:
        pid = int(p[P_ID])
        if pid == src_id:
            continue
        px, py, pr = float(p[P_X]), float(p[P_Y]), float(p[P_R])
        dx, dy = px - sx, py - sy
        t = dx * fx + dy * fy
        if t <= 0 or t > 200:
            continue
        perp = abs(dx * fy - dy * fx)
        if perp <= pr + 1.0 and perp < best_perp:
            best_perp = perp
            best_pid = pid
    return best_pid


def _process_replay(json_path: Path, top_tier: set | None = None) -> list[tuple]:
    """1 replay → list of (feat, label, meta dict)."""
    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    eid = json_path.stem.replace("episode-", "").replace("-replay", "")
    info = data.get("info") or {}
    teams = info.get("TeamNames") or []
    steps = data.get("steps") or []
    if not steps:
        return []

    rows: list[tuple] = []
    for step_idx, step_obs in enumerate(steps):
        if not step_obs:
            continue
        for player_idx, ps in enumerate(step_obs):
            team_name = teams[player_idx] if player_idx < len(teams) else f"p{player_idx}"
            if top_tier is not None and team_name not in top_tier:
                continue
            obs = ps.get("observation") or {}
            actions = ps.get("action") or []
            if not isinstance(actions, list) or not actions:
                continue
            obs_with_player = dict(obs)
            obs_with_player.setdefault("player", player_idx)
            planets = obs.get("planets") or []
            for act in actions:
                if not isinstance(act, list) or len(act) < 3:
                    continue
                src_id = int(act[0])
                ships_sent = int(act[2])
                if ships_sent <= 0:
                    continue

                # determine target via line trajectory
                target_id = _find_target_id(act, planets)
                if target_id is None:
                    continue

                # exclude self-reinforcement
                pdict = {int(p[P_ID]): p for p in planets}
                tgt = pdict.get(target_id)
                if tgt is None:
                    continue
                if int(tgt[P_OWNER]) == player_idx:
                    continue

                feat = _encode_shot(obs_with_player, src_id, target_id, ships_sent)
                if feat is None:
                    continue

                # estimate ETA using same formula
                src_p = pdict.get(src_id)
                if src_p is None:
                    continue
                dist = max(
                    math.hypot(
                        float(tgt[P_X]) - float(src_p[P_X]), float(tgt[P_Y]) - float(src_p[P_Y])
                    )
                    - float(src_p[P_R])
                    - float(tgt[P_R]),
                    0.0,
                )
                speed = (
                    1.0
                    + (MAX_SPEED - 1.0) * (math.log(max(ships_sent, 1)) / math.log(1000.0)) ** 1.5
                )
                eta = max(int(round(dist / max(speed, 0.5))), 1)
                arrival = step_idx + eta

                # check target ownership in window [arrival, arrival + ARRIVAL_LOOKAHEAD]
                end = min(arrival + ARRIVAL_LOOKAHEAD, len(steps) - 1)
                label = 0
                for k in range(arrival, end + 1):
                    if k >= len(steps) or not steps[k]:
                        break
                    obs_k = steps[k][0].get("observation") or {}
                    pls_k = obs_k.get("planets") or []
                    pdk = {int(p[P_ID]): p for p in pls_k}
                    tgt_k = pdk.get(target_id)
                    if tgt_k is None:
                        continue
                    if int(tgt_k[P_OWNER]) == player_idx:
                        label = 1
                        break

                rows.append(
                    (
                        feat,
                        label,
                        {
                            "episode_id": eid,
                            "step": step_idx,
                            "player": player_idx,
                            "team_name": team_name,
                            "target_id": target_id,
                            "ships_sent": ships_sent,
                            "eta": eta,
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

    top_tier = None
    if args.top_tier_only:
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
            "Sliver Legion",
            "NightlyOrbit",
            "ymg_aq",
            "HY2017",
        }

    json_paths: list[Path] = []
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

    feats: list[np.ndarray] = []
    labels: list[int] = []
    metas: list[dict] = []
    for ip, jp in enumerate(json_paths):
        rows = _process_replay(jp, top_tier=top_tier)
        for feat, lbl, meta in rows:
            feats.append(feat)
            labels.append(lbl)
            metas.append(meta)
        if (ip + 1) % 200 == 0:
            print(f"  processed {ip+1}/{len(json_paths)}, {len(feats)} samples")
        if args.max_samples > 0 and len(feats) >= args.max_samples:
            break

    print(f"total samples: {len(feats)}")
    if not feats:
        return 1

    feats_arr = np.stack(feats, axis=0).astype(np.float32)
    labels_arr = np.array(labels, dtype=np.int8)
    pos = int((labels_arr == 1).sum())
    neg = int((labels_arr == 0).sum())
    print(f"  feats: {feats_arr.shape}")
    print(f"  pos: {pos} ({pos / len(labels_arr) * 100:.1f}%)")
    print(f"  neg: {neg} ({neg / len(labels_arr) * 100:.1f}%)")

    np.save(out_dir / "feats.npy", feats_arr)
    np.save(out_dir / "labels.npy", labels_arr)
    pl.DataFrame(metas).write_parquet(out_dir / "meta.parquet")
    print(f"saved {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
