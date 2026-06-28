# V5+ priority（GUA-034 / GUA-036 后续 · 不在 M3 本轮）

> 登记 **2026-06-01**；与 [`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) P1+→V5+ 对齐。

| 优先级 | 主题 | 来源 | 说明 |
|--------|------|------|------|
| **V5+-01** | lalala **两手走完枚举 + 首出选优** | GUA-034 讨论 ②、[`M3_DIAGNOSIS.md`](M3_DIAGNOSIS.md) BUG2、方向 E/C | `numofmy<=12` 枚举 actionList 两手组合；选「第一手难被压、第二手清牌」（如 `99933`→`10101044`）。lalala 参考实现有 **sort 比较 bug + 候选未消费**（见 `reference/lalala/action.py:1117–1127`），移植须重写而非直抄 |
| **V5+-02** | solo 接风 **可回收单张** 优先级 | GUA-034 讨论 ③ | 混型手牌：级牌/王/大单可先出试探；与 END-M02+-02（对手剩 1 禁小单）联合定优先级表 |
| **V5+-03** | 方向 E 轻量模板 | [`GUA-034-方案评审.md`](GUA-034-方案评审.md) | `solo_sprint && numofmy<=8`：2–3 种固定两手模板（三带二+剩余等），介于 M3 guard 与 BUG2 全量之间 |
| **V5+-04** | **整手结构组牌**（钢板+顺子+炸弹+单张协同） | **GUA-036** 复盘、[`PRINCIPLES_MAPPING.md`](PRINCIPLES_MAPPING.md) §复盘与验收理念 | 局面几乎不重复 → 需 `enumerate_groupings` / 搜索；**不**在 M3 扩 `combine_handcards` |
