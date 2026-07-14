---
type: source-summary
title: "原则映射摘要 (PRINCIPLES_MAPPING)"
sources:
  - docs/guandan-brain/PRINCIPLES_MAPPING.md
tags:
  - principles
  - mapping
  - m3
  - v5-backlog
  - p0-p1
status: current
related_gua:
  - GUA-022
  - GUA-026
  - GUA-029
date: 2026-06-20
---

# PRINCIPLES_MAPPING.md 摘要

掼蛋策略原则的 **ID 编码体系** + **引擎归属矩阵**。

## 原则 ID 前缀体系

| 前缀 | 类别 | 示例 |
|------|------|------|
| `P-C` | 核心原则（C=Core） | P-C01~02 |
| `P-J` | 基本原则（J=Basic） | P-J01~04 |
| `P-M` | 中局原则（M=Mid） | P-M01~02 |
| `P-G` | 进贡原则（G=Gong） | P-G01~04 |
| `P-F` | 残局原则（F=Fin） | P-F01~05 |
| `P-H` | 高压线原则（H=高压线，**M3 P0**） | P-H01~06 |
| `S-PR` | PR 策略（牌型相关） | S-PR01~07 |
| `S-ST` | ST 策略（顺子相关） | S-ST01~03 |
| `S-BS` | BS 策略（基本策略） | S-BS01~13 |
| `PASS-P` | 传牌策略 | PASS-P01~05 |
| `ROLE-R` | 角色策略 | ROLE-R01~10 |
| `PAIR-P` | 对子策略 | PAIR-P01~08 |
| `SNG-P` | 信号策略 | SNG-P01~11 |
| `LANG-P` | 语言/通信策略 | LANG-P01~08 |
| `IX-P` | 索引/查表策略 | IX-P01~10 |
| `CALC-USE` | 计算使用策略 | CALC-USE-01~04 |
| `CALC-M*` | 计算方法集 | CALC-M* 系列 |

## 引擎归属矩阵

### M3 已实施（P0 + P1）

**P0 高压线（4 条，强制实施）**：
- **P-H01**：进贡慎出单
- **P-H02**：火不打四
- **P-H05**：顺子慎始发
- **P-G04**：进贡慎出单（与 P-H01 对应）

**P1 实施**：
- 贡还、逢五出对 等基础策略

### V5+ Backlog（未启动）

几乎所有非 P0 高压线原则归入 **V5+ backlog**。整片 V5+ 暂未启动——M3 已基本冻结，团队重心完全在 V7。

## 三文档对照

原则映射需对照三份文档：
1. `01_basic_principles.md` — 原则原文
2. `02_strategy_overview.md` — 策略概览
3. `03_basic_strategy.md` — 基本策略

## 关键洞察

- M3 P0 几乎无新增：除 4 条高压线外都是 P1/P2
- V5+ backlog 是潜在改进空间，但当前优先级低
- 原则 ID 体系是 **唯一真源**——所有 GUA/策略/测试都应能追溯到具体原则 ID

## 交叉引用

- principles-mapping-system — 完整编码体系概念页
- wiki-minimax/entities/engine-m3.md — M3 实施清单
- [[GUA-Index]] — 原则→GUA 反向追溯入口
