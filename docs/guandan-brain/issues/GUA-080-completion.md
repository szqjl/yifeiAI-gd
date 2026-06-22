# GUA-080 完成定义（组牌引擎：中炸 vs 三连对 — 拆炸取舍）

> 登记 **2026-06-22**：回放 `game_records_v7/20260621224308510816 [yf1_v7]-[opponent_1_3]-[16]-[2].json`，贡后首步 `curRank=J`，`enumerate_groupings` 真源复现。

## 现象

`_basic_classify` **正确识别** 3 组炸弹，但最终 `best_plan.bombs` **仅保留 Q 炸**：

| 阶段 | 8 点 | 10 点 | Q 点 |
|------|------|-------|------|
| `_basic_classify` | **五星 8 炸** `S8 H8 C8 C8 D8` | **四星 T 炸** `HT HT CT CT` | **四星 Q 炸** `SQ HQ CQ DQ` |
| 最终 BOMB_FIRST 方案 | 拆为 **888 三张** + 三连对子 `C8 C8` | 拆为 三连对 `HT HT` + 对子 `CT CT` | **保留四 Q 炸** |

最终方案（10 手，role=助攻，score≈0.256）：

- 四 Q 炸、888 三张、三连对 8-9-10（`C8 C8` + `S9 C9` + `HT HT`）、三带二 666+33、对 55/77/TT、单 D2/K/A

**问题**：四星 T 炸、五星 8 炸均未进入 `plan.bombs`，决策侧 `to_card_mask` 无 T/8 炸弹 core 保护 → 后续出牌可能拆炸或无法以炸抢权。

## 主攻 → 助攻 / 弱牌（核心因果 · GUA-072 提前拆炸）

本手 `_basic_classify` 有 **3 炸**（五星8 + 四T + 四Q），按常识应为 **主攻** 牌力；引擎输出 **role=助攻、score_tier=偏弱**。

| 指标 | 引擎唯一方案（GUA-072 拆 8/T 后） | 假想保三炸（引擎未枚举） |
|------|----------------------------------|-------------------------|
| `power_score` | **1** | **5** |
| `determine_role` | **助攻**（1–3） | **主攻**（4–6） |
| 4 维总分 | **0.2556** / 偏弱 | **0.4800** / 好牌 |
| 炸弹数 | 1（仅 Q） | 3（8+T+Q） |

**因果链（定音）**：

1. **GUA-072 Step1**：`_safe_to_break_bomb` 把 **≤10 点炸**（本手五星8、四T）在 SF 池构建时 **提前拆入普通牌池**，早于 `BOMB_FIRST` 策略分支。
2. **`_run_multi_pass_loop`**：三连对 8-9-10 消耗 T/8 炸张 → 最终 `plan.bombs` 只剩 **受保护的 Q 炸**。
3. **`_score_power`**：仅 +2（Q炸）+1（三连对）−3（小单/小对）→ **power=1** → `determine_role` 映射为 **助攻**；总分 **0.26** → **偏弱**。
4. **无并列「保炸方案」**：去重后仅 1 plan，NN/决策侧只能读到助攻+弱牌信号，整副按弱牌打法。

> **结论**：本副「主攻变助攻」**不是** `_score_power` 公式误算，而是 **GUA-072 提前拆炸 + 单方案枚举** 使三炸牌力在组牌层被抹平。

**诊断命令**（去重前三策略）：

```bash
python scripts/checks/check_grouping_engine.py \
  --hand "D2,C3,D3,S5,D5,S6,H6,D6,C7,D7,S8,H8,C8,C8,D8,S9,C9,HT,HT,CT,CT,SQ,HQ,CQ,DQ,DK,SA" \
  --rank J --pre-dedup
```

## 根因链（`grouping_engine.py`）

0. **GUA-080 时序修复（2026-06-22）**：GUA-072 拆弹从 Step1 SF 池 **押后** 至 `_make_plan_from_sf` Step2，由 `break_bombs` 控制。SF 池仅用非炸牌；`BOMB_FIRST` 保全部炸弹，`ROUND_OPTIMAL/ALL_COMBOS` 仍拆 ≤10 炸去单化。

