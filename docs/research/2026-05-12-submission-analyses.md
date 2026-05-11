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
| 4 | TBD | lakhindar_pure.tar.gz | TBD | TBD | TBD | 1100-1300 (= val acc 0.967 transfer 仮定) | TBD | TBD |
| 5 | TBD | lakhindar_topk1.tar.gz | TBD | TBD | TBD | 1000-1200 (= slot 4 ± topk1 effect) | TBD | TBD |

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
| 4 (Lakhindar pure) | **新 paradigm = top-tier IL** (kovi/Shun_PI BC val acc 0.967) | TBD | TBD | IL paradigm 生死判明 |
| 5 (Lakhindar + topk1) | slot 4 + topk1 wrapper | TBD | (slot 5 - slot 4) | topk1 が IL に効くか単独評価 |

---

### Smoke test 事前結果 (= 5/11 22:XX JST、 local 4P 1 ep vs starter × 3)

| Slot | File | duration_sec | step_count | status_p0 | smoke 判定 |
|---|---|---|---|---|---|
| 1 | submission_v2 | 10.488 | 195 | DONE | PASS |
| 2 | konbu17_topk1 | 5.664 | 127 | DONE | PASS |
| 3 | ppo_v3_theta3 | 1.409 | 249 | DONE | PASS |
| 4 | lakhindar_pure | 1.390 | 249 | DONE | PASS |
| 5 | lakhindar_topk1 | 1.379 | 249 | DONE | PASS |

**観察**:
- ppo_v3_theta3 / lakhindar 系は per-step 0.0056s = Kaggle 評価互換性安全 margin あり
- submission_v2 と konbu17_topk1 は step_count 早期終了 (= 195 / 127) = 勝敗早期決着 (smash phase 等)
- lakhindar_pure と lakhindar_topk1 が seed=42 で完全同一 step_count = topk1 effect が 1 ep では trivial、 LB tournament で本評価

出典:
- smoke test 実行ログ: `tools/smoke_day3.sh` 出力 2026-05-11
- AC-5 PASS 確認

---

### 仮説 (= submit 前)

**H1**: Lakhindar IL pure (slot 4) > 1100 (= IL paradigm が LB に transfer)
- 根拠: val acc 0.967 (= per-action BC accuracy)、 kovi/Shun_PI 元 LB 1480/1515
- 失敗時: per-action acc が 4P FFA win rate と非線形、 IL alone は dead = P3 で IL paradigm 棄却

**H2**: Lakhindar + topk1 (slot 5) ≈ Lakhindar pure ± 50 (= topk1 が IL に対しては効きが弱い)
- 根拠: IL agent は per-step 1 move 中心 (= 多 move 既に少ない)、 topk1 が trivial
- konbu17 (rule-base) で topk1 が +75 LB だったのは多 move base agent 限定の改善

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
