---
type: synthesis
title: "V7 残局预处理器综合分析"
sources:
  - docs/knowledge/skills/07_opening/end position.md
tags:
  - v7
  - endgame
  - synthesis
  - architecture
status: current
related_gua:
  - GUA-075
  - GUA-065
date: 2026-06-21
---

# V7 残局预处理器综合分析

## 跨资料综合

本文是对 [[end-position-design-summary|残局预处理器设计文档摘要]] 的进一步综合分析，聚焦：
1. 当前状态全景
2. 已知张力与权衡
3. 待批跑验证项
4. 后续开发路线

## 当前状态全景

### 已确立（设计层面）

- ✅ 残局管线优先级凌驾于 Guard 链之上
- ✅ 注入点：`_inject_numofplayers` 之后、GUA-075 主路径之前
- ✅ 方案 A 硬排除（`banned_types` + `baoshu.never_play`）
- ✅ 四角色分派（Q0/Q1/Q2/Q3）
- ✅ 三级降级兜底（L1/L2/L3）
- ✅ 牌型名映射复用 `v7_guards.py` 现有工具
- ✅ 敌双残局排序规则（下家优先 + 并集）

### 已配置（实验性开关）

| 开关 | 值 | 状态 |
|------|----|----|
| `R11_ENDGAME_MODE` | partial | 待 A/B |
| `GUA075_ENDGAME_WEIGHTED` | False | 待 A/B |
| Q1 多推荐牌型 | 回收优先 | 待 A/B |

### 待补（设计文档）

- ⚠️ Q0「出牌权不在我手」场景策略（文件截断）
- ⚠️ L3 降级「级牌以下最大」实现细节
- ⚠️ Q1/Q2 同牌数冲突最优策略（等记忆管线）

## 已知张力与权衡

### 张力 1：残局 vs Guard 平等架构

**问题**：V7 原架构是 R01-R14 平等竞争，残局管线凌驾之上打破平等。

**当前方案**：方案 A 硬排除——在 Guard 运行前统一处理 `banned_types`，Guard 自身不感知残局。

**风险**：粒度粗，无法做"按 Guard 区别退让"（如 R11 退让但 R08 保留）。

**未来选项**：在每个 Guard 内部判断 `_endgame_context`（粒度细但侵入性强）。

### 张力 2：R11 部分退让是实验选择

**当前**：`R11_ENDGAME_MODE=partial`（阈值上调但仍抑制）

**文档原则**："先跑效果、数据说话"——意味着 partial 仍可调，需 [[batch-evaluation]] 验证。

**待验证级别**：
- `full_cede`（完全退让）
- `threshold_only`（仅节流）

### 张力 3：GUA-075 残局不加权

**当前**：`GUA075_ENDGAME_WEIGHTED=False`

**原因**：推荐已被 Q1/Q2 消耗，禁止已被一刀切，加权意义不大。

**风险**：未来若残局管线变化（如让 GUA-075 接管部分决策），加权可能需要重新打开。

### 张力 4：Q1/Q2 同牌数冲突保守策略

**当前行为**：封锁优先（Q1 胜）

**代价**：有损但安全，可能错失部分最优配合

**未来**：等记忆管线（MemoryTracker 完善）就绪后回头补最优策略

### 张力 5：L3 降级是极限边缘场景

**触发条件极低**：敌人报单 + 自己无炸 + 主动方 + 手牌全单张

**风险**：实现细节（"级牌以下最大"/"无则出全部"）需明确，否则可能误出大牌或漏出

## 待批跑验证项

| 项 | 当前 | 候选 | 验证目标 |
|----|------|------|----------|
| R11 退让级别 | partial | full_cede / threshold_only | 残局胜率 |
| GUA-075 残局加权 | False | True | 推荐质量 |
| Q1 多推荐排序 | 回收优先 | 牌力最强 | 封锁效率 |
| 残局阈值 N | 10 | 8 / 12 | 触发频率 vs 准确度 |

> 详见 [[batch-evaluation]]

## 后续开发路线

### 短期（待补设计文档）
1. 补 Q0「出牌权不在我手」场景策略
2. 明确 L3 降级「级牌以下最大」实现
3. 文档化 GUA-075 在残局激活时的具体行为

### 中期（批跑验证）
1. 跑 `R11_ENDGAME_MODE` 三档 A/B
2. 跑 `GUA075_ENDGAME_WEIGHTED` 开关 A/B
3. 跑 Q1 回收优先 vs 牌力最强 A/B

### 长期（架构演进）
1. 评估方案 A 硬排除的局限，必要时引入 Guard 内部退让
2. 记忆管线就绪后回头补 Q1/Q2 同牌数冲突最优策略
3. 与 [[gua-075]] 的残局加权决策做更深度集成

## 关联页面

- [[endgame-pipeline]] — 残局管线概念
- [[module-endgame-preprocessor]] — 实现模块
- [[guandan-guard-retreat]] — Guard 退让机制
- [[shape-name-to-action-types]] — 牌型名映射
- [[gua-075]] — 推荐引擎
- [[gua-065]] — numofplayers 来源
- [[engine-v7]] — V7 引擎
- [[batch-evaluation]] — 批跑评测
- [[end-position-design-summary]] — 设计文档摘要
