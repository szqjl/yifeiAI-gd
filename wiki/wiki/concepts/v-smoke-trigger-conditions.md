---
type: concept
title: "V 默认冒烟双条件"
sources:
  - docs/governance/M-V-Series-治理方案.md
tags:
  - smoke-test
  - quality-gate
  - v-series
status: current
related_gua: []
date: 2026-06-18
---

# V 默认冒烟双条件

## 定义

V 系列默认冒烟测试的**双条件**（OFF/ON 二选一）：

| 条件 | 阈值 | 说明 |
|------|------|------|
| **条件 A（胜率路径）** | 胜率 ≥ 40% **连续 50 局** | 通过 [[regression-30-set]] 跑出 |
| **条件 B（契约路径）** | m3 契约冻结 + m 冒烟 7 天 | 稳定性证据替代胜率 |

## OFF/ON 含义

- **OFF**：默认不开启 V 冒烟
- **ON**：满足任一条件后开启

## 设计意图

V 系列（特别是 v7 NN 引擎）在早期胜率波动大，强行要求胜率门槛会阻碍迭代。引入**契约稳定性**作为替代路径，使 V 迭代不依赖单次胜率突破。

## 与回归集的关系

- 条件 A 的 50 局可以**包含** 30 局固定回归集（剩余 20 局随机/补充）
- 条件 B 完全不依赖胜率，只看稳定性

## 关联页面

- [[regression-30-set]] — 30 局回归集
- [[M-V-Series-治理方案-summary]] — 治理总纲
- wiki/entities/engine-v7.md — V7 引擎
