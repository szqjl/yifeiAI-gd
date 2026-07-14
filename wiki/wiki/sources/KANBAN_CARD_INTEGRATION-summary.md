---
type: source-summary
title: "飞书看板卡片集成方案摘要"
sources:
  - docs/governance/KANBAN_CARD_INTEGRATION.md
tags:
  - feishu
  - kanban
  - integration
  - json-2.0
status: current
related_gua: []
date: 2026-06-18
---

# 飞书看板卡片集成方案摘要

> **核心模块**：`feishu_kanban_card_generator.py`  
> **协议版本**：JSON 2.0

## 功能说明

将本地 KANBAN 状态机（`triage → todo → ready → running → done`）通过飞书卡片协议推送到飞书群/文档，实现：

- 任务状态实时同步
- Worker 分配通知
- 进度可视化

## 关联页面

- [[KANBAN-summary]] — KANBAN 使用指南
- [[M-V-Series-治理方案-summary]] — 治理总纲
- feishu_kanban_card_generator.py — 生成器模块
