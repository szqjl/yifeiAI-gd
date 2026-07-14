---
type: source-summary
title: "钢板技巧 (04_common_skills/07)"
sources:
  - docs/knowledge/skills/04_common_skills/07_two_trips_skills.md
tags:
  - skills
  - two-trips
  - special-formation
  - level:进阶
status: current
related_gua:
  - GUA-030
  - GUA-031
date: 2026-06-18
---

# 钢板技巧 (04_common_skills/07)

## 文档定位

`docs/knowledge/skills/04_common_skills/07_two_trips_skills.md` (3335 chars) — 钢板（TwoTrips）运用技巧
原则编号：**§十七 钢板** (PRINCIPLES_MAPPING)

## 核心策略

### 小钢板三原则

| 原则 | 含义 |
|------|------|
| 小钢板**先出** | 手数紧张时优先清掉 |
| 小钢板**不出** | 队友可能持有更大钢板，让牌权 |
| 小钢板**后出** | 残局阶段作为收尾牌型 |

### 拆分传牌
- 钢板可拆为两个三张分别传队友
- 配合 GUA-031 送牌矩阵使用

### 引炸策略
- 故意出小钢板引诱对手炸
- 暴露对手炸点后反打

### 红配变钢板
- 利用红桃配（H+curRank）将普通三张+三张升级为钢板
- 适用于红配富余场景

## 引擎实现

| 引擎 | 模块 | 状态 |
|------|------|------|
| M3 | `_TwoTrips` (钢板检测) | ✅ 已实现 |
| M3 | `rankfour` (牌力评估) | ✅ 已实现 |
| M3 | `R6` (牌力分档) | ✅ 已实现 |
| V5+ | 牌力分时优化 | 🔄 进行中 |

## 牌型概率

- 钢板出现概率：**1.02%**（一手 9.8 张基准）
- 属于低频高价值牌型

## 交叉引用

- [[gua-030]]：原则→引擎映射
- [[gua-031]]：送牌/不接队友
- [[gua-032]]：算牌预判
- concept-special-card-formation：特殊牌型同构性
- [[concept-card-type-probability]]：牌型概率分布
- wiki-minimax/entities/engine-m3.md：M3 引擎模块清单
