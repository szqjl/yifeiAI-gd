# -*- coding: utf-8 -*-
from types import SimpleNamespace

import pytest


def _full_game_data():
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "3", ["S3"]],
    ]
    replay_state = {
        "actionList": action_list,
        "stage": "play",
        "handCards": ["S3", "H4"],
        "myPos": 0,
        "curPos": -1,
        "greaterPos": -1,
        "greaterAction": ["PASS", "PASS", "PASS"],
        "publicInfo": [{"rest": 2}, {"rest": 4}, {"rest": 1}, {"rest": 5}],
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
    }
    return {
        "game_id": "abc_full_001",
        "player_id": 0,
        "actions": [
            {
                "cur_pos": 0,
                "cur_action": action_list[1],
                "greater_pos": -1,
                "greater_action": ["PASS", "PASS", "PASS"],
            }
        ],
        "my_decisions": [
            {
                "timestamp": "2026-07-19T12:00:00",
                "action_index": 1,
                "action": action_list[1],
                "score": None,
                "layer": "GUA-075推荐",
                "candidates_count": 2,
                "context": {
                    "stage": "play",
                    "source": "act",
                    "actionList_size": 2,
                    "handCards": ["S3", "H4"],
                    "curRank": "2",
                    "replay_schema": "yf-replay-decision-v1",
                    "replay_state": replay_state,
                },
            }
        ],
    }


class _FakeReplayEngine:
    def __init__(self, player_id=0, use_grouping_engine=True):
        self.player_id = player_id
        self._decision_tracer = None
        self._last_decision_layer = None
        self._last_heuristic_scores = []
        self._active_replay_trace = None
        self._current_role = "主攻"
        self._tracker = SimpleNamespace(hand_counts=[2, 4, 1, 5])

    def on_game_start(self, my_pos=None, game_id=None):
        return None

    def decide(self, state):
        self._active_replay_trace = state["_replay_trace"]
        self._last_decision_layer = "GUA-075推荐"
        state["_belief"] = {"hand_counts": {0: 2, 1: 4, 2: 1, 3: 5}}
        state["_phase_relation"] = {"sprint_fire_ready": True}
        state["_current_stage"] = "stage_3"
        state["_card_mask"] = {"S3": [0, 1.0, 1]}
        state["_group_gid_type_map"] = {0: "Single"}
        state["_replay_guard_trace"].extend([
            {"rule_id": "R10", "removed_indices": [], "removed_count": 0},
            {
                "rule_id": "final_order",
                "removed_indices": [],
                "removed_count": 0,
                "kept_indices": [0, 1],
                "order_indices": [0, 1],
            },
        ])
        state["_replay_trace"]["pipeline"] = [
            {"stage": "input", "candidate_count": 2},
            {
                "stage": "recommendation",
                "gua_id": "GUA-075",
                "recommendation": {"type": "Single", "rank": "3", "cards": ["S3"]},
            },
            {"stage": "candidate_order", "actions": list(state["actionList"])},
            {"stage": "heuristic_scores", "scores": [(1, 100.0), (0, 0.0)]},
            {
                "stage": "final",
                "actIndex": 1,
                "chosen_action": state["actionList"][1],
                "layer": "GUA-075推荐",
            },
        ]
        self._last_heuristic_scores = [(1, 100.0), (0, 0.0)]
        return 1

    def _heuristic_select(self, state, action_list):
        self._last_heuristic_scores = [(1, 100.0), (0, 0.0)]
        return 1


@pytest.mark.parametrize(
    "module_name",
    ["src.communication.v7_game_recorder", "src.communication.v8_game_recorder"],
)
def test_replay_state_records_complete_action_list(module_name):
    module = __import__(module_name, fromlist=["decision_context_from_act"])
    action_list = [["Single", str(index), [f"S{index}"]] for index in range(12)]
    context = module.decision_context_from_act(
        {
            "actionList": action_list,
            "stage": "play",
            "handCards": ["S2"],
            "myPos": 0,
            "greaterAction": ["PASS", "PASS", "PASS"],
            "publicInfo": [{"rest": 1}] * 4,
        },
        0,
    )

    assert context["replay_schema"] == "yf-replay-decision-v1"
    assert context["replay_state"]["actionList"] == action_list
    assert len(context["replay_state"]["actionList"]) == 12
    assert "actionList_sample" not in context


