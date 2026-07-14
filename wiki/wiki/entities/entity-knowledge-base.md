---
type: entity
title: "知识库实体（44 条规则 / 三级架构）"
sources:
  - docs/knowledge/README.md
  - docs/knowledge/GUI_INTEGRATION_STATUS.md
tags:
  - knowledge-base
  - rules
  - three-tier
status: current
related_gua: []
date: 2026-06-18
---

# 知识库实体

## 规则统计

- **内置规则**：5 条（硬编码于 L1 Rules）
- **动态生成**：39 条（`src/knowledge/knowledge_rules.py`）
- **总加载**：**44 条规则**

## 三级架构

| 层级 | 名称 | 加载方式 | 文件位置 |
|------|------|----------|----------|
| L1 | Rules | 硬编码（O(1)） | `docs/knowledge/rules/` |
| L2 | Strategy | 内存加载（O(1)） | `docs/knowledge/` 5 个子目录 |
| L3 | Skills | 按需查询+缓存 | 8 个子目录（01~08） |

## L2 Strategy 子目录

- `01_core_strategies` — 核心策略
- `02_role_strategies` — 角色策略
- `03_card_strategies` — 牌型策略
- `04_phase_strategies` — 阶段策略
- `05_common_strategy` — 通用策略

## 加载机制

- **延迟初始化（lazy init）**：加速 GUI 启动
- **YAML→Python 转换**：`yaml_to_python_converter.py` 规避 pyyaml 依赖
- **静态模块**：转换后为 Python 模块，运行时直接 import

## 关联

- concept-knowledge-three-tier-architecture — 架构详解
- [[module-knowledge-enhanced-decision]] — Layer 3 实现
- [[engine-hybrid-decision-v4]] — 调用方
- [[source-knowledge-README-summary]] — 原始资料
