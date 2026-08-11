# -*- coding: utf-8 -*-
"""GUA-232：自由领出（free lead）不得升级 Straight → StraightFlush。

match 6a7a9846 实战现场：开局首手（curPos=start / greaterPos=-1）打出同花顺
['H6','H8','H9','HT','H2']——同花顺是炸弹，领出禁炸（R10），但 GUA-161 升级
发生在 R10 之后，把已放行的 Straight 强行升级成同花顺，绕过领出禁炸。
"""

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

STRAIGHT_ACT = ["Straight", "6", ["H6", "H8", "H9", "HT", "H2"]]
SF_ACT = ["StraightFlush", "6", ["H6", "H8", "H9", "HT", "H2"]]


def _engine():
    engine = UltimateWinRateEngineV7(player_id=0)
    return engine


def test_free_lead_does_not_upgrade_to_straight_flush():
    """自由领出（greaterPos=-1）→ Straight 保持 Straight，不升级同花顺。"""
    engine = _engine()
    actions = [STRAIGHT_ACT, SF_ACT, ["Single", "J", ["HJ"]]]
    gs = {
        "myPos": 0,
        "curPos": -1,
        "greaterPos": -1,
        "greaterAction": [],
        "handCards": ["H6", "H8", "H9", "HT", "H2", "HJ"],
        "curRank": "2",
    }
    assert engine._prefer_stronger_same_cards_action(0, actions, gs) == 0


def test_lead_with_greaterpos_self_does_not_upgrade():
    """v1006 语义：greaterPos == myPos 也是自由领出 → 不升级。"""
    engine = _engine()
    actions = [STRAIGHT_ACT, SF_ACT]
    gs = {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 0,
        "handCards": ["H6", "H8", "H9", "HT", "H2"],
        "curRank": "2",
    }
    assert engine._prefer_stronger_same_cards_action(0, actions, gs) == 0


def test_follow_press_still_upgrades():
    """跟压/被动场景（greaterPos=对手）→ 保留升级行为（GUA-161 原义）。"""
    engine = _engine()
    actions = [STRAIGHT_ACT, SF_ACT]
    gs = {
        "myPos": 0,
        "curPos": 1,
        "greaterPos": 1,
        "greaterAction": ["Straight", "5", ["S5", "S6", "S7", "S8", "S9"]],
        "handCards": ["H6", "H8", "H9", "HT", "H2"],
        "curRank": "2",
    }
    assert engine._prefer_stronger_same_cards_action(0, actions, gs) == 1


def test_no_state_default_upgrades_for_backward_compat():
    """game_state=None（既有调用）→ 保持旧行为升级。"""
    engine = _engine()
    actions = [STRAIGHT_ACT, SF_ACT]
    assert engine._prefer_stronger_same_cards_action(0, actions) == 1