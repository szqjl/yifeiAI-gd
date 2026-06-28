---
name: guandan-grouping-engine
description: >-
  掼蛋组牌引擎唯一验收入口：check_grouping_engine.py、enumerate_groupings、
  --pre-dedup 三策略、GUA-062/080。Use when 组牌引擎, grouping_engine,
  check_grouping_engine, 组牌方案, BOMB_FIRST, power_score, WF-05.
---

# 组牌引擎测试（WF-05）

## 原则

- **SF 检测属于 `grouping_engine.py` 内部 Step1**，与 `check_grouping_engine.py` 同路径；无单独对战 SF 模块。
- **不要**单独建 `test_gua080_*.py`；改 `grouping_engine.py` 后跑本 Skill 命令 + `pytest tests/test_grouping_engine.py`。

## 命令

```bash
# 默认手牌
python scripts/checks/check_grouping_engine.py

# 自定义 + 去重前三策略（GUA-080 诊断）
python scripts/checks/check_grouping_engine.py --hand "D2,C3,..." --rank J --pre-dedup

# 回归
python -m pytest tests/test_grouping_engine.py -q
```

## 解读

- `power_score` / `role` / `score_tier` 来自 `_score_plan_v2`。
- `--pre-dedup`：BOMB_FIRST vs ROUND_OPTIMAL 结构分化（拆炸时序修复后应不同）。
- `grouping_scanner` 9 维仅为 **import 失败降级**，见 GUA-080-completion §grouping_scanner。

## 真源

`src/v/nn/features/grouping_engine.py` — `_enumerate_plans` / `_detect_straight_flushes`

## 典范 Playbook

- [PB-001 拆炸时序押后](../../docs/guandan-brain/playbooks/PB-001-gua072-bomb-break-timing.md)（WF-11）
