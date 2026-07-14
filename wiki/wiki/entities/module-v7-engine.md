---
type: entity-module
title: "V7 胜率引擎模块（ultimate_win_rate_engine_v7）"
sources:
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
  - docs/guandan-brain/V7-实施方案.md
tags:
  - module
  - v7
  - engine
  - neural-network
status: current
related_gua:
  - GUA-022
  - GUA-014
  - GUA-050
date: 2026-06-17
---

# V7 胜率引擎模块

> V7 主迭代核心模块。AGENT_BOOTSTRAP 明确为 v7-dev 主引擎。详见 wiki/entities/engine-v7.md。

## 1. 模块组成

| 子模块 | 角色 |
|---|---|
| `ultimate_win_rate_engine_v7` | 引擎入口 |
| `yf1_v7.py` | 玩家 1 策略（双人配合的对家） |
| `yf2_v7.py` | 玩家 2 策略 |
| `v7_game_recorder.py` | 对局记录器（每副写 `game_records_v7/`） |
| `strategy_engine` | 策略调度中心 |
| `phase_handlers` | 阶段处理器（出牌/跟牌/接风） |
| `stage_router` | 阶段路由器 |
| `rule_based` | 兜底规则（NN 不确定时使用） |

## 2. 上下游关系

- **上游**：`train_bc_v7.py` 输出 `models/*.pth` → 引擎加载
- **下游**：`game_records_v7/` → 副级分析 → `analyze_v7_round_levels.py`
- **并行**：`yf1_m3` / `yf2_m3`（M3 旧版，m-dev 维护）

## 3. 关键文件

```
ultimate_win_rate_engine_v7/
├── __init__.py
├── yf1_v7.py
├── yf2_v7.py
├── strategy_engine.py
├── phase_handlers/
├── stage_router.py
├── rule_based/
└── v7_game_recorder.py
```

## 4. 评测脚本

- `scripts/launchers/v7/run_v7_vs_lalala_games.py`
- `test_v7_engine_load.py`（启动前自检）

## 5. 关联缺陷

- GUA-022 — `combine_handcards()` 修复
- GUA-014 — `choose_bomb()` 最小代价炸弹
- GUA-050 — `context` 字段补全

## 关联页面

- wiki/entities/engine-v7.md — 引擎总览
- [[branch-strategy]] — 分支策略
- [[data-directory-segregation]] — 数据隔离
- wiki-minimax/concepts/batch-evaluation.md — 评测体系
- [[GUA-022]] / [[GUA-014]] / [[GUA-050]]
```

---
