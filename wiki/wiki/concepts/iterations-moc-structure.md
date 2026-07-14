---
type: concept
title: "迭代日志 MOC 结构 (Obsidian wikilink 模式)"
sources:
  - docs/guandan-brain/ITERATIONS.md
tags:
  - moc
  - obsidian
  - wikilink
  - documentation-pattern
status: current
related_gua: []
date: 2026-06-18
---

# 迭代日志 MOC 结构（Obsidian wikilink 模式）

## 概念定义

`ITERATIONS.md` 顶部明确说明项目迭代日志已重构为 **Obsidian 式组织**，这是项目自身的文档组织范式。其核心特征是：

1. **MOC 入口**：顶层文件作为 Map of Content
2. **wikilink 交叉引用**：使用 `文件名` 语法建立双向链接
3. **快速导航**：Agent 可通过 wikilink 跳转定位任意迭代
4. **模板追加规则**：新迭代需按统一模板登记

## 应用范围

- `ITERATIONS.md` → 顶层 MOC
- `M1-Development` / `M3-Development` / `V7-Development` → 按引擎归档的子 MOC
- 详见 wiki/sources/ITERATIONS-summary.md

## 治理价值

- **可接续性**：新 Agent 通过 MOC 快速理解项目历史
- **可追溯性**：每个迭代有唯一编号（GUA/V7-xxx）
- **可治理性**：状态字段（open/closed/observed）一目了然

## 与 Wiki 系统的关系

本 Wiki 系统采用相同的 wikilink 模式（`页面文件名` 无扩展名），与 `docs/guandan-brain/` 下的 Obsidian 风格保持一致，便于跨系统检索。

## 关键设计原则

- **编号体系是脊柱**：GUA-xxx 是缺陷/迭代的唯一锚点
- **状态显式化**：每个迭代必须有 status 字段
- **来源可追溯**：每条记录必须可回溯到原始 commit/会话
