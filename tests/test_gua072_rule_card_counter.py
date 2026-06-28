# -*- coding: utf-8 -*-
"""
GUA-072: 规则记牌引擎 pytest（≥10 case）。

测试规则：投喂已回放历史的 MemoryTracker，验证 RuleCardCounter 信念输出。
兼容组牌引擎 TDD 模式：秒级反馈，无需 GPU/模型加载。
"""

import pytest
from src.v.nn.features.memory_tracker import MemoryTracker
from src.v.nn.features.rule_card_counter import (
    RuleCardCounter, create_counter_from_tracker, RANK_VALUE,
)


def _make_tracker(my_pos=0):
    """构造一个已初始化的 MemoryTracker。"""
    t = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    t.init_from_hand([])
    return t


def _play(tracker, seat, cards):
    """模拟玩家 seat 打出 cards。"""
    tracker.record_play(seat, [cards[0], "?", cards])


def _play_both_copies(tracker, card_type, seat_a=0, seat_b=1):
    """打出牌型 card_type 的两个副本（从不同座位）。"""
    _play(tracker, seat_a, [card_type])
    _play(tracker, seat_b, [card_type])


class TestRuleCardCounterBasic:
    """基础信念计数（HR/SB/级牌/剩张）。"""

    def test_empty_tracker_all_zero(self):
        """case 1: 空 tracker → 信念全零。"""
        t = _make_tracker()
        c = RuleCardCounter(t)
        b = c.get_belief()
        assert b["hr_played"] == 0
        assert b["sb_played"] == 0
        assert b["level_remain"] == 0  # 未 set_level_rank
        assert len(b["depleted_ranks"]) == 0

    def test_hr_sb_played_counting(self):
        """case 2: 打出 1 张 HR + 1 张 SB → hr_played=1, sb_played=1。"""
        t = _make_tracker()
        _play(t, 0, ["HR"])
        _play(t, 1, ["SB"])
        c = RuleCardCounter(t)
        b = c.get_belief()
        assert b["hr_played"] == 1
        assert b["sb_played"] == 1

    def test_both_hr_played(self):
        """case 3: 两张 HR 都打出 → hr_played=2。"""
        t = _make_tracker()
        _play(t, 0, ["HR"])
        _play(t, 2, ["HR"])
        c = RuleCardCounter(t)
        b = c.get_belief()
        assert b["hr_played"] == 2

    def test_level_cards_remaining_one_played(self):
        """case 4: 级牌=3，打出 1 张 C3 → level_remain=7（8 张级牌剩 7）。"""
        t = _make_tracker()
        t.set_level_rank("3")
        _play(t, 0, ["C3"])
        c = RuleCardCounter(t)
        b = c.get_belief()
        # 8 张级牌（4花色×2副本），1 张已出 → 剩余 7
        assert b["level_remain"] == 7

    def test_level_cards_three_played(self):
        """case 5: 级牌=3，打出 3 张不同花色 → level_remain=5。"""
        t = _make_tracker()
        t.set_level_rank("3")
        _play(t, 0, ["S3"])
        _play(t, 1, ["H3"])
        _play(t, 2, ["D3"])
        c = RuleCardCounter(t)
        b = c.get_belief()
        assert b["level_remain"] == 5  # 8 - 3

    def test_hand_counts_from_tracker(self):
        """case 6: 手动设 hand_counts → get_belief 反映正确值。"""
        t = _make_tracker()
        t.hand_counts[1] = 20
        t.hand_counts[3] = 15
        c = RuleCardCounter(t)
        b = c.get_belief()
        assert b["hand_counts"][1] == 20
        assert b["hand_counts"][3] == 15
        assert b["hand_counts"][0] == 27  # 自己未设


