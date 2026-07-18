# -*- coding: utf-8 -*-
"""
GUA-NEW MemoryV2 pytest

测试覆盖：
  L2 牌型推断：
    - test_bomb_4_of_a_kind_basic - 4 张同牌基本推断
    - test_bomb_4_of_a_kind_3_played_excluded - 已出 3 张排除
    - test_bomb_4_of_a_kind_4_played_excluded - 已出 4 张排除
    - test_joker_bomb_basic - 王炸推断
    - test_joker_bomb_excluded_when_played - 王炸排除
    - test_straight_flush_low_prob - 同花顺低概率
  L3 角色意图推断：
    - test_role_super_weak_when_3_cards - 剩 3 张 = super_weak
    - test_role_main_attack_when_8_cards - 剩 8 张 = main_attack
    - test_sprint_window_active_when_le_5 - 剩 5 张触发冲刺
    - test_partner_send_window_when_2_cards - 队友剩 2 张触发送牌
  L4 决策反馈：
    - test_check_my_action_safety_high_risk - 高风险牌不出
    - test_check_my_action_safety_low_risk - 低风险牌出
    - test_my_hand_safety_score - 安全度评分
  MemoryV2 集成：
    - test_update_from_actions_basic - actions 更新
    - test_summary_includes_bombs_and_roles - summary 输出完整
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.v.nn.features.memory_v2 import (
    MemoryV2,
    BombInference,
    BombCandidate,
    RoleInferencer,
    RoleEstimate,
    SprintWindow,
)


# ─── L2 牌型推断 ─────────────────────────────────────────────

def test_bomb_4_of_a_kind_basic():
    """基本场景：未出任何牌，对手可能持有炸弹。"""
    bi = BombInference(
        my_seat=0, partner_seat=2, opp1_seat=1, opp2_seat=3,
        cur_rank="2",
        hand_counts={0: 27, 1: 27, 2: 27, 3: 27},
        played_count_by_rank={},
    )
    candidates = bi.infer_four_of_a_kind_bombs()
    # 13 个 rank 都应有候选
    assert len(candidates) > 0
    # 概率应 < 1（不是确定）
    for c in candidates:
        assert 0.0 <= c.probability <= 1.0


def test_bomb_4_of_a_kind_3_played_excluded():
    """已出 3 张的 rank 排除 4 张炸弹可能。"""
    bi = BombInference(
        my_seat=0, partner_seat=2, opp1_seat=1, opp2_seat=3,
        cur_rank="2",
        hand_counts={0: 27, 1: 27, 2: 27, 3: 27},
        played_count_by_rank={"A": {0: 1, 1: 1, 2: 1}},  # A 已出 3 张
    )
    candidates = bi.infer_four_of_a_kind_bombs()
    # A 不应在候选中
    for c in candidates:
        assert c.rank != "A"


def test_bomb_4_of_a_kind_4_played_excluded():
    """已出 4 张的 rank 排除 4 张炸弹可能。"""
    bi = BombInference(
        my_seat=0, partner_seat=2, opp1_seat=1, opp2_seat=3,
        cur_rank="2",
        hand_counts={0: 27, 1: 27, 2: 27, 3: 27},
        played_count_by_rank={"K": {0: 2, 1: 2}},  # K 已出 4 张
    )
    candidates = bi.infer_four_of_a_kind_bombs()
    for c in candidates:
        assert c.rank != "K"


def test_joker_bomb_basic():
    """王炸基本推断。"""
    bi = BombInference(
        my_seat=0, partner_seat=2, opp1_seat=1, opp2_seat=3,
        cur_rank="2",
        hand_counts={0: 27, 1: 25, 2: 27, 3: 27},
        played_count_by_rank={},
    )
    candidates = bi.infer_joker_bomb()
    assert len(candidates) > 0


def test_joker_bomb_excluded_when_played():
    """HR 已出 2 张时排除王炸。"""
    bi = BombInference(
        my_seat=0, partner_seat=2, opp1_seat=1, opp2_seat=3,
        cur_rank="2",
        hand_counts={0: 27, 1: 27, 2: 27, 3: 27},
        played_count_by_rank={"HR": {0: 2}},  # HR 已出 2 张
    )
    candidates = bi.infer_joker_bomb()
    assert len(candidates) == 0


def test_straight_flush_low_prob():
    """同花顺推断概率应较低。"""
    bi = BombInference(
        my_seat=0, partner_seat=2, opp1_seat=1, opp2_seat=3,
        cur_rank="2",
        hand_counts={0: 27, 1: 27, 2: 27, 3: 27},
        played_count_by_rank={},
    )
    candidates = bi.infer_straight_flush()
    for c in candidates:
        assert c.probability <= 0.05


# ─── L3 角色意图推断 ─────────────────────────────────────────

def test_role_super_weak_when_3_cards():
    """剩 3 张时角色 = super_weak。"""
    ri = RoleInferencer(
        my_seat=0, partner_seat=2, opp1_seat=1, opp2_seat=3,
        hand_counts={0: 27, 1: 3, 2: 27, 3: 27},
    )
    estimate = ri.infer_role(seat=1)
    assert estimate.role == "super_weak"
    assert estimate.confidence >= 0.6


def test_role_main_attack_when_8_cards():
    """剩 8 张时角色 = main_attack。"""
    ri = RoleInferencer(
        my_seat=0, partner_seat=2, opp1_seat=1, opp2_seat=3,
        hand_counts={0: 27, 1: 8, 2: 27, 3: 27},
    )
    estimate = ri.infer_role(seat=1)
    assert estimate.role == "main_attack"


def test_sprint_window_active_when_le_5():
    """剩 5 张触发冲刺窗口。"""
    ri = RoleInferencer(
        my_seat=0, partner_seat=2, opp1_seat=1, opp2_seat=3,
        hand_counts={0: 27, 1: 5, 2: 27, 3: 27},
    )
    window = ri.detect_sprint_window(seat=1)
    assert window.is_active is True
    assert window.hand_size == 5


def test_partner_send_window_when_2_cards():
    """队友剩 2 张触发送牌窗口。"""
    ri = RoleInferencer(
        my_seat=0, partner_seat=2, opp1_seat=1, opp2_seat=3,
        hand_counts={0: 27, 1: 27, 2: 2, 3: 27},
    )
    window = ri.detect_partner_send_window()
    assert window is not None
    assert window.seat == 2


def test_partner_send_window_none_when_many_cards():
    """队友剩 > 2 张时不应触发送牌窗口。"""
    ri = RoleInferencer(
        my_seat=0, partner_seat=2, opp1_seat=1, opp2_seat=3,
        hand_counts={0: 27, 1: 27, 2: 15, 3: 27},
    )
    window = ri.detect_partner_send_window()
    assert window is None


# ─── L4 决策反馈 ─────────────────────────────────────────────

def test_check_my_action_safety_high_risk():
    """出小单 + 对手可能持有炸弹 → 高风险。"""
    ri = RoleInferencer(
        my_seat=0, partner_seat=2, opp1_seat=1, opp2_seat=3,
        hand_counts={0: 27, 1: 20, 2: 27, 3: 27},
    )
    # 构造高概率炸弹候选
    high_prob_bombs = [
        BombCandidate("four_of_a_kind", "A", 0.8, "opp1 高手牌"),
    ]
    safety = ri.can_be_suppressed(my_action_cards=["S3"], bomb_candidates=high_prob_bombs)
    assert safety["suppression_prob"] >= 0.5
    assert safety["recommendation"] in ("hold", "abandon")


def test_check_my_action_safety_low_risk():
    """出小单 + 对手无炸弹 → 低风险。"""
    ri = RoleInferencer(
        my_seat=0, partner_seat=2, opp1_seat=1, opp2_seat=3,
        hand_counts={0: 27, 1: 27, 2: 27, 3: 27},
    )
    safety = ri.can_be_suppressed(my_action_cards=["S3"], bomb_candidates=[])
    assert safety["suppression_prob"] == 0.0
    assert safety["recommendation"] == "play"


def test_my_hand_safety_score_high_when_jokers():
    """手牌含大小王 → 安全度高。"""
    ri = RoleInferencer(
        my_seat=0, partner_seat=2, opp1_seat=1, opp2_seat=3,
        hand_counts={0: 5, 1: 10, 2: 5, 3: 10},
    )
    my_hand = ["HR", "SB", "SA", "SK", "SQ"]
    score = ri.my_hand_safety_score(my_hand)
    assert score >= 0.7


def test_my_hand_safety_score_low_when_low_cards():
    """手牌全是低牌 → 安全度低。"""
    ri = RoleInferencer(
        my_seat=0, partner_seat=2, opp1_seat=1, opp2_seat=3,
        hand_counts={0: 5, 1: 10, 2: 5, 3: 10},
    )
    my_hand = ["S2", "S3", "S4", "S5", "H2"]
    score = ri.my_hand_safety_score(my_hand)
    assert score <= 0.3


# ─── MemoryV2 集成测试 ────────────────────────────────────────

def test_update_from_actions_basic():
    """从 actions 序列更新出牌统计。"""
    mv2 = MemoryV2(my_seat=0, cur_rank="2")
    actions = [
        {"cur_pos": 0, "cur_action": ["Single", "5", ["S5"]]},
        {"cur_pos": 1, "cur_action": ["Single", "8", ["H8"]]},
        {"cur_pos": 2, "cur_action": ["PASS", "PASS", "PASS"]},
        {"cur_pos": 3, "cur_action": ["Single", "K", ["DK"]]},
    ]
    mv2.update_from_actions(actions)
    assert mv2.played_count_by_rank["5"][0] == 1
    assert mv2.played_count_by_rank["8"][1] == 1
    assert mv2.played_count_by_rank["K"][3] == 1


def test_summary_includes_bombs_and_roles():
    """summary 输出包含炸弹和角色推断。"""
    mv2 = MemoryV2(my_seat=0, cur_rank="2")
    mv2.update_hand_counts({0: 27, 1: 5, 2: 27, 3: 27})
    actions = [
        {"cur_pos": 0, "cur_action": ["Single", "5", ["S5"]]},
        {"cur_pos": 1, "cur_action": ["Bomb", "A", ["SA", "HA", "DA", "CA"]]},  # opp1 出炸弹
    ]
    mv2.update_from_actions(actions)
    summary = mv2.summary()
    assert "bomb_candidates_top5" in summary
    assert "roles" in summary
    assert 1 in summary["roles"]  # opp1


def test_check_my_action_safety_via_memory_v2():
    """MemoryV2.check_my_action_safety 集成测试。"""
    mv2 = MemoryV2(my_seat=0, cur_rank="2")
    mv2.update_hand_counts({0: 27, 1: 20, 2: 27, 3: 27})
    actions = []
    mv2.update_from_actions(actions)
    safety = mv2.check_my_action_safety(["S3"])
    assert "suppression_prob" in safety
    assert "recommendation" in safety
    assert "partner_can_suppress" in safety
