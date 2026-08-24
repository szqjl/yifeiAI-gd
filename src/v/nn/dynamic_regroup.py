# -*- coding: utf-8 -*-
"""GUA-234 阶段 D/E：中期喂牌 P 解析 + 针对性重组过滤。

设计真源：docs/guandan-brain/V8-中期压顺灵活性-组牌-动态重组方案.md §8.4–8.5
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.v.nn.residual_hand_quality import (
    ResidualQualityResult,
    evaluate_after_counter_action,
)

# 压对手时的相克扩展（平台牌型名）
COUNTER_TARGET_TYPES: Dict[str, List[str]] = {
    "Straight": ["Straight", "ThreeWithTwo", "Pair"],
    "ThreePair": ["ThreePair", "TwoTrips", "Straight"],
    "TwoTrips": ["TwoTrips", "ThreePair"],
    "ThreeWithTwo": ["ThreeWithTwo"],
    "Pair": ["Pair", "Trips"],
    "Single": ["Single", "Pair"],
    "Trips": ["Trips", "ThreeWithTwo"],
}

FEED_TYPE_ORDER = ("Straight", "ThreeWithTwo", "Trips", "Pair", "Single")


def resolve_feed_prefer_types(
    teammate_rest: int,
    mid_feed_p: Optional[Sequence[str]],
) -> Optional[List[str]]:
    """阶段 D：残局 1–5 走 assist_prefer；中期 ≥6 用 _mid_feed_P。"""
    if 1 <= teammate_rest <= 5:
        from src.v.nn.assist_prefer_table import assist_prefer_for

        return list(assist_prefer_for(teammate_rest))
    if teammate_rest >= 6 and mid_feed_p:
        ordered = [t for t in FEED_TYPE_ORDER if t in mid_feed_p]
        extras = [t for t in mid_feed_p if t not in ordered]
        return ordered + extras
    return None


def collect_regroup_target_types(
    game_state: Dict[str, Any],
    greater_type: str,
) -> List[str]:
    """阶段 E：合并压对手目标型 + 喂队友 P + 对手连续牌型。"""
    targets: List[str] = []
    gt = str(greater_type or "")
    if gt and gt not in ("PASS", "Bomb", "StraightFlush"):
        for t in COUNTER_TARGET_TYPES.get(gt, [gt]):
            if t not in targets:
                targets.append(t)

    for t in game_state.get("_mid_feed_P") or []:
        if t not in targets:
            targets.append(t)

    snap = game_state.get("_mid_feed_snapshot") or {}
    opp_cons = snap.get("opponent_consecutive") or {}
    if opp_cons:
        focus = max(opp_cons, key=lambda k: int(opp_cons.get(k, 0) or 0))
        for t in COUNTER_TARGET_TYPES.get(str(focus), [str(focus)]):
            if t not in targets:
                targets.append(t)
    return targets


def _seat_rest(game_state: Dict[str, Any], seat: int) -> Optional[int]:
    nop = game_state.get("numofplayers") or []
    if isinstance(nop, (list, tuple)) and len(nop) > seat:
        try:
            return int(nop[seat])
        except (TypeError, ValueError):
            return None
    return None


def check_regroup_exemption(
    game_state: Dict[str, Any],
    rec: Dict[str, Any],
    engine: Any,
    residual: ResidualQualityResult,
) -> Optional[str]:
    """残手地板豁免 E1–E4；返回豁免码或 None。"""
    if not residual.residual_floor_veto:
        return "none"

    my_pos = int(game_state.get("myPos", getattr(engine, "player_id", 0)) or 0)
    teammate = (my_pos + 2) % 4
    my_rest = _seat_rest(game_state, my_pos)
    mate_rest = _seat_rest(game_state, teammate)

    if my_rest is not None and my_rest <= 5:
        return "E4"

    if mate_rest is not None and mate_rest <= 5:
        return "E1"

    try:
        greater_pos = int(game_state.get("greaterPos", -1))
    except (TypeError, ValueError):
        greater_pos = -1
    if greater_pos in (-1, my_pos, teammate):
        return None

    press_rank = str(rec.get("rank", ""))
    action_type = str(rec.get("type", ""))
    if greater_pos >= 0 and press_rank and action_type:
        opp_rest = _seat_rest(game_state, greater_pos)
        counter = engine._rule_card_counter_from_state(game_state)
        if (
            opp_rest is not None
            and opp_rest <= 5
            and counter is not None
            and not counter.can_opponent_form_type(
                greater_pos, action_type, press_rank, game_state
            )
        ):
            return "E2"

        belief = game_state.get("_belief") or {}
        opp_risks = belief.get("opp_bomb_risks") or {}
        risk = float(opp_risks.get(greater_pos, 0) or 0)
        if (
            counter is not None
            and not counter.can_opponent_form_type(
                greater_pos, action_type, press_rank, game_state
            )
            and risk < 0.6
        ):
            return "E3"

    return None


def filter_regroup_candidate(
    engine: Any,
    game_state: Dict[str, Any],
    rec: Dict[str, Any],
    hand_cards: Sequence[str],
    cur_rank: str,
) -> Tuple[bool, str]:
    """信念门控 + 禁拆 SF/Bomb + 残手地板（含豁免）。"""
    if not rec:
        return False, "empty"

    if engine._belief_gate_counter_press(game_state, rec):
        return False, "belief_gate"

    action_type = str(rec.get("type", ""))
    press_rank = str(rec.get("rank", ""))
    cards = rec.get("cards") or []
    broken = engine._get_broken_core_type(
        [action_type, press_rank, list(cards)],
        engine._card_mask or {},
        engine._group_type_map or {},
        engine._group_members,
    )
    if broken in ("Bomb", "StraightFlush"):
        return False, "core_bomb_sf"

    try:
        residual = evaluate_after_counter_action(
            hand_cards,
            cards,
            cur_rank,
        )
    except ValueError:
        return False, "invalid_action_cards"

    if residual.residual_floor_veto:
        exempt = check_regroup_exemption(game_state, rec, engine, residual)
        if exempt:
            return True, f"exempt_{exempt}"
        return False, "residual_" + ",".join(residual.floor_reasons)

    return True, "ok"


def dedupe_recommendations(
    candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """按 (type, rank, cards) 去重。"""
    seen: set = set()
    out: List[Dict[str, Any]] = []
    for rec in candidates:
        key = (
            rec.get("type"),
            rec.get("rank"),
            tuple(sorted(str(c) for c in (rec.get("cards") or []))),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(rec)
    return out
