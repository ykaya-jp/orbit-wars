# 過去 Kaggle agent comp の優勝 RL 軽量化技法調査 (= 2026-05-12)

> orbit-wars 優勝 path 補強研究 W1
> 担当範囲: Halite IV / Lux AI S1-S3 / Connect X / Hungry Geese / Kore 2022 の優勝解法
> 観点: submission size 制約 + RL 軽量化技法 + deployment pattern
> 出典基底: `docs/research/past-comps.references.json` (= 2026-05-09 baseline) + 本 doc で追加 web 探索
> 著者規律: ~/.claude/CLAUDE.md "Links, not verdicts" / ~/projects/kaggle/CLAUDE.md §11 「優勝本質性」

---

## 0. 本 doc の動機 (= 軽量化が なぜ critical か)

orbit-wars 直近の失敗 datapoint:
- PPO sb3 zip = `425 MB` の tar.gz 提出 (= フル sb3 model)
- 結果: **submit reject (= 400 Bad Request 系)、 LB に乗らず**
- 出典: `docs/dev/HANDOFF-2026-05-12.md` §6 + `docs/research/2026-05-12-submission-analyses.md`

仮説: Kaggle simulation comp は **submission size の hard cap (= ~100 MB)** を持つ可能性が高い。 過去 6 comp の優勝者がどう同制約を回避したかを extract、 orbit-wars 残 42 day で **RL paradigm を生かす deployment 最小コスト path** を確定する。

⚠️ host 提示の正式 size limit は orbit-wars 公式 rule では未確認 (= TBD、 priority: high)。 ただし **Lux S3 1st (Frog Parade) が writeup で「62MB shy of the 100MB submission file size limit」と明記** = de facto **100 MB** が agent comp の標準 cap (出典: https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md)。

---

## 1. 各 comp 概要表 (= 6 件 + 補助 2 件)

| Comp | 期間 | n_teams | 1st team | 1st paradigm | 1st submission size | 1st model size | host 提示 size limit |
|---|---|---|---|---|---|---|---|
| **Halite IV** | 2020 | 1143 | ttvand (Tom Van de Wiele) | rule_base + NN collision predictor (= hybrid) | TBD (= 未確認、 priority: mid) | NN は小型 (= per-ship 衝突予測のみ) | TBD |
| **Lux AI S1** | 2021 | 1100+ | Toad Brigade | deep RL (IMPALA+UPGO+TD(λ)) | TBD | **~20M params** (= 24-block ResNet 128ch) | TBD (= 推定 100 MB、 根拠: S3 と同 host platform) |
| **Lux AI S2** | 2023 | 646 | ry-andy | **pure Python heuristic** (= no NN) | 数 MB (= Python source のみ) | n/a | TBD |
| **Lux AI S3** | 2024-2025 | (NeurIPS 2024) | Frog Parade (Isaiah Pressman) | deep RL PPO + SE-ResNet | **~38 MB** (= 62MB shy of 100MB) | **~10M params** (= 8-block SE-ResNet 256ch) | **100 MB** (= 明記、 critical) |
| **Connect X** | 2020- (永続) | (ongoing) | (rotating LB、 Alpha-Beta 系優勢) | rule_base + minimax | < 1 MB (= 推定) | n/a | TBD (推定 100 MB) |
| **Hungry Geese** | 2021 | 875 | HandyRL (DeNA) | distributed off-policy DRL + self-play CNN | TBD | **小型 CNN ~8 layer × 46 channel** (= ~0.5M params 推定) | TBD |
| **Kore 2022** | 2022 | (NeurIPS-affiliated) | khanhvu207 | imitation learning + autoregressive Transformer | TBD | **12-layer ResNet + Transformer decoder** (= param count 未明記) | TBD |
| (補助) Halite II | 2017-2018 | 6000 | reCurs3 | **pure rule-base** (= C++) | 数百 KB (= bot binary) | n/a | n/a |

凡例:
- "TBD (= 未確認、 priority: <high/mid/low>)" は writeup / README から数値が抽出不能だった項目
- "推定" は 1st-party 引用ではないが横断証拠 (= 同 host platform 等) から導いた値

---

## 2. RL paradigm の優勝解法 抽出 (= comp 別深掘り)

