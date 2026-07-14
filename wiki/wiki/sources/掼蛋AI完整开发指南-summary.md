---
type: source-summary
title: "掼蛋AI完整开发指南 - 摘要"
sources:
  - docs/development/掼蛋AI完整开发指南.md
tags:
  - development-guide
  - overview
  - architecture
status: current
related_gua: []
date: 2026-06-18
---

# 掼蛋AI完整开发指南 - 摘要

## 概述

《掼蛋AI完整开发指南》是双上计分王掼蛋 AI 项目的**总纲性文档**，系统性地描述了项目目标、架构设计、引擎演进、决策算法、训练流程及评测体系。

## 关键主题

- **项目定位**：双上计分王掼蛋 AI，目标是开发能在掼蛋游戏中达到高水平表现的 AI 引擎
- **引擎演进**：从 M1 → M3（规则引擎）→ V7（NN 引擎）的迭代路径
- **决策算法**：M3 规则引擎的决策逻辑，包括手牌分析、出牌策略、配合策略
- **训练流程**：V7 神经网络的离线训练与在线推理
- **评测体系**：基于离线批跑的胜率 KPI 评估方法

## 与其他资料的关系

- 是 structure-prompt-spec 的上层指导
- 与 wiki-minimax/entities/engine-m3.md、wiki/entities/engine-v7.md 等引擎文档互为补充
- 评测章节与 wiki-minimax/concepts/batch-evaluation.md 概念直接相关

## 待补充

- 源文件 20015 字符，摘要级别仅覆盖核心主题
- 详细内容需分章节生成 entity/concept 页面
