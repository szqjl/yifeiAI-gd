# -*- coding: utf-8 -*-
"""GUA-117：Layer0 guard 117-2a–2g / 117-7d / 117-7e 构造态。"""

from src.v.nn.guards.v7_guards import filter_action_list, get_action_type


def _gs(**kwargs):
    base = {
        "myPos": 0,
        "curRank": "2",
        "numofplayers": [10, 12, 8, 11],
        "_role": "助攻",
        "_current_stage": "stage_1",
    }
    base.update(kwargs)
    return base


def _types_kept(game_state, action_list):
    filtered, _ = filter_action_list({**game_state, "actionList": action_list})
    return [get_action_type(a) for a in filtered]


def test_b1_blocks_bomb_over_teammate():
    actions = [
        ["PASS", "PASS", "PASS"],
        ["Bomb", "8", ["S8", "H8", "C8", "D8"]],
        ["Single", "5", ["S5"]],
    ]
    gs = _gs(greaterPos=2, greaterAction=["Pair", "9", ["S9", "H9"]])
    types = _types_kept(gs, actions)
    assert "Bomb" not in types
    assert "Single" in types


def test_b2_blocks_straight_on_lead():
    actions = [
        ["PASS", "PASS", "PASS"],
        ["Straight", "3", ["S3", "S4", "S5", "S6", "S7"]],
        ["Pair", "3", ["S3", "H3"]],
    ]
    gs = _gs(greaterPos=0, greaterAction=["PASS", "PASS", "PASS"])
    types = _types_kept(gs, actions)
    assert "Straight" not in types
    assert "Pair" in types


def test_b6_rest4_only_pair_single():
    actions = [
        ["PASS", "PASS", "PASS"],
        ["Trips", "6", ["S6", "H6", "C6"]],
        ["Pair", "4", ["S4", "H4"]],
        ["Single", "5", ["S5"]],
    ]
    gs = _gs(
        curPos=0,
        greaterPos=0,
        numofplayers=[10, 12, 4, 11],
    )
    types = _types_kept(gs, actions)
    assert "Trips" not in types
    assert "Pair" in types or "Single" in types


def test_b2g_yield_three_with_two_over_teammate():
    actions = [
        ["PASS", "PASS", "PASS"],
        ["ThreeWithTwo", "6", ["S6", "H6", "C6", "S4", "H4"]],
    ]
    gs = _gs(greaterPos=2, greaterAction=["Pair", "7", ["S7", "H7"]])
    types = _types_kept(gs, actions)
    assert types == ["PASS"]


def test_b4_blocks_breaking_core_straight_when_not_pressing():
    actions = [
        ["PASS", "PASS", "PASS"],
        ["Single", "3", ["S3"]],
    ]
    gs = _gs(
        greaterPos=0,
        greaterAction=["PASS", "PASS", "PASS"],
        _card_mask={"S3": (0, 1.0, 5), "S4": (0, 1.0, 5)},
        _group_gid_type_map={0: "straight"},
    )
    types = _types_kept(gs, actions)
    assert "Single" not in types


def test_non_assist_role_unfiltered_b2():
    actions = [
        ["PASS", "PASS", "PASS"],
        ["Straight", "3", ["S3", "S4", "S5", "S6", "S7"]],
    ]
    gs = _gs(_role="主攻", greaterPos=0)
    types = _types_kept(gs, actions)
    assert "Straight" in types


def test_b3_blocks_unfamiliar_shape_without_teammate_history():
    actions = [
        ["PASS", "PASS", "PASS"],
        ["ThreeWithTwo", "6", ["S6", "H6", "C6", "S4", "H4"]],
        ["Pair", "3", ["S3", "H3"]],
    ]
    gs = _gs(greaterPos=0, _memory_tracker=type("T", (), {"play_history": []})())
    types = _types_kept(gs, actions)
    assert "ThreeWithTwo" not in types
    assert "Pair" in types


def test_b5_blocks_active_bomb_without_enemy_pressure():
    actions = [
        ["PASS", "PASS", "PASS"],
        ["Bomb", "8", ["S8", "H8", "C8", "D8"]],
        ["Pair", "3", ["S3", "H3"]],
    ]
    gs = _gs(
        greaterPos=0,
        greaterAction=["PASS", "PASS", "PASS"],
        _phase_relation={"enemy_bomb_risk_max": 0.1},
    )
    types = _types_kept(gs, actions)
    assert "Bomb" not in types
    assert "Pair" in types
