# Submission analyses — 2026-05-12 (Day 3)

> 共通 CLAUDE.md §8.1 item 9 (= 「随時やれ」 ルール) に従い、 各 submit LB 反映 30 分以内に append。
> Plan ref: `.criteria/kaggle-orbit-wars-day3-submit-2026-05-12.yaml`
> Roadmap: `docs/strategy/2026-05-11-victory-roadmap.md` (= P1 phase)

---

## Day 3 batch (= 5/12 09:00 JST reset 直後 5 件、 09:01-09:04 JST submit 予定)

### サマリ表 (= submit 後 30 分 + 24h 後 resampling で値を埋める)

| Slot | Submission ID | File | Initial LB (09:30) | 1h 後 (10:30) | 24h 後 resample (5/13 09:00) | Expected LB | Diff vs Expected | Ratio (LB/Exp) |
|---|---|---|---|---|---|---|---|---|
| 1 | TBD | submission_v2.tar.gz | TBD | TBD | TBD | 989 | TBD | TBD |
| 2 | TBD | konbu17_topk1.tar.gz | TBD | TBD | TBD | 922 | TBD | TBD |
| 3 | TBD | ppo_v3_theta3.tar.gz | TBD | TBD | TBD | 600-800 (= unknown) | TBD | TBD |
| 4 | TBD | fleet_angle_zachary.tar.gz | TBD | TBD | TBD | 1100-1300 (= zachary base + fleet.angle backport +100-200) | TBD | TBD |
| 5 | TBD | rudra_topk1_bowwow.tar.gz | TBD | TBD | TBD | 900-1100 (= rudra base 692 + 大 fleet +200-400) | TBD | TBD |

**Expected LB 校正済 計算式** (Day 2 ratio σ=0.13 over-optimistic 反映):
- 既 LB-tested は actual LB をそのまま expected に
- 新規 submit は local 4P win rate × 800-900 + 既存 paradigm との類似度補正

**現状 LB best**: 989.2 (5/10 submission_v2 = phase-α+β+γ konbu17 hybrid + Tamrazov 1224 + ML validator)
**今回 best 目標**: ≥ 1100 (= Top 30 圏入り、 IL paradigm 生死判明 + RL paradigm 1st datapoint)

---

### Per-submit effect isolation (= 各 source 単独効果評価)

| Slot | Source 変更 (= Day 2 比) | LB delta | est_score (local 4P %) | 真効果判定 |
|---|---|---|---|---|
| 1 (safety) | 既存 best 再 submit | TBD | n/a | 24h resampling drift 計測 |
| 2 (konbu17+topk1 再) | Day 2 と同 file 再 submit | TBD | n/a | 同上 |
| 3 (PPO θ.3) | **新 paradigm = RL** (vs Lakhindar IL + rule-base 50k step training) | TBD | TBD | RL paradigm 生死判明 |
| 4 (fleet_angle_zachary) | **NEW: zachary + fleet.angle defense backport** (Day 2 review +ROI 最大) | TBD | smoke vs starter 勝利 (= reward +1.0) | fleet.angle exploit 真効果 (= zachary 600 base から +100-500 期待) |
| 5 (rudra_topk1_bowwow) | rudra MIN_SHIPS=15 + FRAC=0.85 + topk1 | TBD | TBD | rudra paradigm 強化、 大 fleet 戦術の効果 |

---

### Smoke test 事前結果 (= 5/11 22:XX JST、 local 4P 1 ep vs starter × 3)

| Slot | File | duration_sec | step_count | status_p0 | reward_p0 | smoke 判定 |
|---|---|---|---|---|---|---|
| 1 | submission_v2 | 10.679 | 195 | DONE | (4P) | PASS |
| 2 | konbu17_topk1 | 5.719 | 127 | DONE | (4P) | PASS |
| 3 | ppo_v3_theta3 | 1.514 | 249 | DONE | (4P) | PASS |
| 4 | fleet_angle_zachary | 0.799 | 123 | DONE | **+1.0 win** | PASS |
| 5 | rudra_topk1_bowwow | 1.263 | 97 | DONE | (4P) | PASS |

