---
type: concept
title: "批末 victoryNum 自洽校验"
sources:
  - docs/guandan-brain/issues/GUA-033-completion.md
  - docs/knowledge/platform-data-interpretation.md
tags:
  - batch-validation
  - victory-num
  - platform
  - m3-engine
status: current
related_gua:
  - GUA-033
  - GUA-061
date: 2026-06-17
---

# 批末 victoryNum 自洽校验

## 背景

平台 v1006 exe 的 `settingTimes` 参数实测固定为 3，与 PDF 说明书不一致——属于**离线 exe 实现缺陷**。批跑统一使用 `batch_games` + `gameOver` fallback 兜底。

> 口径冲突已在 wiki-minimax/entities/gua-033.md（2026-05-31 closed）定音。

## 核心规则

### 1. 批末自洽校验
- WebSocket 收到的 `[0]+[1]` 应等于 `batch_games`
- 不一致则报错并触发重跑

### 2. gameResult 累计
- 按 3 局（**局 ≠ 副**）累计
- 禁止读 `episodeOver.result[4]`

### 3. 批间清理
- 清空 `pending_result_files` 防止跨批回填污染

### 4. 三条数据源规则（并存）
| 场景 | 规则 |
|------|------|
| `gameOver` 早退 | **不写** `vn` / `gameResult` |
| 正常结束 | 读 `final` 或 `vn`（择一来源） |
| 错误源 | **禁止** `episodeOver.result[4]` |

## 关键模块

- `current_batch.json` — 批跑元数据
- `batch_executor` — 批跑执行器
- `restart_manager` — 重启管理

## 关联原理

- `platform-data-interpretation.md §2` — 平台侧根因真源
- 「局 ≠ 副」— 批末自检的口径基础

## 交叉引用

- wiki-minimax/entities/gua-033.md — 已关单 GUA
- [[platform-data-interpretation]] — 平台数据解释
