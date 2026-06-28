# GUA-031 完成定义（传牌 guard + 队友让道 · M3）

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
