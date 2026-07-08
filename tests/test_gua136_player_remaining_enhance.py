# -*- coding: utf-8 -*-
"""GUA-136 单元 + 集成测试：玩家剩牌估算增强（记忆模块 + 圈序出牌历史）

测试覆盖：
  - _estimate_player_hand_cards（基于 MemoryTracker.card_state 推断）
  - _estimate_player_sprint_capability（基于推断手牌判定冲刺能力）
  - _estimate_player_remaining 增强（MemoryTracker.get_hand_count 优先）
  - GUA-135 _is_double_second_priority_scenario yf1/@3 sprint 评估升级
"""

import pytest
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor


# ── Mock MemoryTracker ──

class MockMemoryTracker:
    """Mock MemoryTracker 用于单元测试。"""

    def __init__(self, hand_counts=None, card_state=None):
        # hand_counts: {seat: count}
        self.hand_counts = hand_counts or {}
        # card_state: {card_type: [seat1, seat2]}（每种牌 2 个副本）
        self.card_state = card_state or {}

    def get_hand_count(self, seat):
        return self.hand_counts.get(seat, 0)


# ── 测试数据 ──

ANCHOR_HAND = [
    "SJ", "SJ", "HJ", "HJ", "DJ", "DJ",  # JJJJJJ
    "S7", "S7", "C7",                    # 777
    "D8", "D8", "C8",                    # 888
    "S2", "D2",                          # 22
]
TWT_333_22 = ["ThreeWithTwo", "3", ["S3", "H3", "D3", "S2", "D2"]]
TWT_777_22 = ["ThreeWithTwo", "7", ["S7", "S7", "C7", "S2", "H2"]]
TWT_888_22 = ["ThreeWithTwo", "8", ["S8", "S8", "C8", "S2", "H2"]]
PASS_ACT = ["PASS", "PASS", "PASS"]


def _build_action_list(twt_options=None, six_j=True, include_pass=True):
    acts = []
    if include_pass:
        acts.append(list(PASS_ACT))
    if six_j:
        acts.append(["Bomb", "J", ["SJ", "SJ", "HJ", "HJ", "DJ", "DJ"]])
    if twt_options:
        acts.extend(twt_options)
    return acts


def _build_state(
    hand_cards=None,
    action_list=None,
    *,
    enemy_remaining=10,
    teammate_remaining=10,
    at3_remaining=8,
    my_pos=0,
    greater_pos=1,
    greater_action=None,
    cur_rank="2",
    enemy_finish_type=None,
    memory_tracker=None,
):
    """通用 Q1 状态构造。"""
    if greater_action is None:
        greater_action = TWT_333_22
    numofplayers = [
        len(hand_cards or ANCHOR_HAND),
        enemy_remaining,
        at3_remaining,
        teammate_remaining,
    ]
    gs = {
        "myPos": my_pos,
        "curPos": greater_pos,
        "greaterPos": greater_pos,
        "greaterAction": greater_action,
        "handCards": list(hand_cards or ANCHOR_HAND),
        "actionList": list(action_list or _build_action_list(
            twt_options=[list(TWT_777_22), list(TWT_888_22)],
            six_j=True,
            include_pass=True,
        )),
        "curRank": cur_rank,
        "selfRank": cur_rank,
        "oppoRank": cur_rank,
        "numofplayers": numofplayers,
        "publicInfo": [{"rest": n} for n in numofplayers],
        "_role": "主攻",
    }
    if enemy_finish_type is not None:
        gs["_finish_type_override"] = enemy_finish_type
    if memory_tracker is not None:
        gs["_memory_tracker"] = memory_tracker
    return gs


def _preprocess(gs):
    EndgamePreprocessor().preprocess(gs)
    ec = gs["_endgame_context"]
    enemy = ec.get("enemies", {}).get(gs["greaterPos"], {})
    if enemy:
        if "finish_type" not in enemy:
            enemy["finish_type"] = gs.get("_finish_type_override", None)
    return gs


