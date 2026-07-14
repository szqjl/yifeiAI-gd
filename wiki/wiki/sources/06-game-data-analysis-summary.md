---
type: source-summary
title: "06 局数据分析摘要"
sources:
  - docs/analysis/agent-sessions/06-game-data-analysis.md
tags:
  - analysis
  - game-data
  - session
status: current
related_gua:
  - GUA-048
  - GUA-049
date: 2026-06-20
---

# 06 局数据分析摘要

Agent 会话 #06 的局数据分析记录，主要涉及批跑卡顿与 game_ready 写盘 race condition 的根因定位。

## 关键发现

- **批跑 73s 卡顿**：双根因，详见 [[gua-048]]
- **game_ready 写盘 race condition**：根因已锁定，详见 [[gua-049]]

## 关联 GUA

- GUA-048：批跑 73s 卡顿双根因（P2）
- GUA-049：game_ready 写盘 race condition 根因锁定（P1）

## 相关页面

- [[batch-evaluation]]
- [[ISSUES-summary]]
```

---

## 批次 2：核心 P0 GUA 实体页
