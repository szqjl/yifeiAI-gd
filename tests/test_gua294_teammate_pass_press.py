# -*- coding: utf-8 -*-
"""GUA-294：队友已 PASS + 对手控牌 → 弱牌也须压制（防对手白跑牌）。

回归自真实对局 6a9527681b27100f38db373a R10：上家打 Pair/8，队友已 PASS，
V8 手握 Q/K/A 对子可压，修复前 GUA-283 却选 PASS（护核心）。
修复后当 ``_teammate_passed_current_trick`` 为真时应选合法压制，而非 PASS。
"""

import pytest

from src.v.nn.features.grouping_engine import enumerate_groupings
from src.v.nn.features.memory_tracker import MemoryTracker
from src.v.nn.play_candidate_competition import (
    run_candidate_competition,
    score_play_candidate,
)
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


# 弱手：3 组 Q/K/A 高对 + 级牌对 2 + 顺子（与真实对局 V8 结构一致）
WEAK_HAND = [
    "C3", "H4", "H5", "H6", "C7",      # straight
    "H7", "C8", "S9", "DT", "HJ",      # straight
    "C8", "S9", "ST", "DJ", "DQ",      # straight
    "SQ", "HQ",                         # pair_in_three_pair
    "CK", "HK",                         # pair_in_three_pair
    "CA", "SA",                         # pair_in_three_pair
    "S2", "S2",                         # 级牌对
]
assert len(WEAK_HAND) == 23


def _make_engine(hand, role="助攻"):
    plan, _ = enumerate_groupings(hand, "2")
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._current_role = role
    engine._card_mask, engine._group_type_map, engine._group_members = plan.to_card_mask()
    engine._active_plan = plan
    engine._best_plan = plan
    engine._dynamic_regroup_enabled = True
    tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand([])
    engine._tracker = tracker
    return engine, plan


def _base_state(engine):
    return {
        "myPos": 0,
        "greaterPos": 3,          # 上家=对手出牌
        "greaterAction": ["Pair", "8", ["S8", "D8"]],
        "handCards": list(WEAK_HAND),
        "curRank": "2",
        "numofplayers": [22, 20, 20, 21],
    }


def test_score_press_beats_pass_when_teammate_passed():
    """队友已 PASS + 对手 Pair/8 → Pair/K 压制权重高于 PASS。"""
    engine, plan = _make_engine(WEAK_HAND)
    state = _base_state(engine)
    state["_teammate_passed_current_trick"] = True

    press = {
        "type": "Pair",
        "rank": "K",
        "cards": sorted(["CK", "HK"]),
    }
    pass_rec = {"type": "PASS", "rank": "", "cards": []}

    press_score = score_play_candidate(
        engine, state, "primary", press,
        baseline_power=float(plan.power_score),
        baseline_rounds=plan.num_rounds(),
    )
    pass_score = score_play_candidate(
        engine, state, "pass", pass_rec,
        baseline_power=float(plan.power_score),
        baseline_rounds=plan.num_rounds(),
    )

    assert not press_score.vetoed
    assert press_score.exec_weight > 0.0
    assert press_score.exec_weight > pass_score.exec_weight
    assert press_score.control_gain >= 0.32 + 0.5  # GUA-294 加成生效


def test_score_keeps_pass_without_teammate_passed_flag():
    """未设置队友已 PASS 标志（默认）→ 保持旧行为（不强制压）。"""
    engine, plan = _make_engine(WEAK_HAND)
    state = _base_state(engine)  # 不设 _teammate_passed_current_trick

    press = {
        "type": "Pair",
        "rank": "K",
        "cards": sorted(["CK", "HK"]),
    }
    pass_rec = {"type": "PASS", "rank": "", "cards": []}

    press_score = score_play_candidate(
        engine, state, "primary", press,
        baseline_power=float(plan.power_score),
        baseline_rounds=plan.num_rounds(),
    )
    pass_score = score_play_candidate(
        engine, state, "pass", pass_rec,
        baseline_power=float(plan.power_score),
        baseline_rounds=plan.num_rounds(),
    )

    # 无队友已 PASS 情境：压制不加成，PASS 可继续胜出（行为不变）
    assert press_score.control_gain < 0.32 + 0.5
    assert pass_score.exec_weight > press_score.exec_weight


def test_competition_picks_press_when_teammate_passed(monkeypatch):
    """集成：队友已 PASS + 对手 Pair/8 → 竞争选出 Pair 压制而非 PASS。"""
    engine, plan = _make_engine(WEAK_HAND)
    state = _base_state(engine)
    state["_teammate_passed_current_trick"] = True

    primary = {
        "type": "Pair",
        "rank": "Q",
        "cards": sorted(["SQ", "HQ"]),
    }
    action_list = [
        ["PASS", "", []],
        ["Pair", "Q", primary["cards"]],
        ["Pair", "K", sorted(["CK", "HK"])],
        ["Pair", "A", sorted(["CA", "SA"])],
        ["Pair", "2", ["S2", "S2"]],
    ]

    def _match(rec, al):
        if str(rec.get("type")) == "PASS":
            return 0
        for i, a in enumerate(al):
            if a[0] == rec.get("type") and str(a[1]) == str(rec.get("rank")):
                return i
        return -1

    monkeypatch.setattr(engine, "_match_actionList", _match)

    result = run_candidate_competition(engine, state, action_list, primary, 1)
    assert result.rec is not None
    # 应选合法压制（对子，能压 Pair/8），绝不能再 PASS
    assert result.rec["type"] == "Pair"
    assert str(result.rec.get("rank")) in ("Q", "K", "A", "2")
    assert result.picked_source != "pass"
