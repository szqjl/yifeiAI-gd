# V7 队胜率历史（Win Rate History）

> **目的**：避免 V4-V5 覆辙——V 系列历史从未认真记录对战 KPI。本文件**强制**每条 V7 迭代记录批跑结果，**评估次数=0 即视为未实施**。
> **创建**：2026-06-07（V4-V5 教训护栏）
> **真源分析**：[`v4v5v6-lessons-2026-06.md`](./v4v5v6-lessons-2026-06.md)
> **关联**：[`V7-实施方案.md` §3 验收总表](../guandan-brain/V7-实施方案.md) 「对战 KPI 验证」列

---

## 记录格式（每次批跑一行）

```
| 日期 | 目标 GUA | 改动摘要 | 批跑命令 | 局数 | V7 队胜率 | 副数 | 备注 |
```

**字段说明**：
- **改动摘要**：必填，与 `ITERATIONS.md` 联动
- **批跑命令**：`python scripts/launchers/v7/run_v7_vs_lalala_games.py --games 3` 或 `RUN_V7_VS_LALALA.bat 12`
- **局数**：3 的倍数（3/9/12）
- **V7 队胜率**：`[0]+[1]` vs 总局数；**≥30%** 才算 GUA-039b 验收通过
- **副数**：`game_records_v7/` mtime 窗新增 JSON 数 / 2
- **备注**：胜场负局是否胶着 / 异常短局原因 / 与上次对比

---

## 记录

