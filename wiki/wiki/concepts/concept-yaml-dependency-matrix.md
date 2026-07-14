---
type: concept
title: "YAML 依赖降级矩阵"
sources:
  - docs/knowledge/YAML_DEPENDENCY_ANALYSIS.md
  - docs/knowledge/STRUCTURE.md
tags:
  - concept
  - yaml
  - dependency
  - deployment
  - robustness
status: current
related_gua:
  - GUA-032
date: 2026-06-17
---

# YAML 依赖降级矩阵

## 核心结论

> **YAML 缺失 → 29 条动态规则全部失效，仅剩 5 条内置规则**

## 降级矩阵

| 组件 | yaml 缺失时行为 | 后果 |
|------|---------------|------|
| **KnowledgeLoader** | 加载失败 | 29 条规则为 0 |
| **KnowledgeTranslator** | 翻译失败 | 决策树为空 |
| **KnowledgeRetriever** | 查询失败 | 评分时无规则可用 |

## 29 条动态规则清单

| 类别 | 数量 | 典型规则 |
|------|------|---------|
| **card_grouping** | 7 | 同花优先、破二炸弹不搭等 |
| **passing_skills** | 7 | 让道、反向喂牌、拆牌喂牌等 |
| **card_language** | 7 | 牌型识别、变型识别等 |
| **card_interactions** | 8 | 牌型相克、配合关系等 |
| **合计** | **29** | - |

## ⚠️ 部署必装

```bash
pip install "pyyaml>=6.0"
```

## 部署检查清单

- [ ] pyyaml >= 6.0 已安装
- [ ] 启动时验证 yaml 加载
- [ ] 检查 29 条规则是否全部加载
- [ ] 缺失时**告警并降级到最简模式**（仅 5 条内置规则）

## 与 GUA 关系
- **GUA-032 推断层/记忆层鲁棒性**：yaml 缺失直接导致推断/记忆能力大幅下降
- 应在 GUA-032 跟踪里记录 yaml 依赖作为**鲁棒性弱点**

## 紧张点
- **架构设计 vs 部署现实**：
  - 架构假设 yaml 总是可用
  - 实际部署中 yaml 可能缺失
  - 需有降级方案（哪怕只是 5 条内置规则）

## 相关页面
- [[source-knowledge-yaml-dependency-analysis-summary]]
- [[source-knowledge-structure-summary]]
- [[gua-032]]
