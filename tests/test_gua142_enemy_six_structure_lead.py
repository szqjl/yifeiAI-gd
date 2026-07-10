# -*- coding: utf-8 -*-
"""GUA-142：敌剩 6 取消强制 Trips；自由领出整组 ThreePair 保 SF/炸冲刺路径。"""

from __future__ import annotations

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor, endgame_rule
from src.v.nn.features.memory_tracker import MemoryTracker


def test_endgame_rule_6_recommends_three_pair_and_does_not_ban_pair():
    danger, recommended, banned = endgame_rule[6]
    assert danger == "中"
    assert "ThreePair" in recommended
    assert "TwoTrips" in recommended
    assert "Pair" not in banned
    assert "Single" not in banned


def test_structure_sprint_path_after_three_pair_leaves_sf():
    """出 8899TT 后剩 SF(9-K)+对5+双王 → 结构冲刺路径成立。"""
    hand = [
        "H5", "C5", "S8", "D8", "S9", "S9", "D9",
        "ST", "HT", "CT", "SQ", "SK", "SJ", "SB", "HR",
    ]
    three_pair = ["ThreePair", "T", ["S8", "D8", "S9", "D9", "HT", "CT"]]
    rem = EndgameDecider._remainder_after_action(hand, three_pair)
    assert rem is not None
    assert EndgameDecider._has_structure_sprint_path(rem)
    # 拆三张 9 后无完整黑桃 SF
    trips = ["Trips", "9", ["S9", "S9", "D9"]]
    rem_trips = EndgameDecider._remainder_after_action(hand, trips)
    assert rem_trips is not None
    assert not EndgameDecider._has_structure_sprint_path(rem_trips)


def test_wf12_anchor_step50_prefers_three_pair_over_trips():
    """
    WF-12 20260710141616032842 步50：@1 rem=6 自由领出，
    应 ThreePair 8899TT，不得 Trips/9。
    """
    hand = [
        "H5", "C5", "S8", "D8", "S9", "S9", "D9",
        "ST", "HT", "CT", "SQ", "SK", "SJ", "SB", "HR",
    ]
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Pair", "5", ["H5", "C5"]],
        ["Pair", "8", ["S8", "D8"]],
        ["Trips", "9", ["S9", "S9", "D9"]],
        ["ThreePair", "T", ["S8", "D8", "S9", "D9", "HT", "CT"]],
        ["StraightFlush", "9", ["S9", "ST", "SJ", "SQ", "SK"]],
        ["Single", "B", ["SB"]],
        ["Single", "R", ["HR"]],
    ]
    tracker = MemoryTracker(my_pos=2, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(hand)
    tracker.set_level_rank("J")
    tracker.hand_counts = {0: 10, 1: 6, 2: 15, 3: 9}

    gs = {
        "myPos": 2,
        "curPos": -1,
        "greaterPos": -1,
        "greaterAction": None,
        "handCards": list(hand),
        "actionList": action_list,
        "curRank": "J",
        "selfRank": "A",
        "oppoRank": "J",
        "numofplayers": [10, 6, 15, 9],
        "_memory_tracker": tracker,
        "_belief": {
            "hand_counts": {0: 10, 1: 6, 2: 15, 3: 9},
            "opp_bomb_risks": {1: 0.0, 3: 0.0},
        },
    }
    EndgamePreprocessor().preprocess(gs)
    enemies = gs["_endgame_context"]["enemies"]
    assert 1 in enemies
    assert "Pair" not in enemies[1].get("banned_types", [])
    assert "ThreePair" in enemies[1].get("recommended_types", [])

    idx, act = EndgameDecider().decide(gs, action_list)
    assert idx is not None
    assert act[0] == "ThreePair", f"expected ThreePair, got {act}"
    assert act[0] != "Trips"
