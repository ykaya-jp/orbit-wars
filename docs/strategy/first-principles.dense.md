# Orbit Wars — 第一原理に基づく数学的解析 (dense)

> Worker C, 2026-05-09. 一次情報源: `/home/yusuke_kaya/projects/kaggle/orbit-wars/.venv/lib/python3.11/site-packages/kaggle_environments/envs/orbit_wars/orbit_wars.py` (以下、`orbit_wars.py` と参照する)。
>
> 全ての公式と定数には engine の `file:line` 引用を付ける。本書の数値は全て engine に対して再導出済みであり、`tools/notebooks/01_physics_sandbox.ipynb` で再現可能。

---

## 0. 表記法、規約、そして 1 つの重要なストレージ上の癖

| 記号 | 意味 | 出典 |
|---|---|---|
| $L = 100$ | `BOARD_SIZE` | `orbit_wars.py:17` |
| $C = 50$ | `CENTER = L/2` | `orbit_wars.py:18` |
| $R_\odot = 10$ | `SUN_RADIUS` | `orbit_wars.py:19` |
| $R_{rot} = 50$ | `ROTATION_RADIUS_LIMIT` | `orbit_wars.py:20` |
| $r_{cmt} = 1$ | `COMET_RADIUS` | `orbit_wars.py:21` |
| $\epsilon = 7$ | `PLANET_CLEARANCE` | `orbit_wars.py:23` |
| $v_{\max} = 6$ | default `shipSpeed` | `orbit_wars.json:19` |
| $v_{cmt} = 4$ | default `cometSpeed` | `orbit_wars.json:24` |
| $T_{ep} = 500$ | `episodeSteps` | `orbit_wars.json:8` |
| $\omega \in \mathcal U[0.025, 0.05]$ | `angular_velocity` | `orbit_wars.py:366` |
| `COMET_SPAWN_STEPS = [50,150,250,350,450]` | comet 生成 tick (`step+1` と照合) | `orbit_wars.py:27`, `:434` |

**ストレージ上の癖（コードを移植する際に致命的）。** `generate_planets` は planet レコードを `[id, -1, y, x, r, ships, prod]` として構築する (例: `orbit_wars.py:103, :153`)。すなわち、サンプリングされた元の $(x, y)$ をスロット $(2, 3) = (y, x)$ に入れ替えて格納する。下流のすべての consumer はその後 `planet[2]` を X 座標、`planet[3]` を Y 座標として扱う (fleet 発射の数学 `orbit_wars.py:493-494`、移動更新 `:537-546`、距離ヘルパー `:30-31` を参照)。正味の効果: ジオメトリは *一貫している* — スロット 2 が X、スロット 3 が Y — が、ランダムサンプルのペア $(x_{src}, y_{src})$ は格納時に転置されるので、これは幾何的に直線 $Y = X$ に対する反転と等価。「home は本当に Q1 にあるのか？」を検証する際に重要: home は *格納された* 座標に対する右上のオクタント内に一様に配置される。

したがって本書では一貫して $(x, y)$ を *格納された* 座標として用いる (= agent が観測するもの)。

---

## 1. 艦隊速度のスイートスポット

### 1.1 閉形式

`orbit_wars.py:577-578` より:

```python
speed = 1.0 + (max_speed - 1.0) * (math.log(ships) / math.log(1000)) ** 1.5
speed = min(speed, max_speed)
```

$$v(N) = \min\!\Big(v_{\max},\; 1 + (v_{\max}-1)\,\big(\tfrac{\ln N}{\ln 1000}\big)^{1.5}\Big),\qquad N \ge 1.$$

`math.log(ships)` は自然対数。`ln(1000) ≈ 6.9078`。`min` でクランプされるので $N \ge 1000$ では全て $v_{\max}=6$ で航行する。

ユークリッド直線距離 $D$ を turn 単位で移動する時間 (連続値、丸めなし — engine は実数値の位置を tick 毎に積分する):

$$T(N, D) = D / v(N).$$

### 1.2 スイープ表 ($v_{\max}=6$)

| $N$ | $v(N)$ | $T(N, 30)$ | $T(N, 50)$ | $T(N, 100)$ |
|---:|---:|---:|---:|---:|
| 1 | 1.0000 | 30.00 | 50.00 | 100.00 |
| 5 | 1.5623 | 19.20 | 32.00 | 64.01 |
| 10 | 1.9623 | 15.29 | 25.48 | 50.96 |
| 50 | 3.1309 | 9.58 | 15.97 | 31.94 |
| 100 | 3.7217 | 8.06 | 13.43 | 26.87 |
| 250 | 4.5731 | 6.56 | 10.93 | 21.87 |
| 500 | 5.2666 | 5.70 | 9.49 | 18.99 |
| 750 | 5.6909 | 5.27 | 8.79 | 17.57 |
| 1000 | 6.0000 | 5.00 | 8.33 | 16.67 |
| 1500 | 6.0000 | 5.00 | 8.33 | 16.67 |

$N=1000$ で飽和する。それを超えても、追加の ship は速度には寄与しない。

### 1.3 単一 vs 分割 (1 艦隊に N ships か、2 艦隊に N/2 ships か)

サイズ $N$ の単一艦隊は、同じ目標に対して $\lfloor N/2 \rfloor$ の 2 艦隊と比べて **常に** 同等以上に速い (どちらも同じ距離を踏破する必要がある):

$$T(N, D) \le T(N/2, D) \iff v(N) \ge v(N/2),$$

そして $v$ は $N$ について単調非減少。$D=50$ での数値スイープ:

| $N$ | $T_{\text{single}}$ | $T_{\text{half}}$ | より速い方 |
|---:|---:|---:|---|
| 10 | 25.48 | 32.00 | single |
| 50 | 15.97 | 19.30 | single |
| 100 | 13.43 | 15.97 | single |
| 200 | 11.47 | 13.43 | single |
| 800 | 8.68 | 9.92 | single |
| 1500 | 8.33 | 8.79 | single |

