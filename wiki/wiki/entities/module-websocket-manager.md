---
type: entity-module
title: "WebSocketManager 通信模块"
sources:
  - docs/development/WEBSOCKET_CONFIG.md
tags:
  - module
  - communication
  - websocket
status: current
related_gua: []
date: 2026-06-18
---

# WebSocketManager 通信模块

## 模块信息

| 项 | 值 |
|----|-----|
| 文件路径 | `src/communication/websocket_manager.py` |
| 用途 | WebSocket 连接管理器 |
| 核心能力 | 自动重连 / 心跳保活 / 超时检测 |

## 核心功能

### 1. 自动重连
- 可配置 `reconnect_interval`（默认 5 秒）
- 支持无限重试
- 断线后自动恢复

### 2. 心跳保活
- 可配置 `heartbeat_interval`（默认 30 秒）
- 定期发送心跳包

### 3. 超时检测
- 可配置 `timeout`（默认 10 秒）
- 超时触发重连

## 配置项（config.yaml）

```yaml
websocket:
  local_url: ws://127.0.0.1:23456/game/
  network_url: ws://[局域网IP]:23456/game/
  reconnect_interval: 5
  heartbeat_interval: 30
  timeout: 10
```

## 客户端入口

- `YF1_V5_Client` — `src/communication/yf1_v5.py`（v5 客户端入口）

## 使用方

- 所有客户端变体：`yf1_m1` / `yf2_m1` / `yf1_v4` / `yf2_v4` / `yf1_v5` / `yf2_v5` / `yf1_v5_stage5` / `yf2_v5_stage5` / `yf1_v7` / `yf2_v7`

## 服务器端点

| 类型 | 地址 |
|------|------|
| 本地 | `ws://127.0.0.1:23456/game/{user_info}` |
| 局域网 | `ws://[局域网IP]:23456/game/{user_info}` |

## 关联

- [[source-websocket-config-summary]] — 配置文件来源
- [[concept-seat-sync-and-diagnosis]] — 座位同步依赖此模块
- wiki/entities/engine-v7.md — V7 客户端使用
