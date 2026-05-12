# 最新 AI モデル の orbit-wars 攻略適用研究 (= 2026-05-12)

> orbit-wars 優勝 path 補強研究 W4
> 担当: Claude 4 / GPT-5 / Gemini 3 / DeepSeek V3 / Qwen 3 / Llama 4 / 特化 model (o3, DeepSeek-R1) の capability + orbit-wars への適用 pattern 抽出
> 知見時点: 2026-05、 残 42 day、 LB target 2000+

---

## 0. TL;DR (= 30 秒で読む結論)

- **即適用 (= 48h 以内)**: (1) Gemini 3.1 Pro の 1M context で **discussion forum 全 topic を 1-shot 要約** (W1 補完)、 (2) Codex (GPT-5.5) の review gate を **すべての rule-base agent.py 変更で必須化** (既に有効化済み、 運用徹底のみ)
- **多刀流推奨構成**: Claude Opus 4.7 (主実装、 1M context) × Codex GPT-5.5 (一次レビュアー、 sycophancy 補完) × Gemini 3.1 Pro (codebase 全体俯瞰 + multimodal replay 解析) の **3 刀流**。 DeepSeek-V3.2 / R1 は cost-sensitive な bulk synthesis (= agent.py variant 量産) で補助
- **最大 ROI 自動化**: leaderboard 1h polling + 異常検知 → Claude notify (= LB 順位変動 / top team submission パターン変化を 24/7 監視)。 wall clock 4-6h で実装可能

---

## 1. 7 model capability 比較表

> 各 score は 2026-05 時点の公開 benchmark。 "推測" は当該 model の公式公開なしで類推値。 単位なき数値は accuracy %。

| Model | context | code gen (SWE-Bench Verified / Pro) | reasoning (GPQA Diamond / ARC-AGI) | agent / tool use | weight | pricing (推測, $/Mtok in/out) |
|---|---|---|---|---|---|---|
| **Claude Opus 4.7** | 1M | **87.6 / 64.3** [1] | ~84 / ~70 (推測, 4.6 比 +) | high (本 session で実証) | proprietary | $15 / $75 |
| **Claude Sonnet 4.6** | 200K | 79.6 [1] | ~80 / ~60 (推測) | high | proprietary | $3 / $15 |
| **Claude Haiku 4.5** | 200K | 73.3 (coding avg) [1] | mid | mid-high | proprietary | $1 / $5 |
| **GPT-5.5 (OpenAI)** | 400K | **88.7 / N/A** [2] | ~85 / ~88 (推測, o3 系統承継) | high (Codex agent) | proprietary | $10 / $30 (推測) |
| **Gemini 3.1 Pro** | **1M** (+1M output 65K) | ~80 (推測) / N/A | ~82 / **MMMU-Pro 81.0** [3] | high (Vertex agent) | proprietary | $1.25 / $10 (推測) |
| **DeepSeek-V3.2** | 128K | ~75 (推測) [4] | ~76 / ~55 (推測) | mid (R1 distill 経由で reasoning 強化) | **open-weight (MIT 系)** | self-host = compute cost のみ |
| **Qwen 3.6-27B** | 1M (Plus) | **77.2** (Qwen3.6-27B) [5] | mid | **high (TAU3-Bench top, MCPMark lead)** [5] | **open-weight** | self-host |
| **Llama 4 Scout / Maverick** | **10M (Scout)** [6] | 43.4 (LiveCodeBench, Maverick) [6] | mid | mid | **open-weight** | self-host |
| **o3 (OpenAI)** | 200K | N/A (reasoning 特化) | **87.7 / 96.7 (high-compute)** [7] | mid (tool 連携限定) | proprietary | high (推測 $60+/Mtok out) |
| **DeepSeek-R1** | 128K | N/A | 71.5 / N/A [7] | mid | **open-weight** | self-host (o3 比 1/18 cost) [7] |

凡例: high = orbit-wars agent / Kaggle 用途に十分、 mid = 補助用途、 N/A = 該当 benchmark 公開なし。

