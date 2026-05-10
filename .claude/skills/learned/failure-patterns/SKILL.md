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
