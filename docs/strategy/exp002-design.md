# exp002 Design — Phase 2 Synthesis from 4 Parallel Research Tracks

> **Status**: Phase 2 synthesis (= research summary + 3 structurally distinct candidates).
> **判断は開発者**。中央は推奨案を出さない (CLAUDE.md 中立指示原則)。
> **実装は次プラン**で。
> **Date**: 2026-05-09

---

## 1. Context

`exp001` (nearest-sniper, commit `9ea65e9`、submission ID 52478880) はスモークテストとして submit され、TrueSkill 内部 ranking で `starter` を僅差で上回るが
(`experiments/exp001/tournament_log.csv` 54-game の集計より μ=33.01 > starter μ=31.92)、
**LB 上では Reexel 名義で rank ≈ 750 / 2370 (TrackB lb_snapshot より)**、Top 10 ($5k 圏内) には程遠い。

公開 notebook (`konbu17/v1_sniper-vs-others`) で **「sniper 系統は hybrid rule-base 相手に 0/16 全敗」が公開** されており (`docs/research/lb-observations.dense.md` Public leaks 節)、
exp001 をマイナーチューンしても上位を抜けないことが構造的に確定している。

---

## 2. Phase 1 4 トラック統合所見

### 2.1 TrackB (LB 観察) からの致命的所見

- **チーム名**: Reexel (replay metadata 由来、`docs/research/lb-observations.dense.md`)
- **公開ランク**: ~750/2370、score 326-366、7 ranked games で 2W/5L
- **Top 1/2 (flg, bowwowforeach 両 1650.9)** は **adaptive bot**: 対戦相手によって発射分布を切替 (1 対戦は 78 大艦隊、別対戦は 1349 小艦隊)
- **Top tier の launch サイズ中央値 25-40**, Isaiah の "kill stack" 最大 **986 隻**
- **我々の `garrison+1+MARGIN=11 隻` poke** では garrison ≥ 30 の惑星すら割れない (`agent.py:RESERVE/MAX_FRACTION/MARGIN`)
- **5 つの致命失敗モード** (詳細は `lb-observations.dense.md` § failure-modes):
  1. Capacity gap (主要因)
  2. 500-step starvation
  3. Swarm-overrun
  4. No sun-rejection (forbidden cone 無視)
  5. No fleet aggregation (速度ボーナス未利用)
- **公開 leak からの戦略ヒント**:
  - **Pilkwang**: **10-mission strategy** を公開 (`lb-observations.dense.md` § public-leaks)
  - **Rahulchauhan**: MCTS weights 公開、`production weight = 46.0`
  - **Djenkivanov**: middle-tier scoring formula

### 2.2 TrackC (first-principles) からの数理的 invariant

