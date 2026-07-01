---
tags: [M3, integration, GUA-024, GUA-025, GUA-027, GUA-028]
created: 2026-05-29
updated: 2026-05-30
topic: M3 引擎集成与场态修复
related: [[M3-Development]], [[m3-strategy-gua026-029]]
---

# M3 引擎集成与场态修复（GUA-024 / GUA-025 / GUA-027 / GUA-028）

> 来源：[[ITERATIONS]] 2026-05-29 ~ 2026-05-30（9 条迭代）

## GUA-024：M3 play 全 PASS 根因

| 日期 | 迭代 | 关键修复 |
|------|------|----------|
| 2026-05-29 | 根因修复 | `curAction[1]`/`action[1]` 替代误写的 `[-1]`；`_rule_parse` 补 `greaterPos==myPos` 主动与 fallback |
| 2026-05-29 | 细化 Debug + 字符串化根因闭环 | `_dbg` 双通道（console+log）；`_ensure_list` 规范化 |

**结论**：字符串根因闭环；瓶颈转为策略层 `_Single` RETURN0 保守。

## GUA-025：回放手牌误合并修复

- `game_recorder._merge_same_game_records`：按 `[opponent]-[round]-[level]` 匹配
- `tests/test_game_recorder_merge.py` **4 passed**

## GUA-027：场态消息重大发现

| 日期 | 迭代 | 关键内容 |
|------|------|----------|
| 2026-05-30 | 文档化 | `M3_DIAGNOSIS.md` 增补「WebSocket 场态用法」；~40% 单牌 greater 异常 |
| 2026-05-30 | 场态重算实现 | `trick_state.py`（`resolve_effective_greater`、`TrickSequenceTracker`）；38 局 40.4% 步重算 ≠ 录制 |

**涉及文件**：
- `src/game_logic/trick_state.py`
- `m3_decision_engine`（act 校正 + beatAction）
- `tests/test_trick_state_gua027.py` **8 passed**

## GUA-028：v1006 三项对齐

- `platform_act.py`（`clamp_act_index`、`normalize_play_act_fields`）
- `TripsPair`→`_ThreeWithTwo`
- `act` 同步 `publicInfo.rest`
- yf1/yf2_m3 indexRange clamp
- **24 passed**（GUA-027+028+契约）

## M3 首轮批跑验证

- `batch_executor` 修复 M3 成对计数 bug
- 10 局首跑：队胜 0/10，yf1 PASS 38.1% / yf2 58.0%
- ThreeWithTwo 出牌 22 次，队胜率仍 0%
