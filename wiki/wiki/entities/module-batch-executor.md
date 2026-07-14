---
type: entity-module
title: "batch_executor 批跑引擎"
sources:
  - docs/guandan-brain/SCRIPT_INDEX.md
  - docs/guandan-brain/工作流.md
tags:
  - module
  - batch
  - executor
  - runner
status: current
related_gua:
  - GUA-044
date: 2026-06-29
---

# batch_executor 批跑引擎

## 身份

- **核心文件**：
  - `batch_executor.py`（核心）
  - `batch_executor_gui_v7.py`（V7 GUI 版）
  - `run_v7_vs_lalala_games.py`（V7 vs lalala 入口）
  - `run_m3_vs_lalala_games.py`（M3 vs lalala 入口）

## 关键约定

| 项 | 约定 | 来源 |
|----|------|------|
| **批跑真源** | `current_batch.json`（`batch_games` 字段） | SCRIPT_INDEX |
| **server_vn_raw fallback** | 当 server 不可达时回退读本地 | 工作流 WF-04 |
| **`vn_source` 字段** | 数据汇报必含（`batch_games` / `server_vn_raw`） | 工作流 WF-04 |
| **`--target-games`** | 必须是 3 的倍数（3/9/12） | SCRIPT_INDEX |
| **exe 固定 3 局** | 单次批跑最少 3 局（tol ≥3） | 工作流 §9 |
| **handshake 四席就绪** | 批跑前置（GUA-044） | SCRIPT_INDEX |

## 关联 GUA

- **GUA-044**：handshake 四席就绪门闩（批跑前置条件）

## 链接

- 批跑评测体系：[[batch-evaluation]]
- 脚本索引：[[SCRIPT_INDEX-summary]]
- 工作流矩阵：[[workflow-summary]]
- V7 引擎：[[engine-v7]]
- M3 引擎：[[engine-m3]]
