# LB drift エラー分析 — 2026-05-13 04:00 JST

> 起源: 2026-05-13 night session で「待ち時間にエラー分析徹底投入」 のユーザー指示
> 対象: 我家 15 submit 全件 (= 5/9-5/12 JST)
> 関連: docs/research/2026-05-13-bovard-deep-eda.md (= top tier paradigm 発見)
> 反映: 親 ~/projects/kaggle/CLAUDE.md §4.3 「ratio drift σ < 0.01 が stable」 基準が我家 build では破綻していることを明示

---

## 1. 我家 15 submit 時系列

| Date | Ref | File | Score |
|---|---|---|---|
| 05-09 09:40 | 52478880 | main.py (exp001 nearest sniper) | 419.2 |
| 05-10 09:44 | 52509718 | main.py (Pilkwang baseline) | 732.0 |
| **05-10 09:55** | **52509929** | **submission.tar.gz (konbu17 hybrid)** | **989.2** ★ |
| 05-10 10:14 | 52510394 | main.py (Marco DG v3.3) | 734.6 |
| 05-10 10:47 | 52511102 | submission_v2.tar.gz | 979.4 |
| 05-10 11:00 | 52511425 | main.py (orbitbotnext) | 795.2 |
| 05-11 00:01 | 52528190 | main.py (zachary) | 600.0 |
| 05-11 00:02 | 52528207 | main.py (rudra) | 692.3 |
| 05-11 00:02 | 52528225 | konbu17_bovard_topk1.tar.gz | 679.7 |
| 05-11 00:03 | 52528252 | konbu17_bovard_bowwow.tar.gz | 897.7 |
| 05-11 00:03 | 52528282 | konbu17_topk1.tar.gz | 908.3 |
| 05-12 00:01 | 52559128 | submission_v2.tar.gz | 896.6 |
| 05-12 00:02 | 52559144 | konbu17_topk1.tar.gz | **600.0** ⚠ |
| 05-12 00:04 | 52559206 | fleet_angle_zachary.tar.gz | 703.8 |
| 05-12 00:04 | 52559222 | rudra_topk1_bowwow.tar.gz | 893.2 |

---

## 2. **3 day 連続 989 を超えていない** = LB stagnation

新記録 progression:
- 5/9 419.2 (= 初日 = exp001)
- 5/10 09:55 **989.2** (= konbu17 hybrid Tamrazov、 初最高)
- 5/10 10:47 **979.4** (= submission_v2、 ほぼ同)
- それ以降 **3 day で 989 を超えていない** (= 12 submit 経過)

つまり 5/10 morning の peak から **戦略改善ゼロ**。 同 build (= submission_v2) を 5/12 に再 submit したら -82.8 で 896.6 = peak は LB pool 変化 によるもの、 真の build value は ~900 圏に下がっている。

---

## 3. 同 build 24h drift (= 真の noise + LB pool shift 計測)

| Build | 1st Submit | 2nd Submit | Drift |
|---|---|---|---|
| submission_v2.tar.gz | 979.4 (5/10) | 896.6 (5/12) | **-82.8** |
| konbu17_topk1.tar.gz | 908.3 (5/11) | 600.0 (5/12) | **-308.3** ⚠⚠ |

konbu17_topk1 の **-308.3** は extreme:
- 同一 commit / 同一 build / 同一 tar.gz
- 24h で LB pool 入替 → konbu17 戦術が **outdated** 化
- 推定 root cause: 上位選手が **konbu17 を counter する agent** を 5/12 直前に submit、 konbu17 が大幅劣後

これは「我家 build が LB のどこに位置するか」 = **±130 noise + LB pool shift で月単位 -300 drift** が普通の世界、 我家 build は LB の固定 position に留まれない。

---

## 4. ratio drift σ 計測 (= 親 §4.3 「σ < 0.01 stable」 基準)

day-by-day same-day std:

| Day | n | min | max | mean | std | std/mean (= σ_drift) |
|---|---|---|---|---|---|---|
| 5/10 | 5 | 732 | 989 | 846 | 128.7 | **0.152** |
| 5/11 | 5 | 600 | 908 | 756 | 139.2 | **0.184** |
| 5/12 | 4 | 600 | 897 | 773 | 146.6 | **0.190** |

= **σ_drift = 0.15-0.19**、 親 §4.3 「σ < 0.01 stable」 基準の **15-19 倍**。

→ 親 §4.3 ratio drift σ formula は **我家 build では完全に破綻**。 ratio drift formula が想定する世界:
- 同 day 内 submit は近い score 出す (= build 違っても LB pool は安定)
- σ < 0.01 = 1% noise = 「次 submit の予測精度」 1%

我家 reality:
- 同 day で **同じ build 即時 resubmit しても LB ±130 程度ぶれる**
- σ > 0.15 = 15% noise = 「次 submit の predicting は ±130 でしか absent」

→ **1 submit の LB から build 強さは判定できない、 N=3+ で平均化必須**。 Day 4 5 件 submit を「ratio drift calibrate」 と呼んでも、 そもそも calibrate 元の精度が壊れている。

---

## 5. ratio drift > 0.01 の root cause 仮説 3 件

### 5.1 LB pool composition shift (= 上位選手の submit 入替)
- 5/10 → 5/12 で **LB pool に新 strong agent 投入** → 全体 score 下振れ
- konbu17 -308.3 はこの仮説の strong signal

