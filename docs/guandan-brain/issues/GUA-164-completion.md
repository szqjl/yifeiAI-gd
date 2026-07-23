# GUA-164 完成定义

> **GUA-164**：A-2-3(百搭)-4-5 wrap 直顺枚举：`_detect_straights` wrap 段长 <5 时 `pos_max=-1` 短路窗户扫描
> **登记**：2026-07-23
> **严重级别**：P0
> **关联**：GUA-108（拆炸换顺降手轮）、GUA-074（多方案 Top 3）、GUA-165（百搭保留）、GUA-166（主攻拆对）、GUA-067（百搭配牌文档口径）
> **针对引擎**：v7、v8（`yf1_v8`/`yf2_v8`）

---

## 1. 问题描述

yf1 主攻跟对手 `Single/9`，散张池 `[C2,C4,H5,HA]`（HA = 当前百搭，`curRank=A`）。理论上应可构造 **A-2-3(百搭)-4-5 直顺**：
- A → 当作 1（在 A→2 包接下）
- 2 → C2（自然）
- 3 → HA（百搭配缺）
- 4 → C4（自然）
- 5 → H5（自然）

引擎**本应产出**该 straight 把百搭从散张池里拉走，但实际：

```
[UltimateWinRateEngineV7.0] [INFO] GUA-075 推荐: 跟上家(greater=Single/9) → type=Single rank=A cards=['HA']
```

HA 被当普通 A=14 单张压 9 → 对手出 `Single/HR` 立刻吃掉 HA。**百搭沦为单张燃料**。

### 1.1 根因（`_detect_straights` L933-L1056 wrap 段构造 bug）

`src/v/nn/features/grouping_engine.py`：

```python
# wrap_tail_len（从 A 往前数）只数 RANKS-strict consecutive
for ti in range(len(rank_indices) - 2, -1, -1):
    if RANKS.index(rank_indices[ti]) == RANKS.index(rank_indices[ti + 1]) - 1:
        wrap_tail_len += 1
    else:
        break

# wrap_head_len（从 2 往后数）同上
for hi in range(1, len(rank_indices)):
    if RANKS.index(rank_indices[hi]) == RANKS.index(rank_indices[hi - 1]) + 1:
        wrap_head_len += 1
    else:
        break

# 段组装：tail + head（无 wild 槽）
seg_ranks = rank_indices[tail_start:] + rank_indices[:wrap_head_len]
```

yf1 起手 27 张过完 `_basic_classify` 后（bombs 锁死 9 / J）：

| 项 | 值 |
|---|---|
| rank_indices | `['2','4','5','7','8','T','Q','K','A']` |
| wrap_tail_len | 3（`[Q, K, A]`） |
| wrap_head_len | 1（仅 `[2]`；4 与 2 在 RANKS 中隔 3，**不算 consecutive**） |
| `seg_ranks` | `['Q','K','A','2']`（长度 4） |
| `pos_max` | `4 - 5 = -1` |
| 窗户扫描执行次数 | **0** |
| `_detect_straights` 返回 | `[]` |

结果 9 方案（BOMB_FIRST / ROUND_OPTIMAL / ALL_COMBOS / THREE_PAIR_FIRST / STRAIGHT_BEFORE_TWT × 多拆炸路径）全部 `Straights=[]` `StraightFlushes=[]`。

### 1.2 引擎「知道」A-2 wrap，但实现不完整

`best_is_wrap = True` 路径存在（`_detect_straights` L933 起），但段构造**只用自然严格连续**：
- 跨 `3` 这种"中间位 rank 缺失"用 wild 填空不在 wrap 检测里
- 候选窗 `[A 2 3 4 5]`（A 头）从未被尝试，wild 自然没机会被插入

---

## 2. 修复方案

### 2.1 函数改造：`_detect_straights` wrap 段允许 1-gap + 1 wild

把 L942-L961 的 wrap_tail/head 探测改为「**接受最多 1 个 RANKS-gap，用 1 张百搭填充**」：

