---
type: concept
title: "级牌归属信念体系"
sources:
  - docs/guandan-brain/CardCountingNetwork-训练方案.md
  - docs/guandan-brain/人类掼蛋决策流程完整分析.md
tags:
  - concept
  - level-card
  - belief
  - curRank
  - philology
status: current
related_gua:
  - GUA-057
date: 2026-07-19
---

# 级牌归属信念体系

> 配套 [[concept-card-counting-network-training]] 使用

## 级牌状态定义

掼蛋中"级牌"（红心级牌）是**当前 `curRank`** 的特殊牌，其归属信念独立于普通牌：

| 状态 | 含义 |
|------|------|
| `LV_PLAYED` | 该级牌已打出 |
| `LV_PARTNER` | 在队友手 |
| `LV_OPPONENT` | 在对手手（敌我不分） |
| `LV_TRIBUTE_OUT` | 进贡出去了 |
| `LV_RETURN_IN` | 还贡回来了 |

## 级牌归属推断信号

1. **进贡事件**：进贡方送出某级牌 → 该牌 `LV_TRIBUTE_OUT`
2. **还贡事件**：还贡方收回某级牌 → 该牌 `LV_RETURN_IN`
3. **出牌事件**：某玩家打出级牌 → `LV_PLAYED`
4. **PASS 行为推断**：玩家连续 PASS → 该级牌可能在他手

## 决策消费规则

### 何时消费 `LV_PARTNER`
- 队友报单 / 报双 / 冲刺阶段 → 优先找级牌给队友让道
- 队友级牌已知 → 可配合其过桥

### 何时消费 `LV_OPPONENT`
- 残局冲刺阶段 → 评估对手级牌威胁
- 双下防守 → 计算级牌是否在对手手中决定是否搏炸

### 何时消费 `LV_TRIBUTE_OUT`
- 进贡回收后（下一局开始）该状态清零
- 但当局内**仍记录**用于复盘

## §3.6 级牌 Ground Truth

- **来源**：与普通牌同源，从 `all_players_hands` 提取
- **特殊处理**：`LV_TRIBUTE_OUT` 在进贡事件后必须从手牌移除
- **反事实任务**：用 `history_before_including_tribute_event` 预测事件后的级牌归属

## 与普通牌信念的区别

| 维度 | 普通牌 | 级牌 |
|------|--------|------|
| 进贡影响 | 无 | 强制转移 |
| 还贡影响 | 无 | 强制回移 |
| 决策权重 | 中 | 高（过桥/让道关键） |
| Phase 1 拆分 | 3 分类 | **独立 head** |

## 交叉引用

- [[concept-card-counting-network-training]] — 主方案
- [[concept-event-driven-belief-update]] — 反事实更新
- [[gua-057]] — 落地路径
