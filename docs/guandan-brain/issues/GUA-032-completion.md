# GUA-032 完成定义（记牌 + 算牌 · M3）

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
