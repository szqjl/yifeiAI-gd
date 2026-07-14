---
type: entity-module
title: "KnowledgeTranslator 规则转化器"
sources:
  - docs/development/INSTALL_DEPENDENCIES.md
tags:
  - module
  - knowledge
  - translator
status: current
related_gua: []
date: 2026-06-18
---

# KnowledgeTranslator 规则转化器

## 模块信息

| 项 | 值 |
|----|-----|
| 文件路径 | `src/knowledge/knowledge_translator.py` |
| 用途 | 规则转化器，优先 Python 模块、回退 YAML |

## 核心逻辑

```python
def translate(rule_id: str) -> Rule:
    # 1. 优先从 Python 模块查找
    rule = lookup_in_python_module(rule_id)
    if rule:
        return rule
    
    # 2. 回退到 YAML
    rule = lookup_in_yaml(rule_id)
    if rule:
        return rule
    
    # 3. 抛出未找到异常
    raise RuleNotFound(rule_id)
```

## 与 KnowledgeLoader 的差异

| 模块 | 职责 |
|------|------|
| [[module-knowledge-loader]] | 加载规则集合（批量） |
| **KnowledgeTranslator** | 单条规则查找与转化 |

## 关联

- [[module-knowledge-loader]]
- [[concept-yaml-python-fallback]]
- `yaml_to_python_converter` — 离线转换工具
- `knowledge_rules` — 编译产物
