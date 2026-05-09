# exp001 — nearest-planet sniper baseline

- **Source commit:** `9ea65e9`
- **Kaggle submission ID:** `52478880`
- **Submission ELO (Kaggle public LB):** ~600 (newcomer baseline)
- **Date:** 2026-05-09

## Approach

Greedy single-target sniper:

1. For each owned planet, find the nearest non-owned target.
2. Compute `ships_needed`:
   - Neutrals (`owner == -1`): exactly `garrison + 1`
   - Enemy planets: `garrison + 1 + MARGIN`
3. Don't drain a planet completely — keep `RESERVE` ships behind for defense.
4. Skip launches that would take more than `MAX_FRACTION` of the source planet's
   garrison (over-commit guard).

### Hyperparameters

| param          | value | rationale                                  |
| -------------- | ----- | ------------------------------------------ |
| `RESERVE`      | 5     | keeps a tripwire behind to absorb counters |
| `MAX_FRACTION` | 0.85  | over-commit guard — never empty a planet   |
| `MARGIN`       | 1     | minimal extra vs enemy garrisons           |

## What worked

- Beats **random** consistently across all 9 seed/episode combinations
  (9/9 wins as left, 9/9 wins as right in `tournament_log.csv`).
- Self-play stable: no zero-divisions, no out-of-bounds angles.
- Single-file, no external state — passes Kaggle's submission constraints
  out of the box.

## What didn't

- **Loses to starter at seeds 1 and 2** (6/9 losses). Starter's wider scatter
  attacks overwhelm a greedy nearest-only strategy when starter happens to spawn
  with multiple closely-clustered planets.
- No defensive logic: when an incoming fleet is large, we keep launching
  outwards instead of recalling.
- No production-rate awareness — happily attacks low-production planets when
  high-production ones are barely further away.

## Tournament summary (3 agents x 3 seeds x 3 episodes = 54 games)

```
agent                             mu    sigma     rank     n
---------------------------  -------  -------  -------  ----
experiments/exp001/agent.py   33.013    1.964   27.122    36
starter                       31.921    1.924   26.148    36
random                        19.788    3.246   10.051    36
```

Despite losing 6/9 to starter, exp001 wins 3/9 and dominates random — net
TrueSkill (`mu - 3*sigma`) puts it slightly above starter.

## Next iterations to consider

- **exp002:** add fleet recall when an incoming threat exceeds local garrison
- **exp003:** weight target choice by `production / distance` instead of raw distance
- **exp004:** swarm coordination — multiple planets target the same enemy when
  a solo strike isn't enough

## Files

- `agent.py` — byte-identical copy of `src/orbit_wars/agent.py` at commit `9ea65e9`
- `config.yaml` — frozen hyperparams + tournament setup
- `tournament_log.csv` — full 54-game round-robin results
- `notes.md` — this file

## Reproduce

```bash
make tournament TOURN_AGENTS="experiments/exp001/agent.py random starter" \
                TOURN_EPISODES=3 TOURN_SEEDS=1,2,3
make rank
```
