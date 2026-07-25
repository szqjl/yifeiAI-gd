# -*- coding: utf-8 -*-
"""GUA-160: lead a natural small single to open teammate's six-card sprint."""

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


HAND = [
    "H2", "C3", "D3", "H4", "S5", "H6",
    "H9", "C9", "CJ", "DJ", "CJ", "CQ", "CK",
]
ACTIONS = [
    ["Single", "2", ["H2"]],
    ["Single", "3", ["D3"]],
    ["Single", "3", ["C3"]],
    ["Straight", "2", ["H2", "D3", "H4", "S5", "H6"]],
    ["Straight", "2", ["H2", "C3", "H4", "S5", "H6"]],
    ["Pair", "J", ["CJ", "DJ"]],
    ["StraightFlush", "9", ["H9", "C9", "CJ", "CQ", "CK"]],
]


def _state(teammate_remaining):
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
            {"rest": 13}, {"rest": 16},
            {"rest": teammate_remaining}, {"rest": 9},
        ],
        "numofplayers": [13, 16, teammate_remaining, 9],
        "selfRank": "9",
        "oppoRank": "2",
        "curRank": "9",
    }


def _decide(teammate_remaining):
    state = _state(teammate_remaining)
    engine = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=True)
    engine._anchor_role = "主攻"
    engine._current_role = "主攻"
    index = engine.decide(state)
    return state["actionList"][index]


def test_wf12_step63_leads_scatter_three_for_teammate_sprint():
    assert _decide(6) == ["Single", "3", ["D3"]]


def test_teammate_seven_does_not_trigger_six_card_send_rule():
    assert _decide(7) == ["Straight", "2", ["H2", "D3", "H4", "S5", "H6"]]
