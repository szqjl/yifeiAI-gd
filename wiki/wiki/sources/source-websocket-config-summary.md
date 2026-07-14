---
type: source-summary
title: "WEBSOCKET_CONFIG 摘要"
sources:
  - docs/development/WEBSOCKET_CONFIG.md
tags:
  - websocket
  - yf_v5
  - source
status: current
related_gua: []
date: 2026-06-18
---

# WEBSOCKET_CONFIG 摘要

> 来源：`docs/development/WEBSOCKET_CONFIG.md`（约 2521 字符）
> **版本说明**：本文档描述 `yf_v5` 的 WebSocket 配置，属历史版本资产

## 服务器端点

| 类型 | 地址 |
|------|------|
| 本地 | `ws://127.0.0.1:23456/game/{user_info}` |
| 局域网 | `ws://[局域网IP]:23456/game/{user_info}` |

## 配置项（config.yaml）

```yaml
websocket:
  local_url: ws://127.0.0.1:23456/game/
  network_url: ws://[局域网IP]:23456/game/
  reconnect_interval: 5        # 秒
  heartbeat_interval: 30       # 秒
  timeout: 10                  # 秒
```

## WebSocketManager 能力

- 自动重连（可配置重试间隔，支持无限重试）
- 心跳保活
- 超时检测
- 详见 [[module-websocket-manager]]

## 客户端变体

- `yf1_v5` / `yf2_v5`（v5 基础版）
- `yf1_v5_stage5` / `yf2_v5_stage5`（v5 stage5）
- `yf1_v7` / `yf2_v7`（V7 引擎，**当前主迭代**）

## 故障排查

- 连接失败 → 检查 `local_url` / `network_url` 是否可达
- 心跳超时 → 调整 `heartbeat_interval` / `timeout`
- 重连风暴 → 增大 `reconnect_interval`

## 关联

- [[module-websocket-manager]]
- wiki/entities/engine-v7.md（V7 客户端沿用此 WebSocket 配置模式）
