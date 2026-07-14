---
type: concept
title: "原则映射 P0/P1 分流"
sources:
  - docs/guandan-brain/iterations/m3-skills-mapping-gua030.md
related_gua:
  - GUA-030
tags:
  - principles
  - skills
  - p0-p1
date: 2026-06-18
---

# 原则映射 P0/P1 分流

## 概览

掼蛋 AI 原则集 → 实现引擎的分流总纲，源自 `PRINCIPLES_MAPPING.md` + skills §16–§22 评估。

## 原则集

| 类别 | 编号 | 含义 |
|------|------|------|
| **P-C** | 控牌类 | 控制点 / 牌权 |
| **P-J** | 接风类 | 队友上手配合 |
| **P-G** | 攻牌类 | 主动进攻 |
| **P-F** | 防守类 | 控守 / 拦张 |
| **P-H** | 残局类 | 残局处理 |
| **S-PR** | 优先级类 | 牌型优先级 |
| **S-ST** | 顺子类 | 顺子策略 |
| **S-BS** | 基础类 | 基础牌型处理 |

## 分流规则

- **P0**（必须实现）：落 `m3_decision_engine`
  - 实际仅 **P-H01 / P-H05** 两条
- **P1+**（优化迭代）：走 V5+ / 后续引擎
  - skills §16–§22 全部 P1+

## 关联

- [[GUA-030]]
- wiki-minimax/entities/engine-m3.md
- wiki/entities/engine-v7.md