---

## 2. 各 model の orbit-wars 適用 pattern

各項目は **強み / orbit-wars 適用 / 出典** の 3 行構成。 適用 pattern は本研究の 5 観点 (rule-base agent コード生成 / PPO advisor / forum 要約 / 数理助手 / code review) に対する fit を明記。

### 2.1 Claude Opus 4.7 (= 現主力、 1M context)

- **強み**: SWE-Bench Verified 87.6 / Pro 64.3 で 2026-05 時点 #1。 1M context により orbit-wars repo (= engine + agent + replays + research docs) を 1-shot 投入可能。 主体性高くツール使用熟達 [1]
- **orbit-wars 適用**:
  - (◎) **rule-base agent コード生成**: 既存 agent.py + replay 解析 + strategy md を 1-shot 投入 → 「step 100 で 5 planets 確保する expansion mission を書け」 が context-rich に通る (これは現に本 session の運用)
  - (◎) **code review**: PPO training loop、 reward shaping 周りの logic bug を call chain top-to-bottom で見る [8]
  - (◎) **数理助手**: PFSP / Nash の数式解説、 Markov chain 定常分布の手計算
  - (△) **forum 要約**: 単発要約は可能だが 1M context fit を Gemini 3.1 Pro の方が単価で大きく上回る (推測 $15 vs $1.25 / Mtok)
- **出典**: [1] https://www.vellum.ai/blog/claude-opus-4-7-benchmarks-explained, https://www.morphllm.com/claude-benchmarks

### 2.2 Claude Sonnet 4.6 / Haiku 4.5 (= cost 効率帯)

- **強み**: Sonnet 4.6 が SWE-Bench 79.6 で 2026-02 時点トップ級、 Haiku 4.5 は coding 73.3 で 価格当たり最強級 [1]
- **orbit-wars 適用**:
  - (○) **Haiku 4.5 で agent.py variant 量産**: 「Reexel ベースに reward shaping 変えただけの 10 variant 出せ」 を Haiku で並列実行 → 全部 submit テスト。 Opus 単価の 1/15 で済む
  - (○) **Sonnet で nightly EDA**: replay 解析 notebook を回す等の中量タスク
- **出典**: [1] https://www.morphllm.com/claude-benchmarks, https://www.remoteopenclaw.com/blog/best-claude-models-2026

### 2.3 GPT-5.5 (= Codex 経由で既に統合済み)

- **強み**: SWE-Bench Verified **88.7 で 2026-05 #1** [2]。 OpenAI 公式 `codex-plugin-cc` で Claude Code から呼べる。 別 model 系統のため Claude の sycophancy bias を補完 [8]
- **orbit-wars 適用**:
  - (◎) **一次 code review (= 現運用)**: Stop hook gate で turn 毎自動レビュー、 `BLOCK:<reason>` で Claude が修正へ戻る (~/.claude/rules/codex-integration.md 既定)
  - (◎) **adversarial review**: `/codex:adversarial-review "challenge whether reward shaping <X> is correct"` で reward hacking の盲点を炙る
  - (○) **security-sensitive な変更時のレビュー** (= 本 comp では submission credential 管理くらいだが)
- **出典**: [2] https://openai.com/index/introducing-gpt-5-5/, https://www.marc0.dev/en/leaderboard, [8] https://milvus.io/blog/ai-code-review-gets-better-when-models-debate-claude-vs-gemini-vs-codex-vs-qwen-vs-minimax.md

### 2.4 Gemini 3.1 Pro (= 1M context + multimodal + 低単価)

