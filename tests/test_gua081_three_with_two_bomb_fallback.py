# -*- coding: utf-8 -*-
"""GUA-081: 三带二推荐跳过拆 bomb core，fallback 下一档三张。"""

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _engine_with_bomb_mask():
    eng = UltimateWinRateEngineV7(player_id=0)
    eng._card_mask = {
        "S8": (0, 1.0, 4),
        "C8": (0, 1.0, 4),
        "D8": (0, 1.0, 4),
        "H9": (1, 1.0, 3),
        "C9": (1, 1.0, 3),
        "D9": (1, 1.0, 3),
        "S2": (2, 1.0, 2),
        "H2": (2, 1.0, 2),
        "C4": (3, 1.0, 2),
        "C6": (4, 0.0, 2),
        "D6": (4, 0.0, 2),
    }
    eng._group_type_map = {
        0: "bomb",
        1: "trip_in_three_with_two",
        2: "pair_in_three_with_two",
        3: "pair_in_three_with_two",
        4: "pair",
    }
    eng._group_members = {
        0: ["S8", "S8", "C8", "D8"],
        1: ["H9", "C9", "D9"],
        2: ["S2", "H2"],
        3: ["C4", "C4"],
        4: ["C6", "D6"],
    }
    return eng


class TestThreeWithTwoBombFallback:
    def test_skip_888_use_999_when_8_is_bomb(self):
        """回放 20260628091707150272 步7：888 拆炸 → 应推荐 999+对。"""
        eng = _engine_with_bomb_mask()
        hand = [
            "S8", "S8", "C8", "D8",
            "H9", "C9", "D9",
            "S2", "H2", "C4", "C4", "C6", "D6",
        ]
        rec = eng._build_three_with_two_press(
            hand,
            greater_val=4,  # rank 6
            cur_rank="5",
            strategy="min",
            card_mask=eng._card_mask,
            group_type_map=eng._group_type_map,
            group_members=eng._group_members,
        )
        assert rec is not None
        assert rec["type"] == "ThreeWithTwo"
        assert rec["rank"] == "9"
        from src.v.nn.guards.v7_guards import get_card_rank
        trip_ranks = [get_card_rank(c) for c in rec["cards"]]
        assert trip_ranks.count("9") == 3
        assert "8" not in trip_ranks

    def test_no_mask_still_prefers_min_trips(self):
        eng = UltimateWinRateEngineV7(player_id=0)
        hand = ["S8", "C8", "D8", "H9", "C9", "D9", "S2", "H2"]
        rec = eng._build_three_with_two_press(hand, greater_val=4, cur_rank="5", strategy="min")
        assert rec is not None
        assert rec["rank"] == "8"
