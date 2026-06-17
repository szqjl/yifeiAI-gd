# -*- coding: utf-8
"""GUA-031：M3 传牌 guard + 队友让道 P-F02 / PASS-P02–P04。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from m.m3 import M3DecisionEngine
from m.m3.m3_utils import CARD_VALUE_S2V


def _card_val(rank="2"):
    cv = CARD_VALUE_S2V.copy()
    cv[rank] = 15
    return cv


def _fill_hand(base, n=27):
    filler = ["H4", "D4", "S6", "C6", "HT", "DT"] * 5
    hand = list(base)
    for c in filler:
        if len(hand) >= n:
            break
        hand.append(c)
    return hand[:n]


@pytest.fixture
def engine():
    return M3DecisionEngine(player_id=0)


@pytest.mark.unit
def test_p_f02_trips_yield_to_teammate(engine):
    """P-F02：队友控牌、非冲刺 → _Trips PASS。"""
    hand = _fill_hand(["S5", "H5", "C5", "D5", "S3", "C3"])
    rank_card = "H2"
    card_val = _card_val()
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Trips", "5", ["S5", "H5", "C5"]],
    ]
    beat = ["Trips", "3", ["S3", "H3", "C3"]]
    numofplayers = [20, 12, 14, 11]
    idx = engine._Trips(
        action_list, beat, rank_card, hand, numofplayers, [[]] * 4, card_val,
        0, 2, 0, 0,
    )
    assert idx == 0


@pytest.mark.unit
def test_p_f02_straight_yield_to_teammate(engine):
    """P-F02：队友控牌、非冲刺 → _Straight PASS。"""
    hand = _fill_hand(["S3", "H4", "C5", "D6", "S7"])
    rank_card = "H2"
    card_val = _card_val()
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Straight", "3", ["S3", "H4", "C5", "D6", "S7"]],
    ]
    beat = ["Straight", "3", ["S3", "H4", "C5", "D6", "S7"]]
    numofplayers = [18, 10, 16, 9]
    idx = engine._Straight(
        action_list, beat, rank_card, hand, numofplayers, card_val, 0, 0, 0, 2,
    )
    assert idx == 0


@pytest.mark.unit
def test_p_f02_two_trips_yield_to_teammate(engine):
    """P-F02：队友控牌、非冲刺 → _TwoTrips PASS。"""
    hand = _fill_hand(["S5", "H5", "C5", "S6", "H6", "C6"])
    rank_card = "H2"
    card_val = _card_val()
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["TwoTrips", "5", ["S5", "H5", "C5", "S6", "H6", "C6"]],
    ]
    beat = ["TwoTrips", "4", ["S4", "H4", "C4", "S5", "H5", "C5"]]
    numofplayers = [22, 11, 13, 10]
    idx = engine._TwoTrips(
        action_list, beat, rank_card, hand, numofplayers, [[]] * 4, card_val,
        0, 2, 0, 0,
    )
    assert idx == 0


@pytest.mark.unit
def test_p_f02_three_pair_yield_to_teammate(engine):
    """P-F02：队友控牌、非冲刺 → _ThreePair PASS。"""
    hand = _fill_hand(["S3", "H3", "S4", "H4", "S5", "H5"])
    rank_card = "H2"
    card_val = _card_val()
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["ThreePair", "3", ["S3", "H3", "S4", "H4", "S5", "H5"]],
    ]
    beat = ["ThreePair", "3", ["S3", "H3", "S4", "H4", "S5", "H5"]]
    numofplayers = [19, 10, 15, 8]
    idx = engine._ThreePair(
        action_list, beat, rank_card, hand, numofplayers, [[]] * 4, card_val,
        0, 2, 0, 0,
    )
    assert idx == 0


@pytest.mark.unit
def test_p02_feed_min_single_when_teammate_one_card(engine):
    """PASS-P02：队友剩 1 张 → 出最小 Single。"""
    for pid, rest in zip("0123", [20, 12, 1, 15]):
        engine.history[pid]["remain"] = rest
    hand = _fill_hand(["S3", "C5", "D7", "H9", "ST"])
    data = {
        "stage": "play",
        "type": "act",
        "myPos": 0,
        "curPos": -1,
        "greaterPos": -1,
        "handCards": hand,
        "curRank": "2",
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["Single", "3", ["S3"]],
            ["Single", "5", ["C5"]],
            ["Single", "9", ["H9"]],
        ],
        "publicInfo": [{"rest": 20}, {"rest": 12}, {"rest": 1}, {"rest": 15}],
    }
    idx = engine.on_message(data)
    assert idx == 1
    assert data["actionList"][idx][1] == "3"


@pytest.mark.unit
def test_p03_block_tiny_single_when_next_one_card(engine):
    """PASS-P03：下家报单时不出过小单（< T）。"""
    filtered = engine._gua031_filter_singles_for_next1(
        [["3", "S3"], ["5", "C5"], ["T", "ST"]],
        _card_val(),
        1,
    )
    assert len(filtered) == 1
    assert filtered[0][0] == "T"


@pytest.mark.unit
def test_p04_prefer_pair_when_teammate_five_cards(engine):
    """PASS-P04：队友剩 5 张 → 优先 Pair。"""
    for pid, rest in zip("0123", [20, 12, 5, 14]):
        engine.history[pid]["remain"] = rest
    hand = _fill_hand(["S3", "C3", "D5", "H5", "S7", "D8", "H9"])
    data = {
        "stage": "play",
        "type": "act",
        "myPos": 0,
        "curPos": -1,
        "greaterPos": -1,
        "handCards": hand,
        "curRank": "2",
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["Single", "3", ["S3"]],
            ["Pair", "5", ["D5", "H5"]],
        ],
        "publicInfo": [{"rest": 20}, {"rest": 12}, {"rest": 5}, {"rest": 14}],
    }
    idx = engine.on_message(data)
    assert idx == 2
    assert data["actionList"][idx][0] == "Pair"
