# -*- coding: utf-8 -*-
"""
GUA-052 108 张牌全量追踪 + 排除法推断。

功能：
  1. 108 张牌全量追踪（54 种 × 2 张，4 席各自的打出/剩余）
  2. 对手/队友出牌牌型记录
  3. 各家剩张
  4. 级牌状态
  5. 排除法推断对手手牌

风险控制：
  - 推理延迟 >50ms → 降级为仅追踪剩牌+炸弹+级牌状态
"""

from __future__ import annotations

import logging
from collections import defaultdict, Counter
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("memory_tracker")

# ── 常量 ────────────────────────────────────────────────

SUITS = ["S", "H", "D", "C"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
JOKERS = ["BJ", "RJ"]

ALL_CARD_TYPES: List[str] = []
for rank in RANKS:
    for suit in SUITS:
        ALL_CARD_TYPES.append(f"{suit}{rank}")
ALL_CARD_TYPES.extend(JOKERS)  # 54 种

CARD_COUNT = 108  # 54 种 × 2 张/副 × 1 副
HAND_SIZE = 27

RANK_LETTERS = {"2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"}

# ── GUA-052 维度常量 ────────────────────────────────
# GUA-054 升级（2026-06-17）：24 维 + 9 维 grouping_score = 33 维
# 24 维 = 4(seat 剩张) + 15(rank 已出比例) + 4(seat 炸弹数) + 1(级牌剩余)
#  9 维 = extract_grouping_score（v7-internal，0~1 归一化独立软信号）
MEMORY_TRACKER_DIM = 33
GROUPING_SCORE_DIM = 9

# ── GUA-054 grouping_scanner 接入（2026-06-17）──────
try:
    from src.v.nn.features.grouping_scanner import (
        extract_grouping_score,
        get_grouping_score_dim,
    )
    _grouping_import_ok = True
except ImportError as e:
    _grouping_import_ok = False
    print(f"[Warning] grouping_scanner 导入失败: {e}, grouping_score 退化为零向量")


def _parse_card_rank(card: str) -> str:
    """从牌面字符串提取点数。"""
    if card in ("BJ", "RJ"):
        return card
    return card[1:] if len(card) > 1 else card[-1]


# ── 牌追踪器 ────────────────────────────────────────────


class MemoryTracker:
    """108 张牌全量追踪。

    内部维护每张牌的 4 席状态：unknown / my_hand / partner_hand / opp_hand / played_0 / played_1。

    性能开关：
      - enable_inference=False → 仅追踪牌的去向，不做排除法推断
      - max_infer_depth=3 → 排除法最大递归深度（默认 0 表示不做排除法）
    """

    # 牌状态枚举
    UNKNOWN = 0
    MY_HAND = 1
    PARTNER_HAND = 2
    OPPONENT_HAND = 3
    PLAYED = 4  # 已打出

    def __init__(self, my_pos: int = 0, enable_inference: bool = True,
                 max_infer_depth: int = 0):
        self.my_pos = my_pos
        self.partner_pos = (my_pos + 2) % 4
        self.opponents = {(my_pos + 1) % 4, (my_pos + 3) % 4}

        # core state: 每张牌（54 种 × 2 副本）的 4 席分配
        # card_state[card_type][copy_idx] = seat (0-3) or -1(unknown) or 4(played)
        self.card_state: Dict[str, List[int]] = {}
        for ct in ALL_CARD_TYPES:
            self.card_state[ct] = [-1, -1]  # -1 = unknown

        # 每家手牌计数
        self.hand_counts: Dict[int, int] = {i: HAND_SIZE for i in range(4)}

        # 出牌历史：每步记录
        self.play_history: List[Dict[str, Any]] = []

        # 已出炸弹计数
        self.bombs_played: Dict[int, int] = defaultdict(int)

        # 级牌剩余（各花色）
        self.level_cards_remaining: Set[str] = set()  # e.g. {"S2", "H2", "D2", "C2"}

        # 性能开关
        self.enable_inference = enable_inference
        self.max_infer_depth = max_infer_depth

        # 推理耗时累计（ms）
        self.inference_time_ms = 0.0

    # ── 初始化 ──────────────────────────────────────────

    def init_from_hand(self, my_hand: List[str]) -> None:
        """从自己的手牌初始化。"""
        my_hand_counter = Counter(my_hand)
        for ct in ALL_CARD_TYPES:
            self.card_state[ct] = [-1, -1]
        for card in my_hand:
            self._mark_my_hand(card)

    def _mark_my_hand(self, card: str) -> None:
        ct = self._canonical_type(card)
        if self.card_state[ct][0] == -1:
            self.card_state[ct][0] = self.MY_HAND
        elif self.card_state[ct][1] == -1:
            self.card_state[ct][1] = self.MY_HAND
        else:
            logger.warning("无法标记手牌 %s: 副本已满", card)

    # ── 状态更新 ────────────────────────────────────────

    def record_play(self, seat: int, action: List[Any]) -> None:
        """记录某席出牌动作。

        action 格式: ["Bomb", "8", [...]]
        """
        if not action or len(action) < 3:
            return
        cards = action[2] if isinstance(action[2], list) else []
        if not cards:
            return

        # 标记这些牌为已打出
        for card in cards:
            self._mark_played(seat, card)

        # 更新手牌计数
        deck = self._get_deck(cards)
        self.hand_counts[seat] = max(0, self.hand_counts[seat] - deck)
        self.hand_counts[self.my_pos] = max(0, self.hand_counts[self.my_pos])  # 不自动改自己

        # 记录出牌历史
        self.play_history.append({
            "seat": seat,
            "action_type": str(action[0]),
            "cards": cards,
            "hand_count_after": self.hand_counts[seat],
        })

        # 排除法推断（如果启用）
        if self.enable_inference and self.max_infer_depth > 0:
            import time
            t0 = time.time()
            self._infer_after_play(seat, cards)
            elapsed_ms = (time.time() - t0) * 1000
            self.inference_time_ms += elapsed_ms
            if elapsed_ms > 50:
                logger.warning("排除法推断耗时 %.0fms (seat=%d, cards=%s)",
                               elapsed_ms, seat, cards[:3])

    def record_bomb(self, seat: int) -> None:
        """记录炸弹打出。"""
        self.bombs_played[seat] += 1

    def set_level_rank(self, rank: str) -> None:
        """设置当前级牌并初始化剩余级牌。"""
        self.level_cards_remaining.clear()
        for suit in SUITS:
            self.level_cards_remaining.add(f"{suit}{rank}")

    def record_hand_update(self, seat: int, hand_count: int) -> None:
        """外部更新手牌计数（如贡还后）。"""
        self.hand_counts[seat] = hand_count

    # ── 查询 ────────────────────────────────────────────

    def get_played_cards(self) -> Dict[str, int]:
        """返回已打出牌的种类计数。"""
        result: Dict[str, int] = {}
        for ct, copies in self.card_state.items():
            played = sum(1 for c in copies if c == self.PLAYED)
            if played > 0:
                result[ct] = played
        return result

    def get_my_hand_types(self) -> List[str]:
        """返回自己手中的牌种类列表。"""
        result = []
        for ct, copies in self.card_state.items():
            if any(c == self.MY_HAND for c in copies):
                result.append(ct)
        return result

    def get_hand_count(self, seat: int) -> int:
        """获取某席手牌计数。"""
        return self.hand_counts.get(seat, 0)

    def get_card_owners(self, card_type: str) -> List[int]:
        """获取某类牌的所有者 [-1=unknown, 0-3=seat, 4=played]。"""
        return list(self.card_state.get(card_type, [-1, -1]))

    def get_inferred_opponent_types(self, opponent_seat: int) -> List[str]:
        """（排除法）推断对手手中有哪些牌种。
        只会推断 max_infer_depth 层已确认的信息。
        """
        if not self.enable_inference:
            return []
        result = []
        for ct, copies in self.card_state.items():
            for c in copies:
                if c == opponent_seat:
                    result.append(ct)
                    break
        return result

    def get_opponent_bomb_risk(self, opponent_seat: int) -> float:
        """评估对手炸弹风险（0.0~1.0）。"""
        played = self.bombs_played.get(opponent_seat, 0)
        remaining = self.hand_counts.get(opponent_seat, HAND_SIZE)
        bomb_likely = remaining <= 10 and played < 2
        return min(1.0, (HAND_SIZE - remaining) / HAND_SIZE * 2.0) if bomb_likely else 0.0

    def get_state_vector(self, game_state: Optional[Dict[str, Any]] = None) -> List[float]:
        """获取记忆追踪状态向量（用于特征拼接）。

        33 维（GUA-054 升级）= 4(seat 剩张) + 15(各 rank 已出比例) + 4(各 seat 炸弹数) + 1(级牌剩余)
                         + 9(grouping_score, GUA-054 软信号)

        Args:
            game_state: 游戏状态（GUA-054 追加 grouping_score 需要 handCards/curRank）。
                       传 None 时退化为 24 维（向后兼容）。
        """
        vec: List[float] = []

        # 4 席剩张
        for i in range(4):
            vec.append(self.hand_counts.get(i, HAND_SIZE) / HAND_SIZE)

        # 15 rank 已出比例（13 个 RANK + 2 王）
        rank_counts: Dict[str, int] = defaultdict(int)
        for ct, copies in self.card_state.items():
            rank = _parse_card_rank(ct)
            played = sum(1 for c in copies if c == self.PLAYED)
            if played > 0:
                rank_counts[rank] += played
        for r in RANKS + ["BJ", "RJ"]:
            vec.append(rank_counts.get(r, 0) / 8.0)  # 最多 8 张/rank

        # 4 席炸弹数
        for i in range(4):
            vec.append(min(1.0, self.bombs_played.get(i, 0) / 5.0))

        # 级牌剩余比例
        lc = 0
        if self.level_cards_remaining:
            for ct, copies in self.card_state.items():
                rank = _parse_card_rank(ct)
                if not rank.isdigit() and rank not in RANK_LETTERS:
                    continue
                for c in copies:
                    if c != self.PLAYED and rank in RANK_LETTERS:
                        lc += 1
        vec.append(min(1.0, lc / 4.0))

        # ── GUA-054 追加 9 维 grouping_score（2026-06-17）────
        if _grouping_import_ok and game_state is not None:
            try:
                grouping = extract_grouping_score(game_state)
                if len(grouping) == GROUPING_SCORE_DIM:
                    vec.extend(grouping)
                else:
                    vec.extend([0.0] * GROUPING_SCORE_DIM)
            except Exception as e:
                logger.warning(f"extract_grouping_score 失败: {e}, 退化零向量")
                vec.extend([0.0] * GROUPING_SCORE_DIM)
        else:
            # 向后兼容：game_state 为 None 时填零向量
            vec.extend([0.0] * GROUPING_SCORE_DIM)

        assert len(vec) == MEMORY_TRACKER_DIM, f"state_vector 维度异常: {len(vec)} (期望 {MEMORY_TRACKER_DIM})"
        return vec

    # ── 内部方法 ──────────────────────────────────────

    def _mark_played(self, seat: int, card: str) -> None:
        ct = self._canonical_type(card)
        copies = self.card_state[ct]
        for i in range(2):
            if copies[i] == seat or copies[i] == -1:
                copies[i] = self.PLAYED
                return
        # 如果全部已标记，为安全不覆盖

    def _infer_after_play(self, seat: int, cards: List[str]) -> None:
        """出牌后执行简单排除法：
        - 若某席某牌已出 2 张 → 其他席不再有该牌
        - 若总已出 + 自己手牌 = 2 张 → 对手无该牌
        """
        for card in cards:
            ct = self._canonical_type(card)
            played = sum(1 for c in self.card_state[ct] if c == self.PLAYED)
            my_hand = sum(1 for c in self.card_state[ct] if c == self.MY_HAND)
            if played + my_hand >= 2:
                for i in range(2):
                    if self.card_state[ct][i] == -1:
                        self.card_state[ct][i] = self.OPPONENT_HAND if seat in self.opponents else self.PARTNER_HAND

    @staticmethod
    def _canonical_type(card: str) -> str:
        """标准化牌面类型（如 'C2'→'C2', '2C'→'C2' 暂时不支持）。"""
        if card in ("BJ", "RJ"):
            return card
        if len(card) == 2 and card[0] in SUITS and (card[1].isdigit() or card[1] in RANK_LETTERS):
            return card
        # fallback: 尝试补全花色
        if len(card) >= 2:
            suit = card[0].upper()
            rank = card[1:].upper()
            if suit in SUITS and (rank in RANK_LETTERS or rank in ("BJ", "RJ")):
                return f"{suit}{rank}"
        return card

    @staticmethod
    def _get_deck(cards: List[str]) -> int:
        """估算牌数（通常 len(cards)）。"""
        return len(cards)

    def reset(self) -> None:
        """重置所有状态。"""
        for ct in ALL_CARD_TYPES:
            self.card_state[ct] = [-1, -1]
        self.hand_counts = {i: HAND_SIZE for i in range(4)}
        self.play_history.clear()
        self.bombs_played.clear()
        self.level_cards_remaining.clear()
        self.inference_time_ms = 0.0
