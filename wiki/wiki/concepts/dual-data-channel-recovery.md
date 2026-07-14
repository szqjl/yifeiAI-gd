---
type: concept
title: "双重数据通道与批跑数据恢复链"
sources:
  - docs/analysis/数据恢复链分析.md
tags:
  - infra
  - data-pipeline
  - recovery
  - critical
status: current
related_gua:
  - GUA-048
  - GUA-049
date: 2026-06-18
---

# 双重数据通道与批跑数据恢复链

## 概述

掼蛋 AI 批跑系统在 WebSocket 通道之外，引入了**进程 stdout** 作为第二条数据通道。这一双重通道设计既提升可靠性（互为备份），也引入新的复杂面：4 进程 race condition、批末对账、victoryNum 写入清单、日志恢复冗余。

## 双重通道架构

```
┌─────────────────┐   WebSocket (A)   ┌─────────────────┐
│  yf1_m3 客户端  │ ─────────────────►│  Server (game)  │
│  (A 通道)       │ ◄─────────────────│  victoryNum → A │
└─────────────────┘                   └─────────────────┘
                                                    │
                                                    │ stdout (B)
                                                    ▼
┌─────────────────┐   read_stdout    ┌──────────────────────┐
│ batch_executor  │ ◄──────────────  │ ServerStdoutReader   │
│ (B 通道)        │   批末对账       │ game_ready.json race │
└─────────────────┘                  └──────────────────────┘
```

## 关键概念

### victoryNum 四层写入清单
服务端将胜负结果写入 4 个不同位置（A 通道 payload、A 通道 JSON、stdout B 通道 stdout_line、game_records/*.json），任一层丢失不影响最终解析。

### 批末对账（两通道交叉验证）
`batch_executor/executor.py` 在每批对局结束时，强制要求 A 通道和 B 通道对同一局的 victoryNum 达成一致，否则标记该局为不可信并跳过。

### 日志恢复冗余通道
当 `game_records/*.json` 被误清（已发生事件，需 wiki 单独留痕），可通过 stdout B 通道的逐手记录回放重建——但若 B 通道同时丢失，则数据彻底不可恢复。

### 4 进程 race condition（[[gua-049]]）
`game_ready.json` 由 4 个客户端进程并发写入，存在 last-writer-wins 风险，是 GUA-049 的根因。

## 与现有 GUA 的关联

- gua-048 — 73s 卡顿的根因之一是 ServerStdoutReader 与 game_ready 双重触发
- [[gua-049]] — 客户端 mark_game_ready 写盘 race condition（P1）
- wiki-minimax/entities/gua-033.md — victoryNum 解析的前置 GUA

## 风险提示

- **数据恢复链不是「一定安全」**：AGENT_BOOTSTRAP 中提到 `game_records/*.json` 被误清为已发生事件
- 双重通道虽然冗余，但若两通道同时受同一根因影响（如服务端崩溃），则全部数据丢失
- 批末对账仅能发现不一致，无法修复——修复依赖通道内日志

## 关联实体

- wiki/entities/module-batch-executor.md — 通道 B 实现 + 73s 卡顿发生地
- [[concept-batch-evaluation]] — 批跑评测体系
- wiki-minimax/entities/engine-m3.md — A 通道客户端载体
