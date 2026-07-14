---
type: concept
title: "30 局固定回归集"
sources:
  - docs/governance/M-V-Series-治理方案.md
tags:
  - regression
  - quality-gate
  - evaluation
status: current
related_gua:
  - GUA-033
date: 2026-06-18
---

# 30 局固定回归集

## 定义

质量门禁的核心组件：**固定 30 局 = 20 问题局 + 10 防回归局**。

| 组成 | 局数 | 作用 |
|------|------|------|
| 问题局 | 20 | 覆盖已知缺陷/边界场景 |
| 防回归局 | 10 | 防止历史修复被回退 |

## 关键属性

- **固定性**：局集内容**不可变**，所有版本必须跑同一批局
- **唯一性**：清单存于 `data/manifests/regression-lalala-v1.json`
- **可比性**：跨版本胜率直接对比，无需考虑局集差异

## 使用流程

1. 从 COS 拉取回归集清单（`scripts/cos/pull_regression.py`）
2. 在固定硬件/seed 下跑 30 局
3. 记录每局胜负 + 总胜率
4. 胜率达标后方可进入下一阶段

## 触发条件

- **V 路径**：胜率 ≥ 40% 连续 50 局（见 [[v-smoke-trigger-conditions]]）
- **M 路径**：无胜率要求，仅无 crash + 可生成 diff

## 关联页面

- [[v-smoke-trigger-conditions]] — V 冒烟触发条件
- wiki-minimax/concepts/batch-evaluation.md — 批跑评测体系
- [[M-V-Series-治理方案-summary]] — 治理总纲
- [[artifact-storage-strategy]] — 产物存储
