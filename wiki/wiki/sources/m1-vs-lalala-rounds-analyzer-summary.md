---
type: source-summary
title: "M1 vs lalala 逐副深度分析脚本"
sources:
  - docs/analysis/agent-sessions/M1 vs lalala 逐副深度分析脚本.md
tags:
  - m1
  - lalala
  - round-analysis
  - legacy
status: draft
date: 2026-06-18
---

# M1 vs lalala 逐副深度分析脚本

## 文件概述

本文件是位于 `docs/analysis/agent-sessions/` 下的分析资产，记录了一个用于逐副（round）粒度对比 **M1 引擎**与 **lalala** 对手表现的 Python 分析脚本。

- **字符数**：约 20015
- **截断状态**：⚠️ 文档在 `m1_victories` / `lalala_victories` 统计段落处被截断，关键 KPI（胜率、pass_rate 分布、最终结论）未呈现
- **依赖数据**：`game_records/*.json`（副级对战记录）

## 已读部分摘要

### 1. 脚本主体结构

脚本是一个独立的 Python 工具，主要函数如下：

| 函数名 | 职责 |
|--------|------|
| `extract_game_info()` | 从 game_records JSON 中抽取 game_id、round_num、玩家名次 |
| `load_round()` | 加载单副（round）数据 |
| `analyze_round_result()` | 判定单副胜负（基于 `episodeOver/order`） |
| `analyze_m1_decisions()` | 逐决策分析：提取 action 序列、`is_pass` 标记、决策详情 |
| `main()` | 入口函数，按 `(game_id, round_num)` 配对 yf1_m1 + yf2_m1 双 M1 数据 |

### 2. 核心数据字段

- `my_decisions`：玩家决策序列（包含 `action`、`is_pass` 等字段）
- `episodeOver/order`：最终名次（用于判定胜负）
- `game_records/*.json`：副级对战记录文件

### 3. 关键概念

- **副级对战分析**：以单副（round）为粒度，分析 M1 决策质量与胜负的相关性
- **yf1 + yf2 配对分析**：按 `(game_id, round_num)` 配对 yf1 和 yf2 的副级记录，对比双 M1 表现
- **pass_rate**：决策中 Pass 占比
- **problem_passes**：问题 Pass（⚠️ 判定逻辑未在已读部分呈现）

## 未读 / 截断部分

- `m1_victories` / `lalala_victories` 统计
- 整体胜率 KPI
- pass_rate 分布
- 决策质量汇总
- 最终结论

> **建议**：获取完整文件后补全本页面 `status: current` 并扩充 KPI 段落。

## 关联页面

- [[engine-m1]]：M1 引擎（当前为历史对照基线）
- entity-opponent-lalala：lalala 对手（需新建）
- wiki/concepts/round-level-decision-analysis.md：副级决策分析方法论
- [[module-m1-vs-lalala-rounds-analyzer]]：本脚本作为独立模块
- [[concept-batch-evaluation]]：批跑评测体系（副级数据来源）
- wiki/entities/module-batch-executor.md：副级记录落盘模块
