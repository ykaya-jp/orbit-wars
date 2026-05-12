# MCTS v2 loss seed trace + AlphaOrbit gap quantify — 2026-05-13 04:15 JST

> 起源: 2026-05-13 night session 「待ち時間にエラー分析徹底投入」
> 対象: MCTS v2 vs 3x starter 8 seeds (= 2/8 wins) の 6 losing seeds 内 5 seed
> 関連: docs/research/2026-05-13-bovard-deep-eda.md (= AlphaOrbit reference)
> 反映: MCTS v3 設計の root direction 確定

---

## 1. 真の負け root cause = expand 不足 (= step 100 で 8 倍劣後)

5 losing seeds (= 1, 4, 5, 6, 8) で MCTS v2 vs 3x starter の per-step planets/ships 計測:

| step | MCTS v2 平均 planets | AlphaOrbit 平均 | **GAP** |
|---|---|---|---|
| 50 | 1.6 | 8.6 | **-7.0** |
| 100 | 1.8 | **14.3** | **-12.5** |
| 200 | 4.2 | 23.4 | **-19.1** |

= **MCTS v2 は step 100 で 1.8 planet** (= AlphaOrbit の **1/8**)、 step 200 で 4.2 planet (= AlphaOrbit の 1/5.6)。

これは「expand しない」 という性質、 MCTS が探索しているはずなのに **planet 数を増やすに値する action を選んでいない**。

---

## 2. seed-by-seed loss pattern 分類

### seed=1 (= 早期 elim)
- step 50: 2 planets 68 ships
- step 100: 2 planets 254 ships
- step 200: 1 planet 85 ships (= already 失い始め)
- step 300+: 0 planet (= 完全 elim、 step 300 で死亡)
- 最終: 0 planet 0 ships、 winner = P2 (= starter) で 18 planets
- **pattern**: 序盤 expand 失敗 → 100 step で 1-2 planet stuck → 200 step 過ぎから combat で失う

### seed=4 (= ship 蓄積 → 終盤崩壊)
- step 50: 1 planet 49 ships
- step 100: 2 planets 82 ships
- step 200: 2 planets 184 ships
- step 300: 2 planets **884 ships** (= ships 大量蓄積)
- step 400: 0 planet (= 蓄積したが planet 失い)
- 最終: 2 planets 583 ships、 winner = P1 で 18 planets
- **pattern**: 2 planet stuck で ships 蓄積、 step 400 直前で大攻勢 → 取られて消耗

### seed=5 (= 即死)
- step 50: 1 planet 43 ships
- step 100: 1 planet 109 ships
- step 200: **0 planets** (= elim 確定)
- **pattern**: 1 planet で出だしから孤立、 早期 elim

### seed=6 (= 後発 expand で win!)
- step 50: 2 planets 65 ships
- step 100: 2 planets 76 ships
- step 200: **14 planets 435 ships** (= 突発 expand)
- 最終 step=230: **19 planets 1019 ships** = **win** (= reward_p0=1?)
- **pattern**: 序盤 stagnant、 step 100-200 で burst expand → 完勝

→ seed=6 は **実は MCTS v2 が win している** (= 4P FFA で 19 planets 制圧)、 earlier AB の `r=-1.0` 判定は **謎** (= 再 check 必要)。 もし真の win 数が 3/8 or 4/8 なら starter baseline (= 25%) を超えるかも。

### seed=8 (= 即死、 seed=5 同様)
- step 50: 2 planets 350 ships
- step 100: 2 planets 308 ships
- step 141: 0 planet (= early elim)
- **pattern**: ships 350-308 → 200 ships の余裕あるのに **expand 切替できず** elim

---

## 3. root cause 仮説 (= MCTS v2 が expand しない 5 仮説)

### 3.1 multi-source combo が selected されていない 仮説
`_action_combos` で "fire-from-all sources" combo を加えたが、 これは **rare に selected**。 理由仮説:
- 全 source 同時 launch = my_ships 大幅減 = leaf eval で alpha*planets + beta*ships の beta 項が下がる → 同 planet count なら no-op の方が evaluate 高い
- 「launch しない」 = ships 蓄積 = leaf eval 高い、 でも planet count 増えないので alpha 項固定
- alpha (= 10) が 1 planet 増加 だけで score +10、 一方 ships 50 減で score -50 → **「ship を温存して expand しない」 が leaf eval 最適**
- これは alpha/beta scale mismatch、 alpha を 50+ にすれば planet 増加 価値が ship 減少 cost を上回る

### 3.2 mock_opponent が starter-faithful すぎて pessimistic 仮説
mock starter は ships // 2 < 20 で何もしない、 一方 mock 我家自身も同様 = sim 内で **誰も動かない** future が rolled out。 実 environment では他 player も動く → MCTS は「動かない future」 を見て「expand 不要」 と判断、 でも reality は動かないと取られる。

