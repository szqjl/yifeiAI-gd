# -*- coding: utf-8 -*-
"""
GUA-089 \u9636\u6bb5\u8c03\u5ea6\u5668 (dispatch_by_stage) \u6784\u9020\u6001\u6d4b\u8bd5

\u8986\u76d6\u8303\u56f4\uff08\u00a77.1.3 / 7.2.3 / 7.3.3 \u9636\u6bb5 Guard \u5b50\u96c6\uff09\uff1a
  1. \u5207\u70b9\u51fd\u6570\uff1a>20 / 6-20 / \u22645
  2. STAGE_RULE_MAP \u8986\u76d6 3 \u9636\u6bb5\uff0c\u9636\u6bb5 0+1 \u4ec5\u542f\u7528 3 \u6761\uff0c\u9636\u6bb5 2 \u542f\u7528 13 \u6761
  3. STAGE_ENGINE_MAP\uff1astage_0_1 / stage_2 = None\uff08\u5f85 GUA-090/091\uff09\uff0cstage_3 = EndgameDecider \u5b9e\u9645\u53ef import
  4. \u9636\u6bb5\u8fb9\u754c\u8868\u9636\u6bb5 0+1 = (21,27)\u3001\u9636\u6bb5 2 = (6,20)\u3001\u9636\u6bb5 3 = (0,5)
  5. \u5f15\u64ce\u96c6\u6210\uff1a\u4f2a\u9020 decide() \u8c03\u7528 \u2192 game_state[\u2018_current_stage\u2019] \u51fa\u73b0
"""

import sys
import os

import pytest


class TestStageDispatch:
    """\u9636\u6bb5\u5207\u70b9\u51fd\u6570\u00a77.4 \u4f2a\u4ee3\u7801"""

    def test_hand_27_stage_0_1(self):
        from src.v.nn.dispatcher import _dispatch_by_stage, STAGE_0_1
        assert _dispatch_by_stage(27) == STAGE_0_1

    def test_hand_21_boundary_inclusive(self):
        from src.v.nn.dispatcher import _dispatch_by_stage, STAGE_0_1
        assert _dispatch_by_stage(21) == STAGE_0_1

    def test_hand_20_stage_2(self):
        from src.v.nn.dispatcher import _dispatch_by_stage, STAGE_2
        assert _dispatch_by_stage(20) == STAGE_2

    def test_hand_6_boundary_inclusive(self):
        from src.v.nn.dispatcher import _dispatch_by_stage, STAGE_2
        assert _dispatch_by_stage(6) == STAGE_2

    def test_hand_5_stage_3(self):
        from src.v.nn.dispatcher import _dispatch_by_stage, STAGE_3
        assert _dispatch_by_stage(5) == STAGE_3

    def test_hand_0_stage_3(self):
        from src.v.nn.dispatcher import _dispatch_by_stage, STAGE_3
        assert _dispatch_by_stage(0) == STAGE_3

    def test_negative_hand_size_raises(self):
        from src.v.nn.dispatcher import _dispatch_by_stage
        with pytest.raises(ValueError):
            _dispatch_by_stage(-1)

    def test_cur_rank_accepted_but_unused(self):
        """cur_rank \u4f20\u5165\u4f46\u672c\u7248\u672a\u4f7f\u7528\uff08\u9884\u7559 GUA-094 IP \u8f93\u5165\uff09"""
        from src.v.nn.dispatcher import _dispatch_by_stage, STAGE_0_1
        assert _dispatch_by_stage(27, cur_rank="2") == STAGE_0_1
        assert _dispatch_by_stage(27, cur_rank="A") == STAGE_0_1


