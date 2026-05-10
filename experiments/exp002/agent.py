"""Orbit Wars exp002 — mission-based agent.

Stage 1 では mission-based 意思決定で rule-base sniper を上回ることを目指す。
当面は `CaptureMission` のみ有効化 (Day 1-2 で sniper を 100% 勝率で上回ることを確認済)。

Day 3-4 で実装した `RecaptureMission` / `CometGrabMission` は **本番では無効化**。
理由は下記コメント参照。Day 5+ で `FleetAggregationMission` と協調させて再評価予定。

This file IS the submission entry point: `kaggle competitions submit -f main.py`.
"""

from __future__ import annotations

# Import strategy: try package-relative first (when imported as orbit_wars.agent),
# fall back to sibling-file import via sys.path (when kaggle_environments / Kaggle
# eval loads this file standalone — no __package__ context).
try:
    from .missions import (
        CaptureMission,
        CometGrabMission,
        Dispatcher,
        RecaptureMission,
        parse_observation,
    )
except (ImportError, KeyError):
    # kaggle_environments の `get_last_callable` は `sys.path.append(exec_dir)` を
    # 行ってから exec する (kaggle_environments/agent.py:51-53)。よって sibling
    # ファイルは module top-level からそのまま import できる。
    from missions import (  # type: ignore[no-redef]
        CaptureMission,
        CometGrabMission,
        Dispatcher,
        RecaptureMission,
        parse_observation,
    )

# Day 3-4 観測 (3 tournaments × 90 games each):
#   Recapture/Comet を enable すると v2 (Capture のみ) に対して 16.7% 勝率まで落ちた。
#   tightening (max_comet_ships=25, min_production=3) や multi-move dispatcher 化でも
#   改善せず。
# 原因仮説:
#   - "extra launch" が home の ship 蓄積を阻害する
#   - v2 の pure expansion は長期戦で復利を稼ぐ
#   - Recapture/Comet は単発で見ると ROI 正だが、複利な expansion を阻害する
# 結論:
#   - 新 mission classes は code として保持 (test カバー済)
#   - 本番 (production) は CaptureMission のみ enable
#   - Day 5+ で FleetAggregationMission を入れて、ships 余剰時のみ追加発射する
#     設計に変えてから enable を再検討
ENABLE_DAY3_MISSIONS: bool = False

_missions: list = [
    CaptureMission(
        reserve=5,
        max_fraction=0.85,
        margin=1,
        sun_safety_margin_deg=2.0,
    ),
]
if ENABLE_DAY3_MISSIONS:
    _missions = [
        RecaptureMission(reserve=5, max_fraction=0.85),
        CometGrabMission(reserve=5, max_fraction=0.85),
    ] + _missions

_DISPATCHER = Dispatcher(missions=_missions)


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
