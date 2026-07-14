---
type: concept
title: "WebSocket 重连与心跳模式"
sources:
  - docs/guandan-brain/WEBSOCKET_CONFIG.md
tags:
  - websocket
  - reconnect
  - heartbeat
  - pattern
status: current
related_gua: []
date: 2026-06-18
---

# WebSocket 重连与心跳模式

## 模式定义

掼蛋客户端在长连接场景下的标准可靠性模式：**自动重连 + 心跳保活 + 超时兜底**。该模式由 [[module-websocket-manager]] 实现，是 [[module-yf1-v5-client]] 的底层保障。

## 三大支柱

### 1. 自动重连（Reconnect）

- 配置项：`websocket.reconnect_interval`、`max_retries=-1`
- 行为：连接断开后**无限重试**，避免瞬时网络抖动导致客户端掉线
- 适用场景：本地调试、局域网联调、网络对战均启用

### 2. 心跳保活（Heartbeat）

- 配置项：`websocket.heartbeat_interval`
- 行为：周期性发送 ping 帧，防止 NAT/代理中间网关因空闲超时断开连接
- 频率：可配，默认值需查 config.yaml 实际值

### 3. 超时兜底（Timeout）

- 配置项：`websocket.timeout`
- 行为：握手阶段与消息往返阶段统一超时阈值，超时即触发重连
- 作用：避免永久挂起

## 配置驱动 vs 硬编码

所有参数集中在 `config.yaml` 的 `websocket.*` 段，**不硬编码**到代码中。优势：

- 不同环境（本地/局域网/网络）切换无需改代码
- 调优心跳/重连参数无需重新编译
- 便于批跑场景下大规模客户端调参

## URL 模板占位符

`{user_info}` 占位符机制：握手 URL 中嵌入用户标识占位符，连接建立时动态替换。简化了多用户/多角色客户端的 URL 拼装。

## 适用范围

- [[module-yf1-v5-client]]（当前主消费者）
- 未来 wiki/entities/engine-v7.md 客户端若复用通信层，可直接继承该模式

## 待沉淀

- 心跳协议格式（应用层 vs 协议层）
- 重连退避算法（固定间隔 vs 指数退避）
- 断线期间的出牌指令缓存与重发策略（暂未在原始资料中体现）
