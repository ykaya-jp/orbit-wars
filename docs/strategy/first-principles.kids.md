# Orbit Wars — First Principles, Explained Simply

> A high-school-friendly tour of the math hiding inside Orbit Wars. Companion to `first-principles.dense.md`. Source line citations at the end of each section.

---

## What's this game, in 30 seconds?

You and 1 (or 3) opponents fight over **planets** that **orbit a sun** in the middle of a 100×100 board. Each player starts with one home planet and 10 ships. You can launch fleets of ships from any planet you own, aimed at any angle. They fly in a straight line at a speed that depends on **how big the fleet is**. They die if they hit the sun. If they hit a planet, combat happens — bigger fleet wins. After 500 turns, whoever has the most ships (counting planets + in-flight) wins.

This document derives the **math** that decides who wins.

---

## Section 1 — Bigger fleets fly faster (logarithm warning)

### What the engine does

The speed of a fleet of $N$ ships is:

$$v(N) = 1 + 5 \cdot \left(\frac{\ln N}{\ln 1000}\right)^{1.5}$$

capped at 6 (when $N \ge 1000$).

### What's a logarithm again?

$\ln 1000 \approx 6.91$. The natural logarithm $\ln N$ is *the power you raise the number $e \approx 2.718$ to, in order to get $N$*. The important thing for us: **$\ln$ grows slowly**. Doubling $N$ adds only $\ln 2 \approx 0.69$ to $\ln N$.

### What this means in numbers

| Fleet size | Speed | Time to cross 50 units |
|---:|---:|---:|
| 1 ship | 1.00 | 50 turns |
| 10 ships | 1.96 | 25.5 turns |
| 100 ships | 3.72 | 13.4 turns |
| 1000 ships | 6.00 | 8.3 turns |
| 5000 ships | 6.00 (capped) | 8.3 turns |

So a 1000-ship fleet only travels **6× faster** than a single ship, even though it's 1000× bigger. After 1000 ships, more ships add **zero** speed.

### Should I split my fleet into two halves?

**No.** A fleet of 100 takes 13.4 turns to cross 50 units. Two fleets of 50 each take 16.0 turns. Because the speed function is concave (gains shrink), one big fleet is *always* faster than two halves going to the same target.

Reasons to split anyway:
- You want to attack **two different planets** at the same time.
- You're decoying or hedging.

### ASCII picture

```
Speed vs fleet size (clamped at 6):

6 |                                  _____ _____   <- ceiling at N=1000
  |                            ___---
4 |                      __---
  |                __---
2 |          __---
  |  __---
1 +--+----+----+----+----+----+----+----+
  1  10   50  100  250  500  1k  2k
```

### Why this matters for orbit-wars

You want to **mass up** before launching. Sending 5 separate fleets of 20 to one target is much slower than sending one fleet of 100. But going past 1000 ships is **wasted speed** — the only benefit is more punch.

**Source:** `orbit_wars.py:577-578`.

---

## Section 2 — Hitting a moving target (lead-shot)

### Imagine throwing a snowball at a friend running

Your friend is running across the field at constant speed. If you aim *directly at them*, your snowball arrives where they *were*, not where they *are*. You have to aim ahead of them. That's called **leading the target**. Orbit Wars is no different — most planets are spinning around the sun, so you have to aim where they'll be when your fleet arrives.

### What's "angular velocity"?

Planets sweep around the sun on a circle. Each turn the planet moves by a small angle, $\omega$ radians. In Orbit Wars $\omega$ is randomly chosen between 0.025 and 0.05 (radians per turn). For comparison, a full circle is $2\pi \approx 6.28$ radians, so a planet takes between $\frac{6.28}{0.05} \approx 126$ and $\frac{6.28}{0.025} \approx 251$ turns to complete an orbit. Episode is 500 turns, so a planet does **2–4 full orbits** during a game.

The planet's position at time $t$ is:

$$x(t) = 50 + r \cos(\theta_0 + \omega\,t), \quad y(t) = 50 + r \sin(\theta_0 + \omega\,t)$$

