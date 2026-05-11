# Submission analyses — 2026-05-13 (Day 4)

> 共通 CLAUDE.md §8.1 item 9 (= 「随時やれ」 ルール) に従い、 各 submit LB 反映 30 分以内に append。
> Plan ref: `.criteria/kaggle-orbit-wars-day4-submit-2026-05-13.yaml`
> Roadmap: `docs/strategy/2026-05-11-victory-roadmap.md` (= P1 Day 4)
> Handoff: `docs/dev/HANDOFF-2026-05-12.md` §6

---

## Day 4 batch (= 5/13 09:00 JST reset 直後 5 件、 09:01-09:04 JST submit 予定)

### サマリ表 (= submit 後 30 分 + 24h 後 resampling で値を埋める)

| Slot | Submission ID | File | Initial LB (09:30) | 1h 後 (10:30) | 24h 後 resample (5/14 09:00) | Expected LB | Diff vs Expected | Ratio (LB/Exp) |
|---|---|---|---|---|---|---|---|---|
| 1 | TBD | (Day 3 best file, env DAY3_BEST_FILE で確定) | TBD | TBD | TBD | (Day 3 LB) | TBD | TBD |
| 2 | TBD | fleet_angle_zachary_v3.tar.gz | TBD | TBD | TBD | 1100-1300 (= v3 = main rule paradigm) | TBD | TBD |
| 3 | TBD | fleet_angle_zachary_v5.tar.gz | TBD | TBD | TBD | 1100-1400 (= v5 = bovard 数値駆動 step 300+ 3.4x boost) | TBD | TBD |
| 4 | TBD | marcodg_topk1.tar.gz | TBD | TBD | TBD | 900-1100 (= marcodg 1060 claim + topk1 lift) | TBD | TBD |
| 5 | TBD | ppo_v4_theta4.tar.gz ★ | TBD | TBD | TBD | 1100-1400 (= IL+RL paradigm, explained_variance 0.95) | TBD | TBD |

**Expected LB 校正済 計算式** (Day 2-3 ratio σ 反映):
- 既 LB-tested は actual LB をそのまま expected に
- 新規 submit は local 4P win rate × 800-900 + 既存 paradigm との類似度補正
- Day 3 + Day 4 = 10 submit で ratio drift σ 再計算 (= AC-7)

**Day 3 後 LB best**: TBD (= 5/12 18:00 JST 反映後埋め)
**今回 best 目標**: ≥ 1200 (= Top 30 圏堅持 + RL paradigm の本気 1st datapoint)

---

### Per-submit effect isolation (= 各 source 単独効果評価)

| Slot | Source 変更 (= Day 3 比) | LB delta | est_score (local 4P %) | 真効果判定 |
|---|---|---|---|---|
| 1 (Day 3 best 再) | 同 file 再 submit | TBD | n/a | 24h resampling drift 計測 (= TrueSkill 安定値) |
| 2 (v3) | fleet.angle + end-game pile-up + Let-them-fight | TBD | TBD (smoke 確認後埋め) | rule paradigm 強化、 v0 (= fleet_angle_zachary) 比 +ROI |
| 3 (v5) | v3 + step 300+ fleet boost (bovard 3.4x) | TBD | TBD | 数値駆動 ablation = step 300+ exploit の真効果 isolate |
| 4 (marcodg+topk1) | 別 paradigm = marcodg base + topk1 wrapper | TBD | TBD | 公開 kernel claim 1060 が我家 environment で transfer するか |
| 5 (PPO θ.4) ★ | **新 paradigm = RL 本気 200k step PFSP** (explained_variance 0.95) | TBD | TBD (vs starter / vs v3 = 1 ep noise) | **RL paradigm 真評価 = bowwowforeach 1698 への path** |

---

### Smoke test 事前結果 (= 2026-05-12 08:18 JST、 local 4P 1 ep vs starter × 3、 seed=42)

`bash tools/smoke_day4.sh` 5 build 一括結果 (= ALL PASS):

| Slot | File | duration_sec | step_count | status_p0 | smoke 判定 |
|---|---|---|---|---|---|
| 1 | submission_v2 (default) | 10.824 | 195 | DONE | PASS |
| 2 | fleet_angle_zachary_v3 | 0.809 | 123 | DONE | PASS |
| 3 | fleet_angle_zachary_v5 | 0.870 | 123 | DONE | PASS |
| 4 | marcodg_topk1 | 7.505 | 152 | DONE | PASS |
| 5 | ppo_v4_theta4 ★ | 1.427 | 249 | DONE | PASS |

**観察**:
- ppo_v4_theta4 は **per-step ~0.006s** (= 1.427s / 249 step)、 Kaggle 1s/step timeout に十分 margin
- v3/v5 は seed=42 で step_count=123 同値 (= step 300+ trigger 未発火、 別 seed で AB 必要)
- marcodg_topk1 7.5s = やや slow だが < 60s margin (= topk1 wrapper の lookup cost)

