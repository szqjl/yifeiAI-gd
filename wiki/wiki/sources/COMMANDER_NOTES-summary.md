---
type: source-summary
title: "指挥官工作笔记摘要（COMMANDER_NOTES.md，M1 阶段历史）"
sources:
  - docs/guandan-brain/COMMANDER_NOTES.md
tags:
  - commander
  - history
  - m1
  - m3
  - outdated
status: outdated
related_gua:
  - GUA-022
  - GUA-014
  - GUA-050
date: 2026-06-17
---

# 指挥官工作笔记摘要（M1 阶段历史）

> ⚠️ **已过时（outdated）**。原文档时间戳 **2026-05-24**，记录的是 **M1 阶段**的指挥决策与 P0 清单。
> 价值在**过程留痕**与**P0 任务来源追溯**，Wiki 当前以 v7-dev 为主线。
> 配套新文档：[[AGENT_BOOTSTRAP-summary]]、[[AGENT_PUSH_CHECKLIST-summary]]

## 1. 文档定位

- **作者**：良总（指挥官）
- **时间**：2026-05-24
- **覆盖范围**：M1（规则引擎）→ M2/M3 演进期
- **重要引用源**：
  - `reviews/架构规则分析_*.md`
  - `M1_vs_lalala.md`
  - `M1_ARCHITECTURE.md`

## 2. M1 vs V 系列路线之争（未决）

- **M1/M2/M3**：规则引擎路线
- **V4/V5/V6**：神经网络路线（早期实验）
- **当前定论**（AGENT_BOOTSTRAP v7.1）：**V7 = 深度学习胜率引擎是当前主线**
- **遗留**：M 系列仍有 m-dev 分支维护，治理入口见 `governance/M-V-Series-治理方案.md`

## 3. P0 任务清单（已被 AGENT_BOOTSTRAP §5 继承）

1. `choose_bomb()` 最小代价炸弹择优
2. `context` 补 `pass_num/numofnext/numofgreaterPos`
3. `combine_handcards()` 修复（关联 GUA-022）

## 4. Batch Executor 自启动问题详述

> 此节是 wiki/entities/module-batch-executor.md 的来源之一。

- **进程链**：`executor.py` → `TrackedClientProcess` → yf1/yf2 客户端
- **监控指标**：
  - 60s 宽限期
  - 连续 2 次不足才终止本批
  - 连续 3 次无进度熔断
- **配置项**：`BATCH_EXECUTOR_MAX_TOTAL_RESTARTS`
- **单实例锁**：`tmp/.batch_executor.lock`

## 5. 当前分支说明（已过时）

- **文档声明**：「当前分支：m-dev」
- **现状**：已切换至 v7-dev（2026-06-17）
- **处理**：保留作历史，wiki/overview 已注明 wiki 当前以 v7-dev 为准

## 关联页面

- [[AGENT_BOOTSTRAP-summary]] — 替代性新文档
- wiki-minimax/entities/engine-m3.md — M3 引擎
- wiki/entities/module-batch-executor.md — Batch Executor 模块
- [[GUA-022]] — combine_handcards 缺陷
- [[branch-strategy]] — 分支策略
```

---
