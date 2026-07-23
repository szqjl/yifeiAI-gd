# -*- coding: utf-8 -*-
"""GUA-165：百搭不作单张优先保留 wild-guard。

- 锚点：yf1_v8 在 `20260721160656059092` 步 18 把百搭 HA 当 Single/A=14 打出，
  被对手 HR 吃掉。根因：`_recommend_min_press_impl`/`_recommend_max_press_impl`
  的单张分支把 wild 当作 A=15 参与排序，无任何降权。
- 修复：在 `_recommend_{min,max}_press_impl` 单张分支前注入 wild-guard：
  非残局 + role∈{主攻,助攻,超强主攻} + 百搭在手中 + 对手出 5-T 单 +
  无非百搭 natural 可压单 + len(hand_cards) > 10 → return None 让出。
- 让出后上游走 GUA-166 主攻拆对 / GUA-157 助攻拆对 / PASS 让道 / 改炸。
"""

import pytest

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

MAIN_ROLE = "主攻"
ASSIST_ROLE = "助攻"


# ── 测试夹具 ────────────────────────────────────────────────
def _engine_wild_guard(role=MAIN_ROLE, hand_cards=None, cur_rank="A",
                       endgame=False, has_pair=False):
    """构造 25 张手牌，仅百搭能压对手 Single/9。

    - 无任何 natural > greater_val(=9) 的牌（避免 _has_non_wild_single_press True）
    - 若 has_pair=True 加 ST-DT 对（注意 ST 自身是 natural T>9，会触发 guard 不让出
      这里我们用 99 对来避免 natural>9 干扰）
    - HA 作为百搭可压 9
    """
    small_singles = [
        "D3", "D4", "D5", "D6", "D7", "D8",
        "C3", "C4", "C5", "C6", "C7", "C8",
        "S3", "S4", "S5", "S6", "S7", "S8",
        "H3", "H4", "H5", "H6", "H7", "H8",
    ]
    if has_pair:
        # 用 99 对（9 不能压 9，借调也无效；用于测 wild-guard 触发让出）
        small_singles = ["C9", "D9"] + [c for c in small_singles if c not in ("C9", "D9")]
        # 补足到 24 张 + HA = 25
        small_singles = small_singles[:22] + ["C9", "D9"]
    hand = (hand_cards or []) + small_singles[:24]
    if len(hand) < 25:
        hand = hand + ["D3"] * (25 - len(hand))
    hand = list(dict.fromkeys(hand))[:25]  # 去重截断
    if "HA" not in hand:
        hand.append("HA")
    hand = hand[:25]

    # card_mask: 所有牌 group_id=-1（散张），HA 标记 wild
    card_mask = {c: (-1, 0.0, 1) for c in hand}
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = {}
    engine._group_members = {-1: [c for c in hand if c != "HA"] + ["HA"]}
    engine._current_role = role
    return engine, hand


def _state(engine, hand, greater_rank="9", greater_card="D9",
           endgame=False):
    state = {
        "myPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Single", greater_rank, [greater_card]],
        "handCards": hand,
        "curRank": "A",
    }
    if endgame:
        state["_endgame_in_progress"] = True
    return state


def _min_press(engine, hand, **kw):
    state = _state(engine, hand, **kw)
    return engine._recommend_min_press_impl(
        state,
        engine._card_mask,
        state["greaterAction"],
        "Single",
        hand,
        "A",
    )


def _max_press(engine, hand, **kw):
    state = _state(engine, hand, **kw)
    return engine._recommend_max_press_impl(
        state,
        engine._card_mask,
        state["greaterAction"],
        "Single",
        hand,
        "A",
    )


# ── 例 1：min_press wild-guard 主攻让出 ──────────────────────
def test_gua165_min_press_main_attack_yields_when_only_wild_can_press():
    """主攻 + 25 张 + 仅百搭可压 + 无对子 → min_press return None 让上游 PASS/改炸。"""
    engine, hand = _engine_wild_guard(role=MAIN_ROLE, has_pair=False)
    rec = _min_press(engine, hand)
    assert rec is None, (
        f"主攻 25 张仅 wild 可压应让出（GUA-165），却返回 {rec}"
    )


