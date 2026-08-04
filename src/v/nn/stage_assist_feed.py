# -*- coding: utf-8 -*-
"""
GUA-117：助攻 / 超弱 自由领出选牌器。

与 EndgameDecider Q2 共用 assist_prefer_table + pick_assist_feed_by_prefer，避免双规。
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from src.v.nn.assist_prefer_table import assist_prefer_for, assist_is_close
from src.v.nn.endgame.endgame_decide import (
    action_list_item_to_feed_recommendation,
    pick_assist_feed_by_prefer,
)

if TYPE_CHECKING:
    from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _teammate_remaining(game_state: Dict[str, Any], teammate_pos: int) -> int:
    belief = game_state.get("_belief") or {}
    hand_counts = belief.get("hand_counts") or game_state.get("numofplayers") or []
    if isinstance(hand_counts, dict):
        try:
            return int(hand_counts.get(teammate_pos, 27))
        except (TypeError, ValueError):
            return 27
    if isinstance(hand_counts, list) and teammate_pos < len(hand_counts):
        try:
            return int(hand_counts[teammate_pos])
        except (TypeError, ValueError):
            return 27
    return 27


def _resolve_assist_prefer(game_state: Dict[str, Any], teammate_rest: int) -> List[str]:
    ec = game_state.get("_endgame_context") or {}
    teammate = ec.get("teammate") or {}
    if teammate.get("remaining") == teammate_rest:
        prefer = teammate.get("assist_prefer")
        if prefer is not None:
            return list(prefer)
    return assist_prefer_for(teammate_rest)


def _effective_stage(current_stage: str) -> str:
    if current_stage == "stage_0":
        return "stage_1"
    return current_stage


def _feed_from_prefer(
    game_state: Dict[str, Any],
    action_list: Optional[List],
    teammate_rest: int,
    intent: str,
    *,
    rank_map: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    prefer = _resolve_assist_prefer(game_state, teammate_rest)
    if not prefer or not action_list:
        return None
    picked = pick_assist_feed_by_prefer(game_state, action_list, prefer)
    if not picked:
        return None
    _, action = picked
    return action_list_item_to_feed_recommendation(
        action, intent, rank_map=rank_map,
    )


def _feed_stage1_open(
    engine: "UltimateWinRateEngineV7",
    game_state: Dict[str, Any],
    card_mask: Dict[str, tuple],
    hand_cards: List[str],
    cur_rank: str,
) -> Optional[Dict[str, Any]]:
    """1.1：10 点以下最小对（禁级牌对）；6–10 中单；再无则点数序第二小散单（禁级牌单）。"""
    from src.v.nn.guards.v7_guards import CARD_RANK_ORDER, get_card_rank, get_card_value

    def _prank(internal_rank: str) -> str:
        return engine.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

    def _pip_order(card: str) -> int:
        return CARD_RANK_ORDER.get(get_card_rank(str(card)), 99)

    def _is_level_pip(card: str) -> bool:
        """curRank 对应四花色均为级牌（牌力 > A）；S1 首发禁止。"""
        return get_card_rank(str(card)) == cur_rank

    rank_map = engine.INTERNAL_TO_PLATFORM_RANK

    groups = engine._build_group_index(card_mask)
    group_type_map = engine._group_type_map or {}
    group_members = engine._group_members or None
    protected_core = frozenset(("Bomb", "StraightFlush", "straight"))

    def _single_breaks_protected_core(card: str) -> bool:
        rank = _prank(get_card_rank(str(card)))
        broken = engine._get_broken_core_type(
            ["Single", rank, [str(card)]],
            card_mask,
            group_type_map,
            group_members,
        )
        return broken in protected_core

    def _opening_value(card: str) -> int:
        return get_card_value(str(card), cur_rank)

    pair_groups = []
    pair_like_types = ("pair", "pair_in_three_pair", "pair_in_three_with_two")
    for gid, ginfo in groups.items():
        if ginfo["type"] not in pair_like_types:
            continue
        if ginfo["is_core"] > 0:
            continue
        if len(ginfo["cards"]) < 2:
            continue
        cards = sorted(str(c) for c in ginfo["cards"])[:2]
        pair_rank = get_card_rank(cards[0])
        if pair_rank == cur_rank:
            continue
        pair_pip = _pip_order(cards[0])
        if pair_pip >= CARD_RANK_ORDER["T"]:
            continue
        pair_groups.append((cards, pair_rank))
    pair_groups.sort(key=lambda item: (_pip_order(item[0][0]), item[0]))

    if pair_groups:
        cards, rank = pair_groups[0]
        return {
            "type": "Pair",
            "rank": _prank(rank),
            "cards": cards,
            "intent": "assist_feed_s1_small_pair",
        }

    scatter_singles = [
        str(card) for card in engine._scatter_singles(card_mask)
        if not _single_breaks_protected_core(str(card))
        and not _is_level_pip(str(card))
        and get_card_rank(str(card)) not in ("HR", "SB")
    ]
    mid_singles = [
        c for c in scatter_singles
        if CARD_RANK_ORDER["6"] <= _pip_order(c) <= CARD_RANK_ORDER["T"]
    ]
    mid_singles.sort(key=lambda c: (_pip_order(c), str(c)))
    if mid_singles:
        card = mid_singles[0]
        return {
            "type": "Single",
            "rank": _prank(get_card_rank(card)),
            "cards": [card],
            "intent": "assist_feed_s1_mid_single",
        }

    scatter_singles.sort(key=lambda c: (_pip_order(c), str(c)))
    if len(scatter_singles) >= 2:
        # 第二小 > Q 则出第一小（守大不破）；对方剩 1 张时保持原逻辑
        enemy_one_left = False
        numofplayers = game_state.get("numofplayers") or []
        if numofplayers and len(numofplayers) == 4:
            my_pos = int(game_state.get("myPos", 0))
            teammate_pos = (my_pos + 2) % 4
            for seat in ((my_pos + 1) % 4, (my_pos + 3) % 4):
                rem = numofplayers[seat]
                if isinstance(rem, (int, float)) and int(rem) == 1:
                    enemy_one_left = True
                    break
        second = scatter_singles[1]
        if not enemy_one_left and CARD_RANK_ORDER.get(get_card_rank(second), 99) > CARD_RANK_ORDER["Q"]:
            card = scatter_singles[0]
        else:
            card = second
        return {
            "type": "Single",
            "rank": _prank(get_card_rank(card)),
            "cards": [card],
            "intent": "assist_feed_s1_second_single",
        }
    if len(scatter_singles) == 1:
        card = scatter_singles[0]
        return {
            "type": "Single",
            "rank": _prank(get_card_rank(card)),
            "cards": [card],
            "intent": "assist_feed_s1_second_single",
        }

    return None


_S1_OPENING_BANNED_TYPES = frozenset(
    (
        "Bomb",
        "StraightFlush",
        "Straight",
        "ThreePair",
        "TwoTrips",
        "ThreeWithTwo",
    )
)


def _feed_stage1_fallback(
    action_list: Optional[List],
    cur_rank: str,
    *,
    rank_map: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    S1-×（Q4）：自由领出不可 PASS；从 actionList 选 assist 窄 fallback。

    仍禁 1.1 顺/连对/三带/炸；优先非级牌、非 A/王 的 Pair/Single（点数序最小）。
    若无 Pair/Single，再放宽到 Trips；仍无则取首个非禁结构（极端）。
    """
    from src.v.nn.guards.v7_guards import (
        ACTION_TYPE_PAIR,
        ACTION_TYPE_PASS,
        ACTION_TYPE_SINGLE,
        ACTION_TYPE_TRIPS,
        CARD_RANK_ORDER,
        get_action_rank,
        get_action_type,
        get_card_rank,
    )

    if not action_list:
        return None

    def _rank_pip(rank: Optional[str]) -> int:
        if not rank or rank in ("HR", "R", "SB", "B"):
            return 99
        return CARD_RANK_ORDER.get(rank, 99)

    def _is_joker_rank(rank: Optional[str]) -> bool:
        return rank in ("HR", "R", "SB", "B")

    def _pair_allowed(action: List, *, strict: bool) -> bool:
        atype = get_action_type(action)
        if atype != ACTION_TYPE_PAIR:
            return False
        rank = get_action_rank(action)
        if rank == cur_rank:
            return False
        if strict and _rank_pip(rank) >= CARD_RANK_ORDER["A"]:
            return False
        return True

    def _single_allowed(action: List, *, strict: bool) -> bool:
        atype = get_action_type(action)
        if atype != ACTION_TYPE_SINGLE:
            return False
        cards = action[2] if len(action) >= 3 and isinstance(action[2], list) else action
        if not cards:
            return False
        rank = get_card_rank(str(cards[0]))
        if rank == cur_rank or _is_joker_rank(rank):
            return False
        if strict and _rank_pip(rank) >= CARD_RANK_ORDER["A"]:
            return False
        return True

    def _collect(kind: str, *, strict: bool) -> List[List]:
        out: List[List] = []
        checker = _pair_allowed if kind == "pair" else _single_allowed
        for action in action_list:
            if get_action_type(action) in (ACTION_TYPE_PASS, "PASS"):
                continue
            if get_action_type(action) in _S1_OPENING_BANNED_TYPES:
                continue
            if checker(action, strict=strict):
                out.append(action)
        return out

    def _pick_best(actions: List[List], kind: str) -> Optional[List]:
        if not actions:
            return None
        if kind == "pair":
            key_fn = lambda act: (_rank_pip(get_action_rank(act)), str(_get_cards(act)))
        else:
            key_fn = lambda act: (
                _rank_pip(get_card_rank(str(_get_cards(act)[0]))),
                str(_get_cards(act)[0]),
            )
        return min(actions, key=key_fn)

    def _get_cards(action: List) -> List:
        if len(action) >= 3 and isinstance(action[2], list):
            return action[2]
        return list(action)

    for strict in (True, False):
        pair = _pick_best(_collect("pair", strict=strict), "pair")
        if pair:
            return action_list_item_to_feed_recommendation(
                pair, "assist_feed_s1_fallback", rank_map=rank_map,
            )
        single = _pick_best(_collect("single", strict=strict), "single")
        if single:
            return action_list_item_to_feed_recommendation(
                single, "assist_feed_s1_fallback", rank_map=rank_map,
            )

    for action in action_list:
        atype = get_action_type(action)
        if atype in (ACTION_TYPE_PASS, "PASS") or atype in _S1_OPENING_BANNED_TYPES:
            continue
        if atype == ACTION_TYPE_TRIPS:
            return action_list_item_to_feed_recommendation(
                action, "assist_feed_s1_fallback", rank_map=rank_map,
            )

    # 极端：平台必须出牌且仅剩顺/三带等 1.1 禁牌型时仍须领出（不可 PASS）
    _last_resort_types = ("Straight", "ThreeWithTwo", "ThreePair", "TwoTrips")
    last_resort = [
        action for action in action_list
        if get_action_type(action) not in (ACTION_TYPE_PASS, "PASS")
        and get_action_type(action) in _last_resort_types
    ]
    if last_resort:
        picked = min(
            last_resort,
            key=lambda act: (len(_get_cards(act)), str(_get_cards(act))),
        )
        return action_list_item_to_feed_recommendation(
            picked, "assist_feed_s1_fallback", rank_map=rank_map,
        )

    for action in action_list:
        atype = get_action_type(action)
        if atype in (ACTION_TYPE_PASS, "PASS"):
            continue
        if atype in ("Bomb", "StraightFlush"):
            continue
        return action_list_item_to_feed_recommendation(
            action, "assist_feed_s1_fallback", rank_map=rank_map,
        )

    return None


