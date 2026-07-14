---
type: source-summary
title: "GUA-034 残局拦头游（M3 guard 切片）完工记录摘要"
sources:
  - docs/guandan-brain/issues/GUA-034-completion.md
tags:
  - gua-034
  - m3-engine
  - endgame
  - open
status: current
related_gua:
  - GUA-034
  - GUA-026
  - GUA-029
  - GUA-031
date: 2026-06-17
---

# GUA-034 残局拦头游（M3 guard 切片）完工记录摘要

## 概览

| 字段 | 值 |
|------|----|
| GUA 编号 | GUA-034 |
| 标题 | 残局拦头游（M3 guard 切片） |
| 类型 | feature |
| 状态 | open |
| 引擎 | M3 |

## 子项清单

| 子项 | 职责 |
|------|------|
| END-M01 | 模式识别：`solo_sprint`（残局 1v2 队友已走完） |
| END-M02 | 接风首出策略：优先 ThreeWithTwo/Trips/Pair，禁拆对出最小单 |
| END-M03 | 被动压牌：solo_sprint 允许拆 trips 压单 |
| END-M04 | 被动压牌：solo_sprint 允许拆对压对（复用 GUA-029 R3 兜底） |

## 边界划清

> **GUA-026（禁三带二常态拆炸弹/级牌 trips）vs GUA-034（残局 1v2 允许拆 trips/对）**——触发条件互斥，不冲突：
> - GUA-026：常态局面，**禁拆**
> - GUA-034：`solo_sprint` 分支（队友已走完），**允许拆**

## 不在范围

- **lalala 两手牌枚举**：留给 V5+（参见 M3_DIAGNOSIS BUG2）
- **不要求队胜率达标**：以 M3 批跑观测为准

## 关联与复用

- **GUA-029 R3 兜底** → END-M04 复用
- **GUA-031 队友让道分支** → END-M01 模式识别后脱离
- **GUA-026** → 常态禁拆分支

## 交叉引用

- [[gua-034]] — 实体页
- [[gua-026]] — 常态禁拆边界
- [[gua-029]] — R3 兜底
- [[gua-031]] — 队友让道
- [[solo-sprint]] — 残局单飞冲刺概念
