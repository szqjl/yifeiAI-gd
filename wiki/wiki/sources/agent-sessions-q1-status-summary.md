---
type: source-summary
title: "项目现状速查表 (Agent Session 01) - 摘要"
sources:
  - docs/analysis/agent-sessions/01-project-status.md
tags:
  - agent-session
  - status
  - project-overview
status: current
date: 2026-06-18
---

# 项目现状速查表 (Agent Session 01) - 摘要

## 文档定位

Hermes Agent 在 2026-06 项目状态自检的速查表，输出项目核心 KPI 和关键路径。

## 关键状态摘要

### V7 引擎状态
- **当前阶段**：BC 热启动完成（GUA-038），RL 自对弈未启动
- **BC 模型分数**：84.3%（测试集）
- **实战胜率 vs lalala**：0%（核心痛点）
- **下一步**：GUA-039 启动自对弈 Actor

### 引擎演进史
| 引擎 | 路线 | 胜率 | 状态 |
|------|------|------|------|
| M1 | 硬编码规则 | 0% vs lalala | 已弃用 |
| M2 | 重构硬编码 | 未评测 | 80% 进度，已停 |
| M3 | 决策引擎 | 70% | 当前生产 |
| V2-V6 | 纯 NN/RL | 未达产 | 全部失败 |
| V7 | 模块化 NN | 0% BC 落地 | 当前主迭代 |

### 关键 P0 GUA
- GUA-022（M1 队胜率 0%）—— 关闭中，待 Lv2 补全
- GUA-014（拆牌与优先级）—— 持续观察
- GUA-042（V7 行为边界）—— 本次决策：弃用

### 团队分工
- yf1_m3 + yf2_m3：双人协作，client 不同
- 共享 src/decision/ 代码
- M1 时代验证：两人代码差异对胜率无影响（GUA-020 已证）

## 关键问题清单

参见 [[agent-sessions-q2-questions-summary]] 深度展开。

## 交叉引用

- 项目状态总览 → overview
- 引擎详情 → wiki-minimax/entities/engine-m3.md / wiki/entities/engine-v7.md
- M1 0% 根因 → synthesis-m1-zero-winrate
