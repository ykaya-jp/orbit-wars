# orbit-wars Roadmap Pivot — 2026-05-12 (= W3/W5/W1/W6 統合発見受けて)

> 既存: docs/strategy/2026-05-11-victory-roadmap.md (= 6 phase 全体) / score-2000-roadmap.md (= 3-Tier path) / rl-best-practices.md (= PPO 研究)
> 起源: 本 session 6 worker (= W1 過去 RL comp / W3 top-tier profile / W4 LLM / W5 数理 / W6 engine audit / W2 forum=rate limit 22:00 retry) 統合
> 出典: docs/research/2026-05-12-victory-research/{01,03,04,05,06}-*.md ★ + Day 3 LB analyses
> Day 3 LB 結果: 全 4 件 989 下回り、 H1 (= fleet.angle defense backport) 完全失敗

---

## 0. TL;DR

3 件の確定発見が **roadmap 大幅 pivot** を要求する:

1. **RL paradigm の LB 天井 = 1500-1650 帯** (= Isaiah Pressman = Lux S3 1st 作者が LB 5 / 1548 で停滞、 W3)
2. **bowwowforeach (LB 1 / 1823) = pure rule-base + 探索 (= chokudai/SA/beam)** (= W3、 AtCoder Heuristic rating 3216、 GitHub C++ 100% / deep learning commit ゼロ)
3. **Kaggle agent comp submission size limit = 100 MB** (= W1/W6、 Lux S3 1st writeup 「62MB shy of the 100MB submission file size limit」 一次資料)

→ **target 2000+ に届く path = rule-base + forward search (= MCTS / beam / SA) hybrid 必須**。 既存 PPO 投資 (= θ.4 完走、 θ.5 走行中) は **leaf evaluator として再利用 (= sunk cost 回収)**、 主 paradigm を rule + 探索 に shift。

---

## 1. 既存 roadmap の弱点

| 弱点 | 出典 | 影響 |
|---|---|---|
| PPO 一辺倒 (= Phase γ.1-γ.3 全て PPO training) | docs/strategy/2026-05-11-victory-roadmap.md | LB 1548 天井で gold 不可 |
| AlphaStar 流 league (= Phase δ) も PPO + exploiter で同 paradigm 内 | docs/strategy/2026-05-11-alphastar-league-design.md | 同上 |
| Tier 3 exploit (= end-game pile-up / Let-them-fight / 1-ship sniper) が rule-base ベースだが組織的でない | docs/research/2026-05-11-engine-audit.md | bowwow 流 long-term plan に欠ける |
| forward search (= MCTS / beam) の言及ほぼなし | 全 roadmap | top paradigm 完全 missing |

---

## 2. 新 Phase 構成 (= 5/12 09:35 JST 起票、 残 41 day)

### Phase α (= 5/12-5/19、 7 day、 **最優先**)
**rule-base + forward search hybrid 試作**

- α.1 **bowwow 行動 reverse engineer** (= 3 day):
  - bovard 280万 row (= existing) から bowwow / Isaiah / top 10 の per-step action 抽出
  - launch_size 分布、 timing pattern、 home defense reserve、 kill stack 形成 step 同定
  - 出力: `docs/research/2026-05-12-bowwow-reverse.md`
- α.2 **MCTS / beam search 試作** (= 4 day):
  - planet 行動空間 = (target_planet, angle_bin, ship_fraction) で 5-step lookahead
  - beam width 64-256、 evaluator = (a) 簡易 hand-crafted heuristic (b) PPO θ.4 policy net
  - 探索深さ vs 1 sec/step budget の trade-off 計測 (= W6 制約)
  - 出力: `submissions/build_mcts_v1/main.py`

### Phase β (= 5/12-5/14、 並行)
**PPO 軽量化 + Day 4 submit test**

- β.1 `tools/build_ppo_lightweight.py` 作成 (= state_dict 抽出 + FP16 = 425 MB → ~85 MB)
- β.2 `submissions/build_ppo_v4_theta4_light/` build + local smoke
- β.3 Day 4 quota 1 件で submit test = **100 MB 仮説 + RL paradigm の LB datapoint** 取得
- 期待 LB: 1100-1500 (= RL 天井に近い、 ただし 1548 超えは bowwow 流 hybrid なしには困難)

