---
type: concept
title: "局面信念向量（8 维）"
sources:
  - docs/guandan-brain/handoff/2026-06-16-v7-dev.md
tags:
  - concept
  - v7
  - nn
  - feature
status: current
related_gua:
  - GUA-050
  - GUA-038
date: 2026-06-17
---

# 局面信念向量（8 维）

## 定义

**局面信念向量（Belief Vector）** 是 V7 引擎对当前局面态势的 8 维连续特征表示，位置 **188-195**（在 188 维 BC 模型末尾）。

## 8 维定义

| 维度 | 名称 | 含义 |
|------|------|------|
| 1 | `my_strength` | 我方整体牌力评估 |
| 2 | `partner_strength` | 队友牌力评估 |
| 3 | `opponent_pressure` | 对手压制强度 |
| 4 | `level_progress` | 升级进度 |
| 5 | `trump_ready` | 主牌/级牌就绪度 |
| 6 | `bomb_count` | 剩余炸弹估计 |
| 7 | `opponent_bomb_risk` | 对手炸弹风险 |
| 8 | `last_card_meaning` | 末家出牌语义 |

## 当前状态（2026-06-17）

- ✅ **代码已实施**：`static_features.py` 中 `BELIEF_DIM = 8`，`extract_state_belief()` 已加
- ✅ **拼接至 V7 引擎**：188-195 占位
- ⚠️ **特征利用率 38.3%**：BC 模型未重训，belief 信号尚未激活
- 🔜 **下次 GUA-038 重训时激活**

## 激活路径

```
GUA-050（已实施，188-195 占位）
    ↓
GUA-038（BC 模型重训，用 M3 胜利局 game_records）
    ↓
激活 196 维 BC 模型
```

## 关联 GUA

- [[gua-050]] — 实施项（2026-06-16 implemented）
- [[gua-038]] — 激活项（open, 下轮 priority #3）
- [[gua-037a]] — Static 特征 0-123（前置）
- gua-037b — Dynamic LSTM 特征 124-187（前置）

## 跨引用

- wiki/entities/engine-v7.md — V7 引擎
- [[gua-050]] — 实施 GUA
- wiki/synthesis/synthesis-v7-current-state.md — V7 现状综合
