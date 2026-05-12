# bowwowforeach Reverse Engineer (= Phase α.1 進捗、 2026-05-12 09:50 JST)

> 起源: docs/strategy/2026-05-12-roadmap-pivot.md Phase α.1
> 出典 data: data/processed/actions/bovard_2026_05_04.parquet (= 280 万 row、 2,630 episodes、 host bovard 提供)
> 補完: docs/research/2026-05-12-victory-research/03-top-tier-profile-research.md (= W3 結論)

---

## 0. TL;DR

**bowwowforeach = 「launch 頻度 中位 (0.43/step) + launch size 突出 (mean 241 ships = 次点 flg の 1.9x)」** の **timing 選択型 big-stack 戦術**。 pure scale (= expansion champion flg は LB 中位) ではなく、 **「いつ大型 launch するか」 の判断能力** が LB 1 / 1823 を支えている。

→ Phase α.2 MCTS / beam search が **launch timing 探索を直撃** すれば bowwow paradigm 再現可能。 leaf evaluator は「expand vs combat vs save」 trade-off の数値評価で足りる可能性。

---

## 1. Launch size 分布 (= 2026-05-04 bovard data、 top 8 agents)

| Agent | n_ep | n_launch | launch/step | p50 | p90 | p95 | **p99** | **mean** | max |
|---|---|---|---|---|---|---|---|---|---|
| **bowwowforeach** ★ | 83 | 11125 | **0.43** | 52 | 447 | 996 | **3647** | **241** | 13714 |
| flg | 58 | 8368 | 0.46 | 49 | 207 | 416 | 1912 | 124 | 8433 |
| Artem | 66 | 4973 | 0.23 | 38 | 138 | 212 | 614 | 71 | 3190 |
| Ezra | 97 | 20246 | 0.71 | 19 | 90 | 143 | 388 | 43 | 3882 |
| Vadasz | 87 | 13665 | 0.63 | 25 | 70 | 93 | 154 | 34 | 421 |
| Orbit Team | 97 | 8914 | 0.40 | 19 | 50 | 66 | 126 | 25 | 641 |
| sash | 77 | 4795 | 0.23 | 25 | 63 | 91 | 268 | 37 | 1772 |
| linrock | 79 | 16211 | 0.73 | 13 | 33 | 43 | 83 | 18 | 320 |

**観察**:

1. **bowwow mean 241 ships は top 8 で最大** (= 次点 flg 124 の 1.9x、 Ezra 43 の 5.6x)。 「big-stack」 戦術 確証。
2. **bowwow p99 3647 = max 13714** = 一発の超大型 launch も多用。 ただし p50 = 52 (= 並) なので **「ほぼ普通 launch + 時々 super-stack」** ハイブリッド。
3. **launch_per_step 0.43 (= 中位)** = small-stack 戦術 (= Ezra 0.71 / linrock 0.73) より低頻度、 high-stack 戦術 (= Artem 0.23 / sash 0.23) より高頻度。 **「中庸頻度 + 巨大 size」** が独特。
4. **flg は scale 同等だが LB 中位** = pure size では gold 不可、 **timing 判断**が分岐点。

## 2. Expansion timing (= step 100 / 200 / 300 で planet 数 + 総 ship 数)

| Agent | step100 pl/sh | step200 pl/sh | step300 pl/sh |
|---|---|---|---|
| **bowwowforeach** ★ | 6.7 / 563 | 7.2 / 1338 | 9.5 / 3751 |
| flg (= expansion king) | 9.4 / 574 | 17.5 / 2417 | 20.5 / 6745 |
| Artem | 7.4 / 720 | 8.6 / 2469 | 10.0 / 5553 |
| Ezra | 6.4 / 615 | 5.6 / 1132 | 8.0 / 2466 |
| linrock | 6.8 / 411 | 5.2 / 480 | 4.3 / 878 |
| Vadasz | 8.9 / 535 | 11.4 / 1138 | 5.1 / 1473 |

**観察**:

1. **bowwow expansion は moderate** = step 100 で 6.7 planet (= mid)、 step 300 で 9.5 planet (= flg 20.5 の半分以下)。 expansion で勝つ paradigm ではない。
2. **flg は expansion 20 planet で ship 6745 だが LB 中位** = expansion alone insufficient。
3. **bowwow ship 3751 (= step 300) は flg 6745 の 56% だが LB は flg の 2x 以上** = **ship efficiency (= mean 241 ships/launch で集中投擲)** が key。

## 3. 仮説 (= Phase α.2 MCTS / beam search design hints)

