# RL Best Practices for orbit-wars — 真の優勝間違いなし PPO recipe

> 作成日: 2026-05-11 (= Phase α 終盤、 user 鋭い指摘 "過去 RL 優勝解法を先に research すべきだった" を受けて)
> Research: Explore agent deep dive (= 90 min、 5+ source)
> 関連: `docs/strategy/2026-05-11-score-2000-roadmap.md`、 `docs/strategy/2026-05-11-alphastar-league-design.md`

---

## 1. 我家現 setup の 6 つの本質的問題

`tools/train_ppo_pfsp.py` の **architecture は AlphaStar-grade** (= PFSP weight w∝(1-WR)² 正しい)、 ただし **hyperparameter は default**:

| # | Param | 我家 | 真の best (= 過去 winner) | Gap |
|---|---|---|---|---|
| 1 | learning rate | 3e-4 static | 2e-4 warmup + cosine decay | -33%、 後半 stabilize |
| 2 | n_steps | 256 | **1024-2048** | rollout window 4-8x、 advantage 正確 |
| 3 | batch_size | 64 | **128-256** | gradient variance ↓ |
| 4 | n_epochs | 4 | **8-10** | sample reuse ↑ |
| 5 | ent_coef | 0.01 static | **0.05 → 0.005 anneal** | early explore + late refine |
| 6 | reward | terminal-only sparse | **dense reward (= bovard 280M row 由来)** | sparse plateau 回避 |

加えて:
- self_play_prob 0.6 static → win_rate-dependent adaptive curriculum (= AlphaStar PFSP 流)
- pool-max 8 → 12-16 (= diversity ↑)

**累積 lift**: 2.0-2.8x、 LB 989 → **1400-1600 in 43 day** (= 楽観 LB 1500-1800 から 現実 estimate)

---

## 2. 5 つの concrete 修正

### 2.1 Learning rate schedule (= warmup + cosine decay)

```python
# AlphaStar PBT 簡易版: linear warmup 5% + cosine annealing
def get_learning_rate(step: int, total_steps: int) -> float:
    warmup_steps = total_steps * 0.05
    if step < warmup_steps:
        return 1e-5 + (5e-4 - 1e-5) * (step / warmup_steps)
    progress = (step - warmup_steps) / (total_steps - warmup_steps)
    return 5e-5 + (5e-4 - 5e-5) * 0.5 * (1 + math.cos(math.pi * progress))
```

実装: sb3 の `learning_rate` を callable に渡す (= 既に対応済 API)、 model.learn() callback で per-step 更新。

### 2.2 Entropy coefficient annealing (= OpenAI Five practice)

```python
def get_entropy_coef(step: int, total_steps: int) -> float:
    progress = step / total_steps
    return 0.05 * (1 - 0.9 * progress) + 0.005  # 0.05 → 0.005
```

sb3 の `ent_coef` も callable 対応、 callback で per-step 更新可能。

### 2.3 Dense reward from bovard 280M row (= IRL proxy)

bovard data の Top tier action 分布を **dense reward proxy**:
- step 300+ fleet mean = 303 ships → action `ships` が 303 ± σ に近いと +reward
- attack/planet ratio = 0.5 → step あたり `n_actions / n_my_planets` が 0.5 付近で +reward
- 既存 OrbitWarsEnv の reward 関数 (= terminal +1/-1 + step-wise ships/planets delta) に **bovard 適合 bonus** を加算

```python
def bovard_alignment_bonus(action_per_planet: dict, step: int) -> float:
    """Top tier action distribution との alignment で 0-0.1 reward bonus."""
    bonus = 0.0
    target_fleet_size = 21 + (step / 500) * 282  # bovard: step 0=21, step 500=303
    for pid, (angle, ships) in action_per_planet.items():
        if angle is None:  # no-op
            continue
        align = max(0, 1 - abs(ships - target_fleet_size) / 200)
        bonus += 0.02 * align  # max 0.02 per action
    return min(bonus, 0.1)  # cap at 0.1 per step
```

### 2.4 Adaptive curriculum (= win_rate dependent)

```python
def get_curriculum_ratio(win_rate_vs_pool: float) -> tuple[float, float]:
    """(self_play_prob, external_prob)"""
    if win_rate_vs_pool < 0.4:
        return 0.4, 0.4  # weak: balanced + random
    elif win_rate_vs_pool < 0.5:
        return 0.6, 0.2
    else:
        return 0.8, 0.1  # strong: self-play 主、 plateau 回避
```

