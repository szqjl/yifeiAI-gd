# -*- coding: utf-8 -*-
"""GUA-229: 下家报单（剩 1 张）时禁止送单——GUA-160/GUA-161 必须让位。

下家（my_pos+1）剩 1 张时，主攻自由领送小单 = 把牌权直接送对手跑。
即使队友恰剩 6 张（GUA-160 队友冲刺）或队友已头游（GUA-161 争双上），
也必须放弃送单，改走其他出牌。
"""

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


HAND = [
    "H2", "C3", "D3", "H4", "S5", "H6",
    "H9", "C9", "CJ", "DJ", "CJ", "CQ", "CK",
]
ACTIONS = [
    ["Single", "2", ["H2"]],
    ["Single", "3", ["D3"]],
    ["Single", "3", ["C3"]],
    ["Straight", "2", ["H2", "D3", "H4", "S5", "H6"]],
    ["Straight", "2", ["H2", "C3", "H4", "S5", "H6"]],
    ["Pair", "J", ["CJ", "DJ"]],
    ["StraightFlush", "9", ["H9", "C9", "CJ", "CQ", "CK"]],
]


def _state(teammate_remaining, next_remaining=16):
    return {
        "actionList": ACTIONS,
        "stage": "play",
        "handCards": HAND,
        "myPos": 0,
        "curPos": -1,
        "curAction": None,
        "greaterPos": -1,
        "greaterAction": None,
        "publicInfo": [
            {"rest": 13}, {"rest": next_remaining},
            {"rest": teammate_remaining}, {"rest": 9},
        ],
        "numofplayers": [13, next_remaining, teammate_remaining, 9],
        "selfRank": "9",
        "oppoRank": "2",
        "curRank": "9",
    }


def _decide(teammate_remaining, next_remaining=16):
    state = _state(teammate_remaining, next_remaining)
    engine = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=True)
    engine._anchor_role = "主攻"
    engine._current_role = "主攻"
    index = engine.decide(state)
    return state["actionList"][index]


def test_gua229_teammate_sprint_sends_single_blocks_when_next_is_declared():
    """GUA-160 队友剩 6 张原本送单3，但下家报单（剩1）→ 禁止送单。"""
    result = _decide(teammate_remaining=6, next_remaining=1)
    # 不得再送 Single 3/2 给下家
    assert not (result[0] == "Single" and result[1] in ("3", "2"))


def test_gua229_teammate_sprint_keeps_sending_when_next_not_declared():
    """下家 16 张不报单 → 原 GUA-160 行为不变（送散单3）。"""
    result = _decide(teammate_remaining=6, next_remaining=16)
    assert result == ["Single", "3", ["D3"]]


def test_gua229_double_second_blocks_when_next_is_declared():
    """GUA-161 队友已头游争双上，下家报单 → 禁止送单。"""
    result = _decide(teammate_remaining=0, next_remaining=1)
    assert not (result[0] == "Single")


def test_gua229_double_second_keeps_when_next_not_declared():
    """下家 14 张不报单 → 原 GUA-161 行为不变。"""
    result = _decide(teammate_remaining=0, next_remaining=14)
    assert result[0] == "Single"