# -*- coding: utf-8 -*-
"""GUA-029：M3 炸弹可执行规则包 R1–R6。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from m.m3 import M3DecisionEngine
from m.m3.m3_utils import CARD_VALUE_S2V, choose_bomb, combine_handcards

BOMB_8 = ["S8", "H8", "C8", "C8", "D8"]


def _card_val(rank="2"):
    cv = CARD_VALUE_S2V.copy()
    cv[rank] = 15
    return cv


def _hand_with_bomb(extra=None):
    filler = extra or (["H2", "D2", "S3", "C3", "D3"] * 4)
    return list(BOMB_8) + list(filler)[:19]


@pytest.fixture
def engine():
    return M3DecisionEngine(player_id=0)


@pytest.mark.unit
def test_r1_choose_bomb_v1006_format():
    """R1：v1006 动作 rank 在 action[1]。"""
    hand = _hand_with_bomb()
    rank_card = "H2"
    card_val = _card_val()
    sorted_cards, bomb_info = combine_handcards(hand, "2", card_val)
    bomb_actionList = [(1, ["Bomb", "8", BOMB_8])]
    idx = choose_bomb(bomb_actionList, hand, sorted_cards, bomb_info, rank_card, card_val)
    assert idx == 1


@pytest.mark.unit
def test_r2_counter_bomb_on_opponent_bomb(engine):
    """R2：对手 Bomb 且可回炸 → 必出。"""
    hand = _hand_with_bomb()
    rank_card = "H2"
    card_val = _card_val()
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Bomb", "8", BOMB_8],
    ]
    beat = ["Bomb", "Q", ["SQ", "SQ", "DQ", "DQ"]]
    numofplayers = [24, 16, 20, 17]
    idx = engine._Bomb(
        action_list, beat, rank_card, hand, numofplayers, [[]] * 4, card_val, 0, 3,
    )
    assert idx == 1


@pytest.mark.unit
def test_r3_sprint_bomb_when_opp_leq7(engine):
    """R3：对手 ≤7 张、无三带二可跟 → 兜底出炸。"""
    hand = _hand_with_bomb()
    rank_card = "H2"
    card_val = _card_val()
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Bomb", "8", BOMB_8],
    ]
    beat = ["ThreeWithTwo", "K", ["SK", "SK", "CK", "S5", "H5"]]
    numofplayers = [15, 5, 18, 5]
    idx = engine._ThreeWithTwo(
        action_list, beat, rank_card, hand, numofplayers, [[]] * 4, card_val,
        0, 3, 0, 0,
    )
    assert idx == 1
    sprint = engine._gua029_passive_sprint_bomb(
        action_list, hand, rank_card, card_val, 0, 3, numofplayers, beat,
    )
    assert sprint == 1


@pytest.mark.unit
def test_r3_on_message_sprint_bomb(engine):
    """R3：被动整链 — 三带二 PASS 后 R3 出炸。"""
    hand = _hand_with_bomb()
    for pid, rest in zip("0123", [15, 5, 18, 5]):
        engine.history[pid]["remain"] = rest
    data = {
        "stage": "play",
        "type": "act",
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 3,
        "curAction": ["PASS", "PASS", "PASS"],
        "greaterAction": ["ThreeWithTwo", "K", ["SK", "SK", "CK", "S5", "H5"]],
        "handCards": hand,
        "curRank": "2",
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["Bomb", "8", BOMB_8],
        ],
        "publicInfo": [
            {"rest": 15}, {"rest": 5}, {"rest": 18}, {"rest": 5},
        ],
    }
    idx = engine.on_message(data)
    assert idx == 1
    assert data["actionList"][idx][0] == "Bomb"


@pytest.mark.unit
def test_r4_block_bomb_when_opp_has_four_cards(engine):
    """R4：对手剩 4 张且有非炸可跟 → 不炸。"""
    hand = _hand_with_bomb()
    rank_card = "H2"
    card_val = _card_val()
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Pair", "3", ["S3", "C3"]],
        ["Bomb", "8", BOMB_8],
    ]
    assert not engine._gua029_r4_allows_bomb(4, 24, action_list)
    idx = engine._gua029_try_bomb(
        action_list, hand, rank_card, card_val, 0, 3, [24, 16, 20, 4],
    )
    assert idx == -1


@pytest.mark.unit
def test_r4_whitelist_only_bomb_beats(engine):
    """R4 白名单：仅炸弹能压时仍可炸。"""
    hand = _hand_with_bomb()
    rank_card = "H2"
    card_val = _card_val()
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Bomb", "8", BOMB_8],
    ]
    assert engine._gua029_r4_allows_bomb(4, 24, action_list)
    idx = engine._gua029_try_bomb(
        action_list, hand, rank_card, card_val, 0, 3, [24, 16, 20, 4],
    )
    assert idx == 1


@pytest.mark.unit
def test_r5_no_bomb_on_teammate(engine):
    """R5：队友控牌时不炸。"""
    hand = _hand_with_bomb()
    rank_card = "H2"
    card_val = _card_val()
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Bomb", "8", BOMB_8],
    ]
    beat = ["Bomb", "Q", ["SQ", "SQ", "DQ", "DQ"]]
    numofplayers = [24, 16, 20, 17]
    idx = engine._Bomb(
        action_list, beat, rank_card, hand, numofplayers, [[]] * 4, card_val, 0, 2,
    )
    assert idx == 0


@pytest.mark.unit
def test_r6_active_bomb_finish(engine):
    """R6：剩 ≤10 张且炸弹一手清 → 主动出炸。"""
    hand = list(BOMB_8)
    for pid, rest in zip("0123", [5, 20, 20, 20]):
        engine.history[pid]["remain"] = rest
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
            ["Bomb", "8", hand],
        ],
        "publicInfo": [{"rest": 5}, {"rest": 20}, {"rest": 20}, {"rest": 20}],
    }
    idx = engine.on_message(data)
    assert idx == 1
    assert data["actionList"][idx][0] == "Bomb"
