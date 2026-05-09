# 過去の Kaggle シミュレーション/エージェント系コンペ — orbit-wars 向け密度高めの統合分析

> Track A の調査成果物。orbit-wars コンペ (Google スポンサー、$50k、kaggle_environments、+1/-1 二値報酬、2370 チーム、締切 2026-06-23) 向けに 2026-05-09 にまとめた。
> すべての主張は `file:line` (ローカル) または完全な URL (Web) で出典を明示。直近のコンペほど重みを高めている。Halite II は **構造的に最も類似した** 過去コンペとして特筆。

---

## TL;DR マトリクス

| コンペ | 年 | チーム数 | 優勝手法 | 計算資源 | orbit-wars との構造的一致度 |
|---|---|---|---|---|---|
| Lux AI S3 | 2024-25 | ~600 | Deep RL (PPO + SE-ResNet) | RTX 3090、約 8 日、3 億フレーム | 高 (24x24、部分観測、sap アクション ≈ orbit-wars の戦闘) |
| Lux AI S2 | 2023 | 646 | **純粋な heuristic Python** (NeurIPS が IL 用に 10 億フレーム提供したにもかかわらず) | なし | 中 |
| Kore 2022 | 2022 | ~1000 | **模倣学習 (Imitation learning)** (2 億組のタプルに対する自己回帰 Transformer) | 2x A100 80GB | 高 (艦隊、+1/-1) |
| Halite II | 2017-18 | 6000 | **Heuristic** (状態機械 + シミュレーション精緻化) | 単一 CPU スレッド | **最大** — 2D 連続空間の艦隊乱戦 |
| Halite IV | 2020 | 1143 | Heuristic + NN による衝突補助 (1 位) | 控えめ | 中〜高 |
| Halite III | 2018-19 | ~4000 | Heuristic (船ごとに Dijkstra) | 控えめ | 中 |
| Lux AI S1 | 2021 | 1178 | Deep RL (IMPALA+UPGO+TD(λ)) | 個人 PC dual-GPU | 中 |
| Hungry Geese | 2021 | 875 | DRL self-play (HandyRL) + 終盤に MCTS を後付け | 分散 | 低 |
| microRTS 2023 | 2023 | n/a (IEEE) | BC で bootstrap → PPO finetune | 70-142 GPU 日 | 中 |

**要点となる横断的観察:** 2023 年までの Kaggle シミュレーション系リーダーボードは、ML の代替手法が存在していても、ほぼ常に **入念にチューニングされた heuristic** が優勝していた。例外は (a) 明示的な IL データが提供された場合 (Kore 2022、Lux S2 NeurIPS トラック)、および (b) 2024 年の Lux AI S3 で部分観測性と best-of-5 シリーズ越しのメタ学習が heuristic 支配を打ち破り DRL を強制したケース。orbit-wars は **完全観測かつ対称的** で 2 ヶ月の期間がある — 歴史的にはこれは heuristic 領域だが、分野は成熟しており、ハイブリッド (heuristic コア + 小型の NN 相手予測器または BC ポリシー) が今や勝ちパターンの最頻値となっている。

---

## 1. Lux AI Season 3 — NeurIPS 2024 (最も新しく、最も示唆に富む)

- コンペページ: https://www.kaggle.com/competitions/lux-ai-season-3
- 論文 (主催者 Tao & Kumar): https://openreview.net/forum?id=7t8kWYbOcj
- エンジン repo: https://github.com/Lux-AI-Challenge/Lux-Design-S3

**1 位 — Frog Parade (Isaiah Pressman):**

- Writeup: https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md
- Repo: https://github.com/IsaiahPressman/kaggle-lux-2024
- 手法: clipping 付き PPO。writeup より ([source](https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md)): *"Deep reinforcement learning aims to answer this question by parameterizing a policy using a deep neural network."*
- アーキテクチャ: 8 ブロック 3×3 SE-ResNet、隠れ次元 256、約 1000 万パラメータ。dual actor head (10 種の移動アクション + 空間的 sap-target head)、10 フレーム履歴スタック、約 80 のグローバル + 約 100 の空間特徴量。
- 計算資源: AMD Ryzen 9950X 16c、64GB RAM、RTX 3090 + RTX 2070 Super。カスタム Rust シミュレータのおかげで **110k env step/s**。Rust 実装は公式 Python エンジンに対して TDD 検証済み。学習スループット **430 step/s**、合計 **約 8 日で 3 億ゲームステップ**。

非自明なテクニック (Lux S3 は部分観測かつマッチごとにルールパラメータがランダム化されていた → 効いたのはこれらの推論系トリック):

