---
type: source-summary
title: "Agent Bootstrap 工作流（摘要）"
sources:
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
tags:
  - workflow
  - agent
  - bootstrap
  - sop
status: current
related_gua:
  - GUA-033
date: 2026-06-17
---

# Agent Bootstrap 工作流（摘要）

## 来源
- 原始文件：`docs/guandan-brain/AGENT_BOOTSTRAP.md`（8350 字符）
- 类型：工作流 SOP

## 核心内容
新 Agent 上线的 5 步标准化读法（SOP）：

| 步骤 | 文档 | 目的 |
|------|------|------|
| 1 | `wiki query` | 持久化知识图谱优先（最关键，避免重复劳动） |
| 2 | `ISSUES.md` | 全部 P0/P1 问题清单 |
| 3 | `ITERATIONS.md` | 迭代历史与决策链 |
| 4 | `TASKS.md` | 当前任务池 |
| 5 | `EVAL.md` + `LOCAL_EVAL_CHECKLIST.md` | 评测体系与本地验证清单 |

## 关键原则
- **wiki query 第一**：LLM Wiki 持久化知识图谱（`scripts/wiki.py`）是最先要查的资产
- **顺序不可乱**：从全局状态到具体任务
- **5 步缺一不可**

## 关联页面
- [[wiki-system]] — Wiki 工具链
- [[v7-current-state]] — V7 当前状态
- wiki-minimax/concepts/batch-evaluation.md — 评测体系
