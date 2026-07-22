# -*- coding: utf-8 -*-
"""GUA-159: legal same-type press hard-blocks bomb-like heuristic candidates."""

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _state():
    hand = [
        "S3", "S3",
        "H7", "S7", "C7", "D7",
        "S8", "C8", "S8",
        "S9",
        "HK", "SK", "DK", "HK", "DK",
        "SB",
    ]
    return {
        "actionList": [],
        "stage": "play",
        "handCards": hand,
        "myPos": 2,
        "curPos": -1,
        "curAction": None,
        "greaterPos": 3,
        "greaterAction": ["ThreeWithTwo", "6", ["H6", "C6", "D6", "D8", "D8"]],
        "publicInfo": [{"rest": 21}, {"rest": 22}, {"rest": 16}, {"rest": 20}],
        "numofplayers": [21, 22, 16, 20],
        "selfRank": "9",
        "oppoRank": "2",
        "curRank": "9",
    }


def _engine_with_grouping(state):
    engine = UltimateWinRateEngineV7(player_id=2, use_grouping_engine=True)
    engine._run_grouping_engine(state)
    return engine


def test_wf12_anchor_three_with_two_hard_blocks_bomb():
    state = _state()
    actions = [
        ["PASS", "PASS", "PASS"],
        ["ThreeWithTwo", "8", ["S3", "S3", "S8", "C8", "S8"]],
        ["Bomb", "7", ["H7", "S7", "C7", "D7"]],
    ]
    engine = _engine_with_grouping(state)

    selected_index = engine._heuristic_select(state, actions)

    assert actions[selected_index][0] == "ThreeWithTwo"
    assert 2 not in dict(engine._last_heuristic_scores)


def test_bomb_remains_eligible_without_same_type_press():
    state = _state()
    actions = [
        ["PASS", "PASS", "PASS"],
        ["Bomb", "7", ["H7", "S7", "C7", "D7"]],
        ["Bomb", "K", ["HK", "SK", "DK", "HK", "DK"]],
    ]
    engine = _engine_with_grouping(state)

    selected_index = engine._heuristic_select(state, actions)

    assert actions[selected_index][0] == "Bomb"
    assert 1 in dict(engine._last_heuristic_scores)
    assert 2 in dict(engine._last_heuristic_scores)