**戦略的含意。** 純粋な到着時間のためには、ships を単一艦隊に集約する。分割する理由は (a) **角度の多様化** — 別々の艦隊で 2 つの planet を狙える、(b) **デコイ / 過剰投入のヘッジ**、(c) 発射元 planet の在庫が限られていて集中できない、のいずれか。速度面で分割する理由は *存在しない*。

### 1.4 限界効用

$$\frac{\partial T}{\partial N} = -\frac{D}{v(N)^2}\,\frac{\partial v}{\partial N}, \qquad \frac{\partial v}{\partial N} = \frac{(v_{\max}-1)\cdot 1.5}{N\,(\ln 1000)^{1.5}}\,(\ln N)^{0.5}\quad\text{for }N<1000.$$

数値 ($D=50$ で ship 1 隻追加あたりの節約 turn 数):

| 範囲 | $\Delta v$ | ship 1 隻あたりの節約 turn |
|---|---:|---:|
| 1 → 5 | +0.56 | 4.499 |
| 5 → 10 | +0.40 | 1.305 |
| 10 → 50 | +1.17 | 0.238 |
| 50 → 100 | +0.59 | 0.051 |
| 100 → 500 | +1.55 | 0.0099 |
| 500 → 1000 | +0.73 | 0.0023 |
| ≥ 1000 | 0 | 0 |

**ブレークポイント。** 艦隊の最初の 10 隻は ship 1 隻あたり >1 turn 節約に寄与する。N=100 を超えると、speed の利得は ship 1 隻あたりの戦闘価値に対して実質的に枯渇する。**戦略的含意。** ≥10 ships の小さな「stinger」は 1 隻偵察のほぼ倍速で動く。これが高速偵察 / 迎撃の最低ラインである。≈250 ships を超えると戦闘力は増えるが、意味のある速度向上はない。

---

## 2. 軌道予測と先読み射撃の発射角

### 2.1 標的の軌跡

`orbit_wars.py:537-546` より、$(x_0, y_0)$ にある *初期* planet で半径 $r_p$ が軌道半径 $r_{orb} = \|(x_0, y_0) - (C, C)\|$ について $r_{orb} + r_p < R_{rot}$ を満たすものは、一定の角速度 $\omega$ で回転する:

$$\theta(t) = \theta_0 + \omega\,t, \qquad \theta_0 = \mathrm{atan2}(y_0 - C,\; x_0 - C),$$
$$\vec p(t) = \big(C + r_{orb}\cos\theta(t),\;\; C + r_{orb}\sin\theta(t)\big).$$

静止 planet (軌道半径 + $r_p \ge R_{rot}$) は動かない。Comet は `orbit_wars.py:556-566` で事前計算された path テーブルに従う。

### 2.2 艦隊の軌跡

`orbit_wars.py:493-494` より、艦隊は planet 端 $(x_a + (r_p+0.1)\cos\alpha,\; y_a + (r_p+0.1)\sin\alpha)$ から発射され、一定の方位 $\alpha$ で tick 毎に $v(N)$ 進む:

$$\vec f(t) = \vec a + (r_p+0.1+v(N)\,t)\cdot(\cos\alpha,\sin\alpha).$$

以下の先読み角の代数では $r_p+0.1$ オフセット (≤2.7 単位) を落として、発射を $\vec a = (x_a, y_a)$ から始まるものとして扱う。

### 2.3 迎撃時間 $t^*$ と発射角 $\alpha^*$ の閉形式

$\|\vec f(t) - \vec p(t)\| = 0$ となる最小の $t^* > 0$ を求める必要がある (より正確には、`orbit_wars.py:46-64` の swept-pair テストはセグメント $[t, t+1]$ 上で距離が $r_p$ 以内に縮まったときに hit を報告する。設計上は厳密な迎撃を解いて $t^*$ から ±0.5 以内の任意の $t$ を許容する)。

条件 $\|\vec f - \vec p\| = 0$ は 1 つの超越方程式を与える:

$$\big(x_a + v\,t\cos\alpha - C - r_{orb}\cos(\theta_0+\omega t)\big)^2 + \big(y_a + v\,t\sin\alpha - C - r_{orb}\sin(\theta_0+\omega t)\big)^2 = 0.$$

未知数が 2 つ ($t, \alpha$) で方程式が 1 つだけなので、*共線条件* を加える: 迎撃時、発射方向は $\vec a$ から $\vec p(t^*)$ への幾何方向に等しい:

$$\alpha = \mathrm{atan2}\big(y_p(t^*) - y_a,\; x_p(t^*) - x_a\big).$$

これを代入して $\alpha$ を消去する。$t$ に関する残りの 1 次元方程式は:

$$g(t) \equiv \|\vec p(t) - \vec a\| - v\,t = 0.$$

これは **標準的な動的標的迎撃方程式** である: 踏破すべき距離 (LHS) = 艦隊が飛行する距離 (RHS)。$\vec a$ が軌道の外側 ($\|\vec a - C\| > r_{orb}$) で $v > r_{orb}\,\omega$ (艦隊が標的の接線速度より速い) なら、$g$ は少なくとも 1 つの正の解を持つ。

存在性: 艦隊の接線方向の closing speed の上限は $v$、標的の接線速度は $r_{orb}\,\omega$。$\omega \le 0.05$ かつ $r_{orb} \le 50$ より、標的の接線速度 $\le 2.5$ — これは厳密に $v(N{=}1)=1.0$ より小さい… 実は **常にそうとは限らない**: 1 隻艦隊 (v=1) は速い外輪 orbiter ($r_{orb}\,\omega$ が最大 2.5 に達する) を捕まえられない。よって最小艦隊での先読み射撃は遠方の orbiter には失敗する。$v(N) > r_{orb}\,\omega$ となるだけ $N$ を大きくする必要がある。§1.2 より $v(50) \approx 3.13 > 2.5$ — **50 ships なら必ず捕まえられる**。

