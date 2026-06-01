# -*- coding: utf-8 -*-
"""GUA-032：M3 记牌基建 + CALC-M01/M03 + MEM-M02。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from m.m3 import M3DecisionEngine
from m.m3.m3_utils import CARD_VALUE_S2V, sync_remain_cards_classbynum


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


@pytest.fixture
def engine():
    return M3DecisionEngine(player_id=0)


@pytest.mark.unit
def test_sync_remain_cards_classbynum_matches_matrix(engine):
    """基建：出牌递减后 classbynum 与 remain_cards 一致。"""
    data = {
        "curPos": 1,
        "curAction": ["Pair", "9", ["S9", "H9"]],
    }
    engine._update_play_state(data)
    expected = sync_remain_cards_classbynum(engine.remain_cards)
    assert engine.remain_cards_classbynum == expected
    assert engine.remain_cards_classbynum[8] == 6


@pytest.mark.unit
def test_calc_m01_skips_bomb_when_rank_outside_le3(engine):
    """CALC-M01：某点外剩≤3 → 被动不回该点 Bomb。"""
    hand = _fill_hand(["S9", "H9", "C9", "D9"])
    rank_card = "H2"
    card_val = _card_val()
    engine.remain_cards_classbynum[8] = 3
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Bomb", "9", ["S9", "H9", "C9", "D9"]],
    ]
    beat = ["Bomb", "8", ["S8", "H8", "C8", "D8"]]
    numofplayers = [20, 12, 14, 11]
    idx = engine._Bomb(
        action_list, beat, rank_card, hand, numofplayers, [[]] * 4, card_val, 0, 1,
    )
    assert idx == 0


@pytest.mark.unit
def test_calc_m01_allows_bomb_when_rank_outside_gt3(engine):
    """CALC-M01：外剩>3 时仍可被动出炸。"""
    hand = _fill_hand(["S9", "H9", "C9", "D9"])
    rank_card = "H2"
    card_val = _card_val()
    engine.remain_cards_classbynum[8] = 4
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Bomb", "9", ["S9", "H9", "C9", "D9"]],
    ]
    beat = ["Bomb", "8", ["S8", "H8", "C8", "D8"]]
    numofplayers = [20, 12, 14, 11]
    idx = engine._Bomb(
        action_list, beat, rank_card, hand, numofplayers, [[]] * 4, card_val, 0, 1,
    )
    assert idx == 1


@pytest.mark.unit
def test_calc_m03_skips_straight_with_t_when_t_exhausted(engine):
    """CALC-M03：点十外剩0 → _active 首发仍降权；被动夺权见 GUA-036 CTRL-P02。"""
    hand = _fill_hand(["S6", "H7", "C8", "D9", "ST"])
    rank_card = "H2"
    card_val = _card_val()
    engine.remain_cards_classbynum[9] = 0
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Straight", "6", ["S6", "H7", "C8", "D9", "ST"]],
    ]
    beat = ["Straight", "5", ["S5", "H6", "C7", "D8", "S9"]]
    numofplayers = [18, 10, 16, 9]
    idx = engine._Straight(
        action_list, beat, rank_card, hand, numofplayers, card_val, 0, 0, 0, 1,
    )
    assert idx == 1


@pytest.mark.unit
def test_calc_m03_skips_straight_with_5_when_5_exhausted(engine):
    """CALC-M03：点五外剩0 → 被动压顺仍可用（GUA-036 豁免）。"""
    hand = _fill_hand(["S5", "H6", "C7", "D8", "S9"])
    rank_card = "H2"
    card_val = _card_val()
    engine.remain_cards_classbynum[4] = 0
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Straight", "9", ["S5", "H6", "C7", "D8", "S9"]],
    ]
    beat = ["Straight", "8", ["S4", "H5", "C6", "D7", "S8"]]
    numofplayers = [18, 10, 16, 9]
    idx = engine._Straight(
        action_list, beat, rank_card, hand, numofplayers, card_val, 0, 0, 0, 1,
    )
    assert idx == 1


@pytest.mark.unit
def test_calc_m03_degraded_flag_active_only(engine):
    """CALC-M03：降权标记仍对 _active 首发有效（passive_seize=False）。"""
    engine.remain_cards_classbynum[9] = 0
    cards = ["S6", "H7", "C8", "D9", "ST"]
    assert engine._gua032_straight_degraded(cards) is True
    assert engine._gua032_straight_degraded(cards, passive_seize=True) is False
    """MEM-M02：记录各家是否出过炸及最大炸弹点数。"""
    engine._update_play_state({
        "curPos": 2,
        "curAction": ["Bomb", "K", ["SK", "HK", "CK", "DK"]],
    })
    mem = engine._player_bomb_mem["2"]
    assert mem["has_bomb"] is True
    assert mem["max_bomb_rank"] == CARD_VALUE_S2V["K"]
