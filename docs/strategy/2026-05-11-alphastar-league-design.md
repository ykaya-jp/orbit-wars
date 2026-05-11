# AlphaStar league training design — orbit-wars Phase γ (= score 2000+ Tier 3)

> 作成日: 2026-05-11、 Day 15+ 実装予定 (= P2 PPO θ.4 200k step 完走後)
> 関連: `docs/strategy/2026-05-11-score-2000-roadmap.md` §2 Tier 3 #2、 `docs/strategy/phase_theta_ppo_design.md`
> 出典: AlphaStar Nature 2019 (Vinyals et al.)、 Lux S3 1st Frog Parade

---

## 1. 動機

PPO θ.4 真 PFSP (= 我家 P2) は **single agent self-play** で、 弱モデル循環 (= user 質問の通り) で **30% ceiling plateau** に hit する risk。 AlphaStar league は **3 種 agent を並列 training** で diversity 確保、 plateau 突破実績あり (= StarCraft II GM 級到達)。

我家 P2 (PPO θ.4) で plateau hit したら、 Phase γ で league に拡張 (= Day 15+)。

---

## 2. League 構成

| Agent 種類 | 役割 | 比率 | 学習目標 |
|---|---|---|---|
| **Main agent** | "中心" policy、 全 opponent vs train | 50% | Top tier 模倣 + 一般化 |
| **Main exploiter** | Main の弱点 attack 専用 | 25% | Main の失敗 pattern 学習 |
| **League exploiter** | 過去 全 agent から sample、 多様 attack | 25% | 全 policy の弱点 mining |

opponents pool:
- Main agent: PFSP weight ∝ (1-win_rate)² で全 league 中から sample
- Main exploiter: Main agent only (= deterministic)
- League exploiter: 全 historical checkpoints (= diversity 確保)

---

## 3. 実装方針 (= Colab Pro+ A100 で 3 agent 並列)

### 3.1 Architecture
- Base: 既存 `tools/train_ppo_pfsp.py` の `SelfHistoryPool` を **3 pool (main / main_exp / league_exp)** に拡張
- 各 agent 独立 training process (= multiprocessing or sequential)
- Colab Pro+ A100 で sequential 推奨 (= 3 agent × 200k step = 600k step = ~15h)

### 3.2 Training schedule (= 4 day × 24h budget for Phase γ)
- Day 1: Main agent 200k step (= θ.4 zip warm start)
- Day 2: Main exploiter 100k step (= vs Main only)
- Day 3: League exploiter 200k step (= vs full history pool)
- Day 4: 3 agent 同時 50k step (= cross-train)

合計 ~550k step、 ~12h on A100。

### 3.3 Submit 戦略
- Main agent → primary submit (= LB main candidate)
- Main exploiter → ablation submit (= Main の弱点に強い、 別 paradigm として有効)
- League exploiter → 3rd paradigm (= diversity)

---

## 4. 数理本質 (= 優勝本質性 §11.2)

1. **問題定式化対応**: 4P FFA で 1st position 取得 max policy 学習、 多 opponent diversity で robust
2. **優勝寄与**: AlphaStar precedent = Elo +800 over baseline、 本コンペで LB +200-400 期待
3. **代替比較**: 
   - Pure PPO (= 我家 P2): 弱 self-play 上限 = LB +200-500
   - AlphaStar league: 多様性 + plateau 突破 = LB +400-700
   - AlphaZero MCTS: 探索本質的 = LB +500-1000 (= ただし sim 速度律速)
4. **rule 耐性**: clean RL、 host fix risk なし
5. **datapoint 価値**: 3 agent 別 paradigm = 3 submit slot 同時取得可

---

## 5. 失敗モード + mitigation

| 失敗モード | mitigation |
|---|---|
| Main agent が local optima (= 弱 league pool で plateau) | exploiter 2 種 で diversity 強制、 + 5% uniform random sample |
| Exploiter が niche policy で degeneracy | reward shaping で「win regardless of opponent」 を強化 |
| Compute budget overflow (= Colab 12h session limit) | checkpoint per 25k step、 session 跨ぎ resume |
| 3 agent 同時 GPU memory OOM | sequential training、 A100 80GB plan 利用 |
| Implementation complexity → bug | sb3 callback で 3 agent training を modular 化 |

---

## 6. Phase γ 起動 condition

以下を満たしたら Phase γ 着手:
- ✅ Phase β (= P2 PPO θ.4 200k step Colab 完了) で local 4P vs konbu17 win rate measured
- ✅ Day 3-4 LB datapoint 反映、 calibration σ < 0.02 stable
- ❌ PPO θ.4 単独で LB ≤ 1400 (= plateau 確証)

If win rate ≥ 50% and LB ≥ 1500 → Phase γ skip (= Tier 2 で gold zone 到達確認)、 polish に進む。

---

## 7. 実装 milestone (= Day 15-21)

| Day | 作業 | 出力 |
|---|---|---|
| 15 | tools/train_ppo_league.py 新設 (= 3-pool sampler) | unit test pass |
| 16 | Colab notebook 拡張 (= 3 agent sequential train) | smoke 1k step × 3 agent |
| 17-19 | Phase γ.1: Main agent 200k step on A100 | agents/proxy/league_main.zip |
| 20 | Phase γ.2: Main exploiter 100k step | league_main_exp.zip |
| 21 | Phase γ.3: League exploiter 200k step | league_lge_exp.zip |
| 22 | submit 3 件 (= Main, Main exp, League exp) AB test | LB datapoint |

---

## 8. 出典

- AlphaStar Nature 2019 (= 主構造借用)
- Lux S3 1st Frog Parade: https://www.kaggle.com/competitions/lux-ai-season-3 (= self-play recipe)
- `~/projects/kaggle/CLAUDE.md` §1.3 single paradigm では gold 不可
- `docs/strategy/phase_theta_ppo_design.md` (= 既存 PPO basis)