1. **隠れパラメータ推論** — エネルギーフィールド設定、小惑星/星雲の動き、ポイントタイル位置を end-to-end で学習させるのではなく、観測の差分から *推論* する。引用: *"all of this initially-hidden information can be deduced by carefully observing how the observations change."*
2. **対称性反映の特徴エンジニアリング** — マップの対角対称性を活用。テスト時拡張で対角反射 + 180° 回転にわたって予測を平均化。
3. **カスタム Rust シミュレータ** — RL アプローチのボトルネックは env スループット。Rust 再実装で約 10× 高速化。公式 Python エンジンに対して TDD でテスト。
4. **選択的アクションマスキング** — ただし著者は振り返って過剰に制限的だった可能性を指摘している。
5. **事前計算済み構成からのエネルギーフィールドキャッシュ** — 可能なエネルギーフィールドは有限個しかないので、全部事前計算してルックアップする (再計算しない)。

**orbit-wars への転用 (約 150 word):**
- orbit-wars は **完全観測** なので推論系トリックは適用不可。ただし対称性トリックは直接移植可能: orbit-wars は (50, 50) を中心とした 4 回回転対称性を持つ (エンジンソース `~/projects/kaggle/orbit-wars/.venv/.../orbit_wars.py`)。これをデータ拡張 (マッチあたり 4× の学習データ) とテスト時予測平均化の両方に使うべき。
- カスタム Rust シミュレータパターンが最高 ROI: env スループットは RL 学習可否を決める。orbit_wars 戦闘リゾルバの Rust 移植だけでも、家庭用 PC スケールで 8 日 × 110k step/s = 約 750 億フレームを開放する。
- SE-ResNet + dual actor head (移動 + 空間的ターゲット) は orbit-wars (艦隊移動 + 攻撃ターゲット) に 1:1 でマップする。
- 10 フレーム履歴は重要。なぜなら step 50/150/250/350/450 の comet スポーンは予測可能だが、それを把握するには時間的コンテキストが必要だから。

---

## 2. Lux AI Season 2 — NeurIPS 2023 (heuristic はまだ勝てるという教訓)

- コンペページ: https://www.kaggle.com/competitions/lux-ai-season-2
- 1 位 writeup (ry-andy): https://www.kaggle.com/competitions/lux-ai-season-2/writeups/ry-andy-1st-place-solution
- Repo: https://github.com/ryandy/Lux-S2-public

