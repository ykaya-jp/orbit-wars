# Submission analyses — 2026-05-11 (Day 2)

> 共通 CLAUDE.md §8.1 item 9 (= 「随時やれ」 ルール) に従い、 各 submit LB 反映 30 分以内に append。

---

## Day 2 batch (= 9:00 reset 直後 5 件、 09:01-09:04 JST submit)

### サマリ表

| Slot | Submission ID | File | Initial LB (09:30) | 1h 後 (10:12) | Expected | Diff vs Expected |
|---|---|---|---|---|---|---|
| 1 | 52528190 | zachary main.py | 600.0 | **600.0** | 1100-1200 | -500 |
| 2 | 52528207 | rudra main.py | 692.3 | **692.3** | 1049 | -357 |
| 3 | 52528225 | konbu17_bovard_topk1.tar.gz | 679.7 | **679.7** | 1100 | -421 |
| 4 | 52528252 | konbu17_bovard_bowwow.tar.gz | 907.8 | **854.9** | 1050 | -195 |
| 5 | 52528282 | konbu17_topk1.tar.gz | 823.7 | **922.9** | 1050 | -127 |

我家 LB best: 989.2 (= 5/10 submit `submission.tar.gz` = phase-α+β+γ konbu17 hybrid + Tamrazov 1224 + ML validator)
今回 best: 922.9 (= konbu17 + topk1 wrapper) → **既存 best より低い**

### Per-submit effect isolation

| Source 変更 | LB delta | est_score (local 4P %) | 真効果判定 |
|---|---|---|---|
| zachary 単体 | 600 | 75% (= vs Rudra/Marco/orbitbotnext) | ❌ **damage** (= local 75% が LB 600 にしか transfer しない) |
| rudra 単体 | 692 | 58% | ❌ **damage** (author claim 1049 → 我家 environment で 692) |
| bovard validator + topk1 | 679 | n/a | ❌ damage (= bovard validator base 1017 → topk1 化で 679 に下がる) |
| bovard validator + bowwow patch | 854 | n/a | △ damage 軽微 |
| konbu17 + topk1 (orig validator) | 922 | n/a | ✅ best of today、 但し既存 989 を超えない |

### 仮説帰納 — 「local high → LB low」 の transfer 失敗

**仮説 H1**: local 4P tournament の opponent diversity 不足。
- 我家 benchmark = konbu17 / Marco / orbitbotnext (= 全部 LB 700-1060 帯)
- LB tournament は 200+ 多様な agent と対戦
- → local で「3 つの中堅 bot に勝つ」 ≠ 「200 多様 agent 中で勝率高い」

**仮説 H2**: TrueSkill 初期 score が low。
- bovard validator は **5/10 submit 683 → 5/11 submit 1017** で +334 を resampling 観測した過去あり
- 今 1h で動いていない → 24h 観測必要

**仮説 H3**: zachary の 4P 適応不足。
- zachary は 2P 仕様 (= owner != player generic enemy)、 4P FFA で 3 enemy を 1 種扱い
- LB の 4P FFA で連合形成 / kingmaker 等の dynamic に弱い

### 即実行アクション

1. **24h 後 (5/12 09:00 JST) 再 LB 確認** — TrueSkill 完全 resampling 後の真値
2. **新 dataset DL** (= bovard 5/11 公開分待ち + 新 kernel 巡回)
3. **Phase θ PPO θ.1 完了** (= 50k step done at 10:09) → tournament smoke test 中

---

## 5-submit 周期分析 (= §8.1 item 10)

### Trend coef 統計 (過去 5 件)

| 指標 | 値 |
|---|---|
| LB / expected ratio (mean) | 0.65 |
| LB / expected ratio (σ) | 0.13 |
| 判定 | **drift** (σ > 0.02 限界超え) |

→ 我家 expected LB 計算式は **systematically over-optimistic**。 修正必要:
- local 4P win rate × 1500 ではなく **× 800-900** が校正後値 (= 75% local → 600-680 LB)
- or local benchmark に LB top tier (kovi/Shun_PI) proxy を追加して再校正

### Source pool ROI ranking (= 累積 LB 寄与 / submit 回数)

| Source | submit 回数 | best LB 寄与 | ROI |
|---|---|---|---|
| konbu17 hybrid (= base) | 4 | 989.2 (5/10), 922.9 (5/11) | high |
| bovard 59k validator | 3 | 1017 (5/10 resample), 854.9 (5/11) | mid |
| Pilkwang fork | 1 | 732.0 | low |
| Marco DG v3.3 | 1 | 734.6 | low |
| orbitbotnext | 1 | 795.2 | low |
| rudra | 1 | 692.3 | low |
| **zachary** | 1 | **600.0** | **lowest** |
| konbu17 + topk1 | 1 | 922.9 | mid |
| bovard + topk1 | 1 | 679.7 | low |
| bovard + bowwow | 1 | 854.9 | low |

### 未活用 source 抽出

- **Lakhindar rank1 dataset (= kovi/Shun_PI 真 Top 10 LB)**: BC 37k samples 構築済 (5/11 早朝)、 PPO opponent NN として未活用
- **真の rule-base lead-shot defense** (= fleet.angle 直読): 我家 base agent.py 332/649-650 で実装済だが Day 2 candidates 全部使ってない (= zachary は heuristic, Rudra は sun_collision のみ)

---

## 次の roadmap refine

1. **PPO θ.1 (= 完了)**: vs random で smoke test 中
2. **PPO θ.2 (= next)**: vs konbu17/orbitbotnext mix opponent、 100k step
3. **Day 3 submit (= 5/12 09:00 reset)**:
   - PPO θ.1 (= 1 件 testing)
   - PPO θ.2 (= 1 件 stronger)
   - 既存 best (= konbu17 hybrid + bovard validator) 再 submit (= safety net)
   - + 残 2 slot は 24h LB resampling 結果次第で zachary / Rudra fork の defense backport 版
4. **Day 4-10**: PPO θ.3 (vs strong rule-base mix) + θ.4 (PFSP self-play)

---

## 出典
- Submissions API: `kaggle competitions submissions orbit-wars` 2026-05-11 09:30, 10:12 JST
- Past LB resampling lesson: 2026-05-10 evening (bovard validator 683 → 1017 +334)
- Local benchmark calibration drift: 本 doc § Trend coef
- 共通 CLAUDE.md §8.1 (= 「随時やれ」 ルール根拠)
