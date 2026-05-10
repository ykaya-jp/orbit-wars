# Data quality audit (2026-05-11 08:30 JST)

## 結論

**bovard top10 episodes dataset を「Top tier 模倣 source」と仮定していたが、実は中堅 player の真似でしかなかった。** これが Phase η v2 IL agent (val acc 0.923) が 4P tournament 0/8 で弱い真因の一つ。

## bovard データ実態

`bovard/orbit-wars-top10-episodes-2026-05-04` description:
> top 10% of episodes ranked by sum of both players' post-episode TrueSkill rating

= **episode の TrueSkill** で top 10%、**player rank ではない**。

500 replay から確認した含有 player rank:

| Player | replay 数 | LB rank (推定) |
|---|---|---|
| Kh0a | 33 | sub-1000 |
| cgrlkc | 32 | 中堅 |
| Orbital Occlusion | 31 | 中堅 |
| glass_256 | 31 | 中堅 |
| Kha Vo | 30 | 中堅 |
| **bowwowforeach** | **0** | LB 1 (1680) ❌ |
| **flg** | **0** | LB 2 (1640) ❌ |
| **Vadasz** | **0** | LB 4 (1539) ❌ |
| **Ebi** | **3** | LB 3 (1570) (の 0.6%) |

## Lakhindar rank1-gameplay (= 真の Top 10 LB)

`lakhindarpal/orbit-wars-rank1-gameplay`:
- 164 replays (48 FFA + 116 1v1)
- **kovi (LB 1480): 102 replays**
- **Shun_PI (LB 1515): 76 replays**

つまり **74% が真の Top 10 LB player の replay**。Lakhindar dataset を IL/PPO の opponent source に使うべきだった。

## Kovi (LB 1480) の FFA stats (25 replays)

- launches/episode: avg **117** (max 258)
- ship size median: **32**
- ship size p90: **107**
- ship size max: 2047
- 艦隊サイズ分布:
  - < 5: 98 件
  - 5-10: 209 件
  - 10-30: 1038 件
  - **30-100: 1238 件 (最多)**
  - 100+: 333 件

## 我家 agent との比較

| 指標 | Kovi (LB 1480) | Rudra (LB 1049) | Zachary (LB ~1000) |
|---|---|---|---|
| 艦隊サイズ median | 32 | ~15 (MIN_SHIPS=10) | < 10 (DECOY_THRESHOLD=8) |
| Top tier に対する比 | 1.0x | 0.5x | 0.3x |

→ 我家は **3-4x 過小艦隊**。但し単純 MIN_SHIPS↑ では駄目 (Phase ε grid sweep で証明: ms=15 → 0/8 vs distractors)。**coordination logic 必要**。

## 改訂アクション (Day 3 以降)

1. **Lakhindar dataset を BC source に追加** (= bovard 50k samples + Lakhindar ~30k samples)
2. **Phase θ PPO opponent に kovi-proxy NN を使う** (= IL on Lakhindar → opponent in PPO curriculum)
3. **rule-base 改良**: artillery aggregation logic 追加 = 複数 home から 1 target に 30+ ship 集中

## ローカル検証の限界

LB 1500+ を相手にした win rate は **local では検証不能**。理由:
- 我家 benchmark = LB 1000-1100 帯のみ
- bowwow / flg の agent は public 公開されてない
- replay ≠ live opponent (replay はこちらの actions に reactできない)

唯一の解: kovi/Shun_PI replay を IL → NN proxy → tournament opponent。Phase θ で実装予定。

## 出典

- bovard description: `kaggle datasets metadata bovard/orbit-wars-top10-episodes-2026-05-04`
- Lakhindar dataset: `kaggle datasets list -s 'orbit-wars rank1'`
- LB rank: `kaggle competitions leaderboard orbit-wars` (2026-05-11 08:25 JST)
- Kovi stats: `data/external/rank1_lakhindar/*_ffa.json` 25 replays
