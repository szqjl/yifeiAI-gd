# -*- coding: utf-8 -*-
"""
GUA-089 阶段调度器 (dispatch_by_stage) 构造态测试

覆盖范围（四阶段修订 2026-07-05）：
  1. 切点函数：27 / 21-26 / 11-20 / 0-10
  2. STAGE_RULE_MAP 覆盖 4 阶段
  3. STAGE_ENGINE_MAP：stage_0/1/2 = None，stage_3 = EndgameDecider
  4. 阶段边界表不重叠且覆盖 0-27
  5. 引擎集成：decide() 注入 _current_stage
"""

import pytest


class TestStageDispatch:
    """阶段切点函数"""

    def test_hand_27_stage_0(self):
        from src.v.nn.dispatcher import _dispatch_by_stage, STAGE_0
        assert _dispatch_by_stage(27) == STAGE_0

    def test_hand_26_stage_1(self):
        from src.v.nn.dispatcher import _dispatch_by_stage, STAGE_1
        assert _dispatch_by_stage(26) == STAGE_1

    def test_hand_21_boundary_inclusive(self):
        from src.v.nn.dispatcher import _dispatch_by_stage, STAGE_1
        assert _dispatch_by_stage(21) == STAGE_1

    def test_hand_20_stage_2(self):
        from src.v.nn.dispatcher import _dispatch_by_stage, STAGE_2
        assert _dispatch_by_stage(20) == STAGE_2

    def test_hand_11_boundary_inclusive(self):
        from src.v.nn.dispatcher import _dispatch_by_stage, STAGE_2
        assert _dispatch_by_stage(11) == STAGE_2

    def test_hand_10_stage_3(self):
        from src.v.nn.dispatcher import _dispatch_by_stage, STAGE_3
        assert _dispatch_by_stage(10) == STAGE_3

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
        from src.v.nn.dispatcher import _dispatch_by_stage, STAGE_0, STAGE_1
        assert _dispatch_by_stage(27, cur_rank="2") == STAGE_0
        assert _dispatch_by_stage(21, cur_rank="A") == STAGE_1

    def test_stage_0_1_alias_equals_stage_1(self):
        from src.v.nn.dispatcher import STAGE_0_1, STAGE_1
        assert STAGE_0_1 == STAGE_1


class TestStageRuleMap:
    """STAGE_RULE_MAP 阶段 Guard 子集"""

    def test_opening_stages_share_three_rules(self):
        from src.v.nn.dispatcher import STAGE_RULE_MAP, STAGE_0, STAGE_1
        for stage in (STAGE_0, STAGE_1):
            rules = STAGE_RULE_MAP[stage]
            assert len(rules) == 3
            assert "R10_no_lead_bomb" in rules
            assert "R11_unbeatable_card_throttle" in rules
            assert "R14_no_break_pattern_when_lead" in rules

    def test_stage_2_has_full_set_minus_r13(self):
        from src.v.nn.dispatcher import STAGE_RULE_MAP, STAGE_2
        rules = STAGE_RULE_MAP[STAGE_2]
        expected_count = 13
        assert len(rules) == expected_count
        for rid in [
            "R01_no_bomb_for_single", "R02_minimal_bomb", "R03_passive_no_pass",
            "R04_single_b_non_pass", "R05_teammate_no_bomb",
            "R06_no_break_structure_pair", "R07_teammate_yield",
            "R08_feed_teammate_single", "R09_feed_teammate_5",
        ]:
            assert rid in rules, f"missing {rid}"
        for rid in [
            "R10_no_lead_bomb", "R11_unbeatable_card_throttle",
            "R12_min_pair_in_three_with_two", "R14_no_break_pattern_when_lead",
        ]:
            assert rid in rules, f"missing {rid}"

    def test_stage_3_minimal_set(self):
        from src.v.nn.dispatcher import STAGE_RULE_MAP, STAGE_3
        rules = STAGE_RULE_MAP[STAGE_3]
        assert len(rules) == 3
        assert "R08_feed_teammate_single" in rules
        assert "R11_unbeatable_card_throttle" in rules
        assert "R14_no_break_pattern_when_lead" in rules

    def test_r13_not_in_any_stage(self):
        from src.v.nn.dispatcher import STAGE_RULE_MAP
        for stage, rules in STAGE_RULE_MAP.items():
            for r in rules:
                assert not r.startswith("R13"), f"R13 unexpectedly enabled in {stage}"


