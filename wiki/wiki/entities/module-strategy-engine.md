---
type: entity-module
title: "StrategyEngine 模块（M3）"
sources:
  - docs/knowledge/掼蛋AI知识应用框架.md
tags:
  - entity-module
  - strategy
  - m3-era
  - core
status: current
related_gua:
  - GUA-030
date: 2026-06-18
---

# StrategyEngine 模块（M3）

## 基本信息

- **路径**：`src/core/strategy_engine.py`
- **时代**：M3
- **层级**：**L2 核心策略层**

## 职责

掼蛋 AI 决策的**核心调度器**：
- 角色定位（主攻/助攻/攻守兼备）
- 组牌算法
- 牌力评分（8分主攻、5-7分兼备、2-4分助攻）
- 调用 [[module-knowledge-retriever]] 补充场景知识
- 调用 module-knowledge-graph 与 module-decision-tree（辅助）

## 关键行为

1. **输入**：当前手牌 + 游戏状态 + L1 校验通过
2. **处理**：牌力评分 → 角色定位 → 组牌 → 场景检索 → 决策树
3. **输出**：候选出牌动作 + 评分

## 接口（推断）

```
decide(state) -> Action
score_hand(hand) -> float
determine_role(score) -> Role
```

## 与 V7 的关系

- V7 NN 引擎**不再使用** L2 角色定位硬逻辑
- 角色定位可能被转化为 NN 的辅助特征或 reward shaping
- 本模块在 V7 阶段**面临重写或废弃**

## 跨域关联

- 上层概念：[[concept-knowledge-layered-decision]]、concept-role-determination
- 关联模块：[[module-knowledge-retriever]]、module-ai-decision-maker
- 引擎映射：[[gua-030]]
