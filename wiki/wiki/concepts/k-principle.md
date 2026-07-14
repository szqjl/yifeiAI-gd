---
type: concept
title: "K 原则：掼蛋组牌回收能力判断"
sources:
  - docs/guandan-brain/iterations/v7-grouping-v2-gua062.md
  - sources/v7-grouping-v2-gua062-summary.md
tags:
  - concept
  - v7
  - grouping
  - K-principle
  - scoring
status: current
related_gua:
  - GUA-062
  - GUA-061
date: 2026-06-18
---

# K 原则：掼蛋组牌回收能力判断

## 定义
**K 原则**是掼蛋组牌阶段判断"某个牌型能否被级牌回收"的规则。
- 核心问题：在对手某回合打出某牌型后，级牌是否还留在我方手中？若留，则该牌型"打不光"，应避免组入
- 命名来源：级牌为 K 时最难处理（K 是最大单牌但又最易被管），故以 K 为代表场景

## 三层规则

### 1. 降级规则
- **级牌为 K 时**：K 原则降为 Q
- 含义：只需判断"Q 能否回收"，比 K 回收的门槛更低
- **原因**：K 本身难以打光（任何 K 都可能被管），将"能否回收"标准放宽到 Q 级别

### 2. 豁免规则
- **残局豁免**：当手牌 ≤ 10 张时，K 原则整体豁免
- **原因**：残局阶段手数有限，回收不再是核心约束
- 注意：见 [[round-vs-game]]——"局/副"口径需对齐

### 3. 兜底规则
- **炸弹本身是回收手段**：炸弹（无论是否登基）不需 K 原则判断
- 原因：炸弹优先级最高，被管的概率最低
- **不需 K 原则的牌型**：钢板、木板、三张
- 原因：这些牌型组合天然被级牌组合克制，K 原则判定困难

## 优先级冲突
当多个规则同时触发时（如"级牌为 K + 残局"），优先级待 GUA-062 实施时明确。

## 应用范围
- **当前**：[[gua-062]] 实施中，用于 `_score_recovery()` 模块
- **历史**：[[gua-061]]（closed）未建模回收能力，故未涉及 K 原则
- **来源**：`docs/guandan-brain/iterations/v7-grouping-v2-gua062.md`

## 关联概念
- wiki/concepts/grouping-scoring-v2.md：K 原则是 4 维加权中"回收能力"维度的核心
- [[gua-062]]：K 原则的工程实施入口
```

---
