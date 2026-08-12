# -*- coding: utf-8 -*-
"""EndgameSolver 求解器单元测试。"""
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.v.nn.endgame.endgame_solver import (
    enumerate_legal_plays, beats, EndgameSolver,
    _platform_action,
)
from src.v.nn.guards.v7_guards import get_action_type


# ═══════════════ 动作生成 ═══════════════

def test_single_and_pair_and_trips():
    hand = ["S3", "H3", "D3", "C5"]
    plays = enumerate_legal_plays(hand, "2")
    types = {get_action_type(p) for p in plays}
    assert "Single" in types
    assert "Pair" in types
    assert "Trips" in types
    assert len(plays) >= 5  # 3 单张 + 1 对 + 1 三张


def test_bomb_detected():
    hand = ["S9", "H9", "D9", "C9"]
    plays = enumerate_legal_plays(hand, "2")
    types = {get_action_type(p) for p in plays}
    assert "Bomb" in types


def test_straight_detected():
    hand = ["S3", "H4", "D5", "C6", "S7"]
    plays = enumerate_legal_plays(hand, "2")
    types = {get_action_type(p) for p in plays}
    assert "Straight" in types


def test_three_with_two_detected():
    hand = ["S3", "H3", "D3", "C5", "S5"]
    plays = enumerate_legal_plays(hand, "2")
    types = {get_action_type(p) for p in plays}
    assert "ThreeWithTwo" in types


def test_three_pair_detected():
    hand = ["S3", "H3", "D4", "C4", "S5", "H5"]
    plays = enumerate_legal_plays(hand, "2")
    types = {get_action_type(p) for p in plays}
    assert "ThreePair" in types


def test_two_trips_detected():
    hand = ["S3", "H3", "D3", "C4", "S4", "H4"]
    plays = enumerate_legal_plays(hand, "2")
    types = {get_action_type(p) for p in plays}
    assert "TwoTrips" in types


def test_straight_flush_detected():
    hand = ["S3", "S4", "S5", "S6", "S7"]
    plays = enumerate_legal_plays(hand, "2")
    types = {get_action_type(p) for p in plays}
    assert "StraightFlush" in types


def test_wild_pair_upgrade():
    # 逢人配 H2 与任意单张升对
    hand = ["S3", "H2"]
    cur_rank = "2"
    plays = enumerate_legal_plays(hand, cur_rank)
    types = {get_action_type(p) for p in plays}
    assert "Pair" in types
    assert "Single" in types


def test_beats():
    g = _platform_action("Single", ["HK"])
    p_hi = _platform_action("Single", ["HA"])
    p_lo = _platform_action("Single", ["H7"])
    assert beats(p_hi, g, "2") is True
    assert beats(p_lo, g, "2") is False
    assert beats(_platform_action("PASS", []), g, "2") is False
    # 自由领出
    assert beats(p_lo, ["PASS", "", []], "2") is True
    assert beats(p_lo, None, "2") is True


# ═══════════════ 搜索 ═══════════════

def test_solver_one_hand_clears():
    """自己只剩一手 → 求解器应出完这手。"""
    hands = [
        ["S3", "H3", "D3"],   # 席0 我
        ["S5", "H5", "D5", "C5"],
        ["S7", "H7", "D7"],   # 席2 队友
        ["S9", "H9", "D9", "C9"],
    ]
    solver = EndgameSolver(max_depth=4)
    act, _, nodes = solver.solve(hands, turn=0, cur_rank="2", my_seat=0)
    assert act is not None
    assert get_action_type(act) == "Trips"
    assert nodes > 0


def test_solver_pass_when_cannot_beat():
    """敌方出大 A，我方只有小牌 → 只能 PASS。"""
    hands = [
        ["S3", "H5"],                    # 席0 我（小牌）
        ["S9", "H9", "D9", "C9"],        # 席1 敌
        ["S7", "H7", "D7"],              # 席2 队友
        ["S9", "H9", "D9", "C9"],        # 席3 敌
    ]
    greater = _platform_action("Single", ["HA"])
    solver = EndgameSolver(max_depth=3)
    act, _, _ = solver.solve(
        hands, turn=0, cur_rank="2", greater=greater, my_seat=0,
    )
    assert act is not None
    assert act[0] == "PASS"


def test_solver_prefers_finish_now_over_single():
    """可一手清（对子）时，不应拆成单张。"""
    hands = [
        ["S3", "H3"],                    # 席0 我：一手对子
        ["S9", "H9", "D9", "C9"],
        ["S7", "H7", "D7"],              # 席2 队友
        ["S9", "H9", "D9", "C9"],
    ]
    solver = EndgameSolver(max_depth=4)
    act, _, _ = solver.solve(hands, turn=0, cur_rank="2", my_seat=0)
    assert act is not None
    assert get_action_type(act) == "Pair"


def test_solver_teammate_finish_aids_team():
    """我方价值：队友已接近出完时仍为我方有利。"""
    hands = [
        ["S5"],                          # 席0 我
        ["S9", "H9", "D9", "C9"],
        ["S7"],                          # 席2 队友（一手）
        ["S9", "H9", "D9", "C9"],
    ]
    solver = EndgameSolver(max_depth=3)
    act, _, _ = solver.solve(hands, turn=0, cur_rank="2", my_seat=0)
    # 我方队友剩 1 张 → 不应炸队友，也不应 PASS 放行敌方
    assert act is not None
