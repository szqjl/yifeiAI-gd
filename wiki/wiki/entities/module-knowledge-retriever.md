---
type: entity-module
title: "KnowledgeRetriever 模块"
sources:
  - docs/knowledge/掼蛋AI知识应用框架.md
tags:
  - entity-module
  - knowledge
  - m3-era
status: current
related_gua:
  - GUA-030
date: 2026-06-18
---

# KnowledgeRetriever 模块

## 基本信息

- **路径**：`src/core/knowledge_retriever.py`
- **时代**：M3
- **层级**：**L3 场景策略层**

## 职责

按需检索 + 缓存机制——根据当前游戏场景（开局/中局/残局）匹配并返回相关知识条目。

## 关键行为

- **按需加载**：避免一次性加载 850+ 知识点
- **缓存机制**：LRU 或场景键缓存
- **场景键**：当前阶段、当前牌力、对手历史行为

## 接口（推断）

```
retrieve(scene_key) -> List[Knowledge]
cache_put(key, value) -> None
clear_cache() -> None
```

## 与 L1-L2-L4 的交互

```
L2 (StrategyEngine) 调用 → L3 (本模块) 返回场景知识 → 注入决策上下文
```

## 跨域关联

- 上层概念：[[concept-knowledge-layered-decision]]
- 关联模块：[[module-strategy-engine]]、[[module-knowledge-loader]]
- 引擎映射：[[gua-030]]
