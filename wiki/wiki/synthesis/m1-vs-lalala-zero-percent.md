---
type: synthesis
title: "M1/M2/M3 vs lalala 0% 胜率跨版本根因综合"
sources:
  - docs/analysis/agent-sessions/04-guandan-mechanics.md
  - docs/analysis/agent-sessions/05-root-cause-analysis.md
  - docs/analysis/agent-sessions/06-game-data-analysis.md
  - docs/analysis/agent-sessions/07-p0-implementation-verification.md
  - docs/analysis/agent-sessions/batch30_p0_trigger_vs_winrate_20260528.md
tags:
  - synthesis
  - root-cause
  - cross-version
status: current
related_gua:
  - GUA-001
  - GUA-002
  - GUA-003
  - GUA-004
  - GUA-005
  - GUA-006
date: 2026-05-28
---

# M1/M2/M3 vs lalala · 0% 胜率跨版本根因综合

## 现状（截至 2026-05-28）

| 版本 | 对 lalala 胜率 | 状态 |
|------|---------------|------|
| M1 | 0% | P0 改进已实施，20 局验证 0 胜 |
| M2 | 0% | 已被 M3 替代 |
| M3 | 0% | 5 大 Bug 已诊断，P0-⑤ 修复未验证 |
| V5 | 未测 | 待 P0-④ 激活 |
| V6 | 未测 | — |
| V7 | 未测 | NN 引擎方向 |

## 关键证据

### 22 副对局完赛名次

- **lalala**：100% 双上（头游 + 二游）
- **M3/M1**：0% 双上（总拿三游 + 末游）

### 战略三层

- **Lv1 改动**：PHASE2 50+ 处代码，0% 胜率 → Lv1 假设证伪
-
