---
type: concept
title: "solo_sprint 模式（拦头游）"
sources:
  - docs/guandan-brain/issues/GUA-034-completion.md
tags:
  - concept
  - endgame
  - m3
status: current
related_gua:
  - GUA-034
  - GUA-029
  - GUA-031
date: 2026-06-17
---

# solo_sprint 模式（拦头游）

## 定义

**solo_sprint 模式**是 M3 决策引擎在残局阶段的特殊分支：当我方处于 1v2 局面（一名对手已 rest，或队友已 rest），需要**独力阻止对手将剩余手牌一手走光**。

## 触发条件（END-M01）

```python
if numofplayers[(myPos + 2) % 4] == 0 or teammate.rest == 0:
    enter_solo_sprint()
```

## 行为分类

| 场景 | 策略 | 编号 |
|------|------|------|
| 接风首出 | 优先出 `ThreeWithTwo` / `Trips` / `Pair`（手数 ≤ 12） | END-M02 |
| 跟小单 | 允许拆 trips 压牌（≥ 对手点） | END-M03 |
| 跟对子 | 拆 trips 凑更大对，或走 GUA-029 R3 兜底 | END-M04 |

## 与常态策略的差异

| 维度 | 常态 | solo_sprint |
|------|------|-------------|
| 拆 trips 压牌 | 禁（GUA-026） | 允许（END-M03/M04） |
| 队友让道 | 走 GUA-031 | 退出让道分支 |
| 兜底 | 通用 R1/R2/R3 | 复用 GUA-029 R3 兜底 |

## 失败兜底

- 拦头游失败时（对手仍走光）走 GUA-029 R3（`numofplayers[greaterPos]<=7` 且无可跟）
- 完整「两手牌组合枚举」（lalala 思路）不在本 GUA 范围，推到 V5+ / 后续迭代

## 相关页面

- [[GUA-034]]：实体页
- [[GUA-034-completion-summary]]：完成定义
- M3 末段拦头与让道博弈：与 GUA-029/031 边界
