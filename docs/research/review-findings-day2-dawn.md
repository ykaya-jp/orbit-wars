# Independent review findings (2026-05-11 08:35 JST, pre-Day 2 reset)

## 外部レビュー agent からの critique

Read-only Explore agent が orbit-wars 全 docs/commits/LB を critique:

### 主張
1. **Gold 確率 25% / 優勝 5%** (LB top-30 = 1286, Top 1 = 1650 に対し)
2. 致命的失敗モード:
   - (A) PPO が 30% ceiling で plateau
   - (B) IL pretrain weak signal (val acc 92.3% でも tournament 0/8)
   - (C) **敵 fleet angle 全可視を heuristic で活用してない** (= "agent.py に angle 読み込みコード無し")

### 提案
- fleet angle exploit を緊急追加 (LB +100-200 期待)
- PPO 10 day → 3-4 day 圧縮
- Phase α-γ 確実 land

## 事実確認結果

### (C) fleet angle 主張 — 半分正しい

| Agent | fleet.angle 直読 | 出典 |
|---|---|---|
| `src/orbit_wars/agent.py` | ✅ | line 332 (`Fleet namedtuple`), line 649-650 (`dir_x = cos(fleet.angle)`) |
| `experiments/rudra/main.py` | ✅ | `sun_collision(m, fleet_speed, angle)`, `incoming_reinforcements` arrive_tick |
| `experiments/zachary/main.py` (= Day 2 slot 1) | ❌ | line 108-131 `planet_under_threat` で **nearest-target heuristic** (fleet が一番近い planet を target と推測、angle 未使用) |

レビュー agent は base agent.py の Fleet 定義を見落とした可能性。但し **Zachary は実際に angle 未使用** で defense 不完全 → critique (C) は Day 2 slot 1 (zachary) に限り **正しい**。

### (A)(B) は妥当

- (A) PPO 30% ceiling: design doc §10 で Option 1-3 (reward shaping/network 拡大/abandon) written
- (B) IL distribution mismatch: data-quality-audit.md で documented (bovard ≠ Top tier)

## 判断

### Day 2 (= 9:00 JST reset、残 25 min)
- **Plan 変更しない** (= zachary / Rudra / bovard×topk1 / bovard×bowwow / konbu17×topk1)
- zachary 75% 勝率は対戦相手の defense 不完全に依存している可能性、LB submit が ground truth

### Day 3 (= LB 結果次第)
**zachary に fleet.angle-based lead-shot defense を backport** が **+ROI 最大**:
- 我家 `src/orbit_wars/agent.py:332-660` の DefenseMission ロジック移植
- 1-2 day 工数、LB +100-200 期待 (review agent の見積もり)
- Day 4 から Phase θ PPO に着手

### Phase θ PPO 工程
- **10 day 維持** (3-4 day 圧縮は無理):
  - Lux S3 1st = 8 day × RTX 3090 (公式 writeup)
  - Orbit Wars 500 step × 4P >> Lux S3 360 step × 2P (state space 大)
  - PPO learning curve = rollout sample 数律速 (圧縮不可)
- 代案: Phase θ skip (= Gold 25% 受容) — 但しユーザー目標 "scope 2000+" 達成不可

## 出典
- レビュー agent message (2026-05-11 08:32 JST, pane 2 上の Explore agent)
- `docs/discussion/insights.md:§2.3` (fleet angle observability)
- `docs/strategy/phase_theta_ppo_design.md:§5,§7,§10`
- `docs/research/data-quality-audit.md` (本日午前)
