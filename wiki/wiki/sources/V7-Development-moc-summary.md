---
type: source-summary
title: "V7 神经网络引擎 MOC 文档摘要"
sources:
  - docs/guandan-brain/MOCs/V7-Development.md
tags:
  - moc
  - v7
  - nn-engine
  - iteration-index
status: current
related_gua:
  - GUA-037
  - GUA-038
  - GUA-041
  - GUA-042
  - GUA-043
  - GUA-044
  - GUA-045
  - GUA-047
  - GUA-048
  - GUA-049
  - GUA-050
  - GUA-051
  - GUA-052
  - GUA-053
  - GUA-059
  - GUA-060
  - GUA-061
date: 2026-06-18
---

# V7 神经网络引擎 MOC 文档摘要

## 概述
V7 是从 M3 规则引擎向神经网络引擎迁移的主迭代方向，当前队胜率仅 3.0%（1/33），距 30% 门槛尚远。MOC 汇总 21 个 GUA，分四条迭代主线。

## 迭代分组

| 迭代分组 | GUA 范围 | 主题 |
|---------|---------|------|
| v7-features-gua037-038 | GUA-037a/b, 038 | 特征工程 |
| v7-infra-gua041-049 | GUA-041~049 | 基础设施（guards、数据集、训练） |
| v7-strategy-gua045-053 | GUA-045~053 | 策略层 |
| v7-bc-training-gua059-061 | GUA-059~061 | BC 训练 & 模块化架构 |

## 编号体系说明
- 同时使用 `V7-XXX` 和 `GUA-XXX` 两种编号
- V7-006/007/010 属于早期编号（pre-GUA 体系），需建立映射表
- V7-007 当前 open（队胜率未达标），V7-006/010 已 closed

## KPI 概览
- V7 当前队胜率：**3.0%**（1/33）— 严重低于 30% 目标
- GUA-060 关闭理由：BC argmax collapse 是理论必然
- GUA-061 是当前唯一开放 P0：模块化架构

## 关联页面
- wiki/entities/engine-v7.md
- wiki/concepts/bc-argmax-collapse.md
- [[modular-architecture-gua061]]
- moc-m3-development
- [[synthesis-m3-vs-v7-status]]
