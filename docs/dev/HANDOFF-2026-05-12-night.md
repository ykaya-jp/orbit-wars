# Orbit Wars Kaggle 引継ぎ — 2026-05-12 23:30 JST (= night session 終了時)

> 前 doc: `docs/dev/HANDOFF-2026-05-12-pivot.md` (= 5/12 10:00 JST morning pivot 後)
> 本 doc: 5/12 23:30 JST night session 終了時の delta + 5/13 Day 4 reset 直前 cold-start 用 即 action
> 関連: docs/strategy/2026-05-12-roadmap-pivot.md ★、 docs/research/2026-05-12-bowwow-reverse.md、 .criteria/kaggle-orbit-wars-day4-submit-2026-05-13.yaml

---

## 1. Night session summary (= 10:00 → 23:30 JST delta)

morning pivot doc §7 の 「即 action 11 step」 のうち以下が完了した:

| Step | 状態 | 物 |
|---|---|---|
| 1. 時刻 + git/submit status 確認 | ✅ | morning + night 両 session で実施 |
| 2. handoff + roadmap pivot + bowwow-reverse の 3 doc を read | ✅ | morning |
| 3. θ.5 進捗確認 (= user 依頼必要) | **未** | next session で user に Cell A/B/C 実行依頼 |
| 4. Phase β.1 = build_ppo_lightweight.py | ✅ | `4734b87` morning (= 425MB → 64.5MB) |
| 5. build_ppo_v4_theta4_light/ 構築 | ✅ | morning (smoke PASS) |
| 6. smoke 全 5 build 確認 | ✅ | **night** (= 2026-05-12 23:30 JST、 5/5 PASS、 §3 参照) |
| 7. `.criteria/kaggle-orbit-wars-day4-submit-2026-05-13.yaml` rewrite | ✅ | `2e49e71` night (= 5 slot pivot 反映) |
| 8. W2 retry (= forum + 公開 kernel 再確認) | **未** | rate limit 解除済、 next session で WebFetch 実行 |
| 9. Phase α.2 first cut = MCTS v0 skeleton | ✅ | `2767c90` night (= depth=3 beam, 1168 行、 smoke 1.37s DONE) |
| 10. Day 4 reset 後の `bash tools/day4_submit.sh` | **未** | 5/13 09:00 JST 待ち |
| 11. Day 4 LB initial を analyses doc に append | **未** | 5/13 09:30 JST 待ち |

完了 6 / 11、 待機 3 / 11 (= time-gated)、 真の未完 2 / 11 (= step 3 user 依頼 + step 8 W2 retry)。

---

## 2. New commits (= morning pivot 以降 6 件)

```
2767c90 feat(phase-alpha-2): mcts v0 skeleton (= depth=3 beam, smoke PASS but vs konbu17_topk1 0/8 wins)
dc16970 docs(postmortem): 2026-05-12 subprocess-output-silence-misdiagnosed-as-stuck
2e49e71 docs(criteria): Day 4 plan を pivot 反映 5 slot に rewrite
d22a8ed docs(handoff): Phase β.1 完了反映 (= PPO lightweight 64.5MB submit-ready)
4734b87 feat(phase-beta-1): PPO lightweight build = 425MB → 64.5MB (= 84.8% 削減)
9a68875 docs(handoff): 2026-05-12 morning session pivot handoff (= roadmap 大幅変更後)
```

morning pivot doc は HEAD `2767c90` 時点では既に 2 commit 遅れ (= criteria + MCTS v0 未反映)、 本 doc がそれを補完する。

---

## 3. Smoke 結果 (= 2026-05-12 23:30 JST、 `bash tools/smoke_day4.sh`)

5 build 全 PASS、 全部 60s timeout cap 内に余裕で完走:

