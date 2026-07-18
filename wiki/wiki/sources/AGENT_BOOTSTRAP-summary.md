---
type: source-summary
title: "AGENT_BOOTSTRAP 摘要"
sources:
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
tags:
  - source-summary
  - bootstrap
  - agent
  - workflow
status: current
related_gua:
  - GUA-091
date: 2026-07-19
---

# AGENT_BOOTSTRAP 摘要

> 来源：`docs/guandan-brain/AGENT_BOOTSTRAP.md`（约 11.6K 字符）

## 用途

yf1_m3 / yf2_m3 两个 Agent 会话的**冷启动手册**。所有新会话第一步必须读此文档。

## 协作模式

| 角色 | 职责 |
|------|------|
| yf1_m3 | 主 Agent：编码、批跑、修复 |
| yf2_m3 | 副 Agent：评审、根因诊断、批跑观察 |

## 关键工作流

### 5 问准入审查
对每个 GUA / Patch 进入实施前必过：

1. **一类局面？** — 是否覆盖一类典型场景
2. **可沉意图层？** — 能否下沉到 _stage_mid_dispatch intent 体系
3. **P0 止血？** — 是否堵住 R-D 根因
4. **pytest + trace + 批跑闭环？** — 单元测试 + 日志追踪 + 离线验证
5. **迁移出口？** — 是否指向 BC 训练 / Self-play RL / GUA-091 intent 体系

### 局 ≠ 副口径
- **1 局 = 多副**（通常 4 副左右）
- `exe N = N 局 ≠ N 副`
- `victoryNum[0] + victoryNum[1] = batch_games`（双上累计）

## 关键 Patch 类型

| 类型 | 典型 GUA |
|------|----------|
| 让道修复 | GUA-135, GUA-150 |
| 记牌增强 | GUA-057, GUA-072 |
| 残局分类 | GUA-079 三层根因 |

## 跨 Agent 数据传递

通过 `docs/guandan-brain/handoffs/` 下时间戳文件。

## 交叉引用

- [[gua-091]] — intent 体系（迁移出口主目标）
- [[concept-three-layer-decision-pipeline]] — L0/L1/L2
- [[concept-batch-evaluation]] — 批跑流程