1. **GUA-072 拆弹阈值**：`_safe_to_break_bomb(bomb)` → 点数 **≤10 可拆**，J/Q/K/A 保护。T 炸、8 炸均落入可拆池。
2. **`_run_multi_pass_loop` + `_detect_three_pairs`**：为组 **8-9-10 三连对**，从可拆池消耗 `HT HT`（T 炸）与 `C8 C8`（来自 8 炸），余 `CT CT` 降为普通对子。
3. **五星 8 炸**：5 张 8 拆为 **888 trips** + 三连对中的 `C8 C8`，**整炸未保留**。
4. **方案枚举不足**：本手 `enumerate_groupings` 仅返回 **1 个 plan**（BOMB_FIRST），无「保留 T 炸 + 8 炸、放弃三连对」的并列候选参与评分。
5. **评分权重**：`recovery_score` / `flexibility_score` / `de_singleton_score` 可能压过 **保留中炸的牌力分**（`bomb_score` / `power_score`），导致拆炸换结构得分更高。

## 讨论焦点（中炸 vs 三连对）

| 维度 | 保留四 T 炸 / 五星 8 炸 | 拆成 8-9-10 三连对 |
|------|------------------------|-------------------|
| 牌力 / 控权 | 中炸可抢出牌权、压制顺子/三带 | 三连对需一次出 6 张，灵活性低 |
| 手数 | 炸 1 手 + 其余结构 | 三连对 1 手，但拆散 2 组炸 |
| 残局 | 炸是 sprint / Q3 兜底硬资源 | 三连对在残局未必能 intact 打出 |
| 掼蛋常识 | 四星 10、五星 8 通常 **不应为顺子型结构主动拆散** | 仅当显著降低手数且回收分极高时才可考虑 |

**待定音规则**（实施前需批跑 A/B，勿写死 if-else 单局）：

- **R-G080-1**：四星及以上、点数 **≥8** 的炸弹，默认 **不可拆** 组三连对/顺子（可配置阈值）。
- **R-G080-2**：五星炸 **永不拆** 为 trips+对子（除非全手 ≤5 张残局重分组）。
- **R-G080-3**：枚举层至少产出 **「保炸方案」** 与 **「结构优先方案」** 两套，由 `bomb_score + power_score` 与 `recovery` 加权比较（见 `04_card_grouping_skills.md` 组牌顺序原则）。

## 涉及模块

| 文件 | 改动方向 |
|------|----------|
| `src/v/nn/features/grouping_engine.py` | 拆炸阈值、三连对检测前炸弹保留、多方案枚举、评分权重 |
| `docs/knowledge/skills/.../04_card_grouping_skills.md` | 炸弹 vs 复合牌型优先级（若规则定音） |
| `scripts/checks/check_grouping_engine.py` | 回归：`--pre-dedup` + 本副 hand；**唯一组牌验收入口** |

## 关单条件

| 项 | 要求 |
|----|------|
| **复现 case** | 贡后 27 张 + `curRank=J`：`best_plan.bombs` **含** 四 T 炸 **或** 五星 8 炸（定音后二选一或均保留）；**不得** 仅 Q 炸而 T/8 炸全拆 |
| **pytest** | `check_grouping_engine.py --pre-dedup` + `tests/test_grouping_engine.py` 回归；**不**单独建 `test_gua080_*.py`（统一组牌引擎测） |
| **批跑观测** | 3 局 V7 vs lalala：组牌 `card_mask` 中 bomb 组数分布不降；副胜率 **环比不下降**（见 `v7-win-rate-history.md`） |
| **不作关单** | 本副单局 replay 逐步一致；队胜率 ≥30% |

## 关联 GUA

- **GUA-062 / GUA-072**：组牌 v2 + 小炸可拆阈值（本缺陷直接来源）
- **GUA-079 ②**：决策侧「拆炸凑压」— 若组牌已拆炸，决策更难挽回；本 GUA 修 **组牌层**，与 079 互补
- **GUA-054**：`grouping_scanner` 9 维 — 引擎导入失败时的 MT 降级，可能影响 NN 组牌信号（见本文 §grouping_scanner）
- **GUA-077**：多步规划—保炸方案为 sprint 提供资源

