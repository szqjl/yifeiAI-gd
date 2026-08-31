# -*- coding: utf-8 -*-
"""
Botzone Local AI 适配器 — 让 V8 通过 HTTP API 与 Botzone 平台对战。

架构：
  Botzone 平台 ←→ HTTP GET/POST → BotzoneAdapter ←→ V8 UltimateWinRateEngineV7

工作流：
  1) Poll GET /api/{userID}/{key}/localai — 获取新 request + 结束对局
  2) 转换 Botzone JSON request → V8 game_state（含自动生成 actionList）
  3) 调用 decision_engine.decide(game_state) 获取 actIndex
  4) 将 actIndex 转回 Botzone 格式，通过 X-Match-{id} header 提交
  5) 循环

协议对照（Botzone ↔ OpenGuanDan）：
  - Cards: int 0-107 ↔ str "S2" / "HR" / "SB"
  - Action: [cards_int] ↔ ["Type", "Rank", [cards_str]]
  - Stage: deal/tribute/return/play ↔ beginning/tribute/back/play
  - Team: (0,2) vs (1,3) — 与 OpenGuanDan 一致
"""

from __future__ import annotations

import asyncio
import itertools
import json
import logging
import socket
import sys
import time
import urllib.request
import urllib.error
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set

logger = logging.getLogger("botzone_adapter")

# ──────────────────────────────────────────────
#  Constants
# ──────────────────────────────────────────────

# Botzone card encoding: 0-107
# V8 card format: "S2", "H3", "CA", "DT", "SB", "HR"
BZ_RANK_STR = "A23456789TJQK"  # value 0-12
BZ_SUIT_MAP = {0: "H", 1: "D", 2: "S", 3: "C"}  # heart, diamond, spade, club
V8_SUIT_TO_BZ = {"H": 0, "D": 1, "S": 2, "C": 3}
V8_RANK_TO_BZ = {r: i for i, r in enumerate(BZ_RANK_STR)}  # "A"→0, "2"→1, ...

# OpenGuanDan rank order for comparison
RANK_ORDER = {"2": 0, "3": 1, "4": 2, "5": 3, "6": 4, "7": 5, "8": 6,
              "9": 7, "T": 8, "J": 9, "Q": 10, "K": 11, "A": 12}
JOKER_RANK_ORDER = {"B": 16, "R": 17}  # Small Joker, Big Joker

# GUA-244: 全部 54 个牌名（value 0-12 × 4 花色 + SB/HR），剩余池按此序展开
_POOL_NAME_ORDER = [
    "%s%s" % (BZ_SUIT_MAP[s], r) for r in BZ_RANK_STR for s in (0, 1, 2, 3)
] + ["SB", "HR"]

# ──────────────────────────────────────────────
#  Card encoding / decoding
# ──────────────────────────────────────────────

def bz_to_v8_card(bz_int: int) -> str:
    """Convert Botzone integer (0-107) to V8 string card."""
    first_deck = bz_int % 54
    value = first_deck // 4
    suit_idx = first_deck % 4
    if value == 13:
        return "SB" if suit_idx in (0, 2) else "HR"
    rank = BZ_RANK_STR[value]
    suit = BZ_SUIT_MAP[suit_idx]
    return f"{suit}{rank}"


def v8_to_bz_int(v8_card: str, deck_offset: int = 0) -> int:
    """Convert V8 string card to Botzone integer (first deck 0-53, second deck 54-107).

    deck_offset=0 -> first deck (0-53), deck_offset=1 -> second deck (54-107).
    """
    suit_char = v8_card[0]
    rank_part = v8_card[1:] if len(v8_card) > 2 else v8_card[1]

    if rank_part in ("B", "R"):
        # Small Joker (B) or Big Joker (R)
        if rank_part == "B":
            value, suit_idx = 13, 0  # 52
        else:
            value, suit_idx = 13, 1  # 53
    else:
        suit_idx = V8_SUIT_TO_BZ.get(suit_char, 2)  # default spade
        value = V8_RANK_TO_BZ.get(rank_part, 0)

    base = 54 * deck_offset
    return base + value * 4 + suit_idx


def bz_to_v8_cards(bz_card_list: List[int]) -> List[str]:
    """Convert a list of Botzone integer cards to V8 strings."""
    return [bz_to_v8_card(c) for c in bz_card_list]


def v8_to_bz_cards(v8_card_list: List[str], deck_offset: int = 0) -> List[int]:
    """Convert a list of V8 string cards to Botzone integers."""
    return [v8_to_bz_int(c, deck_offset) for c in v8_card_list]


# ──────────────────────────────────────────────
#  Card tracking
# ──────────────────────────────────────────────

@dataclass
class CardTracker:
    """Tracks which specific Botzone integer cards are still in V8's hand.

    Since two decks mean each V8 card string ("S2") maps to 2 Botzone ints,
    we need to track remaining counts to produce accurate reverse mappings.
    """

    remaining: Dict[str, List[int]] = field(default_factory=lambda: defaultdict(list))

    @classmethod
    def from_bz_hand(cls, bz_hand: List[int]) -> "CardTracker":
        ct = cls()
        for c in bz_hand:
            v8 = bz_to_v8_card(c)
            ct.remaining[v8].append(c)
        return ct

    def remove(self, v8_card: str) -> Optional[int]:
        """Remove and return one Botzone integer for a V8 card."""
        pool = self.remaining.get(v8_card, [])
        if not pool:
            return None
        return pool.pop(0)

    def remove_multi(self, v8_cards: List[str]) -> List[int]:
        """Remove and return Botzone integers for a list of V8 cards."""
        return [c for c in (self.remove(card) for card in v8_cards) if c is not None]

    def get_available(self, v8_card: str) -> List[int]:
        return list(self.remaining.get(v8_card, []))

    def add(self, v8_card: str, bz_int: int) -> None:
        self.remaining[v8_card].append(bz_int)

    def copy(self) -> "CardTracker":
        ct = CardTracker()
        ct.remaining = {k: list(v) for k, v in self.remaining.items()}
        return ct


# ──────────────────────────────────────────────
#  Action type helpers (OpenGuanDan format)
# ──────────────────────────────────────────────

ACTION_TYPES_SIMPLE = ("Single", "Pair", "Trips")
ACTION_TYPES_COMPLEX = ("ThreeWithTwo", "ThreePair", "TwoTrips", "Straight", "StraightFlush", "Bomb")


def _card_rank(v8_card: str) -> str:
    """Extract rank from V8 card string."""
    return v8_card[1:] if len(v8_card) > 2 else v8_card[1]


def _card_rank_order(v8_card: str, cur_rank: str = "2") -> int:
    """Numerical rank value for comparison."""
    r = _card_rank(v8_card)
    if r == cur_rank:
        return 15  # cur rank wild
    return JOKER_RANK_ORDER.get(r, RANK_ORDER.get(r, -1))


def _rank_to_order(rank: str, cur_rank: str = "2") -> int:
    """Convert a rank string to its order value."""
    if rank == cur_rank:
        return 15
    return JOKER_RANK_ORDER.get(rank, RANK_ORDER.get(rank, -1))


def _make_action(action_type: str, rank: str, cards: List[str]) -> list:
    """Create an OpenGuanDan format action tuple."""
    return [action_type, rank, cards]


def _is_bomb(action: list) -> bool:
    t = action[0] if isinstance(action, list) and len(action) >= 1 else ""
    return t in ("Bomb", "StraightFlush")


# ──────────────────────────────────────────────
#  ActionList generator
# ──────────────────────────────────────────────

