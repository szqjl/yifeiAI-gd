---
type: entity-engine
title: "M1 引擎 (frozen)"
sources:
  - docs/development/M1_ARCHITECTURE.md
  - docs/development/AI首秀分析报告.md
tags:
  - engine
  - m1
  - rule-based
  - frozen
  - predecessor
status: current
related_gua:
  - GUA-022
  - GUA-014
  - GUA-021
date: 2026-07-15
---

# M1 引擎 (frozen)

## 状态

**已冻结 (frozen)** —— 由 GUA-022 标记，队胜率 KPI = 0，M1 不再作为主迭代方向。

M1 是 M 系列的起点与前身，[[engine-m3]] 是其继承者。

## 定位

`RuleBasedDecisionEngineM1` —— 硬编码规则引擎，所有决策逻辑写死在代码中，无学习能力。与 [[engine-v7]] 的 NN 路线形成对照：

| 维度 | M1 | V7 |
|------|----|----|
| 决策方式 | 硬编码 if-else 规则 | 神经网络策略 |
| 路线 | 规则线 | NN 线 |
| 状态 | frozen (GUA-022) | 实验线 (v7-dev) |
| 客户端 | yf1_m1 / yf2_m1 | yf1_v7 / yf2_v7 |
| 数据目录 | game_records | game_records_v7 |

## 核心架构

### 5 阶段路由

M1 引入 [[stage-router-architecture]]：**5 阶段 × 2 模式 = 10 个 handler**：

- 阶段：`opening` / `mid_early` / `mid_late` / `endgame_early` / `endgame_late`
- 模式：`active` (主动) / `passive` (被动)

### 模块组成

- `StageRouter` —— 路由分发
- `BasePhaseHandler` —— handler 基类
- `phase_handlers/` —— 10 常规 + 2 特殊 (TributeHandler / BackHandler)
- `strategy_engine` —— 策略主入口

### 共用层

M1 与 V 系列共享部分代码层（牌型识别、回合驱动），但决策核心独立。

## 缺陷历史

| GUA | 标题 | 状态 |
|-----|------|------|
| [[gua-022]] | M1 frozen, 队胜率 0 | P1 |
| [[gua-014]] | 拆牌优先级 | P2 |
| [[gua-021]] | Router 兜底修复 | 已修复 |

## 历史价值

M1 是项目第一个完整规则引擎，承担：
1. 验证阶段路由架构的可行性
2. 建立 yf1/yf2 双队对抗测试框架
3. 作为 [[first-debut-baseline]] 之后的第一个有结构对手

M1 frozen 之后，[[engine-m3]] 接管主迭代，沿用阶段路由思想但修复了多处硬编码缺陷。
