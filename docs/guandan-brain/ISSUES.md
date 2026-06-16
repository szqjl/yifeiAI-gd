# 缺陷登记簿（Defect Register）

> 编号规则：`GUA-001`、`GUA-002`… **永不复用**。关闭后若复发，新开编号并 `duplicate of GUA-xxx`。  
> **状态**以文档与提交为准；后续在表中直接维护。  
> **来源扫描**（写入本条时已对照）：`docs/掼蛋AI相关比赛汇总.md`、`docs/reports/README_优化项目.md`、`docs/reports/YF掼蛋优化实施报告.md`、`docs/guandan-brain/notes/WORKFLOW_RESTART_LOG.md`、`logs/`（含 `yf*_m1_*.log`、`batch_executor_*.log` 等）。

## 引擎维护策略（定音 · 2026-05-31 · 评审确认）

| 引擎 | 定位 | 维护状态 |
|------|------|----------|
| **M1** | 首个实验 AI（`yf1_m1` / `yf2_m1` + `src/decision/`） | **frozen**（**GUA-022 closed**）— **非交付线**；**勿再开 M1 策略 GUA**；仅 **bugfix**（crash / 协议 / 记录）与 **pytest 回归** |
| **M3** | **主交付** + **`IDecisionProvider` 底座**（`yf1_m3` / `yf2_m3`、`src/m/m3/`、`src/contracts/`） | **active** — 策略迭代、批跑 KPI、GUA-026+ 跟踪 |
| **V7** | NN 实验线（`yf1_v7` / `yf2_v7` + `UltimateWinRateEngineV7`） | **active**（`v7-dev`）— **GUA-037+** 改造；**队胜率 KPI 观测**见 `ITERATIONS` V7-007；**禁止 import `src.m.m3.*`**（见 `V7-实施方案.md` §1.2） |
| **V5+** | 组牌 / 牌力 / 知识层长期路线 | 规划 / 按需 — **P0 以外**的组牌与牌力评估 **不走 M3 硬编码扩张** |

**队胜率 KPI**：自 **2026-05-31** 起**只看 M3 批跑**。**多样本观测**（净盘、同 exe）：S1 **7/10**、S2 **11/12**、S3 **8/10**、S4 **8/10** → **合计 34/42（81.0%）**（见 `ITERATIONS`「M3 队胜率多样本观测」）。M1 净盘 **0/12** 为 frozen 基线对照，**非**口径错误。

### 实现分工（评审定音）

| 优先级 / 能力 | 落点 | 说明 |
|---------------|------|------|
| **P0 guard**（可 pytest + 批跑验收的 if-guard） | **M3**：`src/m/m3/m3_decision_engine.py`（及 `m3_utils.py`）；**V7**：`src/decision/ultimate_win_rate_engine_v7.py` 内 **V7-native** 过滤壳（**GUA-045**，不 import M3） | 与 [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) **M3 · P0** 一致；V7 原则对齐见 **GUA-045** §缺陷分类 |
| **组牌 / 牌力 / 混合决策** | **V5+**（`src/v/`、V 挂接 `IDecisionProvider`） | 不在 M3 引擎内堆整篇策略；M3 保持 lalala 式 guard + 契约底座；V7 组牌类见 **GUA-045** Phase 2 / **V5+-04** |
| **M1 共用层** | `src/decision/`（frozen） | 历史 PHASE2 与 V shim；**不接新开策略迭代** |

### 复盘发现 → 实现 → 验收（定音 · 2026-06-01）

掼蛋 **重配合、高策略、牌型多样**；108 张均分 4 家时，**两次发牌完全相同**的概率约 **\(10^{-58}\)** 量级（\((27!)^4/108!\)），**具体 replay 步数几乎不会复现**。因此：

| 层级 | 该做什么 | 验收 |
|------|----------|------|
| **M3** | **原则型 guard**（夺权压顺、接风不拆结构、队友在时跟对/别乱单 等） | **`pytest` 构造态** + 回归；replay 仅作**发现缺陷的样例**，**不得**以「再跑某批某副牌」为关单 pass 标准 |
| **V5+** | **222333+顺子+炸弹** 等 **整手结构** 与 **多步配合** / 搜索 | 组牌枚举 + 牌力；因局面几乎不重复，才需要 V 系列 |

