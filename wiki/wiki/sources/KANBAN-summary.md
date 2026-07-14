---
type: source-summary
title: "KANBAN 使用指南摘要"
sources:
  - docs/governance/KANBAN.md
tags:
  - governance
  - kanban
  - workflow
  - team-collaboration
status: current
related_gua: []
date: 2026-06-18
---

# KANBAN 使用指南摘要

> **定位**：团队协作工具使用指南

## 工作流状态机

```
triage → todo → ready → running → done
```

| 状态 | 说明 |
|------|------|
| `triage` | 待分诊（新任务入口） |
| `todo` | 已分诊，待排期 |
| `ready` | 已就绪，可领取 |
| `running` | 执行中 |
| `done` | 已完成 |

## Worker 支持

| Worker | 状态 |
|--------|------|
| ACP | 🧪 实验 |
| opencode run | ✅ 可用 |
| cursor-agent | ⚠️ 未测 |

## 飞书集成

通过 FeishuKanbanCardGenerator（JSON 2.0）将看板状态同步到飞书。

## 关联页面

- wiki/sources/KANBAN_CARD_INTEGRATION-summary.md — 飞书卡片集成
- [[M-V-Series-治理方案-summary]] — 治理总纲
