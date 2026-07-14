---
type: query-answer
title: "analyze_v7_rounds 批跑局级副级分析脚本 末级分布 victoryNum 统计"
date: 2026-06-19
sources:
  - synthesis/m3-batch-infra-closure.md
  - queries/query-0618-2149-v-批跑数据统计-局级-副级.md
  - concepts/batch-victorynum-parsing.md
  - sources/GAME_RECORD_VICTORYNUM_CHECK-summary.md
  - wiki/wiki-minimax/sources/GUA-033-completion-summary.md
  - concepts/dual-data-channel-recovery.md
  - concepts/victorynum-data-recovery.md
  - queries/query-0619-0826-批跑脚本-命令-参数-批跑入口-batch-executor.md
  - sources/source-platform-data-interpretation-summary.md
  - entities/module-batch-executor.md
---

# analyze_v7_rounds 批跑局级副级分析脚本 末级分布 victoryNum 统计

# `analyze_v7_rounds` 批跑局级副级分析脚本 · 末级分布 victoryNum 统计

## ⚠️ Wiki 信息覆盖度评估

针对「**`analyze_v7_rounds` 末级分布 victoryNum 统计**」这一精确子问题，Wiki 中**没有直接的脚本实现细节**（如具体函数、字段映射、输出 schema）。但可从周边知识拼出完整上下文。

---

## 一、脚本定位（局级 vs 副级）

| 粒度 | 工具 | 路径 | 必走？ |
|------|------|------|--------|
| **局级** | `analyze_v7_rounds.py` | `scripts/launchers/v-nn/` | 否 |
| **副级** | `analyze_v7_round_levels.py` | `scripts/launchers/v-nn/` 或 `scripts/tools/` | **V7 必走** |

**核心原则**：V7 批跑分析**必须同时跑两套**，避免「局 ≠ 副」统计陷阱。[{2}]

```bash
# 局级
python scripts/launchers/v-nn/analyze_v7_rounds.py results/xxx/

# 副级（局 ≠ 副口径校验，curRank 分组）
python scripts/tools/analyze_v7_round_levels.py \
  --records game_records_v7/ \
  --output reports/v7_round_analysis.csv
```

---

## 二、victoryNum 在局级脚本中的角色

### 数据结构

- **类型**：四元组 `[P0, P1, P2, P3]`
- **队伍维度**：`0+2` 一队 vs `1+3` 一队
- **批跑只读 `[0] vs [1]`**（禁止四席相加）
- `[2]`, `[3]` 是冗余副本，与 `[0]`, `[1]` 一致 [{9}]

### 局级 victoryNum 含义

- **`gameResult.victoryNum`**：本局升级数（0/1/2/3，**局级**）
- 而 **`act.stage.play.curRank`**：当前**副**的 rank（副级，跨副重置）[{8}]
- 1 局 = 多副（实测 N=1 局 → 59 副）[{7}]

### 末级分布（局级统计）的口径

「末级分布」通常指 victoryNum 取值 0/1/2/3 的频次：

| victoryNum | 含义 | 常见于 |
|------------|------|--------|
| 0 | 本局未升级 | 劣势局 |
| 1 | +1 级（如 2→3）| 标准局 |
| 2 | +2 级（如 2→4）| 大胜局 |
| 3 | 双上 / 过 A | 完胜局 |

---

## 三、Wiki 中可见的相关数据

| 指标 | 数值 | 来源 |
|------|------|------|
| V7 vs lalala 副级胜率 | **3.0%** | [{2}] |
| 30% 门槛（跨越目标） | — | [{2}] |
| 胜率目标 | >90% (PHASE3) / >50% (旧) | [{2}] |

> Wiki **未记录** victoryNum=0/1/2/3 的末级分布明细，也未记录局数/副数/种子/时间戳。

---

## 四、关键校验三优先级（影响 victoryNum 统计）

源自 GUA-033 解析规范 [{3}][{9}]：

| 优先级 | 条件 | 处理 |
|--------|------|------|
| **P1** | `[0]+[1]==batch_games` 且 `[0]==[2]` 且 `[1]==[3]` | 校验通过 |
| **P2** | 任一不等 | 走 fallback |
| **P3** | fallback 仅在 `batch_games==1` 时认领 `curTimes==1` | 特殊场景 |

**批末自检**：`victory_num != expected_victory_num(batch_games)` → WARNING + **skip KPI** [{3}]

---

## 五、`vn_source` 标记（影响「采用值」追溯）

`latest_victory_num.json` 应含：

```json
{
  "victory_num": [2, 1, 2, 1],
  "vn_source": "server"  // 或 "fallback"
}
```

- **`server_vn_raw`**：WebSocket 推送原始值
- **采用值**：本地 executor 解析后写入的值
- **差异来源**：网络丢包 / 解析失败 / 进程重启 [{7}]

---

## 六、四层写入清单（数据源视角）

| 层级 | 位置 | 写入时机 |
|------|------|----------|
| L1 | `batch_executor/latest_victory_num.json` | 每局结束 |
| L2 | `logs/v7_vs_lalala_*.log` | 实时（不进 Git） |
| L3 | `v7_vs_lalala_scores.json` | 每局结束 |
| L4 | `game_records_v7/` | 每副结束 |

> 任何末级分布统计都应**优先核对 L1 与 L4 一致性**。[{7}]

---

## 七、信息缺口（Wiki 未覆盖）

| 缺口 | 影响 |
|------|------|
| `analyze_v7_rounds.py` 的具体函数 / 字段 | 无法直接看代码 |
| 末级分布的输出 schema（CSV/JSON 列名） | 需查源码 |
| victoryNum=0/1/2/3 在 V7 批跑中的实测频次 | 无数据 |
| 局级 vs 副级 victoryNum 含义差异的代码处理 | 需查源码 |
| 随机种子与可复现性 | Wiki 未记录 |

---

## 八、建议下一步

1. **查源码**：`scripts/launchers/v-nn/analyze_v7_rounds.py` 内 `victoryNum` 字段的聚合逻辑
2. **跑一次新批跑** + 输出末级分布 CSV：`analyze_v7_rounds.py results/xxx/ --output dist.csv`
3. **建立归档**：把 `victoryNum` 末级分布 + 配置 + 局/副数 + 种子 一起落盘到 `docs/analysis/batch-runs/`
4. **GUA-033 规范对齐**：末级分布若要进 KPI，必须先过批末自检（`victory_num != batch_games` → skip）

---

## 关联页面

- [{1}] M3 批跑基建关闭后的下游影响
- [{2}] v7 批跑数据统计 局级 副级
- [{3}] 批末 victoryNum 解析（**核心规范**）
- [{7}] victoryNum 四层写入与数据恢复链
- [{8}] 批跑执行器全景
- [{9}] 平台数据解读摘要
- [[GUA-033]] 实体页
- 批跑评测体系 概念页