真源详表：[`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) §「复盘与验收理念」。

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
| GUA-036 | closed | P1 | policy | m3 | M3 **控权 + 接风配合**（非 solo） | batch7 round38 复盘：**①** 接风拆 2 打单，未跟队友对子线；**②** 敌出杂顺可压却 PASS，让权后对手连走。**根因**非「缺顺子函数」，而是 guard 缺口 + `_Straight` 过窄。**related** **GUA-031**（喂牌/让道）、**GUA-032** CALC-M03（被动夺权豁免）、**GUA-034/035**（仅 solo） | `m3_decision_engine`：`_active` 接风、`_Straight` | **closed_in** 2026-06-01（GUA-036 实施）；样例 `replay_word.md` / batch7 round38 **不作关单标准**；**KPI 观测 note**：GUA-034/035 合计 33 局（8 批）出现 **3 次 `[3,0,3,0]`**（批2/3/8，3局全胜各拉高均值），GUA-036 合计 57 局（S6/S7/S8 + 06-01 两次净盘共 5 次 12 局）**仅 S6 出现 1 次 `[3,0,3,0]`**（批1/3），其余各批均为 `[2,1]` 或 `[1,2]`，缺少全胜批导致 GUA-036 样本均值（61.1%）低于 GUA-034/035（78.8%），但 30 局累计仍显著 >50%（73.3%，p<0.01）。方差属发牌随机波动，非 GUA-036 代码引入。

**统计检验 note（2026-06-02 补充，2026-06-02 夜 确认结论）**：GUA-034/035 26/33=78.8% vs GUA-036 36/69=52.2%（S9后），**差值 26.6pp，p=0.009（两比例 z 检验），统计显著**；95% CI [8pp, 45pp]。**关键差异**：`[0,3,0,3]` 在 GUA-036 出现 **2 次**（S8批5、S9批2），GUA-035 出现 **0 次**——GUA-036 下限更差，lalala 队有批能把 M3 队剃光头。批次均值 t 检验 p=0.048（边缘显著）。**结论**：GUA-036 **显著差于** GUA-035，非发牌随机波动可解释，待 CALC-M04/M05 修复。 |

| GUA-037a | closed | P0 | V-nn, v7 | v7 | V7 静态特征工程（state_牌态 124 维） | `_extract_features` 静态部分全零填充；需重写手牌 108 维 + 级牌/红心配 9 维 + 主动被动/阶段/炸弹/贡局/队友 6 维 + hand count 1 维 = 124 维；actionList 牌型 15 维后移 | `src/v/nn/ultimate_win_rate_engine_v7.py`、`src/v/nn/features/static_features.py` | `closed_in` 2026-06-07：124 维静态特征提取模块实现（`static_features.py`），V7 引擎 `_extract_features` 前 124 维替换零填充；13 项 pytest 验证通过；关联 V7-实施方案.md §2 Phase 1 |
| GUA-037b | open | P1 | V-nn, v7 | v7 | V7 动态特征工程（LSTM 历史编码） | 在 037a 静态特征基础上叠加 LSTM 历史编码（出牌历史 + numof* 序列），目标总维度 188 维 | `src/v/nn/features/dynamic_features.py`、`src/v/nn/ultimate_win_rate_engine_v7.py` | 完成定义见 `V7-实施方案.md` §2 Phase 1 GUA-037b；可与 GUA-038 并行 |
| GUA-038 | **closed** ✅ | P1 | V-nn, v7 | v7 | V7 M3 知识蒸馏（BC 热启动） | V7-internal 录牌（不依赖 M3 录牌链路）→ 提取 (state, action) 标签对 → BC 训练 → 加载推理；teacher 数据源为 M3 离线 game_records | `src/v/nn/recorder/v7_recorder.py`、`src/v/nn/training/bc_dataset.py`、`src/v/nn/training/bc_trainer.py`、`scripts/v7/run_bc_training.py` | **`closed_in` 2026-06-07**：V7-internal 录牌器（`v7_recorder.py`）+ BC 数据集（`bc_dataset.py`）+ BC 训练器（`bc_trainer.py`）+ CLI 入口（`run_bc_training.py`）；考试通过：`tests/test_v7_bc.py` **34/34 passed**；回归 72 passed；验收标准：数据加载、特征重建、train/val 切分、masked CE、录牌落盘全部覆盖 |
| GUA-039a | open | P2 | V-nn, v7 | v7 | V7 自对弈 DMC + ZMQ 桥 + Actor 原型 | 搭建 V7 自对弈基础设施：DMC value net 训练 + ZMQ Actor-Learner 通信 + 单 Actor 与 v1006 平台交互原型 | `src/v/nn/training/actor.py`、`learner.py`、`replay_buffer.py`、`zmq_bridge.py`、`reward.py` | 完成定义见 `V7-实施方案.md` §2 Phase 3 GUA-039a；**关单前提**：评审后方可启动 GUA-039b |
| GUA-039b | open | P2 | V-nn, v7 | v7 | V7 自对弈 top-K + PPO + 30 局评估 | 在 039a 基础上叠加 top-K=2 过滤 + PPO policy net + 两阶段 30 局 lalala 评估基线（含 fallback baseline） | `scripts/v7/eval_vs_lalala.py`、`src/v/nn/training/learner.py`（PPO 扩展） | 完成定义见 `V7-实施方案.md` §2 Phase 3 GUA-039b；仅在 GUA-039a 关单后启动 |
| GUA-040 | open | P1 | V-nn, v7 | v7 | V7 模型权重管理（COS manifest + 版本切换） | 搭建 V7 模型权重的 COS 上传/下载/版本切换基建，遵循治理 §6.3 目录规范 | `models/v-nn/manifest.json`、`scripts/v7/weight_manager.py`、`scripts/cos/upload_v7_weights.py`、`download_v7_weights.py` | 完成定义见 `V7-实施方案.md` §2 Phase 1 并行 GUA-040；与 Phase 0 + Phase 1 全部并行 |
| GUA-041 | **closed** ✅ | P1 | V-nn, v7 | v7 | V7 路径债清理 | 消除 V7 客户端与启动器中的 D 盘硬编码路径债，使 V7 在本机任意目录 clone 后可开箱即用 | `config/v7_paths.yaml`、`src/utils/v7_paths.py`、`start_v7_complete.py`、`START_V7_*.bat` | **`closed_in` 2026-06-05**：pytest 6/6 passed；D 盘硬编码在 GUA-041 范围内清零；跨平台 subprocess 由用户在 Windows 下批跑 |
| GUA-042 | **closed** ✅ | P1 | V-nn, v7 | v7 | ABL-GD 168 伪动作评估（含开源可行性） | 调研 ABL-GD（CCFAI 2025）168 伪动作方案的可获取性与可移植性，给出采纳/弃用/备选结论；仅调研 + 写结论文档，不实施 | `docs/analysis/abl-gd-eval-2026-06.md` | **`closed_in` 2026-06-07**：结论为弃用该方案，作为备选跟踪；详见评估报告 `docs/analysis/abl-gd-eval-2026-06.md` |
| GUA-043 | **closed** ✅ | P1 | V-nn, v7 | v7 | 专利规避设计审计（CN113018837A 边界） | 审计掼蛋 AI 算法专利 CN113018837A 的权利要求边界，识别 V7 Phase 1-3 实施中被覆盖的子模块，给出规避方案；仅调研，不改代码 | `docs/governance/patent-audit-cn113018837a.md` | **`closed_in` 2026-06-07**：结论为 V7 核心技术路径与专利无实质重叠，仅需对动态分组优化模块做规避设计；详见审计报告 `docs/governance/patent-audit-cn113018837a.md` |
| GUA-044 | **closed** ✅ | P1 | observation, infra | v7, m1, m3, batch | **批跑四席未就绪即开局 + 首局空等卡顿** | **现象**（V7 批跑 `logs/v7_vs_lalala_20260606_102117.log`）：`wait_for_clients_connected` 在 Windows 新控制台启动下误报 **0/4** 仍继续；**第 4 席连上即开局**（v1006 规则），client4 ~10:22:10 连入、局 ~10:22:11 开始；yf2 `actIndex=9` 于 10:22:13 已回包后 **~51s** 无新 `act`（yf1 同步空窗），似等 lalala/平台。**根因**：批跑侧连接检测不可靠 + 末席连入前前三席未门闩。**非** V7 决策超时（无 `决策超时` 日志） | `batch_executor/client_ready.py`、`websocket_manager.py`、`lalala_adapter.py`、`restart_manager.py`、`executor.py` | **`closed_in` 2026-06-06**：四席就绪门闩 + 就绪表；`tests/test_client_ready.py` **3 passed**；见 `ITERATIONS` 2026-06-06 GUA-044 行、§GUA-044 完成定义 |
| GUA-045 | **closed** ✅ | **P0** | policy, v7 | v7 | **V7 决策根因：零特征模型 + 无 P0 Guard** | **统一根因**：`UltimateWinRateEngineV7` 对 `actionList` **argmax**；`_extract_features` **无 108 维牌面**（→ **GUA-037a**）；**零条**队友/最小炸/组牌 guard；回退「首个非 PASS」。**发现样例**（`20260606121245769675`，replay 仅作缺陷分类，**不作关单 pass**）：炸队友顺子、5 炸 9 压单 2、5 张 A+红 2 压 4Q、顺子漏带单 6、应压 PASS、拆钢板出对 7 等 → 见 **§GUA-045** 缺陷分类表 | `src/decision/ultimate_win_rate_engine_v7.py`；`src/v/nn/guards/v7_guards.py` | **`closed_in` 2026-06-07**：V7-native `filter_action_list` + `validate_decision`（V7-R01~R06 全部实现）；`decide()` 接入 guard；`tests/test_v7_gua045.py` **24/24 passed**；回归 48 passed；见 §GUA-045 关单条件 |
| GUA-046 | open | P3 | observation, infra | v7, m1, m3, batch | **副间 ~10s 停顿（服务器内在结算/发牌间隔）** | V7 批跑日志显示每副牌决策集中在 **1 秒内**打完，之后服务器进入 **~10s** 无消息空窗期（episodeOver → 算分 → 贡还 → 发牌 → 下一副 act）。非 V7 客户端问题——M1/M3 同样经历该间隔，只是 GUI 模式下不如 cmd 窗口显眼。**对比验证**：`RUN_V7_VS_LALALA.bat` cmd 窗口停顿 10s 光标不动；`batch_executor_gui_m3.py` 同服同客户端架构，日志框缓冲不觉。**根因**：`guandan_offline_v1006.exe` 内置固定副间结算流程，客户端无法控制。 | 无（服务器行为） | **订正 2026-06-07**：GUA-047 原"4 席全停 20s"误判已 closed；本条恢复原状，仅保留副间/开局 18s 等待等**已确认服务器行为**的观察 |
| GUA-047 | **closed** ✅ | **P1** | observation, infra | v7, m1, m3, batch | **【误判关单】** ~~同副牌内 4 席全停 ~20s（根因待定位，非副间结算）~~ → **实际是 batch_executor 日志 dump 延迟，非真停摆** | 2026-06-07 V7 批跑 cmd 窗口观察（`docs/analysis/批跑cmd窗口观察.md`）：**原报告"4 席全停 20s"经实测为误判**。**根因复盘（13:55:28 批跑对照，Opencode 协助）**：`batch_executor/restart_manager` 将服务器 stdout **延迟 dump** 到 `v7_vs_lalala_*.log`（13:56:35 出的 actIndex 在主日志中 13:57:48 才出现，延迟 73s）；**实际 4 席节奏完全同步**——yf1_v7=342 / yf2_v7=340 / lalala client3=333 / lalala client4=311 条 actIndex 在 13:56:35-13:57:57 之间持续输出，无任何一端掉队；13:57:58-13:58:31 整段 0 条 send 才是真停（dump 落幕 + 本局结束）。**12:29 那次"暂停 20s"同模式**——15 条决策同 1 秒出完也是 dump 延迟假象。**不构成"4 席全停"现象**。 | `docs/analysis/批跑cmd窗口观察.md`；`logs/v7_vs_lalala_*.log`；`batch_executor/restart_manager.py`（dump 延迟根因） | **closed_in 2026-06-07**：原 GUA-047 误判已订正，根因为 `batch_executor` stdout 缓冲/dump 时机问题（**非**服务器/客户端卡顿，**非**副间结算间隔）。**下一步建议**：新开 **GUA-048** 跟踪 `batch_executor` 日志 dump 延迟（73s 量级，会拉低 V7-007 KPI 观测的实时性） |
| GUA-048 | open | P2 | observation, infra | v7, m1, m3, batch | **批跑 73s 卡顿：客户端 game_ready 写盘超时（根因 A）+ ServerStdoutReader 启动晚于 game_ready 超时（根因 B）双根因** | 2026-06-07 V7 批跑（`v7_vs_lalala_20260607_205759.log` 20:57 启动）**21:00 复盘**（13:55 + 20:57 双批跑对照）：**73s 卡顿 = 60s game_ready 超时 + 13s dump 落幕叠加**。**实测数据**：主日志 20:59:09~21:00:10 区间只有 8 条 batch_executor 自日志、**0 条 [服务器] 标签输出**（ServerStdoutReader 还没启动）；21:00:10 dump 落幕后才有 [服务器] 日志。**根因 A**（主因）：`batch_executor/executor.py:514` `wait_for_all_clients_game_ready(timeout=60)` **60 秒硬超时**——4 席客户端在 `server:96 20:59:07` 收到 game_start 后未在 60s 内写 `batch_executor/game_ready.json`。**根因 B**（次因）：`ServerStdoutReader` 在 `executor.py:547` 才 `start()`（line 512 game_ready 60s 超时之后），**前 60s 服务器输出全丢**。**trae 误关单**：trae 创建 `batch_executor/server_stdout_reader.py` + `tests/test_batch_stdout_reader.py`（20:37，untracked），b5df0bc commit（20:50）改 executor.py 用 `async for`，**但未实测就把 GUA-048 标 closed ✅**——dump 延迟 60s 实际仍存在。**影响**：V7-007 KPI 实时性 + 队胜率采样有效时间**双受损**；M1/M3 批跑同链路同问题。 | `batch_executor/client_ready.py:180`（`wait_for_all_clients_game_ready`）；`batch_executor/executor.py:514`（timeout=60）；`batch_executor/executor.py:547`（ServerStdoutReader.start 时机晚）；`src/communication/lalala_adapter.py`（`mark_game_ready` 调用）；`logs/v7_vs_lalala_20260607_205759.log`；`logs/batch_executor/game_ready.json` | **登记 2026-06-07**（P2，回退 open）；**双根因**：① 客户端 `mark_game_ready` 写盘耗时 > 60s 触发 batch_executor 超时；② `ServerStdoutReader.start()` 在 `wait_for_all_clients_game_ready` 之后才启动，前 60s 丢弃。**关单条件**：① game_ready 写盘 < 10s 全部 4 席（实测基线）；② ServerStdoutReader 在 `executor.py:488`（四席 WS 连接就绪）后**立即**启动，dump 延迟 ≤ 5s；③ pytest 覆盖 `tests/test_game_ready_timing.py` + `tests/test_server_stdout_reader_startup.py`；④ 跑 ≥3 局批跑实测 dump 延迟 ≤ 5s 验收；⑤ M3/M1 批跑回归不破坏。**相关**：GUA-047（误判关单的根因）；GUA-046（副间 ~10s 观察，仍 open）；**GUA-049**（game_ready 写盘慢专条，P1） |
| GUA-049 | open | **P1** | observation, infra | v7, m1, m3, batch | **【根因锁定】** 客户端 `mark_game_ready` 写盘 4 进程 race condition，3 子根因：`game_ready.json` 缺 entry 触发 60s 硬超时 | 2026-06-07 V7 批跑（`v7_vs_lalala_20260607_205759.log` 20:57 启动）**22:00 实测**：`batch_executor/game_ready.json` 20:57 批跑后**只有 3 entry**（client3/4 + yf1_v7，**缺 yf2_v7**），单 mtime `20:59:06.519339`。**子根因 A1**（主因）：`batch_executor/client_ready.py:231` `_game_save` 用 `Path.write_text` —— **Windows/Linux 都非原子写**，4 进程并发 _game_load + _game_save 产生中间态 JSON 损坏。**Linux 复现**（`/tmp/race_test` 4 线程 × 50 循环）：`[c2] error: Expecting ',' delimiter: line 1 column 112 (char 111)` —— **JSON 损坏确认**。**子根因 A2**：`mark_game_ready` (`client_ready.py:52`) **无 try/except** + `websocket_manager.py:276` 用 `asyncio.to_thread` —— **异常被 asyncio 静默吞掉**（task exception never retrieved 默认不打印），失败无任何日志。**子根因 A3**：`wait_for_all_clients_game_ready` (`client_ready.py:180`) `expected.issubset(ready.keys())` **期望 4 entry 全到**，`executor.py:514` `timeout=60` —— **差 1 就 60s 超时**。**因果链**：4 席 mark_game_ready 并发 → yf2_v7 entry 写丢（race） → 60s 等不到 → executor WARNING → ServerStdoutReader 晚 60s 启动 → dump 落幕 13s → 73s 卡顿。**根因复盘**：参见 `docs/analysis/gua-049-根因锁定-2026-06.md`（10KB，证据链 + Linux 复现 + 修复方案 + 教训）。**trae 误关单**（GUA-048）：trae 看到 `tests/test_batch_stdout_reader.py` passed 就 closed，未实测 dump 延迟是否真消除。 | `src/communication/lalala_adapter.py`（`mark_game_ready` 调用）；`src/communication/websocket_manager.py:276`（`asyncio.to_thread(mark_game_ready, ...)`）；`src/communication/yf1_v7.py` / `yf2_v7.py`（`handle_game_start` → 触发 mark_game_ready）；`batch_executor/client_ready.py:52`（`mark_game_ready` 写盘）；`batch_executor/client_ready.py:231`（`_game_save` 非原子写）；`batch_executor/game_ready.json`（mtime 落盘时间戳）；`tests/test_game_ready_race.py`（待 Opencode 写） | **登记 2026-06-07**（P1，根因已锁定）；**3 子根因**：① `_game_save` 非原子写（A1 主因）；② `mark_game_ready` 无 try/except + asyncio 静默异常（A2）；③ `wait_for_all_clients_game_ready` 期望 4 entry + 60s 硬超时（A3）。**关单条件**：① 修 A1：`temp + rename` 原子写（`Path.write_text` → `tmp.write_text + tmp.replace`）；② 修 A2：`mark_game_ready` 加 try/except + logger + `await asyncio.to_thread(...)` caller 端 catch；③ 修 A3 可选：维持 4 entry 期望（A1+A2 修好后 100% 满足）；④ pytest 覆盖 `tests/test_game_ready_race.py`（4 进程并发 100 次，0 JSON 损坏 + 4 entry 都在）；⑤ 跑 ≥3 局批跑实测 `executor.py` 日志 `✓ 所有客户端已收到首条游戏消息` 出现且无 WARNING；⑥ M3/M1 批跑回归不破坏。**相关**：**GUA-048**（双根因父条，含 根因 B = ServerStdoutReader 启动晚）；GUA-047（误判关单的根因）；GUA-046（副间 ~10s 观察，仍 open） |

| GUA-050 | open | **P0** | V-nn, v7 | v7 | **局面信念向量 8 维**（扩展 GUA-037a） | V7 需从 `P(action|state)` 升级为 `P(action|state, belief)`。在 037a 静态特征后叠加 8 维信念：my_strength/partner_strength/opponent_pressure/level_progress/trump_ready/bomb_count/opponent_bomb_risk/last_card_meaning。解决套路文档 §1「标准 RL 无信念中间变量」的根本问题。 | `src/v/nn/features/static_features.py`、`src/decision/ultimate_win_rate_engine_v7.py` | **登记 2026-06-16**（P0，GUA-037a 扩展）；来源于 `docs/analysis/v7-re-eval-2026-06.md` §2.2；特征维数 124→132；风险：信念不收敛→降为 4 维核心。**完成定义**：信念向量在线推理 ≤1ms；pytest ≥6 case；V7 净盘 3 局观测（不作关单） |
| GUA-051 | open | P1 | V-nn, v7 | v7 | **稠密 Reward 信号 9 种**（扩展 GUA-039a） | 在 GUA-039a reward.py 基础上增加 9 种中间 reward：出牌成功+0.05/接风+0.1/掼蛋+0.3/级牌控制+0.2/配合+0.1/送对家+0.15/炸弹±0.5/本方升级+2.0/对方升级-1.0。解决纯输赢 reward 太稀疏导致信用分配困难（套路文档§4）。 | `src/v/nn/training/reward.py`（待建） | **登记 2026-06-16**（P1，GUA-039a 扩展）；来源于 `docs/analysis/v7-re-eval-2026-06.md` §3.1；**完成定义**：reward.py 实现 9 种信号 + 单元测试；与 GUA-039a 自对弈管道集成 |
| GUA-052 | open | P1 | V-nn, v7 | v7 | **108 张牌全量追踪 + 排除法推断**（扩展 GUA-037b） | GUA-037b LSTM 仅编码出牌历史序列，缺真正「记忆」。增补：已出牌（花色/点数）、对手/队友出牌牌型、各家剩张、级牌状态；排除法推断对手手牌（套路文档§3）。 | `src/v/nn/features/memory_tracker.py`（待建）、`src/v/nn/features/dynamic_features.py` | **登记 2026-06-16**（P1，GUA-037b 扩展）；来源于 `docs/analysis/v7-re-eval-2026-06.md` §3.2；风险：推理延迟可能 >50ms → 降为仅追踪剩牌+炸弹+级牌状态 |
| GUA-053 | open | P2 | V-nn, v7 | v7 | **对手池多样性**（扩展 GUA-039b） | 保留历史 checkpoint 对手池，每次 self-play 从对手池随机选，用 lalala 硬编码 bot 当固定训练对手。解决 self-play 策略多样性崩溃（套路文档§5）。 | `src/v/nn/training/opponent_pool.py`（待建） | **登记 2026-06-16**（P2，GUA-039b 扩展）；来源于 `docs/analysis/v7-re-eval-2026-06.md` §3.3；本项 P2（最低优先级），等 GUA-039a/039b 关单后启动 |

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
| GUA-036 | batch7 round38 复盘（[`ITERATIONS.md`](ITERATIONS.md)「batch7 replay」行）；[`08_straight_skills.md`](../knowledge/skills/04_common_skills/08_straight_skills.md) §控权；[`01_passing_skills.md`](../knowledge/skills/03_assist_attack/01_passing_skills.md)；**related** **GUA-031**、**GUA-032**、**GUA-034/035**（solo 边界）；[`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) §复盘与验收理念 |
| GUA-044 | [`platform-data-interpretation.md`](../knowledge/platform-data-interpretation.md) §局与副；[`服务器与客户端连接座位顺序排查.md`](../troubleshooting/服务器与客户端连接座位顺序排查.md)；**related** **GUA-033**（批跑 infra）、**GUA-008**（victoryNum 链路）；日志 `logs/yf2_v7_20260606_102201.log`（10:22:13→10:23:04 空窗） |
| GUA-045 | [`V7-实施方案.md`](V7-实施方案.md) §0–§2、[`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) §复盘与验收理念；**related** **GUA-029 R5**（M3 队友不炸，V7 须 V7-native 复刻语义）、**GUA-031 P-F02**、**GUA-014**（拆牌泛化）、**GUA-037a/b**、**GUA-038**、**V5+-04**；发现样例 `game_records/20260606121245769675 [yf2_v7]-…-[1]-[2].json`（**非**关单标准） |

---

## GUA-044 完成定义（批跑四席就绪门闩）

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

---

## GUA-029 完成定义（炸弹可执行规则包 R1–R6）

> 从 `01_bomb_techniques.md` 提炼、与 M3 现有观测字段对齐；**互不打架**，可写进 if-then，避免与 GUA-026 拆牌保护混淆。

| 规则 | 条件（M3 可观测） | 动作 | 文档依据 | 涉及模块 |
|------|-------------------|------|----------|----------|
| **R1** | `actionList` 含 `Bomb`/`StraightFlush` 且进入 `choose_bomb` | **先修** `choose_bomb`：点数读 `action[1]`（对齐 lalala 参考实现），同花顺分支一并查；单元测 v1006 格式 `['Bomb','8',[…]]` | 前置；不修则 R2–R6 均可能异常→PASS | `m3_utils.choose_bomb` |
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

## GUA-036 完成定义（控权压顺 + 接风配合 · M3 guard）

> 登记 **2026-06-01**：batch7 round38 复盘立项；**replay 为发现样例**，关单 **仅** pytest 构造态 + GUA-026/029/031/032/034/035 回归。**不**要求 batch7 再赢或逐步对齐某 replay。

| 项 | ID | 条件（M3 可观测） | 动作 | 文档 / 原则 |
|----|-----|-------------------|------|-------------|
| 被动夺权 | **CTRL-P01** | 被动 `_Straight`；`greaterPos` 为 **对手**（GUA-031 队友让道已 PASS 除外） | `actionList` 中任一 `Straight` **能压则压**，取 **最小够用**；**不**前置要求 `combine_handcards["Straight"]` 与 `action[-1]` 严格对齐 | 掼蛋 **控出牌权**；[`08_straight_skills.md`](../knowledge/skills/04_common_skills/08_straight_skills.md) |
| CALC 豁免 | **CTRL-P02** | 同上，被动压敌顺 | **GUA-032 CALC-M03**（5/10 降权）**不**阻止被动夺权（降权保留给 `_active` 首发顺） | STG-D01 与夺权冲突时 **夺权优先** |
| 接风禁拆 | **WIND-P01** | 接风（`greaterPos==myPos`）且 **`numoffri>0`**（**非** solo_sprint） | 若出单会 **拆 trips/钢板/炸弹成员**，且 `actionList` 有 **不拆结构** 的对/钢板/三带二 → **禁**该单，改出结构牌 | P-F02 配合；**GUA-026** 拆牌边界 |
| 跟队友线 | **TEAM-P01** | 接风 + **`numoffri>0`** + 本圈队友末手为 **Pair 或 Bomb** 且全场过到己 | 若存在 **不拆结构** 的 `Pair` → **优先于 Single** | PASS-P02 / 配合让道扩展 |
| 测试 | — | `tests/test_m3_gua036.py` | ≥4 case：**CTRL-P01**（敌顺+actionList 可压）、**WIND-P01**（接风禁拆 2）、**TEAM-P01**（跟对）、**CTRL-P02** 或队友顺子仍 yield **不回归** | 构造 `actionList`/`handcards`/`numofplayers`，**不**绑具体 game_id |
| 回归 | — | `pytest test_m3_gua036 + test_m3_gua031 + test_m3_gua032 + test_m3_gua034 + test_m3_gua035` | 全 pass | — |

**关单条件**：CTRL-P01–P02 + WIND-P01 + TEAM-P01 + pytest 通过。

**不在范围（→ V5+）**：

- **整手组牌**：222333 + 9–K 顺 + 444 配炸 + 多步配合规划 → **V5+-01/02**、[`04_card_grouping_skills.md`](../knowledge/skills/07_opening/04_card_grouping_skills.md) §二十二
- 重写 `combine_handcards` 多顺子槽 / 红配杂顺全局最优
- 「再跑 batch7 round38 须赢局或逐步一致」作 pass 标准

## GUA-045 完成定义（V7 决策根因 · P0 Guard 壳 + 改进路线）

> 登记 **2026-06-06**：V7 净盘 3 局 replay 复盘（`game_id=20260606121245769675`）。**定音**：108 张分 4 家，**同发牌复现概率 ≈ 0**（见上表「复盘发现 → 实现 → 验收」）；**不得**为该局手牌写特例策略；replay 步数仅用于**缺陷分类**与 pytest **构造态**命名，**不作**关单 pass 标准。

### 统一根因（三层）

| 层 | 现状（`ultimate_win_rate_engine_v7.py`） | 后果 |
|----|------------------------------------------|------|
| **A · P0 Guard 壳** | **零条**；`decide()` 直接模型 argmax 或「首个非 PASS」回退 | 炸队友、过度拆炸、应压 PASS、最小代价缺失 |
| **B · 特征 / 模型** | `_extract_features` 无牌面编码（**GUA-037a** open）；训练目标为 index 匹配率非掼蛋原则 | 同局内决策不稳定（如 SB 有时出、有时 PASS） |
| **C · V5+ 组牌** | 无 `enumerate_groupings` / 结构评分（**V5+-04**） | 顺子漏带单张、钢板被拆、外对子未优先 |

**升格约束**（`V7-实施方案.md` §1.2）：Guard 须 **V7-native** 实现；**禁止** `import src.m.m3.*`；可**只读** M3 `game_records` 作 **GUA-038** BC teacher。

### 缺陷分类 → 原则 → 落点（不迎合单局）

| 缺陷类 | 原则 ID（M3/V5 对齐） | Phase 0 **GUA-045** Guard | Phase 1+ GUA |
|--------|----------------------|---------------------------|--------------|
| 队友领出仍出炸（replay step 14 类） | **P-F02**、GUA-029 **R5** | **V7-R05**：`greaterPos==(myPos+2)%4` 且队友非 PASS → 剔除 `Bomb`/`StraightFlush` | — |
| 压单级牌用炸 / 拆 5→4 炸（step 6 类） | **P-H04**、**P-G01** | **V7-R01**：压 `Single` 且 `curRank` 在场 → 优先 `Single B`/`Single` 最小点；禁为压单选 `Bomb` 若存在更小单牌选项 | **GUA-037a**（牌面特征） |
| 同型炸弹多配牌（step 8：4A+红2 五炸） | **P-H04**、**P-G02** | **V7-R02**：同牌型能压时选 **`len(cards)` 最小** 合法炸；禁逢人配凑炸若纯炸可压 | **GUA-038** BC |
| 被动应压却 PASS（step 40：有 555 不过 333） | **CALC-M03**、控权 | **V7-R03**：被动且 `greaterPos` 为对手；`actionList` 有同型非 PASS → **禁默认 PASS**（取最小够用） | **GUA-037b**（历史编码） |
| 有王/级牌压单却 PASS（step 58 类） | **P-H06** | **V7-R04**：对手 `Single` 且己方可 `Single B` → 优先非 PASS | **GUA-038** |
| 拆钢板/连对出小对（step 62 类） | **P-G01**、P-F02 | **V7-R06**（轻量）：存在**不拆结构**的更大 `Pair` 可压时，剔除拆 `ThreePair`/钢板的 `Pair` | **V5+-04** |
| 顺子未带掉单张（step 12 类） | **P-G01**、CG-T06 | Guard **不覆盖**（需组牌枚举） | **V5+-04** + **GUA-037a** |

### 改进路线（与现有 GUA 对齐）

```
Phase 0（~1 迭代）  GUA-045  P0 Guard 壳
    │  V7-R01–R06（上表）；decide() 前 filter → 模型 → 后校验
    │  tests/test_v7_gua045.py（构造 actionList/greaterPos，不绑 game_id）
    ▼
Phase 1（~1.5–2 迭代）  GUA-037a 静态特征 → GUA-037b 动态特征（可并行 GUA-040）
    │  真牌面 124 维 + actionList 语义；替换零填充
    ▼
Phase 2（1 迭代）  GUA-038  M3 game_records BC 蒸馏（只读 teacher，不 import M3）
    ▼
Phase 3（~3 迭代）  GUA-039a/b  自对弈 + PPO；队胜率 vs lalala（V7-007 KPI）
    │
    └── 贯穿 Phase 2–3：V5+-04 整手组牌（顺子带单、钢板保护）— 不在 GUA-045 关单范围
```

| Phase | GUA | 优先级 | 验收 |
|-------|-----|--------|------|
| **0** | **GUA-045** | **P0** | `pytest tests/test_v7_gua045.py` **≥8 case**（R01–R06 覆盖）；`ultimate_win_rate_engine_v7` 无 M3 import；可选 V7 净盘 3 局 **观测**（不作关单） |
| **1** | **GUA-037a** → **037b** | P0 / P1 | 特征维数契约 + 推理延迟基线（`V7-实施方案.md` §2） |
| **2** | **GUA-038** | P1 | BC 加载后 `model_usage_rate` 稳定；构造态与 M3 标签一致率抽检 |
| **3** | **GUA-039a/b** | P2 | 30 局 lalala 评估；**V7-007** 队胜率多样本 |
| **并行** | **V5+-04** | P1+ | 组牌枚举关单独立于 GUA-045 |

### 关单条件（GUA-045）

| 项 | 要求 |
|----|------|
| **代码** | `decide()` 接入 **V7-native** `filter_action_list()`（或等价）；实现 **V7-R01、R02、R03、R04、R05** 为 **必达**；**R06** 为 **应达**（可 Phase 0 末条迭代） |
| **测试** | `tests/test_v7_gua045.py` pass；**GUA-037a** 未关单前 guard 须可独立运行（模型可为 mock） |
| **回归** | 不破坏 `IDecisionProvider` 契约；`tests/test_v7_paths.py` / `test_v7_notify_routing.py`（若有）不回归 |
| **不作关单** | 再跑 `20260606121245769675` 逐步一致；V7 队胜率 >50%（归 **V7-007** / **GUA-039b**） |

**后续 Agent**：实施 GUA-045 前读本节 + [`V7-实施方案.md`](V7-实施方案.md) §1.2 黑名单；M3 队胜率 KPI **仍只看 M3 批跑**；V7 KPI 见 `ITERATIONS` **V7-007**。

---

## V5+ priority（GUA-034 / GUA-036 后续 · 不在 M3 本轮）

> 登记 **2026-06-01**；与 [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) P1+→V5+ 对齐。

| 优先级 | 主题 | 来源 | 说明 |
|--------|------|------|------|
| **V5+-01** | lalala **两手走完枚举 + 首出选优** | GUA-034 讨论 ②、[`M3_DIAGNOSIS.md`](M3_DIAGNOSIS.md) BUG2、方向 E/C | `numofmy<=12` 枚举 actionList 两手组合；选「第一手难被压、第二手清牌」（如 `99933`→`10101044`）。lalala 参考实现有 **sort 比较 bug + 候选未消费**（见 `reference/lalala/action.py:1117–1127`），移植须重写而非直抄 |
| **V5+-02** | solo 接风 **可回收单张** 优先级 | GUA-034 讨论 ③ | 混型手牌：级牌/王/大单可先出试探；与 END-M02+-02（对手剩 1 禁小单）联合定优先级表 |
| **V5+-03** | 方向 E 轻量模板 | [`GUA-034-方案评审.md`](GUA-034-方案评审.md) | `solo_sprint && numofmy<=8`：2–3 种固定两手模板（三带二+剩余等），介于 M3 guard 与 BUG2 全量之间 |
| **V5+-04** | **整手结构组牌**（钢板+顺子+炸弹+单张协同） | **GUA-036** 复盘、[`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) §复盘与验收理念 | 局面几乎不重复 → 需 `enumerate_groupings` / 搜索；**不**在 M3 扩 `combine_handcards` |

## 来自「比赛汇总」的说明（非缺陷）

`docs/掼蛋AI相关比赛汇总.md` 主要为**南邮平台与赛事索引**，不记载本仓库逻辑缺陷；参赛与平台 JSON/WebSocket 对齐请在迭代中当作**环境约束**验收（不必单列 GUA，除非出现协议不符）。

## 模板（新增行时复制）

| ID | 状态 | 严重级别 | 标签 | 版本 | 简述 | 现象 / 复现要点 | 涉及模块 | 备注 |
|----|------|----------|------|------|------|-----------------|----------|------|
| GUA-xxx | open / closed | P0–P3 | rules, observation, policy | m1/v4/v5/v6/训练/docs | | | | `closed_in` / `duplicate of` |