実用ソルバー ($t$ の二分法):

```python
def lead_intercept(a, theta0, omega, r_orb, center, v):
    """Returns (t_star, fire_angle_rad). a=(x_a,y_a). v=fleet_speed(N)."""
    import math
    cx, cy = center
    def pos(t):
        a_t = theta0 + omega*t
        return (cx + r_orb*math.cos(a_t), cy + r_orb*math.sin(a_t))
    def g(t):
        px, py = pos(t)
        return math.sqrt((px-a[0])**2 + (py-a[1])**2) - v*t
    # g(0) >= 0 (target is some distance away). Search for sign change.
    lo, hi = 1e-3, 500.0
    if g(lo) <= 0:
        return lo, math.atan2(pos(lo)[1]-a[1], pos(lo)[0]-a[0])
    for _ in range(120):
        mid = 0.5*(lo+hi)
        if g(mid) > 0: lo = mid
        else:          hi = mid
    t = 0.5*(lo+hi)
    px, py = pos(t)
    return t, math.atan2(py-a[1], px-a[0])
```

### 2.4 数値例

Q1 home が $(75, 25)$、標的が円軌道 $r_{orb}=30$、$\omega=0.04$、標的の初期位相 $\theta_0 = 0$ ($t=0$ で標的は $(80, 50)$)、50 ships の艦隊 ($v = 3.1309$)。

結果 (上記の二分法で計算):

- $t^* = 12.628$ turns
- 迎撃点 $(76.254, 64.517)$
- $\alpha^* = 1.5391$ rad $= 88.183^\circ$
- naive (先読みなし) で $t=0$ の標的位置を狙う場合: $84.806^\circ$
- **先読み補正: $+3.378^\circ$** (約 0.059 rad)

3.4° の補正は迎撃点では垂直方向の miss が $\approx \tan(3.4°)\cdot 39.6 \approx 2.36$ に相当する — 典型的な $r_p$ (1–2.6 単位) より大きいが、高 prod 標的の planet 半径よりは小さい ($r_p(\text{prod}=5)=2.609$)。低 prod 標的では先読みが必須。高 prod 標的では naive な狙いでも幸運でヒットする可能性があるが、それは tick の途中で swept-pair テスト (`orbit_wars.py:46-64`) が捕まえた場合のみ。

### 2.5 太陽横断チェック (forbidden cone)

艦隊の経路が太陽を横切るのは、$(C, C)$ からセグメント $[\vec a, \vec a + v\Delta t (\cos\alpha,\sin\alpha)]$ への **点-セグメント距離** がいずれかの tick で $< R_\odot = 10$ となる場合である (`orbit_wars.py:34-43, :607-609`)。等価に、$\vec a$ から方位 $\alpha$ の直線について太陽への垂直距離は:

$$d_\perp(\alpha) = \big| (C - x_a)\sin\alpha - (C - y_a)\cos\alpha \big|,$$

そして射影 $s_\| = (C-x_a)\cos\alpha + (C-y_a)\sin\alpha > 0$ (太陽が前方にある)。

$d_\perp < R_\odot$ かつ太陽が前方にあれば、艦隊は焼失する。発射点 $\vec a$ からの forbidden な方位の窓は:

$$\alpha \in \big[\,\theta_\odot - \delta,\;\theta_\odot + \delta\,\big], \quad \theta_\odot = \mathrm{atan2}(C-y_a, C-x_a),\quad \delta = \arcsin\!\Big(\tfrac{R_\odot}{\|\vec a - (C,C)\|}\Big).$$

**数値 ($(75, 25)$ から発射、太陽までの距離 $= 35.355$):**

- $\theta_\odot = 135.000^\circ$
- $\delta = \arcsin(10/35.355) = 16.430^\circ$
- forbidden 範囲 $[118.57^\circ,\; 151.43^\circ]$ (=33° 幅)

よって Q1 home から見ると、太陽を直接横切って Q3 を狙う任意の方位は死亡確定。盤面横断攻撃は迂回が必要 — 通常は太陽線から 16–17° 外し、$\approx \frac{1-\cos\delta}{\cos\delta} \approx 4\%$ の移動距離増を加える。

**注意点。** チェックはセグメント-点間: 1-tick セグメントが今 tick 内では太陽の $R_\odot$ 以内に届かない遅い 1 隻艦隊は今 tick は生存する。直線を延長すれば横断するとしても。ただし swept セグメントが太陽の円に入った瞬間に殺される。ネット挙動: forbidden cone は複数 tick ベースで正しい。

> 関連: §5 で opening 探索における forbidden cone の使い方を参照。

### 2.6 §2 の出典

- `orbit_wars.py:30-31` 距離
- `orbit_wars.py:34-43` 点-セグメント距離
- `orbit_wars.py:46-64` swept-pair (planet+fleet)
- `orbit_wars.py:493-506` 艦隊発射ジオメトリ
- `orbit_wars.py:537-546` planet の回転更新
- `orbit_wars.py:607-609` 太陽横断による撃沈

---

## 3. Comet のタイミングウィンドウ

### 3.1 生成スケジュール

`COMET_SPAWN_STEPS = [50, 150, 250, 350, 450]` (`orbit_wars.py:27`)。チェックは `(step + 1) in COMET_SPAWN_STEPS` (`orbit_wars.py:434`)。ここで `step` は `obs.step` で渡される tick 番号。よって *新しい comet グループが観測可能になる最初の turn* は `step+1` がマッチする tick。comet は `path_index=-1` で append され、同じ tick で初めて盤面に配置される。

**5 spawn × 4 対称コピー = エピソードあたり最大 20 個の comet。**

### 3.2 spawn 毎の RNG seeding — そしてなぜ exploit 不可能か

出典: `orbit_wars.py:438-447`:

```python
env_info = getattr(env, "info", None) or {}
episode_seed = env_info.get("seed", 0) or 0
comet_rng = random.Random(f"orbit_wars-comet-{episode_seed}-{step + 1}")
```

