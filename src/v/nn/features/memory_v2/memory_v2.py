# -*- coding: utf-8 -*-
"""
GUA-NEW 实战级记忆模块 v2（主类）

在 MemoryTracker 基础上叠加：
  L2 牌型推断（bomb_inference.BombInference）
  L3 角色意图推断（role_intent.RoleInferencer）

设计目标：从"知道每张牌归谁"升级到"知道对手/队友手里有什么牌型 + 在组什么"。

Usage:
    from src.v.nn.features.memory_v2 import MemoryV2
    mv2 = MemoryV2(my_seat=0, cur_rank="2")
    mv2.update_from_actions(actions, hand_counts, play_history)
    bomb_candidates = mv2.get_bomb_candidates()
    roles = mv2.get_role_estimates()
    safety = mv2.check_my_action_safety(my_action_cards)
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple

from .bomb_inference import BombInference, BombCandidate
from .role_intent import RoleInferencer, RoleEstimate, SprintWindow


class MemoryV2:
    """实战级记忆模块 v2。

    Attributes:
        my_seat: 自己席号
        cur_rank: 当前级牌
    """

    def __init__(self, my_seat: int, cur_rank: str):
        self.my_seat = my_seat
        self.cur_rank = cur_rank
        self.partner_seat = (my_seat + 2) % 4
        self.opp_seats = [s for s in [0, 1, 2, 3] if s != my_seat and s != self.partner_seat]
        self.hand_counts: Dict[int, int] = {s: 27 for s in [0, 1, 2, 3]}
        self.played_count_by_rank: Dict[str, Dict[int, int]] = {}
        self.play_history: List[Dict] = []
        self._bomb_inference: Optional[BombInference] = None
        self._role_inferencer: Optional[RoleInferencer] = None

    def update_hand_counts(self, hand_counts: Dict[int, int]) -> None:
        """更新各席剩余牌数（来自游戏状态 publicInfo[i].rest）。"""
        self.hand_counts.update(hand_counts)

    def update_from_actions(self, actions: List[Dict]) -> None:
        """从 actions 序列更新出牌统计。

        Args:
            actions: actions 列表，每条含 cur_pos, cur_action (含 cards)
        """
        for a in actions:
            cur_pos = a.get("cur_pos", -1)
            cur_action = a.get("cur_action", [])
            if isinstance(cur_action, list) and len(cur_action) >= 3:
                third = cur_action[2]
                if isinstance(third, list):
                    for card in third:
                        rank = self._card_to_rank(card)
                        if rank not in self.played_count_by_rank:
                            self.played_count_by_rank[rank] = {}
                        self.played_count_by_rank[rank][cur_pos] = self.played_count_by_rank[rank].get(cur_pos, 0) + 1
        self.play_history = actions

    def _card_to_rank(self, card: str) -> str:
        """card -> rank（去掉花色）。"""
        if card in ("HR", "SB"):
            return card
        if len(card) >= 2:
            return card[1:]
        return card

    def _build_inferencers(self) -> None:
        """构建内部 inferencer。"""
        self._bomb_inference = BombInference(
            my_seat=self.my_seat,
            partner_seat=self.partner_seat,
            opp1_seat=self.opp_seats[0],
            opp2_seat=self.opp_seats[1],
            cur_rank=self.cur_rank,
            hand_counts=self.hand_counts,
            played_count_by_rank=self.played_count_by_rank,
        )
        self._role_inferencer = RoleInferencer(
            my_seat=self.my_seat,
            partner_seat=self.partner_seat,
            opp1_seat=self.opp_seats[0],
            opp2_seat=self.opp_seats[1],
            hand_counts=self.hand_counts,
        )

    def get_bomb_candidates(self) -> List[BombCandidate]:
        """推断对手/队友可能持有的所有炸弹候选。"""
        self._build_inferencers()
        assert self._bomb_inference is not None
        return self._bomb_inference.infer_all()

    def get_bomb_candidates_for_opp(self, opp_seat: int) -> List[BombCandidate]:
        """推断特定对手可能持有的炸弹候选。"""
        all_candidates = self.get_bomb_candidates()
        return [c for c in all_candidates if f"opp{opp_seat}" in c.reasoning or "opp" in c.reasoning]

    def get_role_estimates(self) -> Dict[int, RoleEstimate]:
        """推断所有席的角色。"""
        self._build_inferencers()
        assert self._role_inferencer is not None
        return self._role_inferencer.infer_all_roles(self.play_history)

    def get_role(self, seat: int) -> RoleEstimate:
        """推断某席的角色。"""
        self._build_inferencers()
        assert self._role_inferencer is not None
        return self._role_inferencer.infer_role(seat, self.play_history)

    def get_sprint_window(self, seat: int) -> SprintWindow:
        """检测某席的冲刺窗口。"""
        self._build_inferencers()
        assert self._role_inferencer is not None
        return self._role_inferencer.detect_sprint_window(seat, self.play_history)

    def is_partner_send_window(self) -> Optional[SprintWindow]:
        """检测队友是否处于送牌窗口。"""
        self._build_inferencers()
        assert self._role_inferencer is not None
        return self._role_inferencer.detect_partner_send_window(self.play_history)

    def check_my_action_safety(self, my_action_cards: List[str]) -> Dict:
        """检查我出牌是否会被压。

        Args:
            my_action_cards: 我打算出的牌（cards 列表）

        Returns:
            {
                "suppression_prob": 0.0-1.0,
                "by_bomb_type": {...},
                "recommendation": "play" / "hold" / "abandon",
                "partner_can_suppress": bool,  # 队友是否能压我
            }
        """
        self._build_inferencers()
        assert self._role_inferencer is not None
        bomb_candidates = self.get_bomb_candidates()
        safety = self._role_inferencer.can_be_suppressed(my_action_cards, bomb_candidates, self.play_history)

        # 队友压制检测：如果队友可能持有更大牌型，避免送牌给对手
        partner_window = self.is_partner_send_window()
        safety["partner_can_suppress"] = partner_window is not None

        return safety

    def summary(self) -> Dict:
        """返回当前所有推断汇总（用于日志/调试）。"""
        self._build_inferencers()
        bomb_candidates = self.get_bomb_candidates()
        roles = self.get_role_estimates()
        return {
            "my_seat": self.my_seat,
            "cur_rank": self.cur_rank,
            "hand_counts": self.hand_counts,
            "bomb_candidates_top5": [
                {
                    "type": c.bomb_type,
                    "rank": c.rank,
                    "prob": c.probability,
                    "reason": c.reasoning,
                }
                for c in bomb_candidates[:5]
            ],
            "roles": {seat: f"{r.role} (conf={r.confidence:.2f})" for seat, r in roles.items()},
        }
