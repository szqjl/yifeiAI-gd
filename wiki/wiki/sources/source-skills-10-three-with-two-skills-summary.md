---
type: source-summary
title: "三带二技巧 (04_common_skills/10)"
sources:
  - docs/knowledge/skills/04_common_skills/10_three_with_two_skills.md
tags:
  - skills
  - three-with-two
  - main-tactic
  - level:核心
status: current
related_gua:
  - GUA-026
  - GUA-030
  - GUA-031
date: 2026-06-18
---

# 三带二技巧 (04_common_skills/10)

## 文档定位

`docs/knowledge/skills/04_common_skills/10_three_with_two_skills.md` (8062 chars) — 三带二（ThreeWithTwo）运用技巧
原则编号：**§二十 三带二** (PRINCIPLES_MAPPING)

> 🌟 **GUA-026 主战术真源文档** — `_pick_three_with_two` 落地确认

## 核心策略

### 有打有收
- 三带二作为中等牌型，进可攻退可守
- 打出时考虑是否能收回牌权

### 相生相克反打
- 三带二克单牌/对子
- 被钢板/炸弹克制
- 对手打三带二时用更大三带二反打

### 残局骗炸口诀

| 口诀 | 含义 |
|------|------|
| **炸五不炸四** | 5 张三带二可炸，4 张不炸（性价比） |
| **六必治** | 6 张三带二是必治牌（最高优先级） |
| **炸七不炸八** | 7 张可炸，8 张保留（控制） |

### 谁打谁收
- 自己组的三带二自己收尾
- 避免给对手牌权

### 进贡首打夯严防
- 进贡后首打若出三带二属"打夯"
- 队友/对手需严防

## 引擎实现

| 引擎 | 模块 | 状态 |
|------|------|------|
| M3 | `_pick_three_with_two` | ✅ **已落地**（GUA-026 主战术） |
| M3 | `_ThreeWithTwo` 检测 | ✅ 已实现 |
| M3 | 残局骗炸决策 | ✅ 5/10 法则已覆盖 |

## 牌型概率

- 三张出现概率：**8.22%**（一手 9.8 张基准）
- 三带二是三张的扩展形式，占三张中的高频子型

## 引擎映射完整性确认

§二十 三带二 是 6 篇 skills 文档中**唯一明确落地主战术**的文档：
- `_pick_three_with_two` 已被 M3 引擎实现
- 残局骗炸（5/10 法则）覆盖完整
- 与 GUA-031 送牌矩阵协同工作

## 交叉引用

- [[gua-026]]：主战术真源
- [[gua-030]]：原则→引擎映射
- [[gua-031]]：送夯/不接队友
- [[gua-032]]：5/10 法则归属
- concept-tempo-and-feed：相生相克/谁打谁收
- [[concept-card-type-probability]]：牌型概率分布
