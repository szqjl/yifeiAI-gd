# -*- coding: utf-8 -*-
"""
GUA-285：候选池扩至 actionList 全集 + GUA-075 多候选 + group_members 拆核对齐。

背景（match=6a8e9548 类）：
  GUA-075 primary=最廉 A 拆 SF；actionList 另有 D2；
  竞争层应选 D2 而非 primary A。
"""
import pytest

from src.v.nn.features.grouping_engine import enumerate_groupings
from src.v.nn.play_candidate_competition import (
    _broken_core_from_group_members,
    _core_break_penalty,
    collect_actionlist_press_candidates,
    collect_competition_candidates,
    run_candidate_competition,
)
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _engine_with_plan(hand, cur_rank="2", role="主攻"):
    plan, _ = enumerate_groupings(hand, cur_rank)
    engine = UltimateWinRateEngineV7(player_id=2)
    engine._current_role = role
    engine._card_mask, engine._group_type_map, engine._group_members = plan.to_card_mask()
    engine._active_plan = plan
    engine._best_plan = plan
    engine._dynamic_regroup_enabled = False
    return engine, plan


def test_collect_actionlist_enumerates_all_singles():
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "2", ["D2"]],
        ["Single", "A", ["DA"]],
        ["Single", "R", ["HR"]],
    ]
    recs = collect_actionlist_press_candidates(
        action_list, ["Single", "K", ["HK"]], "2",
    )
    ranks = {r["rank"] for r in recs}
    assert ranks == {"2", "A", "R"}


def _sf_hand_with_scatter_d2():
    """同花顺 10-A（5 张同花）+ 级牌 D2 散牌 + 两炸填充。"""
    sf = ["ST", "S3", "S4", "S5", "SA"]
    hand = sf + [
        "D2", "HK",
        "D6", "S6", "C6", "H6",
        "H9", "D9", "S9", "C9",
    ]
    group_members = {
        0: list(sf),
        1: ["D6", "S6", "C6", "H6"],
        2: ["H9", "D9", "S9", "C9"],
        -1: ["D2", "HK"],
    }
    gid_type = {
        0: "StraightFlush",
        1: "Bomb",
        2: "Bomb",
    }
    card_mask = {}
    for c in sf:
        card_mask[c] = (0, 1.0, 5)
    for c in ["D6", "S6", "C6", "H6"]:
        card_mask[c] = (1, 1.0, 4)
    for c in ["H9", "D9", "S9", "C9"]:
        card_mask[c] = (2, 1.0, 4)
    for c in ["D2", "HK"]:
        card_mask[c] = (-1, 0.0, 1)
    return hand, card_mask, gid_type, group_members


def test_group_members_detects_sf_break_when_mask_scatter():
    """mask 标 scatter 但 group_members 仍绑 SF → GUA-285 仍判拆核。"""
    hand, card_mask, gid_type, group_members = _sf_hand_with_scatter_d2()
    engine = UltimateWinRateEngineV7(player_id=2)
    engine._current_role = "主攻"
    engine._card_mask = dict(card_mask)
    engine._group_type_map = dict(gid_type)
    engine._group_members = dict(group_members)
    # 模拟 mask 滞后：SA 在 mask 中为 scatter
    engine._card_mask["SA"] = (-1, 0.0, 1)

    state = {
        "myPos": 2,
        "greaterPos": 1,
        "greaterAction": ["Single", "K", ["HK"]],
        "handCards": hand,
        "curRank": "2",
        "numofplayers": [10, 12, 15, 8],
        "_group_members": dict(group_members),
        "_group_gid_type_map": dict(gid_type),
    }
    sa_rec = {"type": "Single", "rank": "A", "cards": ["SA"]}
    broken = _broken_core_from_group_members(engine, state, sa_rec)
    assert broken == "StraightFlush"

    penalty, _ = _core_break_penalty(engine, state, sa_rec)
    assert penalty >= 100


def test_competition_picks_d2_over_primary_da_breaking_sf():
    hand, card_mask, gid_type, group_members = _sf_hand_with_scatter_d2()
    engine = UltimateWinRateEngineV7(player_id=2)
    engine._current_role = "主攻"
    engine._card_mask = dict(card_mask)
    engine._group_type_map = dict(gid_type)
    engine._group_members = dict(group_members)
    engine._active_plan = None
    engine._dynamic_regroup_enabled = False

    primary = {"type": "Single", "rank": "A", "cards": ["SA"]}
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "2", ["D2"]],
        ["Single", "A", ["SA"]],
    ]
    state = {
        "myPos": 2,
        "greaterPos": 1,
        "greaterAction": ["Single", "K", ["DK"]],
        "handCards": hand,
        "curRank": "2",
        "numofplayers": [10, 12, 15, 8],
        "_group_members": dict(group_members),
        "_group_gid_type_map": dict(gid_type),
    }

    cands = collect_competition_candidates(
        engine, state, primary, action_list, include_regroup=False,
    )
    sources = {s for s, _ in cands}
    assert "actionlist" in sources

    result = run_candidate_competition(engine, state, action_list, primary, 2)
    assert result.rec is not None
    assert result.rec["type"] == "Single"
    assert result.rec["rank"] == "2"
    assert result.rec["cards"] == ["D2"]
    assert result.picked_source == "actionlist"


def test_competition_picks_scatter_k_over_breaking_q_pair():
    """match=6a8e9548 #16 中局版：HQ 拆 Q 对 vs HK 散牌。"""
    hand = [
        "DT", "HK",
        "D6", "S6", "C6", "D6",
        "S7", "C7", "H7", "S7",
        "DJ", "HJ", "CJ",
        "HQ", "DQ",
    ]
    engine, _ = _engine_with_plan(hand)
    primary = {"type": "Single", "rank": "Q", "cards": ["HQ"]}
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "K", ["HK"]],
        ["Single", "Q", ["HQ"]],
        ["Single", "Q", ["DQ"]],
    ]
    state = {
        "myPos": 2,
        "greaterPos": 1,
        "greaterAction": ["Single", "J", ["CJ"]],
        "handCards": hand,
        "curRank": "2",
        "numofplayers": [10, 12, 15, 8],
        "_group_members": {
            0: ["D6", "S6", "C6", "D6"],
            1: ["S7", "C7", "H7", "S7"],
            2: ["DJ", "HJ", "CJ"],
            3: ["HQ", "DQ"],
        },
        "_group_gid_type_map": {
            0: "Bomb", 1: "Bomb",
            2: "trip_in_three_with_two",
            3: "pair_in_three_with_two",
        },
    }
    engine._group_members = state["_group_members"]
    engine._group_type_map = state["_group_gid_type_map"]

    result = run_candidate_competition(engine, state, action_list, primary, 2)
    assert result.rec is not None
    assert result.rec["type"] == "Single"
    assert result.rec["rank"] == "K"
    assert result.rec["cards"] == ["HK"]


def test_recommend_min_press_all_returns_multiple_singles():
    hand = [
        "DT", "HK", "H7", "D7",
        "D6", "S6", "C6", "H6",
        "H9", "D9", "S9", "C9",
        "H3", "D4", "S5",
    ]
    engine, _ = _engine_with_plan(hand)
    state = {
        "myPos": 2,
        "greaterPos": 1,
        "greaterAction": ["Single", "5", ["H5"]],
        "handCards": hand,
        "curRank": "2",
        "numofplayers": [10, 12, 15, 8],
    }
    all_cands = engine.recommend_min_press_all_candidates(state)
    assert len(all_cands) >= 2
    ranks = {r["rank"] for r in all_cands}
    assert any(r in ranks for r in ("7", "9", "T"))