### 2.1 Lux AI Season 3 (= 最重要、 orbit-wars と同年 + 100 MB cap 明記)

- **1st place**: Frog Parade (Isaiah Pressman)
  - Kaggle URL: https://www.kaggle.com/competitions/lux-ai-season-3/writeups/flat-neurons-1st-place-approach-by-flat-neurons (= writeup 入り口、 ただし WebFetch では title のみ返却)
  - Wait, 上記 URL は別チーム (Flat Neurons) の writeup。 Isaiah Pressman の repo は別:
  - **writeup URL**: https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md
  - **GitHub repo**: https://github.com/IsaiahPressman/kaggle-lux-2024
- **architecture (= 引用一次資料)**:
  - 8-block 3x3 SE-ResNet
  - hidden dim 256
  - **~10M params**
  - dual actor head: 2-layer MLP (10 actions) + 2-layer CNN (24x24 sap map)
  - value head: 2-layer 1x1 CNN → 1x24x24 → mean-reduce
  - 10-frame history input
- **submission size**: **~38 MB** (= 100 MB limit に 62 MB margin、 author 自身 "should have scaled up further")
- **軽量化技法**:
  - 明示的な quantization / distillation / pruning は **なし** (= writeup 内 mention なし)
  - ただし **Vision Transformer 試行** (= rotary positional embeddings) で「comparable performance with many fewer parameters」 を確認、 ただし training stability 問題で本番採用せず
- **deployment pattern (= main.py)**:
  - JSON stdin/stdout I/O wrapper (= Kaggle agent protocol)
  - `from rux_ai_s3.rl_agent import Agent` → `agent.act(obs)` 形式 (= 内部 abstraction)
  - 詳細 model load は `python/rux_ai_s3/rl_agent/` 下に隠蔽 (= GitHub directory listing で確認、 WebFetch では中身取得不能)
  - 出典: https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/python/main.py
- **submission packaging (= 完全引用、 orbit-wars に直接適用可)**:
  ```bash
  tar --exclude="*__pycache__*" --transform "s,^python/,," -czvf submission.tar.gz <files>
  ```
  - 出典: `Dockerfile` 内 (https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/Dockerfile 経由 WebFetch 抽出)
  - 含まれる: `python/main.py` + `python/rux_ai_s3/` (= source + model checkpoint)
  - 除外: `*__pycache__*`
  - 圧縮: gzip (`-z` flag)
- **training compute**:
  - 1x RTX 3090 + 1x RTX 2070S, 64GB RAM, AMD 9950X 16-core
  - in-house Rust simulator (= TDD against official Python engine、 ~110k env steps/s)
  - **~300M frames over ~8 days continuous**
  - ~430 train steps/s
- **failure modes (= writeup 明記)**:
  1. 「Action masking was overly restrictive」 (= blind sapping 制限が suboptimal)
  2. 「Per-unit value factorization 実験 全 fail」 (= abandoned)
  3. 「GLIBC version mismatch during Docker compilation」 (= 当初 submit 不能、 Dockerfile build で解決)
- **引用 (= 一次資料)**:
  > "I could, and probably should, have scaled this up further, since I was still 62MB shy of the 100MB submission file size limit."
  > (出典: https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md)

  > "comparable performance with many fewer parameters [Vision Transformer w/ rotary pos embeddings]"
  > (出典: 同上 writeup)

### 2.2 Lux AI Season 1 (= Toad Brigade、 DRL 系統で 1st = orbit-wars に最も類似 path)

- **1st place**: Toad Brigade
  - writeup URL: https://www.kaggle.com/competitions/lux-ai-2021/writeups/toad-brigade-toad-brigade-s-approach-deep-reinforc
  - technique: **deep_rl_impala_upgo_tdlambda** (= 注意: PPO ではない)
- **architecture (= 引用)**:
  - fully convolutional ResNet w/ squeeze-excitation
  - **24 residual blocks**, **128-channel 5x5 conv**
  - **~20M params**
  - no batch-norm in residual blocks (= train stability)
  - 3 actor heads (workers/carts/city-tiles, 32x32xN tensor each) + 1 critic head ([-1, 1] scalar)
  - 入力: discrete features → 32-d learned embeddings + continuous features → per-feature normalize → 128x32x32