```python
# 新 wrap 段构造（伪代码）
def _build_wrap_segment(rank_indices, card_by_rank, available_wilds):
    """返回 seg_ranks + wild_slot 标记，使窗户扫描能尝试 [A, 2, wild@3, 4, 5]。"""
    if rank_indices[-1] != "A" or rank_indices[0] != "2":
        return None, 0

    # tail（从 A 往回数，可有 wild 补 1 个 gap）
    tail_ranks, tail_wilds = ["A"], 0
    for ti in range(len(rank_indices) - 2, -1, -1):
        gap = RANKS.index(rank_indices[ti + 1]) - RANKS.index(rank_indices[ti]) - 1
        if gap == 0:
            tail_ranks.append(rank_indices[ti])
        elif gap == 1 and tail_wilds < available_wilds:
            tail_ranks.append(f"__WILD_{rank_indices[ti+1]}_SLOT__")  # 标记位
            tail_wilds += 1
            tail_ranks.append(rank_indices[ti])
        else:
            break

    # head（从 2 往后数，同理允许 1 gap + 1 wild）
    head_ranks, head_wilds = ["2"], 0
    for hi in range(1, len(rank_indices)):
        gap = RANKS.index(rank_indices[hi]) - RANKS.index(rank_indices[hi - 1]) - 1
        if gap == 0:
            head_ranks.append(rank_indices[hi])
        elif gap == 1 and (tail_wilds + head_wilds) < available_wilds:
            head_ranks.append(f"__WILD_{rank_indices[hi-1]}_SLOT__")
            head_wilds += 1
            head_ranks.append(rank_indices[hi])
        else:
            break

    wild_used = tail_wilds + head_wilds
    if len(tail_ranks) + len(head_ranks) - 1 < 5:
        return None, wild_used  # 还是拼不到 5 张窗
    return (tail_ranks + head_ranks[1:], wild_used)
```

### 2.2 窗户扫描兼容 wildcard slot

`_detect_straights` L1000 的窗户内 for-rank 循环，遇到 `__WILD_X__` 标记位：

```python
for slot in window_ranks:
    if slot.startswith("__WILD_") and slot.endswith("_SLOT__"):
        if wilds_consumed + tent_wilds_used < available_wilds:
            straight_cards.append(wilds[wilds_consumed + tent_wilds_used])
            tent_wilds_used += 1
        else:
            success = False
            break
    elif slot in card_by_rank:
        # 已有逻辑：找可用牌 / 触发 wild 替补
        ...
```

### 2.3 评估 `seg_ranks` 段长阈值

旧：`best_len + available_wilds < 5` 直接 return。新：增加 wild 槽概念后，段总长 = wrap_len + wild_used。**总 ≥ 5** 才进入窗户扫描。

### 2.4 `_detect_straight_flushes` 同步修改

`_enumerate_plans` L1827 起所有 SF 路径同样依赖 wrap 段，须同步。否则 SF 也会漏 A-2-3-4-5 同色（不可能但应保留钩子）。

### 2.5 `enumerate_groupings` 评分

- 直顺多了 1 组 → `_score_decompose` 提升 → ROUND_OPTIMAL 应在 top3 内含该直顺
- BOMB_FIRST 路径应发现 "拆 9 炸弹 → 9 不入顺但增加牌力" 的副效应，但本局 9 在炸弹里也未进直顺

---

## 3. 验收

### 3.1 pytest（`tests/test_gua164_wrap_with_wild_gap.py`）

| # | 用例 | 期望 | 真实锚点 |
|---|------|------|----------|
| ① | `_detect_straights` 输入 yf1 27 张起手（9/J 在炸） + wilds=[HA] | 返回 ≥1 个 straight，含 `[SA,C2,HA,C4,H5]` | ✅ |
| ② | 5 张构造态 `[SA,C2,HA,C4,H5]` + curRank=A + `[TwoTrips/Trips/Pair]` | 唯一方案含 straight `[['SA','C2','HA','C4','H5']]` | ✅ |
| ③ | 反例：手牌无 2 → wrap 不启动，`best_is_wrap=False`，平直顺不变 | `_detect_straights` 行为与修复前一致（非 wrap 路径） | ✅ |
| ④ | 真实锚点：`rec = enumerate_groupings(yf1_27, A)` → top-3 中至少一方案含上述 straight | 锚点决策 `dec[4]` 推荐应改 `Straight/A` 而非 `Single/A [HA]` | ✅ |

### 3.2 端到端

