# Phase η: Lux S3 路線 — IL pretrain + PPO finetune の architecture upgrade

> 目的: LB 1500 → 2000+ に push する真の breakout 戦略。
> 出典: Lux S3 Frog Parade (Isaiah Pressman, 1st place). 8 days RTX 3090 self-play
>       で SE-ResNet PPO + IL pretrain で優勝。
> https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md

## 現状の Phase 0/2 の問題点 (= Day 1 失敗の root cause)

| 課題 | 我々の Day 1 実装 | Lux S3 winner |
|---|---|---|
| state encoder | flat MLP (= 772-dim) | SE-ResNet on 24×24 grid (multi-channel) |
| action space | per-planet 81 class flat | per-position spatial map (= grid output) |
| training data | BC 158k samples × no-op majority | self-play 11M actions/sec (Rust sim) |
| compute | 100k PPO step (= 30 min) | **8 days × 4 GPUs** |
| 結果 | LB 0/30 vs heuristic | LB 1st |

我々の Phase η pilot (PPO 100k vs heuristic 0/18) は **architecture + compute の不足**。

## Phase η v2 architecture (= Lux S3 移植)

### State encoder: 64×64 grid + entity attention

```
Input planes (channels):
  0: planet_self_ships (1.0 = 1000 ships normalized)
  1: planet_enemy_ships
  2: planet_neutral_ships
  3: planet_production
  4: planet_orbiting (binary)
  5: planet_comet (binary)
  6: fleet_self_ships
  7: fleet_enemy_ships
  8: fleet_self_angle_sin
  9: fleet_self_angle_cos
  10: fleet_enemy_angle_sin
  11: fleet_enemy_angle_cos
  12: sun_mask (constant)
  13: home_distance_self (= radial encoding)

Encoder: Conv3x3 → SE-ResNet block × 4 → flatten + global features
Output: 256-dim embedding
```

### Action head: per-own-planet head

```
Each owned planet has:
  - launch / no-op (binary)
  - angle distribution (16 bins via softmax)
  - ship fraction (5 bins via softmax)

Multi-launch supported by sampling N=top-k planets per turn (= bowwow style)
```

### Training pipeline

1. **IL pretrain on bovard top-tier replays** (= 50k+ ep, all 19 days fully extracted)
   - state → expert action mapping
   - 4-fold symmetry augmentation (= rotate 90°/180°/270° + reflect)
   - BCE on launch/no-op + cross-entropy on angle/ships bins
   - Expected: 24-hour RTX 3090 → IL agent that imitates top-tier

2. **PPO finetune from IL weights**
   - PFSP curriculum: vs starter → vs konbu17 hybrid → self-play history pool
   - Rust sim rewrite (= Lux S3 trick): 10× throughput (orbit-wars Python sim is bottleneck)
   - 1-2 weeks RTX 3090 self-play
   - Expected: konbu17 圏 → top tier 圏

### 期待される LB 飛躍

- IL pretrain alone: 989 → ~1100 (= bowwow 模倣)
- PPO finetune: 1100 → 1500-1800
- Combined w/ konbu17 ensemble: 1500-1800 + α

合計 path: 989 (現) → 1100 (Day 2 topk1) → 1300 (Genetic+MCTS) → 1500 (IL pretrain) → 1800-2000 (PPO finetune)

## 実装作業ブレイクダウン

| Task | Eng-day | priority |
|---|---|---|
| Bovard 全 19 day extract (= tar.gz の re-extract) | 0.5 | high (= IL data) |
| State encoder upgrade (= 64×64 grid + 14 channels) | 1 | critical |
| SE-ResNet model (= 4 blocks) | 0.5 | critical |
| Action head (= multi-launch sampling) | 1 | critical |
| BC training script update | 1 | critical |
| Rust sim rewrite (= 10× throughput) | 5 | high (= PPO bottleneck) |
| PFSP curriculum + opponent pool | 2 | high |
| PPO long-running (= 1-2 weeks RTX 3090) | wait | high |
| 4-fold symmetry augmentation | 0.5 | medium |
| ELO ledger + selfgame logging | 1 | medium |

合計: ~14 eng-day for skeleton, +1-2 weeks for PPO compute.

## 短期妥協プラン (= compute 制約下の最大効率)

Lux S3 完全移植は 1-2 weeks。短期で 1500 圏目指すなら:

1. **Phase ζ (Rahul MCTS)** を最優先 (= 1-3 day 実装、+150-300 LB 期待)
2. **Phase η pilot** = Bovard 全 extract + SE-ResNet IL pretrain only (= 2-3 day)
   - PPO は後回し
   - IL alone でも konbu17 を超える可能性
3. **Phase ε (Genetic)** を並行 (= LB-adaptive 微調整)

## 当面の優先 (= Day 2 結果待ち)

- Day 2 LB feedback (= 9-12 hour 後) で best variant 確定
- Day 3 で Phase ζ Rahul MCTS 統合に着手
- Phase η は Day 4-5 で SE-ResNet IL pretrain 着手
