# -*- coding: utf-8 -*-
"""GUA-066 禁止领出炸弹测试（R10：_rule_r10_no_lead_bomb + validate_decision 领出炸弹覆盖）"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.guards.v7_guards import (
    _rule_r10_no_lead_bomb,
    _filter_action_list_impl,
    validate_decision,
    ACTION_TYPE_PASS,
    ACTION_TYPE_SINGLE,
    ACTION_TYPE_PAIR,
    ACTION_TYPE_TRIPS,
    ACTION_TYPE_BOMB,
    ACTION_TYPE_STRAIGHT_FLUSH,
    ACTION_TYPE_THREE_WITH_TWO,
)


# ════════════════════════════════════════════
#  R10: 领出不炸（_rule_r10_no_lead_bomb）
# ════════════════════════════════════════════

class TestR10NoLeadBomb:
    def test_lead_with_bomb_and_singles(self):
        """领出时手牌有单牌+炸弹 → 过滤掉炸弹"""
        actions = [
            ["S2"],                        # 0: Single
            ["H3", "D3"],                  # 1: Pair
            ["S4", "H4", "D4", "C4"],      # 2: Bomb 4
            ["S5", "H5", "D5", "C5"],      # 3: Bomb 5
        ]
        result = _rule_r10_no_lead_bomb(actions, greater_pos=-1)
        assert result == [0, 1], f"预期只留 [0,1]（非炸弹），实际 {result}"

    def test_lead_with_all_bombs(self):
        """领出时手牌全是炸弹 → 保留最小炸弹（不能无动作）"""
        actions = [
            ["S4", "H4", "D4", "C4"],      # 0: Bomb 4 (4张)
            ["S5", "H5", "D5", "C5"],      # 1: Bomb 5 (4张)
            ["S8", "H8", "D8", "C8"],      # 2: Bomb 8 (4张，都是同rank)
        ]
        result = _rule_r10_no_lead_bomb(actions, greater_pos=-1)
        assert len(result) == 1, f"预期只留1个，实际 {result}"
        assert result[0] in [0, 1], f"预期保留最小炸弹（4张），实际选了 {result[0]}"

    def test_lead_with_bomb_greaterpos_eq_mypos(self):
        """领出时 greaterPos == myPos → 过滤掉炸弹（v1006平台新语义）"""
        actions = [
            ["S2"],                        # 0: Single
            ["H3", "D3"],                  # 1: Pair
            ["S4", "H4", "D4", "C4"],      # 2: Bomb 4
        ]
        result = _rule_r10_no_lead_bomb(actions, greater_pos=0, my_pos=0)
        assert result == [0, 1], f"greaterPos==myPos 领出应过滤炸弹，实际 {result}"

    def test_not_lead_no_filter(self):
        """被动场景（greaterPos != -1 且 != myPos）→ 不放行过滤"""
        actions = [
            ["S2"],
            ["S4", "H4", "D4", "C4"],  # Bomb
        ]
        result = _rule_r10_no_lead_bomb(actions, greater_pos=0, my_pos=2)
        assert result == [0, 1], f"非领出场景应全部保留，实际 {result}"
        # 也测试旧调用（不传 my_pos，greater_pos=0 非 -1 → 不放行）
        result2 = _rule_r10_no_lead_bomb(actions, greater_pos=0)
        assert result2 == [0, 1], f"旧调用非领出场景应全部保留，实际 {result2}"

    def test_lead_with_only_non_bombs(self):
        """领出时手牌无炸弹 → 全部保留"""
        actions = [
            ["S2"],
            ["H3", "D3"],
            ["S4", "H4", "H5"],
        ]
        result = _rule_r10_no_lead_bomb(actions, greater_pos=-1)
        assert result == [0, 1, 2], f"无炸弹场景应全部保留，实际 {result}"

    def test_lead_all_bomb_structure_keeps_bombs(self):
        """GUA-204：手牌语义全由炸弹/同花顺构成（组牌引擎无普通牌型）→ 领出不禁炸弹。

        对局 match=6a740a2427e7bf01db12df05：V8 手牌 14 = 5×7 炸弹 + 4×K 炸弹
        + A2345 同花顺，领出若禁炸弹 → 只剩拆炸弹碎片 → 安全阀放行 → 拆 5×7 打对子。
        """
        actions = [
            ["S7", "H7"],                # 0: Pair 7（拆炸弹碎片）
            ["S2"],                      # 1: Single 2
            ["C7", "D7", "H7", "S7"],    # 2: Bomb 7（4张）
            ["C7", "D7", "H7", "S7", "S7"],  # 3: Bomb 7（5张，完整）
            ["CK", "HK", "SK", "CK"],    # 4: Bomb K
        ]
        game_state = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": -1,
            "greaterAction": [],
            "handCards": ["C7", "D7", "H7", "S7", "S7",
                          "CK", "HK", "SK", "CK",
                          "SA", "S2", "H2", "S4", "S5"],
            "curRank": "2",
            "numofplayers": [14, 6, 0, 9],
            "_group_type_map": {"Bomb": 2, "StraightFlush": 1},
        }
        result = _rule_r10_no_lead_bomb(actions, greater_pos=-1, my_pos=0,
                                        game_state=game_state)
        # 手牌语义全炸弹 → 全部保留（含完整 5×7、Bomb/K）
        assert result == list(range(len(actions))), (
            f"手牌全炸弹结构领出应不禁炸弹，实际 {result}"
        )

    def test_lead_normal_hand_still_filters_bomb(self):
        """GUA-204 回归：手牌含普通牌型（对子/单张）→ R10 仍禁炸弹，不受新分支影响"""
        actions = [
            ["S2"],                      # 0: Single
            ["H3", "D3"],                # 1: Pair
            ["S4", "H4", "D4", "C4"],    # 2: Bomb 4
        ]
        game_state = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": -1,
            "greaterAction": [],
            "handCards": ["S2", "H3", "D3", "S4", "H4", "D4", "C4"],
            "curRank": "2",
            "numofplayers": [27, 27, 27, 27],
            "_group_type_map": {"pair": 1, "scatter": 1, "Bomb": 1},
        }
        result = _rule_r10_no_lead_bomb(actions, greater_pos=-1, my_pos=0,
                                        game_state=game_state)
        assert result == [0, 1], f"含普通牌型仍应禁炸弹，实际 {result}"


# ════════════════════════════════════════════
#  R10 在 filter_action_list 集成
# ════════════════════════════════════════════

class TestFilterActionListR10:
    def test_lead_position_filters_bomb(self):
        """领出位置 + 有炸弹 → filter 应剔除炸弹"""
        actions = [
            ["PASS"],
            ["S3"],
            ["S4", "H4", "D4", "C4"],  # Bomb 4
        ]
        game_state = {
            "myPos": 2,
            "curPos": -1,
            "greaterPos": -1,
            "greaterAction": [],
            "curRank": "2",
            "handCards": ["S3", "S4", "H4", "D4", "C4", "S5"],
            "numofplayers": [27, 27, 27, 27],
        }
        filtered, order = _filter_action_list_impl(game_state, actions)
        # 炸弹应被过滤，只留 PASS 和 Single
        filtered_types = []
        for act in filtered:
            from src.v.nn.guards.v7_guards import get_action_type
            filtered_types.append(get_action_type(act))
        assert ACTION_TYPE_BOMB not in filtered_types, f"领出场景不应有炸弹，实际 {filtered_types}"
        assert len(filtered) <= 2, f"预期最多2个动作（PASS+Single），实际 {len(filtered)}"

    def test_lead_position_greaterpos_eq_mypos_filters_bomb(self):
        """领出位置 greaterPos == myPos (v1006新语义) → filter 应剔除炸弹"""
        actions = [
            ["PASS"],
            ["S3"],
            ["S4", "H4", "D4", "C4"],  # Bomb 4
        ]
        game_state = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 0,  # v1006: 领出时 greaterPos == myPos
            "greaterAction": [],
            "curRank": "2",
            "handCards": ["S3", "S4", "H4", "D4", "C4", "S5"],
            "numofplayers": [27, 27, 27, 27],
        }
        filtered, order = _filter_action_list_impl(game_state, actions)
        filtered_types = []
        for act in filtered:
            from src.v.nn.guards.v7_guards import get_action_type
            filtered_types.append(get_action_type(act))
        assert ACTION_TYPE_BOMB not in filtered_types, f"greaterPos==myPos 领出不应有炸弹，实际 {filtered_types}"

    def test_passive_position_keeps_bomb(self):
        """被动场景（对手出牌）→ 炸弹应保留"""
        actions = [
            ["PASS"],
            ["S4", "H4", "D4", "C4"],  # Bomb 4
        ]
        game_state = {
            "myPos": 2,
            "curPos": 1,
            "greaterPos": 1,  # 对手@1 领出
            "greaterAction": [ ],  # 空 greaterAction 跳过 R01/R05 过滤
            "curRank": "2",
            "handCards": ["S4", "H4", "D4", "C4", "S5", "S6"],
            "numofplayers": [27, 27, 27, 27],
        }
        filtered, order = _filter_action_list_impl(game_state, actions)
        filtered_types = []
        for act in filtered:
            from src.v.nn.guards.v7_guards import get_action_type
            filtered_types.append(get_action_type(act))
        assert ACTION_TYPE_BOMB in filtered_types, f"被动场景应保留炸弹，实际 {filtered_types}"


# ════════════════════════════════════════════
#  R10 在 validate_decision 兜底
# ════════════════════════════════════════════

class TestValidateDecisionR10:
    def test_override_lead_bomb_in_validate(self):
        """validate_decision：模型选炸弹 + greaterPos==-1 → 覆盖为非炸弹"""
        # 模拟：filter 漏过，模型选了 Bomb，validate 兜底纠正
        filtered = [
            ["S3"],                        # 0: Single
            ["S4", "H4", "D4", "C4"],      # 1: Bomb 4
            ["PASS"],                       # 2: PASS
        ]
        game_state = {
            "myPos": 2,
            "greaterPos": -1,
            "greaterAction": [],
            "curRank": "2",
        }
        # 模型选了炸弹（idx 1）
        result = validate_decision(1, filtered, game_state)
        assert result == 0, f"预期覆盖为 idx 0 (Single)，实际 {result}"

    def test_override_lead_bomb_greaterpos_eq_mypos(self):
        """validate_decision：模型选炸弹 + greaterPos==myPos → 覆盖为非炸弹（v1006新语义）"""
        filtered = [
            ["S3"],                        # 0: Single
            ["S4", "H4", "D4", "C4"],      # 1: Bomb 4
            ["PASS"],                       # 2: PASS
        ]
        game_state = {
            "myPos": 0,
            "greaterPos": 0,  # v1006: 领出时 greaterPos == myPos
            "greaterAction": [],
            "curRank": "2",
        }
        # 模型选了炸弹（idx 1）
        result = validate_decision(1, filtered, game_state)
        assert result == 0, f"greaterPos==myPos 领出应覆盖炸弹为非炸弹，实际 {result}"

    def test_passive_bomb_not_override(self):
        """validate_decision：被动选炸弹（对手出牌）→ 不覆盖"""
        filtered = [
            ["S3"],
            ["S4", "H4", "D4", "C4"],  # Bomb 4
            ["PASS"],
        ]
        game_state = {
            "myPos": 2,
            "greaterPos": 1,  # 对手领出
            "greaterAction": ["Single", "5", ["D5"]],
            "curRank": "2",
        }
        result = validate_decision(1, filtered, game_state)
        assert result == 1, f"被动选炸弹不应覆盖，预期 1，实际 {result}"
