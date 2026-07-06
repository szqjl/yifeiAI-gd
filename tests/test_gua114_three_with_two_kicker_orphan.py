# -*- coding: utf-8 -*-
"""GUA-114: 三带二 min 压带牌优先独立对子，避免从三张抠对留孤张。"""

from src.v.nn.guards.v7_guards import get_card_rank
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _step37_mask():
    """WF-12 锚点 56193021 步 37：333 + 44 + TTT 相关 card_mask 片段。"""
    return {
        "S3": (0, 1.0, 3),
        "H3": (0, 1.0, 3),
        "D3": (0, 1.0, 3),
        "H4": (7, 1.0, 2),
        "ST": (2, 1.0, 3),
        "DT": (2, 1.0, 3),
    }


class TestGua114ThreeWithTwoKickerOrphan:
    def test_min_press_prefers_natural_pair_over_split_from_trips(self):
        """回放 56193021 步37：TWT/T 应带 H4 H4，不得带 S3 H3 留 D3 孤张。"""
        eng = UltimateWinRateEngineV7(player_id=2)
        hand = ["S3", "H3", "D3", "H4", "H4", "ST", "ST", "DT"]
        rec = eng._build_three_with_two_press(
            hand,
            greater_val=2,  # 压 ThreeWithTwo/4，curRank=Q
            cur_rank="Q",
            strategy="min",
            card_mask=_step37_mask(),
        )
        assert rec is not None
        assert rec["type"] == "ThreeWithTwo"
        assert rec["rank"] == "T"
        ranks = [get_card_rank(c) for c in rec["cards"]]
        assert ranks.count("T") == 3
        assert ranks.count("4") == 2
        assert "3" not in ranks

    def test_min_press_splits_trips_when_no_natural_pair(self):
        """无独立对子时，仍允许从三张同点取 2 张作带牌。"""
        eng = UltimateWinRateEngineV7(player_id=0)
        hand = ["S3", "H3", "D3", "ST", "ST", "DT"]
        rec = eng._build_three_with_two_press(
            hand,
            greater_val=2,
            cur_rank="Q",
            strategy="min",
        )
        assert rec is not None
        assert rec["rank"] == "T"
        ranks = [get_card_rank(c) for c in rec["cards"]]
        assert ranks.count("T") == 3
        assert ranks.count("3") == 2

    def test_min_press_uses_card_mask_gsize2_without_full_hand_mask(self):
        """card_mask 标记 gsize=2 的独立对子应优先于 rank 更小的三张抠对。"""
        eng = UltimateWinRateEngineV7(player_id=0)
        hand = ["S3", "H3", "D3", "C6", "D6", "ST", "ST", "DT"]
        card_mask = {
            "S3": (0, 1.0, 3),
            "H3": (0, 1.0, 3),
            "D3": (0, 1.0, 3),
            "C6": (1, 1.0, 2),
            "D6": (1, 1.0, 2),
        }
        rec = eng._build_three_with_two_press(
            hand,
            greater_val=2,
            cur_rank="Q",
            strategy="min",
            card_mask=card_mask,
        )
        assert rec is not None
        ranks = [get_card_rank(c) for c in rec["cards"]]
        assert ranks.count("6") == 2
        assert ranks.count("3") == 0

    def test_max_strategy_unchanged_can_still_pick_smallest_kicker(self):
        """max 策略不受 GUA-114 约束，带牌仍按 prefer_large 选最大对子。"""
        eng = UltimateWinRateEngineV7(player_id=0)
        hand = ["S3", "H3", "D3", "H4", "H4", "ST", "ST", "DT"]
        rec = eng._build_three_with_two_press(
            hand,
            greater_val=2,
            cur_rank="Q",
            strategy="max",
        )
        assert rec is not None
        ranks = [get_card_rank(c) for c in rec["cards"]]
        assert ranks.count("T") == 3
        assert ranks.count("4") == 2
