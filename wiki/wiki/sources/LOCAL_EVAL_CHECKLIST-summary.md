---
type: source-summary
title: "本机评测清单 (LOCAL_EVAL_CHECKLIST)"
sources:
  - docs/guandan-brain/LOCAL_EVAL_CHECKLIST.md
tags:
  - source-summary
  - evaluation
  - sop
  - batch
status: current
related_gua:
  - GUA-021
  - GUA-061
date: 2026-06-18
---

# 本机评测清单 (LOCAL_EVAL_CHECKLIST)

## 文件定位
本机批跑执行的 SOP（标准操作流程），是 批跑评测体系 概念页的具体落地。

## 核心 SOP 项

### 1. 净盘（跑前清空）
- `game_records/`：清空历史对局录像
- `v7/`：清空 V7 引擎相关缓存
- **目的**：避免历史数据污染新一批次的统计

### 2. 局数档位（target-games）
- 推荐 3 / 9 / 12 局（v1006 单次会话 = 3 局）
- **禁止 10**（非 3 倍数会破坏 victoryNum 累计口径）
- 详见 局≠副 概念

### 3. 环境变量
- `BATCH_EXECUTOR_SECONDS_PER_GAME_ESTIMATE`：单局预估耗时，用于调度
- 其他环境变量按需设置

### 4. diagnose-only 诊断模式
- 不实际运行游戏，仅诊断配置和路径
- 用于跑前快速验证环境

## ⚠️ 待更新项
清单首部提及"当前轮次针对 GUA-021（减少问题 PASS）"——**GUA-021 已 closed**，该指向已过期，需更新为：
- 当前 V7 焦点：**GUA-061**（模块化架构）
- 当前 V7 P0：GUA-054 / GUA-055 / GUA-059

## 关联
- 上位概念：批跑评测体系
- 胜利统计口径：victoryNum 口径
- 当前迭代：wiki/entities/engine-v7.md
