# src/m — M 系列目录

> Phase 2（2026-05-29）：**M1 核心模块已物理迁入 `m/m1/`**；`src/decision/` 保留兼容 shim。

## 子目录

| 路径 | 内容 | 物理位置 |
|------|------|----------|
| `m/platform/` | 通信、记录、WebSocket、常量 | `src/communication/`、`src/game_logic/`（re-export） |
| `m/m1/` | M1 路由 + 阶段处理器 + 策略引擎 | **`src/m/m1/*.py`** |
| `m/m2/` | M2 引擎 | `src/decision/rule_based_decision_engine_m2.py`（待迁入） |
| `m/m3/` | M3 引擎 + 契约适配 | `src/decision/m3_decision_engine.py` + `M3DecisionProvider` |

### `m/m1/` 已迁入模块

`stage_router`、`phase_handlers`、`intelligent_router`、`rule_based_decision_engine_m1`、`strategy_engine`、`enhanced_priority_system`、`history_tracker`、`endgame_planner`、`teammate_opportunity_finder`、`hand_structure_analyzer`、`enhanced_collaboration`

共享牌型策略仍位于 `src/decision/`（`card_power_evaluator`、`single_card_strategy` 等）。

## 推荐 import

```python
from m.m1 import RuleBasedDecisionEngineM1, StageRouter
from m.platform import GameRecorder
```

## Shim 再生

```bash
python scripts/tools/_gen_decision_shims.py
```