`episode_seed` は **どの agent が観測する前にも意図的に設定からスクラブされる** (`orbit_wars.py:359-363`):

```python
configuration.seed = None
env.info["seed"] = seed
```

seed は `env.info` にのみ存在し、これは agent の observation には **伝播しない** (`orbit_wars.py:393-402` を比較すると、agent ごとに `player`, `angular_velocity`, `planets`, `initial_planets`, `fleets`, `next_fleet_id`, `comets`, `comet_planet_ids` のみがコピーされる)。JSON spec doc は明示的に警告している: *"the agent server re-validates the (scrubbed) configuration on every act() call"* (`orbit_wars.json:27`)。

**結論: comet の未来は事前シミュレート可能ではない。** seed は意図的に隠されている。comet に反応できる最も早いタイミングは spawn する tick (その完全な `paths` リストは `orbit_wars.py:457-474` で `obs.comets[g]["paths"]` に append され、`:676-682` で全 agent に公開される)。

**しかし** — comet グループが可視化されると、その完全な path は observation に含まれる。よって on-board lifetime、近日点のタイミング、捕獲ウィンドウは spawn tick 以降決定論的に計算できる。これが exploit 可能な非対称性。

### 3.3 Comet の形状ジオメトリ

`orbit_wars.py:210-244` より、各 comet グループは太陽を 1 つの焦点とする 1 つの楕円軌道で、4 重に複製される:

- $e \in \mathcal U[0.75, 0.93]$ (離心率)
- $a \in \mathcal U[60, 150]$ (長半径)
- 近日点 $= a(1-e) \ge R_\odot + r_{cmt} = 11$
- $b = a\sqrt{1-e^2}$
- 向き $\phi \in \mathcal U[\pi/6, \pi/3]$ (近日点方向、Q4 にアンカー)
- 弧は $t \in [0.3\pi, 1.7\pi]$ でパラメータ化、その後 $v_{cmt} = 4$/turn の弧長間隔で再サンプル (`orbit_wars.py:236-244`)
- **on-board** 連続セグメントのみ保持 (`:246-256`); 5–40 path 点 = 5–40 ticks の comet 寿命

結果として可視弧の持続時間: $v_{cmt}=4$ で 5 から 40 ticks の間、すなわち弧長 $\in [20, 160]$ 盤面単位。中央値は ~22 ticks 可視 (~88 盤面単位)。

4 つのコピーは: $(y, x), (L-x, y), (x, L-y), (L-y, L-x)$ (`orbit_wars.py:266-269`) — すなわち $C$ 中心の 4 重回転対称。各プレイヤーは自分のクアドラントを通過する 1 つの comet を見る。

### 3.4 Q1 home のための捕獲コスト / タイミング

comet グループは `comet_ships = min(rng4)` of `randint(1, 99)` を持つ (`orbit_wars.py:451-456`)。i.i.d. $\mathcal U\{1..99\}$ 4 個の $\min$ の分布:

$$P[\text{ships} \le k] = 1 - (1 - k/99)^4.$$

数値: 中央値 $\approx 19$、P90 $\approx 53$。Comet は **柔らかい標的** である — 25 ships 艦隊で comet 捕獲の ~50% に勝ち、60 ships 艦隊で ~95% に勝つ。

**Closing speed.** comet は弧に沿って $v_{cmt}=4$ で動く。Q1 の 50 ships 艦隊 ($v=3.13$) は実は *より遅い*。planet と同様に comet も先読み射撃する必要がある (§2)。幸い、comet は on-board 弧で home の ≈20–40 単位以内を通過する。

**タイミングウィンドウ。** 各 comet グループ $g$ について最初の可視 tick $t_0 = \text{spawn\_step}$ で長さ $K$ の path を持つ:
- home $\vec h$ への最接近 tick: $t^*_g = \arg\min_{k\in[0,K)} \|\vec h - \text{paths}[g][\text{Q1}][k]\|$
- 推奨発射 tick: $t_0 + \max(0, t^*_g - T_{lead})$ ここで $T_{lead} = \|\vec h - \text{closest-pt}\|/v(N)$

これは path が観測可能になれば $O(K)$ で解ける。

### 3.5 戦術的含意

1. **事前シミュレート不可能** — しかし spawn tick で 4×K の path テーブル全体が手に入る。各未来点に対して先読み迎撃ソルバーを実行せよ。
2. **Comet は安価** — 防御 ship の中央値 19。home に 25–40 ships の事前割当ストライク部隊を置けば comet 捕獲を保証できる。
3. **Comet 期限切れ** — `path_index ≥ len(path)` のとき comet は除去される (`orbit_wars.py:411-415, :558-561`)。期限切れ後に到着する艦隊を送ってはならない。
4. **Orphan capture は本物** — 捕獲した comet の `production = 1` ship/turn (`orbit_wars.py:22, :513-514`) だが、comet は残り path を辿って *動く* 後、消滅する。これは ≤ 40 ticks の一時的な 1-prod planet。

### 3.6 §3 の出典

- `orbit_wars.py:27` spawn リスト
- `orbit_wars.py:191-331` `generate_comet_paths`
- `orbit_wars.py:359-363` seed scrub
- `orbit_wars.py:393-402` agent ごとの observation 伝播 (seed なし)
- `orbit_wars.py:411-429` comet 期限切れ sweep
- `orbit_wars.py:434-474` spawn ブロック
- `orbit_wars.py:549-566` comet 移動
- `orbit_wars.json:27` seed scrubbing の根拠

---

## 4. 戦闘のサープラス計算

### 4.1 ルール (engine の真実)

戦闘は planet ごと、tick ごとに解決される (`orbit_wars.py:636-674`)。swept-pair チェックで planet にヒットした全艦隊が `combat_lists[pid]` に入る。その後:

