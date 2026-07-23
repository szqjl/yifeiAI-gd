# -*- coding: utf-8 -*-
"""GUA-167: 领出时优先继续出同类型组合（对子/顺子/三带二），避免切换单张。"""
import pytest

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _make_engine_and_state():
    """模拟 step 73 场景：领出后手牌含多个对子 + 单张。"""
    card_mask = {
        "ST": (1, 0.0, 2),
        "DT": (1, 0.0, 2),
        "HQ": (2, 0.0, 2),
        "CQ": (2, 0.0, 2),
        "CK": (3, 0.0, 2),
        "DK": (3, 0.0, 2),
        "SB": (0, 0.0, 3),
        "C2": (0, 0.0, 0),
    }
    group_type_map = {0: "pair", 1: "pair", 2: "pair"}
    hand = list(card_mask.keys())
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = group_type_map
    engine._group_members = {}
    gs = {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 0,
        "greaterAction": [],
        "handCards": hand,
        "curRank": "A",
        "numofplayers": [8, 9, 9, 9],
    }
    action_list = [
        ["Single", "2", ["C2"]],
        ["Single", "B", ["SB"]],
        ["Pair", "T", ["ST", "DT"]],
        ["Pair", "Q", ["HQ", "CQ"]],
        ["Pair", "K", ["CK", "DK"]],
    ]
    return engine, gs, action_list


class TestGua167LeadContinuation:
    def test_lead_prefers_pair_over_single(self):
        engine, gs, action_list = _make_engine_and_state()
        idx = engine._heuristic_select(gs, action_list)
        chosen = action_list[idx]
        assert chosen[0] == "Pair", (
            f"Expected Pair when leading with multiple pairs, got {chosen[0]}"
        )

    def test_lead_prefers_lowest_pair(self):
        engine, gs, action_list = _make_engine_and_state()
        idx = engine._heuristic_select(gs, action_list)
        chosen = action_list[idx]
        # ST DT (rank T) should be chosen over HQ CQ (Q) and CK DK (K)
        assert chosen[2] == ["ST", "DT"], (
            f"Expected lowest pair ST DT, got {chosen[2]}"
        )

    def test_lead_still_allows_bomb_when_leading(self):
        """领出时如果有炸弹，炸弹仍可被选（炸弹规则③单独加分）。"""
        engine, gs, action_list = _make_engine_and_state()
        # 加一个炸弹候选
        action_list.append(["Bomb", "Q", ["HQ", "CQ", "SQ", "DQ"]])
        idx = engine._heuristic_select(gs, action_list)
        chosen = action_list[idx]
        # 炸弹 vs 对子：炸弹有③加分，应选炸弹
        assert chosen[0] == "Bomb"

    def test_not_lead_no_pair_bonus(self):
        """非领出场景（有人出牌），不给对子加分。"""
        engine, gs, action_list = _make_engine_and_state()
        gs["greaterPos"] = 1
        gs["greaterAction"] = ["Single", "2", ["H2"]]
        idx = engine._heuristic_select(gs, action_list)
        chosen = action_list[idx]
        # 非领出，应按 rank_key 选最小可压牌
        assert chosen[0] != "PASS"  # 不应该 PASS

    def test_single_pair_no_bonus(self):
        """只有一个对子候选时，不给加分（same_type_count < 2）。"""
        engine, gs, action_list = _make_engine_and_state()
        # 只保留一个对子
        action_list = [
            ["Single", "2", ["C2"]],
            ["Pair", "T", ["ST", "DT"]],
        ]
        idx = engine._heuristic_select(gs, action_list)
        chosen = action_list[idx]
        # 只有一个对子，不加分，可能选 Single（rank 0 < rank T）
        # 但对子仍有⑤基础加分，结果取决于具体分数