class TestStageEngineMap:
    """STAGE_ENGINE_MAP 引擎入口映射"""

    def test_opening_stages_engine_is_none(self):
        from src.v.nn.dispatcher import STAGE_ENGINE_MAP, STAGE_0, STAGE_1
        assert STAGE_ENGINE_MAP[STAGE_0] is None
        assert STAGE_ENGINE_MAP[STAGE_1] is None

    def test_stage_2_engine_is_none(self):
        from src.v.nn.dispatcher import STAGE_ENGINE_MAP, STAGE_2
        assert STAGE_ENGINE_MAP[STAGE_2] is None

    def test_stage_3_engine_path_to_endgame(self):
        from src.v.nn.dispatcher import STAGE_ENGINE_MAP, STAGE_3
        path = STAGE_ENGINE_MAP[STAGE_3]
        assert path is not None
        assert "EndgameDecider" in path


class TestStageBounds:
    """阶段边界表"""

    def test_bounds_cover_all_hand_sizes(self):
        from src.v.nn.dispatcher import stage_bounds
        b = stage_bounds()
        for sz in range(0, 28):
            matched = [s for s, (lo, hi) in b.items() if lo <= sz <= hi]
            assert len(matched) == 1, f"hand_size={sz} matched {len(matched)} stages: {matched}"

    def test_bounds_values(self):
        from src.v.nn.dispatcher import stage_bounds, STAGE_0, STAGE_1, STAGE_2, STAGE_3
        b = stage_bounds()
        assert b[STAGE_0] == (27, 27)
        assert b[STAGE_1] == (21, 26)
        assert b[STAGE_2] == (11, 20)
        assert b[STAGE_3] == (0, 10)


class TestGetEnabledRules:
    def test_returns_copy_not_reference(self):
        from src.v.nn.dispatcher import get_enabled_rules, STAGE_1
        a = get_enabled_rules(STAGE_1)
        a.append("FAKE")
        b = get_enabled_rules(STAGE_1)
        assert "FAKE" not in b

    def test_unknown_stage_returns_empty(self):
        from src.v.nn.dispatcher import get_enabled_rules
        assert get_enabled_rules("stage_xxx") == []


class TestGetEngineEntry:
    def test_stage_3_returns_endgame_decider_class(self):
        from src.v.nn.dispatcher import get_engine_entry, STAGE_3
        cls = get_engine_entry(STAGE_3)
        assert cls is not None
        assert isinstance(cls, type)
        assert cls.__name__ == "EndgameDecider"

    def test_stage_1_returns_none(self):
        from src.v.nn.dispatcher import get_engine_entry, STAGE_1
        assert get_engine_entry(STAGE_1) is None

    def test_stage_2_returns_none(self):
        from src.v.nn.dispatcher import get_engine_entry, STAGE_2
        assert get_engine_entry(STAGE_2) is None


class TestEngineIntegration:
    """集成验证：v7 引擎 decide() 调用后 game_state['_current_stage'] 出现"""

    def test_decide_injects_stage_0_for_full_hand(self):
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        eng = UltimateWinRateEngineV7(player_id=0)
        gs = {
            "myPos": 0,
            "curPos": -1,
            "curRank": "2",
            "greaterPos": -1,
            "greaterAction": [],
            "handCards": ["S2"] * 27,
            "actionList": [["Single", "2", ["S2"]]],
            "publicInfo": {"rest": [27, 27, 27, 27]},
        }
        try:
            eng.decide(gs)
        except Exception:
            pass
        assert gs.get("_current_stage") == "stage_0"

    def test_decide_injects_stage_1_for_21_cards(self):
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        eng = UltimateWinRateEngineV7(player_id=0)
        gs = {
            "myPos": 0,
            "curPos": -1,
            "curRank": "2",
            "greaterPos": -1,
            "greaterAction": [],
            "handCards": ["S2"] * 21,
            "actionList": [["Single", "2", ["S2"]]],
            "publicInfo": {"rest": [21, 21, 21, 21]},
        }
        try:
            eng.decide(gs)
        except Exception:
            pass
        assert gs.get("_current_stage") == "stage_1"

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

    def test_decide_injects_stage_3_for_10_cards(self):
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        eng = UltimateWinRateEngineV7(player_id=0)
        gs = {
            "myPos": 0,
            "curPos": -1,
            "curRank": "2",
            "greaterPos": -1,
            "greaterAction": [],
            "handCards": ["S2"] * 10,
            "actionList": [["Single", "2", ["S2"]]],
            "publicInfo": {"rest": [10, 10, 10, 10]},
        }
        try:
            eng.decide(gs)
        except Exception:
            pass
        assert gs.get("_current_stage") == "stage_3"

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
