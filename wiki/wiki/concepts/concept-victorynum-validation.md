---
type: concept
title: "victoryNum 校验+fallback 概念"
sources:
  - docs/knowledge/platform-data-interpretation.md
tags:
  - victory-num
  - validation
  - fallback
  - batch
status: current
related_gua:
  - GUA-033
date: 2026-06-18
---

# victoryNum 校验+fallback 概念

## 4 席结构解读

```
victoryNum = [P0, P1, P2, P3]
              ↓   ↓   ↓   ↓
            0+2 一队、1+3 一队
```

- **[0] vs [1]** = 队级胜负（P0 队 vs P1 队）
- [2] = [0] 的冗余副本，[3] = [1] 的冗余副本
- **禁止四席相加**

## 三优先级校验

| 优先级 | 条件 | 处理 |
|--------|------|------|
| 1 | `[0]+[1]==batch_games` 且 `[0]==[2]` 且 `[1]==[3]` | 校验通过，采用 |
| 2 | 上述任一不等 | 走 fallback |
| 3 | `batch_games==1` 且 `curTimes==1` | fallback 认领 |

## fallback 详细语义

- **认领条件**：`batch_games==1`（单局批跑）且 `curTimes==1`（第 1 局）
- **`server_vn_raw` 字段**：保留服务器返回的原始数组（如 `[3,0,3,0]`）
- **`vn_source` 字段**：
  - `"server"` — 优先级 1 通过
  - `"fallback"` — 优先级 3 触发
- 写入文件：`batch_executor/latest_victory_num.json`

## 为什么需要 fallback

- v1006 exe 存在 4 席不一致 bug
- 单次会话固定 3 局（与 PDF 文档冲突）
- fallback 保证台账不丢局

## 关联

- wiki-minimax/entities/gua-033.md — 根因 GUA
- concept-exe-argv-clamp — exe argv 钳制
- [[concept-batch-evaluation]] — 批跑体系
- wiki/entities/module-batch-executor.md —
