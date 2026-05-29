# M3 契约（contracts）

| 字段 | 值 |
|------|-----|
| 契约版本 | `0.1-draft`（`DECISION_PROVIDER_CONTRACT_VERSION`） |
| 状态 | **草案**：目录与接口已落地，**尚未**作为 V-default-smoke ON 的冻结门禁 |
| 冻结条件 | 治理方案 §7.2 条件 B：本文档标记 `1.0` + M 冒烟连续 7 天绿 |

## IDecisionProvider

| 成员 | 约定 |
|------|------|
| `player_id: int` | 本平台座位 0–3 |
| `decide(message) -> int` | 输入 `type=act` 等平台消息；返回 `actionList` 合法下标 |

## V 系列依赖规则

- **允许**：`contracts.*`、`m.platform.*`（通信/状态/常量）
- **禁止（新代码）**：`from decision.rule_based_decision_engine_m1 import ...` 等 M 代际直达
- **存量**：`src/decision/` 路径在迁移期仍有效；新 V 代码应走 `src/v/` re-export

## 变更流程

1. 修改 `decision_provider.py` 前在 `ITERATIONS.md` 登记
2. 跑 `pytest tests/test_m3_contracts_layout.py`
3. 版本号递增；破坏性变更需 major bump 并同步 MATRIX
