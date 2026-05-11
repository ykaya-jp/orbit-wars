# Victory roadmap — orbit-wars 残 43 day で LB 979 → 1700+ を狙う 3-paradigm 統合戦略

> **作成日**: 2026-05-11 (= Day 2 終盤、 Day 3 reset 5/12 09:00 JST 直前)
> **Deadline**: 2026-06-23 23:59 (= 残 43 day)
> **現状 LB best**: 979.4 (= 5/10 submission_v2、Reexel ID)
> **Top 1 LB**: 1698 (bowwowforeach)、 Top 20 = 1379+
> **必要 gap**: gold zone (= LB 1500) まで +520、 優勝 (= LB 1700) まで +720

---

## 1. 戦略選定の論理 (= brainstorm 結果)

| 路線 | 構造原理 | 採否 | 理由 |
|---|---|---|---|
| A | **PPO 真 PFSP self-history** (Lux S3 1st Frog Parade recipe) | ✅ Main | RL 系統で **優勝実例あり** (Lux S3 1st)、 θ.3 zip warm start で速度上がる、 残 43 day で完走可能 |
| B | bowwowforeach (Top 1) reverse engineer + BC | ❌ 棄却 | `kaggle kernels list --user bowwowforeach --competition orbit-wars` = **Not found** (= kernel 非公開)。 replay も他チーム不可、scrape cost 高 |
| C | **Expansion rule + Lakhindar IL ensemble + rahul_2000** (3-paradigm meta) | ✅ 後発 | bovard 280 万 row 分析の真因 (= Top tier step 100 で 5-7 planets vs 我家 1-2 planets) を直反映。 §1.3 「single paradigm では gold 不可」要件を C で完成 |
| D | **Lakhindar rank1 IL を Day 3 で datapoint 取得** | ✅ Day 3 | val acc 0.967 だが LB 未 submit = 生死不明。 1 day で本 paradigm の生死判明、 A/C と並列実行可能 |

**棄却 / 一時停止**:
- bowwowforeach reverse (B): kernel 非公開で死亡
- PPO θ.4 vs random (= 現在 4096 step 停止中の run): 「軽さ-driven」の罠、 θ.1 と重複 → 廃棄

---

## 2. 6 phase ロードマップ

各 phase 開始時に **別 plan を起票** (= `.criteria/<task-id>.yaml`)。 数値 threshold は前 phase の datapoint で校正する。

### P1 — Day 3 submit + datapoint 取得 (= 5/12 09:00 JST、 1 day)
- **Goal**: Lakhindar IL paradigm の LB 生死判明 + 既存 best (979) safety net
- **Submit 5 件**:
  1. `submission_v2.tar.gz` (= 5/10 LB 989/1017 base、 safety)
  2. `konbu17_topk1.tar.gz` (= 5/11 best 902 再 submit、 resampling 確認)
  3. `ppo_v3_theta3.tar.gz` (= PPO θ.3 = top-tier IL + rule-base mix opponent で 50k step training)
  4. `build_lakhindar_pure/main.py` (= Lakhindar IL passive、 val acc 0.967)
  5. `build_lakhindar_topk1/main.py` (= Lakhindar IL + topk1 ensemble、 IL+topk1 ablation)
- **Plan**: `.criteria/kaggle-orbit-wars-day3-submit-2026-05-12.yaml`
- **Next plan trigger**: 5/12 18:00 JST までに 5 件 LB initial 反映、 P2 plan 起票

### P2 — PPO θ.4 真 PFSP 完走 (= 5/12-5/18、 7 day)
- **Goal**: θ.3 zip warm start で PFSP self-history training 100k step、 vs konbu17 win rate ≥ 50%
- **Deliverables**:
  - `tools/train_ppo_pfsp.py` 新設 or `tools/train_ppo.py` 拡張 (= self-history pool sampler + PFSP weight w ∝ (1-winrate)²)
  - `agents/proxy/ppo_v4_theta4.zip`
  - `submissions/build_ppo_v4_theta4/`
- **Plan**: `.criteria/kaggle-orbit-wars-ppo-theta4-pfsp.yaml` (= P1 完了同時起票)
- **Next plan trigger**: 5/18 tournament gate pass → P3 plan

### P3 — Expansion rule mission 実装 (= 5/19-5/23、 5 day)
- **Goal**: Top tier の真因 (= early expansion) を rule で直解、 step 0-100 で planets ≥ 5 達成
- **Provenance**: bovard 280 万 row 分析 (CLAUDE.md 2026-05-10 lesson)、 Halite II reCurs3 / Halite IV ttvand early expansion
- **Deliverables**:
  - `src/orbit_wars/missions.py` に `ExpansionPriorityMission` クラス
  - unit test pass (= step 100 で 4P 1 episode で my planets ≥ 5、 local benchmark)
  - `submissions/build_expansion_pure/main.py`
- **Plan**: P2 完了後起票

### P4 — 3-paradigm meta-agent 統合 (= 5/24-5/30、 7 day)
- **Goal**: Expansion rule (early game) + Lakhindar IL (mid game) + PPO θ.4 (end game) の step-based blend、 local 4P win rate ≥ 60%
- **Provenance**: AlphaZero 流の phase-switcher、 Halite IV ttvand の hybrid heuristic+RL
- **Deliverables**:
  - `src/orbit_wars/meta_agent.py` (= step ベース paradigm switcher)
  - `submissions/build_meta_v1/main.py`
  - 3rd paradigm として rahul_2000 (= 公開 kernel target 2000) を Strategic adviser に組込