where $r$ is its distance from the sun and $\theta_0$ is its starting angle.

### The intercept equation

Your fleet flies at speed $v$ in a straight line. To hit the target, you need to find the time $t^*$ when:

> distance from your launch point to the planet's-position-at-time-$t^*$ = $v \times t^*$

This is one equation with one unknown ($t^*$); solve it numerically (bisection works great).

### A worked example

You're at coordinates $(75, 25)$. Your target orbits at radius $r = 30$ around the sun (which is at the center, $(50, 50)$). The planet is at angle 0 right now (so it's at $(80, 50)$). It rotates at $\omega = 0.04$ radians/turn. You're launching 50 ships, which travel at $v = 3.13$ units/turn.

Solving the intercept equation gives:

- intercept time **$t^* = 12.63$ turns**
- intercept location **$(76.25, 64.52)$**
- fire angle (from your home, where to point) **$88.18°$ from the +X axis**

If you naively aimed at the target's *current* position (i.e. $(80, 50)$), you'd aim at **$84.81°$**. The difference (**3.4°**) seems tiny but at distance 40 means you miss by ≈ 2.4 units — bigger than most planet radii. **You will miss without leading.**

### The forbidden cone (don't fly into the sun!)

Your fleet dies if its path crosses within 10 units of the sun. From any launch point, this carves out a "forbidden cone" of headings.

**Picture from $(75, 25)$:**

```
              forbidden
               ___|___
              /   |   \
   (75,25)   /    |   \      <- 33° wide cone you can NEVER fire into
      *->---     SUN     ---<- (50,50)
              \         /
               \_______/
```

The half-angle of the cone is $\arcsin(\frac{10}{d})$ where $d$ is your distance to the sun. From $(75, 25)$, $d = 35.36$, so the cone half-angle is **$16.43°$**, total cone width **$32.86°$**.

### Why this matters for orbit-wars

1. Almost every planet is moving — naive aiming misses most of them.
2. The forbidden cone forbids ~9% of all headings from every Q1 launcher pointing toward the opposite corner. You **must** route around the sun, not through it.

**Sources:** `orbit_wars.py:537-546` (planet motion), `:493-494` (fleet launch), `:607-609` (sun kill check).

---

## Section 3 — Comets

### What's a comet?

Every 100 turns (specifically at game-step 50, 150, 250, 350, 450), the universe spawns 4 comets — one per quadrant of the board, all symmetric to each other. A comet is a temporary planet that **moves** along an elliptical path (not a circle), at a fixed speed of 4 units per turn. Each comet has between 5 and 40 turns of "visible life" — appearing on one side of the board, sweeping past the sun, exiting the other side.

If you successfully attack a comet, **you own it** until it expires. While owned, it produces 1 ship per turn.

### Can I predict comet arrivals before they appear?

The comet's trajectory is determined by a hidden random number generator that uses the **episode seed** as input. The engine **deliberately erases the seed from anything you can see** (`orbit_wars.py:359-363`). So **no**, you cannot pre-simulate future comets.

But — once a comet spawns, **its entire future path is in your observation**. So at the moment it appears, you can compute: when will it be closest to my home? How many ships does it have? Is it worth attacking?

### How tough are comets?

The defending fleet on a fresh comet is `min(rng4)` of `randint(1, 99)` — i.e. the minimum of 4 random integers between 1 and 99. The math gives:

- median ≈ 19 ships
- 90th percentile ≈ 53 ships

So **most comets are weak** — a 25-ship strike force defeats half of them; a 60-ship force defeats nearly all.

### Why this matters for orbit-wars

Comets are **cheap power-ups** if you can intercept them while they're close to home. Keep a 30–60 ship reserve fleet at home; whenever a comet appears in your quadrant, lead-shot it with that reserve. It's a "free" planet (1 ship/turn) for up to 40 turns.

But: don't chase comets across the map — they expire and you'll be wasting fleet on a planet that vanishes. Also, the comet *itself* moves, so you have to lead-shot it like a planet (Section 2).

