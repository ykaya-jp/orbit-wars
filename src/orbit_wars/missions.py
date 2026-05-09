"""orbit-wars Stage 1: mission-based 意思決定フレームワーク。

各 mission は GameState を受け取り `(score, moves)` を返す。Dispatcher は
全 mission の moves を集約、惑星単位の競合は score 順で解決。

Stage 1 Day 1-2 では `CaptureMission` のみ実装。後続 mission (Defense,
CometGrab, Recapture, FleetAggregation, Snipe, Swarm) は Day 3-11 で追加。

Mission スコア仕様:
    - score == 0  → mission 非適用 (no-op)
    - score > 0   → 適用、複数 mission が同じ from_planet を狙ったら高 score 優先
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from kaggle_environments.envs.orbit_wars.orbit_wars import Fleet, Planet

# Import strategy: package-relative when imported as orbit_wars.missions, otherwise
# sibling-file via sys.path (kaggle_environments / Kaggle eval = standalone file load).
try:
    from . import physics
except (ImportError, KeyError):
    # kaggle_environments の exec_dir は sys.path に追加済 → 直接 import 可能。
    import physics  # type: ignore[no-redef]


# ============================================================================
# GameState: 1 turn 分の盤面 snapshot
# ============================================================================


@dataclass
class GameState:
    """parse 済 observation。"""

    player: int
    step: int
    planets: list[Planet]
    fleets: list[Fleet]
    angular_velocity: float
    initial_planets: list[Planet]
    comet_planet_ids: set[int]

    @property
    def my_planets(self) -> list[Planet]:
        return [p for p in self.planets if p.owner == self.player]

    @property
    def enemy_planets(self) -> list[Planet]:
        return [p for p in self.planets if p.owner != self.player and p.owner != -1]

    @property
    def neutral_planets(self) -> list[Planet]:
        return [p for p in self.planets if p.owner == -1]

    @property
    def my_fleets(self) -> list[Fleet]:
        return [f for f in self.fleets if f.owner == self.player]

    @property
    def enemy_fleets(self) -> list[Fleet]:
        return [f for f in self.fleets if f.owner != self.player]


@dataclass
class Move:
    """1 つの艦隊発射 = `[from_planet_id, fire_angle_radians, num_ships]`."""

    from_planet_id: int
    angle: float
    ships: int

    def to_action(self) -> list[float]:
        return [self.from_planet_id, self.angle, int(self.ships)]


# ============================================================================
# Mission Protocol
# ============================================================================


class Mission(Protocol):
    """各 mission が実装する interface。"""

    name: str

    def evaluate(self, state: GameState) -> tuple[float, list[Move]]:
        """`(total_score, moves)` を返す。score=0 は非適用。"""
        ...


# ============================================================================
# Observation parser
# ============================================================================


def parse_observation(observation, configuration=None) -> GameState:
    """raw observation (dict-like) を `GameState` にパース。"""
    if isinstance(observation, dict):
        get = observation.get
    else:

        def get(key, default=None):
            return getattr(observation, key, default)

    raw_planets = get("planets", []) or []
    raw_fleets = get("fleets", []) or []
    raw_initial = get("initial_planets", []) or []

    return GameState(
        player=int(get("player", 0) or 0),
        step=int(get("step", 0) or 0),
        planets=[Planet(*p) for p in raw_planets],
        fleets=[Fleet(*f) for f in raw_fleets],
        angular_velocity=float(get("angular_velocity", 0.0) or 0.0),
        initial_planets=[Planet(*p) for p in raw_initial],
        comet_planet_ids=set(get("comet_planet_ids", []) or []),
    )


# ============================================================================
# CaptureMission: sniper の動的 sizing 強化版
# ============================================================================


class CaptureMission:
    """非所有惑星を ROI 順に占領する mission。

    sniper との差分:
      1. ROI で target を選ぶ (近さだけでなく production も考慮)
      2. 敵惑星には MARGIN を上乗せ
      3. 太陽通過 (forbidden cone) を avoid
      4. orbiting target には lead-shot で命中角を計算
      5. RESERVE と MAX_FRACTION で home の枯渇を防ぐ (sniper 互換)

    Capacity gap (失敗モード #1) は本 mission では完全には解消しない —
    `garrison + 1 + MARGIN` を超える target は skip。後続 `FleetAggregationMission`
    で複数 home から合流させる予定。
    """

    name = "capture"

    def __init__(
        self,
        reserve: int = 5,
        max_fraction: float = 0.85,
        margin: int = 1,
        sun_safety_margin_deg: float = 2.0,
    ):
        self.reserve = reserve
        self.max_fraction = max_fraction
        self.margin = margin
        self.sun_margin_rad = math.radians(sun_safety_margin_deg)

    def _capacity(self, planet: Planet) -> int:
        """この惑星から発射可能な最大 ship 数。"""
        return max(0, min(int(planet.ships * self.max_fraction), planet.ships - self.reserve))

    def _ships_needed(self, target: Planet) -> int:
        """占領に必要な ship 数 (敵惑星は MARGIN 上乗せ)。"""
        if target.owner == -1:
            return target.ships + 1
        return target.ships + 1 + self.margin

    def _aim_angle(self, mine: Planet, target: Planet, ships: int, state: GameState) -> float:
        """target への発射角を決定 (orbital なら lead-shot、太陽 forbidden cone を回避)。"""
        # Lead-shot if orbiting
        if state.angular_velocity != 0.0 and physics.is_orbiting(target.x, target.y, target.radius):
            cx, cy = physics.CENTER
            dx, dy = target.x - cx, target.y - cy
            target_orbit_r = math.hypot(dx, dy)
            target_init_angle = math.atan2(dy, dx)
            result = physics.lead_angle_orbital(
                mine.x,
                mine.y,
                target_orbit_r,
                target_init_angle,
                state.angular_velocity,
                ships,
            )
            if result is not None:
                angle, _t_arr = result
            else:
                angle = math.atan2(target.y - mine.y, target.x - mine.x)
        else:
            angle = math.atan2(target.y - mine.y, target.x - mine.x)

        # Sun forbidden cone を回避
        return physics.safe_angle_around(mine.x, mine.y, angle, margin=self.sun_margin_rad)

    def evaluate(self, state: GameState) -> tuple[float, list[Move]]:
        targets = state.enemy_planets + state.neutral_planets
        if not targets or not state.my_planets:
            return 0.0, []

        moves: list[Move] = []
        score_total = 0.0

        for mine in state.my_planets:
            cap = self._capacity(mine)
            if cap <= 0:
                continue

            # 全 target を ROI で評価、capacity 内で最大 ROI を採用
            best: tuple[Planet, int, float] | None = None
            best_roi = 0.0
            for t in targets:
                ships_needed = self._ships_needed(t)
                if ships_needed > cap:
                    continue
                # travel_time の近似 (orbital でも static で見積もる、誤差小さい)
                _angle, t_arr = physics.lead_angle_static(mine.x, mine.y, t.x, t.y, ships_needed)
                roi_val = physics.roi(t.production, ships_needed, t_arr)
                if roi_val > best_roi:
                    best_roi = roi_val
                    best = (t, ships_needed, t_arr)

            if best is None:
                continue

            target, ships, _ = best
            angle = self._aim_angle(mine, target, ships, state)
            moves.append(Move(mine.id, angle, ships))
            score_total += best_roi

        return score_total, moves


# ============================================================================
# Dispatcher: mission 群を統合して final action list を出す
# ============================================================================


@dataclass
class _PlannedMove:
    move: Move
    score: float
    mission_name: str


class Dispatcher:
    """登録された mission 群を順に呼び、惑星競合は score 順で解決。

    Strategy:
      1. 各 mission を evaluate
      2. mission の score を全 moves に均等配分 (= score / len(moves))
         → mission 全体が高評価なら、その mission の各 move が優先される
      3. 同じ from_planet_id を狙う move があれば高 score 採用
      4. 最終的に planet ごとに 1 つの action を返す

    将来的に「1 turn で複数 fleet を同 planet から発射」も許容するなら
    この dispatcher を拡張する (現状は 1 planet → 1 move)。
    """

    def __init__(self, missions: Sequence[Mission]):
        self.missions = list(missions)

    def step(self, state: GameState) -> list[list[float]]:
        per_planet: dict[int, _PlannedMove] = {}

        for mission in self.missions:
            score, moves = mission.evaluate(state)
            if score <= 0.0 or not moves:
                continue
            # 各 move の優先度 = mission の合計 score / move 数
            move_score = score / max(len(moves), 1)
            for m in moves:
                planned = _PlannedMove(m, move_score, mission.name)
                existing = per_planet.get(m.from_planet_id)
                if existing is None or planned.score > existing.score:
                    per_planet[m.from_planet_id] = planned

        return [pm.move.to_action() for pm in per_planet.values()]
