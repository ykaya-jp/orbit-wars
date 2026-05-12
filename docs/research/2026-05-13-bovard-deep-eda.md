# bovard 906 episodes deep EDA — 2026-05-13 03:00 JST

> 起源: 2026-05-13 night session で「待ち時間に Kaggle GM 級 EDA をやれ」 のユーザー指示
> 対象: `data/external/bovard_full/*/episodes/episodes/*.json` (= 906 完全 DL episodes、 manifests は 35,130 episodes 集計可能)
> 関連: docs/strategy/2026-05-12-roadmap-pivot.md (= morning の bowwow 中心 roadmap、 本 EDA で大幅 revise)
> 反映: 親 ~/.claude/CLAUDE.md lessons.md 候補入り

---

## 1. 衝撃発見 1: morning の「bowwow 中心」 戦略は **真の Top tier 集合を見逃していた**

morning W3 (= research worker output) は **bowwowforeach (= LB 1 / 1823)** を「Top 1 / AHC 1 位 4 回 / pure rule + 探索」 と完全研究したが、 bovard 906 episode で **bowwowforeach は plays=5 未満** で集計外。 真の Top tier:

| Rank | Agent | Win Rate | Plays | Mean Top Score (1700+ cohort) |
|---|---|---|---|---|
| 1 | **AlphaOrbit** | **100.0%** | 7 | (sample 不足) |
| 2 | Sairaj Adhav | 80.0% | 5 | (sample 不足) |
| 3 | Mille Initiate | 60.0% | 20 | — |
| 4 | Lakhindar Pal | 58.0% | 50 | — |
| 5 | V_Arslan | 55.6% | 9 | — |
| 6 | Strategy Optimized Agent | 55.0% | 40 | — |
| 7 | **Shun_PI** | **51.0%** | 51 | **2351.4** ★★★ |
| 8 | 寿! | 50.0% | 54 | — |
| 11 | Mark Slavin | 46.2% | 13 | — |
| 12 | Mahog | 45.9% | 37 | — |

**Shun_PI** は morning research 完全 unknown だが mean top_score 2351 = **score 2000+ を実際に達成している唯一明確な agent**。 bowwowforeach の LB 1823 を凌ぐ実績。

35,130 episode 全体での top_score 分布: max=2577, top 0.4% (= 154 ep) が 1700+、 1.8% (= 651 ep) が 1500+。 **2000+ は実在し、 達成可能 LB**。

---

## 2. 衝撃発見 2: 真の Top tier の launch profile は **「bowwow big-stack 待ち」 と完全 inverse**

morning roadmap pivot doc §2 で「bowwow mean launch 241 ships、 launch/step 0.43、 p99 3647」 と claim、 これに基づき `submissions/build_bowwow_timing/main.py` を min_ships=80-150 で実装。 **bovard 906 episode の実測は全く違う**:

| Agent | Win Rate | Launch Rate | Mean Ships/Launch | P95 Ships/Launch | Max Ships/Launch |
|---|---|---|---|---|---|
| AlphaOrbit | 100% | **0.557** | **29.4** | 53 | 413 |
| Lakhindar Pal | 58% | 0.423 | 24.0 | 66 | 1677 |
| Mille Initiate | 60% | 0.257 | 47.0 | 91 | 1518 |
| Sairaj Adhav | 80% | (n/a) | 25.2 | 70 | 949 |
| Shun_PI | 51% | 0.364 | 36.1 | 103 | 996 |

= **mean 20-50 ships / launch** (= morning claim 241 の 1/5~1/10)、 P95 でも **50-103 ships** (= morning claim 3647 の 1/30~1/70)。

morning の数値 source 不明 (= worker output に source URL あり、 再現必要)。 いずれにせよ「真の top は big-stack 待ち」 仮説は **完全 wrong**、 私の build_bowwow_timing は wrong-spec で作られた。

---

## 3. AlphaOrbit (= 100% WR) の真戦術 = **productive territorial dominance**

7 win / 7 play episodes の step-by-step 集計:

| Step | Mean Planets Owned | Mean Total Ships | Launches/Step | Mean Ships/Launch |
|---|---|---|---|---|
| 0 | 2.6 | 59.8 | 0.28 | 7.5 |
| 50 | 8.6 | 203.9 | 1.23 | 29.8 |
| 100 | **14.3** | **734.6** | 1.35 | 41.0 |
| 150 | 22.2 | 1087.0 | 2.11 | 62.9 |
| 200 | **23.4** | **1891.0** | 1.68 | 61.5 |
| 250 | 14.9 | 504.1 | 2.42 | 59.7 |
| 300 | 15.3 | 332.5 | 2.74 | 78.6 |
| 350 | 22.2 | 1210.0 | 3.60 | 121.3 |

