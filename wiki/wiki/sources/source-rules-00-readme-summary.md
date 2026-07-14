---
type: source-summary
title: "01_basic_rules 目录索引与真源声明"
sources:
  - docs/knowledge/rules/01_basic_rules/README.md
tags:
  - rules
  - index
  - source-of-truth
status: current
related_gua: []
date: 2026-06-18
---

# 01_basic_rules 目录索引与真源声明

## 文档定位

`docs/knowledge/rules/01_basic_rules/README.md` 是掼蛋规则知识库的**目录索引页**，同时承担**真源声明**职责。

## 核心职责

1. **去重索引**：在多个 PR / 文档版本存在时，提供唯一的权威入口
2. **真源声明**：明确该目录下的规则描述为**单一可信来源**（Single Source of Truth）

## 与 Wiki 系统的关系

- 本目录下的规则页（[[source-rules-01-game-introduction-summary]]、[[source-rules-02-quick-start-summary]] 等）均挂在此索引下
- 所有 entity-gua 涉及规则引用的，必须指向 `01_basic_rules/` 下的具体页，**不得从其他 PR 转载的规则文档引用**

## 后续页面规划

`01_basic_rules/` 目录预计包含的子文档（部分已有 Wiki 摘要）：

| 子文档 | 已有 Wiki 摘要 |
|--------|----------------|
| 01 游戏简介 | [[source-rules-01-game-introduction-summary]] |
| 02 快速开始 | [[source-rules-02-quick-start-summary]] |
| 04 牌型指南 | [[source-rules-04-card-types-guide-summary]] |
| 05 发牌分布 | [[source-rules-05-card-distribution-summary]] |
| 06 牌局流程 | [[source-rules-06-game-flow-summary]] |
| 07 升级规则 | [[source-rules-07-upgrade-rules-summary]] |
| 08 基础概念 | [[source-rules-08-basic-concepts-summary]] |

## 注意事项

- 本页为元索引页，**不承载具体规则内容**
- 任何新规则文档应先入 `01_basic_rules/`，再建立 Wiki 摘要
