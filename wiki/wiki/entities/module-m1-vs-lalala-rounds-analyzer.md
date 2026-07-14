---
type: entity-module
title: "M1 vs lalala 逐副深度分析器"
sources:
  - docs/analysis/agent-sessions/M1 vs lalala 逐副深度分析脚本.md
tags:
  - module
  - m1
  - lalala
  - analysis
  - round-level
status: current
related_gua:
  - GUA-033
date: 2026-06-18
---

# M1 vs lalala 逐副深度分析器

## 模块概述

一个独立的 Python 分析脚本，用于逐副（round）粒度对比 **M1 引擎**与 **lalala** 对手的对局表现。属于"批跑后下钻分析"工具链的一环。

## 输入 / 输出

### 输入
- `game_records/*.json`：副级对战记录文件（由 wiki/entities/module-batch-executor.md 落盘）

### 输出
- 副级胜负对照表
- pass_rate / problem_passes 统计
- 决策质量分析报告

## 核心函数

| 函数 | 职责 | 备注 |
|------|------|------|
| `extract_game_info()` | 抽取 game_id / round_num / 玩家名次 | — |
| `load_round()` | 加载单副数据 | — |
| `analyze_round_result()` | 判定单副胜负 | 基于 `episodeOver/order` |
| `analyze_m1_decisions()` | 逐决策分析 | 输出 action / is_pass / 详情 |
| `main()` | 入口 | 按 `(game_id, round_num)` 配对 yf1 + yf2 |

## 依赖与上下游

- **上游数据**：`game_records/*.json`（由批跑产生）
- **下游消费**：分析报告、决策质量审计

## 已知问题

- ⚠️ 文档截断，problem_passes 判定逻辑、整体胜率 KPI 未呈现
- ⚠️ M1 已退役，本模块作为**历史回溯工具**而非活跃分析器
- ⚠️ Python 2/3 兼容性未在截断部分确认

## 关联页面

- [[engine-m1]]：M1 引擎
- entity-opponent-lalala：lalala 对手
- wiki/concepts/round-level-decision-analysis.md：副级决策分析方法论
- [[concept-batch-evaluation]]：批跑评测体系
- wiki/entities/module-batch-executor.md：副级记录落盘模块
