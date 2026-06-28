# -*- coding: utf-8 -*-
"""GUA-075 主路径 R12：有自然单张时跟单不推荐/不校验通过拆普通对子出单。"""
import pytest

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _step23_engine():
    """回放 20260628091707150272 步 23 圈况（简化手牌结构）。"""
    card_mask = {
        "DJ": (-1, 0.0, 1),
        "D5": (-1, 0.0, 1),
        "C6": (0, 0.0, 2),
        "D6": (0, 0.0, 2),
        "HT": (1, 0.0, 2),
        "DT": (1, 0.0, 2),
        "SQ": (2, 0.0, 2),
        "HQ": (2, 0.0, 2),
    }
    group_type_map = {0: "pair", 1: "pair", 2: "pair"}
    hand = list(card_mask.keys())
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = group_type_map
    engine._group_members = {}
    return engine, hand


class TestGua075MinPressR12:
    def test_natural_single_beats_pair_break_for_min_press(self):
        engine, hand = _step23_engine()
        gs = {
            "myPos": 0,
            "curPos": 3,
            "greaterPos": 3,
            "greaterAction": ["Single", "7", ["D7"]],
            "handCards": hand,
            "curRank": "5",
        }
        rec = engine._recommend_min_press_impl(
            gs, engine._card_mask, gs["greaterAction"], "Single", hand, "5"
        )
        assert rec is not None
        assert rec["type"] == "Single"
        assert rec["cards"] == ["DJ"]
        assert rec["rank"] == "J"

    def test_no_natural_single_allows_pair_break(self):
        card_mask = {
            "HT": (0, 0.0, 2),
            "DT": (0, 0.0, 2),
            "C6": (1, 0.0, 2),
            "D6": (1, 0.0, 2),
        }
        group_type_map = {0: "pair", 1: "pair"}
        hand = list(card_mask.keys())
        engine = UltimateWinRateEngineV7(player_id=0)
        engine._card_mask = card_mask
        engine._group_type_map = group_type_map
        gs = {
            "handCards": hand,
            "curRank": "5",
        }
        assert engine._has_any_natural_single(hand, "5") is False
        rec = engine._recommend_min_press_impl(
            gs,
            card_mask,
            ["Single", "7", ["D7"]],
            "Single",
            hand,
            "5",
        )
        assert rec is not None
        assert rec["cards"][0] in ("HT", "DT")

    def test_natural_single_cannot_beat_returns_none_not_pair_break(self):
        """仅有小于对手的散牌时，R12 禁止拆对凑压 → 无推荐（PASS/改炸）。"""
        card_mask = {
            "D3": (-1, 0.0, 1),
            "HT": (0, 0.0, 2),
            "DT": (0, 0.0, 2),
        }
        hand = list(card_mask.keys())
        engine = UltimateWinRateEngineV7(player_id=0)
        engine._card_mask = card_mask
        engine._group_type_map = {0: "pair"}
        rec = engine._recommend_min_press_impl(
            {"handCards": hand, "curRank": "5"},
            card_mask,
            ["Single", "7", ["D7"]],
            "Single",
            hand,
            "5",
        )
        assert rec is None


class TestGua075QuickGuardR12:
    def test_quick_guard_rejects_pair_break_single(self):
        engine, hand = _step23_engine()
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Single", "J", ["DJ"]],
            ["Single", "T", ["HT"]],
        ]
        gs = {
            "myPos": 0,
            "curPos": 3,
            "greaterPos": 3,
            "greaterAction": ["Single", "7", ["D7"]],
            "handCards": hand,
            "curRank": "5",
        }
        assert engine._quick_guard_validate(1, action_list, gs) is True
        assert engine._quick_guard_validate(2, action_list, gs) is False

    def test_recommend_play_main_path_picks_j_not_t(self):
        engine, hand = _step23_engine()
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Single", "J", ["DJ"]],
            ["Single", "5", ["D5"]],
            ["Single", "T", ["HT"]],
        ]
        gs = {
            "myPos": 0,
            "curPos": 3,
            "greaterPos": 3,
            "greaterAction": ["Single", "7", ["D7"]],
            "handCards": hand,
            "curRank": "5",
        }
        rec = engine._recommend_play(gs, action_list)
        assert rec["cards"] == ["DJ"]
        idx = engine._match_actionList(rec, action_list)
        assert idx == 1
        assert engine._quick_guard_validate(idx, action_list, gs) is True
