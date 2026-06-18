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