- 重跑锚点牌谱 `20260721160656059092 [yf1_v8]-[opponent_1_3]-[12]-[2].json` 决策 `dec[4]`：`layer=GUA-075推荐`，推荐从 `Single A [HA]` → `Straight/5 [SA,C2,HA,C4,H5]`
- 锚点 replay 后胜率（净盘 V8 批跑 3+ 局）改善 ≥ +0.5 pp

### 3.3 回归

- `test_grouping_engine.py` ≥ 65 passed
- `test_gua108_grouping_straight_from_low_value_bomb.py` ≥ 8 passed（GUA-108 不退化）
- `test_gua109_*` 全过（straight_before_twt / three_pair_first 策略不受影响）

---

## 4. 进度

- [ ] L942-L961 wrap 构造改为"1-gap + 1-wild"
- [ ] L1000 窗户 for-rank 兼容 `__WILD_X__SLOT__`
- [ ] `_detect_straight_flushes` 同步
- [ ] `tests/test_gua164_wrap_with_wild_gap.py` 4 例全过
- [ ] 锚点 `20260721160656059092` replay 推荐变 `Straight/5`
- [ ] 净盘 V8 批跑 3+ 局不损伤其他 KPI

---

## 5. pytest 模板骨架（落盘时填实）

```python
"""
GUA-164: A-2-3(百搭)-4-5 wrap 直顺枚举。
回归：原 yf1 27 张起手 + 锚点 replay 推荐 → Straight 而非 Single。
"""
from src.v.nn.features.grouping_engine import (
    _detect_straights, _detect_straight_flushes,
    _basic_classify, _rank_groups, enumerate_groupings, _parse_rank,
)

def test_gua164_yf1_initial_straight():
    """Case ① yf1 起手 27 张含 A-2-3(百搭)-4-5 直顺。"""
    hand = ["C2","C4","H5","H7","S7","S8","C8","H9","C9","D9","H9","C9",
            "ST","DT","HJ","SJ","DJ","SJ","HQ","CQ","CK","DK","HA","SA","CA","SB","SB"]
    cur_rank = "A"
    groups = _rank_groups(hand, cur_rank)
    singles, pairs, trips, bombs = _basic_classify(groups)
    wilds = ["HA"]
    non_wild_singles = [c for c in singles if c != "HA"]
    non_wild_pairs   = [[c for c in p if c != "HA"] for p in pairs]
    straights, *_ = _detect_straights(non_wild_singles, non_wild_pairs, trips,
                                       cur_rank, list(wilds))
    target = {"SA", "C2", "HA", "C4", "H5"}
    found = any(target == set(s) for s in straights)
    assert found, f"expected A-2-3(百搭)-4-5 in {straights}"

def test_gua164_minimal_5card_straight():
    """Case ② 5 张构造态：SA/C2/HA/C4/H5 + curRank=A 唯一方案含该直顺。"""
    best, plans = enumerate_groupings(
        ["SA","C2","HA","C4","H5"], "A"
    )
    target = {"SA","C2","HA","C4","H5"}
    found = any(target == {frozenset([c for c in s]) for s in p.straights}
                for p in plans)
    # 更直接判断
    found = any(any(target == set(s) for s in p.straights) for p in plans)
    assert found, f"expected A-2(百搭 3)-4-5 in {[p.straights for p in plans]}"

def test_gua164_no_two_no_wrap():
    """Case ③ 反例：无 2 时 wrap 不启动。"""
    hand_no2 = ["H7","S7","S8","C8","H5","HA","SA","CA","HQ","CQ","CK","DK","SB"]
    best, plans = enumerate_groupings(hand_no2, "A")
    # 不应有任何 wrap [A 2 ? 4 5] 形式的 straight
    for p in plans:
        for s in p.straights:
            assert "2" not in s, f"unexpected 2 in straight {s} when no 2 in hand"

def test_gua164_anchor_replay():
    """Case ④ 锚点 replay：dec[4] 应推荐 Straight 而非 Single A [HA]。"""
    # 仅 smoke：用 _has_any_natural_single + role=主攻 + 百搭唯一可压
    # 推荐应调用 GUA-165 的 wild-guard → return None → 上游回退到 PASS
    # 或调用 GUA-166 pair-borrow → 拆对出 T
    # 此用例在 GUA-165 配套测试里完整覆盖
    pass
```