# -*- coding: utf-8 -*-
"""GUA-234 阶段 D：中期领出消费 _mid_feed_P。"""

import pytest

from src.v.nn.dynamic_regroup import resolve_feed_prefer_types
from src.v.nn.stage_main_attack_lead import recommend_main_attack_lead
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def test_resolve_feed_prefer_endgame_uses_assist_table():
    """残局 1–5 仍走 assist_prefer_for。"""
    prefer = resolve_feed_prefer_types(3, ["Straight", "Pair"])
    assert prefer == ["Trips", "Pair", "Single"]


def test_resolve_feed_prefer_midgame_uses_mid_feed_p():
    """中期 ≥6 优先 _mid_feed_P。"""
    prefer = resolve_feed_prefer_types(12, ["Pair", "Straight", "Single"])
    assert prefer[0] == "Straight"
    assert "Pair" in prefer


def test_feeding_target_types_mid_overrides_legacy():
    """_feeding_target_types 中期被 _mid_feed_P 覆盖。"""
    engine = UltimateWinRateEngineV7(player_id=0)
    types = engine._feeding_target_types(
        8,
        {"_mid_feed_P": ["Straight", "ThreeWithTwo"]},
    )
    assert types == ["Straight", "ThreeWithTwo"]


def test_main_attack_lead_mid_feed_p_from_plan(monkeypatch):
    """主攻领出：_mid_feed_P 命中时 intent=main_feed_mid_p。"""
    hand = ["C3", "D4", "H5", "S6", "C7"] + ["D8"] * 12
    hand = hand[:18]
    card_mask = {c: (-1, 0.0, 1) for c in hand}

    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = {0: "straight"}
    engine._group_members = {0: hand[:5], -1: hand[5:]}
    engine._current_role = "主攻"

    def _fake_feed(*_args, **_kwargs):
        return {
            "type": "Straight",
            "rank": "3",
            "cards": hand[:5],
            "intent": "main_feed_teammate_Straight",
        }

    monkeypatch.setattr(
        "src.v.nn.stage_main_attack_lead._try_feed_from_groups",
        _fake_feed,
    )

    state = {
        "myPos": 0,
        "numofplayers": [18, 18, 12, 18],
        "curRank": "A",
        "_mid_feed_P": ["Straight", "Pair"],
        "handCards": hand,
    }
    rec = recommend_main_attack_lead(
        engine, state, card_mask, hand, "A", "stage_2",
    )
    assert rec is not None
    assert rec["type"] == "Straight"
    assert rec.get("intent") == "main_feed_mid_p"


def test_assist_stage2_mid_feed_p_intent(monkeypatch):
    """助攻 stage_2：_mid_feed_P 命中 plan 时 intent=assist_feed_mid_p。"""
    from src.v.nn.stage_assist_feed import recommend_assist_lead

    hand = ["C3", "D4", "H5", "S6", "C7"] + ["D8"] * 12
    hand = hand[:18]
    card_mask = {c: (-1, 0.0, 1) for c in hand}

    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = {0: "straight"}
    engine._group_members = {0: hand[:5], -1: hand[5:]}
    engine._current_role = "助攻"

    def _fake_feed(*_args, **_kwargs):
        return {
            "type": "Straight",
            "rank": "3",
            "cards": hand[:5],
            "intent": "main_feed_teammate_Straight",
        }

    monkeypatch.setattr(
        "src.v.nn.stage_main_attack_lead._try_feed_from_groups",
        _fake_feed,
    )

    state = {
        "myPos": 0,
        "numofplayers": [18, 18, 12, 18],
        "curRank": "A",
        "_mid_feed_P": ["Straight"],
        "handCards": hand,
    }
    rec = recommend_assist_lead(
        engine, state, card_mask, hand, "A", "stage_2", teammate_pos=2,
    )
    assert rec is not None
    assert rec["type"] == "Straight"
    assert rec.get("intent") == "assist_feed_mid_p"
