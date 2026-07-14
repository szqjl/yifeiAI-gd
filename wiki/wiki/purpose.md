---
type: meta
title: "Wiki 目标与方向"
sources:
  - docs/guandan-brain/ISSUES.md
  - docs/guandan-brain/ITERATIONS.md
tags:
  - meta
  - purpose
status: current
date: 2026-06-28
---

# Wiki 目标与方向

## 核心论点（演进中）

### 1. V7 是未来方向，但当前不可用（双轨表述）

**方向正确**：
- M3 规则引擎已达瓶颈（~70% 局胜 vs lalala）
- V7 NN 引擎（[[engine-v7]]）是突破关键
- L0~L8 决策管线（[[decision-pipeline-v7]]）设计合理

**当前不可用**：
- V7 vs lalala 138 局仅 1 胜（0.7%）
- 截至 2026-06-28 实战不可用
- M3 仍是 lalala 战主力

### 2. 批跑是唯一真源
- 所有策略改动必须经过 [[batch-evaluation]] 离线批跑
- **禁止** replay 逐步一致作为关单标准
- pytest 通过 ≠ 实战可用（GUA-062 案例）

### 3. GUA 编号体系是脊柱
- 所有缺陷、迭代、分析挂在 GUA 上
- GUA-062 ~ GUA-081 当前活跃
- 已闭环 ≠ 已解决（GUA-062 闭环但 V7 主路径仍有问题）

### 4. 局 ≠ 副（核心口径）
- 局胜 vs 副胜必须分别报告
- PASS-only 比例 ≠ 漏候选
- 见 [[局不等于副]]

## 关键问题与回答

| 问题 | 回答 |
|------|------|
| V7 引擎当前状态？ | 迭代方向但不可用，见 [[v7-current-state]] |
| P0 open GUA？ | GUA-075/078/079/081 |
| 最近批跑胜率？ | V7 0/9 局（M3 ~70% 基准） |
| M3 决策引擎缺陷？ | 见 [[m3-engine-debt]] |
|
