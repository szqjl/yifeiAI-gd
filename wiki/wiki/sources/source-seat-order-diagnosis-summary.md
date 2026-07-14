---
type: source-summary
title: "座位顺序排查与修复记录 摘要"
sources:
  - docs/development/座位顺序排查与修复记录.md
tags:
  - seat
  - diagnosis
  - bug
  - source
status: current
related_gua:
  - GUA-062
date: 2026-06-18
---

# 座位顺序排查与修复记录 摘要

> 来源：`docs/development/座位顺序排查与修复记录.md`（约 3139 字符）
> 排查日期：**2026-02-27**

## 问题描述

`yf2_m1` 客户端被误识别为 0 号位，导致座位错乱、出牌逻辑异常。

## 根因分析

- 服务器下发的 `act` 请求**可能不带 `myPos` 字段**
- M1 决策层（`stage_router`）使用默认值 `0`
- 导致 `yf2_m1` 被误判为 0 号位（实际应为 1 号位）

## 修复方案

在 `decide(data)` 调用前注入：

```python
data["myPos"] = self.player_id
```

确保决策层始终使用客户端维护的真实 `player_id`。

## 联调清单

1. 4 个客户端按 1/2/3/4 顺序连接
2. 检查日志中 `[座位排查]` 标记是否齐全
3. 验证每个客户端的 `player_id` 与服务器下发的 `myPos` 一致

## 后续动作（待办）

- **方式 A**：诊断模式命令行参数（未实施）
- **方式 B**：`diagnose_seat_order.py` 独立诊断脚本（未实施）
- 二选一实现，用于自动化座位诊断

## 关联

- [[concept-seat-sync-and-diagnosis]] — 座位排查与同步机制
- [[GUA-062]] — M1 myPos 默认值缺陷（待正式登记）
- [[module-websocket-manager]] — WebSocket 通信层