**Sources:** `orbit_wars.py:27, :191-331` (comet generation), `:438-447` (seed scrub), `:451-456` (comet ship count).

---

## Section 4 — Combat math (the tie-trap)

### How combat resolves

Multiple fleets can arrive at the same planet on the same turn. The engine resolves combat in 3 steps:

1. **Sum ships per attacker** (different fleets from the same player merge).
2. **Largest vs second-largest fight first**: survivor = largest − second-largest, owned by the largest. **Tie = both annihilate** (survivor = 0).
3. **Survivor vs garrison**: the planet's existing ships defend. If survivor > garrison → planet flips, new garrison = survivor − garrison. Otherwise → garrison reduces by survivor.

### Why ties are scary

If two enemies attack your planet with **exactly equal** force, they wipe each other out *before* touching your garrison. That's amazing for you. **But** if you and your ally try to coordinate a 50-50 attack on a defender, you both get wiped out and the defender keeps the planet. Coordinating attacks **with equal forces is suicide**.

### Worked outcomes

Garrison $G = 80$, varied attackers $T$ (top) and $S$ (second):

| $G$ | $T$ | $S$ | What happens | New garrison |
|---:|---:|---:|---|---:|
| 80 | 100 | 0 | flip — top wins | 20 |
| 80 | 100 | 50 | garrison holds (survivor 50 < 80) | 30 |
| 80 | 50 | 50 | tie wipes attackers; garrison untouched | 80 |
| 80 | 60 | 40 | garrison holds (survivor 20) | 60 |
| 80 | 80 | 80 | tie wipes attackers | 80 |
| 80 | 200 | 100 | flip (survivor 100 > 80) | 20 |

### How to flip a planet cheaply

If garrison $G$ is alone (no second attacker), you need $T > G$. Cheapest flip = $G + 1$ ships.

If a rival is also attacking with $S$ ships, you need $T - S > G$, i.e. $T > G + S$. **An ally is your enemy** if you both target the same planet — every ship the ally sends is a ship you must add.

### Why this matters for orbit-wars

1. **Don't pile on a planet your ally is also attacking** — it makes the cost go up, not down. Designate one puncher.
2. **Tie defense is real**: if you can engineer two enemies to send equal forces to your planet, your garrison spends 0.
3. **Cheapest planet steal** = $G + 1$ ships, where $G$ is the garrison. That's your conversion price.

**Sources:** `orbit_wars.py:636-674` (combat resolution), `:659-661` (tie rule).

---

## Section 5 — The opening (4-fold symmetry)

### Where do homes live?

Every game, planets are placed in symmetric groups of 4 (one per quadrant of the board). One group is randomly chosen as the **home group**. In a 2-player game, you get the Q1 (upper-right octant) copy and your opponent gets the Q3 (lower-left octant) copy. In 4-player, all four players each get one copy.

### How far apart are home planets in 2-player?

Home positions are mirror images: if you're at $(p_2, p_3)$, your enemy is at $(100 - p_2, 100 - p_3)$. Distance:

$$d = \sqrt{(100 - 2p_2)^2 + (100 - 2p_3)^2}$$

