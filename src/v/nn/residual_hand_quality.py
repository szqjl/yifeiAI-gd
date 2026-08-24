# -*- coding: utf-8 -*-
"""
V8 动态组牌 — 残手质量评估（纯函数，不接 decide）。

设计真源：docs/guandan-brain/V8-中期压顺灵活性-组牌-动态重组方案.md §3.3.2–3.3.3（v11）
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from src.v.nn.features.grouping_engine import (
    GroupingPlan,
    NORM_MAX_POWER,
    NORM_MAX_ROUNDS,
    _card_rank_value,
    _cards_high_rank_value,
    _is_wild,
    _parse_rank,
    _rank_to_value,
    _score_power,
    determine_score_tier,
    enumerate_groupings,
)

_RANK_T_VALUE = _rank_to_value("T")
_RANK_6_VALUE = _rank_to_value("6")
_RANK_4_VALUE = _rank_to_value("4")
_RANK_6_STRAIGHT_LIMIT = _rank_to_value("6")


@dataclass(frozen=True)
class ResidualMetrics:
    """残手 plan 的质量指标（§3.3.2）。"""

    low_singles: int = 0
    low_pairs: int = 0
    low_trips: int = 0
    low_straights: int = 0
    waste_units: int = 0
    has_anchor: bool = False
    residual_power: int = 0
    residual_rounds: int = 0
    residual_hand_size: int = 0
    plan_score: float = 0.0
    score_tier: str = ""


@dataclass(frozen=True)
class ResidualQualityResult:
    """残手评估完整结果（含地板判定）。"""

    residual_plan: GroupingPlan
    metrics: ResidualMetrics
    residual_floor_veto: bool
    floor_reasons: Tuple[str, ...] = ()
    residual_quality_score: float = 0.0
    residual_waste_penalty: float = 0.0
    residual_structure_penalty: float = 0.0


def residual_hand_after_action(
    hand_cards: Sequence[str],
    action_cards: Sequence[str],
) -> List[str]:
    """打出 action 后的剩余手牌（多重集减法）。"""
    counter = Counter(hand_cards)
    for card in action_cards:
        counter[card] -= 1
        if counter[card] < 0:
            raise ValueError(
                f"action 牌 {card!r} 不在手牌中或张数不足: hand={list(hand_cards)}"
            )
    result: List[str] = []
    for card, count in counter.items():
        result.extend([card] * count)
    return result


def _twt_pair_keys(plan: GroupingPlan) -> set:
    return {tuple(sorted(twt[1])) for twt in plan.three_with_twos}


def compute_has_anchor(plan: GroupingPlan, cur_rank: str) -> bool:
    """续打锚点：残手是否仍能争牌权（§3.3.2 表）。"""
    if plan.bombs or plan.straight_flushes:
        return True
    if plan.three_pairs or plan.steel_plates:
        return True

    for straight in plan.straights:
        if _cards_high_rank_value(straight) >= _RANK_T_VALUE:
            return True

    for twt in plan.three_with_twos:
        trip_rank = _parse_rank(twt[0][0])
        if _rank_to_value(trip_rank) >= _RANK_T_VALUE:
            return True

    for trip in plan.trips:
        trip_rank = _parse_rank(trip[0])
        if _rank_to_value(trip_rank) >= _RANK_T_VALUE:
            return True

    twt_pairs = _twt_pair_keys(plan)
    for pair in plan.pairs:
        if tuple(sorted(pair)) in twt_pairs:
            continue
        pair_rank = _parse_rank(pair[0])
        if _rank_to_value(pair_rank) >= _RANK_T_VALUE:
            return True

    return False


def compute_residual_metrics(
    plan: GroupingPlan,
    cur_rank: str,
    residual_hand_size: int,
) -> ResidualMetrics:
    """从残手 GroupingPlan 计算废牌簇与锚点指标。"""
    wild_set = set(plan.wild_cards)
    twt_pairs = _twt_pair_keys(plan)

    low_singles = 0
    for card in plan.singles:
        if card in wild_set:
            continue
        rank = _parse_rank(card)
        if rank in ("HR", "SB"):
            continue
        if _card_rank_value(card, cur_rank) < _RANK_T_VALUE:
            low_singles += 1

    low_pairs = 0
    for pair in plan.pairs:
        if tuple(sorted(pair)) in twt_pairs:
            continue
        rank = _parse_rank(pair[0])
        if rank in ("HR", "SB"):
            continue
        if _card_rank_value(pair[0], cur_rank) < _RANK_6_VALUE:
            low_pairs += 1

    low_trips = 0
    for twt in plan.three_with_twos:
        if _card_rank_value(twt[0][0], cur_rank) < _RANK_4_VALUE:
            low_trips += 1
    for trip in plan.trips:
        if _card_rank_value(trip[0], cur_rank) < _RANK_4_VALUE:
            low_trips += 1

    low_straights = 0
    for straight in plan.straights:
        if _cards_high_rank_value(straight) <= _RANK_6_STRAIGHT_LIMIT:
            low_straights += 1

    waste_units = low_singles + low_pairs + low_trips
    residual_power = _score_power(plan, cur_rank)
    residual_rounds = plan.num_rounds()
    has_anchor = compute_has_anchor(plan, cur_rank)

    return ResidualMetrics(
        low_singles=low_singles,
        low_pairs=low_pairs,
        low_trips=low_trips,
        low_straights=low_straights,
        waste_units=waste_units,
        has_anchor=has_anchor,
        residual_power=residual_power,
        residual_rounds=residual_rounds,
        residual_hand_size=residual_hand_size,
        plan_score=plan.score,
        score_tier=determine_score_tier(plan.score),
    )


def residual_quality_score(metrics: ResidualMetrics) -> float:
    """§3.3.2 残手质量分（0~1）。"""
    power_term = min(metrics.residual_power / NORM_MAX_POWER, 1.0)
    rounds_term = max(0.0, 1.0 - metrics.residual_rounds / NORM_MAX_ROUNDS)
    anchor_term = 1.0 if metrics.has_anchor else 0.0
    return 0.5 * power_term + 0.3 * rounds_term + 0.2 * anchor_term


def residual_waste_penalty(metrics: ResidualMetrics) -> float:
    """§3.4 废牌簇软惩罚（供后续 exec_weight 使用）。"""
    penalty = (
        0.08 * max(0, metrics.low_singles - 1)
        + 0.06 * metrics.low_pairs
        + 0.05 * metrics.low_trips
    )
    if not metrics.has_anchor:
        penalty *= 1.5
    return penalty


def residual_structure_penalty(metrics: ResidualMetrics) -> float:
    """§3.4 结构断层软惩罚。"""
    quality = residual_quality_score(metrics)
    penalty = max(0.0, 0.35 - quality)
    if metrics.score_tier in ("偏弱", "烂牌"):
        penalty += 0.15
    return penalty


def check_residual_floor_veto(
    metrics: ResidualMetrics,
    *,
    baseline_rounds: Optional[int] = None,
    baseline_power: Optional[int] = None,
) -> Tuple[bool, Tuple[str, ...]]:
    """
    残手质量硬地板 F1–F4（§3.3.3）。

    Returns:
        (veto, reason_codes)  reason_codes 如 ("F1",) 或 ("F2", "F3")
    """
    reasons: List[str] = []

    if metrics.waste_units >= 3 and not metrics.has_anchor:
        reasons.append("F1")

    if (
        metrics.residual_hand_size >= 8
        and metrics.residual_hand_size > 0
        and metrics.waste_units / metrics.residual_hand_size >= 0.55
        and not metrics.has_anchor
    ):
        reasons.append("F2")

    if (
        metrics.residual_power < 1
        and not metrics.has_anchor
        and metrics.low_singles >= 2
    ):
        reasons.append("F3")

    if baseline_rounds is not None and baseline_power is not None:
        if (
            metrics.residual_rounds > baseline_rounds
            and metrics.residual_power <= baseline_power - 2
        ):
            reasons.append("F4")

    return bool(reasons), tuple(reasons)


def evaluate_residual_plan(
    plan: GroupingPlan,
    cur_rank: str,
    residual_hand_size: int,
    *,
    baseline_rounds: Optional[int] = None,
    baseline_power: Optional[int] = None,
) -> ResidualQualityResult:
    """对已有残手 plan 做完整评估。"""
    metrics = compute_residual_metrics(plan, cur_rank, residual_hand_size)
    veto, reasons = check_residual_floor_veto(
        metrics,
        baseline_rounds=baseline_rounds,
        baseline_power=baseline_power,
    )
    quality = residual_quality_score(metrics)
    return ResidualQualityResult(
        residual_plan=plan,
        metrics=metrics,
        residual_floor_veto=veto,
        floor_reasons=reasons,
        residual_quality_score=quality,
        residual_waste_penalty=residual_waste_penalty(metrics),
        residual_structure_penalty=residual_structure_penalty(metrics),
    )


def evaluate_residual_hand(
    hand_cards: Sequence[str],
    cur_rank: str = "2",
    *,
    baseline_rounds: Optional[int] = None,
    baseline_power: Optional[int] = None,
) -> ResidualQualityResult:
    """残手列表 → enumerate_groupings → 质量评估。"""
    cards = list(hand_cards)
    plan, _ = enumerate_groupings(cards, cur_rank)
    return evaluate_residual_plan(
        plan,
        cur_rank,
        len(cards),
        baseline_rounds=baseline_rounds,
        baseline_power=baseline_power,
    )


def evaluate_after_counter_action(
    hand_cards: Sequence[str],
    action_cards: Sequence[str],
    cur_rank: str = "2",
    *,
    baseline_rounds: Optional[int] = None,
    baseline_power: Optional[int] = None,
) -> ResidualQualityResult:
    """打出压牌动作后的残手评估（§3.3 阶段 B 入口）。"""
    residual = residual_hand_after_action(hand_cards, action_cards)
    return evaluate_residual_hand(
        residual,
        cur_rank,
        baseline_rounds=baseline_rounds,
        baseline_power=baseline_power,
    )
