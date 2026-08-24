# -*- coding: utf-8 -*-
"""GUA-268：跟压敌方普通单张时，手中有能压的小王/大王，用王控单，禁止同花顺/炸弹开炸。

match=6a8c3e2c 1号（p0 Local AI）跟 4 号 Single/5（D5）打出 StraightFlush/A
（CA,C2,C3,C4,C5）。当时手牌 26 含 SB×2 + 两把同花顺。用户定音：这是败笔，
两个小王应发挥控单作用，同花顺留作火力。

根因链：组牌把 SB 收成对、最廉跟单拆 TT 出 T → P0a 信念门控拦 T →
被当成「无同型」→ R11 第一圈 PASS 或 GUA-102/205 开炸（_recommend_bomb_from_mask
永远先拿同花顺）。
"""

from __future__ import annotations

import logging

from src.communication.botzone_adapter import ActionListGenerator, bz_to_v8_cards
from src.v.nn import UltimateWinRateEngineV7


# match=6a8c3e2c 1号开局手牌（出过 S9 后跟单 5 时的 26 张）
_INIT_P0_BZ = [
    50, 90, 100, 106, 73, 52, 63, 7, 98, 19, 4, 65, 69, 80, 8,
    66, 88, 101, 84, 21, 14, 85, 57, 102, 18, 27, 39,
]


def _hand_after_s9():
    hand = bz_to_v8_cards(_INIT_P0_BZ)
    hand.remove("S9")
    return hand


def _follow_actions(hand, greater, cur_rank="2"):
    return ActionListGenerator(cur_rank=cur_rank).generate_follow_actions(
        hand, greater
    )


def _make_engine(*, role="超强主攻"):
    eng = UltimateWinRateEngineV7.__new__(UltimateWinRateEngineV7)
    eng.logger = logging.getLogger("test_gua268")
    eng.player_id = 0
    eng._card_mask = {}
    eng._group_type_map = {0: "StraightFlush", 1: "StraightFlush"}
    eng._group_members = {}
    eng._current_role = role
    eng._match_fail_type_mismatch = 0
    eng._match_fail_rank_mismatch = 0
    eng._match_fail_cards_mismatch = 0
    return eng


def test_decide_uses_sb_not_straightflush_vs_single_five():
    """端到端复现：26 张 + 双 SF + SB×2，跟上家 Single/5 → 出 SB，不出同花顺。"""
    hand = _hand_after_s9()
    greater = ["Single", "5", ["D5"]]
    acts = _follow_actions(hand, greater)
    assert any(a[0] == "Single" and a[2] == ["SB"] for a in acts)
    assert any(a[0] == "StraightFlush" and a[1] == "A" for a in acts)

    engine = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=True)
    gs = {
        "type": "act",
        "stage": "play",
        "myPos": 0,
        "handCards": hand,
        "curRank": "2",
        "greaterPos": 3,
        "greaterAction": greater,
        "actionList": acts,
        "numofplayers": [26, 27, 27, 25],
        "publicInfo": [{"rest": n} for n in [26, 27, 27, 25]],
    }
    idx = engine.decide(gs)
    chosen = acts[idx]
    assert chosen[0] != "StraightFlush", f"不得用同花顺开炸压单 5，实际 {chosen}"
    assert chosen[0] != "Bomb", f"不得用炸弹压单 5，实际 {chosen}"
    assert chosen[0] == "Single", f"应用王控单，实际 {chosen}"
    assert chosen[2] == ["SB"], f"应出小王，实际 {chosen}"


def test_mid_aggressive_skips_bomb_when_sb_beats_single():
    """GUA-205：超强主攻跟敌方 Single/5，actionList 有 SB → 不开炸。"""
    engine = _make_engine()
    engine._recommend_min_press_impl = lambda *a, **k: None
    engine._recommend_max_press_impl = lambda *a, **k: None
    engine._r11_bomb_throttle_check = lambda *a, **k: (True, "test")
    gs = {
        "_belief": {"hand_counts": {0: 26, 1: 27, 2: 27, 3: 25}},
        "_phase_relation": {
            "critical_enemy_seat": 3,
            "teammate_cover_confidence": 0.2,
            "teammate_rear_single_cover_confidence": 0.0,
            "same_type_suppressor_outside": True,
            "enemy_bomb_risk_max": 0.1,
            "sprint_fire_ready": False,
        },
        "myPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Single", "5", ["D5"]],
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["Single", "B", ["SB"]],
            ["StraightFlush", "A", ["CA", "C2", "C3", "C4", "C5"]],
            ["Bomb", "Q", ["SQ", "HQ", "CQ", "H2"]],
        ],
        "handCards": ["SB", "SB", "CA", "C2", "C3", "C4", "C5"],
        "curRank": "2",
    }
    rec = engine._mid_aggressive_bomb_special(
        gs,
        engine._card_mask,
        gs["handCards"],
        "2",
        greater_action=gs["greaterAction"],
        greater_type="Single",
        greater_rank="5",
        teammate_pos=2,
        is_teammate=False,
    )
    assert rec is None, f"有小王能压单 5 时 GUA-205 不应开炸，实际 {rec}"


