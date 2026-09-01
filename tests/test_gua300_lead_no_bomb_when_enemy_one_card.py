# -*- coding: utf-8 -*-
"""GUA-300：残局领出 + 敌方报单(剩1张) + 本方持「2炸+2对」时，
`_q1_enemy_critical_lead_special` 不得把炸弹选为封锁整牌 —— 应领对子开发、
保留两把炸作回手/控牌抢头游，而非先出任何炸弹。

match=6a96458f1b27100f38dc76e6（`logs/v8_vs_botzone_20260901_111936.log` L187-189）：
req16 V8=player0 领出 12 张 = Bomb/6(S6,S6,H6,D6) + Bomb/J(HJ,CJ,HJ,H2) + 对7 + 对Q，
上家 p3 报单@1（排队于队友之后，对子圈接不走）。修复前 Q1 封锁敌方 idx=29=Free
（Bomb/J，`get_action_type` 因 H2 逢人配误判为 Free，不被 bomb 过滤排除）→
`_select_enemy_one_locking_structure` 按「多出牌+大牌力」把 Bomb/J 选为锁敌整牌。
修复：safe_structured 过滤改用声明型敏感的 `_is_bomb_like_action` 排除野生配子炸 → 出对7。
"""

from __future__ import annotations

from src.v.nn.endgame.endgame_decide import _is_bomb_like_action, get_action_type
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
from src.communication.botzone_adapter import ActionListGenerator

HAND_12 = [
    "S6", "S6", "H6", "D6",          # G0 Bomb/6
    "HJ", "CJ", "HJ", "H2",          # G1 Bomb/J（H2 逢人配）
    "S7", "S7",                      # G2 对7
    "DQ", "DQ",                      # G3 对Q
]

# 上家 p3 报单@1（排队队友之后），V8 领出 12 张
NUMOF_16 = [12, 13, 12, 1]
PUBLIC_REST_16 = [{"rest": 12}, {"rest": 13}, {"rest": 12}, {"rest": 1}]

BOMB_J_WILD = ["Bomb", "J", ["HJ", "CJ", "HJ", "H2"]]


def _match16_engine():
    """构造与 match 6a96458f req16 完全一致的 engine + game_state。"""
    alg = ActionListGenerator(cur_rank="2")
    action_list = alg.generate_lead_actions(HAND_12)
    engine = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=True)
    gs = {
        "actionList": action_list,
        "handCards": list(HAND_12),
        "myPos": 0,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "stage": "play",
        "curPos": 0,
        "greaterPos": -1,
        "greaterAction": ["PASS", "PASS", "PASS"],
        "curAction": ["PASS", "PASS", "PASS"],
        "done": [],
        "publicInfo": list(PUBLIC_REST_16),
        "_botzone_mode": True,
        "history": [],
    }
    return engine, gs, action_list


def test_wild_bomb_j_get_action_type_is_free_but_is_bomb_like():
    """根因前置：野生 Bomb/J 被 `get_action_type` 误判为 Free → 旧 bomb 过滤漏网；
    `_is_bomb_like_action` 按声明型正确识别为炸弹。"""
    assert get_action_type(BOMB_J_WILD) == "Free"
    assert _is_bomb_like_action(BOMB_J_WILD) is True
    # 纯 4 头炸仍正常识别
    assert _is_bomb_like_action(["Bomb", "6", ["S6", "S6", "H6", "D6"]]) is True


def test_match6a96458f_free_lead_leads_pair_not_bomb():
    """match 6a96458f req16：上家报单@1，V8 领出 12 张（2炸+2对）→
    应出对7（保留两把炸作回手），而非先出任何炸弹（修复前 idx=29 Bomb/J）。"""
    engine, gs, action_list = _match16_engine()
    idx = engine.decide(gs)
    chosen = action_list[idx]
    assert chosen[0] == "Pair", f"应开发对子保留炸弹作回手，实际 {chosen}"
    assert chosen[1] == "7"
    assert sorted(chosen[2]) == sorted(["S7", "S7"])


def test_match6a96458f_keeps_both_bombs_for_reclaim():
    """修复后对7领出，两把炸（Bomb/6 + Bomb/J）仍在手牌中作回手/控牌。"""
    engine, gs, action_list = _match16_engine()
    idx = engine.decide(gs)
    chosen = action_list[idx]
    # 对7消耗 S7×2，两把炸核心牌未被消耗
    played = set(chosen[2])
    hand_after = [c for c in HAND_12 if c not in played]
    from collections import Counter
    cnt = Counter(hand_after)
    assert cnt["S6"] == 2 and cnt["H6"] == 1 and cnt["D6"] == 1
    assert cnt["HJ"] == 2 and cnt["CJ"] == 1 and cnt["H2"] == 1
    assert cnt["DQ"] == 2


def test_unit_q1_critical_lead_prefers_pair_over_wild_bomb():
    """单元：`_q1_enemy_critical_lead_special` safe_structured 过滤排除野生配子炸，
    有可开发对子时选 Pair/7 而非 Bomb/J。"""
    from src.v.nn.endgame.endgame_decide import EndgameDecider
    from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor

    action_list = [
        ["Pair", "7", ["S7", "S7"]],
        ["Pair", "Q", ["DQ", "DQ"]],
        ["Trips", "J", ["HJ", "CJ", "H2"]],
        ["ThreeWithTwo", "7", ["S7", "S7", "H2", "HJ", "CJ"]],
        BOMB_J_WILD,
        ["Bomb", "6", ["S6", "S6", "H6", "D6"]],
    ]
    gs = {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": -1,
        "greaterAction": ["PASS", "PASS", "PASS"],
        "handCards": list(HAND_12),
        "actionList": action_list,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "numofplayers": list(NUMOF_16),
        "_group_members": {
            0: ["S6", "S6", "H6", "D6"],
            1: ["HJ", "CJ", "HJ", "H2"],
            2: ["S7", "S7"],
            3: ["DQ", "DQ"],
        },
        "_group_gid_type_map": {0: "Bomb", 1: "Bomb", 2: "pair", 3: "pair"},
        "_role": "主攻",
    }
    EndgamePreprocessor().preprocess(gs)
    ec = gs["_endgame_context"]
    main_pos, main_enemy = EndgameDecider()._select_main_enemy(ec["enemies"], 0)

    result = EndgameDecider()._q1_enemy_critical_lead_special(
        gs, list(enumerate(action_list)), ec, main_pos, main_enemy,
    )
    assert result is not None
    idx, act = result
    assert act[0] == "Pair"
    assert act[1] == "7"
    assert act[2] == ["S7", "S7"]
    assert idx != 4, "Bomb/J 不应被选为锁敌整牌"
