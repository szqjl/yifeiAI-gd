---
type: source-summary
title: "CardCountingNetwork 训练方案（v3）摘要"
sources:
  - docs/guandan-brain/CardCountingNetwork-训练方案.md
tags:
  - source-summary
  - nn
  - card-counting
  - training-methodology
  - phase-0
status: current
related_gua:
  - GUA-057
  - GUA-072
  - GUA-079
  - GUA-091
date: 2026-07-19
---

# CardCountingNetwork 训练方案（v3）摘要

> 来源：`docs/guandan-brain/CardCountingNetwork-训练方案.md`（约 20K 字符，v3 修订版）

## 一句话定位

V7 NN 引擎的**第一个落地模块**：用监督学习训练一个 108 槽位 × 3 状态的记牌网络，为现有 [[module-memory-tracker|确定性 MemoryTracker]] 提供概率升级。

## 核心论点

- **输入 → 输出**：完整出牌序列 → 低维 (108 槽位 × 3 状态) 概率分布
- **Ground Truth 优势**：相较于 BC 端到端训练，记牌任务有**精确 ground truth**（牌确实出过/没出过）
- **反事实后验更新**：P(shape | history_before) → 观察事件 → P(shape | history_after)
- **事件驱动信念更新** 4 个 Head：
  - `counter_opportunity_head`（我方出牌机会计数）
  - `inaction_information_head`（PASS 信息保留）
  - `shape_posterior_head`（牌型后验）
  - `belief_delta_head`（信念增量）

## 模型架构渐进式

| Phase | 模型 | 参数量 | 时长 |
|-------|------|--------|------|
| Phase 1 | LSTM baseline | ~50K | 1-2 周 |
| Phase 2 | Transformer | ~319K | 2-3 周 |
| Phase 3 | 集成到 V7 管线 | — | 2 周 |

## Phase 0-3 路线图

1. **Phase 0（1 周）**：1 周数据采集 + 形式化验证（不依赖 GUA-072 关单）
2. **Phase 1**：LSTM baseline，启动独立
3. **Phase 2**：Transformer，渐进
4. **Phase 3**：集成到 V7 决策管线（与 GUA-079 互锁）

## 关键约束（v3 修订要点）

### 赌注边界
> **Phase 1-3 失败 ≠ NN 路线失败**，仅证"用 7700 样本 + Transformer 监督学习失败"。

避免给读者"输赢全押"的错误印象。

### 3 分类的进贡转移牌问题
- 原 3 分类 {PLAYED / PARTNER_HAND / OPPONENT_HAND} 会把进贡转移牌**错归 OPPONENT_HAND**
- Phase 1 用 `tribute_transfer_events` 驱动事件层解决
- **Phase 1 不做 4 分类**拆分 OPPONENT_A/B

### 硬事实优先于行为推断
- 行为推断只能改变概率，不能覆盖已知事实
- 例：观察到玩家 PASS 单王，他仍可能手里有大王 → 概率上升但不置 0

## 验收标准

- **ECE / MCE / Brier** 校准指标
- **大王小王 / Bomb recall@0.5** 召回门槛
- 形式化验证：纯逻辑盘 + 对照实盘，差异 < 阈值

## 与三大失败案例的关系

| 失败案例 | 教训 |
|----------|------|
| 端到端 BC | argmax collapse → 必须分模块 |
| M3 规则补丁螺旋 | 规则已达瓶颈 → NN 化是出口 |
| 7700 样本 Transformer | 数据规模不足 → Phase 0 优先采数据 |

## 交叉引用

- [[gua-057]] — 本方案是 GUA-057 的落地路径
- [[gua-072]] — 前置条件（代码 100% / 关单条件④批跑验证 pending；Phase 1 不依赖关单）
- [[gua-079]] — Phase 3 集成互锁
- [[gua-091]] — 迁移出口 = intent 体系
- [[concept-card-counting-network-training]] — 概念页
- [[concept-event-driven-belief-update]] — 信念更新方法论
- [[concept-level-card-belief]] — 级牌归属信念
- [[module-memory-tracker]] — 现有确定性记牌
- [[synthesis-ccn-vs-memory-tracker]] — 范式对比