# ═══════════════════════════════════════════════════════
#  _estimate_player_hand_cards
# ═══════════════════════════════════════════════════════

class TestEstimatePlayerHandCards:
    def test_no_tracker_returns_empty(self):
        """无 MemoryTracker → 返回 []"""
        gs = _build_state()
        d = EndgameDecider()
        result = d._estimate_player_hand_cards(1, gs)
        assert result == []

    def test_tracker_returns_position_cards(self):
        """MemoryTracker 有 position 1 标记的牌 → 返回该牌"""
        card_state = {
            "SJ": [0, 1],  # 1 张属于 yf2 (0)，1 张属于 @1 (1)
            "HJ": [1, 4],  # 1 张属于 @1 (1)，1 张已出 (4)
        }
        tracker = MockMemoryTracker(card_state=card_state)
        gs = _build_state(memory_tracker=tracker)
        d = EndgameDecider()
        result = d._estimate_player_hand_cards(1, gs)
        # @1 (position 1) 有 SJ + HJ
        assert sorted(result) == ["HJ", "SJ"]

    def test_tracker_with_no_position_cards(self):
        """MemoryTracker 中 position 没有牌 → 返回 []"""
        card_state = {
            "SJ": [0, 0],  # 都在 yf2 手
            "HJ": [2, 3],  # 都在队友/对手
        }
        tracker = MockMemoryTracker(card_state=card_state)
        gs = _build_state(memory_tracker=tracker)
        d = EndgameDecider()
        result = d._estimate_player_hand_cards(1, gs)
        assert result == []

    def test_tracker_two_copies_of_same_card(self):
        """同一牌种 2 张都属于 position → 返回 2 张"""
        card_state = {
            "SJ": [1, 1],  # 2 张都属于 @1
        }
        tracker = MockMemoryTracker(card_state=card_state)
        gs = _build_state(memory_tracker=tracker)
        d = EndgameDecider()
        result = d._estimate_player_hand_cards(1, gs)
        assert result == ["SJ", "SJ"]


# ═══════════════════════════════════════════════════════
#  _estimate_player_sprint_capability
# ═══════════════════════════════════════════════════════

class TestEstimatePlayerSprintCapability:
    def test_bomb_plus_pair_has_sprint(self):
        """6J + 22 = 冲刺能力"""
        card_state = {
            "SJ": [1, 1], "HJ": [1, 1], "DJ": [1, 1],
            "S2": [1, 1], "D2": [1, 1],
        }
        tracker = MockMemoryTracker(card_state=card_state)
        gs = _build_state(memory_tracker=tracker)
        d = EndgameDecider()
        result = d._estimate_player_sprint_capability(1, gs)
        assert result is True

    def test_no_bomb_no_sprint(self):
        """无炸弹 = 无冲刺能力"""
        card_state = {
            "S7": [1, 4],  # 1 张 @1，1 张已出
            "H7": [1, 0],
            "D7": [1, 0],
        }
        tracker = MockMemoryTracker(card_state=card_state)
        gs = _build_state(memory_tracker=tracker)
        d = EndgameDecider()
        result = d._estimate_player_sprint_capability(1, gs)
        assert result is False

    def test_no_tracker_returns_false(self):
        """无 MemoryTracker → 保守 False"""
        gs = _build_state()
        d = EndgameDecider()
        result = d._estimate_player_sprint_capability(1, gs)
        assert result is False

    def test_bomb_only_no_sprint(self):
        """整手只有炸弹（无单手）= 已是「一手清空」，不是冲刺能力"""
        card_state = {
            "SJ": [1, 1], "HJ": [1, 1], "DJ": [1, 1],
        }
        tracker = MockMemoryTracker(card_state=card_state)
        gs = _build_state(memory_tracker=tracker)
        d = EndgameDecider()
        result = d._estimate_player_sprint_capability(1, gs)
        assert result is False

    def test_bomb_plus_too_many_no_sprint(self):
        """炸弹 + 6 张单 = 剩 6 张 > 5，无冲刺能力"""
        card_state = {
            "SJ": [1, 1], "HJ": [1, 1], "DJ": [1, 1],  # 6 张炸
            "S2": [1, 0], "D2": [1, 0],  # 2 张
            "S3": [1, 0], "D3": [1, 0],  # 2 张
            "S4": [1, 0], "D4": [1, 0],  # 2 张
        }
        tracker = MockMemoryTracker(card_state=card_state)
        gs = _build_state(memory_tracker=tracker)
        d = EndgameDecider()
        result = d._estimate_player_sprint_capability(1, gs)
        assert result is False


