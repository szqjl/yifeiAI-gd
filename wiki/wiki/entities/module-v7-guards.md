```markdown
---
type: entity-module
title: "V7 守门模块（v7_guards.py）"
sources:
  - docs/guandan-brain/ITERATIONS.md
tags:
  - module
  - guards
  - v7
status: current
related_gua:
  - GUA-073
date: 2026-07-15
---

# V7 守门模块

## 文件
- `v7_guards.py`

## 职责
**Layer 1 硬排除** — 在 Heuristic 之前排除非法/危险选项：
- 同花顺/三连对/顺子的 A→2 包接检查
- 队友保护（弱角色时不出大）
- 牌型合法性

## 关联
- [[three-layer-decision-pipeline]] — 三层决策
- [[gua-073]] — 管道整理 GUA
```

---