class ActionListGenerator:
    """Generates OpenGuanDan-format actionList from V8 hand cards."""

    def __init__(self, cur_rank: str = "2"):
        self.cur_rank = cur_rank

    def generate_lead_actions(self, hand_cards: List[str]) -> List[list]:
        """Generate all valid lead actions from hand.

        对齐 OpenGuanDan 服务器：领出轮 actionList 不含 PASS（服务器领出轮
        size=1731/1410/1091 均无 "PASS" 实测），消除「领出/接风轮引擎选 PASS
        被兜底成弱单张」退化（logs/v8_vs_botzone_20260802_220840.log 22:09:03）。
        """
        actions = []
        rank_groups = self._group_by_rank(hand_cards)
        suits = self._group_by_suit(hand_cards)

        # Singles
        for card in hand_cards:
            actions.append(self._single_action(card))

        # Pairs：同 rank 全 2 张组合（对齐服务器枚举，让引擎可挑不拆核组合）
        for rank, cards in rank_groups.items():
            if len(cards) >= 2:
                for combo in self._combos(cards, 2):
                    actions.append(self._pair_action(combo))

        # Trips：同 rank 全 3 张组合
        for rank, cards in rank_groups.items():
            if len(cards) >= 3:
                for combo in self._combos(cards, 3):
                    actions.append(self._trips_action(combo))

        # GUA-195: 配子(H{curRank})补对成三张 —— H2+对10 应生成 Trips/10 候选，
        # 否则 actionList 只有 Single×3+Pair×1，残局一手清（H2+ST+HT=Trips/10）
        # 无法命中，引擎只能先出单 H2 再出对 10，分两次打（实测 match
        # 6a717aab27e7bf01db10369f 13:38:30）。
        wild = "H" + str(self.cur_rank)
        if any(c == wild for c in hand_cards):
            natural_groups = self._group_by_rank(
                [c for c in hand_cards if c != wild]
            )
            for rank, cards in natural_groups.items():
                if len(cards) >= 2:
                    for combo in self._combos(cards, 2):
                        # 配子放最后，保证 _trips_action 以组合牌点数声明
                        actions.append(self._trips_action(list(combo) + [wild]))

        # Bombs (4+ same rank)：全量炸弹 + 各档小炸（对齐服务器 4/5/6…张枚举）
        for rank, cards in rank_groups.items():
            if len(cards) >= 4:
                for size in range(4, len(cards) + 1):
                    actions.append(self._bomb_action(list(cards[:size])))
        # 逢人配补炸：自然 3 张同 rank + H{cur_rank} → 4 张 Bomb（配子补炸）
        actions.extend(self._wild_bomb_candidates(hand_cards))

        # ThreeWithTwo (trips + pair)：trip × pair 全组合
        for t_rank, t_cards in rank_groups.items():
            trip_combos = self._combos(t_cards, 3)
            if not trip_combos:
                continue
            for p_rank, p_cards in rank_groups.items():
                if p_rank == t_rank:
                    continue
                pair_combos = self._combos(p_cards, 2)
                for trips in trip_combos:
                    for pair in pair_combos:
                        actions.append(self._three_with_two_action(trips, pair))

        # GUA-236: 配子补三头组成 TWT —— 两枚同点 + H{curRank} 作 trip，再带另一对。
        # GUA-195 只补了 Trips；缺配子 TWT 时两手清（顺 + 77H2+TT）无法命中残余一手。
        if any(c == wild for c in hand_cards):
            natural_groups = self._group_by_rank(
                [c for c in hand_cards if c != wild]
            )
            for t_rank, t_cards in natural_groups.items():
                if len(t_cards) < 2:
                    continue
                for trip_base in self._combos(t_cards, 2):
                    trips = list(trip_base) + [wild]
                    for p_rank, p_cards in natural_groups.items():
                        if p_rank == t_rank or len(p_cards) < 2:
                            continue
                        for pair in self._combos(p_cards, 2):
                            actions.append(
                                self._three_with_two_action(trips, list(pair))
                            )
            # GUA-273：三自然张 + 配子 + 单张 → TWT（trip 三枚同点，pair=配子+单）。
            # match 6a8d2762：444+H2+DT 仅枚举了配子炸，缺 TWT 一手清。
            for t_rank, t_cards in natural_groups.items():
                if len(t_cards) < 3:
                    continue
                for trips in self._combos(t_cards, 3):
                    left = [c for c in hand_cards if c not in trips]
                    if len(left) == 2 and wild in left:
                        single = next(c for c in left if c != wild)
                        actions.append(
                            self._three_with_two_action(list(trips), [wild, single])
                        )

        # Straights
        actions.extend(self._generate_straights(rank_groups, suits, hand_cards))

        # StraightFlushes
        for suit, s_cards in suits.items():
            if len(s_cards) >= 5:
                s_ranks = sorted(set(_card_rank(c) for c in s_cards),
                                key=lambda r: RANK_ORDER.get(r, 99))
                actions.extend(self._generate_straight_flushes(s_cards, s_ranks))

        # H2-wild StraightFlushes (逢人配)：H2 补同花色 5 连窗口缺位
        actions.extend(self._generate_h2_wild_straight_flushes(hand_cards, suits))

        # ThreePairs (三连对，只能 3 连)：每 rank 的 pair 全组合
        consecutive_pairs = self._find_consecutive_pairs(rank_groups, 3)
        for ranks, _pairs in consecutive_pairs:
            pair_combos = [self._combos(rank_groups[r], 2) for r in ranks]
            for combo in itertools.product(*pair_combos):
                cards = [c for pc in combo for c in pc]
                actions.append(self._three_pair_action(cards, ranks[-1]))

        # TwoTrips (钢板，只能 2 连)：每 rank 的 trip 全组合
        consecutive_trips = self._find_consecutive_trips(rank_groups, 2)
        for ranks, _trips_list in consecutive_trips:
            trip_combos = [self._combos(rank_groups[r], 3) for r in ranks]
            for combo in itertools.product(*trip_combos):
                cards = [c for tc in combo for c in tc]
                actions.append(self._two_trips_action(cards, ranks[-1]))

        # Deduplicate by card list hash
        seen: Set[str] = set()
        deduped = []
        for act in actions:
            key = self._action_key(act)
            if key not in seen:
                seen.add(key)
                deduped.append(act)
        return deduped

    def generate_follow_actions(self, hand_cards: List[str],
                                greater_action: list) -> List[list]:
        """Generate actions that beat greater_action + PASS."""
        actions = [["PASS", "PASS", "PASS"]]
        greater_type = greater_action[0] if len(greater_action) >= 1 else ""
        greater_rank = greater_action[1] if len(greater_action) >= 2 else ""
        greater_order = _rank_to_order(greater_rank, self.cur_rank)
        # 顺子/同花顺：rank 字段是窗口低牌，比大小须用窗口最高牌（_straight_top_order）
        greater_cards = (greater_action[2]
                         if len(greater_action) >= 3 and isinstance(greater_action[2], list)
                         else [])
        greater_straight_top = (self._straight_top_order(greater_cards, self.cur_rank)
                                if greater_cards
                                and greater_type in ("Straight", "StraightFlush")
                                else greater_order)

        rank_groups = self._group_by_rank(hand_cards)
        suits = self._group_by_suit(hand_cards)

        if greater_type in ("Single", "Pair", "Trips"):
            n = {"Single": 1, "Pair": 2, "Trips": 3}[greater_type]
            for rank, cards in rank_groups.items():
                if len(cards) >= n and _rank_to_order(rank, self.cur_rank) > greater_order:
                    # 生成该 rank 的全部 n 组合，让引擎能挑到不拆核心组（炸/同花顺/顺子）的组合。
                    # 此前仅生成 cards[:n]（手牌顺序前 n 张），可能总是拆 SF core（如 HQ），
                    # GUA-176 拦截后 actionList 无替代 → 该压不压 PASS。
                    for combo in itertools.combinations(cards, n):
                        actions.append(_make_action(greater_type, rank, list(combo)))

        elif greater_type == "Bomb":
            # 炸弹对炸弹：裁判先比张数（points[0]）再比牌值（points[1]），
            # 4 张高值炸不能压 5/6 张炸（G5）。
            greater_cnt = len(greater_cards) if greater_cards else 4
            for rank, cards in rank_groups.items():
                if len(cards) < 4:
                    continue
                if len(cards) != greater_cnt:
                    if len(cards) > greater_cnt:
                        actions.append(self._bomb_action(cards))
                    continue
                if _rank_to_order(rank, self.cur_rank) > greater_order:
                    actions.append(self._bomb_action(cards))
            # 逢人配补炸参与比炸：自然 3 张 + H{cur_rank} 为 4 张炸，
            # 仅能压 4 张炸（同张数比牌值），5+ 张炸不可压（G5）。
            if greater_cnt == 4:
                for bomb in self._wild_bomb_candidates(hand_cards):
                    if _rank_to_order(bomb[1], self.cur_rank) > greater_order:
                        actions.append(bomb)

        elif greater_type == "StraightFlush":
            sfs = self._generate_straight_flushes_by_suit(
                hand_cards, suits, greater_straight_top)
            actions.extend(sfs)

        elif greater_type == "ThreeWithTwo":
            for t_rank, t_cards in rank_groups.items():
                if _rank_to_order(t_rank, self.cur_rank) <= greater_order:
                    continue
                trip_combos = self._combos(t_cards, 3)
                if not trip_combos:
                    continue
                for p_rank, p_cards in rank_groups.items():
                    if p_rank == t_rank:
                        continue
                    pair_combos = self._combos(p_cards, 2)
                    for trips in trip_combos:
                        for pair in pair_combos:
                            actions.append(self._three_with_two_action(trips, pair))

        elif greater_type == "ThreePair":
            consecutive_pairs = self._find_consecutive_pairs(rank_groups, 3)
            for ranks, _pairs in consecutive_pairs:
                last_rank = ranks[-1]
                if _rank_to_order(last_rank, self.cur_rank) <= greater_order:
                    continue
                pair_combos = [self._combos(rank_groups[r], 2) for r in ranks]
                for combo in itertools.product(*pair_combos):
                    cards = [c for pc in combo for c in pc]
                    actions.append(self._three_pair_action(cards, last_rank))

        elif greater_type == "TwoTrips":
            consecutive_trips = self._find_consecutive_trips(rank_groups, 2)
            for ranks, _trips_list in consecutive_trips:
                last_rank = ranks[-1]
                if _rank_to_order(last_rank, self.cur_rank) <= greater_order:
                    continue
                trip_combos = [self._combos(rank_groups[r], 3) for r in ranks]
                for combo in itertools.product(*trip_combos):
                    cards = [c for tc in combo for c in tc]
                    actions.append(self._two_trips_action(cards, last_rank))

        elif greater_type == "Straight":
            rank_set = set(rank_groups.keys())
            for window in self._straight_windows(rank_set):
                low = window[0]
                if _rank_to_order(window[-1], self.cur_rank) <= greater_straight_top:
                    continue
                choices = [self._uniq_cards(rank_groups[r]) for r in window]
                for combo in itertools.product(*choices):
                    actions.append(self._straight_action(list(combo), low))
            # GUA-217: 跟牌轮配子补普通顺子缺位（能压 greater 的候选）
            actions.extend(self._generate_wild_straights(hand_cards, greater_straight_top))

        # Also add all bombs as valid follow plays
        if greater_type not in ("Bomb", "StraightFlush"):
            for rank, cards in rank_groups.items():
                if len(cards) >= 4:
                    actions.append(self._bomb_action(cards))
            # 逢人配补炸：自然 3 张同 rank + H{cur_rank} → 4 张 Bomb（GUA-199 配子补炸）。
            # 此前漏配子补炸，手牌 444+H2 时候选仅 PASS+Pair → 拆炸弹 core 打弱牌
            # （match=6a71ace3 回合11：H4,H4,D4,H2,C2 对 Pair/8 只出 22 对子）。
            actions.extend(self._wild_bomb_candidates(hand_cards))
            # 同花顺也是炸：能压任意非炸牌型（Single/Pair/Trips/Straight/TWT…）
            # 此前只补同 rank≥4 四头炸，漏同花顺炸 → 手牌仅剩 SF 时该压不压 PASS
            # （实测 match=6a714a8027e7bf01db1017a3：C5-C9 SF 对 Single/7 全程 PASS）。
            actions.extend(self._sf_bomb_candidates(hand_cards, suits))
        elif greater_type == "StraightFlush":
            # 同花顺只被 6+ 张炸压制（裁判：4/5 张炸 < 同花顺 < 6+ 炸，G1）
            for rank, cards in rank_groups.items():
                if len(cards) >= 6:
                    actions.append(self._bomb_action(cards))
        elif greater_type == "Bomb":
            # 同花顺压 4/5 张炸（裁判 G1：4/5 张炸 < 同花顺 < 6+ 炸）；
            # 6+ 炸压同花顺，不补。
            greater_cnt = len(greater_cards) if greater_cards else 4
            if greater_cnt < 6:
                actions.extend(self._sf_bomb_candidates(hand_cards, suits))

        seen: Set[str] = set()
        deduped = []
        for act in actions:
            key = self._action_key(act)
            if key not in seen:
                seen.add(key)
                deduped.append(act)
        return deduped

    def _sf_bomb_candidates(self, hand_cards: List[str],
                            suits: Dict[str, List[str]]) -> List[list]:
        """手牌中全部同花顺（自然 + H2 逢人配），作为跟牌炸弹候选。

        同花顺在掼蛋中属于炸弹，能压任意非炸牌型（_beats 已确认）。
        领出侧已有同花顺生成，跟牌侧此前漏掉，导致手牌仅剩 SF 时
        对手出 Single/Pair 等无法用 SF 压 → 该压不压 PASS。
        """
        sfs: List[list] = []
        for suit, s_cards in suits.items():
            if len(s_cards) >= 5:
                s_ranks = sorted(set(_card_rank(c) for c in s_cards),
                                key=lambda r: RANK_ORDER.get(r, 99))
                sfs.extend(self._generate_straight_flushes(s_cards, s_ranks))
        sfs.extend(self._generate_h2_wild_straight_flushes(hand_cards, suits))
        return sfs

    def _wild_bomb_candidates(self, hand_cards: List[str]) -> List[list]:
        """逢人配补炸：自然 3 张同 rank + H{cur_rank} 配子 → 4 张 Bomb。

        领出/跟牌炸弹枚举此前只认自然 4+ 同 rank，「444 + H2」配子补炸漏掉
        → actionList 无 Bomb，引擎只能 PASS 或拆炸弹 core 打弱牌
        （GUA-199，实测 match=6a71ace3 回合11：手牌 H4,H4,D4,H2,C2，greater Pair/8
        候选仅 PASS+Pair/2，H2 被拆出打 22 对子）。语义对齐
        `_generate_h2_wild_straight_flushes`（H2 恒作万能牌）。
        """
        wild = f"H{self.cur_rank}"
        if wild not in hand_cards:
            return []
        actions = []
        natural_groups = self._group_by_rank([c for c in hand_cards if c != wild])
        for rank, cards in natural_groups.items():
            if len(cards) == 3:
                # 配子放最后，保证 _bomb_action 以自然 rank 声明
                actions.append(self._bomb_action(list(cards) + [wild]))
        return actions

    def _single_action(self, card: str) -> list:
        return _make_action("Single", _card_rank(card), [card])

    def _pair_action(self, cards: List[str]) -> list:
        return _make_action("Pair", _card_rank(cards[0]), cards)

    def _trips_action(self, cards: List[str]) -> list:
        return _make_action("Trips", _card_rank(cards[0]), cards)

    def _bomb_action(self, cards: List[str]) -> list:
        return _make_action("Bomb", _card_rank(cards[0]), cards)

    def _three_with_two_action(self, trips: List[str], pair: List[str]) -> list:
        rank = _card_rank(trips[0])
        return _make_action("ThreeWithTwo", rank, trips + pair)

    def _straight_action(self, cards: List[str], rank: str) -> list:
        return _make_action("Straight", rank, cards)

    def _three_pair_action(self, cards: List[str], high_rank: str) -> list:
        return _make_action("ThreePair", high_rank, cards)

    def _two_trips_action(self, cards: List[str], high_rank: str) -> list:
        return _make_action("TwoTrips", high_rank, cards)

    def _straight_flush_action(self, cards: List[str], rank: str) -> list:
        return _make_action("StraightFlush", rank, cards)

    def _action_key(self, action: list) -> str:
        # 含牌型维度：Straight 与 StraightFlush 可用相同 5 张牌，不能互相去重。
        # 含 rank 维度：同花顺同一副牌可对应多个窗口（如 H2,H2,D6,D7,D8 →
        # rank '4' 与 '5' 都是合法动作，服务器 size=2209 实证两者共存），
        # 不能仅按牌面去重吞掉后者。
        cards = action[2] if len(action) >= 3 and isinstance(action[2], list) else []
        atype = action[0] if len(action) >= 1 else ""
        arank = action[1] if len(action) >= 2 else ""
        return f"{atype}|{arank}|{'|'.join(sorted(cards))}"

    def _group_by_rank(self, hand_cards: List[str]) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = defaultdict(list)
        for c in hand_cards:
            groups[_card_rank(c)].append(c)
        return dict(groups)

    def _group_by_suit(self, hand_cards: List[str]) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = defaultdict(list)
        for c in hand_cards:
            groups[c[0]].append(c)
        return dict(groups)

    @staticmethod
    def _uniq_cards(cards: List[str], max_cards: Optional[int] = None) -> List[str]:
        """去重并保留顺序（两副牌可能有重复 key），可选限长。"""
        uniq = list(dict.fromkeys(cards))
        if max_cards is not None:
            return uniq[:max_cards]
        return uniq

    @staticmethod
    def _combos(cards: List[str], n: int, max_cards: int = 4) -> List[List[str]]:
        """cards 中取 n 张的所有组合（保留两副牌重复牌，去重相同组合）。

        两副牌下同 rank 同花色可重复（如 ['CJ','HJ','HJ'] 三张 J），
        旧实现用 _uniq_cards 去重会把重复牌吞掉，导致 ThreeWithTwo /
        ThreePair / TwoTrips 无法生成 → GUA-075 推荐匹配不到 actionList
        → 该压不压 PASS（Botzone 实测两处）。
        修复：不去重直接组合，按排序后牌面 key 去重相同组合。
        """
        pool = cards[:max_cards]
        if len(pool) < n:
            return []
        seen: Set[Tuple[str, ...]] = set()
        result: List[List[str]] = []
        for combo in itertools.combinations(pool, n):
            key = tuple(sorted(combo))
            if key not in seen:
                seen.add(key)
                result.append(list(combo))
        return result

    @staticmethod
    def _all_straight_windows() -> List[List[str]]:
        """Botzone 官方顺子 rank 窗口全集（10 个，5 张）。

        A 可作 1（A2345）也可作 14（TJQKA）；JQKA2、2AKQJ 等非法。
        返回形如 [['A','2','3','4','5'], ..., ['T','J','Q','K','A']]。
        """
        seq = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
        return [seq[i:i + 5] for i in range(len(seq) - 5 + 1)]

    @staticmethod
    def _straight_windows(rank_set: Set[str]) -> List[List[str]]:
        """Botzone 官方顺子 rank 窗口（只能 5 张），要求窗口内 rank 全部在手。"""
        return [w for w in ActionListGenerator._all_straight_windows()
                if all(r in rank_set for r in w)]

    def _find_consecutive_pairs(self, rank_groups: Dict[str, List[str]],
                                length: int) -> List[Tuple[List[str], List[List[str]]]]:
        """Find consecutive ranks that each have >= 2 cards."""
        sorted_ranks = sorted(rank_groups.keys(), key=lambda r: RANK_ORDER.get(r, 99))
        result = []
        for i in range(len(sorted_ranks) - length + 1):
            chunk = sorted_ranks[i:i + length]
            if all(_card_rank_order(rank_groups[r][0], self.cur_rank) ==
                   _card_rank_order(rank_groups[chunk[0]][0], self.cur_rank) + idx
                   for idx, r in enumerate(chunk)):
                if all(len(rank_groups[r]) >= 2 for r in chunk):
                    pairs = [rank_groups[r][:2] for r in chunk]
                    result.append((list(chunk), pairs))
        return result

    def _find_consecutive_trips(self, rank_groups: Dict[str, List[str]],
                                length: int) -> List[Tuple[List[str], List[List[str]]]]:
        """Find consecutive ranks that each have >= 3 cards.

        必须与 _find_consecutive_pairs 一样校验点数连续：钢板 = 相邻两个三张
        （如 333-444），仅 len>=3 会把不相邻的 888+QQQ 拼成非法钢板
        （实测线上对局 6a717aab 被判「1号玩家非法牌型」）。
        """
        sorted_ranks = sorted(rank_groups.keys(), key=lambda r: RANK_ORDER.get(r, 99))
        result = []
        for i in range(len(sorted_ranks) - length + 1):
            chunk = sorted_ranks[i:i + length]
            if all(_card_rank_order(rank_groups[r][0], self.cur_rank) ==
                   _card_rank_order(rank_groups[chunk[0]][0], self.cur_rank) + idx
                   for idx, r in enumerate(chunk)):
                if all(len(rank_groups[r]) >= 3 for r in chunk):
                    trips = [rank_groups[r][:3] for r in chunk]
                    result.append((list(chunk), trips))
        return result

    def _generate_straights(self, rank_groups: Dict[str, List[str]],
                            suits: Dict[str, List[str]],
                            hand_cards: Optional[List[str]] = None) -> List[list]:
        """Generate straight actions (官方：只能五张相连，A 可作 1 或 14）。

        全组合：窗口内每个 rank 选一张（去重后前 3 张候选），笛卡尔积。
        hand_cards 非空时叠加 H{cur_rank} 配子补缺位候选（GUA-217）。
        """
        actions = []
        rank_set = set(rank_groups.keys())
        for window in self._straight_windows(rank_set):
            low = window[0]
            choices = [self._uniq_cards(rank_groups[r]) for r in window]
            for combo in itertools.product(*choices):
                actions.append(self._straight_action(list(combo), low))
        # GUA-217: 配子补普通顺子缺位（如 A2345 缺 3 → H{cur_rank} 当 3）。
        # 此前手牌 HA+D2+H2+D4+S5 组牌引擎识别 A2345，但 actionList 只有
        # Single×5+Pair×1，残局 Q0 只能拆 HA 打 Single/A（match 6a7772fb）。
        if hand_cards:
            actions.extend(self._generate_wild_straights(hand_cards))
        return actions

    def _generate_wild_straights(self, hand_cards: List[str],
                                 greater_top: Optional[int] = None) -> List[list]:
        """H{cur_rank} 配子补普通顺子缺位（GUA-217，领出/跟牌共用）。

        cur_rank=2 时 H2 万能牌可补 5 连窗口任意缺位 rank（如 HA+D2+H2+D4+S5
        → A2345，H2 当 3）；配子放 cards 末尾，rank 取窗口低牌 window[0]。
        greater_top 非空时（跟牌轮）只保留窗口最高牌 order > greater_top 的候选。
        """
        wild = f"H{self.cur_rank}"
        wild_count = hand_cards.count(wild)
        if wild_count == 0:
            return []
        actions = []
        natural = [c for c in hand_cards if c != wild]
        natural_groups = self._group_by_rank(natural)
        for window in self._all_straight_windows():
            missing = [r for r in window if r not in natural_groups]
            if not missing or len(missing) > wild_count:
                continue
            if greater_top is not None:
                # 窗口最高牌（A2345 → '5'）带级牌提升，与 _straight_top_order 一致
                if _rank_to_order(window[-1], self.cur_rank) <= greater_top:
                    continue
            low = window[0]
            choices = [self._uniq_cards(natural_groups[r])
                       for r in window if r not in missing]
            for combo in itertools.product(*choices):
                cards = list(combo) + [wild] * len(missing)
                actions.append(self._straight_action(cards, low))
        return actions

    def _generate_straight_flushes(self, suit_cards: List[str],
                                    suit_ranks: List[str]) -> List[list]:
        """Generate straight flush actions（官方：只能五张相连、花色相同）。

        全组合：同花色窗口内每个 rank 选一张（同花色同点最多 2 张）。
        rank 取窗口低牌（window[0]），与 OpenGuanDan 服务器 / 引擎推荐一致
        （如 9-K 同花顺 rank='9'；A2345 rank='A'）。
        """
        actions = []
        rank_set = set(_card_rank(c) for c in suit_cards)
        for window in self._straight_windows(rank_set):
            low = window[0]
            choices = []
            ok = True
            for r in window:
                cs = self._uniq_cards([c for c in suit_cards if _card_rank(c) == r], 2)
                if not cs:
                    ok = False
                    break
                choices.append(cs)
            if not ok:
                continue
            for combo in itertools.product(*choices):
                actions.append(self._straight_flush_action(list(combo), low))
        return actions

    def _generate_h2_wild_straight_flushes(
        self, hand_cards: List[str], suits: Dict[str, List[str]],
        greater_top: Optional[int] = None,
    ) -> List[list]:
        """逢人配同花顺（服务器语义，实测 size=2209 RAW 证据）。

        H{cur_rank} 万能牌（cur_rank=2 时即 H2）可补同花色 5 连窗口任意缺位
        （同一 SF 至多 2 张万能牌，两副牌上限）；同花色其它 rank 的 2
        （如 D2/S2/C2，当 cur_rank=2）是自然牌，仅 H{cur_rank} 是万能牌。
        rank 取窗口低牌（window[0]），如 ['S4','S5','S6','H2','S8'] → rank='4'。
        greater_top 非空时（跟牌路径）只保留能压过 greater 的候选。

        GUA-200（2026-08-04）：此前写死 H2，cur_rank≠2 时配子 SF 全部丢失。
        实证 match=6a71cf5f 回合19：级牌6 手牌 DA,D2,D3,D4,H6 本可组成
        A2345 同花顺炸压 Single/HR，actionList 却只剩配子补炸 Bomb/3（拆 SF
        core 被 _group_consistency_filter 拦截）→ 该炸未炸，对手双上。
        """
        wild = f"H{self.cur_rank}"
        actions = []
        wild_count = hand_cards.count(wild)
        if wild_count == 0:
            return actions
        for suit, s_cards in suits.items():
            # 万能牌只作补位，不参与本花色自然牌池（服务器 H{cur_rank} 恒作 wild）
            natural = [c for c in s_cards if c != wild]
            if len(natural) < 3:
                continue
            by_rank: Dict[str, List[str]] = defaultdict(list)
            for c in natural:
                by_rank[_card_rank(c)].append(c)
            for window in self._all_straight_windows():
                missing = [r for r in window if not by_rank.get(r)]
                if not missing or len(missing) > wild_count:
                    continue
                if greater_top is not None:
                    # 窗口最高牌（A2345 → '5'）带级牌提升，与 _straight_top_order 一致
                    if _rank_to_order(window[-1], self.cur_rank) <= greater_top:
                        continue
                choices = [self._uniq_cards(by_rank[r], 2)
                           for r in window if r not in missing]
                for combo in itertools.product(*choices):
                    cards = list(combo) + [wild] * len(missing)
                    actions.append(self._straight_flush_action(cards, window[0]))
        return actions

    def _generate_straight_flushes_by_suit(
        self, hand_cards: List[str], suits: Dict[str, List[str]],
        greater_top: int,
    ) -> List[list]:
        """跟牌路径：生成能压过 greater SF 的同花顺候选（含 H2 逢人配）。

        比较键 = 5 连窗口最高牌 order（_straight_top_order），而非 rank 字段——
        rank 字段已统一为窗口低牌（window[0]），不能直接用于「比最大」。
        """
        actions = []
        for suit, cards in suits.items():
            if len(cards) < 5:
                continue
            suit_ranks = sorted(set(_card_rank(c) for c in cards),
                               key=lambda r: RANK_ORDER.get(r, 99))
            for sf in self._generate_straight_flushes(cards, suit_ranks):
                if self._straight_top_order(sf[2], self.cur_rank) > greater_top:
                    actions.append(sf)
        actions.extend(
            self._generate_h2_wild_straight_flushes(hand_cards, suits, greater_top))
        return actions

    @staticmethod
    def _straight_top_order(cards: List[str], cur_rank: str = "2") -> int:
        """5 连牌（顺子/同花顺）的比较值 = 窗口最高牌 order（级牌提升沿用
        _rank_to_order 的 15）。

        A2345 视为窗口最高 '5'；TJQKA 最高 'A'。用于「比最大牌」，与服务器
        跟牌规则一致；不能用 rank 字段（已统一为窗口低牌）直接比较。
        """
        if not cards:
            return -1
        ranks = {_card_rank(c) for c in cards}
        if "A" in ranks and {"2", "3", "4", "5"}.issubset(ranks):
            top = "5"
        else:
            top = max(ranks, key=lambda r: RANK_ORDER.get(r, -1))
        return _rank_to_order(top, cur_rank)