**観察**:
- **fleet_angle_zachary は vs starter で勝利** (= reward +1.0、 zachary base が Day 2 で 4P 0/8 だった事実から劇的改善 signal)
- rudra_topk1_bowwow が step_count 97 で早期終了 (= 大 fleet 戦術で早期に決着)
- ppo_v3_theta3 は per-step 0.0056s = Kaggle 評価互換性安全 margin あり

出典:
- smoke test 実行ログ: `tools/smoke_day3.sh` 出力 2026-05-11
- AC-5 PASS 確認

---

### 仮説 (= submit 前)

**H1 (= 主仮説)**: fleet_angle_zachary (slot 4) ≥ 1100 (= zachary 600 base + fleet.angle defense backport で +500)
- 根拠: review-findings-day2-dawn.md「LB +100-200 期待」、 base agent.py:649-650 流の trajectory hit predict
- smoke evidence: vs starter で勝利 (= reward +1.0)、 zachary 単独 Day 2 LB 600 vs Day 4 で +500
- 失敗時: defense 強化が attack budget を圧迫 → expansion が遅れて LB 横ばい

**H2**: rudra_topk1_bowwow (slot 5) ≈ 900-1100 (= rudra 692 base + MIN_SHIPS=15 大 fleet + topk1)
- 根拠: Day 2 rudra base 692.3、 MIN_SHIPS 10→15 + FRAC 0.7→0.85 + topk1 で kovi-tier 大 fleet match
- 失敗時: home garrison 枯渇で defenseless → LB 低下

**H3**: PPO θ.3 (slot 3) ≈ 600-900 (= 50k step training は不十分、 random ベース)
- 根拠: AlphaStar / Lux S3 で convergence は 数 100k-1M step、 50k は warm-up 程度
- ただし top-tier IL + rule-base opponent で training したので random よりは強い

**H4**: konbu17+topk1 (slot 2) ≈ 950 ± 50 (= Day 2 同 file の resampling 後 LB)
- Day 2 initial 922 → 24h 後 reset で TrueSkill 安定値

**H5**: submission_v2 (slot 1) ≈ 980 ± 30 (= 既存 best safety net)
- 5/10 submit 989 → 5/11 resampling 979.4、 約 980 帯安定

---

### 即実行アクション (= 5/12 09:30-10:30 JST window)

1. **5/12 09:00 JST reset 後**: `bash tools/day3_submit.sh` で 5 件一括 submit
2. **5/12 09:30 JST**: `kaggle competitions submissions orbit-wars` で 5 件 status + initial LB 取得
3. **5/12 09:45 JST**: 本 doc § サマリ表 + Per-submit effect isolation を埋める
4. **5/12 10:30 JST**: 1h 後 LB 更新確認、 trend coef 再計算
5. **5/13 09:00 JST**: 24h resampling 値で再 update、 P2 trigger 判定 (= Lakhindar IL の真生死)

---

## Next phase trigger

5/12 18:00 JST までに以下を満たせば P2 (= PPO θ.4 真 PFSP) 本格 training 開始:
- 5 件 LB initial 反映済 (= 全 status COMPLETE)
- per-submit effect isolation 表埋まる
- Lakhindar IL paradigm の生死判明 (= slot 4 LB ≥ 700 か否か)
- ratio drift σ 計測

P2 plan: `.criteria/kaggle-orbit-wars-ppo-theta4-pfsp.yaml`

---

## 出典

- Submissions API: `kaggle competitions submissions orbit-wars` 2026-05-12 09:30 JST (= TBD)
- Day 2 教訓: docs/research/2026-05-11-submission-analyses.md
- Smoke test result: tools/smoke_day3.sh 出力 (= AC-5 PASS evidence)
- Plan: .criteria/kaggle-orbit-wars-day3-submit-2026-05-12.yaml
- Roadmap: docs/strategy/2026-05-11-victory-roadmap.md (= P1)
- 共通 CLAUDE.md §8.1 (= 「随時やれ」 ルール根拠) + §11 「優勝本質性」
