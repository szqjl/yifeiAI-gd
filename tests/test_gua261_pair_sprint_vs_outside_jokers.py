# -*- coding: utf-8 -*-
"""
GUA-261: 无王在手 + 外面有大小王 + 手牌=对+单 + 对>K → Q0 领出冲刺出对。

背景（match `6a87fb050fbd680d7c7d9aec`，`logs/v8_vs_botzone_20260821_143712.log`
15:16:00）：V8=player0 手牌 3 = 级牌对 C2C2 + 单 HT，下家亦剩约 3，自由领出。
残局 Q0 冲刺选 `Single/HT` → 被压后拆级牌对烂尾，队负 scores=[0,3,0,3]。
合理打法：出级牌对 2 冲刺。

用户定音：
  - 自己无大小王 + 记忆外面还有王未出 + 剩对+单 + 对>K → 冲刺出对
  - 外面无王 → 可出单，拆级牌对回收（本规则不强制出对）
"""
from src.v.nn.endgame.endgame_decide import EndgameDecider


def _belief_jokers(*, hr_remain=0, hr_mine=0, sb_remain=0, sb_mine=0):
    return {
        "joker_signal": {
            "hr_remain": hr_remain,
            "hr_in_my_hand": hr_mine,
            "sb_remain": sb_remain,
            "sb_in_my_hand": sb_mine,
        }
    }


def build_gs(*, belief=None, hand=None):
    """复现场景：级牌对2 + 单 T，自由领出，下家剩 3。"""
    hand = hand or ["C2", "C2", "HT"]
    return {
        "curRank": "2",
        "handCards": list(hand),
        "myPos": 0,
        "curPos": 0,
        "greaterPos": -1,
        "greaterAction": ["PASS", "PASS", "PASS"],
        "curAction": None,
        "numofplayers": [3, 3, 8, 0],
        "publicInfo": [
            {"rest": 3}, {"rest": 3}, {"rest": 8}, {"rest": 0},
        ],
        "done": [3],
        "stage": "play",
        "selfRank": "2",
        "oppoRank": "2",
        "_botzone_mode": True,
        "_group_type_map": {"pair": 1, "scatter": 1},
        "_group_members": {
            0: {"type": "pair", "cards": ["C2", "C2"]},
            -1: {"type": "scatter", "cards": ["HT"]},
        },
        "_belief": belief if belief is not None else _belief_jokers(
            hr_remain=1, sb_remain=1,
        ),
    }


def build_ec():
    return {
        "my_pos": 0,
        "cur_pos": 0,
        "cur_rank": "2",
        "numofplayers": [3, 3, 8, 0],
        "enemies": {
            1: {
                "remaining": 3, "danger_level": "高",
                "recommended_types": ["Trips", "Pair", "Single"],
                "banned_types": [], "baoshu": {},
            },
            3: {
                "remaining": 0, "danger_level": "低",
                "recommended_types": [], "banned_types": [], "baoshu": {},
            },
        },
        "teammate": {"remaining": 8, "is_close": False, "assist_prefer": []},
        "self": {
            "remaining": 3, "has_two_clean_hands": True,
            "has_bomb": False, "should_sprint": True,
        },
        "finished": [3],
    }


def build_action_list():
    # 与日志一致：Single×2 + Pair×1（先 Single 易被旧排序误选）
    return [
        ["Single", "2", ["C2"]],
        ["Single", "T", ["HT"]],
        ["Pair", "2", ["C2", "C2"]],
    ]


def test_gua261_outside_jokers_high_pair_leads_pair():
    """外面有王 + 级牌对>K → 出 Pair/2，非 Single/T。"""
    gs = build_gs(belief=_belief_jokers(hr_remain=1, sb_remain=1))
    ec = build_ec()
    actions = build_action_list()
    decider = EndgameDecider()
    result = decider._q0_self_sprint(gs, actions, ec)
    assert result is not None
    idx, act = result
    assert act[0] == "Pair"
    assert act[1] == "2"
    assert idx == 2


def test_gua261_no_outside_jokers_does_not_force_pair():
    """外面无王 → GUA-261 分支不命中（可出单拆级牌对回收，不强制冲刺对）。"""
    gs = build_gs(belief=_belief_jokers(hr_remain=0, sb_remain=0))
    actions = build_action_list()
    decider = EndgameDecider()
    assert decider._q0_pair_plus_singles_sprint_lead(
        gs, [(i, a) for i, a in enumerate(actions)], actions,
    ) is None


def test_gua261_pair_not_above_k_no_force():
    """对子=K（不大于 K）→ 不强制冲刺对。"""
    hand = ["CK", "SK", "HT"]
    gs = build_gs(
        hand=hand,
        belief=_belief_jokers(hr_remain=2, sb_remain=2),
    )
    gs["_group_members"] = {
        0: {"type": "pair", "cards": ["CK", "SK"]},
        -1: {"type": "scatter", "cards": ["HT"]},
    }
    actions = [
        ["Single", "K", ["CK"]],
        ["Single", "T", ["HT"]],
        ["Pair", "K", ["CK", "SK"]],
    ]
    decider = EndgameDecider()
    assert decider._q0_pair_plus_singles_sprint_lead(
        gs, list(enumerate(actions)), actions,
    ) is None


def test_gua261_has_joker_in_hand_no_force():
    """自己有王 → 规则不命中。"""
    hand = ["C2", "C2", "HR"]
    gs = build_gs(
        hand=hand,
        belief=_belief_jokers(hr_remain=1, hr_mine=1, sb_remain=1),
    )
    actions = [
        ["Single", "2", ["C2"]],
        ["Single", "R", ["HR"]],
        ["Pair", "2", ["C2", "C2"]],
    ]
    decider = EndgameDecider()
    assert decider._q0_pair_plus_singles_sprint_lead(
        gs, list(enumerate(actions)), actions,
    ) is None


def test_gua261_decide_integration_pair_not_single_t():
    """decide 集成：外面有王时残局管线出 Pair/2。"""
    gs = build_gs(belief=_belief_jokers(hr_remain=1, sb_remain=0))
    ec = build_ec()
    ec["is_active"] = True
    gs["_endgame_context"] = ec
    actions = build_action_list()
    decider = EndgameDecider()
    idx, act = decider.decide(gs, actions)
    assert act is not None
    assert act[0] == "Pair" and act[1] == "2", f"got {act}"
    assert idx == 2
