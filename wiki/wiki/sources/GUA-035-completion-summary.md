---
type: source-summary
title: "GUA-035 完成定义摘要 · solo 接风对手剩张过滤（END-M02+）"
sources:
  - docs/guandan-brain/issues/GUA-035-completion.md
tags:
  - gua
  - m3
  - endgame
  - solo-sprint
  - end-m02
status: current
related_gua:
  - GUA-035
  - GUA-034
  - GUA-026
  - GUA-029
  - GUA-031
date: 2026-06-17
---

# GUA-035 完成定义摘要

## 概述

GUA-035 是 [[GUA-034]] 的子切片（END-M02+），专注于 **solo 续切场景下对手剩张数的过滤逻辑**。

## 核心规则

对手接风时本方主动跑牌，根据对手**剩张数**选择跳过的牌型：

| 对手剩张 | 跳过动作 | 说明 |
|----------|----------|------|
| 1 | 跳 Single | 对手即将打完，过滤掉单张接风选项 |
| 2 | 跳 Pair | 对手剩一对即可收官，跳过对子选项 |
| 5 | 优先跳 ThreeWithTwo | 三带二通常被对手硬吃，避免送牌 |
| 其他 | 正常出牌 | 走既有评分 |

## 关键约束

- **fallback 机制**：若被跳过的牌型是当前唯一合法出法，仍允许出
- **模式前提**：仅在 `solo_sprint` 模式下生效（[[solo-sprint]]）
- **三带二 fallback**：对手剩 5 张时若不出三带二会卡死，必须保留出牌通道

## 范围边界

**在范围：**
- END-M02+ 切片（对手剩张过滤 + 三带二 fallback）
- 对手剩 1/2/5 张的过滤规则

**不在范围（推迟到 V5+）：**
- 两手规划
- 可回收单张完整评分

## 依赖关系

- **父条目**：`[[GUA-034]]`（M3 末段博弈）
- **回归集合**：`test_m3_gua034`、`test_m3_gua026`、`test_m3_gua029`、`test_m3_gua031`
- **依赖 GUAs**：`GUA-026`、`GUA-029`、`GUA-031`

## 关单口径

> **pytest 构造态 + 回归通过即可关单**；不绑定具体 game_id

这与早期"末段要让道让赢"的类目标形成口径区分，需在 [[m3-endgame-guard]] 中明确标注。

## 关联页面

- [[gua-035]] - GUA-035 实体页
- [[gua-034]] - 父条目
- [[m3-endgame-guard]] - M3 末段博弈综合
- wiki-minimax/entities/engine-m3.md - M3 引擎
