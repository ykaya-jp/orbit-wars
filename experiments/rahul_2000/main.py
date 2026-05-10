# ELITE-BOT v5 (Rahul Chauhan, public notebook target-score-2000-4)
# v2 build: last-definition-per-name regex extraction (redef-safe)
# Source: kaggle.com/code/rahulchauhan016/orbit-wars-target-score-2000-4

import math, time, random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional

SUN_X, SUN_Y = 50.0, 50.0
SUN_RADIUS = 5.0
INNER_ORBIT_R = 30.0
MAX_TIME_MS = 900
PHASE_THRESHOLDS = (0.22, 0.58)

def fleet_speed(ships: int, cap: float = 6.0) -> float:
    return min(1.0 + ships // 20, cap)


# ── Sun collision: ray vs circle ──────────────────────────────────────────────

def hits_sun(sx: float, sy: float, angle: float, margin: float = 1.8) -> bool:
    dx, dy = math.cos(angle), math.sin(angle)
    t = (SUN_X - sx) * dx + (SUN_Y - sy) * dy
    if t < 0:
        return False
    return math.hypot(sx + t * dx - SUN_X, sy + t * dy - SUN_Y) < SUN_RADIUS + margin


print("Imports OK.")

env0 = make("orbit_wars", debug=True)
print(f"Env  : {env0.name} v{env0.version}")
print(
    f"Steps: {env0.configuration.episodeSteps}  |  Timeout: {env0.configuration.actTimeout}s/turn"
)
print(f"MaxSpd: {env0.configuration.shipSpeed} units/turn")

print("\nFleet Speed Formula  speed = min(1 + ships//20, 6)")
print(f"{'Ships':>7}  {'Speed':>6}  {'50u ETA':>9}  {'100u ETA':>10}")
for n in [1, 5, 10, 20, 40, 60, 80, 100, 120]:
    s = fleet_speed(n)
    print(f"  {n:>5}   {s:>5.1f}  {50/s:>10.1f}  {100/s:>11.1f}")

print("\nSun collision tests:")
cases = [
    (10, 50, 0, "east through sun"),
    (10, 80, math.atan2(-30, 40), "diagonal miss"),
    (50, 5, math.pi / 2, "north, safe"),
]
for sx, sy, ang, desc in cases:
    print(f"  {'HIT ':5} {desc}" if hits_sun(sx, sy, ang) else f"  {'SAFE':5} {desc}")

env0.run(["random", "random"])
obs0 = env0.steps[1][0].observation
print(
    f"\nSample obs: {len(obs0.planets)} planets  {len(obs0.fleets)} fleets  omega={obs0.angular_velocity:.5f} rad/turn"
)

class Planet:
    __slots__ = ("id", "owner", "x", "y", "radius", "ships", "production")

    def __init__(self, r):
        self.id, self.owner, self.x, self.y, self.radius, self.ships, self.production = r

    def dist(self, o):
        return math.hypot(self.x - o.x, self.y - o.y)

    def dist_xy(self, x, y):
        return math.hypot(self.x - x, self.y - y)

    def angle_to(self, o):
        return math.atan2(o.y - self.y, o.x - self.x)

    def angle_xy(self, x, y):
        return math.atan2(y - self.y, x - self.x)

    def __repr__(self):
        return f"P(id={self.id},own={self.owner},sh={self.ships},pr={self.production})"

class Fleet:
    __slots__ = ("id", "owner", "x", "y", "angle", "from_planet_id", "ships")

    def __init__(self, r):
        self.id, self.owner, self.x, self.y, self.angle, self.from_planet_id, self.ships = r

class GameState:
    def __init__(self, obs):
        g = (
            lambda k: getattr(obs, k, None)
            if hasattr(obs, k)
            else (obs.get(k) if isinstance(obs, dict) else None)
        )
        self.my_id = g("player") or 0
        self.ang_vel = g("angular_velocity") or 0.0
        self.step = g("step") or 0
        self.planets = [Planet(p) for p in (g("planets") or [])]
        self.fleets = [Fleet(f) for f in (g("fleets") or [])]
        self.comet_ids = set(g("comet_planet_ids") or [])
        self._pm = {p.id: p for p in self.planets}
        self.my_pl = [p for p in self.planets if p.owner == self.my_id]
        self.en_pl = [p for p in self.planets if p.owner not in (-1, self.my_id)]
        self.neu_pl = [p for p in self.planets if p.owner == -1]
        self.en_ids = list({p.owner for p in self.en_pl})
        self.incoming = defaultdict(lambda: defaultdict(int))
        for f in self.fleets:
            t = self._tgt(f)
            if t is not None:
                self.incoming[t][f.owner] += f.ships

    def _tgt(self, f):
        b, bd = None, 9999.0
        for p in self.planets:
            a = math.atan2(p.y - f.y, p.x - f.x)
            if abs((a - f.angle + math.pi) % (2 * math.pi) - math.pi) < 0.28:
                d = math.hypot(p.x - f.x, p.y - f.y)
                if d < bd:
                    bd, b = d, p.id
        return b

    def get(self, pid):
        return self._pm.get(pid)

    def is_inner(self, p):
        return p.dist_xy(SUN_X, SUN_Y) < INNER_ORBIT_R

    def is_comet(self, p):
        return p.id in self.comet_ids

    def net_threat(self, p):
        inc = self.incoming.get(p.id, {})
        return sum(v for k, v in inc.items() if k not in (self.my_id, -1)) - inc.get(self.my_id, 0)

    def total_ships(self, owner):
        return sum(p.ships for p in self.planets if p.owner == owner) + sum(
            f.ships for f in self.fleets if f.owner == owner
        )

    def phase(self):
        r = len(self.my_pl) / max(len(self.planets), 1)
        lo, hi = PHASE_THRESHOLDS
        return "early" if r < lo else ("late" if r >= hi else "mid")

    def centroid(self):
        if not self.my_pl:
            return SUN_X, SUN_Y
        return (
            sum(p.x for p in self.my_pl) / len(self.my_pl),
            sum(p.y for p in self.my_pl) / len(self.my_pl),
        )


gs0 = GameState(obs0)
print(f"GameState: player={gs0.my_id}  phase={gs0.phase()}")
print(
    f"  my={len(gs0.my_pl)}  enemy={len(gs0.en_pl)}  neutral={len(gs0.neu_pl)}  comets={len(gs0.comet_ids)}"
)
print(f"  fleets total={len(gs0.fleets)}")

class Predictor:
    def __init__(self, state):
        self.s = state

    def future_pos(self, p, turns):
        if not self.s.is_inner(p):
            return p.x, p.y
        r = p.dist_xy(SUN_X, SUN_Y)
        a0 = math.atan2(p.y - SUN_Y, p.x - SUN_X)
        a1 = a0 + self.s.ang_vel * turns
        return SUN_X + r * math.cos(a1), SUN_Y + r * math.sin(a1)

    def intercept(self, src, dst, ships, iters=6):
        spd = fleet_speed(ships)
        tx, ty = dst.x, dst.y
        for _ in range(iters):
            d = math.hypot(tx - src.x, ty - src.y)
            tx, ty = self.future_pos(dst, max(1, int(d / spd)))
        return tx, ty

    def aim(self, src, dst, ships):
        if not self.s.is_inner(dst):
            return src.angle_to(dst)
        tx, ty = self.intercept(src, dst, ships)
        return src.angle_xy(tx, ty)

    def eta(self, src, dst, ships):
        tx, ty = self.intercept(src, dst, ships)
        return max(1, int(math.hypot(tx - src.x, ty - src.y) / fleet_speed(ships)))

    def safe_aim(self, src, dst, ships):
        a = self.aim(src, dst, ships)
        if hits_sun(src.x, src.y, a):
            for delta in [0.08, -0.08, 0.16, -0.16, 0.28, -0.28, 0.45, -0.45]:
                if not hits_sun(src.x, src.y, a + delta):
                    return a + delta
        return a


pred0 = Predictor(gs0)
print("Lead-aim test (inner planets get non-zero delta):")
if gs0.my_pl and gs0.neu_pl:
    src = gs0.my_pl[0]
    for dst in gs0.neu_pl[:5]:
        naive = src.angle_to(dst)
        lead = pred0.aim(src, dst, 40)
        print(
            f"  dst={dst.id:>2} inner={str(gs0.is_inner(dst)):5}  "
            f"naive={math.degrees(naive):7.2f}  lead={math.degrees(lead):7.2f}  "
            f"delta={math.degrees(abs(lead-naive)):.4f}  ETA={pred0.eta(src,dst,40)}"
        )

class SimP:
    __slots__ = ("id", "owner", "ships", "production")

    def __init__(self, p):
        self.id, self.owner, self.ships, self.production = p.id, p.owner, p.ships, p.production

class SimF:
    __slots__ = ("owner", "tid", "ships", "eta")

    def __init__(self, o, t, s, e):
        self.owner, self.tid, self.ships, self.eta = o, t, s, e

def sim_step(P: dict, F: list):
    for p in P.values():
        if p.owner >= 0:
            p.ships += p.production
    nxt = []
    for f in F:
        f.eta -= 1
        if f.eta <= 0:
            p = P[f.tid]
            if p.owner == f.owner:
                p.ships += f.ships
            else:
                p.ships -= f.ships
                if p.ships < 0:
                    p.owner = f.owner
                    p.ships = abs(p.ships)
        else:
            nxt.append(f)
    F[:] = nxt

def clone(state: GameState):
    P = {p.id: SimP(p) for p in state.planets}
    F = []
    for f in state.fleets:
        t = state._tgt(f)
        if t:
            tp = state.get(t)
            if tp:
                e = max(1, int(math.hypot(tp.x - f.x, tp.y - f.y) / fleet_speed(f.ships)))
                F.append(SimF(f.owner, t, f.ships, e))
    return P, F

def eval_sim(
    P: dict, F: list, my_id: int, ws=1.0, wp=46.0, wc=20.0, wr=-2.8, wb=9.0, wf=0.6, wn=12.0
) -> float:
    ms = sum(p.ships for p in P.values() if p.owner == my_id)
    ms += sum(f.ships for f in F if f.owner == my_id)
    es = sum(p.ships for p in P.values() if p.owner not in (-1, my_id))
    es += sum(f.ships for f in F if f.owner not in (-1, my_id))
    mp = sum(p.production for p in P.values() if p.owner == my_id)
    ep = sum(p.production for p in P.values() if p.owner not in (-1, my_id))
    mc = sum(1 for p in P.values() if p.owner == my_id)
    ec = sum(1 for p in P.values() if p.owner not in (-1, my_id))
    threat = max(0, es - ms)
    mf = sum(f.ships for f in F if f.owner == my_id)
    ef = sum(f.ships for f in F if f.owner not in (-1, my_id))
    return ws * (ms - es) + wp * (mp - ep) + wc * (mc - ec) + wr * threat + wf * (mf - ef)

def run_actions(state: GameState, pred: "Predictor", actions: list, steps: int = 8) -> float:
    mi = state.my_id
    P, F = clone(state)
    for fi, ti, sh in actions:
        sp = state.get(fi)
        dp = state.get(ti)
        if sp and dp and P.get(fi) and P[fi].ships >= sh > 0:
            e = pred.eta(sp, dp, sh)
            F.append(SimF(mi, ti, sh, e))
            P[fi].ships -= sh
    for _ in range(steps):
        sim_step(P, F)
    return eval_sim(P, F, mi)


P0, F0 = clone(gs0)
for _ in range(8):
    sim_step(P0, F0)
print(f"8-turn no-action sim score: {eval_sim(P0,F0,gs0.my_id):.1f}")

class EliteEval:
    # Tuned weights targeting score 2000.4
    WS = 1.0  # ship delta
    WP = 46.0  # production delta  (compounds over time)
    WC = 20.0  # planet count delta
    WR = -2.8  # net risk
    WB = 9.0  # border pressure
    WF = 0.6  # fleet momentum
    WN = 12.0  # neutral denial (prod of neutrals we block enemy from)

    @classmethod
    def score(cls, state: GameState) -> float:
        mi = state.my_id
        ms = state.total_ships(mi)
        es = sum(state.total_ships(e) for e in state.en_ids) + 1e-9
        mp = sum(p.production for p in state.my_pl)
        ep = sum(p.production for p in state.en_pl)
        mc = len(state.my_pl)
        ec = len(state.en_pl)
        threat = sum(max(0, state.net_threat(p)) for p in state.my_pl)
        mf = sum(f.ships for f in state.fleets if f.owner == mi)
        ef = sum(f.ships for f in state.fleets if f.owner not in (-1, mi))
        cx, cy = state.centroid()
        border = sum(
            (35 - m.dist(e)) / 35 * m.production
            for m in state.my_pl
            for e in state.en_pl
            if m.dist(e) < 35
        )
        # Neutral denial: neutrals close to enemy but not us
        ndeny = sum(
            n.production
            for n in state.neu_pl
            if any(n.dist(e) < 25 for e in state.en_pl)
            and not any(n.dist(m) < 25 for m in state.my_pl)
        )
        return (
            cls.WS * (ms - es)
            + cls.WP * (mp - ep)
            + cls.WC * (mc - ec)
            + cls.WR * threat
            + cls.WB * border
            + cls.WF * (mf - ef)
            - cls.WN * ndeny
        )

    @classmethod
    def breakdown(cls, state: GameState) -> dict:
        mi = state.my_id
        ms = state.total_ships(mi)
        es = sum(state.total_ships(e) for e in state.en_ids) + 1e-9
        mp = sum(p.production for p in state.my_pl)
        ep = sum(p.production for p in state.en_pl)
        mc = len(state.my_pl)
        ec = len(state.en_pl)
        threat = sum(max(0, state.net_threat(p)) for p in state.my_pl)
        mf = sum(f.ships for f in state.fleets if f.owner == mi)
        ef = sum(f.ships for f in state.fleets if f.owner not in (-1, mi))
        border = sum(
            (35 - m.dist(e)) / 35 * m.production
            for m in state.my_pl
            for e in state.en_pl
            if m.dist(e) < 35
        )
        ndeny = sum(
            n.production
            for n in state.neu_pl
            if any(n.dist(e) < 25 for e in state.en_pl)
            and not any(n.dist(m) < 25 for m in state.my_pl)
        )
        return {
            "Ships": cls.WS * (ms - es),
            "Prod": cls.WP * (mp - ep),
            "Control": cls.WC * (mc - ec),
            "Risk": cls.WR * threat,
            "Border": cls.WB * border,
            "Fleet": cls.WF * (mf - ef),
            "NeutDeny": -cls.WN * ndeny,
            "TOTAL": cls.score(state),
        }


bd = EliteEval.breakdown(gs0)
print("7-Component Evaluator Breakdown:")
for k, v in bd.items():
    bar = "#" * max(0, int(abs(v) / 8))
    print(f"  {k:<12}: {('+' if v>=0 else '')}{v:>9.1f}  {bar}")

class MCTSNode:
    __slots__ = ("action", "parent", "children", "visits", "value", "untried")

    def __init__(self, action=None, parent=None, untried=None):
        self.action = action
        self.parent = parent
        self.children = []
        self.visits = 0
        self.value = 0.0
        self.untried = untried or []

    def ucb1(self, c=1.41):
        if self.visits == 0:
            return float("inf")
        return self.value / self.visits + c * math.sqrt(math.log(self.parent.visits) / self.visits)

    def best_child(self, c=1.41):
        return max(self.children, key=lambda n: n.ucb1(c))

    def fully_expanded(self):
        return not self.untried

    def is_leaf(self):
        return not self.children

class MCTSEngine:
    def __init__(self, state, pred, tl_ms=420, depth=10, c=1.41):
        self.s = state
        self.pred = pred
        self.tl = tl_ms / 1000.0
        self.depth = depth
        self.c = c
        self.mi = state.my_id

    def _cands(self):
        acts = [(None, None, None)]
        for src in self.s.my_pl:
            bud = max(0, src.ships - max(src.production * 2, 4))
            targets = sorted(self.s.en_pl + self.s.neu_pl, key=lambda p: src.dist(p))[:7]
            for dst in targets:
                need = dst.ships + 5
                if bud >= need:
                    acts.append((src.id, dst.id, need))
                half = bud // 2
                if half > 4 and half != need:
                    acts.append((src.id, dst.id, half))
        return acts

    def _apply(self, action, P, F):
        fi, ti, sh = action
        if fi is None:
            return
        sp = self.s.get(fi)
        dp = self.s.get(ti)
        src = P.get(fi)
        if src and sp and dp and src.ships >= sh > 0 and src.owner == self.mi:
            F.append(SimF(self.mi, ti, sh, self.pred.eta(sp, dp, sh)))
            src.ships -= sh

    def _rollout(self, P, F, depth):
        Pc = {pid: SimP(p) for pid, p in P.items()}
        Fc = [SimF(f.owner, f.tid, f.ships, f.eta) for f in F]
        for _ in range(depth):
            srcs = [p for p in Pc.values() if p.owner == self.mi and p.ships > 5]
            tgts = [p for p in Pc.values() if p.owner != self.mi]
            if srcs and tgts:
                src = random.choice(srcs)
                dst = random.choice(tgts)
                s = random.randint(1, max(1, src.ships // 3))
                src.ships -= s
                Fc.append(SimF(self.mi, dst.id, s, 10))
            sim_step(Pc, Fc)
        return eval_sim(
            Pc,
            Fc,
            self.mi,
            EliteEval.WS,
            EliteEval.WP,
            EliteEval.WC,
            EliteEval.WR,
            EliteEval.WB,
            EliteEval.WF,
        )

    def search(self):
        cands = self._cands()
        root = MCTSNode(untried=cands[:])
        t0 = time.time()
        iters = 0
        while time.time() - t0 < self.tl:
            node = root
            P, F = clone(self.s)
            while node.fully_expanded() and not node.is_leaf():
                node = node.best_child(self.c)
                self._apply(node.action, P, F)
                sim_step(P, F)
            if node.untried:
                a = random.choice(node.untried)
                node.untried.remove(a)
                self._apply(a, P, F)
                sim_step(P, F)
                child = MCTSNode(action=a, parent=node, untried=self._cands())
                node.children.append(child)
                node = child
            r = self._rollout(P, F, self.depth)
            while node:
                node.visits += 1
                node.value += r
                node = node.parent
            iters += 1
        if not root.children:
            return (None, None, None), iters, root
        best = max(root.children, key=lambda n: n.visits)
        return best.action, iters, root


pred0 = Predictor(gs0)
mcts0 = MCTSEngine(gs0, pred0, tl_ms=400)
act0, iters0, root0 = mcts0.search()
print(f"MCTS: {iters0} iterations | best={act0}")
if root0.children:
    top = sorted(root0.children, key=lambda n: -n.visits)[:5]
    print(f"Top visits: {[n.visits for n in top]}")

class OpponentModel:
    def __init__(self):
        self.ship_h = defaultdict(list)
        self.planet_h = defaultdict(list)
        self.atk = defaultdict(list)
        self.last_pl = {}

    def update(self, state: GameState):
        for eid in state.en_ids:
            self.ship_h[eid].append(state.total_ships(eid))
            self.planet_h[eid].append(len([p for p in state.planets if p.owner == eid]))
            for f in state.fleets:
                if f.owner != eid:
                    continue
                t = state._tgt(f)
                if t:
                    tp = state.get(t)
                    if tp and tp.owner == state.my_id:
                        self.atk[eid].append({"turn": state.step, "ships": f.ships})

    def aggression(self, eid: int) -> float:
        n = len(self.atk.get(eid, []))
        t = max(len(self.ship_h.get(eid, [1])), 1)
        return min(n / t * 5, 1.0)

    def growth_rate(self, eid: int) -> float:
        h = self.ship_h.get(eid, [])
        if len(h) < 2:
            return 0.0
        w = h[-20:]
        return (w[-1] - w[0]) / max(len(w) - 1, 1)

    def likely_target(self, eid: int, state: GameState) -> Planet | None:
        ep = [p for p in state.planets if p.owner == eid]
        mp = state.my_pl
        if not ep or not mp:
            return None
        best = min(((ep_, mp_) for ep_ in ep for mp_ in mp), key=lambda x: x[0].dist(x[1]))
        return best[1]

class FleetInterceptor:
    def __init__(self, state: GameState, pred: Predictor):
        self.s = state
        self.pred = pred

    def fleet_at(self, f: Fleet, t: int):
        spd = fleet_speed(f.ships)
        return f.x + math.cos(f.angle) * spd * t, f.y + math.sin(f.angle) * spd * t

    def find_window(self, f: Fleet, src: Planet, our_ships: int):
        our_spd = fleet_speed(our_ships)
        for t in range(1, 50):
            fx, fy = self.fleet_at(f, t)
            d = math.hypot(fx - src.x, fy - src.y)
            if abs(d / our_spd - t) < 1.5:
                return fx, fy, t
        return None

    def find_all(self):
        out = []
        for f in self.s.fleets:
            if f.owner in (-1, self.s.my_id):
                continue
            t = self.s._tgt(f)
            if not t:
                continue
            tp = self.s.get(t)
            if not tp or tp.owner != self.s.my_id:
                continue
            for src in self.s.my_pl:
                our = max(5, src.ships // 3)
                r = self.find_window(f, src, our)
                if r and our > f.ships:
                    ix, iy, eta = r
                    ang = src.angle_xy(ix, iy)
                    if not hits_sun(src.x, src.y, ang):
                        out.append(
                            {
                                "en_ships": f.ships,
                                "src": src.id,
                                "our": our,
                                "ix": ix,
                                "iy": iy,
                                "eta": eta,
                                "angle": ang,
                            }
                        )
                        break
        return sorted(out, key=lambda o: -o["en_ships"])


fi0 = FleetInterceptor(gs0, pred0)
opps0 = fi0.find_all()
print(f"Intercept opportunities: {len(opps0)}")
for o in opps0[:3]:
    print(
        f"  {o['en_ships']} en ships | our={o['our']} from P{o['src']} | "
        f"intercept ({o['ix']:.1f},{o['iy']:.1f}) in {o['eta']} turns"
    )
if not opps0:
    print("  (none this turn -- typical early game)")

class CometOpp:
    def __init__(self, state: GameState, pred: Predictor):
        self.s = state
        self.pred = pred

    def active(self):
        return [p for p in self.s.planets if self.s.is_comet(p)]

    def roi(self, src: Planet, c: Planet) -> float:
        cost = c.ships + 3
        if src.ships < cost + 2:
            return -1.0
        turns_left = max(1, 500 - self.s.step)
        val = c.production * min(45, turns_left)
        transit = src.dist(c) / fleet_speed(cost)
        return (val - transit) / max(cost, 1)

    def best(self):
        br, best = -1.0, None
        for src in self.s.my_pl:
            for c in self.active():
                r = self.roi(src, c)
                if r > br:
                    br = r
                    best = (src, c, c.ships + 3)
        return best if br > 0 else None


ct0 = CometOpp(gs0, pred0)
print(f"Active comets: {len(ct0.active())}  Best capture: {ct0.best()}")
print("Searching for a game with comets...")
found = False
for _ in range(15):
    ec = make("orbit_wars", debug=False)
    ec.run(["random", "random"])
    for sd in ec.steps[5:]:
        gsc = GameState(sd[0].observation)
        if gsc.comet_ids:
            ct_c = CometOpp(gsc, Predictor(gsc))
            print(f"  Turn {gsc.step}: {len(gsc.comet_ids)} comet(s). Best={ct_c.best()}")
            found = True
            break
    if found:
        break
if not found:
    print("  No comets found in 15 games.")

class DiplomacyEngine:
    def __init__(self, state: GameState, opp: OpponentModel | None = None):
        self.s = state
        self.opp = opp

    def power(self, eid: int) -> float:
        return (
            self.s.total_ships(eid)
            + sum(p.production for p in self.s.planets if p.owner == eid) * 24
        )

    def threat_to_us(self, eid: int) -> float:
        ep = [p for p in self.s.planets if p.owner == eid]
        prox = sum(1.0 / max(e.dist(m), 1) for e in ep for m in self.s.my_pl)
        sh = self.s.total_ships(eid)
        aggr = 1.0 + (self.opp.aggression(eid) if self.opp else 0.0)
        return (prox * 38 + sh * 0.65) * aggr

    def rank(self):
        pws = {e: self.power(e) for e in self.s.en_ids}
        mx = max(pws.values()) if pws else 1
        out = []
        for eid in self.s.en_ids:
            t = self.threat_to_us(eid)
            r = (
                "LEADER"
                if pws[eid] == mx and len(self.s.en_ids) > 1
                else ("WEAK" if pws[eid] < mx * 0.35 else "MID")
            )
            if r == "LEADER":
                t *= 1.7
            elif r == "WEAK":
                t *= 0.45
            out.append((eid, t, r, pws[eid]))
        return sorted(out, key=lambda x: -x[1])

    def primary_target(self) -> Planet | None:
        ranked = self.rank()
        if not ranked or not self.s.my_pl:
            return None
        top_eid = ranked[0][0]
        ep = [p for p in self.s.planets if p.owner == top_eid]
        if not ep:
            return None
        cx, cy = self.s.centroid()
        return min(ep, key=lambda p: p.ships + math.hypot(p.x - cx, p.y - cy) * 0.38)


env4 = make("orbit_wars", debug=False)
env4.run(["random"] * 4)
obs4 = env4.steps[min(30, len(env4.steps) - 1)][0].observation
gs4 = GameState(obs4)
diplo4 = DiplomacyEngine(gs4, GLOBAL_OPP)
print(f"4-Player Threat Matrix (turn {gs4.step}):")
for eid, th, reason, pw in diplo4.rank():
    print(f"  E{eid} [{reason:6s}]: power={pw:.0f}  threat={th:.1f}")
pt = diplo4.primary_target()
print(f"Primary target: planet {pt.id if pt else None}")

class BeamSearch:
    # Keeps top-K states at each depth instead of a single rollout.
    # More thorough than greedy; cheaper than full MCTS.
    def __init__(self, state: GameState, pred: Predictor, K: int = 3, depth: int = 5):
        self.s = state
        self.pred = pred
        self.K = K
        self.depth = depth
        self.mi = state.my_id

    def _atom_actions(self):
        acts = [(None, None, None)]
        for src in self.s.my_pl:
            bud = max(0, src.ships - max(src.production * 2, 4))
            for dst in sorted(self.s.en_pl + self.s.neu_pl, key=lambda p: src.dist(p))[:6]:
                need = dst.ships + 5
                if bud >= need:
                    acts.append((src.id, dst.id, need))
        return acts

    def _score(self, P, F):
        return eval_sim(
            P,
            F,
            self.mi,
            EliteEval.WS,
            EliteEval.WP,
            EliteEval.WC,
            EliteEval.WR,
            EliteEval.WB,
            EliteEval.WF,
        )

    def best_action(self):
        atoms = self._atom_actions()
        # Beam: list of (score, actions_list, P, F)
        beam = []
        for a in atoms:
            P, F = clone(self.s)
            fi, ti, sh = a
            if fi is not None:
                sp = self.s.get(fi)
                dp = self.s.get(ti)
                if sp and dp and P.get(fi) and P[fi].ships >= sh > 0:
                    P[fi].ships -= sh
                    F.append(SimF(self.mi, ti, sh, self.pred.eta(sp, dp, sh)))
            sim_step(P, F)
            beam.append((self._score(P, F), [a], P, F))

        beam.sort(key=lambda x: -x[0])
        beam = beam[: self.K]

        for _ in range(self.depth - 1):
            next_beam = []
            for sc, acts, P0, F0 in beam:
                for a in atoms:
                    P = {pid: SimP(p) for pid, p in P0.items()}
                    F = [SimF(f.owner, f.tid, f.ships, f.eta) for f in F0]
                    fi, ti, sh = a
                    if fi is not None:
                        sp = self.s.get(fi)
                        dp = self.s.get(ti)
                        if sp and dp and P.get(fi) and P[fi].ships >= sh > 0:
                            P[fi].ships -= sh
                            F.append(SimF(self.mi, ti, sh, self.pred.eta(sp, dp, sh)))
                    sim_step(P, F)
                    next_beam.append((self._score(P, F), acts + [a], P, F))
            next_beam.sort(key=lambda x: -x[0])
            beam = next_beam[: self.K]

        return beam[0][1][0] if beam else (None, None, None)


bs0 = BeamSearch(gs0, pred0, K=3, depth=4)
ba0 = bs0.best_action()
print(f"Beam Search best atom action: {ba0}")

class CounterfactualRisk:
    def __init__(self, state: GameState, pred: Predictor, steps: int = 6):
        self.s = state
        self.pred = pred
        self.steps = steps
        self.mi = state.my_id

    def _enemy_best_response(self, P: dict, F: list) -> float:
        # Simulate enemy sending half their ships to our weakest planet
        my_weakest = min(
            [p for p in P.values() if p.owner == self.mi], key=lambda p: p.ships, default=None
        )
        if my_weakest is None:
            return 0.0
        for p in P.values():
            if p.owner not in (-1, self.mi) and p.ships > 10:
                F.append(SimF(p.owner, my_weakest.id, p.ships // 2, 15))
        return 0.0

    def regret(self, action) -> float:
        fi, ti, sh = action
        # Baseline: do nothing
        P0, F0 = clone(self.s)
        self._enemy_best_response(P0, F0)
        for _ in range(self.steps):
            sim_step(P0, F0)
        base = eval_sim(P0, F0, self.mi)

        # With action
        P1, F1 = clone(self.s)
        sp = self.s.get(fi)
        dp = self.s.get(ti)
        if fi and sp and dp and P1.get(fi) and P1[fi].ships >= sh > 0:
            P1[fi].ships -= sh
            F1.append(SimF(self.mi, ti, sh, self.pred.eta(sp, dp, sh)))
        self._enemy_best_response(P1, F1)
        for _ in range(self.steps):
            sim_step(P1, F1)
        with_action = eval_sim(P1, F1, self.mi)

        return base - with_action  # positive = action made things worse vs counterfactual

    def filter(self, actions: list, threshold: float = -50.0) -> list:
        # Keep actions with regret above threshold (not too risky)
        result = []
        for a in actions:
            fi, ti, sh = a
            if fi is None:
                result.append(a)
                continue
            r = self.regret(a)
            if r > threshold:
                result.append(a)
        return result if result else actions


cfr0 = CounterfactualRisk(gs0, pred0)
sample_acts = [
    (src.id, dst.id, dst.ships + 5)
    for src in gs0.my_pl[:2]
    for dst in gs0.neu_pl[:3]
    if src.ships > dst.ships + 5
]
filtered = cfr0.filter(sample_acts)
print(f"Counterfactual Risk filter: {len(sample_acts)} actions -> {len(filtered)} after pruning")

@dataclass

def budget(src: Planet, state: GameState, ratio: float = 0.70) -> int:
    threat = max(0, state.net_threat(src))
    reserve = max(src.production * 4, threat + 10)
    return max(0, int((src.ships - reserve) * ratio))

class StrategyEngine:
    def __init__(
        self,
        state: GameState,
        pred: Predictor,
        opp: OpponentModel | None = None,
        diplo: DiplomacyEngine | None = None,
    ):
        self.s = state
        self.pred = pred
        self.opp = opp
        self.diplo = diplo
        self.mi = state.my_id

    def _tval(self, src, dst):
        d = src.dist(dst)
        if d < 0.1:
            return -999.0
        val = dst.production * 58 - dst.ships
        val += 28 if dst.owner == -1 else 72 if dst.owner != self.mi else 0
        ang = self.pred.aim(src, dst, 20)
        if hits_sun(src.x, src.y, ang):
            val -= 60
        return val / (d / fleet_speed(budget(src, self.s) or 1) + 1)

    def early(self):
        A = []
        for src in sorted(self.s.my_pl, key=lambda p: -p.ships):
            b = budget(src, self.s, 0.80)
            for dst in sorted(self.s.neu_pl, key=lambda t: self._tval(src, t), reverse=True)[:6]:
                need = dst.ships + 5
                if b >= need:
                    A.append((src.id, dst.id, need))
                    b -= need
        return A

    def mid(self):
        A = []
        # Reinforce threatened planets
        for p in self.s.my_pl:
            if self.s.net_threat(p) > 0:
                for d in sorted([x for x in self.s.my_pl if x.id != p.id], key=lambda x: x.dist(p))[
                    :2
                ]:
                    s = min(self.s.net_threat(p) + 10, budget(d, self.s, 0.50))
                    if s > 0:
                        A.append((d.id, p.id, s))
        # Multi-source coordinated attack
        if self.s.en_pl:
            tgt = min(self.s.en_pl, key=lambda p: p.ships)
            need, rec = tgt.ships + 14, 0
            for src in sorted(self.s.my_pl, key=lambda p: p.dist(tgt)):
                av = budget(src, self.s, 0.72)
                if av > 0 and rec < need:
                    s = min(av, need - rec)
                    A.append((src.id, tgt.id, s))
                    rec += s
        # Neutral grab
        for src in self.s.my_pl:
            b = budget(src, self.s, 0.55)
            for dst in sorted(self.s.neu_pl, key=lambda t: src.dist(t))[:3]:
                need = dst.ships + 4
                if b >= need:
                    A.append((src.id, dst.id, need))
                    b -= need
        return A

    def late(self):
        if not self.s.en_pl:
            return self.mid()
        A = []
        pri = max(self.s.en_pl, key=lambda p: p.production)
        for src in self.s.my_pl:
            s = budget(src, self.s, 0.90)
            if s > pri.production:
                A.append((src.id, pri.id, s))
        secs = [p for p in self.s.en_pl if p.id != pri.id]
        if secs:
            for src in self.s.my_pl:
                sec = min(secs, key=lambda p: src.dist(p))
                s = budget(src, self.s, 0.35)
                if s > sec.ships:
                    A.append((src.id, sec.id, s))
        return A

    def aggro(self):
        if not self.s.en_pl:
            return []
        t = min(self.s.en_pl, key=lambda p: p.ships)
        return [
            (src.id, t.id, s) for src in self.s.my_pl for s in [budget(src, self.s, 0.94)] if s > 0
        ]

    def defend(self):
        if not self.s.my_pl:
            return []
        anchor = max(self.s.my_pl, key=lambda p: p.ships)
        return [
            (src.id, anchor.id, s)
            for src in self.s.my_pl
            if src.id != anchor.id
            for s in [budget(src, self.s, 0.45)]
            if s > 0
        ]

    def diplo_attack(self):
        if not self.diplo:
            return []
        pt = self.diplo.primary_target()
        if not pt:
            return []
        A = []
        for src in sorted(self.s.my_pl, key=lambda p: p.dist(pt))[:5]:
            s = budget(src, self.s, 0.74)
            need = pt.ships + 10
            if s >= need:
                A.append((src.id, pt.id, min(s, need + 25)))
        return A

    def counter_attack(self):
        # Attack enemy planets with low garrison (stretched their fleets).
        A = []
        for ep in self.s.en_pl:
            outgoing = sum(
                f.ships for f in self.s.fleets if f.owner == ep.owner and self.s._tgt(f) != ep.id
            )
            effective = ep.ships - outgoing
            if effective < 15:
                for src in sorted(self.s.my_pl, key=lambda p: p.dist(ep))[:2]:
                    s = budget(src, self.s, 0.60)
                    if s > effective + 3:
                        A.append((src.id, ep.id, min(s, effective + 8)))
        return A

    def all_candidates(self):
        ph = self.s.phase()
        primary = {"early": self.early, "mid": self.mid, "late": self.late}[ph]()
        return [
            primary,  # 0: phase-appropriate
            self.mid(),  # 1: balanced fallback
            self.early(),  # 2: expansion
            self.aggro(),  # 3: full aggro
            self.defend(),  # 4: defensive
            self.diplo_attack(),  # 5: diplomacy-guided
            self.counter_attack(),  # 6: counter when enemy is stretched
        ]


strat0 = StrategyEngine(gs0, pred0, GLOBAL_OPP, DiplomacyEngine(gs0, GLOBAL_OPP))
cands0 = strat0.all_candidates()
names0 = ["Phase", "Mid", "Expand", "Aggro", "Defend", "Diplo", "Counter"]
print(f"Strategy candidates (phase={gs0.phase()}):")
for name, c in zip(names0, cands0, strict=False):
    sc = run_actions(gs0, pred0, c, steps=8)
    print(f"  {name:<8}: {len(c):>2} actions -> score {sc:>9.1f}")

def elite_bot_v5(obs, config=None):
    global GLOBAL_OPP_V5
    t0 = time.time()
    elapsed = lambda: (time.time() - t0) * 1000

    try:
        state = GameState(obs)
        if not state.my_pl:
            return []
        mi = state.my_id
        pred = Predictor(state)

        # ── Update persistent opponent model ──────────────────────────────────
        GLOBAL_OPP_V5.update(state)

        # ── Build sub-engines ─────────────────────────────────────────────────
        diplo = DiplomacyEngine(state, GLOBAL_OPP_V5)
        strat = StrategyEngine(state, pred, GLOBAL_OPP_V5, diplo)
        fi_eng = FleetInterceptor(state, pred)
        ct_eng = CometOpp(state, pred)
        cfr = CounterfactualRisk(state, pred, steps=5)

        # ── 1. Fleet interception (highest priority, < 100ms) ─────────────────
        intercept_ops = []
        if elapsed() < 100:
            opps = fi_eng.find_all()
            if opps and opps[0]["en_ships"] >= 10:
                intercept_ops = opps[:3]

        # ── 2. MCTS search (420ms budget) ─────────────────────────────────────
        mcts_action = (None, None, None)
        tl_mcts = min(420, 860 - elapsed())
        if tl_mcts > 50 and state.en_pl:
            me = MCTSEngine(state, pred, tl_ms=tl_mcts, depth=10)
            mcts_action, _, _ = me.search()

        # ── 3. Beam search supplement (if time remains) ───────────────────────
        beam_action = (None, None, None)
        if elapsed() < 700 and state.en_pl:
            bs = BeamSearch(state, pred, K=3, depth=4)
            beam_action = bs.best_action()

        # ── 4. Strategy candidates (CFR-filtered) ─────────────────────────────
        cands = strat.all_candidates()
        bsc, bc = -1e18, []
        for c in cands:
            if elapsed() > 840:
                break
            filtered = cfr.filter(c, threshold=-80)
            sc = run_actions(state, pred, filtered, steps=8)
            if sc > bsc:
                bsc, bc = sc, filtered

        # ── 5. Neural gate: override to aggro if losing badly ─────────────────
        try:
            nv = NEURAL.predict(state)
            if nv < -0.65 and state.en_pl:
                ac = strat.aggro()
                sc = run_actions(state, pred, ac, steps=8)
                if sc > bsc:
                    bsc, bc = sc, ac
        except:
            pass

        # ── 6. Comet opportunism ──────────────────────────────────────────────
        comet_moves = []
        if elapsed() < 870:
            bc_comet = ct_eng.best()
            if bc_comet:
                src_c, dst_c, sh_c = bc_comet
                comet_moves = [(src_c.id, float(pred.safe_aim(src_c, dst_c, sh_c)), int(sh_c))]

        # ── Assemble final moves ──────────────────────────────────────────────
        moves: list[list] = []
        spent: dict[int, int] = {}

        def add(pid, ang, sh):
            sp = state.get(pid)
            if not sp or sp.owner != mi:
                return
            av = sp.ships - spent.get(pid, 0) - 1
            send = min(sh, max(0, av))
            if send <= 0:
                return
            moves.append([pid, float(ang), int(send)])
            spent[pid] = spent.get(pid, 0) + send

        # Priority ordering
        for o in intercept_ops:
            add(o["src"], o["angle"], o["our"])

        for act in [mcts_action, beam_action]:
            if act and act[0] is not None:
                sp = state.get(act[0])
                dp = state.get(act[1])
                if sp and dp:
                    add(act[0], pred.safe_aim(sp, dp, act[2]), act[2])

        for fi, ti, sh in bc:
            if elapsed() > 890:
                break
            sp = state.get(fi)
            dp = state.get(ti)
            if sp and dp:
                add(fi, pred.safe_aim(sp, dp, sh), sh)

        for pid, ang, sh in comet_moves:
            add(pid, ang, sh)

        return moves

    except Exception:
        return []


# ── Smoke test ────────────────────────────────────────────────────────────────

# === agent entrypoint ===
_OPP_V5 = OpponentModel()

def agent(obs, config=None):
    global _OPP_V5
    return elite_bot_v5(obs, config)
