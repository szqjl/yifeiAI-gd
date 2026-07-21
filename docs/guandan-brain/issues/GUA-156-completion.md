# GUA-156 完成定义

> **GUA-156**：三带二初始组牌带牌排序：pairs 未按 rank 排序导致大对子被消耗  
> **登记**：2026-07-21  
> **严重级别**：P0  
> **关联**：GUA-114（出牌时 min 策略带牌优先级）、GUA-070（R12 核心保护）

---

## 问题描述

`_detect_three_with_two`（`grouping_engine.py:805-818`）注释写"小 trip 吃小对"，但 `remaining_pairs` 未按 rank 排序，实际行为是"小 trip 吃列表里第一个可用对子"。

**复现**：手牌含 333/888/AAA + 55/66/TT/QQ

| 期望 | 实际 |
|------|------|
| 333+55、888+66、AAA+TT | 333+TT、888+QQ、AAA+55 |
| 小对被三带二带走，大对保留 | 大对被消耗，小对保留 |

**根因**：`_basic_classify` 按手牌出现顺序输出 pairs，`_detect_three_with_two` 未排序直接取第一个。

---

## 修复方案

**改动**：`src/v/nn/features/grouping_engine.py` `_detect_three_with_two` 函数

```python
# line 806 后加一行
sorted_trips = sorted(remaining_trips, key=lambda t: _card_rank_value(t[0], cur_rank))
remaining_pairs.sort(key=lambda p: _card_rank_value(p[0], cur_rank))  # ← 新增
```

**影响范围**：仅初始组牌阶段的三带二配对，不影响出牌时的动态构建（GUA-114 已修）。

---

## 关单条件

| # | 条件 | 验证形式 |
|---|------|----------|
| ① | 333/888/AAA + 55/66/TT/QQ → 333+55/888+66/AAA+TT | pytest 构造态 |
| ② | 无独立对子时仍可从三张取对（回退等价） | pytest 反例 |
| ③ | 不影响 GUA-070/R12 核心保护 | 现有 pytest 回归 |
| ④ | 不影响 GUA-114 出牌时带牌优先级 | 现有 pytest 回归 |
| ⑤ | 批跑 R-G080-4 零退化 | 批跑验证 |

---

## 验收清单

- [ ] pytest `tests/test_grouping_engine.py` 全绿（含新增 GUA-156 case）
- [ ] pytest `tests/test_gua114_three_with_two_kicker_orphan.py` 全绿（回归）
- [ ] pytest `tests/test_gua069.py` 全绿（R12 回归）
- [ ] 批跑 R-G080-4 零退化（card_mask 退化诊断 + 组牌引擎异常 = 0）
