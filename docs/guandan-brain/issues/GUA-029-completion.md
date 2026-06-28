# GUA-029 完成定义（炸弹可执行规则包 R1–R6）

> 从 `01_bomb_techniques.md` 提炼、与 M3 现有观测字段对齐；**互不打架**，可写进 if-then，避免与 GUA-026 拆牌保护混淆。

| 规则 | 条件（M3 可观测） | 动作 | 文档依据 | 涉及模块 |
|------|-------------------|------|----------|----------|
| **R1** | `actionList` 含 `Bomb`/`StraightFlush` 且进入 `choose_bomb` | **先修** `choose_bomb`：点数读 `action[1]`（对齐 lalala 参考实现），同花顺分支一并查；单元测 v1006 格式 `['Bomb','8',[…]]` | 前置；不修则 R2–R6 均可能异常→PASS | `m3_utils.choose_bomb` |
| **R2** | `beatAction[0] in (Bomb, StraightFlush)` 且 `choose_bomb != -1` | **必回炸**（最小够用炸弹） | §二.3 追炸；§二.6 炸对手炸弹 | `_Bomb`；取消/绕过 `cur_Bomb_num>=3` 硬门槛 |
| **R3** | `numofplayers[greaterPos] <= 7` 且当前牌型分支无可跟牌 且 `choose_bomb != -1` | **必炸**（防冲刺/听牌） | §三.5.3 剩 5–7 张；§五.2 逢 5 必防 | 各 `_Single`/`_Pair`/`_ThreeWithTwo`/… 统一兜底 |
| **R4** | `numofplayers[greaterPos] == 4` | **默认不炸**；白名单：① 我剩 ≤2 手且炸后一手走完；② 仅炸弹能压且炸后可接风领出 | §五.1 炸不打四 | `_Bomb` 与各被动分支 guard |
| **R5** | `(myPos+2)%4 == greaterPos` | **禁止出炸**（全局 guard，各分支统一） | §二.3 不压队友（默认） | `_Bomb`、`_ThreeWithTwo` 等 |
| **R6** | `numofmy <= 10` 且 `actionList` 存在炸弹/SF **一手清牌** | **优先 bomb/SF 冲刺**（扩 `one_hand` + `_active` 首段） | §二.5 残局冲刺；§五.3 尾炸+一手 | `_passive`/`_active`/`one_hand` |

**验收**：① `pytest` 新增 `test_m3_gua029.py`（R1 格式 + R2 回炸 + R3 ≤7 阻断，用样例局 step46/74 构造）；② 异常兜底不再无脑 `send_action(0)` 掩盖炸弹分支（或 bomb 分支内不抛异常）；③ 净盘 M3 批跑 ≥10 对：炸弹出牌次数 >0、队胜率或 PASS 率有方向性改善（记录在 `ITERATIONS.md`）。

**与 GUA-026 边界**：GUA-026 禁止三带二**拆炸弹/耗级牌**；GUA-029 要求在**应炸场景主动出整炸**，二者不冲突。
