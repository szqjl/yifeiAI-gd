# -*- coding: utf-8 -*-
"""GUA-167 fix: RANK_KEY 感知 curRank，级牌 rank = 15 而非固定 1。"""
import pytest

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _engine_with_state(cur_rank, greater_action, hand_cards, action_list,
                       my_pos=0, cur_pos=-1, greater_pos=1):
    engine = UltimateWinRateEngineV7(player_id=my_pos)
    engine._card_mask = {}
    engine._group_type_map = {}
    engine._group_members = {}
    card_mask = {}
    for c in hand_cards:
        if c not in card_mask:
            card_mask[c] = (-1, 0.0, 1)
    engine._card_mask = card_mask
    gs = {
        "myPos": my_pos,
        "curPos": cur_pos,
        "greaterPos": greater_pos,
        "greaterAction": greater_action,
        "handCards": hand_cards,
        "curRank": cur_rank,
        "numofplayers": [27, 27, 27, 27],
    }
    return engine, gs, action_list


class TestGua167RankKeyCurRank:

    def test_follow_prefers_pair_a_over_pair_3_when_currank_3(self):
        """curRank=3 时，级牌 3 应高于 A，heuristic 应选 Pair/A（保留级牌）。"""
        hand = ["S2", "S3", "S3", "HA", "CA", "H4", "D4", "H5", "C5",
                "H6", "D6", "H6", "S7", "H8", "S8", "C8", "D8",
                "HT", "CT", "DT", "CT"]
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Pair", "A", ["HA", "CA"]],
            ["Pair", "3", ["S3", "S3"]],
        ]
        engine, gs, action_list = _engine_with_state(
            cur_rank="3",
            greater_action=["Pair", "K", ["HK", "CK"]],
            hand_cards=hand,
            action_list=action_list,
        )
        idx = engine._heuristic_select(gs, action_list)
        chosen = action_list[idx]
        assert chosen[0] == "Pair" and chosen[1] == "A", (
            f"Expected Pair/A (save level card), got {chosen[0]}/{chosen[1]}"
        )

    def test_follow_prefers_smallest_when_rank_not_level(self):
        """curRank=4 时，3 不是级牌，选 Pair/3（最小够用）。"""
        hand = ["S2", "S3", "S3", "HA", "CA", "H4", "D4", "H5", "C5",
                "H6", "D6", "H6", "S7", "H8", "S8", "C8", "D8",
                "HT", "CT", "DT", "CT"]
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Pair", "A", ["HA", "CA"]],
            ["Pair", "3", ["S3", "S3"]],
        ]
        engine, gs, action_list = _engine_with_state(
            cur_rank="4",
            greater_action=["Pair", "K", ["HK", "CK"]],
            hand_cards=hand,
            action_list=action_list,
        )
        idx = engine._heuristic_select(gs, action_list)
        chosen = action_list[idx]
        assert chosen[0] == "Pair" and chosen[1] == "3", (
            f"Expected Pair/3 (save strength), got {chosen[0]}/{chosen[1]}"
        )

    def test_rank_key_currank_override_value(self):
        """RANK_KEY[curRank] 应返回 15（高于 A=12）。"""
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        engine = UltimateWinRateEngineV7(player_id=0)
        engine._card_mask = {}
        engine._group_type_map = {}
        engine._group_members = {}
        gs = {
            "myPos": 0, "curPos": -1, "greaterPos": 1,
            "greaterAction": ["Pair", "K", ["HK", "CK"]],
            "handCards": ["S2", "S3", "S3", "HA", "CA"],
            "curRank": "3",
            "numofplayers": [27, 27, 27, 27],
        }
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Pair", "A", ["HA", "CA"]],
            ["Pair", "3", ["S3", "S3"]],
        ]
        # Inject _score to inspect RANK_KEY behavior
        # We test indirectly via selection result
        idx = engine._heuristic_select(gs, action_list)
        chosen = action_list[idx]
        assert chosen[1] == "A", "curRank=3 should make Pair/3 rank=15 > Pair/A rank=12"

    def test_lead_with_currank_3_still_prefers_pair_over_single(self):
        """领出 + curRank=3，对子候选多于 1 个时仍优先对子（GUA-167 不变）。"""
        hand = ["S3", "S3", "ST", "DT", "C2"]
        action_list = [
            ["Single", "2", ["C2"]],
            ["Pair", "3", ["S3", "S3"]],
            ["Pair", "T", ["ST", "DT"]],
        ]
        engine, gs, action_list = _engine_with_state(
            cur_rank="3",
            greater_action=[],
            hand_cards=hand,
            action_list=action_list,
            cur_pos=0, greater_pos=0,
        )
        idx = engine._heuristic_select(gs, action_list)
        chosen = action_list[idx]
        assert chosen[0] == "Pair", (
            f"Expected Pair when leading with pairs, got {chosen[0]}"
        )

    def test_gua167_same_type_skip_highest_with_currank(self):
        """GUA-167: 领出时同类型中有级牌对和非级牌对，级牌对是最高不应加 40。"""
        hand = ["S3", "S3", "ST", "DT", "C2"]
        action_list = [
            ["Pair", "3", ["S3", "S3"]],
            ["Pair", "T", ["ST", "DT"]],
        ]
        engine, gs, action_list = _engine_with_state(
            cur_rank="3",
            greater_action=[],
            hand_cards=hand,
            action_list=action_list,
            cur_pos=0, greater_pos=0,
        )
        idx = engine._heuristic_select(gs, action_list)
        chosen = action_list[idx]
        # Pair/T (rank=8) 应比 Pair/3 (rank=15) 得分更高（save level card）
        assert chosen[1] == "T", (
            f"Expected Pair/T (save level card), got Pair/{chosen[1]}"
        )
