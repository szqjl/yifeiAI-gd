---
type: source-summary
title: "规则摘要：07 升级规则"
sources:
  - docs/knowledge/rules/01_basic_rules/07_upgrade_rules.md
tags:
  - rules
  - upgrade
  - ranking
status: current
related_gua:
  - GUA-033
date: 2026-06-18
---

# 规则摘要：07 升级规则

## 来源

- 原始文件：`docs/knowledge/rules/01_basic_rules/07_upgrade_rules.md`（1684 字符）

## 核心内容

### 三等级字段分离（关键）

| 字段 | 含义 | 作用域 | 更新时机 |
|------|------|--------|----------|
| `curRank` | 本副级牌 | 全场共用 | 每副开始时设定 |
| `selfRank` | 我方队伍等级 | 跨副累积 | 仅获胜方升级 |
| `oppoRank` | 对方队伍等级 | 跨副累积 | 仅获胜方升级 |

⚠️ **数据解读要点**：
- `curRank` ≠ `selfRank` ≠ `oppoRank`
- 仅获胜方的 `selfRank` / `oppoRank` 在副结束时更新
- 批跑数据解析时，三者必须分别处理

### 升级表

| 己方当前级 | 上游名次 | 升/降级数 |
|------------|----------|-----------|
| 2-9 | 头游 | +3 |
| 2-9 | 二游 | +2 |
| 2-9 | 三游 | +1 |
| 2-9 | 末游 | 不变 |
| 10 / J | 头游 | +2 |
| 10 / J | 二游 | +1 |
| 10 / J | 三游 | 不变 |
| 10 / J | 末游 | -1 |
| Q / K | 任意 | +1 / -1 |
| A | 头游 | 双上即赢局 |
| A | 未双上 | 连续 2 副未赢 → 降回 2 |

### 过A 赢局规则

- **赢局条件**：`selfRank == A` 且本副双上
- **A 级降级**：`selfRank == A` 连续 2 副未赢 → 降回 2
- **平局判负**：A↔2 循环达 50 次 → 判平

## 与其他页面的关系

- 上游：[[source-rules-06-game-flow-summary]]
- 下游：[[source-rules-08-basic-concepts-summary]]
- 相关概念：[[concept-three-rank-fields]]、[[concept-pass-a-rule]]
- 关联 GUA：wiki-minimax/entities/gua-033.md

## 关键平台动作

- 进贡：`Tribute` JSON 动作
- 还贡：`Back` JSON 动作
- 抗贡：`AntiTribute` JSON 动作
