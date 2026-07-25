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
import json
import logging
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
        """Generate all valid lead actions from hand."""
        actions = [["PASS", "PASS", "PASS"]]
        rank_groups = self._group_by_rank(hand_cards)
        suits = self._group_by_suit(hand_cards)

        # Singles
        for card in hand_cards:
            actions.append(self._single_action(card))

        # Pairs
        for rank, cards in rank_groups.items():
            if len(cards) >= 2:
                actions.append(self._pair_action(cards[:2]))

        # Trips
        for rank, cards in rank_groups.items():
            if len(cards) >= 3:
                actions.append(self._trips_action(cards[:3]))

        # Bombs (4+ same rank)
        for rank, cards in rank_groups.items():
            if len(cards) >= 4:
                actions.append(self._bomb_action(cards))
            if len(cards) >= 5:
                actions.append(self._bomb_action(cards[:5]))
            if len(cards) >= 6:
                actions.append(self._bomb_action(cards[:6]))

        # ThreeWithTwo (trips + pair)
        for t_rank, t_cards in rank_groups.items():
            if len(t_cards) >= 3:
                trips = t_cards[:3]
                for p_rank, p_cards in rank_groups.items():
                    if p_rank != t_rank and len(p_cards) >= 2:
                        actions.append(self._three_with_two_action(trips, p_cards[:2]))

        # Straights
        actions.extend(self._generate_straights(rank_groups, suits))

        # StraightFlushes
        for suit, s_cards in suits.items():
            if len(s_cards) >= 5:
                s_ranks = sorted(set(_card_rank(c) for c in s_cards),
                                key=lambda r: RANK_ORDER.get(r, 99))
                actions.extend(self._generate_straight_flushes(s_cards, s_ranks))

        # ThreePairs
        consecutive_pairs = self._find_consecutive_pairs(rank_groups, 3)
        for ranks, pairs in consecutive_pairs:
            cards = []
            for r in ranks:
                cards.extend(rank_groups[r][:2])
            actions.append(self._three_pair_action(cards, ranks[-1]))

        # TwoTrips
        consecutive_trips = self._find_consecutive_trips(rank_groups, 2)
        for ranks, trips_list in consecutive_trips:
            cards = []
            for r in ranks:
                cards.extend(rank_groups[r][:3])
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

        rank_groups = self._group_by_rank(hand_cards)
        suits = self._group_by_suit(hand_cards)

        if greater_type in ("Single", "Pair", "Trips"):
            n = {"Single": 1, "Pair": 2, "Trips": 3}[greater_type]
            for rank, cards in rank_groups.items():
                if len(cards) >= n and _rank_to_order(rank, self.cur_rank) > greater_order:
                    actions.append(_make_action(greater_type, rank, cards[:n]))

        elif greater_type == "Bomb":
            for rank, cards in rank_groups.items():
                if len(cards) >= 4 and _rank_to_order(rank, self.cur_rank) > greater_order:
                    actions.append(self._bomb_action(cards))

        elif greater_type == "StraightFlush":
            sfs = self._generate_straight_flushes_by_suit(suits, greater_order)
            actions.extend(sfs)

        elif greater_type == "ThreeWithTwo":
            for t_rank, t_cards in rank_groups.items():
                if len(t_cards) >= 3 and _rank_to_order(t_rank, self.cur_rank) > greater_order:
                    trips = t_cards[:3]
                    for p_rank, p_cards in rank_groups.items():
                        if p_rank != t_rank and len(p_cards) >= 2:
                            actions.append(self._three_with_two_action(trips, p_cards[:2]))

        elif greater_type == "ThreePair":
            consecutive_pairs = self._find_consecutive_pairs(rank_groups, 3)
            for ranks, pairs in consecutive_pairs:
                last_rank = ranks[-1]
                if _rank_to_order(last_rank, self.cur_rank) > greater_order:
                    cards = []
                    for r in ranks:
                        cards.extend(rank_groups[r][:2])
                    actions.append(self._three_pair_action(cards, last_rank))

        elif greater_type == "TwoTrips":
            consecutive_trips = self._find_consecutive_trips(rank_groups, 2)
            for ranks, trips_list in consecutive_trips:
                last_rank = ranks[-1]
                if _rank_to_order(last_rank, self.cur_rank) > greater_order:
                    cards = []
                    for r in ranks:
                        cards.extend(rank_groups[r][:3])
                    actions.append(self._two_trips_action(cards, last_rank))

        elif greater_type == "Straight":
            rank_set = set(rank_groups.keys())
            straights = self._find_straights_from_ranks(rank_set, greater_order)
            for ranks in straights:
                cards = [rank_groups[r][0] for r in ranks]
                actions.append(self._straight_action(cards, ranks[-1]))

        # Also add all bombs as valid follow plays
        for rank, cards in rank_groups.items():
            if len(cards) >= 4:
                actions.append(self._bomb_action(cards))

        seen: Set[str] = set()
        deduped = []
        for act in actions:
            key = self._action_key(act)
            if key not in seen:
                seen.add(key)
                deduped.append(act)
        return deduped

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

    def _straight_action(self, cards: List[str], high_rank: str) -> list:
        return _make_action("Straight", high_rank, cards)

    def _three_pair_action(self, cards: List[str], high_rank: str) -> list:
        return _make_action("ThreePair", high_rank, cards)

    def _two_trips_action(self, cards: List[str], high_rank: str) -> list:
        return _make_action("TwoTrips", high_rank, cards)

    def _straight_flush_action(self, cards: List[str], high_rank: str) -> list:
        return _make_action("StraightFlush", high_rank, cards)

    def _action_key(self, action: list) -> str:
        cards = action[2] if len(action) >= 3 and isinstance(action[2], list) else []
        return "|".join(sorted(cards))

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
        """Find consecutive ranks that each have >= 3 cards."""
        sorted_ranks = sorted(rank_groups.keys(), key=lambda r: RANK_ORDER.get(r, 99))
        result = []
        for i in range(len(sorted_ranks) - length + 1):
            chunk = sorted_ranks[i:i + length]
            if all(len(rank_groups[r]) >= 3 for r in chunk):
                trips = [rank_groups[r][:3] for r in chunk]
                result.append((list(chunk), trips))
        return result

    def _generate_straights(self, rank_groups: Dict[str, List[str]],
                            suits: Dict[str, List[str]]) -> List[list]:
        """Generate straight actions (5+ consecutive, any suit)."""
        rank_set = set(rank_groups.keys())
        actions = []
        all_ranks = sorted(rank_set, key=lambda r: RANK_ORDER.get(r, 99))
        rank_order_map = {r: RANK_ORDER.get(r, 99) for r in all_ranks}

        for length in range(5, 13):
            for i in range(len(all_ranks) - length + 1):
                chunk = all_ranks[i:i + length]
                expected = list(range(rank_order_map[chunk[0]],
                                      rank_order_map[chunk[0]] + length))
                actual = [rank_order_map[r] for r in chunk]
                if actual == expected:
                    cards = [rank_groups[r][0] for r in chunk]
                    actions.append(self._straight_action(cards, chunk[-1]))
        return actions

    def _find_straights_from_ranks(self, rank_set: Set[str],
                                   greater_order: int) -> List[List[str]]:
        """Find straights with high rank > greater_order."""
        all_ranks = sorted(rank_set, key=lambda r: RANK_ORDER.get(r, 99))
        results = []
        for length in range(5, 13):
            for i in range(len(all_ranks) - length + 1):
                chunk = all_ranks[i:i + length]
                high = chunk[-1]
                if _rank_to_order(high, self.cur_rank) > greater_order:
                    results.append(list(chunk))
        return results

    def _generate_straight_flushes(self, suit_cards: List[str],
                                    suit_ranks: List[str]) -> List[list]:
        """Generate straight flush from a suit's cards."""
        actions = []
        rank_order_map = {r: RANK_ORDER.get(r, 99) for r in suit_ranks}
        for length in range(5, min(len(suit_cards) + 1, 13)):
            for i in range(len(suit_ranks) - length + 1):
                chunk = suit_ranks[i:i + length]
                expected = list(range(rank_order_map[chunk[0]],
                                      rank_order_map[chunk[0]] + length))
                actual = [rank_order_map[r] for r in chunk]
                if actual == expected:
                    cards = [c for c in suit_cards if _card_rank(c) in chunk]
                    if len(cards) >= length:
                        cards = sorted(cards, key=lambda c: RANK_ORDER.get(_card_rank(c), 99))[:length]
                        actions.append(self._straight_flush_action(cards, chunk[-1]))
        return actions

    def _generate_straight_flushes_by_suit(self, suits: Dict[str, List[str]],
                                            greater_order: int) -> List[list]:
        actions = []
        for suit, cards in suits.items():
            if len(cards) < 5:
                continue
            suit_ranks = sorted(set(_card_rank(c) for c in cards),
                               key=lambda r: RANK_ORDER.get(r, 99))
            for sf in self._generate_straight_flushes(cards, suit_ranks):
                sf_high = sf[1] if len(sf) >= 2 else ""
                if _rank_to_order(sf_high, self.cur_rank) > greater_order:
                    actions.append(sf)
        return actions


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
                                 base_url="https://www.botzone.org/api",
                                 decision_engine=engine)
        asyncio.run(adapter.run())
    """

    def __init__(
        self,
        user_id: str,
        api_key: str,
        base_url: str = "https://www.botzone.org/api",
        decision_engine=None,
        player_id: int = 0,
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
        self._max_decision_time = 0.4
        self._default_cur_rank = "2"

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
            with urllib.request.urlopen(req, timeout=None) as res:
                body = res.read().decode("utf-8")
            self._pending_responses.clear()
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

    def _on_request(self, match_id: str, request_json: str) -> None:
        """Handle a new request from Botzone."""
        try:
            req = json.loads(request_json)
        except json.JSONDecodeError:
            logger.warning("无法解析 request JSON: match=%s", match_id)
            return

        stage = req.get("stage", "")
        logger.info("收到 request: match=%s stage=%s", match_id, stage)

        if match_id not in self.games:
            self.games[match_id] = BotzoneGameState(match_id=match_id, player_id=self.player_id)

        game = self.games[match_id]

        if stage == "deal":
            self._handle_deal(game, req)
            self._pending_responses[match_id] = "[]"
        elif stage == "tribute":
            game.current_request = req
        elif stage == "return":
            game.current_request = req
        elif stage == "play":
            self._handle_play_request(game, req)
            game.current_request = req
        elif stage in ("episodeOver", "gameOver"):
            logger.info("对局阶段结束: match=%s stage=%s", match_id, stage)
            if stage == "gameOver":
                game.active = False

    def _handle_deal(self, game: BotzoneGameState, req: dict) -> None:
        """Handle deal stage: set up hand cards."""
        bz_hand = req.get("deliver", [])
        game.hand_cards = bz_to_v8_cards(bz_hand)
        game.card_tracker = CardTracker.from_bz_hand(bz_hand)
        game.player_id = req.get("your_id", game.player_id)
        global_info = req.get("global", {})
        level = global_info.get("level", "2")
        game.cur_rank = level
        game.self_rank = level
        game.oppo_rank = level
        game.play_history = []
        game.pass_on = -1
        game.done = []
        game.episode_count += 1
        game.current_request = None  # deal needs no response
        logger.info(
            "发牌: match=%s player=%d hand=%d curRank=%s",
            game.match_id, game.player_id, len(game.hand_cards), level,
        )

    def _handle_play_request(self, game: BotzoneGameState, req: dict) -> None:
        """Update game state from a play request."""
        history = req.get("history", [])
        if history:
            game.play_history.extend(history)
            self._update_from_history(game, history)

        game.done = req.get("done", [])
        game.pass_on = req.get("pass_on", -1)

        global_info = req.get("global", {})
        if "level" in global_info:
            game.cur_rank = global_info["level"]

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
                v8_action = self._bz_response_to_v8_action(action_list)
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

    def _bz_response_to_v8_action(self, bz_action_cards: List[int]) -> Optional[list]:
        """Convert Botzone play action (list of card ints) to OpenGuanDan format."""
        if not bz_action_cards:
            return ["PASS", "PASS", "PASS"]
        v8_cards = bz_to_v8_cards(bz_action_cards)
        return self._classify_action(v8_cards)

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
        if n >= 5:
            if self._is_consecutive(ranks, cr) and len(set(suits)) == 1:
                high = max(ranks, key=lambda r: _rank_to_order(r, cr))
                return _make_action("StraightFlush", high, cards)
            if self._is_consecutive(ranks, cr):
                high = max(ranks, key=lambda r: _rank_to_order(r, cr))
                return _make_action("Straight", high, cards)
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
        """Check if action beats greater (for tracking)."""
        t1, r1 = action[0], action[1] if len(action) >= 2 else ""
        t2, r2 = greater[0], greater[1] if len(greater) >= 2 else ""
        if t1 in ("Bomb", "StraightFlush") and t2 not in ("Bomb", "StraightFlush"):
            return True
        if t1 == "StraightFlush" and t2 == "Bomb":
            return True
        if t1 == t2:
            return _rank_to_order(r1, cur_rank) > _rank_to_order(r2, cur_rank)
        return False

    async def _handle_request(self, match_id: str, game: BotzoneGameState) -> Optional[str]:
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
            return await self._handle_play_decision(match_id, game, req)
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
        """Handle return tribute: give back a card <= 10."""
        # First, add any tribute card received into hand
        tribute_cards: dict = req.get("global", {}).get("tribute_cards", {})
        for payer_id, bz_card in tribute_cards.items():
            if isinstance(bz_card, int) and bz_card >= 0:
                v8_card = bz_to_v8_card(bz_card)
                if v8_card not in game.hand_cards:
                    game.hand_cards.append(v8_card)
                    if game.card_tracker:
                        game.card_tracker.add(v8_card, bz_card)

        rank_order_10 = 8  # T = rank index 8 (fixed, regardless of cur_rank)
        candidates = [c for c in game.hand_cards
                      if _card_rank_order(c, game.cur_rank) <= rank_order_10]
        if not candidates:
            candidates = game.hand_cards[:]
        return_card = min(candidates, key=lambda c: _card_rank_order(c, game.cur_rank))
        bz_cards = game.card_tracker.remove_multi([return_card]) if game.card_tracker else []
        game.hand_cards.remove(return_card)
        if bz_cards:
            return json.dumps([bz_cards[0]], separators=(",", ":"))
        return json.dumps([v8_to_bz_int(return_card)], separators=(",", ":"))

    async def _handle_play_decision(self, match_id: str, game: BotzoneGameState,
                                     req: dict) -> Optional[str]:
        """Convert Botzone play request -> V8 decide -> Botzone response."""
        if self.decision_engine is None:
            logger.error("decision_engine 未设置")
            return None

        # 1. Build V8-compatible game_state
        hand_cards = game.hand_cards[:]
        cur_rank = game.cur_rank

        # Get greaterAction from the request history
        history = req.get("history", [])
        greater_action_str = None
        greater_pos = -1
        cur_pos = -1
        for entry in history:
            player = entry.get("player", -1)
            resp = entry.get("response", [[], []])
            action_cards = resp[0] if isinstance(resp, list) and len(resp) > 0 else []
            cur_pos = player
            if action_cards:
                v8_action = self._bz_response_to_v8_action(action_cards)
                if v8_action and v8_action[0] != "PASS":
                    greater_action_str = v8_action
                    greater_pos = player

        # 2. Generate actionList
        if greater_action_str and greater_action_str[0] != "PASS":
            self.action_generator.cur_rank = cur_rank
            action_list = self.action_generator.generate_follow_actions(
                hand_cards, greater_action_str)
        else:
            self.action_generator.cur_rank = cur_rank
            action_list = self.action_generator.generate_lead_actions(hand_cards)

        if not action_list or len(action_list) <= 1:
            # Only PASS available
            return json.dumps([[], []], separators=(",", ":"))

        # 3. Build game_state for V8's decide()
        history_actions = []
        for entry in history[-8:]:  # last 8 entries for context
            player = entry.get("player", -1)
            resp = entry.get("response", [[], []])
            v8_action = self._bz_response_to_v8_action(
                resp[0] if isinstance(resp, list) and len(resp) > 0 else [])
            history_actions.append({
                "player": player,
                "action": v8_action,
            })

        # numofplayers: estimate from known cards
        known_done = req.get("done", [])
        numofplayers = [27] * 4
        numofplayers[game.player_id] = len(hand_cards)

        game_state = {
            "actionList": action_list,
            "handCards": hand_cards,
            "myPos": game.player_id,
            "curRank": cur_rank,
            "selfRank": game.self_rank,
            "oppoRank": game.oppo_rank,
            "stage": "play",
            "numofplayers": numofplayers,
            "curPos": cur_pos,
            "greaterPos": greater_pos,
            "greaterAction": greater_action_str or ["PASS", "PASS", "PASS"],
            "curAction": greater_action_str or ["PASS", "PASS", "PASS"],
            "done": known_done,
            "_botzone_mode": True,
            "_history": history_actions,
        }

        # 4. Call V8's decision engine
        try:
            t0 = time.perf_counter()
            act_index = await asyncio.wait_for(
                asyncio.to_thread(self.decision_engine.decide, game_state),
                timeout=self._max_decision_time,
            )
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

        # 5. Convert chosen action to Botzone response
        chosen = action_list[act_index]
        if chosen[0] == "PASS":
            bz_response = [[], []]
        else:
            v8_cards = chosen[2] if len(chosen) >= 3 else []
            bz_ints = game.card_tracker.remove_multi(v8_cards) if game.card_tracker else []
            if not bz_ints:
                bz_ints = v8_to_bz_cards(v8_cards)
            wild = f"H{game.cur_rank}"
            has_wild = any(c == wild for c in v8_cards)
            bz_response = [bz_ints, bz_ints] if has_wild else [bz_ints, []]

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
            logger.error("创建对局失败: %s", e)
            return None
        except Exception as e:
            logger.error("创建对局异常: %s", e)
            return None
