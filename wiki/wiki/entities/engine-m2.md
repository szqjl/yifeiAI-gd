---
type: entity-engine
title: "M2 引擎（早期规则引擎）"
sources:
  - docs/analysis/agent-sessions/guandan-basic-knowledge.md
  - docs/guandan-brain/M2_OPTIMIZATION.md
tags:
  - M2
  - 引擎
  - 规则引擎
  - 历史
status: current
related_gua: []
date: 2026-06-21
---

# M2 引擎（早期规则引擎）

## 引擎定位

| 维度 | 说明 |
|------|------|
| 引擎代号 | **M2** |
| 类型 | 规则引擎（非 NN） |
| 状态 | **早期版本**（M3 之前的迭代） |
| 在演进史位置 | M2 → **M3**（当前，已瓶颈） → **V7**（NN，迭代中） |

## 核心模块

| 文件 | 角色 |
|------|------|
| `yf1_m2.py` | Agent 1（写 JSON 持久化） |
| `yf2_m2.py` | Agent 2（对家，仅打日志） |
| `game_scores_m2.json` | 副级 + 局级持久化文件 |
| `batch_executor/executor.py` | 批跑调度器（含 `_count_new_paired_games()`） |

## 架构特征

### 双 Agent 配对
- yf1 / yf2 是一对**对家**（同队）
- 通过**连接顺序**决定座位号（0+2 vs 1+3）
- 双方观察到相同的 `order`，可独立判定胜负

### 持久化策略
- **yf1 独占写 JSON**（`game_scores_m2.json`）
- yf2 仅打日志，避免 race condition
- JSON 结构：`rounds[]`（副级）+ `games[]`（局级）

### 平台接入
- 调用 `offline_platform/guandan_offline_v1006.exe`
- 命令行参数 `target-games N` 控制局数
- 协议字段：`order`、`curRank`、`selfRank`、`oppoRank`

## 已知设计要点
1. **跨副追踪 curRank 判定局结束**（单副消息不够）
2. **order 索引和 ≤ 2** 判定双上
3. **A 级必须双上**才算赢局
4. **连续 2 副 A 未胜**降回 2
5. **A↔2 循环 50 次** → 平局

## 优化记录
- 详见 `docs/guandan-brain/M2_OPTIMIZATION.md`
- 优化点可能涉及：升级判定、A 级特殊规则、JSON 写入并发

## 对 M3 / V7 的影响
- M2 的"yf1 写 / yf2 打日志"协调模式**可能是 M3 的雏形**
- yf1/yf2 配对 + JSON 持久化架构**影响 V7 模块设计**
- 副级 vs 局级双轨追踪思路**延续到 M3/V7**

## 待澄清问题
- yf1_m2 / yf2_m2 在 V7 时代是否仍存在？（历史资产 vs 仍在维护）
- M2 与 M3/V7 的胜负追踪架构是同源演化还是各自独立？

## 关联页面
- [[engine-m3]]：当前主引擎
- [[v7-current-state]]：下一代引擎
- [[guandan-basic-rules]]：M2 实现的基础规则
- [[game-scoring-tracking]]：M2 的核心架构
- [[batch-evaluation]]：M2 的评测体系
