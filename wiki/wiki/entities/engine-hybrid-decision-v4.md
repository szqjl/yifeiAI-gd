---
type: entity-engine
title: "V4 混合决策引擎（Layer 3 Knowledge Enhanced）"
sources:
  - docs/knowledge/GUI_INTEGRATION_STATUS.md
  - docs/knowledge/platform-data-interpretation.md
tags:
  - v4-engine
  - knowledge-enhanced
  - layer-3
  - decision-engine
status: current
related_gua: []
date: 2026-06-18
---

# V4 混合决策引擎

## 定位

`HybridDecisionEngineV4` 是当前主迭代的决策引擎，从 M3 规则引擎向 Layer 3 Knowledge Enhanced 演进。

## 演进链

```
M1 → M2 → M3 → HybridDecisionEngineV4 (Layer 1/2/3)
                              ↓
                            V7 NN（规划中）
```

## 三层架构

| Layer | 职责 | 实现 |
|-------|------|------|
| 1 | 候选动作生成 | 硬编码规则 |
| 2 | 多策略融合 | MCTS + 启发式 |
| 3 | 知识增强 | 44 条规则（`enhance_candidates`） |

## 关键调用点

- 第 266 行 `_enhance_candidates` — Layer 3 注入候选动作
- 决策流程：`候选生成 → Layer 2 评估 → Layer 3 增强 → 选择最优`

## 与 M3 的区别

- M3：纯规则引擎（已瓶颈）
- V4：引入知识库增强，可动态加载 39 条规则
- V4 是 V7 NN 引擎迁移前的过渡形态

## 关联

- wiki-minimax/entities/engine-m3.md — 前代主决策引擎
- [[module-hybrid-decision-engine-v4]] — 模块详情
- [[module-knowledge-enhanced-decision]] — Layer 3 实现
- [[entity-knowledge-base]] — 44 条规则
