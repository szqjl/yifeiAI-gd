---
type: synthesis
title: "V7 vs lalala 胜率历史"
sources:
  - docs/analysis/archive/2026-06-18-gua062-batch-eval.md
  - docs/guandan-brain/EVAL.md
tags:
  - v7
  - lalala
  - win-rate
  - batch-eval
  - kpi
  - baseline
status: current
related_gua:
  - GUA-060
  - GUA-061
  - GUA-062
date: 2026-06-29
---

# V7 vs lalala 胜率历史

## 概述

V7 引擎 vs lalala（南邮离线平台参考对手）的累计胜率历史，是 V7 战略转向的**核心证据**。handoff 2026-06-18 明确禁止重跑 GUA-061 批跑（基线已锁），本页承载历次批跑 KPI 综合。

## 基线对比

| 引擎 | 累计局数 | 队胜率 | 副胜率 | 备注 |
|------|----------|--------|--------|------|
| **M3**（参考基线） | ~500+ | **~70%** | 60-70% | 规则引擎，V7 借鉴 Guard 壳 |
| **M1 / M2** | 已废弃 | — | — | 早期规则引擎 |
| **V7** | 138 局 | **0.7%** | 3-26% 波动 | NN 引擎，BC 路线 |

**结论**：V7 队胜率**比 M3 低两个数量级**，副胜率波动大且不稳定。

## 关键批跑节点

### 2026-06-18 GUA-062 批跑

- **设置**：V7 vs lalala × 9 局
- **结果**：
  - **局胜 0/9**（0%）
  - **副胜 10.1%**（与 GUA-061 无显著区别）
- **结论**：组牌引擎 v2 评分**pytest 通过但实战未转化**（GUA-062 教训）
- **文件**：`docs/analysis/archive/2026-06-18-gua062-batch-eval.md`

### GUA-061 基线（V7 BC 路线）

- **设置**：V7 BC 路线 vs lalala
- **结果**：累计 138 局 0.7% 队胜
- **结论**：BC argmax collapse 已证（[[bc-argmax-collapse]]）
- **状态**：基线已锁，禁止重跑

### 历史波动

副胜率 3-26% 波动原因分析：
1. **对家配合**：当对家是配合型 AI 时副胜率上升
2. **起手牌质量**：起手有大牌/炸弹时副胜率偏高
3. **残局管线触发**：Q0~Q3 残局触发时表现稍好
4. **BC collapse 时点**：卡 2 级局副胜率显著下降

## 战略意义

### 禁止事项（handoff 2026-06-18）

- ❌ 禁止重训 BC
- ❌ 禁止重跑 GUA-061 批跑
- ❌ 禁止把 BC 作为 V7 主决策器

### 下一步方向

- ✅ 启发式 + 自对弈 RL（handoff 明确方向）
- ✅ 决策链根因定位（GUA-062 后续）
- ✅ Guard 综合迭代（GUA-065~071）

详见 [[v7-current-state]]。

## 关键教训

1. **"pytest 通过 ≠ 实战有效"**（GUA-062）
2. **"BC 路线已到天花板"**（GUA-060/061）
3. **"基线锁定后不再重跑"**（handoff 纪律）
4. **"副胜率波动需要分层归因"**（位置/手牌/触发管线）

## 关联页面

- [[v7-current-state]]
- [[bc-argmax-collapse]]
- [[gua-060]]
- [[gua-061]]
- [[gua-062]]
- [[batch-evaluation]]
- [[game-scoring-tracking]]
- [[engine-m3]]
- [[局不等于副]]
