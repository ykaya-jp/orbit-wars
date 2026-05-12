# Postmortem: build_ppo_v4_theta4_light silent load failure

> Date: 2026-05-13 02:15 JST
> Severity: HIGH (= 偽の「submit-ready」 claim を Day 4 まで 13 時間以上維持していた、 もし気付かず Day 4 で submit していたら slot 5 で 0-300 LB の事実上 0 datapoint)
> Surface time: 朝 commit `4734b87` (= 2026-05-12 10:10 JST) → 発見 2026-05-13 00:08 JST = **14 時間で気付いた**
> Related commits: `4734b87 feat(phase-beta-1)` (= 原因生成) / `1fc7cb0 fix(submit)` (= 修復)

---

## 1. Symptom (= 表面的現象)

朝の Phase β.1 完了報告で以下を claim:

- `submissions/build_ppo_v4_theta4_light/` を作成、 PPO θ.4 200k step model を 425 MB → 64.5 MB に軽量化
- `bash tools/smoke_day4.sh` で 5/5 PASS、 duration 1.4s で完走
- Day 4 slot 5 candidate (= LB 1100-1400 期待、 100 MB cap 仮説実証 + RL paradigm 1st datapoint)
- `HANDOFF-2026-05-12-pivot.md` `HANDOFF-2026-05-12-night.md` に 「submit-ready ★」 と記録

これらの claim が **fundamental に誤り** だった。 13 時間気付かれず維持された。

---

## 2. Cause (= 1 つ下のレイヤー、 直接原因)

Night session で MCTS v2 (= PPO leaf evaluator hybrid) 実装中、 PPO load を独自 path で行ったところ:

```
ModuleNotFoundError: No module named 'train_ppo'
KeyError: 'policy.optimizer'
```

調査の結果、 既存 `build_ppo_v4_theta4_light` でも同じエラーで sb3 load が **silent fail** していた:

1. `kaggle_environments.env.run(["path/main.py", ...])` は agent.py を **`exec()`** で読込、 `__file__` global は注入されない
2. `_HERE = Path(__file__).resolve().parent` で `NameError`
3. main.py の `agent = make_ppo_agent(_WEIGHTS, ...)` 行が global try (= 暗黙) で skip、 agent 関数定義は別ファイルからの import で残るが、 import 自体は `__file__` 解決後の sys.path insert に依存 = 失敗
4. agent 内部 `try: ... except Exception: return []` が runtime でも load error を silent kill
5. env は max 500 step まで NO-OP agent で進行、 timeout で DONE return = smoke PASS

---

## 3. Root cause (= 2 つ下のレイヤー、 根本原因)

### 3.1 設計レベル: silent except の連鎖

`build_ppo_lightweight.py` を作った時、 sb3 `MaskablePPO.load()` が optimizer state を必須にする仕様を knowledge 不足で見逃した。 加えて agent runtime の `try / except Exception: return []` (= Kaggle worker での crash 防止) が、 load 失敗を「実 PPO が動かない agent」 と気付かせない構造を作っていた。

```
[1] sb3 仕様 (= optimizer 必須) ←─ knowledge gap
       │
       ▼
[2] build_ppo_lightweight.py (= optimizer drop)
       │
       ▼
[3] Kaggle 環境の exec() 経由 import (= __file__ undefined)
       │
       ▼
[4] main.py の暗黙 global try (= NameError silent)
       │
       ▼
[5] agent() の try/except (= runtime error silent)
       │
       ▼
[6] env が timeout DONE return (= smoke PASS)
       │
       ▼
[7] smoke 判定 status_p0=DONE のみ (= 「動いている」 と誤判定)
```

各層単独では 「失敗時のフォールバック」 として合理的、 だが全て silent な fallback が直列で重なると **「壊れているが完走する」** 状態が **どこにも error log を残さず** 進行する。

### 3.2 プロセスレベル: 「動的スモーク必須」 の解釈不足

`~/.claude/CLAUDE.md` lessons.md「[2026-04-30] lint/tsc/test/build pass で完了報告 → 動的スモーク必須ルール」 を Kaggle agent build にも適用していた、 つもり だった。 しかし:

- 動的スモーク = 「env で完走する」 と解釈、 「agent が **意図した内部 component で** 動くこと」 までは検証していなかった
- 「PPO が実 inference してる」 を確認する手段 (= duration 増加 / `_PPO_VALUE_FN is not None` probe) を smoke 判定に含めなかった

### 3.3 体制レベル: Codex review skip

`~/.claude/rules/codex-integration.md` で「コミット前 / push 前: 自動 gate に頼る (= 手動なら `/codex:review`)」 が MUST だった。 morning pivot 完了 commit `4734b87` で Codex review gate が走ったかは未確認、 だが少なくとも私は **明示的 `/codex:review` を呼ばず** に claim 出した。 Codex 別モデルなら sb3 zip 内 optimizer 必須 を catch できた可能性。

---

## 4. Systemic gaps (= 仕組み として何が欠けていたか)

### 4.1 Smoke の合格基準が浅い

現状の smoke_day4.sh は `status_p0=DONE && duration < 60s` のみ。 必要だが不十分:

- **NO-OP agent でも DONE 完走可能** = signal とノイズ識別不能
- **build-specific expected duration** がない (= PPO load は 7-15s、 handcrafted は 1.4s、 区別なし)
- **internal state probe** がない (= agent 内部の重要 state を smoke で検査しない)

