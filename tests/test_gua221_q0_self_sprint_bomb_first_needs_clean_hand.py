# -*- coding: utf-8 -*-
"""GUA-221 回归：Q0 领出轮 bomb_first「先炸后整」必须校验炸后剩牌能整手收尾。

真源：match=6a7823180fbd680d7c6d1392（logs/v8_vs_botzone_20260809_144625.log 14:55:44）。
V8 手 9 张 = H8,H9,DT,HJ,SQ,DT,CT,CT,CQ，领出轮 non_bombs 中 Straight/Trips/Pair/Single
均命中「敌方同张数」→ bomb_first=True → 空扔 Bomb/T（DT,DT,CT,CT，拆自 straight+trips），
炸后剩 H8,H9,HJ,SQ,CQ 5 张非整手只能散打。
修复：炸后剩余牌必须 ≤1 或构成一手整牌才先炸，否则跳过 bomb_first 落回先整后炸（Q1 出单）。
"""
import logging

import pytest

from src.v.nn.endgame.endgame_decide import EndgameDecider

logging.getLogger("endgame_decider").setLevel(logging.CRITICAL)


def _lead_gs(hand_cards, action_list):
    """领出轮 game_state：上一手为 V8 自己 → is_my_turn=True。"""
    return {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": -1,
        "greaterAction": ["Single", "7", ["H7"]],
        "handCards": list(hand_cards),
        "actionList": [list(a) for a in action_list],
        "curRank": "5",
        "selfRank": "5",
        "oppoRank": "3",
    }


def _ec(enemy1_remaining):
    return {
        "my_pos": 0,
        "enemies": {1: {"remaining": enemy1_remaining}, 3: {"remaining": 0}},
        "teammate": {},
    }


class TestGua221Q0SelfSprintBombFirstNeedsCleanHand:
    """Q0 自己冲刺：bomb_first 分支必须保证炸后剩牌整手，否则不先炸。"""

    def test_match_scenario_skips_bomb_first_when_after_bomb_scatter(self):
        """真实日志场景：炸后剩 5 张散牌 → 不先炸，返回 None 落回管线（Q1 出单）。"""
        gs = _lead_gs(
            hand_cards=["H8", "H9", "DT", "HJ", "SQ", "DT", "CT", "CT", "CQ"],
            action_list=[
                ["PASS", "PASS", "PASS"],
                ["Bomb", "T", ["DT", "DT", "CT", "CT"]],
                ["Single", "8", ["H8"]],
                ["Single", "9", ["H9"]],
                ["Single", "J", ["HJ"]],
                ["Single", "Q", ["SQ"]],
                ["Single", "Q", ["CQ"]],
                ["Pair", "T", ["DT", "DT"]],
                ["Pair", "C", ["CT", "CT"]],
                ["Trips", "T", ["DT", "CT", "CT"]],
                ["Straight", "8", ["H8", "H9", "DT", "HJ", "SQ"]],
            ],
        )
        decider = EndgameDecider()
        res = decider._q0_self_sprint(gs, gs["actionList"], _ec(5))
        # 炸后剩 H8,H9,HJ,SQ,CQ 非整手 → 禁止先炸
        assert res is None

    def test_enemy_remaining_matches_straight_but_after_bomb_scatter(self):
        """敌方剩 5 张命中 Straight 同张数，但炸拆了该 Straight → 跳过先炸。"""
        gs = _lead_gs(
            hand_cards=["H8", "H9", "DT", "HJ", "SQ", "DT", "CT", "CT", "CQ"],
            action_list=[
                ["PASS", "PASS", "PASS"],
                ["Bomb", "T", ["DT", "DT", "CT", "CT"]],
                ["Straight", "8", ["H8", "H9", "DT", "HJ", "SQ"]],
            ],
        )
        decider = EndgameDecider()
        res = decider._q0_self_sprint(gs, gs["actionList"], _ec(5))
        assert res is None

    def test_bomb_first_kept_when_after_bomb_clean_straight(self):
        """炸后剩牌构成整手 straight（Bomb/K + straight 5 张）→ 仍先炸压敌。"""
        gs = _lead_gs(
            hand_cards=["H8", "H9", "HT", "HJ", "SQ", "SK", "HK", "CK", "DK"],
            action_list=[
                ["PASS", "PASS", "PASS"],
                ["Bomb", "K", ["SK", "HK", "CK", "DK"]],
                ["Single", "8", ["H8"]],
                ["Straight", "8", ["H8", "H9", "HT", "HJ", "SQ"]],
            ],
        )
        decider = EndgameDecider()
        res = decider._q0_self_sprint(gs, gs["actionList"], _ec(5))
        assert res is not None
        idx, act = res
        assert act[0] == "Bomb"
        assert sorted(act[2]) == sorted(["SK", "HK", "CK", "DK"])

    def test_bomb_first_kept_when_after_bomb_single(self):
        """炸后剩 1 张（bomb+单张）→ 仍先炸，剩单回收清场。"""
        gs = _lead_gs(
            hand_cards=["SK", "HK", "CK", "DK", "H8"],
            action_list=[
                ["PASS", "PASS", "PASS"],
                ["Bomb", "K", ["SK", "HK", "CK", "DK"]],
                ["Single", "8", ["H8"]],
            ],
        )
        decider = EndgameDecider()
        res = decider._q0_self_sprint(gs, gs["actionList"], _ec(1))
        assert res is not None
        idx, act = res
        assert act[0] == "Bomb"
        assert sorted(act[2]) == sorted(["SK", "HK", "CK", "DK"])
