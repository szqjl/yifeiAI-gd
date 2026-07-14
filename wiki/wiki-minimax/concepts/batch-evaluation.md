---
type: concept
title: "批跑评测体系"
sources:
  - docs/guandan-brain/COMMANDER_NOTES.md
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
tags:
  - evaluation
  - batch
  - kpi
  - target-games
status: current
related_gua:
  - GUA-033
date: 2026-06-17
---

# 批跑评测体系

## 定义
所有策略改动的 **唯一真源验证方式**——通过离线批跑对局计算胜率 KPI。

## 核心命令

```bash
# V7 vs lalala
python scripts/launchers/v7/run_v7_vs_lalala_games.py --target-games 12

# M3 vs lalala
python scripts/launchers/m/run_m3_vs_lalala_games.py --target-games 12
```

## ⚠️ 关键参数

**`--target-games` 必须是 3 的倍数（3 / 9 / 12），绝对不要用 10**

原因：
- 1 局 = 2 局中先达「双上过关」
- 3 局 = 一轮完整对抗（最小单位）
- 10 局会中途截断，导致 victoryNum 计算错误

## KPI 指标

| 指标 | 公式 | 目标 |
|------|------|------|
| 队胜率 | `[0]+[2]` / 总局 | >90%（PHASE3 新目标） |
| 局胜率 | 同上 | — |
| 副级胜率 | 按 curRank 分组 | — |
| 平均出牌耗时 | 总耗时 / 副数 | <2s |

## 数据落点

- M3 → `game_records/`
- V7 → `game_records_v7/`
- 计分 → `latest_victory_num.json` + `scores.json`

## 关联页面
- wiki-minimax/entities/gua-033.md — 局/副口径
- [[dual-data-channel]] — 数据通道
- wiki/entities/engine-v7.md / wiki-minimax/entities/engine-m3.md — 引擎
- [[tool-analyze-v7-round-levels]] — 副级分析
