---
type: source-summary
title: "M-V 系列治理方案摘要"
sources:
  - docs/governance/M-V-Series-治理方案.md
tags:
  - governance
  - m-series
  - v-series
  - process
status: current
related_gua: []
date: 2026-07-03
---

# M-V 系列治理方案摘要

## 文件定位

`docs/governance/M-V-Series-治理方案.md` 是 **M 系列（规则引擎）和 V 系列（NN 引擎）的治理真源**，定义迭代规范、KPI 要求、归档流程。

## 核心治理条款

1. **V 系列战 KPI 强制记录**：每条 V 迭代必须在 `v7-win-rate-history.md`（及前身）记录批跑结果
2. **未实施判定**：评估次数 = 0 的迭代视为未实施
3. **M 系列遗产**：M1 已 frozen，M3 是当前规则引擎基线
4. **V7 战略定位**：V 系列是未来方向，M3 已达瓶颈

## M vs V 分工

| 维度 | M3 | V7 |
|------|----|----|
| 类型 | 规则引擎 | NN 引擎 |
| 状态 | 生产可用但有天花板 | 实验迭代中 |
| 决策依据 | hand-coded rules | BC 模型 + heuristic fallback |
| 当前胜率 | 历史稳定 | 累计 < 1% 队胜率 |
| 治理 | 维护模式 | 重点投入 |

## 关联

- [[v7-win-rate-history-summary]] — V7 KPI 真源
- [[engine-m3]] — M3 引擎条目
- [[engine-v7]] — V7 引擎条目
- [[v7-current-state]] — V7 综合状态
