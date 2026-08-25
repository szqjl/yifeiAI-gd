# -*- coding: utf-8 -*-
"""GUA-161: double-second cleanup and stronger declaration dominance."""

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


HAND = ["H4", "S5", "H6", "H9", "C9", "CJ", "CJ", "CQ", "CK"]
ACTIONS = [
    ["Single", "4", ["H4"]],
    ["Single", "5", ["S5"]],
    ["Single", "6", ["H6"]],
    ["Single", "9", ["C9"]],
    ["Single", "9", ["H9"]],
    ["Single", "J", ["CJ"]],
    ["Single", "Q", ["CQ"]],
    ["Single", "K", ["CK"]],
    ["Pair", "9", ["H9", "C9"]],
    ["Pair", "J", ["CJ", "CJ"]],
    ["Trips", "J", ["H9", "CJ", "CJ"]],
    ["Straight", "9", ["H9", "C9", "CJ", "CQ", "CK"]],
    ["StraightFlush", "9", ["H9", "C9", "CJ", "CQ", "CK"]],
]


def _step82_state():
    return {
        "actionList": ACTIONS,
        "stage": "play",
        "handCards": HAND,
        "myPos": 0,
        "curPos": -1,
        "curAction": None,
        "greaterPos": -1,
        "greaterAction": None,
        "publicInfo": [
            {"rest": 9}, {"rest": 14}, {"rest": 0}, {"rest": 9},
        ],
        "numofplayers": [9, 14, 0, 9],
        "done": [2],
        "selfRank": "9",
        "oppoRank": "2",
        "curRank": "9",
    }


def test_wf12_step82_clears_smallest_scatter_after_teammate_finishes():
    state = _step82_state()
    engine = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=True)
    engine._anchor_role = "主攻"
    engine._current_role = "主攻"

    index = engine.decide(state)

    assert state["actionList"][index] == ["Single", "4", ["H4"]]


def test_same_cards_upgrade_straight_to_straight_flush_at_final_exit():
    engine = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=False)
    actions = [
        ["Straight", "9", ["H9", "C9", "CJ", "CQ", "CK"]],
        ["StraightFlush", "9", ["CK", "CQ", "CJ", "C9", "H9"]],
    ]

    assert engine._trace_finalize(0, actions) == 1


def test_different_cards_do_not_trigger_declaration_upgrade():
    engine = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=False)
    actions = [
        ["Straight", "9", ["H9", "C9", "CJ", "CQ", "CK"]],
        ["StraightFlush", "8", ["C8", "C9", "CT", "CJ", "CQ"]],
    ]

    assert engine._trace_finalize(0, actions) == 0
