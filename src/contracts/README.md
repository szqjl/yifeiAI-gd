# M3 契约（contracts）

| 字段 | 值 |
|------|-----|
| 契约版本 | **`1.0`**（`DECISION_PROVIDER_CONTRACT_VERSION`） |
| V 挂接门禁 | **`V_INTEGRATION_GATE_ENABLED = True`** |
| 状态 | **已冻结**（2026-05-29 Phase 2）；V 客户端/引擎 PR 须通过 `assert_v_integration_gate` |

## IDecisionProvider

| 成员 | 约定 |
|------|------|
| `player_id: int` | 本平台座位 0–3 |
| `decide(message) -> int` | 输入 `type=act` 等平台消息；返回 `actionList` 合法下标 |

## V 系列依赖规则

- **允许**：`contracts.*`、`m.platform.*`、`v.learn.*`、`v.nn.*`
- **禁止（新 V 代码）**：`from decision.hybrid_decision_engine_v5 import ...` 等（请用 `v.learn` / `v.nn`）
- **禁止（新 V 代码）**：`from decision.rule_based_decision_engine_m1 import ...` 等 M 代际直达
- **存量**：`src/decision/*.py`  shim 在迁移期仍可用；新 PR 不得新增对 shim 的依赖

## CI / 测试门禁

```bash
pytest tests/test_m3_contracts_layout.py tests/test_v_integration_gate.py
```

## 变更流程

1. 修改 `decision_provider.py` 前在 `ITERATIONS.md` 登记
2. 破坏性变更须 major bump 并同步 MATRIX / 治理方案
