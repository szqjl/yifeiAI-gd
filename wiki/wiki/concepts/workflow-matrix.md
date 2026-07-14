---
type: concept
title: "工作流矩阵 WF-01~12"
sources:
  - docs/guandan-brain/工作流.md
tags:
  - workflow
  - process
  - wf-series
status: current
related_gua: []
date: 2026-06-29
---

# 工作流矩阵 WF-01~12

## 概述
项目标准工作流体系，对应 `工作流.md`，是 Agent 协作的标准工序。

## 工作流清单

| 编号 | 名称 | 适用场景 | 关联 Skill |
|------|------|----------|-----------|
| WF-01 | 会话启动 | Agent 首次进入会话 | — |
| WF-04 | 批跑胜率 | 批跑后解读 | [[batch-evaluation]] |
| WF-05 | 组牌引擎验证 | grouping_engine 回归 | — |
| WF-12 | yf 决策链路根因 | yf1/yf2 决策缺陷定位 | — |

## 衍生实践
- **局副自检 30 秒**：任何批跑数据使用前先做口径检查
- **推送前检查**：参见 `AGENT_PUSH_CHECKLIST.md`

## 相关页面
- [[workflow-summary]]
- [[batch-evaluation]]
