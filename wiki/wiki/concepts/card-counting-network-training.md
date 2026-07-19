---
type: concept
title: "CardCountingNetwork 训练方案"
sources:
  - docs/guandan-brain/CardCountingNetwork-训练方案.md
  - docs/guandan-brain/掼蛋AI自我进化-随机应变套路.md
  - docs/guandan-brain/人类掼蛋决策流程完整分析.md
  - docs/guandan-brain/组牌-NN衔接设计-软引导vs硬约束.md
  - docs/guandan-brain/掼蛋AI技术路径重校-V系列方法论反思.md
tags:
  - concept
  - nn
  - card-counting
  - belief
  - training
  - phase-0
  - phase-1
  - phase-2
  - phase-3
  - gua-057
status: current
related_gua:
  - GUA-057
  - GUA-072
  - GUA-079
  - GUA-091
date: 2026-07-19
---

# CardCountingNetwork 训练方案

> 来源：[[CardCountingNetwork-训练方案-summary]]（v3 修订版）

## §0 一句话定位

V7 NN 引擎的**第一个落地模块**：用监督学习训练一个 108 槽位 × 3 状态的记牌网络，为 [[module-memory-tracker|确定性 MemoryTracker]] 提供概率升级。

## §1 为什么先训这个

1. **规则补丁螺旋已逼近天花板**（见 [[gua-079]] 三层根因）
2. **端到端 BC 失败**（argmax collapse，见 [[concept-bc-argmax-collapse]]）
3. **记牌任务有精确 ground truth**（牌确实出过/没出过）→ 比 BC 端到端更可监督
4. **下游所有决策都需要记牌** → 投资回报率最高

## §2 任务定义

- **输入**：完整出牌序列（含己方 + 三方历史）
- **输出**：108 槽位 × 3 状态概率分布
  - 槽位：4 种花色 × 每种花色 13 张 + 2 王 = 54 牌 × 2（我方/对方手牌）= **108 槽**
  - 状态：`PLAYED` / `PARTNER_HAND` / `OPPONENT_HAND`

## §3 数据来源与 Ground Truth

- **数据池**：`game_records_v8/`（V8 牌谱 184 副公开）
- **Ground Truth 来源**：每步的 `all_players_hands` 字段（精确到张）
- **反事实对构造**：每步用 `history_before` 预测，对照 `history_after` 真实牌型

## §4 模型架构

### 渐进式

| Phase | 模型 | 参数量 | 时长 |
|-------|------|--------|------|
| Phase 1 | LSTM baseline | ~50K | 1-2 周 |
| Phase 2 | Transformer | ~319K | 2-3 周 |
| Phase 3 | 集成到 V7 管线 | — | 2 周 |

### 4 个 Head

```python
class CardCountingNetwork(nn.Module):
    def __init__(self):
        self.backbone = LSTM(input_dim=108, hidden_dim=128, num_layers=2)
        self.counter_opportunity_head = nn.Linear(128, 108)  # 出牌机会计数
        self.inaction_information_head = nn.Linear(128, 108)  # PASS 信息保留
        self.shape_posterior_head = nn.Linear(128, 108 * 3)   # 牌型后验
        self.belief_delta_head = nn.Linear(128, 108)         # 信念增量
```

## §7 降级路径

- Phase 1 失败 → 退回 MemoryTracker 增强（不动 NN 路线）
- Phase 2 失败 → 暂用 Phase 1 LSTM 结果
- Phase 3 失败 → **NN 路线整体暂时搁置**，回到规则补丁
- **赌注边界**：Phase 1-3 失败 ≠ NN 路线失败，仅证"7700 样本 + Transformer 监督学习失败"

## §8 Phase 0-3 路线图

### Phase 0（1 周）
- 1 周数据采集 + 形式化验证
- **不依赖 GUA-072 关单**
- 形式化：纯逻辑盘 + 对照实盘，差异 < 阈值

### Phase 1（1-2 周）
- LSTM baseline 训练
- 启动独立
- 验收：ECE/MCE/Brier + 大王小王/Bomb recall@0.5

### Phase 2（2-3 周）
- Transformer（~319K 参数）
- 数据规模目标：≥ 10K 副

### Phase 3（2 周）
- 集成到 V7 决策管线
- **与 GUA-079 集成互锁**

## §11 验收标准

| 指标 | 目标 |
|------|------|
| ECE | < 0.05 |
| MCE | < 0.10 |
| Brier | < 0.15 |
| 大王 recall@0.5 | > 0.90 |
| 小王 recall@0.5 | > 0.90 |
| Bomb recall@0.5 | > 0.85 |

## 关键约束（v3 修订要点）

### 3 分类的进贡转移牌问题
- 进贡转移牌会**错归 OPPONENT_HAND**
- Phase 1 用 `tribute_transfer_events` 驱动事件层解决
- **Phase 1 不做 4 分类**拆分 OPPONENT_A/B

### 硬事实优先于行为推断
- 行为推断只能改变概率，不能覆盖已知事实
- 例：观察到玩家 PASS 单王，他仍可能手里有大王 → 概率上升但不置 0

## 交叉引用

- [[gua-057]] — 落地路径
- [[gua-072]] — 前置条件（代码 100%）
- [[gua-079]] — Phase 3 互锁
- [[gua-091]] — 迁移出口
- [[concept-event-driven-belief-update]] — 反事实后验方法论
- [[concept-level-card-belief]] — 级牌归属
- [[module-memory-tracker]] — 现有确定性记牌
- [[synthesis-ccn-vs-memory-tracker]] — 范式对比
