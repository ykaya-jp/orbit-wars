"""MCTS v1 agent (= Phase alpha.2 v0 first cut).

Inlined from tools/mcts_orbit_wars.py for the Kaggle agent sandbox: the
submission must run with only this single file + stdlib.

Paradigm:
- depth=3 beam search, width=32, on the bowwow big-stack action mask.
- leaf heuristic: alpha*my_planets + beta*my_ships - gamma*enemy_ships
  - delta*enemy_planets (with terminal +-1000 override).
- mock opponent (nearest-neutral half-launch) used for forward rollouts.
- single launch per turn (= bowwow-style timing-focused, NOT multi-source).

Out of scope for v0 (planned v1 follow-ups):
- depth=5, PPO leaf eval, multi-source per turn, opponent model upgrade.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Engine constants
# ---------------------------------------------------------------------------

SUN_X = 50.0
SUN_Y = 50.0
SUN_RADIUS = 10.0
MAX_SPEED = 6.0
ROTATION_RADIUS_LIMIT = 50.0
SUN_SAFETY_MARGIN = 1.5


# ---------------------------------------------------------------------------
# Search configuration
# ---------------------------------------------------------------------------


@dataclass
class BeamConfig:
    depth: int = 3
    beam_width: int = 32
    angle_bins: int = 16
    fractions: tuple = (0.5, 0.85, 1.0)
    min_launch_ships: int = 100
    min_send_fraction: float = 0.85
    leaf_alpha: float = 10.0
    leaf_beta: float = 1.0
    leaf_gamma: float = 1.0
    leaf_delta: float = 8.0
    terminal_bonus: float = 1000.0
    max_top_actions_per_step: int = 50


CFG = BeamConfig()


# ---------------------------------------------------------------------------
# State dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Planet:
    pid: int
    owner: int
    x: float
    y: float
    radius: float
    ships: float
    prod: float
    is_orbiting: bool

    def copy(self):
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
    owner: int
    ships: float
    target_pid: int
    eta: float

    def copy(self):
        return Fleet(self.owner, self.ships, self.target_pid, self.eta)


@dataclass
class SimState:
    planets: dict
    fleets: list = field(default_factory=list)
    step: int = 0

    def copy(self):
        return SimState(
            planets={pid: p.copy() for pid, p in self.planets.items()},
            fleets=[f.copy() for f in self.fleets],
            step=self.step,
        )

    def player_planets(self, player):
        return sum(1 for p in self.planets.values() if p.owner == player)

    def player_ships(self, player):
        return sum(p.ships for p in self.planets.values() if p.owner == player) + sum(
            f.ships for f in self.fleets if f.owner == player
        )

    def alive_players(self):
        return {p.owner for p in self.planets.values() if p.owner >= 0}


@dataclass
class Action:
    src_pid: int
    target_pid: int
    fraction: float
    angle: float
    eta: float
    send_ships: float


# ---------------------------------------------------------------------------
# Physics helpers
# ---------------------------------------------------------------------------


def fleet_speed(ships):
    if ships <= 1:
        return 1.0
    s = 1.0 + (MAX_SPEED - 1.0) * (math.log(max(ships, 1.0)) / math.log(1000.0)) ** 1.5
    return min(s, MAX_SPEED)


def _path_crosses_sun(x1, y1, x2, y2, margin=SUN_SAFETY_MARGIN):
    dx = x2 - x1
    dy = y2 - y1
    len_sq = dx * dx + dy * dy
    if len_sq == 0:
        return math.hypot(x1 - SUN_X, y1 - SUN_Y) < SUN_RADIUS + margin
    t = ((SUN_X - x1) * dx + (SUN_Y - y1) * dy) / len_sq
    if t < 0:
        t = 0.0
    elif t > 1:
        t = 1.0
    cx = x1 + t * dx
    cy = y1 + t * dy
    return math.hypot(cx - SUN_X, cy - SUN_Y) < SUN_RADIUS + margin


def _safe_angle(x1, y1, x2, y2):
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

    def adiff(a):
        dd = (a - direct) % (2.0 * math.pi)
        return min(dd, 2.0 * math.pi - dd)

    return cw if adiff(cw) < adiff(ccw) else ccw


# ---------------------------------------------------------------------------
# Observation -> SimState
# ---------------------------------------------------------------------------


def obs_to_state(obs):
    planets = {}
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

    fleets = []
    for f in obs.get("fleets", []):
        owner = int(f[1])
        fx = float(f[2])
        fy = float(f[3])
        angle = float(f[4])
        ships = float(f[6])
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
# Action enumeration with bowwow big-stack filter
# ---------------------------------------------------------------------------


def enumerate_actions(state, player, cfg):
    actions = []
    my_planets = [p for p in state.planets.values() if p.owner == player]
    other_planets = [p for p in state.planets.values() if p.owner != player]
    for src in my_planets:
        if src.ships < cfg.min_launch_ships:
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
                threshold = cfg.min_launch_ships * cfg.min_send_fraction
                if send < threshold:
                    continue
                if send > src.ships - 1.0:
                    send = src.ships - 1.0
                if send < threshold:
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
    if len(actions) > cfg.max_top_actions_per_step:
        actions.sort(key=lambda a: -a.send_ships)
        actions = actions[: cfg.max_top_actions_per_step]
    return actions


# ---------------------------------------------------------------------------
# Mock opponent (starter-agent-like)
# ---------------------------------------------------------------------------


def _mock_opponent_actions(state, player):
    actions = []
    own = [p for p in state.planets.values() if p.owner == player]
    others = [p for p in state.planets.values() if p.owner != player]
    if not own or not others:
        return actions
    for src in own:
        if src.ships < 15.0:
            continue
        best_tgt = None
        best_d = float("inf")
        for t in others:
            d = math.hypot(t.x - src.x, t.y - src.y)
            if d < best_d:
                best_d = d
                best_tgt = t
        if best_tgt is None or best_d < 1.0:
            continue
        send = max(5.0, src.ships * 0.5)
        if send > src.ships - 1.0:
            send = src.ships - 1.0
        if send < 5.0:
            continue
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
# Sim step
# ---------------------------------------------------------------------------


def _apply_launches(state, actions, player):
    for act in actions:
        src = state.planets.get(act.src_pid)
        if src is None or src.owner != player:
            continue
        send = min(act.send_ships, max(src.ships - 1.0, 0.0))
        if send <= 0:
            continue
        src.ships -= send
        state.fleets.append(Fleet(player, send, act.target_pid, act.eta))


def _resolve_arrivals(state):
    arrived = {}
    pending = []
    for f in state.fleets:
        if f.eta <= 1.0:
            buf = arrived.setdefault(f.target_pid, {})
            buf[f.owner] = buf.get(f.owner, 0.0) + f.ships
        else:
            f.eta -= 1.0
            pending.append(f)
    state.fleets = pending

    for tgt_pid, by_owner in arrived.items():
        tgt = state.planets.get(tgt_pid)
        if tgt is None:
            continue
        if tgt.owner >= 0:
            by_owner[tgt.owner] = by_owner.get(tgt.owner, 0.0) + tgt.ships
            tgt.ships = 0.0
        sorted_owners = sorted(by_owner.items(), key=lambda kv: -kv[1])
        if not sorted_owners:
            continue
        top_owner, top_ships = sorted_owners[0]
        second_ships = sorted_owners[1][1] if len(sorted_owners) >= 2 else 0.0
        if top_ships == second_ships and len(sorted_owners) >= 2:
            tgt.owner = -1
            tgt.ships = 0.0
        else:
            tgt.owner = top_owner
            tgt.ships = top_ships - second_ships


def _grow_planets(state):
    for p in state.planets.values():
        if p.owner >= 0:
            p.ships += p.prod


def sim_step(state, actions_by_player):
    for player, acts in actions_by_player.items():
        _apply_launches(state, acts, player)
    _resolve_arrivals(state)
    _grow_planets(state)
    state.step += 1


# ---------------------------------------------------------------------------
# Leaf evaluator
# ---------------------------------------------------------------------------


def evaluate_leaf(state, player, cfg):
    my_planets = state.player_planets(player)
    enemy_planets = sum(1 for p in state.planets.values() if p.owner >= 0 and p.owner != player)
    my_ships = state.player_ships(player)
    enemy_ships = sum(
        p.ships for p in state.planets.values() if p.owner >= 0 and p.owner != player
    ) + sum(f.ships for f in state.fleets if f.owner != player and f.owner >= 0)

    if my_planets == 0:
        return -cfg.terminal_bonus
    alive = state.alive_players()
    alive.discard(player)
    if not alive:
        return cfg.terminal_bonus

    return (
        cfg.leaf_alpha * my_planets
        + cfg.leaf_beta * my_ships
        - cfg.leaf_gamma * enemy_ships
        - cfg.leaf_delta * enemy_planets
    )


# ---------------------------------------------------------------------------
# Beam search
# ---------------------------------------------------------------------------


@dataclass
class BeamNode:
    state: SimState
    first_actions: list
    score: float


def _action_combos(actions, cfg):
    combos = [[]]
    actions_sorted = sorted(actions, key=lambda a: (-a.send_ships, a.eta))
    for act in actions_sorted[: cfg.beam_width - 1]:
        combos.append([act])
    return combos


def beam_search(state, player, cfg):
    root_actions = enumerate_actions(state, player, cfg)
    if not root_actions:
        return []
    initial_combos = _action_combos(root_actions, cfg)

    beam = []
    for combo in initial_combos:
        sim = state.copy()
        opp = {}
        for other in (0, 1, 2, 3):
            if other == player:
                continue
            opp[other] = _mock_opponent_actions(sim, other)
        sim_step(sim, {player: combo, **opp})
        beam.append(BeamNode(state=sim, first_actions=combo, score=0.0))

    for _ in range(1, cfg.depth):
        new_beam = []
        for node in beam:
            my_acts = enumerate_actions(node.state, player, cfg)
            combos = _action_combos(my_acts, cfg) if my_acts else [[]]
            for combo in combos[:2]:
                sim = node.state.copy()
                opp = {}
                for other in (0, 1, 2, 3):
                    if other == player:
                        continue
                    opp[other] = _mock_opponent_actions(sim, other)
                sim_step(sim, {player: combo, **opp})
                new_beam.append(BeamNode(state=sim, first_actions=node.first_actions, score=0.0))
        for n in new_beam:
            n.score = evaluate_leaf(n.state, player, cfg)
        new_beam.sort(key=lambda n: -n.score)
        beam = new_beam[: cfg.beam_width]
        if not beam:
            break

    for n in beam:
        if n.score == 0.0:
            n.score = evaluate_leaf(n.state, player, cfg)
    beam.sort(key=lambda n: -n.score)
    return beam[0].first_actions


# ---------------------------------------------------------------------------
# Public entrypoint expected by kaggle_environments
# ---------------------------------------------------------------------------


def agent(obs, config=None):
    """Kaggle entrypoint. Returns a list of [src_pid, angle_rad, ships]."""
    if isinstance(obs, dict):
        obs_dict = obs
    else:
        obs_dict = {
            "player": getattr(obs, "player", 0),
            "planets": getattr(obs, "planets", []),
            "fleets": getattr(obs, "fleets", []),
            "step": getattr(obs, "step", 0),
            "angular_velocity": getattr(obs, "angular_velocity", 0.04),
        }
    player = int(obs_dict.get("player", 0))
    state = obs_to_state(obs_dict)
    actions = beam_search(state, player, CFG)

    moves = []
    threshold = int(CFG.min_launch_ships * CFG.min_send_fraction)
    for act in actions:
        src = state.planets.get(act.src_pid)
        if src is None or src.owner != player:
            continue
        send = int(min(act.send_ships, max(src.ships - 1.0, 0.0)))
        if send < threshold:
            continue
        moves.append([act.src_pid, act.angle, send])

    # Fallback expansion mode: bowwow-style big-stack search only triggers once
    # we have planet(s) with >= 100 ships. Early game / low-stack situations
    # need cheap expansion to build that stack. Mirrors a starter-like
    # nearest-target half-launch loop, but uses takeover-cost sizing.
    if not moves:
        moves = _early_game_expansion(state, player)

    return moves


def _early_game_expansion(state, player):
    """Cheap expansion mode used when no big-stack action is available.

    Each owned planet with >=6 ships launches at the cheapest nearby non-owned
    target, using ``takeover = ships + prod * eta + 1`` sizing.
    """
    out = []
    my_planets = [p for p in state.planets.values() if p.owner == player]
    others = [p for p in state.planets.values() if p.owner != player]
    if not my_planets or not others:
        return out
    in_flight_targets = {f.target_pid for f in state.fleets if f.owner == player}
    for src in my_planets:
        if src.ships < 6:
            continue
        best = None
        best_score = float("inf")
        for tgt in others:
            if tgt.pid == src.pid or tgt.pid in in_flight_targets:
                continue
            d = math.hypot(tgt.x - src.x, tgt.y - src.y)
            if d < 1.0:
                continue
            # prefer neutral over enemy, prefer high production, prefer near
            owner_pen = 0.0 if tgt.owner == -1 else 30.0
            score = d + owner_pen - tgt.prod * 4.0 + tgt.ships * 0.5
            if score < best_score:
                best_score = score
                best = tgt
        if best is None:
            continue
        d = math.hypot(best.x - src.x, best.y - src.y)
        eta_guess = d / max(fleet_speed(src.ships * 0.6), 0.5)
        needed = int(best.ships + best.prod * eta_guess + 1)
        if best.owner == -1:
            needed = max(needed, int(best.ships) + 1)
        send = min(int(src.ships * 0.6), int(src.ships - 1))
        send = max(send, needed)
        send = min(send, int(src.ships - 1))
        if send < 5:
            continue
        if _path_crosses_sun(src.x, src.y, best.x, best.y):
            ang = _safe_angle(src.x, src.y, best.x, best.y)
        else:
            ang = math.atan2(best.y - src.y, best.x - src.x)
        out.append([src.pid, ang, send])
        src.ships -= send
        in_flight_targets.add(best.pid)
    return out


if __name__ == "__main__":
    print("mcts_v1 loaded")
