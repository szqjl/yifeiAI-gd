# -*- coding: utf-8 -*-
"""GUA-082: 回退路径 _heuristic_select R12 — 有自然单张 K 时禁止拆对 9 出 S9。"""
import pytest

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _step64_engine_and_state():
    """回放 20260628091703972753 步 64 构造态（9 张，curRank=8）。"""
    card_mask = {
        "S9": (1, 0.0, 2),
        "D9": (1, 0.0, 2),
        "SQ": (2, 0.0, 2),
        "HQ": (2, 0.0, 2),
        "CK": (-1, 0.0, 1),
        "SA": (0, 0.0, 3),
        "CA": (0, 0.0, 3),
        "HA": (0, 0.0, 3),
        "H8": (-1, 0.0, 1),
    }
    group_type_map = {0: "bomb", 1: "pair", 2: "pair"}
    hand = list(card_mask.keys())
    engine = UltimateWinRateEngineV7(player_id=2)
    engine._card_mask = card_mask
    engine._group_type_map = group_type_map
    engine._group_members = {}
    gs = {
        "myPos": 2,
        "curPos": 1,
        "greaterPos": 1,
        "greaterAction": ["Single", "6", ["C6"]],
        "handCards": hand,
        "curRank": "8",
        "numofplayers": [9, 9, 9, 9],
    }
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "9", ["S9"]],
        ["Single", "9", ["D9"]],
        ["Single", "K", ["CK"]],
    ]
    return engine, gs, action_list


class TestGua082HeuristicR12:
    def test_has_natural_single_ck_not_wild(self):
        engine, gs, _ = _step64_engine_and_state()
        assert engine._has_any_natural_single(gs["handCards"], "8") is True

    def test_single_breaks_pair_under_r12_for_s9_not_ck(self):
        engine, gs, action_list = _step64_engine_and_state()
        hand = gs["handCards"]
        assert engine._single_breaks_pair_under_r12(action_list[1], hand, "8") is True
        assert engine._single_breaks_pair_under_r12(action_list[3], hand, "8") is False

    def test_heuristic_picks_ck_not_pair_break_nine(self):
        engine, gs, action_list = _step64_engine_and_state()
        idx = engine._heuristic_select(gs, action_list)
        chosen = action_list[idx]
        assert chosen[0] == "Single"
        assert chosen[2] == ["CK"]

    def test_decide_fallback_picks_ck(self):
        engine, gs, action_list = _step64_engine_and_state()
        engine.model = None
        gs["actionList"] = action_list
        idx = engine.decide(gs)
        chosen = action_list[idx]
        assert chosen[0] == "Single"
        assert chosen[2] == ["CK"]

    def test_group_consistent_rejects_single_from_pair(self):
        engine, gs, action_list = _step64_engine_and_state()
        idx = engine._heuristic_select(gs, action_list)
        assert action_list[idx][2] != ["S9"]
        assert action_list[idx][2] != ["D9"]
