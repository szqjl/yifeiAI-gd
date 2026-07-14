---
type: concept
title: "主攻转助攻 (Role Conversion)"
sources:
  - docs/knowledge/skills/03_assist_attack/02_role_conversion.md
tags:
  - role-conversion
  - team-coordination
  - state-machine
status: current
related_gua:
  - GUA-031
  - GUA-027
date: 2026-06-18
---

# 主攻转助攻 (Role Conversion)

## 定义

掼蛋中主攻和助攻角色可以**动态转换**，牌力/牌型/队友状态变化时需要灵活调整。这是一种**角色状态机**而非固定标签。

## 牌力分级

| 牌力 | 评分 | 角色 |
|------|------|------|
| 强 | 8+ | 主攻 |
| 中 | 5-7 | 弹性 |
| 弱 | 2-4 | 助攻 |
| 极弱 | <1 | 交牌 |

## 转换因子

- **牌力变化**：手牌打完几张后评分变化
- **队友增强**：队友接牌后牌力上升
- **对手变化**：对手暴露弱点或转强
- **残局**：剩牌阶段角色自然切换
- **出牌权**：轮到谁出影响角色定位

## 转换策略

### 组牌阶段
保留炸弹 + 保留多种牌型（三连对 + 三带二）

### 出牌阶段
- PASS 让队友
- 及时送牌
- 阻击对手

### 进贡阶段
- 双进贡时还小贡
- 让队友获好牌

## 与引擎的映射

| 引擎 | 实施情况 |
|------|----------|
| M1 | 已有 `stage_router.team_role` 模块 |
| M3 | **未实施**，deferred 到 V5+ |
| V5+ / V7 | 需要 `role_conversion` 状态机 + 观察层 |

## 关联

- [[gua-031]] — 传牌技巧实施跟踪
- [[gua-027]] — 座位公式（观察层）
- wiki/concepts/team-coordination.md — 团队协作综合
- wiki/sources/skills-03-role-conversion-summary.md — 原始文档摘要

---
