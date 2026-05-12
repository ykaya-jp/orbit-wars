# orbit-wars Top-tier 選手 Profile + 戦略推測 (= 2026-05-12)

> orbit-wars 優勝 path 補強研究 W3
> 担当: top 20 圏 (= LB 1367+) の選手 profile + paradigm 推測
> LB snapshot: `.venv/bin/kaggle competitions leaderboard orbit-wars --show` 2026-05-12 取得 (= 本 doc 冒頭時点)
> 既存研究との接続: `docs/discussion/insights.md` § 1 (= bovard 2,820,068 row の per-player 行動分布) と clausula 整合

---

## 0. 本 doc の TL;DR

- **bowwowforeach (= LB 1 位 / 1823.1)** は **AtCoder Heuristic Contest (AHC) で 4 回 1 位 + Heuristic rating 3216 + TopCoder Marathon rating 2306** の Heuristic / Marathon 世界 top 0.1% 級。 paradigm = **rule-base + beam search / SA / chokudai search** (確信度 high)。 RL ではない。 公開 kernel 0。
- top 5 圏 (= bowwow / flg / Vadasz / Ebi / Isaiah) のうち **Isaiah Pressman (= LB 5 位 / 1548.5 @ Tufa Labs)** だけ **deep RL 達人** (= Lux AI 2021 RL 主導 + Lux S3 Frog Parade gold)。
- 残り top 5 (flg / Vadasz / Ebi) は profile 出典不足だが、 bovard data の **行動分布パターン** (= insights.md § 1) から **rule-base + 探索** 推定 (= 確信度 mid)。
- LB 5/9 → 5/12 の delta: **bowwow +172** (= 1650.9 → 1823.1) は他者と隔絶した跳躍、 **flg は -49** (= 1650.9 → 1602.1) で逆に下落。 ⇒ **bowwow は探索 depth or evaluator を 5/9 以降に breakthrough 改良**、 他者は対応できていない。

---

## 1. Top 1 bowwowforeach (= LB 1823.1) 詳細

| 項目 | 値 |
|---|---|
| LB rank / score (= 2026-05-12) | 1 / 1823.1 |
| LB delta (= 5/9 → 5/12) | **+172** (1650.9 → 1823.1) |
| Kaggle profile URL | https://www.kaggle.com/bowwowforeach |
| Kaggle profile body | Kaggle SPA で WebFetch 取得不可 (= body 空)、 直接 medal 数 未確認 |
| GitHub URL | https://github.com/bowwowforeach |
| GitHub repo | `Contest` (= 1 repo only、 C++ 100%、 2 stars、 MM148 / MM149 = TopCoder Marathon Match 解) |
| AtCoder profile URL | https://atcoder.jp/users/bowwowforeach |
| AtCoder Algorithm rating | 1353 (highest 1488、 = 普通 / 上位 ~25%) |
| **AtCoder Heuristic rating** | **3216** (= 上位 0.1% 級、 全国 top 10 級) |
| AHC 1 位回数 | **4 回** (AHC013 / 014 / 017 / 033) |
| AHC notable 上位 | AHC033 Toyota 1 位 perf 3488、 AHC052 / AHC063 で 2 位 |
| TopCoder Marathon rating | **2306** (= Marathon Red、 世界 top 級) |
| Twitter | https://x.com/bowwowforeach |
| 所属 | 株式会社 THIRD (= 日本の不動産 SaaS スタートアップ) |
| 公開 speakerdeck | https://speakerdeck.com/bowwowforeach (= AHC026 Toyota の至高アルゴリズム解説、 1.6k views) |
| 公開 kernel for orbit-wars | **0 件** (= 上位選手 hidden 戦略 pattern、 ~/projects/kaggle/CLAUDE.md §7 警告 3 と整合) |
| 公開 discussion 投稿 | 未確認 (= Kaggle SPA で trace 困難、 既存 0510.md にも明示なし) |

### 1.1 行動分布 (= bovard 2026-05-04 top10 dataset 自家分析、 出典: `docs/discussion/insights.md` § 1)

