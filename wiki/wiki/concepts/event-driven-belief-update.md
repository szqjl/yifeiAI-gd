---
type: concept
title: "事件驱动反事实后验更新"
sources:
  - docs/guandan-brain/CardCountingNetwork-训练方案.md
  - docs/guandan-brain/人类掼蛋决策流程完整分析.md
tags:
  - concept
  - belief
  - counterfactual
  - event-driven
  - philology
status: current
related_gua:
  - GUA-057
date: 2026-07-19
---

# 事件驱动反事实后验更新

> 配套 [[concept-card-counting-network-training]] 使用

## 定义

记牌网络的**训练范式**：把"信念变化"建模为**事件驱动**的反事实后验更新。

$$P(\text{shape} \mid H_{\text{before}}) \xrightarrow{\text{event}} P(\text{shape} \mid H_{\text{after}})$$

每次出牌、PASS、进贡、还贡都是一个"事件"，触发信念 delta。

## §2.5.1 小王未被大王压制

**场景**：玩家 A 出小王，玩家 B 不压（PASS）

**信念变化**：
- $P(\text{大王 in B}) \uparrow$（B 可能有大王）
- $P(\text{大王 in C/D}) \downarrow$（B 没出大王的概率上升）

**反事实训练任务**：让模型从 PASS 事件学到"对方保留大牌"。

## §2.5.2 小牌型被压后不反压

**场景**：玩家 A 出小对，玩家 B 压大对，玩家 C/D 都不反压

**信念变化**：
- $P(\text{C 有炸弹}) \uparrow$
- $P(\text{D 有炸弹}) \uparrow$

## §2.5.3 事件记录最小字段

```python
@dataclass
class BeliefEvent:
    event_id: str
    timestamp: int
    actor: int            # 谁出的/过的
    action_type: str      # PLAY/PASS/TRIBUTE/RETURN
    card_signature: str   # 出牌签名（如 "PAIR_55"）
    belief_before: Tensor # 事件前 108×3 概率
    belief_after: Tensor  # 事件后 108×3 概率
    ground_truth: Tensor  # 真实 108×3 标签（仅训练时可用）
```

## §2.5.4 牌型信念与后验变化

| 事件 | PLAYED ↑ | PARTNER ↑ | OPPONENT ↑ |
|------|----------|-----------|------------|
| 玩家出牌 | 该张牌 ↑ | — | — |
| 玩家 PASS 单张 | — | — | 该张牌可能在他手 ↑ |
| 玩家进贡 | 收贡方可能持某牌 ↑ | — | 进贡方出某牌 |
| 还贡 | 还贡方可能持某牌 ↑ | — | — |

## §2.5.5 反事实训练任务

**任务定义**：给定 $H_{\text{before}}$，预测事件后的 $P(\text{shape} \mid H_{\text{after}})$，对照真实 $H_{\text{after}}$ 计算 loss。

```python
def counterfactual_loss(model, history_before, event, history_after):
    pred = model(history_before, event)  # (108, 3)
    target = compute_ground_truth(history_after)  # (108, 3)
    return F.cross_entropy(pred, target.argmax(dim=-1))
```

## §2.5.6 决策层使用边界

- **硬事实优先**：已知打出的牌 = PLAYED 概率 1.0，不被行为推断覆盖
- **概率校准**：未观测牌型 = 概率分布，可被决策层消费
- **置信度阈值**：recall@0.5 不达标的牌型不进入决策（保留为 MemoryTracker 兜底）

## 交叉引用

- [[concept-card-counting-network-training]] — 主方案
- [[concept-level-card-belief]] — 级牌归属
- [[gua-057]] — 落地路径
