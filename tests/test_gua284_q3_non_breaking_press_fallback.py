# -*- coding: utf-8 -*-
"""
GUA-284: Q3 最省压牌拆核 → 继续试次省散牌，勿直接 PASS

背景（match=6a8e9548，V8=player2，greater=Single/J）：
  最省压牌 Q（HQ）拆 pair_in_three_with_two 核心 → 旧逻辑直接 PASS；
  散牌 HK 可压 J 且 _action_breaks_core_structure=False，应出 HK。
"""
import pytest

from src.v.nn.endgame.endgame_decide import EndgameDecider


HAND = [
    "DT", "HK",
    "D6", "S6", "C6", "D6",
    "S7", "C7", "H7", "S7",
    "DJ", "HJ", "CJ",
    "HQ", "DQ",
]

ACTION_LIST = [
    ["PASS", "PASS", "PASS"],
    ["Single", "K", ["HK"]],
    ["Single", "Q", ["HQ"]],
    ["Single", "Q", ["DQ"]],
    ["Bomb", "6", ["D6", "S6", "C6", "D6"]],
    ["Bomb", "7", ["S7", "C7", "H7", "S7"]],
]


def _build_gs():
    return {
        "myPos": 2,
        "curPos": 2,
        "greaterPos": 1,
        "greaterAction": ["Single", "J", ["CJ"]],
        "handCards": list(HAND),
        "curRank": "2",
        "numofplayers": [10, 12, 15, 8],
        "_group_members": {
            0: ["D6", "S6", "C6", "D6"],
            1: ["S7", "C7", "H7", "S7"],
            2: ["DJ", "HJ", "CJ"],
            3: ["HQ", "DQ"],
        },
        "_group_gid_type_map": {
            0: "Bomb",
            1: "Bomb",
            2: "trip_in_three_with_two",
            3: "pair_in_three_with_two",
        },
    }


def test_q3_skips_breaking_q_picks_scatter_k():
    decider = EndgameDecider()
    gs = _build_gs()
    ec = {"my_pos": 2, "enemies": {1: {"remaining": 12}}}
    result = decider._q3_bomb_fallback(gs, ACTION_LIST, ec)
    assert result is not None
    idx, act = result
    assert act[0] == "Single"
    assert act[1] == "K"
    assert act[2] == ["HK"]
    assert idx == 1


def test_q3_all_break_core_still_passes():
    """全部合法压牌均拆核且无 GUA-252 豁免 → PASS。"""
    decider = EndgameDecider()
    gs = _build_gs()
    # 去掉散牌 HK，只剩拆 Q 对
    gs["handCards"] = [c for c in HAND if c != "HK"]
    al = [
        ["PASS", "PASS", "PASS"],
        ["Single", "Q", ["HQ"]],
        ["Single", "Q", ["DQ"]],
    ]
    ec = {"my_pos": 2, "enemies": {1: {"remaining": 12}}}
    result = decider._q3_bomb_fallback(gs, al, ec)
    assert result is not None
    idx, act = result
    assert act[0] == "PASS"
