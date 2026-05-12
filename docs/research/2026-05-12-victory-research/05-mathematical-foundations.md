# orbit-wars 数理本質研究 (= 2026-05-12)

> orbit-wars 優勝 path 補強研究 W5 — game theory / RL theory 観点
> 担当 topic: 4P FFA equilibrium + self-play theory + PPO math + Expansion 数理 + reward shaping + PFSP weighting
> 関連 plan: `docs/strategy/2026-05-11-victory-roadmap.md`, `docs/strategy/2026-05-11-score-2000-roadmap.md`, `docs/strategy/2026-05-11-rl-best-practices.md`, `docs/strategy/2026-05-11-alphastar-league-design.md`
> 目的: 既存 roadmap の各 hyperparameter / reward / curriculum 設定を **理論的 backbone で再武装** し、 「経験的に決まっていた」 値を 「数理的根拠を持つ値」 に upgrade する

---

## 0. 本研究の position

既存 roadmap (`docs/strategy/2026-05-11-rl-best-practices.md:11-26`) は **AlphaStar / OpenAI Five の架構を踏襲** している。 ただし以下が **理論的根拠なく default 値** または **paper の最小引用にとどまる**:

1. PFSP の sharpness exponent `a = 2` 固定 (`tools/train_ppo_pfsp.py:64`) — AlphaStar Nature 2019 由来だが 4P FFA の理論的最適値か?
2. self-play / external opponent 比 `0.6 / 0.2 / 0.2` (`docs/strategy/2026-05-11-rl-best-practices.md:84-87`) — AlphaStar 流だが 4P で同じ比は最適か?
3. dense reward 係数 `+0.001 × Δships, +0.01 × Δplanets` (`docs/strategy/phase_theta_ppo_design.md:34-36`) — Lux S3 流だが orbit-wars expansion 動力学に合わせて校正してない
4. discount `γ = 0.997` (= 500 step 半減 0.22, `docs/strategy/phase_theta_ppo_design.md:38`) — episode length 500 と整合だが credit assignment 観点での optimality 未確認

本研究は 6 topic で **数理整理 → 既存 plan 整合 → 具体修正提案** を行う。

---

## 1. 4P FFA equilibrium 概念

### 1.1 定義

