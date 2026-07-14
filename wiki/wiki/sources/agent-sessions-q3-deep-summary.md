---
type: source-summary
title: "深度解读精要版 (Agent Session 03) - 摘要"
sources:
  - docs/analysis/agent-sessions/03-deep-analysis-summary.md
tags:
  - agent-session
  - deep-analysis
  - three-layer-strategy
status: current
related_gua:
  - GUA-022
  - GUA-039
date: 2026-06-18
---

# 深度解读精要版 (Agent Session 03) - 摘要

## 文档定位

Hermes Agent 对项目核心矛盾的精要版分析。聚焦"为什么 M3 70% 胜率但 M1 0%"和"V7 BC 高分但实战胜率 0%"两个反直觉现象。

## 核心论点

### 论点 1：三层战略是 M1/M3 差异的根因
- M1：纯 Lv1（单副出牌）→ 0% 胜率
- M3：Lv1 + 部分 Lv2（队员信号）→ 70%
- V7 目标：Lv1 + Lv2 + Lv3 完整覆盖

### 论点 2：BC 分数与实战胜率脱钩
- BC 84.3%：在测试集上模仿人类动作的准确率
- 实战 0%：BC 模仿的是"人的动作"不是"最优动作"
- 掼蛋的对抗性：模仿人会被对手读牌
- 解决：套路五（对手多样性 self-play）+ 套路四（稠密 reward）

### 论点 3：指标改善 ≠ 胜率提升
- PHASE2 五轮：PASS 率↓、近似 PASS 清零（指标改善）
- 局胜率：0%（无改善）
- 教训：Lv1 优化无法突破系统瓶颈
- 解决：必须攻 Lv2（套路七模块化的核心动机）

### 论点 4：自我进化的前提是"知道自己不知道什么"
- M1 不知道自己不知道 Lv2
- V7 模块化（套路七）显式建模 Lv2/Lv3
- 信念向量（套路一）= "知道自己不知道"

## 关键数据点

| 指标 | 数值 | 含义 |
|------|------|------|
| M1 vs lalala | 0% | 缺乏 Lv2/Lv3 |
| M3 vs lalala | 70%（待验证） | Lv2 部分补全 |
| V7 BC 分数 | 84.3% | 模仿准确率 |
| V7 实战 | 0% | BC 不解决对抗 |
| 168 伪动作 | v1006 平台上限 | 策略网络输出维度 |
| 124 + 64 + 8 + 24 维 | V7 特征 | 静态+动态+信念+记忆 |

## 行动优先级

1. **P0**：完成 V7 BC→RL 链路（GUA-039 启动自对弈）
2. **P0**：建立 Lv2 队伙联动模块（套路二 specialized）
3. **P1**：批跑体系标准化（50-100 局 vs lalala）
4. **P2**：M3 维持 70% 胜率到 V7 上线

## 交叉引用

- 三层战略 → [[three-layer-strategy]]
- V7 状态 → [[synthesis-v7-redesign]]
- M1 根因 → synthesis-m1-zero-winrate
- 批跑体系 → wiki-minimax/concepts/batch-evaluation.md