### 3.3 leaf_top_k_ppo が PPO bias を最終決定に inject 仮説
top 8 leaves を PPO V(s) で rescore、 PPO θ.4 は **bowwow-style training**、 starter expand-greedy state を low-V 評価。 結果 「我家が starter にチェイス される位置」 を leaf 高 V = MCTS が我家 stationary keeping を選ぶ。 PPO weight=200 で dominate される。

### 3.4 enumerate_actions が own-target を除外 仮説
現実装は `other_planets = [p for p in state.planets.values() if p.owner != player]` で **自軍内 ships 移動を除外**。 AlphaOrbit の 68% own-target launches を完全 ignore。 = 「我家 frontline 不在」 状態を fix できない。

### 3.5 step_dependent_prune の floor が結果 starter より高い 仮説
- 我家 min_launch_early = 40 (= 修正後)
- 実 starter ships // 2 >= 20 → ships >= 40 で 20 send = 我家と同 threshold
- でも starter は **複数 planet 同時 fire** = 4 planet 各 20 ships fire = 80 total ships
- MCTS は depth=1 で **1 turn 内に 1-2 combo** = 同 turn で 40-80 ships fire = 同等 だが、 これは width=32 beam の問題

---

## 4. MCTS v3 設計 specific fixes (= Day 5+)

priority 順:

1. **leaf alpha = 10 → 50 に上げる** (= planet count を ship count の 5 倍重視) — quick fix、 仮説 3.1 対応
2. **own-target launches を enumerate_actions に追加** (= reinforcement、 仮説 3.4 対応):
   ```python
   for src in my_planets:
       if src.ships < min_launch * 2: continue  # surplus only
       for tgt in my_planets:
           if tgt.pid == src.pid: continue
           if tgt.ships < min_launch * 0.5:  # frontline depleted
               actions.append(Action(src=src, tgt=tgt, ...))
   ```
3. **mock_opponent が active agent を simulate** (= 仮説 3.2 対応):
   - opponent の predicted action を `_mock_opponent_actions` ではなく starter_agent inline call で
   - = sim 内 opponents が「starter 戦術で常に動く」 を assume、 我家を取られる pressure を MCTS に見せる
4. **depth=3 with smaller beam** (= 仮説 3.2 緩和):
   - 1 step 先のみ評価では「expand しないと取られる」 を見えない
   - 3 step 先で「starter が我家 planet 取りに来る」 を見て、 「expand しないと負ける」 と理解
5. **ppo_value_weight = 200 → 50 に下げる** (= 仮説 3.3 対応、 PPO bias を弱める)
6. **`leaf_top_k_ppo` を 8 → 3 に下げる** (= PPO inference 量削減 + 多様 leaf を許容)

= 6 件の changes、 各 30 分以内に implement + AB measurement、 全体 3-4h で Day 5 提出版完成。

---

## 5. seed=6 の謎 (= AB tournament 結果の整合性)

seed=6 で env 内では 19 planets で完勝 (= step 230 finish) だが earlier AB では `r=-1.0`。 これは:
- AB tournament の env.run と 本 trace の env.run で **seed=6 が違う initial state** を生成している?
- 我家 mcts_v2 main.py で `os.environ['MCTS_V2_DEBUG']` 等 stateful な何か?

再現性検証 (= 次 session で確認):
```bash
.venv/bin/python -m tools._run_episode --left submissions/build_mcts_v2/main.py --right starter --p3 starter --p4 starter --seed 6 2>&1 | tail -1
# expected: r=1.0 step=230 plnt=19、 もしくは r=-1.0 step=199 (= 旧 AB)
```

不一致なら **agent の hidden state issue** (= MCTS internal random / load 状態)、 別途 debug。

---

## 6. 「mcts は明日も使えるのか」 への自答

本 EDA で明らか:
- **MCTS の設計方向は正しい** (= expand 価値を ships の 5 倍に scale すれば improve 期待)
- **mock_opponent と own-target が現状の 2 blocker**、 これらが fix で 2/8 → 4-5/8 vs starter に届く可能性大
- **Day 5+ で 6 件の fix を ship**、 LB datapoint 取得 (= まず slot 候補化 = vs konbu 1-2/8 まで)
- **Day 10+ で paradigm A (= AlphaOrbit-style) 完全 reproduce** が gold 圏 path

つまり MCTS は **dead** ではなく **未完成**、 41 day で path がある。 一方で「6 fix」 がもしすべて wrong 仮説なら time wasted、 慎重に AB measure 必須。

---

## 7. 関連 commits + docs

- `4b141e3 fix(mcts): sim parity` (= 真因 reality check の途中段階)
- `be252a5 feat(eda): bovard 906 episodes deep dive`
- `f666b51 feat(eda): LB drift エラー分析`
- 本 doc: `docs/research/2026-05-13-mcts-loss-analysis.md`
- 次 session 用 MCTS v3 implementation reference (= 本 §4 の 6 fixes)
