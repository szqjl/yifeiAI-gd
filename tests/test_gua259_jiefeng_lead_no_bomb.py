# -*- coding: utf-8 -*-
"""GUA-259：接风领出禁炸（R10）。

锚点 match `6a87ca4d0fbd680d7c7d795d`（logs/v8_vs_botzone_20260821_114247.log
11:47:51）：队友 P2 出 Pair/2 头游后，跟牌轮 V8 正确 PASS；下一手接风领出
却因 greaterPos 仍为队友(2) → R10 不生效 → 领出 Bomb/8。

修复：must_play 领出时 adapter 将 greaterPos 置 -1，R10 过滤炸弹。
"""

from __future__ import annotations

import asyncio
import json

from src.communication.botzone_adapter import (
    ActionListGenerator,
    BotzoneAdapter,
    BotzoneGameState,
    CardTracker,
    bz_to_v8_cards,
    v8_to_bz_int,
)
from src.v.nn import UltimateWinRateEngineV7
from src.v.nn.guards.v7_guards import (
    _rule_r10_no_lead_bomb,
    get_action_type,
)


def _jiefeng_lead_game_state() -> dict:
    """复现接风领出：手牌 = Bomb/8888 + 散牌（有非炸可选）。"""
    hand = ["H8", "H8", "S8", "S8", "DK", "DT", "HT"]
    gen = ActionListGenerator(cur_rank="2")
    action_list = gen.generate_lead_actions(hand)
    assert any(get_action_type(a) == "Bomb" for a in action_list)
    assert any(
        get_action_type(a) not in ("Bomb", "StraightFlush", "PASS")
        for a in action_list
    )
    return {
        "actionList": action_list,
        "handCards": hand,
        "myPos": 0,
        "curPos": 0,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "stage": "play",
        "greaterPos": -1,
        "greaterAction": ["PASS", "PASS", "PASS"],
        "curAction": ["PASS", "PASS", "PASS"],
        "done": [2],
        "numofplayers": [7, 10, 0, 12],
        "publicInfo": [{"rest": n} for n in [7, 10, 0, 12]],
        "_botzone_mode": True,
        "history": [],
    }


def test_gua259_r10_filters_bomb_when_greater_pos_neg1():
    """自由领出（greaterPos=-1）有非炸选项时 R10 剔炸弹。"""
    actions = [
        ["Single", "K", ["DK"]],
        ["Pair", "T", ["DT", "HT"]],
        ["Bomb", "8", ["H8", "H8", "S8", "S8"]],
    ]
    kept = _rule_r10_no_lead_bomb(actions, greater_pos=-1, my_pos=0)
    assert kept == [0, 1]


def test_gua259_r10_does_not_filter_when_greater_is_teammate():
    """回归：greaterPos=队友 是跟牌，R10 不禁炸。"""
    actions = [
        ["PASS", "PASS", "PASS"],
        ["Bomb", "8", ["H8", "H8", "S8", "S8"]],
    ]
    kept = _rule_r10_no_lead_bomb(actions, greater_pos=2, my_pos=0)
    assert kept == [0, 1]


def test_gua259_adapter_must_play_sets_greater_pos_neg1():
    """adapter must_play 接风：注入引擎的 greaterPos 必须为 -1，且不领出 Bomb/8。"""
    adapter = BotzoneAdapter("t", "k", player_id=0)
    engine = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=True)
    adapter.set_decision_engine(engine)

    hand = ["H8", "H8", "S8", "S8", "DK", "DT", "HT"]
    game = BotzoneGameState(match_id="t", player_id=0)
    game.hand_cards = list(hand)
    game.cur_rank = "2"
    game.self_rank = "2"
    game.oppo_rank = "2"
    bz_ints = [
        v8_to_bz_int(c, deck_offset=0 if i < 4 else 1)
        for i, c in enumerate(hand)
    ]
    game.card_tracker = CardTracker.from_bz_hand(bz_ints)
    adapter.games["t"] = game

    req = {
        "stage": "play",
        "history": [
            {"player": 2, "response": [[6, 59], [6, 59]]},
            {"player": 3, "response": [[], []]},
            {"player": 0, "response": [[], []]},
            {"player": 1, "response": [[], []]},
        ],
        "done": [2],
        "pass_on": -1,
        "global": {"level": "2"},
    }
    game.current_request = req

    captured: dict = {}

    def _capture_decide(gs):
        captured["greaterPos"] = gs.get("greaterPos")
        captured["greaterAction"] = gs.get("greaterAction")
        return engine.decide(gs)

    adapter.decision_engine.decide = _capture_decide  # type: ignore[method-assign]

    loop = asyncio.new_event_loop()
    try:
        resp = loop.run_until_complete(
            adapter._handle_play_decision("t", game, req, use_thread=False)
        )
    finally:
        loop.close()

    assert captured.get("greaterPos") == -1, (
        f"接风 must_play 应 greaterPos=-1，实际 {captured.get('greaterPos')}"
    )
    assert captured.get("greaterAction") == ["PASS", "PASS", "PASS"]

    out = json.loads(resp)
    assert out != [[], []], "接风领出禁止 PASS"
    cards = bz_to_v8_cards(out[0])
    is_bomb8 = (
        len(cards) == 4
        and all(len(c) >= 2 and c[1:] == "8" for c in cards)
    )
    assert not is_bomb8, f"接风领出有非炸可选时不应出 Bomb/8，实际 {cards}"


def test_gua259_decide_jiefeng_lead_prefers_non_bomb():
    """端到端：greaterPos=-1 + 有非炸 → decide 不选 Bomb。"""
    engine = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=True)
    gs = _jiefeng_lead_game_state()
    idx = engine.decide(gs)
    chosen = gs["actionList"][idx]
    assert get_action_type(chosen) not in ("Bomb", "StraightFlush"), (
        f"接风自由领出应非炸，实际 {chosen}"
    )
