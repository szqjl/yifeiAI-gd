---
type: source-summary
title: "GUA-044 完成定义摘要 · 批跑四席就绪门闩"
sources:
  - docs/guandan-brain/issues/GUA-044-completion.md
tags:
  - gua
  - batch
  - infra
  - gate
  - websocket
status: current
related_gua:
  - GUA-044
  - GUA-033
date: 2026-06-17
---

# GUA-044 完成定义摘要

## 概述

GUA-044 是**批跑基建门闩类** GUA，目标是确保四席客户端在开局前全部就绪，避免半连接状态下的脏数据。

## 核心机制

### 四席就绪门闩

- **门闩触发**：必须四席（4 个客户端）全部发出就绪信号
- **状态文件**：`batch_executor/clients_ready.json`
- **席位顺序**：`CONNECT_ORDER_INDEX` + 按席位 `_peers_ready`

### 关键模块

| 模块 | 职责 |
|------|------|
| `batch_executor/clients_ready.json` | 就绪状态持久化 |
| `batch_executor/wait_for_clients_connected` | 等待四席连入 |
| `batch_executor/clear_all_ready` | 清空就绪状态 |
| `websocket_manager/wait_for_connect_turn` | 按席位轮候连入 |
| `lalala_adapter/wait_for_connect_turn` | lalala 适配器轮候 |
| `executor` | 调度入口 |

## 时间参数（2026-06-06 调整）

| 参数 | 旧值 | 新值 | 含义 |
|------|------|------|------|
| client4 延迟 | 2s | **11s** | 末席连入前额外等待 |
| 末席稳定窗口 | 5s | **7s** | 末席连入后稳定时间 |

**调整原因**：旧参数在网络抖动下偶发半连接。

## 调试旁路

- **环境变量**：`YF_SKIP_CONNECT_GATE=1`
- **用途**：调试时跳过门闩直接进入对局
- **注意**：生产批跑严禁开启

## 复发排查指南

> 单席长时间无 act 时，**先查他席回包**，不要直接判定该席断连

## 依赖关系

- **上游**：`GUA-033` 关闭后的批跑体系
- **M3 批跑基建**（拼图末块）
- **启用**：稳定四席批跑

## 关联页面

- [[gua-044]] - GUA-044 实体页
- [[quad-ready-gate]] - 四席就绪门闩概念
- 批跑评测体系 - 批跑体系总览
- [[m3-batch-infra-closure]] - M3 批跑基建关闭综合
- wiki-minimax/entities/gua-033.md - 批跑基建历史关联
