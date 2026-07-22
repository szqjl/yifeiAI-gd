# -*- coding: utf-8 -*-
"""GUA-157 main-path regression tests for assist pair borrowing."""

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
    engine, hand = _engine(role=MAIN_ROLE)
    rec = _recommend(engine, hand, "9", "D9")
    assert rec is not None
    assert rec["cards"] == ["HA"]


def test_assist_does_not_borrow_pair_above_t_window():
    engine, hand = _engine()
    rec = _recommend(engine, hand, "J", "DJ")
    assert rec is not None
    assert rec["cards"] == ["HA"]
