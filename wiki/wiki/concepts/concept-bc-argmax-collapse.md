---
type: concept
title: "BC argmax collapse（行为克隆 argmax 坍缩）"
sources:
  - docs/analysis/archive/level2-root-cause.md
  - docs/analysis/archive/2026-06-18-gua062-batch-eval.md
tags:
  - v7
  - theory
  - bottleneck
status: current
related_gua:
  - GUA-059
  - GUA-060
  - GUA-062
date: 2026-06-18
---

# BC argmax collapse（行为克隆 argmax 坍缩）

## 概念定义

V7 神经网络在行为克隆（BC）训练后，argmax 输出坍缩到训练数据中最高频动作（Single）的理论必然现象。

## 理论必然性

- 训练数据中 Single 占绝大多数
- argmax 选概率最高的动作
- 结果：无论局面如何，NN 几乎总选 Single

## 实证表现

- Single 占非 PASS 决策 80.5%（GUA-062 批跑）
- 卡 2 级（出牌类型极单一）
- 2/A 双峰分布异常

## 修复方向

| 方向 | 关联 GUA |
|------|----------|
| 调参（学习率/正则） | GUA-060（已终止） |
| 训练数据平衡 | GUA-059（进行中） |
| 动作空间二阶段过滤 | GUA-055（启动中） |
| 组牌质量中间表示 | GUA-054（启动中） |

## 关键判断

- GUA-060（BC val_acc 锁死 36.46%）关闭理由：调参路线终止
- GUA-059（BC v2 退化根因定位）是所有 P1 GUA 的硬前置
- 组牌引擎 v2（GUA-062）未解决本问题，因为决策链仍走 BC argmax

## 关联

- [[gua-059]]
- [[gua-060]]
- [[gua-062]]
- [[concept-v7-card-type-polarization]]
- wiki/entities/engine-v7.md
