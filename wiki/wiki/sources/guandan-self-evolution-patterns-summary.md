---
type: source-summary
title: "掼蛋AI自我进化-随机应变套路 - 摘要"
sources:
  - docs/guandan-brain/掼蛋AI自我进化-随机应变套路.md
tags:
  - v7
  - strategy
  - methodology
  - patterns
status: current
related_gua:
  - GUA-009
  - GUA-010
  - GUA-013
  - GUA-014
  - GUA-015
  - GUA-016
  - GUA-017
  - GUA-022
  - GUA-037a
  - GUA-038
  - GUA-039
  - GUA-039a
date: 2026-06-18
---

# 掼蛋AI自我进化-随机应变套路 - 摘要

## 文档定位

掼蛋 AI 自我进化路径的方法论体系。V2-V7 纯神经网络路线全面失败后，对"如何让 AI 自我进化"的系统性反思，提出七个"随机应变"套路。

## 残酷结论

| 引擎 | 状态 |
|------|------|
| V2 | 失败 |
| V3 | 失败 |
| V4 | 失败（GUA-009 未启用） |
| V5 | 失败 |
| V6 | 失败（GUA-015 未闭环） |
| V7 | **当前主迭代**（模块化重做中） |
| 纯 RL 路线 | 在不完全信息博弈（掼蛋）下基本失败 |
| 成功案例参考 | WBridge5（桥牌规则）/ Pluribus（扑克 CFR）/ AlphaGo（围棋完美信息 MCTS+NN） |

**关键洞察**：掼蛋 = 桥牌的信息隐藏 + 扑克的对抗性 + 围棋的策略深度。单一方法不能照搬。

## 七个套路

### 套路一：局面信念建模
- 维护对对手手牌分布的信念向量
- V7 已实现 8 维信念向量

### 套路二：多模块 specialized 评估
- 不同子任务（拆牌/组牌/控制/Partner）由不同网络评估
- [[modular-training-v7]] 路线核心

### 套路三：Memory/长程情境记忆
- 24 维记忆追踪特征
- 应对掼蛋长程决策（打 1 副需 30+ 步）

### 套路四：稠密 Reward 信号
- 解决 RL 信用分配难题
- TD(λ) 信用分配 + 每步 sub-reward

### 套路五：对手多样性/破解 self-play
- 不能只跟自己打
- V7 自对弈 Actor（GUA-039a）需要对手池

### 套路六：模仿学习起步
- BC → RL 链路
- V7 BC 热启动（GUA-038）84.3% 分数但实战胜率 0%
- 教训：**BC 分数 ≠ 实战胜率**（[[synthesis-v7-redesign]] 重点展开）

### 套路七：模块化分阶段训练
- 卡牌分组网络 → 计数网络 → 策略网络 → 行动网络
- V7 当前核心路线（[[modular-training-v7]]）

## 三层战略框架（[[three-layer-strategy]]）

| 层级 | 范围 | 现有覆盖 |
|------|------|----------|
| Lv1 个别决策 | 单副出牌选择 | 较完整（M3 决策引擎） |
| Lv2 队伙联动 | 同伴配合、火力集中 | **缺失**（M3 主要 0% 胜率根因） |
| Lv3 全局对抗 | 一局内多副策略、抗贡、进贡 | 未实现 |

## 历史失败教训

### GUA-022（M1 队胜率 0%）
- M1 时代缺乏 Lv2/Lv3 思维，只有 Lv1 决策
- 见 synthesis-m1-zero-winrate

### PHASE2 五轮迭代（0% 胜率）
- Lv1 指标改善（PASS 率↓、近似 PASS 清零 - GUA-020/GUA-021 已闭）
- **指标改善 ≠ 胜率提升**（关键教训）

## 交叉引用

- V7 引擎现状 → wiki/entities/engine-v7.md
- V7 模块化重做 → [[synthesis-v7-redesign]]
- 三层战略 → [[three-layer-strategy]]
- M1 0% 根因 → synthesis-m1-zero-winrate
