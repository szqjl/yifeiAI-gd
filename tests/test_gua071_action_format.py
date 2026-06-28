# -*- coding: utf-8 -*-
"""
GUA-071: actionList 格式兼容 — 平台格式 [type, rank, [cards]] vs 扁平 [cards]
"""

import pytest
from src.v.nn.guards.v7_guards import (
    get_action_type, get_action_rank, is_bomb, is_pure_bomb,
    _extract_action_cards, filter_action_list,
    ACTION_TYPE_BOMB, ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR,
    ACTION_TYPE_STRAIGHT, ACTION_TYPE_THREE_WITH_TWO,
)


class TestExtractActionCards:
    """测试 _extract_action_cards 双格式兼容。"""

    def test_platform_format(self):
        cards = _extract_action_cards(["Bomb", "A", ["HA", "CA", "SA", "DA"]])
        assert cards == ["HA", "CA", "SA", "DA"]

    def test_flat_format(self):
        cards = _extract_action_cards(["S2", "H2"])
        assert cards == ["S2", "H2"]

    def test_single_flat(self):
        cards = _extract_action_cards(["H2"])
        assert cards == ["H2"]

    def test_pass(self):
        cards = _extract_action_cards(["PASS", "PASS", "PASS"])
        assert cards == ["PASS", "PASS", "PASS"]  # Not platform format (index 2 is not list)


class TestGetActionTypePlatform:
    """测试 get_action_type 对平台格式的正确识别。"""

    def test_bomb_platform(self):
        assert get_action_type(["Bomb", "A", ["HA", "CA", "SA", "DA"]]) == ACTION_TYPE_BOMB

    def test_single_platform(self):
        assert get_action_type(["Single", "2", ["H2"]]) == ACTION_TYPE_SINGLE

    def test_pair_platform(self):
        assert get_action_type(["Pair", "2", ["S2", "H2"]]) == ACTION_TYPE_PAIR

    def test_straight_platform(self):
        assert get_action_type(["Straight", "5", ["S5", "C6", "C7", "D8", "D9"]]) == ACTION_TYPE_STRAIGHT

    def test_three_with_two_platform(self):
        assert get_action_type(["ThreeWithTwo", "K", ["HK", "CK", "CK", "CQ", "DQ"]]) == ACTION_TYPE_THREE_WITH_TWO


class TestFakeBombFiltering:
    """测试 R13 平台炸弹合法性校验。"""

    def test_fake_bomb_filtered(self):
        """3 Aces + 9 标为 Bomb 但非真炸 → R13 剔除。"""
        game_state = {
            "myPos": 0,
            "greaterPos": 3,
            "greaterAction": ["Single", "3", ["D3"]],
            "curPos": 0,
            "curRank": "2",
            "handCards": ["HA", "CA", "CA", "H9", "H2", "C3", "D5"],
            "actionList": [
                ["Bomb", "A", ["HA", "CA", "CA", "H9"]],  # 假炸：3 Aces+9
                ["Single", "2", ["H2"]],
                ["PASS", "PASS", "PASS"],
            ],
            "numofplayers": [27, 27, 27, 27],
        }
        filtered, mapping = filter_action_list(game_state)
        types = [get_action_type(a) for a in filtered]
        assert ACTION_TYPE_BOMB not in types, "假炸应被 R13 剔除"

    def test_real_bomb_kept_when_no_singles(self):
        """真炸 4 同牌且无 Single 选项 → 保留。"""
        game_state = {
            "myPos": 0,
            "greaterPos": 3,
            "greaterAction": ["Single", "3", ["D3"]],
            "curPos": 0,
            "curRank": "2",
            "handCards": ["HA", "CA", "SA", "DA"],
            "actionList": [
                ["Bomb", "A", ["HA", "CA", "SA", "DA"]],  # 真炸
                ["PASS", "PASS", "PASS"],
            ],
            "numofplayers": [27, 27, 27, 27],
        }
        filtered, mapping = filter_action_list(game_state)
        types = [get_action_type(a) for a in filtered]
        assert ACTION_TYPE_BOMB in types, "真炸无 Single 时应保留"

    def test_real_bomb_removed_when_singles_exist(self):
        """真炸 4 同牌但存在 Single 选项 → R01 剔除。"""
        game_state = {
            "myPos": 0,
            "greaterPos": 3,
            "greaterAction": ["Single", "3", ["D3"]],
            "curPos": 0,
            "curRank": "2",
            "handCards": ["HA", "CA", "SA", "DA", "H2", "C3"],
            "actionList": [
                ["Bomb", "A", ["HA", "CA", "SA", "DA"]],  # 真炸
                ["Single", "2", ["H2"]],
                ["Single", "3", ["C3"]],
                ["PASS", "PASS", "PASS"],
            ],
            "numofplayers": [27, 27, 27, 27],
        }
        filtered, mapping = filter_action_list(game_state)
        types = [get_action_type(a) for a in filtered]
        assert ACTION_TYPE_BOMB not in types, "有 Single 时 R01 应剔除炸弹"


class TestGetActionRankPlatform:
    """测试 get_action_rank 对平台格式的正确识别。"""

    def test_bomb_rank(self):
        assert get_action_rank(["Bomb", "A", ["HA", "CA", "SA", "DA"]]) == "A"

    def test_pair_rank(self):
        assert get_action_rank(["Pair", "5", ["C5", "D5"]]) == "5"

    def test_single_rank(self):
        assert get_action_rank(["Single", "K", ["HK"]]) == "K"


class TestIsPureBomb:
    """测试 is_pure_bomb 对平台格式的正确识别。"""

    def test_pure_bomb_platform(self):
        assert is_pure_bomb(["Bomb", "A", ["HA", "CA", "SA", "DA"]], "2") is True

    def test_impure_bomb_with_wild(self):
        """含逢人配的炸不应为纯炸。"""
        assert is_pure_bomb(["Bomb", "A", ["HA", "CA", "SA", "HA"]], "A") is False
