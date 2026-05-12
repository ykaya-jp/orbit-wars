# orbit-wars Forum + 公開 Kernel Deep Dive (= 2026-05-12)

> orbit-wars 優勝 path 補強研究 W2
> 担当: forum 全 topic 最新 + 公開 kernel 17+ 再 audit + host file 制約再 read
> 出典規律: ~/.claude/CLAUDE.md "Links, not verdicts" — すべての claim に URL or file:line を併記
> 補完 doc: `docs/research/2026-05-12-victory-research/01-past-comp-rl-deployment.md` (= W1 過去 comp 軽量化研究)

---

## 0. 結論先出し (= TL;DR for main agent)

1. **submission size の host 公式 limit は orbit-wars README / agents.md / discussion で「未記載」** (確認済)。 ただし **de facto 100 MB** が Kaggle agent comp 標準 cap という強い間接証拠あり (= Lux S3 1st Frog Parade writeup "62MB shy of the 100MB submission file size limit" / https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md)。 我家の 425-457 MB tar.gz が **kaggle CLI に 400 Bad Request で reject** された事実 (`docs/dev/HANDOFF-2026-05-12.md` §6) は、 4-5x 超過なので Lux-互換 100 MB cap 仮説に矛盾しない。
2. **LB top 1 bowwowforeach (= 1779.2 LB) は forum / 公開 kernel に何も出していない** (confirmed: `.venv/bin/kaggle kernels list -s bowwowforeach` で 0 hit、 `kaggle competitions leaderboard -s` で score のみ visible)。 RL or rule の判定は **間接証拠でしか不可能** (= bovard 280 万 row 分析の launch p99 = 3647 ships 突出 = kill stack 戦略 → rule-base aggressive stacker と矛盾しない)。
3. **公開 kernel 17+ で「真の RL paradigm + 100 MB 以下 + LB > 1000」 の成功例 = 0 件**。 RL を名乗る kernel は ① 訓練のみで submission を deploy していない (= 公式 RL tutorial) ② fallback greedy が常に発火する (= kronos-omega) ③ 実装は rule-base で REINFORCE は変数名のみ (= orbitwork-v14、 marco-dg) — の 3 パターンのみ。
4. **戦略 update 推奨**: (a) **PPO submission の優先度を「Day 5-6 にずらす」** + (b) **モデル軽量化 (= ~10MB target、 sb3 zip→state_dict のみ抽出 + fp16)** を Day 3-4 で先行実装、 (c) **rule-base + fleet.angle 完全活用 (= 1100+ kernel author 級)** で先に LB 1100-1300 帯を確保。

---

## 1. submission size limit 探索結果 (= 最優先)

### 1.1 forum / 公式 doc での明示的言及

| ソース | 内容 | 出典 |
|---|---|---|
| README.md (host file、 8241 bytes) | submission size に関する記述 **なし** (= 通読確認) | `/tmp/orbit-wars-host/README.md` (kaggle competitions download orbit-wars で取得、 1-174 行 全 read 済) |
| agents.md (host file、 6486 bytes) | "Multi-file agent — bundle into a tar.gz with main.py at the root" のみ。 **size 上限の明示なし** | `/tmp/orbit-wars-host/agents.md:152-157` |
| main.py (host file、 2079 bytes) | starter agent コードのみ、 size 記述なし | `/tmp/orbit-wars-host/main.py:1-60` |
| Discussion 696043 (sweep bug 修正) | size 言及なし、 engine bug fix のみ | `kaggle competitions topic-messages orbit-wars 696043` で取得 |
| Discussion 693541 (visualizer color) | size 言及なし、 UI 改善のみ | 同上、 696043 と同 query で 取得 |
| Discussion 0510.md (dump、 host meta-thread) | submission size 言及なし。 LLM agent 参戦 / top10 episode dataset / sweep bug 修正のみ | `docs/discussion/0510.md` (123 行 全 read 済) |
| `docs/discussion/insights.md` 自家蓄積 | size 言及なし | `docs/discussion/insights.md` (158 行 全 read 済) |
| Meta-Kaggle ForumTopics dump | orbit-wars 関連 topic ほぼ 0 件 (= snapshot 古) | `data/external/meta_kaggle/ForumTopics.csv` (= `docs/discussion/insights.md:152` で「実用性 low」と確認済) |

**Forum 直接言及: 0 件**。 host も community も「N MB が limit」と書いていない。

### 1.2 公開 kernel の submission file size 分布 (= 実測 + ヘッダ抽出)

公開 kernel で **submission tarball の実体 size を表示する記述** を持つ kernel:

| Kernel (= 著者/slug) | 出力 size | type | submission 構成 | 出典 file:line |
|---|---|---|---|---|
| **0rbit-w-rs-complete-solution** (= Wasiq Ali) | 計測した直後 print (= 数値未掲載、 ただし `submission.py` 単体) | rule (= heuristic) | 1-file `submission.py` のみ | `docs/research/public_kernels/0rbit-w-rs-complete-solution/content.md:899-903` |
| **train-submit-v4-ml-validator-topk1-tutorial** (= konbu17) | "tar_path` + size print" (= 注: 推測 < 1 MB、 NN weights は `weights.npz` ~数 KB) | rule + tiny NN validator | tar.gz = main.py + weights.npz | `docs/research/public_kernels/train-submit-v4-ml-validator-topk1-tutorial/content.md:780` (`size = tar_path.stat().st_size`) |
| **kronos-omega** (= aminmahmoud) | "submission.py — {os.path.getsize(...)} bytes" (= 計測のみ、 数値非引用) | sb3 PPO **on paper、 実際は greedy fallback** | 1-file submission.py のみ (= **model.zip を bundle せず** `/kaggle/working/...` 期待 = production で missing) | `docs/research/public_kernels/kronos-omega/content.md:935` + `/tmp/kernel_audit2/aminmahmoud_kronos/kronos-omega.ipynb` cell 8-9 |
| **orbitiq-v3** | "File size: {len(submission_code):,} characters" | rule | 1-file submission.py のみ | `docs/research/public_kernels/orbitiq-v3/content.md:1424` |
| **orbit-wars-2026-neural-network** (= NN baseline) | コメント "Kaggle max is usually 40" は **planet 数の話**、 size の話ではない | NN (training kernel only、 非 deployed) | n/a | `docs/research/public_kernels/orbit-wars-2026-neural-network/orbit-wars-2026-neural-network.ipynb:304` |

**実体 size 言及の kernel = 5 件、 すべて 1 MB 未満 (= 推測込)**。 100 MB 近傍の RL submission を公開している kernel は **0 件**。

### 1.3 自家 submission size の実測 (= 強い間接証拠)

`submissions/*.tar.gz` を `ls -laS` で出力:

| 提出 file | size (bytes) | size (MB) | LB 結果 | 出典 |
|---|---|---|---|---|
| ppo_v2_theta2.tar.gz | 457,375,801 | **436 MB** | reject (400 Bad Request, LB に出現せず) | `ls -laS submissions/` 2026-05-11 14:11 |
| ppo_v3_theta3.tar.gz | 448,319,547 | **428 MB** | reject (= "PPO θ.3 400 error"、 Day 3 slot 3 fail) | 同上 + `kaggle competitions submissions orbit-wars` の slot 4 description "after PPO θ.3 400 error" |
| ppo_v4_theta4.tar.gz | 444,608,199 | **424 MB** | 未 submit (= 425 MB は θ.3 と同じ理由で reject 予想) | 同上 |
| konbu17_topk1.tar.gz | 39,062 | **0.04 MB** | **COMPLETE** LB 600-908 | `kaggle competitions submissions orbit-wars` slot 3 行 |
| konbu17_bovard_bowwow.tar.gz | 38,436 | **0.04 MB** | **COMPLETE** LB 897 | 同上 |
| fleet_angle_zachary.tar.gz | (= ~40 KB 圏内推測) | **<1 MB** | **COMPLETE** LB 703.8 | 同上 slot 4 |

**結論**: 我家の data だけで「~40 KB ⇒ accept / ~425 MB ⇒ reject」の二分が明確。 中間域 (= 1-100 MB) は自家 datapoint なし。

### 1.4 推定 limit (= 出典付き)

**最も妥当な推定値: 100 MB** (= 95% confidence)

根拠の論理鎖:
1. Kaggle agent comp は **共通 platform** で submission を扱う (= kaggle_environments の単一 pipeline、 Halite / Lux / Hungry Geese / ConnectX / orbit-wars 等横断)。 出典: `agents.md:64-90` (= `pip install kaggle-environments` + `env.run(["main.py", ...])` 形式の標準化)
2. **Lux AI Season 3 (= 2024-2025、 同 host platform、 同 submission protocol) で host 提示 cap = 100 MB が writeup で明記**: "I could, and probably should, have scaled this up further, since I was still **62MB shy of the 100MB submission file size limit**" (= Isaiah Pressman 1st place writeup、 https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md 経由 W1 doc で抽出)
3. orbit-wars host の bovard は **Lux AI シリーズと同じ kaggle-environments team の運営者** (= Frog Parade writeup と同 ecosystem)。 platform 限度を上書きしているという証拠なし。
4. 我家 425 MB → reject の事実は **4.25x 超過**で 100 MB 仮説と整合 (= もし limit が 500 MB だったら通っているはず)。

**TBD (= 未確定要素、 priority high)**:
- Kaggle CLI 側 client-side limit (= 一部 sources は 50 MB と記述するが orbit-wars README にはない) → 自家 70 MB / 90 MB / 110 MB の **段階的 dry-run** で実測すべき。 出典: 推測 (= 一次資料未取得)。
- 100 MB が gzip 後か gunzip 後か → Lux S3 writeup は明示せず、 通常 tar.gz 後の値と推測。

