# 缺陷登记簿（Defect Register）

> 编号规则：`GUA-001`、`GUA-002`… **永不复用**。关闭后若复发，新开编号并 `duplicate of GUA-xxx`。  
> **状态**以文档与提交为准；后续在表中直接维护。  
> **来源扫描**（写入本条时已对照）：`docs/掼蛋AI相关比赛汇总.md`、`docs/reports/README_优化项目.md`、`docs/reports/YF掼蛋优化实施报告.md`、`docs/guandan-brain/notes/WORKFLOW_RESTART_LOG.md`、`logs/`（含 `yf*_m1_*.log`、`batch_executor_*.log` 等）。

> **已重构为 Obsidian 式组织**（2026-06-17）。完成定义详细段落已提取到 `issues/` 目录，主表仅保留索引 + 交叉引用。

## 如何使用本文件（Agent 必读）

| 场景 | 操作 |
|------|------|
| **了解当前缺陷全景** | 读下方「当前条目」表格 → 关注 open 项 + P0 标签 |
| **查某个 GUA 详情** | 表格「备注」列含简案；已关单项的完成定义见 `issues/GUA-xxx-completion.md` |
| **登记新缺陷** | 在底部「模板」复制表格行 → 填入 GUA 编号；若需详细完成定义 → 新建 `issues/GUA-xxx-completion.md` |
| **按版本/引擎筛选** | 看「引擎维护策略」表确认 active/frozen 状态；搜索表格「版本」列 |

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
| **P0 guard**（可 pytest + 批跑验收的 if-guard） | **M3**：`src/m/m3/m3_decision_engine.py`（及 `m3_utils.py`）；**V7**：`src/decision/ultimate_win_rate_engine_v7.py` 内 **V7-native** 过滤壳（**GUA-045**，不 import M3） | 与 [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) **M3 · P0** 一致；V7 原则对齐见 [[GUA-045-completion]] |
| **组牌 / 牌力 / 混合决策** | **V5+**（`src/v/`、V 挂接 `IDecisionProvider`） | 不在 M3 引擎内堆整篇策略；M3 保持 lalala 式 guard + 契约底座；V7 组牌类见 GUA-045 Phase 2 / **V5+-04** |
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

