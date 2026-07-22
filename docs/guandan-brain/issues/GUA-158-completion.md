# GUA-158 完成定义

> **GUA-158**：接风两手整牌因运行时异常被 fallback 拆散
> **登记/关单**：2026-07-22
> **严重级别**：P0
> **关联**：GUA-150（中局冲刺潜力）、GUA-085（动作索引映射）、GUA-070（组牌保护）

## 锚点

`20260722202516875509 [yf2_v8]-[opponent_1_3]-[8]-[2].json` 步 73。

- yf1 第 69 步出 `StraightFlush` 获得头游，yf2 接风。
- yf2 剩 10 张，完整两手为 `ThreeWithTwo(444+66)` 与 `Straight(8-Q)`。
- Guard 与组牌前置过滤已把 9 个候选压到上述 2 个整牌动作。
- `_midgame_sprint_potential_check()` 调用未导入的 `get_card_rank` 抛 `NameError`。
- 顶层异常兜底错误地回到原始 `actionList`，`_rule_based_decision()` 取索引 0，拆出 `Single/4 ['C4']`。

## 修复

1. 在 `_midgame_sprint_potential_check()` 内显式导入 `get_card_rank`。
2. `decide()` 的异常兜底优先使用 `group_actions`，其次 `filtered_actions`，最后才用原始 `actionList`。
3. 兜底选中动作后按内容映射回原始 `actionList` 索引，保持平台返回契约。

## 验收

- [x] 目标两手牌状态正常决策，不再抛 `NameError`。
- [x] 强制 heuristic 抛异常时，仍只能从 `ThreeWithTwo` / `Straight` 中选择。
- [x] 不得返回原始 `actionList[0] = Single/C4`。
- [x] 定向测试 `tests/test_gua158_wind_catch_two_hands_fallback.py` 通过。
