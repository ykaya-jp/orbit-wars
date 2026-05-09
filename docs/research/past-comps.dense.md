# Past Kaggle Simulation/Agent Competitions — Dense Synthesis for orbit-wars

> Track A research deliverable. Compiled 2026-05-09 for the orbit-wars competition (Google-sponsored, $50k, kaggle_environments, +1/-1 binary reward, 2370 teams, deadline 2026-06-23).
> Every claim is cited with `file:line` (local) or full URL (web). Most-recent comps weighted higher; Halite II flagged as the **structurally most similar** prior comp.

---

## TL;DR matrix

| Comp | Year | n teams | Winner technique | Compute | Structural match to orbit-wars |
|---|---|---|---|---|---|
| Lux AI S3 | 2024-25 | ~600 | Deep RL (PPO + SE-ResNet) | RTX 3090, ~8 days, 300M frames | High (24x24, partial-obs, sap action ≈ orbit-wars combat) |
| Lux AI S2 | 2023 | 646 | **Pure heuristic Python** (despite NeurIPS-provided 1B IL frames) | None | Medium |
| Kore 2022 | 2022 | ~1000 | **Imitation learning** (autoregressive Transformer on 200M tuples) | 2x A100 80GB | High (fleet, +1/-1) |
| Halite II | 2017-18 | 6000 | **Heuristic** (state machine + simulation refinement) | Single CPU thread | **Maximum** — 2D continuous fleet melee |
| Halite IV | 2020 | 1143 | Heuristic + NN collision aid (1st) | Modest | Medium-High |
| Halite III | 2018-19 | ~4000 | Heuristic (Dijkstra-per-ship) | Modest | Medium |
| Lux AI S1 | 2021 | 1178 | Deep RL (IMPALA+UPGO+TD(λ)) | Personal PC dual-GPU | Medium |
| Hungry Geese | 2021 | 875 | DRL self-play (HandyRL) + late MCTS bolt-on | Distributed | Low |
| microRTS 2023 | 2023 | n/a (IEEE) | BC bootstrap → PPO finetune | 70-142 GPU-days | Medium |

**Headline cross-cut:** until 2023 the Kaggle simulation leaderboard was almost always won by **carefully tuned heuristics** even when ML alternatives existed. The exceptions are (a) when explicit IL data was provided (Kore 2022, Lux S2 NeurIPS track) and (b) Lux AI S3 in 2024 where partial observability and meta-learning across a best-of-5 series broke heuristic dominance and forced DRL. orbit-wars is **fully observable and symmetric** with a 2-month window — historically that is the heuristic regime, but the field has matured and a hybrid (heuristic core + small NN opponent predictor or BC policy) is now the modal winning recipe.

---

## 1. Lux AI Season 3 — NeurIPS 2024 (the most recent and most informative)

- Comp page: https://www.kaggle.com/competitions/lux-ai-season-3
- Paper (organizers, Tao & Kumar): https://openreview.net/forum?id=7t8kWYbOcj
- Engine repo: https://github.com/Lux-AI-Challenge/Lux-Design-S3

**1st place — Frog Parade (Isaiah Pressman):**

- Writeup: https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md
- Repo: https://github.com/IsaiahPressman/kaggle-lux-2024
- Technique: PPO with clipping. Per the writeup ([source](https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md)): *"Deep reinforcement learning aims to answer this question by parameterizing a policy using a deep neural network."*
- Architecture: 8-block 3×3 SE-ResNet, hidden dim 256, ~10M parameters; dual actor heads (10 movement actions + spatial sap-target head); 10-frame history stack; ~80 global + ~100 spatial features.
- Compute: AMD Ryzen 9950X 16c, 64GB RAM, RTX 3090 + RTX 2070 Super. **110k env steps/s** thanks to a custom Rust simulator (TDD-validated against the official Python engine). Train throughput **430 steps/s**, total **~300M game steps over ~8 days**.

Non-obvious tricks (Lux S3 had partial observability and randomized rule parameters per match → these are the deduction tricks that mattered):

