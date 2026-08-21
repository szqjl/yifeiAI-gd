# -*- coding: utf-8 -*-
"""GUA-075 卡下家分档：强牌顺势 min / 弱牌卡点≈J / 危急 max。

锚点 match 6a87ec25：超强主攻 + H9/CJ/HR 压 Single/7 → 应 H9/CJ 非 HR。
"""

from __future__ import annotations

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _engine_scatter(role: str, singles: list[str]):
    card_mask = {c: (-1, 0.0, 1) for c in singles}
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = {}
    engine._group_members = {}
    engine._current_role = role
    return engine, list(singles)


def _xiajia_single(engine, hand, *, rest: int = 20):
    state = {
        "myPos": 0,
        "greaterPos": 1,
        "greaterAction": ["Single", "7", ["H7"]],
        "handCards": hand,
        "curRank": "2",
        "numofplayers": [len(hand), rest, 20, 20],
        "publicInfo": [{"rest": n} for n in [len(hand), rest, 20, 20]],
    }
    return engine._recommend_max_press_impl(
        state,
        engine._card_mask,
        state["greaterAction"],
        "Single",
        hand,
        "2",
    )


def test_gua075_xiajia_strong_follow_min_not_joker():
    """超强主攻 + 多散单可压 → 顺势最小够压，不出 HR。"""
    engine, hand = _engine_scatter(
        "超强主攻", ["C3", "S5", "H9", "CJ", "SB", "HR"],
    )
    rec = _xiajia_single(engine, hand, rest=20)
    assert rec is not None
    assert rec["cards"][0] != "HR"
    assert rec["cards"][0] in ("H9", "CJ", "S5")  # 最小够压优先 S5? S5>7?
    # curRank=2: S5 value vs H7 — 5 < 7 natural order but level 2 elevates 2
    # H7 natural 7; S5=5 cannot press. H9 and CJ can. min → H9
    assert rec["cards"][0] == "H9"
    assert rec.get("_xiajia_mode") == "顺势"


def test_gua075_xiajia_weak_neck_prefers_j_band():
    """助攻弱牌：卡点优先 9/T/J，非 HR。"""
    engine, hand = _engine_scatter(
        "助攻", ["C5", "H9", "CJ", "HR"],
    )
    rec = _xiajia_single(engine, hand, rest=20)
    assert rec is not None
    assert rec["cards"][0] in ("H9", "CJ")
    assert rec["cards"][0] != "HR"
    assert rec.get("_xiajia_mode") == "卡点"


def test_gua075_xiajia_only_joker_allows_hr():
    """仅 HR 可压 → 允许出王。"""
    engine, hand = _engine_scatter("助攻", ["C3", "C4", "HR"])
    rec = _xiajia_single(engine, hand, rest=20)
    assert rec is not None
    assert rec["cards"] == ["HR"]


def test_gua075_xiajia_critical_rest_allows_max():
    """下家 rest≤5 危急 → 可取最大（HR）。"""
    engine, hand = _engine_scatter(
        "超强主攻", ["H9", "CJ", "HR"],
    )
    rec = _xiajia_single(engine, hand, rest=2)
    assert rec is not None
    assert rec["cards"] == ["HR"]
    assert rec.get("_xiajia_mode") == "危急"


def test_gua075_xiajia_recommend_play_logs_follow():
    """端到端 _recommend_play：超强主攻卡下家不出 HR。"""
    singles = ["C3", "S5", "H9", "CJ", "SB", "HR"]
    engine, hand = _engine_scatter("超强主攻", singles)
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "9", ["H9"]],
        ["Single", "J", ["CJ"]],
        ["Single", "B", ["SB"]],
        ["Single", "R", ["HR"]],
    ]
    gs = {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 1,
        "greaterAction": ["Single", "7", ["H7"]],
        "handCards": hand,
        "curRank": "2",
        "numofplayers": [6, 20, 20, 20],
        "_current_stage": "stage_1",
    }
    rec = engine._recommend_play(gs, action_list)
    assert rec is not None
    assert rec.get("type") == "Single"
    assert rec.get("cards") != ["HR"]
    assert rec.get("cards") == ["H9"]
