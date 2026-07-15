```markdown
---
type: meta
title: "Wiki 操作日志"
sources: []
tags:
  - meta
  - log
status: current
date: 2026-07-15
---

# Wiki 操作日志

## 2026-07-15 — 第二批摄入

**触发源**：docs/guandan-brain/v8-win-rate-history.md + ITERATIONS.md

**新增页面**：
- `wiki/sources/v8-win-rate-history-summary.md`
- `wiki/sources/ITERATIONS-summary.md`
- `wiki/entities/engine-v8.md`
- `wiki/entities/module-grouping-engine.md`
- `wiki/entities/module-v7-guards.md`
- `wiki/entities/module-memory-tracker.md`
- `wiki/entities/module-bc-trainer.md`
- `wiki/concepts/v8-win-rate-governance.md`
- `wiki/concepts/bc-argmax-collapse.md`
- `wiki/concepts/grouping-engine-v2.md`
- `wiki/concepts/card-mask-is-core.md`
- `wiki/concepts/three-layer-decision-pipeline.md`
- `wiki/concepts/belief-input-rule-engine.md`
- `wiki/concepts/recorder-bug.md`
- `wiki/synthesis/v7-current-state.md`

**更新页面**：
- `wiki/purpose.md`（V7+ / V8 并行表述）
- `wiki/overview.md`（V8 状态、argmax 瓶颈、副胜率方差）
- `wiki/index.md`（各 section 补全）
- `wiki/concepts/batch-evaluation.md`（V8 阈值表）

**关键决策**：
- GUA-064 argmax collapse 标记为 V7 BC 路线硬瓶颈
- V8 评估基线 = 30 局 ≥ 30%
- 副胜率统计意义门槛 = ≥9 局
```

---
| 2026-07-15 10:56 | ingest | docs\guandan-brain\v8-win-rate-history.md, docs\guandan-brain\ITERATIONS.md |
