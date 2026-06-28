# -*- coding: utf-8 -*-
"""v7 录牌：actionList 小列表时写入 context 抽样。"""
import pytest

from src.communication.v7_game_recorder import (
    ACTION_LIST_CONTEXT_SAMPLE_MAX,
    decision_context_from_act,
    summarize_action_list_for_context,
)


class TestSummarizeActionList:
    def test_empty(self):
        assert summarize_action_list_for_context([]) == []
        assert summarize_action_list_for_context(None) == []

    def test_pass_and_pair(self):
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Pair", "A", ["SA", "CA"]],
        ]
        sample = summarize_action_list_for_context(action_list)
        assert len(sample) == 2
        assert sample[0]["type"] == "PASS"
        assert sample[1]["type"] == "Pair"
        assert sample[1]["rank"] == "A"
        assert set(sample[1]["cards"]) == {"SA", "CA"}


class TestDecisionContextFromAct:
    def test_includes_sample_when_small(self):
        data = {
            "myPos": 2,
            "curPos": 2,
            "greaterPos": 3,
            "handCards": ["SA", "CA", "H3"],
            "actionList": [
                ["PASS", "PASS", "PASS"],
                ["Pair", "A", ["SA", "CA"]],
            ],
            "curRank": "2",
            "stage": "play",
        }
        ctx = decision_context_from_act(data, player_id=2)
        assert ctx["actionList_size"] == 2
        assert "actionList_sample" in ctx
        assert ctx["actionList_sample"][1]["type"] == "Pair"

    def test_omits_sample_when_large(self):
        n = ACTION_LIST_CONTEXT_SAMPLE_MAX + 1
        data = {
            "myPos": 0,
            "actionList": [["Single", str(i), [f"S{i}"]] for i in range(n)],
            "handCards": ["S3"],
        }
        ctx = decision_context_from_act(data, player_id=0)
        assert ctx["actionList_size"] == n
        assert "actionList_sample" not in ctx
