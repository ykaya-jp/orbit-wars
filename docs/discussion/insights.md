# Orbit Wars 戦略 insights

> 作成日: 2026-05-10
> 情報源: discussion (0510.md, kaggle CLI で取得した topic 696043) + bovard top10 dataset (2,820,068 row) 自家分析

---

## 1. データ駆動で判明した「真の主因」

### Top tier vs Reexel/v2 の expansion 速度差

| step bin | shomossa | Erik Kvanli | bowwowforeach | flg | Vadasz | Ezra | **Reexel/v2 (推定)** |
|---|---|---|---|---|---|---|---|
| 0-99 (avg ships) | **430** | 300 | 287 | 283 | 274 | 284 | **~30-50** |
| 0-99 (avg planets) | 6.16 | 7.39 | 5.01 | 5.65 | 5.40 | 4.15 | **1-2** |
| 100-199 ships | 2161 | 1693 | 869 | 1141 | 780 | 872 | ~80 |
| 100-199 planets | 12.27 | 13.73 | 7.27 | 13.35 | 10.23 | 6.57 | ~3 |
| 400-499 ships | 15200 | **18122** | 7084 | 12267 | 3556 | 4054 | ~150 |
| 400-499 planets | 18.25 | 19.27 | 9.16 | 19.22 | 3.70 | 6.50 | ~3 |

**衝撃**: Top tier は終盤に 7000-18000 ships 持つ vs 我々 ~150 ships → **100 倍劣後**。
**真の主因は「Capacity gap」ではなく「Expansion gap」** (= step 0-100 の planet 占領数)。

### Top tier の launch サイズ分布 (per-launch ships)

| Team | p10 | p25 | **p50** | p75 | p90 | **p99** |
|---|---|---|---|---|---|---|
| shomossa | 12 | 13 | 20 | 45 | 176 | 954 |
| Erik Kvanli | 6 | 10 | 20 | 38 | 70 | 337 |
| **bowwowforeach** | 10 | 20 | **52** | **141** | **447** | **3647 ← kill stack!** |
| flg | 4 | 20 | 49 | 94 | 207 | 1912 |
| Vadasz | 9 | 15 | 25 | 42 | 70 | 154 |
| Ezra | 10 | 12 | 19 | 42 | 90 | 388 |

**所見**:
- 中央値の launch は 19-52 ships (= 思ったより小)
- p99 が 154-3647 = **終盤に kill stack で決着付ける** スタイル
- bowwowforeach の 3647 ships は突出 (Isaiah の最大 986 を遥かに上回る)

### 戦略の多様性 (各 player の avg launches/turn × avg ships)

- **shomossa**: launch_per_turn 0.95、ships 6519 → 高頻度 + 高 ships = aggressive expansion
- **Erik Kvanli**: 0.69、5594 → mid-frequency aggressive
- **bowwowforeach**: 0.59、~7084 → low-frequency big-stack (= kill stack 戦略)
- **Vadasz**: 0.74、3555 → mid-frequency mid-ships
- **Ezra**: 0.85、4054 → mid-defensive
- 単一の最適戦略は存在しない → **複数戦略が共存**

---

## 2. ディスカッション (0510.md + 直接取得分) の重要 insight

### 2.1 host 提供 dataset

**`bovard/orbit-wars-top10-episodes-YYYY-MM-DD`** が毎日 publish:
- 期間: 2026-04-16 〜 2026-05-04 (= 19 day 分)
- 各 dataset = top 10% episodes (sum of player ratings 上位)
- 各日 ~2630 episodes (1 day で 816MB) = 計 ~50,000 episodes 級
- License: CC0-1.0

```bash
for d in 2026-04-{16..30} 2026-05-{01..04}; do
  kaggle datasets download "bovard/orbit-wars-top10-episodes-$d" --unzip -p "data/external/$d"
done
```

### 2.2 engine bug (修正済)

**`sweep_fleets` の overshoot bug**: fleet が planet を **すり抜けて collision 検知されない**。
- 観測: episode 75649154 で 339 step ゲーム中 13 回発生
- 原因: 2-phase movement で fleet 移動 → planet 移動の合間 (mid-tick) の closest approach を検知しない
- **2026-04 後半に修正済** (出典: discussion 696043)
- **影響**: 修正前の replay (= bovard 2026-04-16〜29 あたり) は壊れた挙動を含む。**BC 訓練は 2026-04-30 以降** に絞るべき

### 2.3 敵 fleet の `angle` が完全 observable

**重大**: fleet record `[id, owner, x, y, angle, from_planet_id, ships]` の `angle` が **敵 fleet でも常に見える** (出典: 「I achieved 1100+ score」discussion)。
- どの target に向かっているか完全に分かる
- → **完全な lead-shot defense** が可能 (敵 fleet 着弾位置 + 時刻計算 → 守備派遣)
- → **強力な intercept** (敵が target に向かう途中で奪取)
- → **counter-attack の最適化** (敵 launch 直後の home が手薄なときに反撃)