| 日期 | 目标 GUA | 改动摘要 | 批跑命令 | 局数 | V7 队胜率 | 副数 | 备注 |
|------|---------|---------|---------|------|----------|------|------|
| 2026-06-05 | V7-006/V7-007 | 修复 V7 victoryNum 链路 + 批跑路径 | `run_v7_vs_lalala_3games.py` | 3 | 0/3（0%） | 92 | GUI 跑局；模型决策 100% |
| 2026-06-06 | V7-007 | 批跑 3 局（scores 汇总 bugfix） | `run_v7_vs_lalala_3games.py` | 3 | 1/3（33.3%） | 46 | 较 06-05 回升 |
| 2026-06-06 | V7-007 | 3 局批跑复盘定音（lalala 满编碾压） | `run_v7_vs_lalala_3games.py` | 3 | 0/3（0%） | 15 | **副数异常短**；4 席 10:44:27 齐连，lalala 连升 2→A 横扫 |
| **合计 06-05~06-06** | — | — | — | **9** | **1/9（11.1%）** | ~153 | — |
| 2026-06-17 | GUA-038 | BC v2 重训（录牌→特征→训练→模型部署，val_acc=82.57%） | `python scripts\launchers\v7\run_v7_vs_lalala_games.py --games 3` | 3 | 0/3（0%） | 51 | V7 队达 A 级 **14 次**（共 51 副），lalala 3-0 横扫 |
| 2026-06-17 | GUA-038 | BC v2（M3 胜局重训 action_dim 512→2048，val_acc=35.85%）+ 净盘 12 局 | `python scripts\launchers\v7\run_v7_vs_lalala_games.py --games 12` | 12 | **0/12（0%）** | **204** | 副级：V7 赢 24/204（11.8%），V7 达 A **32 副**；lalala 全 4 批连续 vn=[0,3,0,3]。对比前次 3 局（8/58=13.8%）：副胜率基本持平（11.8%），V7 竞争力无显著改善。累计 **1/21（4.8%）**。日志：`logs\v7_vs_lalala_20260617_130258.log` |
| 2026-06-17 | GUA-038 | BC v2（M3胜局366局重训，val_acc=35.19%，bc_model_v2.pth）+ 12局批跑 | `python scripts\launchers\v7\run_v7_vs_lalala_games.py --games 12` | 12 | **0/12（0%）** | **244** | 副级：V7 赢 0/236（0%），lalala 赢 236/236（100%）；4批全部 vn=[0,3,0,3]。使用M3规则引擎胜局训练，模型仅训练1个epoch即early stopping。V7实战表现极差，**需增加训练轮次或调整训练策略**。累计 **1/33（3.0%）**。日志：`logs\v7_vs_lalala_20260617_145158.log` |
| 2026-06-18 | GUA-062 | 组牌引擎 v2（回收0.3+灵活0.2+4维加权+6方案枚举）批跑验证 | `python scripts\launchers\v7\run_v7_vs_lalala_games.py --games 9` | 9 | **0/9（0%）** | **79** | V7 vs Lalala 9局：队胜 0/9，副胜 8/79（10.1%），达A 12副（15.2%）。分组引擎 v2 未转化为对局竞争力；副级 2/A 双峰两极化。**末级分布**：2级:12副；5级以下（含2级）:29副；J-K:16副；A:12副。累计 **1/42（2.4%）**。日志：`v7_batch_output.txt` |
| 2026-06-18 | GUA-061/062 | 决策流水线接通 + BC v3 重训。修复4处断点（prod端9→24维切换/MT维度33→48/yf1_yf2引擎统一）+ 2个阻塞bug（card格式SB/HR→BJ/RJ归一化、label_smoothing扩散到masked类~95M loss修复）。6文件改动。 | 训练命令 `python scripts/train_bc_v7.py` | — | 训练指标 (待批跑) | — | BC v3 重训：1938样本 val_acc=**80.88%** (vs v2 35.19%)，model `bc_model_v3.pth`。**待批跑验证实战效果**（GUA-062 此前 0/9 = v2 评分首次真实参与决策的表现）。 |
| 2026-06-18 | GUA-062 | bc_model_v3 实战 12 局批跑。决策流水线已接通（v2 24维评分） + bc_model_v3.pth (val_acc=80.88%)。分析脚本升级 `scripts/analysis/analyze_v7_rounds.py` 新增末级分布。 | `python scripts/analysis/analyze_v7_rounds.py -s 4` | 12 | **0/12（0%）** | **164** | 队胜 0/12，副胜 **8/164 (4.9%)**，达A 26副 (15.9%)。**末级分布**：2级:26副；≤5级（含2级）:58副；J-K:36副；A:26副。val_acc 80.88% → 实战 0%，BC argmax collapse 无解。分布与 GUA-062 v2 一致（2/A 双峰），bc_model_v3 未改变结构问题。累计 **1/54（1.9%）**。 |
| 2026-06-18 | GUA-062 | A→2 包接（×3）+ SF_FIRST 多 pass 去单化。`_detect_straights`/`_straight_flushes`/`_three_pairs` 各加 A→2 包接（A下放当1）；SF_FIRST Phase 3-5 从单 pass 改为多 pass 循环。`04_card_grouping_skills.md` 新增组牌顺序原则。3 文件改动：grouping_engine.py / 04_card_grouping_skills.md / check_grouping_engine.py。 | 单元测试 (无批跑) | — | 待批跑验证 | — | 27 张手牌：SF_FIRST 0.2750→0.4067（+47.9%），单张 8→4，手轮 13→10。A-5 同花顺/AA-22-33 三连对 4/4 单元测试 pass。待批跑验证实战效果。 |
| 2026-06-18 | GUA-062 | **NO_STRAIGHTS 双变体 + 同花顺候选枚举**。① NO_STRAIGHTS trips 拆 5a/5b 两个变体（不参与顺子保留升炸 vs 可参与顺子去单化）；② `_detect_straight_flushes` `return_idx` 全候选枚举，低牌组SF优先（wild数升序→最低自然牌面升序）；③ SF_FIRST 提取 `_make_sf_first_plan()` 为每个候选独立生成方案。1 文件：`grouping_engine.py`（全新创建 1461行）。 | `python scripts/checks/check_grouping_engine.py` | — | 单元测试 (未批跑) | — | 3副手牌 27/27。手牌1：9-K方块同花顺正确出现（D9-D10-DJ-DQ-H2），三带二 AAA-44，SF_FIRST 0.6166；NO_STRAIGHTS 全局最优 0.6686（3炸0单7轮，9-K顺子+AAA升炸+778899三连对），与人工组牌一致。待批跑验证。 |
| 2026-06-18 | GUA-062, GUA-063 | 流水线接通首次批跑。_env.bat venv激活。v7_game_recorder.py joker SB/HR修旧编码。yf1/yf2_v7 prod使用grouping_engine 24维+bc_model_v3。模型决策率100%。 | `.venv\Scripts\python.exe scripts\launchers\v7\run_v7_vs_lalala_games.py --games 3` | 3 | **0/3（0%）** | **54** | 副胜 3/54(5.6%)，达A 9/54(16.7%)，双上0。末级：2-5 21(38.9%) / 6-10 13(24.1%) / J-K 11(20.4%) / A 9(16.7%)。3副胜：R7(cR=2,pos2)/R10(cR=8,pos2)/R27(cR=6,pos0)。累计**1/57(1.8%)**。BC argmax collapse+无方案约束→零竞争力。 |
| 2026-06-18 | GUA-062, GUA-063 | 流水线接通后第二批2轮6局。同配置：bc_model_v3 + grouping_engine v2 24维评分，模型决策率100%。 | `RUN_V7_VS_LALALA.bat 3` ×2 | 6 | **0/6（0%）** | **86** | 第1轮：副胜 2/48(4.2%)，达A 8/48(16.7%)，双上2。末级：2-5 18(37.5%) / 6-10 14(29.2%) / J-K 8(16.7%) / A 8(16.7%)。第2轮：副胜 4/38(10.5%)，达A 6/38(15.8%)，双上4。末级：2-5 16(42.1%) / 6-10 8(21.1%) / J-K 8(21.1%) / A 6(15.8%)。合计副胜 **6/86(7.0%)**，达A 14/86(16.3%)，双上6。末级：2-5 34(39.5%) / 6-10 22(25.6%) / J-K 16(18.6%) / A 14(16.3%)。环比+1.4pp(5.6%→7.0%)。累计**1/63(1.6%)**。 |
| 2026-06-19 | **GUA-065** | **导入 M3 队友识别与保护**。+R07（队友控牌非残局→让道PASS）、+R08（队友剩1张→送最小单）、+R09（队友剩5张→优先Pair/ThreeWithTwo）；`_inject_numofplayers()` 从 MemoryTracker 推算各家剩张；`_group_consistency_filter` 队友控牌→助攻放行不拆对子。3 文件改动（v7_guards.py / engine_v7.py / test_gua065），83/83 pytest。 | `python scripts/launchers/v7/run_v7_vs_lalala_games.py --games 3` | 6 | **0/6（0%）** | **110** | 2会话/6局/110副（诊断3局+正式3局）。副胜 **28/110（25.5%）**，V7达A 14副。末级：2:14(12.7%) / 3:8 / 4:6 / 5:22(20.0%) / 7:2 / 8:18(16.4%) / T:6 / J:14(12.7%) / Q:2 / K:4 / A:14(12.7%)。≤5:50(45.5%) / 6-10:26(23.6%) / J-K:20(18.2%) / A:14(12.7%)。Session1 副胜12/54(22.2%)，Session2 副胜16/56(28.6%)。环比前次(6/86=7.0%)：**副胜率大幅提升+18.5pp**（7.0%→25.5%），局级队胜仍0。GUA-064 argmax collapse 仍是硬瓶颈。累计**1/69（1.4%）**。日志：`logs\v7_vs_lalala_20260619_082614.log` |
| 2026-06-19 | **GUA-063/065/069** | **决议6-10全面实施 + 缩进bug修复**。决议6（角色分流过滤~140行）、决议7（Solo模式~15行）、决议8（接风跟线~16行）、决议9（R07按牌型curVal阈值~30行）、决议10（方案C投喂两阶段~50行）、角色阈值降档。**关键bug修复**：`_model_decision`/`_extract_features`/`_rule_based_decision`/`get_statistics` 被错误嵌套在模块级函数 `is_bomb_straight_flush_for_check` 内部导致98.4% PASS率。——修复后 PASS率 65.9%，模型正常决策。4文件改动（engine_v7.py / v7_guards.py / grouping_engine.py / 3个test文件），42/42 pytest。 | `python scripts/launchers/v7/run_v7_vs_lalala_games.py --games 3` ×2 | 6 | **0/6（0%）** | **68** | 2会话/6局：Session3（bug版PASS率98.4%）：3局/30副/副胜0(0.0%)/达A 6。Session4（修复后）：3局/38副/副胜4(10.5%)/达A 6。末级：2:12 / 3:4 / 4:2 / 5:4 / 7:2 / 8:4 / 9:2 / T:2 / J:2 / Q:2 / K:2 / A:6。≤5:22(32.4%) / J-K:6(8.8%) / A:6(8.8%)。修复后副胜率 10.5%，低于 GUA-065 单行（25.5%），但 model 正常工作。累计**1/75（1.3%）**。日志：`logs\v7_vs_lalala_20260619_122046.log`（bug版）/`logs\v7_vs_lalala_20260619_122824.log`（修复版）。 |
| 2026-06-19 | **GUA-070** | **三连对&钢板子结构拆分 + to_card_mask 牌型感知完善**。grouping_engine: ThreePair→3×pair_in_three_pair、SteelPlate→2×trip_in_steel_plate，均 is_core=True，防止拆三连对/钢板拿对子/三张单出静默放行。commit a7f8da0。 | `python scripts/launchers/v7/run_v7_vs_lalala_games.py --games 3` ×3 | 9 | **0/9（0%）** | **96** | 3局(28副)副胜5/28(17.9%) + 6局(68副)副胜12/68(17.6%)，合计副胜17/96(17.7%)。达A 17/96(17.7%)，双上0。末级：≤5:37(38.5%) / 6-10:27(28.1%) / J-K:18(18.8%) / A:17(17.7%)。3局与6局副胜率高度一致(~17.7%)，稳定性验证通过。vs GUA-063/065/069 Session4(+7.2pp)，vs GUA-065巅峰(-7.8pp)。累计**1/84（1.2%）**。 |
| 2026-06-19 | **GUA-066/068/069/070** | **Guard综合批跑：R10 greaterPos传参修复(GUA-066) + R11全局抑制牌节流(GUA-068) + 超弱角色core保护(GUA-069) + R12拆对子出单禁制+ThreeWithTwo is_core(GUA-070) + 决议6-10角色过滤/接风/投喂/Solo模式**。全量Guard+过滤+方案C投喂叠加运行。 | `python scripts/launchers/v7/run_v7_vs_lalala_games.py --games 9` | 9 | **0/9（0%）** | **108** | 3会话/9局：副胜 **4/108（3.7%）**，达A 20/108(18.5%)，双上4。末级：2:20,3:4,4:2,5:18,7:2,8:18,T:2,J:18,K:4,A:20。≤5:44(40.7%) / 6-10:22(20.4%) / J-K:22(20.4%) / A:20(18.5%)。⚠️ 副胜率 vs GUA-070 单行（17.7%）：**暴跌 -14.0pp**，可能随机方差或过滤叠加过严。2/A双峰持续（20+20）。累计**1/93（1.1%）**。日志：`logs\v7_vs_lalala_20260619_145700.log`。 |
| 2026-06-19 | **GUA-071** | **_heuristic_select 替代 NN argmax 首批跑**。`_heuristic_select` ~90行（四条优先级：①队友控牌→PASS、②对手急眼→炸、③非PASS优先、④正序最小节约牌力）。`_model_decision()` 不再调用，NN 权重保留。 | 手动 `python -m batch_executor` | 9 | **0/9（0%）** | **168** | 3会话/9局：副胜 **4/168（2.4%）**，达A 46/168(27.4%)，双上0。末级：2:28,3:6,4:4,5:24,6:8,7:6,8:16,9:8,A:28,J:12,K:8,Q:10,T:10。≤5:62(36.9%)/6-10:38(22.6%)/J-K:30(17.9%)/A:28(16.7%)。⚠️ **副胜率 2.4% vs 关单基线 25.5%（GUA-065）→ 严重未达标**。vs 上次综合批跑（3.7%）：-1.3pp 基本持平。达A 从 18.5% 升至 27.4%（+8.9pp），说明 heuristic 局部更优但全局决策不够。累计**1/102（1.0%）**。日志：`logs\v7_vs_lalala_20260619_174930.log`。 |
| 2026-06-20 | **GUA-071** | **_heuristic_select 继续迭代**（v7_guards.py / engine_v7.py / yf1_v7.py / yf2_v7.py 改动，3局验证） | 手动 `python -m batch_executor` | 3 | **0/3（0%）** | **36** | 1会话/3局：副胜 **2/36（5.6%）**，达A 6/36(16.7%)，双上0。名次分布：头2/二4/三36/末30。末级：2:6,3:2,4:2,5:4,6:2,8:4,9:2,T:2,J:4,K:2,A:6。≤5:14(38.9%)/6-10:8(22.2%)/J-K:8(22.2%)/A:6(16.7%)。vs 上次（2.4%）：副胜率+3.2pp 回升仍远低于 GUA-065 基线。2/A 双峰减弱（6+6 vs 28+28），A端改善明显。累计**1/105（1.0%）**。 |
| 2026-06-20 | **GUA-063/GUA-072** | **R16 队友送单精细化 + card_mask 退化保护批跑验证**。R16：`_group_consistency_filter` 新增硬例外（队友剩1张+下家≠1→放行全部）；设计文档管线顺序修正（Guard→group_filter→NN）。card_mask 三项修复已实施（GUA-072）。pytest 50/50 pass。 | `python -m batch_executor --server-path "offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe" --target-games 3 --clients yf1_v7 lalala3 yf2_v7 lalala4` | 3 | **0/3（0%）** | **42** | 1会话/3局：副胜 **10/42（23.8%）**，达A 6/42(14.3%)，双上10。名次：头10/二4/三32/四38。末级：2:6,3:4,5:6,6:4,7:2,8:6,9:2,J:4,Q:2,A:6。≤5:16(38.1%)/J-K:6(14.3%)/A:6(14.3%)。card_mask 诊断：零退化 ✅。R16 本批未触发（队友剩1张情况未出现）。vs GUA-065 基线（25.5%）：副胜率 -1.7pp 基本持平。累计**1/111（0.9%）**。日志：`logs\batch_executor_20260620_112107.log`。 |
| 2026-06-21 | **GUA-076** | **组牌方案完整性：AssertionError→warning+剔除**。`enumerate_groupings()` 防御性 AssertionError 改为 `warnings.warn()` + 自动剔除不完整方案。1000副随机复现零丢牌，根因已由2026-06-20重构修复。pytest `test_gua076_plan_completeness.py` 60/60 pass。 | `python scripts/launchers/v7/run_v7_vs_lalala_games.py --games 3` | 3 | **0/3（0%）** | 16（仅1局记录） | 1会话/3局：队胜0/3(0%)，V7赢副0/16(0%)。card_mask 退化：0 ✅。GUA-076 warning：0（无不完整方案）。累计**1/114（0.9%）**。日志：`logs\v7_vs_lalala_20260621_114617.log`。 |
| 2026-06-21 | **GUA-078**, **GUA-079** | **MemoryTracker decide 入口（①b）+ 残局管线 + GUA-079 单张牌力/R12/greaterPos 路由**。批跑后 `analyze_v7_rounds.py --all -s 1` + `check_endgame_agent.py --scan` 联合分析。 | `batch_executor` / V7 GUI **3 局**（`20260621224249`→`224310`） | 3 | **0/3（0%）** | **38** | **局级**：vn=`[0,3,0,3]` lalala 3-0。**副级**：V7 赢 **0/38（0.0%）**；名次 二10/三34/末32（无头游）；Lalala 达A 6/38(15.8%)；末级 ≤5:12(31.6%) / J-K:10(26.3%) / A:6(15.8%)。**vs 历史**：副胜 vs GUA-063（23.8%）**−23.8pp**；vs GUA-076 同日（0/16）同为 0% 但本批 38 副完整。**残局扫描**（`check_endgame_agent.py --scan`，38 文件/913 决策点）：激活 **603/913（66.0%）**，含残局文件 33/38；Q 命中 **220/603（36.5%）** — Q1:102 / Q2:118 / Q0:0 / Q3:0；banned 过滤移除 1798 action。对比 GUA-078 开发扫描（32 记录/756 点：激活 42.1%、命中 48.4%）：**激活率↑、命中率↓**；扫描为牌谱重建 numofplayers（非 live `publicInfo.rest`），样本见 `26/0/4/0` 类异常剩张，与实战 decide 路径可能有偏差。**结论**：KPI 无改善；残局模块离线覆盖高但未转化为副胜。累计**1/117（0.9%）**。分析：`python scripts/analysis/analyze_v7_rounds.py --all -s 1`；`python scripts/checks/check_endgame_agent.py --scan`。 |
| 2026-06-28 | **GUA-080** | **GUA-072 拆炸时序押后净盘冒烟批跑（R-G080-4 scanner/card_mask 降级观测）**。post `f91f0af`；净盘后 1 批 × batch_games=3。 | `python scripts\launchers\v7\run_v7_vs_lalala_games.py --games 3` | 3 | **0/3（0%）** | **19** | vn=`[0,3,0,3]`，`vn_source=gameResult`，批末校验通过；**真实副数 19**（38 JSON = yf1+yf2 双录，按 round+level 成对）。副胜 **2/19（10.5%）**（第 8/14 副）。card_mask / grouping_scanner / 组牌引擎失败：**零退化** ✅（R-G080-4 本批通过）。末级：2:6 / ≤5:16 / J-K:6 / A:6。vs GUA-062 9局（10.1%）≈持平；vs GUA-063（23.8%）**−13.3pp**；3 局小样本**不关 GUA-080**。累计 **1/120（0.8%）**。日志：`logs\v7_vs_lalala_20260628_085452.log`。 |
| 2026-06-28 | **GUA-080** | **拆炸时序 9 局环比批跑（3 批 × 3 局，restart=2）**。同机续跑（含上午 3 局冒烟后未再净盘则牌谱混窗；本行指标仅计 **09:03 起 9 局** 窗口）。 | `python scripts\launchers\v7\run_v7_vs_lalala_games.py --games 9` | 9 | **0/9（0%）** | **59** | 3 批 vn 均 `[0,3,0,3]`，末批快照同；`completed_games=9/9`。**59 副**（118 JSON，按批内 round+level 成对）。副胜 **2/59（3.4%）**（批1 1/23、批2 1/19、批3 0/17）。**零退化** ✅。末级合计：2:20 / ≤5:44 / J-K:24 / A:20。vs 同日上午 3 局（10.5%）**−7.1pp**；vs GUA-062 9局（10.1%）**−6.7pp**；vs GUA-063（23.8%）**−20.4pp**。**GUA-080 仍不关单**（副胜率未回升）。累计 **1/129（0.8%）**。日志：`logs\v7_vs_lalala_20260628_090331.log`。 |
| 2026-06-28 | **GUA-072/075/078** | **净盘后决策链批跑（GUA-072 信念注入 + heuristic ③b/③c；组牌冻结）**。3 批 × batch_games=3，`restart_count=2`。 | `python scripts\batch\run_v7_vs_lalala_games.py --games 9` | 9 | **0/9（0%）** | **55** | vn 各批 `[0,3,0,3]`，累加 `[0,9,0,9]`，批末校验通过；**55 副**（110 JSON，round+level 成对）。副胜 **6/55（10.9%）**（批1 4/19=21.1%、批2 0/16、批3 2/20=10.0%）。**零退化** ✅（R-G080-4）。vs 同日上午 GUA-080 9局（3.4%）**+7.5pp**；vs 3局冒烟（10.5%）≈持平；**局胜仍 0%**。累计 **1/138（0.7%）**。日志：`logs\v7_vs_lalala_20260628_091551.log`。 |

