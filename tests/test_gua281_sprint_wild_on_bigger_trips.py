# -*- coding: utf-8 -*-
"""GUA-281：冲刺剩两趟三张 + 1 配子 → 配子升更大点成炸。

锚点 match=6a8d9a400fbd680d7c8340a4（logs/v8_vs_botzone_20260825_211731.log
21:36:37）：手牌 666+QQQ+H2 跟 Single/S2，actionList 有 Bomb/6 与 Bomb/Q，
引擎出 Bomb/6，被对方 Bomb/9 反压，QQQ 卡死。定音：配子搭 QQQ 出 Bomb/Q。
"""

from __future__ import annotations

from src.v.nn.endgame.endgame_decide import (
    EndgameDecider,
    _declared_bomb_rank_value,
    _is_two_trips_plus_wild_hand,
    _sort_q1_block_candidates,
)
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.grouping_engine import _upgrade_bombs_with_wilds
from src.v.nn.features.memory_tracker import MemoryTracker

CUR = "2"
HAND = ["H6", "C6", "D6", "HQ", "SQ", "CQ", "H2"]
PASS = ["PASS", "PASS", "PASS"]
BOMB_6 = ["Bomb", "6", ["H6", "C6", "D6", "H2"]]
BOMB_Q = ["Bomb", "Q", ["HQ", "SQ", "CQ", "H2"]]
SINGLE_S2 = ["Single", "2", ["S2"]]


def _gs(hand, action_list, numofplayers, my_pos=2, greater_pos=3):
    tracker = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(hand)
    tracker.set_level_rank(CUR)
    tracker.hand_counts = {i: numofplayers[i] for i in range(4)}
    gs = {
        "myPos": my_pos,
        "curPos": my_pos,
        "greaterPos": greater_pos,
        "greaterAction": SINGLE_S2,
        "handCards": list(hand),
        "actionList": action_list,
        "curRank": CUR,
        "selfRank": CUR,
        "oppoRank": CUR,
        "numofplayers": list(numofplayers),
        "publicInfo": [{"rest": n} for n in numofplayers],
        "done": [0],
        "_memory_tracker": tracker,
        "_belief": {
            "hand_counts": {i: numofplayers[i] for i in range(4)},
            "opp_bomb_risks": {1: 0.0, 3: 0.0},
        },
        "_role": "主攻",
        "_group_members": {
            0: ["H6", "C6", "D6"],
            1: ["HQ", "SQ", "CQ"],
            -1: ["H2"],
        },
        "_group_gid_type_map": {
            0: "trips",
            1: "trips",
            -1: "scatter",
        },
        "_group_type_map": {"trips": 2, "scatter": 1},
    }
    EndgamePreprocessor().preprocess(gs)
    return gs


def test_upgrade_wild_attaches_to_bigger_trips():
    """无钢板：唯一配子升 QQQ，剩 666。"""
    trips = [
        ["H6", "C6", "D6"],
        ["HQ", "SQ", "CQ"],
    ]
    bombs, remaining, wilds = _upgrade_bombs_with_wilds(trips, ["H2"], CUR)
    assert len(bombs) == 1
    assert set(bombs[0]) == {"HQ", "SQ", "CQ", "H2"}
    assert remaining == [["H6", "C6", "D6"]]
    assert wilds == []


def test_upgrade_wild_non_steel_still_beats_steel_pair():
    """GUA-181 Part A：有非钢板 trips 时配子仍给非钢板；GUA-281 在非钢板里取大点。"""
    trips = [
        ["H5", "C5", "D5"],
        ["H6", "C6", "D6"],
        ["H9", "C9", "D9"],
        ["HQ", "SQ", "CQ"],
    ]
    bombs, remaining, _wilds = _upgrade_bombs_with_wilds(trips, ["H2"], CUR)
    assert len(bombs) == 1
    assert set(bombs[0]) == {"HQ", "SQ", "CQ", "H2"}
    remaining_ranks = {t[0][1] for t in remaining}
    assert remaining_ranks == {"5", "6", "9"}


def test_upgrade_steel_only_picks_bigger_trip():
    """GUA-181 Part B：仅钢板对时仍升炸；GUA-281 升更大点。"""
    trips = [
        ["H5", "C5", "D5"],
        ["H6", "C6", "D6"],
    ]
    bombs, remaining, _wilds = _upgrade_bombs_with_wilds(trips, ["H2"], CUR)
    assert len(bombs) == 1
    assert set(bombs[0]) == {"H6", "C6", "D6", "H2"}
    assert remaining == [["H5", "C5", "D5"]]


def test_two_trips_plus_wild_detector():
    assert _is_two_trips_plus_wild_hand(HAND, CUR) is True
    assert _is_two_trips_plus_wild_hand(HAND + ["CA"], CUR) is False
    assert _declared_bomb_rank_value(BOMB_Q, CUR) > _declared_bomb_rank_value(BOMB_6, CUR)


def test_q1_sort_prefers_bigger_wild_bomb():
    """Q1 最小足够炸在本结构下改为配子搭大点。"""
    ordered = _sort_q1_block_candidates(
        [(1, BOMB_6), (2, BOMB_Q)],
        HAND,
        {"curRank": CUR, "greaterAction": SINGLE_S2},
    )
    assert ordered[0][1][1] == "Q"


def test_select_best_bomb_ignores_wild_inflation():
    """物理牌含级牌配子时，按声明点数比，不把 H2 当最大张。"""
    bombs = [(1, BOMB_6), (2, BOMB_Q)]
    _idx, act = EndgameDecider()._select_best_bomb(bombs, [PASS, BOMB_6, BOMB_Q])
    assert act[1] == "Q"


def test_follow_single_plays_bomb_q_not_bomb_6():
    """跟 Single/S2：出 Bomb/Q（配子+QQQ），不出 Bomb/6。"""
    al = [PASS, BOMB_6, BOMB_Q]
    gs = _gs(HAND, al, [8, 6, 7, 5], my_pos=2, greater_pos=3)
    _idx, act = EndgameDecider().decide(gs, al)
    assert act is not None
    assert act[0] == "Bomb"
    assert act[1] == "Q"
    assert set(act[2]) == {"HQ", "SQ", "CQ", "H2"}
