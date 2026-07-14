---
type: entity-module
title: "YF1_V5 客户端"
sources:
  - docs/guandan-brain/WEBSOCKET_CONFIG.md
tags:
  - client
  - communication
  - yf_v5
  - websocket
status: current
related_gua: []
date: 2026-06-18
---

# YF1_V5 客户端

## 基本信息

- **模块路径**：`communication/yf1_v5`
- **核心类**：`YF1_V5_Client`
- **所属引擎代际**：yf_v5（V5 客户端实现）
- **职责**：掼蛋对局客户端的 WebSocket 通信层，与服务端建立/维护长连接，发送出牌指令、接收对局事件

## 依赖模块

- [[module-websocket-manager]] — 底层连接管理（重连、心跳、超时）
- `config.yaml`（`websocket.*` 配置段）

## 配置入口

通过 `websocket.use_local_websocket` 切换本地调试与局域网联调：

- 本地：`websocket.local_url`
- 局域网/网络：`websocket.network_url`

URL 模板中支持 `{user_info}` 占位符，握手阶段动态注入用户标识。

## 日志

- 玩家位 1：`logs/yf1_v5_<时间戳>.log`
- 玩家位 2：`logs/yf2_v5_<时间戳>.log`

## 与 Wiki 已有实体的关系

- **vs yf1_m3 / yf2_m3**：命名上 `yf_v5` 是代际属性，`yf1_m3` 是团队/角色属性，**待确认是否为同一客户端的两种描述维度**（见下方张力）
- **与 wiki-minimax/entities/engine-m3.md 的关系**：M3 决策引擎页面应明确 yf_v5 客户端是否为 M3 的通信层、或为平行实现
- **与 wiki/entities/engine-v7.md 的关系**：V7 NN 引擎迁移候选通信栈

## 张力与待澄清

1. **命名口径冲突**：`yf_v5` 与 `yf1_m3` / `yf2_m3` 的对应关系未在 Wiki 中定调
2. **代际归属**：V5 是版本号还是引擎分支标识？
3. **是否会被 V7 取代**：V7 迁移时是改造 YF1_V5_Client 还是新写？
