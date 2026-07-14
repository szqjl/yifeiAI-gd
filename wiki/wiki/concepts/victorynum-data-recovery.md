---
type: concept
title: "victoryNum 四层写入与数据恢复链"
sources:
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
  - docs/guandan-brain/EVAL.md
tags:
  - victorynum
  - data-recovery
  - gua-033
  - batch
status: current
related_gua:
  - GUA-033
date: 2026-06-17
---

# victoryNum 四层写入与数据恢复链

> AGENT_BOOTSTRAP §8 的详版展开，融合 GUA-033 fallback 决策与四层写入清单。

## 1. victoryNum 数据模型

- **类型**：四元组 `[p0, p1, p2, p3]`
- **队伍维度**：`0+2` vs `1+3`
- **更新粒度**：每副结束（`episodeOver`）
- **总累计**：`game_records/` 逐副流水

详见 wiki-minimax/concepts/batch-evaluation.md。

## 2. 四层写入清单

| 层级 | 位置 | 用途 | 写入时机 |
|---|---|---|---|
| L1 | `batch_executor/latest_victory_num.json` | 最新一局结果 | 每局结束 |
| L2 | `logs/v7_vs_lalala_*.log` | 人类可读 | 实时 |
| L3 | `v7_vs_lalala_scores.json` | 累计 | 每局结束 |
| L4 | `game_records_v7/` | 逐副流水 | 每副结束 |

> **注意**：L2 与 L4 是 Layer 2，不进 Git（见 [[agent-protocol]]）。

## 3. server_vn_raw vs 采用值

- **`server_vn_raw`**：服务端 WebSocket 推送的原始值
- **采用值**：本地 `executor` 解析后写入 `latest_victory_num.json` 的值
- **差异来源**：网络丢包 / 解析失败 / 进程重启
- **fallback 触发条件**：server 值缺失或不合法

## 4. vn_source 标记

`latest_victory_num.json` 中应包含 `vn_source` 字段：

```json
{
  "victory_num": [2, 1, 2, 1],
  "vn_source": "server"  // 或 "fallback"
}
```

## 5. 双重数据通道

| 通道 | 内容 | 可靠性 |
|---|---|---|
| WebSocket | 实时 `episodeOver` 事件 | 高（首选） |
| stdout | 进程输出兜底 | 中（fallback） |

## 6. GUA-033 关联

GUA-033（"exe N 局 vs N 副" 口径）已定音：**`--target-games` = 局数，须为 3 的倍数**。
- 1 局 = 多副（实测 N=1 局 → 59 副）
- 任何数据恢复操作必须按"局"粒度解释 victoryNum

## 关联页面

- [[AGENT_BOOTSTRAP-summary]]
- wiki-minimax/concepts/batch-evaluation.md
- [[GUA-033]]
- [[data-directory-segregation]]
- wiki/entities/module-batch-executor.md
```

---
