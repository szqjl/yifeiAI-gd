---
type: source-summary
title: "组牌-NN衔接设计-软引导vs硬约束 - 摘要"
sources:
  - docs/guandan-brain/组牌-NN衔接设计-软引导vs硬约束.md
tags:
  - v7
  - nn
  - card-grouping
  - architecture
  - design
status: current
related_gua: []
date: 2026-07-15
---

# 组牌-NN衔接设计-软引导vs硬约束 - 摘要

## 来源
原始文件：`docs/guandan-brain/组牌-NN衔接设计-软引导vs硬约束.md`（20015 字符）

## 核心内容
V7 引擎中组牌模块与 NN 推理之间的衔接设计方案，对比"软引导"与"硬约束"两种架构路线，评估各自优劣。

## 关键主题
- 组牌模块在 V7 中的定位
- 软引导方案：NN 输出经启发式规则过滤
- 硬约束方案：NN 输出严格遵循牌型合法性
- 两种方案的胜率、稳定性、可维护性权衡
- 衔接点的接口设计
- 与 M3 引擎组牌逻辑的兼容性

## 关联页面
- [[engine-v7]]
- [[v7-current-state]]
- [[card-grouping-engine]]
