"""Render a Kaggle replay JSON to a standalone HTML file.

Two replay JSON shapes are supported:
1. Full env dump (the format `kaggle competitions replay` produces): the JSON
   contains `configuration`, `specification`, `steps`, etc. We reconstruct the
   env by `make()` and overwrite its internal fields, then call `render(html)`.
2. Steps-only blob: a list (or `{"steps": [...]}`) — we still wrap it via the
   same path.

Example
-------
    python -m tools.replay_viewer \\
        --json data/replays/episode-76156402-replay.json \\
        --output outputs/replays/episode-76156402.html
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_replay(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {"steps": data}
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", dest="json_path", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--env", default="orbit_wars")
    args = ap.parse_args()

    json_path = Path(args.json_path)
    if not json_path.exists():
        print(f"error: not found: {json_path}", file=sys.stderr)
        return 2

    data = _load_replay(json_path)
    steps = data.get("steps")
    if not steps:
        print("error: replay has no 'steps'", file=sys.stderr)
        return 2

    from kaggle_environments import make

    # Use embedded configuration if present (matches replay seed/parameters).
    cfg = data.get("configuration") or {}
    env = make(args.env, configuration=cfg, debug=False)
    env.steps = steps
    if "rewards" in data:
        env.state = steps[-1]  # ensure final-state-derived calls have something to look at

    html = env.render(mode="html")
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path} ({len(html):,} bytes, {len(steps)} steps)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
