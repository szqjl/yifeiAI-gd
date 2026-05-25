# Cursor 评审指令：M1_ARCHITECTURE.md

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
   - 验证：stage_router.py 中阶段划分和阈值是否与文档一致

2. **12个Handler**：
   - 文档说"10个常规 + TributeHandler + BackHandler"
   - 验证：phase_handlers.py 实际有多少个 Handler？名称列表是否正确？

3. **架构图验证**：
   - 文档 L28-40 有架构图，逐层验证调用链

4. **共用层**：
   - 文档说"共用层与V系列共享"
   - 验证：共用模块是否真实存在？

5. **入口和调试入口行号**：
   - `decide()` 在哪里？
   - `get_phase_info()` 在哪里？

6. **PhaseHandler 各阶段功能描述**：
   - 文档 L90-200 对各 Handler 的描述是否与实际代码一致？

## 指出任何错误或遗漏

## 自评：认真程度 🔥（1-5个，1=随便看看，5=逐行核对）
