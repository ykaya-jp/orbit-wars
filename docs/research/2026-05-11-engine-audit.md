# orbit-wars engine source audit — 2026-05-11

> 通読 file: `.venv/lib/python3.11/site-packages/kaggle_environments/envs/orbit_wars/orbit_wars.py` (812 lines)
> 目的: 未使用 observation field + 未発見 exploit の探索 (= score 2000+ Tier 3 path)
> 関連: `docs/strategy/2026-05-11-score-2000-roadmap.md` §F (= 不明領域: 未知 exploit)

---

## 1. Key engine facts (= 戦略判断の前提)

### 1.1 Termination (line 684-697)
- `alive_players ≤ 1` OR `step ≥ episodeSteps - 2 (= 498)` で terminate
- score = `sum(ships) per player` (= owned planet ships + in-flight fleet ships)
- **reward = +1 only for max-score player, -1 for ALL others**

→ **4P FFA でも 2-3-4 番目は全員 -1**。 King-maker 戦術は **自分の reward 上げない** = 全 ep で 1st 狙うのみ valid。

### 1.2 Speed scaling (line 577)
```
speed = 1.0 + (max_speed - 1.0) * (log(ships) / log(1000)) ** 1.5
```
| ships | speed | ratio |
|---|---|---|
| 10 | 1.27 | 1.0x |
| 100 | 1.95 | 1.54x |
| 500 | 3.66 | 2.88x |
| 1000 | 6.00 | 4.72x |

→ **大 fleet の数理優位確認**: 1000 ships は 10 ships の 4.7 倍速い。 bovard 280 万 row 分析の「late game ships 蓄積」 = 速度 + production が同時優位。

### 1.3 Combat resolution (line 636-674)
- 同 turn 同 planet に複数 fleet が到着すると **player ごとに ships 集計**
- `top - second` = survivor ships、 same → 0
- survivor が same owner → add、 different owner → subtract → < 0 で owner 変更
- **4P FFA implication**: 他 player 同士が same target に集中していると、 我家は介入せずに watch (= 食い合わせ) で resources 節約可能

### 1.4 Fleet trajectory (line 580-583)
- `fleet[x,y] += cos/sin(angle) * speed` (= 直線、 重力なし、 太陽中心引力なし)
- 1 turn 解像度の swept_pair_hit (line 46-64) で衝突判定
- **lead-shot 数理本質**: planet 円運動、 fleet 直線 = intercept time 解析的に解ける

### 1.5 Seed scrubbed (line 358-363)
- `configuration.seed = None` で agent から不可視
- env.info にのみ persist (= replay にだけ残る)
- **comet pre-positioning exploit 不可能** (= 50/150/250/350/450 step の position は seed 依存、 推測不可)

---

## 2. 未発見 exploit candidate (= 5 件、 LB lift 推定付き)

### 2.1 [#1] Let-them-fight (= 4P FFA で他 player 同士に食わせる) — Lift +20-50
- **Mechanism**: 同 target に other 2 player が攻撃 → 介入せず、 ships 余剰で別 target 取る
- **Code 根拠**: line 650-665 で combat resolution = top - second、 our reward 不変
- **実装**: planet_under_threat で「threat fleet が ALL enemy from different owners」検出 → defense skip
- **失敗モード**: 誤判定で planets 失う、 mid-game state 把握困難

### 2.2 [#2] 1-ship sniper (= coverage 増 + 1 turn 単位 intercept) — Lift +30-70
- **Mechanism**: ships=1 fleet は speed 1.0 (= 遅い)、 ただし low cost で coverage 拡張、 同 step 内に複数 launch 可能
- **Code 根拠**: line 484-489 で integer ships の lower bound チェックなし、 同 turn 同 planet 多 launch OK
- **実装**: defense layer で trajectory blocking (= enemy fleet の path に 1-ship を投げて combat 衝突)
- **失敗モード**: 1 ship は speed 1.27 で intercept 困難、 timing 計算困難

### 2.3 [#3] Multi-fleet decoy timing — Lift +20-40
- **Mechanism**: 同 target に異 ETA で 2-3 fleet 連続 launch、 1st decoy (= 敵 garrison 消耗) + 2nd 本攻撃
- **Code 根拠**: line 593 で combat list 蓄積、 順次 resolve
- **実装**: 既存 sigmaborov_reinforce の 3-SOURCE_SWARM_ETA_TOLERANCE と類似
- **失敗モード**: decoy が無駄に消費、 ships overhead

