---
type: concept
title: "GUA 编号体系"
sources:
  - docs/guandan-brain/ISSUES.md
  - docs/guandan-brain/iterations/governance-docs.md
tags:
  - gua
  - governance
  - methodology
status: current
related_gua:
  - GUA-001
  - GUA-061
date: 2026-06-18
---

# GUA 编号体系

## 定义

GUA（Guandan AI Issue）编号体系是双上计分王掼蛋 AI 项目的**缺陷与迭代追踪脊柱**。所有已知缺陷、迭代任务、分析报告都以 GUA-xxx 编号统一挂载。

## 核心规则

1. **唯一编号**：每个缺陷/任务一个 GUA 编号，从 GUA-001 起递增
2. **全生命周期**：从 open → in-progress → resolved → closed 状态流转
3. **跨资料锚点**：ISSUES.md、ITERATIONS、分析报告均通过 GUA 编号关联
4. **P0/P1/P2 优先级**：所有 GUA 必须标注优先级

## 使用场景

- 缺陷登记与追踪
- 迭代任务管理
- 跨文档引用（如 `GUA-033`）
- Agent 会话问题关联

## 关联页面

- ISSUES 总表
- [[gua-045]]
- [[gua-061]]
- governance-docs 迭代
