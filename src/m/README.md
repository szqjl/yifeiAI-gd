# src/m — M 系列目录（渐进迁移）

> 治理方案 §5.2 目标形态。Phase 1（2026-05-29）：**命名空间 + re-export**，不移动物理文件。

## 子目录

| 路径 | 内容 | 物理位置（当前） |
|------|------|------------------|
| `m/platform/` | 通信、状态、常量（V 可依赖） | `src/communication/`、`src/game_logic/` |
| `m/m1/` | M1 规则引擎 | `src/decision/rule_based_decision_engine_m1.py` |
| `m/m2/` | M2 引擎 | `src/decision/rule_based_decision_engine_m2.py` |
| `m/m3/` | M3 lalala 移植引擎 | `src/decision/m3_decision_engine.py`；契约入口 **`M3DecisionProvider`**（`on_message` → `decide`） |

## 推荐 import（新代码）

```python
from contracts import IDecisionProvider, is_decision_provider
from m.m1 import RuleBasedDecisionEngineM1
from m.platform import GameRecorder, WebSocketManager
```

## 后续 Phase

- Phase 2：将 `stage_router`、`phase_handlers` 迁入 `m/m1/` 或 `m/shared/`
- Phase 3：客户端 `yf*_m1.py` 改为从 `m.m1` 引用
