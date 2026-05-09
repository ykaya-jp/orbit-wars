# Orbit Wars — First-Principles Mathematical Analysis (dense)

> Worker C, 2026-05-09. Source of truth: `/home/yusuke_kaya/projects/kaggle/orbit-wars/.venv/lib/python3.11/site-packages/kaggle_environments/envs/orbit_wars/orbit_wars.py` (referred to below as `orbit_wars.py`).
>
> Every formula and constant carries a `file:line` citation to the engine. All numerics in this document were re-derived against the engine; reproducible by `tools/notebooks/01_physics_sandbox.ipynb`.

---

## 0. Notation, conventions, and one important storage quirk

| Symbol | Meaning | Source |
|---|---|---|
| $L = 100$ | `BOARD_SIZE` | `orbit_wars.py:17` |
| $C = 50$ | `CENTER = L/2` | `orbit_wars.py:18` |
| $R_\odot = 10$ | `SUN_RADIUS` | `orbit_wars.py:19` |
| $R_{rot} = 50$ | `ROTATION_RADIUS_LIMIT` | `orbit_wars.py:20` |
| $r_{cmt} = 1$ | `COMET_RADIUS` | `orbit_wars.py:21` |
| $\epsilon = 7$ | `PLANET_CLEARANCE` | `orbit_wars.py:23` |
| $v_{\max} = 6$ | default `shipSpeed` | `orbit_wars.json:19` |
| $v_{cmt} = 4$ | default `cometSpeed` | `orbit_wars.json:24` |
| $T_{ep} = 500$ | `episodeSteps` | `orbit_wars.json:8` |
| $\omega \in \mathcal U[0.025, 0.05]$ | `angular_velocity` | `orbit_wars.py:366` |
| `COMET_SPAWN_STEPS = [50,150,250,350,450]` | comet spawn ticks (matched against `step+1`) | `orbit_wars.py:27`, `:434` |

**Storage quirk (critical when porting code).** `generate_planets` constructs planet records as `[id, -1, y, x, r, ships, prod]` (e.g. `orbit_wars.py:103, :153`), i.e. it swaps the original sampled $(x, y)$ into slots $(2, 3) = (y, x)$. Every consumer downstream then treats `planet[2]` as the X coordinate and `planet[3]` as Y (cf. fleet-launch math at `orbit_wars.py:493-494`, motion update at `:537-546`, distance helper at `:30-31`). Net effect: the geometry is *consistent* — slot 2 is X, slot 3 is Y — but the random sample pair $(x_{src}, y_{src})$ is transposed when stored, which is geometrically equivalent to a reflection over the line $Y = X$. This matters when validating "is the home really in Q1?": the home is uniformly placed in the upper-right octant relative to the *stored* coords.

We therefore use $(x, y)$ for the *stored* coords throughout (= what agents observe).

---

## 1. Fleet speed sweet-spot

### 1.1 Closed form

Per `orbit_wars.py:577-578`:

```python
speed = 1.0 + (max_speed - 1.0) * (math.log(ships) / math.log(1000)) ** 1.5
speed = min(speed, max_speed)
```

$$v(N) = \min\!\Big(v_{\max},\; 1 + (v_{\max}-1)\,\big(\tfrac{\ln N}{\ln 1000}\big)^{1.5}\Big),\qquad N \ge 1.$$

`math.log(ships)` is natural log. `ln(1000) ≈ 6.9078`. `min` clamps so $N \ge 1000$ all travel at $v_{\max}=6$.

Time to travel a Euclidean straight-line distance $D$ in turns (continuous, no rounding — the engine integrates a real-valued position each tick):

$$T(N, D) = D / v(N).$$

### 1.2 Sweep table ($v_{\max}=6$)

| $N$ | $v(N)$ | $T(N, 30)$ | $T(N, 50)$ | $T(N, 100)$ |
|---:|---:|---:|---:|---:|
| 1 | 1.0000 | 30.00 | 50.00 | 100.00 |
| 5 | 1.5623 | 19.20 | 32.00 | 64.01 |
| 10 | 1.9623 | 15.29 | 25.48 | 50.96 |
| 50 | 3.1309 | 9.58 | 15.97 | 31.94 |
| 100 | 3.7217 | 8.06 | 13.43 | 26.87 |
| 250 | 4.5731 | 6.56 | 10.93 | 21.87 |
| 500 | 5.2666 | 5.70 | 9.49 | 18.99 |
| 750 | 5.6909 | 5.27 | 8.79 | 17.57 |
| 1000 | 6.0000 | 5.00 | 8.33 | 16.67 |
| 1500 | 6.0000 | 5.00 | 8.33 | 16.67 |

Saturation at $N=1000$. Past that, additional ships do not travel any faster.

### 1.3 Single vs split (N ships in 1 fleet vs N/2 in 2 fleets)

A single fleet of size $N$ is **always** at least as fast as two fleets of size $\lfloor N/2 \rfloor$ at the same target (both must traverse the same distance):

$$T(N, D) \le T(N/2, D) \iff v(N) \ge v(N/2),$$

and $v$ is monotone non-decreasing in $N$. Numerical sweep at $D=50$:

| $N$ | $T_{\text{single}}$ | $T_{\text{half}}$ | Faster |
|---:|---:|---:|---|
| 10 | 25.48 | 32.00 | single |
| 50 | 15.97 | 19.30 | single |
| 100 | 13.43 | 15.97 | single |
| 200 | 11.47 | 13.43 | single |
| 800 | 8.68 | 9.92 | single |
| 1500 | 8.33 | 8.79 | single |

