---
type: concept
title: "批跑评测体系"
sources:
  - docs/guandan-brain/ISSUES.md
  - docs/guandan-brain/V7-引擎调用链.md
  - docs/analysis/archive/2026-06-18-gua062-batch-eval.md
tags:
  - evaluation
  - batch
  - kpi
status: current
related_gua:
  - GUA-033
  - GUA-059
  - GUA-061
  - GUA-062
date: 2026-06-18
---

# 批跑评测体系

## 核心原则

**批跑是唯一真源**：所有策略改动必须经过离线批跑验证。

## 关键口径

- **局 ≠ 副**（wiki-minimax/entities/gua-033.md 定音）：1 局可含数十副，胜利Num 是会话 3 局合计
- 副胜率：单副内胜出比例
- 局胜率：完整一局中胜出比例
- 队胜率：yf1+yf2 队伍整体胜率

## 引擎胜率锚点

| 引擎 | 指标 | 数值 | 来源 |
|------|------|------|------|
| V7 | 累计队胜率 | 1/42 = 2.4% | [[gua-062]] |
| V7 | vs lalala 局胜率 | 0%（9 局全负） | [[gua-062]] |
| V7 | vs lalala 副胜率 | 8/79 = 10.1% | [[gua-062]] |
| M3 | 累计队胜率 | 81% | 历史 |
| M3 | 最近净盘 | 3 局胜 2（66.7%） | 2026-06-17 |
| M3 | 100% 胜率批跑 | 366 局 | 2026-06-17 |

## 批跑工具

| 工具 | 路径 | 用途 |
|------|------|------|
| 批跑执行器 | batch_executor | 含 latest_victory_num.json |
| 副级分析 | scripts/tools/analyze_v7_round_levels.py | V7 副级分析 |
| 牌谱回放 | scripts/tools/yf_replay.py / YF_REPLAY.bat | 复盘 |
| 组牌引擎测试 | scripts/checks/check_grouping_engine.py | 独立测试 |

## 双重数据通道

- WebSocket → `latest_victory_num.json`（结构化）
- stdout → 日志（可恢复丢失）

## 关联

- wiki-minimax/entities/gua-033.md（局 ≠ 副）
- [[gua-062]]
- wiki/entities/engine-v7.md
- wiki-minimax/entities/engine-m3.md
- wiki/synthesis/synthesis-v7-current-state.md
