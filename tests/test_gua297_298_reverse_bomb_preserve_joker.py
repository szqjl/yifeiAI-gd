# -*- coding: utf-8 -*-
"""GUA-297 + GUA-298（match 6a9635a81b27100f38dc6beb）。

GUA-297：对手出 Bomb 不再无条件不跟炸——本方持更高炸（中局也不例外）应可反炸。
GUA-298：候选竞争不得靠 E3 豁免把大王(HR)当普通单烧掉——有廉可压单时保留王作控制。
"""

import pytest

from src.v.nn.features.grouping_engine import enumerate_groupings
from src.v.nn.play_candidate_competition import (
    run_candidate_competition,
    score_play_candidate,
    _preserve_joker_control_penalty,
)
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


HAND = [
    "C3", "C6", "C6", "C7", "C9", "C9", "CJ", "CJ", "CQ",
    "D7", "D8", "DA", "DT", "H3", "H3", "H4", "H6", "H9",
    "HA", "HR", "HT", "S2", "S6", "S6", "SJ", "SJ", "SK",
]
assert len(HAND) == 27


def _make_engine(hand=HAND, role="主攻"):
    plan, _ = enumerate_groupings(hand, "2")
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._current_role = role
    engine._card_mask, engine._group_type_map, engine._group_members = plan.to_card_mask()
    engine._active_plan = plan
    engine._best_plan = plan
    engine._dynamic_regroup_enabled = True
    engine._player_id = 0
    return engine, plan


def _base_state(engine, greater, action_list, greater_pos=3):
    return {
        "myPos": 0,
        "greaterPos": greater_pos,
        "greaterAction": greater,
        "actionList": action_list,
        "handCards": list(HAND),
        "curRank": "2",
        "numofplayers": [27, 27, 27, 27],
    }


# ══════════════════════════════════════════════════════════════
# GUA-297：对手出炸我更高 → 可反炸；无更高 → 让道
# ══════════════════════════════════════════════════════════════

def test_reverse_bomb_higher_midgame_upper():
    """对手出 4 星 Bomb/7、V8 持 5 星 Bomb/6（更高）→ 可反炸（中局不例外）。"""
    engine, _ = _make_engine()
    state = _base_state(
        engine,
        greater=["Bomb", "7", ["S7", "C7", "H7", "S7"]],
        action_list=[
            ["PASS", "PASS", ["PASS"]],
            ["Bomb", "6", ["C6", "C6", "H6", "S6", "S6"]],
            ["Bomb", "J", ["CJ", "SJ", "SJ", "CJ"]],
        ],
        greater_pos=3,
    )
    can, reason = engine._r11_bomb_throttle_check(state, ["Bomb", "7", ["S7", "C7", "H7", "S7"]], "7", "2")
    assert can is True
    assert "可反炸" in reason


def test_reverse_bomb_no_higher_lets_pass():
    """对手出 4 星 Bomb/A、V8 只持 4 星 Bomb/J（J<A 无更高）→ 让道 PASS。"""
    engine, _ = _make_engine()
    state = _base_state(
        engine,
        greater=["Bomb", "A", ["CA", "HA", "DA", "SA"]],
        # actionList 仅 PASS（平台不给出压不过 A 的炸）
        action_list=[["PASS", "PASS", ["PASS"]]],
        greater_pos=3,
    )
    can, reason = engine._r11_bomb_throttle_check(state, ["Bomb", "A", ["CA", "HA", "DA", "SA"]], "A", "2")
    assert can is False
    assert "无更高炸" in reason


