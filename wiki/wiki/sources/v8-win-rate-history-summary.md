```markdown
---
type: source-summary
title: "V8 局胜率历史（4 批跑详析）"
sources:
  - docs/guandan-brain/v8-win-rate-history.md
tags:
  - v8
  - kpi
  - batch-run
  - win-rate
  - gua-150
  - gua-151
  - gua-152
  - gua-153
  - gua-154
  - gua-155
status: current
related_gua:
  - GUA-150
  - GUA-151
  - GUA-152
  - GUA-153
  - GUA-154
  - GUA-155
date: 2026-07-21
---

# V8 局胜率历史（4 批跑详析）

## 概述

本文是 V8 引擎（OpenGuanDan 迁移主迭代）的**批跑 KPI 真源**，覆盖 2026-07-18 至 2026-07-21 共 4 批次离线对局，从 GUA-150 self_sprint 让道修复后的首跑开始，逐步扩展样本、引入实战回归。

## 4 批跑时间线

| 批次 | 日期 | GUA 节点 | 样本 | 局胜率 | 关键事件 |
|------|------|----------|------|--------|----------|
| B1 | 2026-07-18 | GUA-150 修复首跑 | 6 局 | 4/6 (66.7%) | self_sprint 让道语义升级 |
| B2 | 2026-07-18 | GUA-151/152/153 修复 | 73 副 | n/a（卡顿归零） | scores.json 正常化 |
| B3 | 2026-07-18 | GUA-151/152/153 小样本 | 9 局 | 100% | 样本巧合 |
| B4a | 2026-07-21 | GUA-154 验证 | 3 局 | 100% | Trips/StraightFlush 跨组修复 |
| B4b | 2026-07-21 | GUA-154 实战回归 | 12 局 / 171 副 | 83.3% | yf2 末游率 41.0% 暴露 |

## B4b（12 局）实战 KPI 详析

### 总成绩

- **局胜率**：10/12 = 83.3%（vs lalala）
- **副数**：171 副全部完成，零卡顿
- **队友**：yf1_v8 / yf2_v8 主队

### 队员 KPI 拆解

| 指标 | yf1_v8 | yf2_v8 | 差异 |
|------|--------|--------|------|
| 头游率 | 较高 | 较低 | — |
| 末游率 | 24.6% | **41.0%** ⚠️ | +16.4pp |
| 双上率 | — | — | 17.5%（-8.7pp vs 上批） |
| 双下率 | — | — | — |

### 异常观察

1. **yf2 末游率 41.0% 异常偏高**
   - 比 yf1 高 16.4pp
   - 比上批 yf2 (28.3%) 高 12.7pp
   - 候选根因：GUA-078 残局 PASS 劫持在 yf2 视角覆盖不全 / yf2 策略偏保守 / 与 yf1 抢权冲突
   - 见 [[WF-12-20260716-self-sprint-misjudgment|WF-12 副 12 根因诊断]]

2. **双上率从 26.2% 下降到 17.5%（-8.7pp）**
   - 可能与 GUA-150 self_sprint 让道修复相关
   - yf1 抢权 vs yf2 抢权冲突需进一步观察 1st/2nd 名次分布

### 关键反扑

- Lalala 在会话 6 和 12 反扑成功（lalala 胜 2 局）
- 真实水平回归：83.3% 而非 100%
- 3 局 100% 是统计巧合，样本量不足

## 数据真源辨析

### 局 ≠ 副 口径

- `executor.completed_games` 与 `scores.json` 只反映**最后 launcher**
- `analyze_v7_rounds.py` L4 累计识别存在系统性偏差
- [[GUA-155]] 修复了"多 launcher 累计战绩"问题
- 多 launcher 累计真源 → [[analyze_v7_rounds.py]] L4 重放

### scores.json 三件套

`scores.json` 包含 `team_a_wins / team_b_wins / draws / total_games`。

**故障历史：**
- GUA-152 平局计数遗漏 → 已修复
- GUA-153 双重计数 → 已修复
- GUA-155 多 launcher 累计（executor L942 加载后 L956-960 立即重置）→ 已修复

### OpenGuanDan 数据通道

- stdout **不输出** gameResult
- `latest_victory_num.json` 不存在
- **牌谱 JSON 是唯一胜负真源**
- 6 客户端日志，898 条实例分配（GUA-154 12 局验证）

## GUA 迭代串联

```
GUA-150 (R-D09 self_sprint 语义)
   ↓
GUA-151 (match_key 碰撞)
GUA-152 (平局计数)
GUA-153 (双重计数)
   ↓
GUA-154 (重复牌串跨组归属 — R-G080-4 零退化)
   ↓
GUA-155 (多 launcher 累计战绩 — 新登记)
   ↓ (发现于 GUA-154 12 局回归)
```

## 修复版数据集（按时间）

1. `philsz/guandan-v8-game-records-184-episodes` — 修复前
2. `philsz/guandan-v8-records-post-fix-73eps` — 修复后 73 副
3. `philsz/guandan-v8-records-9-games-post-fix` — 9 局验证
4. `philsz/guandan-v8-records-12-games` — 12 局实战回归

## 关联页面

- [[gua-150]] — self_sprint 让道误判（R-D09）
- [[gua-151]] — match_key 碰撞
- [[gua-152]] — 平局计数
- [[gua-153]] — 双重计数
- [[gua-154]] — 重复牌串跨组归属
- [[gua-155]] — 多 launcher 累计战绩
- [[self-sprint-priority]] — self_sprint 意图层概念
- [[multi-launcher-score-aggregation]] — 多 launcher 累计设计模式
- [[WF-12-20260716-self-sprint-misjudgment]] — 副 12 根因诊断
- [[engine-v8]] — V8 引擎实体
- [[v8-win-rate-governance]] — V8 KPI 治理
- [[batch-evaluation]] — 批跑评测体系

## 关键 quote

> 局 ≠ 副 是数据解读的核心口径问题，已定音但需持续强调。
> 牌谱 JSON 是唯一胜负真源。
