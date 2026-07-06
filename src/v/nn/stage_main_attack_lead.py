# -*- coding: utf-8 -*-
"""
GUA-116：主攻 stage_1 / stage_2 自由领出 P1–4 链。

真源：docs/guandan-brain/V7-主攻领出-阶段划分设计口径.md
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _effective_stage(current_stage: str) -> str:
    if current_stage == "stage_0":
        return "stage_1"
    return current_stage


def _pip_order(card: str, cur_rank: str) -> int:
    from src.v.nn.guards.v7_guards import CARD_RANK_ORDER, get_card_rank

    rank = get_card_rank(str(card))
    if rank == cur_rank:
        return 99
    if rank in ("HR", "SB", "BJ", "RJ"):
        return 100
    return CARD_RANK_ORDER.get(rank, 99)


def _has_joker(hand_cards: List[str]) -> bool:
    for c in hand_cards:
        r = str(c)
        if r in ("HR", "SB", "BJ", "RJ"):
            return True
        if len(r) >= 2 and r[1] in ("R", "B") and r[0] in "SHDC":
            return True
    return False


def _eligible_p1_singles(
    engine: "UltimateWinRateEngineV7",
    card_mask: Dict[str, tuple],
    hand_cards: List[str],
    cur_rank: str,
    group_type_map: Dict[int, str],
    group_members: Optional[Dict[int, List[str]]],
) -> List[str]:
    """O10：<10 散单（3–9，不含级牌）。"""
    from src.v.nn.guards.v7_guards import CARD_RANK_ORDER, get_card_rank

    protected = frozenset(("bomb", "straight_flush", "straight"))

    def _prank(internal_rank: str) -> str:
        return engine.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

    def _breaks_core(card: str) -> bool:
        broken = engine._get_broken_core_type(
            ["Single", _prank(get_card_rank(str(card))), [str(card)]],
            card_mask,
            group_type_map,
            group_members,
        )
        return broken in protected

    out: List[str] = []
    for card in engine._scatter_singles(card_mask):
        card = str(card)
        if get_card_rank(card) == cur_rank:
            continue
        pip = _pip_order(card, cur_rank)
        if CARD_RANK_ORDER["3"] <= pip <= CARD_RANK_ORDER["9"]:
            if not _breaks_core(card):
                out.append(card)
    out.sort(key=lambda c: (_pip_order(c, cur_rank), c))
    return out


def _pick_p1_second_smallest(eligible: List[str]) -> Optional[str]:
    if len(eligible) >= 2:
        return eligible[1]
    if len(eligible) == 1:
        return eligible[0]
    return None


def _has_k_principle_pair_recapture(
    engine: "UltimateWinRateEngineV7",
    groups: Dict[int, dict],
    cur_rank: str,
) -> bool:
    """§2.4：存在 K 及以上（含级牌）对子作回手。"""
    from src.v.nn.guards.v7_guards import CARD_RANK_ORDER, get_card_rank

    pair_types = ("pair", "pair_in_three_with_two", "pair_in_three_pair")
    for ginfo in groups.values():
        if ginfo["type"] not in pair_types:
            continue
        if len(ginfo["cards"]) < 2:
            continue
        rank = get_card_rank(str(ginfo["cards"][0]))
        if rank == cur_rank:
            return True
        if CARD_RANK_ORDER.get(rank, -1) >= CARD_RANK_ORDER["K"]:
            return True
    return False


def _has_twt_recapture(
    groups: Dict[int, dict],
    lead_gid: Optional[int],
) -> bool:
    """P2：除拟出 TWT 外仍有更大三带二 / 三张结构。"""
    twt_types = ("three_with_two", "trip_in_three_with_two")
    candidates = []
    for gid, ginfo in groups.items():
        if ginfo["type"] not in twt_types:
            continue
        if gid == lead_gid:
            continue
        candidates.append(gid)
    return len(candidates) >= 1


def _has_straight_recapture(
    groups: Dict[int, dict],
    lead_gid: Optional[int],
) -> bool:
    straights = [gid for gid, g in groups.items() if g["type"] == "straight" and gid != lead_gid]
    return len(straights) >= 1


def _count_groups(groups: Dict[int, dict], gtypes: frozenset) -> int:
    return sum(1 for g in groups.values() if g["type"] in gtypes)


def _pick_smallest_twt(
    engine: "UltimateWinRateEngineV7",
    groups: Dict[int, dict],
    cur_rank: str,
) -> Optional[tuple]:
    from src.v.nn.guards.v7_guards import get_card_rank

    def _prank(internal_rank: str) -> str:
        return engine.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

    twt_types = ("three_with_two", "trip_in_three_with_two")
    best = None
    for gid, ginfo in groups.items():
        if ginfo["type"] not in twt_types:
            continue
        if ginfo["is_core"] > 0:
            continue
        cards = sorted(str(c) for c in ginfo["cards"])
        if len(cards) < 5:
            continue
        trip_rank = get_card_rank(cards[0])
        key = (_pip_order(cards[0], cur_rank), cards)
        if best is None or key < best[0]:
            pr = _prank(trip_rank)
            best = (key, gid, "ThreeWithTwo", pr, cards[:5])
    if not best:
        return None
    _, gid, typ, pr, cards = best
    return gid, typ, pr, cards


def _pick_smallest_straight(
    engine: "UltimateWinRateEngineV7",
    groups: Dict[int, dict],
    cur_rank: str,
) -> Optional[tuple]:
    from src.v.nn.guards.v7_guards import get_card_rank

    def _prank(internal_rank: str) -> str:
        return engine.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

    best = None
    for gid, ginfo in groups.items():
        if ginfo["type"] != "straight":
            continue
        if ginfo["is_core"] > 0:
            continue
        cards = sorted(str(c) for c in ginfo["cards"])
        if len(cards) < 5:
            continue
        pr = _prank(get_card_rank(cards[0]))
        key = (_pip_order(cards[0], cur_rank), cards)
        if best is None or key < best[0]:
            best = (key, gid, "Straight", pr, cards[:5])
    if not best:
        return None
    _, gid, typ, pr, cards = best
    return gid, typ, pr, cards


def _pick_p4_small_pair(
    engine: "UltimateWinRateEngineV7",
    groups: Dict[int, dict],
    cur_rank: str,
) -> Optional[Dict[str, Any]]:
    from src.v.nn.guards.v7_guards import CARD_RANK_ORDER, get_card_rank

    def _prank(internal_rank: str) -> str:
        return engine.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

    pair_types = ("pair", "pair_in_three_with_two", "pair_in_three_pair")
    candidates = []
    for ginfo in groups.values():
        if ginfo["type"] not in pair_types:
            continue
        if ginfo["is_core"] > 0:
            continue
        cards = sorted(str(c) for c in ginfo["cards"])[:2]
        rank = get_card_rank(cards[0])
        if rank == cur_rank:
            continue
        pip = CARD_RANK_ORDER.get(rank, 99)
        if pip >= CARD_RANK_ORDER["T"]:
            continue
        candidates.append((pip, cards, rank))
    if not candidates:
        return None
    _, cards, rank = min(candidates, key=lambda x: (x[0], x[1]))
    return {
        "type": "Pair",
        "rank": _prank(rank),
        "cards": cards,
        "intent": "main_p4_small_pair",
    }


def recommend_main_attack_lead(
    engine: "UltimateWinRateEngineV7",
    game_state: Dict[str, Any],
    card_mask: Dict[str, tuple],
    hand_cards: List[str],
    cur_rank: str,
    current_stage: str,
) -> Optional[Dict[str, Any]]:
    """
    主攻 is_lead：P1 → P2 → P3 → P4（命中即返回）。
    stage_0 overlay 按 stage_1 规则；L11/L14 defer 在 stage_1 跳过唯一小 TWT/顺。
    """
    from src.v.nn.guards.v7_guards import CARD_RANK_ORDER, get_card_rank

    def _prank(internal_rank: str) -> str:
        return engine.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

    stage = _effective_stage(current_stage)
    group_type_map = engine._group_type_map or {}
    group_members = engine._group_members or None
    groups = engine._build_group_index(card_mask)

    # ── P1（O10）──
    p1_singles = _eligible_p1_singles(
        engine, card_mask, hand_cards, cur_rank, group_type_map, group_members,
    )
    if _has_joker(hand_cards) or len(p1_singles) >= 2:
        card = _pick_p1_second_smallest(p1_singles)
        if card:
            return {
                "type": "Single",
                "rank": _prank(get_card_rank(card)),
                "cards": [card],
                "intent": "main_p1_second_single",
            }

    twt_types = frozenset(("three_with_two", "trip_in_three_with_two"))
    straight_types = frozenset(("straight",))
    twt_count = _count_groups(groups, twt_types)
    straight_count = _count_groups(groups, straight_types)

    # ── P2 ──
    twt_pick = _pick_smallest_twt(engine, groups, cur_rank)
    if twt_pick:
        gid, typ, pr, cards = twt_pick
        defer = twt_count == 1 and stage == "stage_1"
        if not defer and _has_twt_recapture(groups, gid):
            return {
                "type": typ,
                "rank": pr,
                "cards": cards,
                "intent": "main_p2_three_with_two",
            }

    # ── P3 ──
    st_pick = _pick_smallest_straight(engine, groups, cur_rank)
    if st_pick:
        gid, typ, pr, cards = st_pick
        scatter_n = len(engine._scatter_singles(card_mask))
        defer = straight_count == 1 and stage == "stage_1"
        lonely_ok = scatter_n <= 2
        if not defer and lonely_ok and _has_straight_recapture(groups, gid):
            return {
                "type": typ,
                "rank": pr,
                "cards": cards,
                "intent": "main_p3_short_straight",
            }
        if not defer and lonely_ok and _has_k_principle_pair_recapture(engine, groups, cur_rank):
            return {
                "type": typ,
                "rank": pr,
                "cards": cards,
                "intent": "main_p3_short_straight",
            }

    # 无回手 TWT 仍可能 P2 若多手
    if twt_pick and twt_count >= 2:
        _, typ, pr, cards = twt_pick
        return {
            "type": typ,
            "rank": pr,
            "cards": cards,
            "intent": "main_p2_three_with_two",
        }

    # ── P4 ──
    p4 = _pick_p4_small_pair(engine, groups, cur_rank)
    if p4:
        return p4

    # 兜底：最小非 core 单（仍优于 orphan 高单）
    singles = _eligible_p1_singles(
        engine, card_mask, hand_cards, cur_rank, group_type_map, group_members,
    )
    if singles:
        card = singles[0]
        return {
            "type": "Single",
            "rank": _prank(get_card_rank(card)),
            "cards": [card],
            "intent": "main_p4_fallback_single",
        }

    return None