# ═══════════════════════════════════════════════════════
#  _estimate_player_remaining 增强
# ═══════════════════════════════════════════════════════

class TestEstimatePlayerRemainingEnhanced:
    def test_tracker_priority_over_enemy_ctx(self):
        """MemoryTracker.get_hand_count 优先于 enemy_ctx.remaining"""
        tracker = MockMemoryTracker(hand_counts={1: 8})
        gs = _build_state(enemy_remaining=10, memory_tracker=tracker)
        ec = {"enemies": {1: {"remaining": 10}}}
        d = EndgameDecider()
        result = d._estimate_player_remaining(1, ec, gs)
        assert result == 8

    def test_enemy_ctx_fallback(self):
        """无 MemoryTracker 时用 enemy_ctx.remaining"""
        gs = _build_state(enemy_remaining=10)
        ec = {"enemies": {1: {"remaining": 10}}}
        d = EndgameDecider()
        result = d._estimate_player_remaining(1, ec, gs)
        assert result == 10

    def test_tracker_for_teammate(self):
        """MemoryTracker 对队友（yf1）也生效"""
        tracker = MockMemoryTracker(hand_counts={2: 6})  # teammate_pos = 2
        gs = _build_state(memory_tracker=tracker)
        ec = {"enemies": {}}  # 队友不在 enemies
        d = EndgameDecider()
        result = d._estimate_player_remaining(2, ec, gs)
        assert result == 6

    def test_no_tracker_no_enemy_ctx_returns_zero(self):
        """完全未知 → 返回 0"""
        gs = _build_state()
        ec = {"enemies": {}}
        d = EndgameDecider()
        result = d._estimate_player_remaining(1, ec, gs)
        assert result == 0

    def test_tracker_returns_zero_for_unknown_seat(self):
        """MemoryTracker 无该 seat → 0（再回退 enemy_ctx）"""
        tracker = MockMemoryTracker(hand_counts={})  # 空
        gs = _build_state(enemy_remaining=5, memory_tracker=tracker)
        ec = {"enemies": {1: {"remaining": 5}}}
        d = EndgameDecider()
        result = d._estimate_player_remaining(1, ec, gs)
        assert result == 5


# ═══════════════════════════════════════════════════════
#  GUA-135 _is_double_second_priority_scenario 升级验证
# ═══════════════════════════════════════════════════════

