# src/v — V 系列目录（渐进迁移）

| 子路径 | 代号 | 物理位置（当前） |
|--------|------|------------------|
| `v/learn/` | v4, v5, v5_stage5 | `src/decision/hybrid_decision_engine_v4.py` 等 |
| `v/nn/` | v7 | `src/decision/ultimate_win_rate_engine_v7.py` |

客户端壳仍在 `src/communication/yf*_v*.py`；决策核心请通过本目录 import。

## 推荐 import

```python
from v.learn import HybridDecisionEngineV5
from v.nn import UltimateWinRateEngineV7
from contracts import IDecisionProvider
from m.platform import GameRecorder
```
