# -*- coding: utf-8 -*-
"""
GUA-NEW L2 牌型推断：炸弹候选推断

目标：从已出牌序列推断对手/队友可能持有的炸弹组合。

推断逻辑（基于排除法 + 牌型组合数学）：

  1. **直接排除**：
     - 4 张同牌已出 → 该牌型不可能是炸弹
     - 3 张同牌 + 1 张被对方打过（同 rank） → 4 张同牌不可能
     - 王炸（HR×2 + SB×2）若 4 张都已出 → 王炸不可能

  2. **间接推断**：
     - 某 rank 已出 2 张：剩余 2 张可能在 (我, 队友, opp1, opp2) 中任意分布
     - 某 rank 已出 3 张：剩余 1 张位置确定 = "唯一可能持有者"
     - 某 rank 已出 4 张：该 rank 已穷尽，无炸弹可能

  3. **概率加权**（可选 L3 进阶）：
     - 对手出牌风格（如频繁拆对 = 大牌倾向 → 高 rank 炸弹概率高）
     - 牌型组合推断（同花顺需 5 张同花 → 推断可能）

返回：BombCandidate 列表，按 probability 降序。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class BombCandidate:
    """炸弹候选：对手/队友可能持有的炸弹组合。

    Attributes:
        bomb_type: "four_of_a_kind" / "straight_flush" / "two_trips" / "joker_bomb"
        rank: 牌型点数（"A"/"K"/.../王炸时为 None）
        probability: 推断概率 [0.0, 1.0]
        reasoning: 推断依据（可读字符串）
    """
    bomb_type: str
    rank: Optional[str]
    probability: float
    reasoning: str

    def __repr__(self) -> str:
        type_str = self.bomb_type
        if self.rank:
            type_str += f"({self.rank})"
        return f"BombCandidate[{type_str}, p={self.probability:.2f}, {self.reasoning}]"


@dataclass
class BombInference:
    """炸弹推断器状态。

    Attributes:
        my_seat: 自己席号
        partner_seat: 队友席号
        opp1_seat, opp2_seat: 对手两个席号
        cur_rank: 当前级牌点数
        hand_counts: {seat: 剩余牌数}
        played_count_by_rank: {rank: {seat: 已出该 rank 张数}}（按席分）
    """

    my_seat: int
    partner_seat: int
    opp1_seat: int
    opp2_seat: int
    cur_rank: str
    hand_counts: Dict[int, int]
    played_count_by_rank: Dict[str, Dict[int, int]] = field(default_factory=dict)

    @property
    def opp_seats(self) -> List[int]:
        return [self.opp1_seat, self.opp2_seat]

    def total_cards_remaining_for_seat(self, seat: int) -> int:
        return self.hand_counts.get(seat, 27)

    def infer_four_of_a_kind_bombs(self) -> List[BombCandidate]:
        """推断可能持有的"四张同牌"型炸弹。

        排除逻辑：
          - 已出 4 张某 rank → 该 rank 不可能是炸弹
          - 已出 3 张某 rank → 该 rank 仅有 1 张剩余，不可能是 4 张炸弹
        剩余分布：
          - 已出 0/1/2 张某 rank → 剩余 2/1/0 张在 4 席中分布
        """
        candidates: List[BombCandidate] = []
        RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
        for rank in RANKS:
            played_by_seat = self.played_count_by_rank.get(rank, {})
            total_played = sum(played_by_seat.values())
            if total_played >= 4:
                # 该 rank 已出 4 张，无 4 张炸弹可能
                continue
            if total_played >= 3:
                # 剩余 1 张不可能是 4 张炸弹
                continue

            remaining_copies = 2 - total_played  # 剩余副本数

            # 推断每席可能的持有数
            seat_probs: Dict[int, float] = {}
            for seat in [self.my_seat, self.partner_seat, self.opp1_seat, self.opp2_seat]:
                hand_size = self.hand_counts.get(seat, 27)
                if hand_size <= 0:
                    seat_probs[seat] = 0.0
                    continue
                # 简化概率：剩余副本数 / 总剩余牌数
                # 实际应基于对手已出的具体牌
                total_remaining_cards = sum(self.hand_counts.get(s, 27) for s in [self.my_seat, self.partner_seat, self.opp1_seat, self.opp2_seat])
                if total_remaining_cards <= 0:
                    seat_probs[seat] = 0.0
                    continue
                seat_probs[seat] = hand_size / total_remaining_cards

            # 推断对手持有该 rank 全部 remaining_copies 张的概率
            # P(opp 有 4 张该 rank) = sum_{opp} P(opp 有 2 张该 rank)
            # 简化：仅当 remaining_copies == 2 且 opp 持有 ≥ 2 张时考虑
            if remaining_copies == 2:
                for opp_seat in self.opp_seats:
                    opp_hand = self.hand_counts.get(opp_seat, 27)
                    # 假设所有 opp_hand 张牌里期望 remaining_copies 张该 rank
                    expected_count = remaining_copies * opp_hand / max(1, sum(self.hand_counts.values()))
                    # 概率 = opp 持有 ≥ 2 张的概率（泊松近似）
                    # 简化：expected_count >= 1.5 时高概率，否则低概率
                    if expected_count >= 1.5:
                        prob = min(0.7, expected_count / 2.0)
                    else:
                        prob = expected_count / 4.0
                    if prob > 0.1:
                        candidates.append(BombCandidate(
                            bomb_type="four_of_a_kind",
                            rank=rank,
                            probability=prob,
                            reasoning=f"rank={rank} 已出 {total_played} 张，opp{opp_seat} 期望持 {expected_count:.2f} 张",
                        ))

        # 按概率降序排序
        candidates.sort(key=lambda c: -c.probability)
        return candidates

    def infer_joker_bomb(self) -> List[BombCandidate]:
        """推断王炸（HR×2 + SB×2）。

        排除逻辑：
          - HR 已出 2 张或 SB 已出 2 张 → 王炸不可能
        概率推断：
          - HR 剩 0 张 + SB 剩 0 张 → 王炸存在
          - 4 王分布 (HR×2 + SB×2) 在 4 席中可能位置
        """
        hr_played_by_seat = self.played_count_by_rank.get("HR", {})
        sb_played_by_seat = self.played_count_by_rank.get("SB", {})
        total_hr_played = sum(hr_played_by_seat.values())
        total_sb_played = sum(sb_played_by_seat.values())

        if total_hr_played >= 2 or total_sb_played >= 2:
            return []  # 王炸不可能

        # 剩余 2 张 HR + 2 张 SB，共 4 张
        # 推断谁可能持有完整王炸（4 张全在手）
        candidates: List[BombCandidate] = []
        for seat in [self.my_seat, self.partner_seat, self.opp1_seat, self.opp2_seat]:
            hand_size = self.hand_counts.get(seat, 27)
            if hand_size < 4:
                continue
            # 简化概率：hand_size 越大，王炸在手概率越高
            prob = min(0.6, hand_size / 27.0 * 0.4)
            if prob > 0.1:
                candidates.append(BombCandidate(
                    bomb_type="joker_bomb",
                    rank=None,
                    probability=prob,
                    reasoning=f"seat={seat} 手牌 {hand_size} 张，王炸 4 张全在手概率 {prob:.2f}",
                ))

        candidates.sort(key=lambda c: -c.probability)
        return candidates

    def infer_straight_flush(self) -> List[BombCandidate]:
        """推断同花顺炸弹（5+ 张同花顺）。

        简化：不做精确推断，仅返回低概率候选（需配合 NN）。
        """
        # 概率极低（5+ 张同花需同 rank 5 张），仅当 opp 手牌 > 15 张时考虑
        candidates: List[BombCandidate] = []
        for opp_seat in self.opp_seats:
            hand_size = self.hand_counts.get(opp_seat, 27)
            if hand_size < 10:
                continue
            # 13 个 rank × 4 花色 = 52 张，每张 rank 同花顺概率 ~ 4/52 ≈ 0.077
            # 持有 5 张同花的同 rank 概率极低，约 0.001
            prob = 0.02 if hand_size > 20 else 0.01
            candidates.append(BombCandidate(
                bomb_type="straight_flush",
                rank=None,
                probability=prob,
                reasoning=f"opp{opp_seat} 手牌 {hand_size} 张，同花顺低概率（约 {prob:.2f}）",
            ))
        return candidates

    def infer_two_trips(self) -> List[BombCandidate]:
        """推断钢板（三带对 / Two Trips）炸弹。

        需要 2 个三张同牌（如 333+444）。
        简化：检测已出的三张组合（剩 0 张副本）排除，否则给低概率候选。
        """
        # 简化：不精确推断，返回 0 概率候选（Phase 2 扩展）
        return []

    def infer_all(self) -> List[BombCandidate]:
        """推断所有可能炸弹类型，合并返回（按 probability 降序）。"""
        all_candidates: List[BombCandidate] = []
        all_candidates.extend(self.infer_four_of_a_kind_bombs())
        all_candidates.extend(self.infer_joker_bomb())
        all_candidates.extend(self.infer_straight_flush())
        all_candidates.extend(self.infer_two_trips())
        all_candidates.sort(key=lambda c: -c.probability)
        return all_candidates