> **status**: `open`（蓝色）= 待处理；`closed` ✅ = 已关单。  
> **完成定义**：已关单项的详细实施条件见 `issues/GUA-xxx-completion.md`。  
> **当前活跃 P0**：GUA-054、GUA-055、GUA-059、**GUA-063**、GUA-064、**GUA-065**

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
| GUA-029 | closed | **P0** | policy, rules | m3 | M3 炸弹可执行规则包（R1–R6） | 回放 `20260530172743739854` 曾现 yf1 **5×8** 全程未出；根因 `choose_bomb` 读 `action[-1]` → TypeError → PASS | `m3_utils.choose_bomb`、`m3_decision_engine` | **`closed_in` 2026-05-31**：R1–R6 + `test_m3_gua029` **8 passed**；净盘批跑 **10/10**；炸弹 yf1 **175** + yf2 **152**。完成定义见 [[GUA-029-completion]] |
| GUA-030 | closed | P2 | docs, policy | m3, v5 | **原则+战略映射表**：`01_basic_principles` / `02_strategy_overview` / `03_basic_strategy` → 引擎归属（**P0→M3**，**P1+→V5**） | 无代码缺陷；需将 skills 落实为可测 guard / V5 知识层，避免整篇硬编码进 M3 | [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md)；真源见 §一–§七 | `closed_in` 2026-05-31；三篇映射评审通过；M3 P0/P1 实现由 GUA-029 及后续迭代跟踪。完成定义见 [[GUA-030-completion]] |
| GUA-031 | closed | P1 | policy | m3 | M3 传牌 `numof*` guard + 队友让道扩全牌型 | 被动仅 `_Single/_Pair` 等部分牌型做队友 PASS；`_active` 无 `numoffri==1` 送小单 / `numoffri==5` 喂牌；`numofnext==1` 防小单不完整 | `m3_decision_engine`（`_active`、`_passive`、各 `_Xxx` handler） | **`closed_in` 2026-05-31**：P-F02 扩 `_Trips/_ThreePair/_TwoTrips/_Straight`；PASS-P02/P03/P04；`test_m3_gua031.py` **7 passed**。完成定义见 [[GUA-031-completion]] |
| GUA-032 | closed | P1 | observation, policy | m3 | M3 **记牌+算牌**确定性规则 + `remain_cards_classbynum` 同步 | 文档 §14–§15、§18–§20、**§二十二**（孤张定律 CG-T06、口诀 13）；5/10 法则、顺/夯点位预判（**CALC-M03/M04**）；`remain_cards_classbynum` stale | `m3_decision_engine._update_play_state`、`m3_utils` | **`closed_in` 2026-05-31**：`sync_remain_cards_classbynum` + `_update_play_state` 同步；`test_m3_gua032.py` **6 passed**。完成定义见 [[GUA-032-completion]] |
| GUA-033 | closed | P1 | observation, rules | m3, infra | M3 **批末 `victoryNum` / `gameResult` 解析错误**（批级回填污染） | **客户端已修**；**平台根因**：本包 v1006 exe **argv 无效**，单次会话 **固定 3 局** → WebSocket `settingTimes=3` | `yf1_m3.py`、`yf2_m3.py`、`game_result_utils.py` | **`closed_in` 2026-05-31**；`test_m3_gua033.py` **11 passed**。完成定义 + 平台根因见 [[GUA-033-completion]] |
| GUA-034 | closed | P1 | policy | m3 | M3 **残局：队友走光后 rank 小牌首出 + 被动不拆结构压牌** | round **38** yf2：102–107 步 — 接风 `_active` 拆对 **3** 出单；对手 **6/对6** 可压却 **PASS**。**根因**：`_active` 仍走 `rankone/ranktwo` 清小点；缺「队友 rest=0 → 1v2 拦头游」模式 | `m3_decision_engine`（`_active`、`rankone/ranktwo/rankthree`、`_Single`、`_Pair`） | **`closed_in` 2026-06-01**：方向 A — `_is_solo_sprint` + END-M02–M04；`test_m3_gua034.py` **6 passed**。完成定义见 [[GUA-034-completion]] |
| GUA-035 | closed | P1 | policy | m3 | M3 **END-M02+：solo 接风按对手剩张过滤牌型** | GUA-034 END-M02 仅固定优先三带二/三张/对子；缺：**任一对手剩 1 张 → 不宜出小单**等 | `m3_decision_engine._gua035_solo_wind_pick`、`_gua034_solo_active_pick` | **`closed_in` 2026-06-01**：END-M02+-01–04；`test_m3_gua035.py` **6 passed**。完成定义见 [[GUA-035-completion]] |
| GUA-036 | closed | P1 | policy | m3 | M3 **控权 + 接风配合**（非 solo） | batch7 round38 复盘：**①** 接风拆 2 打单，未跟队友对子线；**②** 敌出杂顺可压却 PASS。**根因**非「缺顺子函数」，而是 guard 缺口 + `_Straight` 过窄 | `m3_decision_engine`：`_active` 接风、`_Straight` | **closed_in** 2026-06-01。完成定义见 [[GUA-036-completion]]。KPI 观测：GUA-036 样本均值低于 GUA-034/035，方差属发牌随机波动（详统计检验 note） |

**统计检验 note（2026-06-02 补充）**：GUA-034/035 26/33=78.8% vs GUA-036 36/69=52.2%（S9后），**差值 26.6pp，p=0.009**；95% CI [8pp, 45pp]。**结论**：GUA-036 **显著差于** GUA-035，非发牌随机波动可解释。

