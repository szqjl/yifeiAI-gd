# -*- coding: utf-8 -*-
"""GUA-035：M3 END-M02+ solo 接风对手剩张过滤。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from m.m3 import M3DecisionEngine


@pytest.fixture
def engine():
    return M3DecisionEngine(player_id=2)


def _wind_data(hand, action_list, rests, cur_rank="7"):
    return {
        "stage": "play",
        "type": "act",
        "myPos": 2,
        "curPos": -1,
        "greaterPos": -1,
        "curAction": ["PASS", "PASS", "PASS"],
        "greaterAction": ["PASS", "PASS", "PASS"],
        "handCards": hand,
        "curRank": cur_rank,
        "actionList": action_list,
        "publicInfo": [{"rest": r} for r in rests],
    }


@pytest.mark.unit
def test_end_m02_plus_01_opponent_rests(engine):
    """END-M02+-01：扫描上家、下家两家对手。"""
    rests = engine._gua035_solo_opponent_rests([0, 1, 8, 2], 2)
    assert rests == [2, 1]


@pytest.mark.unit
def test_skip_single_when_any_opponent_one_card(engine):
    """END-M02+-02：任一对手剩 1 张 → 接风不出单张。"""
    hand = ["S3", "S9", "H9", "C9", "ST", "HT", "CT"]
    for pid, rest in zip("0123", [0, 1, 7, 10]):
        engine.history[pid]["remain"] = rest
    data = _wind_data(
        hand,
        [
            ["PASS", "PASS", "PASS"],
            ["Single", "3", ["S3"]],
            ["Trips", "9", ["S9", "H9", "C9"]],
            ["Trips", "T", ["ST", "HT", "CT"]],
        ],
        [0, 1, 7, 10],
    )
    idx = engine.on_message(data)
    assert data["actionList"][idx][0] == "Trips"


@pytest.mark.unit
def test_skip_pair_when_any_opponent_two_cards(engine):
    """END-M02+-03：任一对手剩 2 张 → 接风不出对子。"""
    hand = ["S3", "H3", "S9", "H9", "C9", "ST", "HT", "CT"]
    for pid, rest in zip("0123", [0, 2, 8, 12]):
        engine.history[pid]["remain"] = rest
    data = _wind_data(
        hand,
        [
            ["PASS", "PASS", "PASS"],
            ["Pair", "3", ["S3", "H3"]],
            ["Trips", "9", ["S9", "H9", "C9"]],
            ["Trips", "T", ["ST", "HT", "CT"]],
        ],
        [0, 2, 8, 12],
    )
    idx = engine.on_message(data)
    assert data["actionList"][idx][0] == "Trips"


@pytest.mark.unit
def test_skip_threetwo_when_opponent_five_prefers_trips(engine):
    """END-M02+-04：对手剩 5 张 → 优先跳过三带二，改出三张。"""
    hand = ["S3", "H3", "S9", "H9", "C9", "ST", "HT", "CT"]
    for pid, rest in zip("0123", [0, 5, 8, 12]):
        engine.history[pid]["remain"] = rest
    data = _wind_data(
        hand,
        [
            ["PASS", "PASS", "PASS"],
            ["ThreeWithTwo", "9", ["S9", "H9", "C9", "S3", "H3"]],
            ["Trips", "9", ["S9", "H9", "C9"]],
            ["Trips", "T", ["ST", "HT", "CT"]],
        ],
        [0, 5, 8, 12],
    )
    idx = engine.on_message(data)
    assert data["actionList"][idx][0] == "Trips"


@pytest.mark.unit
def test_threetwo_fallback_when_only_whole_hand(engine):
    """END-M02+-04 fallback：过滤后无整手 → 仍出三带二。"""
    hand = ["S9", "H9", "C9", "S3", "H3"]
    for pid, rest in zip("0123", [0, 5, 5, 12]):
        engine.history[pid]["remain"] = rest
    data = _wind_data(
        hand,
        [
            ["PASS", "PASS", "PASS"],
            ["ThreeWithTwo", "9", ["S9", "H9", "C9", "S3", "H3"]],
        ],
        [0, 5, 5, 12],
    )
    idx = engine.on_message(data)
    assert data["actionList"][idx][0] == "ThreeWithTwo"


@pytest.mark.unit
def test_gua034_regression_wind_still_prefers_combo(engine):
    """GUA-034 回归：无 1/2/5 过滤时仍优先三带二/三张。"""
    hand = ["S3", "H3", "S9", "H9", "C9", "ST", "HT", "CT"]
    for pid, rest in zip("0123", [0, 8, 8, 10]):
        engine.history[pid]["remain"] = rest
    data = _wind_data(
        hand,
        [
            ["PASS", "PASS", "PASS"],
            ["Single", "3", ["S3"]],
            ["Trips", "9", ["S9", "H9", "C9"]],
            ["ThreeWithTwo", "9", ["S9", "H9", "C9", "S3", "H3"]],
        ],
        [0, 8, 8, 10],
    )
    idx = engine.on_message(data)
    assert data["actionList"][idx][0] in ("ThreeWithTwo", "Trips")
