# -*- coding: utf-8 -*-
"""
GUA-223 / CardCountingNetwork-训练方案 §8 Phase 0 ④
heuristic 规则 ⑨ 草案骨架 + 5 项等价性 pytest

关联：GUA-223 / GUA-057 / GUA-224（Phase 2 接入点）

5 项等价性（pytest 锁行为）：
  ① belief_state=None → 降级到 rest_distribution
  ② belief_state 低置信度（L2 < threshold） → 降级
  ③ 降级路径无 rest_distribution → 返回 0.0 中性值
  ④ belief_state 含 NaN/Inf → 降级（不抛异常）
  ⑤ 主路径返回 ∈ [-1.0, +1.0]，0.5 阈值化打分
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.v.nn.features.belief_bomb_risk import (
    BELIEF_CONFIDENCE_THRESHOLD,
    heuristic_belief_bomb_risk,
)


class TestFallbackPath:
    """降级路径等价性（5 项硬约束）"""

    def test_降级_1_belief_state_None(self):
        """belief_state=None → 用 rest_distribution 计算。"""
        rest_dist = {"A": 0.9, "K": 0.3}
        risk = heuristic_belief_bomb_risk(
            action_cards=["HA"],
            belief_state=None,
            rest_distribution=rest_dist,
        )
        # rest_dist["A"]=0.9 > 0.8 → risk = 2; norm = 2/2 = 1; clip(2*1-1, -1, 1) = 1
        assert risk == pytest.approx(1.0, abs=0.01)

    def test_降级_2_low_confidence_L2(self):
        """belief_state L2 norm 低于阈值 → 降级。"""
        # uniform 0.5 → L2 = sqrt(108*0.25) ≈ 5.2 > threshold，OK
        # 但全 0 → L2 = 0 < threshold → 降级
        belief = np.zeros(108, dtype=np.float32)
        rest_dist = {"A": 0.6}  # 中等风险
        risk = heuristic_belief_bomb_risk(
            action_cards=["HA"],
            belief_state=belief,
            rest_distribution=rest_dist,
        )
        # 降级路径：rest_dist["A"]=0.6 > 0.5 → risk=1; norm = 1/2 = 0.5; clip(0)=0
        assert risk == pytest.approx(0.0, abs=0.01)

    def test_降级_3_无_rest_distribution(self):
        """belief_state=None + rest_distribution=None → 返回 0.0 中性值（不抛异常）。"""
        risk = heuristic_belief_bomb_risk(
            action_cards=["HA"],
            belief_state=None,
            rest_distribution=None,
        )
        assert risk == 0.0

    def test_降级_4_belief_含_NaN_Inf(self):
        """belief_state 含 NaN/Inf → 降级（不抛异常）。"""
        belief = np.ones(108, dtype=np.float32)
        belief[10] = np.nan
        rest_dist = {"A": 0.7}
        # 不应抛异常
        risk = heuristic_belief_bomb_risk(
            action_cards=["HA"],
            belief_state=belief,
            rest_distribution=rest_dist,
        )
        assert isinstance(risk, float)
        assert -1.0 <= risk <= 1.0

    def test_降级_5_belief_shape_错误(self):
        """belief_state shape ≠ (108,) → 降级。"""
        belief = np.ones(100, dtype=np.float32)
        risk = heuristic_belief_bomb_risk(
            action_cards=["HA"],
            belief_state=belief,
            rest_distribution={"A": 0.9},
        )
        # shape 错 → 降级 → risk = 1.0
        assert risk == pytest.approx(1.0, abs=0.01)


class TestMainPath:
    """主路径行为校验"""

    def test_主路径返回值范围(self):
        """主路径返回值 ∈ [-1.0, +1.0]。"""
        belief = np.full(108, 0.5, dtype=np.float32)
        risk = heuristic_belief_bomb_risk(
            action_cards=["HA", "HK", "HQ"],
            belief_state=belief,
            rest_distribution=None,
        )
        assert -1.0 <= risk <= 1.0

    def test_主路径_高_belief_高风险(self):
        """belief 高概率（REST=对手有牌）→ 风险分 > 0。"""
        belief = np.zeros(108, dtype=np.float32)
        belief[54:108] = 0.9  # 第 2 副本 REST 概率 0.9
        risk = heuristic_belief_bomb_risk(
            action_cards=["HA", "HK", "HQ"],
            belief_state=belief,
            rest_distribution=None,
        )
        # 风险应该 > 0
        assert risk > 0

    def test_主路径_空_action_cards(self):
        """空 action_cards → 返回 0.0。"""
        belief = np.full(108, 0.5, dtype=np.float32)
        risk = heuristic_belief_bomb_risk(
            action_cards=[],
            belief_state=belief,
            rest_distribution=None,
        )
        assert risk == 0.0