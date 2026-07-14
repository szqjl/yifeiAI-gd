---
type: concept
title: "类人决策五阶段"
sources:
  - docs/guandan-brain/人类掼蛋决策流程完整分析.md
tags:
  - human-like-decision
  - v7-architecture
  - core-concept
status: current
related_gua: []
date: 2026-06-18
---

# 类人决策五阶段

## 概念定义

**类人决策五阶段**是新 V7 架构的核心设计原则:模拟人类玩家在掼蛋对局中的完整决策流程,将其拆分为 5 个可独立训练/优化的模块。

## 五阶段模型

```
[阶段0: 组牌] → [阶段1: 角色] → [阶段2: 试探] → [阶段3: 中期] → [阶段4: 残局]
   拆牌          定位         探测         调整         收官
```

### 阶段 0:组牌(Grouping)

- **人类行为**:拿到牌后,先在脑子里"摆牌",尝试不同拆法
- **AI 实现**:GroupingEngine 枚举 10-50 种合法方案
- **关键概念**:多方案组牌

### 阶段 1:角色定位(Role Assignment)

- **人类行为**:判断自己是主攻还是助攻,决定出牌风格
- **AI 实现**:角色定位模块(设计中,待命名)
- **关键概念**:牌权争夺

### 阶段 2:试探出牌(Probe)

- **人类行为**:用小牌探测对手反应,收集信息
- **AI 实现**:试探策略模块(设计中)
- **关键概念**:结构化记忆(已出牌信号)

### 阶段 3:中期调整(Dynamic Adjustment)

- **人类行为**:局势变化时(队友被压制、对手升级),调整策略
- **AI 实现**:MemoryTracker + DynamicAdjustment

### 阶段 4:残局决胜(Endgame)

- **人类行为**:精确计算剩余牌,寻找必胜路径
- **AI 实现**:HumanLikeDecisionEngine

## 设计原则

### 1. 模块化分阶段训练

参考 AlphaGo 原则,每个阶段可独立训练与验证,降低端到端训练的难度。

### 2. 物理可解释

每个阶段对应人类**可观察的行为**,便于:
- 调试与可解释性
- 失败归因(哪个阶段出问题)
- 知识蒸馏(从人类对局提取)

### 3. 与 M3 的关系

- M3 实现了**部分阶段**(尤其是组牌和角色)
- 新 V7 补齐**试探、中期、残局**的 NN 化

## 已知挑战

| 挑战 | 说明 |
|------|------|
| 阶段间耦合 | 一个阶段的输出是下一阶段的输入 |
| 长程依赖 | 阶段 0 的组牌影响阶段 4 的残局 |
| 训练数据 | 需要大量"带阶段标注"的人类对局 |

## 关联页面

- wiki/entities/engine-v7.md — V7 引擎,新架构的实施载体
- wiki-minimax/entities/engine-m3.md — M3 引擎,提供了阶段 0/1 的基线
- wiki/concepts/power-contention.md — 牌权争夺,阶段 1-2 的核心目标
- wiki/concepts/modular-staged-training.md — 模块化训练方法论
- wiki/concepts/structured-memory.md — 结构化记忆