# ──────────────────────────────────────────────
#  Game state manager
# ──────────────────────────────────────────────

@dataclass
class BotzoneGameState:
    """Tracks the full state of a single Botzone game (one completed 掼蛋 局)."""
    match_id: str
    player_id: int = 0
    cur_rank: str = "2"
    self_rank: str = "2"
    oppo_rank: str = "2"
    hand_cards: List[str] = field(default_factory=list)
    card_tracker: Optional[CardTracker] = None
    current_request: Optional[dict] = None
    episode_count: int = 0
    active: bool = True

    # For following plays
    cur_action: Optional[list] = None
    greater_action: Optional[list] = None
    greater_pos: int = -1
    cur_pos: int = -1

    # History tracking
    play_history: List[dict] = field(default_factory=list)

    # 各席累计已出 Botzone 整数牌（跨 request history 重叠去重用 set）
    # 用于推算各席剩张 → publicInfo[].rest → engine 残局管线激活（GUA-170）
    played_cards: Dict[int, Set[int]] = field(default_factory=dict)

    # Pass-on (接风) state
    pass_on: int = -1
    done: List[int] = field(default_factory=list)

    # Tribute memory
    tribute_info: dict = field(default_factory=dict)


class BotzoneAdapter:
    """Main Botzone Local AI adapter.

    Usage:
        engine = UltimateWinRateEngineV7(player_id=0)
        adapter = BotzoneAdapter(user_id="yf1_v8", api_key="your_key",
                                 base_url="https://www.botzone.org.cn/api",
                                 decision_engine=engine)
        asyncio.run(adapter.run())
    """

    def __init__(
        self,
        user_id: str,
        api_key: str,
        base_url: str = "https://www.botzone.org.cn/api",
        decision_engine=None,
        player_id: int = 0,
        poll_timeout: float = 30.0,
    ):
        self.user_id = user_id
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.decision_engine = decision_engine
        self.player_id = player_id

        self.localai_url = f"{self.base_url}/{user_id}/{api_key}/localai"
        self.runmatch_url = f"{self.base_url}/{user_id}/{api_key}/runmatch"

        self.games: Dict[str, BotzoneGameState] = {}
        self.action_generator = ActionListGenerator()
        self._pending_responses: Dict[str, str] = {}  # match_id -> response string
        self._max_decision_time = 1.5
        self._default_cur_rank = "2"
        # 轮询超时：Botzone 在无对局（含 Kicked）时可能挂起连接不返回，
        # timeout=None 会永久阻塞导致监听停摆；默认 30s 超时后重新轮询。
        self.poll_timeout = poll_timeout

    def set_decision_engine(self, engine) -> None:
        self.decision_engine = engine

    async def run(self, poll_interval: float = 1.0) -> None:
        """Main loop: poll Botzone, process requests, submit responses."""
        logger.info("BotzoneAdapter 启动: url=%s", self.localai_url)
        while True:
            try:
                await self._poll()
            except Exception as e:
                logger.error("轮询异常: %s", e, exc_info=True)
                await asyncio.sleep(poll_interval)
                continue

            # Process all games with pending requests
            for match_id, game in list(self.games.items()):
                if not game.active:
                    continue
                if game.current_request is not None:
                    try:
                        response = await self._handle_request(match_id, game)
                        if response is not None:
                            self._pending_responses[match_id] = response
                            game.current_request = None
                    except Exception as e:
                        logger.error("处理请求异常 match=%s: %s", match_id, e, exc_info=True)
                        self._pending_responses[match_id] = ""
                        game.current_request = None

            if not self._pending_responses:
                await asyncio.sleep(0.1)

    async def _poll(self) -> None:
        """Send GET request to Botzone Local AI API."""
        req = urllib.request.Request(self.localai_url)

        # Attach pending responses as headers
        pending = list(self._pending_responses.items())
        for match_id, resp in pending:
            req.add_header(f"X-Match-{match_id}", resp)

        try:
            with urllib.request.urlopen(req, timeout=self.poll_timeout) as res:
                body = res.read().decode("utf-8")
            self._pending_responses.clear()
        except socket.timeout:
            logger.debug("Botzone 轮询超时（连接被挂起，重新轮询）")
            return
        except urllib.error.HTTPError as e:
            if e.code == 504:
                logger.debug("Botzone 超时（正常，等待新 request）")
                return
            logger.warning("Botzone HTTP 错误: %s", e)
            return
        except urllib.error.URLError as e:
            logger.debug("Botzone 连接错误: %s", e)
            return

        self._process_poll_response(body)

    def _process_poll_response(self, body: str) -> None:
        """Parse the poll response body."""
        lines = body.strip().split("\n")
        if len(lines) < 1:
            return

        try:
            request_count, result_count = map(int, lines[0].split(" ", 1))
        except ValueError:
            logger.warning("无法解析首行: %s", lines[0])
            return

        idx = 1
        for i in range(request_count):
            if idx >= len(lines):
                break
            match_id = lines[idx].strip()
            request_json = lines[idx + 1].strip()
            idx += 2
            self._on_request(match_id, request_json)

        for i in range(result_count):
            if idx >= len(lines):
                break
            parts = lines[idx].strip().split(" ")
            idx += 1
            if len(parts) >= 3:
                match_id = parts[0]
                slot = int(parts[1])
                player_count = int(parts[2])
                scores = list(map(int, parts[3:])) if len(parts) > 3 else []
                self._on_result(match_id, slot, player_count, scores)

    def handle_online_turn_sync(self, full_input: dict) -> str:
        """Botzone 在线模式同步版（py3.6 沙箱无 asyncio.to_thread/run）。

        与 handle_online_turn 等价，但决策走同步直调（use_thread=False），
        供 scripts/launchers/botzone/__main__.py 使用——Botzone python3 沙箱
        (Ubuntu 16.04) 为 Python 3.6，asyncio.run(3.7+)/to_thread(3.9+) 不可用。
        """
        match_id = "online"
        if not isinstance(full_input, dict):
            return json.dumps([[], []], separators=(",", ":"))
        if "requests" not in full_input:
            # 长驻增量模式：平台 KEEP_RUNNING 下首回合发 requests 包装，
            # 后续回合发单对象（无 requests key）。单对象须直接处理，
            # 否则被空转忽略、current_request 恒为 None → 全程 PASS
            # （实测对局 6a746e0a：v8_10 常驻进程 play 回合全部 time=0 返回 PASS）。
            return self._handle_single_turn_sync(match_id, full_input)
        requests = full_input.get("requests") or []
        responses = full_input.get("responses") or []
        last_stage = ""

        for i, req_raw in enumerate(requests):
            req = req_raw
            if isinstance(req_raw, str):
                try:
                    req = json.loads(req_raw)
                except json.JSONDecodeError:
                    logger.warning("在线请求解析失败 i=%d raw=%s", i, req_raw[:200])
                    continue
            if not isinstance(req, dict):
                continue
            last_stage = req.get("stage", "")
            self._on_request(match_id, json.dumps(req, separators=(",", ":")))
            game = self.games.get(match_id)
            if game is None:
                continue
            if i < len(responses) and responses[i]:
                self._apply_online_self_response(game, responses[i])

        game = self.games.get(match_id)
        if game is None or game.current_request is None:
            if last_stage == "deal":
                return json.dumps([], separators=(",", ":"))
            return json.dumps([[], []], separators=(",", ":"))
        try:
            req = game.current_request
            if req.get("stage", "") == "play":
                resp = self._handle_play_decision_sync(match_id, game, req)
            elif req.get("stage", "") == "tribute":
                resp = self._handle_tribute_request(match_id, game, req)
            elif req.get("stage", "") == "return":
                resp = self._handle_return_request(match_id, game, req)
            else:
                resp = None
        except Exception:
            logger.error("在线决策异常", exc_info=True)
            resp = None
        if resp is None:
            resp = json.dumps([[], []], separators=(",", ":"))
        logger.info("在线决策输出: %s", resp)
        return resp

    def _handle_single_turn_sync(self, match_id: str, req: dict) -> str:
        """长驻增量模式单对象回合：无 requests/responses 包装，直接决策。

        增量模式下无 responses 数组，自己的已出牌须从本回合 history 应用
        （全量模式靠 _apply_online_self_response），否则 hand_cards 只增不减。
        """
        try:
            self._on_request(match_id, json.dumps(req, separators=(",", ":")))
        except Exception:
            logger.error("在线增量回合请求处理异常", exc_info=True)
            return json.dumps([[], []], separators=(",", ":"))
        game = self.games.get(match_id)
        if game is None:
            return json.dumps([[], []], separators=(",", ":"))
        stage = req.get("stage", "")
        if stage == "deal":
            # deal 无响应（_on_request 已建状态），返回空动作数组
            return json.dumps([], separators=(",", ":"))
        # 注意：增量模式下自己已出的牌只在决策路径（_handle_play_decision 第 6 步
        # "Update hand tracking"）扣减一次。history 中 player==自己的动作是上一轮
        # 决策已扣过的牌，此处若再从 history 重复扣减会双扣，导致手牌漂移
        # （GUA-216：真手牌含 SB 时被误删，线上退化为 PASS）。
        if game.current_request is None:
            return json.dumps([[], []], separators=(",", ":"))
        try:
            r = game.current_request
            rs = r.get("stage", "")
            if rs == "play":
                return self._handle_play_decision_sync(match_id, game, r)
            if rs == "tribute":
                return self._handle_tribute_request(match_id, game, r)
            if rs == "return":
                return self._handle_return_request(match_id, game, r)
        except Exception:
            logger.error("在线增量回合决策异常", exc_info=True)
        return json.dumps([[], []], separators=(",", ":"))

    async def handle_online_turn(self, full_input: dict) -> str:
        """Botzone 在线模式：全量重放 requests/responses 后对当前回合决策。

        在线 bot（JSON Interaction）每回合由平台调用一次，stdin 输入
        {"requests": [...], "responses": [...], "data": ..., "globaldata": ...}
        —— requests 为该局从头到当前回合的全部请求（首元素为 deal），
        responses 为自己此前全部响应。本方法复用 Local AI 的决策链
        （_on_request 重建状态 + _handle_request 决策），输出须为
        {"response": <JSON 字符串>, "data": ..., "globaldata": ...}。

        与 Local AI 差异：
          - match_id 固定为 "online"（单局单进程）；
          - 不依赖 HTTP 轮询 / pending_responses；
          - 支持 KEEP_RUNNING 长驻（进程存活，首回合加载一次引擎后复用）。
        """
        match_id = "online"
        if not isinstance(full_input, dict):
            return json.dumps([[], []], separators=(",", ":"))
        if "requests" not in full_input:
            # 长驻增量模式：单对象回合直接决策（见 _handle_single_turn_sync 说明）。
            return self._handle_single_turn_sync(match_id, full_input)
        requests = full_input.get("requests") or []
        responses = full_input.get("responses") or []
        last_stage = ""

        # 全量重放历史：从 deal 开始逐条喂入，重建 state（hand_cards / greater /
        # play_history / played_cards / pass_on / done），并同步自己此前响应。
        for i, req_raw in enumerate(requests):
            req = req_raw
            if isinstance(req_raw, str):
                try:
                    req = json.loads(req_raw)
                except json.JSONDecodeError:
                    logger.warning("在线请求解析失败 i=%d raw=%s", i, req_raw[:200])
                    continue
            if not isinstance(req, dict):
                continue
            last_stage = req.get("stage", "")
            self._on_request(match_id, json.dumps(req, separators=(",", ":")))
            game = self.games.get(match_id)
            if game is None:
                continue
            # 历史回合：把该回合自己的响应同步进状态（进贡/还贡/出牌对手牌有影响）
            if i < len(responses) and responses[i]:
                self._apply_online_self_response(game, responses[i])

        # 当前回合决策
        game = self.games.get(match_id)
        if game is None or game.current_request is None:
            if last_stage == "deal":
                return json.dumps([], separators=(",", ":"))
            return json.dumps([[], []], separators=(",", ":"))
        try:
            resp = await self._handle_request(match_id, game)
        except Exception:
            logger.error("在线决策异常", exc_info=True)
            resp = None
        if resp is None:
            resp = json.dumps([[], []], separators=(",", ":"))
        logger.info("在线决策输出: %s", resp)
        return resp

    def _apply_online_self_response(self, game: BotzoneGameState,
                                    resp_raw: str) -> None:
        """在线重放中应用自己某一历史回合的响应到 game 状态。

        仅处理会改变手牌的动作（tribute/return/play 出的牌），PASS 无影响。
        之所以需要：重放时 _on_request 只重建「他人动作带来的 state」，
        自己出过的牌必须从 hand_cards 扣除，否则当前回合手牌数错误。
        """
        if resp_raw is None:
            return
        resp = resp_raw
        if isinstance(resp_raw, str):
            try:
                resp = json.loads(resp_raw)
            except json.JSONDecodeError:
                return
        if not isinstance(resp, list) or not resp:
            return
        action_cards = resp[0]
        if not isinstance(action_cards, list) or not action_cards:
            return
        v8_cards = bz_to_v8_cards(action_cards)
        for card in v8_cards:
            if card in game.hand_cards:
                game.hand_cards.remove(card)
        if game.card_tracker is not None:
            game.card_tracker.remove_multi(v8_cards)

    def _on_request(self, match_id: str, request_json: str) -> None:
        """Handle a new request from Botzone."""
        try:
            req = json.loads(request_json)
        except json.JSONDecodeError:
            logger.warning("无法解析 request JSON: match=%s", match_id)
            return

        stage = req.get("stage", "")
        logger.info("收到 request: match=%s stage=%s", match_id, stage)
        if stage == "play":
            logger.info("play request raw: match=%s %s", match_id, request_json)

        if match_id not in self.games:
            self.games[match_id] = BotzoneGameState(match_id=match_id, player_id=self.player_id)

        game = self.games[match_id]

        if stage == "deal":
            self._handle_deal(game, req)
            self._pending_responses[match_id] = "[]"
        elif stage == "tribute":
            game.current_request = req
            self._sync_tribute_info_from_global(game, self._extract_global(req))
        elif stage == "return":
            game.current_request = req
            self._sync_tribute_info_from_global(game, self._extract_global(req))
        elif stage == "play":
            self._handle_play_request(game, req)
            game.current_request = req
        elif stage in ("episodeOver", "gameOver"):
            logger.info("对局阶段结束: match=%s stage=%s", match_id, stage)
            if stage == "gameOver":
                game.active = False

    @staticmethod
    def _extract_global(req: dict) -> dict:
        """提取全局信息，兼容两种格式：
        A. 官方 wiki：global 字段包裹，level 为字符串（如 "2"）；
        B. 实测新格式：字段平铺在 request 顶层，level 为数组（如 ["2","2"]），
           含 seed 等额外字段（Botzone 掼蛋 2v2 每阵营一个等级）。
        """
        g = req.get("global")
        if isinstance(g, dict):
            return g
        keys = ("level", "tribute", "first", "last", "resist",
                "tribute_cards", "return_cards")
        return {k: v for k, v in req.items() if k in keys}

    @staticmethod
    def _resolve_level(level, player_id: int) -> str:
        """level 兼容字符串 "2" 与数组 ["2","2"]（每阵营等级）。
        2v2 队伍 = {0,2}（teamA）vs {1,3}（teamB）；V8 座位 0，队友 2。
        """
        if isinstance(level, list):
            if not level:
                return "2"
            team_idx = 0 if player_id in (0, 2) else 1
            if len(level) <= team_idx:
                return str(level[0])
            return str(level[team_idx])
        return str(level or "2")

    @staticmethod
    def _first_bz_card(value) -> Optional[int]:
        """Botzone global 中单张牌：int 或 [int]。"""
        if isinstance(value, list):
            if not value:
                return None
            value = value[0]
        if isinstance(value, int) and value >= 0:
            return value
        return None

    def _tribute_card_sort_key(
        self, card_int: int, cur_rank: str, last_player: int, payer: int,
    ) -> tuple:
        v8 = bz_to_v8_card(card_int)
        order = _card_rank_order(v8, cur_rank)
        last_bonus = 1 if payer == last_player else 0
        return (order, last_bonus)

    def _tribute_receiver(self, global_info: dict, payer: int, cur_rank: str) -> int:
        """进贡接收方（对齐 Botzone 裁判双贡大贡→头游、小贡→二游）。"""
        first = int(global_info.get("first", -1) if global_info.get("first") is not None else -1)
        last = int(global_info.get("last", -1) if global_info.get("last") is not None else -1)
        tc = global_info.get("tribute_cards") or {}
        items: List[Tuple[int, int]] = []
        for k, v in tc.items():
            card_int = self._first_bz_card(v)
            if card_int is None:
                continue
            try:
                pid = int(k)
            except (TypeError, ValueError):
                continue
            items.append((pid, card_int))
        if len(items) <= 1:
            return first
        items.sort(
            key=lambda kv: self._tribute_card_sort_key(kv[1], cur_rank, last, kv[0]),
            reverse=True,
        )
        if items[0][0] == payer:
            return first
        return (first + 2) % 4

    def _return_receiver(self, global_info: dict, returner: int, cur_rank: str) -> int:
        """还贡接收方（对齐 Botzone 裁判：头游还大贡、二游还小贡）。"""
        first = int(global_info.get("first", -1) if global_info.get("first") is not None else -1)
        last = int(global_info.get("last", -1) if global_info.get("last") is not None else -1)
        tc = global_info.get("tribute_cards") or {}
        items: List[Tuple[int, int]] = []
        for k, v in tc.items():
            card_int = self._first_bz_card(v)
            if card_int is None:
                continue
            try:
                pid = int(k)
            except (TypeError, ValueError):
                continue
            items.append((pid, card_int))
        if len(items) == 1:
            return items[0][0]
        if len(items) == 2:
            items.sort(
                key=lambda kv: self._tribute_card_sort_key(kv[1], cur_rank, last, kv[0]),
                reverse=True,
            )
            big_payer, small_payer = items[0][0], items[1][0]
            if returner == first:
                return big_payer
            return small_payer
        return -1

    def _build_open_guandan_tribute_phase(
        self, global_info: dict, cur_rank: str,
    ) -> dict:
        """Botzone global → OpenGuanDan tributeResult/backResult/antiPos（GUA-072）。"""
        empty = {"tributeResult": None, "backResult": None, "antiPos": None}
        if not global_info:
            return empty

        tribute_mode = int(global_info.get("tribute", 0) or 0)
        last = int(global_info.get("last", -1) if global_info.get("last") is not None else -1)
        resist = bool(global_info.get("resist", False))
        tribute_cards = global_info.get("tribute_cards") or {}
        return_cards = global_info.get("return_cards") or {}

        if resist:
            anti: Optional[List[int]] = None
            if tribute_mode == 2 and last >= 0:
                anti = [last, (last + 2) % 4]
            elif last >= 0:
                anti = [last]
            return {"tributeResult": None, "backResult": None, "antiPos": anti}

        tribute_result: List[List[Any]] = []
        for payer_s, raw in tribute_cards.items():
            card_int = self._first_bz_card(raw)
            if card_int is None:
                continue
            try:
                payer = int(payer_s)
            except (TypeError, ValueError):
                continue
            receiver = self._tribute_receiver(global_info, payer, cur_rank)
            if receiver < 0:
                continue
            tribute_result.append([payer, receiver, bz_to_v8_card(card_int)])

        back_result: List[List[Any]] = []
        for returner_s, raw in return_cards.items():
            card_int = self._first_bz_card(raw)
            if card_int is None:
                continue
            try:
                returner = int(returner_s)
            except (TypeError, ValueError):
                continue
            receiver = self._return_receiver(global_info, returner, cur_rank)
            if receiver < 0:
                continue
            back_result.append([returner, receiver, bz_to_v8_card(card_int)])

        return {
            "tributeResult": tribute_result or None,
            "backResult": back_result or None,
            "antiPos": None,
        }

    def _sync_tribute_info_from_global(
        self, game: BotzoneGameState, global_info: dict,
    ) -> None:
        """从 Botzone global 刷新本副贡牌阶段记忆（供 MemoryTracker / 信念门控）。"""
        if not global_info:
            return
        has_tribute_data = bool(
            global_info.get("tribute_cards")
            or global_info.get("return_cards")
            or global_info.get("resist")
        )
        tribute_mode = int(global_info.get("tribute", 0) or 0)
        if has_tribute_data or tribute_mode == 0:
            game.tribute_info = self._build_open_guandan_tribute_phase(
                global_info, game.cur_rank,
            )

    def _handle_deal(self, game: BotzoneGameState, req: dict) -> None:
        """Handle deal stage: set up hand cards."""
        bz_hand = req.get("deliver", [])
        game.hand_cards = bz_to_v8_cards(bz_hand)
        game.card_tracker = CardTracker.from_bz_hand(bz_hand)
        game.player_id = req.get("your_id", game.player_id)
        global_info = self._extract_global(req)
        level = self._resolve_level(global_info.get("level", "2"), game.player_id)
        game.cur_rank = level
        game.self_rank = level
        game.oppo_rank = level
        game.play_history = []
        game.played_cards = {}
        game.pass_on = -1
        game.done = []
        game.tribute_info = {}
        game.episode_count += 1
        game.current_request = None  # deal needs no response
        # 每副开始重置引擎跨副残留状态（MemoryTracker / 增量回放游标等）。
        # 缺失会跨副/跨 match 串位：_tracker_history_replayed 从上一副末值继续，
        # 新副首 request 的 history 从头开始 → 增量回放 `history[start:]` 全空，
        # MemoryTracker 完全失忆（与 yf1_v8.py on_game_start 每 game_start 调用对齐）。
        if self.decision_engine is not None:
            try:
                self.decision_engine.on_game_start(game.player_id)
            except Exception:
                logger.warning("on_game_start 失败 match=%s", game.match_id, exc_info=True)
        self._sync_tribute_info_from_global(game, global_info)
        logger.info(
            "发牌: match=%s player=%d hand=%d curRank=%s hand=%s",
            game.match_id, game.player_id, len(game.hand_cards), level,
            sorted(game.hand_cards),
        )

    def _handle_play_request(self, game: BotzoneGameState, req: dict) -> None:
        """Update game state from a play request."""
        history = req.get("history", [])
        if history:
            game.play_history.extend(history)
            self._update_from_history(game, history)
            self._accumulate_played_cards(game, history)

        game.done = req.get("done", [])
        game.pass_on = req.get("pass_on", -1)

        global_info = self._extract_global(req)
        if "level" in global_info:
            game.cur_rank = self._resolve_level(global_info["level"], game.player_id)
        self._sync_tribute_info_from_global(game, global_info)

    def _accumulate_played_cards(self, game: BotzoneGameState, history: list) -> None:
        """累计各席已出的 Botzone 整数牌（set 去重，跨 request history 重叠安全）。"""
        for player, action_cards, _claim_cards in self._parse_bz_play_history(history):
            if player < 0 or not action_cards:
                continue
            game.played_cards.setdefault(player, set()).update(action_cards)

    def _count_bombs_played(self, game: BotzoneGameState) -> dict:
        """GUA-293：跨整个对局累计各席炸弹数（含同花顺），供 GUA-289 读上家 historical 炸。

        背景：Botzone 在线每次只把「当前 request 的 history」喂给引擎 MemoryTracker，
        且 `_replay_history_to_tracker` 的 `_tracker_history_replayed` 停在首副首圈长度后
        永不增长 → 在线模式 MemoryTracker.bombs_played 恒空，GUA-289 读它永远拿不到
        上家 historical 炸而失效（match 6a9517d9 第49回合放走上家）。
        此处改用 adapter 端累计的 game.play_history（整个对局，_handle_play_request 逐
        request extend），按 (player, 牌面集合) 去重统计炸弹数，跨 request 重叠安全。
        """
        cur_rank = game.cur_rank
        bombs: dict = {}
        seen = set()
        for player, action_cards, claim_cards in self._parse_bz_play_history(game.play_history):
            if player < 0 or not action_cards:
                continue
            v8_action = self._bz_response_to_v8_action(
                action_cards, bz_claim_cards=claim_cards, cur_rank=cur_rank)
            if not v8_action or str(v8_action[0]).upper() == "PASS":
                continue
            if str(v8_action[0]).upper() in ("BOMB", "STRAIGHTFLUSH"):
                key = (player, tuple(sorted(str(c) for c in v8_action[2])))
                if key in seen:
                    continue
                seen.add(key)
                bombs[player] = bombs.get(player, 0) + 1
        return bombs

    def _compute_numofplayers(self, game: BotzoneGameState,
                              hand_cards: List[str],
                              known_done: List[int]) -> List[int]:
        """推算各席剩余张数：自己实牌数，done 玩家 0，其他 = 27 - 已出。

        Botzone 每副 27 张起（两副牌 108/4）；进贡/还贡只交换不改变张数。
        """
        numofplayers = [27] * 4
        for seat in range(4):
            if seat == game.player_id:
                numofplayers[seat] = len(hand_cards)
            elif seat in known_done:
                numofplayers[seat] = 0
            else:
                played = len(game.played_cards.get(seat, set()))
                numofplayers[seat] = max(0, 27 - played)
        return numofplayers

    def _compute_remaining_pool(self, game: "BotzoneGameState",
                                hand_cards: List[str]) -> List[str]:
        """GUA-244：name 级剩余池 = 108 ints − 各席已出 − 当前手牌。

        Botzone 每副 27 张、每张牌名 2 副本（int i 与 i+54 同牌名）。
        返回展开的牌名列表（按 _POOL_NAME_ORDER 序）；供引擎/残局决策做
        对手残牌构成推理（对子/单被接风险）。
        """
        played: Counter = Counter()
        for seat in range(4):
            for i in game.played_cards.get(seat, set()):
                if 0 <= i <= 107:
                    played[bz_to_v8_card(i)] += 1
        hand: Counter = Counter(hand_cards or [])
        pool: List[str] = []
        for name in _POOL_NAME_ORDER:
            cnt = 2 - hand.get(name, 0) - played.get(name, 0)
            pool.extend([name] * max(0, cnt))
        return pool

    def _update_from_history(self, game: BotzoneGameState, history: list) -> None:
        """Update greater action from play history."""
        for entry in history:
            if isinstance(entry, list):
                player = entry[0] if len(entry) > 0 else -1
                resp = entry[1] if len(entry) > 1 else [[], []]
            else:
                player = entry.get("player", -1)
                resp = entry.get("response", [[], []])
            action_list = resp[0] if isinstance(resp, list) and len(resp) > 0 else []
            if action_list:
                claim_list = (resp[1] if isinstance(resp, list) and len(resp) > 1
                              and isinstance(resp[1], list) else None)
                v8_action = self._bz_response_to_v8_action(
                    action_list, bz_claim_cards=claim_list, cur_rank=game.cur_rank)
                game.cur_action = v8_action
                game.cur_pos = player
                # If not pass and beats current greater, update greater
                if v8_action and v8_action[0] != "PASS":
                    if (game.greater_action is None or
                            self._beats(v8_action, game.greater_action, game.cur_rank)):
                        game.greater_action = v8_action
                        game.greater_pos = player
            else:
                # Pass
                game.cur_action = None
                game.cur_pos = player

    def _bz_response_to_v8_action(self, bz_action_cards: List[int],
                                  bz_claim_cards: Optional[List[int]] = None,
                                  cur_rank: Optional[str] = None) -> Optional[list]:
        """Convert Botzone play action (list of card ints) to OpenGuanDan format.

        逢人配牌形下 Botzone 下发的 [action, claim] 两栏：action 是实际物理牌
        （逢人配如 H{cur_rank} 保持原值），claim 才是声明成的牌型（逢人配
        已按声明补齐，如 H2 充当 D5 组成 D5-D9 同花顺）。只用 action 分类会把
        逢人配同花顺误判为 Free（实测 match=6a759ae9 16:44:42：greater 被判
        ['Free','2',...]，4 头炸被当合法压牌出，实际压不过同花顺）。
        因此优先用 claim 牌分类（平台保证合法），Free 时回退到实际牌。
        """
        if not bz_action_cards:
            return ["PASS", "PASS", "PASS"]
        if bz_claim_cards:
            claim_v8 = bz_to_v8_cards(bz_claim_cards)
            claimed = self._classify_action(claim_v8, cur_rank)
            if claimed and claimed[0] != "Free":
                return claimed
        v8_cards = bz_to_v8_cards(bz_action_cards)
        return self._classify_action(v8_cards, cur_rank)

    def _classify_action(self, cards: List[str], cur_rank: Optional[str] = None) -> Optional[list]:
        """Classify a list of V8 cards into an OpenGuanDan action tuple."""
        cr = cur_rank or self._default_cur_rank
        if not cards:
            return ["PASS", "PASS", "PASS"]
        n = len(cards)
        ranks = [_card_rank(c) for c in cards]
        suits = [c[0] for c in cards]
        rank_counts = Counter(ranks)
        most_common = rank_counts.most_common()

        if n == 1:
            return _make_action("Single", ranks[0], cards)
        if n == 2 and len(most_common) == 1:
            return _make_action("Pair", ranks[0], cards)
        if n == 3 and len(most_common) == 1:
            return _make_action("Trips", ranks[0], cards)
        if len(most_common) == 1 and n >= 4:
            return _make_action("Bomb", ranks[0], cards)
        if n == 5:
            # 顺子/同花顺：级牌不提升（裁判 cardscale 中 2 为自然位，level=2 的
            # 2-3-4-5-6 仍是合法顺子，实测 match=6a71ace3 对手打 2-6 被误判 Free）。
            # 用官方 10 个窗口匹配（A2345 … TJQKA），避免 _rank_to_order 级牌
            # 提升打断连续性。
            if self._is_straight_ranks(ranks) and len(set(suits)) == 1:
                return _make_action("StraightFlush", self._straight_low(ranks), cards)
            if self._is_straight_ranks(ranks):
                return _make_action("Straight", self._straight_low(ranks), cards)
        if n == 5 and 3 in rank_counts.values() and 2 in rank_counts.values():
            trip_rank = [r for r, c in most_common if c == 3][0]
            return _make_action("ThreeWithTwo", trip_rank, cards)
        if n == 6:
            if all(c == 2 for r, c in most_common) and self._is_consecutive(
                    [r for r, c in most_common], cr):
                high = max([r for r, c in most_common],
                          key=lambda r: _rank_to_order(r, cr))
                return _make_action("ThreePair", high, cards)
            if all(c == 3 for r, c in most_common) and len(most_common) == 2:
                high = max(most_common[0][0], most_common[1][0],
                          key=lambda r: _rank_to_order(r, cr))
                return _make_action("TwoTrips", high, cards)

        return _make_action("Free", ranks[0] if ranks else "2", cards)

    @staticmethod
    def _is_straight_ranks(ranks: List[str]) -> bool:
        """5 张牌 rank 是否构成官方顺子窗口（A2345 / 23456 / … / TJQKA）。"""
        rs = set(ranks)
        return len(rs) == 5 and any(
            set(w) == rs for w in ActionListGenerator._all_straight_windows())

    @staticmethod
    def _straight_low(ranks: List[str]) -> str:
        """顺子窗口低牌（裁判 points[0] 语义）：A2345→'A'、23456→'2'、TJQKA→'T'。"""
        rs = set(ranks)
        for w in ActionListGenerator._all_straight_windows():
            if set(w) == rs:
                return w[0]
        return min(ranks, key=lambda r: RANK_ORDER.get(r, -1))

    def _is_consecutive(self, ranks: List[str], cur_rank: Optional[str] = None) -> bool:
        """Check if ranks form a consecutive sequence."""
        cr = cur_rank or self._default_cur_rank
        orders = sorted(set(_rank_to_order(r, cr) for r in ranks))
        if len(orders) < 5:
            return False
        for i in range(1, len(orders)):
            if orders[i] - orders[i - 1] != 1:
                return False
        return True

    def _beats(self, action: list, greater: list, cur_rank: str = "2") -> bool:
        """Check if action beats greater (裁判 checkBigger 语义，用于合法性防线)。

        - 火箭 > 炸弹/同花顺 > 普通牌型；
        - 同花顺 vs 炸弹：4/5 张炸 < 同花顺 < 6+ 张炸（裁判先比张数）；
        - 炸弹 vs 炸弹：先比张数（裁判 points[0]），同张数再比牌值（points[1]）；
        - 顺子/同花顺比窗口最高牌（rank 字段是窗口低牌，不能直接比大小）。
        """
        t1, r1 = action[0], action[1] if len(action) >= 2 else ""
        t2, r2 = greater[0], greater[1] if len(greater) >= 2 else ""

        def _bomb_count(a: list) -> int:
            cards = a[2] if len(a) >= 3 and isinstance(a[2], list) else []
            return len(cards)

        if t1 not in ("Bomb", "StraightFlush"):
            # 普通牌型不能压炸弹/同花顺
            if t2 in ("Bomb", "StraightFlush"):
                return False
        else:
            if t2 not in ("Bomb", "StraightFlush"):
                return True
            if t1 == "Bomb" and t2 == "Bomb":
                a_cnt, g_cnt = _bomb_count(action), _bomb_count(greater)
                if a_cnt != g_cnt:
                    return a_cnt > g_cnt
                return _rank_to_order(r1, cur_rank) > _rank_to_order(r2, cur_rank)
            if t1 == "StraightFlush" and t2 == "Bomb":
                # 同花顺只压 4/5 张炸；6+ 炸 > 同花顺
                return _bomb_count(greater) < 6
            if t1 == "Bomb" and t2 == "StraightFlush":
                # 6+ 炸压同花顺；4/5 张炸不压
                return _bomb_count(action) >= 6
        if t1 == t2:
            if t1 in ("Straight", "StraightFlush"):
                a_cards = (action[2]
                           if len(action) >= 3 and isinstance(action[2], list) else [])
                g_cards = (greater[2]
                           if len(greater) >= 3 and isinstance(greater[2], list) else [])
                if a_cards and g_cards:
                    return (ActionListGenerator._straight_top_order(a_cards, cur_rank)
                            > ActionListGenerator._straight_top_order(g_cards, cur_rank))
            return _rank_to_order(r1, cur_rank) > _rank_to_order(r2, cur_rank)
        return False

    async def _handle_request(self, match_id: str, game: BotzoneGameState,
                              use_thread: bool = True) -> Optional[str]:
        """Process a Botzone request and return the response string."""
        req = game.current_request
        if req is None:
            return None

        stage = req.get("stage", "")

        if stage == "tribute":
            return self._handle_tribute_request(match_id, game, req)
        elif stage == "return":
            return self._handle_return_request(match_id, game, req)
        elif stage == "play":
            return await self._handle_play_decision(match_id, game, req,
                                                    use_thread=use_thread)
        return None

    def _handle_tribute_request(self, match_id: str, game: BotzoneGameState,
                                req: dict) -> str:
        """Handle tribute: give the biggest non-wild card."""
        if not game.hand_cards:
            return "[]"
        hand_ordered = sorted(game.hand_cards,
                             key=lambda c: _card_rank_order(c, game.cur_rank),
                             reverse=True)
        wild = f"H{game.cur_rank}"
        for card in hand_ordered:
            if card != wild:
                bz_cards = game.card_tracker.remove_multi([card]) if game.card_tracker else []
                game.hand_cards.remove(card)
                if bz_cards:
                    return json.dumps([bz_cards[0]], separators=(",", ":"))
                return json.dumps([v8_to_bz_int(card)], separators=(",", ":"))
        return "[]"

    def _handle_return_request(self, match_id: str, game: BotzoneGameState,
                               req: dict) -> str:
        """Handle return tribute: give back a card <= 9 (level='9' 时 <= 8)."""
        # First, add any tribute card received into hand
        tribute_cards: dict = self._extract_global(req).get("tribute_cards", {})
        for payer_id, bz_card in tribute_cards.items():
            if isinstance(bz_card, int) and bz_card >= 0:
                v8_card = bz_to_v8_card(bz_card)
                if v8_card not in game.hand_cards:
                    game.hand_cards.append(v8_card)
                    if game.card_tracker:
                        game.card_tracker.add(v8_card, bz_card)

        # 裁判 isValidReturn：还贡须 ≤'9'（level='9' 时 ≤'8'），按级牌重排后点序。
        # RANK_ORDER：'9'→7、'8'→6；级牌卡 `_card_rank_order` 返回 15 被自然排除。
        max_return = "8" if game.cur_rank == "9" else "9"
        threshold = RANK_ORDER[max_return]
        candidates = [c for c in game.hand_cards
                      if _card_rank_order(c, game.cur_rank) <= threshold]
        if not candidates:
            candidates = game.hand_cards[:]
        return_card = min(candidates, key=lambda c: _card_rank_order(c, game.cur_rank))
        bz_cards = game.card_tracker.remove_multi([return_card]) if game.card_tracker else []
        game.hand_cards.remove(return_card)
        if bz_cards:
            return json.dumps([bz_cards[0]], separators=(",", ":"))
        return json.dumps([v8_to_bz_int(return_card)], separators=(",", ":"))

    def _build_bz_claim(self, chosen: list, cur_rank: str,
                        bz_ints: List[int]) -> List[int]:
        """构造 Botzone claim（裁判用 checkPokerType(claim) 判型）。

        官方规定「出牌中不包含配子时，两个数组应当相同」→ 默认 claim==action；
        含 H+cur_rank 逢人配且作配子（同花顺补缺位）时，把配子替换为所代表
        rank 的同花牌，否则含 H2 的 claim 会被裁判判 invalid → INVALID_TYPE（G2）。
        """
        v8_cards = (chosen[2]
                    if len(chosen) >= 3 and isinstance(chosen[2], list) else [])
        covering = f"H{cur_rank}"
        if covering not in v8_cards:
            return bz_ints
        if chosen[0] == "Bomb":
            # 逢人配补炸：H{cur_rank} 作配子补足自然 3 张同 rank，claim 须把配子
            # 替换为所代表 rank 的牌，否则裁判判 invalid（与同花顺同规则 G2）。
            claim_cards = self._replace_bomb_covering(v8_cards, cur_rank)
            if claim_cards is not None:
                return v8_to_bz_cards(claim_cards)
            return bz_ints
        if chosen[0] in ("Pair", "Trips"):
            # GUA-195 配子补对/三：与炸弹同规则，claim 须替换配子。
            claim_cards = self._replace_bomb_covering(v8_cards, cur_rank)
            if claim_cards is not None:
                return v8_to_bz_cards(claim_cards)
            return bz_ints
        if chosen[0] == "ThreeWithTwo":
            # GUA-280：配子补三带二（KK+H2+JJ）claim==action → INVALID_TYPE。
            trip_rank = chosen[1] if len(chosen) >= 2 else ""
            claim_cards = self._replace_twt_covering(v8_cards, cur_rank, trip_rank)
            if claim_cards is not None:
                return v8_to_bz_cards(claim_cards)
            return bz_ints
        if chosen[0] == "Straight":
            # GUA-217: 配子补普通顺子缺位（如 HA+D2+H2+D4+S5 → A2345），claim
            # 须把配子替换为所代表 rank 的牌，否则含 H2 的 claim 被判 INVALID_TYPE。
            low_rank = chosen[1] if len(chosen) >= 2 else ""
            try:
                claim_cards = self._replace_straight_covering(v8_cards, cur_rank, low_rank)
                if claim_cards is not None:
                    return v8_to_bz_cards(claim_cards)
            except Exception as exc:  # 兜底：不阻断出牌，退回 claim==action
                logger.warning("构造顺子 claim 失败，退回 claim==action: %s", exc)
            return bz_ints
        if chosen[0] != "StraightFlush":
            return bz_ints
        low_rank = chosen[1] if len(chosen) >= 2 else ""
        try:
            claim_cards = self._replace_sf_covering(v8_cards, cur_rank, low_rank)
            if claim_cards is not None:
                return v8_to_bz_cards(claim_cards)
        except Exception as exc:  # 兜底：不阻断出牌，退回 claim==action
            logger.warning("构造同花顺 claim 失败，退回 claim==action: %s", exc)
        return bz_ints

    def _replace_sf_covering(self, v8_cards: List[str], cur_rank: str,
                             low_rank: str = "") -> Optional[List[str]]:
        """H+cur_rank 逢人配同花顺：把配子替换为窗口缺位 rank 的同花牌。

        窗口由 chosen 的 rank 字段（窗口低牌，window[0]）消歧——同一副牌可对应
        多个窗口（如 [H2,S4,S5,S6,S7] 可作 3-7 或 4-8）。返回 None 表示配子作
        自然级牌（如 A2345 窗口的 H2），claim==action 即可，无需替换。
        """
        covering = f"H{cur_rank}"
        covering_cnt = v8_cards.count(covering)
        natural = [c for c in v8_cards if c != covering]
        if not natural or len(natural) + covering_cnt != len(v8_cards):
            return None
        suit = natural[0][0]
        if any(c[0] != suit for c in natural):
            return None
        nranks = {_card_rank(c) for c in natural}
        windows = ActionListGenerator._all_straight_windows()
        if low_rank:
            windows = [w for w in windows if w[0] == low_rank]
        for window in windows:
            missing = [r for r in window if r not in nranks]
            if len(missing) != covering_cnt:
                continue
            if cur_rank in missing:
                return None  # 配子作自然级牌，claim==action 即合法
            by_rank: Dict[str, str] = {}
            for c in natural:
                by_rank.setdefault(_card_rank(c), c)
            result = []
            for r in window:
                if r in by_rank:
                    result.append(by_rank[r])
                else:
                    result.append(f"{suit}{r}")
            return result
        return None

    def _replace_twt_covering(
        self, v8_cards: List[str], cur_rank: str, trip_rank: str = "",
    ) -> Optional[List[str]]:
        """H+cur_rank 逢人配补 ThreeWithTwo：把配子替换为所代表 rank。

        GUA-280：自然 KK+QQ+H2 作 TWT 时，claim 若仍含 H2，裁判 checkPokerType
        看到 K/K/2/Q/Q → INVALID_TYPE。两种配子用法：
        - 自然 2+2：配子补 trip（chosen rank）
        - 自然 3+1：配子补 pair（那张单的点数，GUA-273）
        配子作自然级牌（目标点数==cur_rank）→ 返回 None，claim==action。
        替换花色按目标点数未占用花色选取（TWT 四张自然牌可能占满四花，
        不能像炸弹那样按「全部自然牌花色」排除）。
        """
        covering = f"H{cur_rank}"
        covering_cnt = v8_cards.count(covering)
        natural = [c for c in v8_cards if c != covering]
        if covering_cnt != 1 or len(natural) != 4:
            return None
        counts = Counter(_card_rank(c) for c in natural)
        ranks_2 = [r for r, n in counts.items() if n == 2]
        ranks_3 = [r for r, n in counts.items() if n == 3]
        ranks_1 = [r for r, n in counts.items() if n == 1]
        target = ""
        if len(ranks_2) == 2 and not ranks_3:
            target = trip_rank if trip_rank in ranks_2 else ranks_2[0]
        elif len(ranks_3) == 1 and len(ranks_1) == 1:
            target = ranks_1[0]
        else:
            return None
        if not target or target == cur_rank:
            return None
        existing = set(natural)
        for suit in ("H", "D", "S", "C"):
            cand = f"{suit}{target}"
            if cand not in existing:
                return natural + [cand]
        return None

    def _replace_bomb_covering(self, v8_cards: List[str],
                               cur_rank: str) -> Optional[List[str]]:
        """H+cur_rank 逢人配补炸：把配子替换为所代表 rank 的牌。

        配子补炸形如 [H4,H4,D4,H2]（自然 3 张同 rank + H2），配子代表自然
        rank。替换花色取一未在自然牌中出现的花色（同花顺替换沿用自然花色，
        炸弹无窗口约束，任取一个不在场花色即可保证 claim 判型唯一）。
        返回 None 表示无需替换（配子作自然级牌，如 Bomb/2 含 H2 本身），
        claim==action 即可。
        """
        covering = f"H{cur_rank}"
        covering_cnt = v8_cards.count(covering)
        natural = [c for c in v8_cards if c != covering]
        if not natural or len(natural) + covering_cnt != len(v8_cards):
            return None
        ranks = {_card_rank(c) for c in natural}
        if len(ranks) != 1:
            return None
        rank = next(iter(ranks))
        if rank == cur_rank:
            return None  # 配子作自然级牌（Bomb/2 含 H2），claim==action 即合法
        used_suits = {c[0] for c in natural}
        for suit in ("H", "D", "S", "C"):
            if suit not in used_suits:
                return natural + [f"{suit}{rank}"] * covering_cnt
        return None

    def _replace_straight_covering(self, v8_cards: List[str], cur_rank: str,
                                   low_rank: str = "") -> Optional[List[str]]:
        """H+cur_rank 逢人配普通顺子：把配子替换为窗口缺位 rank 的牌。

        与 _replace_sf_covering 相同逻辑但用于普通顺子（非同花）：普通顺子
        无花色约束，配子补位任意 rank，替换花色取一未在自然牌中出现的花色
        即可保证 claim 判型唯一。返回 None 表示无需替换（配子作自然级牌，
        如 A2345 窗口的 H2），claim==action 即可。
        """
        covering = f"H{cur_rank}"
        covering_cnt = v8_cards.count(covering)
        natural = [c for c in v8_cards if c != covering]
        if not natural or len(natural) + covering_cnt != len(v8_cards):
            return None
        nranks = {_card_rank(c) for c in natural}
        windows = ActionListGenerator._all_straight_windows()
        if low_rank:
            windows = [w for w in windows if w[0] == low_rank]
        for window in windows:
            missing = [r for r in window if r not in nranks]
            if len(missing) != covering_cnt:
                continue
            if cur_rank in missing:
                return None  # 配子作自然级牌，claim==action 即合法
            by_rank: Dict[str, str] = {}
            for c in natural:
                by_rank.setdefault(_card_rank(c), c)
            used_suits = {c[0] for c in natural}
            result = []
            for r in window:
                if r in by_rank:
                    result.append(by_rank[r])
                else:
                    for suit in ("H", "D", "S", "C"):
                        if suit not in used_suits:
                            result.append(f"{suit}{r}")
                            break
            return result
        return None


    @staticmethod
    def _parse_bz_play_history(history) -> list:
        """解析 Botzone play request 的 history，兼容两种下发格式。

        Botzone 掼蛋 history 存在两种格式：
          A. 数组格式（官方 wiki 交互样例）：按玩家位置索引，元素为该玩家的
             response（[action, claim]，PASS 为空数组 []）。
             {"stage":"play","history":[[[26],[26]],[],[],[]],...}  # 玩家0出牌
          B. 字典格式（官方 easyAI/ruleAI 源码）：元素为
             {"player": id, "response": [action, claim]}。

        统一归一化为 [(player, action_cards, claim_cards), ...]。
        """
        entries = []
        if not isinstance(history, list):
            return entries
        for i, entry in enumerate(history):
            if isinstance(entry, dict):
                player = entry.get("player", -1)
                resp = entry.get("response", [])
            elif isinstance(entry, list):
                player = i
                resp = entry
            else:
                continue
            action_cards = []
            claim_cards = []
            if isinstance(resp, list) and len(resp) > 0 and isinstance(resp[0], list):
                action_cards = resp[0]
                if len(resp) > 1 and isinstance(resp[1], list):
                    claim_cards = resp[1]
            entries.append((player, action_cards, claim_cards))
        return entries

    def _handle_play_decision_sync(self, match_id: str, game: BotzoneGameState,
                                   req: dict) -> Optional[str]:
        """同步版 _handle_play_decision（在线模式，py3.6 兼容）。

        复用 async 版本的完整逻辑，仅把决策调用改为同步直调
        （use_thread=False）。实现为对 async 版本的事件循环驱动封装：
        Botzone 在线场景单进程单回合，直接 run_until_complete 即可；
        但 py3.6 无 asyncio.run，用 get_event_loop + run_until_complete。
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(
            self._handle_play_decision(match_id, game, req, use_thread=False))

    async def _handle_play_decision(self, match_id: str, game: BotzoneGameState,
                                     req: dict,
                                     use_thread: bool = True) -> Optional[str]:
        """Convert Botzone play request -> V8 decide -> Botzone response.

        use_thread=True：Local AI 轮询模式（async 事件循环内跑，用线程池隔离
        长决策，asyncio.wait_for 超时保护）。
        use_thread=False：Botzone 在线模式（同步直调，py3.6 沙箱无
        asyncio.to_thread/run；规则栈同步执行，超时靠平台 6s 限时兜底）。
        """
        if self.decision_engine is None:
            logger.error("decision_engine 未设置")
            return None

        # 1. Build V8-compatible game_state
        hand_cards = game.hand_cards[:]
        cur_rank = game.cur_rank

        # Get greaterAction from the request history
        history = req.get("history", [])
        parsed_history = self._parse_bz_play_history(history)
        greater_action_str = None
        greater_pos = -1
        # curPos = 当前行动席 = V8 自己（本 adapter 只在轮到自己出牌时决策）；
        # 不能取 history 最后一项（领出轮最后一项常为跟牌 PASS 的他人）。
        cur_pos = game.player_id
        for player, action_cards, claim_cards in parsed_history:
            if action_cards:
                v8_action = self._bz_response_to_v8_action(
                    action_cards, bz_claim_cards=claim_cards, cur_rank=cur_rank)
                if v8_action and v8_action[0] != "PASS":
                    greater_action_str = v8_action
                    greater_pos = player

        # 判断本轮 V8 是否必须出牌（领出 / 接风轮，掼蛋不允许 PASS）：
        #  - 上一圈最后出牌者是 V8 自己（赢圈），本圈由 V8 领出；
        #  - pass_on 标记接风轮（接风者必须出牌）；
        #  - 当前没有待压的 greater（history 全空 = 首手领出）；
        #  - 接风领出：最后出牌者已出完（done），其最后一手之后其他玩家均已 PASS，
        #    则 V8 为下一个未出完玩家，必须领出（否则会被平台判「决策错误」中止）。
        # 此时 history 中最后一个非 PASS 是 V8 自己的牌，不能当作待压的 greater。
        self_lead = (greater_pos == game.player_id)
        pass_on = req.get("pass_on", -1)
        no_greater = not (greater_action_str and greater_action_str[0] != "PASS")
        # 接风领出判定：greater 出牌者已 done，且其最后一手之后 V8 自己与其他
        # 未 done 玩家均已 PASS，则 V8 是接风者必须领出。区分场景：
        #   request A：history=[..., P2:QQQ44]（QQQ44 是末条）→ V8 首个响应，跟牌轮可 PASS；
        #   request B：history=[P1:[], P2:QQQ44, P0:[], P1:[]]（末条之后有 PASS 且
        #              含 V8 自己）→ 该手已响应完，V8 接风领出，禁止 PASS；
        #   request C：history=[P0:[], P1:[59,6], P2:[], P3:[]]（P0 在 greater 之前，
        #              P1 已 done，P2/P3 PASS）→ V8 是最后一个未表态者，仍须跟牌轮
        #              （可跟同型 / 炸 / PASS），不能自由领出——否则平台判
        #              「牌型与上家不一致」中止（实测 21:33:03 对局 6a709869）。
        # 判定关键：trailing 必须包含 V8 自己对该 greater 的 PASS 表态，才说明
        # 这手已响应完轮到 V8 领出；V8 未表态（trailing 无自己条目）是跟牌轮。
        done_set = set(req.get("done", []) or [])
        done_greater_lead = False
        if (greater_pos >= 0 and greater_pos in done_set
                and greater_pos != game.player_id):
            last_non_pass_idx = max(
                (i for i, (_p, ac, _cc) in enumerate(parsed_history) if ac),
                default=-1,
            )
            trailing = parsed_history[last_non_pass_idx + 1:]
            v8_responded = any(
                p == game.player_id for (p, _ac, _cc) in trailing)
            done_greater_lead = bool(trailing) and v8_responded and all(
                not ac for (_p, ac, _cc) in trailing
            )
        must_play = (self_lead or (pass_on == game.player_id)
                     or no_greater or done_greater_lead)
        if no_greater:
            logger.info(
                "首手领出轮: match=%s history 无待压 greater，必须出牌",
                match_id,
            )
        elif self_lead:
            logger.info(
                "领出轮: match=%s 上一手为 V8 自己(player=%s)，本圈领出，禁止 PASS",
                match_id, game.player_id,
            )
        elif pass_on == game.player_id:
            logger.info(
                "接风轮: match=%s pass_on=%s == V8，必须出牌",
                match_id, pass_on,
            )
        elif done_greater_lead:
            logger.info(
                "接风领出轮: match=%s 最后出牌者 player=%s 已 done 且该手已 PASS 完，V8 领出，禁止 PASS",
                match_id, greater_pos,
            )

        # 2. Generate actionList
        if must_play or not (greater_action_str and greater_action_str[0] != "PASS"):
            self.action_generator.cur_rank = cur_rank
            action_list = self.action_generator.generate_lead_actions(hand_cards)
        else:
            self.action_generator.cur_rank = cur_rank
            action_list = self.action_generator.generate_follow_actions(
                hand_cards, greater_action_str)

        if not action_list or len(action_list) <= 1:
            # Only PASS available
            if must_play:
                # 领出/接风轮不允许 PASS：手牌必有可出的单张，用生成器补一个单张。
                logger.warning(
                    "领出/接风轮 actionList 无候选 match=%s，兜底出最小单张",
                    match_id,
                )
                fallback = self.action_generator.generate_lead_actions(hand_cards)
                non_pass = [a for a in fallback if a[0] != "PASS"]
                if non_pass:
                    action_list = non_pass
                else:
                    return json.dumps([[], []], separators=(",", ":"))
            else:
                logger.info(
                    "跟牌轮无可压动作（仅 PASS）: match=%s greater=%s/%s hand=%d，直接 PASS",
                    match_id, greater_action_str[0] if greater_action_str else "?",
                    greater_action_str[1] if greater_action_str and len(greater_action_str) >= 2 else "",
                    len(hand_cards),
                )
                return json.dumps([[], []], separators=(",", ":"))

        # 3. Build game_state for V8's decide()
        # history 用完整 parsed_history（不能截断，引擎 _replay_history_to_tracker
        # 按 _tracker_history_replayed 增量回放，截断会漏回放/错位）。
        # 条目键对齐引擎期望：pos/seat + action/curAction + context.greaterAction。
        # PASS 条目的 context.greaterAction 用该 PASS 发生时面对的当前最大动作
        # （引擎据此 record_pass 记牌），而非本条 request 的最终 greater。
        history_actions = []
        running_greater = None
        running_greater_pos = -1
        for player, action_cards, claim_cards in parsed_history:
            v8_action = self._bz_response_to_v8_action(
                action_cards, bz_claim_cards=claim_cards, cur_rank=cur_rank)
            entry: Dict[str, Any] = {"pos": player, "action": v8_action}
            if v8_action and v8_action[0] == "PASS":
                # GUA-262：PASS context 须带 greaterPos，队友该压不压才能归王到敌侧
                entry["context"] = {
                    "greaterAction": running_greater or ["PASS", "PASS", "PASS"],
                    "greaterPos": running_greater_pos,
                }
            else:
                running_greater = v8_action or running_greater
                if v8_action and v8_action[0] != "PASS":
                    running_greater_pos = player
            history_actions.append(entry)

        # numofplayers: 各席剩余张数 = 27 - 已出张数；done 玩家为 0；
        # 自己以实牌数为准。补传 publicInfo[].rest（GUA-170 最高优先级），
        # 否则 engine 残局管线因对手恒 27 永远不激活（Botzone 实测全程 GUA-091）。
        known_done = req.get("done", [])
        numofplayers = self._compute_numofplayers(game, hand_cards, known_done)
        public_info = [{"rest": n} for n in numofplayers]

        # GUA-259：领出/接风领出（must_play）时 greaterPos 置 -1。
        # history 里最后非 PASS 常为已 done 的队友（接风），若原样传入
        # greaterPos=队友 → R10 不判 is_lead → 领出开炸（match 6a87ca4d
        # 队友 Pair/2 头游后接风打 Bomb/8）。greaterAction/curAction 本就在
        # must_play 时置 PASS 占位；greaterPos 必须同步成自由领出语义。
        engine_greater_pos = -1 if must_play else greater_pos

        tribute_phase = game.tribute_info or {}
        game_state = {
            "actionList": action_list,
            "handCards": hand_cards,
            "myPos": game.player_id,
            "curRank": cur_rank,
            "selfRank": game.self_rank,
            "oppoRank": game.oppo_rank,
            "stage": "play",
            "numofplayers": numofplayers,
            "remainingPool": self._compute_remaining_pool(game, hand_cards),
            "curPos": cur_pos,
            "greaterPos": engine_greater_pos,
            "greaterAction": (["PASS", "PASS", "PASS"]
                              if must_play else (greater_action_str or ["PASS", "PASS", "PASS"])),
            "curAction": (["PASS", "PASS", "PASS"]
                          if must_play else (greater_action_str or ["PASS", "PASS", "PASS"])),
            "done": known_done,
            "publicInfo": public_info,
            "_botzone_mode": True,
            "history": history_actions,
            "tributeResult": tribute_phase.get("tributeResult"),
            "backResult": tribute_phase.get("backResult"),
            "antiPos": tribute_phase.get("antiPos"),
        }
        # GUA-293：注入跨对局累计的「各席已出炸弹数」（在线 MemoryTracker 拿不到），
        # GUA-289 据此判「上家敌 historical 已用炸」→ GUA-270 让道失效。
        game_state["_bombs_played_by_seat"] = self._count_bombs_played(game)
        # GUA-294：注入「队友本圈是否已 PASS」，供候选竞争在对手控牌时判
        # 「若我方也 PASS 则对手白跑」→ 弱牌也须压制。
        mate_pos = (game.player_id + 2) % 4
        game_state["_teammate_passed_current_trick"] = any(
            p == mate_pos and not ac for (p, ac, _cc) in parsed_history
        )

        # 4. Call V8's decision engine
        from collections import Counter as _C
        try:
            _type_counts = _C(a[0] for a in action_list)
            logger.info(
                "actionList 摘要: match=%s len=%d types=%s greater=%s must_play=%s",
                match_id, len(action_list), dict(_type_counts),
                greater_action_str, must_play,
            )
        except Exception as _e:
            logger.warning("actionList 摘要失败: %s", _e)
        try:
            t0 = time.perf_counter()
            if use_thread:
                act_index = await asyncio.wait_for(
                    asyncio.to_thread(self.decision_engine.decide, game_state),
                    timeout=self._max_decision_time,
                )
            else:
                # 在线模式：同步直调（避免 py3.6 无 asyncio.to_thread/run）。
                act_index = self.decision_engine.decide(game_state)
            elapsed = time.perf_counter() - t0
            if elapsed > 0.5:
                logger.warning("决策偏慢: match=%s elapsed=%.3fs", match_id, elapsed)
        except asyncio.TimeoutError:
            logger.warning("决策超时 match=%s, 回退 actIndex=0", match_id)
            act_index = 0
        except Exception as e:
            logger.error("决策异常 match=%s: %s", match_id, e)
            act_index = 0

        if act_index is None or act_index >= len(action_list):
            act_index = 0

        # 领出/接风轮兜底：即使引擎选了 PASS，也强制替换为最小可出动作
        chosen = action_list[act_index]
        if must_play and chosen[0] == "PASS":
            non_pass = [a for a in action_list if a[0] != "PASS"]
            if non_pass:
                chosen = non_pass[0]
                act_index = action_list.index(chosen)
                logger.warning(
                    "领出/接风轮引擎选 PASS，兜底改出 %s/%s/%s match=%s",
                    chosen[0], chosen[1] if len(chosen) >= 2 else "",
                    chosen[2] if len(chosen) >= 3 else [], match_id,
                )

        # 跟牌轮合法性防线：chosen 必须能压 greater，否则换为 actionList 中
        # 第一个能压 greater 的动作（follow 列表只含可压 + 炸弹，理论必有）。
        # 若 actionList 误为 lead 列表（引擎路径异常），此校验可拦截跨牌型非法响应，
        # 防止平台 -2 罚分导致对局终止。
        if not must_play and greater_action_str and chosen[0] != "PASS":
            if not self._beats(chosen, greater_action_str, cur_rank):
                replace = [a for a in action_list
                           if a[0] != "PASS" and self._beats(a, greater_action_str, cur_rank)]
                if replace:
                    chosen = replace[0]
                    act_index = action_list.index(chosen)
                    logger.warning(
                        "跟牌轮非法响应 %s/%s 不压 %s/%s，改出 %s/%s match=%s",
                        chosen[0], chosen[1] if len(chosen) >= 2 else "",
                        greater_action_str[0], greater_action_str[1] if len(greater_action_str) >= 2 else "",
                        chosen[0], chosen[1] if len(chosen) >= 2 else "", match_id,
                    )
                else:
                    chosen = ["PASS", "PASS", "PASS"]
                    act_index = 0
                    logger.warning(
                        "跟牌轮无法压 %s/%s，改 PASS match=%s",
                        greater_action_str[0], greater_action_str[1] if len(greater_action_str) >= 2 else "",
                        match_id,
                    )

        # 5. Convert chosen action to Botzone response
        chosen = action_list[act_index]
        if chosen[0] == "PASS":
            bz_response = [[], []]
        else:
            v8_cards = chosen[2] if len(chosen) >= 3 else []
            bz_ints = game.card_tracker.remove_multi(v8_cards) if game.card_tracker else []
            if not bz_ints:
                bz_ints = v8_to_bz_cards(v8_cards)
            # Botzone 掼蛋协议：出牌 response = [action, claim]。
            # 官方文档规定「如出牌中不包含配子，两个数组应当相同」；
            # 官方 bot（ruleAI/easyAI）无条件 claim = action.copy()。
            # 此前返回 [bz_ints, []]（claim 空）被平台判为非法响应，导致对局终止。
            # 含 H2 逢人配同花顺须替换 claim 中的配子（_build_bz_claim）。
            bz_response = [bz_ints, self._build_bz_claim(chosen, game.cur_rank, bz_ints)]

        # 6. Update hand tracking
        chosen_cards = chosen[2] if len(chosen) >= 3 and isinstance(chosen[2], list) else []
        for card in chosen_cards:
            if card in game.hand_cards:
                game.hand_cards.remove(card)

        logger.info(
            "决策: match=%s type=%s rank=%s cards=%s actIndex=%d",
            match_id, chosen[0], chosen[1] if len(chosen) >= 2 else "",
            chosen[2] if len(chosen) >= 3 else [], act_index,
        )

        return json.dumps(bz_response, separators=(",", ":"))

    def _on_result(self, match_id: str, slot: int, player_count: int,
                   scores: List[int]) -> None:
        """Handle game result."""
        logger.info(
            "对局结束: match=%s slot=%d players=%d scores=%s",
            match_id, slot, player_count, scores,
        )
        self.games.pop(match_id, None)

    async def create_match(self, game_name: str, opponent_bot_id: str,
                           init_data: Optional[str] = None,
                           teammate_bot_id: Optional[str] = None) -> Optional[str]:
        """Create a match against Botzone bots.

        Botzone runmatch API requires exactly one 'me'.
        V8 plays seat 0, teammates/opponents fill the rest.

        For 4-player GuanDan:
          seat 0: me (V8)
          seats 1,3: opponent_bot_id (DanLM)
          seat 2: teammate_bot_id or opponent_bot_id

        Returns match_id on success, None on failure.
        """
        headers = {
            "X-Game": game_name,
            "X-Player-0": "me",
            "X-Player-1": opponent_bot_id,
            "X-Player-2": teammate_bot_id or opponent_bot_id,
            "X-Player-3": opponent_bot_id,
        }
        if init_data:
            headers["X-Initdata"] = init_data

        req = urllib.request.Request(self.runmatch_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                body = res.read().decode("utf-8").strip()
            logger.info("创建对局成功: %s", body)
            return body
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace").strip() if e.fp else ""
            logger.error("创建对局失败: %s %s", e, body)
            return None
        except Exception as e:
            logger.error("创建对局异常: %s", e)
            return None
