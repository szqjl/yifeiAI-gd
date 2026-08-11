# -*- coding: utf-8 -*-
"""GUA-233：跟压时级牌 trips 可拆单/拆对压（match 6a7a9846 实战现场）。

curRank=2 时级牌 2 是除王外最大的单牌/对子/三张。
旧行为：三个级牌 2 被组进 trips，_collect_single_follow_candidates 只遍历
pair 类组，压单时不拆 2（用 J 压单3），压对时也不拆 2，等于废掉级牌资源。
"""

import pytest

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _trips2_engine(cur_rank="2"):
    """三个级牌 2 组进 trips + 一个 J 散单。"""
    card_mask = {
        "S2": (0, 1.0, 3),
        "D2": (0, 1.0, 3),
        "C2": (0, 1.0, 3),
        "HJ": (-1, 0.0, 1),
    }
    group_type_map = {0: "trips"}
    group_members = {0: ["S2", "D2", "C2"]}
    hand = ["S2", "D2", "C2", "HJ"]
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = group_type_map
    engine._group_members = group_members
    engine._current_role = "主攻"
    engine._anchor_role = "主攻"
    return engine, hand


def _press(engine, hand, cur_rank, action):
    gs = {
        "myPos": 0,
        "curPos": 1,
        "greaterPos": 1,
        "greaterAction": action,
        "handCards": hand,
        "curRank": cur_rank,
    }
    return engine._recommend_min_press_impl(
        gs, engine._card_mask, action, action[0], hand, cur_rank
    )


def test_gua233_press_single_uses_rank2_trips_single():
    """对手打单A（J 无法压）→ 必须拆级牌 trips 出单2 压。"""
    engine, hand = _trips2_engine()
    rec = _press(engine, hand, "2", ["Single", "A", ["CA"]])
    assert rec is not None
    assert rec["type"] == "Single"
    assert rec["cards"] == ["S2"]


def test_gua233_press_single_rank2_beats_j():
    """对手单A：级牌 2 是唯一可压单（J < A）。"""
    engine, hand = _trips2_engine()
    rec = _press(engine, hand, "2", ["Single", "A", ["CA"]])
    assert rec["cards"][0] == "S2"


def test_gua233_press_pair_from_trips():
    """对手打对3 → 拆级牌 trips 出对2 压（不能因 trips 锁定而放弃）。"""
    card_mask = {
        "S2": (0, 1.0, 3),
        "D2": (0, 1.0, 3),
        "C2": (0, 1.0, 3),
        "S3": (-1, 0.0, 1),
        "D3": (1, 0.0, 2),
        "C3": (1, 0.0, 2),
    }
    group_type_map = {0: "trips", 1: "pair"}
    group_members = {0: ["S2", "D2", "C2"], 1: ["D3", "C3"]}
    hand = ["S2", "D2", "C2", "S3", "D3", "C3"]
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = group_type_map
    engine._group_members = group_members
    rec = _press(engine, hand, "2", ["Pair", "3", ["D3", "C3"]])
    assert rec is not None
    assert rec["type"] == "Pair"
    assert rec["rank"] == "2"
    assert len(rec["cards"]) == 2
    assert all(c.endswith("2") for c in rec["cards"])


def test_gua233_ordinary_trips_not_broken_for_press():
    """普通 trips（非级牌）不得拆单压——保持既有牌理（GUA-081 只允许整组）。"""
    card_mask = {
        "S5": (0, 1.0, 3),
        "D5": (0, 1.0, 3),
        "C5": (0, 1.0, 3),
        "HJ": (-1, 0.0, 1),
    }
    group_type_map = {0: "trips"}
    group_members = {0: ["S5", "D5", "C5"]}
    hand = ["S5", "D5", "C5", "HJ"]
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = group_type_map
    engine._group_members = group_members
    rec = _press(engine, hand, "2", ["Single", "3", ["S3"]])
    # 普通 trips 不拆单 → 用 J 压（或不压），不得出单5
    if rec is not None:
        assert rec["type"] == "Single"
        assert rec["cards"] == ["HJ"]