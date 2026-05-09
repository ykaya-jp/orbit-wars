# Orbit Wars: トッププレイヤーは何をしているのか (高校生版)

こんにちは！ これは `lb-observations.dense.md` のフレンドリー版です。中身の事実は同じで、エンジニア用語を減らしてあります。

まだ Orbit Wars をやったことが無い場合、ざっくり説明すると: 2 人プレイのリアルタイム戦略ゲームで、各プレイヤーは 1 つの母星 (home planet) を持ち、毎ターン宇宙船 (ships) を獲得し、相手の planets を占領しようとします。盤面は 100 × 100 で、中央には太陽があり、太陽を通り抜ける ships は破壊されます。決まったターン (50, 150, 250, 350, 450) でランダムな「彗星 planets (comet planets)」が出現します — ゲーム途中に湧く無料の不動産みたいなものです。

私たちの bot の名前は **Reexel** (基本的な「最近接の planet を撃つ」戦略で動いてます)。Kaggle にはもっと賢い bot を書いてる人たちがたくさんいます。このドキュメントでは彼らが何をやってるかを説明します。

---

## 1. リーダーボードはどう見えるか？

リーダーボードはチェスの Elo レーティングみたいなものだと思ってください: 勝つと上がって、負けると下がる数字。チェスでは、ビギナーは ~800、クラブプレイヤーは ~1500、マスターは ~2200。Orbit Wars では今 (2026-05-09):

| Rank | Team | "スキル評点" |
|---|---|---|
| 1 | flg | 1650.9 |
| 2 | bowwowforeach | 1650.9 |
| 3 | Ebi | 1631.4 |
| 4 | Isaiah @ Tufa Labs | 1582.1 |
| 5 | Vadasz | 1553.3 |
| ... | ... | ... |
| 30 | Aidan P5 | 1286.6 |
| 100 | Álvaro | 1094.1 |

私たち (Reexel) は **300-360** あたりで、かなり低いです。なぜか？ ランクマッチを 7 試合しかやってなくて、ほとんど負けたから (詳しくは下で)。

**重要:** トップ-30 のチームは毎日新しいバージョンを submit し続けています。コンペは生きていて、先週効いた戦略は今週効かないかもしれません。

完全な top-200 はスプレッドシートとして `docs/research/lb_snapshot_2026-05-09.csv` に保存しています。

---

## 2. 私たちの bot はどう戦った？

ランクマッチを 7 試合プレイ。2 勝 5 敗。

```
Episode ID    Opponent           Result    Steps
76155027      Yudji Chainho      LOSS      140
76155250      wojak_321          LOSS      160
76155486      Jason Kimmmmmmmm   WIN       360  <- やった
76155696      lishell liang      LOSS      500  <- 時間切れ
76156043      Vishal Grover      LOSS      420
76156165      Malaika Ijaz       WIN       282  <- やった
76156402      Sai Rakshit0107    LOSS      220
```

各ゲームは `data/replays/episode-<ID>-replay.json` にあります。これらは大きな JSON ファイル (各 約 10 MB) で、毎ターンの全 planets、全 ships、各プレイヤーが何をしたかが記録されています。

---

## 3. トップ層の試合はどんな感じ？

上位ランク同士のゲームをダウンロードしました。一例: ランク-2 (`bowwowforeach`) vs ランク-1 (`flg`)、ファイル `data/replays/episode-76155725-replay.json`。

弱火でじっくり煮込む鍋を想像してください。ターン 0 で各プレイヤーは 10 ships の 1 planet を持ちます。ターン 25 までに、各自 2 planets を所有し、合計 ~80-90 ships。試合は静か。

そしてターン 50 が来る — **comet 波** が無料の comet planets 4 つを盤に落とす (これはターン 50, 150, 250, 350, 450 で起きる)。両プレイヤーは狂ったように planets を掴む:

