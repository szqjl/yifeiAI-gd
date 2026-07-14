---
type: concept
title: "残局管线 (EndgamePipeline)"
sources:
  - docs/knowledge/skills/07_opening/end position.md
tags:
  - endgame
  - preprocessor
  - q0-q3
status: current
related_gua:
  - GUA-075
  - GUA-078
date: 2026-07-03
---

# 残局管线 (EndgamePipeline)

## 概念

EndgamePreprocessor 是 V7 引擎在残局阶段的预处理模块，位于 `src/v/nn/endgame/`，对应 GUA-078。

## 触发条件

| 规则 | 阈值 | 说明 |
|------|------|------|
| `BAOSHU_RULE` | 对手 ≤ 10 张 | 进入报数模式 |
| `endgame_rule` | 对手 ≤ 4 张 | 进入终局模式 |

## 四阶段 Q0~Q3

### Q0 — 是否进入残局？

- 检查对手手牌数 ≤ 10？
- 是 → 进入 Q1；否 → 跳过残局管线

### Q1 — 战术选择

套用 [[gua-075]] 推荐引擎（四场景）：
- **领出**：主动控场
- **跟上家**：压牌
- **卡下家**：阻断
- **让对家**：助攻

### Q2 — 牌型筛选

- 应用 banned types 硬排除（方案 A：decide() 中一刀切）
- 输出候选牌型列表

### Q3 — 执行出牌

- **残局助攻管线**：队友 pos+2 投喂
- **冲刺/头游判定**：`sprint` + `has_two_clean_hands`
- 输出最终出牌动作

## 已知矛盾

- 模块激活率 66.0% 但副胜仍 0
- 离线覆盖 ≠ 实战收益

## 关联

- [[end-position-design-summary]] — 残局预处理设计真源
- [[gua-075]] — 推荐引擎
- [[gua-078]] — 残局预处理器 GUA
- [[v7-current-state]] — V7 综合状态