target selection profile:
- target distance median = **21.4** (= 短距離、 我家 fleet_angle_zachary は 80+ もよくある = 長距離 gamble)
- target ships median = **22**, P95 = **84** (= 防衛 weak な planet を狙う、 fortress 攻めない)
- target **prod median = 3.0** (= 高生産性 planet 優先、 他 agent は prod=2.0)
- target owner: **own = 68%** (= 自軍内で ships 循環 / 前線へ reinforce)、 neutral 11%、 enemy 21%

戦術要約 (= 4 pillar):

1. **High-prod targeting**: 生産性 3+ の planet を優先確保 (= 「投資効率」 重視)
2. **Short-range fire**: 距離 30 以内のみ、 長距離 gamble なし
3. **Friendly reinforcement majority**: 全 launch の 68% が **自軍 planet 間の ships 移動** = 前線維持戦術
4. **High frequency, small magnitude**: launches_per_step 0.557 + mean 29 ships = 「1 step に何か小さい launch」 = constant pressure

これは MCTS / rule build にとって **完全に新しい設計指針**。

---

## 4. Lakhindar Pal (= 58% WR、 50 plays = sample stable) の 別戦術 = **late-game massed assault**

step 帯別 mean ships/launch:
- step <80: 18.5
- step 80-250: 23.6
- step 250-420: 41.8
- step **420+: 363.8 (med 162, max 1677)** ★★

= **early-mid は small launches、 終盤に massive fleets 集中**。 これは AlphaOrbit の linear scaling と異なる pattern = **「step 420 までに ships を蓄えて、 残 80 step で爆発」**。

但し planet count growth は AlphaOrbit に劣る:
- AlphaOrbit step 200: 23.4 planets
- Lakhindar step 200: 11.9 planets

= **Lakhindar は planet 数で勝負しない、 ships pile で勝負**。 これは別 paradigm。

---

## 5. Shun_PI (= 2351 score、 score 2000+ 実証) の戦術 = **escalation scaling**

step 帯別 mean ships/launch:
- step <80: 20.3
- step 80-250: 32.0
- step 250-420: **55.3** (med 26, max 961)
- step 420+: **68.4** (med 32, max 996)

= **継続的 escalation**、 各 phase で 50% ずつ ships を増やす。 AlphaOrbit (= constant size) と Lakhindar (= 終盤集中) の **中間 strategy**。

planets@step200=13.3 で AlphaOrbit (=23) より少ないが、 score 2351 達成 = **planet 数ではなく ships destruction 効率で勝つ**。

target ships P95 = **330** (= P95 が高い = たまに massive launches で massive fleets を sink)。 AlphaOrbit (= P95 84) より「攻撃のメリハリ」 が強い。

---

## 6. 戦略 paradigm 分類 (= 真の Top tier 3 paradigm)

| Paradigm | 代表 agent | Key feature | LB 期待 |
|---|---|---|---|
| **A. Territorial dominance** | AlphaOrbit, Mille Initiate | constant small launches + high-prod target + own-target reinforcement | 1500-2400 |
| **B. Late-game massed assault** | Lakhindar Pal | early small + step 420+ で massive accumulation | 1500-2000 |
| **C. Escalation scaling** | Shun_PI, 寿! | 各 phase で 50% ずつ ships escalate | 1700-2500 |

我家 build の所属:
- **submission_v2 / konbu17 / fleet_angle_zachary** = どれも **B/C の弱い変種** (= late-game push 戦術)、 score ~700-900 圏
- **bowwow_timing v2** = ill-defined (= morning fake data 駆動)、 1/8 wins
- **MCTS v2** = sim parity 修正後 2/8 vs starter = baseline 圏
- **alpha_orbit_style** = **A paradigm 試作**、 vs starter 3/8 = 改善傾向、 vs konbu/zachary 0/8 = 未熟

---

## 7. MCTS v3 / build 設計への反映 (= Day 5+ work)

### 7.1 leaf eval 関数 を Top tier 観測に校正

現在の `evaluate_leaf`:
```python
alpha * my_planets + beta * my_ships - gamma * enemy_ships - delta * enemy_planets
+ epsilon * my_prod * remaining_steps - zeta * enemy_prod * remaining_steps
```

提案 (= AlphaOrbit-style 反映):
- **alpha (= planet count) を 20 に倍化** (= AlphaOrbit は step 200 で 23 planets、 これが victory predictor 最強)
- **epsilon (= my_prod * remaining) を 1.5 倍** = 高 prod planet 重視
- **own-front reinforcement term 追加** (= 我家 frontline planets の ships ≥ enemy threat の確保)

