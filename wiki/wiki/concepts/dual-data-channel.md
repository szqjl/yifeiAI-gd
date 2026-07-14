---
type: concept
title: "双重数据通道 (WebSocket + stdout 日志)"
sources:
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
tags:
  - data-pipeline
  - websocket
  - logging
  - reliability
status: current
related_gua:
  - GUA-033
date: 2026-06-17
---

# 双重数据通道 (WebSocket + stdout 日志)

## 定义
V7 引擎设计的 **数据可靠性架构**：用两条独立通道同时落盘数据，确保单一通道故障时数据不丢失。

## 两条通道

### 通道 1：WebSocket 数据通道
- **写入**：`latest_victory_num.json`（覆盖式）+ `game_records/`（追加式）
- **频率**：每副/每局实时推送
- **进程**：`v7_game_recorder.py` / `game_recorder.py`

### 通道 2：stdout 日志通道
- **写入**：进程 stdout 日志（含 `vn_source` 标记）
- **格式**：可被 `grep` / `awk` 解析
- **作用**：WebSocket 失败时兜底

## 四层 victoryNum 写入清单

数据写入的 4 个落点（必须全部覆盖才算完整）：

| # | 目标 | 写入方式 | 用途 |
|---|------|----------|------|
| 1 | `latest_victory_num.json` | 覆盖 | 当前会话状态快照 |
| 2 | stdout 日志 | 追加 | 防丢失兜底 |
| 3 | `scores.json` | 覆盖 | 累计计分 |
| 4 | `game_records/` | 追加 | 牌谱历史 |

## 三步恢复法

当数据丢失/异常时使用：

1. **读 `latest_victory_num.json`** → 获取最新 victoryNum
2. **搜日志 `vn_source`** → 交叉验证
3. **计算队胜率** → `[0]+[2]` vs `[1]+[3]`

## 设计动机
- 单通道故障在长跑批中常见
- WebSocket 断连/超时 → 数据丢失
- stdout 日志易被截断 → 不全
- **双通道 + 交叉验证** = 高可用

## 关联页面
- [[platform-data-interpretation]] — 局/副口径解读
- wiki-minimax/entities/gua-033.md — victoryNum 定音
- data-recovery-chain — 数据恢复链
