# -*- coding: utf-8 -*-
"""GUA-141：Q1 `_sort_by_recapture_first` 回收优先后按牌力大优先（非张数多）。"""

from __future__ import annotations

from src.v.nn.endgame.endgame_decide import (
    EndgameDecider,
    _sort_by_recapture_first,
    get_action_type,
)
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker


def test_sort_by_recapture_first_prefers_higher_rank_over_more_cards():
    """同有回收时：单张王应排在 4 炸前（牌力大 > 张数多）。"""
    hand = [
        "S4", "S4", "H4", "D4",
        "SB", "HR",
        "S8", "D8", "S9", "ST", "SJ", "SQ", "SK",
    ]
    actions = [
        (0, ["PASS", "PASS", "PASS"]),
        (1, ["Single", "B", ["SB"]]),
        (2, ["Bomb", "4", ["S4", "S4", "H4", "D4"]]),
    ]
    ordered = _sort_by_recapture_first(actions, hand, cur_rank="J")
    assert get_action_type(ordered[0][1]) == "Single"
    assert ordered[0][1][2] == ["SB"]


def test_q1_press_single_a_prefers_joker_over_four_bomb():
    """
    WF-12 锚点 20260710141616032842 步45→46：
    @1 Single/A、@1 剩 6；手中有 SB/HR 时不得先出 Bomb/4。
    """
    hand = [
        "S4", "S4", "H4", "D4",
        "H5", "C5",
        "S8", "D8",
        "S9", "S9", "D9",
        "ST", "HT", "CT",
        "SQ", "SK", "SJ",
        "SB", "HR",
    ]
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "J", ["SJ"]],
        ["Single", "B", ["SB"]],
        ["Single", "R", ["HR"]],
        ["Bomb", "4", ["S4", "S4", "H4", "D4"]],
        ["StraightFlush", "8", ["S8", "S9", "ST", "SJ", "SQ"]],
        ["StraightFlush", "9", ["S9", "ST", "SJ", "SQ", "SK"]],
    ]
    tracker = MemoryTracker(my_pos=2, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(hand)
    tracker.set_level_rank("J")
    tracker.hand_counts = {0: 10, 1: 6, 2: 19, 3: 9}

    gs = {
        "myPos": 2,
        "curPos": 1,
        "greaterPos": 1,
        "greaterAction": ["Single", "A", ["DA"]],
        "handCards": list(hand),
        "actionList": action_list,
        "curRank": "J",
        "selfRank": "A",
        "oppoRank": "J",
        "numofplayers": [10, 6, 19, 9],
        "_memory_tracker": tracker,
        "_belief": {
            "hand_counts": {0: 10, 1: 6, 2: 19, 3: 9},
            "opp_bomb_risks": {1: 0.0, 3: 0.0},
        },
    }
    EndgamePreprocessor().preprocess(gs)
    decider = EndgameDecider()
    filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
    idx, act = decider.decide(gs, gs["actionList"] if banned_empty else filtered)

    assert idx is not None
    assert act[0] == "Single", f"expected same-type Single press, got {act}"
    assert act[2][0] in ("SB", "HR", "SJ"), f"expected SB/HR/级牌J, got {act}"
    assert act[0] != "Bomb"
