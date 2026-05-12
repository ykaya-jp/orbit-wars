---
name: failure-patterns
description: orbit-wars プロジェクトで実際に踏んだ失敗パターン集。CLAUDE.md「失敗の組織知化」(/postmortem) で更新される。実装前にこのファイルを参照して同じ穴に落ちないこと。
type: learned
---

# orbit-wars Failure Patterns

各 entry は `### YYYY-MM-DD <short-id>` で append-only。

---

### 2026-05-10 aggregation-without-data-validation

- **Symptom:** `FleetAggregationMission` を実装したが local tournament で v2 (Capture only) 比 **5/30 (17%) 勝率** で実戦失敗。33 unit tests pass + tournament で初めて反証された。
- **Trigger:** Day 5 で「Capacity gap が #1 失敗モードの主因」という Phase 1 リサーチ仮説に基づき、**bovard top10 dataset の存在を知らないまま** 仮説検証ステップ無しに実装着手。
- **Five whys:**
  1. なぜ Aggregation は v2 に勝てなかった? → 同 turn 多 home 発射が serial expansion 複利を阻害して、序盤の planet 占領数で v2 に劣後した。
  2. なぜ複利を阻害した? → home garrison を多 target に分散させて、後続 turn の Capture 発射力が低下。改善版 (`min_step=150 + min_target_ships=80`) でも 17% に留まり、aggregation 戦略自体が **少なくとも v2 を上回らない** ことが判明。
  3. なぜそれが事前に分からなかった? → 「Capacity gap が #1 主因」という仮説を **実プレイ data で反証/確証する step を plan に組み込まずに実装に入った**。
  4. なぜ実プレイ data 検証を skip した? → docs/research/lb-observations.md は **17 replay の statistical inference** にすぎず、N が小さく観測 (Top tier launch 中央値 25-40 など) は仮説検証の根拠として弱い。だが Phase 1 plan ではそれを根拠扱いにした。
  5. なぜ N=17 で十分とした? → **bovard 公式 top10 dataset (= 2630 ep/day × 19 day = 50,000 episodes 級)** の存在を知らなかった。0510.md (user dump の discussion 抜粋) を読んだのは Aggregation 失敗判明後。`/plan` 段階で「data 源の網羅調査」が precondition になっていなかった。
- **Root cause:** **verification-gap + process** — 仮説駆動実装の前に、入手可能な最大 data 源 (= bovard dataset) で仮説の方向性を実証する step が plan workflow に組み込まれていない。
- **Pattern:** Kaggle agent competition で「LB 観察 + research 仮説」だけを根拠に rule-base mission/policy を実装し、bovard / Meta-Kaggle / 公式 host dataset 等の **大規模実プレイ data で検証せず** に着手するケース全般。
- **Mitigation in this codebase:**
  - `src/orbit_wars/agent.py` で `ENABLE_FLEET_AGGREGATION = False` 化 (コードと test は温存)
  - `experiments/exp002/` に v2 snapshot を保存 (失敗対比用 baseline)
  - `tournament_log_v3_FAILED.csv` + `tournament_v31_vs_v2.csv` を残して反証データとして保存
  - bovard dataset 1 day 分 (2631 episodes) DL 完了、actions 抽出 pipeline (`tools/extract_actions.py`) 構築済 → top tier の実プレイ pattern 分析を **次の mission 設計の前に必ず通す** 運用に切替
- **Detection signal added:**
  - `/plan` 起動時の precondition チェックリストに「該当コンペ host が公開する replay/episode dataset を `kaggle datasets list -s <competition>` で確認したか」を追加することを提案
  - `acceptance_criteria.yaml` に `data_validated: true` フィールドを置き、対応する evidence (= bovard data の N サンプルで仮説 X が成立した) を要求
- **Proposed rules (require developer action):**
  1. `~/.claude/CLAUDE.md` lessons.md に追加: 「Kaggle agent competition で仮説駆動の rule-base 実装に着手する前に、host が公開する replay dataset (= 公式の bovard 系 dataset) を kaggle datasets list で確認 + 1 day 分は最低 DL して actions/state 分布を実測する」
  2. orbit-wars 用 `~/.claude/rules/` ではなく project 内の learned/rules-proposal.md に「**Kaggle Agent Comp Plan Precondition**: bovard / Meta-Kaggle / 公式 dataset 確認をPlan acceptance_criteria に必須項目として置く」を草案として残す (developer 判断で global rules/ 昇格)
  3. `tools/extract_actions.py` を `make insights TARGET=hypothesis-X` 形式の標準コマンドにし、仮説検証を data 駆動で routine 化

---

### 2026-05-12 subprocess-output-silence-misdiagnosed-as-stuck

