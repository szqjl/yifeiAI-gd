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
from math import comb
from typing import Any, Dict, List, Set, Set

from src.v.nn.features.memory_tracker import MemoryTracker

SUITS = ["S", "H", "D", "C"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]

RANK_VALUE: Dict[str, int] = {
    "2": 0, "3": 1, "4": 2, "5": 3, "6": 4, "7": 5,
    "8": 6, "9": 7, "T": 8, "J": 9, "Q": 10, "K": 11, "A": 12,
}
RANK_VALUE_WITH_JOKERS: Dict[str, int] = {
    **RANK_VALUE,
    "SB": 13,
    "HR": 14,
}

ROUTE_ACTION_TYPES = [
    "Single",
    "Pair",
    "Trips",
    "ThreeWithTwo",
    "Straight",
    "ThreePair",
    "TwoTrips",
]

# M5：规则记牌 → 固定维向量（不改 BELIEF_DIM，供 NN 训练/日志侧车）
RULE_MEMORY_DIM = 12


def _normalize_platform_action_type(action_type: str) -> str:
    """平台 action[0] → PascalCase 牌型名。"""
    raw = str(action_type or "").strip()
    if not raw or raw.upper() == "PASS":
        return ""
    upper = raw.upper()
    aliases = {
        "SINGLE": "Single",
        "PAIR": "Pair",
        "TRIPS": "Trips",
        "THREEWITHTWO": "ThreeWithTwo",
        "STRAIGHT": "Straight",
        "THREEPAIR": "ThreePair",
        "TWOTRIPS": "TwoTrips",
        "BOMB": "Bomb",
        "STRAIGHTFLUSH": "StraightFlush",
    }
    if upper in aliases:
        return aliases[upper]
    if raw in ROUTE_ACTION_TYPES:
        return raw
    return raw


def extract_rule_memory_features(belief: Dict[str, Any]) -> List[float]:
    """M5：从 ``get_belief()`` 产出 12 维规则记牌向量（侧车，不扩 BC BELIEF_DIM）。"""
    if not belief:
        return [0.0] * RULE_MEMORY_DIM

    def _norm01(value: float, scale: float = 1.0) -> float:
        if scale <= 0:
            return 0.0
        return max(0.0, min(float(value) / scale, 1.0))

    key = belief.get("key_card_signal") or belief.get("straight_skeleton") or {}
    route = belief.get("type_route") or {}
    head = belief.get("head_bomb_signal") or {}
    high = belief.get("high_card_signal") or {}
    line = belief.get("line_read") or {}
    gap = belief.get("gap_bomb_risk") or {}
    opp_risks = belief.get("opp_bomb_risks") or {}

    five_out = float(key.get("five_outside", key.get("five_remain", 8)) or 0)
    ten_out = float(key.get("ten_outside", key.get("ten_remain", 8)) or 0)
    safe_n = len(key.get("safe_straight_windows") or [])

    down = route.get("downseat") or {}
    tm = route.get("teammate") or {}

    return [
        _norm01(five_out, 8.0),
        _norm01(ten_out, 8.0),
        _norm01(safe_n, 10.0),
        1.0 if key.get("five_outside_depleted") else 0.0,
        1.0 if key.get("ten_outside_depleted") else 0.0,
        float(gap.get("gap_bomb_risk_max") or 0.0),
        1.0 if down.get("likely_short_pair") else 0.0,
        1.0 if tm.get("likely_wants_big_single") else 0.0,
        _norm01(len(head.get("head_bomb_ranks") or []), 4.0),
        _norm01(high.get("high_card_outside_total", 0), 24.0),
        max(float(v) for v in opp_risks.values()) if opp_risks else 0.0,
        1.0 if belief.get("can_opp_form_type_current") else 0.0,
    ]


