# GUA-045 完成定义（V7 决策根因 · P0 Guard 壳 + 改进路线）

> 登记 **2026-06-06**：V7 净盘 3 局 replay 复盘（`game_id=20260606121245769675`）。**定音**：108 张分 4 家，**同发牌复现概率 ≈ 0**（见 ISSUES 头部「复盘发现 → 实现 → 验收」）；**不得**为该局手牌写特例策略；replay 步数仅用于**缺陷分类**与 pytest **构造态**命名，**不作**关单 pass 标准。

## 统一根因（三层）

| 层 | 现状（`ultimate_win_rate_engine_v7.py`） | 后果 |
|----|------------------------------------------|------|
| **A · P0 Guard 壳** | **零条**；`decide()` 直接模型 argmax 或「首个非 PASS」回退 | 炸队友、过度拆炸、应压 PASS、最小代价缺失 |
| **B · 特征 / 模型** | `_extract_features` 无牌面编码（**GUA-037a** open）；训练目标为 index 匹配率非掼蛋原则 | 同局内决策不稳定（如 SB 有时出、有时 PASS） |
| **C · V5+ 组牌** | 无 `enumerate_groupings` / 结构评分（**V5+-04**） | 顺子漏带单张、钢板被拆、外对子未优先 |

**升格约束**（`V7-实施方案.md` §1.2）：Guard 须 **V7-native** 实现；**禁止** `import src.m.m3.*`；可**只读** M3 `game_records` 作 **GUA-038** BC teacher。

## 缺陷分类 → 原则 → 落点（不迎合单局）

| 缺陷类 | 原则 ID（M3/V5 对齐） | Phase 0 **GUA-045** Guard | Phase 1+ GUA |
|--------|----------------------|---------------------------|--------------|
| 队友领出仍出炸（replay step 14 类） | **P-F02**、GUA-029 **R5** | **V7-R05**：`greaterPos==(myPos+2)%4` 且队友非 PASS → 剔除 `Bomb`/`StraightFlush` | — |
| 压单级牌用炸 / 拆 5→4 炸（step 6 类） | **P-H04**、**P-G01** | **V7-R01**：压 `Single` 且 `curRank` 在场 → 优先 `Single B`/`Single` 最小点；禁为压单选 `Bomb` 若存在更小单牌选项 | **GUA-037a**（牌面特征） |
| 同型炸弹多配牌（step 8：4A+红2 五炸） | **P-H04**、**P-G02** | **V7-R02**：同牌型能压时选 **`len(cards)` 最小** 合法炸；禁逢人配凑炸若纯炸可压 | **GUA-038** BC |
| 被动应压却 PASS（step 40：有 555 不过 333） | **CALC-M03**、控权 | **V7-R03**：被动且 `greaterPos` 为对手；`actionList` 有同型非 PASS → **禁默认 PASS**（取最小够用） | **GUA-037b**（历史编码） |
| 有王/级牌压单却 PASS（step 58 类） | **P-H06** | **V7-R04**：对手 `Single` 且己方可 `Single B` → 优先非 PASS | **GUA-038** |
| 拆钢板/连对出小对（step 62 类） | **P-G01**、P-F02 | **V7-R06**（轻量）：存在**不拆结构**的更大 `Pair` 可压时，剔除拆 `ThreePair`/钢板的 `Pair` | **V5+-04** |
| 顺子未带掉单张（step 12 类） | **P-G01**、CG-T06 | Guard **不覆盖**（需组牌枚举） | **V5+-04** + **GUA-037a** |

## 改进路线（与现有 GUA 对齐）

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

## 关单条件（GUA-045）

| 项 | 要求 |
|----|------|
| **代码** | `decide()` 接入 **V7-native** `filter_action_list()`（或等价）；实现 **V7-R01、R02、R03、R04、R05** 为 **必达**；**R06** 为 **应达**（可 Phase 0 末条迭代） |
| **测试** | `tests/test_v7_gua045.py` pass；**GUA-037a** 未关单前 guard 须可独立运行（模型可为 mock） |
| **回归** | 不破坏 `IDecisionProvider` 契约；`tests/test_v7_paths.py` / `test_v7_notify_routing.py`（若有）不回归 |
| **不作关单** | 再跑 `20260606121245769675` 逐步一致；V7 队胜率 >50%（归 **V7-007** / **GUA-039b**） |

**后续 Agent**：实施 GUA-045 前读本节 + [`V7-实施方案.md`](V7-实施方案.md) §1.2 黑名单；M3 队胜率 KPI **仍只看 M3 批跑**；V7 KPI 见 `ITERATIONS` **V7-007**。
