# -*- coding: utf-8 -*-
"""GUA-158: wind-catch two-hand structure must survive heuristic failures."""

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _state():
    hand = ["H4", "S4", "C4", "S6", "C6", "C8", "S9", "HT", "DJ", "HQ"]
    return {
        "actionList": [
            ["Single", "4", ["C4"]],
            ["Single", "4", ["S4"]],
            ["Single", "4", ["H4"]],
            ["Single", "6", ["C6"]],
            ["Single", "6", ["S6"]],
            ["Single", "8", ["C8"]],
            ["Single", "9", ["S9"]],
            ["Single", "T", ["HT"]],
            ["Single", "J", ["DJ"]],
            ["Single", "Q", ["HQ"]],
            ["Pair", "4", ["S4", "C4"]],
            ["Pair", "4", ["H4", "C4"]],
            ["Pair", "4", ["H4", "S4"]],
            ["Pair", "6", ["S6", "C6"]],
            ["Trips", "4", ["H4", "S4", "C4"]],
            ["ThreeWithTwo", "4", ["H4", "S4", "C4", "S6", "C6"]],
            ["Straight", "8", ["C8", "S9", "HT", "DJ", "HQ"]],
        ],
        "stage": "play",
        "handCards": hand,
        "myPos": 2,
        "curPos": -1,
        "curAction": None,
        "greaterPos": -1,
        "greaterAction": None,
        "publicInfo": [{"rest": 0}, {"rest": 16}, {"rest": 10}, {"rest": 12}],
        "numofplayers": [0, 16, 10, 12],
        "selfRank": "J",
        "oppoRank": "2",
        "curRank": "J",
    }


def test_two_hand_wind_catch_no_longer_raises_name_error():
    engine = UltimateWinRateEngineV7(player_id=2, use_grouping_engine=True)
    state = _state()
    index = engine.decide(state)
    assert state["actionList"][index][0] in {"ThreeWithTwo", "Straight"}


def test_exception_fallback_keeps_group_filtered_actions(monkeypatch):
    engine = UltimateWinRateEngineV7(player_id=2, use_grouping_engine=True)
    state = _state()

    def fail_heuristic(*args, **kwargs):
        raise RuntimeError("forced heuristic failure")

    monkeypatch.setattr(engine, "_heuristic_select", fail_heuristic)
    index = engine.decide(state)
    assert state["actionList"][index][0] in {"ThreeWithTwo", "Straight"}
    assert state["actionList"][index] != ["Single", "4", ["C4"]]
