---
type: source-summary
title: "主攻转助攻技巧摘要"
sources:
  - docs/knowledge/skills/03_assist_attack/02_role_conversion.md
tags:
  - skills
  - role-conversion
  - team-coordination
status: current
related_gua:
  - GUA-031
  - GUA-027
date: 2026-06-18
---

# 主攻转助攻技巧摘要

> 来源：docs/knowledge/skills/03_assist_attack/02_role_conversion.md

## 核心定义

**主攻转助攻 (Role Conversion)**：掼蛋中主攻和助攻角色可以动态转换，牌力/牌型/队友状态变化时需要灵活调整。

## 角色牌力分级

| 牌力 | 评分 | 角色定位 |
|------|------|----------|
| 强 | 8+ | 主攻 |
| 中 | 5-7 | 弹性 |
| 弱 | 2-4 | 助攻 |
| 极弱 | <1 | 交牌 |

## 转换触发因子

- 牌力评分变化
- 队友牌力增强
- 对手情况变化
- 残局剩牌
- 出牌权转换

## 转换策略三阶段

### 1. 组牌阶段
- 保留炸弹
- 保留多种牌型（三连对 + 三带二）

### 2. 出牌阶段
- PASS 让队友
- 及时送牌
- 阻击对手

### 3. 进贡阶段
- 双进贡时还小贡
- 让队友获好牌

## 引擎关联

- **M3**：缺乏 team_role 状态机，已 deferred
- **V5+ / V7**：需要 role_conversion 状态机 + 观察层
- 关联 `PRINCIPLES_MAPPING.md §九`
- 关联 `team_role` 模块（M1 已有）

## 关联页面

- wiki/concepts/role-conversion.md — 完整概念页
- [[gua-031]] — 传牌技巧实施跟踪
- [[gua-027]] — 座位公式（观察层）

---
