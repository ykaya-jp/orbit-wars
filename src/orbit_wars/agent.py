"""Orbit Wars exp002 — mission-based agent (Stage 1 Day 1-2).

Stage 1 では `CaptureMission` のみで rule-base sniper を上回ることを目指す:
  - ROI ベースの target 選択 (近さだけでなく production も考慮)
  - 太陽 forbidden cone を回避する発射角
  - orbiting 惑星には lead-shot で命中角を計算
  - sniper の RESERVE / MAX_FRACTION / MARGIN は維持 (= 後方互換)

Day 3-11 で Defense / CometGrab / Recapture / FleetAggregation / Snipe / Swarm を追加予定。

This file IS the submission entry point: `kaggle competitions submit -f main.py`.
"""

from __future__ import annotations

import math

# Import strategy: try package-relative first (when imported as orbit_wars.agent),
# fall back to sibling-file import via sys.path (when kaggle_environments / Kaggle
# eval loads this file standalone — no __package__ context).
try:
    from .missions import CaptureMission, Dispatcher, parse_observation
except (ImportError, KeyError):
    # kaggle_environments の `get_last_callable` は `sys.path.append(exec_dir)` を
    # 行ってから exec する (kaggle_environments/agent.py:51-53)。よって sibling
    # ファイルは module top-level からそのまま import できる。
    from missions import CaptureMission, Dispatcher, parse_observation  # type: ignore[no-redef]

# Module-level singleton — episode 内でターンを跨いで保持される (将来 OpponentClassifier
# などの状態をここに持たせる)
_DISPATCHER = Dispatcher(
    missions=[
        CaptureMission(
            reserve=5,
            max_fraction=0.85,
            margin=1,
            sun_safety_margin_deg=2.0,
        ),
    ]
)


def agent(observation, configuration=None):
    """Per-turn 意思決定。kaggle_environments の `run([agent, opp])` から呼ばれる。

    例外時は安全側に倒して空 action リストを返す (= timeout や crash で agent が
    死ぬのを防ぐ)。
    """
    try:
        state = parse_observation(observation, configuration)
        return _DISPATCHER.step(state)
    except Exception:
        # 万が一の例外は黙って no-op (kaggle eval 環境で agent が落ちないように)
        return []


# ----- Backward-compat for inline submission as a single-file `main.py` -----
# Kaggle がこの module を import し直しで `agent` 関数だけ参照するので、
# package import が失敗するケースに備えてフォールバックを用意:
#   `from .missions import ...` が失敗した場合、`main.py` 単独でも動くよう
#   sniper logic を inline で持つ (現時点ではフォールバック未実装、Stage 2 で
#   submission_queue.py が tar.gz を使うようになったら撤去)
_USE_FALLBACK = False  # 通常は False、testing 用に True に切替可能


if _USE_FALLBACK:
    from kaggle_environments.envs.orbit_wars.orbit_wars import Planet

    RESERVE = 5
    MAX_FRACTION = 0.85
    MARGIN = 1

    def _capacity(p: Planet) -> int:
        return max(0, min(int(p.ships * MAX_FRACTION), p.ships - RESERVE))

    def _distance(a: Planet, b: Planet) -> float:
        return math.hypot(a.x - b.x, a.y - b.y)

    def agent(observation, configuration=None):  # noqa: F811
        if isinstance(observation, dict):
            get = observation.get
        else:

            def get(key, default=None):
                return getattr(observation, key, default)

        raw_planets = get("planets", []) or []
        player = get("player", 0) or 0
        planets = [Planet(*p) for p in raw_planets]
        my_planets = [p for p in planets if p.owner == player]
        targets = [p for p in planets if p.owner != player]
        if not my_planets or not targets:
            return []

        moves: list[list[float]] = []
        for mine in my_planets:
            cap = _capacity(mine)
            if cap <= 0:
                continue
            nearest = min(targets, key=lambda t: _distance(mine, t))
            ships_needed = nearest.ships + 1 + (MARGIN if nearest.owner != -1 else 0)
            if ships_needed > cap:
                continue
            angle = math.atan2(nearest.y - mine.y, nearest.x - mine.x)
            moves.append([mine.id, angle, int(ships_needed)])
        return moves
