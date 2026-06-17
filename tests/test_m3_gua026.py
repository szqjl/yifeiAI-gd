# -*- coding: utf-8 -*-
"""GUA-026：M3 三带二拆牌 / 炸弹 / 级牌保护。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from m.m3 import M3DecisionEngine
from m.m3.m3_utils import CARD_VALUE_S2V


YF1_ROUND19_HAND = [
    "H2", "C2", "H3", "D3", "C4", "H5", "C5", "D5", "H6", "C7", "D7", "D7",
    "H8", "C8", "D8", "CJ", "DJ", "SQ", "CQ", "DQ", "HK", "DK", "DK",
    "SA", "HA", "HA", "HR",
]


@pytest.fixture
def engine():
    return M3DecisionEngine(player_id=0)


@pytest.mark.unit
def test_three_with_two_protect_rejects_level_rank_and_bomb(engine):
    rank_card = "H2"
    bomb_member = ["S4", "H4", "C4", "D4"]
    assert not engine._three_with_two_protect_ok(
        ["H5", "C5", "D5", "H2", "C2"], bomb_member, rank_card
    )
    assert not engine._three_with_two_protect_ok(
        ["S4", "H4", "C4", "S3", "H3"], bomb_member, rank_card
    )
    assert engine._three_with_two_protect_ok(
        ["H5", "C5", "D5", "D7", "D7"], bomb_member, rank_card
    )


@pytest.mark.unit
def test_pick_three_with_two_prefers_non_level_kicker(engine):
    rank_card = "H2"
    card_val = CARD_VALUE_S2V.copy()
    card_val["2"] = 15
    trip_member = ["S5", "H5", "C5"]
    pair_member = ["D7", "H7", "H2", "C2"]
    bomb_member = ["S4", "H4", "C4", "D4"]

    three2_actionList = [
        (1, ["ThreeWithTwo", "5", ["H5", "C5", "D5", "H2", "C2"]]),
        (2, ["ThreeWithTwo", "5", ["H5", "C5", "D5", "D7", "H7"]]),
    ]
    idx = engine._pick_three_with_two(
        three2_actionList,
        trip_member,
        pair_member,
        bomb_member,
        rank_card,
        card_val,
        prefer_low=True,
    )
    assert idx == 2


@pytest.mark.unit
def test_three_with_two_passes_when_only_level_rank_kicker(engine):
    rank_card = "H2"
    card_val = CARD_VALUE_S2V.copy()
    card_val["2"] = 15
    handcards = YF1_ROUND19_HAND
    numofplayers = [20, 20, 20, 20]
    cur_action = ["ThreeWithTwo", "3", ["S3", "C3", "C3", "S8", "S8"]]
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["ThreeWithTwo", "5", ["H5", "C5", "D5", "H2", "C2"]],
    ]
    idx = engine._ThreeWithTwo(
        action_list,
        cur_action,
        rank_card,
        handcards,
        numofplayers,
        [[]] * 4,
        card_val,
        myPos=0,
        greaterPos=3,
        pass_num=0,
        my_pass_num=0,
    )
    assert idx == 0
