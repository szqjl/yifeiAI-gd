---
tags: [M3, guards, GUA-031, GUA-032, GUA-034, GUA-035, GUA-036]
created: 2026-05-31
updated: 2026-06-02
topic: M3 传牌/算牌/残局 guard
related: [[M3-Development]], [[m3-strategy-gua026-029]]
---

# M3 Guard 系列：传牌 / 算牌 / 残局（GUA-031 ~ GUA-036）

> 来源：[[ITERATIONS]] 2026-05-31 ~ 2026-06-02

## GUA-031：传牌 guard

| 日期 | 迭代 | 关键内容 |
|------|------|----------|
| 2026-05-31 | 登记 | PASS-P02/P03/P04 + P-F02 扩全牌型 |
| 2026-05-31 | 落地 | `_gua031_passive_teammate_yield`、`_gua031_active_min_single`、`_gua031_filter_singles_for_next1`、`_gua031_active_feed_five`；pytest **7 passed**；**GUA-031 closed** ✅ |

## GUA-032：记牌算牌

| 日期 | 迭代 | 关键内容 |
|------|------|----------|
| 2026-05-31 | 登记 | CALC-M01/M02/M03；`remain_cards_classbynum` stale 发现 |
| 2026-05-31 | 落地 | `sync_remain_cards_classbynum`；CALC-M01 被动炸过滤；CALC-M03 顺子 5/10 降权；MEM-M02 炸弹记忆；pytest **6 passed**；**GUA-032 closed** ✅ |

## GUA-034：残局拦头游

| 日期 | 迭代 | 关键内容 |
|------|------|----------|
| 2026-06-01 | 登记 | END-M01~M04（round 38 复盘） |
| 2026-06-01 | 方案评审 | 方向 A–E 评估 → **选定方向 A** |
| 2026-06-01 | 方向 A 实施 | `_is_solo_sprint`、`_gua034_solo_active_pick`、`_gua034_solo_beat_single`/`_beat_pair`；pytest **6 passed**；**GUA-034 closed** ✅ |

## GUA-035：END-M02+ 对手剩张过滤

| 日期 | 迭代 | 关键内容 |
|------|------|----------|
| 2026-06-01 | 登记 + 路线图 | END-M02+-01~04；两手枚举不进 M3 |
| 2026-06-01 | 实施 | `_gua035_solo_opponent_rests`、`_gua035_solo_wind_pick`（1/2/5 张过滤）；pytest **6 passed**；**GUA-035 closed** ✅ |
| 2026-06-01 | 净盘 9+24 局 | 队胜 26/33（78.8%） |

## GUA-036：控权 + 接风配合

| 日期 | 迭代 | 关键内容 |
|------|------|----------|
| 2026-06-01 | 登记 | CTRL/WIND/TEAM-P01~P02 |
| 2026-06-01 | 实施 | `_gua036_pick_min_straight_beat`、`_Straight` 重写；pytest **6 passed**；回归 42 passed；**GUA-036 closed** ✅ |

### KPI 观测（S6~S9）

| 样本 | 队胜率 | 备注 |
|------|--------|------|
| S6 (12局, GUI) | 75.0% | GUA-036 后首跑 |
| S7 (12局, CLI) | 66.7% | |
| S8 (12局, CLI) | 41.7% | 批2 `[0,3,0,3]` ⚠️ |
| S9 (12局, CLI) | 50.0% | |
| **S6~S9 合计** | **52.2% (36/69)** | |

**关键发现**：GUA-036 显著差于 GUA-035（78.8% vs 52.2%，p=0.009）。`[0,3,0,3]` 在 GUA-036 出现 2 次，GUA-035 出现 0 次。结论：GUA-036 非 solo 场景下限更差，待 CALC-M04/M05 修复。
