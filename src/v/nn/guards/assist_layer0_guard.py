# -*- coding: utf-8 -*-
"""
GUA-117 Layer0：助攻 / 超弱 B1–B6 + 约束 1 让权（117-2a … 117-2g）。

落点：由 v7_guards.filter_action_list 在 role=助攻/超弱 时调用。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, FrozenSet, List, Optional, Set

from src.v.nn.assist_prefer_table import assist_is_close, assist_prefer_for
from src.v.nn.guards.v7_guards import (
    ACTION_TYPE_BOMB,
    ACTION_TYPE_PAIR,
    ACTION_TYPE_PASS,
    ACTION_TYPE_SINGLE,
    ACTION_TYPE_STRAIGHT,
    ACTION_TYPE_STRAIGHT_FLUSH,
    ACTION_TYPE_THREE_PAIR,
    ACTION_TYPE_THREE_WITH_TWO,
    ACTION_TYPE_TRIPS,
    ACTION_TYPE_TWO_TRIPS,
    CARD_RANK_ORDER,
    JOKER_VALUE_CUR_RANK,
    _extract_action_cards,
    get_action_rank,
    get_action_type,
    get_card_rank,
    get_card_value,
)

logger = logging.getLogger("v7_guards")

_ASSIST_ROLES = frozenset(("助攻", "超弱"))

# B2 / S1 首发禁牌型（领出）
_B2_LEAD_BANNED = frozenset(
    (
        ACTION_TYPE_BOMB,
        ACTION_TYPE_STRAIGHT_FLUSH,
        ACTION_TYPE_STRAIGHT,
        ACTION_TYPE_THREE_PAIR,
        ACTION_TYPE_TWO_TRIPS,
    )
)

# B3：无队友记录时仍允许的类型
_B3_ALLOWED_WITHOUT_HISTORY = frozenset(
    (
        ACTION_TYPE_PASS,
        ACTION_TYPE_SINGLE,
        ACTION_TYPE_PAIR,
    )
)

# B2g：队友控牌时须 PASS 的结构牌（非 bomb-like）
_B2G_YIELD_STRUCTURES = frozenset(
    (
        ACTION_TYPE_STRAIGHT,
        ACTION_TYPE_THREE_WITH_TWO,
        ACTION_TYPE_THREE_PAIR,
        ACTION_TYPE_TWO_TRIPS,
        ACTION_TYPE_TRIPS,
    )
)

_CORE_BREAK_TYPES = frozenset(
    (
        "straight",
        "three_with_two",
        "three_pair",
        "two_trips",
        "trip_in_three_with_two",
        "pair_in_three_with_two",
        "pair_in_three_pair",
    )
)


def is_assist_role(game_state: Dict[str, Any]) -> bool:
    role = str(game_state.get("_role") or game_state.get("role") or "")
    return role in _ASSIST_ROLES


def _my_pos(game_state: Dict[str, Any]) -> int:
    return int(game_state.get("myPos", game_state.get("player_id", 0)))


def _teammate_pos(my_pos: int) -> int:
    return (my_pos + 2) % 4


def _teammate_rest(game_state: Dict[str, Any], my_pos: int) -> int:
    teammate = _teammate_pos(my_pos)
    numofplayers = game_state.get("numofplayers") or []
    if isinstance(numofplayers, list) and teammate < len(numofplayers):
        try:
            return int(numofplayers[teammate])
        except (TypeError, ValueError):
            pass
    belief = game_state.get("_belief") or {}
    hand_counts = belief.get("hand_counts") or {}
    if isinstance(hand_counts, dict):
        try:
            return int(hand_counts.get(teammate, 27))
        except (TypeError, ValueError):
            pass
    return 27


def _is_self_lead(game_state: Dict[str, Any], my_pos: int) -> bool:
    greater_pos = game_state.get("greaterPos", -1)
    return greater_pos in (my_pos, -1, None)


def _effective_stage(game_state: Dict[str, Any]) -> str:
    stage = str(game_state.get("_current_stage") or "stage_1")
    if stage == "stage_0":
        return "stage_1"
    return stage


def _teammate_sent_types(game_state: Dict[str, Any], my_pos: int) -> Set[str]:
    tracker = game_state.get("_memory_tracker")
    if tracker is None:
        return set()
    teammate = _teammate_pos(my_pos)
    out: Set[str] = set()
    for entry in getattr(tracker, "play_history", []) or []:
        if entry.get("seat") != teammate:
            continue
        raw = entry.get("action_type") or entry.get("type") or ""
        if not raw:
            continue
        out.add(str(raw))
    return out


def _action_breaks_core_gid(
    action: List,
    game_state: Dict[str, Any],
) -> bool:
    card_mask = game_state.get("_card_mask") or {}
    gid_type_map = game_state.get("_group_gid_type_map") or {}
    if not card_mask or not gid_type_map:
        return False
    cards = _extract_action_cards(action)
    for card in cards:
        meta = card_mask.get(str(card))
        if not meta or not isinstance(meta, (list, tuple)):
            continue
        gid, is_core = meta[0], meta[1]
        if gid < 0:
            continue
        gtype = gid_type_map.get(gid, "")
        if is_core and is_core > 0 and gtype in _CORE_BREAK_TYPES:
            return True
    return False


def _is_high_press_vs_teammate(action: List, cur_rank: str) -> bool:
    atype = get_action_type(action)
    if atype in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
        return True
    if atype == ACTION_TYPE_SINGLE:
        cards = _extract_action_cards(action)
        if not cards:
            return False
        val = get_card_value(str(cards[0]), cur_rank)
        return val >= JOKER_VALUE_CUR_RANK
    if atype == ACTION_TYPE_PAIR:
        rank = get_action_rank(action)
        if rank in ("HR", "SB", "BJ", "RJ"):
            return True
        if rank == cur_rank:
            return True
        pip = CARD_RANK_ORDER.get(rank, 99)
        return pip >= CARD_RANK_ORDER["A"]
    return False


def apply_assist_layer0_exclusions(
    action_list: List[List[str]],
    game_state: Dict[str, Any],
    excluded: Set[int],
) -> None:
    """GUA-117：对 action_list 累积 excluded 下标（原地修改 excluded）。"""
    if not is_assist_role(game_state):
        return

    my_pos = _my_pos(game_state)
    cur_rank = str(game_state.get("curRank", "2"))
    greater_pos = game_state.get("greaterPos", -1)
    cur_pos = game_state.get("curPos", -1)
    teammate = _teammate_pos(my_pos)
    stage = _effective_stage(game_state)
    self_lead = _is_self_lead(game_state, my_pos)
    teammate_rest = _teammate_rest(game_state, my_pos)
    pressing_enemy = (
        greater_pos not in (my_pos, teammate, -1, None)
        and game_state.get("greaterAction")
        and game_state["greaterAction"][0] != "PASS"
    )

    for i, act in enumerate(action_list):
        if i in excluded:
            continue
        atype = get_action_type(act)
        if atype == ACTION_TYPE_PASS:
            continue

        # 117-2a B1：队友控圈 — 禁高点 / 炸压队友
        if greater_pos == teammate:
            if _is_high_press_vs_teammate(act, cur_rank):
                excluded.add(i)
                continue

        # 117-2g 约束 1：队友控牌 — 结构牌让权（补 R07 漏网）
        if greater_pos == teammate and atype in _B2G_YIELD_STRUCTURES:
            excluded.add(i)
            continue

        # 117-2b B2：stage_1/2 自由领出禁炸 / 长结构
        if self_lead and stage in ("stage_1", "stage_2") and atype in _B2_LEAD_BANNED:
            excluded.add(i)
            continue

        # 117-2c B3：禁队友从未出过的牌型（无记录 → 仅 S1 允许型）
        if self_lead and stage in ("stage_1", "stage_2"):
            sent = _teammate_sent_types(game_state, my_pos)
            if not sent:
                if atype not in _B3_ALLOWED_WITHOUT_HISTORY:
                    excluded.add(i)
                    continue
            elif atype not in sent and atype not in (
                ACTION_TYPE_SINGLE,
                ACTION_TYPE_PAIR,
                ACTION_TYPE_PASS,
            ):
                excluded.add(i)
                continue

        # 117-2d B4：前期无谓拆 core 配套（非压敌）
        if stage in ("stage_1", "stage_2") and not pressing_enemy:
            if _action_breaks_core_gid(act, game_state):
                excluded.add(i)
                continue

        # 117-2e B5：无压制需求禁主动开炸
        if self_lead and not pressing_enemy:
            belief = game_state.get("_belief") or {}
            enemy_bomb_risk = 0.0
            phase = game_state.get("_phase_relation") or {}
            try:
                enemy_bomb_risk = float(
                    phase.get("enemy_bomb_risk_max")
                    or belief.get("enemy_bomb_risk_max")
                    or 0.0
                )
            except (TypeError, ValueError):
                enemy_bomb_risk = 0.0
            if atype in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH) and enemy_bomb_risk < 0.45:
                excluded.add(i)
                continue

        # 117-2f B6：close 喂牌仅 allow prefer 型
        if assist_is_close(teammate_rest) and cur_pos == my_pos:
            prefer = assist_prefer_for(teammate_rest)
            if prefer and atype not in prefer:
                excluded.add(i)
                continue

    if excluded:
        logger.debug(
            "GUA-117 assist Layer0: excluded %d actions (role=%s stage=%s)",
            len(excluded),
            game_state.get("_role"),
            stage,
        )