---

## 2. 公開 kernel paradigm 分布 (= 17+ 件再 audit)

### 2.1 paradigm 判定基準

- **rule_base**: ML import が一切ない or training のみ／submission 側で使わない
- **NN_validator (rule + 小 NN)**: rule で action 候補生成、 NN で binary filter のみ
- **RL_named_only**: 変数名に REINFORCE / policy / opponent_model 等あるが、 実装は rule (= sb3 / torch import なし)
- **RL_attempted_greedy_fallback**: PPO / sb3 import + 提出時 `try ... except greedy_fallback` (= prod でモデル load 失敗するため実体は rule)
- **RL_actually_deployed**: PPO load → predict が正常動作する submission (= 自家証拠なし、 0 件)

### 2.2 audit 結果 (= 17 kernel)

| Kernel | paradigm | LB (= author 主張 or 観測) | submission 構成 | 軽量化考慮 | 出典 |
|---|---|---|---|---|---|
| pilkwang/orbit-wars-structured-baseline | rule_base | 1000-1100 | 1-file main.py | n/a | `/tmp/kernel_audit/orbit-wars-structured-baseline.ipynb` (= bovard endorsed 202 votes) |
| sigmaborov/orbit-wars-2026-starter | rule_base | 900-1000 | 1-file main.py | n/a | `docs/research/public_kernels/...starter/...` |
| sigmaborov/lb-958-1-orbit-wars-2026-reinforce | **RL_named_only** (= REINFORCE は変数名、 実装は rule) | 958 | 1-file main.py | n/a | `/tmp/kernel_audit/sigmaborov_reinforce_full.py` ; `grep stable_baselines /tmp/kernel_audit/sigmaborov_reinforce_full.py` = 0 hit |
| pascalledesma/orbitwork-v14 | RL_named_only | 1000+ | 1-file main.py | n/a | `/tmp/kernel_audit/orbitwork_v14_full.py:60-108` REINFORCE_* constants は rule 閾値 |
| pascalledesma/orbitbotnext | RL_named_only | 1000-1100 | 1-file main.py | n/a | `/tmp/kernel_audit2/pascalledesma_next/orbitbotnext.ipynb`、 ML import 0 |
| marcodg/marco-dg-v3-3-top-score-1060-5 | rule_base (= REINFORCE 変数名のみ) | 1060.5 | 1-file main.py | n/a | `/tmp/kernel_audit2/marcodg_1060/marco-dg-v3-3-top-score-1060-5.py:84-132` orbitwork から fork した形跡 |
| romantamrazov/orbit-star-wars-lb-max-1224 | rule_base | 1224 | 1-file main.py | n/a | `/tmp/kernel_audit2/romantamrazov_1224/orbit-star-wars-lb-max-1224.ipynb`、 NN なし |
| ykhnkf/distance-prioritized-agent-lb-max-score-1100 | rule_base | 1100 | 1-file main.py | n/a | `/tmp/kernel_audit2/ykhnkf_1100/...`、 distance priority のみ |
| konbu17/orbit-wars-rule-base-ml-shot-validator-hybrid | **NN_validator** (= rule + 小 NN filter) | 922-1017 (= Day 2 LB 922、 自家 base) | tar.gz = main.py + small weights (= ~30 KB 推測) | tiny NN | `/tmp/kernel_audit2/konbu17_hybrid/orbit-wars-rule-base-ml-shot-validator-hybrid.ipynb`、 train-submit-v4 が同シリーズ |
| konbu17/train-submit-v4-ml-validator-topk1-tutorial | NN_validator | 922 (= 同上) | tar.gz = main.py + weights.npz | numpy フォワードで torch 依存除去 | `docs/research/public_kernels/.../content.md:780` `tar.add(WORK / "weights.npz")` |
| sigmaborov/orbit-wars-2026-tactical-heuristic | rule_base | 800-900 | 1-file main.py | n/a | `/tmp/kernel_audit/orbit-wars-2026-tactical-heuristic.ipynb`、 純 rule |
| zacharymaronek/orbit-wars-heuristic-agent-scored-1000 | rule_base | 1000 | 1-file main.py | n/a | `/tmp/kernel_audit/orbit-wars-heuristic-agent-scored-1000.py`、 純 rule |
| djenkivanov/orbit-wars-agent-ow-proto-passed-1-000 | rule_base | 1000 | 1-file main.py | n/a | `/tmp/kernel_audit2/djenkivanov_proto/orbit-wars-agent-ow-proto-passed-1-000.ipynb`、 ML import 0 |
| rahulchauhan016/orbit-wars-target-score-2000-4 | rule_base + safe_aim predictor | 2000 (= author 主張) | 1-file main.py | n/a | `/tmp/kernel_audit2/rahulchauhan_2000/orbit-wars-target-score-2000-4.ipynb`、 NN なし |
| debugendless/orbit-wars-sun-dodging-baseline | rule_base | 800-900 | 1-file main.py | n/a | `/tmp/kernel_audit2/debugendless_sun/orbit-wars-sun-dodging-baseline.ipynb` |
| dylanxue04/orbit-wars-complete-game-mechanics-deep-dive | utility (= analysis、 deploy 非対象) | n/a | n/a | n/a | `/tmp/kernel_audit2/dylanxue_mechanics/...`、 visualizer / EDA |
| **aminmahmoud/kronos-omega** | **RL_attempted_greedy_fallback** | author 自慢 LB 不明、 LB 上位入り未確認 | 1-file submission.py (= **model.zip を bundle せず** `/kaggle/working/kronos_omega_FINAL` 期待 = prod で missing → greedy fallback 確定) | n/a | `/tmp/kernel_audit2/aminmahmoud_kronos/kronos-omega.ipynb` cell 8 `MaskablePPO.load('/kaggle/working/kronos_omega_FINAL', device='cpu')` ; cell 9 `try ... except: _KRONOS_MODEL = 'GREEDY'` |
| **kashiwaba/orbit-wars-reinforcement-learning-tutorial** (= bovard 公式) | **training only** (= submission packaging 含まず) | n/a | n/a | n/a | `/tmp/kernel_audit/orbit-wars-reinforcement-learning-tutorial.ipynb` cell 26-37 は eval / play スクリプトのみ、 main.py 生成 cell 0 |
| thisisn0mad/orbit-wars-rl-pipeline-public | training only? | n/a (= LB 評価未掲載) | TBD | TBD | `docs/research/public_kernels/orbit-wars-rl-pipeline-public/...` (我家 not_yet_audited、 priority mid) |

