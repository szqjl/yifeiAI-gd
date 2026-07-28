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
JOKERS = ["SB", "HR"]  # 平台原生：SB=小王, HR=大王

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
# GUA-061 升级（2026-06-18）：24 维 + 24 维 grouping_engine = 48 维（可选）
MEMORY_TRACKER_DIM = 33           # 当前默认（兼容已训练模型）
MEMORY_TRACKER_DIM_V061 = 48      # GUA-061 升级：24 追踪 + 24 grouping_engine
GROUPING_SCORE_DIM = 9            # GUA-054 grouping_scanner 维度
GROUPING_ENGINE_DIM = 24          # GUA-061 grouping_engine 维度

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

# ── GUA-061 grouping_engine 接入（2026-06-18）──────
try:
    from src.v.nn.features.grouping_engine import (
        extract_grouping_features as extract_grouping_engine_features,
        get_grouping_engine_dim,
    )
    _grouping_engine_import_ok = True
except ImportError as e:
    _grouping_engine_import_ok = False
    print(f"[Warning] grouping_engine 导入失败: {e}, 退化为 grouping_scanner 模式")


def _parse_card_rank(card: str) -> str:
    """从牌面字符串提取点数。平台原生 SB(小王)/HR(大王)。"""
    if card in ("SB", "HR"):
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
                 max_infer_depth: int = 0, use_grouping_engine: bool = False):
        self.my_pos = my_pos
        self.partner_pos = (my_pos + 2) % 4
        self.opponents = {(my_pos + 1) % 4, (my_pos + 3) % 4}
        self.use_grouping_engine = use_grouping_engine  # GUA-061 开关

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

        # 牌型弱点追踪（GUA-179）：对手某牌型上 PASS/被迫开炸的次数
        # type_weakness[seat][type] = 该位在该牌型上 PASS 的次数
        self.type_weakness: Dict[int, Dict[str, int]] = {}
        # type_bombed[seat][type] = 该位在该牌型上被迫开炸的次数
        self.type_bombed: Dict[int, Dict[str, int]] = {}

        # 贡牌/抗贡（04_calculation_skills §二.1 + 06_game_flow）
        self.tribute_history: List[Dict[str, Any]] = []
        self._processed_tribute_keys: Set[str] = set()
        self._processed_anti_keys: Set[str] = set()
        self._anti_tribute_pos: List[int] = []
        self._tribute_sync_fingerprint: Optional[str] = None

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

    def record_play(
        self,
        seat: int,
        action: List[Any],
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """记录某席出牌动作。

        action 格式: ["Bomb", "8", [...]] 或 tribute/back 单张转移。
        """
        if not action or len(action) < 3:
            return
        action_type = str(action[0]).lower()
        cards = action[2] if isinstance(action[2], list) else []
        if not cards:
            return

        ctx = context or {}
        if action_type == "tribute":
            tribute_pos = ctx.get("tribute_pos", seat)
            receive_pos = ctx.get("receive_tribute_pos")
            try:
                tribute_pos = int(tribute_pos)
            except (TypeError, ValueError):
                tribute_pos = seat
            if receive_pos is not None:
                try:
                    receive_pos = int(receive_pos)
                except (TypeError, ValueError):
                    receive_pos = None
            if receive_pos is not None:
                self.record_tribute_transfer(tribute_pos, receive_pos, cards[0])
            else:
                self.record_tribute_outgoing(tribute_pos, cards[0])
            return
        if action_type == "back":
            back_pos = ctx.get("back_pos", seat)
            receive_pos = ctx.get("receive_back_pos")
            try:
                back_pos = int(back_pos)
            except (TypeError, ValueError):
                back_pos = seat
            if receive_pos is not None:
                try:
                    receive_pos = int(receive_pos)
                except (TypeError, ValueError):
                    receive_pos = None
            if receive_pos is not None:
                self.record_back_transfer(back_pos, receive_pos, cards[0])
            else:
                self.record_tribute_outgoing(back_pos, cards[0])
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

        # GUA-179：若用炸/同花顺压制非炸牌型 → 记为该牌型弱点
        ga = ctx.get("greaterAction")
        if (isinstance(ga, list) and len(ga) >= 3 and str(action[0]).upper()
                in ("BOMB", "STRAIGHTFLUSH")):
            ga_type = str(ga[0])
            if ga_type.upper() not in ("PASS", "BOMB", "STRAIGHTFLUSH"):
                if seat not in self.type_bombed:
                    self.type_bombed[seat] = {}
                self.type_bombed[seat][ga_type] = (
                    self.type_bombed[seat].get(ga_type, 0) + 1
                )

        # GUA-072：大小王 always-on 归属推断（不依赖 enable_inference）
        self._infer_joker_ownership(seat, cards, str(action[0]))

        # 排除法推断（如果启用；大小王已在 _infer_joker_ownership 单独处理）
        if self.enable_inference and self.max_infer_depth > 0:
            import time
            t0 = time.time()
            self._infer_after_play(seat, cards)
            elapsed_ms = (time.time() - t0) * 1000
            self.inference_time_ms += elapsed_ms
            if elapsed_ms > 50:
                logger.warning("排除法推断耗时 %.0fms (seat=%d, cards=%s)",
                               elapsed_ms, seat, cards[:3])

    def record_pass(self, seat: int, target_type: str) -> None:
        """记录某席因无法压制某牌型而 PASS。"""
        if target_type and target_type.upper() not in ("PASS", ""):
            if seat not in self.type_weakness:
                self.type_weakness[seat] = {}
            self.type_weakness[seat][target_type] = (
                self.type_weakness[seat].get(target_type, 0) + 1
            )

    def get_type_weakness(self, seat: int) -> Dict[str, int]:
        """综合弱点：PASS 次数 + 被迫开炸次数。"""
        result = {}
        for d in [self.type_weakness.get(seat, {}), self.type_bombed.get(seat, {})]:
            for k, v in d.items():
                result[k] = result.get(k, 0) + v
        return result

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

    # ── 贡牌 / 抗贡（04_calculation_skills §二.1 + 06_game_flow）────────

    def record_anti_tribute(self, anti_pos: List[Any]) -> None:
        """抗贡：antiPos 各席持双 HR（06_game_flow 双大王免进贡）。"""
        if not anti_pos:
            return
        try:
            positions = sorted(int(p) for p in anti_pos)
        except (TypeError, ValueError):
            return
        key = tuple(positions)
        if key in self._processed_anti_keys:
            return
        self._processed_anti_keys.add(key)
        self._anti_tribute_pos = list(positions)

        if len(positions) == 1:
            self._assign_joker_copies_to_seat("HR", positions[0], 2)
        else:
            for i, pos in enumerate(positions[:2]):
                self._assign_joker_copies_to_seat("HR", pos, 1, copy_index=i)

        self._infer_joker_from_tribute_rules()
        logger.debug("抗贡推断 antiPos=%s joker=%s", positions, self.get_joker_tracking())

    def record_tribute_transfer(
        self, tribute_pos: int, receive_pos: int, card: str
    ) -> None:
        """进贡 notify：末游→头游等单张转移（非打出）。"""
        key = f"tribute:{tribute_pos}:{receive_pos}:{self._canonical_type(card)}"
        if key in self._processed_tribute_keys:
            return
        self._processed_tribute_keys.add(key)
        self._transfer_card(int(tribute_pos), int(receive_pos), card, event="tribute")
        self.tribute_history.append(
            {
                "event": "tribute",
                "from": int(tribute_pos),
                "to": int(receive_pos),
                "card": self._canonical_type(card),
            }
        )
        self._infer_joker_from_tribute_rules()

    def record_back_transfer(self, back_pos: int, receive_pos: int, card: str) -> None:
        """还贡 notify：单张转移。"""
        key = f"back:{back_pos}:{receive_pos}:{self._canonical_type(card)}"
        if key in self._processed_tribute_keys:
            return
        self._processed_tribute_keys.add(key)
        self._transfer_card(int(back_pos), int(receive_pos), card, event="back")
        self.tribute_history.append(
            {
                "event": "back",
                "from": int(back_pos),
                "to": int(receive_pos),
                "card": self._canonical_type(card),
            }
        )

    def record_tribute_outgoing(self, from_seat: int, card: str) -> None:
        """进贡/还贡 act（仅知送出方）：从该席移除标记，不记为已打出。"""
        key = f"out:{from_seat}:{self._canonical_type(card)}"
        if key in self._processed_tribute_keys:
            return
        self._processed_tribute_keys.add(key)
        self._release_card_from_seat(int(from_seat), card)
        self.hand_counts[from_seat] = max(0, self.hand_counts.get(from_seat, HAND_SIZE) - 1)
        self.tribute_history.append(
            {
                "event": "outgoing",
                "from": int(from_seat),
                "card": self._canonical_type(card),
            }
        )

    def sync_tribute_phase_from_state(
        self,
        *,
        tribute_result: Optional[List[Any]] = None,
        back_result: Optional[List[Any]] = None,
        anti_pos: Optional[List[Any]] = None,
        cur_rank: str = "2",
    ) -> None:
        """从 game_state 批量消费贡牌/抗贡 notify（去重）。"""
        fp = repr((tribute_result, back_result, anti_pos))
        if fp != self._tribute_sync_fingerprint:
            self.clear_tribute_phase_state()
            self._tribute_sync_fingerprint = fp

        if anti_pos:
            self.record_anti_tribute(anti_pos)
        for item in tribute_result or []:
            if not isinstance(item, (list, tuple)) or len(item) < 3:
                continue
            try:
                tp, rp = int(item[0]), int(item[1])
            except (TypeError, ValueError):
                continue
            self.record_tribute_transfer(tp, rp, str(item[2]))
        for item in back_result or []:
            if not isinstance(item, (list, tuple)) or len(item) < 3:
                continue
            try:
                bp, rp = int(item[0]), int(item[1])
            except (TypeError, ValueError):
                continue
            self.record_back_transfer(bp, rp, str(item[2]))
        if tribute_result:
            self._infer_joker_from_tribute_rules(cur_rank=str(cur_rank))

    def clear_tribute_phase_state(self) -> None:
        """新一副开始时清理贡牌阶段去重键（保留 card_state 推断结果）。"""
        self._processed_tribute_keys.clear()
        self._processed_anti_keys.clear()
        self._anti_tribute_pos.clear()
        self.tribute_history.clear()
        self._tribute_sync_fingerprint = None

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

    def sync_my_jokers(self, hand_cards: List[str]) -> None:
        """用当前手牌校准大小王 MY_HAND 标记（每步 decide 调用）。"""
        want = Counter(
            self._canonical_type(c) for c in hand_cards
            if self._canonical_type(c) in JOKERS
        )
        for jt in JOKERS:
            copies = self.card_state[jt]
            target = want.get(jt, 0)
            my_indices = [i for i, c in enumerate(copies) if c == self.MY_HAND]
            if len(my_indices) > target:
                for i in my_indices[target:]:
                    copies[i] = -1
            elif len(my_indices) < target:
                need = target - len(my_indices)
                for i in range(2):
                    if need <= 0:
                        break
                    if copies[i] == -1:
                        copies[i] = self.MY_HAND
                        need -= 1

    def _count_joker_plays_by_seat(self, joker_type: str) -> Dict[int, int]:
        """统计各席已打出某王张数（来自 play_history）。"""
        counts: Dict[int, int] = defaultdict(int)
        for entry in self.play_history:
            seat = entry.get("seat", -1)
            if seat < 0:
                continue
            for card in entry.get("cards", []):
                if self._canonical_type(card) == joker_type:
                    counts[seat] += 1
        return dict(counts)

    def _joker_copy_stats(self, joker_type: str) -> Dict[str, int]:
        """单种王的副本状态计数。"""
        copies = self.card_state.get(joker_type, [-1, -1])
        played = sum(1 for c in copies if c == self.PLAYED)
        my_c = sum(1 for c in copies if c == self.MY_HAND)
        partner_c = sum(1 for c in copies if c == self.PARTNER_HAND)
        opp_c = sum(1 for c in copies if c == self.OPPONENT_HAND)
        unknown = sum(1 for c in copies if c == -1)
        return {
            "played": played,
            "remain": max(0, 2 - played),
            "in_my_hand": my_c,
            "with_teammate": partner_c,
            "with_opponents": opp_c,
            "unknown": unknown,
            "outside_my_hand": max(0, 2 - played - my_c),
        }

    def get_joker_tracking(self) -> Dict[str, Dict[str, int]]:
        """大小王记牌摘要：已出/剩余/在我手/队友/对手/未知。"""
        return {jt: self._joker_copy_stats(jt) for jt in JOKERS}

    def _infer_joker_ownership(
        self,
        acting_seat: int,
        cards: List[str],
        action_type: str = "",
    ) -> None:
        """Always-on：根据出牌与手牌校准大小王副本归属（PARTNER/OPPONENT/PLAYED）。"""
        action_type_l = (action_type or "").lower()
        jokers_in_action = [
            self._canonical_type(c) for c in cards if self._canonical_type(c) in JOKERS
        ]
        if len(jokers_in_action) >= 2 and jokers_in_action.count("HR") >= 2:
            self._assign_joker_copies_to_seat("SB", acting_seat, 1)
        elif (
            action_type_l in ("pair", "pairpair")
            and jokers_in_action.count("HR") >= 2
        ):
            self._assign_joker_copies_to_seat("SB", acting_seat, 1)

        hr_before = self._seat_played_joker_before("HR", acting_seat)
        sb_in_action = "SB" in jokers_in_action
        if hr_before and sb_in_action:
            self._assign_joker_copies_to_seat("SB", acting_seat, 1)

        for jt in JOKERS:
            copies = self.card_state[jt]
            played = sum(1 for c in copies if c == self.PLAYED)
            my_c = sum(1 for c in copies if c == self.MY_HAND)

            # 已出 + 在我手 = 两副本穷尽 → 剩余 unknown 归对家或敌家
            if played + my_c >= 2:
                for i in range(2):
                    if copies[i] != -1:
                        continue
                    if acting_seat in self.opponents:
                        copies[i] = self.OPPONENT_HAND
                    elif acting_seat == self.partner_pos:
                        copies[i] = self.PARTNER_HAND
                    else:
                        copies[i] = self.OPPONENT_HAND
                continue

            if played >= 2:
                continue

            plays_by_seat = self._count_joker_plays_by_seat(jt)
            partner_plays = plays_by_seat.get(self.partner_pos, 0)
            opp_plays = sum(plays_by_seat.get(s, 0) for s in self.opponents)
            unk_indices = [i for i, c in enumerate(copies) if c == -1]

            if played == 1 and my_c == 0 and len(unk_indices) == 1:
                idx = unk_indices[0]
                if opp_plays >= 2:
                    copies[idx] = self.PLAYED
                elif partner_plays >= 1 and opp_plays == 0:
                    if self.hand_counts.get(self.partner_pos, HAND_SIZE) <= 5:
                        copies[idx] = self.OPPONENT_HAND
                elif opp_plays >= 1 and partner_plays == 0:
                    if (
                        acting_seat in self.opponents
                        and self.hand_counts.get(acting_seat, HAND_SIZE) <= 5
                    ):
                        copies[idx] = self.PARTNER_HAND

            partner_held = sum(1 for c in copies if c == self.PARTNER_HAND)
            opp_held = sum(1 for c in copies if c == self.OPPONENT_HAND)
            if played + my_c + partner_held + opp_held >= 2:
                for i in range(2):
                    if copies[i] != -1:
                        continue
                    if partner_held > 0 and opp_held == 0:
                        copies[i] = self.OPPONENT_HAND
                    elif opp_held > 0 and partner_held == 0:
                        copies[i] = self.PARTNER_HAND

    def _infer_joker_from_tribute_rules(self, cur_rank: str = "2") -> None:
        """贡牌阶段算王：04_calculation_skills §二.1 + 06_game_flow 抗贡。"""
        if self._anti_tribute_pos:
            return

        tribute_events = [
            e for e in self.tribute_history if e.get("event") == "tribute"
        ]
        if not tribute_events:
            return

        cur_rank = str(cur_rank or "2").upper()
        if len(tribute_events) >= 2:
            cards = [e["card"] for e in tribute_events]
            if all(self._is_level_card(c, cur_rank) for c in cards):
                receive_seats = {e["to"] for e in tribute_events}
                self._assign_all_jokers_to_seats(receive_seats)
                return

        if len(tribute_events) == 1:
            ev = tribute_events[0]
            card = ev["card"]
            tribute_pos = ev["from"]
            receive_pos = ev["to"]
            if card != "HR":
                return

            winning_seats = {receive_pos, (receive_pos + 2) % 4}
            losing_seats = {tribute_pos, (tribute_pos + 2) % 4}
            my_jokers = self.get_joker_tracking()
            i_have_jokers = (
                my_jokers["HR"]["in_my_hand"] + my_jokers["SB"]["in_my_hand"]
            ) > 0

            for seat in winning_seats:
                self._assign_joker_copies_to_seat("HR", seat, 1)
            for seat in losing_seats:
                if seat == tribute_pos:
                    continue
                if (
                    seat == self.my_pos
                    and not i_have_jokers
                    and seat != tribute_pos
                    and seat != receive_pos
                ):
                    self._clear_jokers_from_seat(seat)
            for seat in winning_seats | {tribute_pos}:
                self._assign_joker_copies_to_seat("SB", seat, 1)

    def _seat_played_joker_before(self, joker_type: str, seat: int) -> bool:
        for entry in self.play_history:
            if entry.get("seat") != seat:
                continue
            for card in entry.get("cards", []):
                if self._canonical_type(card) == joker_type:
                    return True
        return False

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

    def get_tracking_vector(self) -> List[float]:
        """GUA-063：仅返回追踪部分（24 维），不含组牌特征。

        组牌特征由 V7 引擎在 _extract_features() 中直接调 enumerate_groupings()
        获取后外部拼接，不再通过 MemoryTracker 内部计算。

        24 维 = 4(seat 剩张) + 15(各 rank 已出比例) + 4(各 seat 炸弹数) + 1(级牌剩余)
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
        for r in RANKS + ["SB", "HR"]:
            vec.append(rank_counts.get(r, 0) / 8.0)

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

        return vec

    def get_state_vector(self, game_state: Optional[Dict[str, Any]] = None) -> List[float]:
        """获取记忆追踪状态向量（用于特征拼接）。

        33 维（GUA-054 升级）= 4(seat 剩张) + 15(各 rank 已出比例) + 4(各 seat 炸弹数) + 1(级牌剩余)
                        + 9(grouping_score, GUA-054 软信号)

        GUA-063 说明：此方法保留向后兼容。新架构中推荐用 get_tracking_vector()
        获取 24 维追踪向量，再由 V7 引擎外部拼接一次 enumerate_groupings() 的组牌特征。

        Args:
            game_state: 游戏状态（GUA-054 追加 grouping_score 需要 handCards/curRank）。
                       传 None 时退化为 24 维（向后兼容）。
        """
        vec = self.get_tracking_vector()

        # ── GUA-054/061 追加组牌特征（2026-06-17/18）────
        if self.use_grouping_engine and _grouping_engine_import_ok and game_state is not None:
            # GUA-061: 使用 grouping_engine 24 维
            try:
                hand_cards = game_state.get("handCards", []) or []
                cur_rank = str(game_state.get("curRank", "2"))
                grouping = extract_grouping_engine_features(hand_cards, cur_rank)
                if len(grouping) == GROUPING_ENGINE_DIM:
                    vec.extend(grouping)
                else:
                    vec.extend([0.0] * GROUPING_ENGINE_DIM)
            except Exception as e:
                logger.warning(f"grouping_engine 失败: {e}, 退化零向量")
                vec.extend([0.0] * GROUPING_ENGINE_DIM)
        elif _grouping_import_ok and game_state is not None:
            # GUA-054: 使用 grouping_scanner 9 维（默认）
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
            default_dim = GROUPING_ENGINE_DIM if self.use_grouping_engine else GROUPING_SCORE_DIM
            vec.extend([0.0] * default_dim)

        expected_dim = MEMORY_TRACKER_DIM_V061 if self.use_grouping_engine else MEMORY_TRACKER_DIM
        assert len(vec) == expected_dim, f"state_vector 维度异常: {len(vec)} (期望 {expected_dim})"
        return vec

    # ── 内部方法 ──────────────────────────────────────

    def _seat_bucket(self, seat: int) -> int:
        if seat == self.my_pos:
            return self.MY_HAND
        if seat == self.partner_pos:
            return self.PARTNER_HAND
        return self.OPPONENT_HAND

    def _is_level_card(self, card: str, cur_rank: str) -> bool:
        ct = self._canonical_type(card)
        if ct in JOKERS:
            return False
        rank = _parse_card_rank(ct)
        return rank == str(cur_rank or "2").upper()

    def _assign_joker_copies_to_seat(
        self,
        joker_type: str,
        seat: int,
        count: int,
        *,
        copy_index: Optional[int] = None,
    ) -> None:
        if joker_type not in JOKERS or count <= 0:
            return
        bucket = self._seat_bucket(seat)
        copies = self.card_state[joker_type]
        assigned = 0
        indices = [copy_index] if copy_index is not None else range(2)
        for i in indices:
            if i < 0 or i > 1:
                continue
            if copies[i] == self.PLAYED:
                continue
            if seat == self.my_pos and copies[i] == self.MY_HAND:
                assigned += 1
                continue
            copies[i] = bucket
            assigned += 1
            if assigned >= count:
                return
        for i in range(2):
            if assigned >= count:
                break
            if copies[i] == self.PLAYED:
                continue
            if seat == self.my_pos and copies[i] == self.MY_HAND:
                assigned += 1
                continue
            if copies[i] == bucket:
                assigned += 1
                continue
            if copies[i] in (-1, self.MY_HAND, self.PARTNER_HAND, self.OPPONENT_HAND):
                copies[i] = bucket
                assigned += 1

    def _assign_all_jokers_to_seats(self, seats: Set[int]) -> None:
        if not seats:
            return
        seat_list = sorted(seats)
        for jt in JOKERS:
            copies = self.card_state[jt]
            si = 0
            for i in range(2):
                if copies[i] == self.PLAYED:
                    continue
                if copies[i] == self.MY_HAND:
                    continue
                copies[i] = self._seat_bucket(seat_list[si % len(seat_list)])
                si += 1

    def _clear_jokers_from_seat(self, seat: int) -> None:
        bucket = self._seat_bucket(seat)
        for jt in JOKERS:
            copies = self.card_state[jt]
            for i in range(2):
                if copies[i] == bucket:
                    copies[i] = -1

    def _transfer_card(
        self,
        from_seat: int,
        to_seat: int,
        card: str,
        *,
        event: str = "tribute",
    ) -> None:
        ct = self._canonical_type(card)
        from_bucket = self._seat_bucket(from_seat)
        to_bucket = self._seat_bucket(to_seat)
        copies = self.card_state.get(ct, [-1, -1])

        moved = False
        for i in range(2):
            if copies[i] == from_bucket:
                copies[i] = to_bucket
                moved = True
                break
        if not moved and from_seat == self.my_pos:
            for i in range(2):
                if copies[i] == self.MY_HAND:
                    copies[i] = to_bucket
                    moved = True
                    break
        if not moved:
            for i in range(2):
                if copies[i] == -1:
                    copies[i] = to_bucket
                    moved = True
                    break
        if not moved:
            for i in range(2):
                if copies[i] != self.PLAYED and copies[i] != to_bucket:
                    copies[i] = to_bucket
                    break

        self.hand_counts[from_seat] = max(0, self.hand_counts.get(from_seat, HAND_SIZE) - 1)
        self.hand_counts[to_seat] = min(HAND_SIZE, self.hand_counts.get(to_seat, 0) + 1)

        if ct in JOKERS:
            logger.debug(
                "%s transfer %s %s→%s bucket %s→%s",
                event,
                ct,
                from_seat,
                to_seat,
                from_bucket,
                to_bucket,
            )

    def _release_card_from_seat(self, seat: int, card: str) -> None:
        ct = self._canonical_type(card)
        bucket = self._seat_bucket(seat)
        copies = self.card_state.get(ct, [-1, -1])
        for i in range(2):
            if copies[i] == bucket or (seat == self.my_pos and copies[i] == self.MY_HAND):
                copies[i] = -1
                return

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
        """标准化牌面类型（平台原生 SB=小王, HR=大王）。"""
        legacy = {"BJ": "SB", "RJ": "HR"}
        if card in legacy:
            return legacy[card]
        if card in ("SB", "HR"):
            return card
        if len(card) == 2 and card[0] in SUITS and (card[1].isdigit() or card[1] in RANK_LETTERS):
            return card
        # fallback: 尝试补全花色
        if len(card) >= 2:
            suit = card[0].upper()
            rank = card[1:].upper()
            if suit in SUITS and (rank in RANK_LETTERS or rank in ("SB", "HR")):
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
        self.tribute_history.clear()
        self._processed_tribute_keys.clear()
        self._processed_anti_keys.clear()
        self._anti_tribute_pos.clear()
