# -*- coding: utf-8
"""GUA-027：trick_state 与 M3 被动 greater 重算回归。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from game_logic.trick_state import (
    TrickSequenceTracker,
    action_beats,
    leader_from_play_areas,
    resolve_effective_greater,
    resolve_for_recorded_action,
)
from m.m3 import M3DecisionEngine


@pytest.mark.unit
def test_action_beats_single_with_level():
    assert action_beats(["Single", "A", ["SA"]], ["Single", "9", ["S9"]], "5") is True
    assert action_beats(["Single", "9", ["S9"]], ["Single", "A", ["SA"]], "5") is False


@pytest.mark.unit
def test_leader_from_play_areas_picks_max():
    public = [
        {"rest": 20, "playArea": ["Single", "A", ["SA"]]},
        {"rest": 18, "playArea": ["Single", "9", ["S9"]]},
        {"rest": 22, "playArea": None},
        {"rest": 21, "playArea": None},
    ]
    pos, act = leader_from_play_areas(public, "5")
    assert pos == 0
    assert act[1] == "A"


@pytest.mark.unit
def test_resolve_effective_greater_prefers_play_area_over_wrong_msg():
    resolved = resolve_effective_greater(
        cur_pos=1,
        cur_action=["Single", "9", ["S9"]],
        greater_pos=1,
        greater_action=["Single", "9", ["S9"]],
        public_info=[
            {"rest": 20, "playArea": ["Single", "A", ["SA"]]},
            {"rest": 18, "playArea": ["Single", "9", ["S9"]]},
            {"rest": 22, "playArea": None},
            {"rest": 21, "playArea": None},
        ],
        cur_rank="5",
    )
    assert resolved["greater_pos"] == 0
    assert resolved["greater_action"][1] == "A"
    assert resolved["beat_action"][1] == "A"
    assert resolved["corrected"] is True
    assert resolved["source"] == "playArea"


@pytest.mark.unit
def test_trick_tracker_recomputes_after_failed_single():
    tracker = TrickSequenceTracker("5")
    tracker.apply(0, ["Single", "A", ["SA"]])
    tracker.apply(1, ["Single", "9", ["S9"]])
    snap = tracker.snapshot()
    assert snap["greater_pos"] == 0
    assert snap["greater_action"][1] == "A"


@pytest.mark.unit
def test_resolve_for_recorded_action_uses_tracker_without_play_area():
    tracker = TrickSequenceTracker("5")
    tracker.apply(0, ["Single", "A", ["SA"]])
    action = {
        "cur_pos": 1,
        "cur_action": ["Single", "9", ["S9"]],
        "greater_pos": 1,
        "greater_action": ["Single", "9", ["S9"]],
        "context": {},
    }
    resolved = resolve_for_recorded_action(action, tracker)
    assert resolved["greater_pos"] == 0
    assert resolved["greater_action"][1] == "A"
    assert resolved["corrected"] is True


@pytest.mark.unit
def test_resolve_for_recorded_action_matches_when_cur_wins_trick():
    tracker = TrickSequenceTracker("5")
    tracker.apply(0, ["Single", "9", ["S9"]])
    action = {
        "cur_pos": 1,
        "cur_action": ["Single", "A", ["SA"]],
        "greater_pos": 1,
        "greater_action": ["Single", "A", ["SA"]],
        "context": {},
    }
    resolved = resolve_for_recorded_action(action, tracker)
    assert resolved["greater_pos"] == 1
    assert resolved["corrected"] is False


@pytest.mark.unit
def test_m3_passive_uses_action_rank_not_cards_list():
    """回归 GUA-024：curAction[1] 误写 [-1] 会 TypeError。"""
    engine = M3DecisionEngine(player_id=0)
    data = {
        "stage": "play",
        "type": "act",
        "greaterPos": 1,
        "curPos": 1,
        "curRank": "2",
        "curAction": ["Single", "8", ["D8"]],
        "greaterAction": ["Single", "8", ["D8"]],
        "publicInfo": [
            {"rest": 20, "playArea": None},
            {"rest": 18, "playArea": ["Single", "8", ["D8"]]},
            {"rest": 22, "playArea": None},
            {"rest": 21, "playArea": None},
        ],
        "handCards": [
            "C2", "S3", "D3", "S4", "H4", "D4", "D4", "D5", "H6", "C6",
            "S7", "S7", "S8", "S8", "H8", "C8", "D9", "HT", "DT", "SJ",
            "HJ", "SQ", "HQ", "CK", "CA", "DA", "SB",
        ],
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["Single", "9", ["D9"]],
            ["Single", "T", ["HT"]],
            ["Single", "J", ["HJ"]],
            ["Single", "Q", ["HQ"]],
        ],
    }
    idx = engine.on_message(data)
    assert idx > 0
    assert data["actionList"][idx][0] == "Single"


@pytest.mark.unit
def test_m3_act_corrects_greater_before_passive_dispatch():
    engine = M3DecisionEngine(player_id=2)
    data = {
        "stage": "play",
        "type": "act",
        "greaterPos": 1,
        "curPos": 1,
        "curRank": "5",
        "curAction": ["Single", "9", ["S9"]],
        "greaterAction": ["Single", "9", ["S9"]],
        "publicInfo": [
            {"rest": 20, "playArea": ["Single", "A", ["SA"]]},
            {"rest": 18, "playArea": ["Single", "9", ["S9"]]},
            {"rest": 22, "playArea": None},
            {"rest": 21, "playArea": None},
        ],
        "handCards": ["SA", "DA", "CA", "HK", "SK"] + ["S3"] * 22,
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["Single", "K", ["HK"]],
            ["Single", "A", ["SA"]],
        ],
    }
    engine.on_message(data)
    assert data["greaterPos"] == 0
    assert data["greaterAction"][1] == "A"
    assert data["_beat_action"][1] == "A"