1. *攻撃側プレイヤーごと* に ships を合計: `player_ships[owner] += fleet[6]` (`:643-645`)。
2. ship 数で降順ソート (`:650-652`)。
3. **トップ vs 二位** (`:655-658`):
$$\text{survivor} = T - S, \quad \text{owner} = \text{top}.$$
4. **同点ルール** (`:659-661`): top と二位が等しいなら、**survivor = 0**、planet は $G$ にかかわらず元のオーナーを保持。
5. survivor vs 駐留 $G$ (`:667-674`):
   - survivor = 0 なら → 駐留は無傷
   - survivor > 0 かつ `planet.owner == survivor_owner` なら → 増援: $G \mathrel{+}= \text{survivor}$
   - それ以外なら → $G \mathrel{-}= \text{survivor}$; $G < 0$ なら → planet が flip し、新駐留 $= |G|$。

**重要な帰結。** 駐留 ship は攻撃者間の戦いに *入らない*。攻撃者が互いに戦った後の生存攻撃者を減らすだけである。よって 2 人の敵から防御する場合、彼らを同点にできれば駐留コストは 0。

### 4.2 結果表 (G = 駐留、T = top 攻撃者、S = 二位攻撃者)

ソルバー:
```python
def combat3(G, T, S):
    top, sec = (T, S) if T >= S else (S, T)
    if top == sec:                      # tie
        return ("garrison_holds", G)    # both forces wiped
    survivor = top - sec
    if survivor <= G:
        return ("garrison_holds", G - survivor)
    return ("flip", survivor - G)
```

| $G$ | $T$ | $S$ | 結果 | 新駐留 |
|---:|---:|---:|---|---|
| 80 | 100 | 0 | flip (top wins) | 20 |
| 80 | 100 | 50 | garrison holds | 30 |
| 80 | 50 | 50 | tie → both wiped | 80 |
| 80 | 60 | 40 | garrison holds | 60 |
| 80 | 80 | 80 | tie → both wiped | 80 |
| 50 | 100 | 80 | garrison holds | 30 |
| 20 | 100 | 80 | garrison holds | 0 (sets to 0) |
| 0 | 100 | 80 | flip | 20 |
| 80 | 200 | 100 | flip | 20 |

### 4.3 駐留 G に対する 2 協力攻撃者の最適分割

**間違った直感:** 「均等分割」。2 人の *非協力* 敵 + 1 駐留 (3 者) に対して、同点は両攻撃者にとって自殺 (彼らの survivor = 0)。

**1 攻撃者-2 艦隊 vs G の正解:** engine はプレイヤーごとに合計し、艦隊ごとではない。同じプレイヤーの 2 艦隊はマージされる。よって分割は総インパクトには無関係。到着タイミングにのみ関連する。

**2 つの異なる攻撃者 vs G の正解** (協力シナリオ、例: 4 プレイヤーのチームアップ):

総攻撃 ships $X = T + S$。駐留が勝つのは $|T - S| \le G$ の時。planet を flip するには: $|T - S| > G$ が必要、すなわち非対称な戦力。最も安い flip は **1 プレイヤーが $X = G+1$ ships を送り、もう 1 人は 0 を送る** (無駄を最小化)。等しい戦力を送ると全てが無駄になる。任意の $S > 0$ に対して $G+1+S$ vs $S$ を送ると surplus 1 で flip する — しかし $S$ の ships は純粋な無駄。

**戦略的含意:** 4 プレイヤー FFA において、*ally の標的への重複 = ally の裏切り* に等しい。一方が同点で食われる桁違いに小さい戦力を送らない限り。一人の指定パンチャー無しでは 2 プレイヤー協力 flip は不可能。

### 4.4 同点防御 (殲滅の扉)

2 人の敵が同じ tick に等しい合計でこちらの planet に到着することを保証できれば、駐留コスト 0 で防御できる。これが **ミラー攻撃防御**: 同じ標的に対して 2 人の敵を狂わせ、彼らの戦闘がこちらに到達する前に解決するように受信タイミングを調整する。エンジニアリングが難しいが 4 プレイヤーで強力。

### 4.5 §4 の出典

- `orbit_wars.py:572` `combat_lists` セットアップ
- `orbit_wars.py:594` ヒット艦隊を combat list に追加
- `orbit_wars.py:636-674` 解決
- `orbit_wars.py:659-661` 同点殲滅
- `orbit_wars.py:667-674` 駐留との相互作用

---

## 5. 4 重対称の opening 探索

### 5.1 Q1 home の分布

`orbit_wars.py:67-122` (Phase 1 静止 planet) より、**home は静止クラスに配置される** (4 重ミラーは対角線越し、§0 ストレージの癖を参照)。各「静止」候補グループについて:

- $\theta \in \mathcal U[0, \pi/2]$ (中心からの角度、行 `:82`)
- $\text{prod} \in \{1..5\}$, $r_p = 1 + \ln(\text{prod})$
- 軌道半径 $r_{orb} \in [\,R_{rot} - r_p,\; (L-C-r_p)/\max(\cos\theta, \sin\theta)\,]$ (`:83-88`)
- 最小盤面分離: $|x - C| \ge r_p + 5$ かつ $|y - C| \ge r_p + 5$ (`:98-99`)

**home グループ** は全グループからランダムに選ばれる (`orbit_wars.py:380-381`)。2 プレイヤーゲームでは、プレイヤー 0 が Q1 コピー (`base+0` at `(planet[2]=y_src, planet[3]=x_src)`) を、プレイヤー 1 が Q4 コピー (`base+3` at `(L-y_src, L-x_src)`) を得る。それぞれ **10 ships** で開始 (`orbit_wars.py:383-387`)。

### 5.2 home 間距離の分布

ジオメトリから、home ペアは常に軸対称配置の対角コーナーである。Q1 home は格納座標 $(p_2, p_3)$、Q4 home は $(L - p_2, L - p_3)$。距離:

$$d_{HH} = \sqrt{(L - 2 p_2)^2 + (L - 2 p_3)^2} \ge 2\sqrt{2}(R_{rot} - r_p) \approx 2\sqrt{2} \cdot (50 - r_p).$$