class TestDoubleSecondPrioritySprintEvalEnhanced:
    def test_yf1_sprint_true_via_tracker(self):
        """GUA-136：yf1 推断手牌有冲刺能力 → yf1_sprint=True"""
        # teammate_pos = (0 + 2) % 4 = 2
        card_state = {
            "SJ": [2, 2], "HJ": [2, 2], "DJ": [2, 2],  # 6J yf1 有
            "S2": [2, 2], "D2": [2, 2],  # 22 yf1 有
        }
        tracker = MockMemoryTracker(hand_counts={2: 8}, card_state=card_state)
        gs = _build_state(
            hand_cards=["SJ", "SJ", "HJ", "HJ", "DJ", "DJ", "S7", "H7", "D7", "S8", "H8", "D8", "S2", "D2"],  # 14 张
            enemy_finish_type="ThreeWithTwo",
            memory_tracker=tracker,
        )
        gs["_finish_rank_value"] = 4
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        ctx = d._is_double_second_priority_scenario(gs, ec)
        # GUA-136 增强后：yf1 有 sprint 能力 → trigger=yf1_sprint（yf1 必头游）
        # 注：触发顺序 C2/C4 → yf1_sprint → sprint_race → yf2_self_sprint
        assert ctx is not None
        assert ctx["trigger"] == "yf1_sprint"
        # GUA-136 增强：yf1_sprint 应基于推断手牌 = True（6J+22）
        assert ctx["yf1_sprint"] is True

    def test_at3_sprint_true_via_tracker(self):
        """GUA-136：@3 推断手牌有冲刺能力 → @3_sprint=True"""
        # enemy_pos = 1（@1，greaterPos）
        card_state = {
            "S8": [1, 1], "H8": [1, 1], "D8": [1, 1], "C8": [1, 1],  # 4 张 8 给 @1
            "S2": [1, 1],  # 1 张 2 给 @1
            # yf1 (pos=2) 没有牌 → yf1_sprint=False
            # yf2 (pos=0) 用 ANCHOR 但 hand_cards 改 6 张无炸弹
            "S7": [0, 4], "H7": [0, 4], "D7": [0, 4],
            "S9": [0, 4], "H9": [0, 4], "D9": [0, 4],
        }
        tracker = MockMemoryTracker(hand_counts={0: 6, 1: 6, 2: 0, 3: 10}, card_state=card_state)
        gs = _build_state(
            hand_cards=["S7", "H7", "D7", "S9", "H9", "D9"],  # 6 张无炸弹
            enemy_finish_type="Scatter",
            enemy_remaining=10,
            teammate_remaining=10,  # yf1 不在 sprint_race 范围
            memory_tracker=tracker,
        )
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        ctx = d._is_double_second_priority_scenario(gs, ec)
        # yf1 (pos=2) remaining=10 > 6 → sprint_race 不命中
        # yf2 (pos=0) remaining=6 ≤ 6 + yf2_sprint=False → yf2_self_sprint 也跳过
        # → 最后走 C2/C4 判定？finish=Scatter 不是 bomb_family → 走 yf2_self_sprint？
        # 实际上 finish=Scatter + yf2_remaining=6 ≥ 5 → yf2_self_sprint 触发
        # 因 yf1_sprint=False（推断 pos=2 无手牌）+ at3_sprint=True → 关键验证 at3_sprint
        assert ctx is not None
        assert ctx["@3_sprint"] is True

    def test_at3_sprint_false_no_tracker(self):
        """GUA-136 兼容：无 MemoryTracker → @3_sprint 保守 False"""
        gs = _build_state(
            hand_cards=["S7", "H7", "D7", "S8", "H8", "D8"],  # 6 张无炸弹
            enemy_finish_type="Scatter",
            enemy_remaining=10,
            teammate_remaining=6,
            # 无 memory_tracker
        )
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        ctx = d._is_double_second_priority_scenario(gs, ec)
        assert ctx is not None
        assert ctx["trigger"] == "sprint_race"
        # 无 tracker → @3_sprint 保守 False
        assert ctx["@3_sprint"] is False


# ═══════════════════════════════════════════════════════
#  Hook 集成（保留 GUA-135 集成验证）
# ═══════════════════════════════════════════════════════

class TestHookIntegration:
    def test_q1_block_enemy_no_crash_with_tracker(self):
        """GUA-136 集成：注入 MemoryTracker 不抛错"""
        tracker = MockMemoryTracker(
            hand_counts={1: 10, 3: 10},
            card_state={
                "SJ": [1, 1], "HJ": [1, 1], "DJ": [1, 1],
                "S2": [1, 1], "D2": [1, 1],
            },
        )
        gs = _build_state(
            enemy_finish_type="StraightFlush",
            memory_tracker=tracker,
        )
        gs = _preprocess(gs)
        ec = gs["_endgame_context"]
        d = EndgameDecider()
        # 不抛错即 OK
        result = d._q1_block_enemy(gs, gs["actionList"], ec)
        assert result is not None or result is None