class TestStageRuleMap:
    """STAGE_RULE_MAP \u00a77.1.3 / 7.2.3 / 7.3.3 \u9636\u6bb5 Guard \u5b50\u96c6"""

    def test_stage_0_1_has_three_rules(self):
        from src.v.nn.dispatcher import STAGE_RULE_MAP, STAGE_0_1
        rules = STAGE_RULE_MAP[STAGE_0_1]
        assert len(rules) == 3
        # \u542f\u7528 R10/R11/R14\uff08R12 \u4e0d\u542b\uff1a\u9636\u6bb5 0 \u4e0d\u62c6\u724c\uff1bR13 \u5c1a\u672a\u5b9e\u73b0\uff09
        assert "R10_no_lead_bomb" in rules
        assert "R11_unbeatable_card_throttle" in rules
        assert "R14_no_break_pattern_when_lead" in rules

    def test_stage_2_has_full_set_minus_r13(self):
        from src.v.nn.dispatcher import STAGE_RULE_MAP, STAGE_2
        rules = STAGE_RULE_MAP[STAGE_2]
        # \u00a77.2.3\uff1a\u9636\u6bb5 2 \u542f\u7528 14 \u6761\u4e2d\u7684\u53ef\u5b9e\u73b0\u90e8\u5206
        # R01-R09 \u9664 R13\uff08\u672a\u5b9e\u73b0\uff09\u5916\u90fd\u5728\uff1bR10-R12 + R14 \u90fd\u5728
        expected_count = 13  # 14 \u6761\u51cf R13 = 13
        assert len(rules) == expected_count
        # R01-R09 \u53ef\u5b9e\u73b0\u7684 8 \u6761
        for rid in ["R01_no_bomb_for_single", "R02_minimal_bomb", "R03_passive_no_pass",
                    "R04_single_b_non_pass", "R05_teammate_no_bomb",
                    "R06_no_break_structure_pair", "R07_teammate_yield",
                    "R08_feed_teammate_single", "R09_feed_teammate_5"]:
            assert rid in rules, f"missing {rid}"
        # R10-R12 + R14
        for rid in ["R10_no_lead_bomb", "R11_unbeatable_card_throttle",
                    "R12_min_pair_in_three_with_two", "R14_no_break_pattern_when_lead"]:
            assert rid in rules, f"missing {rid}"

    def test_stage_3_minimal_set(self):
        from src.v.nn.dispatcher import STAGE_RULE_MAP, STAGE_3
        rules = STAGE_RULE_MAP[STAGE_3]
        # \u00a77.3.3\uff1a\u9636\u6bb5 3 \u7cbe\u7b80\u5230 R08/R11/R14\uff08R13 \u540c\u6837\u672a\u5b9e\u73b0\uff09
        assert len(rules) == 3
        assert "R08_feed_teammate_single" in rules
        assert "R11_unbeatable_card_throttle" in rules
        assert "R14_no_break_pattern_when_lead" in rules

    def test_r13_not_in_any_stage(self):
        """R13 \u00ab\u5e73\u53f0\u70b8\u5f39\u5408\u6cd5\u6027\u00bb \u5c1a\u672a\u5b9e\u73b0\uff0c\u4e0d\u5728\u4efb\u4f55\u9636\u6bb5\u542f\u7528\u96c6\u5408"""
        from src.v.nn.dispatcher import STAGE_RULE_MAP
        for stage, rules in STAGE_RULE_MAP.items():
            for r in rules:
                assert not r.startswith("R13"), f"R13 unexpectedly enabled in {stage}"


class TestStageEngineMap:
    """STAGE_ENGINE_MAP \u5f15\u64ce\u5165\u53e3\u6620\u5c04"""

    def test_stage_0_1_engine_is_none(self):
        """GUA-090 \u672a\u5b00\uff0c\u9636\u6bb5 0+1 \u5f15\u64ce\u4e3a None"""
        from src.v.nn.dispatcher import STAGE_ENGINE_MAP, STAGE_0_1
        assert STAGE_ENGINE_MAP[STAGE_0_1] is None

    def test_stage_2_engine_is_none(self):
        """GUA-091 \u672a\u5b00\uff0c\u9636\u6bb5 2 \u5f15\u64ce\u4e3a None"""
        from src.v.nn.dispatcher import STAGE_ENGINE_MAP, STAGE_2
        assert STAGE_ENGINE_MAP[STAGE_2] is None

    def test_stage_3_engine_path_to_endgame(self):
        """\u9636\u6bb5 3 \u4f7f\u7528\u73b0\u6709\u6b8b\u5c40\u7ba1\u7ebf EndgameDecider\uff08GUA-078\uff09"""
        from src.v.nn.dispatcher import STAGE_ENGINE_MAP, STAGE_3
        path = STAGE_ENGINE_MAP[STAGE_3]
        assert path is not None
        assert "EndgameDecider" in path


class TestStageBounds:
    """\u9636\u6bb5\u8fb9\u754c\u8868"""

    def test_bounds_cover_all_hand_sizes(self):
        from src.v.nn.dispatcher import stage_bounds
        b = stage_bounds()
        # 0-27 \u5e94\u5168\u90e8\u8986\u76d6\uff0c\u4e14\u9636\u6bb5\u95f4\u4e0d\u91cd\u53e0
        for sz in range(0, 28):
            matched = [s for s, (lo, hi) in b.items() if lo <= sz <= hi]
            assert len(matched) == 1, f"hand_size={sz} matched {len(matched)} stages: {matched}"

    def test_bounds_values(self):
        from src.v.nn.dispatcher import stage_bounds, STAGE_0_1, STAGE_2, STAGE_3
        b = stage_bounds()
        assert b[STAGE_0_1] == (21, 27)
        assert b[STAGE_2] == (6, 20)
        assert b[STAGE_3] == (0, 5)


