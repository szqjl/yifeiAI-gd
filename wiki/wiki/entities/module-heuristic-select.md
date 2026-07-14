---
type: entity-module
title: "module-heuristic-select · 启发式选出函数"
sources:
  - docs/guandan-brain/ISSUES.md
  - src/v/nn/ultimate_win_rate_engine_v7.py
tags:
  - module
  - v7
  - heuristic
  - recommend
status: current
related_gua:
  - GUA-063
  - GUA-075
date: 2026-06-30
---

# module-heuristic-select · 启发式选出函数

V7 决策回退路径中的启发式函数，在 Guard / NN 都不能产出有效推荐时作为最后兑底。

## 主要函数

- `_heuristic_select`：根据当前手牌 + role 选最小损耗出牌
- `_quick_guard_validate`：Guard 硬规则快速校验（R10/R01/R05）

## 位置

`src/v/nn/ultimate_win_rate_engine_v7.py` 中的多个启发式 helper，作为 GUA-075 推荐管线失败后的兑底。

## 关联

- GUA-063：角色驱动的过滤位于 heuristic 之前
- GUA-075：推荐法主路径优先