def test_replay_analyzer_builds_full_abc_report(tmp_path):
    from src.v.nn.tracing.replay_analysis import (
        ReplayDecisionAnalyzer,
        format_analysis_sections,
    )

    analyzer = ReplayDecisionAnalyzer(
        repo_root=tmp_path,
        engine_factory=_FakeReplayEngine,
    )
    result = analyzer.analyze(_full_game_data(), 1)

    assert result["coverage"] == "full"
    assert result["A"]["actual_actIndex"] == 1
    assert result["B"]["offline_matches_actual"] is True
    assert result["B"]["offline_layer"] == "GUA-075推荐"
    assert result["C"]["memory_snapshot"]["teammate_hands_est"] == 1
    assert result["C"]["memory_snapshot"]["opponent_sprint_capable"] is True
    assert result["C"]["candidate_rows"][0]["original_index"] == 1
    assert result["C"]["candidate_rows"][0]["heuristic_score"] == 100.0
    assert result["C"]["candidate_rows"][0]["score_source"] == "actual_path"
    assert any(item["gua_id"] == "GUA-075" for item in result["C"]["gua_traces"])

    sections = format_analysis_sections(result)
    assert set(sections) == {"A 实战事实", "B 决策路径", "C 深度分析"}
    assert "实际 actIndex: 1" in sections["A 实战事实"]
    assert "与实战一致: True" in sections["B 决策路径"]
    assert "候选逐层去留与排序" in sections["C 深度分析"]


def test_replay_analyzer_marks_legacy_records_limited(tmp_path):
    from src.v.nn.tracing.replay_analysis import ReplayDecisionAnalyzer

    game_data = _full_game_data()
    context = game_data["my_decisions"][0]["context"]
    context.pop("replay_schema")
    context.pop("replay_state")
    context["actionList_sample"] = [
        {"type": "Single", "rank": "3", "cards": ["S3"]}
    ]

    result = ReplayDecisionAnalyzer(
        repo_root=tmp_path,
        engine_factory=_FakeReplayEngine,
    ).analyze(game_data, 1)

    assert result["coverage"] == "legacy_limited"
    assert result["B"]["offline_actIndex"] is None
    assert result["warnings"]
    assert len(result["C"]["candidate_rows"]) == 1


def test_guard_trace_records_candidate_removal():
    from src.v.nn.guards.v7_guards import filter_action_list

    state = {
        "myPos": 0,
        "curPos": -1,
        "greaterPos": -1,
        "greaterAction": ["PASS", "PASS", "PASS"],
        "curRank": "2",
        "handCards": ["S3", "S4", "H4", "D4", "C4"],
        "actionList": [
            ["Bomb", "4", ["S4", "H4", "D4", "C4"]],
            ["Single", "3", ["S3"]],
        ],
        "_replay_guard_trace": [],
    }

    filtered, action_map = filter_action_list(state)

    assert filtered == [["Single", "3", ["S3"]]]
    assert action_map == [1]
    r10 = next(
        item for item in state["_replay_guard_trace"] if item["rule_id"] == "R10"
    )
    assert r10["removed_indices"] == [0]
    assert state["_replay_guard_trace"][-1]["rule_id"] == "final_order"


def test_realtime_decision_trace_is_disabled_by_default(monkeypatch):
    from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

    monkeypatch.delenv("V7_ENABLE_DECISION_TRACE", raising=False)
    assert UltimateWinRateEngineV7._is_decision_trace_enabled() is False
    monkeypatch.setenv("V7_ENABLE_DECISION_TRACE", "1")
    assert UltimateWinRateEngineV7._is_decision_trace_enabled() is True
