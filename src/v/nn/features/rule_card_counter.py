# -*- coding: utf-8 -*-
"""
GUA-072: 规则记牌引擎 — 从 MemoryTracker 推断剩余牌分布，给 heuristic 喂信念输入。

零成本计数（不依赖 GPU/排除法/模型），仅做 card_state 已知信息的结构化提取。
给 heuristic_select 装上"眼睛"：打破当前零信念决策（不知道对手还能压制什么牌型）。

信念信号：
  - HR/SB/级牌 各已出多少
  - 对手能否压制某 rank 的牌（核心：can_opponent_suppress）
  - 对手剩余炸弹风险
  - 各 rank 全耗尽集合

与组牌引擎完全相同的 TDD 迭代模式：投喂→分析→修正→pytest→批跑。
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Set

from src.v.nn.features.memory_tracker import MemoryTracker

SUITS = ["S", "H", "D", "C"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]

RANK_VALUE: Dict[str, int] = {
    "2": 0, "3": 1, "4": 2, "5": 3, "6": 4, "7": 5,
    "8": 6, "9": 7, "T": 8, "J": 9, "Q": 10, "K": 11, "A": 12,
}


def _parse_card_rank_fast(card_type: str) -> str:
    """快速从标准化牌型提取 rank。卡牌格式 'S2'/'HR'/'SB'。"""
    if card_type in ("HR", "SB"):
        return card_type
    return card_type[1:] if len(card_type) >= 2 else ""


class RuleCardCounter:
    """GUA-072: 规则记牌引擎。

    从 MemoryTracker 的 card_state/play_history/hand_counts 提取信念信号，
    供 engine._heuristic_select 使用。

    核心方法 can_opponent_suppress 回答：
    "对手 X 是否很可能还能压制 rank Y 的牌？"
    """

    def __init__(self, tracker):
        """
        Args:
            tracker: MemoryTracker 实例（已回放完历史）
        """
        self._t = tracker

    # ── 压制判断（核心 ────────────────────────────────

    def can_opponent_suppress(self, opp_seat: int, target_rank: str,
                              min_candidates: int = 1) -> bool:
        """对手 opp_seat 是否确信还能压制 rank=target_rank 的牌？

        算法：遍历所有 rank > target_rank 的牌型（含大小王），
        统计 card_state 中仍可能由对手打出的张数：
          - UNKNOWN（-1 / 0）：去向未明，保守计入
          - OPPONENT_HAND（3）：已推断在对手侧
        不计 MY_HAND / PARTNER_HAND / PLAYED。

        若候选数 ≥ min_candidates → True（对手仍可能压制）；
        反之 False → heuristic ③c 鼓励压牌。

        注意：炸弹不单独判断（炸弹是普适压制，已在 get_opponent_bomb_risk 中覆盖）。
        这里只判断 rank 压制（同牌型比大小）。
        """
        if opp_seat not in self._t.opponents:
            return False

        tval = RANK_VALUE.get(target_rank)
        if tval is None:
            return False

        suppress_count = 0
        for ct, copies in self._t.card_state.items():
            if ct in ("SB", "HR"):
                for c in copies:
                    if self._may_opp_hold(c):
                        suppress_count += 1
                continue
            if len(ct) < 2:
                continue
            rv = RANK_VALUE.get(ct[1:])
            if rv is None or rv <= tval:
                continue
            for c in copies:
                if self._may_opp_hold(c):
                    suppress_count += 1

        return suppress_count >= min_candidates

    @staticmethod
    def _may_opp_hold(copy_state: int) -> bool:
        """牌副本是否仍可能由任一对手持有（非我方/队友/已出）。"""
        return copy_state in (
            -1,
            MemoryTracker.UNKNOWN,
            MemoryTracker.OPPONENT_HAND,
        )

    # ── 炸弹统计分析 ──────────────────────────────────

    def get_bomb_stats(self) -> Dict[str, Any]:
        """炸弹统计：各席炸弹已出数、同花顺已出数、预计剩余炸弹数。

        Returns:
            dict with keys:
              - bombs_played: {seat: int} 各席已出炸弹数
              - sf_bombs_played: {seat: int} 各席已出同花顺数（近似）
              - total_bombs_played: int 总炸弹数
              - bombs_remaining_self: int 自己手牌中预计剩余炸弹数
              - bombs_remaining_opp: {seat: int} 对手预计剩余炸弹数
        """
        tracker = self._t
        bombs_played = dict(tracker.bombs_played)
        total = sum(bombs_played.values())

        # 从 play_history 统计同花顺（>=6 张的 Bomb）
        sf: Dict[int, int] = defaultdict(int)
        for play in tracker.play_history:
            action_type = play.get("action_type", "")
            if action_type == "Bomb":
                cards = play.get("cards", [])
                if len(cards) >= 6:
                    seat = play.get("seat", -1)
                    if seat >= 0:
                        sf[seat] += 1

        # 自己手中预计剩余炸弹数（4 张同 rank + 级牌炸弹 = 5 张）
        from collections import Counter
        my_types = tracker.get_my_hand_types()
        rank_counter: Dict[str, int] = Counter()
        for ct in my_types:
            rank = _parse_card_rank_fast(ct)
            if rank:
                rank_counter[rank] += 1
        self_bombs = sum(1 for cnt in rank_counter.values() if cnt >= 4)
        # 级牌炸弹：自己手中级牌数 + (8 - 已出级牌) >= 5
        level_rank = ""
        if tracker.level_cards_remaining:
            for lc in tracker.level_cards_remaining:
                level_rank = _parse_card_rank_fast(lc)
                break
        if level_rank and rank_counter.get(level_rank, 0) >= 5:
            self_bombs += 1

        # 对手预计剩余炸弹数（启发式：剩张较少 + 已出炸弹数少 → 可能有炸）
        opp_bombs = {}
        for opp in tracker.opponents:
            remaining = tracker.hand_counts.get(opp, 27)
            played = bombs_played.get(opp, 0)
            likely_bomb = 0
            if remaining <= 10 and played < 2:
                likely_bomb = 1
            opp_bombs[opp] = likely_bomb

        return {
            "bombs_played": bombs_played,
            "sf_bombs_played": dict(sf),
            "total_bombs_played": total,
            "bombs_remaining_self": self_bombs,
            "bombs_remaining_opp": opp_bombs,
        }

    # ── rank 安全判断 ─────────────────────────────────

    def is_rank_safe(self, rank: str) -> bool:
        """该 rank 是否安全（所有副本均已出或在我方手中，对手不可能持有）。

        安全 rank 的牌打出去不会被对手压制，相当于"小王"的效果。
        """
        if rank in ("SB", "HR"):
            return False
        for suit in SUITS:
            ct = f"{suit}{rank}"
            copies = self._t.card_state.get(ct, [-1, -1])
            for c in copies:
                if c == -1 or c in self._t.opponents:
                    return False
        return True

    def get_rank_unknown_count(self, rank: str) -> int:
        """该 rank 还有多少张 UNKNOWN（尚未确定去向）。"""
        count = 0
        for suit in SUITS:
            ct = f"{suit}{rank}"
            copies = self._t.card_state.get(ct, [-1, -1])
            count += sum(1 for c in copies if c == -1)
        return count

    def get_unknown_rank_stats(self) -> Dict[str, int]:
        """所有 rank 的 UNKNOWN 计数。"""
        return {r: self.get_rank_unknown_count(r) for r in RANKS + ["SB", "HR"]}

    # ── 全局信号 ──────────────────────────────────────

    def get_level_signal(self) -> Dict[str, Any]:
        """级牌状态信号：
          - level_rank: 当前级牌
          - level_remaining_in_play: 总级牌剩余张数
          - level_in_my_hand: 自己手中级牌张数
          - can_form_level_bomb: 是否有潜力组级牌炸弹（级牌>=5张可用）
          - level_threat: 对手持有级牌做炸弹的可能性 0~1
        """
        tracker = self._t
        level_rank = ""
        if tracker.level_cards_remaining:
            for lc in tracker.level_cards_remaining:
                level_rank = _parse_card_rank_fast(lc)
                break

        # 总级牌剩余
        level_left = 0
        if tracker.level_cards_remaining:
            for lc in tracker.level_cards_remaining:
                copies = tracker.card_state.get(lc, [-1, -1])
                level_left += sum(1 for c in copies if c != 4)

        # 自己手中级牌
        my_types = tracker.get_my_hand_types()
        level_in_hand = 0
        if level_rank:
            for ct in my_types:
                if _parse_card_rank_fast(ct) == level_rank:
                    level_in_hand += 1

        can_form_bomb = level_in_hand >= 5

        # 对手威胁：对手手牌数还很多 → 可能藏级牌炸弹
        opp_threat = 0.0
        for opp in tracker.opponents:
            if tracker.hand_counts.get(opp, 27) >= 15:
                opp_threat = max(opp_threat, 0.5)
            if tracker.hand_counts.get(opp, 27) >= 20:
                opp_threat = max(opp_threat, 0.8)
        # 级牌已出越多 → 威胁越小
        level_played = 8 - level_left
        if level_played >= 6:
            opp_threat *= 0.3
        elif level_played >= 4:
            opp_threat *= 0.7

        return {
            "level_rank": level_rank,
            "level_remaining": level_left,
            "level_in_my_hand": level_in_hand,
            "can_form_level_bomb": can_form_bomb,
            "level_threat": opp_threat,
        }

    # ── 信念字典（完整 ────────────────────────────────

    def get_belief(self, game_state=None) -> Dict[str, Any]:
        """返回完整信念 dict，供 engine._inject_belief_vector 注入 game_state。

        信念信号（全部零成本、纯计数）：
          - hr_played/sb_played: 大小王已出张数 (0-2)
          - level_remain: 级牌剩余张数 (0-8)
          - opp_bomb_risks: {opp_seat: float} 对手炸弹风险 0~1
          - hand_counts: {seat: int} 各家剩余张数
          - depleted_ranks: list[str] 已完全耗尽的 rank（8 张全出或全已知归属）
          - safe_ranks: set[str] 安全的 rank（对手不可持有）
          - can_opp_suppress_current: 对手是否可能压制当前控牌
          - bomb_stats: get_bomb_stats() 返回值
          - level_signal: get_level_signal() 返回值
          - unknown_rank_stats: get_unknown_rank_stats() 返回值
        """
        tracker = self._t

        # 大小王已出
        hr = tracker.card_state.get("HR", [-1, -1])
        sb = tracker.card_state.get("SB", [-1, -1])
        hr_played = sum(1 for c in hr if c == 4)
        sb_played = sum(1 for c in sb if c == 4)

        # 级牌剩余
        level_left = 0
        if tracker.level_cards_remaining:
            for lc in tracker.level_cards_remaining:
                copies = tracker.card_state.get(lc, [])
                level_left += sum(1 for c in copies if c != 4)

        # 对手炸弹风险
        opp_risks = {}
        for opp in tracker.opponents:
            opp_risks[opp] = tracker.get_opponent_bomb_risk(opp)

        # 已完全耗尽的 rank（所有 8 张均已出或归属已知且不在对手未知里）
        depleted: List[str] = []
        safe: Set[str] = set()
        for r in RANKS:
            total = 0
            played_or_known = 0
            is_safe = True
            for s in SUITS:
                ct = f"{s}{r}"
                copies = tracker.card_state.get(ct, [-1, -1])
                total += len(copies)
                played_or_known += sum(1 for c in copies if c == 4 or c == 1)  # PLAYED or MY_HAND
                for c in copies:
                    if c == -1 or c in tracker.opponents:
                        is_safe = False
            if total > 0 and played_or_known == total:
                depleted.append(r)
            if is_safe:
                safe.add(r)

        # 对手能否压制当前控牌
        can_opp_suppress = True  # 默认保守
        if game_state:
            greater_pos = game_state.get("greaterPos", -1)
            greater_action = game_state.get("greaterAction")
            if (greater_pos in tracker.opponents
                    and greater_action
                    and isinstance(greater_action, list)
                    and len(greater_action) >= 2):
                g_rank = str(greater_action[1])
                can_opp_suppress = self.can_opponent_suppress(greater_pos, g_rank)

        hand_counts = dict(tracker.hand_counts)

        return {
            "hr_played": hr_played,
            "sb_played": sb_played,
            "level_remain": level_left,
            "opp_bomb_risks": opp_risks,
            "hand_counts": hand_counts,
            "depleted_ranks": depleted,
            "safe_ranks": safe,
            "can_opp_suppress_current": can_opp_suppress,
            "bomb_stats": self.get_bomb_stats(),
            "level_signal": self.get_level_signal(),
            "unknown_rank_stats": self.get_unknown_rank_stats(),
        }


def create_counter_from_tracker(tracker) -> RuleCardCounter:
    """工厂函数：从 MemoryTracker 构造 RuleCardCounter。"""
    return RuleCardCounter(tracker)
