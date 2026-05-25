# opencode 评审指令：M1_ARCHITECTURE.md

## 任务

评审文件：`C:\yifeGDBOT\docs\guandan-brain\M1_ARCHITECTURE.md`

## 强制阅读文件清单

1. `C:\yifeGDBOT\docs\guandan-brain\M1_ARCHITECTURE.md`（主文档）
2. `C:\yifeGDBOT\src\decision\rule_based_decision_engine_m1.py`
3. `C:\yifeGDBOT\src\decision\stage_router.py`
4. `C:\yifeGDBOT\src\decision\phase_handlers.py`
5. `C:\yifeGDBOT\src\decision\strategy_engine.py`

## 准确性验证（必须引用原文）

1. **5阶段路由**：
   - 文档说5阶段：开局/中局前期/中局后期/残局前期/残局后期
   - 验证：stage_router.py 中的阶段划分是否与文档一致？阈值是否正确？

2. **12个Handler**：
   - 文档说"10个常规 + TributeHandler + BackHandler"
   - 验证：phase_handlers.py 中实际有多少个 Handler？名称是否一致？

3. **架构图**：
   - 文档 L28-40 有架构图
   - 验证：图中的调用关系是否与源码一致？

4. **共用层**：
   - 文档说"共用层与V系列共享"
   - 验证：M1 和 V 系列共用哪些模块？

5. **入口和调试入口**：
   - 文档说入口 `decide()` 在 rule_based_decision_engine_m1.py
   - 文档说调试入口 `engine.get_phase_info(message)` 在 L231
   - 验证：行号是否正确？

6. **关键行号引用**：
   - 文档中所有声称的行号，逐一验证

## 指出任何错误或遗漏

## 自评：认真程度 🔥（1-5个，1=随便看看，5=逐行核对）
