---
type: concept
title: "三等级字段（curRank / selfRank / oppoRank）"
sources:
  - docs/knowledge/rules/01_basic_rules/07_upgrade_rules.md
  - docs/knowledge/rules/01_basic_rules/08_basic_concepts.md
tags:
  - rules
  - data-fields
  - batch
  - critical
status: current
related_gua:
  - GUA-033
date: 2026-06-18
---

# 三等级字段（curRank / selfRank / oppoRank）

## 核心定义

掼蛋平台返回的三个「等级」字段，**作用域完全不同**，是批跑数据解析的核心易错点。

| 字段 | 含义 | 作用域 | 更新时机 |
|------|------|--------|----------|
| `curRank` | **本副**级牌 | 全场 4 人共用 | 每副开始时由平台确定 |
| `selfRank` | 我方队伍等级 | 我方 2 人累积 | 仅**获胜方**升级时更新 |
| `oppoRank` | 对方队伍等级 | 对方 2 人累积 | 仅**获胜方**升级时更新 |

## 关键区分

### `curRank`（本副级牌）

- 表示**当前这副牌**中，哪张牌被选为「级牌」（每副可能变化）
- 逢人配 = `H + curRank`（红桃 + 当前级牌）
- 每副开始时由平台发牌决定，全场 4 人**共享同一 curRank**
- **不是**队伍等级

### `selfRank` / `oppoRank`（队伍等级）

- 表示**跨副累积**的队伍等级（2-3-4-...-A）
- 升级表见 [[source-rules-07-upgrade-rules-summary]]
- 仅**获胜方**升级时更新（即平局时双方都不变）
- 平台 A 级赢局需 selfRank=A 且本副双上（见 [[concept-pass-a-rule]]）

## 批跑数据处理建议

```python
# 推荐处理流程
for episode in match_data:
    curRank = episode.curRank        # 本副级牌（不变）
    for player in [self_team]:
        if episode.winner == self_team:
            selfRank += victoryNum   # 升级
        # oppoRank 不变
```

## ⚠️ 常见误读

| 误读 | 后果 |
|------|------|
| 把 `curRank` 当作 `selfRank` | 升级计算全部错误 |
| 平局时升级 | 违反「仅获胜方升级」规则 |
| `selfRank` 在每副更新 | 忽略累积性 |

## 关联页面

- 来源：[[source-rules-07-upgrade-rules-summary]]、[[source-rules-08-basic-concepts-summary]]
- 概念：[[concept-pass-a-rule]]、concept-round-vs-game-multi-level
- 关联 GUA：wiki-minimax/entities/gua-033.md（victoryNum 验证与三等级字段解析）
- 引擎：wiki-minimax/entities/engine-m3.md
