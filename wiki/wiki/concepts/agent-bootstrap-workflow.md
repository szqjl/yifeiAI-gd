---
type: concept
title: "Agent Bootstrap 工作流"
sources:
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
tags:
  - workflow
  - agent
  - sop
  - bootstrap
status: current
related_gua:
  - GUA-033
date: 2026-06-17
---

# Agent Bootstrap 工作流

## 定义
新 Agent 上线时必须遵循的 **5 步标准化读法（SOP）**，确保快速进入项目上下文。

## 5 步流程

| 步骤 | 文档 | 目的 | 不可省略原因 |
|------|------|------|--------------|
| 1 | `wiki query` | 持久化知识图谱 | 避免重复劳动，最高优先级 |
| 2 | `ISSUES.md` | P0/P1 问题清单 | 知道待解决缺陷 |
| 3 | `ITERATIONS.md` | 迭代历史 | 理解决策链与背景 |
| 4 | `TASKS.md` | 任务池 | 知道当前该做什么 |
| 5 | `EVAL.md` + `LOCAL_EVAL_CHECKLIST.md` | 评测体系 | 知道怎么验证 |

## 核心原则

### 1. Wiki Query 第一
**LLM Wiki 持久化知识图谱** 是最先要查的资产。
- 工具：`scripts/wiki.py query <主题>`
- 失败兜底：再读 raw 文档
- 反例：直接读 `ISSUES.md` 容易忽略已沉淀的方法论

### 2. 顺序不可乱
从全局状态 → 问题清单 → 决策历史 → 当前任务 → 评测方法
**漏读任何一步**都会导致重复劳动或方向偏差

### 3. 5 步缺一不可
即使是熟悉项目的 Agent，每次重连也要完整走一遍

## 适用范围
- ✅ 新 Agent 首次上线
- ✅ 长会话中断后重连
- ✅ Agent 切换任务线（M3 ↔ V7）
- ❌ 不适用于单回合短任务

## 关联页面
- [[wiki-system]] — Wiki 工具链
- [[v7-current-state]] — V7 状态综合
- wiki-minimax/concepts/batch-evaluation.md — 评测体系
- [[AGENT_BOOTSTRAP-summary]] — 源文档摘要
