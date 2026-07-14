---
type: concept
title: "M1 frozen 迁 M3 决策路径"
sources:
  - docs/guandan-brain/iterations/m1-strategy-gua022.md
  - docs/guandan-brain/iterations/m3-integration-gua024-028.md
related_gua:
  - GUA-022
  - GUA-024
tags:
  - m1
  - m3
  - handoff
  - frozen
date: 2026-06-18
---

# M1 frozen 迁 M3 决策路径

## 总纲

M1 0/12 同机对照 → M1 frozen → P0 guard 改 `m3_decision_engine` 的完整路径。

## 关键事件

1. **GUA-022 closed-frozen**（40 天 10 轮迭代，0/12 队胜率）
2. **KPI 迁 M3**：PASS率 / 队胜率 / 炸弹频次 / vn非空率 全面切换
3. **GUA-024 M3 play 全 PASS 根因**：暴露 M3 集成阶段首轮批跑 0/10 失败
4. **共用层复用**：M1 的 `stage_router.py` / `phase_handlers.py` 在 M3 保留
5. **P0 guard 迁移**：原 M1 guard 改由 `m3_decision_engine` 实现

## 设计原则

- 资产复用：共用层（路由 / 阶段处理）跨 M1/M3 共享
- KPI 单一真源：所有 KPI 由 M3 批跑产出
- 缺陷归档：M1 缺陷不重开，转 M3 等价条目

## 关联

- [[engine-m1]]
- wiki-minimax/entities/engine-m3.md
- m1-vs-m3-handoff
- [[GUA-022]] / [[GUA-024]]
