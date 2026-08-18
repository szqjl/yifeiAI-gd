# -*- coding: utf-8 -*-
"""GUA-232：自由领出禁升级自然同花顺（R10 领出禁炸），野生同花顺允许升级。

野生同花顺（含逢人配 H{cur_rank}）牌力等同自然同花顺，不受 R10 限制。
自然同花顺（全自然牌）在自由领出时仍被阻止升级。
"""

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

NATURAL_STRAIGHT_ACT = ["Straight", "6", ["H6", "H7", "H8", "H9", "HT"]]
NATURAL_SF_ACT = ["StraightFlush", "6", ["H6", "H7", "H8", "H9", "HT"]]
WILD_STRAIGHT_ACT = ["Straight", "6", ["H6", "H8", "H9", "HT", "H2"]]
WILD_SF_ACT = ["StraightFlush", "6", ["H6", "H8", "H9", "HT", "H2"]]


def _engine():
    return UltimateWinRateEngineV7(player_id=0)


def test_free_lead_blocks_natural_sf_upgrade():
    """自由领出（greaterPos=-1）→ 自然同花顺保持 Straight，不升级。"""
    engine = _engine()
    actions = [NATURAL_STRAIGHT_ACT, NATURAL_SF_ACT, ["Single", "J", ["HJ"]]]
    gs = {
        "myPos": 0, "curPos": -1, "greaterPos": -1,
        "greaterAction": [],
        "handCards": ["H6", "H7", "H8", "H9", "HT", "HJ"],
        "curRank": "2",
    }
    assert engine._prefer_stronger_same_cards_action(0, actions, gs) == 0


def test_free_lead_allows_wild_sf_upgrade():
    """自由领出（greaterPos=-1）→ 野生同花顺（含 H2）允许升级。"""
    engine = _engine()
    actions = [WILD_STRAIGHT_ACT, WILD_SF_ACT, ["Single", "J", ["HJ"]]]
    gs = {
        "myPos": 0, "curPos": -1, "greaterPos": -1,
        "greaterAction": [],
        "handCards": ["H6", "H8", "H9", "HT", "H2", "HJ"],
        "curRank": "2",
    }
    assert engine._prefer_stronger_same_cards_action(0, actions, gs) == 1


def test_lead_with_greaterpos_self_blocks_natural_sf():
    """v1006 语义：greaterPos == myPos 也是自由领出 → 自然 SF 不升级。"""
    engine = _engine()
    actions = [NATURAL_STRAIGHT_ACT, NATURAL_SF_ACT]
    gs = {
        "myPos": 0, "curPos": 0, "greaterPos": 0,
        "handCards": ["H6", "H7", "H8", "H9", "HT"],
        "curRank": "2",
    }
    assert engine._prefer_stronger_same_cards_action(0, actions, gs) == 0


def test_lead_with_greaterpos_self_allows_wild_sf():
    """v1006 语义：greaterPos == myPos 也是自由领出 → 野生 SF 允许升级。"""
    engine = _engine()
    actions = [WILD_STRAIGHT_ACT, WILD_SF_ACT]
    gs = {
        "myPos": 0, "curPos": 0, "greaterPos": 0,
        "handCards": ["H6", "H8", "H9", "HT", "H2"],
        "curRank": "2",
    }
    assert engine._prefer_stronger_same_cards_action(0, actions, gs) == 1


def test_follow_press_still_upgrades():
    """跟压/被动场景（greaterPos=对手）→ 保留升级行为（GUA-161 原义）。"""
    engine = _engine()
    actions = [WILD_STRAIGHT_ACT, WILD_SF_ACT]
    gs = {
        "myPos": 0, "curPos": 1, "greaterPos": 1,
        "greaterAction": ["Straight", "5", ["S5", "S6", "S7", "S8", "S9"]],
        "handCards": ["H6", "H8", "H9", "HT", "H2"],
        "curRank": "2",
    }
    assert engine._prefer_stronger_same_cards_action(0, actions, gs) == 1


def test_no_state_default_upgrades_for_backward_compat():
    """game_state=None（既有调用）→ 保持旧行为升级。"""
    engine = _engine()
    actions = [WILD_STRAIGHT_ACT, WILD_SF_ACT]
    assert engine._prefer_stronger_same_cards_action(0, actions) == 1
