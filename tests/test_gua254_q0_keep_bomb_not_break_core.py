# -*- coding: utf-8 -*-
"""
GUA-254: Q0 保留炸不拆炸弹/核心整牌当散牌压 单元测试

背景（2026-08-20，match=6a86911a0fbd680d7c7c284b）：
  残局 V8 手牌 10 = 四星炸9 [C9,D9,H9,S9] + 四星炸A [SA,SA,CA,HA] + 散 C4,C5，
  敌（player1）出 Single/6。修复前 `_q0_passive_keep_bomb_play_scatter` 收集
  散牌候选时未排除核心整牌成员：压 6 的最小可压单 = C9（拆 9999 炸弹），随后压
  Single/T 又拆 AAAA 出 SA → 双炸被拆成 999+AAA+散，后续 Q1 拆 trips 出单 A
  被 `_action_breaks_core_structure` 拦截 → 只能全 PASS（L643-646 敌 Straight/T
  跑完，scores=[0,2,0,2] V8 队负）。

修复：Q0 保留炸收集散牌候选时，`_action_breaks_core_structure` 判定为拆核心的
  动作跳过（不拆回手炸弹）；GUA-252 豁免（敌≤5 出单）仍放行——此时拆核心出
  最大单压牌是正确夺权打法。修复后无合法散牌 → 返回 None 落回 Q1/炸弹兜底。
"""
import pytest

from src.v.nn.endgame.endgame_decide import EndgameDecider


def build_state(hand_cards=None, greater_action=None, enemy1_remaining=9,
                enemy3_remaining=6, greater_pos=1):
    hand_cards = list(hand_cards or ["C4", "C5", "C9", "D9", "H9", "S9",
                                     "SA", "SA", "CA", "HA"])
    greater_action = greater_action or ["Single", "6", ["S6"]]
    return {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": greater_pos,
        "greaterAction": greater_action,
        "curRank": "2",
        "handCards": hand_cards,
        "numofplayers": [len(hand_cards), enemy1_remaining, 1, enemy3_remaining],
        "_botzone_mode": True,
        "_group_members": {
            -1: ["C4", "C5"],
            0: ["C9", "D9", "H9", "S9"],
            1: ["SA", "SA", "CA", "HA"],
        },
        "_group_gid_type_map": {
            -1: "scatter",
            0: "Bomb",
            1: "Bomb",
        },
    }


def build_ec(enemy1_remaining=9, enemy3_remaining=6, should_sprint=True):
    return {
        "my_pos": 0,
        "cur_pos": 0,
        "cur_rank": "2",
        "numofplayers": [10, enemy1_remaining, 1, enemy3_remaining],
        "enemies": {
            1: {
                "remaining": enemy1_remaining,
                "danger_level": "高",
                "recommended_types": ["最大单张"],
                "banned_types": [],
                "baoshu": {},
            },
            3: {
                "remaining": enemy3_remaining,
                "danger_level": "中",
                "recommended_types": [],
                "banned_types": [],
                "baoshu": {},
            },
        },
        "teammate": {
            "remaining": 1,
            "is_close": True,
            "assist_prefer": ["Single"],
        },
        "self": {
            "remaining": 10,
            "has_two_clean_hands": False,
            "has_bomb": True,
            "should_sprint": should_sprint,
        },
        "finished": [],
    }


def call_q0(gs, ec, action_list=None):
    d = EndgameDecider()
    return d._q0_self_sprint(gs, action_list or list(REPRO_ACTION_LIST), ec)


REPRO_ACTION_LIST = [
    ["PASS", "PASS", "PASS"],
    ["Single", "4", ["C4"]],
    ["Single", "5", ["C5"]],
    ["Single", "9", ["C9"]],
    ["Single", "A", ["SA"]],
    ["Bomb", "9", ["C9", "D9", "H9", "S9"]],
    ["Bomb", "A", ["SA", "SA", "CA", "HA"]],
]


def test_repro_double_bomb_keep_do_not_break_core():
    """复现局：手牌 9999+AAAA+散 C4/C5，敌 Single/6 → 不拆炸弹当散牌压。

    修复前：压 6 的最小可压单 = C9（拆 9999 炸弹）→ 返回 Single/C9 拆核心。
    修复后：C9/SA 均被判拆核心跳过 → 无合法散牌 → 落回炸弹兜底 Bomb/A
    （保留炸弹完整性，不拆核心；后续可由 Q1 正常封锁）。
    """
    gs = build_state()
    ec = build_ec()
    result = call_q0(gs, ec)
    assert result is not None
    idx, act = result
    assert act[0] == "Bomb", \
        f"双炸残局无合法散牌应落回出炸（保留炸弹）；实际出 {act}"
    assert len(act[2]) == 4, f"应保留完整炸弹；实际出 {act}"


def test_keep_bomb_real_scatter_still_used():
    """有真实散牌（非核心成员）能压 greater → 仍用散牌压、保留炸弹。"""
    gs = build_state(
        hand_cards=["C4", "C5", "S8", "C9", "D9", "H9", "S9", "D2"],
        greater_action=["Single", "7", ["S7"]],
    )
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "8", ["S8"]],
        ["Single", "2", ["D2"]],
        ["Bomb", "9", ["C9", "D9", "H9", "S9"]],
    ]
    ec = build_ec(enemy1_remaining=8, enemy3_remaining=6)
    result = call_q0(gs, ec, action_list)
    assert result is not None, "有真实散牌可压时应出散牌"
    idx, act = result
    assert act[0] == "Single", f"应出散牌单张；实际出 {act}"
    assert act[2] == ["S8"], f"应用最小可压散牌 S8；实际出 {act}"


def test_gua252_exemption_not_applied_at_q0():
    """GUA-252 豁免不在此放行：敌≤5 出单拆最大单压牌由 Q1 处理。

    Q0 保留炸职责 = 保住回手炸弹，一律不拆核心（避免用最小可压单 C9 拆炸，
    而非 GUA-252 的最大单 K）；敌≤5 场景落回炸弹兜底，Q1 侧再按豁免放行。
    """
    gs = build_state(
        hand_cards=["C4", "C5", "C9", "D9", "H9", "S9", "SA", "SA", "CA", "HA"],
        greater_action=["Single", "8", ["S8"]],
        enemy1_remaining=4,
    )
    ec = build_ec(enemy1_remaining=4, enemy3_remaining=6)
    result = call_q0(gs, ec)
    # Q0 不拆核心：要么落回炸弹兜底，要么 None；绝不应返回 Single/C9 拆核心
    assert result is None or result[1][0] == "Bomb", \
        f"Q0 保留炸不应拆核心；实际返回 {result}"