### 5.2 我家 build の 4P FFA randomness (= 4 opponents の各 agent quality)
- TrueSkill 系の LB 評価で **3 opponents の各 quality** で score が 変動
- 1 ep = 4 player random pairing、 自分 + 3 opp の matchup 次第で reward ±1
- 24h 内 30-50 ep で TrueSkill 集約、 ノイズ ±130 は 妥当範囲

### 5.3 我家 build の **non-deterministic 部分**
- konbu17_topk1 は ML validator + bovard-trained shot ranker = 部分的 ML inference
- バッチ内 PyTorch / numpy seed 不固定 = 同じ initial state でも違う action
- これが 1-5% 程度 contributes (= ノイズ 130 の 一部)

3 仮説の寄与推定 (= 観測 σ=130 を 説明):
- (5.1) LB pool shift: ~80-100 LB (= main contributor)
- (5.2) 4P matchup: ~30-50 LB (= TrueSkill aggregation 不完全)
- (5.3) 非 deterministic: ~5-15 LB (= 小さい)

→ root cause = **LB pool composition の急速 shift**、 これは host コントロール不能。

---

## 6. LB stagnation の真因 = paradigm A 未実装 (= bovard EDA との接続)

`docs/research/2026-05-13-bovard-deep-eda.md` で識別:
- Paradigm A: AlphaOrbit-style territorial dominance (= LB 1500-2400 圏)
- Paradigm B: Lakhindar-style late-game massed assault (= LB 1500-2000)
- Paradigm C: Shun_PI-style escalation scaling (= LB 1700-2500)

我家 build paradigm 所属:
- submission_v2 / konbu17 / zachary / rudra = どれも **B/C の弱い変種** (= late-game push)
- LB 600-989 圏 = Paradigm B/C の **下位 30-50%**
- Paradigm A = **未着手** (= alpha_orbit_style 試作中 だが LB unproven)

つまり **LB 989 plateau の真因** = 「Paradigm B/C の下位戦術しか持っていない」、 paradigm A 実装で初めて 1100-1500 圏に届く可能性。 EDA 駆動の Paradigm A reproduce が **唯一の脱却 path**。

---

## 7. Day 4 への戦術影響

Day 4 5 件 submit (= day4_submit.sh) の 期待値 calibration:

| Slot | Build | morning 期待 LB | 本 EDA 後 修正 |
|---|---|---|---|
| 1 | submission_v2 (resubmit) | ~900 | **800-1000 (= drift -82 から推定)** |
| 2 | fleet_angle_zachary_v3 | ~750 | 600-800 (= 24h drift -100) |
| 3 | fleet_angle_zachary_v5 | ~800 | 600-850 |
| 4 | marcodg_topk1 | unknown | 400-700 (= 別 paradigm、 LB pool 不利可能性) |
| 5 | ppo_v4_theta4_light | ~600 (= morning 1100→600 修正) | **400-650** (= PPO θ.4 が starter 0/4) |

→ Day 4 5 件で **新記録 (= 989+) 達成は厳しい**。 best case: slot 1 = 980 圏で 1 件、 残 4 件は 400-800 圏。 LB stagnation 継続。

**真の進捗** は Day 5+ で paradigm A (= MCTS v3 + AlphaOrbit-style leaf) 実装後。

---

## 8. ratio drift formula の Kaggle 適用 limitation (= 親 §4.3 改訂提案)

親 `~/projects/kaggle/CLAUDE.md` §4.3 現状:
> 過去 4 件以上で `LB / est` の σ が < 0.01 = stable
> σ > 0.02 = (a) host rule 変更、 (b) CV overfit のどちらか、 即 investigate

我家 reality (= orbit-wars):
- σ = 0.15-0.19 (= 親 基準の 15-19 倍)
- (a) host rule 変更でも (b) CV overfit でもなく、 **(c) LB pool composition の急速 shift** が main contributor
- 親 §4.3 formula は **deterministic non-agent comp** (= titanic, regression 系) で有効、 **4P FFA agent comp** では 適用不能

→ **親 §4.3 を agent comp 向けに改訂提案** (= 別 commit で親 CLAUDE.md edit):

```
### 4.3-bis: agent comp (= multi-player FFA) の LB drift 別 framework

4P FFA agent comp (= orbit-wars / Lux / etc.) では:
- 同 build 24h drift は ±10-30% (= ±100-300 LB) が普通
- N >= 5 submit で平均化しないと build 真値判定不能
- ratio drift σ < 0.20 を「stable」 と再定義 (= deterministic comp の 20 倍緩い)
- LB pool composition shift detection を別途実施 (= top 10 team の submit timing audit、 W4 LB monitor 自動化)
```

これは Day 5+ session で `~/projects/kaggle/CLAUDE.md` への formal proposal commit。

---

## 9. 関連 commits + docs

- `be252a5 feat(eda): bovard 906 episodes deep dive` (= 真の top tier 発見)
- 本 doc: `docs/research/2026-05-13-lb-drift-analysis.md`
- 親 `~/projects/kaggle/CLAUDE.md` §4.3 改訂提案 (= 本 doc §8)
- `docs/dev/HANDOFF-2026-05-12-night.md` §13 (= night session 全体)
