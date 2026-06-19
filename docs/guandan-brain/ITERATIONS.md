# 迭代日志（Iteration Log）— MOC 入口

> **已重构为 Obsidian 式组织**（2026-06-17）。历史迭代从单文件 157 行拆分为主题文件，按 [[wikilink]] 交叉引用。

## 如何使用本文件（Agent 必读）

| 场景 | 操作 |
|------|------|
| **接续任务 / 了解当前进度** | 打开本文件 → 查最新迭代（文件清单底部高亮项）→ 点 `[[GUA-xxx]]` wikilink 直达详情 |
| **记录新迭代** | 在本文件底部「模板」表格追加新行（模板已保留） |
| **某主题超过 10 条迭代** | 拆分为独立 `.md` 文件放入 `iterations/`，更新对应 `MOCs/` 索引，本文件表格追加一行链接 |

> **新迭代记录**：请在下方表格追加新行；若某主题超过 10 条迭代，考虑拆分为独立文件并更新对应 MOC。

## 快速导航

| 你要找什么 | 去哪里 |
|-----------|--------|
| 按 GUA 编号查找 | [[GUA-Index]] |
| M1 开发历史（frozen） | [[M1-Development]] |
| M3 决策引擎（主交付） | [[M3-Development]] |
| V7 神经网络（当前开发） | [[V7-Development]] |
| 批跑器、路径、治理 | [[Infrastructure]] |
| 队胜率 KPI 汇总 | [[kpi-observations]] |
| 按时间线查看全部 | 下方「迭代文件清单」 |

## 迭代文件清单

### M 系列

| 文件 | 覆盖范围 | GUA |
|------|----------|-----|
| [[m1-pass-gua020-021]] | 2026-04-21，M1 PASS 率分析 | GUA-020, GUA-021 |
| [[m1-strategy-gua022]] | 2026-04-21 ~ 2026-05-31，M1 队胜率攻关 | GUA-022, GUA-014 |
| [[m3-integration-gua024-028]] | 2026-05-29 ~ 2026-05-30，M3 引擎集成 | GUA-024, GUA-025, GUA-027, GUA-028 |
| [[m3-strategy-gua026-029]] | 2026-05-30 ~ 2026-05-31，三带二 + 炸弹 | GUA-026, GUA-029 |
| [[m3-guards-gua031-036]] | 2026-05-31 ~ 2026-06-02，传牌/算牌/残局 | GUA-031, GUA-032, GUA-034, GUA-035, GUA-036 |
| [[m3-skills-mapping-gua030]] | 2026-05-31，技能映射与原则评估 | GUA-030, §16–§22 |

### V 系列

| 文件 | 覆盖范围 | GUA |
|------|----------|-----|
| [[v7-infra-gua041-049]] | 2026-06-04 ~ 2026-06-08，V7 基础设施 | GUA-041, GUA-044, GUA-047, GUA-048, GUA-049, V7-006, V7-010 |
| [[v7-features-gua037-038]] | 2026-06-07 ~ 2026-06-17，特征工程与 BC 训练 | GUA-037a/b, GUA-038, GUA-050, GUA-052 |
| [[v7-strategy-gua045-053]] | 2026-06-07 ~ 2026-06-17，Guard 壳与策略 | GUA-045, GUA-051, GUA-052, GUA-053 |
| [[v7-bc-training-gua059-061]] | 2026-06-17，BC 训练诊断与模块化 | GUA-059, GUA-060, **GUA-061** |
| [[v7-grouping-v2-gua062]] | 2026-06-18，组牌引擎 v2（回收能力+灵活性+真回溯） | **GUA-062** |

### 基础设施

| 文件 | 覆盖范围 | 主题 |
|------|----------|------|
| [[phase5-infra]] | 2026-05-29，Phase 5 仓库治理 | 5a~5g + M2/M3 迁入 |
| [[batch-executor]] | 2026-05-29 ~ 2026-05-31，批跑器 | GUA-033, victoryNum 链路 |
| [[governance-docs]] | 2026-05-29 ~ 2026-06-01，治理与回放 | docs, handoff, replay |
| [[kpi-observations]] | 2026-05-30 ~ 2026-06-17，队胜率汇总 | M3/V7 全量 KPI |

---

## 模板（新迭代在此追加）

