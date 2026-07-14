---
type: source-summary
title: "掼蛋牌语摘要"
sources:
  - docs/knowledge/skills/04_common_skills/02_card_language.md
tags:
  - skills
  - card-language
  - observation
status: current
related_gua:
  - GUA-027
  - GUA-064
date: 2026-06-18
---

# 掼蛋牌语摘要

> 来源：docs/knowledge/skills/04_common_skills/02_card_language.md

## 核心原则

**鸟有鸟语，牌手出牌传递信息** —— 通过对手/队友的出牌读出牌力与意图。

## 座位公式

```python
上家 = (myPos - 1) % 4
下家 = (myPos + 1) % 4
队友 = (myPos + 2) % 4
```

> 注：座位公式已被 [[gua-027]] 覆盖，本文不重复创建。

## 首出信号

| 首出牌型 | 含义 |
|----------|------|
| 首出小单 | 牌力强信号 |
| 首出对子 | 情况不明，试探 |
| 首出高单 | 助攻定位 / 交牌权 |
| 首出小顺 | 有打有收 / 牌力强 |
| 首出木板/钢板 | 中性牌 |
| 首出三张 | 弱牌 |

## 牌型组合信号

- **三带二带对大小**：暗示是否希望队友传三带二
- **相邻炸弹大小顺序**：暗示是否还有炸弹
- **出 33399**：家里可能有 4-8 顺子
- **出 4 张同花色顺子**：无红心配，同花顺少

## 引擎关联

- **M3**：缺乏观察层架构
- **V5+ / V7**：需要 observation_layer + team_intent_recognition
- 关联 `PRINCIPLES_MAPPING.md §十二`

## 关联页面

- wiki/concepts/card-language.md — 完整牌语概念
- [[gua-064]] — 牌语/读牌系统（拟）
- [[gua-027]] — 座位公式（观察层）

---
