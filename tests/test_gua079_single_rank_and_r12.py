# -*- coding: utf-8 -*-
"""GUA-079：单张牌力顺序 + R12 王/级牌拆对 + GUA-075 greaterPos 场景路由。"""
import pytest

from src.v.nn.guards.v7_guards import get_card_value
from src.v.nn.features.grouping_engine import GroupingPlan
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


class TestSingleRankOrder:
    """04_card_types_guide §4.0：大王 > 小王 > 级牌 > A > … > 2"""

    def test_joker_beats_level_card(self):
        cur = "4"
        assert get_card_value("HR") > get_card_value("S4", cur)
        assert get_card_value("SB") > get_card_value("S4", cur)

    def test_level_beats_ace(self):
        assert get_card_value("S4", "4") > get_card_value("SA", "4")

    def test_full_order_chain(self):
        cur = "4"
        assert get_card_value("HR") > get_card_value("SB", cur)
        assert get_card_value("SB", cur) > get_card_value("S4", cur)
        assert get_card_value("S4", cur) > get_card_value("SA", cur)
        assert get_card_value("SA", cur) > get_card_value("S2", cur)

    def test_legacy_bj_rj_aliases(self):
        assert get_card_value("RJ") == get_card_value("HR")
        assert get_card_value("BJ") == get_card_value("SB")


class TestR12JokerLevelPairBreak:
    """R12 修订：有散牌时仍允许拆对出王/级牌。"""

    def _engine_with_hr_pair(self):
        plan = GroupingPlan()
        plan.pairs = [["HR", "HR"]]
        plan.singles = ["C3", "D6"]
        mask, gtm, gm = plan.to_card_mask()
        engine = UltimateWinRateEngineV7(player_id=0)
        engine._card_mask = mask
        engine._group_type_map = gtm
        engine._group_members = gm
        engine._group_role = "主攻"
        return engine

    def test_hr_single_not_filtered_by_r12(self):
        engine = self._engine_with_hr_pair()
        action_list = [
            ["PASS", "", []],
            ["Single", "R", ["HR"]],
        ]
        gs = {
            "myPos": 0,
            "handCards": ["HR", "HR", "C3", "D6"],
            "curRank": "4",
            "numofplayers": [21, 25, 21, 12],
        }
        filtered, _ = engine._group_consistency_filter(action_list, gs)
        types = [a[0] for a in filtered]
        assert "Single" in types or any(
            a[0] == "Single" and a[2] == ["HR"] for a in filtered
        )


class TestGua075GreaterPosRouting:
    """act 消息：curPos=行动席，greaterPos=本圈最大者。"""

    def test_press_lower_with_curpos_self(self):
        plan = GroupingPlan()
        plan.pairs = [["HR", "HR"]]
        plan.singles = ["C3", "D6", "H5", "S7", "C8", "D9", "HT", "CJ", "SK"]
        mask, gtm, gm = plan.to_card_mask()
        engine = UltimateWinRateEngineV7(player_id=0)
        engine._card_mask = mask
        engine._group_type_map = gtm
        engine._group_members = gm

        hand = plan.pairs[0] + plan.singles
        action_list = [
            ["PASS", "", []],
            ["Single", "R", ["HR"]],
        ]
        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 1,
            "greaterAction": ["Single", "4", ["S4"]],
            "handCards": hand,
            "curRank": "4",
            "numofplayers": [21, 25, 21, 12],
        }
        rec = engine._recommend_play(gs, action_list)
        assert rec is not None
        assert rec["type"] == "Single"
        assert rec["rank"] == "R"

    def test_decide_hr_vs_level_s4_replay(self):
        """回放 20260621204653147750 步22：下家级牌 S4，双 HR 应压不 PASS。"""
        plan = GroupingPlan()
        plan.pairs = [["HR", "HR"]]
        plan.singles = [
            "C3", "D6", "H5", "S7", "C8", "D9", "HT", "CJ", "SK", "HK",
            "CK", "S3", "H4", "D5", "C6", "S9", "H8", "D7", "ST", "CA",
        ]
        mask, gtm, gm = plan.to_card_mask()
        hand = plan.pairs[0] + plan.singles
        action_list = [
            ["PASS", "", []],
            ["Single", "R", ["HR"]],
        ]
        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 1,
            "greaterAction": ["Single", "4", ["S4"]],
            "handCards": hand,
            "curRank": "4",
            "numofplayers": [21, 25, 21, 12],
            "actionList": action_list,
        }
        engine = UltimateWinRateEngineV7(player_id=0)
        engine._card_mask = mask
        engine._group_type_map = gtm
        engine._group_members = gm
        idx = engine.decide(gs)
        assert action_list[idx][0] != "PASS"