**Phase 1.2 (DefenseMission) の設計はこの前提で**

### 2.4 LLM agent 参戦中

- Gemini 3.1 Pro (`@gemini31pro`): score 590 / rank ~1049
- Claude Opus 4.7 / GPT-5 / DeepSeek 等も追加予定
- 形式: 1-file submission, no fine-tuning, no eval-time search beyond 1s/turn budget
- (我々は **multi-file + agent 自身は eval-time 計算可能** = 制約緩い)

### 2.5 4-player FFA モード存在

- bovard top10 は 4-player FFA mode の試合
- rewards = `[1, -1, -1, -1]` 形式 (winner takes all)
- 「4p kingmaker dynamics」と discussion で言及
- 我々の agent は 2-player と 4-player 両対応必要 (kaggle_environments がどう player 数を渡すか要確認)

---

## 3. 戦略への直接含意 (= 我々の agent 改善方針)

### 3.1 即実装 (Phase 1.1b → 1.6)

| # | 改善 | 解決する gap | 出典 |
|---|---|---|---|
| 1.1b | `CaptureMission` を per-home 多 target launch に拡張 | Expansion gap (step 0-100 の planet 占領数) | bovard data § 1 |
| 1.2 | `DefenseMission` (敵 fleet angle 利用、intercept) | counter による失地 | discussion § 2.3 |
| 1.3 | `HoldMission` (production-heavy planet で守備兵力確保) | 500-step starvation | bovard 終盤 ships growth |
| 1.4 | `OpponentModelLite` (相手の launch 分布 → adaptive) | adaptive bot への対抗 | bovard § 1 戦略多様性 |
| 1.5 | `Recapture/CometGrab` 再有効化 (干渉解消後) | 既存資産 | docs/strategy/exp002 |
| 1.6 | E2E tournament 検証 (200+ ep) | 検証 gap | postmortem § |

### 3.2 中期 (Phase 2 候補)

候補 A: 段階的レシピ (Halite IV ttvand) — Phase 1 完成 → IL pretrain (bovard data 50,000 ep) → PPO finetune
- bovard data 取得済で IL の data 源は問題なし
- pretrain は **2026-04-30 以降の dataset** に絞る (bug 修正後)

候補 D: Adaptive Heuristic + Online Opponent ID — 最短ルート、bowwow / Erik / shomossa 各スタイルへの対抗 logic を rule で実装

(plan の構造原理 4 案は `~/.claude/plans/piped-sauteeing-lake.md` 参照)

---

## 4. 重要な未検証事項

- [ ] 4-player モードでの `agent(observation, configuration)` interface (player_id 0-3 で動くか)
- [ ] 2-player vs 4-player の LB segregation (= 同じ score 系列か?)
- [ ] Top tier の **target priority** (production-heavy を先に取る? それとも近接優先?) → bovard データから query 可
- [ ] Top tier の **defense response time** (敵 launch 検知から守備までの turn 数) → 同上
- [ ] kill stack のタイミング (= step 何で大艦隊形成開始?)

これらは Phase 1.2-1.3 設計前に bovard data で確認する。

---

## 5. データソース管理

| ソース | パス | 規模 | 用途 |
|---|---|---|---|
| 自分の試合 + 既存 17 replay | `data/replays/*.json` | 17 ep | initial baseline |
| bovard 2026-05-04 | `data/external/top10_replays/episodes/episodes/*.json` | 2631 ep | 戦略分析 (現在) |
| bovard 全期間 (TODO) | (未取得) | ~50,000 ep | IL pretrain (Phase 0.4) |
| extracted actions | `data/processed/actions/bovard_2026_05_04.parquet` | 2.82M row | 統計分析 |
| Meta-Kaggle ForumTopics | `data/external/meta_kaggle/ForumTopics.csv` | 495K row | (orbit-wars 関連 0 で実用性 low) |
| 取得済 topic | `data/external/topic_696043.csv` (sweep bug + visualizer) | 115 row | discussion log |
| user dump discussion | `docs/discussion/0510.md` | manual | 主情報源 |

---

## 6. discussion 自動巡回の限界

- Kaggle discussion ページは React SPA で **WebFetch / curl で content 取れない**
- `kaggle competitions topic-messages <topic_id>` は動くが topic_id 発見が手動
- Meta-Kaggle ForumTopics は orbit-wars topic を網羅していない (= snapshot が古い)
- → **0510.md 形式で user による dump が引き続き主情報源**
- 取得 topic id がわかれば `kaggle competitions topic-messages orbit-wars <id>` で content 取得可能