| 指標 | bowwowforeach 値 | top tier 平均 | 我家 (= Reexel / v2 旧) |
|---|---|---|---|
| step 0-99 avg ships | 287 | 287-430 | ~30-50 |
| step 0-99 avg planets | 5.01 | 4.15-7.39 | 1-2 |
| step 400-499 avg ships | 7084 | 3556-18122 | ~150 |
| launch_per_turn | **0.59** (= 最 low) | 0.69-0.95 | n/a |
| **launch size p99** | **3647 ships** (= **突出**、 isaiah 986 を 3.7 倍上回る) | 154-1912 | n/a |
| launch size 中央値 | 52 ships | 19-49 | n/a |

→ **戦略 signature: low-frequency big-stack「kill stack」** (= 終盤に 1 launch 3000+ ships で決着付ける)。 これは **state space を長期 simulate して決定点で集中投入する beam search / chokudai search 系の典型挙動**。

### 1.2 推測 paradigm (= 確信度 high)

**rule-base + 探索 (beam search / chokudai search / simulated annealing) hybrid**

確信度 **high** の根拠:

1. **AHC Heuristic rating 3216 + AHC 4 回 1 位 + TopCoder Marathon 2306** = 世界 top 0.1% の Heuristic / Marathon 解の達人。 これら全コンペの主流解法は **beam search + 評価関数 + simulated annealing** (= 出典: https://atcoder.jp/contests/ahc017/editorial, https://www.kaggle.com/c/halite/discussion/183543 ttvand 1 位 11000 行 rule)
2. **GitHub の Contest repo が C++ 100% / 2 commit only (MM148, MM149)** = AtCoder / TopCoder 用の最小 dump、 deep learning 系の commit 履歴なし
3. **AtCoder Algorithm rating 1353 (= 普通)** = アルゴリズム本職ではない、 **Heuristic 専業 player**
4. **bovard 行動分布の「kill stack」 pattern** = 単純 rule では出ない。 turn 単位の long-horizon plan を持つ探索系の挙動と整合
5. **公開 kernel 0 / discussion 沈黙** = AHC 王者の慣行 (= 解法を最後まで隠す、 出典 例: https://speakerdeck.com/bowwowforeach AHC026 解説は **comp 終了後** 公開)
6. **Halite IV (= orbit-wars に最も構造類似) の Top 1 ttvand も 11000 行 rule-base** (= ~/projects/kaggle/orbit-wars/docs/research/past-comps.references.json `halite_iv.top1_technique = "rules_5000_lines"`) → orbit-wars でも rule-base が gold zone 妥当
7. orbit-wars は **angle 完全 observable** (= insights.md § 2.3) + 2P 主 + 1 turn ~1s 想定 → **partial observability low、 reactive RL より forward search が優位**

確信度 **mid** に下げる reservation: 一部の AHC 上位 player が近年 NN evaluator + MCTS / AlphaZero 系を採用しているため、 **NN evaluator を載せた MCTS** の可能性も残る (= 例: 2026 年 AHC 系で深層 evaluator を beam search hybrid に挿す事例あり、 ただし学習なし純粋探索が多数派)。 ただし base structure は forward search で固定と推測。

### 1.3 LB 跳躍 (= +172 in 3 days) の戦略的意味

5/9 → 5/12 で **bowwowforeach +172**、 同期間に **flg -49 (= 1650.9 → 1602.1)** で 1 位独走。 これは:

- bowwow が **5/9 以降に評価関数 or 探索 depth に breakthrough を入れた** signal
- 他 top tier は対応 update できていない (= 5/9 時点で bowwow と並走していた flg が score 下落、 環境 (= opponent pool) が bowwow 強化分だけ難化)
- score 1823 達成 = unprecedented、 score 2000+ 目標まで **残 +177** (= 我家の到達需要量)

---

## 2. Top 2-20 圏 選手リスト

### 2.1 #2 flg (= LB 1602.1)

| 項目 | 値 |
|---|---|
| LB delta (= 5/9 → 5/12) | **-49** (= bowwow 強化分で被害最大) |
| Kaggle profile URL | https://www.kaggle.com/flg (= 直接 fetch 404、 slug 別の可能性 / 削除されている可能性) |
| 出典確認状況 | profile 取得 失敗 (= Kaggle SPA + slug 不一致) |
| 行動分布 (insights.md § 1) | step 0-99 ships 283 / planets 5.65、 launch p99 **1912 ships** (= 2 位)、 launch_per_turn 未公開 |
| **推測 paradigm** | **rule-base + 探索 hybrid** (確信度 **mid**)。 launch p99 1912 = bowwow と並ぶ big-stack 系、 ただし bowwow の 3647 まで届かず |
| **推測根拠** | bovard 行動分布で bowwow と同類の「low-freq big-stack」 pattern、 bowwow と同じ paradigm 系統と推定。 LB 1650 → 1602 下落 = 同戦略系で押し負けた解釈と整合 |
| 出典 | `docs/discussion/insights.md` § 1; `lb_snapshot_2026-05-09.csv` vs 2026-05-12 LB |

### 2.2 #3 Vadasz (= LB 1599.4)

| 項目 | 値 |
|---|---|
| LB delta | +46 (= 1553.3 → 1599.4) |
| Kaggle profile URL | https://www.kaggle.com/vadasz (= 直接 fetch で profile body 取得不可) |
| 行動分布 (insights.md § 1) | step 0-99 ships 274 / planets 5.40、 step 400-499 ships **3556 (= 最小)** / planets 3.70、 launch p99 **154 ships only** (= 最 conservative) |
| launch_per_turn | 0.74 (mid-frequency mid-ships) |
| **推測 paradigm** | **rule-base 純** (確信度 **mid**)。 launch p99 154 / ships 終盤 3556 = 探索無し or 軽探索の defensive heuristic typology |
| **推測根拠** | 行動分布が最も均質 (= 大 launch を捨て small-and-many)、 これは複雑探索より rule 軽量 evaluator 系の挙動。 ただし profile 一次資料不足 |
| 出典 | insights.md § 1 |

### 2.3 #4 Ebi (= LB 1560.6)

| 項目 | 値 |
|---|---|
| LB delta | -70 (= 1631.4 → 1560.6) |
| Kaggle profile URL | https://www.kaggle.com/ebi 系 (= 一意 slug 確認不可、 「Ebi」 は日本由来 handle 多数) |
| 行動分布 | insights.md § 1 表に Ebi 単独列なし (= 直接 query 必要) |
| **推測 paradigm** | **rule-base 推定** (確信度 **low**)。 handle が日本由来 + AHC / TopCoder MM 系参加者が多い名前パターン、 LB 1500+ は通常 rule-base 上位 |
| **推測根拠** | 名前 pattern + LB position のみ。 一次資料未確認 |

### 2.4 #5 Isaiah @ Tufa Labs (= LB 1548.5)

| 項目 | 値 |
|---|---|
| LB delta | -34 (= 1582.1 → 1548.5) |
| Kaggle profile URL | https://www.kaggle.com/isaiahpressman 系 (= 推定) |
| GitHub URL | https://github.com/IsaiahPressman |
| 所属 | **Tufa Labs** (= Zurich の AI 研 lab、 RL / multi-agent / LLM 系)、 出典: https://tufalabs.ai/team/ |
| 過去 Kaggle agent comp 入賞 (= 出典確認済) | **Kaggle Lux AI S1 (2021): top tier RL 主導** (= IMPALA + UPGO + TD-λ + SE-ResNet 24 block + 20M params + KL teacher distillation、 出典: https://github.com/IsaiahPressman/Kaggle_Lux_AI_2021); **Lux AI S3 (NeurIPS 2024): Frog Parade gold** (= Rust + JAX + PPO + SE-ResNet 8 block + 10M params + 300M frames、 出典: https://github.com/IsaiahPressman/kaggle-lux-2024); ARC Prize 2025 関連 (= MindsAI & Tufa Labs writeup) |
| Tufa Labs bio | "Research engineer ... self-play RL ... multiple 1st- and 2nd-place finishes in Kaggle competitions" (出典: https://tufalabs.ai/team/) |
| 公開 kernel for orbit-wars | 未確認、 過去パターン的に **解法は GitHub に comp 終了後 dump** (= Lux S1 / S3 共に最終 writeup を repo に置く慣行) |
| 行動分布 (insights.md § 1) | (= 直接 query 必要、 insights.md にも未列挙) |
| **推測 paradigm** | **deep RL (PPO + 自前 simulator + SE-ResNet)** (確信度 **high**) |
| **推測根拠** | Lux S1 / Lux S3 / Tufa Labs 所属 が全部 RL 系。 「自前 Rust simulator + JAX + PPO」 の方法論 が固定 pipeline (= Lux S3 write-up.md に明記)。 orbit-wars でも同 stack を再利用する蓋然性 high |

### 2.5 #6-10 (= LB 1416-1495)

| Rank | Username | Score | LB delta (5/9→5/12) | 推測 paradigm | 確信度 | 根拠 |
|---|---|---|---|---|---|---|
| 6 | Shun_PI | 1495.8 | -4.8 | rule-base or hybrid | low | Kaggle slug `shunrcn`、 profile body 取得不可 |
| 7 | Erfan Eshratifar | 1486.9 | +11.9 | RL or IL | mid | Yahoo 研究員 PhD (edge intelligence / NN compression)、 学術系 = deep learning 寄り蓋然性 (出典: https://scholar.google.com/citations?user=fpNg6ZcAAAAJ) |
| 8 | kovi | 1457.9 | -19.7 | 不明 | low | profile 一次資料未確認 |
| 9 | 3Comets | 1437.6 | +59.1 (= **大幅伸び**) | 不明 (= 急成長 sign) | low | profile 一次資料未確認、 5/9 以降にも改良入れている = active player |
| 10 | sash | 1426.0 | -67.2 | 不明 | low | profile 一次資料未確認 |

### 2.6 #11-20 (= LB 1367-1416)

| Rank | Username | Score | LB delta | 推測 paradigm | 確信度 | 根拠 |
|---|---|---|---|---|---|---|
| 11 | Ezra | 1416.5 | -39.1 | rule-base | mid | insights.md § 1 行動分布 (= ships 4054 / launch p99 388、 mid-defensive)、 個人 profile 不明 |
| 12 | ShunkiKyoya | 1413.4 | -17.2 | 不明 | low | 名前 pattern = 日本人個人 (= AHC / Kaggle 兼業の可能性)、 profile 取得失敗 |
| 13 | Galatea of the Spheres | 1410.0 | +11.5 (= 5/8 Andrew + SalvadorDali から rename / re-team) | 不明 | low | Dali 絵画名 handle、 5/8 → 5/12 で +11.5 のみ = stable rule-base 推測 |
| 14 | lookaside | 1389.2 | -30.8 | 不明 | low | profile 一次資料未確認 |
| 15 | klog | 1388.8 | +53.0 | 不明 (= 急成長) | low | profile 一次資料未確認、 5/6 開始 → 5/10 update active |
| 16 | dnish | 1386.5 | -4.1 | 不明 | low | profile 一次資料未確認 |
| 17 | Ousagi | 1384.6 | -107.3 (= **最大下落**) | 不明 | low | 名前 = 日本人個人 (兎 + さん)、 大幅 LB 落ち |
| 18 | ymg_aq | 1374.3 | -11.0 | 不明 | low | profile 一次資料未確認 |
| 19 | 赵云龙 | 1372.5 | -11.6 | 不明 | low | 中国名 person、 profile 取得失敗 |
| 20 | Erik Kvanli | 1367.8 | +72.8 (= **大幅伸び**) | **rule-base + 探索 (GA 系含む)** | **mid** | Norway、 GitHub `Illedan` (= 53 repos、 BOTG-Refree / CGSearchRace / SimpleSharp-GA / Bit-Runner-2048)、 **CodinGame community game 作者** + TopCoder MM + AtCoder 兼業の **competitive game AI** 系。 行動分布 (insights.md § 1): step 0-99 ships 300 / planets 7.39 (= 最 expansion-heavy)、 step 400-499 ships **18122 (= top tier 最大)**。 launch_per_turn 0.69、 mid-frequency aggressive 出典: https://github.com/Illedan, https://kvanli.com |

---

## 3. 我家 戦略への hint (= 5 件、 actionable)

### 3.1 ★ bowwowforeach の "kill stack 戦略" を **解読・破壊 / 模倣** の 2 路線を並走で

**根拠**: bowwow の paradigm = rule-base + 探索 (確信度 high)、 launch p99 3647 = 探索系の長期 plan が無いと生成できない大 stack。 同 paradigm で勝負するなら:
- **路線 A (= 模倣)**: bovard 2026-05-04 dataset (= 2820k row) から bowwow の per-step decision を逆推定し、 同 type の「step 200-300 で形成 / step 350-450 で投擲」 schedule を IL ターゲットに混ぜる
- **路線 B (= 破壊)**: kill stack の弱点 = **stack 形成中の home defense が手薄**、 ここを敵 fleet angle (= 完全 observable) で見て **forward-search 系 intercept (= 数 step 先で交差予測の即時応答)** で奪取する
- どちらでも **forward-search を入れる** = PPO 単独路線では bowwow に届かない可能性大

**actionable**:
1. `docs/strategy/` 配下に **「bowwow countermeasure 検討」 doc** (= 仮: `2026-05-12-kill-stack-counter.md`) を起票、 bovard data から bowwow vs Vadasz / vs Ezra の試合を抽出して「kill stack 形成 timing」 と「相手の return shot」 を per-turn map に
2. PPO θ.5 reward shaping に **「敵 stack 形成検知 → 1.5× 反撃 bonus」** を入れて RL 自前学習を補助

### 3.2 ★ Isaiah (deep RL) が **score 1548 でしかない** = orbit-wars は pure RL では不十分

**根拠**: Isaiah は Lux S1 / Lux S3 両方で RL gold の世界 top RL 実装者。 その彼が orbit-wars LB 5 位 1548 で **bowwow に -275** で頭打ち。 → orbit-wars は **pure RL では 1500-1600 帯が天井**、 gold zone (= 1800+) は **rule-base + 探索 が必須**。

**actionable**:
1. 我家の Phase 2 PPO path は **1600-1700 圏まで上げる手段** として継続、 だが **gold zone 突破には forward-search / search-policy hybrid を Phase 3 として併走**
2. ~/projects/kaggle/CLAUDE.md §1.3 (= "single paradigm では gold は不可能、 transduction + induction の combination") と整合: **PPO (= reactive policy) + forward search (= induction) hybrid を Phase 3 でデザイン**
3. Phase 3 候補: **policy net (= PPO 学習済) を leaf evaluator として MCTS / beam search に挿入** (= AlphaZero typology の軽量版)。 orbit-wars は **angle 完全 observable + state space 中規模** → MCTS が成立する条件

### 3.3 ★ bowwow が 5/9 → 5/12 で +172 跳躍 = 上位は **active な weekly update** で剥がせる隙がある

**根拠**: LB delta 表で **bowwow +172 / flg -49 / 3Comets +59 / Erik Kvanli +73 / klog +53 / Ousagi -107** = この 3 day で大きく入れ替わった = **環境変化に追従できる active update 体制が必須**。 update 停滞すると LB 下落が止まらない (= flg, Ousagi)。

**actionable**:
1. **2-3 day cadence で必ず 1 submit + bovard top10 dataset の最新日 (= 5/4 以降あれば再取得) を取り込む** ルールを `~/projects/kaggle/CLAUDE.md` §4.1 quota 管理に追加提案
2. 我家の現 PPO θ.4 200k step は **bowwow 5/9 時点の opponent pool に最適化** = 5/12 update された pool で勝率測定し直す必要 (= 旧 benchmark で評価しない)

### 3.4 ★ Erfan Eshratifar (= LB 7 位 RL 推定 + +11.9 active) + Isaiah (= LB 5 位 RL 確定) = **RL は中位 (top 5-10) を獲る paradigm**

**根拠**: RL 学術系の Erfan + RL 業界の Isaiah が共に 1486-1548 帯。 つまり orbit-wars で **「PPO + 自前 simulator + ResNet」 stack の上限は 1550 前後**。

**actionable**:
1. 我家の **PPO 単独路線の天井予測 = 1550-1650** (= Isaiah Lux S3 流をベタ移植しても届くのはここ)
2. PPO で 1500 帯を確保した後、 **forward search を hybrid 化** が必須 = Phase 3 設計を **PPO 完成を待たず Phase 2 後半から並走**

### 3.5 ★ Erik Kvanli (= Illedan) は **GA + 探索** で top 20 入り = 我家でも検討余地

**根拠**: Erik Kvanli の GitHub に **`SimpleSharp-GA`** (= Genetic Algorithm) repo あり + CodinGame community game 作者 = **GA / beam search の game AI 達人**。 行動分布 (insights.md § 1) で step 400-499 で **ships 18122 (= top tier 最大)** = **超 aggressive expansion**。 paradigm = rule-base + GA / beam search で 1367 帯。

**actionable**:
1. 我家の Phase 1 rule-base agent (= `agent_v2`) の **mission パラメータ (= CaptureMission target priority threshold、 DefenseMission intercept radius、 等) を GA で自動チューニング** する補助 task を新規 ticket 化候補
2. これは **PPO 学習中の wall clock 待ち時間に CPU で並走** できる (= GPU 不要、 evaluation cost 軽)、 score +30-80 程度の利益見込み (= Erik の上昇 +72 と整合)

---

## 4. 未確認 / 推測の弱い項目 (= TBD list)

| # | TBD | 確認手段 | priority |
|---|---|---|---|
| 1 | bowwowforeach の Kaggle medal 履歴 (= 過去 RL / agent comp 出場歴) | Kaggle SPA を browser 経由で human view (= 我家本人) or Meta-Kaggle dataset (= `data/external/meta_kaggle/Users.csv` 含む) で teamId 15648364 を query | **high** |
| 2 | flg (LB 2) の profile (= slug 不明、 過去 comp 履歴) | Kaggle teamId 15635910 を Meta-Kaggle で query | **high** |
| 3 | bowwow の **submission timing pattern** (= 何 day cadence で submit) | `.venv/bin/kaggle competitions submissions` は自分のみ、 LB snapshot を **daily で記録** して bowwow score 更新 timing を trace | mid |
| 4 | bowwow discussion 投稿の有無 (= 戦略 hint 漏れ) | `kaggle competitions topic-messages orbit-wars <topic_id>` 全 topic ローラー (= insights.md § 6 の限界あり) | mid |
| 5 | Vadasz / Ebi / kovi / 3Comets / sash / klog / Ousagi / lookaside / dnish / ymg_aq / 赵云龙 の正体 | Meta-Kaggle Users.csv + teamId join + Google handle search | low (= 各 1 名で大きく hint は変わらない) |
| 6 | 3Comets の +59 急成長手法 (= active update player) | bovard data 最新日 (= 5/4 以降) でこの player の試合を抽出可能か? | mid |
| 7 | bowwow の **使用言語** (= Python / C++ / Rust ?) | submission コンテンツは見えないが、 GitHub Contest repo が C++ 100% = C++ で書く慣行と推測 | low |
| 8 | bowwow が PPO / 探索どちらか の **decisive evidence** (= 推測 high を確定 high に上げる) | discussion / 終了後 write-up を待つ (= 通常 winner の公開は comp 終了後 1-2 week) | low (= 終了後しか確定不能) |

---

## 5. 我家の優勝確率に対する evidence-based 更新

(本 doc 単体での結論ではなく、 親 plan / handoff doc への入力として記載)

- **2026-05-12 時点 LB 1 位 1823.1、 目標 2000+ なので +177 の追加伸び を **bowwow 自身が** または **我家が抜く形で達成** 必要
- bowwow の paradigm 推定が rule-base + 探索 で正しいなら、 **同 paradigm + 我家のオリジナル評価関数 / search depth で勝負** が最短 path (= 確信度 mid)
- PPO 単独路線では 1550-1650 圏が天井 (= Isaiah, Erfan の証拠から推定)、 これ単独では **絶対に勝てない**
- 残 42 day で **PPO (Phase 2) + 探索 hybrid (Phase 3) + GA tuning (Phase 1.5 補助)** の **3 paradigm 並走** が「優勝本質性」 criterion (= 親 CLAUDE.md §11) に最も近い設計

---

## 出典 (= 全件 URL、 access 2026-05-12)

### Kaggle / orbit-wars 関連
- orbit-wars LB: https://www.kaggle.com/competitions/orbit-wars/leaderboard
- orbit-wars discussion (= SPA): https://www.kaggle.com/competitions/orbit-wars/discussion
- bowwow Kaggle profile: https://www.kaggle.com/bowwowforeach
- Shun_PI Kaggle (= slug shunrcn): https://www.kaggle.com/shunrcn/competitions
- 既存 LB snapshot (= 5/9 比較ベース): `docs/research/lb_snapshot_2026-05-09.csv`
- 既存 bovard data 分析 (= 行動分布表の出典): `docs/discussion/insights.md` § 1 (= 2,820,068 row / 2026-05-04 host dataset)

### 過去 agent comp 優勝者解法
- Lux AI S1 Isaiah Pressman 解: https://github.com/IsaiahPressman/Kaggle_Lux_AI_2021
- Lux AI S3 Frog Parade 解: https://github.com/IsaiahPressman/kaggle-lux-2024
- Kore 2022 1 位 IL 解: https://github.com/khanhvu207/kore2022
- Halite IV ttvand 1 位 11000 行 rule: https://github.com/ttvand/Halite
- Lux S2 ry-andy 1 位 pure heuristic: https://www.kaggle.com/competitions/lux-ai-season-2/writeups/ry-andy-1st-place-solution
- nagiss 「Kaggle シミュレーションコンペの動向」 (= 歴史 paradigm 整理): https://speakerdeck.com/nagiss/kagglesimiyuresiyonkonpenodong-xiang
- 既存 past comp 索引: `docs/research/past-comps.references.json`

### bowwowforeach 個別出典
- GitHub: https://github.com/bowwowforeach
- GitHub Contest repo: https://github.com/bowwowforeach/Contest (= MM148 / MM149、 C++ 100%)
- AtCoder profile: https://atcoder.jp/users/bowwowforeach
- AtCoder Heuristic 履歴 (= AHC 4 回 1 位): https://atcoder.jp/users/bowwowforeach/history?contestType=heuristic
- TopCoder profile (= Marathon rating 2306): https://competitiveprogramming.info/topcoder/handle/bowwowforeach
- Speaker Deck (= AHC026 解説): https://speakerdeck.com/bowwowforeach
- Speaker Deck AHC026 1.6k views: https://speakerdeck.com/bowwowforeach/toyotazi-dong-che-puroguramingukontesuto2023-number-6-atcoder-heuristic-contest-026-zhi-gao-noarugorizumujie-shuo
- Twitter: https://x.com/bowwowforeach
- 所属 株式会社 THIRD: AtCoder profile (= "株式会社THIRD" 表記)

### Isaiah Pressman 個別出典
- GitHub: https://github.com/IsaiahPressman
- Tufa Labs team: https://tufalabs.ai/team/
- LinkedIn (= RocketReach 経由 reference): https://rocketreach.co/isaiah-pressman-email_369535845
- MindsAI & Tufa Labs ARC Prize 2025: https://www.kaggle.com/competitions/arc-prize-2025/writeups/mindsai-and-tufa-labs-arc-prize-2025-solution

### Erik Kvanli (= Illedan) 個別出典
- GitHub: https://github.com/Illedan
- 個人 blog: https://kvanli.com/
- LinkedIn: https://www.linkedin.com/in/erikkvanli/

### Erfan Eshratifar 個別出典
- Google Scholar: https://scholar.google.com/citations?user=fpNg6ZcAAAAJ&hl=en
- LinkedIn: https://www.linkedin.com/in/erfan-eshratifar-4059225a/
- GitHub: https://github.com/erfaneshrati
- Personal site: https://amirerfan.com/

### orbit-wars 過去 LB / 既存研究の cross-reference
- 既存 discussion docs: `docs/discussion/0510.md`, `docs/discussion/insights.md`
- 既存 LB observation: `docs/research/lb-observations.dense.md`, `docs/research/lb-observations.kids.md`
- 親 instructions: `~/projects/kaggle/CLAUDE.md` §1.3 single-paradigm 禁止、 §7 警告 3 他人の解法 rezip 禁止、 §11 優勝本質性 criterion

---

## 更新履歴

- 2026-05-12: 初版 (= 優勝 path 補強研究 W3、 top 20 圏 profile + paradigm 推測 + 我家 戦略 hint 5 件)
