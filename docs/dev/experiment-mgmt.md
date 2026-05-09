# Experiment Management

This doc describes the local agent-improvement loop:

> ローカルで N agent をぶつけ → ELO で順位付け → 勝てば Kaggle に提出

All commands are wired into the top-level `Makefile`.

## TL;DR

```bash
# 1. Start a new experiment from the current head agent
make exp NAME=exp042

# 2. Edit experiments/exp042/agent.py + config.yaml + notes.md, then…

# 3. Pit it against your past best + the built-ins
make tournament TOURN_AGENTS="experiments/exp042/agent.py experiments/exp001/agent.py random starter" \
                TOURN_EPISODES=5 TOURN_SEEDS=1,2,3

# 4. Look at the ranking
make rank

# 5. If it's the new top, promote it to src/orbit_wars/agent.py and submit
cp experiments/exp042/agent.py src/orbit_wars/agent.py
make submit M="exp042: <one-liner>"
```

## File layout

```
orbit-wars/
├── tools/
│   ├── tournament.py      # round-robin runner (1 episode = 1 subprocess)
│   ├── elo.py             # TrueSkill ledger update / show / reset
│   ├── replay_viewer.py   # render Kaggle replay JSON to HTML
│   ├── decode_episode.py  # replay JSON → per-step CSV
│   └── _run_episode.py    # internal subprocess helper
├── experiments/
│   └── expNNN/
│       ├── agent.py       # frozen snapshot for this experiment
│       ├── config.yaml    # hyperparams + tournament setup
│       ├── tournament_log.csv  # round-robin results that bootstrapped its rank
│       └── notes.md       # what worked / what didn't / next steps
├── elo.json               # ledger (gitignored — regenerable)
└── tournament_log.csv     # most-recent run output (gitignored)
```

## Tools

### `tools.tournament` — round-robin runner

CLI (also see `make tournament`):

```bash
python -m tools.tournament \
    --agents experiments/exp001/agent.py random starter \
    --episodes 3 --seeds 1,2,3 \
    --output tournament_log.csv
```

For every (left, right, seed) combination it spawns a fresh subprocess and runs
exactly one episode. Subprocesses are isolated for memory safety: a leak,
infinite loop, or segfault in one episode never poisons the rest.

Each episode appends one row with these columns:

| column                 | meaning                                             |
| ---------------------- | --------------------------------------------------- |
| `timestamp`            | ISO-8601 UTC                                        |
| `seed`                 | env seed used                                       |
| `agent_left_path`      | normalized name (repo-relative path or `random` etc.) |
| `agent_right_path`     | same, for player 1                                  |
| `agent_left_reward`    | +1 / −1 / 0                                         |
| `agent_right_reward`   | +1 / −1 / 0                                         |
| `step_count`           | total env steps                                     |
| `episode_duration_sec` | wall-clock seconds                                  |
| `status_left`          | `DONE` / `TIMEOUT` / `ERROR` / `INVALID`            |
| `status_right`         | same                                                |
| `error`                | populated only when subprocess crashed              |

Built-in opponent names (`random`, `starter`) are passed through verbatim;
anything else is treated as a path to a Python agent file.

Per-episode timeout: 600 s. Tournament rows with non-`DONE` statuses are
skipped by `tools.elo update` so the ELO ledger never gets corrupted by a
crash.

### `tools.elo` — TrueSkill ledger

```bash
python -m tools.elo update --from tournament_log.csv   # apply outcomes
python -m tools.elo show                               # print top 20
python -m tools.elo reset                              # delete ledger (with confirm)
```

The ledger is a single JSON file (`elo.json` at repo root by default):

```json
{
  "experiments/exp001/agent.py": {"mu": 33.013, "sigma": 1.964, "n_games": 36},
  "starter": {"mu": 31.921, "sigma": 1.924, "n_games": 36},
  "random":  {"mu": 19.788, "sigma": 3.246, "n_games": 36}
}
```

