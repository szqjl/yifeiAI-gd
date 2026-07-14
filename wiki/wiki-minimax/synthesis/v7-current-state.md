---
type: synthesis
title: "V7 引擎当前状态综合"
sources:
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
  - docs/guandan-brain/AGENT_PUSH_CHECKLIST.md
  - docs/guandan-brain/COMMANDER_NOTES.md
tags:
  - synthesis
  - v7
  - status
  - nn
status: current
related_gua:
  - GUA-022
  - GUA-033
date: 2026-06-17
---

# V7 引擎当前状态综合

## 一句话状态
**V7 NN 引擎已接入 Wiki 工具链（v7.2），与 M3 在 `v7-dev` / `m-dev` 双线并行；`batch_executor` 进程管理 2026-05-22 已修复；GUA-022 根因隔离完成，下一步进入 P0 代码改动。**

## 当前里程碑

| 维度 | 状态 |
|------|------|
| Wiki 接入 | ✅ v7.2 完成（`scripts/wiki.py`） |
| 分支隔离 | ✅ `v7-dev` / `m-dev` 独立运行 |
| 进程管理 | ✅ `TrackedClientProcess` 已修复（2026-05-22） |
| 副级分析 | ✅ `analyze_v7_round_levels.py` 上线 |
| 数据通道 | ✅ WebSocket + stdout 双通道 + 四层写入 |
| P0 代码改动 | ⏳ 待执行（choose_bomb/context/combine） |

## 关键决策链

### 决策 1：M3 已瓶颈，转 V7
- M3 规则引擎架构天花板
- V7 NN 引擎是突破关键
- 实验线隔离避免互相污染

### 决策 2：GUA-022 非根因
- T7/T8/T9 全 0% → 排除 combine_handcards
- 下一步：choose_bomb/context/combine 三件套

### 决策 3：胜率目标升级
- 旧：>50% (COMMANDER_NOTES #5)
- 新：>90% (PHASE3 2026-05-24)
- ⚠️ 需确认是否仍以 M1 为主线

## 关键文件

| 类别 | 路径 |
|------|------|
| 引擎入口 | `src/decision/ultimate_win_rate_engine_v7.py` |
| 客户端 | `yf1_v7.py` / `yf2_v7.py` |
| 批跑脚本 | `scripts/launchers/v7/run_v7_vs_lalala_games.py` |
| 数据目录 | `game_records_v7/` |
| 分析工具 | `scripts/tools/analyze_v7_round_levels.py` |

## 工具链全景

| 工具 | 作用 |
|------|------|
| `scripts/wiki.py` | LLM Wiki 知识图谱 |
| `scripts/tools/yf_replay.py` | 牌谱回放 |
| `scripts/tools/analyze_v7_round_levels.py` | 副级分析 |
| `scripts/hooks/pre_push_validate.py` | 推送门控 |
| `batch_executor` | 批量对局执行 |

## 下一步行动

1. **P0 代码改动**：choose_bomb → context → combine_handcards
2. **测试矩阵**：用 T1-T9 矩阵验证
3. **批跑验证**：12 局 vs lalala
4. **目标确认**：M1 vs lalala >90% 是否仍主线

## 关联页面
- wiki/entities/engine-v7.md / wiki-minimax/entities/engine-m3.md
- [[gua-022]] / wiki-minimax/entities/gua-033.md
- [[agent-bootstrap-workflow]]
- [[wiki-system]]
- [[branch-isolation]]
- [[dual-data-channel]]
- wiki-minimax/concepts/batch-evaluation.md
- [[code-quality-gate]]
- [[tool-batch-executor]] / [[tool-analyze-v7-round-levels]]
