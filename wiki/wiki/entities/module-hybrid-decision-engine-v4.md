---
type: entity-module
title: "V4 决策引擎（Layer 1/2/3 集成）"
sources:
  - docs/knowledge/GUI_INTEGRATION_STATUS.md
tags:
  - v4-engine
  - layer-3
  - decision-engine
status: current
related_gua: []
date: 2026-06-18
---

# V4 决策引擎

## 文件位置

- 主类：`HybridDecisionEngineV4`（`src/decision/hybrid_decision_engine_v4.py`）
- Layer 3 集成点：第 266 行 `_enhance_candidates` 方法

## 三层架构

| Layer | 名称 | 职责 |
|-------|------|------|
| 1 | Base | 候选动作生成（硬编码规则） |
| 2 | Hybrid | 多策略融合（MCTS + 启发式） |
| 3 | **Knowledge Enhanced** | 知识库增强（44 条规则） |

## 决策流程

```
Layer 1 (候选生成) → Layer 2 (候选评估) → Layer 3 (知识增强) → 选择最优
   ↓                     ↓                       ↓
硬编码规则           MCTS/启发式             44 条规则
```

## 关联

- [[engine-hybrid-decision-v4]] — 引擎实体
- [[module-knowledge-enhanced-decision]] — Layer 3 实现
- [[entity-knowledge-base]] — 44 条规则
- [[source-GUI_INTEGRATION_STATUS-summary]] — 集成状态
