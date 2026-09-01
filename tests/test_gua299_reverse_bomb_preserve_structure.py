# -*- coding: utf-8 -*-
"""GUA-299：GUA-297 中局反炸不得「拆己组 SF+顺子」凑炸（保留结构）。

回归自 match 6a963f8f1b27100f38dc7248：V8 为「超强主攻」、初始组牌为
3-7 同花顺 + 7-J 顺子（最大去单化）。下家 player1 打 StraightFlush/3 后，
GUA-297 反炸逻辑把 3-7SF+7-J顺 重新拼成 4-8SF（broken=['StraightFlush','straight']），
留下 3(C3)/7(H7)/9(S9) 三个弱散单。

GUA-299 原则（同 GUA-296/288）：反炸只有在「不拆本方已组核心结构」时才采用；
若唯一能压对手炸的是拆核凑出的炸，则回退 PASS 保留 3-7SF+7-J顺 结构。
"""

import pytest

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
from src.v.nn.endgame.endgame_decide import _bomb_disrupts_core_group


def _engine():
    return UltimateWinRateEngineV7(player_id=0)


# ── 6a963f8f 场景：V8 已组 3-7SF + 7-J顺 + 炸Q，对手打 SF/3 ──
_BASE_STATE = {
    "myPos": 0,
    "greaterPos": 1,
    "curRank": "2",
    "greaterAction": ["StraightFlush", "3", ["H3", "H4", "H5", "H6", "H7"]],
    "actionList": [
        ["PASS", "PASS", ["PASS"]],
        ["StraightFlush", "4", ["C4", "C6", "C7", "C8", "H2"]],
        ["StraightFlush", "5", ["C5", "C6", "C7", "C8", "CT"]],
        ["StraightFlush", "6", ["C6", "C7", "C8", "C9", "CT"]],
        ["StraightFlush", "7", ["C7", "C8", "C9", "CT", "CJ"]],
    ],
    "_group_members": {
        1: ["C3", "C4", "H2", "C6", "C7"],   # StraightFlush(3-7)
        2: ["H7", "C8", "S9", "DT", "DJ"],   # straight(7-J)
        3: ["HQ", "HQ", "DQ", "CQ"],         # Bomb(Q)
    },
    "_group_gid_type_map": {1: "StraightFlush", 2: "straight", 3: "Bomb"},
}


def test_disrupting_sf_counter_detected():
    """4-8SF 反炸借用 SF+顺子核牌而未整组消耗 → 判为拆核。"""
    state = dict(_BASE_STATE)
    c1 = ["StraightFlush", "4", ["C4", "C6", "C7", "C8", "H2"]]
    assert _bomb_disrupts_core_group(state, c1) is True


def test_no_reverse_bomb_when_only_disrupting_counter():
    """对手 SF/3、唯一反炸候选拆 3-7SF+7-J顺 → 不反炸（保留结构）。"""
    engine = _engine()
    state = dict(_BASE_STATE)
    can = engine._can_reverse_bomb_higher(
        state,
        ["StraightFlush", "3", ["H3", "H4", "H5", "H6", "H7"]],
        "2",
    )
    assert can is False


def test_reverse_bomb_ok_with_preserving_standalone_bomb():
    """对手 Bomb/7、V8 持独立 5星 Bomb/6（整组消耗）→ 允许反炸（GUA-297 保住）。"""
    engine = _engine()
    state = {
        "myPos": 0,
        "greaterPos": 3,
        "curRank": "2",
        "greaterAction": ["Bomb", "7", ["S7", "C7", "H7", "S7"]],
        "actionList": [
            ["PASS", "PASS", ["PASS"]],
            ["Bomb", "6", ["C6", "C6", "H6", "S6", "S6"]],
        ],
        "_group_members": {5: ["C6", "C6", "H6", "S6", "S6"]},
        "_group_gid_type_map": {5: "Bomb"},
    }
    can = engine._can_reverse_bomb_higher(
        state, ["Bomb", "7", ["S7", "C7", "H7", "S7"]], "2"
    )
    assert can is True


def test_no_structure_info_falls_back_to_allowing():
    """无 _group_members（结构未知）→ 不阻断，保持 GUA-297 原行为（可反炸）。"""
    engine = _engine()
    state = dict(_BASE_STATE)
    state.pop("_group_members")
    state.pop("_group_gid_type_map")
    can = engine._can_reverse_bomb_higher(
        state,
        ["StraightFlush", "3", ["H3", "H4", "H5", "H6", "H7"]],
        "2",
    )
    assert can is True


def test_no_higher_reverse_bomb_still_lets_pass():
    """对手 Bomb/A、actionList 无更高保留炸 → 无更高炸让道。"""
    engine = _engine()
    state = {
        "myPos": 0,
        "greaterPos": 3,
        "curRank": "2",
        "greaterAction": ["Bomb", "A", ["CA", "HA", "DA", "SA"]],
        "actionList": [["PASS", "PASS", ["PASS"]]],
        "_group_members": {5: ["C6", "C6", "H6", "S6", "S6"]},
        "_group_gid_type_map": {5: "Bomb"},
    }
    can = engine._can_reverse_bomb_higher(
        state, ["Bomb", "A", ["CA", "HA", "DA", "SA"]], "2"
    )
    assert can is False
