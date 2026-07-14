---
type: source-summary
title: "数据恢复链分析摘要"
sources:
  - docs/analysis/数据恢复链分析.md
tags:
  - infra
  - data-recovery
  - analysis
status: current
related_gua:
  - GUA-048
  - GUA-049
date: 2026-06-18
---

# 数据恢复链分析摘要

## 核心结论

批跑系统的双重数据通道（WebSocket A + stdout B）虽然提升了可靠性，但仍存在以下风险：

1. **已发生事件**：`game_records/*.json` 曾被误清，需在 wiki 中单独留痕
2. **4 进程 race condition**：`game_ready.json` 并发写入，last-writer-wins（[[gua-049]]）
3. **73s 卡顿**：`game_ready` 等待 + ServerStdoutReader 双重触发（gua-048）
4. **批末对账**：仅能发现不一致，无法修复

## victoryNum 写入清单（4 层）

| 层级 | 通道 | 内容 |
|------|------|------|
| 1 | A 通道 payload | 实时 WebSocket 消息 |
| 2 | A 通道 JSON | 客户端落盘 |
| 3 | B 通道 stdout_line | ServerStdoutReader 解析 |
| 4 | game_records/*.json | 持久化文件 |

## 关联实体

- gua-048 — 73s 卡顿
- [[gua-049]] — mark_game_ready race
- wiki-minimax/entities/gua-033.md — victoryNum 解析（前置）
- wiki/entities/module-batch-executor.md — 通道 B 实现
- wiki/concepts/dual-data-channel-recovery.md — 详细概念页
