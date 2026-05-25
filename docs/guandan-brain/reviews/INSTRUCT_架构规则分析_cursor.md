# Cursor 评审指令：架构规则分析.md

## 任务

评审文件：`C:\yifeGDBOT\docs\guandan-brain\架构规则分析.md`

## 强制阅读文件清单

1. `C:\yifeGDBOT\docs\guandan-brain\架构规则分析.md`（主文档）
2. `C:\yifeGDBOT\src\decision\rule_based_decision_engine_m1.py`（M1 入口）
3. `C:\yifeGDBOT\src\decision\stage_router.py`（阶段路由器）
4. `C:\yifeGDBOT\src\decision\phase_handlers.py`（12个Handler）
5. `C:\yifeGDBOT\src\decision\strategy_engine.py`（策略引擎）
6. `C:\yifeGDBOT\docs\competition\lalala\lalala_src\action.py`（lalala 源码）
7. `C:\yifeGDBOT\docs\competition\lalala\lalala_src\utils.py`（lalala 工具）

## 准确性验证（必须引用原文）

1. **调用链层数**：
   - lalala "3层"的说法是否准确？从哪里可以验证？
   - M1 从 `decide()` 到出牌实际经过几层？

2. **分数积累 vs 精确 if-then**：
   - lalala 源码里有没有用到"分数积累"？还是全部是 if-then？
   - M1 的 `should_protect()` 用的是什么机制？原文在哪里？

3. **lalala 三件套**：
   - `choose_bomb()`、`one_hand()`、`passive()` 入口残局拦截——这三个在文档里的描述是否准确？

4. **"lalala 更优"结论**：
   - 结论是否过于笼统？"更优"需要指明在什么维度更优。

5. **P0 任务清单**：
   - P0 任务是否都有双 CLI review 的出处？

## 指出任何错误或遗漏

## 自评：认真程度 🔥（敷衍/一般/认真/非常认真）
