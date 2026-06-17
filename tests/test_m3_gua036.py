# -*- coding: utf-8 -*-
"""GUA-036：M3 控权压顺 + 接风配合（CTRL/WIND/TEAM）。"""

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
    filler = ["H4", "D4", "S4", "C4"] * 8
    hand = list(base)
    for c in filler:
        if len(hand) >= n:
            break
        hand.append(c)
    return hand[:n]


def _wind_data(hand, action_list, rests, cur_rank="2", greater_action=None, greater_pos=-1):
    ga = greater_action or ["PASS", "PASS", "PASS"]
    return {
        "stage": "play",
        "type": "act",
        "myPos": 2,
        "curPos": -1,
        "greaterPos": greater_pos,
        "curAction": ["PASS", "PASS", "PASS"],
        "greaterAction": ga,
        "handCards": hand,
        "curRank": cur_rank,
        "actionList": action_list,
        "publicInfo": [{"rest": r} for r in rests],
    }


@pytest.fixture
def engine():
    return M3DecisionEngine(player_id=2)


@pytest.mark.unit
def test_ctrl_p01_passive_seize_min_straight(engine):
    """CTRL-P01：敌顺 actionList 可压 → 最小够用顺（不依赖 combine 对齐）。"""
    hand = _fill_hand(["S6", "H7", "C8", "D9", "ST"])
    rank_card = "H2"
    card_val = _card_val()
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Straight", "T", ["S6", "H7", "C8", "D9", "ST"]],
    ]
    beat = ["Straight", "9", ["S5", "H6", "C7", "D8", "S9"]]
    numofplayers = [18, 10, 16, 9]
    idx = engine._Straight(
        action_list, beat, rank_card, hand, numofplayers, card_val, 0, 0, 2, 1,
    )
    assert idx == 1
    assert action_list[idx][0] == "Straight"


@pytest.mark.unit
def test_ctrl_p02_passive_beats_despite_calc_m03(engine):
    """CTRL-P02：被动压顺时 CALC-M03 不拦（点十外剩 0 仍夺权）。"""
    hand = _fill_hand(["S6", "H7", "C8", "D9", "ST"])
    rank_card = "H2"
    card_val = _card_val()
    engine.remain_cards_classbynum[9] = 0
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Straight", "T", ["S6", "H7", "C8", "D9", "ST"]],
    ]
    beat = ["Straight", "9", ["S5", "H6", "C7", "D8", "S9"]]
    numofplayers = [18, 10, 16, 9]
    idx = engine._Straight(
        action_list, beat, rank_card, hand, numofplayers, card_val, 0, 0, 2, 1,
    )
    assert idx == 1


@pytest.mark.unit
def test_ctrl_p01_prefers_bomb_over_break_bomb_straight(engine):
    """拆炸不组顺：顺子占炸弹成员 → 优先 Bomb。"""
    hand = _fill_hand(["S7", "H8", "C9", "D9", "S9", "H9", "ST", "HT", "CT"])
    rank_card = "H2"
    card_val = _card_val()
    engine.remain_cards_classbynum[8] = 8
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Straight", "T", ["S7", "H8", "C9", "ST", "HT"]],
        ["Bomb", "9", ["S9", "H9", "C9", "D9"]],
    ]
    beat = ["Straight", "6", ["S3", "H4", "C5", "D6", "S7"]]
    numofplayers = [18, 10, 16, 9]
    idx = engine._Straight(
        action_list, beat, rank_card, hand, numofplayers, card_val, 0, 0, 2, 1,
    )
    assert idx == 2
    assert action_list[idx][0] == "Bomb"


@pytest.mark.unit
def test_gua031_teammate_yield_still_passes_on_straight(engine):
    """队友控牌让道：GUA-031 不回归。"""
    hand = _fill_hand(["S6", "H7", "C8", "D9", "ST"])
    rank_card = "H2"
    card_val = _card_val()
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Straight", "T", ["S6", "H7", "C8", "D9", "ST"]],
    ]
    beat = ["Straight", "9", ["S5", "H6", "C7", "D8", "S9"]]
    numofplayers = [18, 10, 16, 9]
    idx = engine._Straight(
        action_list, beat, rank_card, hand, numofplayers, card_val, 0, 0, 2, 0,
    )
    assert idx == 0


@pytest.mark.unit
def test_wind_p01_blocks_splitting_trips_single(engine):
    """WIND-P01：接风禁拆三张出单，改出对/三张。"""
    hand = _fill_hand(["S2", "H2", "C2", "S5", "H5"])
    for pid, rest in zip("0123", [10, 12, 8, 14]):
        engine.history[pid]["remain"] = rest
    data = _wind_data(
        hand,
        [
            ["PASS", "PASS", "PASS"],
            ["Single", "2", ["S2"]],
            ["Pair", "5", ["S5", "H5"]],
            ["Trips", "2", ["S2", "H2", "C2"]],
        ],
        [10, 12, 8, 14],
    )
    idx = engine.on_message(data)
    chosen = data["actionList"][idx]
    assert chosen[0] in ("Pair", "Trips")
    assert chosen[0] != "Single"


@pytest.mark.unit
def test_team_p01_wind_follows_teammate_pair_line(engine):
    """TEAM-P01：队友末手对子 + 接风 → 优先出对。"""
    hand = _fill_hand(["S3", "H3", "S5", "H5", "S8", "H8"])
    for pid, rest in zip("0123", [10, 12, 8, 14]):
        engine.history[pid]["remain"] = rest
    engine._gua036_teammate_last = ["Pair", "2", ["S2", "H2"]]
    data = _wind_data(
        hand,
        [
            ["PASS", "PASS", "PASS"],
            ["Single", "3", ["S3"]],
            ["Pair", "3", ["S3", "H3"]],
            ["Pair", "5", ["S5", "H5"]],
        ],
        [10, 12, 8, 14],
        greater_action=["Pair", "2", ["S2", "H2"]],
        greater_pos=0,
    )
    idx = engine.on_message(data)
    chosen = data["actionList"][idx]
    assert chosen[0] == "Pair"
