```markdown
---
type: concept
title: "三层决策管线（Guard → Heuristic → validate）"
sources:
  - docs/guandan-brain/ITERATIONS.md
tags:
  - architecture
  - pipeline
  - v7
status: current
related_gua:
  - GUA-073
date: 2026-07-15
---

# 三层决策管线

## 架构

```
Layer 1: Guard (v7_guards.py)
  ↓
