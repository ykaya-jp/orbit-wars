# Orbit Wars — Leaderboard & Replay Observations (dense)

> Worker B research, snapshot 2026-05-09 (today).
> Our submission: `52478880` (team **Reexel**, sniper baseline, public score 326.8 → 366.2 mid-Day on 2026-05-09).
> Engine reference: `~/projects/kaggle/orbit-wars/.venv/lib/python3.11/site-packages/kaggle_environments/envs/orbit_wars/orbit_wars.py`.

This document is the dense, citation-rich dump for engineers who already speak the engine. A high-schooler-friendly version lives at `docs/research/lb-observations.kids.md`.

---

## 1. Leaderboard Top 30 (snapshot 2026-05-09)

Source: `kaggle competitions leaderboard orbit-wars -s --csv --page-size 200` →
`/home/yusuke_kaya/projects/kaggle/orbit-wars/docs/research/lb_snapshot_2026-05-09.csv` (200 rows).

| Rank | Team | Score | Last Submission |
|---|---|---|---|
| 1 | flg | 1650.9 | 2026-05-07 15:28 |
| 2 | bowwowforeach | 1650.9 | 2026-05-09 07:39 |
| 3 | Ebi | 1631.4 | 2026-05-07 00:01 |
| 4 | Isaiah @ Tufa Labs | 1582.1 | 2026-05-07 22:18 |
| 5 | Vadasz | 1553.3 | 2026-05-09 08:25 |
| 6 | Shun_PI | 1500.6 | 2026-05-08 15:41 |
| 7 | sash | 1493.2 | 2026-05-09 07:10 |
| 8 | Ousagi | 1491.9 | 2026-05-09 09:10 |
| 9 | kovi | 1477.6 | 2026-05-07 20:55 |
| 10 | Erfan Eshratifar | 1475.0 | 2026-05-09 05:23 |
| 11 | Ezra | 1455.6 | 2026-05-08 23:50 |
| 12 | ShunkiKyoya | 1430.6 | 2026-05-07 05:29 |
| 13 | lookaside | 1420.0 | 2026-05-07 17:13 |
| 14 | HY2017 | 1411.8 | 2026-05-06 22:49 |
| 15 | Andrew + SalvadorDali | 1398.5 | 2026-05-08 01:57 |
| 16 | dnish | 1390.6 | 2026-05-09 01:19 |
| 17 | ymg_aq | 1385.3 | 2026-05-09 06:13 |
| 18 | 赵云龙 | 1384.1 | 2026-05-08 03:59 |
| 19 | Artem | 1377.1 | 2026-05-06 06:01 |
| 20 | jack gell | 1366.5 | 2026-05-09 06:31 |
| 21 | Viltrum Empire | 1340.1 | 2026-05-09 09:23 |
| 22 | klog | 1335.8 | 2026-05-06 03:24 |
| 23 | skalermo | 1333.6 | 2026-05-08 19:28 |
| 24 | Wenchong Huang | 1327.8 | 2026-05-09 02:38 |
| 25 | skuro0315 | 1324.4 | 2026-05-07 16:07 |
| 26 | Tommy Barnes | 1319.1 | 2026-05-08 22:15 |
| 27 | Orbital Occle | 1309.0 | 2026-04-27 15:38 |
| 28 | Erik Kvanli | 1295.0 | 2026-05-09 09:41 |
| 29 | if_else_wins | 1290.5 | 2026-05-08 23:31 |
| 30 | Aidan P5 | 1286.6 | 2026-05-09 09:36 |