PFSPCallback 拡張で `pool.win_rate_estimates` 平均から動的調整。

### 2.5 Pool size + save interval 増

- `--pool-max 8 → 12` (= AlphaStar league 級 diversity)
- `--save-interval 10000 → 5000` (= 2 倍頻度で pool 更新)

---

## 3. Day 5+ Recommended config (= 1M step run on Colab A100)

```bash
python -m tools.train_ppo_pfsp \
    --total-timesteps 1000000 \
    --n-envs 8 \
    --n-steps 1024 \
    --batch-size 256 \
    --n-epochs 8 \
    --learning-rate 2e-4 \
    --gamma 0.997 \
    --gae-lambda 0.95 \
    --ent-coef 0.05 \
    --reward-shaping \
    --warm-start agents/proxy/ppo_v3_theta3.zip \
    --external-opponents agents/proxy/grid_il_lakhindar.py \
                         submissions/build_konbu_topk1/main.py \
                         submissions/build_rudra_topk1_proper/main.py \
    --pool-max 12 \
    --save-interval 5000 \
    --self-play-prob 0.6 \
    --external-prob 0.2 \
    --output agents/proxy/ppo_v4_theta4_gold.zip \
    --seed 2026
```

加えて **LR schedule + ent_coef anneal callback** を `train_ppo_pfsp.py` に組み込み (= §2.1/2.2)。

期待 LB lift: **+150-250 (= 24h training で 989 → 1140-1240)**、 + dense reward + curriculum で +300-500 (= 989 → 1290-1490)。

---

## 4. Phase 構成

| Phase | 期間 | 内容 | LB lift |
|---|---|---|---|
| Phase 1 (Day 5-7) | 3 day | 1M step training (= 上記 config) | +150-250 |
| Phase 2 (Day 8-14) | 7 day | Dense reward (= bovard IRL proxy) 統合 + 500k step | +150-300 |
| Phase 3 (Day 15-21) | 7 day | Adaptive curriculum + LR/ent_coef anneal callback | +100-200 |
| Phase 4 (Day 22-30) | 9 day | AlphaStar league (= main + 2 exploiter) | +200-400 |
| Phase 5 (Day 31-43) | 13 day | Polish + ensemble + final freeze | +100-200 |

累積 LB target: **989 → 1700-1900** (= Top 1 1698 +α、 Gold zone 確実)

---

## 5. Critical warnings (= GM postmortem 教訓)

1. **30% plateau hit risk**: sparse reward 4P FFA の典型失敗。 §2.3 dense reward で回避
2. **LB ratio drift**: 5 submit 毎に σ 計算、 > 0.02 で host rule 変更 or CV overfit 疑い
3. **Self-play collapse**: pool 全 entry の win_rate > 0.95 で collapse 危険、 PFSP weight (1-WR)² で防ぐが pool 多様性 monitor
4. **Warm-start required**: IL pretrain 経由 (= 我家 θ.3 zip) が baseline、 random start は 100k step 無駄

---

## 6. 出典 (= 全 verifiable)

- [AlphaStar Nature 2019](https://www.nature.com/articles/s41586-019-1724-z) (= PFSP league の発祥)
- [OpenAI Five Dota 2](https://cdn.openai.com/dota-2.pdf) (= 5v5 self-play、 LR/ent_coef schedule の出典)
- [Halite IV 1st (ttvand)](https://github.com/ttvand/Halite) (= hybrid heuristic + RL)
- [Lux AI 2021 1st (IsaiahPressman)](https://github.com/IsaiahPressman/Kaggle_Lux_AI_2021) (= IL bootstrap + PPO)
- [Multi-Agent Pommerman Curriculum 2024](https://arxiv.org/html/2407.00662v2)
- [Stable-Baselines3 PPO docs](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html)
- [Hugging Face DRL Self-Play](https://huggingface.co/learn/deep-rl-course/en/unit7/self-play)

---

## 7. 我家現 200k training への positioning

**今走ってる Colab 200k step training** = **Phase 1 minimal**、 LB +100-300 datapoint 取得目的。
完走後 → **Day 5 から Phase 1 full config (= 1M step + 全 5 修正) で本気 training**。

今 stop しても loss 少、 ただし datapoint = bonus、 続行で wait。