### H1: bowwow は「敵 home 攻撃 timing 」を探索で選んでいる
- 大型 launch の timing が偶然ではなく「敵 home defense 薄い瞬間 + 自 home defense 確保後」を狙い撃ち
- MCTS で 5-10 step lookahead して敵 ship arrival timing を予測すれば再現可能
- **検証法**: bowwow の big launch (= p99 超 = ships > 996) の **その時 敵 home defense / 自 home reserve** を data から isolate

### H2: bowwow は home defense reserve を厳密管理
- mean 241 ships で launch するなら home は 500+ ships 必要、 = home capacity が常に高い状態に build-up
- 「expand しない」 という選択が timing 待ち、 大型 launch のための ship 蓄積期間
- **検証法**: bowwow の各 step での home planet ship_count 推移、 「expand 0 / launch 0」 連続 step の頻度

### H3: bowwow ターゲット選定は「弱った enemy home」 のみ
- 中立 planet は無視、 expansion は self-reinforcement のみ
- enemy home 直撃 (= 一気に kill stack で消す) で 1 vs 3 状況打開
- **検証法**: bowwow launch の target_planet_owner 分布 (= empty vs friendly vs enemy)

## 4. Phase α.2 MCTS / beam search 設計 (= bowwow paradigm 再現)

### 4.1 探索空間
- **action**: (target_planet_id, angle_bin (= 16-32 bins), ship_count (= home_cap × fraction in [0.0, 0.5, 0.85, 1.0]))
- **branching**: ~10 planets × 16 angles × 4 fractions = ~640 (= 大、 ただし mask で実際 ~50)

### 4.2 探索深さ
- **5-10 step lookahead** (= 1 step ~1.5 sec で fleet が ~half 移動、 5 step で 中距離移動完了)
- 1 sec/step budget 内で depth 5 が現実的、 depth 10 は leaf eval 軽量化必要

### 4.3 leaf evaluator (= 3 候補)
1. **hand-crafted heuristic**: ship_count / planet_count / enemy_threat の weighted score
2. **PPO policy + value** (= θ.4 / θ.5 完成後の reuse、 Phase γ-δ で統合)
3. **shallow rollout** (= leaf から 10 step 自他 random play + 終局 score 推定)

### 4.4 prune 戦略
- **launch size = home_cap × 0.85 以上のみ評価** (= bowwow 流 big-stack mimick、 探索空間 1/3)
- **ship_count < 100 launch は完全 skip** (= mean 241 戦術と整合)

### 4.5 implement 順序
1. **5/13-5/14**: action space + step simulator + 1-step search baseline
2. **5/15-5/16**: 5-step beam search depth=5 width=64 + hand-crafted leaf eval
3. **5/17**: local 4P smoke vs konbu17_topk1、 win rate ≥ 50% target
4. **5/18-5/19**: tuning + LB submit test

## 5. 未解決 / 次調査 (= 次 session の私が引き継ぐ)

- [ ] **H1 検証**: bowwow big launch の **時 敵 home defense** を data から isolate (= episode 内 同 step で全 player の home ship 必要、 schema 上は my_ships_total と enemy_ships_total しかない、 enemy_per_planet が要追加抽出)
- [ ] **H2 検証**: bowwow の home planet ship 推移 (= 同 schema 不足、 planet 単位 data 必要、 別 parquet or replay 解析)
- [ ] **H3 検証**: bowwow launch target の owner 分布 (= action 内に target_planet_id あり、 同 step の planet ownership と join 可)
- [ ] **W2 forum 再 retry** (= 22:00 JST rate limit reset 後、 bowwowforeach の forum 投稿確認)
- [ ] **bowwow GitHub** (= https://github.com/bowwowforeach/Contest) MM148/149 解の C++ コード deep read = MCTS / beam / SA 流の実装 pattern 抽出

## 6. 関連 doc

- 親 roadmap: docs/strategy/2026-05-12-roadmap-pivot.md (= Phase α-ζ)
- W3 出力: docs/research/2026-05-12-victory-research/03-top-tier-profile-research.md (= bowwow profile + RL 天井)
- W5 出力: docs/research/2026-05-12-victory-research/05-mathematical-foundations.md (= PFSP / PPO / 4P FFA equilibrium 数理)
- Day 3 LB: docs/research/2026-05-12-submission-analyses.md (= 09:30 反映、 H1 失敗)

## 7. 出典

- bovard data: data/processed/actions/bovard_2026_05_04.parquet (= host 公開、 2,630 episodes、 LB top 30 帯)
- 集計コード: 本 doc 起票時の Bash inline (= reproducible、 commit `4359328` 以降 next commit にコード保存予定)
