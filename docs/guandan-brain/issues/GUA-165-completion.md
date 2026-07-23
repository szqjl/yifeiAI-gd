# GUA-165 完成定义

> **GUA-165**：百搭不作单张优先保留：`_recommend_min_press_impl` 须把百搭从 single press 候选池降权
> **登记**：2026-07-23
> **严重级别**：P0
> **关联**：GUA-164（wrap 段 bug 同根）、GUA-157（助攻拆对）、GUA-166（主攻拆对扩 scope）、`docs/knowledge/skills/07_opening/04_card_grouping_skills.md` §逢人配分布

---

## 1. 问题描述

yf1 主攻跟对手 `Single/9`，百搭 `HA` 是当前 curRank=A 时的红心级牌（`f"H{cur_rank}"`）。**统计基线**（来自 `04_card_grouping_skills.md`）：

| 百搭用途 | 实战占比 |
|---------|---------|
| 配成炸弹 | **85%** |
| 补缺（如三张缺脚、单顺子缺张） | **12%** |
| 单张打出 | **≤ 3%** |

但当前 `_recommend_min_press_impl` 的排序：

```python
natural_singles = list(self._scatter_singles(card_mask))   # g=-1 全量，含百搭
natural_can_press = any(get_card_value(c, cur_rank) > greater_val for c in natural_singles)
allow_assist_pair_borrow = (
    self._current_role == "助攻"
    and greater_rank in {"5", "6", "7", "8", "9", "T"}
    and not natural_can_press
)
singles = self._collect_single_follow_candidates(
    card_mask, groups, hand_cards, cur_rank,
    allow_assist_pair_borrow=allow_assist_pair_borrow,
)
candidates.sort(key=lambda x: x[0])
_, best, _ = candidates[0]
```

**百搭被当成普通 A=14 单张**（`get_card_value` 不区分百搭与同级牌）→ 排序后被压对手 → 实战里 85% 应配入炸弹的机会浪费。

本局锚点 log：

```
[16:06:56] [UltimateWinRateEngineV7.0] [INFO] GUA-075 推荐: 跟上家(greater=Single/9) → type=Single rank=A cards=['HA']
[16:06:56] [UltimateWinRateEngineV7.0] [INFO] GUA-075 主路径: recommend=Single/A → actIndex=12 ✅
[16:06:56] [yf1_v8] [INFO] 发送动作: PLAY act=['Single', 'A', ['HA']]
```

接下来 pos=1 出 `HR` 把 HA 吃掉，百搭沦为燃料。

---

## 2. 修复方案

### 2.1 `_recommend_min_press_impl` Single 分支前加 wild-guard

在 `src/v/nn/ultimate_win_rate_engine_v7.py` L4282 起加一道：

```python
wild_card = f"H{cur_rank}"
hand_cards = game_state.get("handCards") or list(self._card_mask.keys())

def _is_in_endgame(hand_size: int, game_state: dict) -> bool:
    """残局阶段：hand_size <= 10 或 命中 endgame_decider Q1/Q2 才放行百搭出单。"""
    if hand_size <= 10:
        return True
    # 命中 Q1 的标志（endgame q1 命中）从 game_state['_endgame_q1_hit'] 读取
    return bool(game_state.get("_endgame_q1_hit"))

def _has_non_wild_press(hand_cards, wild_card, greater_val, cur_rank):
    """是否有非百搭 natural 单张能压对手 single。"""
    from src.v.nn.guards.v7_guards import get_card_value
    for c in hand_cards:
        if c == wild_card:
            continue
        if get_card_value(c, cur_rank) > greater_val:
            # 排除 R12 王/级牌特例（已在 R12 内处理）
            return True
    return False

# —— wild-guard 主入口 ——
if greater_type == "Single":
    hand_size = len(hand_cards)
    if (
        not _is_in_endgame(hand_size, game_state)
        and wild_card in hand_cards
        and not _has_non_wild_press(hand_cards, wild_card, greater_val, cur_rank)
        and self._current_role in ("主攻", "助攻")
    ):
        # 百搭是唯一可压非百搭 → 让出 GUA-166/GUA-157 拆对路径评估
        return None
```

`_recommend_min_press_impl` 返回 `None` 后，主路径自然回退到：
1. GUA-157 规则⑩（助攻拆对）
2. GUA-166 修复（主攻拆对扩 scope）
3. 启发式 fallback
4. PASS（让对家）

### 2.2 `_recommend_max_press_impl` 同步

卡下家场景也有同样问题：百搭当作压单同样浪费。同步加 guard（条件相同）。

### 2.3 残局放行

- `hand_size ≤ 10` → 百搭当作单张可出（残局收尾）
- Q1/Q2 命中 → 百搭放行（endgame_decider 接管）

### 2.4 与 GUA-164 协作

GUA-164 修好后，HA 在 5 张直顺里被合理消耗。GUA-165 与 GUA-164 是**互补**关系：
- GUA-164 让组牌阶段把百搭送进组合
- GUA-165 让决策阶段**不**把百搭当作单张燃料

GUA-164 先修，本 GUA-165 才能正确判断"百搭是否应当留"。

---

## 3. 验收

### 3.1 pytest（`tests/test_gua165_wild_single_press_guard.py`）

| # | 用例 | 期望 |
|---|------|------|
| ① | handcards=25、role=主攻、wild=HA 是唯一可压、对手 9 | 返回 None → 上游拆对 PASS |
| ② | handcards=18、role=主攻、有 99/TT/JJ 对、wild 唯一可压、对手 7 | 走 GUA-166 拆对 → `Single/T` |
| ③ | role=助攻（同 ②）、对手 7 | 走 GUA-157 规则⑩ → 拆 T |
| ④ | handcards=8、对手 9、百搭唯一可压 | 放行 → `Single/HA` |
| ⑤ | handcards=25、wild=HA、对手 9、natural 单张 SA 可压 | 正常路径选 SA，百搭不出 |

### 3.2 端到端

- yf1 锚点决策 `dec[4]` 主路径不再返回 `Single A [HA]`；日志显示：
  - `wild-guard 触发: 百搭唯一可压且非残局 → 让出推荐`
  - 后续 GUA-166 拆对 ST-DT → `Single/T [ST]`

### 3.3 回归

- `test_gua157_assist_pair_borrow_main_path.py` ≥ 4 passed
- `test_gua122_wild_level_single_press.py` ≥ N passed（保留百搭档压规则的范围）
- `test_grouping_engine.py` ≥ 65 passed

---

## 4. 进度

- [ ] `_recommend_min_press_impl` / `_recommend_max_press_impl` 加 wild-guard
- [ ] `_is_in_endgame` helper 实现
- [ ] 与 GUA-166 拆对路径协调
- [ ] `tests/test_gua165_wild_single_press_guard.py` 5 例全过
- [ ] 锚点 replay 推荐变 `Single/T [ST]` 或 PASS
- [ ] KPI：净盘 V8 批跑 3+ 局百搭出单率从 ~15% 降至 ≤ 5%

---

## 5. KPI 锚点（修前后对照预期）

| 指标 | 修前 | 修后预期 |
|------|------|---------|
| yf1 锚点 `dec[4]` 推荐 | `Single A [HA]` | `Single T [ST]` 或 PASS |
| 百搭出单率（盘内） | 估计 ~12% | ≤ 5% |
| 百搭配炸率（盘内） | 估计 ~70% | 接近 85% 基线 |
| 主攻跟单回合扣分 | 正常 | 多数 PASS 让队友 |
| 队胜率 | 基线 | +1~3 pp（首尾段） |