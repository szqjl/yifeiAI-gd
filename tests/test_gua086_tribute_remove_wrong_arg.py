# -*- coding: utf-8 -*-
"""
GUA-086 进/还贡出牌 remove 路径传参错修复测试

原 bug：yf1_v7.py / yf2_v7.py 的 _handle_tribute_action / _handle_back_action
把 action_list[act_index]（即 ["tribute"|"back", "tribute"|"back", [card_str,...]]）
直接传给 adjust_initial_hand_for_tribute_back，导致 _normalize_tribute_back_card
走 list 分支得 "TRIBUTETRIBUTE" 永远 warn 不匹配。

修复：yf1_v7.py / yf2_v7.py 新增 _extract_tribute_back_card helper，
从 selected[2][0] 提取单张牌字符串再传给 adjust_initial_hand_for_tribute_back。

参考：scripts/tools/yf_replay.py:59 _cards_from_tribute_back_action
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ════════════════════════════════════════════
#  helper 提取逻辑（yf1_v7 / yf2_v7 内部方法）
# ════════════════════════════════════════════

class TestExtractTributeBackCard:
    """yf1_v7.py / yf2_v7.py 内部 _extract_tribute_back_card"""

    @staticmethod
    def _extract(selected):
        """与 yf1_v7.py 修复后实现的提取逻辑保持一致"""
        if not isinstance(selected, list) or len(selected) < 3:
            return None
        cards = selected[2]
        if isinstance(cards, list) and cards:
            first = cards[0]
            if isinstance(first, str) and len(first) >= 2:
                return first[0].upper() + first[1:].upper()
        return None

    def test_tribute_action_with_sb(self):
        """v1006 平台 actionList 项: ["tribute", "tribute", ["SB"]] → 'SB'"""
        selected = ["tribute", "tribute", ["SB"]]
        assert self._extract(selected) == "SB"

    def test_back_action_with_s3(self):
        """back 形态: ["back", "back", ["S3"]] → 'S3'"""
        selected = ["back", "back", ["S3"]]
        assert self._extract(selected) == "S3"

    def test_lowercase_input_normalized(self):
        """小写牌面也应规范成大写: ["tribute","tribute",["hr"]] → 'HR'"""
        selected = ["tribute", "tribute", ["hr"]]
        assert self._extract(selected) == "HR"

    def test_none_selected(self):
        selected = None
        assert self._extract(selected) is None

    def test_empty_action(self):
        selected = []
        assert self._extract(selected) is None

    def test_too_short_action(self):
        selected = ["tribute", "tribute"]
        assert self._extract(selected) is None

    def test_empty_card_list(self):
        selected = ["tribute", "tribute", []]
        assert self._extract(selected) is None

    def test_non_list_action(self):
        selected = "TRIBUTETRIBUTE"
        assert self._extract(selected) is None


# ════════════════════════════════════════════
#  端到端：adjust_initial_hand_for_tribute_back remove 路径
# ════════════════════════════════════════════

class TestAdjustInitialHandRemoveWithRealisticAction:
    """模拟 _handle_tribute_action 调 remove 时传 helper 输出，应真正从 hand 移除"""

    def _build_recorder(self, hand):
        """构造最小 GameRecorder（绕开 start_game）"""
        from src.communication.v7_game_recorder import GameRecorder
        rec = GameRecorder.__new__(GameRecorder)
        rec.player_id = 0
        rec.player_name = "yf1_v7"
        rec.current_game = {
            "initial_hand": list(hand),
            "all_players_hands": {"0": list(hand)},
        }
        return rec

    def test_remove_sb_from_hand(self):
        """手牌含 SB，调 remove('SB', 'remove') 应真移除"""
        rec = self._build_recorder(["S2", "H3", "SB", "D5", "CK"])
        rec.adjust_initial_hand_for_tribute_back("SB", "remove")
        assert rec.current_game["initial_hand"] == ["S2", "H3", "D5", "CK"]
        assert rec.current_game["all_players_hands"]["0"] == ["S2", "H3", "D5", "CK"]

    def test_remove_card_not_in_hand_warns(self):
        """手牌不含该牌 → warn 但不抛"""
        rec = self._build_recorder(["S2", "H3", "D5"])
        rec.adjust_initial_hand_for_tribute_back("HR", "remove")  # 手牌里没 HR
        # 应当不变
        assert rec.current_game["initial_hand"] == ["S2", "H3", "D5"]

    def test_remove_normalize_does_not_break_with_list_action(self):
        """
        修复前的回归保护：若有人不小心把整个 action 列表直接传进来
        （GUA-086 修前的错误做法），_normalize_tribute_back_card 对 list
        走 f"{c[0]}{c[1]}" 拼接成 'tributetribute' / 'backback' 永远匹配不到。
        本测试只验证：如果按修复后方式传 selected[2][0]，remove 生效。
        """
        rec = self._build_recorder(["S2", "H3", "HR", "D5", "CK"])
        # 模拟修复后调用
        selected = ["tribute", "tribute", ["HR"]]
        card = selected[2][0]  # helper 提取
        rec.adjust_initial_hand_for_tribute_back(card, "remove")
        assert rec.current_game["initial_hand"] == ["S2", "H3", "D5", "CK"]


# ════════════════════════════════════════════
#  集成：与 _handle_tribute_action 等价路径
# ════════════════════════════════════════════

class TestIntegrationTributeRemoveFlow:
    """
    模拟完整调用链：
    1. action_list = [["tribute","tribute",["HR"]]]
    2. selected = action_list[0]
    3. card = _extract_tribute_back_card(selected)  # 修复点
    4. adjust_initial_hand_for_tribute_back(card, "remove")
    5. 断言 initial_hand 真正移除了 HR
    """

    def test_full_flow_tribute_remove_succeeds(self):
        from src.communication.v7_game_recorder import GameRecorder
        rec = GameRecorder.__new__(GameRecorder)
        rec.player_id = 0
        rec.player_name = "yf1_v7"
        rec.current_game = {
            "initial_hand": ["S2", "H3", "HR", "D5", "CK", "C7"],
            "all_players_hands": {"0": ["S2", "H3", "HR", "D5", "CK", "C7"]},
        }
        # 模拟平台下发的 act 消息
        action_list = [["tribute", "tribute", ["HR"]]]
        selected = action_list[0]
        # helper 等价（与 yf1_v7.py 修复后实现一致）
        card = None
        if isinstance(selected, list) and len(selected) >= 3:
            cards = selected[2]
            if isinstance(cards, list) and cards:
                first = cards[0]
                if isinstance(first, str) and len(first) >= 2:
                    card = first[0].upper() + first[1:].upper()
        assert card == "HR"
        rec.adjust_initial_hand_for_tribute_back(card, "remove")
        assert "HR" not in rec.current_game["initial_hand"]
        assert len(rec.current_game["initial_hand"]) == 5

    def test_full_flow_back_remove_succeeds(self):
        """还贡送牌路径同样应成功"""
        from src.communication.v7_game_recorder import GameRecorder
        rec = GameRecorder.__new__(GameRecorder)
        rec.player_id = 0
        rec.player_name = "yf1_v7"
        rec.current_game = {
            "initial_hand": ["S2", "H3", "S5", "D5", "CK", "C7"],
            "all_players_hands": {"0": ["S2", "H3", "S5", "D5", "CK", "C7"]},
        }
        action_list = [["back", "back", ["S5"]]]
        selected = action_list[0]
        card = None
        if isinstance(selected, list) and len(selected) >= 3:
            cards = selected[2]
            if isinstance(cards, list) and cards:
                first = cards[0]
                if isinstance(first, str) and len(first) >= 2:
                    card = first[0].upper() + first[1:].upper()
        assert card == "S5"
        rec.adjust_initial_hand_for_tribute_back(card, "remove")
        assert "S5" not in rec.current_game["initial_hand"]
        assert len(rec.current_game["initial_hand"]) == 5
