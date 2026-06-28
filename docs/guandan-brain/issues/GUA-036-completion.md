# GUA-036 完成定义（控权压顺 + 接风配合 · M3 guard）

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
