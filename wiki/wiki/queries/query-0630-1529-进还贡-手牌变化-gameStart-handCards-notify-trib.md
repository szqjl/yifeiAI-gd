---
type: query-answer
title: "进还贡 手牌变化 gameStart handCards notify tribute back"
date: 2026-06-30
sources:
---

# 进还贡 手牌变化 gameStart handCards notify tribute back

# 进/还贡手牌变化梳理

## 核心链条

```
gameStart → handCards (27 张)
   ↓
[进贡阶段]  进贡方出最大牌 → 手牌 -1
[还贡阶段]  受贡方还 ≤10 单张 → 手牌 -1
   ↓
play 阶段 → 初始为 25 张（正常情况下）
```

## 三个关键 GUA

### GUA-067（open P1）— 训练数据 `initial_hand` 偏移
- **根因**：`initial_hand` = gameStart.handCards，但 `bc_dataset.py` 策略2 `current_hand = initial_hand - played_cards` **只能减不能加**
- **表现**：已还走的牌多算、收到的贡牌少算
- **修复**：实施 `adjust_initial_hand_for_tribute_back()`，在 4 条路径实时调整：

| 事件 | 动作 |
|------|------|
| 收贡 | add 收到的牌 |
| 收还 | add 还回的牌 |
| 进贡 | remove 贡出的牌 |
| 还牌 | remove 还回的牌 |

- **关闭条件**：批跑验证 `initial_hand` 张数 = 27（贡后）且不含已贡出牌 [1]

### GUA-086（closed P3）— tribute 阶段 `remove` 传参错
- 出贡牌后调 `remove` 方法传参错误，导致手牌状态未正确更新，进而触发 GUA-067 偶发漂移
- **修复**：引入 `extract_tribute_back_card` helper，修复 4 处调用点（`yf1_v7.py:373,397` + `yf2_v7.py:373,397`）[2]

### GUA-087（observation P2）— actions 流水漏 tribute 阶段出牌
- 流水仅记主牌阶段，tribute 阶段出牌**不进入 actions 列表**
- 决策：**documentation-only**，不动代码（在 `platform-data-interpretation.md` 增加说明）[3]

## 服务器消息层（Wiki 信息缺口 ⚠️）

Wiki 中**未详细记录**进/还贡消息的 JSON schema：
- 已知：消息方向 S→C（"进贡通知"）
- **未知**：`tributeCards`、`antiTribute` flag 等消息体字段
- 平台层 protocol 仍未文档化为正式 RFC（TENSION-5）
- 需查 `docs/guandan-brain/掼蛋AI算法对抗平台使用说明.md` 原文确认 [4]

## 策略分叉对比（T3 张力）

| 维度 | GUA-086 | GUA-087 |
|------|---------|---------|
| 处理方式 | 改代码 | 文档化 |
| 调用点 | remove 传参 | actions 记录 |
| 严重度 | P3-resolved | P2 observation |
| 状态 | ✅ closed | 📝 持续观察 |

同一 tribute 调用点出现两个 GUA，按"成本-收益"原则分了不同叉：传参错直接修（数据正确性），流水漏仅文档化（仅复盘可见性）。

## 引用

- [1] entities/gua-067.md
- [2] entities/gua-086.md
- [3] entities/gua-087.md
- [4] queries/query-0621-1953-还贡服务器消息-进贡-protocol-贡牌.md
