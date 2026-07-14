---
type: concept
title: "组牌引擎 v2"
sources:
  - docs/guandan-brain/组牌-NN衔接设计-软引导vs硬约束.md
tags:
  - v7
  - grouping
  - GUA-062
  - GUA-063
  - card-engine
status: current
related_gua:
  - GUA-062
  - GUA-063
date: 2026-06-20
---

# 组牌引擎 v2

V7 引擎的 **手牌→组牌方案** 转换模块，GUA-062 立项。

## 单元测试表现

- **测试用例**：27 个
- **通过率**：**27/27 = 100%**
- **覆盖维度**：所有基本牌型 + 边界场景

## 实战表现（批跑）

- **批跑局数**：9 局
- **队胜率**：**0/9 = 0%**
- **典型问题**：选出的方案在单元测试中正确，但实战中队友/对手应对模式不匹配

→ 典型的 **"单元测试 vs 实战"鸿沟**。

## 核心设计

### 1. 6 策略枚举

| 策略 ID | 策略名 |
|---------|--------|
| `BOMB_FIRST` | 炸弹优先 |
| `NO_STRAIGHTS` | 无顺子 |
| `SF_FIRST` | 同花优先 |
| `BOMB_STRAIGHT_FLUSH_FIRST` | 同花顺炸弹优先 |
| 变体 1 | 组合策略 A |
| 变体 2 | 组合策略 B |

### 2. 5 维加权评分

```
_score_plan_v2 = w1 * _score_power 
               + w2 * _score_flexibility 
               + w3 * _score_recovery_static 
               + w4 * _score_plan_v2 
               + w5 * _group_consistency_filter
```

| 维度 | 函数 | 含义 |
|------|------|------|
| 牌力 | `_score_power` | 当前牌型的压制力 |
| 灵活性 | `_score_flexibility` | 出牌后剩余手牌的灵活性 |
| 静态恢复力 | `_score_recovery_static` | 未来轮次的恢复潜力 |
| 方案综合分 | `_score_plan_v2` | 综合指标 |
| 组一致性 | `_group_consistency_filter` | role-driven 过滤 |

### 3. 牌力计分

- **A→2 包接**：A 下放当 1 处理
- **三连对**：连续三对（如 5-5/6-6/7-7）
- **钢板**：连续三张（如 5/6/7）
- **同花顺**：最高优先级

### 4. 角色判定（role-driven）

- `_group_consistency_filter` 根据角色（领出/跟牌/压制）过滤不合理方案
- 配合 R07/R08/R09 队友保护

### 5. 牌级 mask

- `to_card_mask`：每张牌的可用性 mask
- `is_core`：核心牌保护（不被错误拆解）

## GUA-063 三衔接缺口

组牌→NN 出决策存在 **三缺口**：

1. **NN 零方案意识**：网络不知道当前可选方案
2. **24 维特征密度低**：特征不足以让 NN 学习组牌选择
3. **中局无重评估**：方案生成后不随牌局变化重新评估

→ 详见 wiki/concepts/bc-argmax-collapse.md 与 wiki/concepts/heuristic-pivot.md。

## 关键模块

| 模块 | 职责 |
|------|------|
| `grouping_engine.py` | 组牌引擎主类 |
| `check_grouping_engine.py` | 27 个单元测试 |
| `analyze_v7_rounds.py` | 批跑结果分析 |
| `_score_power` 等 | 5 维评分函数 |

## 教训

- 单元测试通过 ≠ 实战有效
- 必须配套 **批跑 KPI** 验证（见 wiki-minimax/concepts/batch-evaluation.md）
- 24 维特征对 NN 学习组牌远远不够
- role-driven 过滤是关键，但需更多实战调参

## 交叉引用

- [[GUA-062]] — 组牌引擎 v2 缺陷条目
- [[GUA-063]] — 三衔接缺口诊断
- wiki/entities/engine-v7.md — V7 引擎整体设计
- wiki/concepts/three-layer-pipeline.md — 组牌方案作为 Layer 2 输入
