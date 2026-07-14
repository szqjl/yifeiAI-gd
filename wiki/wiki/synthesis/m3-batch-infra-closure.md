---
type: synthesis
title: "M3 批跑基建（GUA-033）关闭后的下游影响"
sources:
  - docs/guandan-brain/issues/GUA-033-completion.md
  - docs/analysis/gua033-batch-matrix-2026-05-31.md
  - docs/guandan-brain/EVAL.md
tags:
  - synthesis
  - batch
  - infra
  - m3
  - v7-migration
status: current
related_gua:
  - GUA-033
date: 2026-06-17
---

# M3 批跑基建（GUA-033）关闭后的下游影响

## 背景

GUA-033 于 2026-05-31 正式 closed，标志着 M3 批跑基建（victoryNum / gameResult 解析、批末自检、backfill 范围）已沉淀为稳定规范。本综合页评估其对下游 EVAL 体系、批跑 KPI、V7 迁移的连锁影响。

## 下游影响清单

### 1. EVAL 体系（直接受益）

- [[EVAL-summary]] 共用 victoryNum / gameResult 解析逻辑
- 批末自检的 WARNING 路径已稳定，KPI 计算不再受「胜利数污染」干扰
- **结论**：GUA-033 关闭后，批跑评测体系 的胜率 KPI 可信度提升

### 2. 回归测试（直接受益）

- `gua033-batch-matrix-2026-05-31.md` 作为基准矩阵被持久保留
- 后续任何 victoryNum 解析改动都需对照该矩阵回归
- **结论**：基准矩阵成为后续 GUA（如 GUA-032 / GUA-034）批跑验证的参照物

### 3. 平台侧遗留（未解决）

- v1006 exe argv 限制（`settingTimes=3` 固定）属于平台问题
- 已记录但**未修复**
- **影响**：更换 exe 前，所有矩阵必须重跑
- **建议**：在 index 中标记「平台遗留问题」专项区

### 4. V7 NN 引擎迁移（待评估）

- V7 可能不再依赖 WebSocket `victoryNum`
- 当前 GUA-033 closed 仅针对 M3 批跑体系
- **风险**：
  - V7 若保留旧解析路径，可能继承 v1006 argv 限制
  - V7 若切换新解析路径，需重新建立 GUA-033 级别的解析规范
- **建议**：
  - [[handoff-2026-06-16-v7-dev-summary]] 中应明确 V7 的解析路径选择
  - 若 V7 切换路径，需新建 GUA-XXX-V7 跟踪

## 沉淀的通用规范

虽然 GUA-033 closed，以下规范可被任何后续引擎复用：

| 规范 | 内容 |
|------|------|
| 事件区分 | `gameOver` 早退不写 / `gameResult` 写 / `episodeOver` 禁误用 |
| 批末自检 | `victoryNum != batch_games` → WARNING + skip KPI |
| backfill 范围 | `[0]+[1]==batch_games` + 同队胜利数一致 |
| 批间清空 | `pending_result_files` 批间必须清空 |

**建议**：将上述规范写入 `wiki/concepts/batch-victorynum-parsing.md`（已完成），并在新引擎开发时作为基线参考。

## 行动项

1. [ ] V7 交接文档中明确解析路径选择（待办）
2. [ ] 平台遗留 v1006 argv 限制追踪（移交平台侧）
3. [ ] 后续 GUA 批跑验证统一对照 `gua033-batch-matrix-2026-05-31.md` 基准
4. [ ] 胜利数解析规范文档化（[[batch-victorynum-parsing]] 已建）

## 相关页面

- [[GUA-033]]：实体页
- [[GUA-033-completion-summary]]：完成定义
- [[batch-victorynum-parsing]]：解析规范概念
- [[EVAL-summary]]：EVAL 体系
- 批跑评测体系：批跑评测概念
- [[handoff-2026-06-16-v7-dev-summary]]：V7 交接