**复现命令**：

```bash
python scripts/checks/check_grouping_engine.py \
  --hand "D2,C3,D3,S5,D5,S6,H6,D6,C7,D7,S8,H8,C8,C8,D8,S9,C9,HT,HT,CT,CT,SQ,HQ,CQ,DQ,DK,SA" \
  --rank J --pre-dedup

python scripts/analysis/compare_sf_detection_vs_multipass.py
```

## SF 检测 vs「组同花顺进 multi_pass」（核查结论 · 2026-06-22）

| 对比项 | Step1 `_detect_straight_flushes` | multi_pass 内 `_detect_straights` |
|--------|--------------------------------|-----------------------------------|
| 同花约束 | ✅ 同花色 5 张 | ❌ 混花顺子，非同花顺 |
| 逢人配补 SF | ✅ | ❌ |
| A→2 包接 SF | ✅ | ❌（顺子有，SF 无） |
| 多候选枚举 | ✅ `return_idx` | ❌ |
| 时序 | SF **先于** 三带二/三连对/顺子 | 在三带二 **之后** 才跑顺子 |

**定音**：**不能**用 multi_pass「组顺子」替代 Step1 SF 检测；押后拆炸后 SF 检测仍正常（双同花顺测试：9 方案、SF_FIRST score=0.6085）。SF 池改为非炸牌后，与文档「不拆炸组 SF / SF→炸弹→连牌」更一致。

## grouping_scanner 降级路径（可能影响 yf 出牌质量 · 2026-06-22）

`grouping_scanner`（GUA-054，**9 维统计**）与 `grouping_engine`（**24 维 + 多方案枚举 + SF + card_mask**）是两套中间表示。生产端 `yf1_v7`/`yf2_v7` 已设 `use_grouping_engine=True`，但下列路径仍会落到 scanner 或更弱信号：

| 路径 | 触发条件 | 对出牌的影响 |
|------|----------|--------------|
| **A. MT 特征降级** | `memory_tracker.py` 模块加载时 `grouping_engine` **ImportError** → `_grouping_engine_import_ok=False`；`get_state_vector(game_state)` 走 **9 维 scanner**（L326–336） | NN/BC 侧组牌信号退化为计数统计，**无** role/SF/方案分差；与 v3 模型训练的 24 维不对齐 |
| **B. 开关关闭** | `UltimateWinRateEngineV7(use_grouping_engine=False)` | `_extract_features` 用 33 维 MT（含 scanner 9 维）；**不跑** `_run_grouping_engine` / `enumerate_groupings` |
| **C. 引擎运行失败** | `_run_grouping_engine` 异常 → `_basic_classify` 炸弹降级（GUA-072） | **非 scanner**；无多方案/SF/role 评分，card_mask 仅简单炸弹识别 |
| **D. 特征零向量** | `extract_grouping_engine_features` 异常或 `_grouping_features` 空 | 24 维填 **0**，等价于 NN 盲飞组牌结构 |

**与 GUA-080 关系**：拆炸时序修正在 **路径正常（A 未触发）** 时生效；若实战静默落到 scanner/零向量，即使组牌逻辑已修，**card_mask/role/NN 仍可能弱于 `check_grouping_engine.py` 单测结果**。

**观测建议**（批跑 / 日志）：

- 搜 `[Warning] grouping_engine 导入失败` / `grouping_score 退化为零向量`
- 搜 `_run_grouping_engine 失败` / `_basic_classify 降级`
- 对比：同手牌 `check_grouping_engine.py` 输出 vs 对战日志 `组牌引擎: role=... bombs=...`

**待定音（R-G080-4）**：生产路径 **禁止静默降级**——`grouping_engine` 导入失败应 **显式告警 + 指标计数**；关单前批跑确认零条 scanner 降级日志。**关联 open**：GUA-054（scanner 9 维基线）、GUA-061（engine 24 维主路径）。