### Phase γ (= 5/14-5/20、 θ.5 完走後)
**PPO θ.5 best ckpt 選定 + W5 修正版 θ.6**

- γ.1 θ.5 ~500k step session 切れ → ckpt 12 個 + best ckpt 選定 (= local AB tournament)
- γ.2 W5 修正 を θ.6 で適用:
  - **PFSP exponent $p_{exp} = 2 \to 1.0$** (= 4P FFA で hardest opp 過剰 bias 緩和)
  - **target_kl = 0.02 early stopping 有効化** (= 我家 approx_kl 0.045 trust region 違反緩和)
  - **dense reward に logistic carrying capacity K=6 飽和 patch** (= over-expansion bias 抑制)
- γ.3 θ.6 1M step (= 24h Colab session 内に target 0.5M step)

### Phase δ (= 5/20-6/10、 hybrid 統合)
**Phase α MCTS / beam + Phase γ PPO best を leaf evaluator として統合**

- δ.1 MCTS の leaf eval を PPO policy + value で置換 (= AlphaZero / MuZero 流)
- δ.2 step time budget 内で search depth 自動調整 (= time control)
- δ.3 bowwow counter 戦術 (= kill stack 形成 timing 検知 + home defense intercept)

### Phase ε (= 6/10-6/16、 polish)
**ensemble + meta-agent**

- ε.1 3-paradigm meta-agent (= rule / IL / hybrid) ensemble、 game state ごとに best paradigm 選択
- ε.2 LB 1700-2000 帯への push

### Phase ζ (= 6/17-6/23、 final freeze)
**deadline 7 day 前 safe + risky 2 final submit freeze**

- safe = Phase δ hybrid CV stable + shake resistant
- risky = Phase ε meta-agent + bowwow counter

---

## 3. 既存 plan/criteria への影響

### 即削除 (= roadmap pivot で out-of-scope に)
- なし (= 全 existing artifact が leaf evaluator として再利用可能)

### 大幅 update
- `docs/strategy/2026-05-11-victory-roadmap.md`: Phase γ-δ を本 doc Phase α-ε に置換
- `docs/strategy/2026-05-11-score-2000-roadmap.md`: 5 必要条件のうち #1 「self-compiled task 数 75%+」 を「**rule + forward search が main paradigm**」 に置換
- `docs/strategy/2026-05-11-rl-best-practices.md`: W5 修正 2 件 (= pexp 1.0, target_kl 0.02) + dense reward patch を §1-2 に追記

### 新規起票
- `docs/research/2026-05-12-bowwow-reverse.md` (= Phase α.1 deliverable)
- `tools/mcts_orbit_wars.py` (= Phase α.2 試作)
- `submissions/build_mcts_v1/main.py` (= Phase α.2 試作)
- `tools/build_ppo_lightweight.py` (= Phase β.1)
- `.criteria/kaggle-orbit-wars-phase-alpha-mcts.yaml` (= Phase α 全体 plan)
- `.criteria/kaggle-orbit-wars-phase-beta-ppo-light.yaml` (= Phase β plan)

---

## 4. リスク / failure mode

| Risk | 兆候 | 対策 |
|---|---|---|
| MCTS / beam が 1 sec/step budget 内で収まらない | timeout 多発 + overage 枯渇 | search depth 動的調整、 explored node count cap、 leaf eval を軽量化 (= PPO policy のみ、 value 切捨) |
| bowwow 流 long-term plan を rule で再現できない | LB 1200 帯停滞 | (a) IL で bowwow replay を mimic、 (b) MCTS depth を 10-15 step まで深く |
| PPO leaf evaluator が rule 単独より弱い | hybrid 試作 LB < pure rule | PPO θ.6 完走後再評価、 value net のみ採用 |
| 残 41 day で Phase α-ε 全完走できない | Phase β/γ 並行で時間圧迫 | Phase ε 棄却、 δ で freeze (= LB 1700-1800 帯で gold zone) |
| LB pool shift 継続 (= 我家 base が更に -10% drift) | 各 Day で同 file submit で -50+ | Day 0 から確実な CV (= self-play vs top 10 公開 kernel) で LB 依存度下げる |