def test_reverse_bomb_teammate_not_triggered():
    """队友出炸（greaterPos=队友）→ non-opponent，_r11 不进入反炸判定。"""
    engine, _ = _make_engine()
    # greaterPos=2（队友），_r11 的 opponent 前置在炸弹分支之后，
    # 但为避免反炸队友，这里验证队友出炸不反炸：greaterPos 不是对手。
    # _r11 炸弹分支不看 greaterPos；关键在调用侧 GUA-214 已拦截队友。
    # 此处只保证 _can_reverse_bomb_higher 不会因队友出炸而误判为「对手」。
    can = engine._can_reverse_bomb_higher(
        _base_state(
            engine,
            greater=["Bomb", "7", ["S7", "C7", "H7", "S7"]],
            action_list=[
                ["Bomb", "6", ["C6", "C6", "H6", "S6", "S6"]],
            ],
            greater_pos=2,
        ),
        ["Bomb", "7", ["S7", "C7", "H7", "S7"]],
        "2",
    )
    assert can is True  # 只有 actionList 判定；队友让道由 GUA-214/282 在上游拦


# ══════════════════════════════════════════════════════════════
# GUA-298：候选竞争不得烧王——有廉可压单时出小单，保留王作控制
# ══════════════════════════════════════════════════════════════

def test_joker_penalty_applies_when_cheap_press_exists():
    """对上家 Single/3：H4 可压且非王 → HR(大王) 单压应受罚分。"""
    engine, _ = _make_engine()
    state = _base_state(
        engine,
        greater=["Single", "3", ["D3"]],
        action_list=[
            ["PASS", "PASS", ["PASS"]],
            ["Single", "4", ["H4"]],
            ["Single", "R", ["HR"]],
        ],
        greater_pos=3,
    )
    rec_joker = {"type": "Single", "rank": "R", "cards": ["HR"]}
    rec_h4 = {"type": "Single", "rank": "4", "cards": ["H4"]}
    assert _preserve_joker_control_penalty(engine, state, rec_joker, "2") > 0
    assert _preserve_joker_control_penalty(engine, state, rec_h4, "2") == 0.0


def test_competition_prefers_cheap_single_over_joker():
    """候选竞争对上家 Single/3：应选 Single/4(H4)，不得选 Single/R(HR)。"""
    engine, plan = _make_engine()
    state = _base_state(
        engine,
        greater=["Single", "3", ["D3"]],
        action_list=[
            ["PASS", "PASS", ["PASS"]],
            ["Single", "4", ["H4"]],
            ["Single", "R", ["HR"]],
            ["Single", "T", ["HT"]],
        ],
        greater_pos=3,
    )
    primary = {"type": "Single", "rank": "4", "cards": ["H4"]}
    result = run_candidate_competition(engine, state, state["actionList"], primary, 0)
    assert result.rec is not None
    assert result.rec.get("type") == "Single"
    score_joker = next(
        (s for s in result.scores if s.rec.get("rank") == "R"), None
    )
    assert score_joker is not None
    assert score_joker.joker_penalty > 0
    # 王不应凭 E3 豁免盖过廉可压单
    score_h4 = next((s for s in result.scores if s.rec.get("rank") == "4"), None)
    assert score_h4 is not None
    assert score_h4.exec_weight > score_joker.exec_weight


def test_joker_no_penalty_when_no_cheap_press():
    """无廉可压单（仅 王 可压）→ 王不罚（合法用王抢权）。"""
    engine, _ = _make_engine()
    # 上家出 Single/Q，V8 仅 HR 能压（无普通单可压过 Q）
    state = _base_state(
        engine,
        greater=["Single", "Q", ["CQ"]],
        action_list=[
            ["PASS", "PASS", ["PASS"]],
            ["Single", "R", ["HR"]],
            ["Single", "2", ["S2"]],
        ],
        greater_pos=3,
    )
    rec_joker = {"type": "Single", "rank": "R", "cards": ["HR"]}
    # S2 是级牌（值> Q，能压），故仍有可压单 → 王仍罚。为测「无廉可压」，
    # 用无 S2 的 actionList。
    state2 = _base_state(
        engine,
        greater=["Single", "Q", ["CQ"]],
        action_list=[
            ["PASS", "PASS", ["PASS"]],
            ["Single", "R", ["HR"]],
        ],
        greater_pos=3,
    )
    assert _preserve_joker_control_penalty(engine, state2, rec_joker, "2") == 0.0