class TestGetEnabledRules:
    def test_returns_copy_not_reference(self):
        """\u9632\u5916\u90e8\u4fee\u6539\u5f71\u54cd\u539f\u59cb\u8868"""
        from src.v.nn.dispatcher import get_enabled_rules, STAGE_0_1
        a = get_enabled_rules(STAGE_0_1)
        a.append("FAKE")
        b = get_enabled_rules(STAGE_0_1)
        assert "FAKE" not in b

    def test_unknown_stage_returns_empty(self):
        from src.v.nn.dispatcher import get_enabled_rules
        assert get_enabled_rules("stage_xxx") == []


class TestGetEngineEntry:
    def test_stage_3_returns_endgame_decider_class(self):
        from src.v.nn.dispatcher import get_engine_entry, STAGE_3
        cls = get_engine_entry(STAGE_3)
        assert cls is not None
        # EndgameDecider \u662f\u7c7b
        assert isinstance(cls, type)
        assert cls.__name__ == "EndgameDecider"

    def test_stage_0_1_returns_none(self):
        from src.v.nn.dispatcher import get_engine_entry, STAGE_0_1
        assert get_engine_entry(STAGE_0_1) is None

    def test_stage_2_returns_none(self):
        from src.v.nn.dispatcher import get_engine_entry, STAGE_2
        assert get_engine_entry(STAGE_2) is None


class TestEngineIntegration:
    """\u96c6\u6210\u9a8c\u8bc1\uff1av7 \u5f15\u64ce decide() \u8c03\u7528\u540e game_state[\u2018_current_stage\u2019] \u51fa\u73b0"""

    def test_decide_injects_current_stage_for_full_hand(self):
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        eng = UltimateWinRateEngineV7(player_id=0)
        gs = {
            "myPos": 0,
            "curPos": -1,
            "curRank": "2",
            "greaterPos": -1,
            "greaterAction": [],
            "handCards": ["S2"] * 27,  # \u5168\u624b\u724c 27 \u5f20
            "actionList": [["Single", "2", ["S2"]]],
            "publicInfo": {"rest": [27, 27, 27, 27]},
        }
        try:
            eng.decide(gs)
        except Exception:
            # decide \u53ef\u80fd\u5728\u540e\u7eed\u6b65\u9aa4\u629b\u5f02\u5e38\uff0c\u4f46\u9636\u6bb5\u6ce8\u5165\u5728\u63a5\u53e7\u5f00\u5934\u5df2\u5b8c\u6210
            pass
        cur = gs.get("_current_stage")
        assert cur == "stage_0_1", "expected stage_0_1, got " + str(cur)

    def test_decide_injects_stage_2_for_15_cards(self):
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        eng = UltimateWinRateEngineV7(player_id=0)
        gs = {
            "myPos": 0,
            "curPos": -1,
            "curRank": "2",
            "greaterPos": -1,
            "greaterAction": [],
            "handCards": ["S2"] * 15,
            "actionList": [["Single", "2", ["S2"]]],
            "publicInfo": {"rest": [15, 15, 15, 15]},
        }
        try:
            eng.decide(gs)
        except Exception:
            pass
        assert gs.get("_current_stage") == "stage_2"

    def test_decide_injects_stage_3_for_3_cards(self):
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        eng = UltimateWinRateEngineV7(player_id=0)
        gs = {
            "myPos": 0,
            "curPos": -1,
            "curRank": "2",
            "greaterPos": -1,
            "greaterAction": [],
            "handCards": ["S2", "S3", "S4"],
            "actionList": [["Single", "2", ["S2"]]],
            "publicInfo": {"rest": [3, 3, 3, 3]},
        }
        try:
            eng.decide(gs)
        except Exception:
            pass
        assert gs.get("_current_stage") == "stage_3"

    def test_dispatch_counter_increments(self):
        """\u8c03\u5ea6\u8ba1\u6570\u5668 _dispatch_stage_count \u9012\u589e"""
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        eng = UltimateWinRateEngineV7(player_id=0)
        gs = {
            "myPos": 0, "curPos": -1, "curRank": "2",
            "greaterPos": -1, "greaterAction": [],
            "handCards": ["S2"] * 27,
            "actionList": [["Single", "2", ["S2"]]],
            "publicInfo": {"rest": [27, 27, 27, 27]},
        }
        try:
            eng.decide(gs)
        except Exception:
            pass
        assert eng._dispatch_stage_count == 1
        try:
            eng.decide(gs)
        except Exception:
            pass
        assert eng._dispatch_stage_count == 2