| Build | duration_sec | step_count | status_p0 |
|---|---|---|---|
| submission_v2 | 10.782 | 195 | DONE |
| fleet_angle_zachary_v3 | 0.783 | 123 | DONE |
| fleet_angle_zachary_v5 | 0.805 | 123 | DONE |
| marcodg_topk1 | 7.490 | 152 | DONE |
| ppo_v4_theta4_light ★ | 1.386 | 249 | DONE |

ppo_v4_theta4_light が 1.4s で完走 = 軽量化 build の cold-start cost (= zip extract + sb3 model load) は実用範囲、 100MB cap も満たす (= 64.5 MB)。

MCTS v0 は別途 commit `2767c90` の smoke 結果に記録: seed=42, vs 3x starter で 1.37s DONE, 0.1ms/step。

---

## 4. 2026-05-12 23:29 JST LB snapshot (= day 3 結果 24h drift 計測点)

| Sub ID | File | morning 09:30 LB | **night 23:29 LB** | Delta | 解釈 |
|---|---|---|---|---|---|
| 52559128 | submission_v2 | 954.1 | **903.4** | -50.7 | downward drift (= LB pool に強 agent 増加) |
| 52559144 | konbu17_topk1 | 600.0 | 600.0 | 0 | 既に底、 動かず |
| 52559206 | fleet_angle_zachary | 703.8 | 703.8 | 0 | 不変 |
| 52559222 | rudra_topk1_bowwow | 808.2 | **888.7** | **+80.5** | reverse drift = mix 改善 |

**観察**: 同一 day 内で同 build が +80 / -50 と分布、 σ ≈ 60、 ratio drift CRITICAL > 0.02 を確実超過。 Day 4 の ratio calibrate (= 親 Kaggle CLAUDE.md §4.3) **必須実施**。 day4_submit.sh の slot 1 は drift resample 用設計、 想定通り。

---

## 5. Day 4 slot 構成 + MCTS v0 除外判断

### 確定 5 slot (= `tools/day4_submit.sh` + `.criteria/kaggle-orbit-wars-day4-submit-2026-05-13.yaml`)

1. **Day 3 best resubmit** = `${DAY3_BEST_FILE:-submissions/submission_v2.tar.gz}` (= 24h resample + ratio drift calibrate)
   - 09:30 JST LB 反映後、 user が `DAY3_BEST_FILE=submissions/rudra_topk1_bowwow.tar.gz` 等で override する可能性
   - 現状 night snapshot で **rudra_topk1_bowwow = 888.7** が day 3 best、 v2 は 903.4 で僅差。 LB 反映 30 分以内に判断
2. **fleet_angle_zachary_v3** = main rule paradigm
3. **fleet_angle_zachary_v5** = v3 + step 300+ fleet boost、 bovard 数値駆動 ablation
4. **marcodg_topk1** = 別 paradigm
5. **ppo_v4_theta4_light** ★ = 軽量化 64.5 MB、 100 MB cap 仮説実証 + RL paradigm 1st LB datapoint

### MCTS v0 (= build_mcts_v1) を Day 4 slot に**入れない**判断

morning pivot doc §6 では 「build_mcts_v1.tar.gz (Phase α.2 試作 が間に合えば、 5/13 09:00 までに 1 file)」 と暫定方針。 night session で smoke 完走確認したが、 commit `2767c90` メッセージに以下記録あり:

> vs konbu17_topk1 (8 seeds, p3/p4=starter): **0 wins** — v0 leaf heuristic too coarse to beat konbu17's tuned production-engine baseline.