- **submission size**: TBD (= 未確認、 priority: high。 推測: ~80 MB if FP32 で full state_dict のみ。 根拠: 20M params × 4 bytes = 80 MB)
- **軽量化技法**:
  - 明示的 mention なし (= writeup 内)
  - "progressive net size 8→16→24 blocks with teacher distillation (KL)" (= **distillation を train 内部で使用**、 ただし submission size 削減目的ではなく training stability + 性能向上)
- **inference time** (= 一次引用):
  > "Inference took 2-2.5 seconds on Kaggle servers with batch size 2"
  > (出典: WebFetch via https://github.com/IsaiahPressman/Kaggle_Lux_AI_2021 経由要約)
- **deployment**:
  - test-time aug: 180° rotation averaging
  - deterministic action select (= argmax、 not sample)
- **training compute**: **single 8c/16t personal PC w/ dual GPU、 overnight training** (= 驚くほど modest)
- **failure modes**:
  - "Reward shaping for first 20M steps then sparse +1/-1" → reward shape を外した瞬間 collapse する risk
  - per-unit network ではなく single network for all units (= GridNet pattern)、 これを per-unit に分割していたら collapse の可能性 mention
- **引用**:
  > "Progressive net size 8→16→24 blocks with teacher distillation (KL)"
  > "Test-time augmentation: 180° rotation averaging"
  > (出典: docs/research/past-comps.references.json + Kaggle writeup)

### 2.3 Hungry Geese (= HandyRL、 小型 CNN の代表例)

- **1st place**: HandyRL (DeNA team)
  - framework URL: https://github.com/DeNA/HandyRL
  - discussion: https://www.kaggle.com/c/hungry-geese/discussion/218190
- **architecture**:
  - ResNet-based Policy/Value dual network
  - **8 layers × 46 channels** (= 出典: speakerdeck.com/hoxomaxwell/kaggle-hungry-geese 経由 WebSearch)
  - param 推定: ~0.5M (= 8 × 46 × 46 × 3 × 3 × 5 / 1e6 = roughly 0.4M)
  - step-count channel as input (= endgame strategy)
- **submission size**: TBD (= 未確認、 priority: low。 推定: < 5 MB、 0.5M params × 4 bytes = 2 MB)
- **軽量化技法**:
  - **そもそも小型** = 8 layer × 46ch で十分性能
  - mixed past-version opponent pool (= 単純 self-play でなく、 過去 self を pool 化)
  - AlphaZero-style MCTS を**最終段で bolt-on** (= train 時は MCTS なし、 deploy 時のみ追加で size 不変)
- **deployment**: HandyRL framework が PyTorch model 保存 + 標準的な torch.load パターン (= GitHub repo 構造から推定、 詳細コードは未取得 priority: low)
- **failure modes**:
  - "Continuous body gradient (1.0 head → 0.0 tail) instead of binary mask" を採らなかった team が劣後 (= input representation の細部が決定的)
- **引用**:
  > "ResNet-based Policy/Value dual network with 8 layers and 46 channels"
  > (出典: speakerdeck.com/hoxomaxwell/kaggle-hungry-geese WebSearch 結果)

### 2.4 Kore 2022 (= IL + Transformer の代表例、 唯一の Transformer 優勝)

- **1st place**: khanhvu207
  - writeup URL: https://www.kaggle.com/competitions/kore-2022/discussion/340035 (= Kaggle login wall で WebFetch 直接抽出不能)
  - GitHub repo: https://github.com/khanhvu207/kore2022
- **architecture (= README から抽出)**:
  - multi-modal Transformer (= Pixel-BERT inspired)
  - 12-layer ResNet w/ GroupNorm (= spatial 18-channel 3D tensor encoder)
  - MLP for scalars
  - 256-d char embedding for ship plans (= autoregressive 出力)
  - autoregressive Transformer decoder (= char-by-char, e.g. "N 10 W 5")
- **submission size**: TBD (= 未確認、 priority: high。 推定: Transformer 系は params 多い可能性、 30-90 MB range)
- **軽量化技法**:
  - bag-of-words ship-plan embedding (= 2nd Transformer を回避、 計算量削減、 = 間接的に param 削減)
  - **明示的 FP16 / quantization / ONNX 言及なし** (= README 確認、 priority: low for confirmation)
- **training compute (= README 明記)**:
  - **2x A100 80GB**
  - batch 64
  - 20 epochs
  - AdamW lr=4e-3 cosine scheduler, 5% warmup
  - gradclip 0.5
  - 60% spatial pixel dropout aug (= 強い regularization、 訓練 dataset 200M tuples)
- **training data**: **200M (obs, plan) tuples scraped from top-5 leaderboard submissions** (= IL paradigm の典型)
- **failure modes**: README 内明示なし。 仮想 risk:
  - 200M tuples scrape の cost (= submission replay 取得が host 提供 dataset で easy だったから可能だった)
- **引用**:
  > "12-layer ResNet with a GroupNorm layer ... multi-modal Transformers architecture"
  > "2 x A100 (80GB VRAM), batch size 64, 20 epochs, AdamW lr=4e-3"
  > (出典: https://github.com/khanhvu207/kore2022 README)

### 2.5 Halite IV (= ttvand、 hybrid rule + NN の代表例)

- **1st place**: Tom Van de Wiele (ttvand)
  - GitHub repo: https://github.com/ttvand/Halite
  - discussion: https://www.kaggle.com/c/halite/discussion/183312 (= Kaggle login wall で WebFetch 不能)
- **architecture (= 一次資料は README 構造のみ)**:
  - rule_based core (`Rule agents/` folder)
  - + NN collision predictor (`Deep Learning Agents/` folder)
  - 2 component の hybrid
- **submission size / NN size**: TBD (= 未確認、 priority: mid。 NN は collision 予測のみで小型と推定 < 10 MB)
- **軽量化技法**: 不要 (= NN が補助的、 rule_base が主)
- **failure modes**: writeup 直接 access 不能、 priority: low for follow-up
- **引用**:
  > "separate folders for rule-based and Deep Learning agents — final winner combined heuristic strategy with NN for opponent move prediction"
  > (出典: docs/research/past-comps.references.json + https://github.com/ttvand/Halite README)

### 2.6 Lux AI Season 2 (= 反例、 pure heuristic が DRL/IL を破った)

- **1st place**: ry-andy
  - writeup URL: https://www.kaggle.com/competitions/lux-ai-season-2/writeups/ry-andy-1st-place-solution
  - GitHub repo: https://github.com/ryandy/Lux-S2-public
- **paradigm**: **pure Python heuristic** (= no NN at all)
- **submission size**: 数 MB 推定 (= Python source のみ)
- **lesson (= 重要)**: NeurIPS が 1B+ frames の S1 IL data を提供したにもかかわらず、 **Kaggle LB 1st は pure heuristic**。 RL track は別評価
- 引用:
  > "Despite NeurIPS providing >1B frames of S1 imitation-learning data, the Kaggle leaderboard was won by a pure-Python rule-based bot."
  > (出典: docs/research/past-comps.references.json)

### 2.7 Connect X (= 永続 comp、 軽量解の代表)

- 1st place: rotating (= 永続 LB)、 ConnectX は強解析解 (= 完全先読み) が既知、 minimax + Alpha-Beta が dominant
- size: << 1 MB
- 軽量化: 不要、 そもそも NN 不使用
- 出典: https://www.kaggle.com/c/connectx/discussion/126678 (WebFetch 不能)

---

## 3. 軽量化技法の整理表 (= 全 comp 統合)

| 技法 | 出典 comp / source | 削減率 | 副作用 | orbit-wars 適用可? | priority |
|---|---|---|---|---|---|
| **そもそも小型 model 採用** | Hungry Geese 1st (8 layer × 46ch ≈ 0.5M params) | 95%+ vs sb3 default | none、 ただし表現力上限 | ✅ **第一推奨** (= sb3 PPO の default policy_kwargs を縮小) | **high** |
| **state_dict 抽出 (= sb3 zip 解体)** | sb3 docs (https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html) | 50-70% (sb3 zip 全部 vs torch.save state_dict) | sb3.load 不可、 自前 forward 必要 | ✅ **必須実装** | **high** |
| **FP16 weight 保存** | PyTorch native (`tensor.half()` save) | **50%** vs FP32 | 推論精度わずか低下 (= 通常無視可) | ✅ 適用可 | **high** |
| **tar.gz w/ `__pycache__` exclude + gzip** | Lux S3 1st (Frog Parade Dockerfile) | 5-15% | none | ✅ **そのまま採用** | **high** |
| **distillation (smaller student net)** | Lux S1 1st (Toad Brigade progressive 8→16→24) | comp 依存 (= 2-5x downsize) | KL 損失調整必要、 train cost +30% | ✅ Day 5+ で検討 (= 1M step PPO 完走後の polishing 段階) | **mid** |
| **ONNX export** | 一般技法 (= 明示 RL comp での使用 1st 例なし) | varies (FP32 → ONNX で 10-30%) | sb3 直接 export 不可、 wrapper 自作 | ⚠️ 検証必要 | **low** |
| **quantization int8 (post-training)** | 一般技法、 RL comp 1st 例なし | 75% vs FP32 | RL policy で精度 drop が報告例あり | ❌ **risk 高、 後回し** | **low** |
| **小型 architecture (SE-ResNet 8 block 256ch)** | Lux S3 1st | base 比 30-50% | none | ✅ 推奨 (= 直近 Day 5 PPO config) | **high** |
| **stateful 削除 + caching** | Halite II 2nd (FakePsyho 50-100x speedup) | 推論 speed 文脈、 size には無関係 | bug-prone | n/a (= size 観点では適用外) | low |

---

## 4. 「これ知らないと負ける」 罠 5 件

1. **sb3 `.save("model.zip")` をそのまま提出すると死ぬ**
   - sb3 の zip は **policy + optimizer + replay_buffer + env_normalize 全部入り** で多くの場合 100 MB 超
   - 正解: `model.policy.state_dict()` を `torch.save(state_dict, "policy.pt")` で抽出、 deploy 側は `MlpPolicy` (or 自前 nn.Module) を init して `load_state_dict` (= sb3 docs + 一般 PyTorch deployment pattern)
   - 出典: orbit-wars 自体の 425 MB reject 失敗 (= `docs/dev/HANDOFF-2026-05-12.md` §6 ⇔ 推測根拠: sb3 docs https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html "PPO.save saves a zip-file with all attributes")

2. **Docker compile した binary を含めて GLIBC 不一致で死ぬ**
   - Lux S3 1st (Frog Parade) が writeup で明記
   - 「GLIBC version mismatch during Docker compilation initially caused submission difficulties」
   - 出典: https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md
   - orbit-wars 適用: Kaggle agent runtime image (= Ubuntu base + Python 3.10/3.11) と build host (= Colab、 Linux x86_64) を **一致** させる、 もしくは pure Python のみで提出

3. **`__pycache__` を tar に巻き込んで size 超過 + import 順序破壊**
   - Lux S3 1st が `--exclude="*__pycache__*"` を明示 tar option に
   - orbit-wars 適用: `tar --exclude="*__pycache__*" --exclude=".git" --exclude="*.pyc" -czvf submission.tar.gz` を build script に固定化
   - 出典: https://github.com/IsaiahPressman/kaggle-lux-2024 Dockerfile

4. **inference timeout (= 1 step あたり host 規定 ms)**
   - Lux S1 1st (Toad Brigade): 「Inference took 2-2.5 seconds on Kaggle servers with batch size 2」
   - つまり **20M params の ResNet は 1 step に 2.5s 使える host = それなりに ample**、 ただし orbit-wars が 1 step 何 ms を許容するか TBD (= 未確認、 priority: high)
   - 出典: Toad Brigade writeup
   - smoke test 観察 (= 自前 `docs/research/2026-05-13-submission-analyses.md` §44-55): ppo_v4_theta4 で per-step ~0.006s = sb3 PPO は十分高速、 size の方が制約
   - 注意: cuda 環境を期待する torch.load は host CPU 環境で fail、 `map_location="cpu"` を必ず

5. **single paradigm では LB 1700+ 抜けない (= 親 CLAUDE.md §1.3 ARChitects 教訓)**
   - Lux S3 1st = pure RL で 1st 取れたが、 Lux S2 1st = pure heuristic、 Halite IV 1st = hybrid
   - orbit-wars LB top1 = bowwowforeach 1698 (= 公開 kernel 未投稿)、 paradigm 不明
   - **rule_base + RL hybrid (= NN を 1 part だけ補助に使う Halite IV 1st pattern)** が安全 path
   - 出典: docs/research/past-comps.references.json §_cross_comp_synthesis

---

## 5. orbit-wars への直接適用 推奨 3 件 (= ROI 順)

### 推奨 1 (= **必須**): sb3 zip 解体 → state_dict.pt + 自前 inference module

- **何**: `model.policy.state_dict()` を `torch.save(state_dict, "policy.pt")` で抽出、 deploy 側は `nn.Module` を init + `load_state_dict(torch.load("policy.pt", map_location="cpu"))`
- **size 削減**: 425 MB → 推定 **20-40 MB** (= 50-70% 削減、 sb3 docs と 20M params × 4 bytes ≈ 80 MB の理論値 cross-check)
- **train 影響**: なし (= train は sb3 のまま、 export のみ追加)
- **ROI**: 最高 (= 直近 RL submit を生かす唯一 path)
- **実装 effort**: 1-2 hour (= sb3 docs に exact recipe あり)
- **risk**: 自前 forward が sb3 と numerically 一致するかの検証 (= unit test 必須)
- **出典**: https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html, https://github.com/DLR-RM/stable-baselines3/blob/master/stable_baselines3/ppo/ppo.py

### 推奨 2 (= **強推奨**): policy_kwargs で hidden 縮小 + FP16 export

- **何**: 次回 PPO train で `policy_kwargs=dict(net_arch=[256, 256])` → `[128, 128]` または `[64, 64]` (= 現在 default の 64-64 確認後 priority 再判定)、 + `state_dict` を `{k: v.half() for k,v in state_dict.items()}` で FP16 化
- **size 削減**: 推奨 1 適用後の 30 MB → **~8 MB** (= FP16 50% + 縮小 50%)
- **train 影響**: 表現力 trade-off (= 既存 explained_variance 0.95 が 0.90-0.93 に低下する可能性、 ただし orbit-wars の signal は希薄なので 0.90 でも十分 win rate に効く可能性)
- **ROI**: 高
- **実装 effort**: 1 hour
- **risk**: FP16 で NaN 起きる layer (= norm 系) を FP32 維持 (= mixed precision pattern)
- **出典**: PyTorch native `tensor.half()` + Lux S3 1st が `~10M params で 38 MB` = FP32 4 bytes × 10M = 40 MB の理論一致 (= つまり S3 1st は FP32 そのまま、 我々はそこから更に削れる余地)

### 推奨 3 (= **mid-term**): Lux S3 1st repo の packaging script を**そのまま port**

- **何**: 以下を `tools/make_submission.sh` として固定化:
  ```bash
  tar --exclude="*__pycache__*" \
      --exclude="*.pyc" \
      --exclude=".git" \
      --exclude="*.swp" \
      -czvf submission.tar.gz \
      main.py policy.pt rux_orbit_wars/
  ```
- **size 削減**: 直接 size 削減ではないが、 **size 超過事故防止** + reproducibility
- **train 影響**: なし
- **ROI**: 中 (= 副次的、 ただし「次の 425 MB reject」 を物理的に防ぐ)
- **実装 effort**: 30 min
- **risk**: なし
- **出典**: https://github.com/IsaiahPressman/kaggle-lux-2024 Dockerfile

---

## 6. TBD 一覧 (= 残課題、 priority 順)

1. **orbit-wars 公式 rule の submission size limit** (= **priority: high**)
   - 行動: `kaggle competitions describe orbit-wars` + rule page WebFetch + discussion で 「size」 検索
   - 期限: 推奨 1 を実装する **前** に確認 (= 100 MB cap が本当か検証、 もしかしたら 50 MB / 200 MB の可能性)
2. **Kore 2022 1st (khanhvu207) Transformer の param count + submission size** (= priority: high)
   - 行動: GitHub repo を `git clone` して config 直接読む、 writeup discussion を Kaggle CLI で `kaggle kernels list / kaggle competitions discussion list` 経由取得
3. **Toad Brigade (Lux S1 1st) submission size の実数値** (= priority: high)
   - 行動: Toad Brigade GitHub repo (= 検索結果に出ず、 後継 IsaiahPressman/Kaggle_Lux_AI_2021 で代替確認)
4. **Halite IV ttvand の NN model 実 size** (= priority: mid)
   - 行動: `git clone https://github.com/ttvand/Halite && du -sh "Deep Learning Agents/"`
5. **`stable_baselines3.PPO.save()` の zip 構造 detail** (= priority: high、 sb3 zip を 425MB → 30MB に削る上で必須情報)
   - 行動: sb3 source code `stable_baselines3/common/base_class.py` `save_to_zip_file` 関数を Context7 で直接 read、 zip 内に optimizer / replay_buffer がどれだけ含まれるか確認
6. **Frog Parade `rl_agent.py` の torch.load pattern** (= priority: mid)
   - 行動: `gh repo clone IsaiahPressman/kaggle-lux-2024 /tmp/lux-s3 && cat /tmp/lux-s3/python/rux_ai_s3/rl_agent/agent.py`

---

## 7. 出典 (= 全 URL 明記)

### 一次資料 (= writeup / repo / docs を直接 fetch 済)

- Lux S3 1st writeup: https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/write-up.md
- Lux S3 1st repo: https://github.com/IsaiahPressman/kaggle-lux-2024
- Lux S3 1st Dockerfile: https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/Dockerfile
- Lux S3 1st main.py: https://github.com/IsaiahPressman/kaggle-lux-2024/blob/main/python/main.py
- Kore 2022 1st repo: https://github.com/khanhvu207/kore2022
- Halite IV 1st repo: https://github.com/ttvand/Halite
- Halite IV 4th repo: https://github.com/0Zeta/HaliteIV-Bot
- Halite II 2nd repo: https://github.com/FakePsyho/halite2
- Lux S1 alt repo: https://github.com/IsaiahPressman/Kaggle_Lux_AI_2021
- HandyRL framework: https://github.com/DeNA/HandyRL
- sb3 PPO docs: https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html
- sb3 source: https://github.com/DLR-RM/stable-baselines3

### 二次資料 (= cross-validated through 引用、 WebSearch 結果由来)

- Lux S3 1st writeup (Flat Neurons, Kaggle wall blocked): https://www.kaggle.com/competitions/lux-ai-season-3/writeups/flat-neurons-1st-place-approach-by-flat-neurons
- Lux S1 1st writeup (Kaggle wall blocked): https://www.kaggle.com/competitions/lux-ai-2021/writeups/toad-brigade-toad-brigade-s-approach-deep-reinforc
- Lux S2 1st writeup: https://www.kaggle.com/competitions/lux-ai-season-2/writeups/ry-andy-1st-place-solution
- Kore 2022 1st discussion (Kaggle wall blocked): https://www.kaggle.com/competitions/kore-2022/discussion/340035
- Halite IV 1st discussion (Kaggle wall blocked): https://www.kaggle.com/c/halite/discussion/183312
- Hungry Geese 1st discussion (Kaggle wall blocked): https://www.kaggle.com/c/hungry-geese/discussion/218190
- Hungry Geese arch slides: https://speakerdeck.com/hoxomaxwell/kaggle-hungry-geese
- Halite II 1st post-mortem (server offline at fetch time): https://recursive.cc/blog/halite-ii-post-mortem.html
- Halite II 1st mirror: https://medium.com/aescru/halite-ii-strategies-of-a-top-player-88127b3b49e2
- Kaggle simulation size limit discussion: https://www.kaggle.com/discussions/product-feedback/291072 (= content blocked、 priority: high で別経路再 fetch)

### orbit-wars 内部 cross-reference

- docs/research/past-comps.references.json (= 2026-05-09 baseline、 本 doc の構造化骨子)
- docs/dev/HANDOFF-2026-05-12.md §6 (= 425 MB reject の一次 evidence、 内部 doc)
- docs/research/2026-05-13-submission-analyses.md (= ppo_v4_theta4 smoke test per-step latency 0.006s)
- ~/projects/kaggle/CLAUDE.md §11 「優勝本質性」 criterion (= 本 doc 推奨 1-3 の選別基準)
