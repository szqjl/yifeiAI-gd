---
type: entity-module
title: "M3 决策引擎模块"
sources:
  - docs/guandan-brain/MOCs/M3-Development.md
tags:
  - module
  - m3
  - decision-engine
status: current
related_gua:
  - GUA-024
  - GUA-025
  - GUA-026
  - GUA-027
  - GUA-028
  - GUA-029
  - GUA-030
  - GUA-031
  - GUA-032
  - GUA-034
  - GUA-035
  - GUA-036
date: 2026-06-18
---

# M3 决策引擎模块

## 模块身份
- **类型**：规则型决策引擎
- **状态**：✅ 现役
- **引擎**：wiki-minimax/entities/engine-m3.md

## 文件清单
- `src/m/m3/m3_decision_engine.py` — 决策主类
- `src/m/m3/m3_utils.py` — 工具函数
- `src/game_logic/trick_state.py` — 牌局状态
- `src/communication/platform_act.py` — 平台通信
- `src/communication/yf1_m3.py` — 队友 1 通信
- `src/communication/yf2_m3.py` — 队友 2 通信

## 关联页面
- wiki-minimax/entities/engine-m3.md
- moc-m3-development
- [[gua-036]]（近期回落）
- [[synthesis-m3-vs-v7-status]]
