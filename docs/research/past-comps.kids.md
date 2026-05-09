# How AI Bots Won Past Game Competitions — Plain English Edition

> Written for someone smart but new to AI/ML. If a word is in **bold italics** the first time it appears, look it up in the glossary at the bottom.

This is a research summary for a Kaggle competition called **orbit-wars**. orbit-wars is a 2-player game played on a computer where each side commands fleets of spaceships flying around planets. The goal is to capture more planets than your opponent.

Kaggle has run several similar games in the past. Studying who won them, and *how* they won, tells us what to build for orbit-wars.

---

## The big question: do we hand-write rules, or train an AI to learn?

There are basically three ways to make a bot for these games:

```
  ┌──────────────────────────────────────────┐
  │  Three ways to build a game-playing bot  │
  └──────────────────────────────────────────┘

   1. HEURISTIC          2. IMITATION             3. REINFORCEMENT
      ("rule-based")        ("copy the pros")        LEARNING ("RL")
   ────────────────      ─────────────────         ────────────────────
   Programmer thinks     Watch lots of replays     Bot starts random,
   "if enemy is closer   from top players,         plays millions of
   than X, run away"     train neural net to       games against itself,
   and codes that.       predict their moves.      gradually learns what
                                                   wins.
   Like writing a        Like watching a chess     Like an alien who
   chess opening book.   master and copying.       learned chess by
                                                   only knowing the
                                                   final score.
```

In Kaggle's history, **all three have won different competitions**. The winning approach depends on (a) how complex the game is, (b) whether good replays are available to copy from, and (c) how much computer power the team has.

---

## The 9 competitions we studied (sorted from most-recent to oldest)

### 1. Lux AI Season 3 (2024-2025) — **Reinforcement Learning won**

In this game, two AI agents compete on a 24×24 grid. The unusual twist: some game rules are *hidden* from the players, and matches are best-of-5 so the bot has to learn what's happening as it plays.

**Winner: "Frog Parade" by Isaiah Pressman**

He used a method called **_PPO_** (a kind of reinforcement learning) on a neural network with about 10 million parameters, training for ~8 days on a single high-end gaming GPU (RTX 3090).

His three coolest tricks:
- **Wrote the game in Rust** to make it run 10× faster, so his bot could practice ~110,000 game-moves per second.
- **Detective work**: since some rules were hidden, his bot would *deduce* them by watching how the game state changed turn-to-turn — like figuring out the rules of Battleship from each "hit" or "miss" reply.
- **Mirror trick**: the game is symmetric (looks the same if you flip it diagonally), so he showed his bot the same situation in 4 different orientations, effectively quadrupling his training data.

> Writeup: https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md

**Why this matters for orbit-wars:** The mirror trick is a freebie — orbit-wars also has rotational symmetry around the center. We should always train with this kind of data flipping, and the Rust-rewrite trick is the secret weapon: a 10× faster game simulator makes everything else 10× cheaper.

---

### 2. Lux AI Season 2 (2023) — **Hand-written rules won, surprisingly**

This was a follow-up where you control workers, factories, and grow alien plant life called "lichen" on a grid. The competition organizers literally *gave away* a billion frames of expert play, hoping people would train AI on it.

