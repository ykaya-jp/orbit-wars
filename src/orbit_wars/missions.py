"""orbit-wars Stage 1: mission-based 意思決定フレームワーク。

各 mission は GameState を受け取り `(score, moves)` を返す。Dispatcher は
全 mission の moves を集約、惑星単位の競合は score 順で解決。

実装 mission:
  - CaptureMission           : 非所有惑星を ROI 順で占領 (Day 1-2)
  - CometGrabMission         : 彗星を反応的に占領 (Day 3-4)
  - RecaptureMission         : 失った惑星を奪還 (Day 3-4)
  - FleetAggregationMission  : 複数 home から oversized target を奪取 (Day 5)

未実装 (Day 6+):
  - DefenseMission, SnipeMission, SwarmMission, HoldMission

Mission スコア仕様:
    - score == 0  → mission 非適用 (no-op)
    - score > 0   → 適用、複数 mission が同じ from_planet を狙ったら高 score 優先
    - mission ごとに score の絶対値で優先順位がつく:
        Recapture (10x base) >> Comet (5x) > Capture (1x ROI) ≈ Aggregation (1x ROI)
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

    @property
    def comet_planets(self) -> list[Planet]:
        return [p for p in self.planets if p.id in self.comet_planet_ids]


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
# _BaseMission: 共通 capacity 計算 / aim 角度計算 / episode reset 検知
# ============================================================================


class _BaseMission:
    """全 mission の共通処理を持つベース class。

    継承先で `name` と `evaluate(state)` を実装する。`_maybe_new_episode(state)` を
    `evaluate` の冒頭で呼ぶと `_on_new_episode()` (override hook) が走る。
    """

    name: str = "_base"

    def __init__(
        self,
        reserve: int = 5,
        max_fraction: float = 0.85,
        sun_safety_margin_deg: float = 2.0,
    ):
        self.reserve = reserve
        self.max_fraction = max_fraction
        self.sun_margin_rad = math.radians(sun_safety_margin_deg)
        self._last_step: int = -1

    # --- shared capacity ---
    def _capacity(self, planet: Planet) -> int:
        """この惑星から発射可能な最大 ship 数。"""
        return max(0, min(int(planet.ships * self.max_fraction), planet.ships - self.reserve))

    # --- shared aim angle (lead-shot + sun cone avoidance) ---
    def _aim_angle(self, mine: Planet, target: Planet, ships: int, state: GameState) -> float:
        """target への発射角を決定 (orbital なら lead-shot、太陽 forbidden cone を回避)。"""
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
            angle = (
                result[0]
                if result is not None
                else math.atan2(target.y - mine.y, target.x - mine.x)
            )
        else:
            angle = math.atan2(target.y - mine.y, target.x - mine.x)
        return physics.safe_angle_around(mine.x, mine.y, angle, margin=self.sun_margin_rad)

    # --- episode boundary detection ---
    def _maybe_new_episode(self, state: GameState) -> None:
        """step が巻き戻ったら新エピソード扱いで `_on_new_episode()` を呼ぶ。"""
        if state.step < self._last_step or (state.step == 0 and self._last_step > 0):
            self._on_new_episode()
        self._last_step = state.step

    def _on_new_episode(self) -> None:
        """エピソード開始時の reset hook。state を持つ mission で override."""
        pass


# ============================================================================
# CaptureMission: sniper の動的 sizing 強化版
# ============================================================================


class CaptureMission(_BaseMission):
    """非所有惑星を ROI 順に占領する mission。

    sniper との差分:
      1. ROI で target を選ぶ (近さだけでなく production も考慮)
      2. 敵惑星には MARGIN を上乗せ
      3. 太陽通過 (forbidden cone) を avoid
      4. orbiting target には lead-shot で命中角を計算
      5. RESERVE と MAX_FRACTION で home の枯渇を防ぐ (sniper 互換)

    Capacity gap (失敗モード #1) は本 mission では完全には解消しない —
    `garrison + 1 + MARGIN` を超える target は skip。後続 `FleetAggregationMission`
    で複数 home から合流させる予定 (Day 5)。
    """

    name = "capture"

    def __init__(
        self,
        reserve: int = 5,
        max_fraction: float = 0.85,
        margin: int = 1,
        sun_safety_margin_deg: float = 2.0,
    ):
        super().__init__(reserve, max_fraction, sun_safety_margin_deg)
        self.margin = margin

    def _ships_needed(self, target: Planet) -> int:
        """占領に必要な ship 数 (敵惑星は MARGIN 上乗せ)。"""
        if target.owner == -1:
            return target.ships + 1
        return target.ships + 1 + self.margin

    def evaluate(self, state: GameState) -> tuple[float, list[Move]]:
        self._maybe_new_episode(state)

        # CometGrab / Recapture が既に占領計画している惑星は、CaptureMission の対象外
        # (Dispatcher で score 比較されるが、ここでは comet を skip して自然に避ける)
        targets = [
            p
            for p in (state.enemy_planets + state.neutral_planets)
            if p.id not in state.comet_planet_ids
        ]
        if not targets or not state.my_planets:
            return 0.0, []

        moves: list[Move] = []
        score_total = 0.0

        # Day 6 (Phase 1.1b multi-target) は v2 比 0/28 全敗で rollback。
        # bovard data の 5-step bin 分析で「Top tier も序盤は 1 launch/turn 程度」と
        # 判明し、multi-launch は home garrison を一気に消費して防衛/再 launch を阻害。
        # → single-target (= 1 home 1 launch) に戻す。
        # 真の expansion gap 原因はまだ特定中: 取った planet が空 (= 取得時 ships ≈ 0) で
        # 即 home として再利用できないことが疑われ、Phase 1.1c で `capture_buffer` を
        # 上げる仮説を検証予定。
        for mine in state.my_planets:
            cap = self._capacity(mine)
            if cap <= 0:
                continue

            best: tuple[Planet, int, float] | None = None
            best_roi = 0.0
            for t in targets:
                ships_needed = self._ships_needed(t)
                if ships_needed > cap:
                    continue
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
# CometGrabMission: spawn step 直後の彗星を反応的に占領 (失敗モード #3)
# ============================================================================


class CometGrabMission(_BaseMission):
    """彗星を反応的に占領する mission。

    彗星は step 50/150/250/350/450 で spawn、半径 1.0、production 1。
    速度 4.0 で楕円軌道を移動、ボード外に出ると消滅。

    戦略:
      - 自分が所有していない comet を全て候補化
      - 各 comet について、`max_distance` 以内の最近の自惑星から発射
      - 必要 ship 数: `comet.ships + buffer` (彗星 defense median ~19 隻、25 隻で 50%
        / 60 隻で 95% 占領率)
      - 太陽 forbidden cone は避ける、orbiting target としては扱わない
        (彗星は楕円軌道なので軌道予測の閉形式は使えない)

    後続改善 (Day 5+):
      - 彗星パスから lead-shot 命中角を求める (TrackC §3 の path 観察)
      - 多 comet × 多 home の最適 assignment (Hungarian)
    """

    name = "comet_grab"

    def __init__(
        self,
        reserve: int = 5,
        max_fraction: float = 0.85,
        sun_safety_margin_deg: float = 2.0,
        capture_buffer: int = 5,
        max_distance: float = 40.0,
        max_comet_ships: int = 25,  # 安い comet のみ狙う (defense median 19)
        score_per_comet: float = 0.3,  # Capture の ROI と同等規模 (0.05-0.5) に下げる
    ):
        super().__init__(reserve, max_fraction, sun_safety_margin_deg)
        self.capture_buffer = capture_buffer
        self.max_distance = max_distance
        self.max_comet_ships = max_comet_ships
        self.score_per_comet = score_per_comet

    def evaluate(self, state: GameState) -> tuple[float, list[Move]]:
        self._maybe_new_episode(state)

        # 安い comet (defense 軽い) のみ候補化、高コストは Capture に任せる
        comets = [
            c
            for c in state.comet_planets
            if c.owner != state.player and c.ships <= self.max_comet_ships
        ]
        if not comets or not state.my_planets:
            return 0.0, []

        # 各 comet について、最近接の自惑星 (capacity 十分) を greedy assign
        # 1 home が複数 comet に発射するのは現状禁止 (Dispatcher で 1 planet 1 move)
        used_planets: set[int] = set()
        moves: list[Move] = []
        score_total = 0.0

        # 距離が近い comet から処理 (近いほど先回りされにくい)
        comets_by_proximity = sorted(
            comets,
            key=lambda c: min(physics.distance((c.x, c.y), (m.x, m.y)) for m in state.my_planets),
        )

        for comet in comets_by_proximity:
            ships_needed = max(comet.ships + self.capture_buffer, 1)

            best: tuple[Planet, float] | None = None
            best_dist = float("inf")
            for mine in state.my_planets:
                if mine.id in used_planets:
                    continue
                if self._capacity(mine) < ships_needed:
                    continue
                d = physics.distance((mine.x, mine.y), (comet.x, comet.y))
                if d > self.max_distance:
                    continue
                if d < best_dist:
                    best_dist = d
                    best = (mine, d)

            if best is None:
                continue

            mine, _d = best
            used_planets.add(mine.id)
            angle = self._aim_angle(mine, comet, ships_needed, state)
            moves.append(Move(mine.id, angle, ships_needed))
            score_total += self.score_per_comet

        return score_total, moves


# ============================================================================
# RecaptureMission: 失った惑星を奪還 (失敗モード #2)
# ============================================================================


class RecaptureMission(_BaseMission):
    """過去所有していた惑星が失われたら、それを奪還する mission。

    State (episode 内で蓄積):
      - `_was_mine`: これまで所有した planet ID set
      - `_on_new_episode()` で reset

    戦略:
      - 失われた惑星 (= `_was_mine` ∋ id かつ `owner != player`) を recapture target に
      - `max_distance` 以内の自惑星から、`ships_needed = target.ships + recapture_margin`
        を発射 (敵 garrison が再増強される前に取り戻す必要があるため margin 厚め)
      - 高 score 設定 → CaptureMission や CometGrab より優先される

    Score: 各 recapture target について `production * 10`。production 高い planet ほど
    奪還の価値が高い (ROI 観点)。
    """

    name = "recapture"

    def __init__(
        self,
        reserve: int = 5,
        max_fraction: float = 0.85,
        sun_safety_margin_deg: float = 2.0,
        recapture_margin: int = 5,
        max_distance: float = 50.0,
        min_production: int = 3,  # production>=3 の planet のみ recapture (低 prod は捨てる)
        score_per_production: float = 0.5,  # Capture ROI と同程度に抑える (高コストの recapture を抑制)
    ):
        super().__init__(reserve, max_fraction, sun_safety_margin_deg)
        self.recapture_margin = recapture_margin
        self.max_distance = max_distance
        self.min_production = min_production
        self.score_per_production = score_per_production
        self._was_mine: set[int] = set()

    def _on_new_episode(self) -> None:
        self._was_mine.clear()

    def evaluate(self, state: GameState) -> tuple[float, list[Move]]:
        self._maybe_new_episode(state)

        # 現在所有している惑星を track
        current_mine = {p.id for p in state.my_planets}
        self._was_mine.update(current_mine)

        # 失われた惑星 (= 過去所有 かつ 現在非所有)
        # comet は除外 (CometGrab で別途処理、recapture ではない)
        # 低 production (< min_production) も除外 (奪還コストに見合わない)
        lost_planets = [
            p
            for p in state.planets
            if p.id in self._was_mine
            and p.owner != state.player
            and p.id not in state.comet_planet_ids
            and p.production >= self.min_production
        ]
        if not lost_planets or not state.my_planets:
            return 0.0, []

        used_planets: set[int] = set()
        moves: list[Move] = []
        score_total = 0.0

        # 高 production の lost planet を優先
        lost_planets.sort(key=lambda p: -p.production)

        for target in lost_planets:
            ships_needed = target.ships + 1 + self.recapture_margin

            best: tuple[Planet, float] | None = None
            best_score = 0.0
            for mine in state.my_planets:
                if mine.id in used_planets:
                    continue
                if self._capacity(mine) < ships_needed:
                    continue
                d = physics.distance((mine.x, mine.y), (target.x, target.y))
                if d > self.max_distance:
                    continue
                # 近いほど良い + 自軍 ship 多いほど良い
                score = (1.0 / max(d, 1.0)) * mine.ships
                if score > best_score:
                    best_score = score
                    best = (mine, d)

            if best is None:
                continue

            mine, _d = best
            used_planets.add(mine.id)
            angle = self._aim_angle(mine, target, ships_needed, state)
            moves.append(Move(mine.id, angle, ships_needed))
            score_total += target.production * self.score_per_production

        return score_total, moves


# ============================================================================
# FleetAggregationMission: 複数 home から oversized target を奪取 (失敗モード #1 主因)
# ============================================================================


class FleetAggregationMission(_BaseMission):
    """単独 home の capacity を超える高 ROI target に対し、複数 home から同 turn 発射する mission。

    `CaptureMission` は `single_home_capacity >= ships_needed` の target のみ取れる。
    上位プレイヤーが運用する 100-200 ships の garrison を持つ planet に届かない =
    Capacity gap (失敗モード #1, 主因) の正体。本 mission はこれを解消する。

    戦略:
      1. `ships_needed > max(home_capacity)` な oversized target を抽出
         (= CaptureMission が個別では取れない target)
      2. 全 home の capacity 合計が `ships_needed` 以上なら候補
      3. ROI (production / (capture_cost + travel_time)) で sort
      4. greedy: 高 ROI target から、近接 home を順に動員、必要 ships に達したら停止
      5. 各 home → target に lead-shot + sun-cone safe な angle で発射

    注意:
      - 同 turn 発射でも arrival 時刻は home 距離で異なる。engine は target 到着順に
        battle resolution。最初の fleet が capture → 後続が self-reinforce。
        合計 ships >= ships_needed なら最終的に target を奪取できる
        (途中で敵の counter があると話は別、Day 6+ で OpponentModel で対応予定)。
      - CaptureMission との重複は target 識別子で実質回避: oversized target のみ扱う
        ので Capture が拾える small target には触らない。同じ home の capacity は
        Dispatcher が remaining 管理するので衝突しない。

    後続改善 (Day 6+):
      - 同期発射 (= 同 turn 到着の遅延発射計画)。現在は同 turn 発射のみ
      - max_homes パラメタの自動調整 (現在は固定 4)
    """

    name = "fleet_aggregation"

    def __init__(
        self,
        reserve: int = 5,
        max_fraction: float = 0.85,
        margin: int = 2,
        sun_safety_margin_deg: float = 2.0,
        max_homes: int = 4,
        min_step: int = 0,
        min_target_ships: int = 0,
        min_production: int = 0,
        aggr_reserve: int = 0,
    ):
        """
        Args:
            min_step: この step 未満では aggregation off (序盤 expansion を阻害しない).
            min_target_ships: target.ships がこれ未満なら skip (true oversized のみ).
            min_production: target.production がこれ未満なら skip (低 prod に投資しない).
            aggr_reserve: aggregation 後、各 home に最低これだけ ships を残す
                (= 守備兵力確保、敵 counter から守る).
        """
        super().__init__(reserve, max_fraction, sun_safety_margin_deg)
        self.margin = margin
        self.max_homes = max_homes
        self.min_step = min_step
        self.min_target_ships = min_target_ships
        self.min_production = min_production
        self.aggr_reserve = aggr_reserve

    def _ships_needed(self, target: Planet) -> int:
        """占領に必要な ship 数 (敵惑星は MARGIN 上乗せ)。Capture と同じ式。"""
        if target.owner == -1:
            return target.ships + 1
        return target.ships + 1 + self.margin

    def _aggr_capacity(self, planet: Planet) -> int:
        """aggregation 用の控えめ capacity (= 通常 capacity から aggr_reserve 引く).

        各 home に守備兵力 (`aggr_reserve` 隻) を残しておく → 敵 fleet 着弾時の counter
        を維持。Day 5 観測で aggregation が早期 garrison 枯渇を招き expansion 阻害した
        ため導入 (`tournament_log_v3_FAILED.csv` に v2 0/12 全敗の証拠).
        """
        base = self._capacity(planet)
        return max(0, base - self.aggr_reserve)

    def evaluate(self, state: GameState) -> tuple[float, list[Move]]:
        self._maybe_new_episode(state)

        # 序盤は静観 (= v2 と同じ動作で expansion の複利を確保)
        if state.step < self.min_step:
            return 0.0, []

        my = state.my_planets
        if not my:
            return 0.0, []

        # comet は CometGrab 担当、低 ship/低 prod は skip
        targets = [
            p
            for p in (state.enemy_planets + state.neutral_planets)
            if p.id not in state.comet_planet_ids
            and p.ships >= self.min_target_ships
            and p.production >= self.min_production
        ]
        if not targets:
            return 0.0, []

        home_caps = {p.id: self._aggr_capacity(p) for p in my}
        max_home_cap = max(home_caps.values()) if home_caps else 0
        if max_home_cap <= 0:
            return 0.0, []

        # oversized target (= 単独 home cap < ships_needed) かつ全 home 合計で取れるもの
        total_cap = sum(home_caps.values())
        oversized: list[tuple[float, Planet, int]] = []  # (roi, target, ships_needed)
        for t in targets:
            need = self._ships_needed(t)
            if need <= max_home_cap:
                continue  # CaptureMission が単独で取れる
            if need > total_cap:
                continue  # 全 home でも足りない
            nearest = min(my, key=lambda p: physics.distance((p.x, p.y), (t.x, t.y)))
            _, t_arr = physics.lead_angle_static(nearest.x, nearest.y, t.x, t.y, need)
            roi_val = physics.roi(t.production, need, t_arr)
            oversized.append((roi_val, t, need))

        if not oversized:
            return 0.0, []

        # ROI 降順
        oversized.sort(key=lambda x: -x[0])

        moves: list[Move] = []
        score_total = 0.0
        # remaining capacity per home (target 間で消費される)
        remaining = dict(home_caps)

        for roi_val, target, need in oversized:
            # 早期 abort: 残 capacity 合計が need 未満なら諦める
            if sum(remaining.values()) < need:
                continue

            # 近接 home を順に動員
            sorted_homes = sorted(
                my,
                key=lambda p: physics.distance((p.x, p.y), (target.x, target.y)),
            )
            assigned: list[tuple[Planet, int]] = []
            collected = 0
            homes_used = 0
            for home in sorted_homes:
                if homes_used >= self.max_homes:
                    break
                cap = remaining[home.id]
                if cap <= 0:
                    continue
                take = min(cap, need - collected)
                if take <= 0:
                    continue
                assigned.append((home, take))
                collected += take
                homes_used += 1
                if collected >= need:
                    break

            if collected < need:
                continue  # 達成できず (max_homes 制限など)

            # 採用: 各 home から発射
            for home, ships in assigned:
                angle = self._aim_angle(home, target, ships, state)
                moves.append(Move(home.id, angle, ships))
                remaining[home.id] -= ships
            score_total += roi_val

        return score_total, moves


# ============================================================================
# DefenseMission: 敵 fleet の angle observable を利用した守備派遣 (失敗モード #3)
# ============================================================================


def _predict_fleet_target(
    fleet: Fleet, planets: list[Planet], max_distance: float = 50.0
) -> tuple[Planet, float] | None:
    """敵 fleet (x, y, angle, ships) の line trajectory 上で最近接の planet を推定。

    Returns:
        (target_planet, distance_from_fleet) or None
    """
    fx, fy = float(fleet.x), float(fleet.y)
    fa = float(fleet.angle)
    cos_a, sin_a = math.cos(fa), math.sin(fa)

    best: tuple[Planet, float] | None = None
    best_dist = float("inf")
    for p in planets:
        dx = float(p.x) - fx
        dy = float(p.y) - fy
        # fleet trajectory 方向への射影 (= 進行方向の距離)
        proj = dx * cos_a + dy * sin_a
        if proj <= 0:
            continue  # planet は fleet の後方 = 着弾しない
        # 直交方向の距離 (= line から planet までの距離)
        ortho = abs(-dx * sin_a + dy * cos_a)
        if ortho > float(p.radius) + 1.5:
            continue  # planet 半径外 = 当たらない
        if proj > max_distance:
            continue
        if proj < best_dist:
            best_dist = proj
            best = (p, proj)
    return best


class DefenseMission(_BaseMission):
    """自陣 planet が敵 fleet の標的になっている時、近接 home から守備派遣する mission。

    使用 insight (`docs/discussion/insights.md` § 2.3):
      `[id, owner, x, y, angle, from_planet_id, ships]` の `angle` フィールドが
      敵 fleet でも observable → どの target に向かっているか完全に分かる。
      → 着弾 turn と必要守備 ships を逆算して間に合う home から派遣。

    戦略:
      1. 敵 fleet を全 enumerate
      2. 各 fleet の line trajectory で当たる my_planet (= target) を予測
      3. target.ships < fleet.ships - margin なら threat 認識
      4. fleet の eta (= 進行距離 / 速度) より早く守備が届く home を探す
      5. 必要 ships = fleet.ships - target.ships + buffer で派遣

    後続改善 (Phase 1.2 v2):
      - sun cone を考慮した実 trajectory (現状は直線)
      - target.ships 増加 (production / 進行中の自 fleet) を組み込み
      - 多 fleet 集中攻撃の拡張版
    """

    name = "defense"

    def __init__(
        self,
        reserve: int = 5,
        max_fraction: float = 0.85,
        sun_safety_margin_deg: float = 2.0,
        defense_buffer: int = 5,
        eta_safety: float = 1.0,
        score_per_threat: float = 2.0,
    ):
        super().__init__(reserve, max_fraction, sun_safety_margin_deg)
        self.defense_buffer = defense_buffer
        self.eta_safety = eta_safety
        self.score_per_threat = score_per_threat

    def evaluate(self, state: GameState) -> tuple[float, list[Move]]:
        self._maybe_new_episode(state)

        my = state.my_planets
        enemy_fleets = state.enemy_fleets
        if not my or not enemy_fleets:
            return 0.0, []

        my_set = {p.id for p in my}
        moves: list[Move] = []
        score_total = 0.0
        used_homes: set[int] = set()

        for f in enemy_fleets:
            pred = _predict_fleet_target(f, state.planets)
            if pred is None:
                continue
            target, dist_to_target = pred
            if target.id not in my_set:
                continue  # 自陣 planet ではない

            # ETA: 敵 fleet 進行距離 / 速度
            v_enemy = physics.fleet_speed(int(f.ships))
            eta = dist_to_target / max(v_enemy, 1e-3)

            # 必要守備 ships: fleet.ships - target.ships + buffer
            ships_needed = int(f.ships) - int(target.ships) + self.defense_buffer
            if ships_needed <= 0:
                continue  # garrison で守れる

            # 各候補 home から送って間に合うか
            best: tuple[Planet, int] | None = None
            best_score = 0.0
            for home in my:
                if home.id in used_homes:
                    continue
                cap = self._capacity(home)
                if cap < ships_needed:
                    continue
                d_home = physics.distance(
                    (float(home.x), float(home.y)),
                    (float(target.x), float(target.y)),
                )
                v_home = physics.fleet_speed(ships_needed)
                travel = d_home / max(v_home, 1e-3)
                if travel > eta - self.eta_safety:
                    continue  # 間に合わない
                # 近 + capacity 多い = 高 score
                score = (1.0 / max(d_home, 1.0)) * cap
                if score > best_score:
                    best_score = score
                    best = (home, ships_needed)

            if best is None:
                continue

            home, ships = best
            used_homes.add(home.id)
            angle = self._aim_angle(home, target, ships, state)
            moves.append(Move(home.id, angle, ships))
            score_total += self.score_per_threat

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
    """登録された mission 群を順に呼び、惑星単位の ship 容量を考慮して全 move を処理。

    Strategy (Day 3-4 改良):
      1. 各 mission を evaluate して `_PlannedMove` のリスト化
      2. score 降順にソート (高 score の move が ship を先に確保)
      3. 各 planet の `_capacity()` を残量管理しつつ、`move.ships` が残量内なら採用
      4. 同 planet から複数 mission の move が両立可能 (engine 仕様: 1 turn で
         同惑星から複数発射可)

    これで Recapture や CometGrab が Capture の expansion を "置き換える" のではなく
    "上乗せ" できる。ships が枯渇するときのみ高 score 優先で取り合う。
    """

    def __init__(self, missions: Sequence[Mission], reserve: int = 5, max_fraction: float = 0.85):
        self.missions = list(missions)
        # Dispatcher 自身も capacity 計算を持つ (= mission と同じ式)
        self.reserve = reserve
        self.max_fraction = max_fraction

    def _planet_capacity(self, planet: Planet) -> int:
        return max(0, min(int(planet.ships * self.max_fraction), planet.ships - self.reserve))

    def step(self, state: GameState) -> list[list[float]]:
        # 1) 全 mission から候補 move を集める
        candidates: list[_PlannedMove] = []
        for mission in self.missions:
            score, moves = mission.evaluate(state)
            if score <= 0.0 or not moves:
                continue
            move_score = score / max(len(moves), 1)
            for m in moves:
                candidates.append(_PlannedMove(m, move_score, mission.name))

        # 2) score 降順ソート (高 score が先に ships 確保)
        candidates.sort(key=lambda pm: -pm.score)

        # 3) planet 単位で残量を管理して採用判定
        planet_by_id = {p.id: p for p in state.planets}
        remaining: dict[int, int] = {}
        actions: list[list[float]] = []

        for pm in candidates:
            pid = pm.move.from_planet_id
            if pid not in planet_by_id:
                continue  # 不正な from_planet_id
            if pid not in remaining:
                remaining[pid] = self._planet_capacity(planet_by_id[pid])
            if pm.move.ships <= remaining[pid] and pm.move.ships > 0:
                actions.append(pm.move.to_action())
                remaining[pid] -= pm.move.ships

        return actions


# ============================================================================
# ExpansionPriorityMission: Early-game rapid expansion (= bovard 280万 row 真因解)
# ============================================================================


class ExpansionPriorityMission(_BaseMission):
    """早期 game (step <= early_game_steps) で nearby cluster を rapid expand する mission。

    **真因解析根拠** (= ~/.claude/CLAUDE.md 2026-05-10 lesson, bovard 280万 row 分析):
      - Top tier (kovi/Shun_PI) は step 100 で **5-7 planets / 300-430 ships**
      - 我家 (Reexel/v2 系) は step 100 で **1-2 planets / 30-50 ships** (= 100倍劣後)
      - 既存 CaptureMission の失敗モード: ROI 順に取得するが capacity gap で skip 多発、
        取得時 ships ≈ 0 で post-capture garrison なし → 即 home 再利用不能

    **解決策** (= 既存 CaptureMission との差分):
      1. **early_game_steps 限定**: step > 早期 で score=0、 通常 CaptureMission に渡す
      2. **capture_buffer 上げ**: ships_needed = enemy + 1 + capture_buffer (デフォ 8)
         → 取得時 garrison ≥ 5 確保、 次 turn からの home 再利用が可能
      3. **nearby cluster 優先**: 自 planet から max_distance 以内に限定
         → 中央集権的 chain expansion で planets 数を線形増加
      4. **score multiplier**: Capture の 2 倍で Dispatcher で先に ships 確保

    Day 4 以降 P4 で Lakhindar IL + PPO θ.4 と meta-blend、 step-based switcher で
    early game = この mission / mid-late = IL + RL の 3-paradigm 構成想定。
    """

    name = "expansion_priority"

    def __init__(
        self,
        reserve: int = 5,
        max_fraction: float = 0.85,
        sun_safety_margin_deg: float = 2.0,
        early_game_steps: int = 150,
        max_distance: float = 35.0,
        capture_buffer: int = 8,
        score_multiplier: float = 2.0,
    ):
        super().__init__(reserve, max_fraction, sun_safety_margin_deg)
        self.early_game_steps = early_game_steps
        self.max_distance = max_distance
        self.capture_buffer = capture_buffer
        self.score_multiplier = score_multiplier

    def _ships_needed(self, target: Planet) -> int:
        """capture_buffer 上乗せで取得時 garrison を確保。"""
        return target.ships + 1 + self.capture_buffer

    def evaluate(self, state: GameState) -> tuple[float, list[Move]]:
        self._maybe_new_episode(state)

        # Early game 限定 — late game では通常 CaptureMission に任せる
        if state.step > self.early_game_steps:
            return 0.0, []

        my = state.my_planets
        if not my:
            return 0.0, []

        neutrals = [p for p in state.neutral_planets if p.id not in state.comet_planet_ids]
        if not neutrals:
            return 0.0, []

        moves: list[Move] = []
        score_total = 0.0

        for mine in my:
            cap = self._capacity(mine)
            if cap <= 0:
                continue

            best: tuple[Planet, int, float] | None = None
            best_roi = 0.0
            for t in neutrals:
                d = math.hypot(t.x - mine.x, t.y - mine.y)
                if d > self.max_distance:
                    continue
                ships_needed = self._ships_needed(t)
                if ships_needed > cap:
                    continue
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
            score_total += best_roi * self.score_multiplier

        return score_total, moves