### 4.2 Silent except の警告が無い

agent module load 時の `try / except: pass` 系を audit する仕組み無し、 各 build dir で個別判断。 lint ルール (= flake8 W0718 等) で `except Exception: pass` を warn にすれば自動検知できた。

### 4.3 build artifact が git に追跡されていない

`submissions/build_*/` は朝の時点で **git untracked** だった (= 朝 commit `4734b87` は `submissions/ppo_v4_theta4_light.tar.gz` 本体のみ commit、 source 不在)。 結果、 後から audit / postmortem で「朝の build がどうだったか」 を比較できない。 night fix で `git add submissions/build_*/` を初めて実施。

### 4.4 完了 claim 前の 別モデル review が運用されていなかった

`~/.claude/rules/codex-integration.md` の MUST「コミット前 / push 前」 を実質 skip。

---

## 5. Fixes shipped (= 本 session で投入した対策)

### 5.1 build_ppo_v4_theta4_light の直接修復 (= commit `1fc7cb0`)

- `main.py`: `try: _HERE = Path(__file__) except NameError: _HERE = cwd/...` で local smoke と production tar.gz 両対応
- `ppo_inference.py`: `_weight_only_load()` で `load_from_zip_file()` → 空モデル construct → `policy.load_state_dict(strict=False)` で optimizer 完全 skip
- `train_ppo.py`: cloudpickle が pickled policy class を resolve できるよう `GridFeatureExtractor` class のみの stub module を build dir 同梱

検証: 修復後 smoke duration 1.4s → 7.1s = **PPO inference active 確認**、 vs 3x starter で 0/4 wins (= θ.4 200k step は starter にも勝てない、 LB 期待 600 圏に下方修正)。

### 5.2 build_mcts_v2 も同 pattern で実装

新規 hybrid build `submissions/build_mcts_v2/` も最初から weight-only load + `__file__` fallback + train_ppo stub を実装、 silent bug を最初から回避。

### 5.3 build dir を git tracked に

`.gitignore` で `submissions/build_*/ppo_*.zip` 等の weight zip のみ除外、 source は track。 commit `1fc7cb0` で `submissions/build_ppo_v4_theta4_light/{main.py, ppo_inference.py, train_ppo.py, orbit_wars/}` を初 add。

---

## 6. Proposed (not yet shipped)

これらは **提案のみ** で `learned/` への記録は別 session で `/postmortem` skill 経由で実施:

### 6.1 smoke の合格基準を build-aware に

`tools/smoke_day4.sh` を build 単位で expected duration を持たせる:

```bash
declare -a BUILDS=(
  "submission_v2:submissions/build_v2/main.py:expected_dur>1.0"
  "fleet_angle_zachary_v3:submissions/build_fleet_angle_zachary_v3/main.py:expected_dur<5.0"
  "ppo_v4_theta4_light:submissions/build_ppo_v4_theta4_light/main.py:expected_dur>5.0"
)
```

PPO build なら duration > 5s expected (= inference 不在なら fail)。

### 6.2 lint ルールで `except Exception: pass` を warn

`ruff` の `B902` 系 や `BLE001` を有効化、 silent except を CI block に。

### 6.3 完了 claim 前の Codex review 必須化

`/codex:review --base main` を **手動でも必ず通す** ルールを CLAUDE.md に明記。 自動 gate (= Stop hook) が走らなかった場合の保険。

### 6.4 lessons.md 昇格候補

`~/.claude/CLAUDE.md` の lessons.md に「smoke PASS = 真の機能動作」 でない の 1 行 entry を提案 (= 5 件 溜まったら昇格ルール、 親 §11.4):

> [2026-05-13] smoke PASS が「空 action でも DONE 完走」 を意味する silent bug → smoke 判定に build-aware expected duration + internal state probe を必須化。 silent except の連鎖 (= main.py global try + agent() try/except + env timeout DONE) が「壊れているが完走する」 状態を log 不在で生む

---

## 7. Lessons (= 次回以降に活かす)

1. **silent except は default で禁止**、 catch するなら必ず stderr に出す
2. **smoke の判定は build awareness を持つ** = handcrafted と PPO build で duration / step distribution の expected が違う
3. **build artifact source は最初から git tracked** = 後から比較できる
4. **完了 claim 前に別モデル review** = 同モデルの blind spot を回避
5. **「dynamic smoke 必須」 を kaggle agent にも適用する時、 「env で完走」 ではなく 「意図した内部 component が動いて完走」 まで検証する**
6. **lessons.md の rule を kaggle context に翻訳する責任** = 一般原則 → 具体ルールへの translation を skip しない

---

## 8. References

- 親 ~/.claude/CLAUDE.md lessons.md「[2026-04-30] 動的スモーク必須」「Phase β.1 silent bug」 (= 本件 入りの可能性)
- 親 ~/.claude/rules/codex-integration.md (= Codex review 必須化)
- ~/.claude/rules/development-workflow.md「動的スモーク必須ルール (CRITICAL)」
- 親 ~/projects/kaggle/CLAUDE.md §11.2「優勝本質性 5 問」 #5 「noise 範囲 submit 価値ゼロ」
- 本 repo `HANDOFF-2026-05-12-night.md` §12 「silent bug 発見 + 修復」
- commits: `4734b87 feat(phase-beta-1)` (= 原因生成) / `1fc7cb0 fix(submit)` (= 修復)
