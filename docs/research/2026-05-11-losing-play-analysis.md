# 負けプレー分析 — 2026-05-11 (Day 2 LB games)

> 共通 CLAUDE.md §8.1 item 9 (= 「随時やれ」 ルール) に従い、 LB submission 後の actual gameplay を inspect。

## 入手 episodes (5 件、 全 Day 2 submission)

| Submission | LB | Mode | Opponents | 結果 |
|---|---|---|---|---|
| zachary 600 | 4P FFA | Reexel × 3 | TIE 1/4 (= 全員 reward 1) |
| rudra 692 | 2P | Reexel | LOST 2/2 |
| bovard+topk1 679 | 2P | Reexel | LOST 2/2 |
| bovard+bowwow 854 | 2P | Jan Wrobel | LOST 2/2 |
| konbu17+topk1 947 | 2P | PxlPau | WON 1/2 |

## Critical pattern (= 5/5 episodes 共通)

### 数値例: rudra vs Reexel (episode 76262314, 127 step)

| step | us launches | us ships | opp ships | us planets | opp planets |
|---|---|---|---|---|---|
| 0 | 0 | 10 | 10 | 1 | 1 |
| 25 | 2 | 13 | **82** (6x) | 3 | **6** (2x) |
| 50 | 2 | 200 | **489** (2.4x) | 10 | 12 |
| 75 | 2 | 255 | **823** (3.2x) | 10 | **16** |
| 100 | 0 | 206 | **1121** (5.4x) | **3 (lost)** | **21** |
| 125 | 0 | 100 | **2002** (20x) | **1** | **23** |

**Total stats**:
- 我家 launches: **134** vs opp **703** = **5.2x undershoot**
- 我家 ship size avg: **18** vs opp **37** = **2x undershoot**
- 我家 ship size median: **13.5** vs opp **30** = **2.2x undershoot**

→ **完全に opponent に expansion 負け + 艦隊小さい**

### Top tier (kovi LB 1480) との比較

| 指標 | Reexel (LB ~700) | 我家 Rudra (LB 692) | kovi (LB 1480) |
|---|---|---|---|
| launches/episode | 703 (in 127 step = 5.5/step) | 134 (1.0/step) | 117 (= 0.5/step) |
| ship size median | 30 | 14 | 32 |
| ship size p90 | ~60 | 35 | 107 |

**興味深い**: Reexel (LB 700 中堅) は kovi (LB 1480) より launch 頻度が**高い** (5.5/step vs 0.5/step)。
→ **launch 頻度だけでは LB 決まらない**。 **ship size 質 + target 選択** が重要。

我家 Rudra は launch 頻度 1.0/step (= mid-tier より低い、 top-tier より低い、 完全劣後)。

## 仮説帰納 — なぜ負けてる?

### H1: matchmaking trap
- LB 600-900 帯に居ると、 同帯 (Reexel = LB sub-1000) と組まれる
- 1100+ 帯に escape しないと top tier との対戦データが取れない
- → **既存 LB best (= konbu17 hybrid + bovard validator 989) を再 submit して 1000+ 帯確保が先**

### H2: 2P vs 4P 訓練 mismatch
- 我家 local benchmark = 4P FFA only
- LB は 2P 多 (= 5 episodes 中 4 が 2P)
- 2P では「全敵 = 1 個」、 expansion の優先度 / risk profile が違う
- → **local 2P benchmark 必須**

### H3: launch frequency 過小
- 我家 1.0/step、 mid-tier 5.5/step
- Rudra MIN_SHIPS_MINE_ATTACK=10 で launch 抑制されている
- bovard validator で「打つかどうか」決めるとき false negative 多
- → **MIN_SHIPS↓ + threshold↓ で launch frequency 増やす**

### H4: 4P TIE 問題 (zachary)
- zachary は 4P FFA で **500step 何も起きず TIE** (1,1,1,1 = 全員 winner)
- 過度に保守的 (= 攻撃しない or 敵がいなくても発射しない)
- → **expansion bonus の reward shaping** で aggressive 化必要

## 即実行アクション

### Day 3 submit (= 5/12 09:00 JST reset、 5 slots)

1. **既存 LB best 再 submit** (= 989 級 konbu17 hybrid + bovard validator) → matchmaking escape
2. **rudra MIN_SHIPS=5** variant → launch frequency increase test
3. **konbu17 + bovard + topk1** (= author claim +75) 再 submit
4. **PPO θ.2** (= IL pretrain + vs strong opponent training 完了後)
5. **zachary + aggressive reward shaping** (= expansion bonus 追加 + 4P FFA TIE 防止)

### Phase θ PPO 修正

- **追加**: `--il-pretrain agents/proxy/grid_il_v2_fw10.pt` で warm start
- **追加**: opponent rotation = 3 random → 1 random + 1 starter + 1 our_konbu17
- **追加**: `--reward-shaping` で expansion bonus を有効化 (Day 2 default off の見直し)

## 出典

- Episode replays: `data/external/our_episodes/episode-7626*-replay.json`
- Kaggle API: `kaggle competitions episodes <sub_id>`, `replay <ep_id>`
- Top tier stats: `data/external/rank1_lakhindar` 25 ep kovi FFA 分析 (本日早朝)
- 共通 CLAUDE.md §8.1 (= 「随時やれ」 ルール根拠)