---

## 5. acceptance criteria (= 形名参同、 各 phase plan で別途 criteria.yaml 起票)

### α phase
- α.1 bowwow reverse: bovard 280万 row から bowwow / Isaiah / top 10 の per-step action 統計が `docs/research/2026-05-12-bowwow-reverse.md` で表化、 出典 file:line 明示
- α.2 MCTS 試作: `submissions/build_mcts_v1/main.py` が local 4P smoke で 1 ep 完走、 vs konbu17_topk1 で win rate ≥ 50%

### β phase
- β.1 build_ppo_lightweight.py: sb3 zip → state_dict.pt + FP16 cast 動作、 size 425 MB → ≤ 100 MB 達成
- β.2 build_ppo_v4_theta4_light: local 4P smoke 完走、 size < 100 MB
- β.3 Day 4 submit test: status COMPLETE (= 100 MB 仮説実証 or 反証)、 LB 値取得

### γ-ε phase
- 各 phase 開始時に `.criteria/<phase>-*.yaml` 別途起票

---

## 6. 進捗 KPI (= 残 41 day で track)

| Day | KPI |
|---|---|
| 5/13 | β.1-β.3 完了、 Day 4 submit 5 件 + RL light submit test |
| 5/15 | α.1 bowwow reverse 完了 |
| 5/19 | α.2 MCTS v1 完了、 vs konbu17 win rate ≥ 50% |
| 5/22 | γ.2 θ.6 修正版 trigger、 5/13 ~500k ckpt 採用 |
| 5/26 | δ.1 hybrid v1 試作 (= MCTS + PPO leaf eval) |
| 6/05 | δ.2 完成、 LB 1500+ 帯到達確認 |
| 6/15 | ε.1 meta-agent ensemble、 LB 1700+ 帯 |
| 6/16 | final 2 submit freeze (= safe + risky) |
| 6/23 | deadline、 LB target 1800-2000+ |

---

## 7. 関連 doc

- W1 出力: `docs/research/2026-05-12-victory-research/01-past-comp-rl-deployment.md` (= 軽量化技法 + Lux S3 1st pattern)
- W3 出力: `docs/research/2026-05-12-victory-research/03-top-tier-profile-research.md` (= bowwowforeach 流確証 + RL 天井)
- W4 出力: `docs/research/2026-05-12-victory-research/04-llm-augmentation.md` (= 多刀流 + LB monitor 自動化)
- W5 出力: `docs/research/2026-05-12-victory-research/05-mathematical-foundations.md` (= PPO θ.5 修正 + dense reward patch)
- W6 出力: (= 直接 main return、 file 不作成、 size limit 100 MB 確証)
- Day 3 LB analyses: `docs/research/2026-05-12-submission-analyses.md` (= 09:30 反映済、 H1 完全失敗)
- W2 (forum): 5/12 22:00 JST rate limit reset 後 retry 予定

---

## 8. 主道原則整合確認 (= ~/.claude/CLAUDE.md / ~/projects/kaggle/CLAUDE.md)

- ✅ **1.3 single paradigm 不可** → Phase α-ε で 4+ paradigm mix (= rule / forward search / RL / IL / meta-ensemble)
- ✅ **1.2 trust your CV** → Phase α.1 で bovard data から CV proxy 確立
- ✅ **1.5 形名参同** → 各 Phase で `.criteria/<phase>-*.yaml` 起票後実装
- ✅ **11 「優勝本質性」 criterion** → MCTS / forward search は 「軽い alternative では届かない」 (= W3 確認、 RL 天井)、 数理本質で必須
- ✅ **8.1 #9 「随時やれ」** → Day 3 LB を analyses doc に 09:32 期限内 append 済