```
       所有 planets      Ships (planet 上 + 飛行中)
turn 0:    1 vs 1         10  vs  10
turn 25:   2 vs 2         87  vs  91
turn 50:   7 vs 8        324  vs 213    <- comet 確保
turn 75:  11 vs 9        711  vs 535
turn 100: 13 vs 8        701  vs 385
turn 143: 23 vs 0       1899  vs   0    <- bowwow が勝つ
```

ターン 143 で `flg` の planets はゼロ — ゲームオーバー。`bowwowforeach` の勝ち。

**パターン:** トップのプレイヤーはターン 25 からターン 75 の間に planet 数を 3 倍にする、comet planets と中立 planets を積極的に掴むことで。それ以降、生産ギャップ (planet が多い = ターンあたりの ships が多い) が複利で効いて、片方がもう片方を干上がらせる。

良い例えにすると、トップのプレイヤーはビリヤードの達人みたいで、目の前のボールをポケットに入れるだけでなく、**次のショットの位置取り** までしている。彼らはいつも 2-3 ターン先を考えている。

### 彼らの fleets はどれくらい大きい？

自分の planet から ships を発射するときは、何隻送るかを選びます。トップのプレイヤーはとても選り好みします:

| Player | 発射回数 | 典型的なサイズ | これまでの最大 |
|---|---|---|---|
| flg (#1) | 121 回 | 30 ships | 133 ships |
| bowwowforeach (#2) | 90 回 | 41 ships | 245 ships |
| Isaiah (#4) | 59 回 | **106 ships** | **986 ships!** |
| Vadasz (#5) | 78 回 | 25 ships | 136 ships |
| Forrest (#58) | 72 回 | 64 ships | 250 ships |

Isaiah の bot は面白い — 発射回数は少ないが、**ずっと大きい** fleets を送る (1 回の発射で max 986 ships!)。1 年分のお小遣いを貯めて 1 個のメガアイテムを買うイメージ。それが Isaiah の戦略。

flg と bowwowforeach はもっと多くの fleets を送るが、状況に合わせてサイズを調整する。ときに 4 ships (小さな "snipe")、ときに 245 ships ("kill stack")。彼らは適応する。

私たちの bot? 私たちは常に `garrison + 2` を送る。なので私たちの planet が 10 ships を持って、ターゲットが 8 を持っているなら、9 を送る。ターゲットが買える限度より大きいなら、撃たずに座り続ける。**それが負ける理由です。**

---

## 4. なぜ私たちは負けているのか？

私たちの bot のコードは全部で 73 行 (`submissions/main.py`)。毎ターンこれをやる:

```
自分の所有する各 planet について:
  最近接の非フレンドリーな planet を見つける
  ぎりぎり占領できるだけの ships があれば: 撃つ
  そうでなければ: 何もしない
```

それだけ。Sun-dodging なし。チーム攻撃なし (3 つの planet からの 1 大型攻撃)。Comet 計画なし。失った planets の取り戻しなし。

実際のゲームでの 5 通りの死に方:

### 失敗 A: 序盤で遅れて二度と追いつけない

vs Yudji Chainho、ターン 25: 私たちは 60 ships の 1 planet、Yudji は 62 ships の 2 planets と、**すでに 9 fleets を飛行中**。私たちの飛行中 fleets が 0 ということは、ships が planets に座ったまま、誰にも圧力をかけていない。ターン 47 までに私たちは 67 ships、Yudji は 149。ターン 140 でゲームオーバー。

**例え**: 片方のチームが試合中ずっとディフェンスして 1 度もシュートしないピックアップバスケットボール試合を想像してください。ボールが常に自陣にあるから負ける。

### 失敗 B: 500 ステップ飢餓

vs lishell liang、500 ターン: どちらの bot もあまり掴まない。私たちは 1 planet で停滞、相手も 1 planet、最後に 4 へ。ターン 500 でエンジンが ships を数えると、彼らは 110、私たちは 43、で負け。

私たちは失った planets を奪還しない。一度 planet が敵のものになると、私たちの「最近接を撃つ」は ships が多すぎる敵 planet を見つけて、撃たないと判断する。永遠に。

**例え**: 凍ったポンドのホッケー試合で、両プレイヤーが自分のゴールだけを守る。ブザーが鳴ったときに少しでもパックが多い方が勝つ。

### 失敗 C: 千の紙の切り傷で死ぬ

vs Sai Rakshit0107、220 ターン: Sai は **1601 個の小 fleets** を発射 (中央値 3 ships)。蜂の大群に襲われるみたい — 各 1 匹は小さいが、何百万といる。私たちの `RESERVE = 5` (常に防御用に 5 ships を home に残す) では足りない。彼らは私たちを干上がらせる。

```
turn  Sai の planets   Sai の発射回数      私たちの planets
  50         6              56                  4
  75        12             171                  7
 100        13             305                 12
 150        21             487                  9
 200        32             —                    0  <- 消滅
```

### 失敗 D: 太陽に飛び込む

ゲームには中央に太陽がある (半径 10)。経路が太陽を横切る fleet はすべて破壊される (engine ソース: `orbit_wars.py:606-609`)。私たちの bot はこれをチェックしない。なので片側の planet から反対側のターゲットに撃つと、**私たちの ships は太陽に消えて無駄になる**。

これは 10 行で済む無料の修正: 太陽に当たる角度を棄却して、第二最近接ターゲットを選ぶだけ。

### 失敗 E: 私たちはチームを組まない

3 planets を持っている場合、それぞれが自分の最近接ターゲットを選ぶ。なので 3 つの planet が 1 つの弱い中立に撃つことがあり、1 つの planet で十分だったのに 30 ships を無駄にする。一方、もっと手強いターゲットは無視される。

トップの bot は **集約する**: すべてのターゲットを見て、どれが最も価値があるかを決め、複数の home planets から ships を組み合わせて取りに行く。私たちの bot はやらない。

---

## 5. トップの bot のコードについて何がわかっているか？

何人かの Kaggler は自分の作業を公開ノートブックとして公開している。4 つダウンロードしました:

### "Structured Baseline" by pilkwang (194 票)

これは **コミュニティリファレンス**。強い bot のほとんどはここからフォークされている。**10 種類のミッションタイプ** がある:

1. **Reinforce-to-hold** — 防御に陥落しそうな planet に ships を送る。
2. **Rescue** — 攻撃を受けている planet に追加を送る。
3. **Recapture** — たった今失った planet を取り戻す。
4. **Single-source capture** — 1 つの planet が 1 つのターゲットを攻撃する。
5. **Snipe** — 小型 fleet で防御の薄い弱い planet を倒す。
6. **Swarm** — 複数の planets が協調して 1 つのターゲットを攻撃する。
7. **Crash exploit** — 敵 fleets が太陽に衝突したときの便乗攻撃。
8. **Follow-up capture** — もう少しで自分のものになりそうな planet を追う。
9. **Live doomed salvage** — どうせ陥落する planet があるとき、残った ships を別の有用な場所に送る。
10. **Rear funneling** — 後方の安全な planets から ships を前線に動かす。

私たちの bot は **1 つだけ** (#4 のみ) 持っている。

ノートブックはまた言う: 太陽を飛び抜けるな、回転する planets が fleet 到着時にどこにいるか予測しろ (中心近くの planets は太陽の周りを回る)、各発射後にすべての計画を再チェックしろ。

### "Hybrid agent" by konbu17 (50 票)

これは最も読むのが辛い。ノートブックからの引用:

> "v1_sniper [opponent]: hybrid wins 16/16 (100%), rule-base wins 16/16 (100%)"

その `v1_sniper` は **私たちの bot の祖先である公開 sniper baseline**。なのでリーダーボード上半分にいる公開 agent は基本的に全て、彼らのテストでは私たちのタイプに 100% 勝つ。これは私たちの 326 スコアと一致する — システムは私たちが中位層よりはるか下と判定している。

著者はまた、強化学習でゼロからニューラルネットを訓練しようと **5 回** 試みて諦めた: "5 個別 ML 試行が同じ壁にぶつかった"。代わりに動いたアプローチは、ルールベース agent が取ろうとした **悪い shot を棄却するだけ** の小さなネットワーク。それで彼らは +19 ポイントの勝率上昇を得た。

**教訓**: ニューラルネットにゼロから Orbit Wars をプレイさせようとするな。代わりに、まず良いルールベース agent を書いて、それから ML を加えて決定を **フィルタする**。

### "Target Score 2000.4" by rahulchauhan016 (57 票)

この著者のノートブックは 21 モジュールをリストする、含む:

- **MCTS** (Monte Carlo Tree Search) — Alpha-Go の考え方みたい。10 ターン先までシミュレーションし、異なる手を試し、最適なものを選ぶ。
- 5-iteration **lead-aim predictor** with sun avoidance — 動く planet に撃つとき、ships が到着するときどこにいるかを予測する (動いてるカモの先を狙うように)。
- 7-feature evaluator with 重み調整: ship count diff (1.0)、production diff (46.0!)、planet count diff (20.0)、risk (-2.8)、border pressure (9.0)、fleet momentum (0.6)、neutral denial (12.0)。
- 小さなニューラルネット 14 → 64 → 32 → 1。

production の重み (46.0) が大きいのは理にかなう: 今ある ships は一度使ったらおしまいだが、各 planet の生産は永遠に与え続ける。生産 2 の planet を 100 ターン所有 = 200 個の無料 ships。長期思考が勝つ。

### "OW-Proto" by djenkivanov (119 票)

この著者は ~ランク 95 に到達、bot のスコアリング式が逐語リーク:

```
score = (100 - dist) + (15 * production) + (10 * enemy_bonus) - (0.7 * total_ships) - (2 * eta)
```

翻訳: "**近い** (dist が小さい)、**価値のある** (production が高い)、**敵所有** (ボーナス)、**安い** (必要 ships が少ない、到着までのターンが少ない) ものを攻撃したい"。これは妥当な中位層 baseline。ELO ~1200 を超えるものはこの bot を倒す。

---

## 6. 戦略の「個性」はどんなものがあるか？

各トップ bot がどれだけ頻繁に、どれだけ大きな fleets を発射するかを見ると、3 つの主要な「プレイスタイル」が見える:

### スタイル 1: Kill-stack マクロ (Isaiah, Forrest)

- **空気感**: "生産を 1 つの巨大な fleet に貯める"
- 発射回数は少ない (試合あたり 100 未満)
- 中央値 fleet サイズ 60-100+
- ときに 200-1000 ships の単発発射
- 1 つの瞬間に圧倒して勝つ

### スタイル 2: 継続圧力 (Vadasz, Shun_PI, HY2017)

- **空気感**: "200-300 個の中型 fleets を送って、決して止めない"
- 試合あたり 200-300 発射
- 中央値 fleet サイズ 25-30
- 最大は 100-250 あたり
- 消耗 (ゆっくり出血) で勝つ

### スタイル 3: Adaptive (flg, bowwowforeach)

- **空気感**: "この相手に効くものを見つける"
- 試合ごとに分布が大きく異なる
- ときに 78 個の大型 fleets、ときに 1349 個の小型
- これが **#1 と #2** の戦略。リーダーボードのトップには行動を変える bot がいる。

---

## 7. Comet について (無料の不動産の瞬間)

Comet はターン 50, 150, 250, 350, 450 に出現する (engine: `orbit_wars.py:27`)。一度に 4 つの planets が、対称的に配置される (中心の 4-fold 対称)。占領できる ships を持ち、通常の planets と同様に各々ターンあたり 1 ship を生産する。

トップの bot は comet スポーンを待ち、**1-3 ターン以内に反応する** (`Vadasz` はターン 52、ちょうどスポーンの 2 ターン後に 36 ships を発射)。彼らは「comet 確保モード」をプログラムしている — ターン 49 で予備を準備し、ターン 51-52 で新しい comets に発射する。

私たちの bot は comets が存在することを知らない。最近接の非フレンドリーな planet を撃つだけなので、たまたま comet が最近接のターゲットだったらそれに撃つ。でも計画は立てない。

---

## 8. リーダーボードを上るために何をすべきか？

難易度順に:

### ステップ 1: 太陽に飛び込まない (~10 行のコード)

すべての shot について、経路が中心の太陽を通るかチェック。通るなら、スキップして次の最近接ターゲットを選ぶ。Engine 参照: `orbit_wars.py:606-609`。簡単。+200 から +400 ELO の効果がある。

### ステップ 2: Fleet を集約する (~30 行)

各 planet が独立してターゲットを選ぶのをやめる。代わりに、すべての (ソース、ターゲット) ペアを見て、`(ターゲットの価値 / ships のコスト)` でスコアリングし、最高 ROI から先に撃つ。2 つの planet が同じターゲットに撃つのを避ける。+100 から +200 ELO。

### ステップ 3: 奪還ロジック (~30 行)

敵が planet を取ったら、それを **マークし**、次のターンで取り返すことを優先する。今は単に諦めている。+50 から +150 ELO。

### ステップ 4: Comet 認識 (~50 行、ジオメトリが難しい)

ターン 48-52、148-152、等で「comet 確保モード」に切り替える — 全所有 planet が ships の 40% を予想される comet 位置の最近接に送る。+50 から +100 ELO。

### ステップ 5: ML shot validator (konbu17 の技)

小さなニューラルネット (5,000 重み、24 入力特徴) を訓練して、「この shot は成功しそうか？」を予測する。ルールベース agent の決定から悪い shot をフィルタするのに使う。ノートブックは +19 ポイントの勝率を主張。+100 から +150 ELO。

5 ステップ全部の後、私たちは **ランク 50-100** (ELO ~1100-1300) のはず。本当のトップ (1500+) は新しい戦略を **発明する** か MCTS bot をチューニングする必要がある — それは複数週のプロジェクト。

---

## 9. クイックリファレンス: 私が作った全ファイル

`/home/yusuke_kaya/projects/kaggle/orbit-wars/` にて:

```
docs/research/
  lb_snapshot_2026-05-09.csv             <- Top 200 リーダーボード
  lb-observations.dense.md               <- このドキュメントのエンジニア版
  lb-observations.kids.md                <- このファイル

data/replays/
  episode-76154720-replay.json           <- Self-play (Reexel × 4)
  episode-76155027-replay.json           <- Yudji 戦の LOSS
  episode-76155250-replay.json           <- wojak_321 戦の LOSS
  episode-76155486-replay.json           <- Jason 戦の WIN
  episode-76155695-replay.json           <- Top: Isaiah vs Vadasz
  episode-76155696-replay.json           <- lishell 戦の 500 ステップ LOSS
  episode-76155725-replay.json           <- Top1 vs Top2: bowwow vs flg
  episode-76155929-replay.json           <- Top1 vs Top2 (再戦)
  episode-76156043-replay.json           <- Vishal Grover 戦の LOSS
  episode-76156145-replay.json           <- Top: bowwow vs Vadasz
  episode-76156160-replay.json           <- Top: Shun_PI vs Vadasz
  episode-76156165-replay.json           <- Malaika 戦の WIN
  episode-76156220-replay.json           <- Top: HY2017 vs jack gell
  episode-76156339-replay.json           <- Mid: Forrest vs Leszek
  episode-76156375-replay.json           <- Top: Shun_PI vs Vadasz (再戦)
  episode-76156398-replay.json           <- Mid: Alvin vs monnu
  episode-76156402-replay.json           <- Sai Rakshit 戦の LOSS
  _analysis.json                         <- サンプル時系列
```

---

それが全体像です。私たちはきれいなサンドボックスにとてもシンプルな bot を持っていて、そこにある他の bot のほとんどは 10 倍洗練されています。上の 5 つの修正それぞれは 1-2 日で達成可能。難しい部分はランク 100 を超えてから始まる — それが本物のエンジニアリングコンペが始まる場所です。
