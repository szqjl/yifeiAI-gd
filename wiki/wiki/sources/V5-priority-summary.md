---
type: source-summary
title: "V5-priority · V5+ 路线优先级汇总"
sources:
  - docs/guandan-brain/issues/V5-priority.md
tags:
  - source-summary
  - v5-plus
  - roadmap
status: current
related_gua:
  - GUA-034
  - GUA-035
  - GUA-036
  - V5+-01
  - V5+-02
  - V5+-03
  - V5+-04
date: 2026-06-17
---

# V5-priority · V5+ 路线优先级汇总

## 摘要

V5+ 是 GUA-034 讨论中明确划出本轮 M3 范围外、但需要统一追踪的四个工作流。本汇总对应 GUA-034-方案评审.md。

## 四项优先级

| ID | 主题 | 来源 / 触发 | 备注 |
|----|------|-------------|------|
| V5+-01 | lalala 两手走完枚举 + 首出选优 | GUA-034 讨论 ②；M3_DIAGNOSIS BUG2 | lalala sort 比较 bug + 候选未消费（action.py:1117-1127） |
| V5+-02 | solo 接风可回收单张优先级 | GUA-034 讨论 ③ | 配套 GUA-035/036 排除范围 |
| V5+-03 | 方向 E 轻量模板 | GUA-034-方案评审.md | 触发条件：solo_sprint && numofmy<=8 |
| V5+-04 | 整手结构组牌（钢板+顺子+炸弹+单张协同） | — | 不在 M3 扩 combine_handcards；需 enumerate_groupings / 搜索；贯穿 V7 Phase 2-3 |

## 与 GUA 体系的耦合

- V5+-01/02 是 M3 续切片（参见 [[gua-035]] / [[gua-036]]）的范围外条目
- V5+-04 是 V7 Phase 2-3 的关键依赖（参见 [[gua-045]] / [[gua-038]] / [[gua-039a]]）

## 张力

V5+ 同时被 M3 排除范围和 V7 Phase 2-3 引用，需在 [[v5-plus-roadmap]] 统一视图，避免认知负担分裂。