- **強み**: 1M context (Claude Opus と同等) + **multimodal で video / image を取れる**、 MMMU-Pro 81.0 で GPT-5.1 を 5 pt 上回る [3]。 Video-MMMU 87.6 で **replay の動画解析が可能** [3]。 推測 単価で Claude Opus の 1/10
- **orbit-wars 適用**:
  - (◎) **discussion forum 全 topic 1-shot 要約**: `kaggle competitions topic-messages` 出力を全部投入 → 日次 summary を生成。 単価で Claude より圧倒的有利
  - (○) **replay の multimodal 解析**: kaggle_environments の render 動画を Gemini に直接見せ 「Top1 と Reexel の expansion pattern の違いを述べよ」 を文字通り視覚で問える。 これは Claude / GPT では現状不可
  - (○) **monorepo 全体俯瞰の design review**: 1M context で orbit-wars repo 全体を 1-shot 読み 「reward 設計の構造的欠陥はあるか」 を別視点で
- **出典**: [3] https://deepmind.google/models/model-cards/gemini-3-1-pro/, https://www.vellum.ai/blog/google-gemini-3-benchmarks

### 2.5 DeepSeek-V3.2 (= open-weight、 program synthesis)

- **強み**: 671B MoE (37B active)、 R1 reasoning を V3 へ distill 済みで program synthesis 強い、 多言語 issue resolution 環境で RL 訓練済み (1827 envs / 4417 tasks) [4]。 self-host で **submit 件数 cost ゼロ** が最大 ROI
- **orbit-wars 適用**:
  - (○) **agent.py variant の大量並列生成**: self-host で night cycle に「Reexel ベース × reward shaping 10 種 × strategy 5 種 = 50 variant」 を一晩生成。 Claude / GPT の API cost を回避
  - (△) **code review**: SWE-Bench score が Opus 4.7 / GPT-5.5 に劣るため一次レビュアー向きではない
- **出典**: [4] https://arxiv.org/pdf/2512.02556, https://magazine.sebastianraschka.com/p/technical-deepseek

### 2.6 Qwen 3.6 (= agent / tool-use 特化)

- **強み**: Qwen3.6-27B が SWE-Bench Verified **77.2** (Claude 4.5 Opus 級)、 Terminal-Bench 2.0 **59.3**、 **TAU3-Bench / MCPMark / MCP-Atlas で top** [5]。 1M context (Plus)。 open-weight
- **orbit-wars 適用**:
  - (○) **MCP 経由の Kaggle 自動化 agent**: kaggle CLI を MCP 化して Qwen agent に「leaderboard 監視 + submission 自動投下」 を委譲。 agent / tool-use 特化のため安定動作期待
  - (△) **rule-base agent コード生成**: Opus 4.7 / GPT-5.5 に劣るため主用途には推奨しない
- **出典**: [5] https://www.marktechpost.com/2026/04/22/alibaba-qwen-team-releases-qwen3-6-27b-a-dense-open-weight-model-outperforming-397b-moe-on-agentic-coding-benchmarks/, https://qwen.ai/blog?id=qwen3-coder-next

### 2.7 Llama 4 Scout / Maverick (= 10M context、 multimodal、 open-weight)

- **強み**: Scout で **10M context** [6]、 Maverick で multimodal 強い。 open-weight で self-host 可
- **弱み**: SWE-Bench Verified / LiveCodeBench で DeepSeek-V4 / Qwen 3.6 に明確に劣る [6]
- **orbit-wars 適用**:
  - (△) **10M context で全 replay history (= 数千 game) を 1-shot 解析**: 唯一無二の context size。 ただし code gen 弱いため 「pattern 抽出 → 日本語 summary」 までで止める前提
  - (×) rule-base agent コード生成 / code review には不向き
- **出典**: [6] https://codersera.com/blog/llama-4-complete-guide-2026/, https://ai.meta.com/blog/llama-4-multimodal-intelligence/

### 2.8 特化 model (= o3 / DeepSeek-R1)

- **o3 強み**: GPQA Diamond **87.7**、 ARC-AGI **96.7 (high-compute)** で reasoning #1 [7]
- **DeepSeek-R1 強み**: GPQA 71.5 と o3 に劣るが **cost 1/18** [7]、 open-weight
- **orbit-wars 適用**:
  - (○) **Nash equilibrium / Markov chain / PFSP の証明的問題**: 「self-play で transitive cycle が壊れる条件を formal に示せ」 を o3 に投げる。 Claude では reasoning depth 不足な可能性
  - (○) **DeepSeek-R1 で nightly batch reasoning**: 「直近 100 game の負け方を 5 cluster に分類しろ」 を cost を気にせず投げる