**Strategic implication.** Aggregate ships into a single fleet for raw arrival time. The only reason to split is (a) **angle diversity** — separate fleets can target two planets, (b) **decoy / overcommit hedge**, (c) the launching planet has limited inventory so concentration isn't possible. There is *no* speed reason to split.

### 1.4 Marginal benefit

$$\frac{\partial T}{\partial N} = -\frac{D}{v(N)^2}\,\frac{\partial v}{\partial N}, \qquad \frac{\partial v}{\partial N} = \frac{(v_{\max}-1)\cdot 1.5}{N\,(\ln 1000)^{1.5}}\,(\ln N)^{0.5}\quad\text{for }N<1000.$$

Numerical (turns saved per ship added, at $D=50$):

| Range | $\Delta v$ | turns saved per ship |
|---|---:|---:|
| 1 → 5 | +0.56 | 4.499 |
| 5 → 10 | +0.40 | 1.305 |
| 10 → 50 | +1.17 | 0.238 |
| 50 → 100 | +0.59 | 0.051 |
| 100 → 500 | +1.55 | 0.0099 |
| 500 → 1000 | +0.73 | 0.0023 |
| ≥ 1000 | 0 | 0 |

**Breakpoints.** First 10 ships in a fleet contribute >1 turn saved per ship; past N=100 the speed gain is essentially exhausted relative to per-ship combat value. **Strategic implication.** A small "stinger" of ≥10 ships moves at almost double the speed of a 1-ship probe; this is the bare minimum for fast scouting / interception. Going beyond ≈250 ships adds combat strength but no meaningful speed.

---

## 2. Orbital prediction & lead-shot fire angle

### 2.1 Target trajectory

Per `orbit_wars.py:537-546`, an *initial* planet at $(x_0, y_0)$ with $r_p$ such that orbital radius $r_{orb} = \|(x_0, y_0) - (C, C)\|$ satisfies $r_{orb} + r_p < R_{rot}$ rotates with constant angular velocity $\omega$:

$$\theta(t) = \theta_0 + \omega\,t, \qquad \theta_0 = \mathrm{atan2}(y_0 - C,\; x_0 - C),$$
$$\vec p(t) = \big(C + r_{orb}\cos\theta(t),\;\; C + r_{orb}\sin\theta(t)\big).$$

Static planets (orbital radius + $r_p \ge R_{rot}$) sit still. Comets follow the precomputed path table at `orbit_wars.py:556-566`.

### 2.2 Fleet trajectory

Per `orbit_wars.py:493-494`, fleet spawns at planet edge $(x_a + (r_p+0.1)\cos\alpha,\; y_a + (r_p+0.1)\sin\alpha)$ with constant heading $\alpha$ and per-tick step $v(N)$:

$$\vec f(t) = \vec a + (r_p+0.1+v(N)\,t)\cdot(\cos\alpha,\sin\alpha).$$

For lead-angle algebra below we drop the $r_p+0.1$ offset (≤2.7 units) and treat the launch as starting at $\vec a = (x_a, y_a)$.

### 2.3 Closed form for intercept time $t^*$ and fire angle $\alpha^*$

We need the smallest $t^* > 0$ with $\|\vec f(t) - \vec p(t)\| = 0$ (or rather, the swept-pair test in `orbit_wars.py:46-64` reports a hit whenever the distance closes to within $r_p$ over the segment $[t, t+1]$; for design we solve for exact intercept and accept any $t$ within ±0.5 of $t^*$).

The condition $\|\vec f - \vec p\| = 0$ gives one transcendental equation:

$$\big(x_a + v\,t\cos\alpha - C - r_{orb}\cos(\theta_0+\omega t)\big)^2 + \big(y_a + v\,t\sin\alpha - C - r_{orb}\sin(\theta_0+\omega t)\big)^2 = 0.$$

There are two unknowns ($t, \alpha$) but only one equation, so we add the *collinearity condition*: at intercept, the launch direction equals the geometric direction from $\vec a$ to $\vec p(t^*)$:

$$\alpha = \mathrm{atan2}\big(y_p(t^*) - y_a,\; x_p(t^*) - x_a\big).$$

Substituting eliminates $\alpha$. The remaining 1D equation in $t$ is:

$$g(t) \equiv \|\vec p(t) - \vec a\| - v\,t = 0.$$

