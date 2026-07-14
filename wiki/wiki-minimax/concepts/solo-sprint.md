---
type: concept
title: "solo_sprint（残局单飞冲刺）"
sources:
  - docs/guandan-brain/issues/GUA-034-completion.md
  - docs/guandan-brain/M3_DIAGNOSIS.md
tags:
  - endgame
  - solo-sprint
  - m3-engine
  - guard-slice
status: current
related_gua:
  - GUA-034
  - GUA-026
  - GUA-029
  - GUA-031
date: 2026-06-17
---

# solo_sprint（残局单飞冲刺）

## 定义

**solo_sprint** 是 M3 引擎在残局 1v2（队友已走完、己方单兵对阵对方两人）场景下的特殊决策模式，归属 [[gua-034]] 残局 guard 切片。

## 模式识别（END-M01）

- 触发条件：**队友已走完**，己方 1 人对对方 2 人
- 脱离条件：进入 GUA-031 队友让道分支后不再触发

## 决策规则

### 接风首出（END-M02）
- 优先级：ThreeWithTwo > Trips > Pair
- **禁拆对出最小单**（避免空炸）

### 被动压牌
- **END-M03**：允许拆 trips 压单
- **END-M04**：允许拆对压对（复用 GUA-029 R3 兜底）

## 边界划清

| 模式 | 触发条件 | 拆 trips/对？ |
|------|----------|---------------|
| **常态**（GUA-026） | 4 人或 2v2 | **禁拆** |
| **solo_sprint**（GUA-034） | 1v2 残局 | **允许拆** |

> 触发条件**互斥**，不冲突。

## 不在范围

- lalala 两手牌枚举：留给 V5+（参见 M3_DIAGNOSIS BUG2）

## 交叉引用

- [[gua-034]] — 残局拦头游主条目
- [[gua-026]] — 常态禁拆
- [[gua-029]] — R3 兜底
- [[gua-031]] — 队友让道
