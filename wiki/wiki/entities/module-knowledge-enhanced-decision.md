---
type: entity-module
title: "知识增强决策模块（Layer 3）"
sources:
  - docs/knowledge/GUI_INTEGRATION_STATUS.md
tags:
  - knowledge-enhanced
  - layer-3
  - v4-engine
status: current
related_gua: []
date: 2026-06-18
---

# 知识增强决策模块（Layer 3）

## 文件位置

- 主实现：`src/knowledge/knowledge_enhanced_decision.py` 第 123 行 `enhance_candidates`
- 规则加载：`src/knowledge/knowledge_rules.py`（39 条自动生成规则）
- YAML 转换：`src/knowledge/yaml_to_python_converter.py`

## 核心职责

Layer 3 知识增强在 `HybridDecisionEngineV4` 决策流程中的位置：
```
候选动作生成 → enhance_candidates (Layer 3) → 选择最优
```

## 加载流程

1. `yaml_to_python_converter` 将 YAML 规则转换为 Python 模块（静态）
2. `knowledge_rules.py` 提供 39 条动态生成规则
3. 启动时合并：5 内置 + 39 动态 = **44 条规则**
4. 决策时通过 `enhance_candidates` 注入候选动作评分

## 关联

- [[engine-hybrid-decision-v4]] — 调用方
- [[entity-knowledge-base]] — 44 条规则
- concept-knowledge-three-tier-architecture — 三级架构
- [[source-GUI_INTEGRATION_STATUS-summary]] — 集成状态
