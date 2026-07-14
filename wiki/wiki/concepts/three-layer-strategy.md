---
type: concept
title: "掼蛋 AI 三层战略框架 (Lv1/Lv2/Lv3)"
sources:
  - docs/guandan-brain/掼蛋AI自我进化-随机应变套路.md
  - docs/analysis/agent-sessions/03-deep-analysis-summary.md
tags:
  - strategy
  - framework
  - lv1
  - lv2
  - lv3
status: current
related_gua:
  - GUA-014
  - GUA-022
  - GUA-037a
date: 2026-06-18
---

# 掼蛋 AI 三层战略框架 (Lv1/Lv2/Lv3)

## 概念定义

掼蛋 AI 战略决策的三层抽象。是 M1 0% 胜率根因分析的核心框架，也是 V7 模块化训练的目标覆盖矩阵。

## 三层结构

| 层级 | 名称 | 范围 | 时间尺度 | 决策密度 |
|------|------|------|----------|----------|
| Lv1 | 个别决策 | 单副出牌选择 | 1 步 | 高（每副 30+ 步） |
| Lv2 | 队伙联动 | 同伴配合、火力集中 | 多副 | 中 |
| Lv3 | 全局对抗 | 一局内多副策略、抗贡、进贡 | 1 局 | 低 |

## 各层详解

### Lv1：个别决策
- **范围**：单副出牌时选择哪张牌
- **典型决策**：拆牌/组牌/PASS/管牌
- **现有覆盖**：M3 决策引擎（70% 胜率基础）
- **V7 对应**：ActionNetwork + CardGroupingNetwork
- **问题**：M1 时代仅有 Lv1，导致 0% 胜率（无 Lv2/Lv3 支撑）

### Lv2：队伙联动
- **范围**：与 teammate_pos 配合
  - 火力集中（两人同时压制一家）
  - 帮队友跑牌
  - 信号传递（出牌暗示手牌）
- **现有覆盖**：M3 部分（70% 胜率核心来源）
- **V7 对应**：StrategyNetwork + 信念向量
- **关键挑战**：跨副决策（出牌 A 时考虑 3 副后局势）

### Lv3：全局对抗
- **范围**：一局内多副的整体战略
  - 抗贡/进贡决策
  - 升级/降级时机
  - 关键副的取舍
- **现有覆盖**：**未实现**（M1/M3/V7 均为空）
- **V7 对应**：long_term_reward head + 记忆追踪
- **关键挑战**：长程信用分配

## M1 0% vs M3 70% 的根因

| 引擎 | Lv1 | Lv2 | Lv3 | 胜率 |
|------|-----|-----|-----|------|
| M1 | ✅ | ❌ | ❌ | 0% |
| M3 | ✅ | 部分 | ❌ | 70% |
| V7 目标 | ✅ | ✅ | ✅ | 目标 80%+ |

**关键洞察**：Lv1 是基础但不充分；缺 Lv2 即 0% 胜率；Lv2 是质变点。

## V7 模块化映射

```
Lv1 → ActionNetwork + CardGroupingNetwork
Lv2 → StrategyNetwork + 信念向量（套路一）
Lv3 → long_term_reward head + 记忆追踪（套路三）
```

## 历史教训：指标改善 ≠ 胜率提升

PHASE2 五轮迭代（GUA-020/GUA-021）：
- Lv1 指标改善：PASS 率↓、近似 PASS 清零
- Lv2/Lv3：未动
- 局胜率：0%
- **结论**：Lv1 优化无法突破 0% 胜率瓶颈

## 交叉引用

- M1 根因 → synthesis-m1-zero-winrate
- V7 模块化 → [[modular-training-v7]]
- 套路体系 → [[guandan-self-evolution-patterns-summary]]
- 关键问题 → [[agent-sessions-q2-questions-summary]]
