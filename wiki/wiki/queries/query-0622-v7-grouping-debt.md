---
type: query-answer
title: "V7 组牌引擎当前债：GUA-054/062/072/079/080/077 关系图"
status: current
date: 2026-06-22
sources:
  - docs/guandan-brain/issues/GUA-080-completion.md
  - docs/guandan-brain/playbooks/PB-001-gua072-bomb-break-timing.md
  - docs/guandan-brain/工作流.md
tags:
  - query
  - v7
  - grouping-engine
related_gua:
  - GUA-054
  - GUA-062
  - GUA-072
  - GUA-079
  - GUA-080
  - GUA-077
  - GUA-061
related_playbook: PB-001
---

# 查询：V7 组牌引擎当前债全景

## 问题

V7 组牌引擎当前的「债」有哪些？它们之间的关系是什么？下一步该做哪个？

## 回答

### 全景图（6 个 GUA + 1 个 Playbook）

```
                ┌─────────────────────────────────────┐
                │   GUA-061：engine 24 维主路径        │
                │   （目标态，open）                    │
                └────────────────┬────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
┌───────────────┐       ┌─────────────────┐      ┌─────────────────┐
│ GUA-054       │       │ GUA-062         │      │ GUA-077         │
│ scanner 9 维  │       │ 组牌 v2 基线    │      │ 多步规划        │
│ （基线债）    │       │ （基线）        │      │ （sprint 资源）  │
│ open          │       │                 │      │                 │
└───────────────┘       └─────────────────┘      └─────────────────┘
        │
        │ 降级路径（受 R-G080-4 约束）
        ▼
┌─────────────────────────────────────────────────────────────┐
│ GUA-080：中炸 vs 三连对
