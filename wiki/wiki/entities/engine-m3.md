---
type: entity-engine
title: "M3 规则引擎"
sources:
  - docs/guandan-brain/ITERATIONS.md
  - docs/analysis/v7-kpi-vs-m3-vs-lalala-2026-06-29.md
tags:
  - engine
  - rule-based
  - m-dev
status: current
related_gua:
  - GUA-022
  - GUA-055
date: 2026-07-01
---

# M3 规则引擎

## 基本信息

- **分支**：`m-dev`
- **类型**：规则引擎（rule-based）
- **状态**：当前主迭代（规则层），但已**达瓶颈**
- **客户端**：`yf1_m3` / `yf2_m3`（团队协作模式）

## 团队协作模式

- **yf1_m3 + yf2_m3** 双客户端协作
- 双上计分王 = 上对家 + 下对家 各两人队

## M1 冻结

- M1 已 frozen（[[gua-022]]）
- 作为 M3 的对照基线

## M3 已知缺陷

- [[gua-055]] — M3 决策引擎已知缺陷，修复进度需追踪
- 规则引擎结构性瓶颈：无法处理对手牌型推断

## V7 迁移

M3 已被认定为**达瓶颈**，未来方向是 [[engine-v7]]（NN 引擎）。
详见 [[v7-nn-engine-migration]]。

## 跨引用

- [[engine-v7]] — 下一代
- [[v7-nn-engine-migration]] — 迁移路径
- synthesis-v-series-failure — V系列失败方法论
```

---