- **出典**: [7] https://arcprize.org/leaderboard, https://www.meta-intelligence.tech/en/insight-reasoning-models

---

## 3. 多刀流戦略 (= 3+ model 並用)

### 3.1 現運用 (= Claude + Codex 二刀流) の評価

- **現状**: Claude Opus 4.7 = 主実装、 Codex (GPT-5.5) = Stop hook gate での自動一次レビュー (~/.claude/rules/codex-integration.md)
- **判定**: **best practice として継続**。 別 model 系統が sycophancy bias を補完する事実は 2026 多モデル debate 研究で確証されている [8] (= 5 round adversarial debate で bug detection 80%、 system-level bug 100%)。 JetBrains 2026-01 survey で Claude Code 採用 18% / NPS 54 で最高水準 [9]
- **改善余地**: 二刀流は **同質的 challenge** に弱い。 設計判断レベル (= reward shaping 方針、 PPO vs rule-base の選択) で第 3 視点を入れる ROI が高い

### 3.2 推奨 3 刀流構成 (= orbit-wars 残 42 day 向け)

| Role | Model | 用途 | 単価優先度 |
|---|---|---|---|
| **主実装** | Claude Opus 4.7 | rule-base agent / PPO training code 実装、 数理導出、 docs 生成 | high |
| **一次レビュアー** | GPT-5.5 (Codex) | 既存 Stop hook gate で turn 毎自動。 adversarial-review は手動で security-sensitive 変更時 | high |
| **第 3 視点 / forum / multimodal** | Gemini 3.1 Pro | discussion forum 全 topic 日次要約、 replay 動画解析、 monorepo 全体 design review | high (低単価で常用可) |

### 3.3 4 刀流以上 (= bulk synthesis 帯)

| 追加 Role | Model | 用途 |
|---|---|---|
| **agent.py variant 量産** | DeepSeek-V3.2 (self-host) または Haiku 4.5 | 「Reexel ベースで reward 10 種 × strategy 5 種 = 50 variant」 を night batch で生成、 全部 submit |
| **reasoning 特化** | o3 | Nash / PFSP / Markov chain の formal 問題、 「shake-up を起こす structural condition は何か」 |
| **agent / MCP** | Qwen 3.6-27B | kaggle CLI を MCP 化して 「leaderboard 1h polling + 異常検知 + Claude notify」 を委譲 |

### 3.4 多モデル debate の ROI (= 同問題に複数 model 並列投入)

- **エビデンス**: 多モデル adversarial debate で bug detection +30% [8]、 5 round 後 80% / 最難 bug 100% 検出
- **orbit-wars での適用**: **設計判断レベル (= reward shaping の方向性、 self-play 相手 pool 構成) で 3 model 並列投入が ROI 最大**。 実装レベル (= 1 関数 30 行) には oversized
- **運用 cost**: Claude 主実装 + Gemini 第 3 視点だけで多くの設計判断はカバー可。 4-5 model 並列 debate は week scale の戦略判断に限定 (= 残 42 day で 2-3 回が現実的)
- **出典**: [8] https://milvus.io/blog/ai-code-review-gets-better-when-models-debate-claude-vs-gemini-vs-codex-vs-qwen-vs-minimax.md

---

## 4. 自動化 pattern 5 件 (= ROI 順)

ROI = (orbit-wars LB 押上げ効果 × 着手容易度) / (実装 cost)。 単位は wall clock 推定。

### 4.1 [最 ROI / 48h 以内に着手] 24/7 LB monitor + 異常検知 → Claude notify

