---
type: source-summary
title: "M2 优化记录 (M2_OPTIMIZATION)"
sources:
  - docs/guandan-brain/M2_OPTIMIZATION.md
tags:
  - source-summary
  - engine-m2
  - diagnosis
  - migration
status: current
related_gua:
  - GUA-020
  - GUA-021
  - GUA-022
date: 2026-06-18
---

# M2 优化记录 (M2_OPTIMIZATION)

## 文件定位
M2 引擎的完整跑分 + Bug 诊断 + 炸弹策略对照 + Step1-4 待执行清单。是 **M2 → M3 迁移的桥接证据**。

## M2 引擎概况
- **实现位置**：`src/decision/rule_based_decision_engine_m2.py`、`src/decision/phase_handlers_m2.py`
- **风格**：lalala 风格硬编码规则
- **跑分结果**：70+ 局 **0% 队胜**（即 0/N 局队胜）
- 详见 [[engine-m2]]

## M2 五大 Bug（已识别）
1. Bug 1：[待补]
2. Bug 2：[待补]
3. Bug 3：[待补]
4. Bug 4：[待补]
5. Bug 5：[待补]

> 注：完整 Bug 描述需在 [[engine-m2]] 实体页展开

## 炸弹策略覆盖率（关键指标）
- **出炸弹要领覆盖率**：M2 仅实现约 **8/76 条**（约 10%）
- 配炸 / 炸什么 / 如何用炸：**0%**
- 残局用炸：**15%**
- 结论：M2 在炸弹策略上几乎是空白的

## 跑分数据异常
- M2 两次 Run 1 数据**完全相同**（2026-05-26 各 44 局，均 [0,3,0,3]）
- 疑似表格重复粘贴，摄入时**只保留一行**

## 残局两手牌组合（重要发现）
- lalala 原版 `action.py:1117-1127` 原始实现**本身含 Bug**：
  - `sort()` 返回 None 导致比较恒假
  - 候选列表为 dead code
- **不能作为 M3 移植参考**，必须重写
- 详见 M2 极端被动根因、残局两手牌组合

## Step1-4 待执行清单
[待补：根据 M2_OPTIMIZATION.md 原文补充]

## 关联
- 后续迭代：wiki-minimax/entities/engine-m3.md
- 极端被动根因：M2 极端被动根因
- 桥接合成：[[synthesis-m2-to-m3-migration]]
