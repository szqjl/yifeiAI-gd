```markdown
---
type: entity-engine
title: "V7 引擎（神经网络策略）"
sources:
  - docs/guandan-brain/ITERATIONS.md
tags:
  - engine
  - v7
  - nn
  - bc
status: current
related_gua:
  - GUA-037
  - GUA-038
  - GUA-039b
  - GUA-041
  - GUA-044
  - GUA-045
  - GUA-047
  - GUA-048
  - GUA-049
  - GUA-050
  - GUA-051
  - GUA-052
  - GUA-053
  - GUA-059
  - GUA-060
  - GUA-061
  - GUA-062
  - GUA-063
  - GUA-064
  - GUA-065
  - GUA-066
  - GUA-068
  - GUA-069
  - GUA-070
  - GUA-071
  - GUA-072
  - GUA-073
date: 2026-07-15
---

# V7 引擎（神经网络策略）

## 引擎定位

V7 是项目当前主迭代方向的引擎，从 [[engine-m3]] 的规则引擎范式迁移到 **神经网络策略头 + 规则记牌/战略框架** 的混合架构。

## 关键模块

| 模块 | 职责 |
|------|------|
| `ultimate_win_rate_engine_v7.py` | 主引擎入口 |
| `v7_guards.py` | Guard 体系（R07~R12） |
| `grouping_engine.py` (v2) | 组牌引擎 |
| `memory_tracker.py` | 出牌记忆追踪 |
| `bc_dataset.py` / `bc_trainer.py` | BC 数据集与训练器 |
| `train_bc_v7.py` | BC 训练入口 |
| `yf1_v7.py` / `yf2_v7.py` | 两位选手实现 |
| `v7_game_recorder.py` | 对局记录 |

## 迭代历史

- **基础设施**：GUA-041~049（v7-infra）
- **特征工程**：GUA-037/038（v7-features）
- **策略层**：GUA-045~053（v7-strategy）
- **BC 训练**：GUA-059~061（v7-bc-training）
- **组牌 v2**：GUA-062（v7-grouping-v2）
- **桥接与 guard**：GUA-063/065~073

## 当前状态

| 指标 | 数值 |
|------|------|
| vs Lalala 累计队胜 | 1/69（1.4%） |
| 单次批跑副胜率波动 | 5.6% ~ 25.5% |
| BC v3 val_acc | 80.88% |
| BC v3 实战 | 0% |
| 2048 维动作空间利用率 | 0.01（argmax collapse） |

## 核心瓶颈

1. **BC argmax collapse**：见 [[bc-argmax-collapse]]，已判定教师强制路线死亡
2. **Guard 叠加过严**：GUA-070 副胜率 17.7% → 综合批跑 3.7%
3. **P0 堆积**：GUA-064/068/072 等多条 P0 并行

## 下一步方向

- 走 GUA-039b 自对弈路线
- 或引入 RL 微调
- 见 [[synthesis-v7-current-state]]

## 关联

- [[bc-argmax-collapse]]
- [[guard-heuristic-pipeline]]
- [[three-engine-training-pipeline]]
- [[engine-m3]]
- [[engine-v8]]
- [[synthesis-v7-current-state]]
```

---