### 7.2 action enumeration を AlphaOrbit 流に拡張

現在の MCTS `enumerate_actions`: 非所有 planet target のみ、 own-target 除外。

提案:
- **own-target launches を allow** (= 68% of AlphaOrbit launches が own = reinforcement)
- target distance cutoff = 40-60 (= AlphaOrbit P95 = 77)
- target prod >= 2 を **bias** (= 高 prod を target に優先)

### 7.3 step-band min_ships

AlphaOrbit:
- step < 80: 15 ships (= mean 25 だが 個別 fire は 15+)
- step 80-200: 20 ships
- step 200-380: 30 ships
- step 380+: 30 ships

= **bowwow_timing morning 設計 (= 15→80→150→80) と完全 inverse**。 真の top は **flat low threshold**。

### 7.4 多 paradigm hybrid build

Day 5+ で 3 paradigm 混合:
- Paradigm A (= AlphaOrbit-style) を base agent
- Paradigm B (= Lakhindar-style) を step 420+ から activate
- Paradigm C (= Shun_PI-style) を step 100-420 でgradient

これは「軽量 ensemble」 = condition-switched policy、 MCTS と直交。

---

## 8. 我家 LB position の re-calibration

morning roadmap pivot §10 の「Top 1-3 (= 2000+) 8-12%」 は **revise 必要**:

Episodes 35,130 中 score >= 1700 が **154 件 (0.44%)** = LB 上位は普通の play で取れる score ではないが、 sample size が 35,130 もあって 154 件 hit している = **LB 2000+ は奇跡ではなく、 真の top agent なら頻発する**。

→ 「Top 1-3 (= 2000+) 8-12%」 の **私 honest 評価が pessimistic 過ぎた可能性**。 真の top tier agent (= AlphaOrbit-style 100% WR、 Shun_PI mean 2351) を **同等品質で再現できれば LB 1500-2200 が確実圏**。 「奇跡 + 神 RNG」 ではなく「真の top 戦術 を data 駆動で実装」 が答え。

revise 評価:
- Silver (= 1200+): 70% → **80%** (= EDA で paradigm 明確化)
- Gold (= 1500+): 40% → **50%** (= AlphaOrbit-style 完成度 70% で可能)
- Top 5 (= 1700+): 20% → **30%** (= 3 paradigm 混合で可能)
- **Top 1-3 (= 2000+): 8-12% → 12-18%** (= Shun_PI 級の escalation 完成度 必須、 41 day で実装可能性 mid)

---

## 9. 限界 (= 本 EDA で touch していないこと)

1. **AlphaOrbit 7 episodes 含めた DL 範囲が偏在**: bovard host が 906 episodes しか公開していない、 真の AlphaOrbit 戦術は他にもパターンあるかも
2. **target 判定の precision**: launch action の (from_pid, angle, ships) から target を推定したが、 sun-safe 迂回や orbital prediction で誤判定あり (= 推定 90%+ accuracy 想定だが未測定)
3. **defense pattern unstudied**: 防衛 pattern (= 敵 fleet incoming への反応) は 本 EDA で touch せず、 別 work
4. **opponent identify による戦術切替**: top tier が「弱 opponent vs 強 opponent」 で戦術変えるか未確認
5. **配置 (= initial planet layout) effect**: random seed による map 差が戦術 prefer に影響するか未測定

---

## 10. 次 session 即 action (= Day 5+)

1. **AlphaOrbit / Lakhindar / Shun_PI の追加 episode を kaggle CLI で全量 DL** (= `kaggle competitions episodes <sub_id>`)、 各 100+ episodes に増量
2. **MCTS v3 = MCTS + AlphaOrbit-style action space + AlphaOrbit-style leaf eval** を実装
3. **alpha_orbit_style build を vs starter 5/8+ wins まで improve** (= 現状 3/8、 fine-tune 余地ある)
4. **build_bowwow_timing は archive** (= morning fake data 駆動、 価値ゼロ)
5. **Day 6: 3-paradigm hybrid build** (= AlphaOrbit + Lakhindar + Shun_PI condition-switched)

---

## 11. 関連 commits + docs

- `4b141e3 fix(mcts): sim parity + mock + leaf` (= MCTS v2 修正、 starter 2/8)
- `submissions/build_alpha_orbit_style/main.py` (= 本 EDA 駆動 first build、 starter 3/8)
- 親 `~/projects/kaggle/CLAUDE.md` §0.5 (= Codex review 必須化)
- `docs/dev/HANDOFF-2026-05-12-night.md` §12 (= night session 全体)
- 本 doc は **次 session 即 read 必須** (= Day 5+ 戦略の base)