### 2.4 [#4] **End-game ship pile-up** (= step 480+ で総攻撃) — Lift **+50-100** ★ 最高 ROI
- **Mechanism**: bovard 280 万 row で top tier は step 400+ で ships 1800+ 蓄積、 step 498 で 1 turn 内に全 ships を 1 target に集中させて勝てる
- **Code 根拠**:
  - line 686 で `step >= episodeSteps - 2` で terminate
  - line 712 で `max_score` のみ +1 reward
  - line 703-708 で score = ships count (= owned planet ships + in-flight)
- **実装** (= rule で簡単):
  1. step > 460 detect
  2. enemy max planet (= top tier の biggest source) を target
  3. all our planets から ETA <= remaining_step の biggest fleet を launch
  4. step 498 で combat resolve、 我家 score が enemy max + own ships > our ships → 1st 取得
- **失敗モード**: defense 取れず、 ships 100% 攻撃に振り切るので 取り返せない、 late game の 1-shot ギャンブル
- **既存 build との関係**: 既存 mission system に「`EndgamePileupMission`」を追加可能、 step 460+ で active

### 2.5 [#5] Trajectory blocking (= own fleet で enemy fleet combat) — Lift +20-50
- **Mechanism**: enemy fleet の trajectory 上に own fleet を投げ、 1 turn で combat 衝突 (= ships top - second)
- **Code 根拠**: combat_lists per planet で集計、 同 fleet path 衝突は collision check されない (line 588-597 = planet hit のみ)
- **WAIT**: line 588-597 で fleet vs **planet** swept_pair_hit のみ check。 fleet vs fleet の交差は **無視**! つまり trajectory blocking は **engine 仕様上動作しない**
- → **#5 棄却** (= engine が fleet 間 collision を resolve しない)

→ **真に有効な candidate は #1, #2, #3, #4**

---

## 3. 即実装 priority

1. **#4 End-game ship pile-up** = 最高 ROI (+50-100)、 rule で簡単、 既存 missions.py に EndgamePileupMission 追加
2. **#1 Let-them-fight** = passive 戦略、 既存 planet_under_threat に「multi-enemy detection」追加で実装可能
3. **#3 Multi-fleet decoy timing** = orbitwork_v14 / sigmaborov_reinforce で既に類似 logic、 backport 価値高
4. **#2 1-ship sniper** = 実装複雑、 後回し

---

## 4. Day 4 candidate に組み込む build 候補

| build | content | LB 期待 |
|---|---|---|
| `build_fleet_angle_zachary_v2` | fleet.angle + **End-game pile-up** rule | 1200-1400 |
| `build_fleet_angle_zachary_v3` | 上記 + Let-them-fight detection | 1300-1500 |
| `build_orbitwork_v14_topk1` | 公開 LB ~1050 + topk1 wrapper | 1050-1200 |
| `build_sigmaborov_reinforce_topk1` | LB 958 + topk1 wrapper (= multi-fleet decoy 既存) | 950-1100 |

→ Day 4 5 slot:
1. Day 3 best (= TBD after 5/12 reset)
2. `build_fleet_angle_zachary_v2` (end-game pile-up 追加)
3. `build_lakhindar_pure` (= IL paradigm 生死判明、 Day 3 で延期した分)
4. `build_orbitwork_v14` (= 公開 kernel fork、 paradigm 多様化)
5. `build_expansion_pure` (= P3 = Expansion rule mission)

---

## 5. 不明領域への進展

| §F 不明事項 | engine audit 結果 |
|---|---|
| 未知 exploit | 5 candidate 同定、 うち #4 (+50-100) が即実装可能 |
| Top 1 戦略 | bovard 280 万 row 分析で「late game ships 蓄積」を確認、 #4 と一致 |
| PPO scaling | 関係なし (= rule paradigm の本 audit) |
| Kaggle impl diff | engine source は 1 file、 Kaggle と local で同一 |

---

## 6. 出典

- `.venv/lib/python3.11/site-packages/kaggle_environments/envs/orbit_wars/orbit_wars.py` 全 812 lines
- `data/processed/actions/bovard_2026_05_04.parquet` (= late game ships 蓄積 確認)
- `docs/strategy/2026-05-11-score-2000-roadmap.md` (= Tier 3 探索 path)
- 2026-05-11 18:00 JST 通読
