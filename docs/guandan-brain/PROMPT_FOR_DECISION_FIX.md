# 给执行 AI 的说明（根据本轮评测改决策）

把下面**整段**复制到对话里，让改代码的 AI 按评测结论动手（仓库根路径以本机为准，当前主工作仓：`c:\yifeGDBOT`）。

---

本轮评测（`game_records/` 中成对 `yf1_m1`/`yf2_m1` 的 JSON，合并多局）的结论如下，请**严格按此范围改代码**：目标是 **减少「近似问题 PASS」**——即决策为 PASS，且当时 `context.actionList_size > 1`（仍有多种合法非 PASS 可选）却仍 PASS；**不要**去改 `yf1_m1.py`/`yf2_m1.py` 做两套分叉路由，评测已表明两队共用 **M1 硬编码决策栈**，问题在 **`src/decision/` 共用层**。请优先检查并修改 **`phase_handlers.py`** 里与 **被动跟牌**相关的 **`OpeningPassiveHandler`、`MidEarlyPassiveHandler`**（及其中 `_default_passive_action`、牌力阈值、「让牌/不压」等会 `return 0` 的分支），其次检查 **`stage_router.py`** 里 **`_is_passive_play`** 是否误判主动/被动导致进错 handler，再次检查 **`enhanced_priority_system.py`** 及优先级选中后是否仍可能落到 PASS；改法原则是：当 `action_list` 中存在非 PASS 动作时，**不得**在无充分理由下直接 PASS，并保留与历史修复一致的 **「最后兜底：第一个非 PASS」** 逻辑。改完后需在本地重新跑批量对战生成 **新** `game_records`，用**同一统计口径**（PASS 且 `actionList_size>1`）对比改前基线，把前后数字写入 `docs/guandan-brain/ITERATIONS.md`，若合计下降再考虑将 **GUA-021** 标为关闭。

---

**可选附言（若执行 AI 要文件锚点）**：台账见 `docs/guandan-brain/ISSUES.md`（GUA-021）、`ITERATIONS.md`（最新一行）、`EVAL.md`（M1 对照与统计口径）。
