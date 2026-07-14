---
type: source-summary
title: "YAML依赖问题修复说明 — 摘要"
sources:
  - docs/knowledge/YAML_DEPENDENCY_FIX.md
tags:
  - knowledge
  - yaml
  - dependency
  - graceful-degradation
  - m3-era
status: current
related_gua: []
date: 2026-06-18
---

# YAML依赖问题修复说明 — 摘要

## 来源

- **原始文件**：`docs/knowledge/YAML_DEPENDENCY_FIX.md`（1249 字符）
- **涉及模块**：`src/knowledge/knowledge_loader.py`、`src/knowledge/knowledge_translator.py`

## 核心问题

`KnowledgeLoader` 与 `KnowledgeTranslator` 两个模块依赖 PyYAML 解析知识库规则文件，但 `requirements.txt` 中的 `pyyaml>=6.0` 在某些部署环境可能未安装。

## 修复方案：优雅降级（Elegant Degradation）

- **未安装 PyYAML 时**：
  - `KnowledgeLoader`：仅使用内置硬编码规则，跳过 YAML 规则文件加载
  - `KnowledgeTranslator`：所有 YAML 相关 API 返回空或空操作（no-op）
- **已安装 PyYAML 时**：完整功能可用

## 影响与限制

- 知识库动态扩展能力受限——无法在运行时加载/重载新的 YAML 规则
- 编译进代码的内置规则仍可用，决策系统可降级运行
- 后续如需动态知识更新，需补齐 PyYAML 依赖

## 跨域关联

- 关联到 [[concept-knowledge-layered-decision]]：L1 内置规则对应"无 PyYAML 时的降级路径"
- 关联到 [[module-knowledge-loader]] 与 [[module-knowledge-translator]] 模块实体
- 与 concept-elegant-degradation 概念同源（待创建概念页时合并）

## 待跟进

- 评估是否需要为 PyYAML 缺失场景创建 GUA（如 GUA-062）
- V7 NN 引擎是否仍采用 YAML 知识库？还是转为 NN 嵌入/向量库？
