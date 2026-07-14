---
type: source-summary
title: "规则摘要：06 完整对局流程（高价值）"
sources:
  - docs/knowledge/rules/01_basic_rules/06_game_flow.md
tags:
  - rules
  - game-flow
  - stage
  - high-value
status: current
related_gua:
  - GUA-033
date: 2026-06-18
---

# 规则摘要：06 完整对局流程（高价值）

## 来源

- 原始文件：`docs/knowledge/rules/01_basic_rules/06_game_flow.md`（2447 字符）
- 重要性：**批跑数据解析基础**（平台 stage 序列）

## 核心内容

### 平台 stage 序列

```
beginning
  └─ [tribute]?        ← 进贡
  └─ [anti-tribute]?   ← 抗贡
  └─ [back]?           ← 还贡
  └─ play              ← 出牌阶段
  └─ episodeOver       ← 一副结束
  └─ [下一副] OR gameOver
gameOver
  └─ gameResult        ← 一局结束（A 双上或超时）
```

### 进贡规则

- **触发条件**：双下（对家分别获得 3/4 名，即末游 + 三游）时
- **进贡对象**：末游 → 头游；三游 → 二游
- **进贡牌**：进贡方最大牌（逢人配可跳）
- **领出者**：受贡者领出本圈首圈

### 还贡规则

- **时机**：受贡者出牌前
- **还贡牌**：任意 ≤10 的牌（不得大于进贡牌）
- **限制**：得还回不同的牌型类别

### 抗贡规则

- **触发**：进贡方持有双王时
- **效果**：抗贡成功，本圈无进贡无还贡
- **领出者**：上游（头游）领出

### 首圈领出规则

- **第一副**：由服务器决定
- **第二副起**：由进贡给上游者领出
- **双下情况**：三游领出
- **抗贡情况**：上游（头游）领出

> ⚠️ **冲突说明**：实体赛有「下游领出」说法，**M3 引擎以平台 act 为准**

## 与其他页面的关系

- 上游：[[source-rules-05-card-distribution-summary]]
- 下游：[[source-rules-07-upgrade-rules-summary]]
- 相关概念：[[concept-first-lead-rules]]、concept-m2-game-detection、concept-round-vs-game-multi-level
- 关联 GUA：wiki-minimax/entities/gua-033.md（curRank/gameOver 字段）

## 关键平台字段

- `curRank`：本副级牌（全场共用）
- `selfRank` / `oppoRank`：队伍等级（跨副累积）
- `gameOver`：N **局**（非 N 副）
