# 缺陷登记簿（Defect Register）

> 编号规则：`GUA-001`、`GUA-002`… **永不复用**。关闭后若复发，新开编号并 `duplicate of GUA-xxx`。  
> **状态**以文档与提交为准；后续在表中直接维护。  
> **来源扫描**（写入本条时已对照）：`docs/掼蛋AI相关比赛汇总.md`、`docs/reports/README_优化项目.md`、`docs/reports/YF掼蛋优化实施报告.md`、`docs/guandan-brain/notes/WORKFLOW_RESTART_LOG.md`、`logs/`（含 `yf*_m1_*.log`、`batch_executor_*.log` 等）。

## 引擎维护策略（定音 · 2026-05-31 · 评审确认）

| 引擎 | 定位 | 维护状态 |
|------|------|----------|
| **M1** | 首个实验 AI（`yf1_m1` / `yf2_m1` + `src/decision/`） | **frozen**（**GUA-022 closed**）— **非交付线**；**勿再开 M1 策略 GUA**；仅 **bugfix**（crash / 协议 / 记录）与 **pytest 回归** |
| **M3** | **主交付** + **`IDecisionProvider` 底座**（`yf1_m3` / `yf2_m3`、`src/m/m3/`、`src/contracts/`） | **active** — 策略迭代、批跑 KPI、GUA-026+ 跟踪 |
| **V5+** | 组牌 / 牌力 / 知识层长期路线 | 规划 / 按需 — **P0 以外**的组牌与牌力评估 **不走 M3 硬编码扩张** |

**队胜率 KPI**：自 **2026-05-31** 起**只看 M3 批跑**。**多样本观测**（净盘、同 exe）：S1 **7/10**、S2 **11/12**、S3 **8/10**、S4 **8/10** → **合计 34/42（81.0%）**（见 `ITERATIONS`「M3 队胜率多样本观测」）。M1 净盘 **0/12** 为 frozen 基线对照，**非**口径错误。

### 实现分工（评审定音）

| 优先级 / 能力 | 落点 | 说明 |
|---------------|------|------|
| **P0 guard**（可 pytest + 批跑验收的 if-guard） | `src/m/m3/m3_decision_engine.py`（及 `m3_utils.py`） | 与 [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) **M3 · P0** 一致；例 GUA-026/029/031/032 |
| **组牌 / 牌力 / 混合决策** | **V5+**（`src/v/`、V 挂接 `IDecisionProvider`） | 不在 M3 引擎内堆整篇策略；M3 保持 lalala 式 guard + 契约底座 |
| **M1 共用层** | `src/decision/`（frozen） | 历史 PHASE2 与 V shim；**不接新开策略迭代** |

**GUA-022**：**closed**（2026-05-31）；队胜率 KPI 自该日起迁 **M3**（见 [`ITERATIONS.md`](ITERATIONS.md)「M1 frozen 定音」行）。

