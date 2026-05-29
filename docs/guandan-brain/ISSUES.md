# 缺陷登记簿（Defect Register）

> 编号规则：`GUA-001`、`GUA-002`… **永不复用**。关闭后若复发，新开编号并 `duplicate of GUA-xxx`。  
> **状态**以文档与提交为准；后续在表中直接维护。  
> **来源扫描**（写入本条时已对照）：`docs/掼蛋AI相关比赛汇总.md`、`docs/reports/README_优化项目.md`、`docs/reports/YF掼蛋优化实施报告.md`、`docs/guandan-brain/notes/WORKFLOW_RESTART_LOG.md`、`logs/`（含 `yf*_m1_*.log`、`batch_executor_*.log` 等）。

## 当前条目

| ID | 状态 | 严重级别 | 标签 | 版本 | 简述 | 现象 / 复现要点 | 涉及模块 | 备注 |
|----|------|----------|------|------|------|-----------------|----------|------|
| GUA-001 | closed | P3 | observation | docs | 比赛汇总文档曾无法正确阅读 | `docs/掼蛋AI相关比赛汇总.md` 乱码 | 文档 | `closed_in` 文档 v2.0 UTF-8（2026-04-21）；**非**客户端版本问题 |
| GUA-002 | closed | P1 | policy | m1 | M1 不必要 PASS（主动/被动） | 有合法动作仍 PASS；策略链失败后直接 PASS | M1 `phase_handlers` | 见 `docs/reports/m1/M1_PASS问题修复完成报告.md` |
| GUA-003 | closed | P1 | policy | m1 | M1 优先级空候选等价 PASS | `candidates` 为空时曾直接 PASS | `enhanced_priority_system`、`phase_handlers` | 见 `docs/reports/m1/M1_PASS问题修复总结.md` |
| GUA-004 | closed | P1 | rules | m1 | M1 Opening 阶段问题 PASS 集中 | 校验过严致动作被滤；opening 问题 PASS 统计高 | Opening 路由 / 校验 | `docs/fixes/M1_20251224_问题修复记录.md` |
| GUA-005 | closed | P1 | policy | m1 | M1 endgame_early PASS 率过高 | 残局前期过保守 + 校验/优先级叠加 | 残局前期 handler | 同上 |
| GUA-006 | closed | P2 | policy | m1 | yf2_m1 相对 yf1_m1 改善滞后 | yf2 PASS、问题 PASS 仍偏多 | M1 双客户端 | `docs/reports/m1/M1行为改善分析总结.md` |
| GUA-007 | closed | P1 | policy | m1 | M1 Opening 被动不当 PASS | 对手出对/单张仍有可选动作却 PASS | `OpeningPassiveHandler` | 同上；与 `M1_PASS问题分析报告.md` 中阶段分析一致 |
| GUA-008 | closed | P1 | observation | m1 | M1 记录缺少 victoryNum / 评估异常 | `gameOver` 过早保存；需 `gameResult` 与 `victoryNum` | `yf1_m1.py`、`game_recorder`、评估器 | [GAME_RECORD_SAVE_FIX.md](../fixes/GAME_RECORD_SAVE_FIX.md)、[EVALUATOR_COMPATIBILITY_REPORT.md](../fixes/EVALUATOR_COMPATIBILITY_REPORT.md) |
| GUA-009 | open | P3 | policy | v4 | V4 RL 未启用 | 对比说明：RL 部分集成但未作为默认路径 | V4 混合决策 | `docs/V4_V5_COMPARISON.md` | `docs/versions/V4_V5_COMPARISON.md` |
| GUA-010 | open | P1 | observation, policy | v4, v5 | 对局记录中决策信息不全 | `candidates_count=0` 等，score/layer 空，难评混合链 | hybrid / V4–V5 栈 | 对照 `docs/analysis/YF决策问题分析与修复.md`；与回放/评测管道一致时需样本 |
| GUA-011 | closed | P1 | rules | v5 | 红心配（逢人配）识别与使用不当 | 曾硬编码 H2；应按 `cur_rank` 用 `H{rank}`；小顺浪费红心配 | `card_grouping_strategy` | `docs/fixes/GAME_ISSUE_FIX_SUMMARY.md` |
| GUA-012 | closed | P2 | policy | v5 | 天然单张未优先、拆三张出单 | 有天然单张却拆三张 | `yf1_v5.py`、`yf2_v5.py` | 同上 |
| GUA-013 | open | P2 | observation | v5, 引擎? | 疑似重复出牌（手牌跟踪） | 记录中同张牌似重复；例 D9 | 引擎或客户端状态 | `GAME_ISSUE_FIX_SUMMARY.md` 建议查 `guandan_offline` 侧 |
| GUA-014 | open | P2 | policy | 共用 | 拆牌与优先级不合理 | 拆三张、未优先多余单张、钢板/对子等（多报告归纳） | 多版本共用决策层 | `docs/analysis/YF决策问题分析与修复.md`；根因在 policy 居多 |
| GUA-015 | open | P2 | policy | v6 | V6 路线与验收未闭环 | README 与实施报告：**队友保护、动态优先级、yf1/2_v6、胜率对 lalala/V4/V5** 仍为规划或待验 | V6 规划 | `docs/reports/README_优化项目.md`、`docs/reports/YF掼蛋优化实施报告.md`（`.kiro/specs` 任务 3–11） |
| GUA-016 | open | P1 | policy | 训练 | 训练样本大量空 action_cards | PASS 样本稀释；需加载器过滤 | `simple_data_loader`、Stage7+ | [TRAINING_FIXES_SUMMARY.md](notes/TRAINING_FIXES_SUMMARY.md)；`logs/mlruns` 联调 |
| GUA-017 | open | P1 | policy | 训练 | 损失尺度与预测行为异常 | 过度预测、阈值与惩罚需迭代（含 WORKFLOW 重启那轮参数） | Stage7、`logs/mlruns` | [WORKFLOW_RESTART_LOG.md](notes/WORKFLOW_RESTART_LOG.md)；`logs/batch_executor_*.log` 对照运行窗口 |
| GUA-018 | open | P2 | policy | 训练 | 策略理解率指标曾为 0 / 与完全匹配耦合过严 | 需联合损失与「基本正确」定义 | 训练指标 | `docs/fixes/STRATEGY_UNDERSTANDING_FIX.md` |
| GUA-019 | closed | P1 | policy | 训练 | （已合并跟踪）损失爆炸与阈值专项 | 与 GUA-017 同源：[WORKFLOW_RESTART_LOG.md](notes/WORKFLOW_RESTART_LOG.md) 中阈值 clamp、对数惩罚等 | 同 GUA-017 | **closed**；`duplicate of GUA-017`（同一轮日志治理，避免双开） |
| GUA-020 | closed | P2 | observation, policy | m1 | 验证 yf2_m1 是否仍明显弱于 yf1_m1 | 成对 `game_id` 扩样后差距不显著 | `yf1_m1.py`、`yf2_m1.py`、共用 `src/decision/` | `closed_in` 2026-04-21：见 `ITERATIONS.md`；`logs/yf1_m1_*.log` / `yf2_m1_*.log` |
| GUA-021 | closed | P1 | policy | m1 | M1 「问题 PASS」仍偏多（复盘） | 改后新局 3 个成对 `game_id` 合并：近似问题 PASS **0**（见 `ITERATIONS`「GUA-021 共用层收紧」行） | `phase_handlers`、`stage_router`、`rule_based_decision_engine_m1`、`intelligent_router` | `closed_in` 2026-04-21；全量 `game_records` 若混改前旧局，合并合计仍可能 **>0**，评测建议按「改后 `game_id`」子集统计 |
| GUA-022 | open | P1 | policy | m1 | M1 对 lalala **队胜率过低**（YiFei 0+2 长期不胜） | 多局 `victoryNum` 为 `[0,3,0,3]`；需队级策略与配合 | 共用决策层、队友/压制、残局；与 **GUA-014** 可联动 | 指挥/看板见 [`AGENT_HUB.md`](AGENT_HUB.md)；迭代见 `ITERATIONS`「下一轮指挥」行 |
| GUA-023 | open | P1 | observation, infra | agent-hub | Kanban worker 经 OpenCode ACP 无法执行（0 tool calls → crash 循环） | `copilot-acp` + `opencode acp`：Hermes 收不到 `<tool_call>`，worker 未 `kanban_complete` 即退出；例 `t_b53fc45b` | Hermes `copilot_acp_client`、profile `opencode-eng` | 根因与处置见 [`AGENT_HUB.md`](AGENT_HUB.md)「方案 A」「接下来要做的（2026-05-21）」；与 **GUA-022** 策略无关（Kanban 任务误标 GUA-022 测试） |

---

## 交叉引用

| ID | 相关文档 |
|----|----------|
| GUA-022 | [`AGENT_HUB.md`](AGENT_HUB.md) — 多 Agent / Kanban 编排（cursor → opencode-eng） |
| GUA-023 | [`AGENT_HUB.md`](AGENT_HUB.md) — OpenCode ACP 桥接不兼容、GUA-022 联调任务 `t_b53fc45b` 结论 |


## 来自「比赛汇总」的说明（非缺陷）

`docs/掼蛋AI相关比赛汇总.md` 主要为**南邮平台与赛事索引**，不记载本仓库逻辑缺陷；参赛与平台 JSON/WebSocket 对齐请在迭代中当作**环境约束**验收（不必单列 GUA，除非出现协议不符）。

## 模板（新增行时复制）

| ID | 状态 | 严重级别 | 标签 | 版本 | 简述 | 现象 / 复现要点 | 涉及模块 | 备注 |
|----|------|----------|------|------|------|-----------------|----------|------|
| GUA-xxx | open / closed | P0–P3 | rules, observation, policy | m1/v4/v5/v6/训练/docs | | | | `closed_in` / `duplicate of` |
