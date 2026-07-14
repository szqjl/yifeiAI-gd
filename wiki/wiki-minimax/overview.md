---
type: meta
title: "Wiki 全局概要"
sources:
  - docs/guandan-brain/issues/GUA-032-completion.md
  - docs/guandan-brain/issues/GUA-033-completion.md
  - docs/guandan-brain/issues/GUA-034-completion.md
tags:
  - overview
  - index
status: current
date: 2026-06-17
---

# Wiki 全局概要

> 最近更新：2026-06-17（摄入 GUA-032/033/034 三份完工记录）

## GUA 生命周期速览

### P0 Open
- [[gua-032]] — 记牌 + 算牌（M3）— feature
- [[gua-034]] — 残局拦头游（M3 guard 切片）— feature

### Recently Closed
- [[gua-033]] — M3 批末 victoryNum / gameResult — bug — **2026-05-31 closed** ✅

## 核心论点

1. **V7 是未来方向**：M3 规则引擎已达瓶颈，V7 NN 引擎是突破关键
2. **批跑是唯一真源**：所有策略改动必须经过离线批跑验证
3. **GUA 编号体系是脊柱**：所有缺陷、迭代、分析都挂在 GUA 上
4. **局 ≠ 副**：数据解读的核心口径问题，已在 GUA-033 定音

## 本次摄入要点

- **GUA-032**：记牌算牌基建，MEM-M02 / CALC-M01/M02/M03 子项，2468 计数法为核心方法
- **GUA-033**：平台 exe argv 无效已定音，批末 [0]+[1]=batch_games 校验落地
- **GUA-034**：残局 1v2 solo_sprint 模式，与 GUA-026 常态禁拆互斥；lalala 两手牌枚举留给 V5+

## 完成度定义提示

> GUA-032/033/034 均明确**不要求队胜率达标**，以 M3 批跑观测为准——与「批跑是唯一真源」论点衔接。

## 交叉引用

- [[gua-026]] — 常态禁拆（与 GUA-034 互斥）
- [[gua-029]] — R3 兜底（GUA-034 END-M04 复用）
- [[gua-031]] — 队友让道（GUA-034 END-M01 脱离）
- [[gua-061]] — V7 引擎相关

## 新增概念页

- [[card-counting-and-calc]] — 记牌算牌体系
- [[solo-sprint]] — 残局单飞冲刺
- [[batch-end-victory-num-validation]] — 批末 victoryNum 校验
