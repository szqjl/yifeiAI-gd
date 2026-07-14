---
type: source-summary
title: "工作流索引摘要"
sources:
  - docs/guandan-brain/工作流.md
tags:
  - workflow
  - index
  - wf01-wf12
status: current
related_gua: []
date: 2026-07-03
---

# 工作流索引摘要

## 文件定位

`工作流.md` 是 **WF-01 ~ WF-12 工作流的索引真源**，定义每个工作流的触发场景、输入、输出和执行步骤。

## 工作流清单

| 编号 | 名称 | 用途 |
|------|------|------|
| WF-01 | 缺陷录入 | 新 GUA 创建 |
| WF-02 | 缺陷诊断 | 根因分析 |
| WF-03 | 缺陷修复 | 代码改动 |
| WF-04 | 批跑解读 | 离线对局结果分析（含 V7 批跑日志定位 L2 步骤） |
| WF-05 | 引擎迭代 | V7 版本演进 |
| WF-06 | 引擎对比 | V7 vs M3 vs lalala |
| WF-07 | 知识录入 | Skill 沉淀 |
| WF-08 | 复盘归档 | handoff 文档 |
| WF-09 | Skill 规划 | Skill 路线图 |
| WF-10 | 评测设计 | KPI 阈值定义 |
| WF-11 | 残局预处理器 | EndgamePreprocessor 集成 |
| WF-12 | yf 决策链路分析 | my_decisions + 客户端 log → decide 管线还原 |

## V7 执行卡片

工作流.md 内含 **V7 引擎执行卡片**，定义：
- 触发条件（如 BC 模型变更、Guard 规则调整）
- 执行步骤（run_v7_vs_lalala_games.py → analyze_v7_rounds.py）
- 验收标准（参考 [[win-rate-kpi]]）

## Skill 规划

工作流.md 包含 Skill 规划路线图，关联 `docs/knowledge/skills/` 目录。

## 隐含绑定关系

- WF-04 ↔ v7-win-rate-history.md（强绑定）
- WF-12 ↔ workflows/WF-12-yf-decision-trace.md（一对一）
- 工作流.md ↔ 所有工作流文件（索引真源）

## 关联

- [[WF-12-yf-decision-trace-summary]] — WF-12 决策链路工作流详情
- [[v7-win-rate-history-summary]] — V7 战 KPI 真源
- [[workflow-decision-trace]] — 决策链路分析概念
