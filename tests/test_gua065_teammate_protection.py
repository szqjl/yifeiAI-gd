# -*- coding: utf-8 -*-
"""GUA-065 队友保护 Guard 规则测试（R07/R08/R09 + _group_consistency_filter 队友场景）"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.guards.v7_guards import (
    _rule_r07_teammate_yield,
    _rule_r08_feed_teammate_single,
    _rule_r09_feed_teammate_5,
    _filter_action_list_impl,
    ACTION_TYPE_PASS,
    ACTION_TYPE_SINGLE,
    ACTION_TYPE_PAIR,
    ACTION_TYPE_THREE_WITH_TWO,
    ACTION_TYPE_BOMB,
)


# ════════════════════════════════════════════
#  R07: 队友控牌不压
# ════════════════════════════════════════════

class TestR07TeammateYield:
    def test_teammate_controls_non_sprint(self):
        """队友控牌 + 自己 >10 张 → 只留 PASS"""
        actions = [["PASS"], ["S2"], ["S3","H3"], ["S4","H4","D4","C4"]]
        result = _rule_r07_teammate_yield(
            actions, greater_pos=2, my_pos=0, numofplayers=[15, 20, 20, 20])
        assert result == [0], f"预期只留PASS，实际 {result}"

    def test_teammate_controls_sprint(self):
        """队友控牌 + 自己 ≤10 张 → 全部放行（残局冲刺）"""
        actions = [["PASS"], ["S2"], ["S3","H3"]]
        result = _rule_r07_teammate_yield(
            actions, greater_pos=2, my_pos=0, numofplayers=[8, 20, 20, 20])
        assert result == [0, 1, 2], f"预期全部放行，实际 {result}"

    def test_teammate_controls_boundary_10(self):
        """队友控牌 + 自己 =10 张 → 放行（边界值）"""
        actions = [["PASS"], ["S2"]]
        result = _rule_r07_teammate_yield(
            actions, greater_pos=2, my_pos=0, numofplayers=[10, 20, 20, 20])
        assert result == [0, 1]

    def test_opponent_controls(self):
        """对手控牌 → 不放行"""
        actions = [["PASS"], ["S2"], ["S3","H3"]]
        result = _rule_r07_teammate_yield(
            actions, greater_pos=1, my_pos=0, numofplayers=[15, 20, 20, 20])
        assert result == [0, 1, 2], f"对手控牌不应过滤，实际 {result}"

    def test_teammate_controls_11_cards(self):
        """队友控牌 + 自己 =11 张 → 只留 PASS"""
        actions = [["PASS"], ["S2"]]
        result = _rule_r07_teammate_yield(
            actions, greater_pos=2, my_pos=0, numofplayers=[11, 20, 20, 20])
        assert result == [0]


# ════════════════════════════════════════════
#  R08: 队友剩 1 张送最小单
# ════════════════════════════════════════════

class TestR08FeedTeammateSingle:
    def test_teammate_1_card_active(self):
        """主动 + 队友剩 1 张 → 最小单 + PASS"""
        actions = [["PASS"], ["SA"], ["S2"], ["S3","H3"]]
        result = _rule_r08_feed_teammate_single(
            actions, cur_pos=0, my_pos=0,
            numofplayers=[27, 20, 1, 20], cur_rank="2")
        # SA=12, S2=15(级牌) → 最小是 SA(index 1)
        # 结果应是 [PASS(0), SA(1)] 或排序为 [1, 0]
        assert set(result) == {0, 1}, f"期望 PASS+最小单，实际 {result}"

    def test_teammate_not_1_card(self):
        """队友剩 10 张 → 不触发"""
        actions = [["PASS"], ["SA"], ["S2"]]
        result = _rule_r08_feed_teammate_single(
            actions, cur_pos=0, my_pos=0,
            numofplayers=[27, 20, 10, 20], cur_rank="2")
        assert result == [0, 1, 2], f"不应触发，实际 {result}"

    def test_teammate_1_card_passive(self):
        """被动时队友剩 1 张 → 不触发 R08（被动由其他规则处理）"""
        actions = [["PASS"], ["SA"], ["S2"]]
        result = _rule_r08_feed_teammate_single(
            actions, cur_pos=1, my_pos=0,  # curPos != myPos → 被动
            numofplayers=[27, 20, 1, 20], cur_rank="2")
        assert result == [0, 1, 2], f"被动不应触发 R08，实际 {result}"

    def test_no_single_in_list(self):
        """队友剩 1 张但无 Single → 全部保留"""
        actions = [["PASS"], ["S2","H2"], ["S3","H3","D3"]]
        result = _rule_r08_feed_teammate_single(
            actions, cur_pos=0, my_pos=0,
            numofplayers=[27, 20, 1, 20], cur_rank="2")
        assert result == [0, 1, 2], f"无单牌应保留全部，实际 {result}"


# ════════════════════════════════════════════
#  R09: 队友剩 5 张送 Pair/ThreeWithTwo
# ════════════════════════════════════════════

class TestR09FeedTeammate5:
    def test_teammate_5_cards_active(self):
        """主动 + 队友剩 5 张 → 优先 Pair/ThreeWithTwo + PASS"""
        actions = [
            ["PASS"], ["SA"],  # 0:PASS, 1:Single
            ["S2","H2"], ["S3","H3","D3"],  # 2:Pair, 3:Trips
            ["S4","H4","D4","C4","S5"],  # 4:? (bomb+single, not ThreeWithTwo)
        ]
        result = _rule_r09_feed_teammate_5(
            actions, cur_pos=0, my_pos=0, numofplayers=[27, 20, 5, 20])
        # 只有 index 2 是 Pair，无 ThreeWithTwo → kept=[2,0]
        assert 2 in result, f"应保留 Pair(index 2)，实际 {result}"
        assert 0 in result, f"应保留 PASS(index 0)，实际 {result}"

    def test_teammate_not_5_cards(self):
        """队友剩 8 张 → 不触发"""
        actions = [["PASS"], ["S2","H2"], ["S3","H3","D3"]]
        result = _rule_r09_feed_teammate_5(
            actions, cur_pos=0, my_pos=0, numofplayers=[27, 20, 8, 20])
        assert result == [0, 1, 2], f"不应触发，实际 {result}"

    def test_teammate_5_passive(self):
        """被动时队友剩 5 张 → 不触发"""
        actions = [["PASS"], ["S2","H2"]]
        result = _rule_r09_feed_teammate_5(
            actions, cur_pos=1, my_pos=0,  # curPos != myPos
            numofplayers=[27, 20, 5, 20])
        assert result == [0, 1], f"被动不应触发，实际 {result}"

    def test_teammate_5_no_pair_sthree(self):
        """队友剩 5 张但无 Pair/ThreeWithTwo → 全部保留"""
        actions = [["PASS"], ["SA"], ["S3","H3","D3"]]
        result = _rule_r09_feed_teammate_5(
            actions, cur_pos=0, my_pos=0, numofplayers=[27, 20, 5, 20])
        assert result == [0, 1, 2], f"无目标牌型应保留全部，实际 {result}"


# ════════════════════════════════════════════
#  集成测试：_filter_action_list_impl 含 R07
# ════════════════════════════════════════════

class TestFilterWithR07:
    def test_filter_r07_integration(self):
        """filter_action_list 含 R07：队友控牌时 PASS 优先"""
        game_state = {
            "myPos": 0,
            "greaterPos": 2,  # 队友控牌
            "greaterAction": ["S3"],
            "curRank": "2",
            "handCards": ["S2", "H2", "D2", "C2", "S3", "H3", "D3",
                          "C3", "S4", "H4", "D4", "S5"],
            "curPos": 0,
            "numofplayers": [12, 20, 20, 20],  # 自己 12 张
        }
        action_list = [
            ["PASS"], ["S2"], ["S3","H3"], ["S4", "H4", "D4", "C4"],
        ]
        filtered, order = _filter_action_list_impl(game_state, action_list)
        # R07 应过滤掉非 PASS 动作（自己 12 张 >10）
        assert [["PASS"]] in filtered or ["PASS"] in filtered, \
            f"R07 应保留PASS，实际 {filtered}"
