---
type: source-summary
title: "YAML 依赖降级矩阵"
sources:
  - docs/knowledge/YAML_DEPENDENCY_ANALYSIS.md
tags:
  - knowledge
  - yaml
  - dependency
  - deployment
status: current
related_gua:
  - GUA-032
date: 2026-06-17
---

# YAML 依赖降级矩阵

## 文件位置
- 路径：`docs/knowledge/YAML_DEPENDENCY_ANALYSIS.md`

## 核心问题

**YAML 缺失 → 29 条动态规则全部失效，仅剩 5 条内置规则**

## 降级矩阵

| 组件 | 缺失 yaml 时行为 | 后果 |
|------|----------------|------|
| KnowledgeLoader | 加载失败 | 29 条规则为 0 |
| KnowledgeTranslator | 翻译失败 | 决策树为空 |
| KnowledgeRetriever | 查询失败 | 评分时无规则可用 |

## 29 条动态规则清单

| 类别 | 数量 | 典型规则 |
|------|------|---------|
| card_grouping | 7 | 同花优先、破二炸弹不搭等 |
| passing_skills | 7 | 让道、反向喂牌、拆牌喂牌等 |
| card_language | 7 | 牌型识别、变型识别等 |
| card_interactions | 8 | 牌型相克、配合关系等 |

## ⚠️ 部署警告

**强制依赖**：`pyyaml >= 6.0`

**建议**：
- 部署前必须验证 yaml 加载
- 启动时检查 29 条规则是否全部加载
- 缺失时应**告警并降级到最简模式**

## 跨资料引用
- 架构：[[source-knowledge-structure-summary]]
- 概念：[[concept-yaml-dependency-matrix]]
- 鲁棒性：GUA-032（推断层/记忆层鲁棒性）

## 紧张点
- **yaml 缺失 → 29 条规则失效**：需在 wiki 中标红"部署必装 pyyaml>=6.0"，并关联 GUA-032
