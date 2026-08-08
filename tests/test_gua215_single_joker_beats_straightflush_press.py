# -*- coding: utf-8 -*-
"""GUA-215：Q1 封锁敌方时，手牌有小王/大王压级牌单张，
不得因 `_has_recapture` 跨牌型误判而先出同花顺浪费炸弹。

match=6a76847d 3号(player2) 视角最后一步实测败招：手牌含 SB + C2-C6 同花顺，
greater=Single/2（4号出 S2），Q1 封锁命中后排序把 StraightFlush/C2-C6 排在
Single/SB 前面（`_has_recapture` 用单张牌力比、级牌提升15 < SB=16 → 误判 SF
有回收），最终出 C2-C6 同花顺压级牌，实际应出小王保留同花顺控制。
"""

from __future__ import annotations

from src.v.nn.endgame.endgame_decide import (
    EndgameDecider,
    _has_recapture,
    _sort_by_recapture_first,
    get_action_type,
)
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker


def test_has_recapture_sf_not_by_single_joker():
    """SF 的回收 = 剩余手牌还有更强炸弹；手牌单张 SB 不算 SF 的回收。"""
    hand = ["C2", "C3", "C4", "C5", "C6", "C8", "C8", "H8", "HT", "SB", "ST"]
    sf = ["StraightFlush", "2", ["C2", "C3", "C4", "C5", "C6"]]
    assert _has_recapture(sf, hand, "2") is False


def test_has_recapture_sb_without_higher_single():
    """SB 出后无更大单张（手牌无 HR）→ 无回收。"""
    hand = ["C2", "C3", "C4", "C5", "C6", "C8", "C8", "H8", "HT", "SB", "ST"]
    sb = ["Single", "B", ["SB"]]
    assert _has_recapture(sb, hand, "2") is False


def test_has_recapture_sf_with_stronger_bomb_remains_true():
    """手牌仍能构成 6+ 张炸（强于同花顺）→ SF 有回收，仍应排前。"""
    hand = ["S9", "S9", "S9", "S9", "S9", "S9", "S8",
            "C2", "C3", "C4", "C5", "C6"]
    sf = ["StraightFlush", "2", ["C2", "C3", "C4", "C5", "C6"]]
    assert _has_recapture(sf, hand, "2") is True


def test_has_recapture_sf_with_five_bomb_only_is_false():
    """同花顺 > 5星炸：手牌仅剩 5 张同点炸时 SF 出后无更强炸弹 → 无回收。"""
    hand = ["S6", "S6", "S6", "S6", "S6", "S8",
            "C2", "C3", "C4", "C5", "C6"]
    sf = ["StraightFlush", "2", ["C2", "C3", "C4", "C5", "C6"]]
    assert _has_recapture(sf, hand, "2") is False


def test_sort_sb_before_straightflush_press_single_level():
    """GUA-215 核心：压级牌2单张时 SB 应排在 C2-C6 同花顺前。"""
    hand = ["C2", "C3", "C4", "C5", "C6", "C8", "C8", "H8", "HT", "SB", "ST"]
    sb = ["Single", "B", ["SB"]]
    sf = ["StraightFlush", "2", ["C2", "C3", "C4", "C5", "C6"]]
    ordered = _sort_by_recapture_first([(0, sb), (1, sf)], hand, "2")
    assert get_action_type(ordered[0][1]) == "Single"
    assert ordered[0][1][2] == ["SB"]


def test_q1_press_single_level_uses_single_joker_not_sf():
    """
    完整残局管线复现 match=6a76847d 3号最后一步：
    greater=Single/2（4号 S2），手牌 SB + C2-C6 SF + C8C8 H8 HT ST，
    队友(player1) 已 done → Q1 封锁敌方 → 应选 Single/SB。
    """
    hand = ["C2", "C3", "C4", "C5", "C6", "C8", "C8", "H8", "HT", "SB", "ST"]
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "B", ["SB"]],
        ["StraightFlush", "2", ["C2", "C3", "C4", "C5", "C6"]],
    ]
    tracker = MemoryTracker(my_pos=2, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(hand)
    tracker.set_level_rank("2")
    tracker.hand_counts = {0: 0, 1: 10, 2: 11, 3: 7}

    gs = {
        "myPos": 2,
        "curPos": 3,
        "greaterPos": 3,
        "greaterAction": ["Single", "2", ["S2"]],
        "handCards": list(hand),
        "actionList": action_list,
        "curRank": "2",
        "selfRank": "A",
        "oppoRank": "2",
        "numofplayers": [0, 10, 11, 7],
        "_memory_tracker": tracker,
        "_belief": {
            "hand_counts": {0: 0, 1: 10, 2: 11, 3: 7},
            "opp_bomb_risks": {1: 0.0, 3: 0.0},
        },
    }
    EndgamePreprocessor().preprocess(gs)
    decider = EndgameDecider()
    filtered, banned_empty = decider.apply_banned_filter(gs["actionList"], gs)
    idx, act = decider.decide(gs, gs["actionList"] if banned_empty else filtered)

    assert idx is not None, "残局管线应命中 Q1 封锁"
    assert act[0] == "Single", f"expected Single/SB press, got {act}"
    assert act[2] == ["SB"], f"expected SB, got {act}"