1. **Hidden parameter inference** — energy field configuration, asteroid/nebula movement, and point-tile locations are *deduced* from observation deltas rather than learned end-to-end. Quote: *"all of this initially-hidden information can be deduced by carefully observing how the observations change."*
2. **Symmetry-reflected feature engineering** — exploit the diagonal symmetry of the map. Test-time augmentation averages predictions over diagonal reflection + 180° rotation.
3. **Custom Rust simulator** — the bottleneck for any RL approach is env throughput; a Rust reimplementation gave ~10× speedup. Tested via TDD against the official Python engine.
4. **Selective action masking** — though the author flags this as possibly *over*-restrictive in retrospect.
5. **Energy field caching from precomputed configurations** — there are only finitely many possible energy fields; precompute them all and look up rather than recompute.

**Transfer to orbit-wars (~150 words):**
- orbit-wars is **fully observable**, so the inference tricks do not apply, BUT the symmetry trick is directly portable: orbit-wars has 4-fold rotational symmetry around (50, 50) (engine source `~/projects/kaggle/orbit-wars/.venv/.../orbit_wars.py`). Use this for both data augmentation (4× training data per match) and test-time prediction averaging.
- The custom-Rust-simulator pattern is the highest-leverage win: env throughput dictates RL-training feasibility. A Rust port of the orbit_wars combat resolver alone unlocks 8 days × 110k steps/s = ~75B frames at home-PC scale.
- The SE-ResNet + dual actor head (movement + spatial-target) maps 1:1 onto orbit-wars (fleet move + attack target).
- 10-frame history is critical because comet spawns at step 50/150/250/350/450 are predictable but only via temporal context.

---

## 2. Lux AI Season 2 — NeurIPS 2023 (the heuristic-still-wins lesson)

- Comp page: https://www.kaggle.com/competitions/lux-ai-season-2
- 1st place writeup (ry-andy): https://www.kaggle.com/competitions/lux-ai-season-2/writeups/ry-andy-1st-place-solution
- Repo: https://github.com/ryandy/Lux-S2-public