class TestCanOpponentSuppress:
    """核心方法 can_opponent_suppress。"""

    def test_high_rank_available_suppress_A(self):
        """case 7: 所有牌未出 → 对手压制 rank=A → True（HR/SB 仍在）。"""
        t = _make_tracker()
        c = RuleCardCounter(t)
        assert c.can_opponent_suppress(1, "A") is True

    def test_high_rank_available_suppress_T(self):
        """case 8: 对手可能压制 rank=T → J/Q/K/A/HR/SB 均未出 → True。"""
        t = _make_tracker()
        c = RuleCardCounter(t)
        assert c.can_opponent_suppress(1, "T") is True

    def test_all_higher_ranks_and_jokers_depleted(self):
        """case 9: 所有 >7 的牌 + HR/SB 全部打出 → 对手无法压制 rank=7 → False。"""
        t = _make_tracker()
        # 打出所有 8~A（8 ranks × 4 suits × 2 copies = 64 张）
        for rank in ["8", "9", "T", "J", "Q", "K", "A"]:
            for suit in ["S", "H", "D", "C"]:
                _play_both_copies(t, f"{suit}{rank}")
        # 打出 HR/SB 的全部 2 张副本
        _play_both_copies(t, "HR")
        _play_both_copies(t, "SB")
        c = RuleCardCounter(t)
        assert c.can_opponent_suppress(1, "7") is False

    def test_opponent_has_suppress_card_marked(self):
        """case 10: 对手手中已有确认压制牌（OPPONENT_HAND）→ True。"""
        t = _make_tracker(my_pos=0)
        # 手动标记：对手1 拥有 HA（rank=A > 5）
        t.card_state["HA"][0] = MemoryTracker.OPPONENT_HAND
        t.card_state["HA"][1] = MemoryTracker.PLAYED
        c = RuleCardCounter(t)
        assert c.can_opponent_suppress(1, "5") is True

    def test_only_jokers_remain_for_suppress(self):
        """case 11: 所有高牌(8~A)已出，仅剩 HR+SB → 2 张候选 ≥ min_candidates(2) → True。"""
        t = _make_tracker()
        for rank in ["8", "9", "T", "J", "Q", "K", "A"]:
            for suit in ["S", "H", "D", "C"]:
                _play_both_copies(t, f"{suit}{rank}")
        # HR/SB 未出，仍在 UNKNOWN 中 → 2 张 suppress 候选
        c = RuleCardCounter(t)
        assert c.can_opponent_suppress(1, "7") is True

    def test_wrong_seat_not_opponent(self):
        """case 12: seat=2（队友）→ can_opponent_suppress → False。"""
        t = _make_tracker(my_pos=0)
        c = RuleCardCounter(t)
        assert c.can_opponent_suppress(2, "5", min_candidates=0) is False


class TestGetBeliefIntegration:
    """get_belief 集成测试。"""

    def test_depleted_ranks_detection(self):
        """case 13: rank=4 全部 8 张打出 → depleted_ranks 含 '4'。"""
        t = _make_tracker()
        for suit in ["S", "H", "D", "C"]:
            _play_both_copies(t, f"{suit}4")
        c = RuleCardCounter(t)
        b = c.get_belief()
        assert "4" in b["depleted_ranks"]

    def test_depleted_ranks_with_my_hand_and_played(self):
        """case 14: rank=4：自己手牌标记 + 所有剩余副本打出 = 全部已知 → depleted。

        MemoryTracker.MY_HAND=1 与 seat=1 值冲突，避免从 seat=1 打出已标 MY_HAND 的牌。
        改用 seat=2,3 打出第二副本。
        """
        t = _make_tracker(my_pos=0)
        # 自己手中持有 S4, H4 → card_state: S4=[1,-1], H4=[1,-1]
        t.init_from_hand(["S4", "H4"])
        # 打出 S4, H4 的第二副本（用 seat=2,3 避免与 MY_HAND=1 冲突）
        _play(t, 3, ["S4"])   # S4: [1, 4]
        _play(t, 3, ["H4"])   # H4: [1, 4]
        # 打出 D4, C4 的全部副本
        _play_both_copies(t, "D4")
        _play_both_copies(t, "C4")
        # 现在 rank=4 全部已知：played_or_known = 2+2+2+2 = 8 = total
        c = RuleCardCounter(t)
        b = c.get_belief()
        assert "4" in b["depleted_ranks"], "expected '4' in depleted_ranks, got " + str(b["depleted_ranks"])

    def test_can_opp_suppress_with_greater_action(self):
        """case 15: game_state 含 greaterAction → can_opp_suppress_current 自动计算。"""
        t = _make_tracker(my_pos=0)
        gs = {
            "myPos": 0,
            "greaterPos": 1,  # 对手
            "greaterAction": ["Single", "5", ["H5"]],
        }
        c = RuleCardCounter(t)
        b = c.get_belief(gs)
        # 所有 >5 的 rank 均未出 → 对手可压制
        assert b["can_opp_suppress_current"] is True

    def test_can_opp_suppress_when_teammate_control(self):
        """case 16: 队友控牌时 can_opp_suppress_current 为 True（保守默认）。"""
        t = _make_tracker(my_pos=0)
        gs = {
            "myPos": 0,
            "greaterPos": 2,  # 队友
            "greaterAction": ["Pair", "K", ["HK", "DK"]],
        }
        c = RuleCardCounter(t)
        b = c.get_belief(gs)
        assert b["can_opp_suppress_current"] is True  # 队友不在 opponents 集合


class TestFactoryFunction:
    """create_counter_from_tracker 工厂函数。"""

    def test_create_from_tracker(self):
        """case 17: 工厂函数返回 RuleCardCounter 实例。"""
        t = _make_tracker()
        c = create_counter_from_tracker(t)
        assert isinstance(c, RuleCardCounter)
        assert c._t is t
