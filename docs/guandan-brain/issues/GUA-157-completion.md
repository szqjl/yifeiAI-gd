# GUA-157 完成定义

> **GUA-157**：助攻拆对拦单策略：无散单时拆对子压对手小单  
> **登记**：2026-07-21  
> **严重级别**：P0  
> **关联**：GUA-071（_heuristic_select 4 条元规则）、GUA-117（助攻领出）

---

## 问题描述

助攻角色无散单时，对手出单张，AI 没有"拆对拦单"的策略逻辑。

**复现**：`20260721131151461716` 步 2  
- yf1 助攻，手牌含 KKKK 炸弹 + 2 顺子 + 对王(loose) + 5 对子(33/88/TT/QQ/AA) + 1 散牌(C6)  
- 对手出 Single/7  
- AI 出 HR（大王）— 太浪费  
- 人类会拆 TT → 出 T 拦 7

**人类打法规则**（初期/中期，无散单，非残局）：

| 上家出的单张 | 应对 |
|-------------|------|
| **> 10**（J/Q/K/A） | **PASS** — 不拆对子，让队友或等残局 |
| **< 5**（2/3/4） | **拆 99/TT/JJ 对子** — 用 9-J 之间的单张拦 |
| **5-10**（5/6/7/8/9/T） | **助攻**：也可拆 9-J 对子，用拆单拦 |

---

## 修复方案

### 方案 A：在 `_heuristic_select` 新增规则⑩

```python
# ── GUA-157: 助攻拆对拦单 ──
# 无自然单张 + 对手出单 5-10 + 助攻角色 → 拆最小可拆对出单拦
if (
    is_single
    and not is_pass
    and not has_natural_single
    and role == "助攻"
    and 3 <= greater_val <= 8  # 5-10 in rank value
):
    # 找最小可拆对（99/TT/JJ 优先）
    break_pair = _find_smallest_breakable_pair(hand_cards, cur_rank)
    if break_pair:
        score += 500  # 拆对拦单加分
```

### 方案 B：在 GUA-117 助攻跟压路径新增逻辑

在 `stage_assist_feed.py` 新增 `_assist_break_pair_to_block` 函数：

```python
def _assist_break_pair_to_block(
    engine, game_state, card_mask, hand_cards, cur_rank, greater_action
) -> Optional[Dict[str, Any]]:
    """助攻无散单时，拆对子拦对手小单。"""
    # 1. 检查是否有自然单张
    # 2. 检查对手出的单张 rank
    # 3. 根据规则选择拆哪个对子
    # 4. 返回拆单动作
```

---

## 关单条件

| # | 条件 | 验证形式 |
|---|------|----------|
| ① | 助攻无散单 + 对手 Single/7 → 拆 TT 出 T | pytest 构造态 |
| ② | 助攻无散单 + 对手 Single/3 → 拆 TT 出 T | pytest 构造态 |
| ③ | 助攻无散单 + 对手 Single/Q → PASS | pytest 构造态 |
| ④ | 主攻无散单 → 不适用（不拆对） | pytest 反例 |
| ⑤ | 锚点 `20260721131151461716` 步 2 → 出 T 而非 HR | 回放验证 |

---

## 验收清单

- [ ] pytest `tests/test_grouping_engine.py` 全绿（回归）
- [ ] pytest `tests/test_gua114_three_with_two_kicker_orphan.py` 全绿（回归）
- [ ] pytest 新增 GUA-157 测试项（4 项）
- [ ] 锚点回放验证
