# -*- coding: utf-8 -*-
"""
GUA-252: 敌方 ≤5 张且出单 → 拆 TWT/整牌出最大单豁免「拆核心转 PASS」

背景（2026-08-20，match=6a86823d0fbd680d7c7c1d71，V8=player0）：
  残局 V8 剩 777+KK（TWT 整牌），下家 P3（敌）剩 5 张打单 S8。
  修复前 Q1 `_q1_enemy_five_single_special` 已用 `_find_highest_single_beater`
  找到最大合法单 K（CK，K>8 可压）返回拆 KK 的 Single K，
  却被外层 `_action_breaks_core_structure`（判定 CK ∈ KK 的 pair_in_three_with_two
  核心组、拆 1 张 = 拆核心）强制转 PASS，导致对手连续控牌、我方失去夺权机会。

修复：decide 层 `_should_exempt_break_core_for_enemy_five_single` 豁免——
  仅当「greaterAction 是 Single + 出牌者是敌人 + 剩余 ≤5 + 拆出的 Single 能压过」才豁免；
  其余场景（敌 >5 张、非单、拆出压不过）仍拦截 PASS，防拆核心送菜。
"""
import pytest

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker

HAND_777_KK = ["D7", "H7", "S7", "CK", "DK"]


def build_gs(opp_remaining=5, greater_action=None):
    tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(HAND_777_KK)
    tracker.set_level_rank("2")
    tracker.hand_counts = {0: 5, 1: 5, 2: 0, 3: opp_remaining}
    return {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 3,
        "greaterAction": greater_action or ["Single", "8", ["S8"]],
        "handCards": list(HAND_777_KK),
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["Single", "7", ["S7"]],
            ["Single", "K", ["CK"]],
        ],
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "numofplayers": [5, 5, 0, opp_remaining],
        "_memory_tracker": tracker,
        "_belief": {
            "hand_counts": {0: 5, 1: 5, 2: 0, 3: opp_remaining},
            "opp_bomb_risks": {1: 1.0, 3: 1.0},
        },
        "_group_members": {0: ["D7", "H7", "S7"], 1: ["CK", "DK"]},
        "_group_gid_type_map": {
            0: "trip_in_three_with_two", 1: "pair_in_three_with_two",
        },
    }


def decide(gs):
    EndgamePreprocessor().preprocess(gs)
    decider = EndgameDecider()
    idx, act = decider.decide(gs, gs["actionList"])
    return act


def test_enemy_five_single_breaks_twt_to_max_single():
    """敌 5 张出单 8 → 拆 TWT 出最大单 K（K>8 可压）。"""
    act = decide(build_gs(5, ["Single", "8", ["S8"]]))
    assert act is not None
    assert act[0] == "Single", f"应拆 TWT 出 Single；实际 {act}"
    assert act[1] == "K", f"应出最大单 K；实际 {act}"


def test_enemy_five_single_unbeatable_passes():
    """敌 5 张出单 2/A（K 压不过）→ PASS，不送菜。"""
    act = decide(build_gs(5, ["Single", "2", ["S2"]]))
    assert act is not None
    assert act[0] == "PASS", f"压不过应 PASS；实际 {act}"

    act = decide(build_gs(5, ["Single", "A", ["SA"]]))
    assert act is not None
    assert act[0] == "PASS", f"压不过应 PASS；实际 {act}"


def test_enemy_over_five_no_exempt_passes():
    """敌 8 张（>5）出单 → 仍拦截拆核心，PASS。"""
    act = decide(build_gs(8, ["Single", "8", ["S8"]]))
    assert act is not None
    assert act[0] == "PASS", f"敌>5 张仍应拦拆核心 PASS；实际 {act}"


def test_enemy_five_pair_no_exempt_passes():
    """敌 5 张出对（非单）→ 不豁免，PASS。"""
    act = decide(build_gs(5, ["Pair", "8", ["S8", "H8"]]))
    assert act is not None
    assert act[0] == "PASS", f"非单场景仍应拦拆核心 PASS；实际 {act}"


def test_exempt_helper_unit():
    """豁免助手单元：敌 ≤5 出单可压 → 豁免；其余场景 → 不豁免。"""
    d = EndgameDecider.__new__(EndgameDecider)
    gs = build_gs(5, ["Single", "8", ["S8"]])
    EndgamePreprocessor().preprocess(gs)
    ec = gs.get("_endgame_context", {}) or {}
    # 拆 KK 出 CK（K>8）→ 豁免
    assert EndgameDecider._should_exempt_break_core_for_enemy_five_single(
        gs, ec, ["Single", "K", ["CK"]]
    ) is True
    # 拆 777 出 S7（7<8）→ 不豁免
    assert EndgameDecider._should_exempt_break_core_for_enemy_five_single(
        gs, ec, ["Single", "7", ["S7"]]
    ) is False
    # 对手出单 2（K 压不过）→ 不豁免
    gs2 = build_gs(5, ["Single", "2", ["S2"]])
    EndgamePreprocessor().preprocess(gs2)
    ec2 = gs2.get("_endgame_context", {}) or {}
    assert EndgameDecider._should_exempt_break_core_for_enemy_five_single(
        gs2, ec2, ["Single", "K", ["CK"]]
    ) is False
