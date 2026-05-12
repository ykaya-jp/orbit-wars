"""Beam search for orbit-wars action selection (Phase alpha.2 v0).

Reverse-engineers the bowwowforeach big-stack timing paradigm:
- Restrict launches to home_cap >= 100 ships AND fraction in {0.5, 0.85, 1.0}.
- Score leaf states via hand-tuned weighted sum of (my_planets, my_ships,
  enemy_ships, enemy_planets).
- Depth 3 beam search with width 32 fits within the Kaggle 1 s/step budget.

The internal simulator is intentionally lightweight:
- forward Euler fleet motion at 5 unit/turn (sun gravity ignored, valid for the
  3-step horizon at angular_velocity ~0.04).
- arrival -> combat resolution using engine convention (top - second survives).
- production growth on owned planets.
- enemy / friendly opponent actions are predicted via a deterministic mock that
  mimics the starter agent (= nearest neutral, half-stack launch).

Public entry: :func:`select_action(obs, player, cfg)` returns a list of
``[src_planet_id, angle_radians, ships_sent]`` triplets compatible with the
kaggle_environments action shape.

The module is self-contained (numpy is optional, only math is required) so the
agent.py wrapper can inline it into the Kaggle submission.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

# ---------------------------------------------------------------------------
# Engine constants (copied to keep the module self-contained on Kaggle worker)
# ---------------------------------------------------------------------------

SUN_X: float = 50.0
SUN_Y: float = 50.0
SUN_RADIUS: float = 10.0
MAX_SPEED: float = 6.0
ROTATION_RADIUS_LIMIT: float = 50.0
BOARD: float = 100.0
SUN_SAFETY_MARGIN: float = 1.5

# ---------------------------------------------------------------------------
# Search configuration
# ---------------------------------------------------------------------------


@dataclass
class BeamConfig:
    """Beam search hyperparameters. Defaults are bowwow-paradigm tuned.

    Keep both ``depth`` and ``beam_width`` small enough that
    ``depth * beam_width * actions_per_state < ~50k`` evaluations finish in
    the 1 s/step Kaggle budget.
    """

    depth: int = 3
    beam_width: int = 32
    angle_bins: int = 16  # = pi/8 rad resolution
    fractions: tuple[float, ...] = (0.5, 0.85, 1.0)
    min_launch_ships: int = 100  # skip src planets below this (bowwow mean 241)
    min_send_fraction: float = 0.85  # only big-stack launches (= 4.4 prune rule)
    leaf_alpha: float = 10.0  # weight on my_planets
    leaf_beta: float = 1.0  # weight on my_ships_total
    leaf_gamma: float = 1.0  # weight on enemy_ships_total (subtracted)
    leaf_delta: float = 8.0  # weight on enemy_planets (subtracted)
    # Future-ship potential: each owned planet produces ``prod`` ships per
    # remaining turn. Capturing high-prod planets early is strictly more
    # valuable than capturing the same count of low-prod ones, but the count-
    # only leaf score can't see that. Weight 1.0 means "treat each future
    # ship the same as a current ship".
    leaf_epsilon: float = 1.0  # weight on (my_prod * remaining_steps)
    leaf_zeta: float = 0.7  # weight on (enemy_prod * remaining_steps) (subtracted)
    leaf_episode_horizon: int = 500  # engine max episodeSteps -- used to bound remaining_steps
    terminal_bonus: float = 1000.0
    sim_speed: float = 5.0  # forward Euler unit/turn (simplification)
    max_top_actions_per_step: int = 50  # safety cap on action enumeration
    rng_seed: int = 0
    # ---- v2 additions: PPO leaf-value hybrid + step-dependent prune ----
    handcrafted_weight: float = 1.0  # weight on the linear leaf score
    ppo_value_weight: float = 0.0  # weight on PPO V(s) at the leaf; 0 = handcrafted-only
    leaf_top_k_ppo: int = 8  # rescore only the K best handcrafted leaves with PPO
    step_dependent_prune: bool = False  # use phase-aware min_launch_ships
    # Phase thresholds (step < phase_mid_start = early, < phase_late_start = mid, else late).
    phase_mid_start: int = 50
    phase_late_start: int = 300
    min_launch_early: int = 30  # early game allows small expansion launches
    min_launch_mid: int = 100  # mid game = bowwow-default big-stack
    min_launch_late: int = 100  # late game = consolidation, slightly relaxed


# ---------------------------------------------------------------------------
# Simulator state
# ---------------------------------------------------------------------------


@dataclass
class Planet:
    """Mutable planet record used by the search simulator."""

    pid: int
    owner: int
    x: float
    y: float
    radius: float
    ships: float
    prod: float
    is_orbiting: bool

    def copy(self) -> Planet:
        return Planet(
            self.pid,
            self.owner,
            self.x,
            self.y,
            self.radius,
            self.ships,
            self.prod,
            self.is_orbiting,
        )


@dataclass
class Fleet:
    """In-flight fleet record (target_pid + ETA based, no orbital correction)."""

    owner: int
    ships: float
    target_pid: int
    eta: float  # turns until arrival

    def copy(self) -> Fleet:
        return Fleet(self.owner, self.ships, self.target_pid, self.eta)


@dataclass
class SimState:
    """Compact mutable state for fast simulator copies."""

    planets: dict[int, Planet]
    fleets: list[Fleet] = field(default_factory=list)
    step: int = 0

    def copy(self) -> SimState:
        return SimState(
            planets={pid: p.copy() for pid, p in self.planets.items()},
            fleets=[f.copy() for f in self.fleets],
            step=self.step,
        )

    # ----- ownership tallies -----
    def player_planets(self, player: int) -> int:
        return sum(1 for p in self.planets.values() if p.owner == player)

    def player_ships(self, player: int) -> float:
        return sum(p.ships for p in self.planets.values() if p.owner == player) + sum(
            f.ships for f in self.fleets if f.owner == player
        )

    def alive_players(self) -> set[int]:
        return {p.owner for p in self.planets.values() if p.owner >= 0}


# ---------------------------------------------------------------------------
# Helpers (mirrors src/orbit_wars/physics.py with engine-compat constants)
# ---------------------------------------------------------------------------


def fleet_speed(ships: float, max_speed: float = MAX_SPEED) -> float:
    """Engine fleet speed formula (= physics.py:fleet_speed)."""
    if ships <= 1:
        return 1.0
    s = 1.0 + (max_speed - 1.0) * (math.log(max(ships, 1.0)) / math.log(1000.0)) ** 1.5
    return min(s, max_speed)


def _path_crosses_sun(
    x1: float, y1: float, x2: float, y2: float, margin: float = SUN_SAFETY_MARGIN
) -> bool:
    """Line segment vs sun-disc intersection."""
    dx, dy = x2 - x1, y2 - y1
    len_sq = dx * dx + dy * dy
    if len_sq == 0:
        return math.hypot(x1 - SUN_X, y1 - SUN_Y) < SUN_RADIUS + margin
    t = ((SUN_X - x1) * dx + (SUN_Y - y1) * dy) / len_sq
    t = max(0.0, min(1.0, t))
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    return math.hypot(closest_x - SUN_X, closest_y - SUN_Y) < SUN_RADIUS + margin


def _safe_angle(x1: float, y1: float, x2: float, y2: float) -> float:
    """Return a sun-safe launch angle towards (x2, y2)."""
    direct = math.atan2(y2 - y1, x2 - x1)
    if not _path_crosses_sun(x1, y1, x2, y2):
        return direct
    d = math.hypot(x1 - SUN_X, y1 - SUN_Y)
    if d <= SUN_RADIUS + 1.0:
        return direct
    half = math.asin(min(1.0, (SUN_RADIUS + 1.5) / d))
    to_sun = math.atan2(SUN_Y - y1, SUN_X - x1)
    cw = to_sun + half
    ccw = to_sun - half

    def adiff(a: float) -> float:
        dd = (a - direct) % (2.0 * math.pi)
        return min(dd, 2.0 * math.pi - dd)

    return cw if adiff(cw) < adiff(ccw) else ccw


# ---------------------------------------------------------------------------
# Observation -> SimState bridge
# ---------------------------------------------------------------------------


def obs_to_state(obs: dict) -> SimState:
    """Translate a Kaggle obs dict into the internal :class:`SimState`."""
    planets: dict[int, Planet] = {}
    for p in obs.get("planets", []):
        pid = int(p[0])
        owner = int(p[1])
        x = float(p[2])
        y = float(p[3])
        radius = float(p[4])
        ships = float(p[5])
        prod = float(p[6])
        r = math.hypot(x - SUN_X, y - SUN_Y)
        is_orb = (r + radius) < ROTATION_RADIUS_LIMIT - 2.0
        planets[pid] = Planet(pid, owner, x, y, radius, ships, prod, is_orb)

    fleets: list[Fleet] = []
    # Approximate ETA from current pos -> nearest planet on heading direction.
    for f in obs.get("fleets", []):
        owner = int(f[1])
        fx = float(f[2])
        fy = float(f[3])
        angle = float(f[4])
        ships = float(f[6])
        # find nearest planet along heading vector (proj > 0)
        best_pid = -1
        best_t = float("inf")
        dir_x = math.cos(angle)
        dir_y = math.sin(angle)
        for pid, p in planets.items():
            dx = p.x - fx
            dy = p.y - fy
            proj = dx * dir_x + dy * dir_y
            if proj <= 0:
                continue
            perp = abs(dx * dir_y - dy * dir_x)
            if perp >= p.radius + 1.5:
                continue
            speed = fleet_speed(ships)
            t_arr = proj / max(speed, 0.5)
            if t_arr < best_t:
                best_t = t_arr
                best_pid = pid
        if best_pid >= 0 and best_t < 200.0:
            fleets.append(Fleet(owner, ships, best_pid, best_t))

    return SimState(planets=planets, fleets=fleets, step=int(obs.get("step", 0)))


# ---------------------------------------------------------------------------
# Action enumeration (bowwow big-stack filter)
# ---------------------------------------------------------------------------


@dataclass
class Action:
    """Concrete launch from one of our planets."""

    src_pid: int
    target_pid: int
    fraction: float
    angle: float  # final launch angle in radians (sun-safe)
    eta: float  # forecast turns to arrival
    send_ships: float

    def as_move(self) -> list:
        return [self.src_pid, self.angle, int(self.send_ships)]


def _phase_min_launch(state: SimState, cfg: BeamConfig) -> int:
    """Return min_launch_ships floor for the current step phase.

    Bowwow data (= bovard 280M row analysis, docs/research/2026-05-12-bowwow-reverse.md §3):
    - step < 50: many small expansion launches (cap ~ 30 ships)
    - 50 <= step < 300: big-stack timing window (cap = 100, bowwow mean 241)
    - step >= 300: consolidation phase, slightly relaxed
    """
    if not cfg.step_dependent_prune:
        return cfg.min_launch_ships
    if state.step < cfg.phase_mid_start:
        return cfg.min_launch_early
    if state.step < cfg.phase_late_start:
        return cfg.min_launch_mid
    return cfg.min_launch_late


def enumerate_actions(state: SimState, player: int, cfg: BeamConfig) -> list[Action]:
    """All (src, target, fraction) launches that pass the big-stack prune."""
    actions: list[Action] = []
    my_planets = [p for p in state.planets.values() if p.owner == player]
    other_planets = [p for p in state.planets.values() if p.owner != player]
    min_launch = _phase_min_launch(state, cfg)
    for src in my_planets:
        if src.ships < min_launch:
            continue
        for tgt in other_planets:
            if tgt.pid == src.pid:
                continue
            dx = tgt.x - src.x
            dy = tgt.y - src.y
            dist = math.hypot(dx, dy)
            if dist < 1.0:
                continue
            for frac in cfg.fractions:
                send = src.ships * frac
                if send < min_launch * cfg.min_send_fraction:
                    continue
                if send > src.ships - 1.0:
                    send = src.ships - 1.0
                if send < min_launch * cfg.min_send_fraction:
                    continue
                speed = fleet_speed(send)
                eta = dist / max(speed, 0.5)
                angle = _safe_angle(src.x, src.y, tgt.x, tgt.y)
                actions.append(
                    Action(
                        src_pid=src.pid,
                        target_pid=tgt.pid,
                        fraction=frac,
                        angle=angle,
                        eta=eta,
                        send_ships=send,
                    )
                )
    # safety cap: keep top-K by send_ships (= bowwow-bias to big stacks)
    if len(actions) > cfg.max_top_actions_per_step:
        actions.sort(key=lambda a: -a.send_ships)
        actions = actions[: cfg.max_top_actions_per_step]
    return actions


# ---------------------------------------------------------------------------
# Mock opponent (= starter-agent-like nearest-neutral half-launch)
# ---------------------------------------------------------------------------


def _mock_opponent_actions(state: SimState, player: int) -> list[Action]:
    """Cheap heuristic for other-player moves used during simulation rollout.

    Faithfully mirrors ``orbit_wars.starter_agent`` (engine source line 778):
      - Only consider STATIC targets (orbital_r + radius >= ROTATION_RADIUS_LIMIT).
      - For each of our planets, fire half-stack at the nearest static enemy/neutral.
      - Send ships only if ships // 2 >= 20.

    Previous version targeted *any* non-owned planet with ships >= 15, which
    was much more aggressive than the real starter -- the MCTS search treated
    its rivals as predators and over-defended, leading to 0/8 vs real starter.
    """
    actions: list[Action] = []
    own = [p for p in state.planets.values() if p.owner == player]
    if not own:
        return actions
    static_targets = [
        p
        for p in state.planets.values()
        if p.owner != player
        and (math.hypot(p.x - SUN_X, p.y - SUN_Y) + p.radius) >= ROTATION_RADIUS_LIMIT
    ]
    if not static_targets:
        return actions
    for src in own:
        if src.ships <= 0:
            continue
        # nearest static target
        best_tgt = None
        best_d = float("inf")
        for t in static_targets:
            d = math.hypot(t.x - src.x, t.y - src.y)
            if d < best_d:
                best_d = d
                best_tgt = t
        if best_tgt is None or best_d < 1.0:
            continue
        send_int = int(src.ships) // 2
        if send_int < 20:
            continue
        send = float(send_int)
        speed = fleet_speed(send)
        eta = best_d / max(speed, 0.5)
        actions.append(
            Action(
                src_pid=src.pid,
                target_pid=best_tgt.pid,
                fraction=0.5,
                angle=_safe_angle(src.x, src.y, best_tgt.x, best_tgt.y),
                eta=eta,
                send_ships=send,
            )
        )
    return actions


# ---------------------------------------------------------------------------
# Simulator step
# ---------------------------------------------------------------------------


def _apply_launches(state: SimState, actions: list[Action], player: int) -> None:
    for act in actions:
        src = state.planets.get(act.src_pid)
        if src is None or src.owner != player:
            continue
        send = min(act.send_ships, max(src.ships - 1.0, 0.0))
        if send <= 0:
            continue
        src.ships -= send
        state.fleets.append(Fleet(player, send, act.target_pid, act.eta))


def _resolve_arrivals(state: SimState) -> None:
    """Engine-faithful combat resolution (two-phase).

    Mirrors orbit_wars.py:634-674. The simulator originally collapsed both
    phases into a single sort, which let a single fleet "capture" a neutral
    that still had its initial garrison -- a major optimism bias the search
    used to over-attack neutrals (Codex review 2026-05-13).

    Phase 1: arriving fleets fight each other -- top - second survives,
             ties cancel to 0 ships / owner = -1.
    Phase 2: the surviving fleet (if any) fights the existing defender:
             - same owner: ships += survivor_ships
             - different:  ships -= survivor_ships; if it goes negative,
                           the survivor captures with abs(remainder).
    """
    arrived_by_target: dict[int, dict[int, float]] = {}
    pending: list[Fleet] = []
    for f in state.fleets:
        if f.eta <= 1.0:
            buf = arrived_by_target.setdefault(f.target_pid, {})
            buf[f.owner] = buf.get(f.owner, 0.0) + f.ships
        else:
            f.eta -= 1.0
            pending.append(f)
    state.fleets = pending

    for tgt_pid, by_owner in arrived_by_target.items():
        tgt = state.planets.get(tgt_pid)
        if tgt is None or not by_owner:
            continue

        # Phase 1: top-vs-second among arriving fleets (defender excluded).
        sorted_owners = sorted(by_owner.items(), key=lambda kv: -kv[1])
        top_owner, top_ships = sorted_owners[0]
        if len(sorted_owners) >= 2:
            second_ships = sorted_owners[1][1]
            survivor_ships = top_ships - second_ships
            if top_ships == second_ships:
                survivor_ships = 0.0
            survivor_owner = top_owner if survivor_ships > 0 else -1
        else:
            survivor_owner = top_owner
            survivor_ships = top_ships

        if survivor_ships <= 0:
            # All arriving fleets cancelled out; defender unchanged.
            continue

        # Phase 2: surviving fleet vs current defender garrison.
        if tgt.owner == survivor_owner:
            tgt.ships += survivor_ships
        else:
            tgt.ships -= survivor_ships
            if tgt.ships < 0:
                tgt.owner = survivor_owner
                tgt.ships = abs(tgt.ships)


def _grow_planets(state: SimState) -> None:
    for p in state.planets.values():
        if p.owner >= 0:
            p.ships += p.prod


def sim_step(state: SimState, actions_by_player: dict[int, list[Action]]) -> None:
    """One synchronous turn: launch -> move fleets -> resolve -> grow."""
    for player, acts in actions_by_player.items():
        _apply_launches(state, acts, player)
    _resolve_arrivals(state)
    _grow_planets(state)
    state.step += 1


# ---------------------------------------------------------------------------
# Leaf evaluation
# ---------------------------------------------------------------------------


def evaluate_leaf(state: SimState, player: int, cfg: BeamConfig) -> float:
    """Hand-crafted leaf scoring matching docs/research bowwow-reverse 4.3.

    Extended with a future-ship potential term so the search prefers
    high-production planets early (= count-only leaf can't distinguish a
    prod=1 expansion from a prod=3 expansion).
    """
    my_planets = state.player_planets(player)
    enemy_planets = sum(1 for p in state.planets.values() if p.owner >= 0 and p.owner != player)
    my_ships = state.player_ships(player)
    enemy_ships = sum(
        p.ships for p in state.planets.values() if p.owner >= 0 and p.owner != player
    ) + sum(f.ships for f in state.fleets if f.owner != player and f.owner >= 0)
    my_prod = sum(p.prod for p in state.planets.values() if p.owner == player)
    enemy_prod = sum(
        p.prod for p in state.planets.values() if p.owner >= 0 and p.owner != player
    )

    if my_planets == 0:
        return -cfg.terminal_bonus
    alive = state.alive_players()
    alive.discard(player)
    if not alive:
        return cfg.terminal_bonus

    remaining = max(0, cfg.leaf_episode_horizon - state.step)
    return (
        cfg.leaf_alpha * my_planets
        + cfg.leaf_beta * my_ships
        - cfg.leaf_gamma * enemy_ships
        - cfg.leaf_delta * enemy_planets
        + cfg.leaf_epsilon * my_prod * remaining
        - cfg.leaf_zeta * enemy_prod * remaining
    )


def state_to_pseudo_obs(state: SimState, player: int) -> dict:
    """Convert SimState -> dict shaped like a Kaggle observation.

    Used by the PPO value-function evaluator (= encode_grid_state expects the
    same tuple layout as the live env). Fleet angles are reconstructed toward
    each fleet's target planet -- only the spatial cell occupancy and heading
    sign matter for the grid encoder, not exact coordinates.
    """
    pseudo_planets = []
    for p in state.planets.values():
        pseudo_planets.append([p.pid, p.owner, p.x, p.y, p.radius, int(p.ships), int(p.prod)])
    pseudo_fleets = []
    for f in state.fleets:
        tgt = state.planets.get(f.target_pid)
        if tgt is None:
            continue
        # Place the fleet a fleet_speed step away from its target heading
        # straight in -- this preserves which grid cell it occupies for the
        # encoder without needing the original launch coordinates.
        speed = fleet_speed(f.ships)
        dx = tgt.x - SUN_X
        dy = tgt.y - SUN_Y
        d = math.hypot(dx, dy)
        if d < 1e-6:
            d = 1e-6
        fx = tgt.x - (dx / d) * speed
        fy = tgt.y - (dy / d) * speed
        angle = math.atan2(tgt.y - fy, tgt.x - fx)
        pseudo_fleets.append([0, f.owner, fx, fy, angle, 0, int(f.ships)])
    return {
        "step": state.step,
        "player": player,
        "planets": pseudo_planets,
        "fleets": pseudo_fleets,
    }


# ---------------------------------------------------------------------------
# Beam search
# ---------------------------------------------------------------------------


@dataclass
class BeamNode:
    """One candidate plan kept in the beam.

    ``first_actions`` records the launches we committed at the *current* turn
    (= what we will actually emit to the env). ``state`` is the projected sim
    state after applying ``depth`` synchronous rollouts.
    """

    state: SimState
    first_actions: list[Action]
    score: float


def _action_combos(actions: list[Action], cfg: BeamConfig) -> list[list[Action]]:
    """Branch the beam with a mix of single-launch and multi-source combos.

    Pure single-launch beam (the v0 default) lets a multi-planet starter
    out-expand us: each of their planets fires every turn while we wait for
    one big stack. We add a "fire from every source we can" combo so the
    beam can evaluate multi-source plans head-to-head with conservative
    big-stack timing plans.
    """
    combos: list[list[Action]] = [[]]
    actions_sorted = sorted(actions, key=lambda a: (-a.send_ships, a.eta))

    # Reserve half the beam for diverse single-launch plans.
    single_slots = max(1, cfg.beam_width // 2)
    for act in actions_sorted[:single_slots]:
        combos.append([act])

    # "Fire-from-all" combo: take the best action per source planet.
    by_src: dict[int, Action] = {}
    for act in actions_sorted:
        by_src.setdefault(act.src_pid, act)
    if len(by_src) >= 2:
        combos.append(list(by_src.values()))

    # Top-2-source combo: only fire from the two strongest sources.
    if len(by_src) >= 3:
        top2 = sorted(by_src.values(), key=lambda a: -a.send_ships)[:2]
        combos.append(top2)

    return combos


def beam_search(
    state: SimState,
    player: int,
    cfg: BeamConfig,
    ppo_value_fn=None,
) -> list[Action]:
    """Run depth-limited beam search and return the chosen launches for now.

    When ``ppo_value_fn`` is provided and ``cfg.ppo_value_weight > 0``, the
    final beam's top-``leaf_top_k_ppo`` nodes are rescored with a hybrid
    score: ``handcrafted_weight * leaf + ppo_value_weight * V(s)``.
    """
    root_actions = enumerate_actions(state, player, cfg)
    if not root_actions:
        return []
    initial_combos = _action_combos(root_actions, cfg)

    # Root expansion: each combo creates one beam entry.
    beam: list[BeamNode] = []
    for combo in initial_combos:
        sim = state.copy()
        opp_actions: dict[int, list[Action]] = {}
        # Mock other players' first-step actions.
        for other in (0, 1, 2, 3):
            if other == player:
                continue
            opp_actions[other] = _mock_opponent_actions(sim, other)
        all_acts = {player: combo, **opp_actions}
        sim_step(sim, all_acts)
        beam.append(BeamNode(state=sim, first_actions=combo, score=0.0))

    # Depth-2 .. depth-N rollouts: greedy single-source expansion per node.
    for _depth in range(1, cfg.depth):
        new_beam: list[BeamNode] = []
        for node in beam:
            my_actions = enumerate_actions(node.state, player, cfg)
            combos = _action_combos(my_actions, cfg) if my_actions else [[]]
            # branch factor capped: keep best 2 combos for shallow lookahead
            for combo in combos[:2]:
                sim = node.state.copy()
                opp_actions = {}
                for other in (0, 1, 2, 3):
                    if other == player:
                        continue
                    opp_actions[other] = _mock_opponent_actions(sim, other)
                sim_step(sim, {player: combo, **opp_actions})
                new_beam.append(
                    BeamNode(
                        state=sim,
                        first_actions=node.first_actions,
                        score=0.0,
                    )
                )
        # prune by leaf score
        for n in new_beam:
            n.score = evaluate_leaf(n.state, player, cfg)
        new_beam.sort(key=lambda n: -n.score)
        beam = new_beam[: cfg.beam_width]
        if not beam:
            break

    # Final scoring (handle depth==1 case where loop didn't run)
    for n in beam:
        if n.score == 0.0:
            n.score = evaluate_leaf(n.state, player, cfg)

    # Hybrid PPO rescoring on top-K only (= latency budget).
    if ppo_value_fn is not None and cfg.ppo_value_weight > 0.0:
        beam.sort(key=lambda n: -n.score)
        k = min(cfg.leaf_top_k_ppo, len(beam))
        for n in beam[:k]:
            try:
                v = float(ppo_value_fn(state_to_pseudo_obs(n.state, player)))
            except Exception:
                v = 0.0
            n.score = cfg.handcrafted_weight * n.score + cfg.ppo_value_weight * v

    beam.sort(key=lambda n: -n.score)
    best = beam[0]
    return best.first_actions


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def select_action(
    obs: dict,
    cfg: BeamConfig | None = None,
    ppo_value_fn=None,
) -> list[list]:
    """Top-level: produce the move list for one agent turn.

    ``ppo_value_fn`` (= optional) receives a pseudo-obs dict and returns a
    scalar V(s). When provided alongside ``cfg.ppo_value_weight > 0``, beam
    leaves are rescored with a handcrafted + PPO hybrid score.
    """
    if cfg is None:
        cfg = BeamConfig()
    player = int(obs.get("player", 0))
    state = obs_to_state(obs)
    actions = beam_search(state, player, cfg, ppo_value_fn=ppo_value_fn)
    moves: list[list] = []
    # Use phase-aware floor for the post-search filter so v2 (early-game
    # expansion) doesn't drop sub-100-ship launches selected by the search.
    floor = _phase_min_launch(state, cfg) if cfg.step_dependent_prune else cfg.min_launch_ships
    for act in actions:
        src = state.planets.get(act.src_pid)
        if src is None or src.owner != player:
            continue
        send = int(min(act.send_ships, max(src.ships - 1.0, 0.0)))
        if send < int(floor * cfg.min_send_fraction):
            continue
        moves.append([act.src_pid, act.angle, send])
    return moves


# ---------------------------------------------------------------------------
# Backward-compat default config
# ---------------------------------------------------------------------------


DEFAULT_CONFIG = BeamConfig()

__all__ = [
    "Action",
    "BeamConfig",
    "DEFAULT_CONFIG",
    "Fleet",
    "Planet",
    "SimState",
    "beam_search",
    "enumerate_actions",
    "evaluate_leaf",
    "fleet_speed",
    "obs_to_state",
    "select_action",
    "sim_step",
]


# Keep dataclass replace import alive for callers that customize cfg fields.
_ = replace
