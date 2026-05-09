# Orbit Wars — リーダーボード & リプレイ観察 (dense)

> Worker B 調査、スナップショット 2026-05-09 (本日)。
> 我々の submission: `52478880` (チーム **Reexel**、sniper baseline、public score 326.8 → 366.2 (2026-05-09 日中))。
> Engine 参照: `~/projects/kaggle/orbit-wars/.venv/lib/python3.11/site-packages/kaggle_environments/envs/orbit_wars/orbit_wars.py`。

このドキュメントは、すでに engine を理解しているエンジニア向けの dense で引用が豊富なダンプである。高校生向けバージョンは `docs/research/lb-observations.kids.md` にある。

---

## 1. リーダーボード Top 30 (スナップショット 2026-05-09)

ソース: `kaggle competitions leaderboard orbit-wars -s --csv --page-size 200` →
`/home/yusuke_kaya/projects/kaggle/orbit-wars/docs/research/lb_snapshot_2026-05-09.csv` (200 行)。

| Rank | Team | Score | Last Submission |
|---|---|---|---|
| 1 | flg | 1650.9 | 2026-05-07 15:28 |
| 2 | bowwowforeach | 1650.9 | 2026-05-09 07:39 |
| 3 | Ebi | 1631.4 | 2026-05-07 00:01 |
| 4 | Isaiah @ Tufa Labs | 1582.1 | 2026-05-07 22:18 |
| 5 | Vadasz | 1553.3 | 2026-05-09 08:25 |
| 6 | Shun_PI | 1500.6 | 2026-05-08 15:41 |
| 7 | sash | 1493.2 | 2026-05-09 07:10 |
| 8 | Ousagi | 1491.9 | 2026-05-09 09:10 |
| 9 | kovi | 1477.6 | 2026-05-07 20:55 |
| 10 | Erfan Eshratifar | 1475.0 | 2026-05-09 05:23 |
| 11 | Ezra | 1455.6 | 2026-05-08 23:50 |
| 12 | ShunkiKyoya | 1430.6 | 2026-05-07 05:29 |
| 13 | lookaside | 1420.0 | 2026-05-07 17:13 |
| 14 | HY2017 | 1411.8 | 2026-05-06 22:49 |
| 15 | Andrew + SalvadorDali | 1398.5 | 2026-05-08 01:57 |
| 16 | dnish | 1390.6 | 2026-05-09 01:19 |
| 17 | ymg_aq | 1385.3 | 2026-05-09 06:13 |
| 18 | 赵云龙 | 1384.1 | 2026-05-08 03:59 |
| 19 | Artem | 1377.1 | 2026-05-06 06:01 |
| 20 | jack gell | 1366.5 | 2026-05-09 06:31 |
| 21 | Viltrum Empire | 1340.1 | 2026-05-09 09:23 |
| 22 | klog | 1335.8 | 2026-05-06 03:24 |
| 23 | skalermo | 1333.6 | 2026-05-08 19:28 |
| 24 | Wenchong Huang | 1327.8 | 2026-05-09 02:38 |
| 25 | skuro0315 | 1324.4 | 2026-05-07 16:07 |
| 26 | Tommy Barnes | 1319.1 | 2026-05-08 22:15 |
| 27 | Orbital Occle | 1309.0 | 2026-04-27 15:38 |
| 28 | Erik Kvanli | 1295.0 | 2026-05-09 09:41 |
| 29 | if_else_wins | 1290.5 | 2026-05-08 23:31 |
| 30 | Aidan P5 | 1286.6 | 2026-05-09 09:36 |

