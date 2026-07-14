---
type: source-summary
title: "GUA-033 完成定义摘要"
sources:
  - docs/guandan-brain/issues/GUA-033-completion.md
  - docs/analysis/gua033-batch-matrix-2026-05-31.md
tags:
  - gua
  - m3
  - batch
  - infra
  - closed
status: current
related_gua:
  - GUA-033
  - GUA-032
  - GUA-034
date: 2026-06-17
---

# GUA-033 完成定义摘要

## GUA 元信息

| 字段 | 值 |
|------|-----|
| 编号 | GUA-033 |
| 标题 | M3 批末 victoryNum / gameResult |
| 类型 | infra / batch |
| 状态 | **closed**（2026-05-31） |
| 范围 | M3 |
| 证据 | `gua033-batch-matrix-2026-05-31.md` |

## 关键概念

### 批末自检（victoryNum vs batch_games）

客户端 / executor 批末自检，不一致则 WARNING + 不计胜率。

### gameOver / gameResult / episodeOver 区分

- `gameOver`：早退，不写 victoryNum
- `gameResult`：读 final / victoryNum
- **禁止**从 `episodeOver` 误用 `result[4]`

### backfill 范围

- 仅在本批 `[0]+[1]==batch_games` 且同队 `[0]=[2], [1]=[3]` 时 backfill
- 批间清空 `pending_result_files`

### v1006 exe argv 限制（平台侧）

- `windows/` 目录无 ini/json 覆盖 argv
- argv 1/3/10 均为 `settingTimes=3`，会话固定 3 平台局
- 属于**平台问题**，非代码缺陷

## 关联概念

- 批跑评测体系：GUA-033 是批跑基建核心
- 批末 victoryNum 解析：GUA-033 确立的解析规范

## V7 迁移说明

- 状态：M3 批跑体系已 closed
- V7 NN 引擎可能不再依赖 WebSocket `victoryNum`
- 当前 closed 仅针对 M3 批跑体系

## 相关页面

- [[GUA-033]]：实体页（根因 + 平台侧限制 + 验收标准）
- M3 批跑基建关闭后的下游影响：综合分析

## 备注

本文档为 GUA-033 完结定义，原文 2032 字符，是三个 GUA completion 文档中信息量最大的一份。
