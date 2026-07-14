---
type: concept
title: "YAML→Python 编译降级"
sources:
  - docs/development/INSTALL_DEPENDENCIES.md
tags:
  - knowledge
  - fallback
  - yf_v4
  - compile
status: current
related_gua: []
date: 2026-06-18
---

# YAML→Python 编译降级

## 定义

yf_v4 知识库的核心机制：将 39 条 YAML 规则**预编译为 Python 模块**，运行时优先加载 Python（无需 yaml 依赖），回退到 YAML。

## 三级降级链

```
1. Python 模块（knowledge_rules.py）   ← 优先，无 yaml 依赖
       ↓ 失败
2. YAML 文件（运行时解析）            ← 需要 pyyaml
       ↓ 失败
3. 内置规则（5 条核心规则）            ← 硬编码 fallback
```

## 编译工具

- `yaml_to_python_converter.py` — YAML → Python 代码转换器
- `knowledge_rules.py` — 编译产物（39 条规则）
- `KnowledgeLoader` — 加载入口（[[module-knowledge-loader]]）
- `KnowledgeTranslator` — 规则转化器（[[module-knowledge-translator]]）

## 优势

- **减少运行时依赖**：生产环境无需 `pyyaml`
- **提升加载速度**：避免运行时 YAML 解析
- **优雅降级**：5 条核心规则保证基本可用性

## 限制

- 39 条动态规则仅在 YAML 或 Python 模块可用时生效
- 内置 fallback 仅有 5 条规则，功能受限

## 适用版本

- yf_v4 / yf_v5（历史版本）
- M3 引擎采用类似模式（wiki-minimax/entities/engine-m3.md）
- V7 引擎（wiki/entities/engine-v7.md）的知识库机制待 Wiki 补充

## 关联

- [[module-knowledge-loader]]
- [[module-knowledge-translator]]
- [[source-install-dependencies-summary]]