**Technique:** pure-Python heuristic. Final placement: **1st of 646 teams** ([repo README](https://github.com/ryandy/Lux-S2-public)).

This is the canonical counter-example. The NeurIPS organizers explicitly provided **>1B frames of S1 imitation-learning data** to enable IL/RL approaches, yet the Kaggle Kaggle bot leaderboard was won by a hand-coded heuristic. The IL/RL track was scored separately (a NeurIPS-sponsored side track), but the open leaderboard — the one that matters for prizes — was heuristic.

**Why heuristic won:** on the Kaggle leaderboard (as opposed to NeurIPS-track-2 IL evaluation), the bot has to play in the 60-second submission environment with strict per-step time budgets, and discrete grids let domain experts encode "obvious" rules (factory placement to maximize lichen, ice mining, defended power transfer) faster than RL can converge.

**Transfer to orbit-wars:** same conditions apply. orbit-wars is a 2-month comp with 2370 teams; a strong heuristic baseline (resource collection + planet capture + symmetry exploitation) is the right Phase-1 deliverable before any ML training kicks in. Plan the heuristic baseline ahead of the RL training pipeline.

---

## 3. Kore 2022 — the canonical imitation-learning-on-Kaggle lesson

- Comp page: https://www.kaggle.com/competitions/kore-2022
- 1st place writeup: https://www.kaggle.com/competitions/kore-2022/discussion/340035
- 1st place repo: https://github.com/khanhvu207/kore2022

**Technique:** autoregressive Transformer trained on **200M (obs, plan)-tuples scraped from the top-5 leaderboard submissions**, treating ship-plan generation as machine-translation seq2seq.

**Architecture details (from the writeup):**
- Spatial encoder: 12-layer ResNet with GroupNorm between residual blocks, processing 18-channel ship/cargo tensors
- Scalar encoder: MLP over (timestep, team score, team resources, etc.)
- Ship-plan encoder: 256-d character embeddings + positional embeddings, summed bag-of-words style (avoids the cost of a second Transformer)
- Decoder: autoregressive char-level Transformer ("N 10 W 5" = "go North 10 steps then West 5"); a [CLS] token feeds an action-type classifier head

**Training:** 2× A100 80GB, batch 64, 20 epochs, AdamW lr=4e-3 with cosine schedule (5% warmup), gradient clipping 0.5, weight decay 0.01. Heavy regularization: **60% random pixel dropout** on the spatial input.

**Non-obvious tricks:**

1. **Tokenize ship plans as character sequences** — turning a multi-step movement plan into "N 10 W 5 SE 3" makes the problem isomorphic to NMT, where decades of literature are available.
2. **Bag-of-words plan embedding** for *other* ships — avoids quadratic Transformer cost for state representation.
3. **60% spatial pixel dropout** — extreme augmentation that prevents memorization of specific board configurations.
4. **Top-5 IL targets, not just top-1** — captures stylistic diversity, prevents collapse onto one player's quirks.
5. **Action-type [CLS] head** — predicts type (LAUNCH/SPAWN/etc.) BEFORE generating plan tokens, so the autoregressive decoder gets a structural prior.

**Transfer to orbit-wars (~180 words):**
- orbit-wars actions are simpler (per-fleet movement target + ship allocation), but the same seq2seq framing applies: encode each fleet's "plan" as a token sequence (target_planet, num_ships, attack_or_dock), train a small Transformer on scraped top-N replays.
- The 60% spatial dropout is directly transferable: orbit-wars has heavy spatial structure (planets, fleets, comets) and the regularization prevents board-memorization.
- The 200M-tuple scale is achievable: each Kaggle replay yields ~1000 step×fleet tuples; scraping 200K replays from top players (via Kaggle's `meta-kaggle` BigQuery export) reaches that order. This is the *easiest* path to a competitive bot if one of the top players publishes a strong heuristic early.
- Critical caveat: IL only works once strong demonstrators exist on the leaderboard. Phase the strategy: heuristic Phase-1 → scrape top replays → BC Phase-2.

---

## 4. Halite II — STRUCTURALLY MOST SIMILAR

This is the prior comp closest to orbit-wars' game shape: 2D continuous space, planets to dock at, fleet vs fleet melee with overlapping attack ranges. **Read this section first if implementing orbit-wars.**

- Comp page: https://www.kaggle.com/competitions/halite-ii (Two Sigma announce: https://www.twosigma.com/articles/halite-ii-concludes-winners-announced/)
- Top-3 review: https://lakesidethinks.com/post/2018/10/halite2-strategy.html

### 1st — reCurs3 (Ubisoft Montreal, Assassin's Creed dev)

- Writeup: https://recursive.cc/blog/halite-ii-post-mortem.html (note: the blog occasionally refuses connections; see the Medium mirror by James Jones https://medium.com/aescru/halite-ii-strategies-of-a-top-player-88127b3b49e2)

State-based AI with two-pass decision:

1. **Strategic pass** assigns roles: colonize / defend / attack
2. **Tactical pass** runs hill-climbing on positions, simulating against **19 different enemy response patterns** to pick the conservative best move

Non-obvious tricks (these are the gold):

1. **Fight-or-flight via signed neighbor count** — for each ship, sum (#nearby enemies − #nearby allies) within radius. Negative → attack; positive → flee. *Quote (paraphrased from review):* this is computed cheaply by maintaining per-ship `nearby_friendly` and `nearby_enemy` vectors.
2. **Coulomb-style 180° flee vector** — when a ship decides to flee, the run direction is `−mean(nearby_enemy_positions)`, "similar to a negatively-charged particle flying away from other negative charges" (https://medium.com/aescru/halite-ii-strategies-of-a-top-player-88127b3b49e2).
3. **Planet priority queue** — for every planet within distance < 75, score = 3 × dock-spots, scaled inversely by distance. Sends *all* available ships to the chosen planet (even when only 2 dock spots are open) to absorb rush damage.
4. **Ship-set pruning by interaction radius** — only consider ships within `2*MAX_SPEED + WEAPON_RADIUS + 2*SHIP_RADIUS` of each ship. This prune turns O(n²) per-tick combat into nearly O(n).
5. **Trajectory collision math** — using minimum-distance-as-function-of-time (basic physics), abort moves where two ships' min-distance < 0.5. The author had to *modify the stock API* because collision-avoidance wasn't included by default.
6. **Anti-rush** — simple distance threshold: don't dock or undock if any enemy ship is within X distance.

### 2nd — FakePsyho (OpenAI, Polish puzzle champion)

- Repo: https://github.com/FakePsyho/halite2

**Stateless evaluation-function design.** Instead of state machine, score *every* (ship, action) combination, then global greedy assign.

Key tricks:

1. **Cache evaluations** — recalc only when underlying state changes. This is what made the eval-everything approach tractable on a 1-second per-turn budget.
2. **Limit ships-per-target** — *"limiting how many ships can follow each enemy ship is a really cheap way of forcing your units to spread among different goals"* ([repo README](https://github.com/FakePsyho/halite2)).
3. **Border-proximity penalty** — discourages edge movement unless retreating.
4. **Health-based positioning** — lower-health ships get pushed away from enemies in the eval.
5. **Bait via attack-range buffer** — retreating ships move outside `(ship_attack + max_speed) = 13` units to force enemies to commit before re-engaging.
6. **Anti-rush via dock distance** — same as reCurs3.

### 3rd — shummie (actuary, Allstate Chicago)

- Postmortem: https://shummie.github.io/Halite-2-Shummie/

Behavior-driven, with **role-specialized navigation functions** (dogfight / retreat / defense each have their own move-evaluator).

Unique tricks:

1. **Distractor role** — dedicated ships that harass docked enemy ships, splitting defenses.
2. **Non-aggression pact (NAP)** — coordinated with another player using *hidden in-game signals* to avoid attacking each other in 4-player matches, guaranteeing top-2 placement when paired (controversial; later patched out by Two Sigma).
3. **Desertion meta** — send one ship to the corner; *"command all ships to run away"* to outlive opponents and steal 2nd place. Now widely known.
4. **Outnumbered detection** — retreat back to friendly ships to *create* numerical superiority before re-engaging.

### Transfer to orbit-wars (~200 words)

Halite II is the **template** for orbit-wars Phase-1 heuristic:

| Halite II concept | orbit-wars analog |
|---|---|
| Fight-or-flight via neighbor count | Compare own fleet size vs. enemy fleet at each interaction; use orbit-wars combat formula `largest vs second-surplus annihilation` to compute expected outcome |
| Coulomb 180° flee | Move fleet directly away from mean of all stronger enemy fleets |
| Planet priority queue (3 pts/dock × inv-distance) | Planet capture priority by garrison-yield × inverse-distance, weighted by `PLANET_CLEARANCE=7` |
| 19-pattern enemy response simulation | Enumerate top-K likely enemy moves, pick max-min-value action |
| Ship-set pruning by interaction radius | Use `1.0 + (max_speed-1.0) * (log(ships)/log(1000))^1.5` to compute per-fleet effective radius |
| Anti-rush distance threshold | Don't undock fleets if enemy fleet within reach × 1.5 |
| Distractor role | Send small splinter fleet to harass opponent's largest planet |
| 4-fold symmetry exploit | orbit-wars has explicit 4-fold symmetry around (50, 50); use it for both heuristic move-mirroring and ML data aug |

The reCurs3 two-pass (strategic role assignment → tactical hill-climbing with simulated enemy responses) maps almost identically onto orbit-wars. Implement it first, then layer ML on top per Section 11 below.

---

## 5. Halite IV — 2020 (4-player grid; hybrid winners)

- Comp page: https://www.kaggle.com/c/halite

### 1st — ttvand (Tom Van de Wiele)

- Repo: https://github.com/ttvand/Halite (separate `Rule agents/` and `Deep Learning Agents/` folders)
- Discussion: https://www.kaggle.com/c/halite/discussion/183312

Hybrid: rule-based core with neural-network components for opponent move prediction. The repo's split folder structure is the visible hint — production submission combined heuristic strategy with a NN that estimates opponent action distributions for collision avoidance.

### 4th — 0Zeta

- Repo: https://github.com/0Zeta/HaliteIV-Bot
- Quote: *"our approach utilizes no fancy ML techniques or otherwise disproportionate complex algorithms. Instead, our bot is a 100% rule-based bot with lots of parameters."*

Tricks worth stealing:

1. **Halite "plantations"** — place shipyards in triangular formations around halite-rich areas, exploit the 2% regen rate. Equivalent for orbit-wars: orbital cluster formations around symmetric planets.
2. **Linear sum assignment for simultaneous ship moves** — assign all ships their action *simultaneously* via Hungarian algorithm. Avoids the temporal coupling of sequential pathfinding.
3. **10 ship roles** — MINING / RETURNING / HUNTING / GUARDING / DEFENDING / etc.; recompute role each turn statelessly to prevent stale plans.
4. **Hunting-score boost for trapped enemies** — *"boost the hunting scores of targets that can move safely to fewer than two cells"*.
5. **Two guards per shipyard** — patrol radius increases dominance and deters intruders.
6. **Accept 1:1 trades around shipyards** — defensive trade-off because shipyard loss is existential.

Lessons: *"Lack of pathfinding caused ship congestion. Over-parameterization created brittleness. No replay analysis tools hampered debugging. Stateless design caused excessive ship type switching. A critical bug introduced day before submission severely damaged final performance."* All five are warnings to heed.

### Rank 8 — Convex (KhaVo, Dan, Gilles, Robga, Tung) — IL approach worth noting

- Writeup: https://khavo.ai/2020/09/15/halite/

Imitation learning by **semantic segmentation**: each ship's immediate action is predicted as a per-pixel label by a UNet-style model trained on top-replay data. Heuristic overrides on key policies (base spawning, ship converting, base protecting).

### Transfer to orbit-wars

- The "linear sum assignment for simultaneous moves" pattern handles the orbit-wars problem of "many fleets choose moves the same turn".
- The role-recompute-every-turn discipline prevents stale plans when comets spawn at step 50/150/250/350/450.
- Convex's semantic-segmentation IL is a good Phase-2 ML pattern: each grid cell predicts the right movement direction (cheaper than per-fleet autoregressive Transformer).

---

## 6. Halite III — 2018-2019 (Dijkstra and threshold-based collisions)

- Comp page: https://halite.io/

### 1st — teccles

- Repo: https://github.com/teccles-halite/halite3-bot

Each ship runs **Dijkstra over the board** to compute halite-burned and turn-cost for every square; chooses target maximizing halite-gain-per-turn over (travel + mining + return). Collision threshold uses ownership (proximity-defined) × halite × ship-value. Dropoff scoring = `halite_density / (cost − square_halite)`.

### 6th — TheDuck314

- Repo: https://github.com/TheDuck314/halite2018

Hybrid heuristic-with-NN. Tricks:

1. **Mining score** = (dist + mining_time + return_dist) with **1.75× distance penalty**, with target requiring 3× more halite than current before abandoning.
2. **Purposes per ship**: Mine / Return / Flee / Ram / Stuck — each routes through purpose-specific scoring.
3. **Traffic control with miner↔returner swap** to prevent dropoff congestion.
4. **C++ rewrite from Python** eliminated bottleneck (echo of Lux S3 winner's Rust simulator).
5. **NN trained offline predicts opponent move probabilities**; ships move only if NN estimates **≥98% safety** for adjacent squares.

### Transfer to orbit-wars

- The 98%-safety threshold for NN-predicted opponent moves is directly transferable to orbit-wars combat: train a small CNN on past matches to predict opponent fleet moves; only commit a move if expected outcome ≥ threshold.
- The C++/Rust rewrite is the universal lesson — env throughput is *the* bottleneck.

---

## 7. Lux AI Season 1 — 2021 (DRL won)

- Writeup: https://www.kaggle.com/competitions/lux-ai-2021/writeups/toad-brigade-toad-brigade-s-approach-deep-reinforc

**1st — Toad Brigade.** Pure RL with self-play. Initially explored heuristic, but switched to DRL when the RL agent surpassed it within the first month — significant data point.

Architecture:

- Fully convolutional ResNet with squeeze-excitation
- 24 residual blocks, 128-channel 5×5 convolutions
- ~20M parameters
- **No batch normalization** in residual blocks (subtle but stable)
- Three actor heads (workers / carts / city-tiles) + one critic

Training: **IMPALA + UPGO + TD(λ)** loss combination, NOT vanilla PPO. Compute: single 8c/16t personal PC with dual GPU, overnight training across the comp.

Tricks:

1. **GridNet action space** — one network output per grid cell. Single net controls all units → emergent cooperation (vs. per-unit nets).
2. **Reward shaping for first 20M steps**, then sparse +1/-1 only — curriculum.
3. **Progressive net size** 8→16→24 blocks with teacher-distillation KL loss.
4. **Day-night cycle and game-phase dims** as explicit input — enabled mid-game strategy shifts.
5. **TTA: 180° rotation averaging** at inference.

Transfer: GridNet maps to orbit-wars planet-grid; reward-shaping curriculum applies (shape on planets-captured for first N steps, then switch to sparse +1/-1); TTA via 4-fold symmetry. Critically, **IMPALA+UPGO+TD(λ) is *not* PPO** — when implementing DRL for orbit-wars, PPO is the default but the Toad Brigade evidence suggests UPGO-augmented IMPALA is more robust on long-horizon multi-unit games.

---

## 8. Hungry Geese — 2021 (DRL self-play with late MCTS)

- Comp: https://www.kaggle.com/competitions/hungry-geese
- Japanese retrospective (excellent): https://zenn.dev/ktechb/articles/e2394bc27358c4
- 5th place writeup: https://www.kaggle.com/competitions/hungry-geese/writeups/takedarts-5th-place-solution-geesezero

**1st — HandyRL team (DeNA).** Distributed off-policy DRL framework: https://github.com/DeNA/HandyRL

Tricks (across top-5):

1. **Continuous body gradient** (1.0 head → 0.0 tail) instead of binary mask — temporal-position info via the channel value.
2. **Step-count input channel** — explicit late-game switching.
3. **Mixed past-version opponents** during training, not pure self-play — prevents local-optimum collapse.
4. **Late-stage AlphaZero-style MCTS bolt-on**, modified for simultaneous-action and stochastic-food. Quote from retrospective: *"During the final month, the author implemented Monte Carlo Tree Search (MCTS) inspired by AlphaZero, modifying it for simultaneous multi-agent action and stochastic food spawning by limiting food pattern possibilities."*

Transfer to orbit-wars: comet spawns are stochastic but seeded by `random.Random(f"orbit_wars-comet-{seed}-{step+1}")` — so their possibility set is enumerable, exactly like Hungry Geese food. MCTS over comet-spawn-and-action joint distributions becomes tractable.

---

## 9. microRTS 2023 — IL bootstrap → PPO finetune

- Paper: https://arxiv.org/html/2402.08112v1
- 1st — RAISocketAI; first DRL agent to win IEEE microRTS

Compute: **70 GPU-days** (A10/A6000/A100) for the competition submission; **142 GPU-days total** for the BC+PPO follow-up paper.

Architecture:

- DoubleCone(4,6,4) — residual blocks with SE + adaptive pooling for variable map size
- squnet — aggressive 3-level downscaling for large maps under 100ms inference

Tricks:

1. **BC loss scaled by unit count** — *"allowed the learning rate to be significantly increased"*; addresses gradient-scale issues with variable unit counts per turn.
2. **3-stage curriculum**: 16×16 (300M frames from random init) → 32×32 (transfer-finetune) → 64×64 (hardest).
3. **Mixed reward schedule**: dense early → sparse +1/-1 late.
4. **Invalid action masking** — *"essential to training an agent that could compete at the most basic level"*.
5. **Self-play alone underperformed** — needed external opponents (scripted bots, prior champions) in the mix.
6. **PPO-after-BC** matched 88% win rate without per-map specialization (vs. RAISocketAI's per-map ensemble).

Failure modes worth knowing:

- *"Naive Large Map Training: Direct PPO training on 64x64 maps without bootstrapping produced training instability — a training policy that initially won 40-50% of training games, dropped to 20% midway."*
- The authors hypothesize **A2C may transition more smoothly from BC than PPO** because A2C's loss form is closer to BC.

Transfer: orbit-wars at 100×100 continuous space is closer to the 32×32-64×64 microRTS regime than 16×16. The paper's curriculum + BC-scaled-by-unit-count is the most transferable single recipe, and the failure mode of "PPO-from-scratch on big maps collapses mid-training" should govern the design choice between BC-bootstrap and pure RL.

---

## 10. ConnectX (perpetual, AlphaZero/MCTS dominated)

- Paper: https://arxiv.org/abs/2210.08263

ConnectX is fully observable, deterministic, and small enough that **plain MCTS at ~20,000 simulations/move beats hybrid MCTS+minimax** because the simulation count dominates depth-quality. Direct relevance to orbit-wars is low (orbit-wars is real-time and continuous), but the ConnectX evidence reinforces that simulation throughput is the crucial axis. For orbit-wars, this favors the Lux S3 / Halite III recipe of "rewrite the env in a fast language so MCTS or BC can evaluate millions of variations in the per-step budget".

---

## 11. Cross-comp synthesis & recipe for orbit-wars

### Heuristic-vs-IL-vs-DRL when each won

| Regime | Examples |
|---|---|
| **Heuristic dominant** | Halite II (1st), Halite III (1st), Halite IV (1st was hybrid; 4th pure rule), **Lux AI S2 (1st despite 1B IL frames provided)** |
| **IL dominant** | Kore 2022 (1st: 200M-tuple Transformer); Halite IV (rank 8: semantic-segmentation) |
| **DRL dominant** | Lux AI S1 (Toad Brigade, IMPALA+UPGO), Lux AI S3 (Frog Parade, PPO+SE-ResNet), Hungry Geese (HandyRL self-play), microRTS 2023 (BC+PPO) |

**The pattern:** heuristic wins where the action space is decomposable into "sensible local sub-decisions" (Halite mining, Lux factory placement, Halite II ship roles). IL wins when expert demonstrations exist on the leaderboard and the action space is naturally tokenizable (Kore plans). DRL wins when the game has irreducible sequential coordination across many units (Lux S1/S3, Hungry Geese, microRTS) AND the team has env-throughput and compute.

### Recommended phased recipe for orbit-wars

| Phase | Weeks | Approach | Why | Citations |
|---|---|---|---|---|
| 1 | 1-2 | Pure heuristic: fight-or-flight + planet priority queue + symmetry | Beats 80% of LB instantly per Halite II / Lux S2 evidence | https://recursive.cc/blog/halite-ii-post-mortem.html, https://www.kaggle.com/competitions/lux-ai-season-2/writeups/ry-andy-1st-place-solution |
| 2 | 3-4 | Add NN opponent move predictor for combat decisions; commit-only-if ≥ X% safe | TheDuck314 Halite III pattern; compounds heuristic | https://github.com/TheDuck314/halite2018 |
| 3 | 5-6 | Custom Rust simulator + scrape top-N replays; BC autoregressive policy | Kore 2022 pattern + Lux S3 throughput trick | https://github.com/khanhvu207/kore2022, https://github.com/IsaiahPressman/kaggle-lux-2024 |
| 4 | 7-8 | PPO finetune w/ unit-count-scaled CE loss (or A2C if PPO unstable) | microRTS 2023 lesson — A2C transitions more smoothly from BC than PPO | https://arxiv.org/html/2402.08112v1 |

### Mandatory tricks (do regardless of phase)

1. **4-fold symmetry test-time augmentation** around (50, 50) — orbit-wars symmetry is documented in `~/projects/kaggle/orbit-wars/.venv/lib/python3.11/site-packages/kaggle_environments/envs/orbit_wars/orbit_wars.py`. Use for data aug (×4) and inference averaging.
2. **Action masking** — every prior winner at every level used it; without it RL fails to train.
3. **Ship-set pruning by interaction radius** — orbit-wars fleet speed is `1.0 + (max_speed-1.0) * (log(ships)/log(1000))^1.5` (max=6.0). Effective interaction radius per fleet is bounded; only consider relevant fleets per decision.
4. **Comet possibility enumeration** — comets spawn at fixed steps (50/150/250/350/450) seeded by `random.Random(f"orbit_wars-comet-{seed}-{step+1}")`. The set of possible comet states at any tick is finite per known seed; enumerate it for MCTS or value-function input.
5. **+1/-1 sparse reward shaping curriculum** — reward-shape on planet captures or fleet preservation for the first N% of training, then switch to sparse +1/-1 only (Lux S1 pattern).
6. **Avoid PPO-from-scratch on full map** — microRTS evidence: 40-50% → 20% mid-training collapse. Bootstrap with BC first.

### Failure modes documented across comps (avoid)

| Failure | Source |
|---|---|
| Critical bug submitted day-before-deadline | 0Zeta Halite IV postmortem |
| Over-parameterized heuristic → brittle to opponent shifts | 0Zeta Halite IV postmortem |
| Pure self-play → local-optimum collapse | Hungry Geese retrospective; microRTS 2023 |
| PPO on big maps without BC bootstrap → mid-training collapse | microRTS 2023 paper |
| No replay-analysis tooling → debugging blind | 0Zeta Halite IV postmortem |
| Stateless ship-role recompute → role thrash | 0Zeta Halite IV postmortem |

### Estimate of compute needed

- Phase 1 (heuristic): zero GPU
- Phase 2 (NN opponent predictor): 1 GPU-day on RTX 3090 class
- Phase 3 (BC on 200M tuples): **2× A100 80GB × 20 epochs ≈ 5-10 GPU-days** (per Kore 2022 numbers)
- Phase 4 (PPO/A2C finetune from BC checkpoint): **30-40 GPU-days** (per microRTS for 32×32; orbit-wars is 100×100 continuous so likely 40-60 GPU-days)

Total budget: roughly **50-100 GPU-days** for a full ML stack. This is achievable on a single RTX 3090 over the 8-week available window (1 GPU × 56 days ≈ 56 GPU-days at full utilization). Lux S3's Frog Parade hit 300M frames in 8 days on a RTX 3090, exactly this regime.

---

## 12. Source compendium

Primary writeups (all cited above):

1. https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md (Lux S3 1st, Frog Parade)
2. https://www.kaggle.com/competitions/lux-ai-season-2/writeups/ry-andy-1st-place-solution (Lux S2 1st)
3. https://github.com/ryandy/Lux-S2-public (Lux S2 1st repo)
4. https://www.kaggle.com/competitions/kore-2022/discussion/340035 (Kore 2022 1st)
5. https://github.com/khanhvu207/kore2022 (Kore 2022 1st repo)
6. https://recursive.cc/blog/halite-ii-post-mortem.html (Halite II 1st, reCurs3) — note: site occasionally refuses connections
7. https://medium.com/aescru/halite-ii-strategies-of-a-top-player-88127b3b49e2 (Halite II top-player guide, James Jones)
8. https://lakesidethinks.com/post/2018/10/halite2-strategy.html (Halite II top-3 review)
9. https://github.com/FakePsyho/halite2 (Halite II 2nd repo)
10. https://shummie.github.io/Halite-2-Shummie/ (Halite II 3rd postmortem)
11. https://github.com/ttvand/Halite (Halite IV 1st repo)
12. https://github.com/0Zeta/HaliteIV-Bot (Halite IV 4th repo + writeup)
13. https://khavo.ai/2020/09/15/halite/ (Halite IV rank-8 IL writeup)
14. https://github.com/teccles-halite/halite3-bot (Halite III 1st repo)
15. https://github.com/TheDuck314/halite2018 (Halite III 6th, w/ NN collision predictor)
16. https://www.kaggle.com/competitions/lux-ai-2021/writeups/toad-brigade-toad-brigade-s-approach-deep-reinforc (Lux S1 1st, Toad Brigade)
17. https://github.com/IsaiahPressman/Kaggle_Lux_AI_2021 (Lux S1 IL alt)
18. https://github.com/DeNA/HandyRL (Hungry Geese 1st framework)
19. https://www.kaggle.com/competitions/hungry-geese/writeups/takedarts-5th-place-solution-geesezero (Hungry Geese 5th)
20. https://zenn.dev/ktechb/articles/e2394bc27358c4 (Hungry Geese retrospective, JP)
21. https://arxiv.org/html/2402.08112v1 (microRTS 2023 BC+PPO paper)
22. https://openreview.net/forum?id=7t8kWYbOcj (Lux S3 organizers paper)
23. https://www.twosigma.com/articles/halite-ii-concludes-winners-announced/ (Halite II winner announcement)

Engine source (local citation): `~/projects/kaggle/orbit-wars/.venv/lib/python3.11/site-packages/kaggle_environments/envs/orbit_wars/orbit_wars.py`
