---
type: source-summary
title: "掼蛋AI知识应用框架 — 摘要"
sources:
  - docs/knowledge/掼蛋AI知识应用框架.md
tags:
  - knowledge
  - architecture
  - m3-era
  - legacy
  - layered-decision
status: outdated
related_gua:
  - GUA-030
  - GUA-031
date: 2026-06-18
encoding_note: "原文存在大量中文字符乱码（'浜'→'个'、'鐗'→'牌'、'妗'→'案'等），本摘要已尽力还原。原始文档可读性差。"
---

# 掼蛋AI知识应用框架 — 摘要

> ⚠️ **定位声明**：本文档描述的是 **M3 规则引擎**时代的知识应用架构。M3 已被标记为"达瓶颈"，V7 NN 引擎是当前主迭代方向。本框架作为 V7 设计的**反向参照**保留。

## 来源

- **原始文件**：`docs/knowledge/掼蛋AI知识应用框架.md`（13188 字符）
- **涉及模块**：
  - `src/core/game_rules.py`（L1）
  - `src/core/strategy_engine.py`（L2）
  - `src/core/knowledge_retriever.py`（L3）
  - `src/core/advanced_reasoning.py`（L4）
  - 辅助：`knowledge_graph.py`、`decision_tree.py`、`ai_decision_maker.py`

## 核心架构：分层决策系统（L1-L4）

| 层级 | 名称 | 实现模块 | 内容 |
|------|------|----------|------|
| **L1** | 硬编码规则 | `GameRules` | 五条高压线、牌型合法性、平台变量名 |
| **L2** | 核心策略 | `StrategyEngine` | 角色定位、组牌算法、牌力评分 |
| **L3** | 场景策略 | `KnowledgeRetriever` | 开局/中局/残局场景规则检索（按需+缓存）|
| **L4** | 高级技巧 | `AdvancedReasoning` | 心理战、对手建模、牌璇推断 |

## 关键设计原则

1. **知识覆盖率 / 决策准确率 / 胜率提升**——知识应用的三指标
2. **按需检索 + 缓存**：避免一次性加载 850+ 知识点
3. **优雅降级**：YAML 依赖问题 的解决方式
4. **平台变量名规范统一**：Single/Pair/Bomb 等命名贯穿代码与 JSON

## 知识库规模

- 17 个原始技能文档
- 约 850 个知识点估计
- 覆盖 8 大类：基础规则、竞赛规则、高级规则、基础技巧、主攻技巧、助攻技巧、通用技巧、心理技巧、开局、残局

## 关键技能清单

- 出炸技巧（第 16-19 篇）
- 对子先行（第 26 篇）
- 卡下家（第 28 篇）
- 送对家（第 30 篇）
- 处理弱路（第 12 篇）
- 残局逼炸为先（第 23 篇）
- 尾牌原理（第 13、14 篇）

## 与 V7 主迭代的张力

| 维度 | M3 框架 | V7 引擎 |
|------|---------|---------|
| 决策方式 | 规则分层调用 | NN 端到端 |
| 知识载体 | YAML + 硬编码 | NN 权重 + 特征工程 |
| 可解释性 | 高（每层可追踪） | 低（黑盒） |
| 上限 | 已被判定达瓶颈 | 期望突破瓶颈 |

## 跨域关联

- 直接对应 [[concept-knowledge-layered-decision]]
- 核心规则对应 [[concept-five-high-voltage-rules]]
- 命名规范对应 [[concept-platform-variable-naming]]
- 角色定位对应 concept-role-determination
- 引擎映射到 [[gua-030]]（原则→引擎映射）
