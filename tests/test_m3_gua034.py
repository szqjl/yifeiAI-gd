# -*- coding: utf-8 -*-
"""GUA-034：M3 残局 solo 冲刺 END-M01–M04。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from m.m3 import M3DecisionEngine
from m.m3.m3_utils import CARD_VALUE_S2V, combine_handcards

BOMB_8 = ["S8", "H8", "C8", "C8", "D8"]


def _card_val(rank="7"):
    cv = CARD_VALUE_S2V.copy()
    cv[rank] = 15
    return cv


def _solo_numofplayers(my_rest=6, opp_rest=5):
    """pos0 队友已走完；pos2 为 yf2；pos1 为对手 greater。"""
    return [0, opp_rest, my_rest, 12]


def _rest_cards_stub():
    return [["SA"], ["HK"], ["SQ"], ["H2"]]


@pytest.fixture
def engine():
    return M3DecisionEngine(player_id=2)


@pytest.mark.unit
def test_end_m01_solo_sprint_detects_teammate_out(engine):
    """END-M01：队友 rest=0 → solo_sprint。"""
    assert engine._is_solo_sprint([0, 8, 6, 10], 2)
    assert not engine._is_solo_sprint([8, 8, 6, 10], 2)


@pytest.mark.unit
def test_end_m02_solo_wind_prefers_combo_over_single(engine):
    """END-M02：接风首出优先三带二/三张/对子，不拆对出小 3。"""
    hand = ["S3", "H3", "S9", "H9", "C9", "ST", "HT", "CT"]
    for pid, rest in zip("0123", [0, 8, 8, 10]):
        engine.history[pid]["remain"] = rest
    data = {
        "stage": "play",
        "type": "act",
        "myPos": 2,
        "curPos": -1,
        "greaterPos": -1,
        "curAction": ["PASS", "PASS", "PASS"],
        "greaterAction": ["PASS", "PASS", "PASS"],
        "handCards": hand,
        "curRank": "7",
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["Single", "3", ["S3"]],
            ["Pair", "3", ["S3", "H3"]],
            ["Trips", "9", ["S9", "H9", "C9"]],
            ["Trips", "T", ["ST", "HT", "CT"]],
            ["ThreeWithTwo", "9", ["S9", "H9", "C9", "S3", "H3"]],
        ],
        "publicInfo": [{"rest": 0}, {"rest": 8}, {"rest": 8}, {"rest": 10}],
    }
    idx = engine.on_message(data)
    chosen = data["actionList"][idx]
    assert chosen[0] in ("ThreeWithTwo", "Trips", "Pair")
    assert chosen[0] != "Single"


@pytest.mark.unit
def test_end_m03_solo_beat_opponent_single(engine):
    """END-M03：solo 下从三张拆单压对手 6（round 38 104 步类）。"""
    hand = ["S9", "H9", "C9", "ST", "HT", "CT"]
    rank_card = "H7"
    card_val = _card_val("7")
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "9", ["S9"]],
        ["Single", "T", ["ST"]],
    ]
    beat = ["Single", "6", ["S6"]]
    numofplayers = _solo_numofplayers()
    idx = engine._Single(
        action_list, beat, rank_card, hand, numofplayers, _rest_cards_stub(), card_val,
        2, 1, 0, 0,
    )
    assert idx > 0
    assert action_list[idx][0] == "Single"
    assert card_val[action_list[idx][1]] > card_val["6"]


@pytest.mark.unit
def test_end_m04_solo_beat_opponent_pair(engine):
    """END-M04：solo 下拆三张凑对压对手对 6（round 38 106 步类）。"""
    hand = ["S9", "H9", "C9", "ST", "HT", "CT"]
    rank_card = "H7"
    card_val = _card_val("7")
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Pair", "9", ["S9", "H9"]],
        ["Pair", "T", ["ST", "HT"]],
    ]
    beat = ["Pair", "6", ["S6", "H6"]]
    numofplayers = _solo_numofplayers()
    idx = engine._Pair(
        action_list, beat, rank_card, hand, numofplayers, [[]] * 4, card_val,
        2, 1, 0, 0,
    )
    assert idx > 0
    assert action_list[idx][0] == "Pair"
    assert card_val[action_list[idx][1]] > card_val["6"]


@pytest.mark.unit
def test_end_m04_r3_bomb_when_solo_cannot_beat_pair(engine):
    """END-M04 + GUA-029 R3：solo 压不住对子时 _passive 兜底出炸。"""
    hand = ["S9", "H9", "C9", "ST", "HT", "CT"] + list(BOMB_8)
    for pid, rest in zip("0123", [0, 5, 11, 12]):
        engine.history[pid]["remain"] = rest
    data = {
        "stage": "play",
        "type": "act",
        "myPos": 2,
        "curPos": 2,
        "greaterPos": 1,
        "curAction": ["PASS", "PASS", "PASS"],
        "greaterAction": ["Pair", "K", ["SK", "HK"]],
        "handCards": hand,
        "curRank": "7",
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["Pair", "9", ["S9", "H9"]],
            ["Pair", "T", ["ST", "HT"]],
            ["Bomb", "8", BOMB_8],
        ],
        "publicInfo": [{"rest": 0}, {"rest": 5}, {"rest": 11}, {"rest": 12}],
    }
    idx = engine.on_message(data)
    assert idx > 0
    assert data["actionList"][idx][0] == "Bomb"


@pytest.mark.unit
def test_solo_does_not_trigger_gua031_teammate_yield(engine):
    """solo 下 greater 为对手时不误触 GUA-031 P-F02。"""
    hand = ["S9", "H9", "C9", "ST", "HT", "CT"]
    rank_card = "H7"
    card_val = _card_val("7")
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Trips", "9", ["S9", "H9", "C9"]],
    ]
    beat = ["Trips", "3", ["S3", "H3", "C3"]]
    numofplayers = _solo_numofplayers()
    assert not engine._gua031_passive_teammate_yield(2, 1, numofplayers[2])
    idx = engine._Trips(
        action_list, beat, rank_card, hand, numofplayers, [[]] * 4, card_val,
        2, 1, 0, 0,
    )
    assert idx > 0