- **仕組み**: cron で 1h ごと `kaggle competitions submissions` + `kaggle competitions leaderboard` を取得、 前回 snapshot と diff → (a) 自分の順位が 5 位以上変動、 (b) top 10 team が新 submission、 のいずれかで Slack / desktop notify。 Gemini 3.1 Pro (低単価) で 「直近 1h の LB 変化を 3 行で要約」 を添える
- **orbit-wars 効果**: top team の submission timing は **戦略変更の signal**。 残 42 day で 1 日も早く検知 → counter 戦略を Claude に投げ込める
- **実装 cost**: bash + python 50 行 + cron 1 entry。 wall clock **4-6h**
- **出典**: kaggle CLI 標準機能 (https://github.com/Kaggle/kaggle-api)、 lessons 「Kaggle agent comp で host dataset 検証 skip → 17% 勝率失敗」 (~/.claude/CLAUDE.md 2026-05-10) の data-first 原則を運用 layer に拡張

### 4.2 [高 ROI / 1 week 以内] discussion forum auto-summarize (Gemini 3.1 Pro 日次)

- **仕組み**: cron で `kaggle competitions topic-messages -c orbit-wars` 取得 → Gemini 3.1 Pro 1M context に全 topic 投入 → 「過去 24h で hint 価値あった top 5 message と理由」 を docs/discussion/<TODAY>.md に append
- **orbit-wars 効果**: discussion は **top team が漏らす hint の最大 source**。 手動巡回は cost 高、 1M context で 1-shot 要約が best fit
- **実装 cost**: 既存 ~/.claude/skills/kaggle-onboard/templates/prompts/ 流用可。 wall clock **3-4h**
- **出典**: [3] https://deepmind.google/models/model-cards/gemini-3-1-pro/、 kaggle-onboard skill (~/.claude/skills/kaggle-onboard/SKILL.md)

### 4.3 [中 ROI / 1 week 以内] agent.py variant batch generator (Haiku 4.5 / DeepSeek-V3.2)

- **仕組み**: 既存 agent (Reexel / v2 等) を seed に、 reward shaping / expansion mission の 10-50 variant を Haiku 4.5 で並列生成 → 自動で local arena (= kaggle_environments self-play) で勝率測定 → top 3 を submit
- **orbit-wars 効果**: 「人手で 1 個ずつ書く」 を 「機械で 50 個書き勝率で選別」 に変える。 残 42 day で submission slot 5/day をフル活用
- **実装 cost**: agent template + variant prompt + local arena runner。 wall clock **1-2 day**
- **出典**: NVIDIA Kaggle 優勝 (= 600K 行 / 850 実験 / GPT-5.4 + Gemini 3.1 Pro + Claude Opus 4.6) [10]

### 4.4 [中 ROI / 設計判断時のみ] 3 model 並列 adversarial debate

- **仕組み**: 大きな設計判断 (= 「PPO に切替か rule-base 継続か」、 「reward shaping の方向性」) を Claude / GPT-5.5 / Gemini に同時投入 → 各 model の論点を Claude に集約させ最終判断は開発者
- **orbit-wars 効果**: 残 42 day で 2-3 回の戦略判断 (= 例えば day 14 / day 28 で方針見直し) で活用。 単発実装には oversized
- **実装 cost**: 手動運用で十分。 wall clock 1 判断あたり **2-3h**
- **出典**: [8] milvus.io 多モデル debate 研究

### 4.5 [低-中 ROI / 余裕あれば] replay multimodal 解析 (Gemini 3.1 Pro Video)

- **仕組み**: kaggle_environments の `render(mode='html')` 出力を動画化 → Gemini に 「Top1 と自分の expansion timing 差を視覚的に述べよ」 を投げる
- **orbit-wars 効果**: 数値解析では拾えない 「空間配置の癖」 (= 序盤 cluster vs 分散) を視覚抽出。 ただし numeric replay 解析で多くが代替可能
- **実装 cost**: render → mp4 化 (ffmpeg) + Gemini API 呼出。 wall clock **6-8h**
- **出典**: [3] https://deepmind.google/models/model-cards/gemini-3-1-pro/ (Video-MMMU 87.6)

---

## 5. 我家への直接 適用 推奨 (= 即着手すべき 3 件)

優先順位 = 残 42 day での LB 押上げ期待値 × 着手容易度。

### 推奨 1: Gemini 3.1 Pro による discussion forum 日次要約 (= 4.2、 wall clock 3-4h)

- **理由**: orbit-wars の hint 価値は forum が最大、 1M context は Gemini が単価で圧倒、 既存 kaggle-onboard skill prompt を流用可
- **着手手順**:
  1. Gemini API key 取得 (~/.claude/settings.json に env 追加)
  2. `~/.claude/skills/kaggle-onboard/templates/prompts/forum-summary.md` を作成 (Gemini 専用 prompt)
  3. cron で日次 `docs/discussion/<TODAY>.md` に append
- **検証手段**: 1 日回して 「翌日読んで戦略変更につながる hint があるか」 を開発者が判定

### 推奨 2: 24/7 LB monitor + 異常検知 → notify (= 4.1、 wall clock 4-6h)

- **理由**: top team の submission timing 検知が遅れると counter 戦略が後手。 残 42 day で 1 日 = 2.4% の時間損失
- **着手手順**:
  1. `scripts/lb_monitor.sh` (= kaggle CLI + jq + diff)
  2. cron で 1h ごと、 異常時のみ desktop-notify + Slack
  3. Gemini で 「直近 1h の変化を 3 行要約」 を notify body に
- **検証手段**: 1 週間運用して 「top team submission 検知 latency が 1h 以内か」 を確認

### 推奨 3: agent.py variant batch generator (= 4.3、 wall clock 1-2 day)

- **理由**: submission slot 5/day をフル活用するには手動量産が間に合わない。 Haiku 4.5 単価で 50 variant / night が現実的
- **着手手順**:
  1. 既存 agent (Reexel v2 系列) を template 化
  2. variant prompt template (= reward shaping / expansion mission / combat policy の 3 軸 × 各 5 値)
  3. local arena runner (= kaggle_environments self-play で勝率測定) → top 3 を submit
- **検証手段**: 1 night cycle で勝率測定し、 自前 baseline を上回る variant が 1 個以上出るか

### 推奨しない (= ROI 不足 or 既達)

- Codex review gate 強化 → 既に有効化済み (~/.claude/rules/codex-integration.md 2026-05-07)
- Llama 4 self-host → SWE-Bench 弱く orbit-wars 用途で出番なし
- o3 常用 → cost 高、 数理問題スポット利用に限定

---

## 6. 出典 (= 全件 URL)

1. https://www.vellum.ai/blog/claude-opus-4-7-benchmarks-explained
2. https://www.morphllm.com/claude-benchmarks
3. https://codersera.com/blog/claude-opus-4-7-complete-guide-2026/
4. https://www.remoteopenclaw.com/blog/best-claude-models-2026
5. https://openai.com/index/introducing-gpt-5-5/
6. https://www.marc0.dev/en/leaderboard
7. https://benchlm.ai/models/gpt-5-5
8. https://deepmind.google/models/model-cards/gemini-3-1-pro/
9. https://www.vellum.ai/blog/google-gemini-3-benchmarks
10. https://blog.google/products-and-platforms/products/gemini/gemini-3/
11. https://arxiv.org/pdf/2512.02556 (DeepSeek-V3.2 Technical Report)
12. https://magazine.sebastianraschka.com/p/technical-deepseek
13. https://github.com/deepseek-ai/deepseek-v3
14. https://www.marktechpost.com/2026/04/22/alibaba-qwen-team-releases-qwen3-6-27b-a-dense-open-weight-model-outperforming-397b-moe-on-agentic-coding-benchmarks/
15. https://qwen.ai/blog?id=qwen3-coder-next
16. https://www.alibabacloud.com/blog/qwen3-6-plus-towards-real-world-agents_603005
17. https://codersera.com/blog/llama-4-complete-guide-2026/
18. https://ai.meta.com/blog/llama-4-multimodal-intelligence/
19. https://arcprize.org/leaderboard
20. https://arcprize.org/blog/r1-zero-r1-results-analysis
21. https://www.meta-intelligence.tech/en/insight-reasoning-models
22. https://www.helicone.ai/blog/openai-o3
23. https://milvus.io/blog/ai-code-review-gets-better-when-models-debate-claude-vs-gemini-vs-codex-vs-qwen-vs-minimax.md
24. https://chandlernguyen.com/blog/2026/03/13/codex-gpt-5-4-vs-claude-code-opus-4-6-dual-wielding-ai-coding-tools/
25. https://smartscope.blog/en/blog/claude-code-codex-review-loop-automation-2026/
26. https://github.com/openai/codex-plugin-cc
27. https://developer.nvidia.com/blog/winning-a-kaggle-competition-with-generative-ai-assisted-coding/
28. https://blog.dailydoseofds.com/p/how-top-ai-labs-are-building-rl-agents
29. https://aclanthology.org/2026.findings-eacl.328/ (Turn-PPO)
30. https://arxiv.org/pdf/2410.07095 (mle-bench)

参照 reference index (= 本文中の `[N]` 対応):
- [1] = (1)(2)(4)
- [2] = (5)(6)
- [3] = (8)(9)
- [4] = (11)(12)(13)
- [5] = (14)(15)(16)
- [6] = (17)(18)
- [7] = (19)(20)(21)(22)
- [8] = (23)(24)(25)
- [9] = JetBrains 2026-01 survey (出典 https://teamai.com/blog/ai-automation/best-ai-models-for-coding-and-agentic-workflows-2026/)
- [10] = (27)

---

## 7. 推測 と 確認 の区別 (= ~/.claude/CLAUDE.md "Links, not verdicts" 準拠)

| 項目 | 確認済 (= 1 次 source あり) | 推測 (= 根拠示) |
|---|---|---|
| SWE-Bench score | Opus 4.7 = 87.6 [1]、 GPT-5.5 = 88.7 [2]、 Qwen3.6-27B = 77.2 [5]、 Maverick = 43.4 [6] | Gemini 3.1 Pro = ~80 (= Vellum 概況 + Codersera 比較から類推) |
| pricing | Opus 4.7 = $15/$75、 Sonnet 4.6 = $3/$15、 Haiku 4.5 = $1/$5 (Anthropic 公式) | GPT-5.5 / Gemini 3.1 Pro 単価は 2026-05 時点で variation あり、 推測値 |
| MCP / TAU3-Bench top | Qwen 3.6-Plus [5] | - |
| 多モデル debate +30% bug detection | milvus.io 実測 [8] | - |
| Codex plugin review gate 効果 | OpenAI 公式 plugin [26]、 chandlernguyen 検証 [24] | - |
| NVIDIA Kaggle 優勝 600K 行 | NVIDIA blog [27] | 「3 LLM 並用」 の効果が orbit-wars (agent comp、 異 problem 構造) にどれだけ移植可能かは推測。 適用は本研究 §4.3 で限定的に提案 |
| Llama 4 Scout 10M context | Meta 公式 [18] | code gen 弱は SWE-Bench 公開なし時点で類推、 orbit-wars 用途で 「推奨しない」 判定 |

---

## 8. 次 step (= W4 完了後の連携)

- 本 doc は **W4 (LLM augmentation)** 単独完結。 W1 (forum mining) / W2 (replay analysis) / W3 (past comp lessons) との接続点:
  - W1 forum mining → 推奨 1 (Gemini 日次要約) で実装 layer 化
  - W2 replay analysis → 4.5 (replay multimodal) と 4.3 (variant batch + local arena) で 自動化
  - W3 past comp lessons → 3 刀流 debate で 「Halite II / Lux S3 と orbit-wars の構造差」 を 3 model に問う
- **plan 着手前提**: 本研究の推奨 1-3 は `/plan kaggle-orbit-wars-llm-automation` で .criteria/<task-id>.yaml を生成してから実装に入る (~/.claude/CLAUDE.md "形名参同")
