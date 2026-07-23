# GUA-166 完成定义

> **GUA-166**：主攻拆对扩 scope：把 GUA-157 由"仅助攻"扩展到主攻领出/跟单
> **登记**：2026-07-23
> **严重级别**：P0
> **关联**：GUA-157（助攻拆对拦单）、GUA-165（百搭保留）、`src/v/nn/ultimate_win_rate_engine_v7.py` L3137 启发式规则⑩

---

## 1. 问题描述

`src/v/nn/ultimate_win_rate_engine_v7.py` 当前 GUA-157 助攻拆对护栏：

```python
allow_assist_pair_borrow = (
    self._current_role == "助攻"                 # ← 卡死仅助攻
    and greater_rank in {"5", "6", "7", "8", "9", "T"}
    and not natural_can_press
)
singles = self._collect_single_follow_candidates(
    card_mask, groups, hand_cards, cur_rank,
    allow_assist_pair_borrow=allow_assist_pair_borrow,
)
```

`_heuristic_select` L3137 启发式层规则⑩：`if role == "助攻": ...`——仅助攻可拆 99/TT/JJ 对子。

**现实**：yf1 主攻跟对手 `Single/9` 时（决策 `dec[4]`），百搭是唯一可压 + 主攻角色，GUA-157 路径**不触发** + GUA-075 min_press 选 HA 出 → 浪费百搭。

主攻拆对的合规场景：
- 队友没剩对手的单张可压
- 拆出来的单张 < 对手单张 + 1（即真压）
- 拆对后保留三人轮次节奏（不让对手反投牌）

---

## 2. 修复方案

### 2.1 `_recommend_min_press_impl` 助攻条件扩 scope

L4282-L4300 区域：

```python
allow_pair_borrow = (
    not natural_can_press
    and greater_rank in {"5", "6", "7", "8", "9", "T"}   # ≤ T
    and self._current_role in ("主攻", "助攻", "超强主攻")
    and not _has_any_natural_single(hand_cards, cur_rank)  # 双无散单才允许
    and _has_breakable_pair_99_99_TT_JJ(groups, hand_cards, cur_rank)
)
# 主攻阈值严一档：对手 ≥ Q（rank 12）即不借调
if self._current_role != "助攻":
    if greater_rank in {"J", "Q", "K"}:  # J 起步 PASS
        allow_pair_borrow = False
```

### 2.2 拆对排序与小对子优先

`_collect_single_follow_candidates` 已实现 L1971 的 `allow_assist_pair_borrow` 借调窗口。本 GUA 仅扩 role 范围；窗口内仍优先 99/TT/JJ：

```python
if (
    allow_pair_borrow
    and ginfo["is_core"] <= 0
    and rank in assist_borrow_ranks   # {"9", "T", "J"}
):
    singles.append(card)
```

主攻继承这套排序——按牌力升序，单张 T(10) < J(11) < Q(12)，对手 5-T 时拆最小可拆对优先。

### 2.3 与 GUA-165 协调

- GUA-165 wild-guard：百搭不是 sole 候选时直接降权
- GUA-166：百搭剔除后，仅自然可压也没有 → 进 pair-borrow
- 二者串联：`wild-guard → return None → 上游(`_collect_single_follow_candidates`) → pair-borrow 路径`

### 2.4 启发式层规则⑩ 同步扩 scope

`_heuristic_select` L3137 加 role 条件：

```python
if (
    is_single
    and not is_pass
    and not has_natural_single
    and role in ("助攻", "主攻", "超强主攻")   # ← 新增
    and 3 <= greater_val <= 8
):
    break_pair = _find_smallest_breakable_pair(hand_cards, cur_rank)
    if break_pair:
        score += 500
```

> 当前 `_heuristic_select` 只在 GUA-075 主路径 return None 时才被选中；本 GUA 主路径扩了 scope 后，规则⑩ 主要作为防御层。

### 2.5 反向规则：保留 PASS 优先级

为防止主攻无脑拆对引入风险，加反向规则：
- `_is_passing_strategically`（PASS 让队友/对手）：handcards>22 + 对手 <7 → 应优先 PASS
- 避免「主攻硬拆对」破坏 PASS 让对家策略

---

## 3. 验收

### 3.1 pytest（`tests/test_gua166_main_attack_pair_borrow.py`）

| # | 用例 | 期望 |
|---|------|------|
| ① | role=主攻、对手 `Single/9`、handcards=20、百搭非主、无 natural 可压单、有 ST-DT | 推荐 `Single/T [ST]` |
| ② | role=主攻、对手 `Single/Q`（rank 12 ≥ Q）、有 TT | 推荐 PASS |
| ③ | role=主攻、对手 `Single/9`、handcards=25、有 33（97/TT/JJ 范围外） | 推荐 PASS（无 99/TT/JJ） |
| ④ | role=助攻 + ① 同样条件 | 走 GUA-157，行为不变 ✓ |
| ⑤ | role=助攻、对手 `Single/Q`（rank 12） | 走 GUA-157 PASS，与主攻阈值一致 ✓ |

### 3.2 与 GUA-165 协作

`tests/test_gua165_*` 5 例全过基础上，扩展两个用例：
- ⑤-b：role=主攻 + 百搭+TT 对 + 对手 9 → 推荐 `Single/T`（GUA-165 guard + GUA-166 pair-borrow）
- ⑤-c：role=主攻 + 百搭唯一 + 无 TT 对 + 对手 9 → 推荐 PASS（GUA-165 guard + 没法拆对）

### 3.3 端到端

- yf1 锚点 `dec[4]` 决策推荐变 `Single/T [ST]`
- yf2 队友后续若有大牌压 ST，yf1 不浪费百搭；若队友也 PASS，对手要么吃小牌要么 PASS（无损）

### 3.4 回归

- `test_gua157_assist_pair_borrow_main_path.py` ≥ 4 passed（不破坏现有）
- `test_gua116_main_attack_lead.py` ≥ 11 passed（领出逻辑不冲突）
- `test_gua117_assist_layer0_guard.py` ≥ N passed

---

## 4. 进度

- [ ] `_recommend_min_press_impl` `allow_pair_borrow` 扩 role
- [ ] `_recommend_max_press_impl` 同步
- [ ] `_collect_single_follow_candidates` 借调范围扩 role（验证 99/TT/JJ 排序未受影响）
- [ ] `_heuristic_select` 规则⑩ role 扩展
- [ ] `_is_passing_strategically` 反向 PASS 优先级
- [ ] `tests/test_gua166_main_attack_pair_borrow.py` 5 例全过
- [ ] 净盘 V8 批跑 3+ 局 KPI 不退化

---

## 5. KPI 锚点（修前后对照预期）

| 指标 | 修前 | 修后预期 |
|------|------|---------|
| 主攻跟单回合缺拆对 | 全 PASS 或出百搭 | 多走 `Single/T` 等拆对 |
| yf1 锚点 `dec[4]` | `Single A [HA]`（被 HR 吃） | `Single T [ST]`（队友可接或 PASS 让） |
| 百搭存活手数（直到配入组合前） | 多被早出 | 平均推迟 2-3 回合 |
| 队胜率 | 基线 | +1~2 pp |
| 主攻跟单回合 PASS 率 | 偏低 | 主攻阈值严一档后略增 PASS（无损） |