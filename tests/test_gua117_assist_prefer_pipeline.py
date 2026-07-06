# -*- coding: utf-8 -*-
"""GUA-117 / Q1：assist_prefer 单一真源与 Q2/R09/feed 共用。"""

from src.v.nn.assist_prefer_table import assist_is_close, assist_prefer_for
from src.v.nn.endgame.endgame_decide import pick_assist_feed_by_prefer
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.guards.v7_guards import _rule_r09_feed_teammate_5


class TestAssistPreferTable:
    def test_rest_3_unchanged(self):
        assert assist_prefer_for(3) == ["Trips", "Pair", "Single"]

    def test_rest_4_pair_single(self):
        assert assist_prefer_for(4) == ["Pair", "Single"]

    def test_rest_5_straight_twt_single(self):
        assert assist_prefer_for(5) == ["Straight", "ThreeWithTwo", "Single"]

    def test_rest_6_empty(self):
        assert assist_prefer_for(6) == []
        assert assist_prefer_for(10) == []

    def test_is_close_through_5(self):
        assert assist_is_close(5) is True
        assert assist_is_close(6) is False


class TestPreprocessorDelegatesTable:
    def test_assist_prefer_for_delegates(self):
        pp = EndgamePreprocessor()
        assert pp._assist_prefer_for(4) == ["Pair", "Single"]
        assert pp._assist_prefer_for(8) == []


class TestPickAssistFeedByPrefer:
    def test_rest_4_filters_pair_and_single(self):
        action_list = [
            ["PASS"],
            ["Straight", "6", ["S3", "H4", "D5", "C6", "S7"]],
            ["Pair", "3", ["S3", "H3"]],
            ["Single", "4", ["S4"]],
        ]
        game_state = {"handCards": ["S3", "H3", "S4", "D9"]}
        picked = pick_assist_feed_by_prefer(
            game_state, action_list, assist_prefer_for(4),
        )
        assert picked is not None
        idx, _ = picked
        assert idx in (2, 3)

    def test_empty_prefer_returns_none(self):
        assert pick_assist_feed_by_prefer({}, [["PASS"]], []) is None


class TestR09UsesPreferTable:
    def test_teammate_5_keeps_single_not_pair(self):
        actions = [
            ["PASS"],
            ["Single", "A", ["SA"]],
            ["Pair", "2", ["S2", "H2"]],
            ["Trips", "3", ["S3", "H3", "D3"]],
        ]
        result = _rule_r09_feed_teammate_5(
            actions, cur_pos=0, my_pos=0, numofplayers=[20, 20, 5, 20],
        )
        assert 0 in result
        assert 1 in result
        assert 2 not in result
        assert 3 not in result
