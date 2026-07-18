# -*- coding: utf-8 -*-
"""
GUA-057 Phase 0 任务 5：heuristic 规则 ⑨ 等价性 pytest

测试覆盖方案 v2 §7.2 5 项场景：
  1. belief=None（降级路径）→ 0.0
  2. belief 全 0 → 0.0
  3. belief 对手高概率持更大炸弹 → -200
  4. belief 对手高概率持同点炸弹 → -100
  5. 末局 + 高信念炸弹风险 → -300

注意：测试用 action_rank=5（小牌），让 _get_bomb_slots_with_rank_gt(5) 选中
      rank>5 的所有 slot（总和 > 0.5），让 _get_bomb_slots_with_rank_eq(5) 选中
      rank=5 的所有 slot（总和 > 0.3）。

slot 索引约定（_get_bomb_slots_with_rank_gt 实现）：
  rank_idx("5") = 3（_RANK_ORDER[3]="5"）
  range(4, 13) = 9 个 rank (5,6,7,8,9,T,J,Q,K,A)
  每个 rank 8 slot (4 花色 × 2 副本) = 72
  + 王炸 (SB, HR) × 2 副本 = 4
  = 76

运行：
  pytest tests/test_gua057_belief_bomb_risk.py -v
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.v.nn.features.counting.heuristic_bomb_risk import (
    _heuristic_belief_bomb_risk,
    _get_bomb_slots_with_rank_gt,
    _get_bomb_slots_with_rank_eq,
    OPPONENT_HAND_IDX,
)


def test_belief_none_returns_zero():
    action = {"type": "Bomb", "cards": ["SA", "SA", "SA", "SA"], "rank": "A"}
    score = _heuristic_belief_bomb_risk(action, belief_vector=None)
    assert score == 0.0


def test_belief_none_pass_action_returns_zero():
    action = {"type": "PASS", "cards": [], "rank": "PASS"}
    score = _heuristic_belief_bomb_risk(action, belief_vector=None)
    assert score == 0.0


def test_belief_zeros_returns_zero():
    belief = np.zeros((108, 3), dtype=np.float32)
    action = {"type": "Bomb", "cards": ["SA", "SA", "SA", "SA"], "rank": "A"}
    score = _heuristic_belief_bomb_risk(action, belief_vector=belief)
    assert score == 0.0


def test_belief_zeros_non_bomb_action_returns_zero():
    belief = np.zeros((108, 3), dtype=np.float32)
    action = {"type": "Single", "cards": ["S5"], "rank": "5"}
    score = _heuristic_belief_bomb_risk(action, belief_vector=belief)
    assert score == 0.0


def test_opp_higher_bomb_high_prob_triggers_minus_200():
    """action_rank=5，belief 让 rank>5 slot 总和 > 0.5 → 触发规则 1 扣 200。"""
    belief = np.zeros((108, 3), dtype=np.float32)
    belief[:, OPPONENT_HAND_IDX] = 0.02
    action = {"type": "Bomb", "cards": ["S5", "H5", "D5", "C5"], "rank": "5"}
    game_state = {"handCards": ["S5"] * 10, "stage": "play"}
    score = _heuristic_belief_bomb_risk(action, belief_vector=belief, game_state=game_state)
    assert score == pytest.approx(-200.0), f"expected -200.0, got {score}"


def test_opp_same_rank_bomb_triggers_minus_100():
    """仅 rank=5 slot 总和 > 0.3（rank>5 总和 < 0.5）→ 触发规则 2 扣 100。"""
    belief = np.zeros((108, 3), dtype=np.float32)
    belief[:, OPPONENT_HAND_IDX] = 0.001
    rank5_slots = _get_bomb_slots_with_rank_eq("5")
    belief[rank5_slots, OPPONENT_HAND_IDX] = 0.04
    action = {"type": "Single", "cards": ["S5"], "rank": "5"}
    game_state = {"handCards": ["S5"] * 10, "stage": "play"}
    score = _heuristic_belief_bomb_risk(action, belief_vector=belief, game_state=game_state)
    assert score == pytest.approx(-100.0), f"expected -100.0, got {score}"


def test_endgame_high_bomb_risk_triggers_minus_300():
    """末局（5 张）+ 高信念更大炸弹 → 200 * 1.5 = -300。"""
    belief = np.zeros((108, 3), dtype=np.float32)
    belief[:, OPPONENT_HAND_IDX] = 0.02
    action = {"type": "Bomb", "cards": ["S5", "H5", "D5", "C5"], "rank": "5"}
    game_state = {"handCards": ["S5", "H6", "D7", "C8", "S9"], "stage": "play"}
    score = _heuristic_belief_bomb_risk(action, belief_vector=belief, game_state=game_state)
    assert score == pytest.approx(-300.0), f"expected -300.0, got {score}"


def test_belief_wrong_shape_returns_zero():
    belief = np.zeros((50, 3), dtype=np.float32)
    action = {"type": "Bomb", "cards": ["SA", "SA", "SA", "SA"], "rank": "A"}
    score = _heuristic_belief_bomb_risk(action, belief_vector=belief)
    assert score == 0.0


def test_belief_none_type_returns_zero():
    action = {"type": "Bomb", "cards": ["SA", "SA", "SA", "SA"], "rank": "A"}
    score = _heuristic_belief_bomb_risk(action, belief_vector=[0.5] * 108)
    assert score == 0.0


def test_bomb_slots_with_rank_gt_5_includes_9_ranks():
    """rank=5 时 higher slots = 9 ranks × 8 slot + 王炸 4 = 76."""
    slots = _get_bomb_slots_with_rank_gt("5")
    assert slots.size == 76, f"expected 76 slots, got {slots.size}"


def test_bomb_slots_with_rank_eq_returns_8_slots():
    """rank=5 时同 rank slot = 8 个（4 花色 × 2 副本）。"""
    slots = _get_bomb_slots_with_rank_eq("5")
    assert slots.size == 8


def test_bomb_slots_with_rank_gt_a_is_just_jokers():
    """rank=A 时 higher slots 只有王炸（4 个 slot）。"""
    slots = _get_bomb_slots_with_rank_gt("A")
    assert slots.size == 4
