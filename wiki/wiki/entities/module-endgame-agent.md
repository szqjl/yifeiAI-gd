---
type: entity-module
title: "check_endgame_agent 残局 Agent"
sources:
  - docs/guandan-brain/SCRIPT_INDEX.md
  - docs/guandan-brain/v7-win-rate-history.md
tags:
  - module
  - endgame
  - agent
  - memory-tracker
status: current
related_gua:
  - GUA-078
date: 2026-06-29
---

# check_endgame_agent 残局 Agent

## 身份

- **核心文件**：`check_endgame_agent.py`
- **三种模式**：独立（standalone）/ 扫描（scan）/ 单记录（single --record）
- **配套**：`MemoryTracker`（带 `decide` 入口，对应管线 ①b）

## 关键数字

| 指标 | 数值 |
|------|------|
| **激活** | **603 / 913 ≈ 66.0%** |
| **Q 命中率** | **36.5%** |
| **端局残局胜率贡献** | **几乎为 0** |

## 关键观察

- 残局 Agent 激活率高（66%），覆盖了大量终局局面
- 但 Q 表命中率仅 36.5%
- **端局残局胜率贡献几乎为 0** → 关键瓶颈
- 残局是单回合决策，理论上更易学，但实战未转化为副胜

## 管线入口

```
MemoryTracker.decide (①b)   # 残局决策入口
  → Q 表查询
    → heuristic 兜底（GUA-075 ③b/③c）
      → 残局输出
```

## 关联 GUA

- **GUA-078**：残局管线（具体内容待补）

## 链接

- V7 引擎：[[engine-v7]]
- 残局 vs 全局：[[synthesis-v7-current-state]]
- heuristic vs BC：[[heuristic-vs-bc]]
