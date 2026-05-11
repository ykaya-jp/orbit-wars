# Remote compute 移行記録 — 2026-05-11

> **Trigger**: 2026-05-11 16:22 JST、 WSL2 (16 GB RAM + 4 GB swap) で `tools.train_ppo_pfsp` 実行中に
> OOM killer 発火 (= dmesg: `oom-kill: ... task=python3`、 1 process で virtual memory 65 GB 占有)
> **判断**: Kaggle + Colab Pro+ ハイブリッドに移行 (= 別 chat の中央 review 結論)

---

## 1. OOM 確定根拠

```
[87645.020187] oom-kill:constraint=CONSTRAINT_NONE,nodemask=(null),cpuset=init.scope,mems_allowed=0
[87645.020240] Out of memory: Killed process 2567275 (python3)
  total-vm:65079824kB, anon-rss:7021940kB, file-rss:384kB, shmem-rss:83968kB
```

- マシン total memory: 15 GiB + 4 GiB swap = 19 GiB
- 1 process で **anon-rss 7 GB + virtual 65 GB**
- 並列 PPO training 2 件 (= 100k full run + 1k smoke 再 run) 同時 → 巻き込み OOM
- WSL2 では 15 GB 上限のため、 **42M params PPO × n_envs=8 は不可能**、 n_envs=4 でも限界

## 2. 安全停止 + checkpoint inventory

- **PID 2594186** (= 50k step rerun, n_envs=4) を `kill -TERM` で graceful shutdown
- exit 143 (= SIGTERM 受領)
- `outputs/ppo_pfsp_pool_theta4/` の checkpoint:
  - `bootstrap_warmstart.zip` 518 MB (= θ.3 zip の cp、 学習進捗ゼロ)
  - save_interval=5000 未到達 (= 実 progress 2048 step = 2 iterations のみ)
- **使える weight**:
  - `agents/proxy/ppo_v3_theta3.zip` (= 既存 θ.3、 50k step training 完了)
  - これを Day 3 submit slot 3 で使う (= 既存 submissions/ppo_v3_theta3.tar.gz)
- **失った training**: 実質ゼロ (= 2 iter は学習に寄与せず)

## 3. Colab Pro+ 移行計画

| 項目 | WSL local (旧) | Colab Pro+ (新) |
|---|---|---|
| GPU | RTX 3090 24 GB (= 動くが OOM の volatile) | A100 16/40/80 GB (= 余裕) |
| CPU memory | 15 GiB (= OOM 主因) | High-RAM 51 GiB |
| 連続時間 | local 制限なしだが OOM で 30 min die | 24h 連続 (= Pro+ unlimited GPU plan) |
| 永続化 | local FS | Google Drive mount + Kaggle Dataset push |
| training 計画 | 50k step が限界 | 1M step × 5 trial 可能 (= 6 週 × 24h × 1000h budget) |

戦略影響: Lux S3 Frog Parade recipe (= 8 day × RTX 3090 = 192h) を **5 試行可能**。
前回 review の「Gold 25% / 優勝 5%」見立て上方修正候補。

## 4. Colab notebook 雛形

`notebooks/train_ppo_colab.ipynb` を作成 (= 4 cell):

1. **cell 1: repo clone** (= `git clone --depth 1` で pull-only、 sensitive secrets 含まない)
2. **cell 2: deps install** (= `pip install -r requirements-colab.txt`、 sb3-contrib + kaggle_environments)
3. **cell 3: train 起動** (= `python -m tools.train_ppo_pfsp ...`、 warm-start を Drive or Kaggle Dataset から load)
4. **cell 4: checkpoint push** (= 学習済 zip を Drive `/MyDrive/orbit-wars/ppo_v4_theta4.zip` or Kaggle Dataset version up)

## 5. bovard 50M row 解析の Kaggle Notebook 化

- WSL local では二度と回さない (= OOM 再発 risk)
- Kaggle Notebook で `+ Add data → bovard/orbit-wars-top10-episodes-*`
- 集計 SQL or polars で実行、 結果 parquet を `docs/research/<date>-bovard-aggregated.parquet` に貼る
- LB 1500+ kernel の analysis も同じく Kaggle Notebook で

## 6. 次の Colab 起動手順 (3 行要約)

1. user が Colab Pro+ ノートブック (`notebooks/train_ppo_colab.ipynb`) を Colab で開き、 cell 1-2 実行 (= repo clone + deps)
2. cell 3 で `python -m tools.train_ppo_pfsp --total-timesteps 200000 --n-envs 8 --warm-start <Drive path to ppo_v3_theta3.zip> ...` を起動 (= ~6-8 hour 想定 on A100)
3. cell 4 完了後、 学習済 zip を Drive に push → user が pull して local の `agents/proxy/ppo_v4_theta4.zip` に置く

## 7. 残 43 day の戦略 reform

- **Day 3 (5/12 09:00)**: 既存 plan のまま実行 (= 5 submit slot)、 θ.4 weight なしで進行
  - slot 構成: submission_v2 / konbu17_topk1 / ppo_v3_theta3 / lakhindar_pure / lakhindar_topk1
- **Day 4-7**: Colab で θ.4 PFSP 200k step 学習 + 平行 P3 Expansion rule 改良
- **Day 8-30**: Colab で 3-paradigm meta-agent training + iteration submit
- **Day 31-43**: polish + final 7 day freeze

## 8. 関連

- 移行前 plan: `.criteria/kaggle-orbit-wars-ppo-theta4-pfsp.yaml` (= 引き続き使用、 training 環境のみ Colab に変更)
- P1 (Day 3) plan: `.criteria/kaggle-orbit-wars-day3-submit-2026-05-12.yaml` (= 影響なし)
- P3 (Expansion rule) plan: `.criteria/kaggle-orbit-wars-expansion-rule-mission.yaml` (= local で完走可能、 small mission)
- Roadmap: `docs/strategy/2026-05-11-victory-roadmap.md`

## 9. 出典

- dmesg OOM log (= 2026-05-11 16:22 JST)
- ~/.claude/CLAUDE.md "[2026-05-10] orbit-wars" lesson (= host dataset 検証 skip lesson)
- 別 chat 中央 review (= 移行判断 + 戦略影響評価)
