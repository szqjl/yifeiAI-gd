---
type: source-summary
title: "残局管线设计（end position.md）"
aliases:
  - 残局管线设计
  - end position.md
sources:
  - docs/knowledge/skills/07_opening/end position.md
tags:
  - v7
  - endgame
  - design-doc
  - pipeline
status: current
related_gua:
  - GUA-078
  - GUA-075
  - GUA-065
date: 2026-06-01
---

# 残局管线设计（`end position.md`）

## 概述

**权威设计真源**：`docs/knowledge/skills/07_opening/end position.md`（备注名：**残局管线设计**）。

定义 V7 **Endgame Pipeline**（`EndgamePreprocessor` + `EndgameDecider` Q0→Q3）：注入点、`numofplayers` 数据源、四角色分派（封锁/助攻/冲刺/兜底）、方案 A 硬排除、R11 退让等。实现见 `src/v/nn/endgame/`。

> 非「开局终局定位」类开局技能；旧摘要（opening 策略）已作废。

## Wiki 衍生页

| 页面 | 类型 | 说明 |
|------|------|------|
| [[end-position-design-summary]] | source-summary | 设计文档结构化摘要 |
| [[endgame-pipeline]] | concept | 残局管线概念与注入点（与真源 §五 同步） |
| [[endgame-preprocessor-overview]] | synthesis | 综合分析 + 已知张力 |
| [[module-endgame-preprocessor]] | entity | 实现模块索引 |

## 摄入状态

- `source_manifest.json` 已登记该路径；**内容变更后**需 `python scripts/wiki.py ingest` 重摄入以更新 LLM 衍生页。
- 手工维护的 `wiki/wiki/sources/*.md`、`concepts/endgame-pipeline.md` 以真源为准，2026-06-01 已与 §二/§五 管线订正对齐。

## 关联

- [[gua-078]] — 残局智能体管线实现
- [[batch-evaluation]] — 实验开关批跑验证
