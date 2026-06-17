# -*- coding: utf-8
"""GUA-028：M3 与 v1006 说明书三项对齐（TripsPair / indexRange / publicInfo.rest）。"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from game_logic.platform_act import clamp_act_index, normalize_play_act_fields
from m.m3 import M3DecisionEngine


@pytest.mark.unit
def test_clamp_act_index_respects_index_range():
    actions = [["PASS"]] * 30
    assert clamp_act_index(25, actions, 21) == 21
    assert clamp_act_index(99, actions, None) == 29


@pytest.mark.unit
def test_normalize_play_act_fields_none_to_minus_one():
    data = {"curPos": None, "greaterPos": None}
    normalize_play_act_fields(data)
    assert data["curPos"] == -1
    assert data["greaterPos"] == -1


@pytest.mark.unit
def test_sync_remain_from_public_info():
    engine = M3DecisionEngine(player_id=0)
    engine.history["1"]["remain"] = 20
    engine.history["2"]["remain"] = 15
    data = {
        "publicInfo": [
            {"rest": 22, "playArea": None},
            {"rest": 18, "playArea": None},
            {"rest": 11, "playArea": None},
            {"rest": 27, "playArea": None},
        ],
    }
    engine._sync_remain_from_public_info(data)
    assert engine.history["0"]["remain"] == 22
    assert engine.history["1"]["remain"] == 18
    assert engine.history["2"]["remain"] == 11
    assert engine.history["3"]["remain"] == 27


@pytest.mark.unit
def test_passive_dispatches_trips_pair_to_three_with_two_handler():
    engine = M3DecisionEngine(player_id=0)
    data = {
        "stage": "play",
        "type": "act",
        "greaterPos": 1,
        "curPos": 1,
        "curRank": "2",
        "curAction": ["TripsPair", "8", ["S8", "H8", "D8", "C7", "D7"]],
        "greaterAction": ["TripsPair", "8", ["S8", "H8", "D8", "C7", "D7"]],
        "publicInfo": [
            {"rest": 20, "playArea": None},
            {"rest": 18, "playArea": ["TripsPair", "8", ["S8", "H8", "D8", "C7", "D7"]]},
            {"rest": 22, "playArea": None},
            {"rest": 21, "playArea": None},
        ],
        "handCards": ["S3"] * 27,
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["TripsPair", "9", ["S9", "H9", "D9", "C4", "D4"]],
        ],
        "indexRange": 1,
    }
    with patch.object(engine, "_ThreeWithTwo", return_value=1) as mock_tw:
        idx = engine.on_message(data)
    assert idx == 1
    assert mock_tw.called
    assert mock_tw.call_args[0][1][0] == "TripsPair"


@pytest.mark.unit
def test_on_message_clamps_index_with_index_range():
    engine = M3DecisionEngine(player_id=0)
    data = {
        "stage": "play",
        "type": "act",
        "greaterPos": -1,
        "curPos": -1,
        "curRank": "2",
        "handCards": ["S3"] * 27,
        "publicInfo": [{"rest": 27}] * 4,
        "actionList": [["PASS", "PASS", "PASS"]] * 5,
        "indexRange": 2,
    }
    with patch.object(engine, "_active", return_value=4):
        idx = engine.on_message(data)
    assert idx == 2
