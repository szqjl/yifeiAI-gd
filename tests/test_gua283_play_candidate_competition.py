# -*- coding: utf-8 -*-
"""GUA-283：GUA-075 候选竞争 + 出牌前残手前瞻。"""

import pytest

from src.v.nn.features.grouping_engine import enumerate_groupings
from src.v.nn.features.memory_tracker import MemoryTracker
from src.v.nn.play_candidate_competition import (
    collect_competition_candidates,
    run_candidate_competition,
    score_play_candidate,
)
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _make_tracker(my_pos: int = 2) -> MemoryTracker:
    t = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    t.init_from_hand([])
    return t


def test_score_pass_beats_bad_twt_follow_teammate_led():
    """队友领出圈 + 助攻：跟 TWT 残手差 / 拆核差 → PASS 胜出。"""
    # 含多顺 + TWT 潜力；AAA 作三带二主体（非炸核）
    hand = [
        "H3", "D4", "S5", "C6", "D7",
        "H8", "D9", "S9", "C9", "H9",
        "H5", "D5", "S6", "C6", "D6",
        "H7", "D7", "S7", "C7", "H6",
        "HA", "SA", "CA", "D4", "S4", "HR", "C3",
    ]
    assert len(hand) == 27
    plan, _ = enumerate_groupings(hand, "2")
    baseline_power = float(plan.power_score)

    engine = UltimateWinRateEngineV7(player_id=2)
    engine._current_role = "助攻"
    engine._card_mask, engine._group_type_map, engine._group_members = plan.to_card_mask()
    engine._active_plan = plan
    engine._best_plan = plan
    engine._dynamic_regroup_enabled = True

    tracker = _make_tracker(2)
    tracker.teammate_led_current_trick = lambda: True  # type: ignore[method-assign]
    engine._tracker = tracker

    state = {
        "myPos": 2,
        "greaterPos": 1,
        "greaterAction": ["ThreeWithTwo", "6", ["H6", "D6", "S6", "H4", "D4"]],
        "handCards": hand,
        "curRank": "2",
        "numofplayers": [27, 27, 27, 27],
    }

    twt_rec = {
        "type": "ThreeWithTwo",
        "rank": "9",
        "cards": sorted(["H9", "D9", "S9", "D4", "S4"]),
    }
    pass_rec = {"type": "PASS", "rank": "", "cards": []}

    twt_score = score_play_candidate(
        engine, state, "primary", twt_rec,
        baseline_power=baseline_power,
        baseline_rounds=plan.num_rounds(),
    )
    pass_score = score_play_candidate(
        engine, state, "pass", pass_rec,
        baseline_power=baseline_power,
        baseline_rounds=plan.num_rounds(),
    )

    assert twt_score.vetoed or twt_score.power_drop > 0.2 or twt_score.waste_penalty > 0.1
    assert pass_score.exec_weight > twt_score.exec_weight


def test_competition_picks_pass_over_primary(monkeypatch):
    """集成：主推荐 TWT，竞争后改 PASS。"""
    hand = [
        "H3", "D4", "S5", "C6", "D7",
        "H8", "D9", "S9", "C9",
        "H5", "D5", "S5", "C5",
        "H6", "D6", "S6", "C6",
        "H7", "D7", "S7", "C7",
        "HA", "SA", "CA", "D9", "HR", "C3",
    ][:27]
    plan, _ = enumerate_groupings(hand, "2")

    engine = UltimateWinRateEngineV7(player_id=2)
    engine._current_role = "助攻"
    engine._card_mask, engine._group_type_map, engine._group_members = plan.to_card_mask()
    engine._active_plan = plan
    engine._best_plan = plan
    engine._dynamic_regroup_enabled = False

    tracker = _make_tracker(2)
    tracker.teammate_led_current_trick = lambda: True  # type: ignore[method-assign]
    engine._tracker = tracker

    primary = {
        "type": "ThreeWithTwo",
        "rank": "A",
        "cards": sorted(["HA", "SA", "CA", "D9", "S9"]),
    }
    action_list = [
        ["PASS", "", []],
        primary,
    ]

    state = {
        "myPos": 2,
        "greaterPos": 1,
        "greaterAction": ["ThreeWithTwo", "6", ["H6", "D6", "S6", "H4", "D4"]],
        "handCards": hand,
        "curRank": "2",
        "numofplayers": [27, 27, 27, 27],
    }

    monkeypatch.setattr(
        engine, "_match_actionList",
        lambda rec, al: 0 if rec.get("type") == "PASS" else 1,
    )

    result = run_candidate_competition(engine, state, action_list, primary, 1)
    assert result.rec is not None
    assert result.rec["type"] == "PASS"
    assert result.act_index == 0
    assert result.picked_source == "pass"


def test_evaluate_after_counter_uses_pre_play_regroup():
    """出牌前前瞻：evaluate_after_counter_action 对残手重算组牌。"""
    from src.v.nn.residual_hand_quality import evaluate_after_counter_action

    hand = [
        "H3", "D4", "S5", "C6", "D7",
        "H8", "D9", "S9", "C9",
        "H5", "D5", "S5", "C5",
        "H6", "D6", "S6", "C6",
        "H7", "D7", "S7", "C7",
        "HA", "SA", "CA", "D9", "HR", "C3",
    ][:27]
    plan, _ = enumerate_groupings(hand, "2")
    twt_cards = sorted(["HA", "SA", "CA", "D9", "S9"])
    residual = evaluate_after_counter_action(
        hand, twt_cards, "2",
        baseline_power=float(plan.power_score),
        baseline_rounds=plan.num_rounds(),
    )
    assert residual.metrics.residual_hand_size == len(hand) - 5
    assert residual.residual_plan is not None
    assert residual.metrics.residual_power < float(plan.power_score)


