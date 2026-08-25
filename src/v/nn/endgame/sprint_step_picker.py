# -*- coding: utf-8 -*-
"""GUA-077 P2：残局冲刺步序选择器（记忆门控 + play_sequence）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

from src.v.nn.features.sprint_belief import SprintBelief

STRUCTURED_LEAD_TYPES = frozenset({
    "ThreeWithTwo",
    "TwoTrips",
    "ThreePair",
    "Straight",
    "StraightFlush",
    "Trips",
    "Pair",
})


def _step_from_raw(raw: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
    if hasattr(raw, "to_dict"):
        return raw.to_dict()
    if isinstance(raw, dict):
        return raw
    return {
        "action_type": getattr(raw, "action_type", ""),
        "target_rank": getattr(raw, "target_rank", ""),
        "step_role": getattr(raw, "step_role", "lead"),
        "cards_hint": getattr(raw, "cards_hint", None),
    }


def _normalize_rank(rank: str) -> str:
    r = str(rank or "").strip().upper()
    if r in ("B", "SB"):
        return "SB"
    if r in ("R", "HR"):
        return "HR"
    if r == "10":
        return "T"
    return r


def _action_matches_step(
    action: List,
    step: Dict[str, Any],
    cur_rank: str,
) -> bool:
    if not isinstance(action, list) or len(action) < 2:
        return False
    at = str(action[0] or "")
    if at != str(step.get("action_type") or ""):
        return False
    act_rank = _normalize_rank(str(action[1] or ""))
    step_rank = _normalize_rank(str(step.get("target_rank") or ""))
    if act_rank == step_rank:
        return True
    # 顺子/同花顺 rank 字段可能为最高张，cards_hint 精确匹配兜底
    hint = step.get("cards_hint") or []
    if hint and len(action) >= 3 and isinstance(action[2], list):
        return sorted(str(c) for c in action[2]) == sorted(str(c) for c in hint)
    return False


def _apply_belief_reorder(
    sequence: List[Dict[str, Any]],
    belief: SprintBelief,
) -> List[Dict[str, Any]]:
    """按 MEM-M07 信念调整前两步顺序（末段 TWT vs 单）。"""
    if len(sequence) < 2:
        return sequence

    first, second = sequence[0], sequence[1]
    a_type = str(first.get("action_type") or "")
    b_type = str(second.get("action_type") or "")

    # GUA-110 / GUA-273：敌报单 → 先整牌
    if belief.enemy_any_remaining_eq_1 and b_type in STRUCTURED_LEAD_TYPES:
        return [second, first]

    if belief.enemy_min_remaining == 1 and b_type == "ThreeWithTwo":
        return [second, first]

    # GUA-238：敌 TWT 弱点 → 先 TWT
    if b_type == "ThreeWithTwo" and any(belief.enemy_twt_unlikely.values()):
        return [second, first]

    if a_type == "Single" and b_type == "ThreeWithTwo":
        probe_rank = _normalize_rank(str(first.get("target_rank") or ""))
        trip_rank = _normalize_rank(str(second.get("target_rank") or ""))
        field_max = belief.my_single_is_field_max.get(probe_rank, False)
        twt_safe = not belief.any_enemy_can_beat_twt.get(trip_rank, True)
        if field_max:
            return [first, second]
        if twt_safe:
            return [second, first]

    return sequence


def try_soft_lead_from_play_sequence(
    engine: Any,
    game_state: Dict[str, Any],
    cur_rank: str,
) -> Optional[Dict[str, Any]]:
    """GUA-077 P3：中局（手牌>10 且 num_rounds≤3）领出软引导 play_sequence 首步。

    命中 actionList 即返回推荐 dict；校验失败返回 None 交 GUA-116 原链。
    """
    hand_cards = list(game_state.get("handCards") or [])
    if len(hand_cards) <= 10:
        return None

    plan = getattr(engine, "_active_plan", None)
    if plan is not None and plan.num_rounds() > 3:
        return None

    seq_raw = list(game_state.get("_active_play_sequence") or [])
    if not seq_raw and plan is not None:
        seq_raw = [
            s.to_dict() if hasattr(s, "to_dict") else s
            for s in (plan.play_sequence or [])
        ]
    if not seq_raw:
        return None

    steps = [_step_from_raw(s) for s in seq_raw]
    belief_raw = game_state.get("_sprint_belief")
    if belief_raw is not None and len(steps) >= 2:
        belief = SprintStepPicker._coerce_belief(belief_raw)
        if belief is not None:
            steps = _apply_belief_reorder(steps, belief)

    step = steps[0]
    action_list = game_state.get("actionList") or []
    if not action_list:
        return None

    card_mask = getattr(engine, "_card_mask", None) or {}
    group_type_map = getattr(engine, "_group_type_map", None) or {}
    group_members = getattr(engine, "_group_members", None)

    for action in action_list:
        at = str(action[0] or "") if isinstance(action, list) else ""
        if at in ("PASS", ""):
            continue
        if not _action_matches_step(action, step, cur_rank):
            continue
        rec = {
            "type": at,
            "rank": str(action[1]) if len(action) > 1 else "",
            "cards": list(action[2]) if len(action) > 2 and isinstance(action[2], list) else [],
            "intent": "gua077_soft_lead",
        }
        if card_mask and hasattr(engine, "_get_broken_core_type"):
            broken = engine._get_broken_core_type(
                [rec["type"], rec["rank"], rec["cards"]],
                card_mask,
                group_type_map,
                group_members,
            )
            if broken in ("Bomb", "StraightFlush"):
                continue
        return rec
    return None


class SprintStepPicker:
    """消费 play_sequence + SprintBelief，在 Q0 领出时选首步。"""

    def pick_lead_step(
        self,
        game_state: Dict[str, Any],
        play_sequence: List[Union[Dict[str, Any], Any]],
        sprint_belief: Optional[Union[SprintBelief, Dict[str, Any]]],
        action_list: List,
        *,
        is_my_turn: bool = True,
    ) -> Optional[Tuple[int, List]]:
        if not is_my_turn or not play_sequence or not action_list:
            return None

        steps = [_step_from_raw(s) for s in play_sequence if s is not None]
        if not steps:
            return None

        belief = self._coerce_belief(sprint_belief)
        if belief is not None and len(steps) >= 2:
            steps = _apply_belief_reorder(steps, belief)

        cur_rank = str(game_state.get("curRank", "2"))
        for step in steps:
            for idx, action in enumerate(action_list):
                if _action_matches_step(action, step, cur_rank):
                    return idx, action
        return None

    @staticmethod
    def _coerce_belief(
        raw: Optional[Union[SprintBelief, Dict[str, Any]]],
    ) -> Optional[SprintBelief]:
        if raw is None:
            return None
        if isinstance(raw, SprintBelief):
            return raw
        if not isinstance(raw, dict):
            return None
        return SprintBelief(
            my_single_is_field_max=dict(raw.get("my_single_is_field_max") or {}),
            enemy_can_beat_single={
                int(k): dict(v)
                for k, v in (raw.get("enemy_can_beat_single") or {}).items()
            },
            probe_single_rank=raw.get("probe_single_rank"),
            enemy_can_beat_twt={
                int(k): dict(v)
                for k, v in (raw.get("enemy_can_beat_twt") or {}).items()
            },
            any_enemy_can_beat_twt=dict(raw.get("any_enemy_can_beat_twt") or {}),
            enemy_twt_unlikely={
                int(k): bool(v)
                for k, v in (raw.get("enemy_twt_unlikely") or {}).items()
            },
            enemy_bomb_risk_on_lead=float(
                raw.get("enemy_bomb_risk_on_lead", 1.0) or 1.0
            ),
            my_bomb_beats_field=bool(raw.get("my_bomb_beats_field")),
            enemy_min_remaining=int(raw.get("enemy_min_remaining", 27) or 27),
            enemy_any_remaining_eq_1=bool(
                raw.get("enemy_any_remaining_eq_1", False)
            ),
        )
