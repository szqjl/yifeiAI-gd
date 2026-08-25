# -*- coding: utf-8 -*-
"""GUA-275/276/277：出完手牌优先级构造态。

原则：同型顺压 > 保级牌/对子结构 > 炸；领出先耗中小结构。
锚点 match=6a8d3d40。
"""

import logging

from src.v.nn.features.memory_tracker import MemoryTracker
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _eng(player_id=2, role="超强主攻"):
    e = UltimateWinRateEngineV7(player_id=player_id)
    e.logger = logging.getLogger("test_gua275_276_277")
    e._current_role = role
    return e


def _tracker(my_pos=2):
    t = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    t.init_from_hand([])
    return t


class TestGua275SameTypeBeforeBomb:
    """有同型可压时禁止 R11 改炸。"""

    def test_pair_t_with_jj_qq_pair2_not_bomb(self):
        """match 6a8d3d40：Pair/T + JJ/QQ/对2 + 炸 → Pair/J，非 Bomb/3。"""
        hand = [
            "SJ", "HJ", "HQ", "SQ", "C2", "S2",
            "D3", "C3", "S3", "H3",
            "C4", "S4", "H4", "D4",
            "SK", "DA", "SB",
        ]
        engine = _eng()
        engine._tracker = _tracker()
        engine._card_mask = {
            "SJ": (3, 0.0, 2), "HJ": (3, 0.0, 2),
            "HQ": (4, 0.0, 2), "SQ": (4, 0.0, 2),
            "C2": (5, 0.0, 2), "S2": (5, 0.0, 2),
            "D3": (0, 1.0, 4), "C3": (0, 1.0, 4),
            "S3": (0, 1.0, 4), "H3": (0, 1.0, 4),
            "C4": (1, 1.0, 4), "S4": (1, 1.0, 4),
            "H4": (1, 1.0, 4), "D4": (1, 1.0, 4),
            "SK": (-1, 0.0, 1), "DA": (-1, 0.0, 1), "SB": (-1, 0.0, 1),
        }
        engine._group_type_map = {
            0: "Bomb", 1: "Bomb", 3: "pair", 4: "pair", 5: "pair",
        }
        engine._group_members = {
            0: ["D3", "C3", "S3", "H3"],
            1: ["C4", "S4", "H4", "D4"],
            3: ["SJ", "HJ"],
            4: ["HQ", "SQ"],
            5: ["C2", "S2"],
            -1: ["SK", "DA", "SB"],
        }
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Pair", "J", ["SJ", "HJ"]],
            ["Pair", "Q", ["HQ", "SQ"]],
            ["Pair", "2", ["C2", "S2"]],
            ["Bomb", "3", ["D3", "C3", "S3", "H3"]],
            ["Bomb", "4", ["C4", "S4", "H4", "D4"]],
        ]
        # 模拟 R11 已记「第一圈让道」：min_press 若失败也应走 GUA-275
        from src.v.nn.guards import v7_guards
        v7_guards._UPPER_SKIP_MEMORY[(2, 1)] = "Pair"

        gs = {
            "myPos": 2,
            "greaterPos": 1,
            "greaterAction": ["Pair", "T", ["ST", "HT"]],
            "handCards": hand,
            "curRank": "2",
            "curPos": 2,
            "_current_stage": "stage_1",
            "actionList": action_list,
            "numofplayers": [18, 18, len(hand), 18],
        }
        engine._inject_belief_vector(gs)
        rec = engine._recommend_play(gs, action_list)
        assert rec is not None
        assert rec["type"] == "Pair", f"应同型对压，得 {rec}"
        assert rec["rank"] == "J"
        assert rec["type"] != "Bomb"


