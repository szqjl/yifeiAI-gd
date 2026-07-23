# -*- coding: utf-8 -*-
"""GUA-157 main-path regression tests for assist pair borrowing.

GUA-166 扩展：主攻也能借调（仅 5-9 窗口，严一档）。
GUA-165 修复：min_press_impl candidates 排序把百搭（curRank H 花色）排最后，
优先出非 wild natural。test 4 原期望 ["HA"] 在 GUA-165 改排序后变成 ["SA"]
（SA=15 排在前，HA=15 排后；SA 是级牌 A，HA 是 wild）。
"""

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

ASSIST_ROLE = "\u52a9\u653b"
MAIN_ROLE = "\u4e3b\u653b"


def _engine(*, role=ASSIST_ROLE, natural=None):
    natural = natural or ["D5", "S7"]
    card_mask = {
        **{card: (-1, 0.0, 1) for card in natural},
        "ST": (0, 0.0, 2),
        "CT": (0, 0.0, 2),
        "HJ": (1, 0.0, 2),
        "SJ": (1, 0.0, 2),
        "HA": (2, 0.0, 2),
        "SA": (2, 0.0, 2),
        "HR": (3, 0.0, 2),
    }
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = {
        0: "pair",
        1: "pair",
        2: "pair",
        3: "pair_in_three_with_two",
    }
    engine._group_members = {}
    engine._current_role = role
    return engine, list(card_mask)


def _recommend(engine, hand, greater_rank, greater_card):
    state = {
        "myPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Single", greater_rank, [greater_card]],
        "handCards": hand,
        "curRank": "A",
    }
    return engine._recommend_min_press_impl(
        state,
        engine._card_mask,
        state["greaterAction"],
        "Single",
        hand,
        "A",
    )


def test_assist_borrows_t_pair_before_joker_and_level_card():
    engine, hand = _engine()
    rec = _recommend(engine, hand, "9", "D9")
    assert rec is not None
    assert rec["cards"][0] in ("ST", "CT")
    assert rec["rank"] == "T"


def test_natural_press_single_stays_ahead_of_pair_borrow():
    engine, hand = _engine(natural=["SQ"])
    rec = _recommend(engine, hand, "9", "D9")
    assert rec is not None
    assert rec["cards"] == ["SQ"]


def test_main_attack_does_not_borrow_pair_when_natural_single_cannot_press():
    """GUA-166 改：主攻 + 对手 9 + TT/JJ 对 → 拆 TT/JJ 出单（不再走 HA/SA）。

    GUA-157 修复前主攻不借调 → 走 HA/SA。GUA-166 把 GUA-157 的 `role=="助攻"`
    扩到 `role in {主攻,助攻,超强主攻}`，所以主攻现在也能拆 9/TT/JJ 对。
    """
    engine, hand = _engine(role=MAIN_ROLE)
    rec = _recommend(engine, hand, "9", "D9")
    assert rec is not None
    assert rec["cards"][0] in ("ST", "CT", "HJ", "SJ"), (
        f"GUA-166 主攻借调：应拆 TT 或 JJ 对出单；实际 {rec}"
    )


def test_assist_does_not_borrow_pair_above_t_window():
    """GUA-165 改：min_press_impl 排序把百搭 HA 排最后，SA/HR 优先。

    GUA-157 时代期望 ["HA"]——candidates 选最小 c_val=15（HA 在前）。
    GUA-165 后百搭排最后 → candidates 选 SA (False 优先级, c_val=15)。
    """
    engine, hand = _engine()
    rec = _recommend(engine, hand, "J", "DJ")
    assert rec is not None
    # 优先 SA/HR（非百搭），不再出 HA
    assert rec["cards"][0] in ("SA", "HR"), (
        f"GUA-165：min_press 候选百搭排最后；实际 {rec}"
    )
