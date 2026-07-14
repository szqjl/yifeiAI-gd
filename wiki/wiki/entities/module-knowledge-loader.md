---
type: entity-module
title: "KnowledgeLoader 知识加载器"
sources:
  - docs/development/INSTALL_DEPENDENCIES.md
tags:
  - module
  - knowledge
  - fallback
status: current
related_gua: []
date: 2026-06-18
---

# KnowledgeLoader 知识加载器

## 模块信息

| 项 | 值 |
|----|-----|
| 文件路径 | `src/knowledge/knowledge_loader.py` |
| 用途 | 知识加载器，支持优雅降级 |

## 核心特性：优雅降级

加载优先级（从高到低）：

```
1. Python 模块（knowledge_rules.py，39 条规则）   ← 编译产物，无需 yaml
       ↓ 失败
2. YAML 文件（运行时解析）                       ← 需要 pyyaml
       ↓ 失败
3. 内置规则（5 条核心规则）                      ← 硬编码 fallback
```

## 降级行为

| 可用资源 | 可用规则数 |
|----------|-----------|
| Python 模块 | 39 条 |
| 仅 YAML | 39 条 |
| 无 yaml 且无 Python | **5 条（核心内置）** |

## 使用方

- yf_v4 / yf_v5 知识库客户端
- M3 决策引擎（类似模式）

## 关联模块

- [[module-knowledge-translator]] — 规则转化器
- `knowledge_rules` — 编译后的 39 条规则 Python 模块
- `yaml_to_python_converter` — YAML → Python 转换工具
- `dependency_check` — 依赖检查工具

## 关联概念

- [[concept-yaml-python-fallback]] — YAML → Python 编译降级机制
- [[source-install-dependencies-summary]] — 安装与依赖
