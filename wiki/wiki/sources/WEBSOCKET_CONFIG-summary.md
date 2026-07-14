---
type: source-summary
title: "WebSocket 配置指南摘要"
sources:
  - docs/guandan-brain/WEBSOCKET_CONFIG.md
tags:
  - websocket
  - config
  - communication
  - yf_v5
status: current
related_gua: []
date: 2026-06-18
---

# WebSocket 配置指南摘要

## 原始资料概览

来源：`docs/guandan-brain/WEBSOCKET_CONFIG.md`（约 2.5 KB）

定位：yf_v5 客户端的 WebSocket 通信层配置手册，覆盖本地调试、局域网联调、网络对战三种场景的配置项与连接管理机制。

## 关键实体

### 引擎/客户端

- **yf_v5**：与 M3 决策引擎并列的客户端实现（V5 代际），承载 WebSocket 通信
- **YF1_V5_Client**：yf_v5 客户端核心类，位于 `communication/yf1_v5` 模块

### 模块

- `communication/yf1_v5` — YF1_V5_Client 实现目录
- `communication/websocket_manager` — WebSocket 连接管理器模块
- **WebSocketManager** — 独立类，封装重连、心跳、超时等机制

### 配置项（`config.yaml` → `websocket.*`）

| 配置键 | 用途 |
|--------|------|
| `websocket.local_url` | 本地调试 WebSocket 地址 |
| `websocket.network_url` | 局域网/网络对战地址 |
| `websocket.reconnect_interval` | 重连间隔（秒） |
| `websocket.heartbeat_interval` | 心跳保活间隔（秒） |
| `websocket.timeout` | 连接/响应超时阈值 |

### 日志约定

- `logs/yf1_v5_YYYYMMDD_HHMMSS.log` — 玩家位 1 客户端日志
- `logs/yf2_v5_YYYYMMDD_HHMMSS.log` — 玩家位 2 客户端日志

## 关键概念

1. **WebSocket 配置化管理**：所有连接参数集中在 `config.yaml`，避免硬编码
2. **自动重连机制**：`max_retries=-1` 表示无限重试，断线自动恢复
3. **心跳保活**：`heartbeat ping` 周期发送，防止中间网关超时断开
4. **连接超时控制**：`timeout` 统一管控握手与消息往返
5. **本地 vs 局域网切换**：`use_local_websocket` 标志位控制走 `local_url` 还是 `network_url`
6. **`{user_info}` URL 模板占位符**：服务端鉴权/路由用占位符，握手时动态替换

## 与现有 Wiki 的关联

- wiki-minimax/entities/engine-m3.md（中等置信度）：M3 决策引擎页面应提及 yf_v5 客户端的通信层是 M3 的平行实现还是其通信层依赖
- wiki/entities/engine-v7.md（低置信度）：V7 NN 引擎迁移时可能复用 yf_v5 的 WebSocket 栈

## 待澄清问题

1. **命名冲突**：`yf_v5` / `YF1_V5_Client` 与 Wiki 已有的 `yf1_m3` / `yf2_m3` 是迭代关系还是并存？
2. **V7 通信层依赖**：V7 计划沿用 yf_v5 客户端还是另起？
3. **文档日期**：原文中 `2025-01-XX` 为占位符，需确认实际更新日期

## 张力点

- **代际命名混乱**：yf_v5（V5 代际客户端）vs yf1_m3（M3 代际团队命名）可能指代相同节点的不同属性，需 Wiki 统一口径
- **V7 路径缺失**：Wiki 标注 V7 是未来方向，但 yf_v5 客户端已是工程化产物，迁移路径尚未在 Wiki 体现
