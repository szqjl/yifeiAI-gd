---
type: concept
title: "规则嵌入 vs 牌型内嵌：M1 与 lalala 范式之争"
sources:
  - docs/guandan-brain/reviews/M1_vs_lalala_TECHNIQUE_cursor.md
  - docs/guandan-brain/V7-实施方案.md
tags:
  - paradigm
  - m1
  - lalala
  - architecture
status: current
related_gua:
  - GUA-061
  - GUA-022
date: 2026-06-18
---

# 规则嵌入 vs 牌型内嵌：M1 与 lalala 范式之争

## 概念定义

掼蛋 AI 决策引擎的两种**根本性架构范式**对比，是当前 V7 路线选择的核心依据。

## 范式对照

| 维度 | M1 阶段分层 | lalala 牌型内嵌 |
|------|-------------|-----------------|
| **决策粒度** | 阶段分层（CardTypeHandlerFactory / phase_handlers） | 牌型内嵌决策 |
| **决策流程** | 先分类 → 后填值 | 牌型匹配阶段同步决策大小/数量 |
| **代码复杂度** | 高（4209 行，多模块） | 低（集中式） |
| **可维护性** | 路径债严重 | 较好 |
| **决策维度** | 缺口（pass_num / numofnext / numofgreaterPos） | 完整 |
| **当前胜率** | 0%（GUA-022，8 轮迭代后） | 100%（对手） |

## 范式选择的工程含义

### M1 阶段分层的问题
1. **过度设计**：分类与决策分离导致策略表达受限
2. **路径债**：4209 行分散代码，修改成本高
3. **决策缺口**：关键上下文字段接线不全

### lalala 牌型内嵌的优势
1. **决策完整**：所有维度在牌型匹配时一次性决定
2. **代码集中**：易于维护与修改
3. **实战验证**：作为对手时胜率显著高于 M1

## 评审视角差异

- **Cursor 评审**：自评 83%，强烈建议 M1 边缘化
- **opencode 评审**：自评 85%，对 M1 子策略仍持谨慎乐观

## V7 的取舍

V7 NN 引擎选择**学习 lalala 的牌型内嵌思路**——通过 188 维特征 + 端到端神经网络，将决策逻辑统一在模型内部，规避 M1 范式的工程化困境。

## 关联页面

- [[engine-m1]]
- wiki/entities/engine-v7.md
- [[M1_vs_lalala_TECHNIQUE_cursor-summary]]
- [[GUA-061]]
- [[GUA-022]]