# ── 例 2：max_press wild-guard 主攻让出 ──────────────────────
def test_gua165_max_press_main_attack_yields_when_only_wild_can_press():
    """主攻 + 25 张 + 仅百搭可压 → max_press（卡下家）也 return None 让出。"""
    engine, hand = _engine_wild_guard(role=MAIN_ROLE, has_pair=False)
    rec = _max_press(engine, hand)
    assert rec is None, (
        f"卡下家场景主攻 25 张仅 wild 可压应让出（GUA-165），却返回 {rec}"
    )


# ── 例 3：残局（last≤10）放行百搭单张 ──────────────────────
def test_gua165_endgame_lets_wild_single_through():
    """残局 last≤10 → wild-guard 不触发，wild 可作单张。"""
    # 9 张手牌（含 HA）模拟残局
    small9 = ["D3", "D4", "D5", "D6", "D7", "D8", "C3", "C4", "HA"]
    hand = small9
    card_mask = {c: (-1, 0.0, 1) for c in hand}
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = {}
    engine._group_members = {-1: hand}
    engine._current_role = MAIN_ROLE
    rec = _min_press(engine, hand)
    # 残局放行：返回 Single/HA
    assert rec is not None, "残局放行 wild-guard 未触发，应返回推荐"
    assert rec["cards"] == ["HA"], f"残局应出 Single/HA，实际 {rec}"


# ── 例 4：natural 可压时 wild-guard 不触发，走 natural 路径 ──
def test_gua165_natural_single_press_unaffected():
    """主攻 + 25 张 + 有 natural SA 可压 → wild-guard 不触发，走 SA 路径。"""
    hand = (
        ["SA", "HA"]  # SA 也能压 9（SA get_card_value=15）
        + [f"D{i}" for i in range(3, 9)]  # D3-D8
        + [f"C{i}" for i in range(3, 9)]  # C3-C8
        + [f"S{i}" for i in range(3, 9)]  # S3-S8
        + ["H3", "H4", "H5"]  # H3-H5
    )
    hand = list(dict.fromkeys(hand))[:25]
    card_mask = {c: (-1, 0.0, 1) for c in hand}
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = {}
    engine._group_members = {-1: hand}
    engine._current_role = MAIN_ROLE
    rec = _min_press(engine, hand)
    assert rec is not None
    # natural 优先：选最小 natural（SA 因 wild-guard 不触发也能出，但 natural_can_press True）
    # 期望至少有一张 natural 出（不是 wild 单走）
    # 这里 SA 是手牌里唯一 >9 的非 wild，wild-guard 不触发 → 出 SA
    assert rec["cards"] == ["SA"], f"应出 Single/SA，实际 {rec}"


# ── 例 5：GUA-157 兼容 —— 助攻路径仍可拆 TT 对 ──────────────
def test_gua165_assist_pair_borrow_still_works():
    """助攻 + 25 张 + 有 TT 对（ST>9）+ 散张不可压 → 走 GUA-157 拆 T 出 ST。

    GUA-157 行为不被 GUA-165 wild-guard 破坏。
    """
    hand = [
        "ST", "DT",          # TT 对（可拆）
        "D3", "D4", "D5", "D6", "D7", "D8",  # small 散张
        "C3", "C4", "C5", "C6", "C7", "C8",  # small 散张
        "S3", "S4", "S5", "S6", "S7", "S8",  # small 散张
        "H3", "H4", "H5",                     # 散张
        "HA",                                # 百搭（不参与）
    ]
    card_mask = {
        **{c: (-1, 0.0, 1) for c in hand if c not in ("ST", "DT")},
        "ST": (0, 0.0, 2),
        "DT": (0, 0.0, 2),
    }
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = {0: "pair"}
    engine._group_members = {-1: [c for c in hand if c not in ("ST", "DT")], 0: ["ST", "DT"]}
    engine._current_role = ASSIST_ROLE
    rec = _min_press(engine, hand)
    # GUA-165 wild-guard: hand_cards 有 ST（natural T=10>9）→ _has_non_wild_single_press=True
    # → guard 不触发；走 GUA-157：role==助攻 + greater_rank 9 + natural_can_press=False
    # （散张都 ≤9）→ 拆 TT 对 → 出 ST
    assert rec is not None, "助攻路径 GUA-157 应拆 TT 对出 ST"
    assert rec["cards"][0] in ("ST", "DT"), f"应出 ST 或 DT，实际 {rec}"
    assert rec["rank"] == "T", f"应出 rank=T，实际 {rec}"
