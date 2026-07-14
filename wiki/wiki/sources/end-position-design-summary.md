---
type: source-summary
title: "残局预处理模块设计摘要"
sources:
  - docs/knowledge/skills/07_opening/end position.md
tags:
  - endgame
  - preprocessor
  - design-doc
status: current
related_gua:
  - GUA-078
date: 2026-07-03
---

# 残局预处理模块设计摘要

## 文件定位

`docs/knowledge/skills/07_opening/end position.md` 是 **EndgamePreprocessor 模块的设计真源**（对应 GUA-078），位于 src/v/nn/endgame/。

## 模块组成

| 子模块 | 职责 |
|--------|------|
| `EndgamePreprocessor` | 主入口，判断是否进入残局模式 |
| `BAOSHU_RULE` | 对手手牌 ≤ 10 触发报数规则 |
| `endgame_rule` | 对手手牌 ≤ 4 触发终局规则 |
| 残局助攻管线 | 队友 pos+2 投喂策略 |
| 冲刺/头游判定 | `sprint`, `has_two_clean_hands` |

## EndgamePipeline 阶段

- **Q0**：是否进入残局？（对手 ≤ 10？）
- **Q1**：战术选择（领出 / 跟上家 / 卡下家 / 让对家）— 对应 GUA-075 推荐引擎
- **Q2**：牌型筛选（banned types 应用）
- **Q3**：执行出牌（送队友 / 自己冲头游）

## 已知问题

- **激活率与实战收益脱节**：模块激活率 66.0%（GUA-078）但副胜仍 0，离线覆盖未转化为实战收益
- 与设计预期矛盾：覆盖率高 ≠ 胜率高

## 关联

- [[endgame-pipeline]] — 残局管线概念页
- [[gua-078]] — 残局预处理器 GUA 条目
- [[gua-075]] — 推荐引擎（四场景）
- [[v7-current-state]] — V7 综合状态