| GUA-037a | closed | P0 | V-nn, v7 | v7 | V7 静态特征工程（state_牌态 124 维） | `_extract_features` 静态部分全零填充；需重写手牌 108 维 + 级牌/红心配 9 维 + 6 维 + hand count 1 维 = 124 维 | `src/v/nn/features/static_features.py` | `closed_in` 2026-06-07。Part 3（2026-06-14）：叠加局面信念分类器 → 4 维 soft 向量至索引 188-191；特征利用率 37.5% |
| GUA-037b | open | P1 | V-nn, v7 | v7 | V7 动态特征工程（LSTM 历史编码） | 在 037a 静态特征基础上叠加 LSTM 历史编码（出牌历史 + numof* 序列），目标总维度 188 维 | `src/v/nn/features/dynamic_features.py` | 完成定义见 `V7-实施方案.md` §2 Phase 1 GUA-037b；可与 GUA-038 并行 |
| GUA-038 | **closed** ✅ | P1 | V-nn, v7 | v7 | V7 M3 知识蒸馏（BC 热启动） | V7-internal 录牌 → BC 训练 | `src/v/nn/recorder/v7_recorder.py`、`bc_dataset.py`、`bc_trainer.py` | **`closed_in` 2026-06-07**：`tests/test_v7_bc.py` **34/34 passed**。06-16 首次物理落地训练（1208 样本，val_acc=82.57%）。06-17 M3 胜局重训（5555 样本，val_acc=35.19%，1 epoch 早停）→ 退化触发 GUA-059 |
| GUA-039a | open | P2 | V-nn, v7 | v7 | V7 自对弈 DMC + ZMQ 桥 + Actor 原型 | 搭建 V7 自对弈基础设施 | `src/v/nn/training/actor.py`、`learner.py`、`replay_buffer.py`、`zmq_bridge.py` | 完成定义见 `V7-实施方案.md` §2 Phase 3；**关单前提**：评审后方可启动 GUA-039b |
| GUA-039b | open | P2 | V-nn, v7 | v7 | V7 自对弈 top-K + PPO + 30 局评估 | 在 039a 基础上叠加 top-K=2 过滤 + PPO policy net + 两阶段 30 局 lalala 评估基线 | `scripts/v7/eval_vs_lalala.py` | 完成定义见 `V7-实施方案.md` §2 Phase 3；仅在 GUA-039a 关单后启动 |
| GUA-040 | open | P1 | V-nn, v7 | v7 | V7 模型权重管理（COS manifest + 版本切换） | 搭建 V7 模型权重的 COS 上传/下载/版本切换基建 | `models/v-nn/manifest.json`、`scripts/v7/weight_manager.py` | 完成定义见 `V7-实施方案.md` §2 Phase 1 并行 GUA-040 |
| GUA-041 | **closed** ✅ | P1 | V-nn, v7 | v7 | V7 路径债清理 | 消除 V7 客户端与启动器中的 D 盘硬编码路径债 | `config/v7_paths.yaml`、`src/utils/v7_paths.py` | **`closed_in` 2026-06-05**：pytest 6/6 passed |
| GUA-042 | **closed** ✅ | P1 | V-nn, v7 | v7 | ABL-GD 168 伪动作评估（含开源可行性） | 调研 ABL-GD（CCFAI 2025）168 伪动作方案的可获取性与可移植性 | `docs/analysis/abl-gd-eval-2026-06.md` | **`closed_in` 2026-06-07**：结论为弃用该方案 |
| GUA-043 | **closed** ✅ | P1 | V-nn, v7 | v7 | 专利规避设计审计（CN113018837A 边界） | 审计掼蛋 AI 算法专利 CN113018837A 的权利要求边界 | `docs/governance/patent-audit-cn113018837a.md` | **`closed_in` 2026-06-07**：结论为 V7 核心技术路径与专利无实质重叠 |
| GUA-044 | **closed** ✅ | P1 | observation, infra | v7, m1, m3, batch | **批跑四席未就绪即开局 + 首局空等卡顿** | V7 批跑 `wait_for_clients_connected` 误报 **0/4** 仍继续；第 4 席连上即开局 | `batch_executor/client_ready.py`、`websocket_manager.py`、`lalala_adapter.py` | **`closed_in` 2026-06-06**：四席就绪门闩 + 就绪表；`tests/test_client_ready.py` **3 passed**。完成定义见 [[GUA-044-completion]] |
| GUA-045 | **closed** ✅ | **P0** | policy, v7 | v7 | **V7 决策根因：零特征模型 + 无 P0 Guard** | `UltimateWinRateEngineV7` 对 `actionList` **argmax**；零条 guard；回退「首个非 PASS」 | `src/decision/ultimate_win_rate_engine_v7.py`；`src/v/nn/guards/v7_guards.py` | **`closed_in` 2026-06-07**：V7-native `filter_action_list` + V7-R01~R06；`tests/test_v7_gua045.py` **24/24 passed**。完成定义见 [[GUA-045-completion]] |
| GUA-046 | open | P3 | observation, infra | v7, m1, m3, batch | **副间 ~10s 停顿（服务器内在结算/发牌间隔）** | V7 批跑日志显示每副牌决策集中在 **1 秒内**打完，之后服务器进入 **~10s** 无消息空窗期 | 无（服务器行为） | **订正 2026-06-07**：GUA-047 原误判已 closed；本条恢复原状 |
| GUA-047 | **closed** ✅ | **P1** | observation, infra | v7, m1, m3, batch | **【误判关单】** 同副牌内 4 席全停 ~20s → **实际是 batch_executor 日志 dump 延迟** | `batch_executor/restart_manager` 将服务器 stdout **延迟 dump** 到日志（延迟 73s）；实际 4 席节奏完全同步 | `docs/analysis/批跑cmd窗口观察.md`；`batch_executor/restart_manager.py` | **closed_in 2026-06-07**：原 GUA-047 误判已订正。新开 GUA-048 跟踪日志 dump 延迟 |
| GUA-048 | open | P2 | observation, infra | v7, m1, m3, batch | **批跑 73s 卡顿：客户端 game_ready 写盘超时（根因 A）+ ServerStdoutReader 启动晚（根因 B）双根因** | **73s 卡顿 = 60s game_ready 超时 + 13s dump 落幕叠加**。`wait_for_all_clients_game_ready(timeout=60)` 硬超时 | `batch_executor/client_ready.py:180`、`executor.py:514`、`executor.py:547` | **登记 2026-06-07**（P2，回退 open）。关单条件：① game_ready 写盘 < 10s；② ServerStdoutReader 立即启动；③ pytest；④ ≥3 局批跑验收。**相关**：GUA-049（game_ready 写盘慢专条，P1） |
| GUA-049 | open | **P1** | observation, infra | v7, m1, m3, batch | **【根因锁定】** 客户端 `mark_game_ready` 写盘 4 进程 race condition，3 子根因 | `batch_executor/game_ready.json` **只有 3 entry**（缺 yf2_v7）。**A1**：`_game_save` 非原子写 → JSON 损坏；**A2**：`mark_game_ready` 无 try/except + asyncio 静默异常；**A3**：期望 4 entry + 60s 硬超时 | `batch_executor/client_ready.py:52`、`231`；`websocket_manager.py:276` | **登记 2026-06-07**（P1，根因已锁定）。关单条件：① temp+rename 原子写；② try/except；③ pytest 4 进程并发 100 次 0 损坏；④ ≥3 局批跑验收。**相关**：GUA-048 |
| GUA-050 | open | **P0** | V-nn, v7 | v7 | **局面信念向量 8 维**（扩展 GUA-037a） | V7 需从 `P(action|state)` 升级为 `P(action|state, belief)`。叠加 8 维信念 | `src/v/nn/features/static_features.py` | **登记 2026-06-16**（P0）。特征维数 124→132。完成定义：信念向量在线推理 ≤1ms；pytest ≥6 case；V7 净盘 3 局观测 |
| GUA-051 | **closed** ✅ | P1 | V-nn, v7 | v7 | **稠密 Reward 信号 9 种**（扩展 GUA-039a） | 9 种中间 reward：出牌成功+0.05/接风+0.1/掼蛋+0.3/级牌控制+0.2/配合+0.1/送对家+0.15/炸弹±0.5/本方升级+2.0/对方升级-1.0 | `src/v/nn/training/reward.py` | **closed_in** 2026-06-16：`reward.py` 实现 + `RewardAccumulator` + 12 项 pytest |
| GUA-052 | **closed** ✅ | P1 | V-nn, v7 | v7 | **108 张牌全量追踪 + 排除法推断**（扩展 GUA-037b） | 增补：已出牌、对手/队友出牌牌型、各家剩张、级牌状态；排除法推断对手手牌 | `src/v/nn/features/memory_tracker.py` | **closed_in** 2026-06-16：`memory_tracker.py` 实现 + 24 维 state_vector + 10 项 pytest |
| GUA-053 | open | P2 | V-nn, v7 | v7 | **对手池多样性**（扩展 GUA-039b） | 保留历史 checkpoint 对手池，每次 self-play 从对手池随机选 | `src/v/nn/training/opponent_pool.py`（待建） | **登记 2026-06-16**（P2，最低优先级），等 GUA-039a/039b 关单后启动 |
| GUA-054 | open | **P0** | V-nn, v7, policy | v7 | **V7 组牌质量中间表示**（grouping_scanner 9 维，借鉴 v4 策略库经验） | 基于 **6 大组牌核心原则** + v4 策略库组牌优先级 → 9 维 grouping_score | `src/v/nn/features/grouping_scanner.py`（新建） | **登记 2026-06-17**（P0）。完成定义：9 维特征；pytest ≥10 case；接入 MT 24→33 维（共 229 维）；V7 净盘 3 局副胜率不下降。**级牌约束**：禁止 `from src.m.m3 import ...` |
| GUA-055 | open | **P0** | V-nn, v7, policy | v7 | **V7 动作空间二阶段过滤**（借鉴 v4 ActionSpaceOptimizer，纯函数式） | 启发式 Top-K 100（纯函数式）→ V7 NN 精细评估 | `src/v/nn/features/action_space_filter.py`（新建） | **登记 2026-06-17**（P0）。完成定义：Top-K 启发式不调参；pytest ≥6 case；V7 引擎 `decide()` 二阶段接入；总耗时 <0.8s。**先 GUA-054 后 GUA-055** |
| GUA-056 | open | P1 | V-nn, v7, training | v7 | **V7 双上节奏 reward**（v4 缺失项补足，扩展 GUA-051） | 队友前 2 名跑光时 +1.0 | `src/v/nn/training/reward.py`（追加） | **登记 2026-06-17**（P1）。必须 GUA-039b 30 局 vs lalala 基线完成后再启动 |
| GUA-057 | open | **P1** | V-nn, v7, policy | v7 | **V7 记牌模块**（4×27 维 = 108 维剩余牌概率分布） | LSTM/Transformer encoder-decoder → 各家剩余牌分布概率 | `src/v/nn/features/card_counting_network.py`（新建） | **登记 2026-06-17**（P1）。前置依赖：GUA-039b 基线 + GUA-054 实施验证 |
| GUA-058 | open | **P1** | V-nn, v7, policy | v7 | **V7 策略模块**（4 分类：进攻/防守/观望/保对家） | 组牌+记牌 → 策略分类（4 类） | `src/v/nn/features/strategy_network.py`（新建） | **登记 2026-06-17**（P1）。前置依赖：GUA-057 closed + GUA-039b 基线 + GUA-054 |
| GUA-059 | open | **P0** | V-nn, v7, training | v7 | **GUA-038 BC v2 退化根因定位**（副胜率 11.8%→0%，训练→实战脱钩） | 三次批跑曲线：第 2 次 12 局副胜率 11.8%；第 3 次 12 局副胜率 0%。训练侧与实战侧完全脱钩 | `scripts/train_bc_v7.py`、`src/v/nn/training/bc_dataset.py` | **登记 2026-06-17**（P0，所有 P1 GUA 的硬前置）。关单硬条件：≥30 局 vs lalala 队胜率 + 副胜率均不下降。**相关**：GUA-038（退化触发源）；GUA-060（BC 调参终止） |
| GUA-060 | **closed** | **P0** | V-nn, v7, training | v7 | **V7 BC val_acc 锁死 36.46% — 终止 BC 调参路线** | 5541 样本 → val_acc=36.46% 6 epoch 锁死；argmax collapse 强证据。BC 模仿学习 argmax collapse 是**理论必然** | `scripts/train_bc_v7.py`、`bc_trainer.py` | **`closed_in` 2026-06-17**：BC 调参路线终止。GUA-061 模块化架构 |
| GUA-061 | **closed** ✅ | **P0** | V-nn, v7, policy, architecture | v7 | **V7 转向模块化架构：M3 组牌逻辑提取 + GroupingEngine** | 从 M3 提取组牌逻辑→封装 GroupingEngine→接入 V7 特征管线→组牌增强 BC 重训对比 | `src/v/nn/features/grouping_engine.py`（新建） | **`closed_in` 2026-06-18**：P0①②③全部完成。① GroupingEngine 新建 298 行 + 31 pytest；② 接入 memory_tracker/bc_dataset/V7 engine 双路径；③ BC 重训对比：grouping_engine(24维) vs grouping_scanner(9维) val_acc 均为 37.36%，BC argmax collapse (GUA-060) 无法区分特征质量。**真实验证待 GUA-039b 自对弈**。**发现**：M3 原始组牌无回收能力/灵活性评分，GUA-061 忠实提取了弱逻辑 → 后继 GUA-062。**2026-06-18 流水线接通**：① 生产端 `yf1_v7/yf2_v7` 从 grouping_scanner(9维)→grouping_engine(24维) 切换 ② `_extract_features` MT维度 33→48 对齐 ③ `decide()` 动作选择现已走 24 维分组评分。 |
| GUA-062 | **closed** ✅ | **P0** | V-nn, v7, policy, architecture | v7 | **组牌引擎 v2：静态回收评估 + 灵活性 + 真回溯多方案** | GUA-061 提取的 M3 组牌逻辑缺两个核心维度（回收能力 0.3 + 灵活性 0.2）+ 仅 4 策略贪心标签。基于 `人类掼蛋决策流程完整分析.md` §阶段0/§4.1 + `04_card_grouping_skills.md` §一 重建评分体系 | `src/v/nn/features/grouping_engine.py`（升级） | **`closed_in` 2026-06-18**：pytest 49 passed。详见 issues/GUA-062-completion.md。**批跑 2026-06-18T20:28**：V7 vs Lalala 3局，局胜 0/3(0%)，副胜 3/54(5.6%)，达A 9/54(16.7%)，双上0次。末级分布：2-5级 21(38.9%) / 6-10级 13(24.1%) / J-K 11(20.4%) / A 9(16.7%)。流水线接通（grouping_engine 24维+bc_model_v3）后首次批跑，模型决策率100%。3副胜：R7(cR=2,pos2先跑)/R10(cR=8,pos2先跑)/R27(cR=6,pos0先跑)。NN出牌无方案约束→衔接待解(GUA-063) |
| GUA-063 | **open** 🔄 | **P0** | V-nn, v7, policy, architecture | v7 | **组牌→出牌衔接：is_core 不保护顺子/三张 + 贡前手牌** | **已实施（2026-06-18）**：Phase 1 card_mask、Phase 2 `_group_consistency_filter` 角色驱动前置过滤、Phase 3 触发式中局重分组。**重开根因（2026-06-18 副牌回放诊断）**：<br>**① is_core=0.0 导致顺子/三张被 NN 拆散**：`_group_consistency_filter` 中顺子和三张的 `is_core=0.0`，filter 不保护这些结构牌型。实际回放：副 17-2 yf1 组牌方案含 3-4-5-6-7 顺子 + 888 三张，但 NN 出牌时拆 D5 打单、拆 S8 打对——`_group_consistency_filter` 角色为主攻时本应剔除拆结构动作，却因 `is_core=0.0` 放行。<br>**② 贡前手牌问题（GUA-067 联动）**：`initial_hand` 来自 gameStart 的 `handCards`（贡前 27 张），训练侧 `current_hand = initial_hand - played_cards` 推算错误。已修复：`adjust_initial_hand_for_tribute_back` 在 4 条贡牌/还贡路径上实时调整 `initial_hand`。<br>**③ 顺子扫描高→低违背去小单化（已修复 2026-06-18）**：`_detect_straights` 原从高→低窗口扫描，2-7 六连张先锁 3-4-5-6-7 留单 2。**根因**：掼蛋核心原则是「去小单化」——越小的单越难顺掉，组顺子首要目标就是吸收小单。**已修**：窗口扫描改为低→高（2-6 优先于 3-7），把大单（7-K-A）留给其他组合（对子/三带二），大单比小单更易匹配搭档。<br>**④ 大顺子压制力需区分初始组牌 vs 动态出牌**：大顺子有压制力（逼炸/盖牌），但这属动态出牌决策层面。初始组牌阶段不应以牺牲去小单化为代价追求大顺子；战时如需升级可从最小组起的方案派生（如对手出 2-6 后可升级为 3-7）。<br>**解法**：① 将顺子和三张标记为 `is_core=1.0`（**已修 2026-06-18**：`to_card_mask` 中 straights/trips → `is_core=True`），让 `_group_consistency_filter` 保护这些结构牌型不被 NN 拆散；② GUA-067 已修复贡前手牌；③ 顺子扫描改为低→高（**已修 2026-06-18**）。 | `grouping_engine.py` → `_detect_straights`（扫描方向）、`to_card_mask`（is_core）、`memory_tracker.py` → `ultimate_win_rate_engine_v7.py`；`v7_game_recorder.py`（GUA-067） | **重开 2026-06-18**，**全部子项已修复 2026-06-18**。原闭单见 [[组牌-NN衔接设计-软引导vs硬约束]]。① is_core=1.0（顺子/三张）已修；③ 顺子去小单化已修；② GUA-067 贡牌调整已实施。可关单条件：批跑验证顺子/三张不再被 NN 拆散。**相关**：GUA-062（组牌引擎 v2）、GUA-067（贡牌手牌修复） |
| GUA-064 | open | **P0** | V-nn, v7, observation, training | v7 | **BC argmax collapse 日志确证：2048 维输出仅用 2 维** | 2026-06-18 两轮 6 局 86 副日志分析：V7 动作索引分布 actIndex=0(PASS) 50.1%、actIndex=1(首候选出牌) 48.9%、actIndex≥2 仅 20 次(0.9%)。PASS 率与 Lalala 持平(V7 50-52% vs Lalala 53-55%)，非败因。卡牌验证 WARNING 28 次(≈每3副1次)，低频不致命。**根因**：BC 模仿学习 argmax collapse 是理论必然(GUA-060)，2048 维候选空间中 99%+ 从未被选择。组牌引擎(GUA-061/062)+衔接(GUA-063)均未改变此结构 | `ultimate_win_rate_engine_v7.py`、`bc_trainer.py`、`bc_model_v3.pth` | **登记 2026-06-18**（P0，所有 V7 策略 GUA 的硬前置）。实锤数据来源：4 个客户端日志 `yf*_v7_20260618_2145*.log` + 2 个服务端日志 `v7_vs_lalala_20260618_2145*.log`。关单方向：① 输出头加温度采样/beam search 打破 argmax；② 引入 policy gradient 脱离 BC teacher forcing；③ 动作掩码强制多样性。**不做此关单，任何组牌/策略改进都不会转化为队胜率**。 |
| GUA-065 | open | **P0** | V-nn, v7, policy, guard | v7 | **导入 M3 队友识别与保护到 V7 Guard 体系** | V7 当前完全缺失队友识别与保护逻辑——不知道「队友是谁」、不保护队友控牌权、不送队友关键张。M3 已有 8 条队友相关规则（`_is_teammate_greater`、`_gua031_passive_teammate_yield`、`_gua031_active_min_single`、`_gua031_active_feed_five`、`_gua036_teammate_trick_anchor`、`_gua036_team_wind_pick`、`_is_solo_sprint`、`_gua029_try_bomb` R5 不炸队友），但 M3 队友保护也被评估为「极弱」（M3_DIAGNOSIS.md：仅检查 `(myPos+2)%4==greaterPos`，无队友手牌分析、无主动送牌）。导入方式：① V7 guard 新增 R07（队友控牌不压除非残局冲刺）、R08（队友剩 1 张送最小单）、R09（队友剩 5 张送 Pair/ThreeWithTwo）；② `_group_consistency_filter` 场景 [队友] 下不拆对子（队友可能接）；③ 接风优先跟随队友线（Pair/Pomb）。| `src/v/nn/guards/v7_guards.py`（追加 R07-R09）、`ultimate_win_rate_engine_v7.py`（导入 `greaterPos`/`numofplayers` 上下文）、`grouping_engine.py`（`_group_consistency_filter` 队友场景） | **登记 2026-06-18**（P0）。V7 无队友配合是 0% 局胜率的重要根因之一——两 AI 各自为战等于 1v3。前置依赖：GUA-063 is_core 保护链完成（队友保护需要稳定的组牌方案基础）。关单条件：① guard R07-R09 pytest ≥6 case；② 批跑 3 局可观测到「队友控牌时 PASS 率 > M3 基线」；③ 不拆队友牌型。**相关**：GUA-031（M3 队友保护已建）、GUA-034（solo 冲刺）、GUA-036（接风队友配合） |
| GUA-067 | open | P1 | V-nn, v7, training, data | v7 | **训练数据 initial_hand 为贡前手牌，current_hand 推算错误** | `initial_hand` 来自 gameStart notify 的 `handCards`（发牌后、还贡前的 27 张）。`bc_dataset.py` 策略2 `current_hand = initial_hand - played_cards` 只能减不能加：已还走的牌多算、收到的贡牌少算 → 训练样本手牌特征偏移 | `v7_game_recorder.py`、`yf1_v7.py`、`yf2_v7.py`、`bc_dataset.py` | **登记 2026-06-18**。**已实施（GUA-067 联动 GUA-063）**：`adjust_initial_hand_for_tribute_back()` 在 4 条贡牌/还贡路径上实时调整 `initial_hand`：收贡→add、收还→add、进贡→remove、还牌→remove。修改文件：`v7_game_recorder.py`（新增方法）、`yf1_v7.py`/`yf2_v7.py`（各 2 处调用）。关单条件：批跑验证 `initial_hand` 张数 = 27（贡后）且不含已贡出牌。 |

