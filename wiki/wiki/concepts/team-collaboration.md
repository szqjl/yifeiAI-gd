---
type: concept
title: "双 Agent 协作模式（yf1_m3 + yf2_m3）"
sources:
  - docs/guandan-brain/AGENT_FIRST_MESSAGE.md
  - docs/guandan-brain/ISSUES.md
tags:
  - collaboration
  - workflow
  - multi-agent
status: current
related_gua: []
date: 2026-06-29
---

# 双 Agent 协作模式

## 概念

掼蛋 AI 项目采用多 Agent 协作架构，至少存在两个核心 Agent 角色：**yf1_m3** 与 **yf2_m3**。这是项目的关键问题之一——"团队（yf1_m3 + yf2_m3）的协作模式是什么？"的答案所在。

## 关键要素

1. **Agent 自举**：新会话通过 [[AGENT_FIRST_MESSAGE]] 启动，快速加载项目上下文
2. **职责划分**：两个 Agent 在 M3 决策引擎上分工（具体分工见 AGENT_FIRST_MESSAGE 源文档）
3. **交接协议**：通过 handoff 文档实现跨会话知识传递

## 关联

- 自举消息：[[AGENT_FIRST_MESSAGE]]
- 决策引擎：[[engine-m3]]
- 缺陷追踪：[[ISSUES]]