**手法:** 純粋 Python heuristic。最終順位: **646 チーム中 1 位** ([repo README](https://github.com/ryandy/Lux-S2-public))。

これは典型的な反例。NeurIPS 主催者は IL/RL アプローチを促すために **S1 の模倣学習用データを 10 億フレーム以上明示的に提供** したが、Kaggle のボットリーダーボードは手書き heuristic に勝たれた。IL/RL トラックは別スコア (NeurIPS スポンサーのサイドトラック) だったが、賞金が懸かるオープンリーダーボードは heuristic が制した。

**heuristic が勝った理由:** Kaggle リーダーボード (NeurIPS トラック 2 IL 評価とは違い) では、ボットは 60 秒の提出環境で厳しいステップごとの時間予算で動かなければならず、離散グリッドではドメインエキスパートが「明らかな」ルール (lichen を最大化する factory 配置、ice 採掘、防衛された power 移送) を、RL が収束するより速く符号化できる。

**orbit-wars への転用:** 同じ条件が当てはまる。orbit-wars は 2370 チームの 2 ヶ月コンペ。ML 学習を始める前に、強力な heuristic ベースライン (リソース収集 + 惑星捕獲 + 対称性活用) を Phase-1 成果物として用意するのが正しい。RL 学習パイプラインに先立って heuristic ベースラインを計画する。

---

## 3. Kore 2022 — Kaggle 上の模倣学習の典型例という教訓

- コンペページ: https://www.kaggle.com/competitions/kore-2022
- 1 位 writeup: https://www.kaggle.com/competitions/kore-2022/discussion/340035
- 1 位 repo: https://github.com/khanhvu207/kore2022

**手法:** リーダーボード上位 5 チームの提出から **2 億組の (obs, plan) タプルをスクレイピング** し、それを学習データとする自己回帰 Transformer。船プラン生成を機械翻訳の seq2seq として扱った。

**アーキテクチャ詳細 (writeup より):**
- 空間エンコーダ: 12 層 ResNet、residual ブロック間に GroupNorm、18 チャネルの船/カーゴテンソルを処理
- スカラーエンコーダ: (timestep、チームスコア、チームリソース等) に対する MLP
- 船プランエンコーダ: 256 次元の文字埋め込み + 位置埋め込みを bag-of-words スタイルで合算 (二段目 Transformer のコストを回避)
- デコーダ: 文字レベル自己回帰 Transformer ("N 10 W 5" = 「北に 10 歩、その後西に 5 歩」)。[CLS] トークンがアクション種別分類器ヘッドに供給される

**学習:** 2× A100 80GB、batch 64、20 epoch、AdamW lr=4e-3、cosine schedule (5% warmup)、勾配クリッピング 0.5、weight decay 0.01。重い正則化: 空間入力に対する **60% ランダムピクセル dropout**。

**非自明なテクニック:**

1. **船プランを文字シーケンスとしてトークン化** — 多段階移動プランを "N 10 W 5 SE 3" にすると問題が NMT と同型になり、何十年もの文献を活用できる。
2. ***他の* 船向けの bag-of-words プラン埋め込み** — 状態表現の Transformer の二乗コストを回避。
3. **60% 空間ピクセル dropout** — 特定の盤面構成を暗記するのを防ぐ極端な拡張。
4. **トップ 5 を IL ターゲットにする (トップ 1 だけでなく)** — スタイルの多様性を捕捉し、特定プレイヤーのクセに崩壊するのを防ぐ。
5. **アクション種別 [CLS] head** — プラントークンを生成する *前に* 種別 (LAUNCH/SPAWN 等) を予測し、自己回帰デコーダに構造的な事前情報を与える。

**orbit-wars への転用 (約 180 word):**
- orbit-wars のアクションはより単純 (艦隊ごとの移動先 + 船数配分) だが、同じ seq2seq フレーミングが当てはまる: 各艦隊の「プラン」をトークン列 (target_planet、num_ships、attack_or_dock) としてエンコードし、トップ N リプレイをスクレイピングして小型 Transformer を学習させる。
- 60% 空間 dropout は直接転用可能: orbit-wars は重い空間構造 (惑星、艦隊、comet) を持っており、正則化が盤面暗記を防ぐ。
- 2 億タプル規模は達成可能: 各 Kaggle リプレイから約 1000 ステップ × 艦隊タプルが取れる。トッププレイヤーから 20 万リプレイをスクレイピング (Kaggle の `meta-kaggle` BigQuery エクスポート経由) すればその規模に達する。トッププレイヤーの誰かが早期に強い heuristic を公開した場合、これが競争力あるボットへの *最も簡単な* 道となる。
- 重要な注意点: IL は強力なデモンストレータがリーダーボードに存在して初めて機能する。戦略を段階化: heuristic Phase-1 → トップリプレイをスクレイプ → BC Phase-2。

---

## 4. Halite II — 構造的に最も類似

これは orbit-wars のゲーム形態に最も近い過去コンペ: 2D 連続空間、ドック対象の惑星、攻撃範囲が重なる艦隊対艦隊の乱戦。**orbit-wars を実装するならこのセクションを最初に読むべき。**

- コンペページ: https://www.kaggle.com/competitions/halite-ii (Two Sigma 公式: https://www.twosigma.com/articles/halite-ii-concludes-winners-announced/)
- トップ 3 レビュー: https://lakesidethinks.com/post/2018/10/halite2-strategy.html

### 1 位 — reCurs3 (Ubisoft Montreal、Assassin's Creed 開発者)

- Writeup: https://recursive.cc/blog/halite-ii-post-mortem.html (注: ブログがたまに接続を拒否する。James Jones による Medium ミラー https://medium.com/aescru/halite-ii-strategies-of-a-top-player-88127b3b49e2 を参照)

二段階意思決定の状態機械型 AI:

1. **戦略パス** が役割を割当: 入植 / 防衛 / 攻撃
2. **戦術パス** が位置に対する hill-climbing を実行し、**19 種類の異なる敵応答パターン** に対してシミュレートして保守的な最良手を選ぶ

非自明なテクニック (これらが金):

1. **符号付き隣接カウントによる戦闘 or 逃走** — 各船について、半径内の (#近くの敵 − #近くの味方) を合計する。負 → 攻撃、正 → 逃走。*引用 (レビューを言い換え):* 各船の `nearby_friendly` と `nearby_enemy` ベクトルを保持することで安価に計算する。
2. **クーロン式 180° 逃走ベクトル** — 船が逃走を決めたら、走る方向は `−mean(nearby_enemy_positions)`。「他の負電荷から飛び去る負電荷の粒子のように」(https://medium.com/aescru/halite-ii-strategies-of-a-top-player-88127b3b49e2)。
3. **惑星優先度キュー** — 距離 < 75 の各惑星に対し、score = 3 × dock スポット数、距離に反比例。ドックスポットが 2 つしか空いていなくても、選んだ惑星に *利用可能な全船* を送って rush ダメージを吸収。
4. **相互作用半径による船セット剪定** — 各船について、`2*MAX_SPEED + WEAPON_RADIUS + 2*SHIP_RADIUS` 以内の船のみを考慮。この剪定により tick ごとの戦闘が O(n²) からほぼ O(n) になる。
5. **軌道衝突計算** — 時間関数としての最小距離 (基本物理) を使い、2 船の min-distance < 0.5 になる移動を中止。著者は標準 API では衝突回避が含まれていなかったため *標準 API を改変* する必要があった。
6. **Anti-rush** — 単純な距離閾値: 敵船が距離 X 以内にいる場合はドックもアンドックもしない。

### 2 位 — FakePsyho (OpenAI、ポーランドのパズル王者)

- Repo: https://github.com/FakePsyho/halite2

**ステートレスな評価関数設計。** 状態機械の代わりに、*すべて* の (船、アクション) 組合せをスコアリングし、グローバル貪欲割当を行う。

主要トリック:

1. **評価値のキャッシュ** — 関連する状態が変わったときだけ再計算。これが「全評価」アプローチを 1 秒/turn 予算で扱えるようにした要因。
2. **ターゲットあたりの船数を制限** — *"limiting how many ships can follow each enemy ship is a really cheap way of forcing your units to spread among different goals"* ([repo README](https://github.com/FakePsyho/halite2))。
3. **境界近接ペナルティ** — 退却中以外では端への移動を抑制。
4. **HP 基準の位置取り** — HP 低めの船は評価上、敵から遠ざける。
5. **攻撃範囲バッファによる釣り出し** — 退却中の船は `(ship_attack + max_speed) = 13` 単位の外側に移動し、再交戦前に敵に commit を強制。
6. **ドック距離による Anti-rush** — reCurs3 と同様。

### 3 位 — shummie (アクチュアリー、Allstate Chicago)

- Postmortem: https://shummie.github.io/Halite-2-Shummie/

行動駆動。**役割特化のナビゲーション関数** (dogfight / retreat / defense はそれぞれ独自の move-evaluator を持つ)。

独自トリック:

1. **Distractor 役割** — ドック中の敵船を harassment する専属の船。防衛を分散させる。
2. **不可侵協定 (NAP)** — 4 人対戦で *ゲーム内の隠れシグナル* を使って別プレイヤーと協調し、互いを攻撃しない。ペアになると上位 2 入賞が保証される (controversial。後に Two Sigma がパッチ)。
3. **Desertion メタ** — 1 船を隅に送り、*"command all ships to run away"* で対戦相手より長生きして 2 位を盗む。今や広く知られている。
4. **数的劣勢の検知** — 友軍に向かって退却し、再交戦前に *数的優位を作り出す*。

### orbit-wars への転用 (約 200 word)

Halite II は orbit-wars Phase-1 heuristic の **テンプレート**:

| Halite II の概念 | orbit-wars 対応物 |
|---|---|
| 隣接カウントによる戦闘 or 逃走 | 各相互作用で自軍艦隊サイズと敵艦隊を比較。orbit-wars の戦闘公式 `largest vs second-surplus annihilation` で期待結果を計算 |
| クーロン 180° 逃走 | 強い敵艦隊全体の平均から艦隊をまっすぐ離脱 |
| 惑星優先度キュー (3 pts/dock × 距離反比例) | garrison 利得 × 距離反比例で惑星捕獲優先度、`PLANET_CLEARANCE=7` で重み付け |
| 19 パターン敵応答シミュレーション | 上位 K 個の有力な敵手を列挙し、max-min 値のアクションを選択 |
| 相互作用半径による船セット剪定 | `1.0 + (max_speed-1.0) * (log(ships)/log(1000))^1.5` で艦隊ごとの実効半径を計算 |
| Anti-rush 距離閾値 | 敵艦隊が reach × 1.5 以内にあれば艦隊をアンドックしない |
| Distractor 役割 | 相手の最大惑星を harassment する小規模分離艦隊を送る |
| 4 回対称性活用 | orbit-wars は (50, 50) を中心に明示的な 4 回対称性を持つ。heuristic 手の鏡像化と ML データ拡張の両方に使う |

reCurs3 の二段階 (戦略的役割割当 → シミュレートされた敵応答に対する戦術的 hill-climbing) は orbit-wars にほぼそのままマップする。最初にこれを実装し、その上に下記セクション 11 に従って ML を重ねる。

---

## 5. Halite IV — 2020 (4 人グリッド。ハイブリッドが優勝)

- コンペページ: https://www.kaggle.com/c/halite

### 1 位 — ttvand (Tom Van de Wiele)

- Repo: https://github.com/ttvand/Halite (`Rule agents/` と `Deep Learning Agents/` の別フォルダ)
- ディスカッション: https://www.kaggle.com/c/halite/discussion/183312

ハイブリッド: ルールベースのコアに対し、相手手予測用にニューラルネットワーク部品を追加。repo のフォルダ分割が見えるヒント — 本番提出は heuristic 戦略と、衝突回避のために相手アクション分布を推定する NN を組み合わせていた。

### 4 位 — 0Zeta

- Repo: https://github.com/0Zeta/HaliteIV-Bot
- 引用: *"our approach utilizes no fancy ML techniques or otherwise disproportionate complex algorithms. Instead, our bot is a 100% rule-based bot with lots of parameters."*

盗む価値のあるトリック:

1. **Halite "プランテーション"** — halite 豊富な区域の周辺に三角形の隊形で shipyard を配置し、2% の再生率を活用。orbit-wars 等価物: 対称な惑星周辺の軌道クラスタ隊形。
2. **同時手のための線形和割当** — Hungarian アルゴリズムで全船のアクションを *同時に* 割り当てる。逐次パスファインディングの時間的結合を回避。
3. **10 種類の船役割** — MINING / RETURNING / HUNTING / GUARDING / DEFENDING 等。役割を毎ターンステートレスに再計算し、古いプランを残さない。
4. **罠にはまった敵への hunting スコアブースト** — *"boost the hunting scores of targets that can move safely to fewer than two cells"*。
5. **shipyard あたりガード 2 人** — パトロール半径が支配性を高め、侵入者を抑止。
6. **shipyard 周辺の 1:1 トレード受容** — shipyard 喪失は致命的なので防衛トレードオフ。

教訓: *"Lack of pathfinding caused ship congestion. Over-parameterization created brittleness. No replay analysis tools hampered debugging. Stateless design caused excessive ship type switching. A critical bug introduced day before submission severely damaged final performance."* これら 5 件すべてが警鐘。

### 8 位 — Convex (KhaVo、Dan、Gilles、Robga、Tung) — 注目に値する IL アプローチ

- Writeup: https://khavo.ai/2020/09/15/halite/

**セマンティックセグメンテーション** による模倣学習: 各船の即時アクションを、トップリプレイデータで学習させた UNet スタイルのモデルでピクセル単位ラベルとして予測。重要ポリシー (基地スポーン、船変換、基地保護) には heuristic オーバーライド。

### orbit-wars への転用

- 「同時手のための線形和割当」パターンは「同じターンに多数の艦隊が手を選ぶ」という orbit-wars の問題に対処する。
- 毎ターン役割を再計算する規律により、step 50/150/250/350/450 で comet がスポーンするときに古いプランが残るのを防ぐ。
- Convex のセマンティックセグメンテーション IL は良い Phase-2 ML パターン: 各グリッドセルが正しい移動方向を予測する (艦隊ごとの自己回帰 Transformer より安価)。

---

## 6. Halite III — 2018-2019 (Dijkstra と閾値ベースの衝突)

- コンペページ: https://halite.io/

### 1 位 — teccles

- Repo: https://github.com/teccles-halite/halite3-bot

各船が **盤面全体に対する Dijkstra** を実行し、各マスについて halite 消費とターンコストを計算。(移動 + 採掘 + 帰還) を通じてターンあたりの halite 利得を最大化するターゲットを選ぶ。衝突閾値は所有権 (近接で定義) × halite × 船価値で決まる。Dropoff スコアリング = `halite_density / (cost − square_halite)`。

### 6 位 — TheDuck314

- Repo: https://github.com/TheDuck314/halite2018

NN を組み合わせたハイブリッド heuristic。トリック:

1. **採掘スコア** = (dist + mining_time + return_dist)、**1.75× 距離ペナルティ** 付き。ターゲットを放棄する前に現在地の 3× の halite が必要。
2. **船ごとの目的**: Mine / Return / Flee / Ram / Stuck — それぞれが目的別スコアリングを通る。
3. **miner ↔ returner スワップによる交通制御** で dropoff 混雑を防ぐ。
4. **Python から C++ に書き換え** でボトルネック解消 (Lux S3 優勝者の Rust シミュレータと響き合う)。
5. **オフラインで学習した NN が相手手の確率を予測**。NN が隣接マスの **安全度 ≥98%** を推定したときだけ船は移動する。

### orbit-wars への転用

- NN による相手手予測の 98% 安全度閾値は orbit-wars の戦闘に直接転用可能: 過去の対戦に対し小型 CNN を学習させて相手艦隊手を予測し、期待結果が閾値以上のときだけ手を commit する。
- C++/Rust 書き換えは普遍的教訓 — env スループットが *唯一の* ボトルネック。

---

## 7. Lux AI Season 1 — 2021 (DRL が勝った)

- Writeup: https://www.kaggle.com/competitions/lux-ai-2021/writeups/toad-brigade-toad-brigade-s-approach-deep-reinforc

**1 位 — Toad Brigade。** self-play による純粋 RL。当初は heuristic を試したが、最初の 1 ヶ月以内に RL エージェントが超えたため DRL に切り替え — 重要なデータポイント。

アーキテクチャ:

- squeeze-excitation 付き完全畳み込み ResNet
- 24 個の residual ブロック、128 チャネル 5×5 畳み込み
- 約 2000 万パラメータ
- residual ブロックに **batch normalization なし** (微妙だが安定する)
- 3 つの actor head (workers / carts / city-tiles) + 1 つの critic

学習: 単純 PPO ではなく **IMPALA + UPGO + TD(λ)** の損失組合せ。計算資源: 単一の 8c/16t 個人 PC dual GPU、コンペ全期間にわたって夜間学習。

トリック:

1. **GridNet アクション空間** — 各グリッドセルにつきネットワーク出力 1 個。単一ネットがすべてのユニットを制御 → 創発的協調 (ユニットごとネットと対比)。
2. **最初の 2000 万 step 用報酬整形**、その後はスパース +1/-1 のみ — カリキュラム。
3. **段階的なネットサイズ拡大** 8→16→24 ブロック、teacher 蒸留 KL 損失付き。
4. **昼夜サイクルとゲーム位相次元** を明示的入力に — 中盤戦略シフトを可能にする。
5. **TTA: 推論時の 180° 回転平均化**。

転用: GridNet は orbit-wars 惑星グリッドにマップ。報酬整形カリキュラムが当てはまる (最初の N step は惑星捕獲で整形、その後スパース +1/-1 のみに切替) (Lux S1 パターン)。4 回対称性による TTA。重要なのは、**IMPALA+UPGO+TD(λ) は PPO ではない** こと — orbit-wars に DRL を実装するとき PPO はデフォルトだが、Toad Brigade の証拠は長期視野の多ユニットゲームでは UPGO 拡張 IMPALA がより堅牢であることを示唆する。

---

## 8. Hungry Geese — 2021 (DRL self-play + 終盤に MCTS)

- コンペ: https://www.kaggle.com/competitions/hungry-geese
- 日本語振り返り (秀逸): https://zenn.dev/ktechb/articles/e2394bc27358c4
- 5 位 writeup: https://www.kaggle.com/competitions/hungry-geese/writeups/takedarts-5th-place-solution-geesezero

**1 位 — HandyRL チーム (DeNA)。** 分散 off-policy DRL フレームワーク: https://github.com/DeNA/HandyRL

トリック (上位 5 を横断):

1. **連続 body グラデーション** (頭 1.0 → 尾 0.0) — 二値マスクではなくチャネル値で時間位置情報を埋め込む。
2. **ステップカウント入力チャネル** — 終盤切替を明示的に。
3. 純粋な self-play ではなく **過去バージョンの相手を混合** して学習 — 局所最適崩壊を防ぐ。
4. **終盤に AlphaZero スタイルの MCTS を後付け**。同時手と確率的食物に対応するよう改変。振り返りからの引用: *"During the final month, the author implemented Monte Carlo Tree Search (MCTS) inspired by AlphaZero, modifying it for simultaneous multi-agent action and stochastic food spawning by limiting food pattern possibilities."*

orbit-wars への転用: comet スポーンは確率的だが `random.Random(f"orbit_wars-comet-{seed}-{step+1}")` でシード化されている — つまり可能集合は列挙可能、まさに Hungry Geese の食物と同じ。comet スポーンとアクションの結合分布上の MCTS が扱いやすくなる。

---

## 9. microRTS 2023 — IL bootstrap → PPO finetune

- 論文: https://arxiv.org/html/2402.08112v1
- 1 位 — RAISocketAI。IEEE microRTS で勝った最初の DRL エージェント

計算資源: コンペ提出に **70 GPU 日** (A10/A6000/A100)。BC+PPO のフォローアップ論文では合計 **142 GPU 日**。

アーキテクチャ:

- DoubleCone(4,6,4) — 可変マップサイズ向けに SE + 適応プーリング付きの residual ブロック
- squnet — 100ms 推論下で大きいマップに対応する積極的な 3 段階ダウンスケール

トリック:

1. **ユニット数でスケールした BC 損失** — *"allowed the learning rate to be significantly increased"*。ターンごとに可変ユニット数による勾配スケール問題に対処。
2. **3 段階カリキュラム**: 16×16 (random init から 3 億フレーム) → 32×32 (transfer-finetune) → 64×64 (最難)。
3. **報酬の混合スケジュール**: 序盤密、終盤スパース +1/-1。
4. **無効アクションマスキング** — *"essential to training an agent that could compete at the most basic level"*。
5. **self-play 単独では性能不足** — 学習プロセスにスクリプト bot や過去チャンピオン等の外部相手を混ぜる必要があった。
6. **BC 後の PPO** はマップ別特化なしで 88% 勝率を達成 (vs. RAISocketAI のマップ別アンサンブル)。

知っておく価値のある失敗モード:

- *"Naive Large Map Training: Direct PPO training on 64x64 maps without bootstrapping produced training instability — a training policy that initially won 40-50% of training games, dropped to 20% midway."*
- 著者は **A2C は PPO よりも BC からスムーズに移行する可能性がある** と仮説を立てている。A2C の損失形式が BC により近いため。

転用: 100×100 連続空間の orbit-wars は 16×16 よりも 32×32-64×64 の microRTS 領域に近い。論文のカリキュラム + ユニット数スケール BC は最も転用可能な単一レシピ。「大きなマップでスクラッチから PPO は中盤に崩壊する」という失敗モードが BC bootstrap か純粋 RL かの設計選択を左右すべき。

---

## 10. ConnectX (永続コンペ。AlphaZero/MCTS が支配)

- 論文: https://arxiv.org/abs/2210.08263

ConnectX は完全観測、決定的、かつ十分小さく **手あたり約 20,000 シミュレーションの素朴な MCTS がハイブリッド MCTS+minimax を打ち負かす**。シミュレーション数が深さ品質を支配するため。orbit-wars への直接的な関連性は低い (orbit-wars はリアルタイム連続) が、ConnectX の証拠はシミュレーションスループットが決定的軸であることを補強する。orbit-wars にとってこれは「env を高速言語で書き直し、ステップ予算内で MCTS や BC が数百万のバリエーションを評価できるようにする」という Lux S3 / Halite III レシピを支持する。

---

## 11. コンペ横断の総合とレシピ for orbit-wars

### Heuristic vs IL vs DRL がそれぞれ勝った場面

| 領域 | 例 |
|---|---|
| **Heuristic 支配** | Halite II (1 位)、Halite III (1 位)、Halite IV (1 位はハイブリッド、4 位は純粋ルール)、**Lux AI S2 (10 億 IL フレーム提供にもかかわらず 1 位)** |
| **IL 支配** | Kore 2022 (1 位: 2 億タプル Transformer)、Halite IV (8 位: セマンティックセグメンテーション) |
| **DRL 支配** | Lux AI S1 (Toad Brigade、IMPALA+UPGO)、Lux AI S3 (Frog Parade、PPO+SE-ResNet)、Hungry Geese (HandyRL self-play)、microRTS 2023 (BC+PPO) |

**パターン:** アクション空間が「明らかな局所サブ決定」に分解できるところで heuristic が勝つ (Halite 採掘、Lux factory 配置、Halite II 船役割)。リーダーボードに専門家のデモンストレーションが存在し、アクション空間が自然にトークン化可能なときに IL が勝つ (Kore プラン)。多数のユニット間で還元不可能な逐次協調があり、かつチームに env スループットと計算資源があるときに DRL が勝つ (Lux S1/S3、Hungry Geese、microRTS)。

### orbit-wars への推奨段階レシピ

| Phase | 週 | アプローチ | 理由 | 出典 |
|---|---|---|---|---|
| 1 | 1-2 | 純粋 heuristic: 戦闘 or 逃走 + 惑星優先度キュー + 対称性 | Halite II / Lux S2 の証拠より、即座に LB の 80% を打破 | https://recursive.cc/blog/halite-ii-post-mortem.html, https://www.kaggle.com/competitions/lux-ai-season-2/writeups/ry-andy-1st-place-solution |
| 2 | 3-4 | 戦闘判断用に NN 相手手予測器を追加。X% 以上安全な場合のみ commit | TheDuck314 の Halite III パターン。heuristic を強化 | https://github.com/TheDuck314/halite2018 |
| 3 | 5-6 | カスタム Rust シミュレータ + トップ N リプレイをスクレイプ。BC 自己回帰ポリシー | Kore 2022 パターン + Lux S3 スループットトリック | https://github.com/khanhvu207/kore2022, https://github.com/IsaiahPressman/kaggle-lux-2024 |
| 4 | 7-8 | ユニット数スケール CE 損失付き PPO finetune (PPO が不安定なら A2C) | microRTS 2023 の教訓 — A2C は PPO より BC からスムーズに移行 | https://arxiv.org/html/2402.08112v1 |

### 必須トリック (フェーズに関係なく実施)

1. **(50, 50) 中心の 4 回対称性によるテスト時拡張** — orbit-wars の対称性は `~/projects/kaggle/orbit-wars/.venv/lib/python3.11/site-packages/kaggle_environments/envs/orbit_wars/orbit_wars.py` に文書化されている。データ拡張 (×4) と推論平均化に使う。
2. **アクションマスキング** — 過去のあらゆるレベルの優勝者が使った。これなしでは RL は学習に失敗する。
3. **相互作用半径による船セット剪定** — orbit-wars 艦隊速度は `1.0 + (max_speed-1.0) * (log(ships)/log(1000))^1.5` (max=6.0)。艦隊ごとの実効相互作用半径は有界。意思決定ごとに関連艦隊のみ考慮する。
4. **comet 可能性の列挙** — comet は固定ステップ (50/150/250/350/450) でスポーンし、`random.Random(f"orbit_wars-comet-{seed}-{step+1}")` でシード化される。任意の tick で可能な comet 状態の集合は既知の seed あたり有限。MCTS や value 関数の入力用に列挙する。
5. **+1/-1 スパース報酬整形カリキュラム** — 最初の N% は惑星捕獲または艦隊保存で報酬整形し、その後スパース +1/-1 のみに切替 (Lux S1 パターン)。
6. **フルマップでスクラッチから PPO は避ける** — microRTS の証拠: 40-50% → 20% への中盤崩壊。BC で先に bootstrap する。

### コンペ横断で文書化された失敗モード (避ける)

| 失敗 | 出典 |
|---|---|
| 締切前日に決定的バグを提出 | 0Zeta Halite IV postmortem |
| 過剰パラメータ heuristic → 相手の変化に脆弱 | 0Zeta Halite IV postmortem |
| 純粋 self-play → 局所最適崩壊 | Hungry Geese 振り返り、microRTS 2023 |
| BC bootstrap なしの大マップ PPO → 中盤崩壊 | microRTS 2023 論文 |
| リプレイ解析ツールなし → デバッグが手探り | 0Zeta Halite IV postmortem |
| ステートレスな船役割再計算 → 役割スラッシング | 0Zeta Halite IV postmortem |

### 必要な計算資源の見積もり

- Phase 1 (heuristic): GPU 不要
- Phase 2 (NN 相手手予測器): RTX 3090 クラスで 1 GPU 日
- Phase 3 (2 億タプルでの BC): **2× A100 80GB × 20 epoch ≈ 5-10 GPU 日** (Kore 2022 の数字より)
- Phase 4 (BC チェックポイントからの PPO/A2C finetune): **30-40 GPU 日** (microRTS の 32×32 より。orbit-wars は 100×100 連続なのでおそらく 40-60 GPU 日)

合計予算: フル ML スタックで概ね **50-100 GPU 日**。これは利用可能な 8 週間ウィンドウで単一 RTX 3090 で達成可能 (1 GPU × 56 日 ≈ フル稼働で 56 GPU 日)。Lux S3 の Frog Parade は RTX 3090 で 8 日に 3 億フレームを達成しており、まさにこの領域。

---

## 12. 出典一覧

主要 writeup (上記すべてで引用済み):

1. https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md (Lux S3 1 位、Frog Parade)
2. https://www.kaggle.com/competitions/lux-ai-season-2/writeups/ry-andy-1st-place-solution (Lux S2 1 位)
3. https://github.com/ryandy/Lux-S2-public (Lux S2 1 位 repo)
4. https://www.kaggle.com/competitions/kore-2022/discussion/340035 (Kore 2022 1 位)
5. https://github.com/khanhvu207/kore2022 (Kore 2022 1 位 repo)
6. https://recursive.cc/blog/halite-ii-post-mortem.html (Halite II 1 位、reCurs3) — 注: サイトがたまに接続を拒否する
7. https://medium.com/aescru/halite-ii-strategies-of-a-top-player-88127b3b49e2 (Halite II トッププレイヤー解説、James Jones)
8. https://lakesidethinks.com/post/2018/10/halite2-strategy.html (Halite II トップ 3 レビュー)
9. https://github.com/FakePsyho/halite2 (Halite II 2 位 repo)
10. https://shummie.github.io/Halite-2-Shummie/ (Halite II 3 位 postmortem)
11. https://github.com/ttvand/Halite (Halite IV 1 位 repo)
12. https://github.com/0Zeta/HaliteIV-Bot (Halite IV 4 位 repo + writeup)
13. https://khavo.ai/2020/09/15/halite/ (Halite IV 8 位 IL writeup)
14. https://github.com/teccles-halite/halite3-bot (Halite III 1 位 repo)
15. https://github.com/TheDuck314/halite2018 (Halite III 6 位、NN 衝突予測器付き)
16. https://www.kaggle.com/competitions/lux-ai-2021/writeups/toad-brigade-toad-brigade-s-approach-deep-reinforc (Lux S1 1 位、Toad Brigade)
17. https://github.com/IsaiahPressman/Kaggle_Lux_AI_2021 (Lux S1 IL alt)
18. https://github.com/DeNA/HandyRL (Hungry Geese 1 位フレームワーク)
19. https://www.kaggle.com/competitions/hungry-geese/writeups/takedarts-5th-place-solution-geesezero (Hungry Geese 5 位)
20. https://zenn.dev/ktechb/articles/e2394bc27358c4 (Hungry Geese 振り返り、JP)
21. https://arxiv.org/html/2402.08112v1 (microRTS 2023 BC+PPO 論文)
22. https://openreview.net/forum?id=7t8kWYbOcj (Lux S3 主催者論文)
23. https://www.twosigma.com/articles/halite-ii-concludes-winners-announced/ (Halite II 優勝者アナウンス)

エンジンソース (ローカル引用): `~/projects/kaggle/orbit-wars/.venv/lib/python3.11/site-packages/kaggle_environments/envs/orbit_wars/orbit_wars.py`
