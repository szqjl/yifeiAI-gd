# docs/analysis/archive · 归档目录

> **2026-06-29 起启用**：沉淀已闭环的 analysis 草稿（一次性观测、debug 报告、根因排查）。
> 位于 docs/analysis/ 主目录的文档是**当前活跃**；这里的文档是**历史归档**。

---

## 归档规则

**何时归档**（满足任一）：
- 对应的 ISSUES / GUA 已 closed
- 文档是一次性观测（如 "观测报告"、"根因排查"）
- 文档仅供某次 handoff 上下文（handoff 完成后）

**何时不归档**（留在主目录）：
- 长期生效的 analysis（如 gua-048-根因复盘-2026-06.md —— 复盘模板）
- 跨迭代复用的方法论（如 数据恢复链分析.md）
- agent session 流水（gent-sessions/ 单独目录，不进 archive）

**命名约定**：
- 沿用原文件名（保留可追溯）
- handoff 类按 YYYY-MM-DD-<topic>.md

---

## 当前归档清单

### GUA 闭环关联
- 2026-06-18-gua062-batch-eval.md — GUA-062 批跑评估（已 closed）
- 2026-06-21-cardmask-dict-collision.md — cardmask 字典冲突排查（已 closed）

### 一次性观测
- 南邮离线平台-actionList候选缺失观测报告.md — 平台 actionList 行为观测
- 批跑cmd窗口观察.md — 批跑 UI 行为观察
- level2-root-cause.md — Layer 2 数据根因排查

---

## 配套归档

- scripts/analysis/archive/ — 一次性 debug 脚本（trace_*, verify_*）
- 主目录 scripts/analysis/ 保留：analyze_*, compare_*, simulate_* 等**长期复用**脚本