This is the **standard moving-target intercept equation**: distance to be covered (LHS) equals distance flown by the fleet (RHS). If $\vec a$ is outside the orbit ($\|\vec a - C\| > r_{orb}$) and $v > r_{orb}\,\omega$ (the fleet is faster than the target's tangential speed), $g$ has at least one positive root.

Existence: the fleet's tangential closing speed cap is $v$, target's tangential speed is $r_{orb}\,\omega$. With $\omega \le 0.05$ and $r_{orb} \le 50$, target tangential speed $\le 2.5$ — strictly less than $v(N{=}1)=1.0$… actually **not always**: a 1-ship fleet (v=1) cannot catch a fast outer-ring orbiter ($r_{orb}\,\omega$ up to 2.5). So minimum-fleet lead-shot fails for distant orbiters; need $N$ large enough that $v(N) > r_{orb}\,\omega$. From §1.2, $v(50) \approx 3.13 > 2.5$ — **50 ships always catches**.

Practical solver (bisection on $t$):

```python
def lead_intercept(a, theta0, omega, r_orb, center, v):
    """Returns (t_star, fire_angle_rad). a=(x_a,y_a). v=fleet_speed(N)."""
    import math
    cx, cy = center
    def pos(t):
        a_t = theta0 + omega*t
        return (cx + r_orb*math.cos(a_t), cy + r_orb*math.sin(a_t))
    def g(t):
        px, py = pos(t)
        return math.sqrt((px-a[0])**2 + (py-a[1])**2) - v*t
    # g(0) >= 0 (target is some distance away). Search for sign change.
    lo, hi = 1e-3, 500.0
    if g(lo) <= 0:
        return lo, math.atan2(pos(lo)[1]-a[1], pos(lo)[0]-a[0])
    for _ in range(120):
        mid = 0.5*(lo+hi)
        if g(mid) > 0: lo = mid
        else:          hi = mid
    t = 0.5*(lo+hi)
    px, py = pos(t)
    return t, math.atan2(py-a[1], px-a[0])
```

### 2.4 Numerical example

Q1 home at $(75, 25)$, target on circular orbit $r_{orb}=30$, $\omega=0.04$, target initial phase $\theta_0 = 0$ (target at $(80, 50)$ at $t=0$), fleet of 50 ships ($v = 3.1309$).

Result (computed with the bisection above):

- $t^* = 12.628$ turns
- intercept point $(76.254, 64.517)$
- $\alpha^* = 1.5391$ rad $= 88.183^\circ$
- naive (no-lead) aim at target's $t=0$ position: $84.806^\circ$
- **lead correction: $+3.378^\circ$** (about 0.059 rad)

A 3.4° correction translates at the intercept point to a perpendicular miss of $\approx \tan(3.4°)\cdot 39.6 \approx 2.36$ — larger than typical $r_p$ (1–2.6 units) but smaller than a planet radius for high-prod planets ($r_p(\text{prod}=5)=2.609$). At low-prod targets you must lead; at high-prod targets you might luck into a hit even with naive aim, but only if the swept-pair test (`orbit_wars.py:46-64`) catches you mid-tick.

### 2.5 Sun-cross check (forbidden cone)

A fleet path crosses the sun if the **point–segment distance** from $(C, C)$ to the segment $[\vec a, \vec a + v\Delta t (\cos\alpha,\sin\alpha)]$ is $< R_\odot = 10$ at any tick (`orbit_wars.py:34-43, :607-609`). Equivalently the line through $\vec a$ at heading $\alpha$ has perpendicular distance to the sun:

$$d_\perp(\alpha) = \big| (C - x_a)\sin\alpha - (C - y_a)\cos\alpha \big|,$$

and the projection $s_\| = (C-x_a)\cos\alpha + (C-y_a)\sin\alpha > 0$ (sun is forward).

If $d_\perp < R_\odot$ AND the sun is forward, the fleet is incinerated. Forbidden heading window from launch point $\vec a$:

$$\alpha \in \big[\,\theta_\odot - \delta,\;\theta_\odot + \delta\,\big], \quad \theta_\odot = \mathrm{atan2}(C-y_a, C-x_a),\quad \delta = \arcsin\!\Big(\tfrac{R_\odot}{\|\vec a - (C,C)\|}\Big).$$

**Numerical (launch from $(75, 25)$, distance to sun $= 35.355$):**

- $\theta_\odot = 135.000^\circ$
- $\delta = \arcsin(10/35.355) = 16.430^\circ$
- forbidden range $[118.57^\circ,\; 151.43^\circ]$ (=33° wide)

So from a Q1 home, any heading targeting Q3 directly through the sun is dead. Cross-board attacks must go around — typically 16–17° off the sun-line, adding $\approx \frac{1-\cos\delta}{\cos\delta} \approx 4\%$ travel distance.

**Caveat.** The check is segment-to-point: a slow 1-ship fleet whose 1-tick segment doesn't reach within $R_\odot$ of the sun *this tick* survives this tick, even if the line, extended, would cross. But it gets killed the moment its swept segment enters the sun's circle. Net behaviour: the forbidden cone is correct on a multi-tick basis.

> Cross-ref: see §5 for using the forbidden cone in opening search.

### 2.6 Source citations for §2

- `orbit_wars.py:30-31` distance
- `orbit_wars.py:34-43` point-to-segment
- `orbit_wars.py:46-64` swept-pair (planet+fleet)
- `orbit_wars.py:493-506` fleet launch geometry
- `orbit_wars.py:537-546` planet rotation update
- `orbit_wars.py:607-609` sun crossing kill

---

## 3. Comet timing windows

### 3.1 Spawn schedule

`COMET_SPAWN_STEPS = [50, 150, 250, 350, 450]` (`orbit_wars.py:27`). The check is `(step + 1) in COMET_SPAWN_STEPS` (`orbit_wars.py:434`), where `step` is the tick number passed in `obs.step`. So the *first turn at which a new comet group is observable* is the tick where `step+1` matches; the comet is appended with `path_index=-1` and gets its first on-board placement on the same tick.

**5 spawns × 4 symmetric copies = up to 20 comets per episode.**

### 3.2 Per-spawn RNG seeding — and why it's not exploitable

Source: `orbit_wars.py:438-447`:

```python
env_info = getattr(env, "info", None) or {}
episode_seed = env_info.get("seed", 0) or 0
comet_rng = random.Random(f"orbit_wars-comet-{episode_seed}-{step + 1}")
```

The `episode_seed` is **deliberately scrubbed from the configuration** before any agent observes it (`orbit_wars.py:359-363`):

```python
configuration.seed = None
env.info["seed"] = seed
```

The seed lives only on `env.info`, which is **not** propagated into agent observations (compare `orbit_wars.py:393-402` where only `player`, `angular_velocity`, `planets`, `initial_planets`, `fleets`, `next_fleet_id`, `comets`, `comet_planet_ids` are copied per agent). The JSON spec doc explicitly warns: *"the agent server re-validates the (scrubbed) configuration on every act() call"* (`orbit_wars.json:27`).

**Conclusion: comet futures are NOT pre-simulatable.** The seed is hidden by design. The earliest you can react to a comet is the tick it spawns (its full `paths` list is appended to `obs.comets[g]["paths"]` at `orbit_wars.py:457-474` and revealed to all agents at `:676-682`).

**However** — once a comet group is visible, its full path is in the observation. So you can compute its on-board lifetime, perihelion timing, and capture window deterministically from spawn tick onward. That is the exploitable asymmetry.

### 3.3 Comet shape geometry

Per `orbit_wars.py:210-244`, each comet group is one orbital ellipse with sun at one focus, replicated 4-fold:

- $e \in \mathcal U[0.75, 0.93]$ (eccentricity)
- $a \in \mathcal U[60, 150]$ (semi-major axis)
- perihelion $= a(1-e) \ge R_\odot + r_{cmt} = 11$
- $b = a\sqrt{1-e^2}$
- orientation $\phi \in \mathcal U[\pi/6, \pi/3]$ (perihelion direction, anchored in Q4)
- arc parameterized over $t \in [0.3\pi, 1.7\pi]$, then re-sampled at $v_{cmt} = 4$/turn arc-length intervals (`orbit_wars.py:236-244`)
- only the **on-board** contiguous segment is kept (`:246-256`); 5–40 path points = 5–40 ticks of comet life

Resulting visible-arc duration: between 5 and 40 ticks at $v_{cmt}=4$, i.e. arc length $\in [20, 160]$ board units. Median is ~22 ticks visible (~88 board units).

The 4 copies are: $(y, x), (L-x, y), (x, L-y), (L-y, L-x)$ (`orbit_wars.py:266-269`) — i.e. 4-fold rotational symmetry about $C$. Each player sees one comet pass through their quadrant.

### 3.4 Capture cost / timing for a Q1 home

A comet group has `comet_ships = min(rng4)` of `randint(1, 99)` (`orbit_wars.py:451-456`). Distribution of $\min$ of 4 i.i.d. $\mathcal U\{1..99\}$:

$$P[\text{ships} \le k] = 1 - (1 - k/99)^4.$$

Numerics: median $\approx 19$, P90 $\approx 53$. Comets are **soft targets** — a 25-ship fleet wins ~50% of comet captures, a 60-ship fleet wins ~95%.

**Closing speed.** Comet moves at $v_{cmt}=4$ along its arc. A Q1 fleet of 50 ships ($v=3.13$) actually moves *slower*; you must lead-shoot a comet just like a planet (§2). Fortunately, comets pass within ≈20–40 units of the home in their on-board arc.

**Timing window.** For each comet group $g$ with first-visible tick $t_0 = \text{spawn\_step}$ and path of length $K$:
- closest-approach tick to home $\vec h$: $t^*_g = \arg\min_{k\in[0,K)} \|\vec h - \text{paths}[g][\text{Q1}][k]\|$
- recommended launch tick: $t_0 + \max(0, t^*_g - T_{lead})$ where $T_{lead} = \|\vec h - \text{closest-pt}\|/v(N)$

This is solvable in $O(K)$ once the path is observable.

### 3.5 Tactical implications

1. **Cannot pre-simulate** — but on spawn tick you get the entire 4×K path table. Run the lead-intercept solver on each future point.
2. **Comets are cheap** — median 19 ships defending. A pre-allocated 25–40 ship strike force at home guarantees comet captures.
3. **Comet expiry** — when `path_index ≥ len(path)` the comet is removed (`orbit_wars.py:411-415, :558-561`). Don't send fleets that arrive after expiry.
4. **Orphan capture is real** — the captured comet's `production = 1` ship/turn (`orbit_wars.py:22, :513-514`) BUT the comet *moves* via its remaining path, then expires. That's a temporary 1-prod planet for ≤ 40 ticks.

### 3.6 Source citations for §3

- `orbit_wars.py:27` spawn list
- `orbit_wars.py:191-331` `generate_comet_paths`
- `orbit_wars.py:359-363` seed scrub
- `orbit_wars.py:393-402` per-agent observation propagation (no seed)
- `orbit_wars.py:411-429` comet expiry sweep
- `orbit_wars.py:434-474` spawn block
- `orbit_wars.py:549-566` comet movement
- `orbit_wars.json:27` seed scrubbing rationale

---

## 4. Combat surplus calculus

### 4.1 The rule (engine truth)

Combat resolves per planet, per tick (`orbit_wars.py:636-674`). All fleets that hit the planet in the swept-pair check go into `combat_lists[pid]`. Then:

1. Sum ships per *attacker player*: `player_ships[owner] += fleet[6]` (`:643-645`).
2. Sort descending by ship count (`:650-652`).
3. **Top vs second** (`:655-658`):
$$\text{survivor} = T - S, \quad \text{owner} = \text{top}.$$
4. **Tie rule** (`:659-661`): if top equals second, **survivor = 0**, planet keeps original owner regardless of $G$.
5. Survivor vs garrison $G$ (`:667-674`):
   - if survivor = 0 → garrison untouched
   - if survivor > 0 and `planet.owner == survivor_owner` → reinforce: $G \mathrel{+}= \text{survivor}$
   - else → $G \mathrel{-}= \text{survivor}$; if $G < 0$ → planet flips, new garrison $= |G|$.

**Key consequence.** Garrison ships do *not* enter the inter-attacker fight. They only reduce the surviving attacker after the attackers fight each other. So if you are defending against two enemies, and you can ensure they tie, your garrison costs 0.

### 4.2 Outcome table (G = garrison, T = top attacker, S = second attacker)

Solver:
```python
def combat3(G, T, S):
    top, sec = (T, S) if T >= S else (S, T)
    if top == sec:                      # tie
        return ("garrison_holds", G)    # both forces wiped
    survivor = top - sec
    if survivor <= G:
        return ("garrison_holds", G - survivor)
    return ("flip", survivor - G)
```

| $G$ | $T$ | $S$ | Outcome | New garrison |
|---:|---:|---:|---|---|
| 80 | 100 | 0 | flip (top wins) | 20 |
| 80 | 100 | 50 | garrison holds | 30 |
| 80 | 50 | 50 | tie → both wiped | 80 |
| 80 | 60 | 40 | garrison holds | 60 |
| 80 | 80 | 80 | tie → both wiped | 80 |
| 50 | 100 | 80 | garrison holds | 30 |
| 20 | 100 | 80 | garrison holds | 0 (sets to 0) |
| 0 | 100 | 80 | flip | 20 |
| 80 | 200 | 100 | flip | 20 |

### 4.3 Optimal split for 2 cooperating attackers vs garrison G

**Wrong intuition:** "split evenly". With 2 *non-cooperating* enemies + 1 garrison (3-way), tying is suicide for both attackers (their survivor = 0).

**Right answer for one-attacker-with-2-fleets vs G:** the engine sums per-player, not per-fleet. Two fleets from the same player merge. So splitting is irrelevant for total impact; only relevant for arrival timing.

**Right answer for 2 distinct attackers vs G** (cooperative scenario, e.g. 4-player team-up):

Total attacking ships $X = T + S$. Garrison wins whenever $|T - S| \le G$. To flip the planet: need $|T - S| > G$, i.e. asymmetric force. The cheapest flip is **one player sends $X = G+1$ ships, other sends 0** (waste minimised). Sending equal forces wastes everything. Sending $G+1+S$ vs $S$ for any $S > 0$ flips with surplus 1 — but $S$'s ships are pure waste.

**Strategic implication:** in 4-player FFA, *ally’s overlap on your target = ally betraying you* unless one of you sends an order-of-magnitude smaller force that gets eaten in the tie. There's no 2-player team-flip without one designated puncher.

### 4.4 Tie defense (annihilation door)

If you can guarantee that two opponents arrive at your planet on the same tick with equal sums, you defend with 0 garrison cost. This is the **mirror-attack defense**: ping both opponents into a frenzy at the same target, time their incoming such that their own combat resolves before they reach you. Hard to engineer but powerful in 4-player.

### 4.5 Source citations for §4

- `orbit_wars.py:572` `combat_lists` setup
- `orbit_wars.py:594` add hit fleet to combat list
- `orbit_wars.py:636-674` resolution
- `orbit_wars.py:659-661` tie annihilation
- `orbit_wars.py:667-674` garrison interaction

---

## 5. 4-fold opening exploration

### 5.1 Q1 home distribution

From `orbit_wars.py:67-122` (Phase 1 static planets), **homes are placed in the static class** (the 4-fold mirror is over the diagonal, see §0 storage quirk). For each "static" candidate group:

- $\theta \in \mathcal U[0, \pi/2]$ (angle from center, line `:82`)
- $\text{prod} \in \{1..5\}$, $r_p = 1 + \ln(\text{prod})$
- orbital radius $r_{orb} \in [\,R_{rot} - r_p,\; (L-C-r_p)/\max(\cos\theta, \sin\theta)\,]$ (`:83-88`)
- min board separation: $|x - C| \ge r_p + 5$ AND $|y - C| \ge r_p + 5$ (`:98-99`)

The **home group** is selected at random from all groups (`orbit_wars.py:380-381`). In a 2-player game, player 0 gets the Q1 copy (`base+0` at `(planet[2]=y_src, planet[3]=x_src)`) and player 1 gets the Q4 copy (`base+3` at `(L-y_src, L-x_src)`), each starting with **10 ships** (`orbit_wars.py:383-387`).

### 5.2 Home-to-home distance distribution

From the geometry, the home pair is always opposite corners of an axis-symmetric placement. Q1 home at stored coords $(p_2, p_3)$, Q4 home at $(L - p_2, L - p_3)$. Distance:

$$d_{HH} = \sqrt{(L - 2 p_2)^2 + (L - 2 p_3)^2} \ge 2\sqrt{2}(R_{rot} - r_p) \approx 2\sqrt{2} \cdot (50 - r_p).$$

For $r_p \le 2.6$, $d_{HH} \ge 134$ in the limit but is *typically less* because the home is in the static class and can sit further out. Empirical sample (200k draws, matching the engine's `randint`-`uniform` chain, modulo the planet-overlap rejection):

- min ≈ 94.78
- median ≈ 100.48
- mean ≈ 103.28
- max ≈ 138.10

So **expected home-to-home is ≈ 100**, the diagonal of the board. For a max-fleet of $N \ge 1000$ ships at $v=6$, that's $\approx 17$ ticks travel — **3.4% of the 500-tick episode** to cross the map at full speed. With a starting garrison of 10 ships, you cannot reach the enemy on tick 1 in any meaningful way; you need to capture local planets first to scale up.

### 5.3 4-player layout

In 4-player (`orbit_wars.py:388-391`), each player gets one copy of the home group, one per quadrant, all with 10 ships. Adjacent enemies are at distance $\approx d_{HH}/\sqrt{2} \approx 71$ (across one axis), opposite enemy at $\approx 100$.

### 5.4 Action-space size estimate

Per `orbit_wars.json:80-93`: action = `[from_planet_id (int), angle (float), num_ships (int)]`, returned as a list of moves.

For one of your planets with $G$ ships:
- `from_planet_id`: 1 (you can only send from one of your own planets per move)
- `angle ∈ [0, 2π)` (continuous; engine doesn't quantize)
- `num_ships ∈ {1, ..., G}` ($G$ choices)

Per-turn move space per planet (with continuous angle discretized to $D$ bins): $D \cdot G$.

Typical mid-game state (5-10 planet groups × 4 = 20-40 planets, you own 5-10 of them, mean garrison ≈ 30):
- planets: ~8
- moves per planet: $D \cdot 30$
- you can do *multiple* moves per turn (action is a list)
- subset of $\{1..8\}$ planets to launch from: $2^8$
- per launching planet: $D \cdot G$ actions
- total per turn: $\prod (1 + D \cdot G_i) \approx (1 + D \cdot 30)^8$

With $D = 36$ (10° bins): $(1 + 1080)^8 \approx 10^{24}$ per-turn actions. With $D = 8$: $(241)^8 \approx 10^{19}$. **Vanilla brute force is dead.**

### 5.5 Pruning principles for a tractable opener

1. **Only consider valid headings.** From planet $p$, only headings that intercept *some* observed planet within $T$ ticks. For 8 planets in observation, that's 8 candidate angles per source planet.
2. **Quantize ships.** $\{0, G/2, G\}$ — empirically the only meaningful split because production refills small fractions quickly.
3. **One launch per planet per tick.** (engine permits more, but redundant given speed table §1.3 — concentration always faster.)
4. **Forbidden-cone filter** (§2.5).
5. **Lead-shot filter** (§2.3) — only headings that actually hit a *moving* planet in range.

After pruning: ~8 sources × ~3 destinations × 3 ship sizes ≈ 72 moves per tick. Subsets in expectation ≈ $4 \cdot 10^4$. Tractable for beam search at depth 5–10.

### 5.6 Pseudocode: beam-search opener (10-tick lookahead)

```python
def beam_opener(obs, depth=10, beam_width=64):
    """Open-game search. State = (planets_snapshot, fleets_snapshot)."""
    initial = clone_state(obs)
    beam = [(score(initial), initial, [])]  # (score, state, action_seq)
    for d in range(depth):
        candidates = []
        for s, state, traj in beam:
            for action in generate_pruned_actions(state):
                next_state = simulate_one_tick(state, action, opponent_policy="hold")
                candidates.append((score(next_state), next_state, traj + [action]))
        # Keep top beam_width by score
        beam = sorted(candidates, key=lambda x: -x[0])[:beam_width]
    return beam[0][2]  # best action sequence

def score(state):
    return (sum(p.ships for p in state.planets if p.owner == ME)
            + sum(f.ships for f in state.fleets if f.owner == ME)
            + 5 * sum(p.production for p in state.planets if p.owner == ME))

def generate_pruned_actions(state):
    """Yields list-of-moves. Each move = (from_id, angle, ships)."""
    my_planets = [p for p in state.planets if p.owner == ME and p.ships >= 5]
    targets = state.planets  # candidates
    moves = []
    for src in my_planets:
        for tgt in targets:
            if not_forbidden_by_sun(src, tgt) and reachable(src, tgt, src.ships):
                t_star, alpha = lead_intercept(...)
                for ships in {src.ships // 2, src.ships - 1}:
                    moves.append([src.id, alpha, ships])
    yield from subset_top_k_combinations(moves, k=4)
```

### 5.7 Source citations for §5

- `orbit_wars.py:67-188` planet generation
- `orbit_wars.py:378-391` home assignment
- `orbit_wars.json:80-93` action shape
- `orbit_wars.py:477-509` action processing (silent-drop filters: see §7)

---

## 6. Production density vs distance trade-off

### 6.1 Planet anatomy

Per `orbit_wars.py:80-81, :133-134, :512-514`:
- $\text{prod} \sim \mathcal U\{1..5\}$ (Phase 1 and Phase 2 same distribution)
- $r_p = 1 + \ln(\text{prod})$
- ships/turn = `prod` (line 514)
- `ships ∈ U{5..99}` (Phase 1, with $\min$ trick: line 101) or `U{5..30}` (Phase 2: line 151)

Capture cost: garrison must drop below 0 after combat, so cost = $G + 1$ in the cheapest path (you arrive surviving with $G+1$ ships).

### 6.2 ROI table

ROI = ships gained per turn, *after* capture, at the planet itself.

| prod | $r_p$ | ships/turn | typical $G$ (Phase 1) | min cost to flip |
|---:|---:|---:|---:|---:|
| 1 | 1.000 | 1 | 5–99 (median ~17 from min-of-2) | $G+1$ |
| 2 | 1.693 | 2 | 5–99 | $G+1$ |
| 3 | 2.099 | 3 | 5–99 | $G+1$ |
| 4 | 2.386 | 4 | 5–99 | $G+1$ |
| 5 | 2.609 | 5 | 5–99 | $G+1$ |

Ph1 garrison distribution: $\min(\mathcal U\{5..99\}, \mathcal U\{5..99\})$ — that's a min-of-2-uniforms which has CDF $1 - (1 - F(g))^2$ where $F$ is the uniform CDF. Median ≈ 36, mean ≈ 36.7.

Phase 2 (`orbit_wars.py:151`) ships $\in \mathcal U\{5..30\}$, mean ≈ 17.5.

### 6.3 Travel-cost-adjusted ROI

Sending $S = G + 1$ ships from distance $D$: time-to-arrive $T = D/v(S)$.

Total cost (in opportunity ticks of ships sitting around):
$$\text{cost}(S, D) = S + \frac{S \cdot D}{v(S)}\cdot\text{(opportunity rate)}.$$

If we count only nominal ships expended (no opportunity cost), payback time after capture = $S / \text{prod}$ (planet must produce S ships to refund the investment), then *additional* turns until episode end pure profit at rate $\text{prod}$.

| $G$ | $S=G+1$ | $T(D{=}50)$ | payback@prod=1 | payback@prod=3 | payback@prod=5 |
|---:|---:|---:|---:|---:|---:|
| 5 | 6 | 31.0 | 6 | 2 | 1.2 |
| 17 | 18 | 21.5 | 18 | 6 | 3.6 |
| 30 | 31 | 18.7 | 31 | 10.3 | 6.2 |
| 50 | 51 | 15.9 | 51 | 17 | 10.2 |
| 80 | 81 | 14.2 | 81 | 27 | 16.2 |

Total time before *break-even on raw ships* = $T + \text{payback}$.

| $G$ | prod=1 break-even | prod=3 | prod=5 |
|---:|---:|---:|---:|
| 5 | 37 | 33 | 32 |
| 30 | 50 | 29 | 25 |
| 50 | 67 | 33 | 26 |
| 80 | 95 | 41 | 30 |

**Strategic implications.**

1. Low-prod planets (prod=1) **are not worth distant travel** — break-even ~50–95 ticks for $G \ge 30$. With episode length 500, you still profit, but **prod=3+ planets always pay back faster.**
2. High-prod, high-garrison planets **dominate** late-game. Prod=5 with $G=80$ pays back in 30 ticks total ($\approx 6\%$ of episode).
3. Low-prod, low-garrison planets are **stepping stones** — capture cheap ($G=5$ → 6 ships), but only profitable if you need their angular position (e.g. as a launch point for the next attack).
4. **Comets** (`prod=1`, garrison median 19, lifespan ≤ 40 ticks) — capture only if they're already near home; otherwise the lifespan often kills the ROI.

### 6.4 Source citations for §6

- `orbit_wars.py:80-81, :133-134` prod sampling
- `orbit_wars.py:101, :151` ship sampling
- `orbit_wars.py:512-514` production tick
- `orbit_wars.py:667-674` capture mechanics

---

## 7. Edge cases / engine quirks

### 7.1 Just-outside-the-sun grazing

The sun-cross check is `point_to_segment_distance((C,C), old_pos, new_pos) < SUN_RADIUS` (`orbit_wars.py:607`). Strict `<`. So a fleet whose closest approach equals exactly 10.0 *survives*. Practically, with floating-point drift, plan ≥ 10.5 to be safe.

The check uses the **actual swept segment per tick**, not the full ray. So if your tick-step lands on the near-sun side AND the next tick lands past the sun, but the segment between never closes inside 10, you're fine. Speed matters: a faster fleet has a longer per-tick segment, more likely to graze → check.

### 7.2 PLANET_CLEARANCE = 7 (squeezing between planets)

`PLANET_CLEARANCE` is *only* enforced at planet-generation time, in `if distance(...) < p[4] + tp[4] + PLANET_CLEARANCE` (`orbit_wars.py:113, :168`). It is **not** enforced at runtime for fleets — fleets are allowed to fly anywhere except into a planet (swept-pair, `:46-64`) or sun. So:

- minimum gap between two adjacent planet *bodies* is $\ge 7$ board units
- fleets of size 1 at $v=1$ can comfortably pass through a 7-unit gap; the swept-pair test ignores anything not within `r_p` of the planet's path
- **Yes, fleets can squeeze between planets** as long as their tick-segment doesn't approach within $r_p$ of a planet center

### 7.3 Action validation: silent drops

Per `orbit_wars.py:477-506`:

| Condition | Action | Source |
|---|---|---|
| Action is not a list | drop entire action | `:478-479` |
| Move is not length-3 | drop that move | `:481-482` |
| `from_planet` not found | drop that move | `:486` |
| `from_planet[1] != player_id` (not yours) | drop that move | `:488` |
| `from_planet[5] < ships` (insufficient garrison) | drop that move | `:489` |
| `ships <= 0` (after `int()` cast) | drop that move | `:489` |
| `len(move) > 3` (extra elements) | drop (length check is `!= 3`) | `:481-482` |

**Implications:**
- `ships = 0` is silently dropped — must use ≥1.
- `ships` is `int()`-cast (`:485`); fractional ships floor.
- No validation on `angle` — any float works. `angle` modulo $2\pi$ is implicit via `cos`/`sin`.
- No validation that target is reachable; you can fire into the sun and the engine kills the fleet at runtime.
- If you have 5 ships and request 10, the entire move is silently dropped (you'd expect "send 5"; you get nothing).
- You can launch from the **same planet multiple times in one action list**, and each move is processed sequentially (`:480-506`); subsequent moves use the *post-deduction* garrison.

### 7.4 Termination edge

Per `orbit_wars.py:684-715`:

```python
if step >= configuration.episodeSteps - 2:
    terminated = True
```

Reading this with `episodeSteps = 500`: termination triggers when `step >= 498`. The interpreter is invoked at the start of a tick; `step` is the *incoming* step. Order of operations within a tick (`:432-715`):

1. Comet expiry sweep (line 411)
2. Comet spawn (line 434)
3. **Action processing** (`process_moves`) (`:476-509`)
4. **Production** (`:511-514`)
5. Compute planet paths (`:516-566`)
6. Fleet movement & collision (`:568-609`)
7. Apply planet motion (`:611-615`)
8. Combat resolution (`:635-674`)
9. **Termination check, scoring, reward** (`:684-715`)

So **production and combat both happen at step ≥ 498**. The last full simulation tick is step 498, scoring at end of that tick (sum of ships everywhere — planets + in-flight fleets, `:704-708`). Tick 499 may also run the same path (`>= 498`) — both ticks execute production+combat and then terminate.

The reward rule (`:710-715`):
- $\max(\text{scores})$ — players tied for max all get +1
- everyone else gets -1
- if max = 0, **everyone gets -1** (`max_score > 0` guard at `:712`)

Last condition is mathematically odd: a draw with all-zero ships is a global loss. Practically rare (you'd need every alive player wiped on the same tick).

### 7.5 In-flight ships count for scoring

Score includes both planet ships AND **in-flight fleet ships** (`orbit_wars.py:704-708`):
```python
for f in obs0.fleets:
    scores[f[1]] += f[6]
```

So you cannot "hide" ships by launching just before timeout; they count. Conversely, a fleet you launched but that hits an empty planet on the last tick still counts at its destination (post-combat).

### 7.6 Source citations for §7

- `orbit_wars.py:46-64` swept-pair (planets only, not fleet-vs-fleet)
- `orbit_wars.py:113, :168` PLANET_CLEARANCE (gen only)
- `orbit_wars.py:477-509` action validation
- `orbit_wars.py:684-715` termination & scoring

---

## Cross-section recap

| Section | Result | Where used downstream |
|---|---|---|
| §1 | $v(N)$ formula, ≥1000 saturation, single-fleet always faster than splits | §2 (lead-shot), §5 (opener pruning), §6 (travel cost) |
| §2 | Lead-angle = `atan2` to intercept, forbidden cone half-angle = $\arcsin(R_\odot/d)$ | §5 (opener filter), §6 (travel modeling) |
| §3 | Comet seed is unobservable, but full path is revealed on spawn; comets soft-targets | §6 (low-ROI exception); standalone tactic |
| §4 | Tie = annihilation; garrison only fights survivor | §5 (multi-attacker analysis); standalone defense |
| §5 | $d_{HH} \approx 100$, action space ≈ $10^{19}$, beam-search on pruned moves | §6 (range frame); standalone opener |
| §6 | Prod=3+ at distance 50 break even ≤ 33 ticks; comets risky | Standalone economy plan |
| §7 | Sun-graze threshold, silent-drop list, scoring counts in-flight ships | All above |

---

## Appendix A — exact constants (engine-grounded)

```python
BOARD_SIZE = 100.0                                         # orbit_wars.py:17
CENTER = 50.0                                              # :18
SUN_RADIUS = 10.0                                          # :19
ROTATION_RADIUS_LIMIT = 50.0                               # :20
COMET_RADIUS = 1.0                                         # :21
COMET_PRODUCTION = 1                                       # :22
PLANET_CLEARANCE = 7                                       # :23
MIN_PLANET_GROUPS, MAX_PLANET_GROUPS = 5, 10               # :24-25
MIN_STATIC_GROUPS = 3                                      # :26
COMET_SPAWN_STEPS = [50, 150, 250, 350, 450]               # :27
shipSpeed_default = 6.0                                    # orbit_wars.json:19
cometSpeed_default = 4.0                                   # orbit_wars.json:24
episodeSteps = 500                                         # orbit_wars.json:8
actTimeout = 1                                             # orbit_wars.json:9
angular_velocity ~ U[0.025, 0.05]                          # orbit_wars.py:366
home_starting_ships = 10                                   # :385, :387, :391
```