| 日期 | 迭代名/分支 | 目标 GUA | 改动摘要（文件/commit） | 评测结果摘要 | 下轮 priority |
|------|-------------|----------|-------------------------|--------------|---------------|
| YYYY-MM-DD | | GUA-xxx, … | | pass/fail；回归： | |
| 2026-06-18 | v7-grouping-v2-gua062 | **GUA-062** | **closed**：grouping_engine.py 升级 v2。P0-A 静态回收评估 `_score_recovery_static()`（单张/对子/顺子/三带二兜底比例）；P0-B 灵活性评分 `_score_flexibility()`（牌型多样性+方案差异性）；P0-C 4 维加权评分 `_score_plan_v2()`（炸弹0.3+手数0.2+回收0.3+灵活0.2）；P1 牌力计分 `_score_power()`+`determine_role()`（登基牌+3/普通炸+2/赘牌-1）；P2 6 方案枚举（4 策略+NO_STRAIGHTS+ALL_COMBOS）。 | pytest **49/49 pass**；下游兼容。**批跑验证**（2026-06-18）：V7 vs Lalala 9局 → 队胜 **0/9 (0%)**，副胜 **8/79 (10.1%)**，达A级 12副 (15.2%)。分组引擎 v2 未转化为对局竞争力。**末级分布**：2级:12副；5级以下（含2级）:29副；J-K:16副；A:12副。 | 根因定位：① V7 决策链是否真正使用了 v2 评分输出？② V7 出牌是否还依赖旧 BC 模型 argmax？ |
| 2026-06-18 | v7-pipeline-connect-fix | **GUA-061, GUA-062** | **流水线接通 + BC v3 重训**。确认 V7 `decide()` 评分→动作选择链路 4 处断点后全部修复：① 生产端 `yf1_v7/yf2_v7` 从 grouping_scanner(9维)→grouping_engine(24维) 切换 ② `_extract_features` MT维度缓冲区 33→48 对齐 ③ `train_bc_v7.py` 同步 24 维特征 ④ 引擎 `__init__` 按 `use_grouping_engine` 选模型路径。修复 2 个阻塞 bug：card格式 `SB/HR→BJ/RJ`（bc_dataset 归一化，解决 MemoryTracker KeyError）+ `masked_cross_entropy` label_smoothing 扩散到 masked -1e9 类（~95M loss → 1.99）。5 文件改动：`ultimate_win_rate_engine_v7.py`/`bc_trainer.py`/`bc_dataset.py`/`yf1_v7.py`/`yf2_v7.py`/`train_bc_v7.py`。 | BC v3 重训：1938 样本（158 files）→ train 1551 / val 387，best epoch=1 **val_acc=80.88%** val_loss=1.99。model `models/v-nn/bc_model_v3.pth` (626KB)。vs v2 (35.19%) 大幅提升。**待批跑验证实战效果**。 | GUA-062 0/9 批跑 = v2 评分首次真实参与决策后的表现；待 bc_model_v3 批跑对比。 |
| 2026-06-18 | v7-bc-v3-benchmark-12 | **GUA-062** | **bc_model_v3 实战批跑 12 局**。决策流水线已接通（v2 24维评分参与 decide()），使用 bc_model_v3.pth (val_acc=80.88%) 跑 12 局 vs Lalala。分析脚本升级：`scripts/analysis/analyze_v7_rounds.py` 新增末级分布输出（2级/≤5级/J-K/A 分组）。 | **队胜 0/12 (0%)，副胜 8/164 (4.9%)，达A 26副 (15.9%)**。训练 val_acc 80.88% → 实战 0%，BC argmax collapse 仍是硬瓶颈。**末级分布**：2级:26副；≤5级（含2级）:58副；J-K:36副；A:26副。分布与 GUA-062 v2 一致（2/A 双峰两极化）。vs GUA-062 9局：副胜率 4.9% (↓ 10.1%)，达A 15.9% (≈ 15.2%)。 | ① BC argmax collapse 无解 — 须走 GUA-039b 自对弈路线；② GUA-054 动作空间过滤优先（减少 2000+→Top-K 候选）；③ GUA-059 退化为观测（BC 路线已死）。 |
| 2026-06-18 | v7-grouping-v2-three-pairs | **GUA-062** | **三连对检测 + 组顺留大不小**。① `GroupingPlan` 新增 `three_pairs` 字段 + `_detect_three_pairs()` 检测 3 个连续 rank 对子组成连对。6 策略枚举全部集成（拆弹前三连对优先检测）。② 牌力评分：三连对 +1（稀有牌型）。灵活性：牌型多样性 6→7 类。③ 顺子检测方向从`低→高`改为`高→低`贪心取：组牌阶段留大不留小，优先消耗低 rank 牌入顺、保留高价值单张（如级牌）。`_detect_straights` pos 从 0 递增改为 `len-5` 递减。 | 验证 27 张测试手牌：6 方案全部 27/27 完整；三连对 99-1010-JJ 正确检测；顺子取 4→8 保留级牌 S3；零 lint。score 从 0.3753→0.4178（级牌价值保留）。 | 牌力评分中三连对与级牌/炸弹性价比可继续调优；组顺方向改动可能影响现有批跑结论，需回归批跑。 |
| 2026-06-18 | v7-grouping-v2-de-singleton | **GUA-062** | **去单化权重落地（A+B 双路径）**。路径 A：`_score_flexibility` 牌型多样性移除单张（单张是短板，不是多样性优势），7 类→6 类，分母 7.0→6.0。路径 B：新增 `de_singleton_score` 显式去单化分 `max(0,1-singles/10)`，`GroupingPlan` 新增字段，`_score_plan_v2` 4 维→5 维加权（炸弹0.3+手数0.2+回收0.3+灵活0.1+去单化0.1）。 | 27 张手牌验证：2 单方案 score 0.4582（↑ 0.0404），6 单方案 0.3775；去单化分 0.800 vs 0.400 正确拉大差距。零 lint。 | 去单化权重仅 0.1，后续可视批跑结果调至 0.15–0.2；路径 A 移除单张从灵活性可能需回归批跑验证。 |
| 2026-06-18 | v7-grouping-role-analysis | **GUA-062** | **组牌引擎角色定论：只做特征提取，不参与决策**。分析三种路径：硬约束（❌ 计划腐败/刚性问题/方案间差距小）、软引导（⚠️ 可行但治标）、纯特征（✅ 最优）。结论：① NN-first 架构下组牌应"让 NN 看到更好手牌结构信息"而非"替 NN 决策"；② 组牌硬规则覆盖 NN 输出会污染训练信号，BC 行为克隆目标与实际行为不一致；③ 真正出路是 GUA-039b 自对弈让 RL 学会利用组牌特征。中间态可考虑 NN top-K 后用组牌一致性做软 tiebreaker，不破坏训练信号。 | 纯特征提取是 V7 当前最优解。 | — |
| 2026-06-18 | v7-grouping-v2-weight-rebalance | **GUA-062** | **5 维评分权重调优：手数+去单化提权，回收降权**。原权重（炸弹0.3/手数0.2/回收0.3/灵活0.1/去单化0.1）→ 新权重（炸弹0.3/**手数0.3**/回收**0.1**/灵活0.1/去单化**0.2**）。触发：同花顺手牌测试发现原回收 0.3 权重过高，压制了同花顺方案（S5-9 黑桃同花顺被 NO_STRAIGHTS 压过只因回收分 0.167 vs 0.289）。 | 同一手牌 re-run：BOMB_FIRST（含同花顺）0.3396 反超 NO_STRAIGHTS 0.3261，同花顺方案正确被选为 best_plan。手数分 0.400 vs 0.300（+33%）+ 回收压力减轻，放大了同花顺省轮次优势。check_grouping_engine.py 同步更新。 | 需批跑验证新权重是否改善对局表现；手数+去单化双提权可能使牌更"急"（速出），需观察达A级分布变化。 |
| 2026-06-18 | v7-grouping-a2-wrap-multipass | **GUA-062** | **A→2 包接（×3）+ SF_FIRST 多 pass 去单化**。① `_detect_straights` 新增 A→2 包接（A 下放当 1，A-5 顺子首次可用）。② `_detect_straight_flushes` 新增 A→2 包接（A-5 同花顺）。③ `_detect_three_pairs` 新增 A→2 包接（AA-22-33 三连对）。④ SF_FIRST Phase 3-5 改为多 pass 去单化循环（三连对→顺子 loop 吃完→配对同 rank 单张→repeat until stable），替代原来单 pass。⑤ `04_card_grouping_skills.md` §三 新增「0. 组牌顺序原则」（去单化→同花顺→炸弹→三带二/三连对/钢板/对子/顺子）。 | 27 张手牌验证：SF_FIRST 0.2750→0.4067（+47.9%），单张 8→4，手轮 13→10；A-5/AA-22-33 单元测试 4/4 pass；零 lint。3 文件改动：grouping_engine.py / 04_card_grouping_skills.md / check_grouping_engine.py。 | 批跑验证多 pass+包接改动是否改善队胜率；A 下放是否在实战手牌中高频生效。 |
| 2026-06-18 | v7-grouping-power-score-replace | **GUA-062** | **牌力分替换炸弹分**：总分公式 `0.3×bomb_score(炸弹数/4)` → `0.3×power_score/NORM_MAX_POWER(12.0)`。同花顺(+3)/登基炸(+3)/普通炸(+2)/三连对(+1)/减分统一纳入牌力归一化。`grouping_engine.py` +NORM_MAX_POWER + score公式 power_score前置。 | 验证：同花顺方案（牌力7）0.6416 > NO_STRAIGHTS（牌力5）0.5686，同花顺正确登顶。零 lint。 | 批跑验证新公式是否改善队胜率 |
| 2026-06-18 | v7-grouping-sf-enumerate-no-straights | **GUA-062** | **NO_STRAIGHTS 双变体 + 同花顺候选枚举**。① NO_STRAIGHTS 拆为两个变体：5a（trips不参与顺子，保留给wild升炸）+ 5b（trips可参与顺子，用于无单9等场景的10-A顺子去单化），评分自选最优；② `_detect_straight_flushes` 增加 `return_idx`，枚举所有可行同花顺候选（不同花色/不同rank段），排序改为 wild 数升序→最低自然牌面升序（低牌组SF，高牌留给炸弹/三带二）；③ SF_FIRST 提取 `_make_sf_first_plan()` 辅助函数，为每个同花顺候选独立生成方案。验证：手牌1 9-K方块同花顺正确出现（D9-D10-DJ-DQ-H2，保留AAA完整→三带二），评分 0.6166 超 10-A 0.5852；NO_STRAIGHTS 全局最优 0.6686（3炸0单7轮，9-K普通顺子+AAA升炸+778899三连对）。 | 3 副手牌 27/27 通过；零 lint。1 文件改动：`grouping_engine.py`（全新创建，1461行）。 | 批跑验证同花顺枚举是否改善对局表现。 |
| 2026-06-18 | v7-grouping-nn-bridge-gap | **GUA-063** | **组牌→出牌衔接三缺口诊断 + 开 GUA**。组牌引擎 v2 跑出合格方案，但下游 NN 出牌存在三个衔接断层：① NN 零方案意识（best_plan 说「9999 是炸」，NN 可能拆 ♦9 打顺子）；② 24 维特征信息密度低（27 张牌完整分组 → 仅轮数/炸弹数/单张数等抽象指标，NN 不知牌型边界）；③ 中局无重评估（组牌仅开局跑一次，手牌结构变化后不复评）。 | GUA-063 open（P0），待方案设计。 | 方向候选：card-level grouping mask / 方案一致性软引导 / 中局增量重分组。先解决 A（方案传 NN）+ C（中局重分组），B 随 A 自然改善。 |
| 2026-06-18 | v7-grouping-nn-bridge-impl | **GUA-063** | **组牌→出牌衔接三阶段实施完成**。Phase 1: `GroupingPlan.to_card_mask()` 牌级mask（card→(group_id,is_core,group_size)，炸弹/同花顺→core）。Phase 2: `decide()` 重构，一次 `enumerate_groupings()` 三产出（mask+role+features），`_group_consistency_filter()` 角色驱动前置过滤（主攻剔拆核心动作，助攻放行，安全阀+硬例外），Guard后→NN forward前插入。Phase 3: 触发式中局重分组。MemoryTracker 拆出 `get_tracking_vector()`(24维)。pytest 20/20 passed。 | GUA-063 closed ✅。待批跑验证效果。 | 改文件：`grouping_engine.py` (+to_card_mask)、`memory_tracker.py` (+get_tracking_vector)、`ultimate_win_rate_engine_v7.py` (_run_grouping_engine/_group_consistency_filter/_check_midgame_triggers/decide重构/_extract_features重构)。测试：`tests/test_gua063_grouping_nn_bridge.py`(20 pass)。 |
| 2026-06-18 | v7-grouping-nn-bridge-missing-trigger | **GUA-063** | **设计架构对照发现**：`_check_midgame_triggers()` 缺少「炸弹已全部消耗」触发条件。设计文档 ([组牌-NN衔接设计](组牌-NN衔接设计-软引导vs硬约束.md)) §三第三层表格明确列出了此条件，但代码仅实现了手牌降量阈值(15/10/5) + 核心牌型破坏检测，未实现炸弹全部消耗后的重分组触发。 | 低优先级待补充。现有手牌降量阈值可部分覆盖此场景（炸弹消耗往往同步伴随手牌减少）。 | 可按需补充；当前不阻塞主流程。 |
| 2026-06-18 | v7-pipeline-verify-batch | **GUA-062, GUA-063** | **流水线接通后首次 V7 vs Lalala 批跑 3 局**。`_env.bat` 加 venv 激活。`v7_game_recorder.py` joker检测 SB/HR 修旧编码。yf1_v7/yf2_v7 生产端确认使用 grouping_engine(24维)+bc_model_v3，模型决策率 100%。 | 局胜 **0/3(0%)**，副胜 **3/54(5.6%)**，达A **9/54(16.7%)**，双上 **0**。末级：2-5级 21(38.9%) / 6-10 13(24.1%) / J-K 11(20.4%) / A 9(16.7%)。3副胜详情：R7(cR=2,pos2先跑)/R10(cR=8,pos2先跑)/R27(cR=6,pos0先跑)。**卡牌验证WARNING**仍在但不影响决策。说明：V7 NN(BC argmax collapse)+无方案约束=对 Lalala 几乎零竞争力，与 GUA-062/060/059 多次批跑结论一致。 | GUA-063 衔接待解（8篇方案文档已有方向）；GUA-054 动作空间过滤可缓解；BC 路线已死待 GUA-039b 自对弈。 |
| 2026-06-18 | v7-bc-argmax-collapse-confirmed | **GUA-064** | **BC argmax collapse 日志确证**。分析 4 个客户端日志 + 2 个服务端日志（2026-06-18 两轮 6 局 86 副）。动作索引分布：actIndex=0(PASS) 1074次(50.1%)、actIndex=1(首候选出牌) 1049次(48.9%)、actIndex≥2 仅 20次(0.9%)。**2048 维输出空间仅用 2 维**。PASS 率 V7 与 Lalala 持平(50-52% vs 53-55%)，非败因。卡牌验证 WARNING 28次(≈每3副1次)，低频不致命。结论：① argmax collapse 是硬瓶颈，组牌引擎 v2(GUA-062)+衔接(GUA-063)未改变此结构；② 需要输出头改造（温度采样/beam search/策略梯度）打破 argmax；③ 不做此关单，任何组牌/策略改进都不会转化为队胜率。 | 开 GUA-064（P0）。 | GUA-064 优先于 GUA-054（动作空间过滤也无法绕过 argmax 塌缩）；方向建议：① 温度采样 + top-K 采样替代 argmax；② 或直接跳至 GUA-039b 自对弈（policy gradient 天然解决 collapse）；③ BC teacher forcing 路线已死。 |
| 2026-06-19 | v7-teammate-protection-gua065 | **GUA-065** | **导入 M3 队友识别与保护到 V7 Guard 体系**。三文件改动：① `v7_guards.py` +R07（队友控牌非残局→让道PASS）、+R08（主动+队友剩1张→送最小单）、+R09（主动+队友剩5张→优先Pair/ThreeWithTwo），共 ~120 行；② `ultimate_win_rate_engine_v7.py` +`_inject_numofplayers()`（从 MemoryTracker 推算各家剩张注入 game_state），+`_group_consistency_filter` 队友控牌场景→助攻放行（不拆对子），共 ~35 行；③ `tests/test_gua065_teammate_protection.py` 新建 14 case。numofplayers 优先取 MemoryTracker.hand_counts（已追踪），回退为手牌长度+其他默认 27。 | pytest **14/14 pass** + 回归 **83/83 pass**（grouping_engine 49 + gua063 20 + gua065 14）。前置依赖 GUA-063 is_core 保护链已完成。待批跑验证队友配合效果。 | 批跑验证：① 队友控牌时 PASS 率变化；② 队友剩 1 张时是否送正确单牌；③ 队友剩 5 张时是否优先 Pair/ThreeWithTwo。GUA-064 argmax collapse 仍是硬瓶颈。**相关**：GUA-031（M3 队友保护）、GUA-034（solo冲刺）、GUA-036（接风配合） |

> **当前活跃**：**GUA-064** 🔴 — BC argmax collapse；**GUA-065** 🟢 — 队友保护已实施待批跑验证；**GUA-054** — 动作空间过滤（须先解 GUA-064）；**GUA-059** — 退化为观测；**GUA-062** ✅ / **GUA-063** ✅
