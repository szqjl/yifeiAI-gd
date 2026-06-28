# GUA-034 完成定义（残局拦头游 · M3 guard 切片）

> 复盘定音 **2026-06-01**：round 38 yf2 末段（`replay_word.md` 成对牌谱）。**与 GUA-026 边界**：GUA-026 禁三带二**常态拆炸弹/级牌 trips**；GUA-034 允许在 **队友已走完（1v2）** 且 **对手将一手走光** 时**定向拆 trips/对子压牌或走 GUA-029 R3**，二者不冲突。

| 项 | ID | 完成标准 |
|----|-----|----------|
| 模式识别 | **END-M01** | `numofplayers[(myPos+2)%4]==0`（或等价：队友 `publicInfo.rest==0`）→ 进入 **solo_sprint** 分支（不再走 GUA-031 队友让道） |
| 接风首出 | **END-M02** | `solo_sprint` + 接风 `_active`（`greaterPos==-1`）+ `numofmy<=12`：优先 **ThreeWithTwo / Trips / Pair**，**禁止** `rankone/ranktwo` 为清小点而 **拆对出最小 Single** |
| 被动压小牌 | **END-M03** | `solo_sprint` + `_Single` 跟对手小单：允许从 trips **拆单** 压牌（≥对手点），不限于 `single_member` |
| 被动压对子 | **END-M04** | `solo_sprint` + `_Pair` 跟对手对子：允许 **拆 trips 凑更大对** 或走 **GUA-029 R3**（`numofplayers[greaterPos]<=7` 且无可跟） |
| 测试 | — | `tests/test_m3_gua034.py`（≥4 case：END-M02 接风、END-M03 压单 6、END-M04 压对 6 / R3 兜底）；GUA-026/029/031 回归 **不回归** |
| 验收 | — | 样例局 102–106 步决策与上表一致（可 replay 构造）；可选：净盘 M3 ≥3 局记录 `numoffri==0` 末段 PASS 率下降 |

**关单条件**：END-M01–M04 + pytest 通过；**不要求**队胜率达标（队胜率以 M3 批跑观测为准）。

**不在范围**：完整 lalala「两手牌组合枚举」（见 M3_DIAGNOSIS BUG2 全量移植 → **V5+ / 后续迭代**）。
