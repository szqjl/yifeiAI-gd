---
type: concept
title: "座位排查与同步机制"
sources:
  - docs/development/DEVELOPMENT_RULES.md
  - docs/development/座位顺序排查与修复记录.md
tags:
  - websocket
  - seat
  - diagnosis
  - core-mechanism
status: current
related_gua:
  - GUA-062
date: 2026-06-18
---

# 座位排查与同步机制

## 定义

掼蛋 AI 项目中**确保客户端座位与服务器一致**的统一机制，覆盖 m1/v4/v5/v7 所有客户端变体。

## 组队规则（核心）

- 第 1/3 个连接的 AI 为队友
- 第 2/4 个连接的 AI 为队友
- **连接时固定，整个会话期间不变**

## 同步机制

### 数据来源
- 服务器在 act 请求中下发 `myPos` 字段
- **但**：服务器可能**省略** `myPos`（M1 缺陷，见 [[GUA-062]]）

### 客户端维护
- 每个客户端维护 `self.player_id`（真实座位号）
- 在 `decide(data)` 调用前注入：

```python
data["myPos"] = self.player_id
```

### 触发时机
- WebSocket 接收 act 请求时
- 决策层计算前
- 日志输出时（统一格式）

## [座位排查] 日志规范

所有客户端座位同步入口必须输出统一格式日志：

```
[座位排查] 来源={websocket/stage_router}, 原始myPos={xxx}, 原始playerPosition={xxx}, 同步后player_id={xxx}
```

**目的**：快速定位座位错乱问题

## 诊断方式（待实施）

文档提到两种诊断方式，**目前均未实现**：

| 方式 | 描述 | 状态 |
|------|------|------|
| 方式 A | 诊断模式命令行参数 | ❌ 待办 |
| 方式 B | `diagnose_seat_order.py` 独立脚本 | ❌ 待办 |

## 联调清单

1. 4 个客户端按 1/2/3/4 顺序连接
2. 检查日志中 `[座位排查]` 标记是否齐全
3. 验证每个客户端的 `player_id` 与服务器下发的 `myPos` 一致
4. 跨客户端验证队友关系（1/3 队友，2/4 队友）

## 历史缺陷

### M1 myPos 默认值缺陷（2026-02-27 发现）

- **症状**：`yf2_m1` 被误识别为 0 号位
- **根因**：服务器 act 请求可能不带 `myPos`，M1 决策层（`stage_router`）使用默认值 `0`
- **修复**：在 `decide(data)` 前注入 `data["myPos"] = self.player_id`
- **状态**：已修复，建议登记为 [[GUA-062]]

## 关联

- [[module-websocket-manager]] — WebSocket 通信层
- [[GUA-062]] — M1 座位误判缺陷
- [[source-seat-order-diagnosis-summary]] — 排查记录
- DEVELOPMENT_RULES — 第 3 条规则（组队规则）
