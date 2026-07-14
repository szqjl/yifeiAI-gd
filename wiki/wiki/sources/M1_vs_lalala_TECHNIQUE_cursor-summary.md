---
type: source-summary
title: "M1 vs lalala 技术评审（Cursor 版）"
sources:
  - docs/guandan-brain/reviews/M1_vs_lalala_TECHNIQUE_cursor.md
tags:
  - m1
  - lalala
  - review
  - cursor
status: current
related_gua:
  - GUA-061
  - GUA-022
date: 2026-06-18
---

# M1 vs lalala 技术评审（Cursor 版）

## 文档定位

由 Cursor 智能体产出的 M1 vs lalala **技术架构对照评审**，是 GUA-061 等 P0 缺陷的技术诊断依据。

## 核心结论

### 范式差异
- **lalala**：**牌型内嵌范式**——在牌型匹配阶段同时决策大小/数量
- **M1**：**阶段分层范式**——CardTypeHandlerFactory / phase_handlers 平行架构，先分类后填值

### Cursor 视角下 M1 的关键缺陷

#### 1. StageRouter 强制非 PASS 兜底
**机制描述**：M1 在无可出牌时会兜底选择一个非 PASS 动作以避免直接弃权。
**问题**：与 GUA-061（m1 over-prediction，P0 缺陷）可能是同一根因的不同表述。
**关联**：[[GUA-061]]、StageRouter-强制非PASS兜底

#### 2. 决策维度缺口
M1 决策引擎缺失以下关键维度：
- `pass_num`（本轮过牌计数）
- `numofnext`（下游牌数）
- `numofgreaterPos`（上游压制位）
**关联**：`lalala_adapter.py` 接线存在缺口，GUA-037a 修复中。

#### 3. 路径债
M1 代码路径分散（4209 行），相比 lalala 存在工程化劣势。

### 自评打分
Cursor 自评 **83%**，认为 M1 已被边缘化，子策略价值有限。

## 张力点

- Cursor 自评 83% vs opencode 自评 85%，两版评审存在「低估 M1 子策略」vs「过度强调 M1 缺陷」的视角差异
- M1 边缘化但 [[SKILL_yifegdbot-onboarding-summary]] 仍把 M1 作为入门主线

## 关联页面

- [[engine-m1]]
- [[m1-vs-lalala-paradigm]]
- [[GUA-061]]
- [[GUA-022]]
- M1_vs_lalala_TECHNIQUE_opencode-summary（待建）
