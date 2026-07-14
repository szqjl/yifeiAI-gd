---
type: source-summary
title: "GUA 缺陷追踪总表"
sources:
  - docs/guandan-brain/ISSUES.md
tags:
  - gua
  - issues
  - defect-tracking
  - core
status: current
related_gua: []
date: 2026-07-03
---

# GUA 缺陷追踪总表（ISSUES.md）

## 概述

`ISSUES.md` 是双上计分王项目的**缺陷管理主表**，按 GUA 编号体系（GUA-001~061+）记录所有已知缺陷、迭代、状态变更。

## 关键内容

- **GUA 编号体系**：GUA-001 起，持续递增
- **文档规模**：20,015 字符
- **核心字段**：编号、标题、状态、优先级、负责人、创建/关闭日期
- **生命周期**：Open → In Progress → Resolved → Closed

## GUA 状态分类

| 状态 | 含义 |
|------|------|
| Open | 待处理 |
| In Progress | 修复中 |
| Resolved | 已修复待验证 |
| Closed | 已验证关闭 |
| Wontfix | 不修复 |

## 优先级

- **P0**：阻塞性问题，立即处理
- **P1**：重要缺陷，优先排期
- **P2**：一般缺陷，按计划处理
- **P3**：优化项，低优先级

## 注意事项

> 原文存在与 `ITERATIONS.md` 同路径的重复条目（20,015 字符），需注意区分。

## 相关页面

- [[ITERATIONS-summary]]
- [[gua-061]]
- [[overview]]

## 原始信息

- 路径：`docs/guandan-brain/ISSUES.md`
- 字符数：20,015
- 类型：缺陷追踪主表
