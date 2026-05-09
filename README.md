# orbit-wars

Kaggle simulation/agent competition: <https://www.kaggle.com/c/orbit-wars>

## Setup

```bash
make install      # uv sync (kagglib + kaggle-environments)
make download     # data/raw に starter files
```

## Develop your agent

`src/orbit_wars/agent.py` is your submission. Edit `agent()` with your strategy.

## Local play loop

```bash
make play                                # me vs random (3 episodes)
make play-self                           # me vs me (sanity / symmetry check)
uv run python -m orbit_wars.play --opponent random --episodes 20 --render
```

## Submit

```bash
make submit M="exp001 nearest sniper"             # single-file
make submit-tar M="exp002 with model weights"     # multi-file tar.gz
make submissions                                  # list past submissions
make lb                                           # leaderboard top 50
```

The `make submit` target embeds the git short-SHA into the message and creates
a git tag — so you can always rewind to the exact code that played any episode.

## Inspect episodes

```bash
make submissions                                  # find SUB_ID
make episodes SUB_ID=1234567                      # list episodes for that submission
make replay  EP_ID=89012345                       # download replay JSON
make logs    EP_ID=89012345 AGENT_IDX=0           # download your agent's stdout/stderr
```

## Strategy log

| exp | description | LB | notes |
|---|---|---|---|
| 001 | starter (nearest sniper) | - | - |

## メモ

(コンペ固有の気付き — ルール、強い対戦相手の傾向、リプレイから見えた失敗モード等)