- **Symptom:** Colab で trigger した PPO θ.5 1M step training が `params: 42,991,539` 出力後 22 分間 silent。 user が「処理止まっちゃってる」 と報告。 私 (Claude) は即「opp file 不在で SubprocVecEnv hang」 と速断し、 kill + opp file 復元 + 再 trigger を提示 (= 1M step ~24h ロス覚悟の destructive plan)。 直後 user paste の新 output で **実際は alive** = `[PFSP] step=5000 ... iter 1 time_elapsed=1346s fps=6` が出てきて 誤診断確定。
- **Trigger:** ① user の「stuck だ」 報告で confirmation bias が働いた。 ② SubprocVecEnv の 1st rollout (= 8 env × 1024 step = 8192 step 収集) が fps 5-6 で **22 分かかる**事実を計算で導かず、 「stdout 沈黙 = hang」 と短絡。 ③ `submissions/build_konbu_topk1/main.py` が untracked (= Colab clone に不在) という事実は確認できたが、 これと「training hang」 を **因果連結する根拠が薄い** (= train_ppo_pfsp.py が opp file 不在で fallback path 持つ可能性を確認せず)。
- **Five whys:**
  1. なぜ stuck と速断した? → user 報告 + log 沈黙 ≥ 20 min の組み合わせで「異常事態」 と decision-tree 起動、 詳細確認を skip。
  2. なぜ詳細確認を skip した? → user の不安に即応する pressure + 「fix path 提示」 の方が 「待つべき」 提案より積極的に見える bias。
  3. なぜ計算根拠を立てなかった? → fps 5-6 × n_steps 1024 × 8 envs = 8192 step / iter という SubprocVecEnv の cadence を導出せず。 PFSPCallback の per-iter log タイミングを把握してなかった。
  4. なぜ把握してなかった? → tools/train_ppo_pfsp.py の sb3 PPO `_log_interval` (= default verbose=1 で iter ごと、 つまり 22 min ごとにしか log 出ない) を再確認しなかった。 sb3 docs cross-check skip。
  5. なぜ docs cross-check を skip した? → 「Python subprocess.Popen + buffering=1 で line-by-line flush なら stdout sync するはず」 という 誤った前提 (= sb3 内部 progress bar の per-iter cadence は subprocess buffering と無関係)。
- **Root cause:** **stuck 判定 rule 不在** — stdout 沈黙のみを stuck signal に使い、 GPU util / ckpt 出力 / log file 増加 / 時刻計算 (= fps × n_steps × n_envs) の **4 面確認 routine** が未整備。
- **Pattern:** RL training / 重 batch processing で 「stdout flush タイミング = 内部 progress 同期」 と誤信、 cold start や 1st batch 収集の自然な silence を異常診断する general pattern。
- **Mitigation:**
  - 本 session で θ.5 process は kill せず alive 維持、 user paste で生存確認後 「stuck じゃなかった」 と訂正報告
  - HANDOFF-2026-05-12-pivot.md §5 で「fps 5-6、 ~45h で 1M step、 24h で ~500k step」 計算根拠明示
  - 次 session で θ.5 状態確認 cell (= nvidia-smi + pgrep + tail log + ls pool/) を user に提案する protocol を HANDOFF に保存
- **Detection signal added:** stuck 判定の **4 面確認 routine** を導入:
  1. **GPU util 計測**: `nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader` で 5 分 平均 が 0% 連続なら本物の stuck
  2. **ckpt 出力 計測**: training pool dir の `ls -t | head -3` で 新 ckpt 生成が 1 iter 想定時間の 2 倍経過しても出ないなら stuck
  3. **log file size 増加 計測**: log path を `stat -c '%s'` で 5 分 前後の delta 0 連続なら sub-process が deadlock
  4. **時刻計算**: 経過時間 vs 「fps × n_steps × n_envs / batch_size」 の理論 iter cadence、 想定の 2 倍以上経過してから stuck 判定
- **Proposed rules (require developer action):**
  1. `~/.claude/CLAUDE.md` lessons.md に追加: 「subprocess の stdout 沈黙のみで stuck 判定するな。 GPU util / ckpt 出力 / log size / 時刻計算 の 4 面確認 routine を発動。 RL training cold start や 1st batch 収集の自然な silence (= 数十分) を異常診断しない」
  2. `~/.claude/rules/agents.md` に「並列 worker / 長時間 process の stuck 判定 protocol」 を追加草案 (= developer 判断で正式 rule 昇格)
  3. 主道フレームワーク §「自動発火トリガー」 に「stuck / 止まった / hang した」 signal で `/postmortem` 自動 trigger を **発火条件 ① stuck 確証 (= 4 面確認 routine pass) ② 修復行動取る前**の二段で起動するよう refine

---
