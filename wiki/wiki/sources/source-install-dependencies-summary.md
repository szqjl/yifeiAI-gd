---
type: source-summary
title: "INSTALL_DEPENDENCIES 摘要"
sources:
  - docs/development/INSTALL_DEPENDENCIES.md
tags:
  - dependencies
  - yf_v4
  - source
status: current
related_gua: []
date: 2026-06-18
---

# INSTALL_DEPENDENCIES 摘要

> 来源：`docs/development/INSTALL_DEPENDENCIES.md`（约 1725 字符）
> **版本说明**：本文档涉及 `yf_v4` 知识库编译机制，属历史版本资产

## 依赖列表（requirements.txt）

```
pyyaml>=6.0
psutil>=5.9.0
pytest>=7.0.0
```

## 安装步骤

1. 创建虚拟环境（推荐）
2. `pip install -r requirements.txt`
3. 运行 `dependency_check.py` 验证依赖完整性

## 知识库编译机制（yf_v4）

- **核心思想**：将 39 条 YAML 规则编译为 Python 模块
- **工具**：`yaml_to_python_converter.py`
- **运行时加载**：优先加载 Python 模块（无需 yaml 依赖），回退到 YAML
- **目的**：减少运行时依赖、提升加载速度
- **详见**：[[concept-yaml-python-fallback]]

## 关键模块

- [[module-knowledge-loader]] — 知识加载器
- [[module-knowledge-translator]] — 规则转化器
- `yaml_to_python_converter` — YAML → Python 转换工具
- `knowledge_rules` — 编译后的 39 条规则 Python 模块
- `dependency_check` — 依赖检查工具

## 关联

- [[concept-yaml-python-fallback]] — YAML → Python 降级机制
- wiki-minimax/entities/engine-m3.md（M3 引擎使用类似规则加载模式）
