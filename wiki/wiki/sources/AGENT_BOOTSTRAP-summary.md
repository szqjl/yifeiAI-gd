---
type: source-summary
title: "Agent Bootstrap 引导（wiki 入口）"
sources:
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
tags:
  - bootstrap
  - agent
  - 入口
  - 口径债
status: current
related_gua:
  - GUA-033
  - GUA-036
date: 2026-06-29
---

# Agent Bootstrap 引导

## 用途

新 agent session 启动时的**必读入口文档**，强制对齐知识体系基线。

## 核心要求

1. **数据口径**：
   - 局 ≠ 副（GUA-033 定音）
   - victoryNum [0]=[2] / [1]=[3] 镜像校验
   - WF-04 三口径对账

2. **决策方法论**：
   - PB-002 四层闭环
   - WF-12 单步决策链路深挖
   - 5 问准入审查（新增规则）

3. **架构认知**：
   - V7 三层架构（Layer 1/2/3）
   - V7 阶段化方案（阶段 A/B/C）
   - DanZero+ 论文同构

4. **历史教训**：
   - M3 GUA-036：加规则有负收益
   - V 系列失败真根因：KPI 循环缺失 + 静默失败 + 知识库用死
   - 信念建模是阶段 B 核心，非 P2

## ⚠️ 已知口径债

| 文档引用路径 | 真实路径 | 状态 |
|--------------|----------|------|
| `scripts/analysis/analyze_v7_round_levels.py` | `scripts/tools/analyze_v7_round_levels.py` | 需修正 |
| `scripts/analysis/analyze_v7_rounds.py` | `scripts/analysis/analyze_v7_rounds.py` | 一致 |
| `scripts/launchers/v7/run_v7_vs_lalala_games.py` | `scripts/launchers/v7/run_v7_vs_lalala_games.py` | 一致 |

## 落点

- [[gua-033]] — 局≠副定音
- [[gua-036]] — M3 加规则负收益教训
- [[purpose]] — Wiki 目标
- schema — Wiki 结构规范
