# opencode 评审指令：架构规则分析.md

## 任务

评审文件：`C:\yifeGDBOT\docs\guandan-brain\架构规则分析.md`

## 强制阅读文件清单

1. `C:\yifeGDBOT\docs\guandan-brain\架构规则分析.md`（主文档）
2. `C:\yifeGDBOT\src\decision\rule_based_decision_engine_m1.py`（M1 入口，254行）
3. `C:\yifeGDBOT\src\decision\stage_router.py`（阶段路由器，593行）
4. `C:\yifeGDBOT\src\decision\phase_handlers.py`（12个Handler，2773行）
5. `C:\yifeGDBOT\src\decision\strategy_engine.py`（策略引擎，589行）
6. `C:\yifeGDBOT\docs\competition\lalala\lalala_src\action.py`（lalala 源码，1411行）
7. `C:\yifeGDBOT\docs\competition\lalala\lalala_src\utils.py`（lalala 工具，769行）

## 准确性验证（必须引用原文）

1. **调用链层数**：
   - lalala "3层"的说法是否准确？（原文哪里说了3层）
   - M1 "7-10层"的说法是否准确？从 `decide()` 到实际出牌最多经过几层？

2. **分数积累 vs 精确 if-then**：
   - 文档说 lalala 用"精确 if-then"，M1 用"分数积累"——这个描述是否准确？有无引用原文？
   - lalala 的 `choose_bomb()`、`one_hand()` 是否在文档里有正确描述？

3. **"lalala 更优"结论**：
   - 文档结论"lalala 优于 M1"——这个结论是否有充分的事实依据支撑？

4. **关键代码位置**：
   - 文档引用的 lalala 代码行号是否与源码匹配？

5. **P0 任务清单来源**：
   - P0 任务（`choose_bomb`、`combine_handcards`、context补维度）是否来自双 CLI review 结论？列出出处。

## 指出任何错误或遗漏

## 自评：认真程度 🔥（敷衍/一般/认真/非常认真）