def test_e1_teammate_sprint_boosts_press_over_pass():
    """E1：队友 ≤5 张 → teammate_win_gain +0.38，残手罚 ×0.25。"""
    hand = ["H3", "D4", "S5", "C6", "H7", "D7", "H8", "D8", "H9", "D9", "HJ", "DJ"]
    plan, _ = enumerate_groupings(hand, "2")
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._current_role = "主攻"
    engine._card_mask, engine._group_type_map, engine._group_members = plan.to_card_mask()
    engine._active_plan = plan

    state = {
        "myPos": 0,
        "greaterPos": 1,
        "greaterAction": ["Pair", "5", ["H5", "D5"]],
        "handCards": hand,
        "curRank": "2",
        "numofplayers": [27, 27, 4, 27],
    }
    pair_rec = {"type": "Pair", "rank": "7", "cards": ["H7", "D7"]}
    pass_rec = {"type": "PASS", "rank": "", "cards": []}
    base_p = float(plan.power_score)
    base_r = plan.num_rounds()

    pr = score_play_candidate(
        engine, state, "primary", pair_rec,
        baseline_power=base_p, baseline_rounds=base_r,
    )
    pas = score_play_candidate(
        engine, state, "pass", pass_rec,
        baseline_power=base_p, baseline_rounds=base_r,
    )
    assert pr.exemption == "E1"
    assert pr.teammate_gain >= 0.38
    assert not pr.vetoed
    assert pr.exec_weight > pas.exec_weight


def test_e2_enemy_sprint_adds_control_gain():
    """E2：敌 ≤5 且信念无反压 → control_gain +0.22。"""
    from src.v.nn.features.rule_card_counter import RuleCardCounter
    from src.v.nn.play_candidate_competition import _enemy_block_control_boost

    residual_cards = ["H3", "D3", "S5", "C5", "H6", "D7", "S8", "C9", "H9"]
    straight = ["CT", "DT", "HJ", "DJ", "HQ"]
    hand = residual_cards + straight
    engine = UltimateWinRateEngineV7(player_id=0)
    tracker = _make_tracker(0)
    for rank in ["8", "9", "T", "J", "Q", "K", "A"]:
        for suit in ["S", "H", "D", "C"]:
            tracker.record_play(0, [f"{suit}{rank}", "?", [f"{suit}{rank}"]])
            tracker.record_play(1, [f"{suit}{rank}", "?", [f"{suit}{rank}"]])
    tracker.record_play(0, ["HR", "?", ["HR"]])
    tracker.record_play(1, ["HR", "?", ["HR"]])
    tracker.record_play(0, ["SB", "?", ["SB"]])
    tracker.record_play(1, ["SB", "?", ["SB"]])
    engine._tracker = tracker
    engine._card_mask = {c: (-1, 0.0, 1) for c in hand}
    engine._group_type_map = {}
    engine._group_members = {-1: hand}

    state = {
        "myPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Straight", "5", ["C3", "D4", "H5", "S6", "C7"]],
        "handCards": hand,
        "curRank": "2",
        "numofplayers": [27, 27, 27, 4],
    }
    engine._inject_belief_vector(state)
    rec = {"type": "Straight", "rank": "T", "cards": straight}
    counter = RuleCardCounter(tracker)
    assert counter.can_opponent_form_type(3, "Straight", "T", state) is False
    boost = _enemy_block_control_boost(engine, state, rec)
    assert boost == 0.22


def test_competition_skipped_when_endgame_active():
    """残局管线激活时：不经候选竞争，保留 EndgameDecider 决策权。"""
    from src.v.nn.play_candidate_competition import is_competition_enabled

    engine = UltimateWinRateEngineV7(player_id=0)
    state = {
        "myPos": 0,
        "greaterPos": 1,
        "greaterAction": ["Pair", "5", ["H5", "D5"]],
        "handCards": ["H3", "D3", "H5", "D5", "H7", "D7"],
        "curRank": "2",
        "_endgame_context": {"is_active": True},
    }
    assert is_competition_enabled(state, engine) is False

    primary = {"type": "Pair", "rank": "7", "cards": ["H7", "D7"]}
    result = run_candidate_competition(
        engine, state, [["PASS", "", []], primary], primary, 1,
    )
    assert result.picked_source == "endgame_reserved"
    assert result.rec == primary


def test_collect_candidates_includes_pass_and_primary():
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._dynamic_regroup_enabled = False
    state = {
        "myPos": 0,
        "greaterPos": 1,
        "greaterAction": ["Pair", "5", ["H5", "D5"]],
        "handCards": ["H3", "D3", "H5", "D5", "H7", "D7"],
        "curRank": "2",
    }
    primary = {"type": "Pair", "rank": "7", "cards": ["H7", "D7"]}
    cands = collect_competition_candidates(engine, state, primary)
    sources = {s for s, _ in cands}
    assert "pass" in sources
    assert "gua075_primary" in sources
