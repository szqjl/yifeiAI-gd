---
type: concept
title: "修复报告聚类 - fixes/ 目录模式"
sources:
  - docs/fixes/EVALUATOR_COMPATIBILITY_REPORT.md
  - docs/fixes/GAME_RECORD_SAVE_FIX.md
  - docs/fixes/GAME_RECORD_VICTORYNUM_CHECK.md
  - docs/fixes/V7_GUI_PATH_VALIDATION_FIX.md
tags:
  - fix-pattern
  - docs-organization
  - lifecycle
status: current
related_gua: []
date: 2026-06-18
---

# 修复报告聚类 - fixes/ 目录模式

## 概述

`docs/fixes/` 目录集中存放已修复缺陷的报告文档，是项目缺陷生命周期管理的"归档层"。

## 命名约定

- `*_FIX.md` — 描述具体修复方案与根因
- `*_REPORT.md` — 描述问题分析与影响范围
- `*_CHECK.md` — 描述增强的校验逻辑

## 典型结构

1. **Bug 现象**：用户/测试可观察的异常
2. **根因分析**：技术层面的原因定位
3. **修复方案**：代码改动与验证步骤
4. **影响范围**：哪些模块/场景受影响

## 与 GUA 体系的关系

- 每个 fix 报告**应**对应一个 GUA 编号
- fix 报告是 GUA 从 open → closed 状态的物证
- 多个 fix 可能合并/关联到同一个 GUA（如 GAME_RECORD_* 系列）

## 当前观察

- evaluator-compatibility-report-summary、game-record-save-fix-summary、game-record-victorynum-check-summary 三个文件形成"评测器+对局记录"修复簇
- v7-gui-path-validation-fix-summary 独立属于 V7 引擎的 GUI 子系统

## 改进建议

- 建议为每个 fix 报告显式标注对应 GUA 编号
- 在 GUA entity 页面中引用对应的 fix 报告作为佐证材料
