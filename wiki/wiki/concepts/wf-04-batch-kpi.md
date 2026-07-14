---
type: concept
title: "工作流 WF-04 · 批跑 KPI"
sources:
  - docs/guandan-brain/工作流.md
  - docs/guandan-brain/EVAL.md
tags:
  - workflow
  - wf-04
  - batch
  - kpi
status: current
related_gua:
  - GUA-096
date: 2026-06-30
---

# 工作流 WF-04 · 批跑 KPI

## 目的

读取、解释、上报批跑数据，以 局/副/victoryNum 三口径为准。

## 主要动作

1. 读 `batch_executor/latest_victory_num.json`、`game_records[/_v7]/*.json`
2. 计算 0+2 与 1+3 队胜率
3. 与历史 `v7-win-rate-history.md` 对比
4. 输出局/副/达A 分布 + 机会主义事件

## 关联

- GUA-096：净盘后强制落盘 hook
- GUA-097：IP 对照批跑 helper

- GUA-097：IP 对照批跑 helper

## 解读 SOP 跳转

- **新**：解读批跑数据请直接用 → [[wf-04-batch-data-interpretation]]（标准 SOP）
- 工作流侧简版：`docs/guandan-brain/工作流.md` §2.3
- 历史 query 答案（已过期）：[[query-0630-0935-如何-解读-批跑数据-流程-步骤]]
