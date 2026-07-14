---
type: concept
title: "Agent 工作流（WF-01~11）与 Skill 矩阵"
status: current
date: 2026-06-22
sources:
  - docs/guandan-brain/工作流.md
  - docs/guandan-brain/AGENT_FIRST_MESSAGE.md
tags:
  - workflow
  - skill
  - agent
  - orchestration
related_gua:
  - GUA-080
  - GUA-054
related_workflow: WF-01,WF-02,WF-03,WF-04,WF-05,WF-06,WF-07,WF-08,WF-09,WF-10,WF-11
---

# Agent 工作流（WF-01~11）与 Skill 矩阵

## 概述

`docs/guandan-brain/工作流.md` 定义了 11 个核心工作流（WF-01~WF-11），覆盖 Agent 从接手、迭代、验证、交接的全生命周期。每个工作流绑定一个或多个 Skill。

## 工作流索引

| WF | 名称 | 主用途 | 关联 Skill | 关键产物 |
|----|------|--------|------------|----------|
| WF-01 | 会话启动 | 读首条消息、加载上下文 | `guandan-session-start`（P0 ✅） | 工作区状态快照 |
| WF-02 | 任务识别 | 判定当前任务属于哪条线（v7-dev / m-dev） | `guandan-session-start`（🔶 并入） | 任务标签 |
| WF-03 | 文档检索 | 读 GUA/Iteration/Playbook | `guandan-session-start`（🔶 并入） | 相关文档清单 |
| WF-04 | 数据口径核对 | 局 vs 副 等口径校验 | `guandan-session-start`（🔶 并入） | 口径声明 |
| WF-05 | 组牌引擎验证 | 跑 `check_grouping_engine.py` | `guandan-grouping-engine`（P0 ✅） | 验证日志 |
| WF-06 | 批跑评测 | 启动离线对局 | `guandan-batch-eval`（P0 ✅） | 胜率 KPI |
| WF-07 | Git 提交流程 | commit / push 校验 | `guandan-git-push`（P0 ✅） | 提交记录 |
| WF-08 | 交接班 | 写 handoff | `guandan-handoff-continue`（P1 ✅） | handoff 文档 |
| WF-09 | 修改 v3 引擎 | v3 迭代（待建） | `guandan-modify-v3`（P1 待建） | — |
| WF-10 | 修改 m3 引擎 | m3 迭代（待建） | `guandan-modify-m3`（P2 待建） | — |
| WF-11 | **Playbook 升格** | 经验沉淀到 Playbook | （隐式，无独立 Skill） | Playbook 文档 |

## Skill 矩阵

| Skill | 优先级 | 状态 | 覆盖工作流 | 说明 |
|-------|--------|------|-----------|------|
| `guandan-session-start` | P0 | ✅ | WF-01（主）/ WF-02,03,05（🔶 并入） | **张力预警**：边界需厘清，是否真正覆盖 WF-05 待确认 |
| `guandan-batch-eval` | P0 | ✅ | WF-06 | 离线对局批跑 |
| `guandan-git-push` | P0 | ✅ | WF-07 | pre_push_validate.py 校验 |
| `guandan-grouping-engine` | P0 | ✅ | WF-05 | 组牌引擎单测验收入口 |
| `guandan-handoff-continue` | P1 | ✅ | WF-08 | 交接班规范 |
| `guandan-modify-v3` | P1 | 待建 | WF-09 | v3 引擎迭代模板 |
| `guandan-modify-m3` | P2 | 待建 | WF-10 | m3 引擎迭代模板 |
| `guandan-replay-analysis` | P2 | 待建 | — | 复盘分析 |
| `guandan-wiki-query` | P2 | 待建 | — | Wiki 查询接口 |

## 客户端与分支

- **客户端**：`yf1_v7` / `yf2_v7`（V7 双客户端，A/B 对照）
- **活跃分支**：
  - `v7-dev` — V7 主迭代线（当前主战场）
  - `m-dev` — M3 维护线（M1 已 frozen，见 GUA-022）

## WF-11 升格方法论（重要）

WF-11 没有独立 Skill，因为它不是一个「执行型」工作流，而是「沉淀型」工作流。完整升格条件见 [[playbook-methodology]]：

1. 同类问题再现（≥2 个 GUA）
2. 可复现验证命令
3. 反例
4. 人类定音

## 首条消息模板（AGENT_FIRST_MESSAGE.md）

Agent 会话启动时，第一条消息应包含：

1. **工作区状态**（从 WF-01）
2. **当前任务定位**（WF-02）
3. **关键 GUA 引用**（WF-03）
4. **数据口径声明**（WF-04）— 局 ≠ 副
5. **下一步计划**

> ⚠️ **张力**：原模板第一条指向 WF-05「组牌引擎单测」，但 PB-001 升格后更精确的做法是「WF-05 + PB-001」。建议更新模板。

## 关联阅读

- [[playbook-methodology]] — WF-11 详细方法论
- [[playbook-pb-001]] — WF-11 首个产出
- [[gua-080]] — WF-05 当前主战场
- [[batch-evaluation]] — WF-06 详细 KPI
