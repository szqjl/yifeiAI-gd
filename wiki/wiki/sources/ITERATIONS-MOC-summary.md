---
type: source-summary
title: "ITERATIONS MOC 入口摘要"
sources:
  - docs/guandan-brain/ITERATIONS.md
tags:
  - moc
  - iterations
  - index
status: current
related_gua:
  - GUA-045
  - GUA-060
  - GUA-061
date: 2026-06-17
---

# ITERATIONS MOC 入口摘要

## 文件定位

`docs/guandan-brain/ITERATIONS.md` 是掼蛋大脑体系的**迭代总索引（MOC, Map of Content）**，以 Obsidian wikilink 风格组织 M1/M2/M3/V2~V7 各开发线与基础设施治理。

## 核心分组

| 分组 | 内容 | 状态 |
|------|------|------|
| **M 系列开发** | [[M1-Development]]、M2-Development、[[M3-Development]] | 已完成/稳定 |
| **V 系列开发** | [[V7-Development]]（当前主迭代） | 进行中 |
| **基础设施** | [[Infrastructure]]（Phase 5 仓库治理） | 进行中 |
| **GUA 索引** | [[GUA-Index]] | 持续维护 |
| **KPI 观察** | [[kpi-observations]] | 持续维护 |

## 关键说明

- **拆分规则**：迭代文件 > 10 条 GUA 拆为子文件 + MOC 索引
- **链接风格**：Obsidian wikillink（`页面`）交叉引用
- **维护节奏**：每个 GUA 关闭/立项时同步更新 MOC 链接

## 当前活跃

- **GUA-061**（P0 OPEN）：模块化架构，V7 BC 路线终止后的方向性转弯
- **GUA-060**（CLOSED 2026-06-17）：argmax collapse 理论必然

## Wiki 落地策略

本 MOC 入口的所有 wikilink（V7-Development、M3-Development、Infrastructure、GUA-Index、kpi-observations）当前在 Wiki 中**尚无对应页面**，建议：
1. `synthesis-v7-current-state.md` 承担 V7-Development 入口职能
2. `engine-m3.md` / `engine-v7.md` 承担 M3/V7 入口职能
3. `phase5-infra-summary.md` 承担 Infrastructure 入口职能
4. 本文件 + `GUA-Index` 概念页承担 GUA 索引入口
5. `synthesis-v7-bc-failure-map.md` 承担 kpi-observations 入口

## 关联

- 批跑评测体系
- GUA 编号体系
- [[gua-045]]
- [[gua-061]]
- wiki/entities/engine-v7.md
