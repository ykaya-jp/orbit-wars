# Orbit Wars: What the Top Players Are Doing (high-school edition)

Hi! This is the friendly version of `lb-observations.dense.md`. Same facts, fewer engineering acronyms.

If you have not played Orbit Wars yet, the short version is: it is a 2-player real-time strategy game where each player owns one home planet, gains ships every turn, and tries to capture the other player's planets. The board is 100 × 100 and there is a sun in the middle that destroys any ship that flies through it. Random "comet planets" appear at fixed turns (50, 150, 250, 350, 450) — they're like free real estate that spawns mid-game.

Our bot is named **Reexel** (we run a basic "shoot the closest planet" strategy). Other people on Kaggle have written much smarter bots. This document explains what they're doing.

---

## 1. What does the leaderboard look like?

Think of the leaderboard like the chess Elo ranking: a number that goes up when you win, down when you lose. In chess, beginners are ~800, club players ~1500, masters ~2200. In Orbit Wars right now (2026-05-09):

| Rank | Team | "Skill rating" |
|---|---|---|
| 1 | flg | 1650.9 |
| 2 | bowwowforeach | 1650.9 |
| 3 | Ebi | 1631.4 |
| 4 | Isaiah @ Tufa Labs | 1582.1 |
| 5 | Vadasz | 1553.3 |
| ... | ... | ... |
| 30 | Aidan P5 | 1286.6 |
| 100 | Álvaro | 1094.1 |

We (Reexel) are around **300-360**, which is very low. Why? Our score is 326 because we have only played 7 ranked games and lost most of them (more on that below).

**Important:** Top-30 teams keep submitting new versions every day. The competition is alive — strategies that worked last week might not work this week.

The full top-200 is saved as a spreadsheet at `docs/research/lb_snapshot_2026-05-09.csv`.

---

## 2. How did our bot do?

We played 7 ranked games. We won 2 and lost 5.

```
Episode ID    Opponent           Result    Steps
76155027      Yudji Chainho      LOSS      140
76155250      wojak_321          LOSS      160
76155486      Jason Kimmmmmmmm   WIN       360  <- yay
76155696      lishell liang      LOSS      500  <- ran out of time
76156043      Vishal Grover      LOSS      420
76156165      Malaika Ijaz       WIN       282  <- yay
76156402      Sai Rakshit0107    LOSS      220
```

Each game is in `data/replays/episode-<ID>-replay.json`. They're big JSON files (about 10 MB each) where every turn is recorded with all planets, all ships, and what each player did.

---

## 3. What does a top-tier game look like?

I downloaded games where two highly-ranked players fought each other. Here's one: rank-2 (`bowwowforeach`) vs rank-1 (`flg`), file `data/replays/episode-76155725-replay.json`.

Imagine a slow-cooking saucepan. At turn 0 each player has 1 planet with 10 ships. By turn 25 they each own 2 planets and have ~80-90 ships total. The game is calm.

Then turn 50 arrives — a **comet wave** drops 4 free comet planets onto the board (this happens at turns 50, 150, 250, 350, 450). Both players grab planets like crazy:

```
       Planets owned   Ships (on planets + flying)
turn 0:    1 vs 1         10  vs  10
turn 25:   2 vs 2         87  vs  91
turn 50:   7 vs 8        324  vs 213    <- comet grab
turn 75:  11 vs 9        711  vs 535
turn 100: 13 vs 8        701  vs 385
turn 143: 23 vs 0       1899  vs   0    <- bowwow wins
```

At turn 143 `flg` had zero planets — game over. `bowwowforeach` won.

**Pattern:** top players triple their planet count between turn 25 and turn 75 by aggressively grabbing comet planets and neutral planets. After that the production gap (more planets = more ships per turn) compounds and one side runs the other out.

To make a good analogy, the top players are like good pool players who don't just sink the ball in front of them — they sink one ball **while setting up the next shot**. They are always thinking 2-3 turns ahead.

### How big are their fleets?

When you launch ships from one of your planets, you choose how many. Top players are very picky:

