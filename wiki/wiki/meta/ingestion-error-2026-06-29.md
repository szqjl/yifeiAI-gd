---
type: meta
title: "摄入异常记录 - 2026-06-29"
sources:
  - docs/guandan-brain/README.md
  - docs/guandan-brain/SCRIPT_INDEX.md
  - docs/guandan-brain/v7-win-rate-history.md
  - docs/guandan-brain/工作流.md
tags:
  - ingestion-error
  - ops
status: current
date: 2026-06-29
---

# 摄入异常记录 - 2026-06-29

## 现象

本次批次（4 个源文件）上游分析器返回：

```
error: "unmatched braces"
```

导致 `key_entities`、`key_concepts`、`connections` 均为空数组。

## 影响

- 本次未生成任何 `entity-*`、`concept-*`、`synthesis-*` 页面。
- 仅产出 4 个 `source-summary` 占位骨架。
- 所有跨文件交叉引用暂未建立。

## 受影响文件

| 文件 | 字符数 | 摘要页 | 状态 |
|------|--------|--------|------|
| `docs/guandan-brain/README.md` | 6389 | [[README-summary]] | 骨架 |
| `docs/guandan-brain/SCRIPT_INDEX.md` | 9598 | [[SCRIPT_INDEX-summary]] | 骨架 |
| `docs/guandan-brain/v7-win-rate-history.md` | 13775 | [[v7-win-rate-history-summary]] | 骨架 |
| `docs/guandan-brain/工作流.md` | 6399 | [[工作流-summary]] | 骨架 |

## 后续动作

1. **优先**：定位上游分析器 `unmatched braces` 报错（疑似源文件中含未配对 `{` `}`）。
2. 重跑分析 4 个源文件，补充实体/概念清单。
3. 基于重跑结果补全每个 `source-summary` 的「关键内容 / 待补字段」章节。
4. 视情况创建：
   - `entity-engine/engine-v7.md`
   - `concept/batch-evaluation.md`
   - `synthesis/v7-current-state.md`

## 建议排查入口

- `v7-win-rate-history.md`（13775 字符，最大嫌疑）中的胜率表格 / 进度条 / 数学公式
- `SCRIPT_INDEX.md` 中的 Python f-string / dict 字面量

> 本次摄入未影响 `index.md` / `overview.md` / `log.md` 的结构正确性。
