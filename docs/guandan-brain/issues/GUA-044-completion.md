# GUA-044 完成定义（批跑四席就绪门闩）

> **定音**：离线 v1006 **第 4 个 WebSocket 连上即自动开局**；批跑须保证 **按序连入 + 末席连入前前三席已登记就绪**，且批跑侧**不得**在就绪不足时继续。

| 项 | 要求 |
|----|------|
| **就绪表** | `batch_executor/clients_ready.json`；每席 WS `connect` 成功后 `mark_client_ready(user_info)` |
| **顺位门闩** | `CONNECT_ORDER_INDEX` + **按席位** `_peers_ready`（非纯计数）；client4 进程延迟 **11s**、末席连入前稳定 **7s**（2026-06-06 由 2s+5s）；`websocket_manager` + `lalala_adapter` 连前 `wait_for_connect_turn` |
| **批跑等待** | `executor` 批次前 `clear_all_ready()`；`wait_for_clients_connected` 读就绪表；**四席未齐 → 中止本批**（不再「超时仍继续」） |
| **验收** | `pytest tests/test_client_ready.py` pass；批跑日志含 `✓ 四席已全部连上，平台可安全开局` |
| **复发排查** | 单席日志在 `发送动作` 后长时间无新 `act` → 先查**他席**是否未回包（非本席决策 hang）；对照四席就绪表时间戳 |
| **手动单测** | `YF_SKIP_CONNECT_GATE=1` 可跳过门闩（仅本地调试） |

**后续 Agent**：若再报「首局卡顿 ~30–60s」，先读就绪表与 yf1/yf2/lalala 四席日志时间线；若门闩已存在仍卡，另开 GUA 查 lalala `rule_parse` 慢路径（**非**本关单范围）。
