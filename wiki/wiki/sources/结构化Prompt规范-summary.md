---
type: source-summary
title: "结构化Prompt规范 - 摘要"
sources:
  - docs/development/结构化Prompt规范.md
tags:
  - development-guide
  - prompt-engineering
  - specification
status: current
related_gua: []
date: 2026-06-18
---

# 结构化Prompt规范 - 摘要

## 概述

《结构化Prompt规范》定义了双上计分王项目中所有 LLM/Agent 交互的 Prompt 编写标准，确保输出一致性与可解析性。

## 关键主题

- **Prompt 模板结构**：角色定义、任务描述、输出格式、约束条件
- **输出格式约定**：JSON Schema、Markdown 块、字段命名
- **Agent 协作规范**：yf1_m3、yf2_m3 等 Agent 角色的 Prompt 模板
- **错误处理**：边界条件、重试机制、降级策略

## 与其他资料的关系

- 是 gua-dan-ai-dev-guide 的下层规范
- 与 wiki-minimax/concepts/batch-evaluation.md 中的"批跑 Prompt 模板"部分相关
- 适用于所有 Agent 会话记录（如 `docs/analysis/agent-sessions/`）

## 关联概念

- wiki-minimax/concepts/batch-evaluation.md — 批跑评测中 Prompt 模板的应用