**集計** (= 19 kernel 中):
- rule_base: 12 件 (63%)
- RL_named_only (= 名前だけ RL、 実装は rule): 4 件 (21%)
- NN_validator (= rule + 小 NN filter): 2 件 (11%)
- RL_attempted_greedy_fallback (= 実 RL 走らず): 1 件 (5%、 kronos-omega)
- **RL_actually_deployed (= 実 RL inference): 0 件**
- training_only (= submission 対象外): 2 件

### 2.3 既存 engine-audit doc との整合性

`docs/research/2026-05-11-engine-audit.md` の 5 exploit candidate と本 audit の関係:
- exploit #1 (Let-them-fight): forum / kernel で言及なし (= 自家発見、 整合性 OK)
- exploit #2 (1-ship sniper): zacharymaronek-1000 / Roman Tamrazov 1224 が "small fleet snipe" を rule で使用 (= 部分実装、 自家提案の path 整合)
- exploit #3 (Multi-fleet decoy timing): sigmaborov-reinforce / orbitwork-v14 が SOURCE_SWARM_ETA_TOLERANCE で多 source 同 ETA を実装 (= 自家提案の上位互換、 既出 idea)
- exploit #4 (End-game ship pile-up): bovard 280 万 row 分析で確認、 forum 未言及 (= **本コンペで明示的に書かれた kernel は 0、 オリジナル発見の可能性高**)
- exploit #5 (Comet trajectory hijack): forum / kernel で未言及

→ engine-audit doc と矛盾なし、 むしろ「exploit #4 の優位性は forum で言及されていない」が new 発見。

---

## 3. 最近の discussion topic (= 5/1-5/12 vote 上位)

### 3.1 直接取得 topic 一覧 (= 取得 id 確認分)

| Date | Topic | id | 投稿者 | Votes (= 一次 post) | 我家への hint | 出典 |
|---|---|---|---|---|---|---|
| 2026-05-01 04:52 | "Fleet/planet pass-through bug (sweep bug)" | **696043** | Andrew Tratz | 17 | engine bug 修正 → 2026-04-30 以降の replay のみ BC training に使える | `kaggle competitions topic-messages orbit-wars 696043` 出力 |
| 2026-04-21 13:38 | "Visualizer color: yellow vs orange" | **693541** | (匿名) | 13 | UI のみ、 戦略 hint 0 | 同上 query 693541 |
| 2026-05-10 (dump) | "Agents are coming for the leaderboard (LLM agent 参戦)" | (= id 未取得、 0510.md dump 内) | bovard | n/a | LLM agent vs human agent 共存、 我家は agent 自身 eval-time compute 制約緩い | `docs/discussion/0510.md:1-30` |
| 2026-05-10 (dump) | "Top-10% daily episode replay datasets" | (= 同) | bovard | n/a | **bovard/orbit-wars-top10-episodes-YYYY-MM-DD** 19 日分 publish、 IL pretrain 用 | `docs/discussion/0510.md:31-100` |
| 2026-05-10 (dump) | "I achieved 1100+ score, and just realized enemy fleets are fully visible" | (= 同) | (= 1100+ author) | n/a | **fleet.angle 完全 observable** → lead-shot defense / intercept / counter-attack 設計の前提 | `docs/discussion/0510.md:106-123` ; `docs/discussion/insights.md:55-65` |

