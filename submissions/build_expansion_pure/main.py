"""Expansion-priority rule agent (P3): bovard 真因解析の expansion gap solver.

戦略:
  - ExpansionPriorityMission: 早期 game (step ≤ 150) で nearby cluster を rapid expand
    (= capture_buffer 8 で post-capture garrison 確保、 max_distance 35 で chain expansion)
  - CaptureMission: late game / capacity 不足時の通常 ROI 拡張
  - CometGrabMission: 彗星反応的占領
  - RecaptureMission: 失った惑星奪還
  - DefenseMission: 脅威 incoming への garrison 強化
  - FleetAggregationMission: 複数 home から oversized target を奪取

Dispatcher が score 降順 + planet capacity 競合解決。
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from orbit_wars.missions import (
    CaptureMission,
    CometGrabMission,
    DefenseMission,
    Dispatcher,
    ExpansionPriorityMission,
    FleetAggregationMission,
    RecaptureMission,
    parse_observation,
)

_dispatcher = Dispatcher(
    [
        ExpansionPriorityMission(),
        RecaptureMission(),
        DefenseMission(),
        CometGrabMission(),
        FleetAggregationMission(),
        CaptureMission(),
    ]
)


def agent(observation, configuration=None):
    state = parse_observation(observation, configuration)
    return _dispatcher.step(state)