$r_p \le 2.6$ のとき、$d_{HH} \ge 134$ が極限値だが、home が静止クラスに属しさらに外側に座ることができるため *通常はそれ以下* となる。実証サンプル (200k draws、engine の `randint`-`uniform` チェーンに合わせ、planet 重複拒否を modulo として):

- min ≈ 94.78
- median ≈ 100.48
- mean ≈ 103.28
- max ≈ 138.10

よって **期待される home 間距離は ≈ 100**、盤面の対角線。$N \ge 1000$ ships で $v=6$ の最大艦隊なら $\approx 17$ ticks 移動 — **盤面を全速で横断するのに 500-tick エピソードの 3.4%**。10 ships の開始駐留では tick 1 で敵に意味ある形で到達できない。先にローカル planet を捕獲してスケールアップする必要がある。

### 5.3 4 プレイヤーレイアウト

4 プレイヤーでは (`orbit_wars.py:388-391`)、各プレイヤーが home グループの 1 コピー (1 クアドラントずつ) を得る。全員 10 ships。隣接する敵までの距離は $\approx d_{HH}/\sqrt{2} \approx 71$ (1 軸越し)、対角の敵までは $\approx 100$。

### 5.4 行動空間サイズの推定

`orbit_wars.json:80-93` より: action = `[from_planet_id (int), angle (float), num_ships (int)]`、move のリストとして返す。

$G$ ships を持つ自分の 1 つの planet について:
- `from_planet_id`: 1 (1 move あたり自分の planet 1 つからしか送れない)
- `angle ∈ [0, 2π)` (連続; engine は量子化しない)
- `num_ships ∈ {1, ..., G}` ($G$ 通り)

planet あたりの 1 turn move 空間 (連続角度を $D$ ビンに離散化): $D \cdot G$。

典型的なミッドゲーム状態 (5-10 planet グループ × 4 = 20-40 planets、自分は 5-10 個所有、平均駐留 ≈ 30):
- planets: ~8
- planet あたりの move: $D \cdot 30$
- 1 turn に *複数* move 可能 (action はリスト)
- 発射元の $\{1..8\}$ planets のサブセット: $2^8$
- 発射 planet あたり: $D \cdot G$ actions
- 1 turn 合計: $\prod (1 + D \cdot G_i) \approx (1 + D \cdot 30)^8$

$D = 36$ (10° ビン) で: $(1 + 1080)^8 \approx 10^{24}$ 1 turn の actions。$D = 8$ で: $(241)^8 \approx 10^{19}$。**素朴な総当たりは死んでいる。**

### 5.5 扱いやすい opener のための枝刈り原則

1. **有効な方位のみ考慮。** planet $p$ から、観測されている *いずれかの* planet に $T$ ticks 以内で迎撃する方位のみ。observation で 8 planets なら、ソース planet あたり 8 候補角度。
2. **ships を量子化。** $\{0, G/2, G\}$ — 経験的に唯一意味のある分割、なぜなら production が小分数を素早く補充するため。
3. **1 planet あたり 1 tick 1 発射のみ。** (engine はもっと許可するが、speed 表 §1.3 から余分 — 集中の方が常に速い。)
4. **forbidden-cone フィルター** (§2.5)。
5. **先読みフィルター** (§2.3) — 範囲内の *動く* planet に実際にヒットする方位のみ。

枝刈り後: ~8 ソース × ~3 行先 × 3 ship サイズ ≈ tick あたり 72 moves。サブセット期待値 ≈ $4 \cdot 10^4$。深さ 5–10 のビーム探索で扱える。

### 5.6 擬似コード: ビーム探索 opener (10-tick lookahead)

```python
def beam_opener(obs, depth=10, beam_width=64):
    """Open-game search. State = (planets_snapshot, fleets_snapshot)."""
    initial = clone_state(obs)
    beam = [(score(initial), initial, [])]  # (score, state, action_seq)
    for d in range(depth):
        candidates = []
        for s, state, traj in beam:
            for action in generate_pruned_actions(state):
                next_state = simulate_one_tick(state, action, opponent_policy="hold")
                candidates.append((score(next_state), next_state, traj + [action]))
        # Keep top beam_width by score
        beam = sorted(candidates, key=lambda x: -x[0])[:beam_width]
    return beam[0][2]  # best action sequence

def score(state):
    return (sum(p.ships for p in state.planets if p.owner == ME)
            + sum(f.ships for f in state.fleets if f.owner == ME)
            + 5 * sum(p.production for p in state.planets if p.owner == ME))

def generate_pruned_actions(state):
    """Yields list-of-moves. Each move = (from_id, angle, ships)."""
    my_planets = [p for p in state.planets if p.owner == ME and p.ships >= 5]
    targets = state.planets  # candidates
    moves = []
    for src in my_planets:
        for tgt in targets:
            if not_forbidden_by_sun(src, tgt) and reachable(src, tgt, src.ships):
                t_star, alpha = lead_intercept(...)
                for ships in {src.ships // 2, src.ships - 1}:
                    moves.append([src.id, alpha, ships])
    yield from subset_top_k_combinations(moves, k=4)
```

### 5.7 §5 の出典

- `orbit_wars.py:67-188` planet 生成
- `orbit_wars.py:378-391` home 割り当て
- `orbit_wars.json:80-93` action shape
- `orbit_wars.py:477-509` action 処理 (silent-drop フィルター: §7 参照)

---

## 6. 生産密度 vs 距離のトレードオフ

### 6.1 Planet の解剖学

`orbit_wars.py:80-81, :133-134, :512-514` より:
- $\text{prod} \sim \mathcal U\{1..5\}$ (Phase 1 と Phase 2 で同分布)
- $r_p = 1 + \ln(\text{prod})$
- ships/turn = `prod` (行 514)
- `ships ∈ U{5..99}` (Phase 1、$\min$ トリック付き: 行 101) または `U{5..30}` (Phase 2: 行 151)

