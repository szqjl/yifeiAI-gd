# -*- coding: utf-8 -*-
"""GUA-270：上家敌进残局 + 队友剩牌>5 → 跟压 PASS 交由队友。

match=6a8d09c3 约第 30 回合：队友 3 号出对 → 上家 4 号 JJ 压过 →
1 号 9 张残局 Q1 直接 88888 开炸；队友仍持多牌，应由队友线继续而非抢炸。
"""

from __future__ import annotations

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker

HAND_9 = ["CQ", "D3", "H3", "HK", "HQ", "SB", "SB", "SK", "SQ"]
BOMB_8 = ["Bomb", "8", ["S8", "D8", "S8", "C8", "D8"]]
PAIR_J = ["Pair", "J", ["DJ", "SJ"]]
PAIR_2 = ["Pair", "2", ["D2", "C2"]]
PASS = ["PASS", "PASS", "PASS"]


def _gs(
    hand,
    action_list,
    numofplayers,
    greater_pos,
    greater_action,
    my_pos=0,
):
    tracker = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(hand)
    tracker.set_level_rank("2")
    tracker.hand_counts = {i: numofplayers[i] for i in range(4)}
    gs = {
        "myPos": my_pos,
        "curPos": my_pos,
        "greaterPos": greater_pos,
        "greaterAction": greater_action,
        "handCards": list(hand),
        "actionList": action_list,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "numofplayers": list(numofplayers),
        "_memory_tracker": tracker,
        "_belief": {
            "hand_counts": {i: numofplayers[i] for i in range(4)},
            "opp_bomb_risks": {1: 0.0, 3: 0.0},
        },
        "_role": "主攻",
    }
    return gs


def _decide(gs):
    EndgamePreprocessor().preprocess(gs)
    return EndgameDecider().decide(gs, gs["actionList"])


def test_upper_single_five_does_not_pass_when_singles_available():
    """上家 Single/5 + 有散单可压 → 不得 GUA-270 PASS（match 6a8d1ca9）。"""
    hand = [
        "C5", "C5", "C7", "C8", "C9", "D7", "D8", "D8", "D9", "DK", "DQ",
        "DT", "H3", "H5", "H6", "H9", "HA", "HJ", "HQ", "HR", "S2", "S3",
        "S4", "S4", "S8", "S8", "SJ",
    ]
    gs = _gs(
        hand,
        [PASS, ["Single", "6", ["S6"]], ["Single", "7", ["H7"]], BOMB_8],
        [26, 10, 17, 12],
        1,
        ["Single", "5", ["H5"]],
        my_pos=2,
    )
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] != "PASS", f"有散单可压 Single/5 不应 PASS，实际 {act}"


def test_match_upper_jj_only_bomb_passes_to_teammate():
    """1 号视角：上家 4 号 JJ 压队友对子，队友 15 张、仅炸可压 → PASS。"""
    # myPos=0: teammate=2, upper=3, lower=1
    gs = _gs(
        HAND_9,
        [PASS, BOMB_8],
        [9, 20, 15, 5],
        3,
        PAIR_J,
        my_pos=0,
    )
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "PASS", f"应 PASS 交由队友，实际 {act}"


def test_mypos2_upper_player1_jj_passes():
    """V8=player2 日志复现：上家 player1 JJ，队友 player0 剩 18 张 → PASS。"""
    hand = [
        "C5", "C5", "C7", "C8", "C9", "D7", "D8", "D8", "D9", "DK", "DQ",
        "DT", "H3", "H5", "H6", "H9", "HA", "HJ", "HQ", "HR", "S2", "S3",
        "S4", "S4", "S8", "S8", "SJ",
    ]
    gs = _gs(
        hand,
        [PASS, BOMB_8],
        [18, 5, len(hand), 12],
        1,
        PAIR_J,
        my_pos=2,
    )
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "PASS"


def test_teammate_close_five_may_still_bomb():
    """队友剩 5 张（close）时不触发让道，仍可开炸抢权。"""
    gs = _gs(
        HAND_9,
        [PASS, BOMB_8],
        [9, 20, 5, 5],
        3,
        PAIR_J,
        my_pos=0,
    )
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "Bomb"


def test_lower_enemy_control_not_yielded():
    """下家敌控牌时不走 GUA-270（位置区分）。"""
    gs = _gs(
        HAND_9,
        [PASS, BOMB_8],
        [9, 5, 18, 20],
        1,
        PAIR_J,
        my_pos=0,
    )
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "Bomb"


def test_enemy_imminent_no_yield():
    """任一敌 ≤2 张 imminent 时不让道。"""
    gs = _gs(
        HAND_9,
        [PASS, BOMB_8],
        [9, 2, 18, 5],
        3,
        PAIR_J,
        my_pos=0,
    )
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "Bomb"


def test_upper_not_in_endgame_no_yield():
    """上家未进残局区（>10 张）不触发。"""
    gs = _gs(
        HAND_9,
        [PASS, BOMB_8],
        [9, 20, 18, 12],
        3,
        PAIR_J,
        my_pos=0,
    )
    EndgamePreprocessor().preprocess(gs)
    decider = EndgameDecider()
    yielded = decider._q1_yield_upper_endgame_to_teammate(
        gs, gs["actionList"], gs["_endgame_context"],
    )
    assert yielded is None
