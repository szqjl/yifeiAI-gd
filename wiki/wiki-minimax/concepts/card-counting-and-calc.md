---
type: concept
title: "记牌算牌体系（MEM-Mxx / CALC-Mxx）"
sources:
  - docs/guandan-brain/issues/GUA-032-completion.md
  - docs/guandan-brain/PRINCIPLES_MAPPING.md
tags:
  - card-counting
  - calculation
  - m3-engine
  - principle
status: current
related_gua:
  - GUA-032
  - GUA-027
  - GUA-028
date: 2026-06-17
---

# 记牌算牌体系（MEM-Mxx / CALC-Mxx）

## 体系总览

M3 引擎的记牌算牌体系分为两大模块：

| 模块前缀 | 含义 | 子项 |
|----------|------|------|
| **MEM-Mxx** | 记牌（Memory） | MEM-M02 |
| **CALC-Mxx** | 算牌（Calculation） | CALC-M01 / CALC-M02 / CALC-M03 |

## 数据流

```
history.send
    ↓
_update_play_state
    ↓
_active（决策入口）
    ↓
remain_cards / remain_cards_classbynum（2468 计数法）
    ↓
MEM-M02：has_bomb, max_bomb_rank
    ↓
CALC-M01（排炸）/ CALC-M02（进贡）/ CALC-M03（关键张）
```

## 核心方法

### 2468 计数法
`remain_cards_classbynum` 与 `remain_cards` 一致性的派生源，是整个体系的根基。

### 记炸 / 排炸
- **MEM-M02**：扫 `history.send` 维护 `has_bomb`（是否出过炸）和 `max_bomb_rank`（最大炸弹级别）
- **CALC-M01**：基于 MEM-M02 产出，推理对方剩余炸弹上限

### 5/10 关键张降权（CALC-M03）
大顺/小顺在点五/点十外剩 0 时降权，避免顺子爆裂。

### 进贡无级牌（CALC-M02）
进贡无级牌对手 + `numofnext==1` 时，触发 `_active` 禁过小单。

## 关联 GUA

- [[gua-032]] — 记牌+算牌主条目
- [[gua-027]] / [[gua-028]] — 回归测试
