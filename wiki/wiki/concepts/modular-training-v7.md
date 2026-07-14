---
type: concept
title: "V7 模块化分阶段训练（套路七）"
sources:
  - docs/guandan-brain/掼蛋AI自我进化-随机应变套路.md
  - docs/analysis/agent-sessions/03-deep-analysis-summary.md
tags:
  - v7
  - methodology
  - modular-training
  - bc
  - rl
status: current
related_gua:
  - GUA-037a
  - GUA-038
  - GUA-039
  - GUA-039a
date: 2026-06-18
---

# V7 模块化分阶段训练（套路七）

## 概念定义

V7 引擎当前核心方法论：将掼蛋 AI 拆分为 4 个 specialized 子网络，按"分阶段训练 → 联合微调"流程构建。源自套路七（模块化分阶段训练），吸收了套路二（多模块 specialized 评估）的思想。

## 四模块架构

```
┌─────────────────────────────────────────────┐
│           V7ModularEngine                   │
├─────────────────────────────────────────────┤
│  ① CardGroupingNetwork   拆牌/组牌          │
│  ② CardCountingNetwork   计数/剩余牌推断    │
│  ③ StrategyNetwork       战略选择（攻/守）  │
│  ④ ActionNetwork         动作选择（出哪张）  │
└─────────────────────────────────────────────┘
```

### 各模块职责

| 模块 | 输入 | 输出 | 训练方式 |
|------|------|------|----------|
| CardGrouping | 手牌 + curRank | 牌型分组 | 监督学习（人类拆牌数据） |
| CardCounting | 已出牌 + 自己手牌 | 剩余牌分布 | 监督学习（计数规则） |
| Strategy | 全局特征 + 信念 | 攻/守倾向 | BC → RL |
| Action | 战略倾向 + 合法动作 | 动作概率分布 | BC → RL（含 actIndex） |

## 特征空间

| 类别 | 维度 | 说明 |
|------|------|------|
| 静态特征 | 124 维 | 手牌/桌面/历史/curRank |
| 动态特征 | 64 维 | 实时局面变化 |
| 信念向量 | 8 维 | 对手手牌分布（套路一） |
| 记忆追踪 | 24 维 | 长程情境（套路三） |
| **合计** | **220 维** | 4-head 网络输入 |

## 4-Head 输出

```python
output = {
  "action_logits": 168,        # 168 伪动作（v1006 上限）
  "position_win_rate": 1,      # 当前位置胜率
  "action_value": 1,            # 当前动作价值
  "long_term_reward": 1,        # 长程奖励（套路四）
}
```

## 分阶段训练流程

### Phase 1：BC 热启动（GUA-038）
- 目标：每个模块用人类数据 BC 到 80%+ 准确率
- 现状：ActionNetwork BC 84.3%（最高）
- **教训**：BC 分数高 ≠ 实战胜率高（见 [[synthesis-v7-redesign]]）

### Phase 2：自对弈 Actor（GUA-039 / GUA-039a）
- 目标：用 4 模块联动 + 自对弈生成训练数据
- 关键：对手多样性（套路五）
- 状态：未启动

### Phase 3：稠密 Reward RL（套路四）
- 目标：用稠密 sub-reward 解决信用分配
- 方法：TD(λ) + 每步 sub-reward
- 状态：未启动

### Phase 4：联合微调
- 目标：4 模块端到端微调
- 状态：未启动

## 与历史失败的对比

| 失败案例 | 教训 | 模块化如何避免 |
|----------|------|----------------|
| V2-V6 端到端 NN | 难以调试，一个错全错 | 模块化可单模块回滚 |
| M1 0% 胜率 | 缺 Lv2/Lv3 | StrategyNetwork 显式建模 Lv2 |
| BC 84% 实战 0% | 模仿 ≠ 最优 | 必须经过自对弈 RL |

## 关键依赖

- [[guandan-platform-protocol]]：168 伪动作上限
- [[three-layer-strategy]]：Lv1/Lv2/Lv3 对应不同模块
- wiki-minimax/concepts/batch-evaluation.md：每个阶段需批跑验证

## 交叉引用

- V7 引擎状态 → wiki/entities/engine-v7.md
- V7 重做综合 → [[synthesis-v7-redesign]]
- 套路体系 → [[guandan-self-evolution-patterns-summary]]
