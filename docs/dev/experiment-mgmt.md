# Experiment Management

このドキュメントはローカルでの agent 改善ループを説明する:

> ローカルで N agent をぶつけ → ELO で順位付け → 勝てば Kaggle に提出

全コマンドはトップレベルの `Makefile` に組み込まれている。

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

## ファイルレイアウト

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

## ツール

### `tools.tournament` — round-robin runner

CLI (`make tournament` も参照):

```bash
python -m tools.tournament \
    --agents experiments/exp001/agent.py random starter \
    --episodes 3 --seeds 1,2,3 \
    --output tournament_log.csv
```

各 (left, right, seed) の組み合わせについて新しい subprocess を起動し、ちょうど 1 episode 実行する。Subprocess は memory 安全性のために隔離される: 1 episode 内のリーク、無限ループ、segfault は他の episode を汚染しない。

各 episode は以下のカラムを持つ 1 行を append する:

| カラム                 | 意味                                                   |
| ---------------------- | --------------------------------------------------- |
| `timestamp`            | ISO-8601 UTC                                        |
| `seed`                 | 使用された env seed                                       |
| `agent_left_path`      | 正規化された名前 (リポジトリ相対パスまたは `random` 等) |
| `agent_right_path`     | player 1 用、同様                                  |
| `agent_left_reward`    | +1 / −1 / 0                                         |
| `agent_right_reward`   | +1 / −1 / 0                                         |
| `step_count`           | env step の総数                                     |
| `episode_duration_sec` | 壁時計秒                                     |
| `status_left`          | `DONE` / `TIMEOUT` / `ERROR` / `INVALID`            |
| `status_right`         | 同様                                                |
| `error`                | subprocess がクラッシュした時のみ埋まる              |

組み込みの対戦相手名 (`random`, `starter`) は verbatim で渡される。それ以外は Python agent ファイルへのパスとして扱われる。

Episode あたりのタイムアウト: 600 s。`DONE` 以外のステータスを持つ tournament 行は `tools.elo update` でスキップされ、ELO ledger がクラッシュで破損することはない。

### `tools.elo` — TrueSkill ledger

```bash
python -m tools.elo update --from tournament_log.csv   # apply outcomes
python -m tools.elo show                               # print top 20
python -m tools.elo reset                              # delete ledger (with confirm)
```

ledger は単一の JSON ファイル (デフォルトでリポジトリルートの `elo.json`):

```json
{
  "experiments/exp001/agent.py": {"mu": 33.013, "sigma": 1.964, "n_games": 36},
  "starter": {"mu": 31.921, "sigma": 1.924, "n_games": 36},
  "random":  {"mu": 19.788, "sigma": 3.246, "n_games": 36}
}
```

裏では古典的な Elo ではなく **TrueSkill** (Microsoft) を使用している。`mu` は技量の平均推定値、`sigma` は不確実性。`elo show` が表示する「rank」カラムは `mu - 3*sigma` — 「99% 確実に超える技量」という保守的な数字で、TrueSkill リーダーボードの標準指標。

表の読み方:

- 新しい agent は `mu=25.000, sigma=8.333` (TrueSkill デフォルト) で開始。
- 十分な対戦数の後、`sigma` は縮む: 対戦数が増えるほど rank 推定が引き締まる。
- 実 reward の引き分け (`agent_left_reward == agent_right_reward`) は draw として TrueSkill に渡され、両者の `mu` をほとんど動かさない。
- クラッシュ / タイムアウト (`status != DONE` の行) はスキップされ、敗北としてカウントされない。

### `tools.decode_episode` — replay → CSV

```bash
python -m tools.decode_episode \
    --json data/replays/episode-76156402-replay.json \
    --output outputs/episode_76156402.csv
```

Make 経由の場合:

```bash
make decode EP_ID=episode-76156402-replay
```

出力カラム: `step, player, ships_total, planets_owned, fleets_count, biggest_fleet, ships_in_flight`。pandas / notebook での簡単な事後分析に有用。

### `tools.replay_viewer` — replay → HTML

```bash
python -m tools.replay_viewer \
    --json data/replays/episode-76156402-replay.json \
    --output outputs/replays/episode-76156402.html
```

env を再構築し、step を再生し、Kaggle の Web UI が使うのと同じスタンドアロン HTML viewer を出力する。

## 実験ディレクトリの規約

実験ごとに 1 ディレクトリを `experiments/expNNN/` 配下に作る。`make exp NAME=expNNN` ターゲットは現在の `src/orbit_wars/agent.py` のコピーで初期化する。

必須ファイル:

- `agent.py` — テストされたものとバイト単位で同一の凍結版
- `config.yaml` — ハイパーパラメータ、agent の説明、出荷した場合の Kaggle submission ID
- `notes.md` — 短い振り返り: アプローチ / うまくいったこと / うまくいかなかったこと / 次
- `tournament_log.csv` — この実験の ELO エントリを bootstrap した実際の round-robin 実行

各 `experiments/expNNN/` ディレクトリは **submission 後は immutable** として扱う。ハイパーパラメータを微調整したい場合は、in-place で編集せず `expNNN+1` を始める。ELO ledger が自動的に系譜を引き継ぐ。

## ウォークスルー: exp001

`experiments/exp001/` は Kaggle に最初に出荷した agent (commit `9ea65e9`、submission ID `52478880`) のレトロアクティブなスナップショット。

```bash
$ cat experiments/exp001/notes.md           # read the post-mortem
$ make rank                                 # show the bootstrapped ELO ledger
agent                             mu    sigma     rank     n
---------------------------  -------  -------  -------  ----
experiments/exp001/agent.py   33.013    1.964   27.122    36
starter                       31.921    1.924   26.148    36
random                        19.788    3.246   10.051    36
```

その ledger がどう構築されたか:

```bash
make tournament TOURN_AGENTS="experiments/exp001/agent.py random starter" \
                TOURN_EPISODES=3 TOURN_SEEDS=1,2,3
# 54 episodes (6 pairings × 3 seeds × 3 eps), rows go to
# experiments/exp001/tournament_log.csv
make rank
```

フォローアップ実験を始めるには:

```bash
make exp NAME=exp002
# … edit experiments/exp002/agent.py …
make tournament TOURN_AGENTS="experiments/exp002/agent.py experiments/exp001/agent.py random starter" \
                TOURN_EPISODES=5 TOURN_SEEDS=1,2,3
make rank
```

exp002 が `make rank` のトップに合理的な `n_games` で位置するなら、`src/orbit_wars/agent.py` にコピーバックし、`make submit M="exp002: …"` で submit する。

## 運用上の注意

- **ledger をリセットする** のは、ペアリングを大幅に変更した (異なる agent 名) か、クリーンな比較が欲しいとき: `python -m tools.elo reset`。CSV が真実の源なので、`update --from <csv>` で ledger を決定的に再構築できる。
- **タイムアウト:** episode あたり 600 s は寛容。これに当たり始めたら、まず agent を見る (おそらく fleet planning の O(N²) ループ)。
- **CI:** `tools/tournament.py` のモジュール docstring 末尾の検証フローは、全コードパスを通す最小実行 (3 agents × 2 seeds × 2 episodes = 24 行)。