- **Nash equilibrium (NE)**: $n$-player game $G$ の strategy profile $\sigma^* = (\sigma_1^*, ..., \sigma_n^*)$ が **NE** であるとは、 全 player $i$ について $u_i(\sigma_i^*, \sigma_{-i}^*) \ge u_i(\sigma_i, \sigma_{-i}^*) \ \forall \sigma_i$ が成立すること。 単独逸脱で誰も利得を上げられない state (出典: Nash 1950, https://doi.org/10.1073/pnas.36.1.48)
- **Coarse Correlated Equilibrium (CCE)**: より弱い概念。 全 player が history-conditioned randomization に commit したとき、 単独逸脱で利得改善できない state。 **no-regret learning の自然な収束点** で、 RL の self-play は CCE に収束する傾向が知られる (出典: Hannan 1957、 modern review Foster & Vohra 1997)
- **Empirical NE** (EGTA = Empirical Game-Theoretic Analysis): 大規模 policy population から meta-game payoff matrix を構築し、 そこで NE を解く実用化 (出典: Lanctot et al. 2017 PSRO, https://arxiv.org/abs/1711.00832; Walsh et al. 2003)

### 1.2 公式

4P FFA で `1st = +1, others = -1` (= orbit-wars 仕様、 `docs/research/2026-05-11-engine-audit.md:14-16` で確認済) の場合:

$$\sum_{i=1}^{4} u_i(\sigma) = 1 + 3 \cdot (-1) = -2 \quad \forall \sigma$$

**zero-sum でない (= constant-sum)**。 ただし constant-sum game は scalar shift で zero-sum と同型なので **2P zero-sum の理論を一部継承** できる。 重要な違い:

- **2P zero-sum**: NE は **minimax 値で一意** (= value function は player 共通)、 self-play は NE に収束
- **4P FFA**: 一般に NE は **複数存在**、 single self-play は **特定の NE に偏向 (= equilibrium selection 問題)**、 さらに **coalition** を導入すると非協力 NE と異なる解になる (= Shapley value 系の transferable utility 理論)

empirical NE の orbit-wars 実用化: PFSP pool 内全 checkpoint の pairwise win-rate matrix から **Nash averaging** (Balduzzi et al. 2018, https://arxiv.org/abs/1806.02643) を計算、 「pool 内で robust に強い」 checkpoint を選ぶ。 これは現状の rl-best-practices.md §2.5 「pool-max 8 → 12」 と 整合する (= pool が大きいほど Nash averaging の robust 性が上がる)。

### 1.3 orbit-wars 適用

**3-player coalition dynamics (= 4P で 1 vs 3 状況)** の数理:

orbit-wars は **transferable utility がない (= cargo を player 間で送れない)** が、 **暗黙協調** は engine 仕様上発生する:

1. **食い合わせ exploit** (= `docs/research/2026-05-11-engine-audit.md:48-58` #1 Let-them-fight): 他 2 player が同 planet を攻撃すると combat resolve で `top - second` が survivor、 我家は **第三者として観戦して resources 節約**
2. **King-maker 不可能**: `engine-audit.md:14-16` の通り 1st 以外全員 -1 なので 「最下位が首位を倒す」 行動は **自分の reward を改善しない**。 ただし long-run に複数 episode を見ると、 「首位を倒すと自分の Elo が上がる」 ので **multi-episode 視点では合理性あり** (= Kaggle LB は累積 Elo で評価)

→ engine-audit.md と整合: **King-maker は LB 評価では合理性あり**、 ただし single episode で reward に出ない。 これは **dense reward を rank-aware (= 2nd > 3rd > 4th)** に設計することで RL agent が学べる (= `phase_theta_ppo_design.md:32` の `{1: +1.0, 2: +0.3, 3: -0.3, 4: -1.0}` がこの直感を捉えている)。

### 1.4 既存 plan 整合

- ✅ `phase_theta_ppo_design.md:32` の rank-aware terminal reward は coalition 視点で正当化される (= king-maker は 2nd 確保で +0.3 を取りに行く合理性)
- ⚠️ `2026-05-11-rl-best-practices.md:20` 「terminal-only sparse」 から 「dense reward」 への shift は **rank-aware を維持しつつ shaping bonus 追加** が必要。 単純な ships delta だけでは coalition 動力学を学べない
- ❓ `2026-05-11-alphastar-league-design.md:18-24` の league 構成 (Main 50% / Main exp 25% / League exp 25%) は 2P 設定の AlphaStar 流。 4P FFA で 同じ比が NE selection に最適かは **理論的に未決定** (= 後述 §6 で再検討)

### 1.5 未解決

- **4P FFA の NE 解は解析的に書けない** (= 500 step horizon × 連続 angle action × 6-12 planet で state space 爆発)。 EGTA / Nash averaging は heuristic で、 **真の NE 性は保証されない**
- **shake-up risk** (= public/private LB) と NE の関係: もし host が 異なる seed を private に使うなら、 我家 agent が 特定 NE に過剰適合する risk あり。 これは PFSP pool diversity を増やすことで mitigate (= §6 で再検討)

---

## 2. self-play 理論

### 2.1 定義

- **Fictitious Play (FP)**: 各 player は相手の **過去 average strategy** に対する best response を play (出典: Brown 1951, https://www.rand.org/content/dam/rand/pubs/papers/2008/P78.pdf)。 2P zero-sum で NE 収束保証あり、 n-player では一般に保証なし
- **Neural Fictitious Self-Play (NFSP)**: FP の deep RL 拡張。 各 player は (a) 過去全 episode の **average policy network** $\pi_{avg}$ と (b) 現在の **best response Q-network** $\beta$ を学習、 mix policy $\sigma = \eta \cdot \beta + (1-\eta) \cdot \pi_{avg}$ で行動 (出典: Heinrich & Silver 2016, https://arxiv.org/abs/1603.01121)。 典型 $\eta = 0.1$
- **Prioritized Fictitious Self-Play (PFSP)**: FP で 「相手をどう sample するか」 を **win rate priority** で重み付け (出典: AlphaStar Vinyals et al. Nature 2019, https://www.nature.com/articles/s41586-019-1724-z)
- **Population-Based Training (PBT)**: 並列 agent population を **periodic exploit + explore** (= 弱い agent は強い agent の hyperparameter を copy + perturb) で進化 (出典: Jaderberg et al. 2017, https://arxiv.org/abs/1711.09846; AlphaStar / OpenAI Five で採用)

### 2.2 公式

**PFSP の重み付け sampling** (= AlphaStar Nature 2019 supplementary、 我家 `tools/train_ppo_pfsp.py:64` で実装済):

$$\Pr(\text{opp} = c \mid \text{agent} = a) \propto f_{\text{hard}}(\Pr[a \text{ beats } c])$$

ここで $f_{\text{hard}}(p) = (1-p)^{p_{\exp}}$、 **$p_{\exp} = 2$** が AlphaStar main agent の default 値 (= 我家 `train_ppo_pfsp.py:67` で `(1.0 - win_rate) ** 2` として実装)。

variance-prioritized variant (= league exploiter 用):

$$f_{\text{var}}(p) = p(1-p)$$

これは 「勝率 50% 付近の opponent (= 互角)」 を最も多く sample する曲線。 hardness exponent $p_{\exp} \to \infty$ で 「最も負けている opponent のみ」 sample に収束、 $p_{\exp} = 0$ で uniform sampling に縮退。

**NFSP の anticipatory parameter** (= Heinrich & Silver 2016):

$$\sigma_i^{\text{behavior}} = \eta \cdot \beta_i + (1-\eta) \cdot \pi_{avg, i}, \quad \eta \approx 0.1$$

$\eta$ は 「現在の best response にどれだけ歩み寄るか」 の anticipatory 係数。 過大 (= $\eta > 0.5$) は average policy 更新が follow できず、 過小 (= $\eta < 0.05$) は best response が活かされない。

### 2.3 orbit-wars 適用

**我家現 setup の数値** (`tools/train_ppo_pfsp.py`):

| param | 我家 | AlphaStar paper | 4P FFA で再評価 |
|---|---|---|---|
| $p_{\exp}$ (PFSP exponent) | 2 (line 67) | 2 (main agent) | **要再算出 (= §6 で proposal)** |
| UNIFORM_MIX | あり (line 108) | あり | OK |
| self_play_prob | 0.6 (line 247) | ≈ 0.5 (main vs all) | **0.6 → 0.7 推奨** (= 4P で diversity 自然増) |
| external_prob | 0.2 (line 272) | ≈ 0.25 (exploiter mix) | OK |
| pool max | 8 / 12 | 100+ | 12 で十分 (= AlphaStar 100 は 14 day × 16 TPU 級の計算前提) |

**4P FFA で diversity 自然増の数理**: 1 episode で 4 player 必要 → 1 opponent slot あたり 3 player 必要 → self-play + external で 3 体埋める必要、 これは 2P 設定より **自然と 3 倍の opponent diversity を強制**。 つまり 2P で `self_play_prob = 0.5` は 4P では実効的に `self_play_prob = 0.5 / 3 ≈ 0.17` 相当の effective self-play 比率になる。 よって 4P で `self_play_prob = 0.6 → 0.7` は **「2P の 0.7 / 3 ≈ 0.23 程度の effective self-play」** で diversity が確保され、 strict self-history training の利点 (= curriculum 効率) を 取りに行く修正は数理的に妥当。

**NFSP は 4P FFA で適用しない方針が合理的**: convergence 保証が 2P zero-sum 限定 (= Heinrich & Silver 2016 Theorem 7)、 4P FFA は constant-sum で zero-sum と同型なので **理論的には 2P で成立**するが、 4 player simultaneous 学習で `best response Q-network` が安定しない実用問題が知られる (= AlphaStar が NFSP ではなく PFSP を選んだ理由の 1 つ)。 → 我家も PFSP を継続。

### 2.4 既存 plan 整合

- ✅ `2026-05-11-rl-best-practices.md:12` で PFSP weight `(1-WR)²` が AlphaStar-grade と明言
- ⚠️ `2026-05-11-alphastar-league-design.md:18-24` の Main/Main exp/League exp 比 50/25/25 は **2P 設定で最適化された値**。 4P FFA で 同じ比は **未検証**。 §6 で再評価
- ⚠️ `tools/train_ppo_pfsp.py:67` の `p_exp = 2` 固定は AlphaStar default。 **4P FFA で curriculum collapse risk (= 全 opponent 互角に近づいて weight 平均化) があり、 後述 §6 で動的調整提案**

### 2.5 未解決

- **PBT の orbit-wars 適用判断**: AlphaStar / OpenAI Five は 数十-数百 agent 並列 PBT。 我家 Colab Pro+ A100 1 枚では 並列 budget なし、 **PBT 風 hyperparameter exploration を sequential で実施 (= AlphaStar league の `Main exp` 役割を hyperparameter perturbation に流用)** という代替案を §3 plan で検討すべき
- **NFSP の 4P 拡張の理論研究**: Lanctot et al. PSRO (2017) は n-player 拡張だが計算重い、 我家 budget では難しい

---

## 3. PPO の数学的 detail

### 3.1 定義

PPO (= Proximal Policy Optimization, Schulman et al. 2017, https://arxiv.org/abs/1707.06347) は **trust region 法を first-order 近似** で実装。 policy update 幅を **clip 比 $\epsilon \approx 0.2$** で制限し、 destabilization を防ぐ。

### 3.2 公式

**clipped surrogate objective**:

$$L^{\text{CLIP}}(\theta) = \mathbb{E}_t\left[\min\left(r_t(\theta) \hat{A}_t,\ \mathrm{clip}(r_t(\theta), 1-\epsilon, 1+\epsilon) \hat{A}_t\right)\right]$$

ここで $r_t(\theta) = \pi_\theta(a_t|s_t) / \pi_{\theta_{\text{old}}}(a_t|s_t)$ (= policy ratio)、 $\hat{A}_t$ は GAE advantage estimate (出典: ICLR Blog 2022 PPO Implementation Details, https://iclr-blog-track.github.io/2022/03/25/ppo-implementation-details/)

**combined loss** (= shared policy/value network):

$$L^{\text{CLIP+VF+S}}(\theta) = L^{\text{CLIP}}(\theta) - c_1 (V_\theta(s_t) - V^{\text{target}})^2 + c_2 H(\pi_\theta(\cdot|s_t))$$

typical: $c_1 = 0.5$ (= value function coef), $c_2 = 0.01$ (= entropy bonus、 後述 anneal 戦略あり) (出典: Lilian Weng PPO notes, https://lilianweng.github.io/posts/2018-04-08-policy-gradient/)

**GAE advantage** (= Generalized Advantage Estimation, Schulman et al. 2015, https://arxiv.org/abs/1506.02438):

$$\hat{A}_t^{\text{GAE}(\gamma, \lambda)} = \sum_{l=0}^{\infty} (\gamma \lambda)^l \delta_{t+l}, \quad \delta_t = r_t + \gamma V(s_{t+1}) - V(s_t)$$

$\lambda \to 1$ で Monte Carlo (= 高 variance, 低 bias)、 $\lambda \to 0$ で TD(0) (= 低 variance, 高 bias)。 standard $\lambda = 0.95$。

**explained_variance** (= value function quality):

$$\mathrm{EV} = 1 - \frac{\mathrm{Var}(R - V)}{\mathrm{Var}(R)}$$

ここで $R$ = return、 $V$ = value prediction。 $\mathrm{EV} = 1$ で完全 fit、 $\mathrm{EV} < 0$ で 「value network が return mean predict より悪い」 (= bug / under-training) (出典: ICLR Blog 2022)

**approx_kl** (= PPO 早期停止 metric):

$$\widehat{\mathrm{KL}}(\pi_{\text{old}} \| \pi_\theta) \approx \frac{1}{N} \sum_{t} \big(-\log r_t(\theta)\big)$$

健全 training で典型 `< 0.02`、 `target_kl = 0.02` 超えると update 中断 (= trust region 違反防止)。 我家観測 `0.045` (`docs/strategy/2026-05-11-victory-roadmap.md` 周辺 logs) は **やや大きい (= step size 過大)** で、 §3.3 で調整推奨。

### 3.3 orbit-wars 適用

**我家観測 metric の解釈**:

| metric | 我家観測 | 理論健全範囲 | 解釈 |
|---|---|---|---|
| `explained_variance` | 0.95 (`CLAUDE.md` "Project context") | > 0.5 healthy, > 0.9 excellent | ✅ **value network は十分 fit**、 これ以上の network 拡大は ROI 低 |
| `approx_kl` | 0.045 | < 0.02 ideal, < 0.05 acceptable | ⚠️ **step size 過大の兆候**、 LR を $3 \times 10^{-4} \to 2 \times 10^{-4}$ に下げる根拠 (= rl-best-practices.md §2.1 と一致) |
| `clip_fraction` | (= 未測定) | 0.1-0.3 healthy | 測定推奨。 > 0.3 で step size 過大、 < 0.05 で過小 |

**LR cosine schedule の理論根拠** (= rl-best-practices.md §2.1):

cosine annealing は **non-convex objective の局所最適間移動を許容しつつ最終 fine-tune 段階を低 LR で安定化** する一般技法 (出典: Loshchilov & Hutter 2017 SGDR, https://arxiv.org/abs/1608.03983)。 PPO の場合 approx_kl が large step で trust region 違反を起こすので、 **後半 cosine decay で `approx_kl < 0.02` に追い込む** ことが目的。 我家 0.045 → schedule 導入で 0.02-0.03 に下がる見込み。

**ent_coef anneal の理論根拠**:

entropy bonus $c_2 H(\pi)$ は **early exploration を強制**。 ただし後半まで残ると **policy が deterministic に固まらず performance ceiling を下げる** (= OpenAI Five 報告)。 schedule:

$$c_2(t) = c_{2,0} \cdot (1 - 0.9 \cdot t / T) + 0.005$$

これは `rl-best-practices.md:50-53` の実装。 $c_{2,0} = 0.05$ から $0.005$ への線形減衰は OpenAI Five で確立された heuristic で、 理論的には **softmax policy の temperature 制御** に対応 (= temperature $\tau \propto 1/c_2$ で entropy が大きいほど uniform に近い random policy)。

### 3.4 既存 plan 整合

- ✅ `2026-05-11-rl-best-practices.md:14` LR `2e-4 warmup + cosine` は理論的に approx_kl 0.045 → < 0.02 改善の根拠あり
- ✅ `2026-05-11-rl-best-practices.md:19` ent_coef `0.05 → 0.005 anneal` は OpenAI Five 由来で理論的妥当
- ⚠️ `2026-05-11-rl-best-practices.md:17` n_epochs `4 → 8` の根拠: PPO sample reuse 増は **approx_kl が制約を満たす限り** において gradient 効率を上げる。 ただし n_epochs 過大は approx_kl 暴騰の risk (= target_kl で early stop callback 必須)。 **n_epochs 8 採用時は target_kl = 0.02 early stop を明示実装すべき** (= 既存 sb3 PPO は default `target_kl = None` で停止しない)

### 3.5 未解決

- **clip_fraction の orbit-wars 健全値**: 経験的 0.1-0.3 が healthy だが、 large action space (= per-planet 81 class × 12 planet) では未検証。 Day 5 1M step run で測定し criteria.yaml に記録すべき
- **`c_1` (value function coef) の tuning**: 我家 default 0.5 が orbit-wars で最適か? explained_variance 0.95 と既に飽和なので **`c_1` を 0.5 → 0.25 に下げて policy loss 比重増** が探索余地

---

## 4. Expansion game 数理 (= orbit-wars 特化)

### 4.1 定義

orbit-wars は **resource-bound expansion game**: 各 player は `planet ownership` (= production source) と `ship count` (= attack/defense unit) を 同時に成長させ、 episode terminal (= step 498) で `score = sum(ships)` max を取った player が 1st。

`docs/research/2026-05-11-engine-audit.md:19-29` の speed scaling:

$$v(s) = 1.0 + (v_{\max} - 1.0) \cdot \left(\frac{\log s}{\log 1000}\right)^{1.5}$$

→ **大 fleet は速度優位**、 これが late-game 集中の数理根拠。

### 4.2 公式

orbit-wars expansion を **修正 Lotka-Volterra 風 ODE** で近似:

$$\frac{dN}{dt} = \alpha \cdot N \cdot \left(1 - \frac{N}{K}\right)$$

$$\frac{dS}{dt} = \beta \cdot N - \gamma \cdot S_{\text{attack}}$$

ここで:
- $N(t)$ = step $t$ 時点の自分の planet 数
- $S(t)$ = step $t$ 時点の自分の ship 数
- $K$ = 4P FFA での 1 player あたり carrying capacity (= 全 planet 数 ≈ 24 / 4 = 6 が naive 上限、 実測上は **bovard top tier で N=5 が安定** = `docs/strategy/2026-05-11-score-2000-roadmap.md:18-22`)
- $\alpha$ = expansion rate (= per-step で 「neutral planet を capture する確率 × 残 capacity」)
- $\beta$ = production rate per planet (= engine 仕様で planet あたり生産速度、 平均 ≈ 1 ship/step)
- $\gamma$ = attack loss rate (= 平均的に attack で失う ship 数)

**carrying capacity を超えると expansion が止まる** (= logistic 項 $1 - N/K$)、 ship 蓄積は planet 数に **線形 proportional**。

### 4.3 orbit-wars 適用

`docs/strategy/2026-05-11-score-2000-roadmap.md:18-22` の bovard 280 万 row 実測 (Top tier vs other):

| step | Top tier (N, S) | other (N, S) | 数理的解釈 |
|---|---|---|---|
| 50 | (5.0, 273) | (5.0, 242) | $N$ 同等、 $S$ +13% = $\beta$ ≈ 5 ship/planet/10step 健全 |
| 100 | (6.0, 450) | (6.0, 349) | $N$ 同等 (= **carrying capacity 6 に届いた**)、 $S$ +29% = top tier の attack 効率 ↑ |
| 200 | (5.0, 558) | (3.0, 251) | **gap 急拡大**: top tier $N$ 維持 vs other は **planet を失う (= defense 失敗)** |
| 300 | (4.5, 966) | (3.0, 503) | top tier $S$ ↑↑ (= 大 fleet 蓄積開始) |
| 400 | (4.0, 1828) | (3.0, 946) | top tier $S$ doubles other |

**真因の数理 reframe** (= score-2000-roadmap.md:24-30 と整合):

1. Early game (step 0-100): 両者とも logistic で $N \to K = 5\text{-}6$ に到達、 **expansion 速度 $\alpha$ は同等**
2. Mid game (step 100-200): top tier は $N$ 維持 (= **defense $\gamma$ 低**)、 other は $N$ 減少 (= defense 失敗)
3. Late game (step 200+): top tier の $S$ 蓄積が $\beta \cdot N$ で 持続、 other は $N$ 喪失で $\beta$ 落ちて指数差拡大

**ODE 解析**: logistic 解 $N(t) = K / (1 + (K/N_0 - 1) e^{-\alpha t})$ で $N_0 = 1$, $K = 5$ なら $t_{50\%} = \log(K-1)/\alpha$ で $N$ が中点。 bovard 観測 step 50 で $N = 5$ → $t_{50\%} \approx 25$ → $\alpha \approx \log 4 / 25 \approx 0.055$ per step。 **これは expansion mission の rule-base 上限値**: 1 step あたり planet capture 確率 5.5% が top tier 級。

### 4.4 既存 plan 整合

- ✅ `2026-05-11-score-2000-roadmap.md:18-30` の真因 reframe は ODE model で説明可能 (= mid-game defense の $\gamma$ が gap 主要因)
- ✅ `docs/research/2026-05-11-engine-audit.md:69-82` の End-game ship pile-up exploit (#4) は ODE 末端 $t = 498$ で $S$ 全集中する戦術、 ODE 視点で 「終端時刻に in-flight ships max にする」 と等価
- ⚠️ `phase_theta_ppo_design.md:35-36` の dense reward `+0.01 × Δplanets` は **logistic 飽和を加味してない**。 $N = 5$ 到達後の `+Δplanets` reward は **取り過ぎ to defense ratio が悪化** する。 **修正案**: `clip(Δplanets, 0, K - N) × 0.01` で carrying capacity 超過分を rewards 出さない
- ⚠️ `2026-05-11-rl-best-practices.md:63-73` の `bovard_alignment_bonus` は target fleet size を線形補間 (= step 0=21, step 500=303)。 ただし bovard 実測は **指数的 (= step 200 で 558, step 400 で 1828)** で線形 mismatch。 **指数 fit に修正**: `target_S(t) = 21 × exp(t / 110)`

### 4.5 未解決

- $\alpha$ optimal の RL 学習が rule-base 上限 0.055 を超えられるか: PPO agent は theory 上 $\alpha$ を超える可能性 (= rule-base は greedy heuristic、 RL は look-ahead で planet 選択最適化)、 実証は Day 8-14 PPO θ.4 run の training curve で確認
- ODE 近似の精度: 実 episode は離散 step + adversarial で stochastic、 ODE deterministic は近似。 Monte Carlo simulation で fit 検証 (= 1 day 投資価値あり、 §「2 我家 PPO θ.5 への 直接 適用」 §5 参照)

---

## 5. Multi-agent reward shaping

### 5.1 定義

**reward shaping** (= Ng et al. 1999, https://www.aaai.org/Papers/ICML/1999/ICML99-064.pdf): RL の sparse reward を dense reward に変換する技法。 **potential-based shaping** $F(s, s') = \gamma \phi(s') - \phi(s)$ は **optimal policy 不変** が証明済 (= Ng theorem)。 一般 dense reward は optimal policy bias を持つ risk あり。

**credit assignment problem in 4P FFA**: 4 player が 同時に action を取る setting で、 player $i$ の reward は他 3 player の action にも依存 (= **non-stationary environment from $i$ の view**)。 標準 RL の Markov property は 厳密には成立せず、 多 player MDP / Stochastic Game の枠組み (= Shapley 1953 拡張) が必要。

### 5.2 公式

**potential-based shaping (= optimal policy 保存)**:

$$R'(s, a, s') = R(s, a, s') + \gamma \phi(s') - \phi(s)$$

ここで $\phi: S \to \mathbb{R}$ は state potential。 **任意の $\phi$ で optimal policy 保存**。 orbit-wars で $\phi(s) = w_1 \cdot N(s) + w_2 \cdot S(s)$ (= planet 数 + ship 数 の重み付き和) は potential として正当化される。

**rank-aware dense reward** (= `phase_theta_ppo_design.md:32`):

$$R_{\text{rank}}(s) = \{1: +1.0, 2: +0.3, 3: -0.3, 4: -1.0\}_{r=\text{rank}_i(s)}$$

この設定は **constant-sum 性を破る** (= $\sum_i R_{\text{rank}} = +1.0 + 0.3 - 0.3 - 1.0 = 0$、 偶然 zero-sum)。 これは coalition 観点で 「king-maker は 2nd 取りに行く」 を可能にする (= §1.3 参照)。

**bovard IRL proxy の理論基礎** (= rl-best-practices.md §2.3, line 56-73): inverse RL (Ng & Russell 2000) の simplification。 真の IRL は expert trajectory から reward 関数を学習するが、 我家は **Top tier action 分布との KL divergence を proxy reward** にする粗 approx。

$$R_{\text{align}}(a_t, s_t) = -\lambda \cdot \mathrm{KL}\big(\pi_{\text{agent}}(\cdot|s_t) \,\|\, \pi_{\text{top tier}}(\cdot|s_t)\big)$$

`bovard_alignment_bonus` (rl-best-practices.md:64-73) は KL の **狭い surrogate** (= 単一 action の ships 数 alignment のみ)、 真の KL ではない。

### 5.3 orbit-wars 適用

**現状 reward shaping の評価** (= `phase_theta_ppo_design.md:30-36`):

| component | 形式 | potential-based? | optimal policy bias risk |
|---|---|---|---|
| terminal `{1: +1.0, ..., 4: -1.0}` | sparse rank | N/A (= terminal) | なし |
| `+0.001 × Δships` | dense | ✅ (= $\phi = S$ の telescope) | 低 |
| `+0.01 × Δplanets` | dense | ✅ (= $\phi = N$) ただし $N$ logistic で **飽和後 0** にすべき | あり (= over-expansion) |
| bovard align bonus | dense | ❌ (= action-conditional, IRL proxy) | あり (= over-mimicry) |

**重大問題**: `+0.01 × Δplanets` が **carrying capacity $K$ 超過分まで rewards 出している** (= §4.4 で指摘)。 修正: $\phi(s) = \min(N(s), K)$ で potential 飽和、 telescope で `Δplanets` が $N \le K$ の時のみ +reward。

**bovard align bonus の risk**: top tier の **bias を継承** する。 例: bovard top tier が 「step 200 で defense 集中」 を必ず取るなら、 agent は novel exploit (= EndgamePileupMission 等) を学ぶ機会を失う。 → **align bonus の coefficient $\lambda$ を training 後半 anneal** すべき (= early は IL-like bootstrap、 後半は free exploration)。

### 5.4 既存 plan 整合

- ✅ `phase_theta_ppo_design.md:32` rank-aware terminal は constant-sum 保存 + coalition 動力学を捉える正しい設計
- ⚠️ `phase_theta_ppo_design.md:36` `+0.01 × Δplanets` は logistic 飽和を加味してない → **修正案**: `+0.01 × max(0, min(Δplanets, K - N))` (= K=6 設定で carrying capacity 超過抑制)
- ⚠️ `2026-05-11-rl-best-practices.md:64-73` bovard align bonus は線形 target を指数 fit に変更 + late game anneal 必須

### 5.5 未解決

- **rank-aware reward の最適 weight**: `{+1.0, +0.3, -0.3, -1.0}` は heuristic。 Shapley value 等の cooperative game 理論で導出する手はあるが、 4P FFA の Shapley value は player 順列 24 通りで計算重い (= 後回し)
- **真の IRL を導入する価値**: bovard 280 万 row + max-entropy IRL (Ziebart 2008) で reward 関数を学習するのは Day 15+ の Tier 3 で検討余地。 align bonus を超える ROI 期待

---

## 6. PFSP weighting formula

### 6.1 定義

PFSP weight (再掲, §2.2):

$$w(c | a) = \frac{f(\Pr[a \text{ beats } c])}{\sum_{c'} f(\Pr[a \text{ beats } c'])}$$

- $f_{\text{hard}}(p) = (1-p)^{p_{\exp}}$, **$p_{\exp} = 2$** (= AlphaStar main agent default)
- $f_{\text{var}}(p) = p(1-p)$ (= league exploiter default)
- $f_{\text{uniform}}(p) = 1$ (= forgetting prevention)

実用上は UNIFORM_MIX (= 我家 `train_ppo_pfsp.py:108` で実装) で 「$\alpha$ rate で uniform mix」: $w_{\text{eff}} = (1 - \alpha) w_{\text{PFSP}} + \alpha \cdot 1/N$, 典型 $\alpha = 0.25$。

### 6.2 公式

**最適 $p_{\exp}$ の trade-off**:

$$\mathrm{Loss}(p_{\exp}) = \mathrm{Forgetting}(p_{\exp}) + \mathrm{Curriculum\_Stall}(p_{\exp})$$

- **Forgetting**: 強い opponent (= $p > 0.5$) を avoid しすぎると、 過去の弱 policy を打てなくなる (= catastrophic forgetting)
- **Curriculum Stall**: 弱い opponent (= $p < 0.5$) ばかり sample すると、 強い opponent への学習が進まない

$p_{\exp} \to 0$: uniform sampling, forgetting 防止だが curriculum 効果薄
$p_{\exp} \to \infty$: 全 weight が hardest opponent 1 体に集中、 curriculum 急、 forgetting 増

**$p_{\exp} = 2$ の数理的意味**: $f(p) = (1-p)^2 = 1 - 2p + p^2$ で $p = 0.5$ で $f = 0.25$、 $p = 0.9$ で $f = 0.01$、 $p = 0.1$ で $f = 0.81$。 つまり **「自分が 90% 勝ってる opponent への重み 0.81 で 9% しか勝ってない opponent への重み 0.01」** → **負けてる opponent を 81 倍多く sample**。 AlphaStar 設定としては妥当だが、 4P FFA で「3 体 opponent 同時 sample」 では effective weight が $w^3$ で乗算的に効くので、 **$p_{\exp} = 2$ は 4P で実効的に過激** な可能性。

**4P 用に再計算**: 1 episode で 3 opponent を独立 sample (= `train_ppo_pfsp.py:262-272` の現実装) すると、 episode あたり opponent set $\{c_1, c_2, c_3\}$ の sampling 確率は $\Pr[c_1] \cdot \Pr[c_2] \cdot \Pr[c_3]$ で **product weight**。 最 hardest opponent への bias が乗算的に効くので、 **2P で $p_{\exp} = 2$ は 4P で $p_{\exp} = 2/3 \approx 0.67$ 相当の effective sharpness** と近似できる (= 3 個独立 sample で 1 個分の sharpness に補正)。

→ **4P FFA での $p_{\exp}$ 推奨値**: **$p_{\exp} = 1.0$** (= AlphaStar の 2 から半減)。 これで 「負けてる opponent への bias は維持しつつ、 3 個 sample の乗算性で過激にならない」。

### 6.3 orbit-wars 適用

**修正案**: `tools/train_ppo_pfsp.py:67` の

```python
return max(0.0, (1.0 - win_rate)) ** 2
```

を

```python
P_EXP = 1.0  # 4P FFA で 2P の 2 から半減 (= 3 個独立 sample の乗算性補正)
return max(0.0, (1.0 - win_rate)) ** P_EXP
```

に変更。 加えて **UNIFORM_MIX** (= line 108 の uniform 比) を現 default から **0.25** に明示。

**変化の expected effect**:
- pool に win_rate 分布 `[0.1, 0.3, 0.5, 0.7, 0.9]` の 5 checkpoint がある場合、 各 weight:
  - $p_{\exp} = 2$: `[0.81, 0.49, 0.25, 0.09, 0.01]` → normalize `[0.49, 0.30, 0.15, 0.05, 0.01]`
  - $p_{\exp} = 1$: `[0.90, 0.70, 0.50, 0.30, 0.10]` → normalize `[0.36, 0.28, 0.20, 0.12, 0.04]`
- **中位 opponent (= win_rate 0.5) への sample 比率が 0.15 → 0.20 に増**、 hardest 集中が緩和、 curriculum stall + forgetting trade-off が 4P 用に再平衡

### 6.4 既存 plan 整合

- ✅ `2026-05-11-rl-best-practices.md:84-87` の adaptive curriculum (= win_rate dependent self_play_prob) と直交、 並用可能
- ⚠️ `2026-05-11-rl-best-practices.md:11` で `PFSP weight w∝(1-WR)²` が AlphaStar-grade と明言、 **4P 補正の議論なし** → 本研究で初の明示的根拠
- ⚠️ `2026-05-11-alphastar-league-design.md:25-28` の opponent sampling 設計が 「PFSP weight ∝ $(1-WR)^2$ で全 league 中から sample」 のみ記載で、 **exponent の 4P 補正に言及なし** → §6 で update 必須

### 6.5 未解決

- $p_{\exp} = 1.0$ vs $p_{\exp} = 1.5$ vs $p_{\exp} = 2.0$ の **実証 ablation**: 200k step run × 3 設定 = 600k step、 Colab Pro+ A100 で 約 6h。 Day 5-7 の PPO θ.4 1M step run の事前 ablation として実施推奨
- **adaptive $p_{\exp}$**: pool 内 win_rate variance が小さくなったら $p_{\exp}$ を増 (= curriculum 加速)、 大きいなら減 (= diversity 確保) の動的調整。 理論未確立だが Day 15+ league phase で検討

---

## 2. 我家 PPO θ.5 training への 直接 適用 推奨 (= 5 件)

### 推奨 1: **PFSP exponent を $p_{\exp} = 2 \to 1$ に下げる** (= §6.2-6.3) ★★★ 即修正

- **理由**: 4P FFA で 3 個独立 sample の乗算性により、 2P 用 $p_{\exp} = 2$ は実効的に過激。 1.0 で中位 opponent への curriculum stall を緩和
- **修正箇所**: `tools/train_ppo_pfsp.py:67` の `** 2` を `** 1.0` に
- **検証**: 200k step run × `[1.0, 1.5, 2.0]` 3 設定で local 4P win rate 比較、 Day 5 実施
- **expected lift**: pool diversity 改善で training 中盤 plateau 回避、 LB +50-100 (= rl-best-practices.md §2.5 と並用で)

### 推奨 2: **target_kl = 0.02 early stopping を明示有効化** (= §3.3-3.4) ★★★ 即修正

- **理由**: 我家観測 `approx_kl = 0.045` は trust region 違反域。 n_epochs を 4 → 8 に増やす提案 (rl-best-practices.md §1) は target_kl 制約なしだと暴走 risk
- **修正箇所**: `tools/train_ppo_pfsp.py` の PPO instantiation に `target_kl=0.02` 追加
- **検証**: 1k step smoke で update_count が `n_epochs × n_envs / batch_size` より少ない (= early stop 発火) を確認
- **expected lift**: training 安定化、 explained_variance 0.95 維持しつつ approx_kl 0.02 に追い込み

### 推奨 3: **`Δplanets` reward を carrying capacity $K = 6$ で clip** (= §4.4, §5.3) ★★ Day 5 修正

- **理由**: 既存 dense reward `+0.01 × Δplanets` は logistic 飽和を加味してない。 over-expansion bias で defense が疎かになる
- **修正箇所**: `phase_theta_ppo_design.md:36` の reward 計算式を `+0.01 × max(0, min(Δplanets, K - N))` に変更、 env wrapper で実装
- **検証**: ODE simulation で planet 分布が `mean N → 5-6` に収束 (= bovard top tier 分布と一致) を確認
- **expected lift**: mid-game defense 強化、 bovard 観測の真因 (= mid-game gap) を直解

### 推奨 4: **bovard align bonus を指数 fit + 後半 anneal** (= §5.3, §4.4) ★★ Day 8-14 (Phase 2) で実装

- **理由**: 現 align bonus `target_S(t) = 21 + t/500 × 282` は線形で bovard 指数 (= step 400 で 1828) と mismatch。 後半 anneal で agent の novel exploit 発見余地確保
- **修正箇所**: `rl-best-practices.md:65` の `target_fleet_size` を `21 * exp(t / 110)` に、 加えて bonus coefficient を `0.02 * (1 - t/T)` で線形減衰
- **検証**: align bonus が step 0-200 で 0.02-0.05 / step、 step 300+ で 0.005 以下に減衰
- **expected lift**: training 後半で EndgamePileupMission 系 novel exploit を agent が学習する余地、 LB +30-80

### 推奨 5: **4P FFA empirical NE 監視 (= Nash averaging) を pool 12+ で導入** (= §1.2, §2.3) ★ Day 15+ (Phase 4 / γ)

- **理由**: 単純 「最新 checkpoint = strongest」 を submit に選ぶと特定 NE に偏向。 Nash averaging で pool 全体に対し robust な checkpoint を選ぶことで shake-up + public/private LB 乖離 risk を mitigate
- **修正箇所**: `tools/train_ppo_pfsp.py` の checkpoint save 後に pairwise win-rate matrix 集計 (= `eval_ppo_checkpoint.sh` 拡張) → meta-Nash 計算 → submit candidate ranking
- **検証**: pool 12 checkpoint で pairwise round-robin 50 episode、 meta-game payoff matrix の Nash mixture を numpy で計算
- **expected lift**: submit selection 精度 ↑、 LB ratio drift σ ≤ 0.02 安定化 (= Kaggle CLAUDE.md §4.3 の要件達成)

---

## 3. roadmap 数理 再武装 (= 既存 roadmap への 直接 patch 提案)

### Patch 1: `docs/strategy/2026-05-11-rl-best-practices.md` §2.4 (line 78-87) Adaptive curriculum 表に PFSP exponent 追加

**現状**:
```python
def get_curriculum_ratio(win_rate_vs_pool: float) -> tuple[float, float]:
    if win_rate_vs_pool < 0.4: return 0.4, 0.4
    elif win_rate_vs_pool < 0.5: return 0.6, 0.2
    else: return 0.8, 0.1
```

**提案 update**:
```python
def get_curriculum_ratio(win_rate_vs_pool: float) -> tuple[float, float, float]:
    """returns (self_play_prob, external_prob, pfsp_exponent)."""
    if win_rate_vs_pool < 0.4: return 0.4, 0.4, 0.5  # 弱: uniform 寄り + external 多
    elif win_rate_vs_pool < 0.5: return 0.6, 0.2, 1.0  # 中: PFSP exp=1.0
    else: return 0.8, 0.1, 1.5  # 強: PFSP exp=1.5 で curriculum 加速
```

**根拠**: §6.5 「adaptive $p_{\exp}$」 を実装。 4P FFA で 2P 用 $p_{\exp} = 2$ は実効過激、 win_rate 依存で 0.5-1.5 範囲調整。

### Patch 2: `docs/strategy/2026-05-11-rl-best-practices.md` §2.3 (line 56-73) bovard align bonus を指数 fit に修正

**現状 line 65**:
```python
target_fleet_size = 21 + (step / 500) * 282
```

**提案 update**:
```python
# bovard 280M row 指数 fit: step 0=21, step 200=130, step 400=1828
target_fleet_size = 21 * math.exp(step / 110)
# 後半 anneal で agent の novel exploit 余地確保
bonus_coef = 0.02 * max(0.0, 1.0 - step / 400)  # step 400+ で 0
```

**根拠**: §4.4 で bovard 実測 (`docs/strategy/2026-05-11-score-2000-roadmap.md:18-22`) と既存 線形 fit の mismatch を指摘。 指数 fit で alignment 精度向上、 後半 anneal で free exploration 確保。

### Patch 3: `docs/strategy/2026-05-11-alphastar-league-design.md` §2 (line 18-24) League 構成比に 4P 補正注釈追加

**現状**: Main 50% / Main exp 25% / League exp 25% (= AlphaStar 2P 設定 borrow)

**提案 update**: 同表を維持しつつ、 §4 「数理本質」 に新 sub-section 追加:

> **4.6 4P FFA での比率調整**: AlphaStar の 50/25/25 比は 2P StarCraft II 設定。 4P FFA では 1 episode で 3 opponent slot 必要、 effective diversity が 2P の 3 倍。 我家 setting では:
>
> | role | 2P AlphaStar | 4P orbit-wars | 根拠 |
> |---|---|---|---|
> | Main | 50% | **60%** | 4P diversity 自然増で Main 比率上げて curriculum 効率取る |
> | Main exp | 25% | **20%** | 1 opponent slot 専用、 比率小で十分 |
> | League exp | 25% | **20%** | 同上 |
> | Pure self-play | 0% | (= 上記に含む) | strict self-history は Main 内で実装 |

**根拠**: §2.3 「4P FFA で diversity 自然増の数理」 で 2P → 4P で effective opponent set サイズが 3 倍化する議論を整理。

### Patch 4: `docs/strategy/phase_theta_ppo_design.md` §2 (line 30-39) Reward shaping に carrying capacity clip + potential-based 保証注釈追加

**現状 line 36**:
```
+0.01 × (Δmy_planet_count - 0) per step (= expansion bonus, 主因 lesson)
```

**提案 update**:
```
+0.01 × max(0, min(Δmy_planet_count, K - N)) per step
  ここで K = 6 (= 4P FFA logistic carrying capacity, bovard 実測, §4.2)
  N = current planet count
  → 飽和後 (N=6 以上) は reward 出ない、 over-expansion bias 防止
```

加えて新 sub-section:

> **2.6 potential-based shaping 保証**: 採用 dense reward $R' = R + \gamma \phi(s') - \phi(s)$ は Ng et al. 1999 theorem で optimal policy 不変が保証される。 我家設定 $\phi(s) = w_1 \cdot \min(N, K) + w_2 \cdot S$ は potential として有効、 偏向 risk なし。 ただし bovard align bonus は potential-based ではない (= action-conditional) で optimal policy bias を持つので **late game anneal が必須**。

**根拠**: §5.2-5.3 potential-based shaping + §4.4 logistic capacity 飽和の議論。

---

## 出典 (= 全件 arxiv ID + URL)

### Game theory / equilibrium

- Nash 1950, "Equilibrium points in n-person games", https://doi.org/10.1073/pnas.36.1.48
- Brown 1951, "Iterative solutions of games by fictitious play", RAND P-78, https://www.rand.org/content/dam/rand/pubs/papers/2008/P78.pdf
- Shapley 1953, "A value for n-person games", contributions to the theory of games
- Hannan 1957, "Approximation to Bayes risk in repeated play", https://doi.org/10.1515/9781400882151-006
- Foster & Vohra 1997, "Calibrated learning and correlated equilibrium" (Games and Economic Behavior)
- Walsh, Das, Tesauro, Kephart 2003, "Empirical game-theoretic analysis"
- Balduzzi et al. 2018, "Re-evaluating Evaluation" (Nash averaging), https://arxiv.org/abs/1806.02643

### Self-play / multi-agent RL

- Heinrich, Lanctot, Silver 2015, "Fictitious self-play in extensive-form games"
- Heinrich, Silver 2016, "Deep Reinforcement Learning from Self-Play in Imperfect-Information Games" (NFSP), https://arxiv.org/abs/1603.01121
- Lanctot et al. 2017, "A Unified Game-Theoretic Approach to Multiagent RL" (PSRO), https://arxiv.org/abs/1711.00832
- Jaderberg et al. 2017, "Population Based Training of Neural Networks", https://arxiv.org/abs/1711.09846
- Vinyals et al. 2019, "Grandmaster level in StarCraft II using multi-agent RL" (AlphaStar Nature), https://www.nature.com/articles/s41586-019-1724-z
- OpenAI 2019, "Dota 2 with Large Scale Deep RL", https://arxiv.org/abs/1912.06680

### PPO / actor-critic

- Schulman et al. 2015, "High-Dimensional Continuous Control Using GAE", https://arxiv.org/abs/1506.02438
- Schulman et al. 2017, "Proximal Policy Optimization Algorithms", https://arxiv.org/abs/1707.06347
- Loshchilov & Hutter 2017, "SGDR: Stochastic Gradient Descent with Warm Restarts", https://arxiv.org/abs/1608.03983
- Lilian Weng 2018, "Policy Gradient Algorithms", https://lilianweng.github.io/posts/2018-04-08-policy-gradient/
- Huang et al. 2022, "The 37 Implementation Details of PPO" (ICLR Blog), https://iclr-blog-track.github.io/2022/03/25/ppo-implementation-details/
- OpenAI Spinning Up, "Proximal Policy Optimization", https://spinningup.openai.com/en/latest/algorithms/ppo.html

### Reward shaping

- Ng, Harada, Russell 1999, "Policy Invariance Under Reward Transformations", ICML, https://www.aaai.org/Papers/ICML/1999/ICML99-064.pdf
- Ng & Russell 2000, "Algorithms for inverse reinforcement learning", ICML
- Ziebart et al. 2008, "Maximum entropy IRL"

### Ecology / Lotka-Volterra (= expansion ODE)

- Lotka 1925, "Elements of physical biology"
- Volterra 1926, "Fluctuations in the abundance of a species considered mathematically"
- Wikipedia "Lotka-Volterra equations", https://en.wikipedia.org/wiki/Lotka%E2%80%93Volterra_equations

### 既存 orbit-wars 内部 docs

- `docs/strategy/2026-05-11-victory-roadmap.md` (= 6-phase 全体 roadmap)
- `docs/strategy/2026-05-11-score-2000-roadmap.md` (= bovard 280M row 真因 reframe, line 18-30)
- `docs/strategy/2026-05-11-rl-best-practices.md` (= 5 修正 best practice, line 11-26)
- `docs/strategy/2026-05-11-alphastar-league-design.md` (= league 構成案, line 18-28)
- `docs/strategy/phase_theta_ppo_design.md` (= reward shaping 仕様, line 30-39)
- `docs/research/2026-05-11-engine-audit.md` (= engine 仕様 5 exploit candidate, line 14-99)
- `tools/train_ppo_pfsp.py` (= 現 PFSP 実装, line 63-119)
- `data/processed/actions/bovard_2026_05_04.parquet` (= 2,820,068 row 観測元)
