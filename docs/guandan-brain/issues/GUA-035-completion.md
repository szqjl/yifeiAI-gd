# GUA-035 完成定义（END-M02+ · solo 接风对手剩张过滤）

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