---

## 阈值

| 节点 | 队胜率门槛 | 触发 |
|------|----------|------|
| GUA-037a 完工 | 必跑 ≥3 局，**变化方向**记录 | 0% → 0% 也算"已观测" |
| GUA-037b 完工 | 必跑 ≥3 局，**不退化** | 需 ≥ GUA-037a 末值 |
| GUA-038 完工 | 必跑 ≥3 局，**> 0%** | 哪怕只赢 1 局 |
| GUA-039b 完工 | **30 局 vs lalala，≥ 30% 队胜率** | V 系列首次战 KPI 硬门槛 |
| V 冒烟 ON 触发 | 50 局 ≥ 40% 队胜率 | 治理 §7.2 启用条件 A |

---

## 与其他文件的关系

- **本文件 = 战 KPI 真源**（每条 V7 决策改动后必填）
- `ITERATIONS.md` = 改动摘要 + 文件列表
- `ISSUES.md` = 缺陷登记 + 完成定义（含"对战验证"条目）
- `replay_word.md` = 单局复盘文字稿
- `game_records_v7/` = 单副 JSON 牌谱（Layer 2 产物，不进 Git）

---

## 复发排查

**症状**："V7 又赢了 0/3 局"
1. 先查本文件最近 5 行——是否有过 1/3 的拐点？回归到 0/3 说明某条改动破坏
2. 对比 `game_records_v7/` 副数 — 副数过短（如 < 10）说明没真打完
3. 对比 `logs/yf*_v7_*.log` — 是否四席就绪门闩生效（GUA-044）
4. 不要用"训练指标好"作为辩解

---

## 治理条款

- ❌ **禁止**用"批跑失败 / 跑不起来 / 没时间跑"作为本文件空白理由
- ❌ **禁止**只填"准确率 60% / loss X"而不填队胜率
- ✅ **必须**每条 GUA 完工时有一条对应记录
- ✅ **必须**记录批跑日志路径（`logs/v7_vs_lalala_*.log`）
