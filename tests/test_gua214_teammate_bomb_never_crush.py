# -*- coding: utf-8 -*-
"""GUA-214: 队友出炸弹（Bomb / StraightFlush）→ 无论队友剩几张一律 PASS 让道。

背景（本地监听 6a76847d，09:21:26，V8=player0）：
队友(player2) 剩 12 张（不 close）出 Bomb/J，V8 手牌 9 = StraightFlush/6 +
Bomb/A 两手整牌，Q0 self_sprint 用 SF/6 反压队友 J 炸。
GUA-212 只在队友 close（剩≤5）才强制让道，队友剩牌多不 close 时放行
（保留 GUA-113 主攻帮挡）。但队友出的是炸弹——用炸弹/同花顺压队友炸弹
等于拆队友控制权，损己利敌（GUA-205 支线1 同语义）。

修复：decide 入口 GUA-212 之前新增 GUA-214——greaterPos 为 teammate 且
greater 为炸弹类（Bomb / StraightFlush）→ 无论队友剩几张、无论敌人是否
imminent，一律 PASS 让道。队友出非炸型（顺/对/单）时仍回 GUA-212 的
close 条件，不 close 保留 GUA-113 帮挡语义。
"""
import logging

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker

HAND_10 = ["C2", "CT", "D3", "D4", "D5", "DT", "H6", "HT", "HT", "S5"]
BOMB_T = ["Bomb", "T", ["CT", "DT", "HT", "HT"]]
PASS = ["PASS", "PASS", "PASS"]
ACTION_LIST = [BOMB_T, PASS]
STRAIGHT_T = ["Straight", "T", ["DT", "SJ", "DQ", "CK", "CA"]]
BOMB_8 = ["Bomb", "8", ["C8", "S8", "C8", "S8"]]
SF_6 = ["StraightFlush", "6", ["C6", "H7", "C8", "D9", "HT"]]


def _base_gs(hand, action_list, numofplayers, greater_pos, greater_action,
             group_type_map=None):
    tracker = MemoryTracker(my_pos=2, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(hand)
    tracker.set_level_rank("K")
    tracker.hand_counts = {
        0: numofplayers[0],
        1: numofplayers[1],
        2: numofplayers[2],
        3: numofplayers[3],
    }
    gs = {
        "myPos": 2,
        "curPos": greater_pos,
        "greaterPos": greater_pos,
        "greaterAction": greater_action,
        "handCards": list(hand),
        "actionList": action_list,
        "curRank": "K",
        "selfRank": "K",
        "oppoRank": "K",
        "numofplayers": list(numofplayers),
        "_memory_tracker": tracker,
        "_belief": {
            "hand_counts": {p: numofplayers[p] for p in range(4)},
            "opp_bomb_risks": {1: 1.0, 3: 0.5},
        },
        "_role": "超强主攻",
    }
    if group_type_map is not None:
        gs["_group_type_map"] = group_type_map
    return gs


def _decide(gs):
    EndgamePreprocessor().preprocess(gs)
    decider = EndgameDecider()
    return decider.decide(gs, gs["actionList"])


def _teammate_far_enemy():
    # teammate=0 剩 12（不 close），敌人 p1=15 / p3=9 均 >2 → 非 imminent
    return [12, 15, 9, 9]


def _teammate_far_enemy_imminent():
    # teammate=0 剩 12（不 close），敌人 p1=2 imminent
    return [12, 2, 9, 9]


def test_teammate_bomb_far_not_close_returns_pass():
    """队友剩 12（不 close）出 Bomb → 仍 PASS（GUA-214，本地 6a76847d 复现）。"""
    gs = _base_gs(HAND_10, ACTION_LIST, _teammate_far_enemy(), 0, BOMB_8)
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "PASS", f"队友出炸(剩多不 close)应 PASS 让道，实际 {act}"


def test_teammate_straight_flush_far_returns_pass():
    """队友剩 12（不 close）出 StraightFlush → 仍 PASS（GUA-214）。"""
    gs = _base_gs(HAND_10, ACTION_LIST, _teammate_far_enemy(), 0, SF_6)
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "PASS", f"队友出同花顺(剩多)应 PASS 让道，实际 {act}"


def test_teammate_bomb_enemy_imminent_still_pass():
    """GUA-214 无 imminent 例外：队友出炸 + 敌人 2 张 imminent → 仍 PASS。"""
    gs = _base_gs(HAND_10, ACTION_LIST, _teammate_far_enemy_imminent(), 0, BOMB_8)
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "PASS", f"队友出炸即使敌人 imminent 也应 PASS，实际 {act}"


def test_teammate_sf_enemy_imminent_still_pass():
    """GUA-214 无 imminent 例外：队友出同花顺 + 敌人 imminent → 仍 PASS。"""
    gs = _base_gs(HAND_10, ACTION_LIST, _teammate_far_enemy_imminent(), 0, SF_6)
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] == "PASS", f"队友出同花顺即使敌人 imminent 也应 PASS，实际 {act}"


def test_greater_from_enemy_bomb_not_blocked():
    """greater 来自敌人且是炸弹 → GUA-214 不介入，正常决策（回归防线）。"""
    gs = _base_gs(HAND_10, ACTION_LIST, _teammate_far_enemy(), 3, BOMB_8)
    idx, act = _decide(gs)
    assert act is not None
    assert act[0] != "PASS", f"敌人出炸不应因队友规则 PASS，实际 {act}"


def test_teammate_straight_far_not_close_not_forced_pass(caplog):
    """队友剩 12（不 close）出非炸型（Straight）→ GUA-214 不触发（回归防线）。"""
    caplog.set_level(logging.INFO, logger="src.v.nn.endgame.endgame_decide")
    gs = _base_gs(HAND_10, ACTION_LIST, _teammate_far_enemy(), 0, STRAIGHT_T)
    idx, act = _decide(gs)
    assert act is not None
    assert "GUA-214" not in caplog.text, "队友出非炸型不应触发 GUA-214"
