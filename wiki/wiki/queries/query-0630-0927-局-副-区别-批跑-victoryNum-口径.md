---
type: query-answer
title: "局 副 区别 批跑 victoryNum 口径"
date: 2026-06-30
sources:
---

# 局 副 区别 批跑 victoryNum 口径

# 局 vs 副 · 批跑 victoryNum 口径

## 一、核心区分（已定音）

| 术语 | 严格定义 | 数据源 |
|------|----------|--------|
| **副** (round) | 108 张发完 → 4 人完牌 → order 确定 | `rounds[]` |
| **局** (game) | 从 2 打到 A 并在 A 级双上过关 | `games[]` |
| **圈** (turn) | 一手出牌 | 每副多圈 |
| **轮** (match) | 通常 ≈「局」，口语混用 | — |

**数量关系**：1 局 ≈ 6 副（平均），实测 `target-games 1` → **59 副**。[{4}][{9}]

## 二、victoryNum 在批跑中的角色

### 数据结构

- **类型**：四元组 `[P0, P1, P2, P3]`，`0+2` 一队 vs `1+3` 一队
- **批跑只读 `[0] vs `[1]``（禁止四席相加）；`[2]`、`[3]` 是冗余副本 [{1}]

### 局级 vs 副级 victoryNum 含义

| 字段 | 层级 | 含义 |
|------|------|------|
| `gameResult.victoryNum` | **局级** | 本局升级数 (0/1/2/3) |
| `act.stage.play.curRank` | **副级** | 当前副的 rank，跨副重置 |

### 末级分布（局级）

| victoryNum | 含义 |
|------------|------|
| 0 | 本局未升级 |
| 1 | +1 级（标准局）|
| 2 | +2 级（大胜）|
| 3 | 双上 / 过 A（完胜）|

## 三、KPI 口径选择（已定音）

> **局胜率是胜率 KPI 的正确口径**，副胜率会虚高。[{4}]

| 指标 | 推荐口径 |
|------|----------|
| 胜率 (vs lalala) | **局胜率**（`games[]`） |
| 平均升级数 | 局级聚合 |
| A 级过关率 | 局级（必含 A→双上）|
| 决策下钻 | 副级（`rounds[]`） |

## 四、双口径分析（必走）

V7 批跑分析**必须同时跑两套**，避免「局 ≠ 副」统计陷阱：[{1}][{3}][{5}]

```bash
# 局级
python scripts/launchers/v-nn/analyze_v7_rounds.py results/xxx/

# 副级（curRank 分组，口径校验）
python scripts/launchers/v-nn/analyze_v7_round_levels.py \
  --records game_records_v7/ --output reports/v7_round_analysis.csv
```

## 五、批末自检（GUA-033 规范）

校验优先级：[{1}]

| 优先级 | 条件 | 处理 |
|--------|------|------|
| **P1** | `[0]+[1]==batch_games` 且 `[0]==[2]` 且 `[1]==[3]` | 校验通过 |
| **P2** | 任一不等 | 走 fallback |
| **P3** | fallback 仅 `batch_games==1` 时认领 `curTimes==1` | 特殊场景 |

`victory_num != expected_victory_num(batch_games)` → **WARNING + skip KPI**。

## 六、双轨追踪架构（代码侧）

| 层级 | 触发 | 输出 | 存储 |
|------|------|------|------|
| 副级 | 4 人完牌 | order、升级数 | `game_scores_*.json` 的 `rounds[]` |
| 局级 | A 双上 / A↔2 循环 50 次 | 胜负 + 升级轨迹 | `games[]` |

**yf1 独占写 JSON，yf2 仅打日志**——规避 race condition。[{8}]

## 七、当前可见数据

| 指标 | 数值 | 来源 |
|------|------|------|
| V7 vs lalala 副级胜率 | **3.0%** | [{1}][{3}] |
| 跨越目标 | 30% | [{3}] |
| 胜率目标 | >90%（PHASE3） | [{3}] |

⚠️ Wiki **未记录** victoryNum=0/1/2/3 的末级分布明细，也未记录最近批跑的局数/副数/种子/时间戳。

## 八、关键引用

- [{1}] analyze_v7_rounds 末级分布 victoryNum 统计
- [{3}] V7 批跑数据统计 局级/副级
- [{4}] **局 ≠ 副**（核心口径）
- [{5}] 批跑执行器全景（双口径原则）
- [{8}] 胜负追踪架构（副级 + 局级）
- [{9}] 离线平台 v1006 协议与参数

## 一句话总结

**victoryNum 是局级字段**（`gameResult.victoryNum`，0~3），批跑只读 `[0] vs [1]` 判队胜负；KPI 口径以**局胜率**为准，副级胜率仅用于下钻诊断——这是已定音的核心口径，所有 V7 批跑分析必须双轨（局级 + 副级）跑两套。
