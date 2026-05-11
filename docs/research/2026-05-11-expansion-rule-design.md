# Expansion rule mission 設計根拠 — 2026-05-11

> Plan ref: `.criteria/kaggle-orbit-wars-expansion-rule-mission.yaml`
> Roadmap: `docs/strategy/2026-05-11-victory-roadmap.md` (= P3 phase)
> 関連 lesson: `~/.claude/CLAUDE.md` [2026-05-10] orbit-wars host dataset verification lesson

---

## 1. 真因解析根拠 (= bovard 280 万 row 分析)

`kaggle datasets download bovard/orbit-wars-top10-episodes-2026-05-04` (= 2630 ep/day × 19 day) の SQL 解析:

| 指標 (step 100 時点 中央値) | Top tier (kovi/Shun_PI) | 我家 (Reexel/v2 系) | gap |
|---|---|---|---|
| my planets owned | **5-7** | **1-2** | **4-7x** |
| my total ships | **300-430** | **30-50** | **~100x** |
| neutral planets remaining | 8-10 | 18-19 | 2x more remaining |
| my fleets in-flight | 2-3 | 0-1 | 3x more aggressive |

**結論**: Top tier の本質は **early expansion (step 0-100 で planets 5+)**。 我家 LB ≤ 989 の根本原因は expansion gap。

出典:
- bovard dataset: https://www.kaggle.com/datasets/bovard/orbit-wars-top10-episodes-2026-05-04
- 数値: ~/.claude/CLAUDE.md "[2026-05-10] orbit-wars" lesson の引用
- 我家 episode 観察: `docs/research/2026-05-11-losing-play-analysis.md`

---

## 2. 既存 CaptureMission の失敗モード (= src/orbit_wars/missions.py:263-265 既存 comment)

```python
# 真の expansion gap 原因はまだ特定中: 取った planet が空 (= 取得時 ships ≈ 0) で
# 即 home として再利用できないことが疑われ、Phase 1.1c で `capture_buffer` を
# 上げる仮説を検証予定。
```

既存 `CaptureMission` の動作:
1. ROI 順に target を選ぶ (= `roi(prod, ships_needed, t_arr)`)
2. `ships_needed = target.ships + 1` (margin 1) で minimum 取得
3. → 取得時 my_planet.ships ≈ 0 (= capture 直後の garrison = 0 から production 蓄積)
4. → 次 turn の launch 不能 = chain expansion 止まる

これが「**1-2 planets で止まる**」 mechanism。

---

## 3. ExpansionPriorityMission の設計差分

| Parameter | 既存 CaptureMission | ExpansionPriorityMission | 効果 |
|---|---|---|---|
| `capture_buffer` | margin=1 (= 既存) | **capture_buffer=8** | post-capture garrison ≥ 5 で次 turn launch 可能 |
| 適用範囲 | 全 step | **step ≤ 150** | late game は CaptureMission に渡す (= over-expansion 抑制) |
| target 範囲 | 全 enemy + neutral | **dist ≤ 35 の neutral のみ** | nearby cluster で chain expansion、 全 map 飛び散らない |
| score weight | base ROI | **base ROI × 2.0** | Dispatcher で Capture より先に ships 確保 |
| 競合解決 | Dispatcher の `_PlannedMove.score` 降順 | 同上 (= multiplier で先取り) | Recapture (10x base) > Expansion (2x base) > Capture (1x base) |

---

## 4. score 設計の数理本質

base ROI = `physics.roi(prod, ships_sent, t_arr) = prod / (ships_sent × t_arr)`
- 高 production の target を **少 ship + 短 arrive time** で取れば高 ROI

ExpansionPriorityMission の合成 score:
```
score = sum(base_roi(target_i) × 2.0)  for each (mine, target) pair selected
```

multiplier 2.0 の根拠:
- 既存 mission 階層 (= ~/projects/kaggle/orbit-wars/src/orbit_wars/missions.py docstring §15-19)
  - Recapture (10x base) >> Comet (5x) > Capture (1x ROI) ≈ Aggregation (1x ROI)
- Expansion を Recapture の下、 Comet と同等のレベルに position
  - = expansion は重要だが奪還ほど urgency ない
  - = comet と同等の重要度

---

## 5. Unit test 仕様 (= tests/test_expansion_mission.py)

| test 名 | 検証内容 | 期待 |
|---|---|---|
| `test_expansion_active_in_early_game` | step=50 で nearby neutral target | score > 0, 1 move, ships ≥ 10+1+8 |
| `test_expansion_deactive_after_early_game` | step=200 で 0 score | score=0, 0 moves |
| `test_expansion_skips_far_targets` | dist=>max_distance | 0 score |
| `test_expansion_capture_buffer_applied` | buffer=15 で ships ≥ 10+1+15 | ships ≥ 26 |
| `test_expansion_respects_capacity` | home cap < ships_needed | skip target |
| `test_expansion_skips_comet_planets` | comet を target にしない | 0 score |
| `test_expansion_no_my_planets` | self planet 0 で no-op | 0 score |
| `test_expansion_score_multiplier_applied` | 1.0 vs 2.0 で score 2x | approx 2x |

全 8 test pytest pass 済 (= AC-2)。

---

## 6. 期待する LB 効果 (= 仮説、 P3 単独 submit で検証)

H1 (= **expansion gap が真因)**: ExpansionPriorityMission 単独 build を local 4P vs starter × 3 で 1 ep 実行、 step 100 の my planets ≥ 3 達成。

LB 期待:
- 既存 build_v2 (= 5/10 LB 989) base に対し、 expansion gap 解消で **+100-200 LB** 期待
  - 既存 our step 100 planets = 1-2 → expansion で 3-4
  - Top tier 5-7 にはまだ届かないが、 50% gap 改善
- 最終 P4 (= meta-agent: Expansion + Lakhindar IL + PPO θ.4) で更に push

H2 (= **expansion gap が真因でない**):
- ExpansionPriorityMission 単独で step 100 planets < 3 のまま
- → 真因は別 (= e.g. fleet routing、 sun-cone avoid、 lead-shot 精度)
- → bovard 280万 row 再解析、 別 metric (= ship production rate、 attack accuracy) candidate

---

## 7. Day 4 以降 submit 戦略への組込

Day 4 (= 5/13 09:00 JST reset) 5 slot 候補:
1. safety net (= 既存 best、 e.g. submission_v2 or P1 Day 3 best)
2. **build_expansion_pure** (= 本 P3 deliverable、 H1 検証)
3. **build_expansion_topk1** (= ExpansionPriorityMission + topk1 wrapper、 large fleet 強化)
4. **PPO θ.4** (= P2 完走済 zip)
5. **meta-agent v0** (= P4 着手、 Expansion + Lakhindar IL の 2-paradigm 暫定 mix)

→ Day 4 で **5 paradigm datapoint** 取得 (= safety / rule / rule+topk1 / RL / 2-paradigm meta)。

---

## 8. 出典

- bovard dataset: https://www.kaggle.com/datasets/bovard/orbit-wars-top10-episodes-2026-05-04
- ~/.claude/CLAUDE.md "[2026-05-10] orbit-wars" lesson (= expansion gap 数値)
- ~/projects/kaggle/CLAUDE.md §1.3 single paradigm では gold 不可 / §11 優勝本質性
- src/orbit_wars/missions.py:263-265 (= 既存 CaptureMission の failure mode 既知)
- docs/research/2026-05-11-losing-play-analysis.md
- docs/strategy/2026-05-11-victory-roadmap.md (= P3 phase 全体像)