class TestGua276PreserveLevelTwTCore:
    """有王可压时勿拆 TWT/级牌 trips 核。"""

    def test_single_a_with_sb_not_split_level_trips(self):
        """Single/A + TWT 三张2 + SB → Single/B，非 Single/2。"""
        hand = [
            "D2", "C2", "S2", "D8", "H8",
            "SB", "SK", "C7",
        ]
        engine = _eng()
        engine._tracker = _tracker()
        engine._card_mask = {
            "D2": (5, 1.0, 3), "C2": (5, 1.0, 3), "S2": (5, 1.0, 3),
            "D8": (6, 1.0, 2), "H8": (6, 1.0, 2),
            "SB": (-1, 0.0, 1), "SK": (-1, 0.0, 1), "C7": (-1, 0.0, 1),
        }
        engine._group_type_map = {
            5: "trip_in_three_with_two",
            6: "pair_in_three_with_two",
        }
        engine._group_members = {
            5: ["D2", "C2", "S2"],
            6: ["D8", "H8"],
            -1: ["SB", "SK", "C7"],
        }
        gs = {
            "myPos": 2,
            "greaterPos": 1,
            "greaterAction": ["Single", "A", ["CA"]],
            "handCards": hand,
            "curRank": "2",
            "numofplayers": [20, 20, len(hand), 20],
        }
        engine._inject_belief_vector(gs)
        rec = engine._recommend_min_press_impl(
            gs,
            engine._card_mask,
            gs["greaterAction"],
            "Single",
            hand,
            "2",
        )
        assert rec is not None
        assert rec["type"] == "Single"
        assert rec["rank"] in ("B", "SB") or rec["cards"] == ["SB"]
        assert "2" not in (rec.get("rank") or "")


class TestGua277LeadMidStructureNotHighSingle:
    """手牌>10 领出：高耗损散单时优先小对/顺。"""

    def test_lead_pair_not_single_k_when_hand_gt_10(self):
        """散单仅 SK/DA/SB + loose Pair/8 → 领 Pair/8。"""
        hand = [
            "SK", "DA", "SB",
            "D8", "H8",
            "SJ", "HJ",
            "C3", "D3", "S3", "H3",
            "C4", "D4", "S4", "H4",
            "H6", "D7", "C9", "DT", "H9",
        ]
        engine = _eng()
        engine._card_mask = {
            "SK": (-1, 0.0, 1), "DA": (-1, 0.0, 1), "SB": (-1, 0.0, 1),
            "D8": (3, 0.0, 2), "H8": (3, 0.0, 2),
            "SJ": (4, 0.0, 2), "HJ": (4, 0.0, 2),
            "C3": (0, 1.0, 4), "D3": (0, 1.0, 4),
            "S3": (0, 1.0, 4), "H3": (0, 1.0, 4),
            "C4": (1, 1.0, 4), "D4": (1, 1.0, 4),
            "S4": (1, 1.0, 4), "H4": (1, 1.0, 4),
            "H6": (2, 1.0, 5), "D7": (2, 1.0, 5),
            "C9": (2, 1.0, 5), "DT": (2, 1.0, 5), "H9": (2, 1.0, 5),
        }
        engine._group_type_map = {
            0: "Bomb", 1: "Bomb", 2: "straight", 3: "pair", 4: "pair",
        }
        engine._group_members = {
            0: ["C3", "D3", "S3", "H3"],
            1: ["C4", "D4", "S4", "H4"],
            2: ["H6", "D7", "C9", "DT", "H9"],
            3: ["D8", "H8"],
            4: ["SJ", "HJ"],
            -1: ["SK", "DA", "SB"],
        }
        assert len(hand) > 10
        gs = {
            "myPos": 2,
            "greaterPos": -1,
            "greaterAction": ["PASS", "PASS", "PASS"],
            "handCards": hand,
            "curRank": "2",
        }
        rec = engine._recommend_lead_impl(
            gs, engine._card_mask, hand, "2",
        )
        assert rec is not None
        assert rec["type"] in ("Pair", "Straight"), f"应中小结构领出，得 {rec}"
        assert rec["type"] != "Single" or rec["rank"] not in ("K", "A", "B", "R")