We use **TrueSkill** (Microsoft) under the hood, not classical Elo. `mu` is the
mean skill estimate, `sigma` is the uncertainty. The "rank" column shown by
`elo show` is `mu - 3*sigma` — the conservative "skill we're ~99% sure they
exceed" number, which is the standard TrueSkill leaderboard metric.

Reading the table:

- New agents start at `mu=25.000, sigma=8.333` (TrueSkill defaults).
- After enough games, `sigma` shrinks: more games → tighter rank estimate.
- Ties in real reward (`agent_left_reward == agent_right_reward`) are passed to
  TrueSkill as draws, which barely move `mu` for either side.
- Crashes / timeouts (rows with `status != DONE`) are skipped, never counted as
  losses.

### `tools.decode_episode` — replay → CSV

```bash
python -m tools.decode_episode \
    --json data/replays/episode-76156402-replay.json \
    --output outputs/episode_76156402.csv
```

Or via Make:

```bash
make decode EP_ID=episode-76156402-replay
```

Output columns: `step, player, ships_total, planets_owned, fleets_count,
biggest_fleet, ships_in_flight`. Useful for quick post-mortems in pandas /
notebooks.

### `tools.replay_viewer` — replay → HTML

```bash
python -m tools.replay_viewer \
    --json data/replays/episode-76156402-replay.json \
    --output outputs/replays/episode-76156402.html
```

Reconstructs the env, plays back the steps, and writes the standalone HTML
viewer that Kaggle's web UI uses.

## Experiment dir convention

Use one directory per experiment under `experiments/expNNN/`. The `make exp
NAME=expNNN` target seeds it with a copy of the current `src/orbit_wars/agent.py`.

Required files:

- `agent.py` — frozen, byte-identical with what was tested
- `config.yaml` — hyperparams, the agent description, the Kaggle submission ID
  if shipped
- `notes.md` — short retrospective: approach / what worked / what didn't / next
- `tournament_log.csv` — the actual round-robin run that bootstrapped this
  experiment's ELO entry

We treat each `experiments/expNNN/` dir as **immutable after submission**. If
you want to tweak the hyperparams, start `expNNN+1` instead of editing in
place. The ELO ledger then carries the lineage automatically.

## Walk-through: exp001

`experiments/exp001/` is the retroactive snapshot of the very first agent
shipped to Kaggle (commit `9ea65e9`, submission ID `52478880`).

```bash
$ cat experiments/exp001/notes.md           # read the post-mortem
$ make rank                                 # show the bootstrapped ELO ledger
agent                             mu    sigma     rank     n
---------------------------  -------  -------  -------  ----
experiments/exp001/agent.py   33.013    1.964   27.122    36
starter                       31.921    1.924   26.148    36
random                        19.788    3.246   10.051    36
```

How that ledger was built:

```bash
make tournament TOURN_AGENTS="experiments/exp001/agent.py random starter" \
                TOURN_EPISODES=3 TOURN_SEEDS=1,2,3
# 54 episodes (6 pairings × 3 seeds × 3 eps), rows go to
# experiments/exp001/tournament_log.csv
make rank
```

To start a follow-up experiment:

```bash
make exp NAME=exp002
# … edit experiments/exp002/agent.py …
make tournament TOURN_AGENTS="experiments/exp002/agent.py experiments/exp001/agent.py random starter" \
                TOURN_EPISODES=5 TOURN_SEEDS=1,2,3
make rank
```

If exp002 sits at the top of `make rank` with reasonable `n_games`, copy it
back to `src/orbit_wars/agent.py` and submit with `make submit M="exp002: …"`.

## Operational notes

- **Reset the ledger** when you've changed pairings drastically (different
  agent names) or want a clean comparison: `python -m tools.elo reset`. The
  CSVs are the source of truth — `update --from <csv>` rebuilds the ledger
  deterministically.
- **Timeouts:** 600 s per episode is generous. If you start hitting it, look
  at the agent first (likely an O(N²) loop in fleet planning).
- **CI:** the verification flow at the bottom of `tools/tournament.py`'s
  module docstring is the smallest run that exercises every code path
  (3 agents × 2 seeds × 2 episodes = 24 rows).
