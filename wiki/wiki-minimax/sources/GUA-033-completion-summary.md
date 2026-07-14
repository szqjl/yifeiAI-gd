---
type: source-summary
title: "GUA-033 批末 victoryNum/gameResult 完工记录摘要"
sources:
  - docs/guandan-brain/issues/GUA-033-completion.md
tags:
  - gua-033
  - m3-engine
  - batch-validation
  - closed
status: current
related_gua:
  - GUA-033
  - GUA-061
date: 2026-06-17
---

# GUA-033 M3 批末 victoryNum / gameResult 完工记录摘要

## 概览

| 字段 | 值 |
|------|----|
| GUA 编号 | GUA-033 |
| 标题 | M3 批末 victoryNum / gameResult |
| 类型 | bug |
| 状态 | **closed** |
| 关闭日期 | 2026-05-31 |
| 关联矩阵 | gua033-batch-matrix-2026-05-31.md |

## 根因定音

**平台 v1006 exe 的 `settingTimes` 参数实测固定为 3**，与 PDF 说明书不一致——属于**离线 exe 实现缺陷**，仓库启动脚本无误。

> 口径冲突已定音：批跑统一使用 `batch_games` + `gameOver` fallback 兜底，不再依赖平台侧 `settingTimes` 透传。

## 修复要点

1. **批末自洽校验**：WebSocket 收到的 `[0]+[1]` 应等于 `batch_games`
2. **gameResult 累计**：按 3 局（局≠副）累计，禁止读 `episodeOver.result[4]`
3. **批间清空 `pending_result_files`**：防止跨批回填污染
4. **三条规则并存**：
   - `gameOver` 早退不写 `vn` / `gameResult`
   - 读 `final` 或 `vn`（择一来源）
   - 禁止 `episodeOver.result[4]`

## 关联原理

- `platform-data-interpretation.md §2` — 平台侧根因真源
- 「局 ≠ 副」— 批末自检的口径基础（已在 GUA-033 中定音）

## 交叉引用

- wiki-minimax/entities/gua-033.md — 实体页（已关单）
- [[batch-end-victory-num-validation]] — 批末校验概念页
- [[platform-data-interpretation]] — 平台数据解释
