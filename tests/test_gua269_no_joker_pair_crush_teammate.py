# -*- coding: utf-8 -*-
"""GUA-269：未冲刺不得用对小王压队友对子。

match=6a8c3e2c t35：3号（队友）用级牌对 D2D2 压过 2 号对 T；
t36 4号 PASS；t37 1号 9 张（QQQ+33+KK+SB×2）尚未两手冲刺，打 Pair/B 抢权，
随后 4 号 Bomb/6 接管清头游。

定音：没形成冲刺时，对王留给控单/收尾，不要盖队友已经控住的对子。
队友 close 时 GUA-212 已让道；本 GUA 补「队友剩牌多 + 主攻帮挡误用对王」。
"""

from __future__ import annotations

from src.v.nn.endgame.endgame_decide import (
    EndgameDecider,
    _is_joker_pair_action,
)
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker

HAND_9 = ["CQ", "D3", "H3", "HK", "HQ", "SB", "SB", "SK", "SQ"]
PAIR_2 = ["Pair", "2", ["D2", "C2"]]
PAIR_B = ["Pair", "B", ["SB", "SB"]]
PAIR_7 = ["Pair", "7", ["S7", "H7"]]
PASS = ["PASS", "PASS", "PASS"]
ACTION_JOKER_ONLY = [PASS, PAIR_B]
ACTION_WITH_SEVEN = [PASS, PAIR_7, PAIR_B]


def _gs(hand, action_list, numofplayers, greater_pos, greater_action, role="超强主攻"):
    tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(hand)
    tracker.set_level_rank("2")
    tracker.hand_counts = {i: numofplayers[i] for i in range(4)}
    gs = {
        "myPos": 0,
        "curPos": greater_pos,
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
        "_role": role,
    }
    return gs


def _decide(gs):
    EndgamePreprocessor().preprocess(gs)
    return EndgameDecider().decide(gs, gs["actionList"])


def test_is_joker_pair_sb():
    assert _is_joker_pair_action(PAIR_B) is True
    assert _is_joker_pair_action(PAIR_2) is False
    assert _is_joker_pair_action(PASS) is False


def test_match_joker_only_follow_teammate_22_passes():
    """复现局：唯一同型是对王、未冲刺、队友 25 张 → PASS。"""
    gs = _gs(HAND_9, ACTION_JOKER_ONLY, [9, 4, 25, 20], 2, PAIR_2)
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "PASS", f"未冲刺不得对王压队友 22，实际 {act}"


def test_q1_picked_joker_pair_rewritten_to_pass():
    """Q1 若选出 Pair/B 压队友，GUA-269 改写为 PASS。"""
    gs = _gs(HAND_9, ACTION_WITH_SEVEN, [9, 8, 18, 16], 2, PAIR_2)
    EndgamePreprocessor().preprocess(gs)
    decider = EndgameDecider()
    rewritten = decider._gua269_rewrite_joker_pair_vs_teammate(
        gs, gs["actionList"], gs["_endgame_context"], 2, PAIR_B,
    )
    assert rewritten is not None
    assert rewritten[1][0] == "PASS"


def test_cheaper_pair_beater_not_forced_pass():
    """还有 77 能压队友对 5 时，不因手里有对王就强制 PASS（主攻仍可帮挡）。"""
    hand = ["S7", "H7", "SB", "SB", "SK", "HK", "CQ", "HQ", "SQ"]
    greater = ["Pair", "5", ["D5", "C5"]]
    gs = _gs(hand, ACTION_WITH_SEVEN, [9, 8, 18, 16], 2, greater)
    EndgamePreprocessor().preprocess(gs)
    early = EndgameDecider()._gua269_joker_pair_vs_teammate_pass(
        gs, gs["actionList"], gs["_endgame_context"],
        2, greater, 2,
    )
    assert early is None, f"有 77 同型时不应因对王提前 PASS，实际 {early}"


def test_enemy_pair_still_allows_joker_pair():
    """压敌方级牌对仍可用对王。"""
    gs = _gs(HAND_9, ACTION_JOKER_ONLY, [9, 4, 25, 20], 1, PAIR_2)
    EndgamePreprocessor().preprocess(gs)
    early = EndgameDecider()._gua269_joker_pair_vs_teammate_pass(
        gs, gs["actionList"], gs["_endgame_context"],
        1, PAIR_2, 2,
    )
    assert early is None


def test_sprint_does_not_force_pass():
    """自己已冲刺时，对王拿权不强制让道。"""
    gs = _gs(HAND_9, ACTION_JOKER_ONLY, [9, 4, 25, 20], 2, PAIR_2)
    EndgamePreprocessor().preprocess(gs)
    gs["_endgame_context"]["self"]["should_sprint"] = True
    gs["_endgame_context"]["self"]["has_two_clean_hands"] = True
    early = EndgameDecider()._gua269_joker_pair_vs_teammate_pass(
        gs, gs["actionList"], gs["_endgame_context"],
        2, PAIR_2, 2,
    )
    assert early is None
