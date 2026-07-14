---
type: source-summary
title: "GUA-073 知识库接入映射（源摘要）"
sources:
  - docs/guandan-brain/knowledge-integration-mapping.md
tags:
  - gua-073
  - knowledge-integration
  - granularity
  - roadmap
status: current
related_gua:
  - GUA-073
  - GUA-071
  - GUA-072
  - GUA-074
date: 2026-06-19
---

# GUA-073 知识库接入映射（源摘要）

## 目标

将掼蛋领域知识**结构化、可控、可验证**地接入 V7 引擎，定义粒度分级与阶段化路线。

## 知识粒度分级

| 级别 | 含义 | 示例 |
|------|------|------|
| **L0** | 牌张原子 | 单张牌面值、花色 |
| **G** | 牌型 | 单张、对子、连对、钢板、炸弹 |
| **H** | 牌型组合/手牌结构 | 头道/中道/尾道 |
| **E** | 局势/外部信号 | 进张张数、级牌归属 |
| **M** | 战术/方法论 | 控牌、跑牌、防炸 |
| **V5** | V5 阶段遗留 | 牌力评分 |
| **N** | NN 学到的隐式知识 | CardCountingNetwork 输出 |

详见 concept-knowledge-integration-granularity

## 标注规模

**阶段 1 已完成**：约 **149 条**知识点标注（与组牌 v2 GUA-062、Guard R 系列、heuristic 维度对齐）

## 阶段 2 P0 行动（紧迫）

1. **6 条新 Guard 规则**（基于 GUA-073 标注缺口）
   - 注意 GUA-066/068/069/070 **全量叠加翻车**教训：需**正交性设计**，避免非线性交互
2. **5 条 heuristic 维度**（替代 NN argmax，参 [[gua-071]]）
3. **记牌模块联动**（[[gua-072]] 规则记牌 + CardCountingNetwork 信念）
4. **组牌引擎 v2 微调**（参 wiki/entities/module-grouping-engine.md，GUA-062）

## 关键风险

- **GUA-066 教训**：单点 Guard 提升 +18.5pp，但**全量叠加反而暴跌至 3.7%**。阶段 2 必须做正交性验证
- **规则叠加的非线性交互效应**（参 [[gua-074]] §层级四）

## 路线图

- 阶段 1（已完成）：149 条标注 + 粒度分级
- **阶段 2（P0）**：6 Guard + 5 heuristic + 记牌联动 + 组牌微调
- 阶段 3：信念 NN 训练（CardCountingNetwork 替代规则记牌）
- 阶段 4：自对弈 PG 阶段（参 wiki/concepts/self-play-policy-gradient.md）

## 相关页面

- [[gua-073]] 实体页
- [[gua-071]] Guard 规则迭代
- [[gua-072]] 规则记牌引擎
- [[gua-074]] V 系列反思
- concept-knowledge-integration-granularity
- synthesis-knowledge-integration-roadmap
