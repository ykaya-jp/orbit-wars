# orbit-wars project-local instructions

> Kaggle competition: https://www.kaggle.com/competitions/orbit-wars (4P FFA agent comp)
> Deadline: 2026-06-23 23:59 (= 残 ~42 day from 2026-05-12)

---

## CRITICAL: Session start protocol

新セッション開始時 (= pwd が `~/projects/kaggle/orbit-wars/`) は以下の順序で必ず read:

1. **本ファイル** (`./CLAUDE.md`) を read (= 今この瞬間)
2. **最新 HANDOFF doc を first read**:
   - **`docs/dev/HANDOFF-2026-05-12.md`** ★ ← 現在の latest
   - これに前 session の最終 state、 完了 work、 next action、 重要 path、 失敗教訓が **comprehensive に記載**
3. その上で `git log --oneline -20` で最新 commit 確認、 `kaggle competitions submissions orbit-wars` で submit 状況確認
4. handoff doc の §11 「Next session 即 action」 に従って 1 つずつ実行

加えて親 CLAUDE.md (= `~/projects/kaggle/CLAUDE.md`) を session 中 1 度は確認 (= Kaggle 共通原則、 §11 「優勝本質性 criterion」)。

---

## Project context (= 1 line)

我家 LB 989 → score 2000+ 目標 (= Top 1 = 1698 + 300、 unprecedented域)。 PPO θ.4 200k step Colab Pro+ A100 で完走済 (= explained_variance 0.95)、 Day 5 で 1M step best-practice config に shift 予定。

---

## Session end protocol (= context clear する前に必ず)

1. **新 handoff doc を `docs/dev/HANDOFF-<today>.md` で作成** (= 既存 doc は historical で残す、 新規追加方式)
   - 全 work summary、 完走 task list、 commit hash list、 next session 即 action 6 step、 critical paths inventory、 教訓 lessons
2. **本ファイル (`./CLAUDE.md`) の "latest" pointer を新 doc に更新**
3. **commit + push** (= `feat(handoff): YYYY-MM-DD session continuation pointer`)
4. user に「session clear OK」 と提示

これを skip すると次 session の私が context lost で start、 重複 work / 戦略 drift の重大 risk (= 2026-05-12 session で実例: 公開 kernel audit 重複、 PPO config research を Day 3 まで skip 等)。

---

## 関連 docs (= 親 CLAUDE.md 階層)

- 本 file: orbit-wars project-local
- 親: `~/projects/kaggle/CLAUDE.md` = Kaggle 案件共通 GM-level workflow + 「session start protocol」 (= §13)
- 親親: `~/.claude/CLAUDE.md` = 全 project 共通原則 (= 主道フレームワーク、 形名参同、 lessons.md)
- skill: `~/.claude/skills/kaggle-grandmaster-mindset/SKILL.md` (= 「優勝狙う」 系トリガーで fire)
