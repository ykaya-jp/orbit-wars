# Phase θ — PPO finetune from IL (Lux S3 Frog Parade レシピ)

> **目的**: Phase η v2 IL (`grid_il_v2_fw10.pt`, val acc 0.923, 88K params) を起点に PPO finetune で **vs konbu17 hybrid >= 50% 勝率**、最終的に LB **2000+** を狙う。
>
> **背景**: 2026-05-11 IL only 評価で 4P vs konbu17/Marco/orbitbotnext = **0/8 勝率** (active variant でも同様)。IL alone では Top tier 太刀打ち不可能と確定。Lux S3 1st (Frog Parade) は **8 日 × RTX 3090 + PFSP curriculum** で IL→PPO で Top1。本コンペは 4P FFA で同様パスが最有力 (出典: Lux S3 1st solution https://www.kaggle.com/competitions/lux-ai-season-3/discussion 等)。

---

## 1. 構造原理 (構造の異なる 3 案から PPO 単独を選んだ理由)

| 案 | 構造原理 | 実現可能性 | Gold 到達確率 | 採否 |
|---|---|---|---|---|
| A | **PPO finetune from IL** (Lux S3 1st 流) | 高 (歴史実績多数) | 高 (Top tier 1st 例) | ✅ **本 plan** |
| B | AlphaZero-style MCTS self-play (per-step 5s 内に PUCT) | 低 (Halite/Lux で採用 0、Python sim 重い) | 中 (探索深さ不足) | ❌ 棄却 |
| C | Pure heuristic adaptive (Halite II reCurs3 流) | 中 (rule で adaptive 模倣の困難) | 中-低 (top1-2 の学習適応を rule 再現不可) | ❌ 既に Phase γ で limit (LB 1017) |

**選択軸**: 「IL pretrain weight が既にある (val acc 92.3%) + GPU RTX 3090 24GB 利用可 + deadline 6 週」→ A。B は ROI 低、C は γ で天井確認済み。

---

## 2. Action space encoding

既存 `grid_encoder.py` の per-cell (64×64×81) を流用:

- **State (Observation)**: spatial (14, 64, 64) + globals (9,)
- **Action**: per-my-planet × 81 classes (= 16 angle × 5 frac + no_op)
  - PPO の policy head は既存 GridSEResNet の `policy_head` (= Conv 1x1 → 81 channels) をそのまま使う
  - **mask**: my_planet が無い cell の logits を `-inf` (= sampling から除外)

### Reward shaping

- **Terminal reward (sparse)**: 4P FFA rank → `{1: +1.0, 2: +0.3, 3: -0.3, 4: -1.0}`
- **Step-wise dense (Lux S3 流)**:
  - `+0.001 × (Δmy_ships_total - Δavg_enemy_ships_total)` per step
  - `+0.01 × (Δmy_planet_count - 0)` per step (= expansion bonus, 主因 lesson)
- **Discount γ**: 0.997 (= 500 step 半減で 0.22)
- **GAE λ**: 0.95

理由: 純 terminal だと credit assignment 困難 (500 step long horizon)、step-wise ships/planets で early learning signal を強化 (出典: Lux S3 Frog Parade 論文相当の standard recipe)。

---

## 3. PFSP (Prioritized Fictitious Self-Play) Curriculum

| Phase | Opponents | Episodes | 期待 |
|---|---|---|---|
| θ.1 | vs random + starter | 5k | 基礎 fire 動作の安定化 |
| θ.2 | vs Marco_1060 + orbitbotnext (混合) | 10k | Top mid tier 模倣超え |
| θ.3 | vs konbu17_hybrid (= 我家 LB best) | 10k | LB 1017 ライン突破 |
| θ.4 | vs self-history (PFSP: 古い checkpoint 重み付け) | 20k | LB 2000 へ |

**PFSP weight**: `w(opp) ∝ (1 - win_rate(opp))^2` で **負けてる相手を多く引く** (出典: AlphaStar PFSP, OpenAI Five)。

---

## 4. インフラ要件

| 項目 | 必要量 | 既存 / 不足 |
|---|---|---|
| GPU | RTX 3090 24GB | ✅ 確認済 (`nvidia-smi`) |
| 環境 wrapper | `gym.Env` 互換 4P kaggle_environments | ⚠ `tools/_run_episode.py` を gym wrap 必要 |
| Vectorized env | 16-32 parallel (CPU sim, GPU forward) | ⚠ multiprocessing 必要 |
| Replay buffer | 100k transitions × 14×64×64×fp16 ≈ 110 GB | ⚠ disk overflow、stream mode 必要 |
| Tournament gate | `goldcheck` (vs konbu17) per 1k step | ✅ 既存 |

**ボトルネック**: kaggle_environments orbit_wars は **per-step ~0.05s** (= Python pure sim)。16 parallel で 1k step/sec = 5h で 18M step (PPO 標準量)。**Rust sim 書き直し**は本 plan の scope 外 (Lux S3 1st も Python のまま PPO していた)。

---

## 5. 実装スケジュール (見積もり)

| Day | 作業 | 出力 |
|---|---|---|
| Day 2 (= 2026-05-11) | `tools/orbit_wars_env.py` gym wrapper 実装 + smoke test | env.step() で reward 出る |
| Day 3 | PPO trainer (`tools/train_ppo.py`) 実装、IL weight load + θ.1 5k step | TrueSkill vs starter > +5 |
| Day 4 | θ.2 10k step | 4P vs Marco/orbitbotnext win rate > 25% |
| Day 5 | θ.3 10k step | 4P vs konbu17 win rate > 30% |
| Day 6-10 | θ.4 self-play 20k step + tournament gate | 4P vs konbu17 win rate > 50% |
| Day 11 | submit (= 5/day 上限内で 5 candidate 試す) | LB 1500+ 期待 |

---

## 6. Critical files (新規 + 既存修正)

### 新規
- `tools/orbit_wars_env.py` — `gym.Env` wrapper for kaggle_environments orbit_wars 4P
- `tools/train_ppo.py` — PPO trainer (Stable-Baselines3 か rllib か独自)
- `src/orbit_wars/ppo_agent.py` — PPO policy 推論 wrapper (Phase η 流用)
- `agents/proxy/ppo_v1.pt` — 学習済 PPO 重み (生成物)

### 修正
- `src/orbit_wars/grid_model.py` — value_head の output が scalar になってるか確認 (PPO advantage 計算用)
- `Makefile` — `make ppo-train`, `make ppo-eval` target 追加

---

## 7. リスクと mitigation

| リスク | mitigation |
|---|---|
| PPO 学習が崩壊 (reward hacking, mode collapse) | (1) IL weight 初期化で warm start (2) entropy bonus 0.01 (3) checkpoint per 1k step で rollback 可能に |
| Python sim 速度不足 | 16 parallel env で base 5x (= 16 worker × 0.05s/step ≈ 320 step/sec, 5h で 5.7M step) |
| 4P opponent selection でメタロック | PFSP weight + 5% random uniform で diversity 確保 |
| Submit limit 5/day で学習中に時間切れ | Day 1-10 で submit せず学習集中、Day 11 から submit、deadline (6/23) まで 6 週確保 |

---

## 8. 検証 (Acceptance criteria)

PPO θ.4 完了時点:

1. `make goldcheck` = vs konbu17 win rate **>= 0.50** (8 ep × 4 seeds × 1 rotation)
2. 4P tournament (vs konbu17/Marco/orbitbotnext × 24 ep) で **>= 25% win rate**
3. Validation episode の terminal reward 分布: mean > +0.2, std < 0.8 (= 学習安定の指標)
4. submit で LB **>= 1500** (= 現在 konbu17 LB 1017 から +500)

θ.4 で 50% 達成しない場合: PPO finetune を放棄、heuristic 経路 (Phase ε genetic + Phase δ Rahul MCTS) に振り戻す。

---

## 9. 参考文献 / 出典

- Lux S3 1st (Frog Parade) — IL pretrain + PPO recipe (URL: https://www.kaggle.com/competitions/lux-ai-season-3)
- AlphaStar PFSP — Prioritized Fictitious Self-Play (出典: Nature 2019)
- Halite IV 1st (ttvand) — Hybrid heuristic+RL (出典: kaggle solution writeup)
- Stable-Baselines3 PPO — https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html
- 本コンペ host dataset bovard top10 (= IL pretrain source, 50k samples × 12 days) — URL: https://www.kaggle.com/datasets/bovard/orbit-wars-top10-episodes-2026-05-04

---

## 10. Phase 切り替え判断 (CRITICAL)

PPO θ.3 (Day 5) 終了時点で **konbu17 vs IL+PPO 勝率 >= 30%** を満たさない場合:

- **Option 1**: Reward shaping を変更 (= step-wise を倍増、terminal を削減)
- **Option 2**: Network 拡大 (= base_channels 32 → 64、params 88K → 350K)
- **Option 3**: Phase η を放棄、heuristic 経路 (Phase ε genetic + Phase δ Rahul MCTS) に戻る

判断は data 駆動: `outputs/ppo_progress.csv` の最新 1k step の win rate trend が **正勾配ならcontinue、平坦/負勾配なら Option 3** に switch。