- **Plan**: P3 完了後起票

### P5 — submit calibration + gold zone 到達 (= 5/31-6/15、 16 day)
- **Goal**: LB ≥ 1500 (= gold zone) 達成、 ratio drift σ ≤ 0.02 安定
- **Deliverables**:
  - 日次 submit (= 1-3 件 / day) で LB 反映、 `docs/research/<date>-submission-analyses.md` に append
  - 5 submit 周期で trend coef σ + source pool ROI re-ranking
- **Plan**: P4 完了後起票

### P6 — Final 7 day polish + 2 final submit freeze (= 6/16-6/23、 7 day)
- **Goal**: LB ≥ 1700 (= 優勝圏) ターゲット、 2 final submit (= safe + risky) を 6/16 freeze
- **Constraints** (Kaggle CLAUDE.md §6):
  - 6/16 以降 architecture 変更禁止
  - submit slot 浪費禁止
  - 最後 48h は何もしない (= eyeball 確認のみ)
- **Plan**: P5 完了後起票

---

## 3. 並列 / 直列依存

| Phase | 並列実行可能 | 直列依存 |
|---|---|---|
| P1 | P2 trainer 実装と並列 | — |
| P2 | training 中に P3 設計可 | P1 datapoint で IL paradigm 生死判明 → P2 reward shaping 調整 |
| P3 | — | P2 完了 (= θ.4 zip ready) |
| P4 | — | P3 完了 (= ExpansionPriorityMission ready) |
| P5 | — | P4 完了 (= meta-agent ready) |
| P6 | — | P5 で LB 1500 安定 |

---

## 4. Kaggle CLAUDE.md 主道原則の対応

| 原則 | 適用 |
|---|---|
| §1.1 「good CV is half of success」 | `docs/research/<date>-submission-analyses.md` で各 submit 後 30 分以内 ratio calibration |
| §1.2 「Trust your CV, ただし trend coef 監視」 | ratio drift σ > 0.02 で再 calibrate (Day 2 で σ=0.13 = over-optimistic 検知済) |
| §1.3 「single paradigm では gold 不可」 | P4 で **3-paradigm meta-agent** = Expansion rule + Lakhindar IL + PPO θ.4 統合 |
| §5 「3+ paradigm mix」 | 上記 + rahul_2000 (= 公開 kernel 4th paradigm 候補) |
| §6 「最終 7 day は polish のみ」 | P6 で 6/16 freeze |
| §11 「優勝本質性 criterion」 | 各 phase plan 起票時に 5 問 (数理本質 / 優勝寄与 / 代替 / rule 耐性 / datapoint 価値) を必ず通す |

---

## 5. 失敗想定 (= reverse thinking)

| Phase | 想定失敗 | mitigation |
|---|---|---|
| P1 | Lakhindar IL LB ≤ 700 = IL paradigm dead | 1 slot のみ pure IL、 残 4 slot は safety/既存 best/PPO/IL+topk1 で 4 軸 datapoint。 dead 判明時 P3 で IL 棄却 → RL + Expansion rule 2 paradigm |
| P2 | PPO θ.4 mode collapse / sim 速度不足 | checkpoint per 1k step で rollback、 16 parallel env で 320 step/sec 確保、 entropy bonus 0.01 |
| P3 | Expansion gap が真因でない (= 単なる 結果指標) | 5/12 LB 反映後に bovard 280 万 row 再分析、 別 metric (= ship production rate, attack accuracy) を candidate に |
| P4 | step-based switcher の境界で agent 切替 noise | step boundary を fuzzy (= step 50-100 で gradual blend) にする、 OR meta-policy を ML で学習 |
| P5 | LB 1500 到達できず P6 入る | P6 polish phase で safe slot を Lakhindar+PPO+rule の純 ensemble、 risky slot で expansion rule 単独高 risk チャレンジ |
| P6 | final submit が shake-up で private LB 大幅低 | safe = CV stable + local 4P 60%+ confirmed、 risky = upside upper-bound、 2 件で dual coverage |

---

## 6. 出典

- brainstorm 結果 (本セッション 2026-05-11)
- bowwowforeach kernel 探索結果 (= `kaggle kernels list --user bowwowforeach --competition orbit-wars` = Not found)
- Lux S3 1st Frog Parade: https://www.kaggle.com/competitions/lux-ai-season-3
- AlphaStar PFSP: Nature 2019
- bovard 280 万 row dataset: https://www.kaggle.com/datasets/bovard/orbit-wars-top10-episodes-2026-05-04
- Day 2 ratio drift σ=0.13: `docs/research/2026-05-11-submission-analyses.md` § Trend coef
- ~/.claude/CLAUDE.md lessons.md [2026-05-10] orbit-wars host dataset verification skip → 17% loss
- ~/projects/kaggle/CLAUDE.md §1.3 / §5 / §11 「優勝本質性 criterion」

---

## 7. 更新履歴

- 2026-05-11 初版 (= Day 2 終盤、 Day 3 reset 前)
- (Next): P1 完了後 (= 5/12 18:00 JST) に Day 3 LB datapoint 反映と P2 plan trigger