- **Fleet speed 最適**: `speed = 1.0 + (max_speed - 1.0) * (log(ships) / log(1000))^1.5` の凸性により、**N 隻を 1 つにまとめる方が常に N/2 隻×2 より速い** (engine `orbit_wars.py:577-578`)。これは TrackB 失敗モード #5 (fleet aggregation) と一致
- **Lead-shot 閉形式**: orbiting target に対する fire_angle は導出済 (`first-principles.dense.md` §2)
- **Forbidden sun cone**: (75,25) home 起点で half-angle ~16.43°、total 32.86° (失敗モード #4 と一致)
- **彗星 RNG seed scrubbed** (`orbit_wars.py:359-363`) → **事前予測不可、ただし spawn 後即パス observable** (= reactive 戦略しか取れない)
- **Combat tie = 相互全滅、garrison untouched** (`orbit_wars.py:659-661`)
- **Score に in-flight 艦数も含む** (`orbit_wars.py:707-708`) → 終盤の発射が無駄にならない
- **Prod ≥ 3 の惑星は break-even 33 turn 以下で常に ROI > 1**、prod=1 の遠方は marginal
- **Engine quirks**: `planet[2]=X, planet[3]=Y` の保存順注意、validation で **7 種の不正手が silent drop** されるためデバッグ困難

### 2.3 TrackA (過去類似コンペ) からの戦略的 prior

- **2024 以前は heuristic 最強**: Halite II~IV、Lux S1/S2 で純 RL は heuristic に勝てなかった (Lux S2 1st ry-andy = pure heuristic で NeurIPS 提供 1B IL frame を倒した)
- **2024+ で RL/IL が並ぶ**: Lux S3 Frog Parade (PPO + SE-ResNet)、Halite IV ttvand 1st (hybrid)
- **「優勝者の段階的レシピ」** (= phased approach):
  ```
  heuristic baseline → NN opponent predictor → behavioral cloning from replays → PPO/A2C finetune
  ```
  各段階の成果が次段階の opponent / training data になる
- **Mandatory 4 tricks** (どの comp も上位がやってる):
  - **4-fold symmetry TTA** (orbit-wars の 4-fold (50,50) 対称と完全一致 — 即適用可)
  - **Action masking** (NN 出力の不正手を 0 確率に — TrackC の "7 種 silent drop" 一覧と一致)
  - **Ship-set pruning by interaction radius** (action space を近傍に limit)
  - **シミュレータ Rust リライト** で ~10× throughput (RL 訓練の bottleneck 解消、orbit-wars でも該当)
- **Halite II は構造的に最も近い** (2D continuous fleet conquest): reCurs3 (1st) / FakePsyho (2nd) / shummie (3rd) はいずれも heuristic + 高度な collision avoidance + role-score ranking

### 2.4 TrackD (実験管理 infra) — 検証済の改良ループ

- `make tournament && make rank` で **N agent vs N agent の TrueSkill 競技 → ランク確定** が回る (`docs/dev/experiment-mgmt.md`)
- **exp001 baseline は 27.12 (sniper) > 26.15 (starter) > 10.05 (random) — 改良の "床" は正確に測定済**
- exp002 開発時の **必須前提**: local tournament で exp001 を上回ってから submit (= submit limit 5/day を浪費しない)

---

## 3. exp002 候補 — 構造原理が異なる 3 案

各候補は **異なるパラダイム**。同じ heuristic でも param tuning するだけは「バリエーション」なので除外。

### 候補 1: Mission-based Heuristic v2

**着想根拠**:
- Halite II top-3 (全員 heuristic、`past-comps.dense.md` §halite_2)
- Lux S2 1st ry-andy (heuristic で IL を倒した)
- Pilkwang 公開 notebook の 10-mission アーキテクチャ
- TrackC の fleet aggregation / sun-cone / lead-shot 公式

**構造**:
- agent 内部に **mission 抽象** を導入: `CaptureMission`, `DefenseMission`, `CometGrabMission`, `AggregationMission`, `RetreatMission`
- 毎 turn で各 mission の **発火条件** + **score** を計算、greedy or weighted で実行集合を決定
- 主要 logic:
  - **Sun-rejection** (forbidden cone を発射前に check)
  - **Fleet aggregation** (近接する自分の小艦隊を合流させて速度ボーナス取る)
  - **Garrison-aware capture** (target の garrison を見て適切な ship 数を派遣、capacity gap 解消)
  - **Comet reactive grab** (spawn step 直後に即占領計画)
  - **Opponent modeling lite** (相手の直近 N turn の launch サイズ平均を監視、passive/aggressive 判定)

**Phase 1 知見の活用**:
- TrackB 失敗モード 5 つすべてを直接対応
- TrackC の fleet speed / lead-shot / forbidden cone を full 利用
- TrackA の 4-fold TTA (推論時の対称変換) を opt-in 適用

**コスト & 期待**:
- 開発: **1-3 日** (純 Python、既存 infra で round-trip 可能)
- 期待 ELO: **+400 〜 +600** (1000-1300 帯狙い)
- リスク: top tier 1650 までは届かない可能性

---

### 候補 2: Behavioral Cloning + Opp-Predictor (IL pipeline)

**着想根拠**:
- Kore 2022 khanhvu207 (Transformer IL on 200M tuples、`past-comps.dense.md` §kore_2022`)
- Halite IV ttvand 1st = hybrid (rule + IL)
- Lux S3 Frog Parade (PPO + SE-ResNet、ただし IL pretrain あり)
- 我々が既に保有: **17 本の replay** (`data/replays/`)

**構造**:
- 17 本 + worker B の sweeping で追加収集する replay (60+ probe 可) から `(state, action)` ペアを抽出
- 軽量 policy network: small CNN or Transformer
  - 入力: planet/fleet をラスタライズ (TrackA の Lux S3 で SE-ResNet のサイズ参考に 64x64 grid)
  - 出力: action distribution (per planet × angle bins × ship fractions)
- **Action masking** で不正手 (TrackC §7 で列挙された 7 クラス) を 0 確率に
- **4-fold symmetry TTA** を inference で適用 (TrackC の幾何 + TrackA の標準 trick)
- ONNX or torchscript で submission-friendly な単一 .pt ファイルに

**Phase 1 知見の活用**:
- TrackB の 17 replay + 公開 episode (sweeping 経由) が直接訓練データ
- TrackA の IL レシピ完全準拠
- TrackC の action mask 仕様

**コスト & 期待**:
- 開発: **3-7 日** (data pipeline + NN 訓練 + serialization)
- compute: RTX 3090 で数時間〜1 日
- 期待 ELO: **+400 〜 +700** (中-高、訓練 data 質に強く依存)
- リスク: 17 episode はサンプル数として薄い、過学習。data 拡張 (sweeping を automate) が成否を分ける

---

### 候補 3: Lightweight Self-Play RL (PPO + small CNN)

**着想根拠**:
- Lux S1 Toad Brigade (IMPALA + UPGO + TD-λ、`past-comps.dense.md` §lux_s1`)
- Lux S3 Frog Parade (PPO + SE-ResNet)
- microRTS 2023 paper (BC → PPO finetune の段階訓練)

**構造**:
- `kaggle_environments` を gymnasium 風 wrapper で包む (multiprocessing で N envs 並列)
- State encoding: 64x64 grid (planets, fleets, comets を channel に分離) + global features (player ID, step, ang_vel)
- Policy: small SE-ResNet (Lux S3 sizing を縮小)
- PPO training: **self-play curriculum**
  - Stage 1: vs random (~ 1M steps)
  - Stage 2: vs starter
  - Stage 3: vs exp001 sniper
  - Stage 4: vs current self (PFSP)
- Reward: +1/-1 + intermediate shape (ship-share gain per turn)
- **Action masking** + **forbidden-cone mask** (TrackC §2.2 の cone を直接 mask に焼く)
- 提出は torchscript で重み + 推論 stub

**Phase 1 知見の活用**:
- TrackA の段階訓練レシピ完全準拠
- TrackC の action mask 仕様 + forbidden cone
- TrackD の tournament infra を **学習 evaluation** にそのまま使える

**コスト & 期待**:
- 開発: **1-2 週間** (env wrapper + net + 学習 + 安定化)
- compute: RTX 3090 で 1-2 週間連続訓練
- 期待 ELO: **+400 〜 +700+** (top tier 到達可能性あり)
- リスク: 学習が不安定だと数日無駄、Python シミュレータが bottleneck (TrackA "Rust rewrite ~10×" の警告)

---

## 4. 評価軸 (中立、開発者判断用)

| 軸 | 候補 1 (Mission-based Heuristic) | 候補 2 (BC + IL) | 候補 3 (Self-play RL) |
|---|---|---|---|
| **実現可能性** | 高 (純 Python、即 round-trip) | 中 (data 17 本はギリギリ) | 中 (大型訓練、安定性課題) |
| **開発期間** | 1-3 日 | 3-7 日 | 1-2 週間 |
| **必要 compute** | ローカル CPU のみ | RTX 3090 数時間 | RTX 3090 1-2 週連続 |
| **期待 ELO 上昇** | +400-600 | +400-700 | +400-700+ |
| **メダル (Top 10)** 確率 | 低 | 中 | 中-高 (compute 次第) |
| **Phase 1 トラック活用度** | TrackB全 + TrackC全 + TrackA一部 | TrackB全 + TrackA全 + TrackC一部 | TrackA全 + TrackC全 + TrackB一部 |
| **失敗時の learning** | 確実な lift、損失なし | data 不足なら 0 進歩 | 学習不安定で数日無駄リスク |
| **次段階への接続** | 候補 2/3 の opponent に再利用 | 候補 3 の pretrain 重みに再利用 | 最終形 |

---

## 5. 段階的アプローチ案 (TrackA "phased recipe" を採用するなら)

```
Week 1: 候補 1 (Mission-based Heuristic v2)         → ELO 1000-1300 目標
   ↓ baseline 確立 (= 候補 2 の opponent + 候補 3 の reward shaping reference)
Week 2: 候補 2 (BC, replay data + 候補 1 を opp として data 自家生成)  → ELO 1300-1500
   ↓ pretrained 重み獲得
Week 3-4: 候補 3 (PPO finetune from 候補 2 weights)  → ELO 1500-1700+
```

Halite IV 1st (ttvand) は実際にこの段階を踏んだ。Lux S3 Frog Parade も IL pretrain → PPO で top。

ただし **段階を全て踏まずに途中で止める** のも合理的:
- 「短期で順位上昇」→ 候補 1 のみで停止
- 「メダル必須 / 時間ある」→ 候補 3 ベース、Week 1-3 で段階移行
- 「学びたい / 失敗してもいい」→ 候補 2 のみ (data 質を見極める)

---

## 6. 中立判断のために (中央は推奨しない)

| もし開発者が ... | 候補 |
|---|---|
| **時間限られる、確実な順位上昇が欲しい** | 候補 1 |
| **メダル取りに本気、時間あり、3090 を使い倒せる** | 候補 3 ベース、段階的 |
| **新手法学習が目的、勝敗より試したい** | 候補 2 |
| **判断保留、まず 1 だけ試してから決める** | 候補 1 → 結果見て候補 2/3 を選ぶ |

---

## 7. Out of scope (このプランではやらない)

- 候補のうちどれを実装するかの**選択** (開発者の判断、次プランで `/plan exp002` を起動する際に決定)
- 候補 2/3 の場合の RL 訓練ハイパーパラメタ詳細チューニング
- LB top 1 (= flg / bowwowforeach の 1650.9) を抜く戦略 (Top 10 圏 = 1500+ を目標とする)
- 別モデルレビュー (Codex gate) — 必要なら別プラン

---

## 8. 参照ファイル一覧 (Phase 1 deliverable map)

### Research (Track A)
- `docs/research/past-comps.dense.md` (4283 word, 9 comps)
- `docs/research/past-comps.kids.md` (2672 word)
- `docs/research/past-comps.references.json`

### Observation (Track B)
- `docs/research/lb-observations.dense.md` (4001 word)
- `docs/research/lb-observations.kids.md` (2732 word)
- `docs/research/lb_snapshot_2026-05-09.csv` (LB top 200)
- `data/replays/episode-7615*.json` (17 本 + `_analysis.json`)

### Strategy (Track C)
- `docs/strategy/first-principles.dense.md` (5588 word)
- `docs/strategy/first-principles.kids.md` (3305 word)
- `tools/notebooks/01_physics_sandbox.ipynb` (837 KB、実行済 figure 入り)

### Infrastructure (Track D)
- `tools/{tournament,elo,replay_viewer,decode_episode,_run_episode}.py`
- `tools/__init__.py`
- `experiments/exp001/{agent.py, config.yaml, tournament_log.csv (54 games), notes.md}`
- `Makefile` (append: `tournament / rank / exp / decode`)
- `docs/dev/experiment-mgmt.md`

### Synthesis (中央)
- `docs/strategy/exp002-design.md` (= this file)

---

## 9. 次プランへの引き継ぎ事項

開発者は次のセッションで **候補 1/2/3 のいずれか (or その組み合わせ) を選択** し、`/plan exp002` で実装プランを立てる。
その際:
- このファイル (`exp002-design.md`) を Read で全文読み直す
- 該当候補の "Phase 1 知見の活用" 列に書かれた dense.md セクションを Read
- `experiments/exp001/notes.md` を読んで sniper の今の挙動を再確認
- `make tournament` の使い方を `docs/dev/experiment-mgmt.md` で確認

実装中に新しく見えてくる事 (公開 notebook の追加情報、新規 LB 観察等) は **新しい research dense.md** として追記し、本ファイルは synthesis スナップショットとして固定する。
