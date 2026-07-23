```markdown
---
sources:
  - docs\guandan-brain\v8-win-rate-history.md
  - docs\analysis\WF-12-20260716222448436062-副12-yf1-Q1让道决策分析.md
type: meta
title: "Wiki 索引"
date: 2026-07-21
status: current
---

# Wiki 索引

## P0 活跃缺陷

- [[gua-150]] — self_sprint 让道误判（R-D09，**12 局实战中双上率下降待二次观察**）
- [[gua-151]] — match_key 碰撞 / V8 完成检测（已修，**多 launcher 累计边界由 GUA-155 覆盖**）
- [[gua-154]] — 重复牌串跨组归属（**12 局实战零退化**）
- [[gua-155]] — **多 launcher 累计战绩（已修复，pytest 6/6）**

## 引擎

- [[engine-v8]] — OpenGuanDan 迁移主迭代（**当前最新 KPI: 12 局 83.3%**）
- [[engine-v7]] — V8 内部使用 `ultimate_win_rate_engine_v7.py`
- [[engine-m3]] — M3 规则引擎（frozen）

## 核心模块

- [[module-v7-guards]] — 守门层（GUA-135/150 self_sprint 关键改动）
- [[module-grouping-engine]] — 组牌引擎（GUA-154 跨组归属）
- [[module-batch-executor]] — 批跑执行器（GUA-155 多 launcher 累计）

## 核心概念

- [[batch-evaluation]] — 批跑评测体系
- [[v8-win-rate-governance]] — V8 KPI 治理（**已加入 GUA-155 规则**）
- [[self-sprint-priority]] — **新概念** self_sprint 意图层
- [[multi-launcher-score-aggregation]] — **新概念** 多 launcher 累计战绩
- [[three-layer-decision-pipeline]] — 三层决策管线
- [[recorder-bug]] — 胜负判定

## GUA 全生命周期

### R-D09（新分类）

- [[gua-150]] — self_sprint 让道误判

### V8 迁移序列

- [[gua-135]] — self_sprint 让道（语义升级前）
- [[gua-149]] — PASS 僵死修复
- [[gua-150]] — self_sprint 让道误判
- [[gua-151]] — match_key 碰撞
- [[gua-152]] — 平局计数
- [[gua-153]] — 双重计数
- [[gua-154]] — 重复牌串跨组归属
- [[gua-155]] — 多 launcher 累计战绩

## 综合分析

- [[synthesis-v7-current-state]] — **当前标题更新为 V8 当前状态**

## 真源

- [[sources/v8-win-rate-history-summary|v8-win-rate-history]] — **当前 12 局实战 KPI 真源**
- [[sources/ISSUES-summary|ISSUES]]
- [[sources/ITERATIONS-summary|ITERATIONS]]

## 查询归档

- [[WF-12-20260716-self-sprint-misjudgment]] — **副 12 yf1 Q1 让道决策根因诊断**

## 当前 P0 关注

1. **yf2 末游率 41.0% 异常** → WF-12 复盘 3~5 副
2. **双上率从 26.2% 下降到 17.5%** → 双跑视角下观察 1st/2nd 名次分布
3. **GUA-155 修复验证** → next run：scores.json 应累计 12 局
4. **CCN Phase 0 数据预热** → 171 副已超 Day 0 目标 200+，但多样性单一（仅 lalala）