def _feed_mid_match_fallback(
    engine: "UltimateWinRateEngineV7",
    game_state: Dict[str, Any],
    card_mask: Dict[str, tuple],
    hand_cards: List[str],
    cur_rank: str,
) -> Optional[Dict[str, Any]]:
    """2.1 回落（无 GUA-094 时）：最小对 33–77。"""
    rec = _feed_stage1_open(engine, game_state, card_mask, hand_cards, cur_rank)
    if rec:
        rec = dict(rec)
        rec["intent"] = "assist_feed_mid_match_fallback"
        return rec
    return None


def recommend_assist_lead(
    engine: "UltimateWinRateEngineV7",
    game_state: Dict[str, Any],
    card_mask: Dict[str, tuple],
    hand_cards: List[str],
    cur_rank: str,
    current_stage: str,
    teammate_pos: int,
    action_list: Optional[List] = None,
) -> Optional[Dict[str, Any]]:
    """
    助攻 / 超弱 is_lead 领出推荐。

    stage_3 + rest≤5：与 Q2 同源 prefer；rest≥6 → 2.1 回落。
    """
    rank_map = engine.INTERNAL_TO_PLATFORM_RANK
    stage = _effective_stage(current_stage)
    teammate_rest = _teammate_remaining(game_state, teammate_pos)

    if stage == "stage_3":
        if teammate_rest >= 6 or not assist_is_close(teammate_rest):
            return _feed_mid_match_fallback(
                engine, game_state, card_mask, hand_cards, cur_rank,
            )
        prefer_rec = _feed_from_prefer(
            game_state,
            action_list,
            teammate_rest,
            "assist_feed_prefer_q2",
            rank_map=rank_map,
        )
        if prefer_rec:
            return prefer_rec
        return _feed_mid_match_fallback(
            engine, game_state, card_mask, hand_cards, cur_rank,
        )

    if stage == "stage_2":
        return _feed_mid_match_fallback(
            engine, game_state, card_mask, hand_cards, cur_rank,
        )

    if stage == "stage_1":
        rec = _feed_stage1_open(
            engine, game_state, card_mask, hand_cards, cur_rank,
        )
        if rec:
            return rec
        return _feed_stage1_fallback(
            action_list, cur_rank, rank_map=rank_map,
        )

    return None
