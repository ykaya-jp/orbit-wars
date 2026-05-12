# Orbit Wars Kaggle 引継ぎ — 2026-05-12 10:00 JST (= roadmap pivot 後)

> 前 doc: `docs/dev/HANDOFF-2026-05-12.md` (= 5/11 night 起票、 私 morning session 前)
> 本 doc: 私 morning session (= 08:14-10:00 JST) で **roadmap 大幅 pivot** 後の状態。 次 session 即読込必須。
> 関連: docs/strategy/2026-05-12-roadmap-pivot.md ★、 docs/research/2026-05-12-victory-research/*.md、 docs/research/2026-05-12-bowwow-reverse.md

---

## 1. 本 session 大発見 サマリ (= 3 確証 + 1 pivot)

### 確証 (= 一次資料、 GM-level confirmed)
1. **Kaggle agent comp submission size limit = 100 MB** (= Lux S3 1st Isaiah Pressman writeup 「62MB shy of the 100MB submission file size limit」 / W1+W6 一次資料)
2. **RL paradigm LB 天井 = 1500-1650** (= 世界 top RL Isaiah Pressman / Lux S3 1st が orbit-wars LB 5 / 1548 で停滞 / W3)
3. **bowwowforeach (LB 1 / 1823) = pure rule-base + 探索** (= AtCoder Heuristic 3216、 AHC 1 位 4 回、 GitHub C++ 100%、 DL commit ゼロ / W3)
4. **bowwow data 流戦術 = mean launch 241 ships (= 次点 flg の 1.9x) + launch/step 0.43 (中位)** = **timing 選択型 big-stack** (= bovard 280万 row 集計、 5/12 09:50 JST)

### Roadmap pivot: PPO 一辺倒 → rule + forward search hybrid
- 既存 (5/11 起票): Phase γ.1-γ.3 (= 全部 PPO training)、 Phase δ AlphaStar league (= PPO + exploiter)
- 新 (5/12 起票): Phase α (= rule + MCTS/beam) + Phase β (= PPO 軽量化 leaf evaluator 再利用) + Phase γ-ε (= 統合 → meta-agent → freeze)
- 詳細: `docs/strategy/2026-05-12-roadmap-pivot.md` (= 169 行)

---

## 2. Day 3 LB 結果 (= 09:30 JST 反映、 全件 COMPLETE)

| Slot | Sub ID | File | LB | 期待 | Delta | 結論 |
|---|---|---|---|---|---|---|
| 1 | 52559128 | submission_v2 | **954.1** | 989 | -35 | 24h drift downward |
| 2 | 52559144 | konbu17_topk1 | **600.0** ⚠️ | 922 | -322 | LB pool shift で大暴落 |
| 3 | ❌ | ppo_v3_theta3 | **400 reject** | — | — | 428 MB > 100 MB cap = 確定 |
| 4 | 52559206 | fleet_angle_zachary ★ | **703.8** ⚠️ | 1100-1300 | -400~600 | **H1 完全失敗** |
| 5 | 52559222 | rudra_topk1_bowwow | **808.2** | 900-1100 | -100 | rudra base から +116 |

**結論**: 全件 989 下回り、 LB pool shift 顕著 (= 上位選手 strong agent 投入で全体 score 下振れ)、 H1 「fleet.angle defense backport で +500」 仮説 完全 失敗 (= 真因は expansion 不足ではなく long-term plan 不在、 W3 と整合)

詳細: `docs/research/2026-05-12-submission-analyses.md` (= 09:32 期限内 append 済)

---

## 3. 6 worker 並列 research 出力 (= 2026-05-12 09:13-09:30 JST dispatch)

| Worker | 出力 | 状態 | 主結論 |
|---|---|---|---|
| W1 | docs/research/2026-05-12-victory-research/01-past-comp-rl-deployment.md (356 行) | 完了 | Lux S3 1st 100 MB cap 確証、 state_dict + FP16 = 85 MB 必須 |
| W2 | 02-orbit-wars-forum-deep-dive.md (329 行) | 部分完了 + rate limit hit (= 22:00 JST 解除済、 retry 推奨) | host forum で size limit 未明示、 公開 kernel 17+ で 100 MB 近傍 RL 0 件 |
| W3 | 03-top-tier-profile-research.md (288 行) | 完了 | bowwowforeach = rule-base + 探索、 RL 天井 1500-1650、 **戦略 pivot trigger** |
| W4 | 04-llm-augmentation.md (294 行) | 完了 | 多刀流 (Claude + Codex + Gemini 3.1 Pro)、 LB monitor 自動化 48h 着手 |
| W5 | 05-mathematical-foundations.md (557 行) | 完了 | **PPO θ.5 即修正 2 件**: pexp 2→1.0、 target_kl 0.02、 + dense reward K=6 飽和 patch |
| W6 | (= 直接 return、 file 不作成) | 完了 | kaggle-api source に client validation なし、 server-side 100 MB enforce |

合計 1993+ 行の research artifact (= commit `4359328` push 済)

---

## 4. Phase α.1 進捗 (= bowwow reverse engineer)

`docs/research/2026-05-12-bowwow-reverse.md` 起票 (= commit `42b1147`)。 主成果:

### bowwow 戦術データ確証
| 指標 | bowwow | 次点 | 5 番目 (ref) |
|---|---|---|---|
| mean launch ships | **241** ★ | 124 (flg) | 43 (Ezra) |
| launch/step | 0.43 中位 | 0.46 (flg) | 0.73 (linrock) |
| p99 launch ships | **3647** ★ | 1912 (flg) | 268 (sash) |
| step 300 planets | 9.5 中位 | 20.5 (flg expansion king) | 4.3 (linrock) |
| step 300 ships | 3751 | 6745 (flg) | 878 (linrock) |

### Phase α.2 MCTS / beam design hints
- action space: (planet × 16 angle × 4 fraction = ~50 after mask)
- depth 5-10 step lookahead、 width 64-256
- leaf eval 3 候補: (a) hand-crafted heuristic (b) PPO θ.4/θ.5 (c) shallow rollout
- prune: home_cap × 0.85 以上のみ評価 (= bowwow mimick)

---

## 5. θ.5 1M step training 状況 (= Colab 走行中)

- **trigger**: 2026-05-12 ~08:20 JST (= warm-start θ.4)
- **fps 観測**: 5-6 (= iter 1 = 22 min)
- **計算**: 1M step / 8192 step/iter * 22 min = **~45h** = 24h Colab session 内に完走しない
- **予測**: ~23h で session 切れる時点で **~500k step** に到達、 ckpt save_interval 5000 で pool に蓄積
- **best ckpt 選定**: session 切れ後 local AB tournament (= ckpt step 100k-500k 各 50 ep) で LB 候補選定

### θ.5 cmd 再確認 (= user paste)
```python
--total-timesteps 1000000 --n-envs 8 --n-steps 1024 --batch-size 256 --n-epochs 8
--learning-rate 5e-4 --warm-start agents/proxy/ppo_v4_theta4.zip
--external-opponents grid_il_lakhindar.py konbu17_topk1/main.py rudra_topk1_proper/main.py
--pool-max 12 --save-interval 5000 --self-play-prob 0.6 --external-prob 0.2
--lr-schedule cosine 5e-4→5e-5 --ent-schedule anneal 0.05→0.005 --seed 2026
```

### θ.6 で適用すべき W5 修正 (= θ.5 完走後)
1. **PFSP exponent $p_{exp} = 2 \to 1.0$** (= tools/train_ppo_pfsp.py:67)
2. **target_kl = 0.02 early stopping 有効化** (= sb3 PPO default は None)
3. **dense reward に logistic carrying capacity K=6 飽和 patch** (= phase_theta_ppo_design.md:36 の `+0.01 × Δplanets` を `+0.01 × max(0, min(Δplanets, K-N))` に)

### 前 session 「stuck」誤診断 教訓 (= Task #10)
- **誤**: 「params: 42,991,539 出力後 22 min 沈黙 → opp file 不在で hang」 と速断
- **真**: SubprocVecEnv 1st rollout 8192 step 収集に 22 min かかる + subprocess.Popen の output が log file に未 flush
- **learn**: stuck 判定は GPU util + ckpt 出力 + log file 増加 + 時刻計算 で 多面確認、 stdout 沈黙のみで判断しない
- → lessons.md or learned/failure-patterns/ に記録候補

---

## 6. Day 4 plan 影響 (= roadmap pivot 受けて slot 構成 update 必要)

既存 `.criteria/kaggle-orbit-wars-day4-submit-2026-05-13.yaml` + `tools/day4_submit.sh` slot:
1. Day 3 best 再 submit (= rudra_topk1_bowwow 808.2 だが 24h drift で更に下振れ予想、 ratio drift calibrate)
2. fleet_angle_zachary_v3 (= H1 失敗を受けて優先 down、 ablation のみ)
3. fleet_angle_zachary_v5 (= 同上)
4. marcodg_topk1 (= 別 paradigm、 LB 未知)
5. ppo_v4_theta4.tar.gz ★ → **submit 不可能 (425 MB > 100 MB)、 軽量化 build に置換必要**

### Day 4 新 slot 提案 (= pivot 反映)
1. **rudra_topk1_bowwow 再 submit** (= 24h resample、 ratio drift 計測必須)
2. **build_ppo_v4_theta4_light.tar.gz ★** (= 軽量化 = state_dict + FP16、 < 100 MB で submit test、 100 MB 仮説実証 + RL paradigm LB datapoint)
3. **build_fleet_angle_zachary_v3 or v5** (= main rule paradigm continue)
4. **build_mcts_v1.tar.gz** (= Phase α.2 試作 が間に合えば、 MCTS depth 3 + heuristic leaf eval、 5/13 09:00 までに 1 file)
5. **build_marcodg_topk1.tar.gz** (= 別 paradigm)

→ **5/12 残時間で Phase β.1 (= build_ppo_lightweight.py) 着手 + Phase α.2 first cut (= MCTS v0 skeleton) が次 session priority**

---

## 7. 次 session 即 action (= 11 step、 cold start から続行)

1. **時刻 + git/submit status 確認**: `date`、 `git log --oneline -10`、 `.venv/bin/kaggle competitions submissions orbit-wars | head -8`
2. **本 doc + roadmap pivot doc + bowwow-reverse doc を read**: §1-6 内容 全把握
3. **θ.5 進捗確認** (= user に Cell A/B/C 実行依頼、 §5 cmd):
   - Cell A `ls /content/drive/MyDrive/orbit-wars/ppo_pfsp_pool_theta5/`
   - Cell B `tail -30 ppo_v5_theta5_training.log` + `stat` で更新時刻
   - Cell C `nvidia-smi` + `pgrep -af train_ppo_pfsp`
4. ~~Phase β.1 = build_ppo_lightweight.py 実装~~ **✅ 完了 (= 4734b87、 2026-05-12 10:10 JST)**
5. ~~build_ppo_v4_theta4_light/ 構築~~ **✅ 完了 (smoke PASS)**
6. **smoke 全 5 build 確認** = `bash tools/smoke_day4.sh` (= 既に light build 含む、 sanity 確認のみ)
7. **`.criteria/kaggle-orbit-wars-day4-submit-2026-05-13.yaml` rewrite** = slot 5 を light build に明記 (= day4_submit.sh は既 update、 criteria も整合 必要)
8. **W2 retry** (= 22:00 JST rate limit reset 済): forum bowwowforeach 投稿確認 + 公開 kernel 17+ size 再確認
9. **Phase α.2 first cut** = `tools/mcts_orbit_wars.py` skeleton + `submissions/build_mcts_v1/main.py` (= MCTS depth 3 + heuristic、 5/13 09:00 までに 1 ep 完走確認)
10. **Day 4 reset (= 5/13 09:00 JST) 後**: `bash tools/day4_submit.sh` で 5 slot 一括 submit (= 軽量化 PPO + MCTS v0 含む)
11. **5/13 09:30 JST**: Day 4 LB initial を `docs/research/2026-05-13-submission-analyses.md` に append (= 「随時やれ」 ルール)

---

## 8. 現状 commits (= ykaya-jp/orbit-wars main HEAD)

```
4734b87 feat(phase-beta-1): PPO lightweight build = 425MB → 64.5MB (= 84.8% 削減) ★
9a68875 docs(handoff): 2026-05-12 morning session pivot handoff
42b1147 feat(phase-alpha-1): bowwow reverse engineer 進捗 + MCTS design hints
4359328 docs(roadmap-pivot): Day 3 LB 反映 + GM-level victory research 統合
93457ac feat(p1-day4): day4_submit.sh + smoke + analyses doc skeleton
5075369 docs(claude): project-local CLAUDE.md with session start/end protocol
737d033 docs(handoff): comprehensive session handoff for next-context continuation
069511d feat(p2-done): θ.4 200k PFSP build + Day 4 slot 5 confirmed
```

### Phase β.1 完了 詳細 (= 4734b87、 2026-05-12 10:10 JST)

- `tools/build_ppo_lightweight.py`: sb3 zip → optimizer drop + FP16 cast
- `agents/proxy/ppo_v4_theta4_light.zip`: 86 MB (= 82.7% 削減 from 495 MB)
- `submissions/build_ppo_v4_theta4_light/`: smoke PASS (step 249, duration 1.4s)
- `submissions/ppo_v4_theta4_light.tar.gz`: **64.5 MB** (= 100 MB cap の 64.5%、 大幅 margin)
- `tools/day4_submit.sh` slot 5 + `tools/smoke_day4.sh` を light build に swap 済

---

## 9. Drive 状態 (= 私の OAuth token 可視のみ、 §10 cleanup deferred)

私 可視 (= 494.6 MB total): ppo_v3_theta3.zip 494 MB / orbit_wars_weights.tar.gz 0.4 MB / 3 notebook 0.1 MB
私 不可視 (= Colab notebook write、 推定 数 GB):
- `ppo_pfsp_pool_theta4/` 8 ckpt × ~430 MB = ~3.4 GB
- `ppo_pfsp_pool_theta5/` 走行中 (= 5 ckpt 想定、 ~24h で 100+ ckpt 蓄積、 pool_max=12 で evict)
- `ppo_v1_theta1.zip` / `ppo_v2_theta2.zip` (= 過去 experiment、 削除候補)

Cleanup は θ.5 完走後 (= 5/13 09:00 JST 以降) deferred (= Task #7)

---

## 10. Score 2000+ への 残 41 day path (= 新 roadmap、 honest 評価)

| Tier | LB target | 確率 | 必要条件 |
|---|---|---|---|
| Silver (= 1200+) | 70% | high | Phase β PPO 軽量化 submit success + ratio drift calibrate |
| Gold (= 1500+) | 40% | mid | + Phase α.2 MCTS v1 + bowwow data driven hybrid |
| Top 5 (= 1700+) | 20% | mid | + Phase δ MCTS + PPO leaf eval 統合 + meta-agent |
| **Top 1-3 (= 2000+)** | **8-12%** | **low** | + bowwow 真戦術 全再現 + 未公開 exploit 1-2 種 + 神 RNG |

前 session honest 5-10% → 本 session で 8-12% に微増 (= roadmap pivot で path が明確化、 ただし 41 day で hybrid 完成は時間圧迫)

---

## 11. 重要 reminder + lessons

- **submit 1 件で結論しない** (= 親 CLAUDE.md §1.2): H1 単一 submit で「fleet.angle defense 失敗」 確定は妥当、 でも H2/H4/H5 は 24h resample 待ち
- **single paradigm 禁止** (= §1.3): roadmap pivot 後 4 paradigm (= rule / 探索 / PPO leaf / IL bovard reverse) mix で対応
- **軽さ-driven 禁止** (= §11 「優勝本質性」): MCTS / forward search は 「軽い alternative では届かない」 数理本質、 W3 確認
- **Day 0 で CV 確定** (= §1.1): bovard 280万 row が事実上の host CV、 我家 self-play 強化必要
- **stuck 判定の rule 化** (= 本 session 教訓 §5): GPU util + ckpt 出力 + log file flush + 時刻計算 で 4 面確認、 stdout 沈黙のみで判断しない
- **W4 LB monitor 自動化 48h 着手**: top 10 team の submission timing 検知遅れは counter 戦略後手 = 1 day = 2.4% 時間損失

---

End of pivot handoff. **次 session 開始時 §7 「即 action 11 step」 を順に実行**。 cold start でも本 doc + roadmap pivot doc + bowwow-reverse doc の 3 つを read すれば full continuation 可能。
