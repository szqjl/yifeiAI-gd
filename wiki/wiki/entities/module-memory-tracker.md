```markdown
---
type: entity-module
title: "记忆追踪器（memory_tracker.py）"
sources:
  - docs/guandan-brain/ITERATIONS.md
tags:
  - module
  - memory
  - belief
status: current
related_gua:
  - GUA-072
date: 2026-07-15
---

# 记忆追踪器

## 文件
- `memory_tracker.py`

## 职责
**规则记牌引擎**，为 V7 提供 belief input：
- 已出牌追踪
- 剩余牌推断
- 队友/对手手牌估计

## 意义
打破 V7 NN 的**零信念决策**，让模型能看到"还剩什么牌"。

## 关联
- [[belief-input-rule-engine]] — 信念输入概念
- [[gua-072]] — 规则记牌引擎 GUA
```

---
