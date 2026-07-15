---
type: concept
title: "solo sprint（残局 solo 冲刺）"
sources:
  - docs/guandan-brain/iterations/m3-guards-gua031-036.md
tags:
  - 概念
  - 残局
  - solo
status: current
related_gua:
  - GUA-034
  - GUA-035
date: 2026-07-15
---

# solo sprint（残局 solo 冲刺）

## 定义

当本方仅剩 1 名玩家（队友已升级或被关）且进入收官阶段时，激活的高强度残局策略模式。

## 触发判定 `_is_solo_sprint`

- 本方存活玩家数 == 1
- 本人手牌 ≤ 5 张
- 对手 ≥ 2 名玩家进入收官

## 方向选择

| 方向 | 含义 | 状态 |
|------|------|------|
| A | 优先拦对手头游 | 当前实施（[[gua-034]]） |
| B | 优先自己冲头游 | 未实施 |

## 配合模块

- [[gua-035]]：对手剩张过滤（1/2/5 张差异化）
- [[gua-031]]：传牌 guard（solo 模式可放宽）

## 关联

- 实体：[[gua-034]]
- 引擎：[[engine-m3-strategy-bundle]]