**批跑局数**：`--target-games` 须 **3 的倍数**（3 / 9 / 12）；见 [`EVAL.md`](EVAL.md)「批跑局数档位」。**勿新开 10 局**等非整批目标。

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
| GUA-022 | closed | P1 | policy | m1 | ~~M1 队胜率攻关~~ → **M1 frozen，队胜率 KPI 迁 M3** | M1 净盘 12 局 **`[0,3,0,3]`×4 → 0/12**；M3 同机 **7/10**；多轮 PHASE2 策略未改队胜 | `src/decision/`（frozen） | **`closed_in` 2026-05-31**：M1 **非交付线**，定音 **frozen**（见上表）；不再迭代 M1 取胜策略；队胜率见 **M3 批跑** / `ITERATIONS` GUA-022/026 行 |
| GUA-023 | open | P1 | observation, infra | agent-hub | Kanban worker 经 OpenCode ACP 无法执行（0 tool calls → crash 循环） | `copilot-acp` + `opencode acp`：Hermes 收不到 `<tool_call>`，worker 未 `kanban_complete` 即退出；例 `t_b53fc45b` | Hermes `copilot_acp_client`、profile `opencode-eng` | 根因与处置见 [`AGENT_HUB.md`](AGENT_HUB.md)「方案 A」「接下来要做的（2026-05-21）」；与 **GUA-022** 策略无关（Kanban 任务误标 GUA-022 测试） |
| GUA-024 | closed | P1 | policy | m3 | M3 play 阶段几乎全 PASS | 两轮根因：（1）`curAction[-1]` 误用；（2）**细化 debug 发现** `curAction`/`greaterAction` 偶发 **str** → dispatch 全 miss → 恒 PASS；已加 `_ensure_list` 规范化 | `m3_decision_engine` | `closed_in` 2026-05-29～30；541958 验证 dispatch 100% list、100+ 非 0 决策 |
| GUA-025 | closed | P1 | observation | infra | 回放 yf1 初始手牌与出牌流水不一致 | `_merge_same_game_records` 用 start_time **5 秒窗口**，batch 多局误把 round 12 手牌合并进 round 19；表现为「出了没有的牌 / 出牌后手牌扣不对 / 误显 4 个 3 炸弹」 | `game_recorder._merge_same_game_records`、`yf_replay` | `closed_in` 2026-05-30；改按文件名 opponent+round+level 匹配；`tests/test_game_recorder_merge.py` 4 passed |
| GUA-026 | closed | P2 | policy | m3 | M3 三带二/拆牌策略偏激进 | round 19 真实记录 yf1 出 555+22、QQQ33 等（非回放 bug）；**2026-05-30**：`_ThreeWithTwo` 增级牌/炸弹保护、禁拆 trips 常态路径、移除逢人配三带二 fallback | `m3_decision_engine` | **`closed_in` 2026-05-31**：`test_m3_gua026.py` **3 passed** + GUA-029/031/032 回归 **24 passed**；净盘 **12 局** 队胜 **11/12**、近似问题 PASS **0**（日志 `logs/batch_executor_20260531_213847.log`）；未再现 **555+22 拆炸** 类回归。牌谱全量含 **H+curRank** 三带二 **39** 手（被动压牌边界，留 PRINCIPLES §二十 P2）；[`10_three_with_two_skills.md`](../knowledge/skills/04_common_skills/10_three_with_two_skills.md) §二十 **主战术真源** |
| GUA-027 | closed | **P0** | observation, policy | m3 | M3 对 WebSocket 场态消息用法不完整/不准确 | 对照 v1006 说明书：**被动比牌应信 `greaterAction` + `publicInfo.playArea`**；M3 仅在 `curAction==PASS` 时用 greater，否则用 `curAction[1]` 算强度；playArea 未参与决策。19 局审计 ~40% 单牌步 greater 与「本圈最大」不一致 | `m3_decision_engine`、`game_logic/trick_state.py`、`yf_replay` | `closed_in` 2026-05-30；`resolve_effective_greater` + `TrickSequenceTracker`；**7+22 pytest passed** |
| GUA-028 | closed | P1 | observation, rules | m3 | M3 与 v1006 说明书三项未对齐 | **TripsPair** 未分派致 PASS；**indexRange** 未 clamp 回包；**publicInfo.rest** 未同步剩牌 | `platform_act.py`、`m3_decision_engine`、`yf1_m3`/`yf2_m3` | `closed_in` 2026-05-30；`test_m3_platform_align_gua028.py` 5 passed |
| GUA-029 | closed | **P0** | policy, rules | m3 | M3 炸弹可执行规则包（R1–R6） | 回放 `20260530172743739854` 曾现 yf1 **5×8** 全程未出；根因 `choose_bomb` 读 `action[-1]` → TypeError → PASS | `m3_utils.choose_bomb`、`m3_decision_engine` | **`closed_in` 2026-05-31**：R1–R6 + `test_m3_gua029` **8 passed**；净盘批跑 **10/10**；炸弹 yf1 **175** + yf2 **152**。队胜率见 M3 批跑观测（**7/10**，`ITERATIONS` 2026-05-31）。规则 [`01_bomb_techniques.md`](../knowledge/skills/02_main_attack/01_bomb_techniques.md) |
| GUA-030 | closed | P2 | docs, policy | m3, v5 | **原则+战略映射表**：`01_basic_principles` / `02_strategy_overview` / `03_basic_strategy` → 引擎归属（**P0→M3**，**P1+→V5**） | 无代码缺陷；需将 skills 落实为可测 guard / V5 知识层，避免整篇硬编码进 M3 | [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md)；真源见 §一–§七 | `closed_in` 2026-05-31；三篇映射评审通过；M3 P0/P1 实现由 GUA-029 及后续迭代跟踪 |
| GUA-031 | closed | P1 | policy | m3 | M3 传牌 `numof*` guard + 队友让道扩全牌型 | 被动仅 `_Single/_Pair` 等部分牌型做队友 PASS；`_active` 无 `numoffri==1` 送小单 / `numoffri==5` 喂牌；`numofnext==1` 防小单不完整 | `m3_decision_engine`（`_active`、`_passive`、各 `_Xxx` handler） | **`closed_in` 2026-05-31**：P-F02 扩 `_Trips/_ThreePair/_TwoTrips/_Straight`；PASS-P02/P03/P04；`test_m3_gua031.py` **7 passed**；GUA-026/027/028/029 回归 **31 passed** |
| GUA-032 | closed | P1 | observation, policy | m3 | M3 **记牌+算牌**确定性规则 + `remain_cards_classbynum` 同步 | 文档 §14–§15、§18–§20、**§二十二**（孤张定律 CG-T06、口诀 13）；5/10 法则、顺/夯点位预判（**CALC-M03/M04**）；`remain_cards_classbynum` stale | `m3_decision_engine._update_play_state`、`m3_utils`；[`04_calculation_skills.md`](../knowledge/skills/04_common_skills/04_calculation_skills.md)、[`04_card_grouping_skills.md`](../knowledge/skills/07_opening/04_card_grouping_skills.md)、[`08_straight_skills.md`](../knowledge/skills/04_common_skills/08_straight_skills.md)、[`10_three_with_two_skills.md`](../knowledge/skills/04_common_skills/10_three_with_two_skills.md) | **`closed_in` 2026-05-31**：`sync_remain_cards_classbynum` + `_update_play_state` 同步；MEM-M02；CALC-M01（被动炸过滤）+ CALC-M03（5/10 顺子降权）；`test_m3_gua032.py` **6 passed**；GUA-029/031/033 回归 **34 passed**；**CALC-M02** 待 **P-H01** |
| GUA-033 | closed | P1 | observation, rules | m3, infra | M3 **批末 `victoryNum` / `gameResult` 解析错误**（批级回填污染） | **客户端已修**；**平台根因**：本包 v1006 exe **argv 无效**，单次会话 **固定 3 局** → WebSocket `settingTimes=3`、`victoryNum` 常 `[0]+[1]=3`；须 **`batch_games` 校验 + fallback** | `yf1_m3.py`、`yf2_m3.py`、`game_result_utils.py`；真源 [`platform-data-interpretation.md`](../knowledge/platform-data-interpretation.md) **§2** | **`closed_in` 2026-05-31**；`test_m3_gua033.py` **11 passed**；exe 探测 `scripts/tools/probe_exe_argv_ws.py` |
| GUA-034 | closed | P1 | policy | m3 | M3 **残局：队友走光后 rank 小牌首出 + 被动不拆结构压牌** | round **38** yf2：`20260601112040940931 …-[38]-[4].json` **102–107 步** — 接风 `_active` 拆对 **3** 出单；对手 **6/对6** 可压（9/10/拆三张）却 **PASS**；107 对手三带二 **5 张走完**。**根因**：`_active` 仍走 `rankone/ranktwo` 清小点；`_Single/_Pair.normal()` 只认 `single_member`/`pair_member`，不为压牌拆 trips；缺「队友 rest=0 → 1v2 拦头游」模式。**related** **GUA-014**（泛化拆牌）、**GUA-026**（禁拆 trips 边界）、**GUA-029 R3**（`_Pair` 或未触发 ≤7 阻断） | `m3_decision_engine`（`_active`、`rankone/ranktwo/rankthree`、`_Single`、`_Pair`）；[`M3_DIAGNOSIS.md`](M3_DIAGNOSIS.md) BUG2 | **`closed_in` 2026-06-01**：方向 A — `_is_solo_sprint` + END-M02–M04；`test_m3_gua034.py` **6 passed**；GUA-026/029/031 回归 **24 passed** |
| GUA-035 | closed | P1 | policy | m3 | M3 **END-M02+：solo 接风按对手剩张过滤牌型** | GUA-034 END-M02 仅固定优先三带二/三张/对子；缺：**任一对手剩 1 张 → 不宜出小单**；剩 **2 张 → 不宜出对**；剩 **5 张 → 不宜出三带二**（「不宜」非绝对禁，无路可走仍出）。**related** **GUA-034** END-M02、**GUA-031** PASS-P03（下家剩 1 禁小单） | `m3_decision_engine._gua035_solo_wind_pick`、`_gua034_solo_active_pick` | **`closed_in` 2026-06-01**：END-M02+-01–04；`test_m3_gua035.py` **6 passed**；GUA-034/026/029/031 回归 **30 passed** |

