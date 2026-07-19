---
type: source-summary
title: "WF-12 副12 yf1 Q1 让道决策分析摘要"
sources:
  - docs/analysis/WF-12-20260716222448436062-副12-yf1-Q1让道决策分析.md
tags:
  - source-summary
  - walkforward
  - root-cause
  - r-d09
status: current
related_gua:
  - GUA-135
  - GUA-150
date: 2026-07-19
---

# WF-12 副12 yf1 Q1 让道决策分析摘要

> 来源：`docs/analysis/WF-12-20260716222448436062-副12-yf1-Q1让道决策分析.md`（约 5.3K 字符）

## 圈况

- **牌局 ID**：WF-12-20260716222448436062
- **玩家**：yf1_m3（在 Q1 让道决策中）
- **步数**：副 12 第 35 步
- **触发日志**：`logs/yf1_v8_20260716_222428.log` 中 `endgame_decide.py:2662` 行命中 GUA-135 self_sprint

## 管线还原

按 [[concept-three-layer-decision-pipeline|L0/L1/L2 决策管线]]逐层追踪：

1. **L0**：识别为 Q1 让道残局情境
2. **L1**：进入 `_q1_block_enemy` 子决策
3. **关键日志**：endgame_decide.py:2662 — **命中 GUA-135 self_sprint 路径**（**非 L962 兜底**）
4. **结论**：根因是 GUA-135 self_sprint 一刀切 PASS，未比较 self/teammate 冲刺路径

## R-D09 根因

| 维度 | 内容 |
|------|------|
| 编号 | R-D09 |
| 症状 | self_sprint 让道误判 |
| 表层 | 一刀切 PASS |
| 深层 | 未比较 self/teammate 冲刺路径长度 |
| 触发 | `self_sprint_priority` 比较缺失 |
| 修复 | GUA-150 — 引入 intent 比较 + 估算剩余轮次 |

## 与 Q0 报告 v1 的关键分歧

| 维度 | Q0 报告 v1 | Q1 报告（正式结论） |
|------|------------|---------------------|
| 触发行号 | `endgame_decide.py:962`（Q0 兜底） | `endgame_decide.py:2662`（GUA-135 self_sprint） |
| 根因 | Q0 入口兜底 PASS | **GUA-135 self_sprint 让道** |
| 证据强度 | 推断 | **日志实证** |
| 修复 GUA | GUA-151 候选 | **GUA-150（已实施）** |

> **结论**：Q1 报告为正式结论。Q0 报告 v2 已据此修订。

## 5 问准入

| 问 | 答 |
|----|----|
| 一类局面？ | ✅ Q1 让道残局 |
| 可沉意图层？ | ✅ _stage_mid_dispatch |
| P0 止血？ | ✅ R-D09 |
| pytest + trace？ | ✅ 6/6 通过 |
| 迁移出口？ | ✅ GUA-091 |

## 后续观察项

- **12 局 V8 批跑后**：观察 GUA-135 self_sprint 触发频次
- **GUA-151 候选**：Q0 跟压场景下应否优先出 SB 解敌控？→ 暂搁置，待观察

## 交叉引用

- [[gua-135]] — self_sprint 规则
- [[gua-150]] — R-D09 修复
- [[gua-091]] — 迁移出口
- [[concept-three-layer-decision-pipeline]] — 决策管线
- [[synthesis-v8-gua150-kaggle-milestone]] — 综合里程碑