ローカル 8 seed で konbu17_topk1 に 0/8 = LB 推定 500-650 圏 (= konbu17_topk1 自身が 600.0 なので、 0 wins build は同等以下)。 datapoint 価値が 「submit する場合、 仮説 isolate ができるか? noise 範囲に埋もれる submit は価値ゼロ」 (親 §11.2 #5) に該当しない。

→ **MCTS v0 は次 session で leaf heuristic 改善 + opponent diversity 拡張してから Day 5 以降 で submit**。 Day 4 は確実な 5 slot を維持。

---

## 6. **Cold-start next session 即 action 7 step** (= 5/13 朝起床時)

### 開始時 (= 5/13 08:00-08:30 JST 想定)

1. **時刻 + git/submit/Day 4 reset 確認**:
   ```bash
   date
   cd ~/projects/kaggle/orbit-wars
   git log --oneline -10
   .venv/bin/kaggle competitions submissions orbit-wars | head -8
   ```
   - 5/12 23:30 以降に user 手動 submit があれば反映確認
   - Day 4 quota reset = 09:00 JST、 reset 前なら submit 不可

2. **本 doc + morning pivot doc + day4 criteria yaml の 3 つ read**:
   ```bash
   cat docs/dev/HANDOFF-2026-05-12-night.md
   cat docs/dev/HANDOFF-2026-05-12-pivot.md
   cat .criteria/kaggle-orbit-wars-day4-submit-2026-05-13.yaml
   ```

3. **θ.5 1M step training 進捗を user 確認** (= step 3 carry-over):
   - Colab で以下 3 cell 実行を user 依頼:
     - Cell A: `ls /content/drive/MyDrive/orbit-wars/ppo_pfsp_pool_theta5/`
     - Cell B: `tail -30 /content/drive/MyDrive/orbit-wars/ppo_v5_theta5_training.log` + ckpt update 時刻
     - Cell C: `nvidia-smi` + `pgrep -af train_ppo_pfsp`
   - 期待値: ~500k step (= morning pivot §5 計算)、 ckpt pool に 5-12 件蓄積
   - θ.5 出力が submit-ready なら Day 5 候補に edit、 ただし軽量化 build script を流す必要

### Day 4 reset 後 (= 5/13 09:00 JST 以降)

4. **Day 3 best 確認 → DAY3_BEST_FILE override 判定**:
   ```bash
   .venv/bin/kaggle competitions submissions orbit-wars 2>&1 | head -8
   ```
   - rudra_topk1_bowwow が 888 維持 / submission_v2 を超えていれば override
   - 例: `DAY3_BEST_FILE=submissions/rudra_topk1_bowwow.tar.gz DAY3_BEST_LB=888.7 bash tools/day4_submit.sh`
   - 同等なら default = submission_v2 のまま

5. **Day 4 5 件一括 submit**:
   ```bash
   bash tools/day4_submit.sh
   ```
   - 30s sleep 入り、 全 5 件で ~3 分

6. **09:30 JST: LB initial 反映 → analyses doc append** (= 「随時やれ」 ルール、 親 §8.1 #9):
   ```bash
   .venv/bin/kaggle competitions submissions orbit-wars | head -10
   ```
   - `docs/research/2026-05-13-submission-analyses.md` に各 slot の est → LB → delta → 解釈 を append
   - ratio drift σ を Day 3 + Day 4 = 10 submit で再算出 (= AC-7)
   - **ppo_v4_theta4_light が 400 reject されない** ことを確証 = 100 MB cap 仮説実証
   - PPO θ.4 light LB が出たら **RL paradigm 1st datapoint** = victory roadmap §β の現実性 update

### Day 4 後

7. **W2 retry** (= step 8 carry-over、 forum + 公開 kernel 再確認):
   - `kaggle competitions topic-messages orbit-wars` で bowwowforeach の投稿確認
   - 公開 kernel 17+ で 100 MB 近傍 RL kernel が新規追加されているか audit
   - 結果は `docs/research/2026-05-12-victory-research/02-orbit-wars-forum-deep-dive.md` に append

---

## 7. 未完了 carry-over (= 次々 session 用)

- **Phase α.2 MCTS v1 強化** (= leaf heuristic 改善):
  - v0 = hand-tuned `alpha*planets + beta*ships - gamma*enemy_ships - delta*enemy_planets`
  - 候補強化: (a) PPO θ.4 light を leaf evaluator として使う、 (b) shallow rollout (= depth 3 simulate 後 score)、 (c) bowwow data 駆動の dynamic α/β/γ/δ (= step 帯別 weights)
  - vs konbu17_topk1 で 4/8+ wins、 vs starter 4/4 wins まで上げる
  - Day 5 / Day 6 で submit 候補
- **Phase β.2 PPO leaf evaluator 統合**:
  - `tools/mcts_orbit_wars.py` に PPO inference 組込
  - LB monitor で MCTS+PPO_leaf hybrid の効果計測
- **W4 LB monitor 自動化** (= 親 §8.1 #9 + morning §10):
  - top 10 team の submission timing 検知遅れは 1 day = 2.4% 時間損失
  - 48h 着手期限は morning から ~14h 経過、 残 34h

---

## 8. Drive 状態 (= morning から不変、 §10 cleanup deferred)

私可視 (= 494.6 MB total): ppo_v3_theta3.zip 494 MB / orbit_wars_weights.tar.gz 0.4 MB / 3 notebook 0.1 MB
私不可視 (= Colab notebook write 経由、 推定 数 GB):
- `ppo_pfsp_pool_theta4/`: 8 ckpt × ~430 MB ≈ 3.4 GB
- `ppo_pfsp_pool_theta5/`: 走行中 (= θ.5 1M step training、 ~12h 経過なら ~250-500k step、 ckpt 数 5-12 蓄積想定)
- `ppo_v1_theta1.zip` / `ppo_v2_theta2.zip`: 削除候補

Cleanup は θ.5 完走後 (= 5/13 09:00 JST 以降 or 5/14) deferred。

---

## 9. 観察 + 教訓 (= night session で得たもの)

- **MCTS v0 「0 wins」 を datapoint 浪費前に検知できた**: smoke を 8 seed AB tournament でやる規律が効いた (= 親 §11.2 #5 「noise 範囲 submit 価値ゼロ」 を予防)
- **LB drift 24h 内 σ ≈ 60 を測定**: 1 submit 結果で agent 性能判定すると ±60 の noise を真値と誤認、 morning H1 「fleet.angle defense backport 失敗」 確定が妥当でも、 H2/H4/H5 は 24h resample 必須
- **rudra_topk1_bowwow の +80 reverse drift**: LB pool 入替で mix 改善型 build が浮上、 つまり 「相対強さ」 は pool composition 依存。 next agent は pool に robust であるべき (= bowwow も「pool に依らず勝つ」 1823)

---

## 10. 関連 docs (= 階層構造)

- 本 doc: `docs/dev/HANDOFF-2026-05-12-night.md` (= night session 終了 + 5/13 cold start)
- 前 doc: `docs/dev/HANDOFF-2026-05-12-pivot.md` (= morning pivot 完了)
- 前々 doc: `docs/dev/HANDOFF-2026-05-12.md` (= 5/11 night、 historical)
- roadmap: `docs/strategy/2026-05-12-roadmap-pivot.md` (= Phase α/β/γ-ε 分解)
- bowwow reverse: `docs/research/2026-05-12-bowwow-reverse.md` (= 戦術 data + MCTS design hints)
- victory research: `docs/research/2026-05-12-victory-research/01..05-*.md` (= W1/W3/W4/W5 出力)
- Day 4 criteria: `.criteria/kaggle-orbit-wars-day4-submit-2026-05-13.yaml`
- project-local CLAUDE.md: `./CLAUDE.md` (= latest pointer 本 doc に update)
- 親 Kaggle CLAUDE.md: `~/projects/kaggle/CLAUDE.md` (= §0 session protocol、 §11 優勝本質性)
- 親親: `~/.claude/CLAUDE.md` (= 主道フレームワーク + lessons.md)

---

End of night handoff. **次 session = 5/13 朝の cold start で §6 「即 action 7 step」 を順に実行**。 本 doc + morning pivot doc + day4 criteria yaml を read すれば full continuation 可能。
