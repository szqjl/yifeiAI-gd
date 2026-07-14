---
type: synthesis
title: "M 系列引擎迭代脉络（M1 → M2 → M3）"
sources:
  - docs/analysis/agent-sessions/decisions_20260528_batch30.md
  - docs/analysis/agent-sessions/guandan-basic-knowledge.md
  - docs/guandan-brain/ISSUES.md
tags:
  - evolution
  - m-series
  - synthesis
status: current
related_gua: []
date: 2026-06-18
---

# M 系列引擎迭代脉络（M1 → M2 → M3）

## 概述

本文综合 [[decisions_20260528_batch30-summary]]、[[guandan-basic-knowledge-summary]] 及 wiki-minimax/entities/engine-m3.md 已有资料，梳理 M 系列决策引擎的代际演进。

> ⚠️ **核心张力**：M1/M2 在不同上下文中可能指代 **引擎代际** 或 **agent 文件后缀**，两套命名是否对齐尚未定论。

## 命名歧义

| 上下文 | M1/M2 含义 | 证据 |
|-------|----------|------|
| agent 文件名 | `yf1_m1.py` / `yf2_m1.py` 可能是 agent 实现版本 | 决策模式 batch30 |
| 优化日志 | `M2_OPTIMIZATION.md` 暗示 M2 是引擎代际 | Wiki 已有 |
| Wiki 引擎条目 | `engine-m3` 明确 M3 是当前主迭代 | Wiki 已有 |
| 客户端后继 | `YF1_V5` 是 M 系列客户端的后继 | [[module-yf1-v5-client]] |

**未解问题**：
- `yf1_m1.py` 中的 `m1` 是 **M1 引擎** 还是 **agent v1 文件**？
- M1/M2/M3 是 **引擎代际**（规则升级）还是 **文件代际**（重构）？

## 代际假设（待验证）

| 代际 | 形态 | 已知产物 | 状态 |
|------|------|---------|------|
| **M1** | 规则引擎 | `yf1_m1.py` / `yf2_m1.py`、batch30 数据 | 历史阶段 |
| **M2** | 规则引擎（优化） | `M2_OPTIMIZATION.md`、`game_scores_m2.json`、基本知识库 | 历史阶段 |
| **M3** | 规则引擎（当前主迭代） | 详见 wiki-minimax/entities/engine-m3.md | 当前主迭代 |
| **V7** | NN 引擎（未来） | 详见 wiki/entities/engine-v7.md | 未来方向 |

## M2 阶段知识沉淀

来自 [[guandan-basic-knowledge-summary]]：

- 完整规则体系（升级表、座位、A 级、完赛名次）
- v1006 平台协议字段
- 局/副/圈/轮的四层术语区分
- 副级 + 局级 双重追踪架构

> M2 阶段是 **领域知识沉淀** 的关键期，为 M3 引擎的状态机建模奠定基础。

## batch30 快照

来自 [[decisions_20260528_batch30-summary]]：

- 玩家：`yf1_m1`（0 号位）+ `yf2_m1`（2 号位）
- 平台：`guandan_offline_v1006`
- 指标：PASS 率 / 首炸@ / 炸弹使用次数 / 牌型分布
- 时间：2026-05-28

> 这是 M1 阶段的最后一批决策数据？还是 M2 回测？需进一步确认。

## V7 与 M 系列的关系

- **V7 是 NN 引擎**（未来方向）
- **M 系列是规则引擎**（当前主迭代）
- M 系列的批跑数据是 V7 的 **训练数据来源** 之一
- V7 与 M3 的迭代边界需在 wiki-minimax/entities/engine-m3.md 与 wiki/entities/engine-v7.md 中明确

## 迭代关系图（推测）

```
M1 (yf1_m1/yf2_m1)
    ↓ 规则优化
M2 (M2_OPTIMIZATION + game_scores_m2.json + 基本知识库)
    ↓ 状态机升级
M3 (当前主迭代) ──→ 训练数据 ──→ V7 (NN 引擎，未来)
    ↓
YF1_V5 (客户端后继)
```

## 关键张力总结

1. **命名歧义未解**：`yf1_m1` 的 `m1` 含义需在 wiki-minimax/entities/engine-m3.md 中明确
2. **M2 文档定位模糊**：是 M2 阶段产物还是通用知识库？
3. **V7 与 M3 边界**：M3 的批跑数据如何用于 V7 训练？
4. **YF1_V5 定位**：是 M 系列的继任者还是并行分支？

## 下一步

1. 在 wiki-minimax/entities/engine-m3.md 中明确 M1/M2/M3 的代际定义
2. 在 [[module-yf1-v5-client]] 中补充与 M 系列的迭代关系
3. 创建 query-m1-m2-m3-naming 查询页追踪命名澄清
4. 与 V7 团队对接，确认训练数据接口

## 关联页面

- wiki-minimax/entities/engine-m3.md：M3 引擎主条目
- wiki/entities/engine-v7.md：V7 NN 引擎
- [[module-yf1-v5-client]]：YF1_V5 客户端
- wiki/entities/module-batch-executor.md：批跑执行器
- [[guandan-basic-knowledge-summary]]：M2 知识库
- [[decisions_20260528_batch30-summary]]：batch30 数据
- [[round-vs-game]]：局/副口径
- [[v1006-platform-params]]：平台协议
- [[decision-metrics]]：决策指标
