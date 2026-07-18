# -*- coding: utf-8 -*-
"""
GUA-NEW L3 角色意图推断

目标：从出牌序列 + 剩余牌数推断：
  - 对手角色（主攻/助攻/超弱/防守）
  - 对手冲刺窗口（剩牌 ≤ 5 且意图明显）
  - 队友送牌窗口（剩牌 1-2 张）
  - 我出牌被接风险（can_be_suppressed）
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RoleEstimate:
    """角色估计。

    Attributes:
        seat: 席号
        role: "main_attack" / "assist" / "super_weak" / "defend" / "unknown"
        confidence: 置信度 [0.0, 1.0]
        reasoning: 推断依据
    """
    seat: int
    role: str
    confidence: float
    reasoning: str

    def __repr__(self) -> str:
        return f"RoleEstimate[seat={self.seat}, role={self.role}, conf={self.confidence:.2f}]"


@dataclass
class SprintWindow:
    """冲刺窗口。

    Attributes:
        seat: 席号
        hand_size: 当前剩余牌数
        is_active: 是否处于冲刺状态（剩 ≤ 5 张）
        turn_estimate: 估计还需 N 轮出完
    """
    seat: int
    hand_size: int
    is_active: bool
    turn_estimate: int

    def __repr__(self) -> str:
        return f"SprintWindow[seat={self.seat}, hand={self.hand_size}, active={self.is_active}, turn={self.turn_estimate}]"


@dataclass
class RoleInferencer:
    """角色意图推断器。

    Attributes:
        my_seat: 自己席号
        partner_seat: 队友席号
        opp1_seat, opp2_seat: 对手两个席号
        hand_counts: {seat: 剩余牌数}
        my_position_in_order: 我在 4 席中的位置（0=头游风险，1=二游...）
    """
    my_seat: int
    partner_seat: int
    opp1_seat: int
    opp2_seat: int
    hand_counts: Dict[int, int] = field(default_factory=dict)
    my_position_in_order: int = 0  # 由 result.order 提供

    @property
    def opp_seats(self) -> List[int]:
        return [self.opp1_seat, self.opp2_seat]

    def infer_role(self, seat: int, play_history: Optional[List[Dict]] = None) -> RoleEstimate:
        """推断某席的角色。

        推断逻辑（按 V 系列 Guard 角色体系）：
          - 头游风险 + 剩余牌数 1-3：super_weak（冲刺求头游）
          - 队友剩牌 > 我 + 我领出：main_attack
          - 队友剩牌 < 我 + 我跟牌：assist
          - 手中无大牌（< 5 张 + 无王炸）：defend
        """
        hand_size = self.hand_counts.get(seat, 27)
        play_history = play_history or []

        # 简化推断（Phase 2 接入 NN + 出牌风格）
        if hand_size <= 3:
            return RoleEstimate(
                seat=seat,
                role="super_weak",
                confidence=0.7,
                reasoning=f"剩 {hand_size} 张，进入冲刺窗口",
            )
        elif hand_size <= 8:
            return RoleEstimate(
                seat=seat,
                role="main_attack",
                confidence=0.5,
                reasoning=f"剩 {hand_size} 张，可能冲刺头游",
            )
        elif hand_size >= 20:
            return RoleEstimate(
                seat=seat,
                role="defend",
                confidence=0.4,
                reasoning=f"剩 {hand_size} 张，仍有大量手牌，倾向防守",
            )
        else:
            return RoleEstimate(
                seat=seat,
                role="assist",
                confidence=0.3,
                reasoning=f"剩 {hand_size} 张，角色未明",
            )

    def infer_all_roles(self, play_history: Optional[List[Dict]] = None) -> Dict[int, RoleEstimate]:
        """推断所有席的角色。"""
        result: Dict[int, RoleEstimate] = {}
        for seat in [self.my_seat, self.partner_seat, self.opp1_seat, self.opp2_seat]:
            result[seat] = self.infer_role(seat, play_history)
        return result

    def detect_sprint_window(self, seat: int, play_history: Optional[List[Dict]] = None) -> SprintWindow:
        """检测冲刺窗口（剩牌 ≤ 5 且意图明显）。

        简化：仅基于 hand_size 判断（Phase 2 加出牌风格 + 牌型分布）。
        """
        hand_size = self.hand_counts.get(seat, 27)
        is_active = hand_size <= 5
        # 估计轮数：假设每轮出 1-3 张
        turn_estimate = max(1, hand_size // 2)
        return SprintWindow(
            seat=seat,
            hand_size=hand_size,
            is_active=is_active,
            turn_estimate=turn_estimate,
        )

    def detect_partner_send_window(self, play_history: Optional[List[Dict]] = None) -> Optional[SprintWindow]:
        """检测队友送牌窗口（剩牌 1-2 张 → 队友冲刺头游/二游）。

        Returns:
            SprintWindow 如果队友处于送牌窗口，否则 None
        """
        partner_window = self.detect_sprint_window(self.partner_seat, play_history)
        if partner_window.hand_size <= 2 and partner_window.hand_size > 0:
            return partner_window
        return None

    def can_be_suppressed(
        self,
        my_action_cards: List[str],
        bomb_candidates: List,  # List[BombCandidate]
        play_history: Optional[List[Dict]] = None,
    ) -> Dict[str, float]:
        """评估我出牌被接风险。

        Args:
            my_action_cards: 我打算出的牌（cards 列表）
            bomb_candidates: BombInference.infer_all() 返回的候选炸弹
            play_history: 出牌历史（用于分析对手风格）

        Returns:
            {
                "suppression_prob": 0.0-1.0,  # 被压的总概率
                "by_bomb_type": {bomb_type: prob},  # 按炸弹类型分解
                "recommendation": "play" / "hold" / "abandon",  # 行动建议
            }
        """
        # 简化推断：对手可能持有的炸弹 × 我出牌的脆弱度
        my_action_count = len(my_action_cards)
        suppression_prob = 0.0
        by_bomb_type: Dict[str, float] = {}

        for candidate in bomb_candidates:
            # 简化规则：对手炸弹类型对我出牌的压制概率
            if candidate.bomb_type == "four_of_a_kind":
                # 4 张同牌炸弹：压制单张/对子/三张（非炸弹）
                if my_action_count <= 3:
                    p = candidate.probability
                    suppression_prob = max(suppression_prob, p)
                    by_bomb_type[candidate.bomb_type] = max(by_bomb_type.get(candidate.bomb_type, 0), p)
            elif candidate.bomb_type == "joker_bomb":
                # 王炸：压制所有非王炸
                p = candidate.probability
                suppression_prob = max(suppression_prob, p)
                by_bomb_type[candidate.bomb_type] = max(by_bomb_type.get(candidate.bomb_type, 0), p)
            elif candidate.bomb_type == "straight_flush":
                # 同花顺：压制大多数牌型
                p = candidate.probability
                suppression_prob = max(suppression_prob, p)
                by_bomb_type[candidate.bomb_type] = max(by_bomb_type.get(candidate.bomb_type, 0), p)

        # 行动建议
        if suppression_prob >= 0.6:
            recommendation = "abandon"  # 不出
        elif suppression_prob >= 0.3:
            recommendation = "hold"  # 持有，改其他牌
        else:
            recommendation = "play"  # 安全出

        return {
            "suppression_prob": suppression_prob,
            "by_bomb_type": by_bomb_type,
            "recommendation": recommendation,
        }

    def my_hand_safety_score(self, my_hand: List[str]) -> float:
        """计算我手牌安全度（被接牌风险，0=完全安全，1=必被接）。

        简化：基于手牌结构和剩余大牌数。
        """
        if not my_hand:
            return 0.0

        # 简化启发式：
        # - 王/级牌越多，安全度越高（不易被接）
        # - 单张小牌越多，安全度越低
        rank_counter: Dict[str, int] = {}
        for card in my_hand:
            rank = card[1:] if len(card) >= 2 else card
            rank_counter[rank] = rank_counter.get(rank, 0) + 1

        high_cards = sum(rank_counter.get(r, 0) for r in ["A", "K", "Q", "J", "HR", "SB"])
        low_cards = sum(rank_counter.get(r, 0) for r in ["2", "3", "4", "5"])
        total = len(my_hand)

        # 安全度 = (高牌占比 - 低牌占比)
        safety = (high_cards - low_cards) / total
        return max(0.0, min(1.0, safety + 0.5))