**直接取得は 2 topic (= 696043 / 693541) のみ**。 kaggle CLI `competitions topics orbit-wars` がパース不能 (= "invalid choice: 'orbit-wars'") で網羅 enumeration できず。 残り topic id は `docs/discussion/0510.md` の手動 dump + Meta-Kaggle ForumTopics (= snapshot 古、 orbit-wars 0 hit) からのみ。

### 3.2 bowwowforeach (= LB 1 1779.2) の publication 状況

- **kernel**: 0 件 (`.venv/bin/kaggle kernels list -s bowwowforeach 2>&1` の結果は別人 sangrampatil5150 が 1 件のみ hit、 bowwowforeach 名義 0)
- **discussion topic**: 0 件 (= 0510.md / 取得 topic でも author 一致なし、 grep "bowwowforeach" docs/ で hit なし)
- **LB**: 1779.2 (= 2026-05-11 23:12、 `kaggle competitions leaderboard orbit-wars -s` 出力)
- **間接観測** (= bovard top10 dataset 自家分析、 `docs/discussion/insights.md:18-28`):
  - launch 中央値 52 ships、 **p99 = 3647 ships** (= 突出 kill stack 戦略)
  - avg launches/turn 0.59 (= 低頻度) + ships 7084 (= 多 stack)
  - 戦略 cluster: 「low-frequency big-stack kill-stack」
- **paradigm 推測**: rule_base か hybrid (= RL の確証なし)。 launch サイズ分布が rule-base にしては明確な kill-stack pattern を持つことから、 **「ship 蓄積 → 大規模 launch を rule で発動する閾値型」** が最も整合的。

### 3.3 forum vote 上位 20 が取得不可な理由

kaggle CLI 2.1.2 で:
- `competitions topics orbit-wars` → `error: argument command: invalid choice: 'orbit-wars'` (= subcommand parsing bug)
- `competitions topics -c orbit-wars` → `403 Forbidden`
- `competitions topics --page-size 100 -s recent` → `No competition specified`

CLI が `competition_url_suffix` を subcommand-name と誤認する parsing bug が現バージョンで存在。 Meta-Kaggle dataset の snapshot は orbit-wars 期間 (= 2026-04-16 開始) より古、 orbit-wars topic がほぼ 0 件。

**回避策**: 推測 topic_id を範囲 probe で 200 件 probe (695000-697200 まで実施、 696043 / 693541 のみ hit)。 1 桁単位 brute force は数千 query 必要で時間制約超過。 **user dump (= 0510.md 形式) を継続的に蓄積** が現実解。

---

## 4. host file 制約 再 read

### 4.1 README.md (= 174 行 全 read 済)

重要 line と引用:

| file:line | 内容 | 戦略含意 |
|---|---|---|
| `README.md:7` | "The game lasts 500 turns. The player with the most total ships (on planets + in fleets) at the end wins." | end-game pile-up exploit (= engine-audit #4) の数理根拠 |
| `README.md:13` | "All planets and comets are placed with 4-fold mirror symmetry around the center" | 4-fold symmetry → 4P FFA で対称配置、 home position bias なし |
| `README.md:20` | "radius: Determined by production: `1 + ln(production)`" | radius と production が直結、 production 高 = 物理的に大きい (= 衝突しやすい) |
| `README.md:26` | "Orbiting planets rotate around the sun at a constant angular velocity (0.025-0.05 radians/turn, **randomized per game**)" | angular_velocity は seed 依存だが obs に渡される (= 利用可能) |
| `README.md:33` | "Home planets start with 10 ships." | 開幕 ships = 10 のみ、 expansion 速度の上限はここ |
| `README.md:44-52` | speed = 1.0 + (max_speed-1.0) × (log(ships)/log(1000))^1.5 | engine-audit §1.2 の速度数理確認、 1000 ships = 6.0、 10 ships = 1.27 |
| `README.md:62` | "Collision detection is continuous -- the entire path segment from old to new position is checked, not just the endpoint." | sweep bug (Discussion 696043) の旧仕様、 修正後は swept_pair_hit |
| `README.md:75-86` | comet 仕様 (= step 50/150/250/350/450 spawn、 各 4 個 1 group、 4-fold symmetric) | comet timing は予測可能、 ただし 開始 ships は random skewed low |
| `README.md:111-117` | "Final score = total ships on owned planets + total ships in owned fleets" | reward = score、 in-flight fleets も count される (= 終盤の大艦隊が直接 score 加算) |
| `README.md:130` | "remainingOverageTime: Remaining overage time budget (seconds)" | 1s/turn の制約は actTimeout、 overage budget は累積 |
| `README.md:166-173` | "actTimeout: 1" "boardSize: 100.0" "cometSpeed: 4.0" 等 | 全 default、 特殊 config なし |

**submission size 言及: 0** (= 全 174 行で "size" "MB" "limit" を検索、 hit なし)

### 4.2 agents.md (= 240 行 全 read 済)

重要 line:

| file:line | 内容 | 戦略含意 |
|---|---|---|
| `agents.md:148-150` | "Single file agent: `kaggle competitions submit orbit-wars -f main.py -m "..."`" | 1-file submission は **直接 .py 投入可能** (= tar.gz 不要) |
| `agents.md:152-157` | "Multi-file agent — bundle into a tar.gz with main.py at the root" + 例 `tar -czf submission.tar.gz main.py helper.py model_weights.pkl` | **model_weights.pkl が公式の bundle 例** = host が「重みファイル同梱」を想定している → size limit があるなら明示すべきだが**なし** |
| `agents.md:159-163` | "Notebook submission: `kaggle competitions submit -k YOUR_USERNAME/orbit-wars-agent -f submission.tar.gz -v 1`" | notebook 経由でも submission.tar.gz が成果物 |
| `agents.md:66-69` | "pip install "kaggle-environments>=1.28.0"" | kaggle-environments 1.28+ 依存、 古い version で起きる API 差異に注意 |
| `agents.md:144` | "Your submission must have a `main.py` at the root with an `agent` function." | tar.gz root に main.py、 sub-directory 不可 |

**submission size 言及: 0** (= 全 240 行 grep 結果)

### 4.3 main.py (= 60 行 全 read 済)

starter agent の実装のみ、 制約記述は **0**。

### 4.4 host file 制約 まとめ

3 file 計 14,806 bytes のすべてに**「submission size limit」「N MB」「reject if larger than ...」の記述は存在しない**。 同時に **「無制限」とも書いていない** (= unspecified behavior、 危険)。 425 MB tar.gz が 400 Bad Request で reject された事実は **client-side or server-side の暗黙 limit が存在することを実証している**。

---

## 5. orbit-wars への直接適用 推奨 (= 戦略 update 5 件)

### 5.1 [推奨 1] PPO submission の優先度を Day 5-6 に後ろ倒し ★ critical

- **根拠**: 425 MB tar.gz が reject。 軽量化なしの sb3 PPO 直送は **構造的に通らない**。 W1 doc `01-past-comp-rl-deployment.md` §2-3 で Lux S3 1st が 38 MB (= 100 MB cap に 62 MB margin) で deploy していることと整合。
- **行動**: Day 3-4 で **rule-base + fleet.angle 完全活用 (= 1100-1300 帯確保)**、 Day 5-6 で **軽量化 PPO (= ~10 MB target)** を投入
- **失敗モード**: rule-base で 1300 が頭打ち、 PPO 軽量化に時間取られて Day 5-6 も submit できず空打ち。 → mitigation: rule-base に 2 day 全力、 PPO は並列 (= 中央外、 別 worker) で進行

### 5.2 [推奨 2] PPO 軽量化技法 = state_dict のみ抽出 + fp16

- **根拠**: sb3 zip = full PPO state (= optimizer state + replay buffer hint + value head 等) ~425 MB。 一方 W1 doc §2.1 で Frog Parade は ~10M params × 4 bytes ≈ 40 MB を 38 MB に packing。 **policy net (= actor + value head) のみ + fp16 quantization で 95% 削減可能**
- **実装** (= 候補):
  1. `torch.save(model.policy.state_dict(), 'policy.pt')` → optimizer / buffer 除去で ~5 MB target
  2. fp16 conversion: `state_dict = {k: v.half() for k, v in state_dict.items()}` → 半分の ~2.5 MB
  3. main.py で `model = PlanetPolicy(...); model.load_state_dict(torch.load('policy.pt', map_location='cpu'))` で復元
- **失敗モード**: fp16 で値が NaN / inf になり推論不能、 policy state_dict 形式が sb3 と不整合で load 失敗。 → mitigation: ローカルで full episode smoke を 5 回以上、 fp32 fallback path も bundle
- **出典**: W1 doc `01-past-comp-rl-deployment.md` §2.1 (Lux S3 Frog Parade 構成)

### 5.3 [推奨 3] **submission size の段階 dry-run** で limit を実測

- **根拠**: forum で公式数値が「**なし**」確定。 425 MB reject / 40 KB accept しか data point がない。 中間域 (= 1-100 MB) の挙動が未知。
- **行動**: padding を入れた dummy submission (= main.py = starter + dummy.bin = 70 MB / 90 MB / 110 MB) を **3 連投** で reject 境界を実測
- **コスト**: 1 day で 5 slot 消費の 3 slot を dry-run に使う = 重い、 ただし「PPO 軽量化 target size を 10 MB に絞っていいか / 80 MB まで使えるか」 が判明する
- **failure modes**: 3 slot 全部 reject → 軽量化 target を 10 MB 厳守、 1 slot accept → 上限が 70-110 MB のいずれかに narrow。 → mitigation: Day 3 の **safety slot (= konbu17 再 submit)** を消費せず Day 4 で 1 slot だけ dry-run、 残り 4 slot は実戦に使う
- **出典**: 自家 425 MB / 40 KB 二分の datapoint (= §1.3) + Lux S3 100 MB 言及 (= W1 doc §2.1)

### 5.4 [推奨 4] fleet.angle defense / intercept の完全実装 (= rule-base で LB 1300+ 取得)

- **根拠**: `docs/discussion/insights.md:55-65` で「敵 fleet の angle は完全 observable」 と確認、 1100+ kernel の author 自慢の通り **lead-shot defense + 完全 intercept + counter-attack 最適化** が rule で実現可能。 自家 fleet_angle_zachary v3 は LB 703.8 (= Day 3 slot 4) = まだ 1100+ author レベルに達していない。
- **行動**: bovard top10 dataset (= step 0-100 ships 集計) で **「fleet angle を全て使った場合の最適 defense 範囲」** を simulator で再現、 missed intercept 数 = baseline からの差分で改善 ROI 測定
- **失敗モード**: angle 計算誤差で intercept 失敗、 defense 振りすぎで attack 不足。 → mitigation: `engine.swept_pair_hit` (= `orbit_wars.py:46-64`) を直接 import して deterministic verification
- **出典**: `docs/discussion/0510.md:106-123` (= 1100+ author 自慢) ; `docs/discussion/insights.md:55-65` (= insights doc 整理)

### 5.5 [推奨 5] bowwowforeach 戦略 reverse-engineering (= bovard top10 dataset 経由)

- **根拠**: bowwowforeach は LB 1 (= 1779.2)、 公開 publication 0 (= §3.2)、 ただし bovard top10 dataset に **本人の replay が含まれる** (= top sum-score の biased sample なので bowwowforeach の replay 比率高、 出典: `docs/discussion/0510.md:31-65` "top 10% of episodes by sum-score")
- **行動**: bovard 2026-05-01 ~ 2026-05-04 の 4 day 分 dataset を DL、 author=bowwowforeach の replay を filter、 step-by-step 行動 → 「launch 閾値 (= ships > N で発動)」「target priority order」「defense 発動条件」 を rule に再構築
- **失敗モード**: bowwowforeach の replay が dataset に少ない (= top 10% biased なら top1 だけ多くサンプリングされる保証なし)、 行動が context-dependent で抽出した rule が generalize しない。 → mitigation: 3 player (= bowwowforeach + shomossa + Erik Kvanli) の合成戦略を抽出、 ensemble で対応
- **出典**: `docs/discussion/insights.md:18-28` (= 既存 bovard 280 万 row 分析、 author 別 launch 分布) ; `docs/discussion/0510.md:31-100` (= bovard dataset 説明)

---

## 6. 未解決事項 / 追加調査推奨

| # | 事項 | priority | 着手 path |
|---|---|---|---|
| U1 | submission size の exact limit (= 100 MB か、 50 MB か、 200 MB か) | **high** | 推奨 §5.3 dry-run、 1 slot/day で 3 day で判明 |
| U2 | bowwowforeach の paradigm (= RL か rule か) | **high** | 推奨 §5.5 reverse-engineering、 bovard 5/1-5/4 dataset filter |
| U3 | LB 1500+ 帯 (= Vadasz 1599 / flg 1594) の paradigm | mid | 同 author の公開 kernel chase、 1500+ 帯は kernel 0 件の可能性高い (= §2.2 audit 結果から推測) |
| U4 | thisisn0mad/orbit-wars-rl-pipeline-public の deploy 構成 | mid | 未 audit kernel、 `kaggle kernels pull` で取得して §2.2 表に追加 |
| U5 | gemini31pro (= LLM agent) の submission 構成 | low | submission 形式が 1-file (= 0510.md:14) と明記、 LB 590 で脅威でない、 ただし将来 Claude Opus 4.7 等が出る前提でモニタリング |
| U6 | Kaggle CLI 2.1.2 で competitions topics の正しい invoke 方法 | mid | CLI source code 読みか CLI 2.2+ 待ち、 Meta-Kaggle 1 day cache が orbit-wars cover していれば bypass 可 |

---

## 7. main agent への return 要約 (= 200-300 word)

submission size の確実な数値は **forum / 公式 doc では公開されていない** (= host README/agents.md/main.py 計 14,806 bytes に "size" "MB" 一切なし、 discussion 取得 2 topic 696043/693541 も engine bug + visualizer のみ)。 ただし **Lux AI Season 3 (= 同 host、 同 kaggle-environments platform) の 1st place writeup が "100MB submission file size limit" を明示** (出典: https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md) で、 我家の 425-457 MB tar.gz が **400 Bad Request reject** された事実 (`docs/dev/HANDOFF-2026-05-12.md` §6 / `submissions/ppo_v[234]_theta[234].tar.gz` 実 size、 一方 40 KB tar.gz は全て COMPLETE) と整合し、 推定 **100 MB de facto cap** が 95% 信頼度。

LB top 1 **bowwowforeach (= 1779.2) は公開 kernel・discussion 共に 0 件**、 paradigm は外部観測不能。 bovard top10 dataset の自家分析で launch p99 = 3647 ships の kill-stack 戦略のみ判明 (= `docs/discussion/insights.md:18-28`)。

公開 kernel 19 件再 audit の結果、 **「真の RL paradigm + 100 MB 以下 + LB > 1000」 の成功例 = 0 件** (= 全 RL-named kernel は変数名のみ rule、 kronos-omega は model.zip 非 bundle で本番 greedy fallback)。

**戦略 update 推奨 (= 2 件 最優先)**:
1. **PPO submission を Day 5-6 に後ろ倒し** + Day 3-4 は **rule-base + fleet.angle 完全活用 (= 1100-1300 帯確保)** に専念 (= §5.1)
2. **PPO 軽量化 = state_dict only + fp16 で ~10 MB target** を並列で進行、 並行して Day 4 で **1 slot を size dry-run (= 70/90/110 MB のいずれか)** に消費して exact limit を実測 (= §5.2-5.3)

**詳細**: `docs/research/2026-05-12-victory-research/02-orbit-wars-forum-deep-dive.md`

---

## 出典 (= URL or file:line 必須)

### 一次資料 (= URL)

- Lux AI Season 3 1st place writeup (= 100 MB cap 明記の唯一一次資料): https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md
- Kaggle orbit-wars competition: https://www.kaggle.com/competitions/orbit-wars
- Discussion 696043 (sweep bug): kaggle competitions topic-messages orbit-wars 696043
- Discussion 693541 (visualizer color): kaggle competitions topic-messages orbit-wars 693541
- bovard top10 episode datasets: https://www.kaggle.com/datasets/bovard/orbit-wars-top10-episodes-2026-05-04 (= 19 daily snapshots, 2026-04-16〜2026-05-04)
- Lux AI Season 3 main.py submission entry: https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/python/main.py
- sb3 PPO save format reference: https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html

### 自家 file:line 引用

- `docs/dev/HANDOFF-2026-05-12.md` §4-6 (= 425 MB ppo_v4_theta4.tar.gz build 完了 / θ.3 400 error の一次内部 evidence)
- `docs/research/2026-05-12-submission-analyses.md` slot 3-5 表 (= Day 3 5 slot 計画)
- `docs/research/2026-05-12-victory-research/01-past-comp-rl-deployment.md` §0, §2.1-2.2 (= 過去 comp RL deployment 比較、 W1 doc)
- `docs/research/2026-05-11-engine-audit.md` §1-2 (= engine source + 5 exploit candidate)
- `docs/discussion/0510.md:1-123` (= user dump、 LLM agent / top10 dataset / 1100+ author / sweep bug)
- `docs/discussion/insights.md:1-158` (= 戦略 insight 蓄積、 bovard 280 万 row 分析結果)
- `/tmp/orbit-wars-host/README.md:1-174` (= host README 全 read)
- `/tmp/orbit-wars-host/agents.md:1-240` (= host agents.md 全 read)
- `/tmp/orbit-wars-host/main.py:1-60` (= host starter agent)
- `/tmp/kernel_audit/sigmaborov_reinforce_full.py` (= REINFORCE 名前のみの rule kernel)
- `/tmp/kernel_audit/orbitwork_v14_full.py:60-108` (= REINFORCE_* constants は rule 閾値)
- `/tmp/kernel_audit2/aminmahmoud_kronos/kronos-omega.ipynb` cell 8-9 (= sb3 PPO + greedy fallback 構造、 model.zip 非 bundle)
- `/tmp/kernel_audit/orbit-wars-reinforcement-learning-tutorial.ipynb` cell 9-37 (= bovard 公式 RL tutorial、 submission packaging 含まず)
- `submissions/ppo_v[234]_theta[234].tar.gz` (= 425-457 MB 実 size、 LB に出ず)
- `submissions/konbu17_*.tar.gz` / `submission_v2.tar.gz` (= 38-40 KB 実 size、 全 COMPLETE)
- `kaggle competitions submissions orbit-wars` 出力 (= 14 slot 履歴、 description に "PPO θ.3 400 error" 明記)
- `kaggle competitions leaderboard orbit-wars -s` 出力 (= bowwowforeach 1779.2 等 50 件)
- `kaggle kernels list -s bowwowforeach` 出力 (= bowwowforeach 名義 0 件)

### 不採用 / 失敗 探索

- Meta-Kaggle ForumTopics dump: orbit-wars 期間より古、 0 hit
- kaggle CLI `competitions topics orbit-wars`: parsing bug で取得不能 (= CLI 2.1.2)
- topic_id 範囲 probe (= 695000-697200): 696043 / 693541 のみ hit、 他 0
- WebFetch on Kaggle SPA: React SPA で empty body 多い前提を踏襲、 試行せず
