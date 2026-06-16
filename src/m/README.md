# src/m — M 系列目录

> Phase 2b（2026-05-29）：**M2 / M3 引擎已物理迁入**；`src/decision/` 保留兼容 shim。

## 子目录

| 路径 | 内容 | 物理位置 |
|------|------|----------|
| `m/platform/` | 通信、记录、WebSocket、常量 | re-export |
| `m/m1/` | M1 路由 + 阶段处理器 + 策略引擎 | **`src/m/m1/*.py`** |
| `m/m2/` | M2 引擎 + M2 阶段处理器 | **`src/m/m2/*.py`** |
| `m/m3/` | M3 lalala 移植 + utils + 契约适配 | **`src/m/m3/*.py`** |

## 推荐 import

```python
from m.m1 import RuleBasedDecisionEngineM1
from m.m2 import RuleBasedDecisionEngineM2
from m.m3 import M3DecisionEngine, M3DecisionProvider
from m.platform import GameRecorder
```

## Shim 再生

```bash
python scripts/tools/_gen_decision_shims.py
```