Sampling 200,000 random episodes (matching the engine's home-placement randomness):

- minimum: 94.78 units
- median: 100.48 units
- mean: 103.28 units
- maximum: 138.10 units

So **expect about 100 units between you and your enemy** — basically the diagonal of the board.

### How long does a max-fleet take to cross?

At $v=6$ (1000+ ships), 100 units = 16.7 turns. With a 500-turn episode, that's **3.3% of the game** to cross the map at top speed. But you start with **10 ships** — you can't even reach the enemy in any meaningful way at game start.

### How big is the action space?

Each turn you can launch 0+ fleets. Each launch needs:
- which of your planets to launch from (you start with 1, may grow to 10)
- what angle (continuous, but discretize to e.g. 36 buckets of 10°)
- how many ships (between 1 and your garrison)

A typical mid-game state has 8 planets owned by you, ~30 ships each. Per turn there are roughly $36 \times 30 = 1080$ launch options per planet. Subsetting which planets to launch from gives $\approx 10^{24}$ raw moves per turn.

That's **way too big** to brute-force. Every reasonable bot prunes.

### Beam search opener (pseudo-code)

```text
state = current observation
beam = [state]   # 1 path
for turn in 1..10:
    candidates = []
    for s in beam:
        for action in pruned_actions(s):
            next_s = simulate_one_tick(s, action)
            candidates.append(next_s)
    beam = top 64 by score(next_s)   # keep best 64
output = best path in beam
```

What's pruned?
- only launch toward actual planets (8 candidate angles, not 36)
- only $\{$ half_garrison, all_garrison $\}$ for ship counts
- skip headings inside the forbidden cone (Section 2)
- skip headings that don't intercept any moving planet within reach

That cuts the per-turn move space to ≈ 72, manageable for a beam.

### Why this matters for orbit-wars

1. The **opening 50 turns** are mostly travel. A fast scout (10 ships, $v=2$) reaches a nearby planet (distance ~30) in 15 turns; a 100-ship punisher reaches it in 8.
2. You **cannot** simply attack the enemy home from your home on turn 1 — you don't have the ships. Build up via **local prod=3+ planets first** (Section 6).
3. Search-based bots (beam search, MCTS) need pruning to be tractable. Hand-crafted heuristics that pick "closest unowned high-prod target" beat naive search at low compute.

**Sources:** `orbit_wars.py:67-188` (planet placement), `:378-391` (home assignment), `orbit_wars.json:80-93` (action shape).

---

## Section 6 — When is a planet worth attacking?

### Planet anatomy

Each planet has:
- **production**: 1 to 5 ships per turn (uniform random)
- **radius**: $1 + \ln(\text{prod})$ — bigger planets = larger targets, easier to hit (prod 5 has radius 2.6)
- **garrison**: defending ships. Phase-1 planets have garrison ~ min of two `randint(5, 99)` (median 36). Phase-2 fill planets have garrison `randint(5, 30)` (mean 17.5).

### How long until I get my ships back?

If you spend $S$ ships to flip a planet, the planet then produces `prod` ships per turn. **Payback time** = $S / \text{prod}$ turns.

### Total break-even table (capture cost + payback) at distance 50

Assume cheapest flip ($S = G + 1$ ships):

| Garrison | Ships sent | Travel time | Payback (prod=1) | Total break-even |
|---:|---:|---:|---:|---:|
| 5 | 6 | 31 turns | 6 turns | 37 turns |
| 30 | 31 | 19 turns | 31 turns | 50 turns |
| 50 | 51 | 16 turns | 51 turns | 67 turns |
| 80 | 81 | 14 turns | 81 turns | 95 turns |

For prod=3 instead:

| Garrison | Ships sent | Travel time | Payback (prod=3) | Total break-even |
|---:|---:|---:|---:|---:|
| 5 | 6 | 31 turns | 2 turns | 33 turns |
| 30 | 31 | 19 turns | 10 turns | 29 turns |
| 50 | 51 | 16 turns | 17 turns | 33 turns |
| 80 | 81 | 14 turns | 27 turns | 41 turns |

For prod=5:

| Garrison | Ships sent | Travel time | Payback (prod=5) | Total break-even |
|---:|---:|---:|---:|---:|
| 5 | 6 | 31 turns | 1.2 turns | 32 turns |
| 30 | 31 | 19 turns | 6.2 turns | 25 turns |
| 50 | 51 | 16 turns | 10.2 turns | 26 turns |
| 80 | 81 | 14 turns | 16.2 turns | 30 turns |

### What the table says

1. **Prod=1 planets at distance** are barely worth it. Prod=1 + heavy garrison breaks even in 95 turns — nearly 20% of the game.
2. **Prod=3+ planets always win** the cost-benefit fight. Even a heavy-garrison prod=5 planet pays back in 30 turns.
3. **Cheap, low-garrison** planets are good as **stepping stones** — capture, then re-launch from there.
4. **Comets**: prod=1, garrison median 19, but they expire in 5–40 turns. Only attack if already in range; they almost never finish their own break-even.

### Why this matters for orbit-wars

Pick targets in this order:
1. Prod=5 with low garrison
2. Prod=4–5 with high garrison if reachable in $\le 10$ turns
3. Prod=3 with low garrison
4. Comets in your quadrant
5. Prod=1–2 only as stepping stones

Avoid prod=1 distant planets unless they're a launch waypoint.

**Sources:** `orbit_wars.py:80-81, :133-134` (production sampling), `:512-514` (production tick), `:667-674` (combat).

---

## Section 7 — Sneaky engine details

### 7.1 Action validation: silently dropped moves

If you submit an invalid move, the engine **silently** ignores it. The list of things that get dropped:

- Move not exactly length 3 → dropped
- Source planet ID doesn't exist → dropped
- Source planet isn't yours → dropped
- Number of ships ≤ 0 → dropped
- Number of ships > garrison → **the entire move is dropped** (you'd think you'd send all you have; you don't, you send nothing)

**Lesson**: always check the planet's current `ships` value and request `min(intent, ships)`.

### 7.2 Multiple launches from the same planet on one turn

You can include the same source planet ID twice in your action list. The engine processes them sequentially, deducting ships after each. So `[[id=5, angle=0, ships=20], [id=5, angle=π, ships=20]]` from a planet with 50 ships fires **40 ships in two directions**, leaving 10. With 30 ships, the second launch is dropped (10 < 20).

### 7.3 Termination tick

The episode ends when `step >= 498` (`orbit_wars.py:686`). Tick 498's actions, production, and combat all execute, *then* scoring happens. So the **last opportunity to launch is around step 497**. Anything launched on the very last tick still counts toward scoring (in-flight ships are scored at line `:707-708`).

### 7.4 Squeezing between planets

`PLANET_CLEARANCE = 7` is **only checked at planet generation time**. Once the game is running, fleets can fly through any gap that doesn't pass within `r_p` of a planet's center. So gaps between planets are at minimum 7 wide, and your fleets can definitely thread between two adjacent planets.

### 7.5 Sun-graze threshold

Sun-kill is `point_to_segment_distance < 10.0` (strict less-than). A path that closes to *exactly* 10.0 survives. With float drift, plan ≥ 10.5 to be safe.

### 7.6 Score draws

If everyone has 0 ships at the end (very rare — you'd all need to be wiped on the same tick), **everyone loses**. Otherwise, all players tied for max ships **all get +1**.

**Sources:** `orbit_wars.py:477-509` (action validation), `:684-715` (termination), `:113, :168` (PLANET_CLEARANCE), `:607-609` (sun kill).

---

## TL;DR cheat sheet

| Question | Answer |
|---|---|
| Best fleet size for speed? | 1000+ (saturates speed at 6) |
| Should I split a fleet? | No, never (for speed reasons) |
| How far is the enemy home? | About 100 units (median) |
| When to lead-shot? | Always for moving (orbiting) targets |
| Cheapest flip cost? | Garrison + 1 ships |
| What ties do? | Wipe out the attackers, save garrison |
| Comet predictability? | Future paths visible the moment they spawn (no earlier) |
| Best ROI prod tier? | 3 or higher |
| Sun-kill rule? | Path within 10 units of (50,50) → fleet dies |

---

## Where to look in the engine

All cited line numbers above point to:

`/home/yusuke_kaya/projects/kaggle/orbit-wars/.venv/lib/python3.11/site-packages/kaggle_environments/envs/orbit_wars/orbit_wars.py`

and:

`/home/yusuke_kaya/projects/kaggle/orbit-wars/.venv/lib/python3.11/site-packages/kaggle_environments/envs/orbit_wars/orbit_wars.json`

Read these alongside the dense doc (`first-principles.dense.md`) for the full proof of each claim.
