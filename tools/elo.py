"""TrueSkill-backed ELO ledger for Orbit Wars agents.

Ledger format (JSON, one file at repo root by default)::

    {
        "src/orbit_wars/agent.py": {"mu": 26.4, "sigma": 6.1, "n_games": 12},
        "random": {"mu": 18.2, "sigma": 6.0, "n_games": 12},
        ...
    }

We use TrueSkill (Microsoft) under the hood. The conservative rank we surface
in `show` is `mu - 3*sigma` — TrueSkill's standard "skill we are 99% sure they
exceed" estimate. Higher = better.

Subcommands
-----------
    update --from <csv>     apply each row's outcome to the ledger
    show                    print top agents by mu - 3*sigma
    reset                   delete the ledger (with confirmation)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import trueskill

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEDGER = REPO_ROOT / "elo.json"


def _load(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: Path, data: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    tmp.replace(path)


def _get_rating(ledger: dict[str, dict], name: str) -> trueskill.Rating:
    e = ledger.get(name)
    if e is None:
        return trueskill.Rating()
    return trueskill.Rating(mu=e["mu"], sigma=e["sigma"])


def _put_rating(ledger: dict[str, dict], name: str, r: trueskill.Rating, delta_games: int) -> None:
    prev_n = ledger.get(name, {}).get("n_games", 0)
    ledger[name] = {
        "mu": float(r.mu),
        "sigma": float(r.sigma),
        "n_games": int(prev_n + delta_games),
    }


def cmd_update(args: argparse.Namespace) -> int:
    csv_path = Path(args.from_csv)
    if not csv_path.is_absolute():
        csv_path = REPO_ROOT / csv_path
    if not csv_path.exists():
        print(f"error: csv not found: {csv_path}", file=sys.stderr)
        return 2

    ledger_path = Path(args.ledger)
    if not ledger_path.is_absolute():
        ledger_path = REPO_ROOT / ledger_path
    ledger = _load(ledger_path)

    applied = 0
    skipped = 0
    drawn = 0
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            left = row["agent_left_path"]
            right = row["agent_right_path"]
            try:
                rl = float(row["agent_left_reward"])
                rr = float(row["agent_right_reward"])
            except (KeyError, ValueError):
                skipped += 1
                continue

            # Skip rows with errors / non-DONE statuses — they aren't valid outcomes.
            status_l = row.get("status_left", "DONE")
            status_r = row.get("status_right", "DONE")
            if status_l != "DONE" or status_r != "DONE":
                skipped += 1
                continue

            r_left = _get_rating(ledger, left)
            r_right = _get_rating(ledger, right)

            if rl > rr:
                new_left, new_right = trueskill.rate_1vs1(r_left, r_right)
            elif rr > rl:
                new_right, new_left = trueskill.rate_1vs1(r_right, r_left)
            else:
                new_left, new_right = trueskill.rate_1vs1(r_left, r_right, drawn=True)
                drawn += 1

            _put_rating(ledger, left, new_left, 1)
            _put_rating(ledger, right, new_right, 1)
            applied += 1

    _save(ledger_path, ledger)
    print(f"applied {applied} games ({drawn} draws), skipped {skipped} rows -> {ledger_path}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger)
    if not ledger_path.is_absolute():
        ledger_path = REPO_ROOT / ledger_path
    ledger = _load(ledger_path)
    if not ledger:
        print(f"(empty ledger at {ledger_path})")
        return 0

    rows = [
        (name, e["mu"], e["sigma"], e["mu"] - 3 * e["sigma"], e["n_games"])
        for name, e in ledger.items()
    ]
    rows.sort(key=lambda r: r[3], reverse=True)
    rows = rows[: args.top]

    name_w = max(len("agent"), max(len(r[0]) for r in rows))
    print(f"{'agent'.ljust(name_w)}  {'mu':>7}  {'sigma':>7}  {'rank':>7}  {'n':>4}")
    print(f"{'-' * name_w}  {'-' * 7}  {'-' * 7}  {'-' * 7}  {'-' * 4}")
    for name, mu, sigma, conservative, n in rows:
        print(f"{name.ljust(name_w)}  {mu:7.3f}  {sigma:7.3f}  {conservative:7.3f}  {n:4d}")
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger)
    if not ledger_path.is_absolute():
        ledger_path = REPO_ROOT / ledger_path
    if not ledger_path.exists():
        print(f"(no ledger at {ledger_path})")
        return 0

    if args.yes:
        ledger_path.unlink()
        print(f"deleted {ledger_path}")
        return 0

    sys.stdout.write(f"delete {ledger_path}? type 'yes' to confirm: ")
    sys.stdout.flush()
    answer = sys.stdin.readline().strip().lower()
    if answer == "yes":
        ledger_path.unlink()
        print(f"deleted {ledger_path}")
        return 0
    print("aborted.")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--ledger",
        default=str(DEFAULT_LEDGER),
        help=f"path to ledger json (default: {DEFAULT_LEDGER})",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_up = sub.add_parser("update", help="apply tournament rows to ledger")
    p_up.add_argument("--from", dest="from_csv", required=True, help="tournament csv")
    p_up.set_defaults(func=cmd_update)

    p_show = sub.add_parser("show", help="print top agents")
    p_show.add_argument("--top", type=int, default=20)
    p_show.set_defaults(func=cmd_show)

    p_reset = sub.add_parser("reset", help="delete the ledger")
    p_reset.add_argument("--yes", action="store_true", help="skip confirmation")
    p_reset.set_defaults(func=cmd_reset)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
