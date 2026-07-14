---
type: concept
title: "M/V 三系列架构"
sources:
  - docs/guandan-brain/SCRIPT_INDEX.md
tags:
  - concept
  - architecture
  - m-series
  - v-series
  - engine-evolution
status: current
related_gua: []
date: 2026-06-20
---

# M/V 三系列架构

## 概述

项目并存**三套引擎族**，分别对应不同的技术路线与生命周期阶段。理解三系列的关系是项目演进的核心。

## 三系列对照

| 系列 | 引擎 | 范式 | 生命周期 | 启动器目录 |
|------|------|------|----------|------------|
| **M 系列**（规则引擎） | M1、M2、M3 | 专家规则 + 启发式 | 维护态 | `scripts/launchers/m/` |
| **V-Learn 系列**（学习引擎过渡版） | V4、V5、V6 | 浅层学习 + 规则混合 | 实验性 | `scripts/launchers/v-learn/` |
| **V-NN 系列**（神经网络引擎） | V7 | 深度神经网络 + 强化学习 | 主迭代 | `scripts/launchers/v7/` |

## 演进路径

```
M1 (2018)        V4 (2019)         V7 (2021-)
  ↓                ↓                  ↓
M2 (2019)        V5 (2020)         Stage 5 BC
  ↓                ↓                  ↓
M3 (2020) ←生产主力  V6 (2021)        Stage 6 优化
  ↓                ↓                  ↓
维护态           实验态            Stage 7 RL ← 当前主战场
                                    ↓
                                  Stage 8 Full RL
```

## 各系列定位

### M 系列（规则引擎）

- **优势**：可解释性强、调试方便、规则明确
- **劣势**：已达性能瓶颈，难有突破
- **当前状态**：wiki-minimax/entities/engine-m3.md 是生产主力，但入口覆盖度低（仅 2 个）
- **未来**：逐步迁移至 V7

### V-Learn 系列（过渡版）

- **优势**：引入学习能力，性能优于 M3
- **劣势**：仍依赖大量规则工程，未触及 NN 本质
- **当前状态**：实验性保留，作为 V7 的预研积累

### V-NN 系列（神经网络引擎）

- **优势**：突破规则引擎天花板，端到端学习
- **劣势**：需要大量训练数据、调试困难、可解释性差
- **当前状态**：wiki/entities/engine-v7.md 是主迭代方向，Stage 7 在线 RL 进行中
- **未来**：Stage 8 全量 RL，最终取代 M3

## 协作模式

- **yf1_m3 + yf2_m3**：维护 M3 规则引擎
- **V7 团队**：推进 V7 NN 引擎（Stage 7 RL + 批跑评测）
- **共用工具**：批跑执行器（wiki/entities/module-batch-executor.md）、Wiki 系统、COS 同步

## 入口覆盖度对比

| 系列 | 入口数 | 启动器目录 |
|------|--------|------------|
| V7 | 8+ | `v7/` + 根目录 stub |
| M3 | 2 | `m/` + 根目录 stub |
| V4-V6 | 6 | `v-learn/` |

> ⚠️ **M3 覆盖度不足**：可能反映 M3 已进入维护态，未来应渐进迁移至 V7。

## 关联页面

- wiki-minimax/entities/engine-m3.md — M3 规则引擎
- wiki/entities/engine-v7.md — V7 NN 引擎
- [[script-launcher-hierarchy]] — 启动器分层
- [[SCRIPT_INDEX-summary]] — 脚本索引
