---
type: query-answer
title: "governance 治理方案 文件目录结构"
date: 2026-06-18
sources:
  - concepts/gua-numbering-system.md
  - wiki/wiki-minimax/sources/AGENT_BOOTSTRAP-summary.md
  - wiki/wiki-minimax/sources/COMMANDER_NOTES-summary.md
  - sources/governance-docs-summary.md
  - sources/handoffs-2026-05-31-m-dev-push-governance-summary.md
  - concepts/agent-protocol.md
  - concepts/branch-strategy.md
  - concepts/handoff-pattern.md
  - concepts/v7-kpi-guardrails.md
  - sources/GUA-Index-summary.md
---

# governance 治理方案 文件目录结构

根据 Wiki 中关于"治理方案"的资料，整理如下：

## 治理方案文件目录结构

根据页面 [2] AGENT_BOOTSTRAP §3 和 [4] governance-docs 摘要，治理类文档分布在以下位置：

### 1. 顶层入口（`docs/guandan-brain/`）

| 文件 | 作用 | 状态 |
|---|---|---|
| `ISSUES.md` | GUA 缺陷池（GUA-001~061+） | current |
| `ITERATIONS.md` | 迭代记录 | current |
| `TASKS.md` | 任务清单 | current |
| `EVAL.md` | 评测入口 | current |
| `AGENT_BOOTSTRAP.md` | 新 Agent 启动指南（v7.1） | current |
| `AGENT_PUSH_CHECKLIST.md` | 推送前硬检查项 | current |
| `COMMANDER_NOTES.md` | M1 阶段历史笔记 | ⚠️ outdated |
| `V7-实施方案.md` | V7 引擎实施方案 | current |

### 2. 治理子目录（`docs/guandan-brain/governance/`）

| 文件 | 作用 |
|---|---|
| `M-V-Series-治理方案.md` | **M/V 系列治理**（M 与 V 分支的治理总则）[2] |

### 3. 治理迭代记录（`docs/guandan-brain/iterations/`）

| 文件 | 作用 | 关联 GUA |
|---|---|---|
| `governance-docs.md` | 治理文档迭代历史与维护规范 [1][4] | — |

### 4. MOC 索引（`docs/guandan-brain/MOCs/`）

| 文件 | 作用 |
|---|---|
| `GUA-Index.md` | GUA 全量索引（1~61 + V7-xxx）[10] |

### 5. Handoff 治理交接（`docs/analysis/handoffs/`）

典型治理类 handoff（2026-05-28 ~ 2026-06-01）：
- `2026-05-28-仓库整理方案执行中.md` — 基础设施维护 [8]
- `2026-05-31-m-dev-push-governance-compliance.md` — **M-Dev push 合规性治理** [5][8]
- `2026-05-31-M3-skills映射与组牌总纲.md` — 技术总纲 [8]
- `2026-06-01-gua036-control-wind-team.md` — 缺陷交接（GUA-036）[8]

---

## 治理体系的核心维度

从跨页面综合看，治理方案围绕以下几条主线展开：

1. **分支治理** — `v7-dev` ↔ `m-dev` 硬隔离，绝不可混推 [2][6][7]
2. **GUA 编号体系** — 所有缺陷/迭代挂载 GUA-xxx，全生命周期管理 [1]
3. **KPI 护栏** — "评估次数=0 即未实施"，30 局 ≥ 30% 队胜率硬门槛 [9]
4. **Agent 协议** — 第一句场景分流 + Commit 前缀 + Layer 2 禁入 Git [6]
5. **推送合规** — `scripts/hooks/pre_push_validate.py` 自动校验 [6][7]
6. **M/V 系列治理** — 解决 M1/M2/M3 与 V4/V5/V6/V7 的路线之争 [3]

---

## ⚠️ 信息缺口

- `docs/guandan-brain/governance/M-V-Series-治理方案.md` 的**具体文件结构和内部章节**未在 Wiki 中摘要 [4] 显示"待详细阅读源文件后补充"。
- `governance-docs.md` 迭代本身的**详细内容**也尚未抽取。

如需 M/V 系列治理方案的具体内容，建议直接查阅源文件 `docs/guandan-brain/governance/M-V-Series-治理方案.md`。
