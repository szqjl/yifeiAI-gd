---
type: source-summary
title: "GUA-045 completion · V7 决策根因 P0 Guard 壳 + 改进路线"
sources:
  - docs/guandan-brain/issues/GUA-045-completion.md
tags:
  - source-summary
  - gua-045
  - v7
  - phase-0
  - p0
status: current
related_gua:
  - GUA-045
  - GUA-037a
  - GUA-037b
  - GUA-038
  - GUA-039a
  - GUA-039b
  - V5+-04
date: 2026-06-17
---

# GUA-045 completion · V7 决策根因 P0 Guard 壳 + 改进路线

## 摘要

GUA-045 是 V7 引擎 Phase 0 的当前 P0 条目，定位 V7 决策不稳的三层根因并提出 P0 Guard 壳约束。本条目是 V7 由 M3 决策引擎向 NN 引擎迁移的关键奠基。

## 复盘来源

- game_id: 20260606121245769675
- 根因诊断：A Guard 壳 / B 特征模型 / C 组牌

## 三层根因诊断

| 层 | 描述 | 关联 GUA |
|----|------|----------|
| A · Guard 壳 | 零条 P0 Guard；当前 decide() 直接 argmax 或首个非 PASS 回退 | GUA-045 本体 |
| B · 特征模型 | _extract_features 无牌面编码；训练目标为 index 匹配率 | GUA-037a |
| C · 组牌 | 无 enumerate_groupings / 结构评分 | V5+-04 |

## Guard 规则（V7-R01~R06）

按缺陷分类 → 原则 → Guard 落点映射；详见 [[gua-045]]。

## 升格约束

**禁止 import src.m.m3.*** — V7-native 实现，不得借调 M3 决策 API；但允许 GUA-038 BC teacher 只读 M3 落盘的 game_records（数据流单向、不可调用）。

## 改进路线（Phase 0-3）

- **Phase 0** — GUA-045（~1 迭代）
- **Phase 1** — GUA-037a → 037b（~1.5-2 迭代）
- **Phase 2** — GUA-038 M3 BC 蒸馏
- **Phase 3** — GUA-039a/b 自对弈 + PPO

## 关单条件

pytest 构造态覆盖 ≥ 8 case；**单局 replay 逐步一致不作为关单标准**（同发牌复现概率 ≈ 0）。

## KPI 引用

V7-007（队胜率 >50%）归属 GUA-039b；本阶段不可用。

## 入册日期

2026-06-06
