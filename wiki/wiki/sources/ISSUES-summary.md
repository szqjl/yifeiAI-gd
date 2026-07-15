---
type: source-summary
title: "ISSUES.md — 缺陷登记簿（活跃主表）"
sources:
  - docs/guandan-brain/ISSUES.md
tags:
  - issues
  - gua-registry
  - main-table
status: current
related_gua:
  - GUA-029
  - GUA-146
date: 2026-07-15
---

# ISSUES.md — 缺陷登记簿（活跃主表）

## 摘要

`ISSUES.md` 是项目**活跃缺陷的主表**，存放 GUA-029 起的 open / closed 条目。GUA-001~028 已拆分至 [[issues-ARCHIVE-summary]]。

## 当前结构

- **主表**：GUA-029 ~ GUA-146（活跃 + 近期 closed）
- **归档**：GUA-001 ~ GUA-028 → `issues/ARCHIVE.md`
- **状态标记**：`open` / `closed ✅` / `open 🔄`（重开）/ `closed (archived)`

## 当前 P0 列表（节选）

- [[gua-054]] — V7 组牌质量中间表示
- [[gua-055]] — V7 动作空间二阶段过滤
- [[gua-059]] — BC v2 退化根因
- [[gua-063]] — 组牌→出牌衔接（重开 🔄）

## 重要已 closed ✅

- [[gua-061]] — V7 模块化架构 GroupingEngine
- [[gua-062]] — 组牌引擎 v2 + 首次批跑 V7 vs lalala
- [[gua-022]] — M1 frozen

## 时间口径注意

- 归档条目中部分 closed 日期早于 `ARCHIVE.md` 文件标注的「2026-07-15」归档时间
- **正确理解**：归档是批量回填操作，非实时同步

## 关联

- [[issues-ARCHIVE-summary]]
- [[ITERATIONS-summary]]
- [[EVAL-summary]]
