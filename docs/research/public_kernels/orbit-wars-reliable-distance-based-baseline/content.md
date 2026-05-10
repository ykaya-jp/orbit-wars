## [MD]
# Orbit Wars: a reliable distance-based baseline

This notebook is a practical walkthrough for building a **single-file Orbit Wars bot** that can play both 2-player and 4-player games without relying on extra local modules.

The goal is not to present a magic leaderboard solution. The goal is to give you a dependable baseline that is easy to read, easy to submit, and useful as a starting point for your own experiments.

What you get here:

- a mental model for the game;
- the main engineering choices behind the bot;
- the common pitfalls that caused real failures;
- a complete `main.py` generator;
- a `submission.tar.gz` package ready to submit.

## [MD]
## 1. The game in one paragraph

Orbit Wars is a resource conversion game. Planets produce ships. Ships can be launched to capture or reinforce planets. The hard part is that ships are slow, planets move, and a locally good attack can become bad by the time it arrives.

So a useful baseline needs to answer four questions every turn:

1. Which planets are worth owning?
2. How many ships do we need to send?
3. Which of our planets can safely spare ships?
4. Is the target still worth it after travel time and enemy reaction risk?

This bot is built around those questions. It is intentionally heuristic-driven rather than search-heavy, because a robust heuristic bot is easier to debug under competition time limits.

## [MD]
## 2. Design philosophy

The baseline follows three rules.

**First, prefer stable value.** High-production static planets and nearby targets are more attractive than distant low-production targets.

**Second, do not empty the frontier.** A planet near enemy territory should keep more ships than a safe backline planet.

**Third, package as one file.** In agent competitions, import paths can behave differently between local runs and hosted simulations. A single `main.py` removes an entire class of avoidable failures.

This is not the most aggressive style. It is a stable starting point that should survive, expand, and produce useful replays for later improvement.

## [MD]
## 3. Important pitfall: detecting 2P vs 4P

One surprisingly easy mistake is to infer player count from only `initial_planets`.

In some games, initial planet owners may be neutral (`-1`). If you use that alone, a 4-player game can be misclassified as a 2-player game. That kind of bug is painful because the bot may look fine in some local tests and then collapse in public 4P matches.

The safer pattern is:

- first inspect the current `planets` owner set;
- count non-neutral owners;
- only use initial state as fallback.

The submitted code follows that defensive style.

## [MD]
## 4. Target scoring

The bot uses a simple but useful scoring idea:

```text
target score roughly increases with:
  production value
  strategic value
  enemy ownership
  static planet stability

target score roughly decreases with:
  travel time
  required ships
  extra attack margin
  enemy reinforcement risk
```

This is enough to produce sensible behavior:

- early neutral expansion;
- opportunistic enemy captures;
- higher caution for long-distance attacks;
- different margins for neutral and hostile planets.

## [MD]
## 5. Why distance matters

Distance is not just geometry. It is risk.

A ship sent across the map is unavailable for many turns. During that time:

- the target may gain ships through production;
- enemy fleets may arrive first;
- the source planet may become vulnerable;
- a third player may benefit from the fight.

For a baseline bot, distance-aware scoring is one of the highest-return ideas. It is simple, fast, and prevents many expensive overextensions.

## [MD]
## 6. Frontier defense

A common beginner bot failure is this:

> It captures planets, but then immediately loses them.

The baseline tries to reduce that by giving frontier planets a higher minimum garrison. A frontier planet is simply a planet close to enemy influence. Backline planets can donate more ships; frontier planets should be more conservative.

This is not perfect tactical defense, but it greatly improves survival compared with sending everything whenever a target looks barely capturable.

## [MD]
## 7. 2P and 4P are different games

In 2-player games, attacking the opponent is usually a direct relative gain.

In 4-player games, an attack can accidentally help a third player. That means the bot needs more caution around:

- overcommitting to distant hostile planets;
- weakening itself while two other players grow;
- fighting the wrong neighbor while a leader snowballs.

This baseline does not solve all 4P politics, but it does use separate margins and weights for 4P so it is not simply treating 4P as '2P with extra enemies'.

## [MD]
## 8. Build the submission package

The full v5 source is stored as a tiny public Kaggle Dataset:

`afr1ste/orbit-wars-v5-distance-baseline-agent`

The next cell keeps the notebook readable: it copies `main.py` from that dataset and builds `submission.tar.gz`.

If you want to submit this notebook output manually, submit the generated `submission.tar.gz` file.

## [CODE]
```python
from pathlib import Path
import hashlib
import tarfile

source_path = Path("/kaggle/input/orbit-wars-v5-distance-baseline-agent/main.py")
agent_code = source_path.read_text(encoding="utf-8")
main_path = Path("main.py")
main_path.write_text(agent_code, encoding="utf-8")

with tarfile.open("submission.tar.gz", "w:gz") as tar:
    tar.add(main_path, arcname="main.py")

digest = hashlib.sha256(main_path.read_bytes()).hexdigest()[:16]
print(f"Wrote {main_path} ({main_path.stat().st_size:,} bytes)")
print(f"SHA256 prefix: {digest}")
print("Wrote submission.tar.gz")
```

## [MD]
## 9. How I would improve this baseline

After you have a stable bot, do not only tune constants blindly. Use replay evidence.

Useful metrics to track:

- first action turn;
- production at turns 50, 100, and 150;
- planet count over time;
- ships sent during turns 50-100;
- capture retention after 20 and 50 turns;
- how often captured planets are immediately taken by a third player;
- whether 4P games are lost to a runaway leader.

The biggest next step is usually a better tactical allocator: instead of each planet independently deciding what to do, compute surplus ships globally and assign them to the best tasks.

## [MD]
## 10. Closing notes

This baseline is intentionally readable. It is meant to be forked, tested, and improved.

Good Orbit Wars bots are not just more aggressive. They turn ships into durable production while avoiding fights that only help another player. Start with reliability, build good replay diagnostics, and then increase tempo where the evidence says it is safe.
