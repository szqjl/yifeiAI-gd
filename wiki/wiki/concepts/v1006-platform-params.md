---
type: concept
title: "v1006 平台参数字义"
sources:
  - docs/analysis/agent-sessions/guandan-basic-knowledge.md
tags:
  - platform
  - v1006
  - protocol
status: current
related_gua: []
date: 2026-06-18
---

# v1006 平台参数字义

## 概述

`guandan_offline_v1006` 是双上计分王项目的离线评测平台。本概念页沉淀其关键参数与协议字段的字义定义。

## 核心参数

### N（平台参数）

- **N = 局数（games）**
- ❌ **N ≠ 副数（rounds）**
- 跑 N 局意味着跑完整 N 个 game，每个 game 包含多副
- 详见 [[round-vs-game]]

## 关键协议字段

| 字段路径 | 类型 | 含义 |
|---------|------|------|
| `episodeOver.order` | array | `[头游, 二游, 三游, 末游]` 完赛名次 |
| `gameResult.victoryNum` | int | 本局升级数（0/1/2/3） |
| `gameResult.draws` | int | 平局计数（A↔2 循环计数） |
| `act.stage.play.curRank` | int | 当前副的完赛 rank（跨副重置） |
| `act.stage.play.selfRank` | int | 我方在当前副的 rank |
| `act.stage.play.oppoRank` | int | 对方在当前副的 rank |

> `curRank` / `selfRank` / `oppoRank` 是 **副级** 字段，跨副会重置。
> `gameResult.victoryNum` / `gameResult.draws` 是 **局级** 字段，跨局累加。

## 平台版本

- `guandan_offline_v1006`：当前主用离线平台
- 关联模块：wiki/entities/module-batch-executor.md

## 关联概念

- [[guandan-rules]]：协议字段如何编码升级规则
- [[round-vs-game]]：局/副字段边界
- wiki-minimax/entities/engine-m3.md：M3 引擎的协议解析层
- [[decision-metrics]]：基于协议字段的决策指标提取

## 开放问题

1. v1006 之前的版本（v1005 等）字段差异？
2. 是否有 `episodeOver.gameOver` 标志字段明确局边界？
3. 跨平台的协议兼容性如何？