---

## 交叉引用

| ID | 相关文档 |
|----|----------|
| GUA-022 | [`AGENT_HUB.md`](AGENT_HUB.md) — 多 Agent / Kanban 编排（cursor → opencode-eng） |
| GUA-023 | [`AGENT_HUB.md`](AGENT_HUB.md) — OpenCode ACP 桥接不兼容、GUA-022 联调任务 `t_b53fc45b` 结论 |
| GUA-029 | [`01_bomb_techniques.md`](../knowledge/skills/02_main_attack/01_bomb_techniques.md)、[`M3_DIAGNOSIS.md`](M3_DIAGNOSIS.md) BUG5；样例局 `replay_word.md` / `game_records/20260530172743739854 [yf1_m3]-…` |
| GUA-030 | [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md)、[`01_basic_principles.md`](../knowledge/skills/01_foundation/01_basic_principles.md)、[`02_strategy_overview.md`](../knowledge/skills/01_foundation/02_strategy_overview.md)、[`03_basic_strategy.md`](../knowledge/skills/01_foundation/03_basic_strategy.md)、[`M-V-Series-治理方案.md`](../governance/M-V-Series-治理方案.md) §3 |
| GUA-031 | [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) §8.4、§十七–§二十二、[`01_passing_skills.md`](../knowledge/skills/03_assist_attack/01_passing_skills.md)、[`04_card_grouping_skills.md`](../knowledge/skills/07_opening/04_card_grouping_skills.md)、[`07_two_trips_skills.md`](../knowledge/skills/04_common_skills/07_two_trips_skills.md)–[`11_trips_skills.md`](../knowledge/skills/04_common_skills/11_trips_skills.md)；与 GUA-029 R5（队友不炸）互补 |
| GUA-032 | [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) §14–§15、§18–§22（CALC-M03/M04/M05、**CG-T06**）、[`04_calculation_skills.md`](../knowledge/skills/04_common_skills/04_calculation_skills.md)、[`04_card_grouping_skills.md`](../knowledge/skills/07_opening/04_card_grouping_skills.md)、[`05_memory_skills.md`](../knowledge/skills/04_common_skills/05_memory_skills.md)、[`08_straight_skills.md`](../knowledge/skills/04_common_skills/08_straight_skills.md)、[`10_three_with_two_skills.md`](../knowledge/skills/04_common_skills/10_three_with_two_skills.md)、[`card_tracking.py`](../../src/game_logic/card_tracking.py) |
| GUA-033 | [`platform-data-interpretation.md`](../knowledge/platform-data-interpretation.md) **§2 exe argv 实测**、§4.1–§4.3、[`guandan-platform-v1006.mdc`](../../.cursor/rules/guandan-platform-v1006.mdc) §局与副；**related** **GUA-008**（M1 `gameResult` 链路）、[`GAME_RECORD_SAVE_FIX.md`](../fixes/GAME_RECORD_SAVE_FIX.md)；探测 `scripts/tools/probe_exe_argv_ws.py`；矩阵 [`gua033-batch-matrix-2026-05-31.md`](../analysis/gua033-batch-matrix-2026-05-31.md) |
| GUA-026 | [`04_card_grouping_skills.md`](../knowledge/skills/07_opening/04_card_grouping_skills.md) §二十二（**组牌总纲**）；[`10_three_with_two_skills.md`](../knowledge/skills/04_common_skills/10_three_with_two_skills.md) §二十（**三带二主真源**）；[`11_trips_skills.md`](../knowledge/skills/04_common_skills/11_trips_skills.md) §二十一（拆 trips 边界）；[`06_red_heart_usage.md`](../knowledge/skills/04_common_skills/06_red_heart_usage.md) §十六（逢人配子集） |
| GUA-034 | [`GUA-034-方案评审.md`](GUA-034-方案评审.md)（**方向 A 已实施**）；[`M3_DIAGNOSIS.md`](M3_DIAGNOSIS.md) BUG2；[`01_bomb_techniques.md`](../knowledge/skills/02_main_attack/01_bomb_techniques.md) §五；[`10_three_with_two_skills.md`](../knowledge/skills/04_common_skills/10_three_with_two_skills.md) §5 残局；**related** **GUA-014**、**GUA-026**、**GUA-029 R3**、**GUA-035**；样例 `replay_word.md` / `game_records/20260601112040940931 [yf2_m3]-…-[38]-[4].json` |
| GUA-035 | **GUA-034** END-M02+；[`GUA-034-方案评审.md`](GUA-034-方案评审.md) 方向 E 前置；[`M3_DIAGNOSIS.md`](M3_DIAGNOSIS.md) BUG2（两手枚举 → V5+）；[`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) P-C01 / CALC-M05 |

---

## GUA-029 完成定义（炸弹可执行规则包 R1–R6）

> 从 `01_bomb_techniques.md` 提炼、与 M3 现有观测字段对齐；**互不打架**，可写进 if-then，避免与 GUA-026 拆牌保护混淆。

| 规则 | 条件（M3 可观测） | 动作 | 文档依据 | 涉及模块 |
|------|-------------------|------|----------|----------|
| **R1** | `actionList` 含 `Bomb`/`StraightFlush` 且进入 `choose_bomb` | **先修** `choose_bomb`：点数读 `action[1]`（对齐 `first_prize/utils.py`），同花顺分支一并查；单元测 v1006 格式 `['Bomb','8',[…]]` | 前置；不修则 R2–R6 均可能异常→PASS | `m3_utils.choose_bomb` |
| **R2** | `beatAction[0] in (Bomb, StraightFlush)` 且 `choose_bomb != -1` | **必回炸**（最小够用炸弹） | §二.3 追炸；§二.6 炸对手炸弹 | `_Bomb`；取消/绕过 `cur_Bomb_num>=3` 硬门槛 |
| **R3** | `numofplayers[greaterPos] <= 7` 且当前牌型分支无可跟牌 且 `choose_bomb != -1` | **必炸**（防冲刺/听牌） | §三.5.3 剩 5–7 张；§五.2 逢 5 必防 | 各 `_Single`/`_Pair`/`_ThreeWithTwo`/… 统一兜底 |
| **R4** | `numofplayers[greaterPos] == 4` | **默认不炸**；白名单：① 我剩 ≤2 手且炸后一手走完；② 仅炸弹能压且炸后可接风领出 | §五.1 炸不打四 | `_Bomb` 与各被动分支 guard |
| **R5** | `(myPos+2)%4 == greaterPos` | **禁止出炸**（全局 guard，各分支统一） | §二.3 不压队友（默认） | `_Bomb`、`_ThreeWithTwo` 等 |
| **R6** | `numofmy <= 10` 且 `actionList` 存在炸弹/SF **一手清牌** | **优先 bomb/SF 冲刺**（扩 `one_hand` + `_active` 首段） | §二.5 残局冲刺；§五.3 尾炸+一手 | `_passive`/`_active`/`one_hand` |

**验收**：① `pytest` 新增 `test_m3_gua029.py`（R1 格式 + R2 回炸 + R3 ≤7 阻断，用样例局 step46/74 构造）；② 异常兜底不再无脑 `send_action(0)` 掩盖炸弹分支（或 bomb 分支内不抛异常）；③ 净盘 M3 批跑 ≥10 对：炸弹出牌次数 >0、队胜率或 PASS 率有方向性改善（记录在 `ITERATIONS.md`）。

**与 GUA-026 边界**：GUA-026 禁止三带二**拆炸弹/耗级牌**；GUA-029 要求在**应炸场景主动出整炸**，二者不冲突。

## GUA-030 完成定义（原则映射 · 文档）

> 真源文档 [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md)。**本轮仅登记与映射，不实现 V5 代码。**

| 项 | 完成标准 |
|----|----------|
| 映射表 | 原则条目有 ID（P-C/J/G/F/H）、战略条目有 ID（S-PR/ST/BS）、优先级、归属（M3/M1/V5+）、M3 现状 |
| P0 清单 | M3 可执行子集单独列出，与 GUA-029 边界说明 |
| 交叉引用 | 链到 `01_basic_principles.md`、`02_strategy_overview.md`、`03_basic_strategy.md`、`guandan-knowledge.mdc`、`06_game_flow.md` |
| 代码 | **不要求**；后续 M3 P0 另开迭代行，V5 待挂接条件满足 |

**关单条件（GUA-030）**：映射表评审通过 + 在 `ITERATIONS.md` 登记；M3/V 实现进度由 **GUA-029** 及未来 V5 条目跟踪，**不阻塞 GUA-030 closed**。

> **已关单**（2026-05-31）：用户确认三篇映射表 OK。

## GUA-031 完成定义（传牌 guard + 队友让道 · M3）

> 真源 [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) §8.4、§十七 **TT-P10**、[`01_passing_skills.md`](../knowledge/skills/03_assist_attack/01_passing_skills.md)、[`07_two_trips_skills.md`](../knowledge/skills/04_common_skills/07_two_trips_skills.md)。**与 GUA-029 正交**（不放宽炸弹/三带二拆牌保护）。

| 项 | ID | 完成标准 |
|----|-----|----------|
| 队友让道 | **P-F02 / PASS-P01** | 被动：`_Trips`、`_ThreePair`、`_TwoTrips`、`_Straight`、`_StraightFlush` 在 `_is_teammate_greater` 且非冲刺场景 **return 0**（与 `_Single/_Pair/_ThreeWithTwo` 对齐） |
| 送小单 | **PASS-P02** | `_active`：`numoffri==1` 且 actionList 含 `Single` → 出 **最小点** Single（非 PASS） |
| 防送炸 | **PASS-P03** | `_active`：`numofnext==1` → 禁出过小单（首发与末段 `single_actionlist` 均覆盖）；无更大牌型时才 fallback |
| 逢五喂队友 | **PASS-P04** | `_active`：`numoffri==5` → `Pair`/`ThreeWithTwo` 升权于 `Single`/小顺（弱推断，`confidence=low`） |
| 测试 | — | 新增 `tests/test_m3_gua031.py`（≥6 case：P02/P03/P04 + 至少 2 牌型 P-F02）；GUA-026/027/028/029 回归 **不回归** |
| 批跑 | — | 可选：净盘 M3 ≥5 对，记录 `numoffri∈{1,5}` / `numofnext==1` 步决策分布 |

**关单条件**：上述 4 条 guard + pytest 通过；**不要求**队胜率达标（队胜率以 **M3 批跑**观测为准，见 `ITERATIONS`）。

## GUA-032 完成定义（记牌 + 算牌 · M3）

> 真源 [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) **§十四（怎么算）**、**§十五（记什么）**、**§二十二（孤张定律 CG-T06）**；[`04_calculation_skills.md`](../knowledge/skills/04_common_skills/04_calculation_skills.md)、[`04_card_grouping_skills.md`](../knowledge/skills/07_opening/04_card_grouping_skills.md)、[`05_memory_skills.md`](../knowledge/skills/04_common_skills/05_memory_skills.md)。

| 项 | ID | 完成标准 |
|----|-----|----------|
| 基建 | — | `_update_play_state` 后 **`remain_cards_classbynum` 与 `remain_cards` 一致**（2468 计数法可派生） |
| 记炸 | **MEM-M02** | 每 `[pos]` 维护 `has_bomb` / `max_bomb_rank`（扫 `history.send`） |
| 排除四炸 | **CALC-M01**（=MEM-M04） | 某点数外剩 ≤3 张 → 被动不回该点 `Bomb` |
| 5/10 关键张 | **CALC-M03**（=MEM-M03） | 点数十外剩 0 → 降权大顺；点五外剩 0 → 降权小顺 |
| 进贡无级牌 | **CALC-M02** | 进贡无级牌对手 + `numofnext==1` → `_active` 禁过小单（可合并 **P-H01**） |
| 测试 | — | `tests/test_m3_gua032.py`（≥5 case，含 MEM+CALC）；GUA-027/028/029/031 回归不失败 |

**关单条件**：基建 + M01/M03 必达；M02 可与 **P-H01** 迭代合并关单。**不要求** V5 级完整算牌（§14.3）。

## GUA-033 完成定义（M3 批末 victoryNum / gameResult）

> 根因核查 **2026-05-31**：客户端混处理 `gameOver`/`gameResult`/`episodeOver`（已修）；**平台侧**见 [`platform-data-interpretation.md`](../knowledge/platform-data-interpretation.md) **§2**——本包 exe **argv 无效**，单次会话 **固定 3 局**，致 `batch_games=1` 时 WebSocket `[0]+[1]=3`。

| 项 | 完成标准 |
|----|----------|
| **解析** | 对齐 M1：`gameOver` **早退**不写 `victoryNum`；`gameResult` 读 **`final` 与/或 `victoryNum`**（以本机 WebSocket 真包为准）；禁止从 `episodeOver` 误用 `result[4]` |
| **日志** | `stage==gameResult` 打 **RAW JSON** 一行（可 `DEBUG`）；batch 日志可对照 `0号位胜利` |
| **回填** | 仅在本批 **`[0]+[1]==batch_games`** 且同队 `[0]=[2]`、`[1]=[3]` 时 `backfill`；批间 **清空 `pending_result_files`** |
| **校验** | 客户端或 executor **批末自检**：`victoryNum` 与 `execution_state` 本批 `batch_games` 一致，否则 **WARNING + 不计胜率** |
| **测试** | `tests/test_m3_gua033.py`（≥4 case：gameOver 无 vn、gameResult+final、backfill 范围、批末校验） |
| **验收** | 净盘 `--target-games 10` **4 批**满跑：每批末 `[0]+[1]` = 该批 `batch_games`；批 4 末条 **≠** 批 1/2 的 `[2,1,2,1]` 除非本批确为 3 局 |

**关单条件**：上述解析 + 测试 + **一次** 10 局满跑批末 vn 全批自洽。**不要求**队胜率达标（队胜率以 **M3 批跑**观测为准）。

**已关单（2026-05-31）**：矩阵 1/3/10 净盘；批 4 `[0]+[1]=1`；详见 [`gua033-batch-matrix-2026-05-31.md`](../analysis/gua033-batch-matrix-2026-05-31.md)。

## GUA-033 平台侧根因：v1006 exe argv 实测（定音，2026-05-31）

> 与 PDF 说明书「`exe N` → `settingTimes=N`」**不一致**；属 **离线 exe 实现**，非本仓库启动脚本写死 3 局。

| 项 | 结论 |
|----|------|
| **配置文件** | `windows/` 目录 **无** ini/json 覆盖 argv |
| **argv 1 / 3 / 10** | WebSocket 均为 **`settingTimes=3`**，`curTimes=1→2→3`，会话 **固定 3 平台局** |
| **`gameResult.victoryNum`** | 按 **3 局**累计 → `[0]+[1]=3`；`batch_games=1` 时与台账冲突 **可预期** |
| **批跑脚本** | `restart_manager` 传参正确；`completed_games` = **会话完成次数**（意图口径），≠ WebSocket 实际局数 |
| **客户端对策** | **`current_batch.json` → `batch_games`** 校验；失败 → **gameOver 本地计数 fallback**（已实现） |
| **复测** | `python scripts/tools/probe_exe_argv_ws.py --compare` |
| **真源** | [`platform-data-interpretation.md`](../knowledge/platform-data-interpretation.md) **§2** |

**后续**：若更换平台 exe，须重跑 §2 矩阵再定音；向南邮反馈 argv 无效时可附本节与探测 JSON。

## GUA-034 完成定义（残局拦头游 · M3 guard 切片）

> 复盘定音 **2026-06-01**：round 38 yf2 末段（`replay_word.md` 成对牌谱）。**与 GUA-026 边界**：GUA-026 禁三带二**常态拆炸弹/级牌 trips**；GUA-034 允许在 **队友已走完（1v2）** 且 **对手将一手走光** 时**定向拆 trips/对子压牌或走 GUA-029 R3**，二者不冲突。

| 项 | ID | 完成标准 |
|----|-----|----------|
| 模式识别 | **END-M01** | `numofplayers[(myPos+2)%4]==0`（或等价：队友 `publicInfo.rest==0`）→ 进入 **solo_sprint** 分支（不再走 GUA-031 队友让道） |
| 接风首出 | **END-M02** | `solo_sprint` + 接风 `_active`（`greaterPos==-1`）+ `numofmy<=12`：优先 **ThreeWithTwo / Trips / Pair**，**禁止** `rankone/ranktwo` 为清小点而 **拆对出最小 Single** |
| 被动压小牌 | **END-M03** | `solo_sprint` + `_Single` 跟对手小单：允许从 trips **拆单** 压牌（≥对手点），不限于 `single_member` |
| 被动压对子 | **END-M04** | `solo_sprint` + `_Pair` 跟对手对子：允许 **拆 trips 凑更大对** 或走 **GUA-029 R3**（`numofplayers[greaterPos]<=7` 且无可跟） |
| 测试 | — | `tests/test_m3_gua034.py`（≥4 case：END-M02 接风、END-M03 压单 6、END-M04 压对 6 / R3 兜底）；GUA-026/029/031 回归 **不回归** |
| 验收 | — | 样例局 102–106 步决策与上表一致（可 replay 构造）；可选：净盘 M3 ≥3 局记录 `numoffri==0` 末段 PASS 率下降 |

**关单条件**：END-M01–M04 + pytest 通过；**不要求**队胜率达标（队胜率以 M3 批跑观测为准）。

**不在范围**：完整 lalala「两手牌组合枚举」（见 M3_DIAGNOSIS BUG2 全量移植 → **V5+ / 后续迭代**）。

## GUA-035 完成定义（END-M02+ · solo 接风对手剩张过滤）

> 登记 **2026-06-01**：GUA-034 END-M02 的 M3 续切片；**不**含两手规划（→ V5+）与「可回收单张」完整评分（→ V5+）。

| 项 | ID | 完成标准 |
|----|-----|----------|
| 对手扫描 | **END-M02+-01** | solo_sprint + 接风 `_active`：取两家对手 `(myPos±1)%4` 的 `numofplayers`，非队友 `(myPos+2)%4` |
| 剩 1 张 | **END-M02+-02** | 任一对手 `rest==1` → `_gua034_solo_active_pick` **跳过 Single**（及 rank 拆单路径）；仍允许三带二/三张/对子等整手 |
| 剩 2 张 | **END-M02+-03** | 任一对手 `rest==2` → **跳过 Pair**；仍允许三带二/三张等 |
| 剩 5 张 | **END-M02+-04** | 任一对手 `rest==5` → **优先跳过 ThreeWithTwo**；若过滤后无合法整手，**fallback** 仍出三带二 |
| 测试 | — | `tests/test_m3_gua035.py`（≥4 case：1/2/5 张过滤 + fallback）；GUA-034/026/029/031 回归 **不回归** |
| 验收 | — | 构造用例 + round 38 类 solo 接风 replay 片段；不要求队胜率关单 |

**关单条件**：END-M02+-01–04 + pytest 通过。

## V5+ priority（GUA-034 后续 · 不在 M3 本轮）

> 登记 **2026-06-01**；与 [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) P1+→V5+ 对齐。

| 优先级 | 主题 | 来源 | 说明 |
|--------|------|------|------|
| **V5+-01** | lalala **两手走完枚举 + 首出选优** | GUA-034 讨论 ②、[`M3_DIAGNOSIS.md`](M3_DIAGNOSIS.md) BUG2、方向 E/C | `numofmy<=12` 枚举 actionList 两手组合；选「第一手难被压、第二手清牌」（如 `99933`→`10101044`）。lalala 参考实现有 **sort 比较 bug + 候选未消费**（见 `reference/lalala/action.py:1117–1127`），移植须重写而非直抄 |
| **V5+-02** | solo 接风 **可回收单张** 优先级 | GUA-034 讨论 ③ | 混型手牌：级牌/王/大单可先出试探；与 END-M02+-02（对手剩 1 禁小单）联合定优先级表 |
| **V5+-03** | 方向 E 轻量模板 | [`GUA-034-方案评审.md`](GUA-034-方案评审.md) | `solo_sprint && numofmy<=8`：2–3 种固定两手模板（三带二+剩余等），介于 M3 guard 与 BUG2 全量之间 |

## 来自「比赛汇总」的说明（非缺陷）

`docs/掼蛋AI相关比赛汇总.md` 主要为**南邮平台与赛事索引**，不记载本仓库逻辑缺陷；参赛与平台 JSON/WebSocket 对齐请在迭代中当作**环境约束**验收（不必单列 GUA，除非出现协议不符）。

## 模板（新增行时复制）

| ID | 状态 | 严重级别 | 标签 | 版本 | 简述 | 现象 / 复现要点 | 涉及模块 | 备注 |
|----|------|----------|------|------|------|-----------------|----------|------|
| GUA-xxx | open / closed | P0–P3 | rules, observation, policy | m1/v4/v5/v6/训练/docs | | | | `closed_in` / `duplicate of` |
