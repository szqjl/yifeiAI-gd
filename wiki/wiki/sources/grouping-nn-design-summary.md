---
type: source-summary
title: "组牌→NN 衔接设计摘要"
sources:
  - docs/guandan-brain/组牌-NN衔接设计-软引导vs硬约束.md
tags:
  - v7
  - grouping
  - nn-integration
  - design-decision
status: current
related_gua:
  - GUA-062
  - GUA-063
date: 2026-06-20
---

# 组牌-NN衔接设计-软引导vs硬约束.md 摘要

V7 引擎 **组牌→出牌** 衔接阶段的架构设计文档，记录 **决议 1-10**。

## 核心问题

组牌引擎 v2（GUA-062）在单元测试中表现优秀（**27/27 通过**），但批跑 **0/9 队胜**——典型的 **"单元测试 vs 实战"鸿沟**。

## 诊断（GUA-063）

组牌→出牌存在 **三衔接缺口**：

1. **NN 零方案意识**：网络不知道当前有哪些组牌方案可选
2. **24 维特征密度低**：不足以让 NN 学习组牌选择
3. **中局无重评估**：组牌方案生成后不随牌局变化重新评估

## 6 组牌策略枚举

| 策略 ID | 策略名 | 说明 |
|---------|--------|------|
| `BOMB_FIRST` | 炸弹优先 | 优先出炸弹 |
| `NO_STRAIGHTS` | 无顺子 | 避免顺子 |
| `SF_FIRST` | 同花优先 | 优先出同花 |
| `BOMB_STRAIGHT_FLUSH_FIRST` | 同花顺炸弹优先 | 复合优先级 |

加上 2 个变体，共 **6 方案**。

## 4-5 维加权评分

每方案按 5 维度评分：
- `_score_power` — 牌力
- `_score_flexibility` — 灵活性
- `_score_recovery_static` — 静态恢复力
- `_score_plan_v2` — 方案综合分
- `_group_consistency_filter` — 组一致性过滤（role-driven）

## 牌力计分体系

- **A→2 包接**：A 下放当 1 处理
- **三连对**：连续三对（如 5-5/6-6/7-7）
- **钢板**：连续三张（如 5/6/7）
- **同花顺**：最高优先级

## 决议 1-10 摘要

| 决议 | 主题 | 状态 |
|------|------|------|
| 决议 1-5 | 组牌引擎内部设计 | ✅ closed |
| **决议 6-10** | NN 衔接设计（软引导 vs 硬约束） | ⚠️ 实施时触发 bug |
| 决议 6 | 软引导（特征叠加） | 触发 98.4% PASS bug |
| 决议 7-10 | 硬约束 / 重评估机制 | bug 修复后实施 |

**关键教训**：软引导（让 NN 自己学）vs 硬约束（直接喂规则）需谨慎——软引导在 BC 路线下不可行（argmax collapse），必须用硬约束。

## 衔接方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **软引导**（特征叠加） | NN 有学习空间 | 依赖 argmax，已死 |
| **硬约束**（规则驱动） | 可控、可解释 | 失去 NN 学习意义 |
| **混合**（启发式 + NN 兜底） | 兼顾两者 | 复杂度高 |

→ 团队最终选择 GUA-071 heuristic 路线：纯 Guard 驱动决策。

## 交叉引用

- [[grouping-engine-v2]] — 组牌引擎 v2 完整设计
- wiki/concepts/bc-argmax-collapse.md — BC 路线死亡
- wiki/concepts/three-layer-pipeline.md — Guard-Heuristic-validate 三层架构
- wiki/concepts/heuristic-pivot.md — GUA-071 战略转向
