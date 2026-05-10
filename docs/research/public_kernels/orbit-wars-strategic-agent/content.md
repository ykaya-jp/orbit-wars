## [CODE]
```python
%%capture
!pip install --upgrade "kaggle-environments>=1.28.0"
```

## [CODE]
```python
from kaggle_environments import make
env = make('orbit_wars', debug=True)
print(f'Environment: {env.name}')
```

## [CODE]
```python
%%writefile main.py
# =============================================================================
# Orbit Wars – Agent v14
# Fixes from v13:
#  1. Minimum 20 ships per fleet → guarantees speed >= 2 (v13 sent as few as 6)
#  2. More aggressive early expansion: budget ratio 0.88, 8 targets
#  3. Minimum 20 ships also enforced in mid() neutral captures
#  4. Exception logging to stderr instead of silent return []
#  5. Slightly tuned budget reserve multiplier (3x production vs 4x)
# =============================================================================
import math, time, sys, traceback
from collections import defaultdict
from typing import List, Dict, Tuple, Optional

SUN_X, SUN_Y  = 50.0, 50.0
SUN_RADIUS    = 5.0
SUN_MARGIN    = 1.8
INNER_ORBIT_R = 30.0

def fleet_speed(ships):
    return min(1.0 + int(ships) // 20, 6)

def hits_sun(sx, sy, angle):
    dx, dy = math.cos(angle), math.sin(angle)
    t = (SUN_X - sx)*dx + (SUN_Y - sy)*dy
    if t < 0: return False
    return math.hypot(sx + t*dx - SUN_X, sy + t*dy - SUN_Y) < SUN_RADIUS + SUN_MARGIN

def safe_angle(sx, sy, angle):
    if not hits_sun(sx, sy, angle): return angle
    for d in [0.08,-0.08,0.16,-0.16,0.28,-0.28,0.45,-0.45,0.65,-0.65]:
        if not hits_sun(sx, sy, angle+d): return angle+d
    return angle

class Planet:
    __slots__ = ('id','owner','x','y','radius','ships','production')
    def __init__(self, r):
        self.id,self.owner,self.x,self.y,self.radius,self.ships,self.production = \
            int(r[0]),int(r[1]),float(r[2]),float(r[3]),float(r[4]),float(r[5]),float(r[6])
    def dist(self, o): return math.hypot(self.x-o.x, self.y-o.y)
    def dist_xy(self, x, y): return math.hypot(self.x-x, self.y-y)
    def angle_to(self, o): return math.atan2(o.y-self.y, o.x-self.x)
    def angle_xy(self, x, y): return math.atan2(y-self.y, x-self.x)
    def is_inner(self): return self.dist_xy(SUN_X, SUN_Y) < INNER_ORBIT_R

class Fleet:
    __slots__ = ('id','owner','x','y','angle','from_planet','ships')
    def __init__(self, r):
        self.id,self.owner,self.x,self.y,self.angle,self.from_planet,self.ships = \
            int(r[0]),int(r[1]),float(r[2]),float(r[3]),float(r[4]),int(r[5]),float(r[6])

class GameState:
    def __init__(self, obs):
        def g(k, d=None):
            if isinstance(obs, dict): return obs.get(k, d)
            return getattr(obs, k, d)
        self.my_id   = int(g('player') or 0)
        self.ang_vel = float(g('angular_velocity') or 0.0)
        self.step    = int(g('step') or 0)
        self.planets = [Planet(p) for p in (g('planets') or [])]
        self.fleets  = [Fleet(f) for f in (g('fleets') or [])]
        self.comet_ids = set(g('comet_planet_ids') or [])
        self._pm     = {p.id: p for p in self.planets}
        # neutral=-1, players=0,1,...
        self.my_pl  = [p for p in self.planets if p.owner == self.my_id]
        self.en_pl  = [p for p in self.planets if p.owner not in (-1, self.my_id)]
        self.neu_pl = [p for p in self.planets if p.owner == -1]
        self.en_ids = list({p.owner for p in self.en_pl})
        self.incoming = defaultdict(lambda: defaultdict(float))
        for f in self.fleets:
            t = self._fleet_target(f)
            if t is not None: self.incoming[t][f.owner] += f.ships

    def _fleet_target(self, f):
        best, bd = None, 9999.0
        for p in self.planets:
            a = math.atan2(p.y-f.y, p.x-f.x)
            diff = abs((a - f.angle + math.pi) % (2*math.pi) - math.pi)
            if diff < 0.30:
                d = math.hypot(p.x-f.x, p.y-f.y)
                if d < bd: bd, b = d, p.id; best = p.id
        return best

    def get(self, pid): return self._pm.get(pid)

    def net_threat(self, p):
        inc = self.incoming.get(p.id, {})
        return sum(v for k,v in inc.items() if k not in (self.my_id,-1)) - inc.get(self.my_id, 0.0)

    def total_ships(self, owner):
        return (sum(p.ships for p in self.planets if p.owner==owner)
              + sum(f.ships for f in self.fleets if f.owner==owner))

    def phase(self):
        r = len(self.my_pl) / max(len(self.planets), 1)
        return 'early' if r < 0.22 else ('late' if r >= 0.58 else 'mid')

    def centroid(self):
        if not self.my_pl: return SUN_X, SUN_Y
        return (sum(p.x for p in self.my_pl)/len(self.my_pl),
                sum(p.y for p in self.my_pl)/len(self.my_pl))

class Predictor:
    def __init__(self, state):
        self.s = state

    def future_pos(self, p, turns):
        if not p.is_inner(): return p.x, p.y
        r  = p.dist_xy(SUN_X, SUN_Y)
        a0 = math.atan2(p.y-SUN_Y, p.x-SUN_X)
        a1 = a0 + self.s.ang_vel * turns
        return SUN_X + r*math.cos(a1), SUN_Y + r*math.sin(a1)

    def intercept(self, src, dst, ships, iters=6):
        spd = fleet_speed(ships)
        tx, ty = dst.x, dst.y
        for _ in range(iters):
            d = math.hypot(tx-src.x, ty-src.y)
            tx, ty = self.future_pos(dst, max(1, int(d/spd)))
        return tx, ty

    def aim(self, src, dst, ships):
        if not dst.is_inner(): return src.angle_to(dst)
        tx, ty = self.intercept(src, dst, ships)
        return src.angle_xy(tx, ty)

    def eta(self, src, dst, ships):
        tx, ty = self.intercept(src, dst, ships)
        return max(1, int(math.hypot(tx-src.x, ty-src.y) / fleet_speed(ships)))

    def safe_aim(self, src, dst, ships):
        a = self.aim(src, dst, ships)
        return safe_angle(src.x, src.y, a)

MIN_FLEET = 20   # minimum ships per fleet → guarantees fleet_speed >= 2

def budget(src, state, ratio=0.70):
    threat  = max(0.0, state.net_threat(src))
    reserve = max(src.production*3, threat+8)   # v14: 3x prod (was 4x), threat+8 (was +10)
    return max(0, int((src.ships - reserve) * ratio))

class SimP:
    __slots__ = ('id','owner','ships','production')
    def __init__(self, p):
        self.id,self.owner,self.ships,self.production = p.id,p.owner,p.ships,p.production

class SimF:
    __slots__ = ('owner','tid','ships','eta')
    def __init__(self, owner, tid, ships, eta):
        self.owner,self.tid,self.ships,self.eta = owner,tid,ships,eta

def clone_state(state):
    P = {p.id: SimP(p) for p in state.planets}
    F = []
    for f in state.fleets:
        t = state._fleet_target(f)
        if t is not None:
            tp = state.get(t)
            if tp:
                e = max(1, int(math.hypot(tp.x-f.x, tp.y-f.y)/fleet_speed(int(f.ships))))
                F.append(SimF(f.owner, t, f.ships, e))
    return P, F

def sim_step(P, F):
    for p in P.values():
        if p.owner >= 0: p.ships += p.production
    nxt = []
    for f in F:
        f.eta -= 1
        if f.eta <= 0:
            p = P[f.tid]
            if p.owner == f.owner: p.ships += f.ships
            else:
                p.ships -= f.ships
                if p.ships < 0: p.owner = f.owner; p.ships = abs(p.ships)
        else: nxt.append(f)
    F[:] = nxt

def eval_state(P, F, mi):
    ms = sum(p.ships for p in P.values() if p.owner==mi)
    es = sum(p.ships for p in P.values() if p.owner not in(-1,mi))
    ms += sum(f.ships for f in F if f.owner==mi)
    es += sum(f.ships for f in F if f.owner not in(-1,mi))
    mp = sum(p.production for p in P.values() if p.owner==mi)
    ep = sum(p.production for p in P.values() if p.owner not in(-1,mi))
    mc = sum(1 for p in P.values() if p.owner==mi)
    ec = sum(1 for p in P.values() if p.owner not in(-1,mi))
    return 1.0*(ms-es) + 46.0*(mp-ep) + 20.0*(mc-ec) - 2.8*max(0,es-ms) + 0.6*(ms-es)

def run_actions(state, pred, actions, steps=8):
    mi = state.my_id
    P, F = clone_state(state)
    for fi, ti, sh in actions:
        sp = state.get(fi); dp = state.get(ti)
        if sp and dp and P.get(fi) and P[fi].ships >= sh > 0:
            F.append(SimF(mi, ti, sh, pred.eta(sp, dp, sh)))
            P[fi].ships -= sh
    for _ in range(steps): sim_step(P, F)
    return eval_state(P, F, mi)

class StrategyEngine:
    def __init__(self, state, pred):
        self.s = state; self.pred = pred; self.mi = state.my_id

    def _tval(self, src, dst):
        d = src.dist(dst)
        if d < 0.1: return -999.0
        val = dst.production*58 - dst.ships
        val += 28 if dst.owner==-1 else 72
        ang = self.pred.aim(src, dst, 20)
        if hits_sun(src.x, src.y, ang): val -= 60
        return val / (d / fleet_speed(max(1, budget(src, self.s))) + 1)

    def early(self):
        A = []
        for src in sorted(self.s.my_pl, key=lambda p: -p.ships):
            b = budget(src, self.s, 0.88)            # v14: 0.88 (was 0.80)
            tgts = sorted(self.s.neu_pl, key=lambda t: self._tval(src,t), reverse=True)[:8]
            for dst in tgts:
                need = max(dst.ships + 5, MIN_FLEET)  # v14: min 20 ships → speed>=2
                if b >= need: A.append((src.id, dst.id, int(need))); b -= need
        return A

    def mid(self):
        A = []
        for p in self.s.my_pl:
            th = self.s.net_threat(p)
            if th > 0:
                donors = sorted([x for x in self.s.my_pl if x.id!=p.id], key=lambda x: x.dist(p))
                for d in donors[:2]:
                    s = min(int(th+10), budget(d, self.s, 0.50))
                    if s > 0: A.append((d.id, p.id, s))
        if self.s.en_pl:
            tgt = min(self.s.en_pl, key=lambda p: p.ships)
            need, rec = tgt.ships+14, 0
            for src in sorted(self.s.my_pl, key=lambda p: p.dist(tgt)):
                av = budget(src, self.s, 0.72)
                if av > 0 and rec < need:
                    s = min(av, need-rec); A.append((src.id, tgt.id, int(s))); rec += s
        for src in self.s.my_pl:
            b = budget(src, self.s, 0.55)
            for dst in sorted(self.s.neu_pl, key=lambda t: src.dist(t))[:3]:
                need = max(dst.ships+4, MIN_FLEET)   # v14: min 20 ships
                if b >= need: A.append((src.id, dst.id, int(need))); b -= need
        return A

    def late(self):
        if not self.s.en_pl: return self.mid()
        A = []
        pri = max(self.s.en_pl, key=lambda p: p.production)
        for src in self.s.my_pl:
            s = budget(src, self.s, 0.90)
            if s > pri.production: A.append((src.id, pri.id, int(s)))
        secs = [p for p in self.s.en_pl if p.id != pri.id]
        if secs:
            for src in self.s.my_pl:
                sec = min(secs, key=lambda p: src.dist(p))
                s = budget(src, self.s, 0.35)
                if s > sec.ships: A.append((src.id, sec.id, int(s)))
        return A

    def aggro(self):
        if not self.s.en_pl: return []
        tgt = min(self.s.en_pl, key=lambda p: p.ships)
        return [(src.id, tgt.id, int(s)) for src in self.s.my_pl
                for s in [budget(src, self.s, 0.94)] if s > 0]

    def defend(self):
        if not self.s.my_pl: return []
        anchor = max(self.s.my_pl, key=lambda p: p.ships)
        return [(src.id, anchor.id, int(s)) for src in self.s.my_pl if src.id!=anchor.id
                for s in [budget(src, self.s, 0.45)] if s > 0]

    def counter_attack(self):
        A = []
        for ep in self.s.en_pl:
            outgoing = sum(f.ships for f in self.s.fleets
                          if f.owner==ep.owner and self.s._fleet_target(f)!=ep.id)
            effective = ep.ships - outgoing
            if effective < 15:
                for src in sorted(self.s.my_pl, key=lambda p: p.dist(ep))[:2]:
                    s = budget(src, self.s, 0.60)
                    if s > effective+3:
                        A.append((src.id, ep.id, int(min(s, effective+8))))
        return A

    def all_candidates(self):
        ph = self.s.phase()
        primary = {'early': self.early, 'mid': self.mid, 'late': self.late}[ph]()
        return [primary, self.mid(), self.early(), self.aggro(),
                self.defend(), self.counter_attack()]

class FleetInterceptor:
    def __init__(self, state, pred):
        self.s = state; self.pred = pred

    def find_all(self):
        out = []
        for f in self.s.fleets:
            if f.owner in (-1, self.s.my_id): continue
            t = self.s._fleet_target(f)
            if not t: continue
            tp = self.s.get(t)
            if not tp or tp.owner != self.s.my_id: continue
            spd = fleet_speed(int(f.ships))
            for src in self.s.my_pl:
                our = max(5, int(src.ships//3))
                our_spd = fleet_speed(our)
                for ti in range(1, 50):
                    fx = f.x + math.cos(f.angle)*spd*ti
                    fy = f.y + math.sin(f.angle)*spd*ti
                    d = math.hypot(fx-src.x, fy-src.y)
                    if abs(d/our_spd - ti) < 1.5 and our > f.ships:
                        ang = src.angle_xy(fx, fy)
                        if not hits_sun(src.x, src.y, ang):
                            out.append({'en_ships': f.ships, 'src': src.id,
                                       'our': our, 'angle': ang})
                            break
        return sorted(out, key=lambda o: -o['en_ships'])

def agent(obs, config=None):
    t0 = time.time()
    elapsed_ms = lambda: (time.time()-t0)*1000
    try:
        state = GameState(obs)
        if not state.my_pl: return []
        mi   = state.my_id
        pred = Predictor(state)

        # Fleet interception
        intercept_moves = []
        if elapsed_ms() < 100:
            fi_eng = FleetInterceptor(state, pred)
            opps   = fi_eng.find_all()
            if opps and opps[0]['en_ships'] >= 10:
                intercept_moves = opps[:3]

        # Pick best strategy
        strat   = StrategyEngine(state, pred)
        cands   = strat.all_candidates()
        best_sc = -1e18
        best_c  = []
        for c in cands:
            if elapsed_ms() > 840: break
            if not c: continue
            sc = run_actions(state, pred, c, steps=8)
            if sc > best_sc: best_sc = sc; best_c = c

        # Assemble moves
        moves = []
        spent = {}

        def add(pid, ang, sh):
            sp = state.get(pid)
            if not sp or sp.owner != mi: return
            av = int(sp.ships) - spent.get(pid, 0) - 1
            send = min(int(sh), max(0, av))
            if send <= 0: return
            moves.append([pid, float(safe_angle(sp.x, sp.y, ang)), send])
            spent[pid] = spent.get(pid, 0) + send

        for o in intercept_moves:
            add(o['src'], o['angle'], o['our'])

        for fi, ti, sh in best_c:
            if elapsed_ms() > 890: break
            sp = state.get(fi); dp = state.get(ti)
            if sp and dp: add(fi, pred.safe_aim(sp, dp, sh), sh)

        return moves
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return []

if __name__ == '__main__':
    mock = {
        'player': 0, 'step': 5, 'angular_velocity': 0.008,
        'comet_planet_ids': [], 'planets': [
            [0,  0, 15., 50., 6., 40., 3.],
            [1,  1, 85., 50., 6., 40., 3.],
            [2, -1, 50., 20., 5., 10., 2.],
            [3, -1, 50., 80., 5., 10., 2.],
        ], 'fleets': []
    }
    gs = GameState(mock)
    print(f'my_id={gs.my_id}, my={[p.id for p in gs.my_pl]}, '
          f'enemy={[p.id for p in gs.en_pl]}, neutral={[p.id for p in gs.neu_pl]}')
    for n in [1,10,20,40,80,120]:
        print(f'  fleet_speed({n:3d})={fleet_speed(n)}')
    mvs = agent(mock)
    print(f'v14: {len(mvs)} moves: {mvs}')
    print('OK')
```

## [CODE]
```python
import main
steps = env.run([main.agent, main.agent])
print(f"Player 0: reward={steps[-1][0].reward}, status={steps[-1][0].status}")
print(f"Player 1: reward={steps[-1][1].reward}, status={steps[-1][1].status}")
```