**Winner: "ry-andy" — pure Python, hand-written rules. No AI.** ([repo](https://github.com/ryandy/Lux-S2-public))

Despite all the free training data, the competition was won by someone who just thought really hard about the game and wrote good rules. He beat 645 other teams.

> Writeup: https://www.kaggle.com/competitions/lux-ai-season-2/writeups/ry-andy-1st-place-solution

**Why this matters for orbit-wars:** Don't rush to train an AI before you've tried the boring hand-written approach. A really clever rule-based bot can beat a mediocre trained AI. Build the hand-written one first, then improve from there.

---

### 3. Kore 2022 — **Imitation Learning won**

Players control fleets of spaceships mining minerals. Each fleet's "plan" is just a string like `N 10 W 5 E 3` (go North 10 turns, West 5, East 3).

**Winner: khanhvu207** treated the problem like Google Translate — translating a *picture of the game* into a *string of moves*.

His method, called **_imitation learning_**, worked like this:

```
   Step 1: Download replays from top 5 players
           ↓
           200,000,000 examples of (game-state → ship-plan)
   Step 2: Train a giant Transformer (same kind of NN as ChatGPT)
           to read a game state and write the right plan
           ↓
   Step 3: Submit the trained model. It plays like the top 5 averaged.
```

He used 2 very expensive GPUs (A100, $10,000 each) for training. His coolest trick: he **threw away 60% of the picture** during training — the bot had to learn to make decisions even with most of the information missing, which made it way more robust.

> Writeup: https://www.kaggle.com/competitions/kore-2022/discussion/340035 · Repo: https://github.com/khanhvu207/kore2022

**Why this matters for orbit-wars:** Once a few good bots exist on the leaderboard, we can scrape their replays and train a copycat. This is a very efficient way to skip the hard part.

---

### 4. Halite II (2017-2018) — **THE most similar past game**

Halite II is the past competition that looks the most like orbit-wars: 2D continuous space (no grid), spaceships, planets, fleet vs fleet combat.

**Top 3:**
- 1st: **reCurs3** (a developer at Ubisoft Montreal who works on Assassin's Creed)
- 2nd: **FakePsyho** (a Polish puzzle champion now at OpenAI)
- 3rd: **shummie** (an actuary at an insurance company)

All three used hand-written rules, no AI. Here are the gems they invented:

#### The "fight or flight" formula (reCurs3)

```
For each of MY ships:
  count_enemies_nearby   = how many enemy ships within radius
  count_friends_nearby   = how many of my ships within radius

  if enemies > friends:  RUN AWAY
  else:                  ATTACK
```

#### How to run away — the "Coulomb particle" trick

If a ship decides to run, it doesn't pick a random direction. It runs **straight away from the AVERAGE position of all nearby enemies**, like a negative magnet repelled by other negative magnets:

```
                                  fleeing ship
                                       △
                                       │
                                       │  (run vector = -average(enemies))
                                       │
       ☠ ─────── center ─────── ☠
       └────────── enemies cluster ──┘
```

#### "Desertion" — a sneaky 4-player trick (shummie)

In 4-player matches, you can hide one ship in a far corner. Even if all your other ships die, that one corner-ship lets you *outlive* opponents who eliminate each other, sneaking you into 2nd place. It's the "play dead until everyone else fights" strategy.

#### "Don't follow the same enemy with too many ships" (FakePsyho)

If too many of your ships chase one enemy, the rest of your fleet bunches up and you lose territory. Cap how many ships can target each enemy.

> Writeups: https://recursive.cc/blog/halite-ii-post-mortem.html (1st), https://github.com/FakePsyho/halite2 (2nd), https://shummie.github.io/Halite-2-Shummie/ (3rd) · Top-3 review: https://lakesidethinks.com/post/2018/10/halite2-strategy.html

**Why this matters for orbit-wars:** orbit-wars is essentially Halite II with different combat math. Almost every trick above transfers directly. The fight-or-flight formula is probably the first thing we should code.

---

### 5. Halite IV (2020) — **Hybrid: rules + a tiny AI**

A 4-player grid game. Winner **ttvand (Tom Van de Wiele)** used hand-written strategy *plus* a small neural network just to predict what opponents would do next ([repo](https://github.com/ttvand/Halite)).

The 4th-place team wrote a 100% rule-based bot ([0Zeta repo](https://github.com/0Zeta/HaliteIV-Bot)) and they shared excellent lessons:

- **"Plantation" farming**: place 3 outposts in a triangle around a resource cluster, harvest the middle. Defensible AND efficient.
- **Decide all moves at once** using something called the Hungarian Algorithm — instead of "ship 1 moves, then ship 2 reacts to ship 1", do `assign all 50 ships their best move simultaneously`. Much smarter.
- **Recompute every ship's role every turn** — don't let stale plans hang around.

Their honest list of regrets is gold:
1. Bug submitted the day before deadline broke their bot
2. Too many tunable parameters → fragile
3. No replay-analysis tools → couldn't debug
4. Pathfinding was missing → ship traffic jams

**Why this matters for orbit-wars:** All four regrets are warnings for us. Build replay tools early. Submit early. Don't add too many tuning knobs.

---

### 6. Halite III (2018-2019) — **Algorithmic rules with one neural net**

Winner **teccles** ran the **_Dijkstra algorithm_** for every single ship every turn, computing "how much halite per turn would I earn if I went to square X" for every X on the board. Best-square wins.

The 6th-place team **TheDuck314** had a great hybrid trick: they trained a neural network to predict opponent moves, then would only commit to a move if the NN said "you're at least 98% safe". Risk-averse AI.

> Writeups: https://github.com/teccles-halite/halite3-bot · https://github.com/TheDuck314/halite2018

**Why this matters for orbit-wars:** The 98%-safety NN is a clean way to add ML to a heuristic bot — small NN, big benefit. We should layer this on top of our heuristic in week 4-5.

---

### 7. Lux AI Season 1 (2021) — **Deep RL won**

Game has a day/night cycle, day means harvest, night means survive. **Toad Brigade** team won using pure reinforcement learning.

They started with hand-written rules but the RL agent surpassed it within the first month, so they pivoted entirely to RL.

Key technical detail: they did NOT use the popular **_PPO_** algorithm. They used **_IMPALA_** with two extras called UPGO and TD(λ). This is technical, but the point is: the default RL algorithm isn't always the right one.

> Writeup: https://www.kaggle.com/competitions/lux-ai-2021/writeups/toad-brigade-toad-brigade-s-approach-deep-reinforc

**Why this matters for orbit-wars:** If we go down the RL path, look beyond plain PPO. Also: Toad Brigade's "test-time augmentation" trick (run the bot on the board, then on the rotated board, average the answers) is universally applicable.

---

### 8. Hungry Geese (2021) — **Self-play RL with late-game search**

Four snakes on a tiny grid eating food. Won by the **HandyRL** team using **_self-play_** RL.

Coolest trick: the **step-counter input**. They told the network "you're at turn 197 of 200" — this completely changed strategy in the endgame, like coaches yelling "two minutes left!" in basketball.

In the final month, the runners-up bolted **_MCTS_** (a search algorithm used in **_AlphaZero_**) on top of their trained network. The trained network gave intuitions, MCTS searched moves a few turns ahead. Big jump.

> Framework: https://github.com/DeNA/HandyRL · Retrospective: https://zenn.dev/ktechb/articles/e2394bc27358c4

**Why this matters for orbit-wars:** orbit-wars has comets that spawn at fixed turns (50, 150, 250, 350, 450) with predictable randomness — perfect for an MCTS-style search to plan around. The step-counter trick should be in our model from day 1.

---

### 9. microRTS 2023 — **Imitation Learning + RL hybrid**

A research RTS competition (not Kaggle). The winning team showed that:

1. First train the bot to **copy** existing bots (imitation learning)
2. Then **fine-tune** with RL (PPO)

This combo beat starting RL from scratch. In one experiment, pure-RL training on a big map *got worse* mid-training (40% win rate → 20%).

> Paper: https://arxiv.org/abs/2402.08112

**Why this matters for orbit-wars:** Don't try to train RL from random initialization on the full game. First copy good bots, then fine-tune. This is now the consensus best practice.

---

## ASCII picture: the recommended phases for orbit-wars

```
  Week 1-2   Week 3-4    Week 5-6      Week 7-8
  ─────────  ─────────   ──────────    ─────────────────
  HEURISTIC  +NN OPP.    +BC POLICY    +RL FINETUNE
  baseline   PREDICTOR   from replays  (warm start, not from scratch!)
  ↑          ↑           ↑             ↑
  Halite II  Halite III  Kore 2022     microRTS 2023
  pattern    TheDuck314  pattern       BC→PPO pattern
              pattern

  ──────────────────────────────────►  TIME
```

Each phase reuses the work from the previous phase. We're not throwing away the heuristic — the trained policies are layered on top.

---

## When did each approach win?

| Approach | Won what | Lost what |
|---|---|---|
| Hand-written rules | Halite II (top 3), Halite III (1st), Halite IV (1st, 4th), **Lux AI S2 (1st!)**, Kore 2022 (before IL bots arrived) | Lux AI S1, Lux AI S3, Hungry Geese, microRTS |
| Imitation learning (copy pros) | Kore 2022 (1st), Halite IV (rank 8) | Lux AI S1, S3 (no expert data) |
| Reinforcement learning | Lux AI S1 (1st), Lux AI S3 (1st), Hungry Geese (1st), microRTS (1st) | Halite II, III, IV, Lux AI S2 |

**Pattern**: rules win when the game can be broken into local "obvious" decisions. Imitation wins when good demonstrators exist. RL wins when many units have to coordinate over long time horizons AND you have the compute.

orbit-wars sits in the middle — it's combinatorial like Halite II, but the winner of a *modern* (2024+) Kaggle simulation comp is probably going to use some ML. Best move: build all three layers, ship the strongest one.

---

## Tricks every winner used (steal these all)

1. **Action masking** — never let the bot consider an illegal move. (Used by every RL winner.)
2. **Symmetry data augmentation** — flip the board to multiply your data. orbit-wars has 4-fold symmetry around (50, 50), so we get 4× free data.
3. **Test-time augmentation** — at inference, run the model on board + rotated board, average predictions.
4. **Custom fast simulator** — Lux S3 winner rewrote the env in Rust for ~10× speedup. Do this if going RL.
5. **Limit ships per target** — FakePsyho's trick. Stops your fleet from clumping.
6. **Step-count as input** — Hungry Geese trick for endgame switching.

---

## Glossary

- **Heuristic / rule-based**: a bot whose behavior is hand-coded by a programmer using `if-then-else` statements (no learning involved).
- **Imitation Learning (IL)** / **Behavioral Cloning (BC)**: training a neural network to mimic the moves a human or top bot made, using their replay data as examples.
- **Reinforcement Learning (RL)**: a bot starts knowing nothing, plays games, and slowly learns by being rewarded (+1) for wins and punished (−1) for losses. Like training a dog with treats.
- **Self-play**: when an RL bot trains by playing copies of itself. Very powerful, but can collapse into weird local strategies if not managed carefully.
- **PPO (Proximal Policy Optimization)**: the most popular RL algorithm. Standard baseline.
- **IMPALA**: a different RL algorithm, more efficient for distributed training. Used by Toad Brigade.
- **MCTS (Monte Carlo Tree Search)**: a planning algorithm that simulates many possible move-sequences ahead and picks the one with the best simulated outcome.
- **AlphaZero**: a famous DeepMind system that combines self-play RL with MCTS. Beat human world champions at chess, Go, and shogi.
- **ELO**: a rating system; if your ELO is 1500 and your opponent's is 1300, you should win ~76% of games.
- **Transformer**: a neural network architecture (the same kind that powers ChatGPT). Good at tokens/sequences.
- **CNN (Convolutional Neural Network)**: a neural network for grid-shaped data (images, game boards). Sees local patterns.
- **ResNet**: a CNN that uses "skip connections" so very deep networks can train. The Lux S3 winner used a small one.
- **GPU**: graphics card, used for training neural networks. RTX 3090 is consumer-tier; A100 is industrial-tier (~$10k each).
- **Action masking**: explicitly telling the model "you cannot move there, that move is illegal" so it never chooses one.
- **Test-time augmentation (TTA)**: at inference, run the model multiple times on rotated/flipped versions of the input and average. Reduces variance.
- **Curriculum learning**: train on easy versions first (small map, dense rewards), then harder (big map, sparse rewards).
- **Reward shaping**: temporarily adding extra small rewards (e.g. "+0.01 per planet captured") to help RL learn faster, then turning them off.
- **Hungarian algorithm / linear sum assignment**: a math trick to optimally assign N workers to N tasks all at once.
- **Dijkstra's algorithm**: shortest-path algorithm. Used by Halite III winner to find best mining route.

---

## Sources (in case you want to read more)

The most-similar past comp to orbit-wars: https://recursive.cc/blog/halite-ii-post-mortem.html (Halite II 1st-place writeup, by reCurs3 / Ubisoft Montreal). Mirror at https://medium.com/aescru/halite-ii-strategies-of-a-top-player-88127b3b49e2 if the original is offline.

Most-recent (and most informative) comp: https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md (Lux AI Season 3 1st place).

The cautionary tale that hand-written rules can still win: https://github.com/ryandy/Lux-S2-public (Lux AI S2 1st place).

The full reference list is in the companion file `past-comps.references.json`, and the technical-density version in `past-comps.dense.md`.