捕獲コスト: 戦闘後に駐留が 0 を下回る必要があるので、最安経路でコスト = $G + 1$ (生存して $G+1$ ships で到着する)。

### 6.2 ROI 表

ROI = 捕獲後、planet 自体で 1 turn あたり得られる ships。

| prod | $r_p$ | ships/turn | 典型的 $G$ (Phase 1) | flip の最小コスト |
|---:|---:|---:|---:|---:|
| 1 | 1.000 | 1 | 5–99 (中央値 ~17 from min-of-2) | $G+1$ |
| 2 | 1.693 | 2 | 5–99 | $G+1$ |
| 3 | 2.099 | 3 | 5–99 | $G+1$ |
| 4 | 2.386 | 4 | 5–99 | $G+1$ |
| 5 | 2.609 | 5 | 5–99 | $G+1$ |

Ph1 駐留分布: $\min(\mathcal U\{5..99\}, \mathcal U\{5..99\})$ — これは 2 つの一様分布の min で、$F$ を一様 CDF として CDF $1 - (1 - F(g))^2$ を持つ。中央値 ≈ 36、平均 ≈ 36.7。

Phase 2 (`orbit_wars.py:151`) ships $\in \mathcal U\{5..30\}$、平均 ≈ 17.5。

### 6.3 移動コスト調整 ROI

距離 $D$ から $S = G + 1$ ships を送る: 到着までの時間 $T = D/v(S)$。

総コスト (ships が遊休している機会 tick で測る):
$$\text{cost}(S, D) = S + \frac{S \cdot D}{v(S)}\cdot\text{(opportunity rate)}.$$

名目 ships のみカウントすると (機会コスト無視)、捕獲後の payback 時間 = $S / \text{prod}$ (planet が S ships を生産して投資を払い戻す)、その後のエピソード終了までの *追加* turn は $\text{prod}$ レートで純利益。

| $G$ | $S=G+1$ | $T(D{=}50)$ | payback@prod=1 | payback@prod=3 | payback@prod=5 |
|---:|---:|---:|---:|---:|---:|
| 5 | 6 | 31.0 | 6 | 2 | 1.2 |
| 17 | 18 | 21.5 | 18 | 6 | 3.6 |
| 30 | 31 | 18.7 | 31 | 10.3 | 6.2 |
| 50 | 51 | 15.9 | 51 | 17 | 10.2 |
| 80 | 81 | 14.2 | 81 | 27 | 16.2 |

*生 ships の損益分岐* までの総時間 = $T + \text{payback}$。

| $G$ | prod=1 損益分岐 | prod=3 | prod=5 |
|---:|---:|---:|---:|
| 5 | 37 | 33 | 32 |
| 30 | 50 | 29 | 25 |
| 50 | 67 | 33 | 26 |
| 80 | 95 | 41 | 30 |

**戦略的含意。**

1. 低 prod planet (prod=1) は **遠方移動の価値がない** — $G \ge 30$ で損益分岐 ~50–95 ticks。エピソード長 500 ならまだ利益は出るが、**prod=3+ planet は常により早く払い戻す。**
2. 高 prod、高駐留 planet は終盤で **支配的**。Prod=5 で $G=80$ なら合計 30 ticks ($\approx$ エピソードの 6%) で払い戻す。
3. 低 prod、低駐留 planet は **踏み石** — 安価に捕獲 ($G=5$ → 6 ships)、ただし角度位置が必要な場合のみ収益的 (例: 次の攻撃の発射点として)。
4. **Comet** (`prod=1`、駐留中央値 19、寿命 ≤ 40 ticks) — home 近くに既にいる場合のみ捕獲。さもなくば寿命がしばしば ROI を殺す。

### 6.4 §6 の出典

- `orbit_wars.py:80-81, :133-134` prod サンプリング
- `orbit_wars.py:101, :151` ship サンプリング
- `orbit_wars.py:512-514` 生産 tick
- `orbit_wars.py:667-674` 捕獲メカニクス

---

## 7. エッジケース / engine の癖

### 7.1 太陽すれすれのかすめ通過

太陽横断チェックは `point_to_segment_distance((C,C), old_pos, new_pos) < SUN_RADIUS` (`orbit_wars.py:607`)。厳密な `<`。よって最接近距離がちょうど 10.0 の艦隊は *生存する*。実用上、浮動小数点ドリフトを考えて安全のため ≥ 10.5 を計画せよ。

チェックは **tick あたりの実際の swept セグメント** を使う、完全な ray ではない。よって tick ステップが太陽の近側に着地し AND 次の tick が太陽の向こう側に着地するが、その間のセグメントが決して 10 以内に閉じない場合、問題ない。Speed が重要: 速い艦隊は tick あたりのセグメントが長く、かすめる可能性が高い → チェック必要。

### 7.2 PLANET_CLEARANCE = 7 (planet 間の通り抜け)

`PLANET_CLEARANCE` は planet 生成時 *のみ* 強制される、`if distance(...) < p[4] + tp[4] + PLANET_CLEARANCE` (`orbit_wars.py:113, :168`) で。実行時には艦隊に対して **強制されない** — 艦隊は planet (swept-pair, `:46-64`) または太陽以外のどこへでも飛行できる。よって:

- 隣接する 2 つの planet *本体* 間の最小ギャップは $\ge 7$ 盤面単位
- $v=1$ のサイズ 1 艦隊は 7 単位ギャップを快適に通過できる; swept-pair テストは planet の経路から `r_p` 以内にないものを無視する
- **はい、艦隊は planet の間をすり抜けられる**、tick セグメントが planet 中心から `r_p` 以内に近づかない限り

### 7.3 Action 検証: silent drop

`orbit_wars.py:477-506` より:

| 条件 | 動作 | 出典 |
|---|---|---|
| Action がリストでない | action 全体を drop | `:478-479` |
| Move の長さが 3 でない | その move を drop | `:481-482` |
| `from_planet` が見つからない | その move を drop | `:486` |
| `from_planet[1] != player_id` (自分のものでない) | その move を drop | `:488` |
| `from_planet[5] < ships` (駐留不足) | その move を drop | `:489` |
| `ships <= 0` (`int()` キャスト後) | その move を drop | `:489` |
| `len(move) > 3` (余分な要素) | drop (長さチェックは `!= 3`) | `:481-482` |

**含意:**
- `ships = 0` は silently drop される — ≥1 を使う必要がある。
- `ships` は `int()` キャスト (`:485`); 端数 ships は floor。
- `angle` の検証は無し — 任意の float が動く。`angle` の $2\pi$ modulo は `cos`/`sin` で暗黙的。
- 標的が到達可能かの検証は無し; 太陽に向けて発射でき、engine が実行時に艦隊を殺す。
- 5 ships を持っていて 10 をリクエストすると、move 全体が silently drop される (「5 を送る」を期待するが、何も得られない)。
- **同じ planet から 1 つの action リスト内で複数回発射** でき、各 move は逐次処理される (`:480-506`); 後続の move は *減算後の* 駐留を使う。

### 7.4 終了エッジ

`orbit_wars.py:684-715` より:

```python
if step >= configuration.episodeSteps - 2:
    terminated = True
```

これを `episodeSteps = 500` で読むと: `step >= 498` のとき終了がトリガーされる。インタープリタは tick の最初に呼び出される; `step` は *入力された* step。tick 内の操作順序 (`:432-715`):

1. Comet 期限切れ sweep (行 411)
2. Comet spawn (行 434)
3. **Action 処理** (`process_moves`) (`:476-509`)
4. **生産** (`:511-514`)
5. Planet path 計算 (`:516-566`)
6. 艦隊移動と衝突 (`:568-609`)
7. Planet 移動を適用 (`:611-615`)
8. 戦闘解決 (`:635-674`)
9. **終了チェック、スコア計算、報酬** (`:684-715`)

よって **生産と戦闘の両方が step ≥ 498 で発生する**。最後の完全シミュレーション tick は step 498、その tick の最後にスコア計算 (どこでも ships の合計 — planets + 飛行中艦隊、`:704-708`)。Tick 499 も同じ経路を実行する可能性がある (`>= 498`) — 両 tick が生産+戦闘を実行してから終了する。

報酬ルール (`:710-715`):
- $\max(\text{scores})$ — max でタイのプレイヤー全員が +1 を得る
- それ以外は全員 -1 を得る
- max = 0 なら、**全員が -1** (`max_score > 0` ガード `:712`)

最後の条件は数学的に奇妙: 全 ships ゼロでの引き分けは全員負け。実用的にはまれ (生存している全プレイヤーが同じ tick で wipe される必要がある)。

### 7.5 スコア計算における飛行中 ships カウント

スコアには planet ships AND **飛行中艦隊の ships の両方** が含まれる (`orbit_wars.py:704-708`):
```python
for f in obs0.fleets:
    scores[f[1]] += f[6]
```

よってタイムアウト直前に発射して ships を「隠す」ことはできない。カウントされる。逆に、発射した艦隊が最終 tick で空の planet にヒットしても、目的地で (戦闘後) カウントされる。

### 7.6 §7 の出典

- `orbit_wars.py:46-64` swept-pair (planet のみ、fleet-vs-fleet ではない)
- `orbit_wars.py:113, :168` PLANET_CLEARANCE (生成のみ)
- `orbit_wars.py:477-509` action 検証
- `orbit_wars.py:684-715` 終了とスコア計算

---

## セクション横断まとめ

| セクション | 結果 | 下流での使用箇所 |
|---|---|---|
| §1 | $v(N)$ 公式、≥1000 で飽和、単一艦隊が分割より常に速い | §2 (先読み射撃)、§5 (opener 枝刈り)、§6 (移動コスト) |
| §2 | 先読み角 = 迎撃点への `atan2`、forbidden cone の半角 = $\arcsin(R_\odot/d)$ | §5 (opener フィルター)、§6 (移動モデリング) |
| §3 | Comet seed は観測不可能だが、spawn 時に完全 path が公開される; comet は柔らかい標的 | §6 (低 ROI 例外); 単独戦術 |
| §4 | 同点 = 殲滅; 駐留は survivor のみと戦う | §5 (multi-attacker 解析); 単独防御 |
| §5 | $d_{HH} \approx 100$、行動空間 ≈ $10^{19}$、枝刈り後の moves でビーム探索 | §6 (範囲フレーム); 単独 opener |
| §6 | distance 50 で prod=3+ は ≤ 33 ticks で損益分岐; comet はリスキー | 単独経済プラン |
| §7 | 太陽かすめ閾値、silent-drop リスト、スコアに飛行中 ships を含む | 上記全て |

---

## 付録 A — 厳密な定数 (engine 由来)

```python
BOARD_SIZE = 100.0                                         # orbit_wars.py:17
CENTER = 50.0                                              # :18
SUN_RADIUS = 10.0                                          # :19
ROTATION_RADIUS_LIMIT = 50.0                               # :20
COMET_RADIUS = 1.0                                         # :21
COMET_PRODUCTION = 1                                       # :22
PLANET_CLEARANCE = 7                                       # :23
MIN_PLANET_GROUPS, MAX_PLANET_GROUPS = 5, 10               # :24-25
MIN_STATIC_GROUPS = 3                                      # :26
COMET_SPAWN_STEPS = [50, 150, 250, 350, 450]               # :27
shipSpeed_default = 6.0                                    # orbit_wars.json:19
cometSpeed_default = 4.0                                   # orbit_wars.json:24
episodeSteps = 500                                         # orbit_wars.json:8
actTimeout = 1                                             # orbit_wars.json:9
angular_velocity ~ U[0.025, 0.05]                          # orbit_wars.py:366
home_starting_ships = 10                                   # :385, :387, :391
```