出典:
- smoke test 実行ログ: `tools/smoke_day4.sh` 出力 2026-05-12 08:18 JST (= AC-5 PASS evidence)

---

### 仮説 (= submit 前)

**H1 (= 主仮説)**: PPO θ.4 (slot 5) ≥ 1100 (= IL+RL paradigm 真評価)
- 根拠: explained_variance 0.95 (= top-tier value function、 想定大幅超え)、 200k step PFSP で opponent pool 12 種、 vs starter は 1 ep noise だが pool 内 win rate は training log で healthy
- 失敗時: 200k step が依然不足、 1M step (= Day 5 θ.5) で本格 convergence。 Day 5 trigger が data-driven 判断材料に

**H2**: fleet_angle_zachary_v3 (slot 2) ≥ 1000 (= Day 3 fleet_angle base が 1100+ なら v3 で更に +)
- 根拠: end-game pile-up (= Tier 3 #4 exploit) + Let-them-fight (= Tier 3 #1) の組合せ
- 失敗時: pile-up が strong opponent に対し守備手薄を露呈、 v5 の step 300+ trigger が代替

**H3**: fleet_angle_zachary_v5 (slot 3) ≥ v3 + 50 (= step 300+ fleet boost で mid-late game の数値駆動)
- 根拠: bovard 280万 row 分析で step 300+ で fleet size 3.4x 観測、 我家 base が 1x stuck
- 失敗時: bovard top-tier 戦術が我家環境では同じ効果出ない、 v3 と差別化失敗

**H4**: marcodg + topk1 (slot 4) ≈ 900-1100 (= marcodg 1060 claim + topk1)
- 根拠: Day 2 で konbu17+topk1 が +75 LB の lift 実績、 marcodg にも transfer 期待
- 失敗時: marcodg 1060 が public kernel claim のみで実 LB 700 帯、 topk1 でも届かず

**H5**: Day 3 best 再 (slot 1) ≈ Day 3 LB ± 30 (= TrueSkill 24h 安定値)
- σ < 30 なら ratio drift 安定、 σ > 50 なら opponent shift か host rule 変更を疑う

---

### 即実行アクション (= 5/13 09:30-10:30 JST window)

1. **5/12 18:00 JST**: Day 3 LB 反映完了 → 本 doc slot 1 file 確定 (= env `DAY3_BEST_FILE` 設定)
2. **5/13 09:00 JST reset 後**: `DAY3_BEST_FILE=<path> DAY3_BEST_LB=<value> bash tools/day4_submit.sh` で 5 件一括 submit
3. **5/13 09:30 JST**: `.venv/bin/kaggle competitions submissions orbit-wars` で 5 件 status + initial LB 取得
4. **5/13 09:45 JST**: 本 doc § サマリ表 + Per-submit effect isolation を埋める
5. **5/13 10:30 JST**: 1h 後 LB 更新確認、 ratio drift σ 再計算 (= Day 3 + Day 4 = 10 submit、 AC-7)
6. **5/14 09:00 JST**: 24h resampling 値で再 update、 Day 5 1M step training (= θ.5) trigger 最終判断

---

## Next phase trigger

5/13 18:00 JST までに以下を満たせば P2 (= PPO θ.5 1M step training) Colab trigger:
- 5 件 LB initial 反映済 (= 全 status COMPLETE)
- per-submit effect isolation 表埋まる
- PPO θ.4 LB ≥ 1000 (= RL paradigm 生死判明、 1M step への投資 ROI 確認)
- ratio drift σ < 0.02 確認

ただし handoff §7 の grandmaster judgment: **option A (= 5/12 即 trigger)** 推奨。 Day 4 LB 待つと 1 day loss。

P2 plan: `.criteria/kaggle-orbit-wars-ppo-theta4-pfsp.yaml` (= θ.5 用に拡張)

---

## 出典

- Submissions API: `kaggle competitions submissions orbit-wars` 2026-05-13 09:30 JST (= TBD)
- Day 3 教訓: docs/research/2026-05-12-submission-analyses.md (= 5/12 18:00 JST 反映後)
- Smoke test result: tools/smoke_day4.sh 出力 (= AC-5 PASS evidence)
- Plan: .criteria/kaggle-orbit-wars-day4-submit-2026-05-13.yaml
- Roadmap: docs/strategy/2026-05-11-victory-roadmap.md (= P1 Day 4)
- 共通 CLAUDE.md §8.1 (= 「随時やれ」 ルール根拠) + §11 「優勝本質性」
- Handoff: docs/dev/HANDOFF-2026-05-12.md
