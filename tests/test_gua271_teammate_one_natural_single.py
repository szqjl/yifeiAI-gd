# -*- coding: utf-8 -*-
"""GUA-271：队友剩 1 张领出 → 天然单送队友（级牌留回收）。

match=6a8d0d7f：级牌 S2 压上家 Q 后接风，原出 D2/KK/TWT 烂尾；
应最小天然单送队友（下家 2 张防守），级牌 2 留回收。
"""

from __future__ import annotations

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker

PASS = ["PASS", "PASS", "PASS"]


def _gs(hand, action_list, numofplayers, my_pos=0):
    tracker = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(hand)
    tracker.set_level_rank("2")
    tracker.hand_counts = {i: numofplayers[i] for i in range(4)}
    gs = {
        "myPos": my_pos,
        "curPos": -1,
        "greaterPos": -1,
        "greaterAction": PASS,
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
        "_remaining_pool_cards": ["C3", "H4", "S6", "D9", "HT", "CJ", "HQ", "SA"],
    }
    return gs


def _decide(gs):
    EndgamePreprocessor().preprocess(gs)
    return EndgameDecider().decide(gs, gs["actionList"])


def test_lead_feeds_min_natural_not_level_card():
    """接风领出：有天然单 C5/H7 时不出级牌 D2。"""
    hand = ["D2", "S2", "C5", "H7", "DK", "CK", "DT", "HT", "ST", "D7", "H7"]
    # fix duplicate H7 - use unique hand
    hand = ["D2", "S2", "C5", "H7", "DK", "CK", "DT", "HT", "ST", "D7", "C8"]
    action_list = [
        PASS,
        ["Single", "2", ["D2"]],
        ["Single", "2", ["S2"]],
        ["Single", "5", ["C5"]],
        ["Single", "7", ["H7"]],
        ["Single", "8", ["C8"]],
        ["Pair", "K", ["DK", "CK"]],
    ]
    # myPos=0: teammate=2 rem1, down=1 rem2, upper=3 rem5
    gs = _gs(hand, action_list, [11, 2, 1, 5], my_pos=0)
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "Single"
    assert act[2] == ["C5"], f"应出最小天然单 C5，实际 {act}"


def test_gua244_skipped_when_teammate_one():
    """队友剩 1 时 GUA-244 不抢出对子。"""
    hand = ["D2", "C5", "H7", "DK", "CK", "DT", "HT", "ST", "D7", "C8", "H9"]
    action_list = [
        PASS,
        ["Single", "5", ["C5"]],
        ["Single", "7", ["H7"]],
        ["Pair", "K", ["DK", "CK"]],
        ["ThreeWithTwo", "T", ["DT", "HT", "ST", "D7", "C8"]],
    ]
    gs = _gs(hand, action_list, [11, 2, 1, 3], my_pos=0)
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "Single"
    assert act[2] in (["C5"], ["H7"], ["C8"], ["H9"])


def test_down_one_only_singles_second_smallest():
    """下家也报单且仅剩散单 → 出倒数第二小天然单。"""
    hand = ["C5", "H7", "C8", "H9"]
    action_list = [
        PASS,
        ["Single", "5", ["C5"]],
        ["Single", "7", ["H7"]],
        ["Single", "8", ["C8"]],
        ["Single", "9", ["H9"]],
    ]
    gs = _gs(hand, action_list, [4, 1, 1, 8], my_pos=0)
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "Single"
    assert act[2] == ["H7"], f"下家报单仅剩散单应出倒数第二小 H7，实际 {act}"


def test_down_one_has_pair_skips_single_feed():
    """下家报单但有对子 → 不送单，优先其他牌型。"""
    hand = ["C5", "H7", "DK", "CK"]
    action_list = [
        PASS,
        ["Single", "5", ["C5"]],
        ["Single", "7", ["H7"]],
        ["Pair", "K", ["DK", "CK"]],
    ]
    gs = _gs(hand, action_list, [4, 1, 1, 8], my_pos=0)
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "Pair", f"有对子时应优先出对子，实际 {act}"
    assert act[2] == ["DK", "CK"]
