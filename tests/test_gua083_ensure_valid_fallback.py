# -*- coding: utf-8 -*-
"""GUA-083：推荐存在但 _ensure_valid 失败时 return None，勿误走「无同型 PASS」。"""
import pytest

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _lower_block_engine():
    """卡下家：下家出 Pair/K，手牌有 Pair/A（步 53 简化）。"""
    card_mask = {
        "SA": (0, 0.0, 2),
        "CA": (0, 0.0, 2),
        "H3": (-1, 0.0, 1),
    }
    group_type_map = {0: "pair"}
    hand = list(card_mask.keys())
    engine = UltimateWinRateEngineV7(player_id=2)
    engine._card_mask = card_mask
    engine._group_type_map = group_type_map
    engine._group_members = {}
    gs = {
        "myPos": 2,
        "curPos": 2,
        "greaterPos": 3,
        "greaterAction": ["Pair", "K", ["SK", "CK"]],
        "handCards": hand,
        "curRank": "2",
    }
    return engine, gs, hand


class TestGua083EnsureValidFallback:
    def test_lower_block_pair_a_in_action_list(self):
        engine, gs, _hand = _lower_block_engine()
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Pair", "A", ["SA", "CA"]],
        ]
        rec = engine._recommend_play(gs, action_list)
        assert rec is not None
        assert rec["type"] == "Pair"
        assert rec["rank"] == "A"

    def test_lower_block_mismatch_returns_none_not_pass(self):
        """impl 有 Pair/A 但 actionList 无同型 → None（回退），非 synthetic PASS。"""
        engine, gs, _hand = _lower_block_engine()
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Bomb", "8", ["S8", "H8", "C8", "D8"]],
        ]
        rec = engine._recommend_play(gs, action_list)
        assert rec is None

    def test_upper_no_same_type_still_passes_via_r11(self):
        """impl 真无同型 → 仍走 R11 让道 PASS，行为不变。"""
        card_mask = {
            "S3": (0, 0.0, 2),
            "H3": (0, 0.0, 2),
        }
        hand = list(card_mask.keys())
        engine = UltimateWinRateEngineV7(player_id=0)
        engine._card_mask = card_mask
        engine._group_type_map = {0: "pair"}
        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 3,
            "greaterAction": ["Pair", "K", ["SK", "CK"]],
            "handCards": hand,
            "curRank": "2",
        }
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Pair", "3", ["S3", "H3"]],
        ]
        rec = engine._recommend_play(gs, action_list)
        assert rec is not None
        assert rec["type"] == "PASS"
