---
type: concept
title: "工作流 WF-10 · Guard 规则约束"
sources:
  - docs/guandan-brain/工作流.md
  - docs/guandan-brain/PRINCIPLES_MAPPING.md
tags:
  - workflow
  - wf-10
  - guard
  - rule
status: draft
related_gua:
  - GUA-045
  - GUA-089
date: 2026-06-30
---

# 工作流 WF-10 · Guard 规则约束

## 目的

维护、评审、扩展 V7 原生 Guard 规则集（R01-R14）。

## 主要动作

1. 读 [[v7-guard-rule-inventory]] 检查规则状态
2. 新增规则需带 `stage_tag`（GUA-089 阶段调度避免堆叠崩）
3. 提交 pytest（构造态） + 个别净盘批跑（GUA-097）
4. 记入 ISSUES.md 主表 + [上下文]、[关联]

## 关联

- GUA-045：V7 Guard 壳定义
- GUA-089：阶段调度器（stage_tag 机制）