def test_sprint_fire_skips_bomb_when_sb_beats_single():
    """GUA-102：sprint_fire_ready 时跟 Single/5 有 SB → 不点火开炸。"""
    engine = _make_engine()
    gs = {
        "_phase_relation": {
            "sprint_fire_ready": True,
            "teammate_cover_confidence": 0.2,
        },
        "myPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Single", "5", ["D5"]],
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["Single", "B", ["SB"]],
            ["StraightFlush", "A", ["CA", "C2", "C3", "C4", "C5"]],
        ],
        "handCards": ["SB", "CA", "C2", "C3", "C4", "C5"],
        "curRank": "2",
    }
    rec = engine._maybe_recommend_sprint_fire_bomb(
        gs, engine._card_mask, "2", teammate_pos=2, intent="mid_sprint_fire_bomb",
    )
    assert rec is None, f"有小王能压单时不应 sprint_fire 开炸，实际 {rec}"


def test_rewrite_bomb_rec_to_sb():
    """安全网：推荐已是 StraightFlush 时改写成 Single/SB。"""
    engine = _make_engine()
    gs = {
        "myPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Single", "5", ["D5"]],
        "curRank": "2",
    }
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "B", ["SB"]],
        ["StraightFlush", "A", ["CA", "C2", "C3", "C4", "C5"]],
    ]
    rec = engine._apply_gua268_joker_control_single(
        {"type": "StraightFlush", "rank": "A", "cards": ["CA", "C2", "C3", "C4", "C5"]},
        gs,
        action_list,
    )
    assert rec["type"] == "Single"
    assert rec["cards"] == ["SB"]


def test_sb_does_not_block_bomb_vs_single_hr():
    """GUA-218 回归：greater=大王，SB 压不住 → 仍允许开炸。"""
    engine = _make_engine()
    gs = {
        "myPos": 0,
        "greaterPos": 1,
        "greaterAction": ["Single", "R", ["HR"]],
        "curRank": "2",
    }
    action_list = [
        ["Single", "B", ["SB"]],
        ["Bomb", "K", ["SK", "CK", "DK", "HK"]],
        ["StraightFlush", "8", ["D8", "D9", "DT", "DJ", "DQ"]],
    ]
    rec = engine._apply_gua268_joker_control_single(
        {"type": "Bomb", "rank": "K", "cards": ["SK", "CK", "DK", "HK"]},
        gs,
        action_list,
    )
    assert rec["type"] == "Bomb"
    assert rec["rank"] == "K"


def test_cheap_natural_single_still_preferred_over_joker():
    """有散单 7 能压 5 且 P0a 不拦 → 仍最省压，不必强行出王。"""
    hand = ["S7", "SB", "CA", "C2", "C3", "C4", "C5"]
    card_mask = {c: (-1, 0.0, 1) for c in hand}
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = {}
    engine._group_members = {-1: list(hand)}
    engine._current_role = "超强主攻"
    gs = {
        "myPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Single", "5", ["D5"]],
        "handCards": hand,
        "curRank": "2",
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["Single", "7", ["S7"]],
            ["Single", "B", ["SB"]],
            ["StraightFlush", "A", ["CA", "C2", "C3", "C4", "C5"]],
        ],
        "_belief": {
            "hand_counts": {0: 7, 3: 25},
            "opp_bomb_risks": {3: 0.0},
        },
    }
    rec = engine._recommend_min_press_impl(
        gs, card_mask, gs["greaterAction"], "Single", hand, "2",
        apply_belief_gate=False,
    )
    assert rec is not None
    assert rec["type"] == "Single"
    assert rec["cards"] == ["S7"], f"有散 7 应最省压，实际 {rec}"