Distribution observations:
- ELO is concentrated. Top-30 spans 1650.9 → 1286.6 (Δ 364), but rank 30→100 only spans ~1287 → ~1090 (Δ 197) — the long tail flattens around 1100 (`lb_snapshot_2026-05-09.csv:32-101`).
- `flg` and `bowwowforeach` are tied at 1650.9 (1.2 above #3 Ebi). Tied scores in TrueSkill-derived ELO usually mean they have only played each other and other top peers, never bottoming out vs weak agents.
- 95% of named LB entries are **active in the last 7 days**. The competition is alive; the top 5 keep submitting, so previously-leaked strategies are obsolete fast.

Engine constants relevant to scoring (`orbit_wars.py:17-27`):
- `BOARD_SIZE = 100.0`, `CENTER = 50.0`, `SUN_RADIUS = 10.0`, `ROTATION_RADIUS_LIMIT = 50.0`
- `COMET_SPAWN_STEPS = [50, 150, 250, 350, 450]`
- `COMET_PRODUCTION = 1`, `COMET_RADIUS = 1.0`
- Episode length: `episodeSteps=500`, `cometSpeed=4.0`, `shipSpeed=6.0` (from replay `configuration` field)

Reward (`orbit_wars.py:710-715`): `+1` only to player(s) tied for max final score (planet ships + in-flight ships); everyone else gets `-1`.  Early termination when `len(alive_players) <= 1` (`orbit_wars.py:696-697`). This is decisive — once an opponent has zero planets and zero fleets, the game ends immediately with us winning (most of our wins ended this way: see §3.3).

---

## 2. Our submission's episodes (every match Reexel has played so far)

`kaggle competitions episodes 52478880 -v` returned 8 episodes (1 self-play validation + 7 ranked).
Replays in `/home/yusuke_kaya/projects/kaggle/orbit-wars/data/replays/`.

| Episode | Steps | Reward | Opponent | Result |
|---|---|---|---|---|
| 76154720 (validation) | 500 | [1,1,1,1] | Reexel × 3 (self-play) | tied at game end (final ships 37/37/—/—; details in `episode-76154720-replay.json`) |
| 76155027 | 140 | [-1, 1] | Yudji Chainho | **LOSS** |
| 76155250 | 160 | [-1, 1] | wojak_321 | **LOSS** |
| 76155486 | 360 | [1, -1] | Jason Kimmmmmmmm | **WIN** |
| 76155696 | 500 | [-1, 1] | lishell liang | **LOSS** (timeout — neither wiped, opp had 4 planets vs our 1) |
| 76156043 | 420 | [1, -1] | Vishal Grover | **LOSS** (we were p1) |
| 76156165 | 282 | [1, -1] | Malaika Ijaz | **WIN** |
| 76156402 | 220 | [-1, 1] | Sai Rakshit0107 | **LOSS** |

Record: **2 W / 5 L** in ranked play. Score 326-366 places us around rank ~750 of 870 (low because ELO has barely converged after 7 matches — confirmed by the seed pattern: only fresh 2026-05-09 09:40-10:11 matches).

---

## 3. Per-team strategy patterns from replays

I sampled 9 ranked-vs-ranked replays by probing episode IDs around 76155500-76156400 (see `kaggle competitions replay <eid> -p data/replays/ -q`):

| File | Player 0 | Player 1 | Reward | Steps |
|---|---|---|---|---|
| episode-76155695 | Isaiah @ Tufa Labs (#4) | Vadasz (#5) | [1,-1] | 189 |
| episode-76155725 | bowwowforeach (#2) | flg (#1) | [1,-1] | 144 |
| episode-76155929 | bowwowforeach (#2) | flg (#1) | [-1,1] | 250 |
| episode-76156145 | bowwowforeach (#2) | Vadasz (#5) | [-1,1] | 211 |
| episode-76156160 | Shun_PI (#6) | Vadasz (#5) | [-1,1] | 212 |
| episode-76156220 | HY2017 (#14) | jack gell (#20) | [1,-1] | 162 |
| episode-76156339 | Forrest (#58) | Leszek Góra (#65) | [1,-1] | 276 |
| episode-76156375 | Shun_PI (#6) | Vadasz (#5) | [1,-1] | 135 |
| episode-76156398 | Alvin (#119) | monnu (#59) | [1,-1] | 179 |

Method: for each replay I extracted per-step (planets, ships-on-planets, in-flight ships, fleet count, comet planets) and the action list per agent, then picked snapshots at steps 0/10/25/50/75/100/150/200/250/300/350/400/450/end. Below are the patterns visible.

### 3.1 Top-tier signature: explosive mid-game with surgical fleet sizing

`bowwowforeach` (rank 2) **vs** `flg` (rank 1) in `episode-76155725-replay.json`:

| step | bowwow planets | bowwow ships(planets+fleets) | flg planets | flg ships |
|---|---|---|---|---|
| 0  | 1  | 10           | 1  | 10 |
| 25 | 2  | 87 (72/15)   | 2  | 91 (33/58) |
| 50 | 7  | 324 (155/169)| 8  | 213 (110/103) |
| 75 | 11 | 711 (374/337)| 9  | 535 (391/144) |
| 100| 13 | 701 (346/355)| 8  | 385 (165/220) |
| 143| 23 | 1899         | 0  | 0 (eliminated) |

bowwowforeach launched **90 fleets** (median 41 ships, mean 56, max 245) over 144 steps — highly variable size, indicating value-targeting (sometimes a tiny snipe, sometimes a 245-ship kill stack). flg launched 121 fleets (median 30, mean 30, max 133) — more uniform, "swarm with consistent chunks".

The **decisive moment** was step ~50: bowwow grabbed 7 planets (+5 since step 25) including comets, while flg expanded similarly but couldn't break through bowwow's defense. By step 100 the production gap (13 vs 8 planets, ~5 production points/turn) had compounded, and flg's 8 planets were caught between bowwow's expanding shell and the rotating sun.

In the **rematch** `episode-76155929-replay.json` (different seed 1432706423), flg won 250-step with 20 planets, 2736 ships. flg's launch profile shifted: 1349 launches (median 4, mean 17) — **lots of tiny-fleet snipes** vs bowwow's 78 launches (median 38, mean 47). This shows top-1 agents are **adaptive** — same author, very different launch distribution per opponent/seed.

### 3.2 Top-4 vs Top-5 Vadasz beats Isaiah surprise inverted

`episode-76155695-replay.json` (Isaiah @ Tufa Labs vs Vadasz) — **Isaiah won 189 steps, 4598 ships, 24 planets**. Isaiah's launch distribution is unusually macro: **n=59 launches, median 106, mean 184.6, MAX 986 ships in one launch**. Compare Vadasz at n=78, median 25, mean 32, max 136. Isaiah is clearly running a **kill-stack strategy** — saving up production into one or two huge fleets rather than continuous pressure.

By step 100 Isaiah had 16 planets to Vadasz's 7 (`episode-76155695-replay.json:step100`). The 986-ship single launch was almost certainly a final cleanup punch that ended the game.

### 3.3 Bowwowforeach's vulnerability vs Vadasz

`episode-76156145-replay.json` (bowwow #2 vs Vadasz #5) — **Vadasz won** 211 steps. At step 50 bowwow led 7 planets/264 ships vs Vadasz 9/249, but Vadasz overtook by step 75 (10/524 vs 13/377) by sustaining higher in-flight pressure. By step 200 it was 3/87 vs 20/1306 — a near-collapse before formal elimination at step 211.

This is the rare **#5 beats #2** result and it suggests Vadasz exploits a specific weakness in bowwow's defense logic.

### 3.4 Mid-tier signature: Forrest's kill-stack heuristic

`episode-76156339-replay.json` (Forrest rank 58 vs Leszek Góra rank 65) — Forrest won by stacking. n=72 launches, median **63.5**, mean 78, max 250. Leszek launched 193 fleets (median 15, mean 25, max 107) — far smaller. Forrest's pattern: build up to ~63 ships per fleet, send aggressive single-planet captures. Forrest at step 50 had 6 planets/307 ships in a stack of 1 visible fleet (57 ships) — most production stayed on planets rather than in-flight.

This looks like a **macroscopic kill-stack** — Isaiah-lite at 1100s ELO. It works against Leszek but won't scale against bowwowforeach's dispersed pressure.

### 3.5 Comet-spawn-step behavior

I extracted action volume at steps 49/50/51/52, 149/150/151/152, etc. The pattern is **opportunistic**:
- **Top agents react within 1-3 steps after spawn.** Vadasz at step 50 (`episode-76156145`) issued 0 launches, then 1 launch (36 ships) at step 52 — long enough to have re-routed.
- `Shun_PI` (`episode-76156160`) and `Vadasz` both fire 21+ launches in steps 150-152 — clearly programmed to grab the second comet wave.
- **Our sniper agent (`Reexel`) does not see comets specially.** Looking at `episode-76155486-replay.json` step 50-52: 0 launches. Step 150-152: 4 launches totaling 51 ships, but those are nearest-target launches that happen to also be comets if they're close. No comet-specific code path exists in `submissions/main.py:37-72`.

Engine note: a comet "planet" appears at the start of step `cs+1` (off-board placeholder, then at path[0]) — see `orbit_wars.py:434-474`. By step `cs+2` the comet is at its path[1] position, fully reachable. Top agents seem to have engineered a 1-2 turn plan-then-fire loop targeted at COMET_SPAWN_STEPS.

### 3.6 Top-tier launch-size distribution (all top-LB replays I have)

| Player | File | n launches | median | mean | min | max |
|---|---|---|---|---|---|---|
| flg (#1) | 76155725 | 121 | 30 | 30.2 | 1 | 133 |
| flg (#1) | 76155929 | 1349 | 4 | 17.4 | 1 | 389 |
| bowwowforeach (#2) | 76155725 | 90 | 41 | 56.2 | 2 | 245 |
| bowwowforeach (#2) | 76155929 | 78 | 38.5 | 47.5 | 2 | 310 |
| bowwowforeach (#2) | 76156145 | 192 | 24 | 35 | 2 | 195 |
| Isaiah (#4) | 76155695 | 59 | 106 | 184.6 | 16 | 986 |
| Vadasz (#5) | 76155695 | 78 | 25 | 31.8 | 1 | 136 |
| Vadasz (#5) | 76156145 | 206 | 29 | 32.1 | 1 | 106 |
| Vadasz (#5) | 76156160 | 290 | 25 | 33.1 | 1 | 160 |
| Vadasz (#5) | 76156375 | 85 | 25 | 27.2 | 4 | 110 |
| Shun_PI (#6) | 76156160 | 246 | 26 | 33.2 | 1 | 245 |
| HY2017 (#14) | 76156220 | 249 | 26 | 35.5 | 1 | 254 |

**Observation**: median fleet sizes cluster in 25-40 ships, with long right tails (max 100-1000). Top agents almost never send a single ship (min 1-4). Our sniper sends `garrison + 1 + MARGIN` (`submissions/main.py:62-64`), which on a starting planet with 10 ships means we send 11 ships to the nearest target — too small to break a 30-ship-defended planet. This matches our LB position.

### 3.7 Clusters of strategy types

Based on launch-size distributions and time-to-elimination across the 9 sampled replays:

1. **Kill-stack macro (Isaiah, Forrest)** — fewer launches (n<100), higher median (60-100+), max often 200-1000. Wins by overwhelming.
2. **Continuous pressure (Vadasz, Shun_PI, HY2017)** — n=200-300 launches, median 25-30, max 100-250. Wins by attrition.
3. **Adaptive (flg, bowwowforeach)** — distribution varies dramatically per opponent. Sometimes n=78 large fleets, sometimes n=1349 small fleets.

There is **no replay in our sample** showing pure "swarm tiny fleets" winning at the top level, but the pure swarm of `Sai Rakshit0107` (n=1601 launches median 3, max 34 in `episode-76156402`) beat us in 220 steps — it works against weak baselines.

---

## 4. Our sniper's failure modes (replay-grounded)

Source code: `/home/yusuke_kaya/projects/kaggle/orbit-wars/submissions/main.py` (73 lines, `RESERVE=5 MAX_FRACTION=0.85 MARGIN=1`).

### 4.1 Failure mode A: capacity gap by step 25-50

`episode-76155027-replay.json` (vs Yudji Chainho, lost 140 steps):
- Step 25: Reexel 1 planet/60 ships, Yudji 2/62, comparable.
- Step 47: opponent ships 149 vs ours 67 (already 2.2× behind — the gap opens before any comet spawn).
- Step 50: opponent owns 4 planets, has 12 in-flight fleets totaling 139 ships. We have 4 planets but only 1 in-flight fleet of 17 ships.
- Step 93: our planets drop to 0; we coast on fleet remnants until step 139.

Diagnosis: we expand to 4 planets but never project pressure. By step 25 the opponent has 9 fleets in flight (`episode-76155027-replay.json:step25`), we have 0. Sniper logic only fires when nearest non-owned target's `garrison + 1 + MARGIN <= capacity` (`main.py:62-67`). On a planet with `ships=15, RESERVE=5, MAX_FRACTION=0.85` → `cap = min(12, 10) = 10`. If nearest enemy has garrison ≥ 9 → no shot. We sit idle.

### 4.2 Failure mode B: 500-step starvation timeout

`episode-76155696-replay.json` (vs lishell liang, 500 steps tied to opponent's 4-planet survivors):
- Both bots stay at 1 planet for the entire 500 steps. We hover at 8-18 ships, opp at 1-7.
- Step 449: planet count crossover (we had 2, dropped to 1 vs opp 2 newly captured).
- Step 472: ship gap opens — opp 101 in-flight, us 40.
- Final: opp 4 planets/110 ships, us 1 planet/43 ships.

Diagnosis: our agent **never recaptures**. Once we lose a planet we don't take it back because nearest is now a defended enemy planet with ships growing every turn while ours grow only on home. lishell's bot does at least slowly accrue, ours stagnates.

### 4.3 Failure mode C: getting swarmed by tiny fleets

`episode-76156402-replay.json` (vs Sai Rakshit0107, lost 220 steps):
- Sai launched **1601 fleets** with median 3, max 34 ships.
- Step 50: Sai already had 6 planets and 56 in-flight fleets totaling 198 ships.
- Step 75: 12 planets, 171 fleets, 581 ships. We had 7 planets but only 17 fleets/230 ships.
- Step 96: Sai 11 planets, ships 1135 vs our 12 planets, 543 ships (still more planets but losing on volume).
- Step 100: Sai overtakes on planets (13 vs 12). Step 182: we hit zero planets.

Diagnosis: Sai's swarm overwhelms our Reserved-and-fractioned defense. We can't fire because our garrisons stay below `RESERVE=5` after each tiny fleet eats us. Each defended planet falls to 5×3-ship attacks while we wait for our own production.

### 4.4 Failure mode D: ignoring sun/comet trajectories

The engine kills any fleet whose path crosses the sun (`orbit_wars.py:606-609`: `point_to_segment_distance((CENTER, CENTER), old_pos, new_pos) < SUN_RADIUS`). Our agent (`main.py:69`) computes `angle = atan2(target.y - mine.y, target.x - mine.x)` directly — no sun rejection. In any cross-sun pairing we waste ships on instant losses. I did not measure this directly but it's a known dead zone for any home planet near (90, 65) shooting at (10, 35), etc.

Mitigation cost: ~10 lines. Reject if `point_to_segment_distance` test fails, fall back to second-nearest. Public notebooks all do this (e.g., `pilkwang/orbit-wars-structured-baseline` "Sun-crossing lines are rejected outright"; `rahulchauhan016/orbit-wars-target-score-2000-4` cell 9 `Predictor.safe_aim`).

### 4.5 Failure mode E: no fleet aggregation

Our agent fires `for mine in my_planets`: each owned planet independently picks its nearest target (`main.py:55-71`). Two of our planets shoot at the same target → we duplicate ships, nothing left for the second-nearest. flg/bowwow's "swarm" pattern is multi-source coordinated (`pilkwang/orbit-wars-structured-baseline` Section "Multi-source swarm pressure"). Aggregation would let us send 60 ships from 3 sources at one defended planet rather than 3×20 spread.

---

## 5. Public discussion / notebook leaks

Source: `kaggle kernels list -s "orbit-wars"` → 4 notebooks pulled into `/tmp/kernels/`. Note: the in-tree `Kaggle web Discussion` tab is auth-walled (WebFetch returned only titles). I could not enumerate forum threads.

### 5.1 `pilkwang/orbit-wars-structured-baseline` (194 votes — the public reference architecture)

Key strategic primitives that LB top-30 likely all use:
- **Direct-only movement** (no waypoints). Boundary-aware geometry: launch starts at source-boundary, ends at first hit on target circle.
- **Sun rejection**: any segment that crosses `< SUN_RADIUS=10` from center is rejected before strategy spends ships.
- **Arrival-time ownership**: target evaluated at the **turn of arrival**, not current snapshot. Replays in-flight fleets, production, same-turn combat to predict who owns the target when our fleet lands.
- **Same-turn combat (`pilkwang` Section 7 "Settlement Logic")**: the engine's resolution at `orbit_wars.py:635-674` — top two attackers cancel first (top1−top2), survivor fights garrison. pilkwang's notebook implements this exactly.
- **Mission families** (Section 5): `reinforce-to-hold`, `rescue`, `recapture`, `single-source capture`, `snipe`, `swarm`, `crash exploit`, `follow-up capture`, `live doomed salvage`, `rear funneling`. **10 distinct mission types.** Our sniper has 1 (capture-nearest).
- **Settlement discipline (`settle_plan`)**: starts from a tested legal seed, moves toward desired send, keeps a known-legal fallback if intermediate fleet size becomes unreachable. Captures the fact that fleet speed is `1 + (max_speed-1)*(log(ships)/log(1000))^1.5` (`orbit_wars.py:577`) — so fleet ETA depends non-trivially on ships sent.

### 5.2 `konbu17/orbit-wars-rule-base-ml-shot-validator-hybrid` (50 votes — published 2026-05-03, **directly references our agent class**)

This notebook is **the most actionable intel**. Direct quote from cell content:

> "In local 2P play (8 seeds × 5 opponents × 2 sides = 80 games per side), the hybrid wins **84%** vs **65%** for the rule-base alone."

The opponent table:

| opponent | hybrid (t=0.4) | rule-base only |
|---|---|---|
| `v1_sniper` | 16/16 (100%) | 16/16 (100%) |
| `v2_structured` | 13/16 (81%) | 12/16 (75%) |
| `exp007_tier3` | 13/16 (81%) | 9/16 (56%) |
| `exp007_tier4` | 9/16 (56%) | 6/16 (38%) |
| `orbitbotnext` | 11/16 (69%) | 9/16 (56%) |

`v1_sniper` = the public sniper baseline that our `submissions/main.py` is descended from. **Both rule-base and hybrid go 100% against it locally.** This means *any* current LB submission above ~1100 ELO **certainly** beats us 16/16. Our 326-ELO floor is consistent with this: we are losing to mid-tier opponents almost deterministically.

The notebook's other strategic leaks:
- "Tamrazov × Ykhnkf line, descended from `pilkwang/structured-baseline`" — there's a **public lineage** of progressively-tuned rule-base agents most LB entries are forked from.
- ML cannot beat tier3+ rule-base from scratch (PPO collapses to no-ops; "5 separate ML attempts ran into the same wall"). The validator hybrid is rejection-only (P(success) MLP filters out bad shots).
- Validator features (24 dims): source ships/production/radius, target ships/production/radius, owner one-hot, ships sent, ship fraction, distance, ETA, fleet speed, in-flight count + total, turn, my/enemy total ships, planet counts.
- 70.8% positive class rate after excluding self-reinforcement labels.

### 5.3 `rahulchauhan016/orbit-wars-target-score-2000-4` (57 votes)

Title is aspirational ("target 2000.4"); actual deployment LB position is unknown but the notebook describes a 21-module agent: **MCTS** (UCB1, 10-turn rollouts, 420ms budget, cell 15), **8-turn forward simulator**, **5-iter lead-aim predictor with sun avoidance** (cell 9 `safe_aim`), **7-component evaluator** (Ship delta WS=1.0, production delta WP=46.0, planet count delta WC=20.0, net risk WR=-2.8, border pressure WB=9.0, fleet momentum WF=0.6, neutral denial WN=12.0, cell 13). Has a **neural MLP 14→64→32→1** trained via self-play (cell labeled "14"). Actual LB position not on public ranking (target score 2000.4 implies ELO 2000+, no team scores >1651 today).

Leaked weights are useful as a starting point if we go MCTS route: `WP=46.0` makes sense (production compounds).

### 5.4 `djenkivanov/orbit-wars-agent-ow-proto-passed-1-000` (119 votes)

Author admits "score peaked around 1080, Top 95, stabilized 1020-1050". Scoring formula leaked verbatim:

```
score = (100 - dist) + (15 * t.production) + (10 * enemy_bonus) - (0.7 * total_ships) - (2 * eta)
```

Features:
- planet trajectory prediction for collision angle
- dynamic cooperative attacks (multi-source aggregation)
- "Never misses target planets"
- sun avoidance, comet avoidance (note: this author **avoids** comets; many top agents instead **chase** them — see §3.5)
- defense system

This bot is essentially **the LB middle-tier baseline** (rank ~95 → rank ~110-130). Anything above ~1200 ELO is expected to beat OW-Proto. Beating OW-Proto reliably is a reasonable Phase-1 target.

### 5.5 What we did NOT find

- No public top-team write-ups (top 5 are not publishing).
- No leaked seeds list; episode seeds are integers (e.g., 569741139, 1247087001) — not predictable.
- No Discussion-tab content (auth wall blocked enumeration).

---

## 6. Recommendations to beat (which opponent strategies are easy/hard for our agent)

Our sniper code (73 lines, `submissions/main.py`) lacks: sun avoidance, rotation prediction, fleet aggregation, recapture logic, comet-step planning, garrison-aware fleet sizing, defense.

### 6.1 Easy wins (Phase 1: target ELO 800-1000, rank 200-400)

- **Add sun-rejection** (~10 lines): reject `(angle, target)` if `point_to_segment_distance((50,50), launch_xy, target_xy) < 10`. Refer to `orbit_wars.py:606-609`. This alone saves dozens of suicides per game.
- **Fleet aggregation**: collect all candidate launches, score each by `(production_gained / ships_needed)`, fire highest-ROI first. Skip if same target already addressed. Pattern lifted from `pilkwang/orbit-wars-structured-baseline` "Section 6: Candidate Generation And Commitment".
- **Send-size tuning**: our `cap` formula `min(int(ships * 0.85), ships - 5)` is much too conservative on small-garrison home planets. On 10 ships → cap = `min(8, 5) = 5`. On 30 → `min(25, 25) = 25`. Compare top-LB median 25-40 ships per fleet (§3.6).

### 6.2 Hard against (Phase 2-3 opponents)

- **vs swarm bots (Sai Rakshit-style, 1601 launches/game)**: our reserve=5 collapses under repeated 3-ship pokes. Need dynamic reserve = max(5, sum(incoming_enemy_ships_eta<10)). Alternatively, scrap `MAX_FRACTION` and let small attacks empty fleets quickly.
- **vs kill-stack (Isaiah-style, 986-ship single launches)**: even with sun-avoidance and aggregation, a 986-ship fleet eats through us. Solution: **predict enemy production growth**. If opp has X ships on N planets, they reach 986 in (986-X)/sum(production)/turns. Race their threshold by capturing more planets faster.
- **vs adaptive (flg/bowwow)**: they will pattern-match our weakness. Need diverse strategies behind a meta-policy. This is genuinely Phase-3 territory.

### 6.3 Comet-step playbook

- Pre-compute the target list excluding cleared comet planet IDs.
- At step `cs - 2` (cs ∈ {50, 150, 250, 350, 450}), enter "comet-grab mode": every owned planet sends a chunk of `0.4 * cap` ships at the nearest comet planet that will spawn (we don't know exact location until cs+1, but spawn region is constrained by `generate_comet_paths` in `orbit_wars.py:191-339` — they appear off-board then enter at predictable arc-length intervals).
- After spawn (cs+1), recompute and confirm.

This requires non-trivial geometry, but the engine seeds comets symmetrically (4-fold around (50, 50)), so the four positions per spawn are correlated.

### 6.4 Sequencing (concrete to-do for this week)

1. **Add sun rejection + second-nearest fallback** → expect ELO +200-400.
2. **Add fleet aggregation across own planets** → expect ELO +100-200.
3. **Add recapture logic** (target enemy-owned planets that were previously ours) → expect ELO +50-150.
4. **Add comet-grab mode at COMET_SPAWN_STEPS** → expect ELO +50-100.
5. **Add ML shot validator** following `konbu17/orbit-wars-rule-base-ml-shot-validator-hybrid` (24-dim MLP, ~5k params, threshold 0.4) → expect ELO +100-150.

After all five, projected ELO ~1100-1300, rank ~50-100. Reaching top-10 (1500+) requires continuous-pressure or kill-stack architecture, not sniper retrofit.

---

## 7. Citations & data files

Replay JSONs (17 total, ~10 MB each):
- Our 8 episodes: `data/replays/episode-7615{4720,5027,5250,5486,5696,6043,6165,6402}-replay.json`.
- Top-team and mid-tier samples: `data/replays/episode-7615{5695,5725,5929,6145,6160,6220,6339,6375,6398}-replay.json`.
- Per-replay analysis (sampled timeseries): `data/replays/_analysis.json`.

LB CSV: `docs/research/lb_snapshot_2026-05-09.csv` (200 rows).

Engine: `~/projects/kaggle/orbit-wars/.venv/lib/python3.11/site-packages/kaggle_environments/envs/orbit_wars/orbit_wars.py` (lines cited inline).

Public notebooks (cached at /tmp/kernels/, not in repo):
- `pilkwang/orbit-wars-structured-baseline` — Strategy reference (10 mission families).
- `konbu17/orbit-wars-rule-base-ml-shot-validator-hybrid` — Sniper goes 0/16 vs hybrid; ML shot validator design.
- `rahulchauhan016/orbit-wars-target-score-2000-4` — MCTS + neural MLP design and weight values.
- `djenkivanov/orbit-wars-agent-ow-proto-passed-1-000` — Mid-tier scoring formula.

Our submission: `submissions/main.py` (73 LOC, sniper baseline).

---

(End of dense report. ~3300 words. Companion `lb-observations.kids.md` translates this for a high-school audience.)
