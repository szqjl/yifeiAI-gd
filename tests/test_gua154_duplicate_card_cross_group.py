# -*- coding: utf-8 -*-
"""GUA-154：同名牌跨组归属不得让拆核判定反转。"""

from src.v.nn.features.grouping_engine import GroupingPlan
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


FULL_STRAIGHT_FLUSH = [
    "StraightFlush", "6", ["C2", "C3", "C4", "H7", "C6"],
]
TRIPS_THREE = ["Trips", "3", ["C3", "D3", "C3"]]


def _anchor_engine():
    plan = GroupingPlan(cur_rank="7")
    plan.straight_flushes = [["C2", "C3", "C4", "H7", "C6"]]
    plan.straights = [["S7", "S8", "S9", "HT", "HJ"]]
    plan.pairs = [["C9", "D9"]]
    plan.three_pairs = [[
        ["S2", "D2"],
        ["D3", "C3"],
        ["H4", "S4"],
    ]]
    plan.singles = ["SB", "SJ"]
    card_mask, group_type_map, group_members = plan.to_card_mask()

    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = group_type_map
    engine._group_members = group_members
    engine._current_role = "主攻"
    return engine, card_mask, group_type_map, group_members


def _game_state():
    return {
        "myPos": 0,
        "curPos": -1,
        "greaterPos": -1,
        "greaterAction": ["PASS", "PASS", "PASS"],
        "handCards": [
            "S2", "C2", "D2", "C3", "D3", "C3", "H4", "S4", "C4",
            "C6", "H7", "S7", "S8", "S9", "C9", "D9", "HT", "HJ",
            "SJ", "SB",
        ],
        "curRank": "7",
        "numofplayers": [20, 24, 24, 25],
        "publicInfo": [
            {"rest": 20}, {"rest": 24}, {"rest": 24}, {"rest": 25},
        ],
    }


def test_card_memberships_preserve_both_c3_instances():
    engine, card_mask, _, group_members = _anchor_engine()

    memberships = engine._build_card_memberships(group_members)

    assert card_mask["C3"][0] == 4
    assert memberships["C3"] == {0: 1, 4: 1}


def test_full_straight_flush_selects_its_c3_instance_without_breaking_core():
    engine, card_mask, group_type_map, group_members = _anchor_engine()

    broken_type = engine._get_broken_core_type(
        FULL_STRAIGHT_FLUSH,
        card_mask,
        group_type_map,
        group_members,
    )

    assert broken_type is None
    assert not engine._action_breaks_core(
        FULL_STRAIGHT_FLUSH,
        card_mask,
        group_members,
        group_type_map,
    )


def test_trips_three_must_consume_both_c3_instances_and_break_straight_flush():
    engine, card_mask, group_type_map, group_members = _anchor_engine()

    broken_type = engine._get_broken_core_type(
        TRIPS_THREE,
        card_mask,
        group_type_map,
        group_members,
    )

    assert broken_type == "StraightFlush"
    assert engine._action_breaks_core(
        TRIPS_THREE,
        card_mask,
        group_members,
        group_type_map,
    )


def test_main_attack_filter_keeps_straight_flush_and_removes_trips_three():
    engine, _, _, _ = _anchor_engine()

    filtered, filter_map = engine._group_consistency_filter(
        [TRIPS_THREE, FULL_STRAIGHT_FLUSH],
        _game_state(),
    )

    assert filtered == [FULL_STRAIGHT_FLUSH]
    assert filter_map == [-1, 0]


def test_heuristic_scores_full_straight_flush_above_trips_three():
    engine, _, _, _ = _anchor_engine()
    actions = [TRIPS_THREE, FULL_STRAIGHT_FLUSH]

    selected_index = engine._heuristic_select(_game_state(), actions)
    scores = dict(engine._last_heuristic_scores)

    assert selected_index == 1
    assert scores[1] > scores[0]


def test_trace_records_selected_action_multi_instance_allocation():
    engine, _, _, _ = _anchor_engine()
    engine._active_replay_trace = {}
    engine._decision_tracer = None

    selected_index = engine._trace_finalize(0, [TRIPS_THREE])

    assert selected_index == 0
    trace_items = engine._active_replay_trace["pipeline"]
    allocation_trace = next(
        item for item in trace_items
        if item["stage"] == "gua154_memberships"
    )
    assert allocation_trace["memberships"]["C3"] == {0: 1, 4: 1}
    assert allocation_trace["allocation"] == {0: 1, 4: 2}
    assert allocation_trace["broken_types"] == ["StraightFlush"]