STRUCTURED_ACTION_TYPES = {
    "ThreeWithTwo",
    "Straight",
    "ThreePair",
    "TwoTrips",
    "Bomb",
    "StraightFlush",
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

    def get_high_card_signal(self) -> Dict[str, Any]:
        """MEM-M01：王/级/A/K 外出计数（对齐 05_memory_skills §一 + PRINCIPLES §十五）。"""
        joker = self.get_joker_signal()
        level = self.get_level_signal()
        a_stats = self._rank_copy_stats("A")
        k_stats = self._rank_copy_stats("K")
        level_rank = str(level.get("level_rank") or "")
        level_point_stats = (
            self._rank_copy_stats(level_rank)
            if level_rank in RANKS
            else {"played": 0, "in_my_hand": 0, "remain": 0, "outside_my_hand": 0}
        )

        hr_outside = int(joker.get("hr_with_opponents", 0) or 0) + int(
            joker.get("hr_unknown", 0) or 0
        )
        sb_outside = int(joker.get("sb_with_opponents", 0) or 0) + int(
            joker.get("sb_unknown", 0) or 0
        )
        high_outside = (
            hr_outside
            + sb_outside
            + int(a_stats["outside_my_hand"])
            + int(k_stats["outside_my_hand"])
            + int(level_point_stats["outside_my_hand"])
        )

        return {
            "hr_played": joker["hr_played"],
            "hr_remain": joker["hr_remain"],
            "hr_outside": hr_outside,
            "sb_played": joker["sb_played"],
            "sb_remain": joker["sb_remain"],
            "sb_outside": sb_outside,
            "level_rank": level_rank,
            "level_played": max(0, 8 - int(level.get("level_remaining", 0) or 0)),
            "level_remain": int(level.get("level_remaining", 0) or 0),
            "level_outside": int(level_point_stats["outside_my_hand"]),
            "a_played": a_stats["played"],
            "a_remain": a_stats["remain"],
            "a_outside": a_stats["outside_my_hand"],
            "k_played": k_stats["played"],
            "k_remain": k_stats["remain"],
            "k_outside": k_stats["outside_my_hand"],
            "high_card_outside_total": high_outside,
            "a_depleted": a_stats["outside_my_hand"] <= 0,
            "k_depleted": k_stats["outside_my_hand"] <= 0,
        }

    @staticmethod
    def _infer_bomb_main_rank(cards: List[str]) -> str:
        """从炸弹牌张推断主 rank（众数）。"""
        if not cards:
            return ""
        counts: Counter[str] = Counter()
        for card in cards:
            rk = _parse_card_rank_fast(str(card))
            if rk in RANKS + ["SB", "HR"]:
                counts[rk] += 1
        if not counts:
            return ""
        return counts.most_common(1)[0][0]

    @staticmethod
    def _rank_beats(candidate: str, incumbent: str) -> bool:
        """candidate rank 是否高于 incumbent（空 incumbent 视为最低）。"""
        if not candidate:
            return False
        if not incumbent:
            return True
        cv = RANK_VALUE_WITH_JOKERS.get(candidate, -1)
        iv = RANK_VALUE_WITH_JOKERS.get(incumbent, -1)
        return cv > iv

    def _scan_seat_bomb_profile(self) -> Dict[str, Any]:
        """MEM-M02：逐席是否出过炸 / 最大炸弹 rank / 张数。"""
        tracker = self._t
        has_played: Dict[int, bool] = {i: False for i in range(4)}
        max_rank: Dict[int, str] = {}
        max_size: Dict[int, int] = {i: 0 for i in range(4)}

        for play in tracker.play_history:
            action_type = str(play.get("action_type") or "")
            if action_type not in ("Bomb", "StraightFlush"):
                continue
            try:
                seat = int(play.get("seat", -1))
            except (TypeError, ValueError):
                continue
            if seat < 0:
                continue
            cards = play.get("cards") or []
            has_played[seat] = True
            size = len(cards)
            if size > max_size.get(seat, 0):
                max_size[seat] = size
            bomb_rank = self._infer_bomb_main_rank(cards)
            if self._rank_beats(bomb_rank, max_rank.get(seat, "")):
                max_rank[seat] = bomb_rank

        return {
            "has_played_bomb": has_played,
            "max_bomb_rank_by_seat": max_rank,
            "max_bomb_size_by_seat": max_size,
        }

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
              - has_played_bomb: {seat: bool} MEM-M02 是否出过炸
              - max_bomb_rank_by_seat: {seat: rank} MEM-M02 最大炸弹点数
              - max_bomb_size_by_seat: {seat: int} MEM-M02 最大炸弹张数
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

        bomb_profile = self._scan_seat_bomb_profile()
        return {
            "bombs_played": bombs_played,
            "sf_bombs_played": dict(sf),
            "total_bombs_played": total,
            "bombs_remaining_self": self_bombs,
            "bombs_remaining_opp": opp_bombs,
            "has_played_bomb": bomb_profile["has_played_bomb"],
            "max_bomb_rank_by_seat": bomb_profile["max_bomb_rank_by_seat"],
            "max_bomb_size_by_seat": bomb_profile["max_bomb_size_by_seat"],
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
        if rank in ("SB", "HR"):
            copies = self._t.card_state.get(rank, [-1, -1])
            return sum(1 for c in copies if c == -1)
        count = 0
        for suit in SUITS:
            ct = f"{suit}{rank}"
            copies = self._t.card_state.get(ct, [-1, -1])
            count += sum(1 for c in copies if c == -1)
        return count

    def get_joker_signal(self) -> Dict[str, Any]:
        """大小王信念：已出/剩余/在我手/队友/对手/未知。"""
        tracking = self._t.get_joker_tracking()
        hr = tracking["HR"]
        sb = tracking["SB"]
        return {
            "HR": hr,
            "SB": sb,
            "hr_played": hr["played"],
            "hr_remain": hr["remain"],
            "hr_in_my_hand": hr["in_my_hand"],
            "hr_with_teammate": hr["with_teammate"],
            "hr_with_opponents": hr["with_opponents"],
            "hr_unknown": hr["unknown"],
            "sb_played": sb["played"],
            "sb_remain": sb["remain"],
            "sb_in_my_hand": sb["in_my_hand"],
            "sb_with_teammate": sb["with_teammate"],
            "sb_with_opponents": sb["with_opponents"],
            "sb_unknown": sb["unknown"],
        }

    def get_unknown_rank_stats(self) -> Dict[str, int]:
        """所有 rank 的 UNKNOWN 计数。"""
        return {r: self.get_rank_unknown_count(r) for r in RANKS + ["SB", "HR"]}

    def _get_recent_action_type(self, seat: int, game_state=None) -> str:
        """返回 seat 最近一次显式动作类型；优先信当前 greaterAction。"""
        if game_state:
            greater_pos = game_state.get("greaterPos", -1)
            greater_action = game_state.get("greaterAction")
            if (
                greater_pos == seat
                and isinstance(greater_action, list)
                and len(greater_action) >= 1
            ):
                return str(greater_action[0] or "")
        for play in reversed(self._t.play_history):
            if play.get("seat", -1) == seat:
                return str(play.get("action_type") or "")
        return ""

    def _iter_higher_ranks(self, target_rank: str) -> List[str]:
        target_value = RANK_VALUE_WITH_JOKERS.get(target_rank)
        if target_value is None:
            return []
        return [
            rank
            for rank, value in RANK_VALUE_WITH_JOKERS.items()
            if value > target_value
        ]

    def _count_possible_enemy_copies(self, rank: str) -> int:
        if rank in ("SB", "HR"):
            copies = self._t.card_state.get(rank, [-1, -1])
            return sum(1 for c in copies if self._may_opp_hold(c))

        total = 0
        for suit in SUITS:
            ct = f"{suit}{rank}"
            copies = self._t.card_state.get(ct, [-1, -1])
            total += sum(1 for c in copies if self._may_opp_hold(c))
        return total

    def _seat_type_weakness_count(self, seat: int, action_type: str) -> int:
        """该席对该牌型 PASS + 被迫开炸次数（牌路弱项，含 type_bombed）。"""
        return int(self._t.get_type_weakness(seat).get(action_type, 0) or 0)

    def _is_head_rank_depleted(self, rank: str) -> bool:
        """MEM-M04：同点 ≥4 已出 → 难再组该点三带二/头炸余牌。"""
        if rank in ("SB", "HR"):
            return False
        return int(self._rank_copy_stats(rank)["played"]) >= 4

    def get_key_card_signal(self) -> Dict[str, Any]:
        """MEM-M03 / §五：5 与 10 关键张外出计数 + 安全顺窗。"""
        sk = self.get_straight_skeleton_signal()
        five = self._rank_copy_stats("5")
        ten = self._rank_copy_stats("T")
        return {
            "five_played": max(0, 8 - int(five["remain"])),
            "five_remain": int(five["remain"]),
            "five_outside": int(five["outside_my_hand"]),
            "five_outside_depleted": int(five["outside_my_hand"]) <= 0,
            "ten_played": max(0, 8 - int(ten["remain"])),
            "ten_remain": int(ten["remain"]),
            "ten_outside": int(ten["outside_my_hand"]),
            "ten_outside_depleted": int(ten["outside_my_hand"]) <= 0,
            "safe_straight_windows": list(sk.get("safe_straight_windows") or []),
        }

    def get_head_bomb_signal(self) -> Dict[str, Any]:
        """MEM-M04：成头炸 rank（同点 ≥4 已出）→ 三带二主三张概率↓。"""
        head_ranks: List[str] = []
        twt_trip_depleted: List[str] = []
        for rank in RANKS:
            played = int(self._rank_copy_stats(rank)["played"])
            if played >= 4:
                head_ranks.append(rank)
            if played >= 3:
                twt_trip_depleted.append(rank)
        return {
            "head_bomb_ranks": head_ranks,
            "twt_trip_ranks_depleted": twt_trip_depleted,
        }

    def get_tribute_signal(self) -> Dict[str, Any]:
        """MEM-M05：进贡/还贡/抗贡牌记入信念。"""
        tracker = self._t
        tribute_cards: List[Dict[str, Any]] = []
        back_cards: List[Dict[str, Any]] = []
        for entry in tracker.tribute_history:
            ev = str(entry.get("event") or "")
            item = {
                "from": entry.get("from"),
                "to": entry.get("to"),
                "card": entry.get("card"),
            }
            if ev == "tribute":
                tribute_cards.append(item)
            elif ev == "back":
                back_cards.append(item)
        latest_tribute_rank = ""
        if tribute_cards:
            latest_tribute_rank = _parse_card_rank_fast(
                str(tribute_cards[-1].get("card") or "")
            )
        return {
            "anti_tribute_seats": list(getattr(tracker, "_anti_tribute_pos", []) or []),
            "tribute_cards": tribute_cards,
            "back_cards": back_cards,
            "tribute_count": len(tribute_cards),
            "back_count": len(back_cards),
            "latest_tribute_rank": latest_tribute_rank,
        }

    def get_type_route_signal(self) -> Dict[str, Any]:
        """M3 / §四：逐席牌路弱项 + 首发/未出型推断。"""
        tracker = self._t
        seats: Dict[int, Dict[str, Any]] = {}
        first_lead: Dict[int, str] = {}

        for seat in range(4):
            types_played: Set[str] = set()
            singles = pairs = small_singles = 0
            for entry in tracker.play_history:
                if int(entry.get("seat", -1)) != seat:
                    continue
                at = _normalize_platform_action_type(str(entry.get("action_type") or ""))
                if not at:
                    continue
                types_played.add(at)
                if seat not in first_lead:
                    first_lead[seat] = at
                if at == "Single":
                    singles += 1
                    cards = entry.get("cards") or []
                    if cards:
                        rk = _parse_card_rank_fast(str(cards[0]))
                        if RANK_VALUE.get(rk, 99) <= RANK_VALUE.get("9", 7):
                            small_singles += 1
                elif at == "Pair":
                    pairs += 1

            weakness = dict(tracker.get_type_weakness(seat))
            never_played = [
                t for t in ROUTE_ACTION_TYPES if t not in types_played
            ]
            unlikely_form = [
                t
                for t in ROUTE_ACTION_TYPES
                if int(weakness.get(t, 0) or 0) >= 2
            ]
            likely_has: List[str] = []
            if singles >= 3 and pairs == 0:
                unlikely_form.append("Pair")
            if "Single" in never_played and int(weakness.get("Single", 0) or 0) == 0:
                likely_has.append("Single")
            if "Pair" in never_played and int(weakness.get("Pair", 0) or 0) == 0:
                likely_has.append("Pair")

            seats[seat] = {
                "first_lead_type": first_lead.get(seat, ""),
                "types_played": sorted(types_played),
                "types_never_played": never_played,
                "type_weakness": weakness,
                "unlikely_form_types": sorted(set(unlikely_form)),
                "likely_has_types": likely_has,
                "single_plays": singles,
                "pair_plays": pairs,
                "small_single_plays": small_singles,
                "likely_short_pair": singles >= 3 and pairs == 0,
            }

        down = (tracker.my_pos + 1) % 4
        tm = tracker.partner_pos
        tm_info = seats.get(tm, {})
        return {
            "seats": seats,
            "downseat": seats.get(down, {}),
            "teammate": {
                **tm_info,
                "likely_wants_big_single": int(tm_info.get("small_single_plays", 0) or 0) >= 2,
            },
            "downseat_short_pair": bool(seats.get(down, {}).get("likely_short_pair")),
        }

    def seat_unlikely_form_type(self, seat: int, action_type: str) -> bool:
        """该席是否 unlikely 再组 action_type（牌路弱项 ≥2 或连单缺对）。"""
        route = self.get_type_route_signal()
        info = route.get("seats", {}).get(seat, {})
        at = _normalize_platform_action_type(action_type)
        return at in (info.get("unlikely_form_types") or [])


    @staticmethod
    def _min_cards_for_action_type(action_type: str) -> int:
        return {
            "Single": 1,
            "Pair": 2,
            "Trips": 3,
            "ThreeWithTwo": 5,
            "Straight": 5,
            "ThreePair": 6,
            "TwoTrips": 6,
            "Bomb": 4,
            "StraightFlush": 5,
        }.get(action_type, 1)

    def _seat_remaining(self, seat: int, game_state=None) -> int:
        """该席剩余张数：优先 numofplayers（平台实时），其次 belief，最后 tracker。"""
        if game_state is not None:
            nop = game_state.get("numofplayers") or []
            if isinstance(nop, (list, tuple)) and len(nop) > seat:
                try:
                    return int(nop[seat])
                except (TypeError, ValueError):
                    pass
            belief = game_state.get("_belief") or {}
            hand_counts = belief.get("hand_counts") or {}
            if seat in hand_counts:
                try:
                    return int(hand_counts[seat])
                except (TypeError, ValueError):
                    pass
        return int(self._t.hand_counts.get(seat, 27) or 0)

    def can_opponent_form_type(
        self,
        opp_seat: int,
        action_type: str,
        target_rank: str,
        game_state=None,
    ) -> bool:
        """MEM-M02：对手 opp_seat 是否仍可能用同型更大牌压制。

        比 can_opponent_suppress 多考虑：对子需 2 张、三带二需 3+2、
        牌路 PASS 弱项、剩张不足以组成该型。
        """
        if opp_seat not in self._t.opponents:
            return False

        action_type = str(action_type or "")
        if action_type in ("Bomb", "StraightFlush", "PASS"):
            return self._t.get_opponent_bomb_risk(opp_seat) >= 0.55

        remaining = self._seat_remaining(opp_seat, game_state)
        if remaining < self._min_cards_for_action_type(action_type):
            return False
        if self._seat_type_weakness_count(opp_seat, action_type) >= 2:
            return False
        if self.seat_unlikely_form_type(opp_seat, action_type):
            return False

        if action_type == "Single":
            return any(
                self._count_possible_enemy_copies(rank) >= 1
                for rank in self._iter_higher_ranks(target_rank)
            )
        if action_type == "Pair":
            return any(
                self._count_possible_enemy_copies(rank) >= 2
                for rank in self._iter_higher_ranks(target_rank)
            )
        if action_type == "Trips":
            return any(
                self._count_possible_enemy_copies(rank) >= 3
                for rank in self._iter_higher_ranks(target_rank)
            )
        if action_type == "ThreeWithTwo":
            for trip_rank in self._iter_higher_ranks(target_rank):
                if self._is_head_rank_depleted(trip_rank):
                    continue
                if self._count_possible_enemy_copies(trip_rank) < 3:
                    continue
                for pair_rank in RANKS + ["SB", "HR"]:
                    if pair_rank == trip_rank:
                        continue
                    if self._count_possible_enemy_copies(pair_rank) >= 2:
                        return True
            return False
        if action_type in ("Straight", "ThreePair", "TwoTrips"):
            if self._seat_type_weakness_count(opp_seat, action_type) >= 1:
                return remaining >= 10
            return remaining >= 5
        return False

    def _can_any_enemy_form_same_type(self, action_type: str, target_rank: str) -> bool:
        """基于记牌估算：任一对手是否仍可能形成更大的同型压制。"""
        for opp in self._t.opponents:
            if self.can_opponent_form_type(opp, action_type, target_rank):
                return True
        return False

    @staticmethod
    def _clip01(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _infer_enemy_shape_hint(
        self,
        remaining: int,
        recent_action_type: str,
        bomb_risk: float,
    ) -> str:
        """敌方剩牌粗分类：只给中局调度吃标签，不直接驱动 actIndex。"""
        if recent_action_type in STRUCTURED_ACTION_TYPES:
            return "structured"
        if remaining <= 1:
            return "single_heavy"
        if remaining == 2:
            if recent_action_type == "Pair":
                return "pair_heavy"
            return "unknown"
        if remaining == 3:
            if recent_action_type == "Trips":
                return "structured"
            if recent_action_type == "Single":
                return "single_heavy"
            return "unknown"
        if remaining == 4:
            if bomb_risk >= 0.6:
                return "structured"
            if recent_action_type == "Pair":
                return "pair_heavy"
            if recent_action_type == "Single":
                return "single_heavy"
            return "unknown"
        if remaining in (5, 6):
            if recent_action_type in ("Straight", "ThreeWithTwo", "Bomb", "StraightFlush"):
                return "structured"
            if bomb_risk >= 0.5:
                return "structured"
            if recent_action_type == "Pair":
                return "pair_heavy"
            if recent_action_type == "Single":
                return "single_heavy"
            return "unknown"
        return "unknown"

    def _estimate_bomb_plus_single_risk(
        self,
        remaining: int,
        recent_action_type: str,
        bomb_risk: float,
    ) -> float:
        if remaining != 5:
            return 0.0
        risk = bomb_risk
        if recent_action_type == "Single":
            risk = max(risk, 0.55)
        if recent_action_type in ("Straight", "ThreeWithTwo"):
            risk *= 0.5
        return self._clip01(risk)

    def _infer_same_type_suppressor_outside(self, game_state=None) -> bool:
        if not game_state:
            return False
        greater_pos = game_state.get("greaterPos", -1)
        greater_action = game_state.get("greaterAction")
        if not isinstance(greater_action, list) or len(greater_action) < 2:
            return False

        action_type = str(greater_action[0] or "")
        target_rank = str(greater_action[1] or "")
        if not action_type or action_type == "PASS":
            return False

        if greater_pos in self._t.opponents:
            action_list = game_state.get("actionList") or []
            return any(
                isinstance(action, list)
                and len(action) >= 1
                and action[0] == action_type
                and action[0] != "PASS"
                for action in action_list
            )

        if greater_pos in (self._t.my_pos, self._t.partner_pos):
            return self._can_any_enemy_form_same_type(action_type, target_rank)

        return False

    def _estimate_teammate_cover_confidence(self, game_state=None) -> float:
        partner_pos = self._t.partner_pos
        remaining = self._t.hand_counts.get(partner_pos, 27)
        # 队友已头游：无法再承接任何牌权，cover 必须为 0（禁止 mid_hold_for_teammate）
        if remaining <= 0:
            return 0.0
        if remaining <= 2:
            base = 0.85
        elif remaining <= 4:
            base = 0.70
        elif remaining <= 6:
            base = 0.55
        elif remaining <= 10:
            base = 0.35
        else:
            base = 0.20

        safe_rank_count = sum(1 for rank in RANKS if self.is_rank_safe(rank))
        if safe_rank_count >= 4:
            base += 0.10
        elif safe_rank_count >= 2:
            base += 0.05

        if game_state:
            greater_pos = game_state.get("greaterPos", -1)
            greater_action = game_state.get("greaterAction")
            same_type_suppressor_outside = self._infer_same_type_suppressor_outside(game_state)
            if greater_pos == partner_pos:
                if (
                    isinstance(greater_action, list)
                    and len(greater_action) >= 1
                    and greater_action[0] in ("Bomb", "StraightFlush")
                ):
                    return 1.0
                if not same_type_suppressor_outside:
                    base = max(base, 0.90)

        enemy_bomb_risk_max = max(
            (self._t.get_opponent_bomb_risk(opp) for opp in self._t.opponents),
            default=0.0,
        )
        if enemy_bomb_risk_max >= 0.8 and remaining >= 6:
            base -= 0.10

        return self._clip01(base)

    def _estimate_teammate_rear_single_cover_confidence(self, game_state=None) -> float:
        """估算：上家敌方报尽单张时，尾位队友是否大概率仍有可接单张。"""
        if not game_state:
            return 0.0

        greater_pos = game_state.get("greaterPos", -1)
        greater_action = game_state.get("greaterAction")
        if greater_pos not in self._t.opponents:
            return 0.0
        if greater_pos != (self._t.my_pos + 3) % 4:
            return 0.0
        if not isinstance(greater_action, list) or len(greater_action) < 3:
            return 0.0
        if str(greater_action[0] or "") != "Single":
            return 0.0

        partner_pos = self._t.partner_pos
        try:
            partner_remaining = int(self._t.hand_counts.get(partner_pos, 0))
        except (TypeError, ValueError):
            partner_remaining = 0
        if partner_remaining <= 0:
            return 0.0

        try:
            leader_remaining = int(self._t.hand_counts.get(greater_pos, 27))
        except (TypeError, ValueError):
            leader_remaining = 27
        if leader_remaining > 0:
            return 0.0

        trailing_enemy = next(
            (seat for seat in self._t.opponents if seat != greater_pos),
            -1,
        )
        try:
            trailing_enemy_remaining = int(self._t.hand_counts.get(trailing_enemy, 0))
        except (TypeError, ValueError):
            trailing_enemy_remaining = 0
        total_slots = partner_remaining + trailing_enemy_remaining
        if total_slots <= 0:
            return 0.0

        cards = greater_action[2] if isinstance(greater_action[2], list) else []
        if cards:
            target_rank = _parse_card_rank_fast(str(cards[0]))
        else:
            raw_rank = str(greater_action[1] or "")
            target_rank = {"R": "HR", "B": "SB", "10": "T"}.get(raw_rank, raw_rank)

        target_value = RANK_VALUE_WITH_JOKERS.get(target_rank)
        if target_value is None:
            return 0.0

        higher_candidates = 0
        exact_partner_cover = False
        for card_type, value in RANK_VALUE_WITH_JOKERS.items():
            if value <= target_value:
                continue
            if card_type in ("SB", "HR"):
                copies = self._t.card_state.get(card_type, [-1, -1])
            else:
                copies = []
                for suit in SUITS:
                    copies.extend(self._t.card_state.get(f"{suit}{card_type}", [-1, -1]))
            for owner in copies:
                if owner == MemoryTracker.PARTNER_HAND:
                    exact_partner_cover = True
                if owner not in (MemoryTracker.MY_HAND, MemoryTracker.PLAYED):
                    higher_candidates += 1

        if exact_partner_cover:
            return 1.0
        if higher_candidates <= 0:
            return 0.0

        higher_candidates = min(higher_candidates, total_slots)
        if higher_candidates >= total_slots:
            return 1.0

        safe_without_cover = total_slots - higher_candidates
        if safe_without_cover < partner_remaining:
            return 1.0

        no_cover = comb(safe_without_cover, partner_remaining) / comb(
            total_slots, partner_remaining
        )
        return self._clip01(1.0 - no_cover)

    def infer_phase_relation(self, game_state=None) -> Dict[str, Any]:
        """GUA-094：规则版推断层最小闭环。

        只输出标签/概率，不直接改 actIndex，供后续 stage_2 专用决策器消费。
        """
        hand_counts = dict(self._t.hand_counts)
        opp_bomb_risks = {
            opp: self._t.get_opponent_bomb_risk(opp) for opp in self._t.opponents
        }

        enemy_shape_hints: Dict[int, str] = {}
        enemy_bomb_plus_single_risks: Dict[int, float] = {}
        for opp in sorted(self._t.opponents):
            remaining = hand_counts.get(opp, 27)
            recent_action_type = self._get_recent_action_type(opp, game_state)
            bomb_risk = opp_bomb_risks.get(opp, 0.0)
            enemy_shape_hints[opp] = self._infer_enemy_shape_hint(
                remaining, recent_action_type, bomb_risk
            )
            enemy_bomb_plus_single_risks[opp] = self._estimate_bomb_plus_single_risk(
                remaining, recent_action_type, bomb_risk
            )

        critical_enemy_seat = min(
            self._t.opponents,
            key=lambda seat: (hand_counts.get(seat, 27), seat),
        )
        same_type_suppressor_outside = self._infer_same_type_suppressor_outside(game_state)

        return {
            "critical_enemy_seat": critical_enemy_seat,
            "enemy_shape_hint": enemy_shape_hints.get(critical_enemy_seat, "unknown"),
            "enemy_shape_hints": enemy_shape_hints,
            "enemy_bomb_plus_single_risks": enemy_bomb_plus_single_risks,
            "teammate_cover_confidence": self._estimate_teammate_cover_confidence(
                game_state
            ),
            "teammate_rear_single_cover_confidence": (
                self._estimate_teammate_rear_single_cover_confidence(game_state)
            ),
            "same_type_suppressor_outside": same_type_suppressor_outside,
            "enemy_bomb_risk_max": max(opp_bomb_risks.values(), default=0.0),
        }

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

    # ── GUA-263：文章第六～九节推理信号（5/10 顺骨架、断张炸、A/K、牌路）──

    def _rank_copy_stats(self, rank: str) -> Dict[str, int]:
        """某 rank 的已出/我手/剩余（未出）张数。普通点 8 张，王 2 张。"""
        tracker = self._t
        played = 0
        mine = 0
        if rank in ("SB", "HR"):
            copies = tracker.card_state.get(rank, [-1, -1])
            played = sum(1 for c in copies if c == tracker.PLAYED)
            mine = sum(1 for c in copies if c == tracker.MY_HAND)
            total = 2
        else:
            total = 8
            for suit in SUITS:
                copies = tracker.card_state.get(f"{suit}{rank}", [-1, -1])
                played += sum(1 for c in copies if c == tracker.PLAYED)
                mine += sum(1 for c in copies if c == tracker.MY_HAND)
        remain = max(0, total - played)
        return {
            "played": played,
            "in_my_hand": mine,
            "remain": remain,
            "outside_my_hand": max(0, remain - mine),
        }

    def get_straight_skeleton_signal(self) -> Dict[str, Any]:
        """GUA-263 §六：5/10 是顺子骨架。

        定音（用户校正）：**外面** 5/10 打光（outside_my_hand==0）时，
        对手组不出依赖该骨架的顺 → 我方对应起点的 Straight **更安全、应优先出**，
        而非当作「死窗剔除」。
        """
        five = self._rank_copy_stats("5")
        ten = self._rank_copy_stats("T")
        # 窗口用起点 rank 标记（平台 Straight rank 多为窗口最低点）
        windows_need_five = ["A", "2", "3", "4", "5"]  # A2345 … 56789
        windows_need_ten = ["6", "7", "8", "9", "T"]   # 6789T … TJQKA
        safe: List[str] = []
        if five["outside_my_hand"] <= 0:
            safe.extend(windows_need_five)
        if ten["outside_my_hand"] <= 0:
            safe.extend(windows_need_ten)
        return {
            "five_remain": five["remain"],
            "ten_remain": ten["remain"],
            "five_outside": five["outside_my_hand"],
            "ten_outside": ten["outside_my_hand"],
            "five_outside_depleted": five["outside_my_hand"] <= 0,
            "ten_outside_depleted": ten["outside_my_hand"] <= 0,
            # 对手无法组这些窗 → 我出这些起点的顺更难被同型压制
            "safe_straight_windows": sorted(set(safe)),
        }

    def is_straight_window_outside_safe(self, window_start_rank: str) -> bool:
        """Straight 起点是否因外面 5/10 打光而对敌不可组（我方可放心冲）。"""
        sig = self.get_straight_skeleton_signal()
        return str(window_start_rank) in sig["safe_straight_windows"]

    def get_gap_bomb_risk_signal(self) -> Dict[str, Any]:
        """GUA-263 §七：我断张 + 邻点多出单 → 外炸预警。"""
        tracker = self._t
        my_rank_cnt: Counter = Counter()
        for ct, copies in tracker.card_state.items():
            if ct in ("SB", "HR"):
                continue
            rk = _parse_card_rank_fast(ct)
            if rk not in RANK_VALUE:
                continue
            my_rank_cnt[rk] += sum(1 for c in copies if c == tracker.MY_HAND)

        # 邻点散单次数（全场 Single 出牌）
        neighbor_singles: Dict[str, int] = defaultdict(int)
        for entry in tracker.play_history:
            if str(entry.get("action_type") or "").upper() != "SINGLE":
                continue
            for card in entry.get("cards") or []:
                rk = _parse_card_rank_fast(
                    tracker._canonical_type(str(card))
                    if hasattr(tracker, "_canonical_type")
                    else str(card)
                )
                if rk in RANK_VALUE:
                    neighbor_singles[rk] += 1

        gap_ranks: List[str] = []
        high_risk: List[str] = []
        risk_scores: Dict[str, float] = {}
        for rk in RANKS:
            if my_rank_cnt.get(rk, 0) > 0:
                continue
            outside = self._rank_copy_stats(rk)["outside_my_hand"]
            if outside <= 0:
                continue
            gap_ranks.append(rk)
            val = RANK_VALUE[rk]
            adj = 0
            for other, ov in RANK_VALUE.items():
                if abs(ov - val) == 1:
                    adj += neighbor_singles.get(other, 0)
            # 邻点散单 ≥3 → 高风险；按次数归一
            score = min(1.0, adj / 3.0) if adj > 0 else 0.0
            if outside >= 4:
                score = max(score, 0.4)
            risk_scores[rk] = score
            if score >= 0.7:
                high_risk.append(rk)

        max_risk = max(risk_scores.values()) if risk_scores else 0.0
        return {
            "gap_ranks": gap_ranks,
            "high_bomb_gap_ranks": high_risk,
            "gap_bomb_risk_by_rank": dict(risk_scores),
            "gap_bomb_risk_max": float(max_risk),
        }

    def get_ak_power_signal(self) -> Dict[str, Any]:
        """GUA-263 §八：A/K 剩余与登基潜力。"""
        a = self._rank_copy_stats("A")
        k = self._rank_copy_stats("K")
        return {
            "a_remain": a["remain"],
            "a_in_my_hand": a["in_my_hand"],
            "a_outside": a["outside_my_hand"],
            "k_remain": k["remain"],
            "k_in_my_hand": k["in_my_hand"],
            "k_outside": k["outside_my_hand"],
            # 外面无 A 且我有 A → 非王/级牌体系下 A 可登基（忽略王时的软信号）
            "my_a_crowns": a["in_my_hand"] > 0 and a["outside_my_hand"] <= 0,
            "my_k_crowns": (
                k["in_my_hand"] > 0
                and k["outside_my_hand"] <= 0
                and a["outside_my_hand"] <= 0
                and a["in_my_hand"] <= 0
            ),
        }

    def get_line_read_signal(self) -> Dict[str, Any]:
        """GUA-263 §九：牌路读心——连出单≈缺对；队友送小≈求大单。"""
        tracker = self._t
        seats: Dict[int, Dict[str, Any]] = {}
        for seat in range(4):
            singles = 0
            pairs = 0
            small_singles = 0
            for entry in tracker.play_history:
                if int(entry.get("seat", -1)) != seat:
                    continue
                at = str(entry.get("action_type") or "").upper()
                cards = entry.get("cards") or []
                if at == "SINGLE":
                    singles += 1
                    if cards:
                        rk = _parse_card_rank_fast(str(cards[0]))
                        if RANK_VALUE.get(rk, 99) <= RANK_VALUE.get("9", 7):
                            small_singles += 1
                elif at == "PAIR":
                    pairs += 1
            likely_short_pair = singles >= 3 and pairs == 0
            seats[seat] = {
                "single_plays": singles,
                "pair_plays": pairs,
                "small_single_plays": small_singles,
                "likely_short_pair": likely_short_pair,
            }

        tm = tracker.partner_pos
        down = (tracker.my_pos + 1) % 4
        tm_info = seats.get(tm, {})
        down_info = seats.get(down, {})
        return {
            "seats": seats,
            "teammate_wants_big_single": (
                int(tm_info.get("small_single_plays", 0)) >= 2
            ),
            "downseat_short_pair": bool(down_info.get("likely_short_pair")),
            "teammate_short_pair": bool(tm_info.get("likely_short_pair")),
        }

    # ── 信念字典（完整 ────────────────────────────────

    def get_belief(self, game_state=None) -> Dict[str, Any]:
        """返回完整信念 dict，供 engine._inject_belief_vector 注入 game_state。

        信念信号（全部零成本、纯计数）：
          - hr_played/sb_played: 大小王已出张数 (0-2)
          - hr_remain/sb_remain: 大小王未打出张数 (0-2)
          - joker_signal: 大小王完整记牌（含队友/对手归属推断）
          - level_remain: 级牌剩余张数 (0-8)
          - opp_bomb_risks: {opp_seat: float} 对手炸弹风险 0~1
          - hand_counts: {seat: int} 各家剩余张数
          - depleted_ranks: list[str] 已完全耗尽的 rank（8 张全出或全已知归属）
          - safe_ranks: set[str] 安全的 rank（对手不可持有）
          - can_opp_suppress_current: 对手是否可能压制当前控牌
          - can_opp_form_type_current: MEM-M02 对手能否同型反压当前控牌
          - high_card_signal: MEM-M01 get_high_card_signal() 返回值
          - key_card_signal / type_route / head_bomb_signal / tribute_signal: M3–M5
          - bomb_stats: get_bomb_stats() 返回值
          - level_signal: get_level_signal() 返回值
          - unknown_rank_stats: get_unknown_rank_stats() 返回值
          - GUA-263: straight_skeleton / gap_bomb_risk / ak_power / line_read
        """
        tracker = self._t
        joker = self.get_joker_signal()

        # 级牌剩余
        level_left = 0
        if tracker.level_cards_remaining:
            for lc in tracker.level_cards_remaining:
                copies = tracker.card_state.get(lc, [])
                level_left += sum(1 for c in copies if c != 4)

        gap_sig = self.get_gap_bomb_risk_signal()
        gap_boost = float(gap_sig.get("gap_bomb_risk_max") or 0.0)

        # 对手炸弹风险（基线 + §七断张炸抬升）
        opp_risks = {}
        for opp in tracker.opponents:
            base = tracker.get_opponent_bomb_risk(opp)
            opp_risks[opp] = min(1.0, max(base, gap_boost * 0.85))

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
        can_opp_form_type = True
        if game_state:
            greater_pos = game_state.get("greaterPos", -1)
            greater_action = game_state.get("greaterAction")
            if (greater_pos in tracker.opponents
                    and greater_action
                    and isinstance(greater_action, list)
                    and len(greater_action) >= 2):
                g_rank = str(greater_action[1])
                g_type = str(greater_action[0])
                can_opp_suppress = self.can_opponent_suppress(greater_pos, g_rank)
                can_opp_form_type = self.can_opponent_form_type(
                    greater_pos, g_type, g_rank, game_state
                )

        hand_counts = dict(tracker.hand_counts)

        return {
            "hr_played": joker["hr_played"],
            "sb_played": joker["sb_played"],
            "hr_remain": joker["hr_remain"],
            "sb_remain": joker["sb_remain"],
            "joker_signal": joker,
            "level_remain": level_left,
            "opp_bomb_risks": opp_risks,
            "hand_counts": hand_counts,
            "depleted_ranks": depleted,
            "safe_ranks": safe,
            "can_opp_suppress_current": can_opp_suppress,
            "can_opp_form_type_current": can_opp_form_type,
            "high_card_signal": self.get_high_card_signal(),
            "key_card_signal": self.get_key_card_signal(),
            "type_route": self.get_type_route_signal(),
            "head_bomb_signal": self.get_head_bomb_signal(),
            "tribute_signal": self.get_tribute_signal(),
            "bomb_stats": self.get_bomb_stats(),
            "level_signal": self.get_level_signal(),
            "unknown_rank_stats": self.get_unknown_rank_stats(),
            "straight_skeleton": self.get_straight_skeleton_signal(),
            "gap_bomb_risk": gap_sig,
            "ak_power": self.get_ak_power_signal(),
            "line_read": self.get_line_read_signal(),
        }


def create_counter_from_tracker(tracker) -> RuleCardCounter:
    """工厂函数：从 MemoryTracker 构造 RuleCardCounter。"""
    return RuleCardCounter(tracker)