| Player | how often they launch | typical size | biggest ever |
|---|---|---|---|
| flg (#1) | 121 times | 30 ships | 133 ships |
| bowwowforeach (#2) | 90 times | 41 ships | 245 ships |
| Isaiah (#4) | 59 times | **106 ships** | **986 ships!** |
| Vadasz (#5) | 78 times | 25 ships | 136 ships |
| Forrest (#58) | 72 times | 64 ships | 250 ships |

Isaiah's bot is interesting — it sends fewer, **much bigger** fleets (max 986 ships in one launch!). Imagine saving up your allowance for a year and buying one mega-thing. That's Isaiah's strategy.

flg and bowwowforeach send more fleets but tune the size to the situation. Sometimes 4 ships (a tiny "snipe"), sometimes 245 ships (a "kill stack"). They adapt.

Our bot? We always send `garrison + 2`. So if our planet has 10 ships and the target has 8, we send 9. If the target is bigger than we can afford, we don't shoot at all and just sit there. **That is why we lose.**

---

## 4. Why are we losing?

Our bot's whole code is 73 lines (`submissions/main.py`). It does this every turn:

```
For each planet I own:
  Find the closest non-friendly planet
  If I have enough ships to barely capture it: shoot
  Otherwise: do nothing
```

That's it. No sun-dodging. No team attacks (one big shot from 3 planets). No comet planning. No taking back lost planets.

Here are 5 ways we die in real games:

### Failure A: We fall behind early and never catch up

Game vs Yudji Chainho, turn 25: we have 1 planet with 60 ships, Yudji has 2 planets with 62 ships and **9 fleets already in flight**. Our 0 fleets in flight means our ships are sitting on planets, not pressuring anyone. By turn 47 we have 67 ships, Yudji has 149. Game over by turn 140.

**Analogy**: imagine a pickup basketball game where one team plays defense the whole time and never shoots. They lose because the ball is always in their half of the court.

### Failure B: 500-step starvation

Game vs lishell liang, 500 turns: neither bot grabs much. We hover at 1 planet, opp at 1 planet, then 4 by the end. We get the loss because at turn 500 the engine counts ships and they have 110, we have 43.

We never recapture lost planets. Once a planet is enemy, our "shoot the closest" finds an enemy planet with too many ships and decides not to shoot. Forever.

**Analogy**: a frozen pond hockey game where both players just guard their goal. The one with marginally more pucks at the buzzer wins.

### Failure C: Death by 1000 paper cuts

Game vs Sai Rakshit0107, 220 turns: Sai launched **1601 little fleets** (median 3 ships). It's like being attacked by a swarm of bees — each one is tiny but there are millions. Our `RESERVE = 5` (always keep 5 ships at home for defense) just isn't enough. They bleed us dry.

```
turn  Sai's planets   Sai's launch count   our planets
  50         6              56                  4
  75        12             171                  7
 100        13             305                 12
 150        21             487                  9
 200        32             —                    0  <- gone
```

### Failure D: We fly into the sun

The game has a sun at the center (radius 10). Any fleet whose path crosses through the sun is destroyed (engine source: `orbit_wars.py:606-609`). Our bot does not check for this. So when we shoot from a planet on one side toward a target on the other side, **our ships disappear into the sun and we waste them**.

This is a free 10-line fix: just reject any angle that would hit the sun, pick the second-closest target instead.

### Failure E: We never team up

If we have 3 planets, each picks its own nearest target. So three planets might shoot at one weak neutral and waste 30 ships when one planet would have been enough. Meanwhile a tougher target gets ignored.

Top bots **aggregate**: they look at all targets, decide which one is most valuable, and combine ships from multiple home planets to take it. Our bot doesn't.

---

## 5. What do we know about top bots' code?

Some Kagglers publish their work as public notebooks. I downloaded four of them:

### "Structured Baseline" by pilkwang (194 votes)

This is the **community reference**. Most strong bots are forked from this one. It has **10 different mission types**:

1. **Reinforce-to-hold** — send ships to a planet that's about to fall to defense.
2. **Rescue** — send extra to a planet under attack.
3. **Recapture** — take back a planet you just lost.
4. **Single-source capture** — one planet attacks one target.
5. **Snipe** — small fleet kills an undefended weak planet.
6. **Swarm** — multiple planets coordinate to attack one target.
7. **Crash exploit** — opportunistic attack when enemy fleets crash into the sun.
8. **Follow-up capture** — chase a planet you almost owned.
9. **Live doomed salvage** — when a planet is going to fall anyway, send its remaining ships somewhere useful.
10. **Rear funneling** — move ships from your safe back-rank planets to the front line.

Our bot has **1** of these (#4 only).

The notebook also says: never fly through the sun, predict where rotating planets will be when your fleet arrives (planets near the center spin around the sun), and re-check every plan after each launch.

### "Hybrid agent" by konbu17 (50 votes)

This is the most painful read. Quote from the notebook:

> "v1_sniper [opponent]: hybrid wins 16/16 (100%), rule-base wins 16/16 (100%)"

That `v1_sniper` is **the public sniper baseline our bot is descended from**. So basically every public agent in the top half of the leaderboard beats our type 100% of the time in their own testing. That matches our 326 score — the system has decided we're way below mid-tier.

The author also tried to train a neural network from scratch with reinforcement learning **five times** and gave up: "Five separate ML attempts ran into the same wall." Instead the working approach was a tiny network that **only rejects bad shots** the rule-based agent would otherwise take. That gave them a +19 percentage-point win rate boost.

**Lesson**: don't try to make a neural net play Orbit Wars from zero. Instead, write a good rule-based agent first, then add ML to **filter** its decisions.

### "Target Score 2000.4" by rahulchauhan016 (57 votes)

This author's notebook lists 21 modules, including:

- **MCTS** (Monte Carlo Tree Search) — like how Alpha-Go thinks. Simulates 10 turns into the future, tries different moves, picks the best.
- 5-iteration **lead-aim predictor** with sun avoidance — when shooting at a moving planet, predict where it will be when your ships arrive (like leading a duck shot).
- 7-feature evaluator with weights tuned for: ship count diff (1.0), production diff (46.0!), planet count diff (20.0), risk (-2.8), border pressure (9.0), fleet momentum (0.6), neutral denial (12.0).
- Tiny neural net 14 → 64 → 32 → 1.

The huge weight on production (46.0) makes sense: ships you have now are spent once, but each planet's production keeps giving forever. Owning a 2-production planet for 100 turns = 200 free ships. Long-term thinking wins.

### "OW-Proto" by djenkivanov (119 votes)

This author hit rank ~95 with a bot scoring formula leaked verbatim:

```
score = (100 - dist) + (15 * production) + (10 * enemy_bonus) - (0.7 * total_ships) - (2 * eta)
```

Translation: "I want to attack things that are **close** (smaller dist), **valuable** (higher production), **enemy-owned** (bonus), and **cheap** (fewer ships needed, fewer turns to reach)." This is a sensible mid-tier baseline. Anything above ~1200 ELO beats this bot.

---

## 6. What are the strategy "personalities" out there?

Looking at how often and how big each top bot launches fleets, I can see three main "playing styles":

### Style 1: Kill-stack macro (Isaiah, Forrest)

- **Vibe**: "I'll save up production into one giant fleet"
- Few launches (under 100 per game)
- Median fleet size 60-100+
- Single launches sometimes 200-1000 ships
- Wins by overwhelming the opponent at one moment

### Style 2: Continuous pressure (Vadasz, Shun_PI, HY2017)

- **Vibe**: "I'll send 200-300 medium fleets and never let up"
- 200-300 launches per game
- Median fleet size 25-30
- Max around 100-250
- Wins by attrition (slow bleed)

### Style 3: Adaptive (flg, bowwowforeach)

- **Vibe**: "I'll figure out what works against this opponent"
- Vastly different distributions in different games
- Sometimes 78 big fleets, sometimes 1349 tiny ones
- This is the **#1 and #2** strategy. The top of the leaderboard has bots that change behavior.

---

## 7. About comets (the free real-estate moments)

Comets appear at turns 50, 150, 250, 350, 450 (engine: `orbit_wars.py:27`). They are 4 planets at a time arranged symmetrically (4-fold symmetry around the center). They have ships you can capture and they produce 1 ship per turn each, just like normal planets.

Top bots wait for the comet spawn and **react within 1-3 turns** (`Vadasz` issues 36 ships at turn 52, exactly 2 turns after the spawn). They have programmed "comet grab mode" — at turn 49 they prepare reserves, then at turn 51-52 they fire at the new comets.

Our bot doesn't know comets exist. We just shoot the nearest non-friendly planet, so if a comet happens to be the nearest target, we shoot at it. But we don't plan for it.

---

## 8. What should we do to climb the leaderboard?

In order of difficulty:

### Step 1: Don't fly into the sun (~10 lines of code)

For every shot, check if the path goes through the central sun. If yes, skip and pick the next-nearest target. Engine reference: `orbit_wars.py:606-609`. Easy. Should give +200 to +400 ELO.

### Step 2: Aggregate fleets (~30 lines)

Stop letting each of our planets independently pick its target. Instead, look at all (source, target) pairs, score them by `(target's value / cost in ships)`, and fire the best-ROI shots first. Avoid having two planets shoot at the same target. Should give +100 to +200 ELO.

### Step 3: Recapture logic (~30 lines)

When the enemy takes a planet, **mark it** and prefer to retake it next turn. Currently we just give up. +50 to +150 ELO.

### Step 4: Comet awareness (~50 lines, harder geometry)

At turns 48-52, 148-152, etc., switch into "comet grab mode" — every owned planet sends 40% of its ships at the nearest expected comet location. +50 to +100 ELO.

### Step 5: ML shot validator (the konbu17 trick)

Train a tiny neural network (5,000 weights, 24 input features) to predict "is this shot likely to succeed?". Use it to filter bad shots out of the rule-based agent's decisions. The notebook claims +19 percentage points win rate. +100 to +150 ELO.

After all 5 steps, we should be at **rank 50-100** (ELO ~1100-1300). The very top (1500+) requires **inventing** a new strategy or tuning an MCTS bot — that's a multi-week project.

---

## 9. Quick reference: all the files I made

In `/home/yusuke_kaya/projects/kaggle/orbit-wars/`:

```
docs/research/
  lb_snapshot_2026-05-09.csv             <- Top 200 leaderboard
  lb-observations.dense.md               <- Engineering version of this doc
  lb-observations.kids.md                <- THIS file

data/replays/
  episode-76154720-replay.json           <- Self-play (Reexel × 4)
  episode-76155027-replay.json           <- Our LOSS vs Yudji
  episode-76155250-replay.json           <- Our LOSS vs wojak_321
  episode-76155486-replay.json           <- Our WIN vs Jason
  episode-76155695-replay.json           <- Top: Isaiah vs Vadasz
  episode-76155696-replay.json           <- Our 500-step LOSS vs lishell
  episode-76155725-replay.json           <- Top1 vs Top2: bowwow vs flg
  episode-76155929-replay.json           <- Top1 vs Top2 (rematch)
  episode-76156043-replay.json           <- Our LOSS vs Vishal Grover
  episode-76156145-replay.json           <- Top: bowwow vs Vadasz
  episode-76156160-replay.json           <- Top: Shun_PI vs Vadasz
  episode-76156165-replay.json           <- Our WIN vs Malaika
  episode-76156220-replay.json           <- Top: HY2017 vs jack gell
  episode-76156339-replay.json           <- Mid: Forrest vs Leszek
  episode-76156375-replay.json           <- Top: Shun_PI vs Vadasz (rematch)
  episode-76156398-replay.json           <- Mid: Alvin vs monnu
  episode-76156402-replay.json           <- Our LOSS vs Sai Rakshit
  _analysis.json                         <- Sampled timeseries
```

---

That's the picture. We have a really simple bot in a fancy sandbox where most other bots are 10× more sophisticated. Each of the 5 fixes above is achievable in a day or two. The hard part starts after rank 100 — that's where the real engineering competition begins.