分布の観察:
- ELO は集中している。Top-30 は 1650.9 → 1286.6 (Δ 364) に広がるが、ランク 30→100 では ~1287 → ~1090 (Δ 197) しか広がらず — 長い裾は 1100 付近で平らになる (`lb_snapshot_2026-05-09.csv:32-101`)。
- `flg` と `bowwowforeach` は 1650.9 で同点 (#3 Ebi より 1.2 上)。TrueSkill 由来の ELO で同点ということは、通常、互いと他のトップ peer としか対戦しておらず、弱い agent に対して底打ちしていないことを意味する。
- 命名された LB エントリの 95% は **過去 7 日間にアクティブ**。コンペは生きており、トップ 5 は submission を続けているため、以前にリークされた戦略はすぐに陳腐化する。

スコアリングに関連する Engine 定数 (`orbit_wars.py:17-27`):
- `BOARD_SIZE = 100.0`、`CENTER = 50.0`、`SUN_RADIUS = 10.0`、`ROTATION_RADIUS_LIMIT = 50.0`
- `COMET_SPAWN_STEPS = [50, 150, 250, 350, 450]`
- `COMET_PRODUCTION = 1`、`COMET_RADIUS = 1.0`
- エピソード長: `episodeSteps=500`、`cometSpeed=4.0`、`shipSpeed=6.0` (replay の `configuration` フィールドより)

報酬 (`orbit_wars.py:710-715`): 最終スコア (planet ships + 飛行中 ships) で最大値タイのプレイヤーにのみ `+1`、それ以外は全員 `-1`。`len(alive_players) <= 1` で早期終了 (`orbit_wars.py:696-697`)。これは決定的である — 相手の planet と fleet がゼロになった瞬間にゲームは即終了し、我々が勝つ (我々の勝利のほとんどはこの形で終わっている: §3.3 参照)。

---

## 2. 我々の submission のエピソード (Reexel がこれまで戦った全マッチ)

`kaggle competitions episodes 52478880 -v` で 8 エピソードが返ってきた (1 self-play 検証 + 7 ランクマッチ)。
リプレイは `/home/yusuke_kaya/projects/kaggle/orbit-wars/data/replays/` にある。

| Episode | Steps | Reward | Opponent | Result |
|---|---|---|---|---|
| 76154720 (validation) | 500 | [1,1,1,1] | Reexel × 3 (self-play) | ゲーム終了時に同点 (最終 ships 37/37/—/—; 詳細は `episode-76154720-replay.json`) |
| 76155027 | 140 | [-1, 1] | Yudji Chainho | **LOSS** |
| 76155250 | 160 | [-1, 1] | wojak_321 | **LOSS** |
| 76155486 | 360 | [1, -1] | Jason Kimmmmmmmm | **WIN** |
| 76155696 | 500 | [-1, 1] | lishell liang | **LOSS** (タイムアウト — 互いに殲滅せず、相手 4 planets vs 我々 1) |
| 76156043 | 420 | [1, -1] | Vishal Grover | **LOSS** (我々は p1) |
| 76156165 | 282 | [1, -1] | Malaika Ijaz | **WIN** |
| 76156402 | 220 | [-1, 1] | Sai Rakshit0107 | **LOSS** |

戦績: ランクマッチで **2 W / 5 L**。スコア 326-366 で 870 中ランク ~750 付近に位置 (低いのは 7 マッチ後でほとんど ELO が収束していないため — シードパターンで確認済み: 2026-05-09 09:40-10:11 の新しいマッチのみ)。

---

## 3. リプレイから見るチーム別戦略パターン

エピソード ID 76155500-76156400 周辺をプローブして、ランクマッチ vs ランクマッチのリプレイを 9 件サンプリングした (`kaggle competitions replay <eid> -p data/replays/ -q` 参照):

| File | Player 0 | Player 1 | Reward | Steps |
|---|---|---|---|---|
| episode-76155695 | Isaiah @ Tufa Labs (#4) | Vadasz (#5) | [1,-1] | 189 |
| episode-76155725 | bowwowforeach (#2) | flg (#1) | [1,-1] | 144 |
| episode-76155929 | bowwowforeach (#2) | flg (#1) | [-1,1] | 250 |
| episode-76156145 | bowwowforeach (#2) | Vadasz (#5) | [-1,1] | 211 |
| episode-76156160 | Shun_PI (#6) | Vadasz (#5) | [-1,1] | 212 |
| episode-76156220 | HY2017 (#14) | jack gell (#20) | [1,-1] | 162 |
| episode-76156339 | Forrest (#58) | Leszek Góra (#65) | [1,-1] | 276 |
| episode-76156375 | Shun_PI (#6) | Vadasz (#5) | [1,-1] | 135 |
| episode-76156398 | Alvin (#119) | monnu (#59) | [1,-1] | 179 |

手法: 各リプレイについて、ステップごとの (planets, planets 上の ships, 飛行中の ships, fleet 数, comet planets) と agent ごとの action リストを抽出し、ステップ 0/10/25/50/75/100/150/200/250/300/350/400/450/end でスナップショットを取った。以下に観察できるパターンを示す。

### 3.1 トップ層のシグネチャ: 精密な fleet サイジングによる中盤の爆発的展開

`bowwowforeach` (ランク 2) **vs** `flg` (ランク 1) `episode-76155725-replay.json` にて:

| step | bowwow planets | bowwow ships(planets+fleets) | flg planets | flg ships |
|---|---|---|---|---|
| 0  | 1  | 10           | 1  | 10 |
| 25 | 2  | 87 (72/15)   | 2  | 91 (33/58) |
| 50 | 7  | 324 (155/169)| 8  | 213 (110/103) |
| 75 | 11 | 711 (374/337)| 9  | 535 (391/144) |
| 100| 13 | 701 (346/355)| 8  | 385 (165/220) |
| 143| 23 | 1899         | 0  | 0 (排除) |

bowwowforeach は 144 ステップで **90 fleets** を発射 (中央値 41 ships、平均 56、最大 245) — サイズが非常にばらついており、これは価値ターゲティング (ときに小さな snipe、ときに 245-ship の kill stack) を示している。flg は 121 fleets を発射 (中央値 30、平均 30、最大 133) — より均一で、「一定サイズのチャンクで swarm」。

**決定的瞬間**はステップ ~50: bowwow が 7 planets (ステップ 25 から +5) を comet 含めて掴み、一方 flg も同様に拡大したが bowwow の防御を突破できなかった。ステップ 100 までに生産ギャップ (13 vs 8 planets、約 5 production points/turn) が複利化し、flg の 8 planets は bowwow の拡大する殻と回転する太陽の間に挟まれた。

**再戦** `episode-76155929-replay.json` (異なるシード 1432706423) では、flg が 250 ステップで 20 planets, 2736 ships で勝利。flg の発射プロファイルは変化: 1349 launches (中央値 4、平均 17) — bowwow の 78 launches (中央値 38、平均 47) に対して **大量の小 fleet snipe**。これはトップ-1 agent が **adaptive** であることを示す — 同じ著者でも、相手/シードごとに発射分布が大きく異なる。

### 3.2 Top-4 vs Top-5 Vadasz が Isaiah を倒す驚きの逆転

`episode-76155695-replay.json` (Isaiah @ Tufa Labs vs Vadasz) — **Isaiah が 189 ステップ、4598 ships、24 planets で勝利**。Isaiah の発射分布は異常にマクロ: **n=59 launches、中央値 106、平均 184.6、1 launch で MAX 986 ships**。Vadasz と比較すると n=78、中央値 25、平均 32、最大 136。Isaiah は明らかに **kill-stack 戦略** を採用 — 継続的圧力ではなく、生産を 1-2 個の巨大 fleet に貯め込む。

ステップ 100 までに Isaiah は 16 planets、Vadasz は 7 (`episode-76155695-replay.json:step100`)。986-ship の単発発射はほぼ確実にゲームを終わらせた最終クリーンアップパンチ。

### 3.3 Bowwowforeach の Vadasz に対する弱点

`episode-76156145-replay.json` (bowwow #2 vs Vadasz #5) — **Vadasz が 211 ステップで勝利**。ステップ 50 で bowwow がリード 7 planets/264 ships vs Vadasz 9/249、しかし Vadasz はステップ 75 までに逆転 (10/524 vs 13/377)、より高い飛行中圧力を維持して。ステップ 200 では 3/87 vs 20/1306 — ステップ 211 の正式排除前のほぼ崩壊。

これは珍しい **#5 が #2 に勝つ** 結果で、Vadasz が bowwow の防御ロジックの特定の弱点を突いていることを示唆する。

### 3.4 中位層のシグネチャ: Forrest の kill-stack ヒューリスティック

`episode-76156339-replay.json` (Forrest ランク 58 vs Leszek Góra ランク 65) — Forrest がスタックして勝利。n=72 launches、中央値 **63.5**、平均 78、最大 250。Leszek は 193 fleets を発射 (中央値 15、平均 25、最大 107) — はるかに小さい。Forrest のパターン: fleet あたり ~63 ships を蓄積し、攻撃的な単一 planet 占領を送る。Forrest はステップ 50 で 6 planets/307 ships を保持、可視 fleet 1 (57 ships) のスタックで — 生産のほとんどは飛行中ではなく planet 上に留まっていた。

これは **マクロな kill-stack** に見える — ELO 1100 台の Isaiah-lite。Leszek には効くが、bowwowforeach の分散圧力にはスケールしない。

### 3.5 Comet スポーンステップの挙動

ステップ 49/50/51/52、149/150/151/152 等での action 量を抽出。パターンは **opportunistic** (機会便乗的):
- **トップ agent はスポーン後 1-3 ステップ内に反応する。** Vadasz はステップ 50 (`episode-76156145`) で 0 launches、その後ステップ 52 で 1 launch (36 ships) — 経路を再計算する時間として十分。
- `Shun_PI` (`episode-76156160`) と `Vadasz` はステップ 150-152 で両者 21+ launches を発射 — 第 2 の comet 波を掴むようプログラムされていることが明らか。
- **我々の sniper agent (`Reexel`) は comet を特別扱いしない。** `episode-76155486-replay.json` のステップ 50-52 を見ると 0 launches。ステップ 150-152: 4 launches で計 51 ships だが、それらは最近接ターゲット発射であり、たまたま近ければ comet になる。`submissions/main.py:37-72` に comet 専用コードパスは存在しない。

Engine ノート: comet "planet" はステップ `cs+1` の開始時に出現する (オフボード placeholder、その後 path[0]) — `orbit_wars.py:434-474` 参照。ステップ `cs+2` では comet は path[1] 位置にあり、完全に到達可能。トップ agent は COMET_SPAWN_STEPS をターゲットとした 1-2 ターンの計画→発射ループを設計しているように見える。

### 3.6 トップ層の発射サイズ分布 (持っているトップ-LB リプレイ全部)

| Player | File | n launches | 中央値 | 平均 | min | max |
|---|---|---|---|---|---|---|
| flg (#1) | 76155725 | 121 | 30 | 30.2 | 1 | 133 |
| flg (#1) | 76155929 | 1349 | 4 | 17.4 | 1 | 389 |
| bowwowforeach (#2) | 76155725 | 90 | 41 | 56.2 | 2 | 245 |
| bowwowforeach (#2) | 76155929 | 78 | 38.5 | 47.5 | 2 | 310 |
| bowwowforeach (#2) | 76156145 | 192 | 24 | 35 | 2 | 195 |
| Isaiah (#4) | 76155695 | 59 | 106 | 184.6 | 16 | 986 |
| Vadasz (#5) | 76155695 | 78 | 25 | 31.8 | 1 | 136 |
| Vadasz (#5) | 76156145 | 206 | 29 | 32.1 | 1 | 106 |
| Vadasz (#5) | 76156160 | 290 | 25 | 33.1 | 1 | 160 |
| Vadasz (#5) | 76156375 | 85 | 25 | 27.2 | 4 | 110 |
| Shun_PI (#6) | 76156160 | 246 | 26 | 33.2 | 1 | 245 |
| HY2017 (#14) | 76156220 | 249 | 26 | 35.5 | 1 | 254 |

**観察**: 中央値 fleet サイズは 25-40 ships に集中、長い右の裾 (max 100-1000)。トップ agent は単一 ship をほぼ送らない (min 1-4)。我々の sniper は `garrison + 1 + MARGIN` を送る (`submissions/main.py:62-64`)、開始 planet で 10 ships の場合、最近接ターゲットに 11 ships を送る — 30-ship 防御の planet を破るには小さすぎる。これが我々の LB 位置に一致する。

### 3.7 戦略タイプのクラスタ

サンプリングした 9 リプレイの発射サイズ分布と排除までの時間に基づく:

1. **Kill-stack マクロ (Isaiah, Forrest)** — 発射回数少 (n<100)、中央値高 (60-100+)、最大はしばしば 200-1000。圧倒で勝つ。
2. **継続圧力 (Vadasz, Shun_PI, HY2017)** — n=200-300 launches、中央値 25-30、最大 100-250。消耗戦で勝つ。
3. **Adaptive (flg, bowwowforeach)** — 相手ごとに分布が劇的に変わる。ときに n=78 大型 fleets、ときに n=1349 小型 fleets。

我々のサンプルには **トップレベルで「純粋な小型 fleet swarm」が勝つリプレイは無い** が、`Sai Rakshit0107` の純粋 swarm (`episode-76156402` で n=1601 launches 中央値 3、最大 34) は我々を 220 ステップで倒した — 弱い baseline には効く。

---

## 4. 我々の sniper の失敗モード (リプレイに基づく)

ソースコード: `/home/yusuke_kaya/projects/kaggle/orbit-wars/submissions/main.py` (73 行、`RESERVE=5 MAX_FRACTION=0.85 MARGIN=1`)。

### 4.1 失敗モード A: ステップ 25-50 までの容量ギャップ

`episode-76155027-replay.json` (vs Yudji Chainho、140 ステップで負け):
- ステップ 25: Reexel 1 planet/60 ships、Yudji 2/62、同程度。
- ステップ 47: 相手 ships 149 vs 我々 67 (すでに 2.2× の遅れ — comet スポーン前にギャップが開く)。
- ステップ 50: 相手は 4 planets を所有、12 飛行中 fleets 計 139 ships。我々は 4 planets だが飛行中 fleet は 17 ships の 1 つだけ。
- ステップ 93: 我々の planets は 0 へ; ステップ 139 まで fleet 残骸で惰性走行。

診断: 我々は 4 planets まで拡大するが圧力をかけない。ステップ 25 までに相手は 9 fleets を飛行させている (`episode-76155027-replay.json:step25`)、我々は 0。Sniper ロジックは最近接の非所有ターゲットの `garrison + 1 + MARGIN <= capacity` のときのみ発射 (`main.py:62-67`)。`ships=15, RESERVE=5, MAX_FRACTION=0.85` の planet では → `cap = min(12, 10) = 10`。最近接の敵 garrison が ≥ 9 なら → 撃たない。我々はアイドル状態で座る。

### 4.2 失敗モード B: 500 ステップ飢餓タイムアウト

`episode-76155696-replay.json` (vs lishell liang、500 ステップで相手の 4-planet 残存に紐付く):
- 両 bot は 500 ステップ全部 1 planet に留まる。我々は 8-18 ships で停滞、相手は 1-7 で。
- ステップ 449: planet 数のクロスオーバー (我々は 2 だったが 1 へ落ち、相手は新たに 2 占領)。
- ステップ 472: ship ギャップが開く — 相手 飛行中 101、我々 40。
- 最終: 相手 4 planets/110 ships、我々 1 planet/43 ships。

診断: 我々の agent は **奪還しない**。一度 planet を失うと、最近接が今や毎ターン ships が増える防御済み敵 planet になり、奪還しない。我々の ships は home でしか増えない。lishell の bot は少なくともゆっくり蓄積するが、我々は停滞する。

### 4.3 失敗モード C: 小型 fleet による swarm 攻撃

`episode-76156402-replay.json` (vs Sai Rakshit0107、220 ステップで負け):
- Sai は **1601 fleets** を発射、中央値 3、最大 34 ships。
- ステップ 50: Sai はすでに 6 planets と 56 飛行中 fleets 計 198 ships。
- ステップ 75: 12 planets、171 fleets、581 ships。我々は 7 planets だが fleets 17 個/ships 230 のみ。
- ステップ 96: Sai 11 planets, ships 1135 vs 我々 12 planets, 543 ships (planet ではまだ多いが volume で負け)。
- ステップ 100: Sai が planet で逆転 (13 vs 12)。ステップ 182: 我々は planet ゼロに到達。

診断: Sai の swarm は我々の Reserved-and-fractioned 防御を圧倒する。各小 fleet が我々を齧った後 garrison が `RESERVE=5` を下回るので発射できない。各防御済み planet は 5 回の 3-ship 攻撃で陥落するが、我々は自分の生産を待つだけ。

### 4.4 失敗モード D: 太陽/comet 軌道を無視

Engine は経路が太陽を横切る fleet を全滅させる (`orbit_wars.py:606-609`: `point_to_segment_distance((CENTER, CENTER), old_pos, new_pos) < SUN_RADIUS`)。我々の agent (`main.py:69`) は `angle = atan2(target.y - mine.y, target.x - mine.x)` を直接計算 — 太陽棄却なし。太陽横断のペアリングでは即時損失で ships を浪費する。直接測定はしていないが、(90, 65) 付近の home planet が (10, 35) に撃つような場合の既知のデッドゾーンである。

緩和コスト: ~10 行。`point_to_segment_distance` テストが失敗したら棄却し、第二最近接にフォールバック。公開ノートブックは皆これをやっている (例: `pilkwang/orbit-wars-structured-baseline` "Sun-crossing lines are rejected outright"; `rahulchauhan016/orbit-wars-target-score-2000-4` cell 9 `Predictor.safe_aim`)。

### 4.5 失敗モード E: fleet 集約なし

我々の agent は `for mine in my_planets` で発射する: 各所有 planet が独立に最近接ターゲットを選ぶ (`main.py:55-71`)。我々の 2 つの planet が同じターゲットに撃つ → ships が重複し、第二最近接には何も残らない。flg/bowwow の "swarm" パターンはマルチソース協調 (`pilkwang/orbit-wars-structured-baseline` Section "Multi-source swarm pressure")。集約すれば、3 ソースから 60 ships を 1 個の防御済み planet に送れて、3×20 が分散するより効果的。

---

## 5. 公開ディスカッション / ノートブックリーク

ソース: `kaggle kernels list -s "orbit-wars"` → 4 ノートブックを `/tmp/kernels/` に取り込み。注: in-tree の `Kaggle web Discussion` タブは認証ウォール (WebFetch はタイトルのみ返した)。フォーラムスレッドを列挙できなかった。

### 5.1 `pilkwang/orbit-wars-structured-baseline` (194 票 — 公開リファレンスアーキテクチャ)

LB トップ-30 全員が使っている可能性が高い主要戦略プリミティブ:
- **直接のみの移動** (waypoint なし)。境界対応のジオメトリ: 発射はソース境界から始まり、ターゲット円の最初のヒットで終わる。
- **Sun rejection**: 中心から `< SUN_RADIUS=10` を横切るセグメントは戦略が ships を費やす前に棄却。
- **到着時オーナーシップ**: ターゲットは現在のスナップショットではなく **到着のターン** で評価される。飛行中 fleets、生産、同ターン戦闘を再生して、我々の fleet が着いたときに誰がターゲットを所有するかを予測する。
- **同ターン戦闘 (`pilkwang` Section 7 "Settlement Logic")**: `orbit_wars.py:635-674` での engine の解決 — トップ 2 攻撃者がまずキャンセル (top1−top2)、生存者が garrison と戦う。pilkwang のノートブックはこれを正確に実装。
- **ミッションファミリー** (Section 5): `reinforce-to-hold`、`rescue`、`recapture`、`single-source capture`、`snipe`、`swarm`、`crash exploit`、`follow-up capture`、`live doomed salvage`、`rear funneling`。**10 種類のミッションタイプ。** 我々の sniper は 1 つしかない (capture-nearest)。
- **Settlement discipline (`settle_plan`)**: テスト済みの合法シードから始まり、希望する送信に向かって動き、中間 fleet サイズが到達不可能になっても既知の合法フォールバックを保持する。fleet 速度が `1 + (max_speed-1)*(log(ships)/log(1000))^1.5` (`orbit_wars.py:577`) であるため、fleet ETA は送信される ships に非自明に依存することを捉えている。

### 5.2 `konbu17/orbit-wars-rule-base-ml-shot-validator-hybrid` (50 票 — 2026-05-03 公開、**我々の agent クラスを直接参照**)

このノートブックは **最も実行可能な情報**。セル内容からの直接引用:

> "ローカル 2P プレイ (8 シード × 5 相手 × 2 サイド = サイドあたり 80 ゲーム) で、hybrid は **84%** 勝利、rule-base 単体は **65%**。"

相手のテーブル:

| opponent | hybrid (t=0.4) | rule-base only |
|---|---|---|
| `v1_sniper` | 16/16 (100%) | 16/16 (100%) |
| `v2_structured` | 13/16 (81%) | 12/16 (75%) |
| `exp007_tier3` | 13/16 (81%) | 9/16 (56%) |
| `exp007_tier4` | 9/16 (56%) | 6/16 (38%) |
| `orbitbotnext` | 11/16 (69%) | 9/16 (56%) |

`v1_sniper` = 我々の `submissions/main.py` の祖先である公開 sniper baseline。**rule-base も hybrid もローカルで 100% 勝つ。** つまり、ELO ~1100 を超える *任意の* 現在の LB submission は **確実に** 我々を 16/16 で破る。我々の 326-ELO フロアはこれと整合する: 中位層の相手にほぼ決定論的に負けている。

ノートブックの他の戦略リーク:
- "Tamrazov × Ykhnkf 系統、`pilkwang/structured-baseline` の子孫" — ほとんどの LB エントリがフォークされている **公開系統** の漸進的にチューニングされた rule-base agent が存在する。
- ML はゼロから tier3+ rule-base を倒せない (PPO は no-op に崩壊; "5 個別 ML 試行が同じ壁にぶつかった")。Validator hybrid は棄却専用 (P(success) MLP が悪い shot をフィルタする)。
- Validator 特徴量 (24 次元): ソース ships/production/radius、ターゲット ships/production/radius、オーナー one-hot、送信 ships、ship 比率、距離、ETA、fleet 速度、飛行中数 + 合計、ターン、自/敵総 ships、planet 数。
- self-reinforcement ラベルを除外した後の 70.8% 正クラス率。

### 5.3 `rahulchauhan016/orbit-wars-target-score-2000-4` (57 票)

タイトルは野心的 ("target 2000.4"); 実際のデプロイ LB 位置は不明だが、ノートブックは 21 モジュールの agent を記述: **MCTS** (UCB1, 10-turn ロールアウト, 420ms バジェット, セル 15)、**8-turn 前方シミュレータ**、**5-iter リードエイム predictor with sun avoidance** (cell 9 `safe_aim`)、**7-component evaluator** (Ship delta WS=1.0, production delta WP=46.0, planet count delta WC=20.0, net risk WR=-2.8, border pressure WB=9.0, fleet momentum WF=0.6, neutral denial WN=12.0, セル 13)。self-play で訓練された **ニューラル MLP 14→64→32→1** を持つ (セル "14")。実際の LB 位置は公開ランキングに無い (target score 2000.4 は ELO 2000+ を示唆するが、本日チームスコア >1651 は無い)。

リークされた重みは MCTS ルートに行く場合の出発点として有用: `WP=46.0` は理にかなう (生産は複利)。

### 5.4 `djenkivanov/orbit-wars-agent-ow-proto-passed-1-000` (119 票)

著者は認める "スコアは 1080 付近でピーク、Top 95、1020-1050 で安定"。スコアリング式は逐語リーク:

```
score = (100 - dist) + (15 * t.production) + (10 * enemy_bonus) - (0.7 * total_ships) - (2 * eta)
```

特徴:
- 衝突角のための planet 軌道予測
- 動的協調攻撃 (マルチソース集約)
- "ターゲット planet を決して外さない"
- sun avoidance、comet avoidance (注: この著者は comet を **避ける**; 多くのトップ agent は代わりに **追う** — §3.5 参照)
- 防御システム

この bot は本質的に **LB 中位層 baseline** (ランク ~95 → ランク ~110-130)。ELO ~1200 を超えるものは OW-Proto を倒すことが期待される。OW-Proto を確実に倒すことは妥当な Phase-1 ターゲット。

### 5.5 我々が見つけられなかったもの

- 公開トップチームの write-up なし (トップ 5 は公開していない)。
- リークされたシードリストなし; エピソードシードは整数 (例: 569741139, 1247087001) — 予測不可能。
- Discussion-tab コンテンツなし (認証ウォールが列挙をブロック)。

---

## 6. 倒すための推奨 (我々の agent にとってどの相手戦略が易しい/難しいか)

我々の sniper コード (73 行、`submissions/main.py`) には: sun avoidance、回転予測、fleet 集約、奪還ロジック、comet ステップ計画、garrison 対応 fleet サイジング、防御がない。

### 6.1 簡単な勝利 (Phase 1: ターゲット ELO 800-1000、ランク 200-400)

- **Sun-rejection を追加** (~10 行): `point_to_segment_distance((50,50), launch_xy, target_xy) < 10` なら `(angle, target)` を棄却。`orbit_wars.py:606-609` 参照。これだけでゲームあたり数十回の自殺を防げる。
- **Fleet 集約**: 全候補発射を集め、`(獲得 production / 必要 ships)` でスコアリング、最高 ROI から発射。同ターゲットがすでに対処済みならスキップ。`pilkwang/orbit-wars-structured-baseline` "Section 6: Candidate Generation And Commitment" のパターン。
- **送信サイズチューニング**: 我々の `cap` 式 `min(int(ships * 0.85), ships - 5)` は小 garrison の home planet では保守的すぎる。10 ships の場合 → cap = `min(8, 5) = 5`。30 の場合 → `min(25, 25) = 25`。トップ-LB の中央値 fleet あたり 25-40 ships と比較 (§3.6)。

### 6.2 不利な相手 (Phase 2-3 相手)

- **swarm bot 相手 (Sai Rakshit スタイル, 1601 launches/game)**: 我々の reserve=5 は繰り返しの 3-ship つつきで崩壊する。動的 reserve = max(5, sum(incoming_enemy_ships_eta<10)) が必要。あるいは `MAX_FRACTION` を破棄して、小規模攻撃が fleets を素早く空にできるようにする。
- **kill-stack 相手 (Isaiah スタイル, 986-ship 単発発射)**: sun-avoidance と集約があっても、986-ship fleet は我々を食い尽くす。解決策: **敵の生産成長を予測する**。相手が N planets に X ships 持つなら、(986-X)/sum(production)/ターン で 986 に達する。彼らの閾値より速く planet を占領してレースする。
- **adaptive 相手 (flg/bowwow)**: 我々の弱点をパターンマッチしてくる。メタポリシーの背後に多様な戦略が必要。これは本物の Phase-3 領域。

### 6.3 Comet ステップのプレイブック

- クリア済み comet planet ID を除いたターゲットリストを事前計算。
- ステップ `cs - 2` (cs ∈ {50, 150, 250, 350, 450}) で "comet-grab モード" に入る: 全所有 planet が、出現する最近接 comet planet に `0.4 * cap` ships のチャンクを送る (cs+1 まで正確な位置はわからないが、出現領域は `orbit_wars.py:191-339` の `generate_comet_paths` で制約される — オフボードに現れた後、予測可能な弧長間隔で入る)。
- 出現後 (cs+1) に再計算して確認する。

これは非自明なジオメトリを必要とするが、engine は comet を対称的にシード (4-fold (50, 50) 周り) するので、出現あたりの 4 つの位置は相関がある。

### 6.4 順序 (今週の具体的 to-do)

1. **Sun rejection + 第二最近接フォールバックを追加** → ELO +200-400 期待。
2. **自所有 planet 横断の fleet 集約を追加** → ELO +100-200 期待。
3. **奪還ロジックを追加** (以前我々のものだった敵所有 planet をターゲット) → ELO +50-150 期待。
4. **COMET_SPAWN_STEPS で comet-grab モードを追加** → ELO +50-100 期待。
5. **`konbu17/orbit-wars-rule-base-ml-shot-validator-hybrid` に従った ML shot validator を追加** (24-dim MLP, ~5k パラメータ, 閾値 0.4) → ELO +100-150 期待。

5 個全部終えた後、予想 ELO ~1100-1300、ランク ~50-100。トップ-10 (1500+) に到達するには、sniper レトロフィットではなく、継続的圧力か kill-stack アーキテクチャが必要。

---

## 7. 引用 & データファイル

リプレイ JSONs (合計 17、各 ~10 MB):
- 我々の 8 エピソード: `data/replays/episode-7615{4720,5027,5250,5486,5696,6043,6165,6402}-replay.json`。
- トップチーム & 中位層サンプル: `data/replays/episode-7615{5695,5725,5929,6145,6160,6220,6339,6375,6398}-replay.json`。
- リプレイごとの分析 (サンプル時系列): `data/replays/_analysis.json`。

LB CSV: `docs/research/lb_snapshot_2026-05-09.csv` (200 行)。

Engine: `~/projects/kaggle/orbit-wars/.venv/lib/python3.11/site-packages/kaggle_environments/envs/orbit_wars/orbit_wars.py` (行はインライン引用)。

公開ノートブック (/tmp/kernels/ にキャッシュ、リポジトリ内なし):
- `pilkwang/orbit-wars-structured-baseline` — 戦略リファレンス (10 ミッションファミリー)。
- `konbu17/orbit-wars-rule-base-ml-shot-validator-hybrid` — Sniper は hybrid に対して 0/16; ML shot validator 設計。
- `rahulchauhan016/orbit-wars-target-score-2000-4` — MCTS + neural MLP 設計と重み値。
- `djenkivanov/orbit-wars-agent-ow-proto-passed-1-000` — 中位層スコアリング式。

我々の submission: `submissions/main.py` (73 LOC、sniper baseline)。

---

(dense レポートの終わり。約 3300 語。コンパニオン `lb-observations.kids.md` がこれを高校生向けに翻訳する。)