---

## 交叉引用

| ID | 相关文档 |
|----|----------|
| GUA-022 | [`AGENT_HUB.md`](AGENT_HUB.md) — 多 Agent / Kanban 编排 |
| GUA-023 | [`AGENT_HUB.md`](AGENT_HUB.md) — OpenCode ACP 桥接不兼容 |
| GUA-029 | [`01_bomb_techniques.md`](../knowledge/skills/02_main_attack/01_bomb_techniques.md)、[`M3_DIAGNOSIS.md`](M3_DIAGNOSIS.md) BUG5；完成定义 [[GUA-029-completion]] |
| GUA-030 | [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md)；完成定义 [[GUA-030-completion]] |
| GUA-031 | [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) §8.4、§十七–§二十二；完成定义 [[GUA-031-completion]] |
| GUA-032 | [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) §14–§15、§18–§22；完成定义 [[GUA-032-completion]] |
| GUA-033 | [`platform-data-interpretation.md`](../knowledge/platform-data-interpretation.md) **§2**；完成定义 [[GUA-033-completion]] |
| GUA-026 | [`10_three_with_two_skills.md`](../knowledge/skills/04_common_skills/10_three_with_two_skills.md) §二十 |
| GUA-034 | [`GUA-034-方案评审.md`](GUA-034-方案评审.md)；完成定义 [[GUA-034-completion]] |
| GUA-035 | GUA-034 END-M02+；完成定义 [[GUA-035-completion]] |
| GUA-036 | batch7 round38 复盘；完成定义 [[GUA-036-completion]] |
| GUA-044 | [`platform-data-interpretation.md`](../knowledge/platform-data-interpretation.md)；完成定义 [[GUA-044-completion]] |
| GUA-045 | [`V7-实施方案.md`](V7-实施方案.md) §0–§2；完成定义 [[GUA-045-completion]] |
| GUA-063 | 组牌→出牌衔接：is_core=0.0 顺子/三张保护 + 贡前手牌；参见 `ITERATIONS.md` 底部活跃行。GUA-067 联动 |
| GUA-064 | BC argmax collapse 日志确证；参见 `ITERATIONS.md` v7-bc-argmax-collapse-confirmed 行；`v7-win-rate-history.md` L43 |
| GUA-067 | 贡牌未调整 initial_hand；`adjust_initial_hand_for_tribute_back` 修复；联动 GUA-063 |
| GUA-065 | 导入 M3 队友识别与保护到 V7 Guard；`_is_teammate_greater` → V7 R07-R09；联动 GUA-031/034/036 |

---

## 模板（新增行时复制）

| ID | 状态 | 严重级别 | 标签 | 版本 | 简述 | 现象 / 复现要点 | 涉及模块 | 备注 |
|----|------|----------|------|------|------|-----------------|----------|------|
| GUA-xxx | open / closed | P0–P3 | rules, observation, policy | m1/v4/v5/v6/训练/docs | | | | `closed_in` / `duplicate of`；若需详细完成定义 → 新建 `issues/GUA-xxx-completion.md` |

## 来自「比赛汇总」的说明（非缺陷）

`docs/掼蛋AI相关比赛汇总.md` 主要为**南邮平台与赛事索引**，不记载本仓库逻辑缺陷；参赛与平台 JSON/WebSocket 对齐请在迭代中当作**环境约束**验收（不必单列 GUA，除非出现协议不符）。
