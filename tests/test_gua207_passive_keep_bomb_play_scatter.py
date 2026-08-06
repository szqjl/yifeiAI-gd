# -*- coding: utf-8 -*-
"""
GUA-207: 被动跟压时保留炸弹，先用最小可压散牌（含级牌）压制 单元测试

背景（2026-08-06，match=6a74236927e7bf01db12f002 L493-500）：
  残局 V8 手牌 6 张 = 四星炸5 [D5,H5,H5,C5] + 级牌 D2 + 单 J (SJ)，
  2 号出 Single/Q。修复前 Q0 两手冲刺规划失败（手牌为炸+两散单，非两手）
  → `_select_best_bomb` 盲目出 Bomb/5，被 3 号 Bomb/J 反压，D2/SJ 失去控制权。

修复：镜像 GUA-168 领出侧「先出单试探、炸留作回手」——被动跟压 + greater 为
  散牌型（Single/Pair）+ 手牌 = 炸 + 少量散牌 + 敌未报单 → 先用最小可压散牌
  （级牌优先）压制，炸弹保留作回手冲刺。
"""
import pytest

from src.v.nn.endgame.endgame_decide import EndgameDecider


# 复现局：actionList = PASS + Single(D2 压 Q) + Bomb/5
REPRO_ACTION_LIST = [
    ["PASS", "PASS", "PASS"],
    ["Single", "2", ["D2"]],
    ["Bomb", "5", ["D5", "H5", "H5", "C5"]],
]


def build_state(hand_cards=None, greater_action=None, enemy1_remaining=5,
                enemy3_remaining=4, greater_pos=1):
    hand_cards = list(hand_cards or ["D2", "SJ", "D5", "H5", "H5", "C5"])
    greater_action = greater_action or ["Single", "Q", ["HQ"]]
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
            -1: ["D2", "SJ"],
            0: ["D5", "H5", "H5", "C5"],
        },
        "_group_gid_type_map": {
            -1: "scatter",
            0: "Bomb",
        },
    }


def build_ec(enemy1_remaining=5, enemy3_remaining=4, should_sprint=True):
    return {
        "my_pos": 0,
        "cur_pos": 0,
        "cur_rank": "2",
        "numofplayers": [6, enemy1_remaining, 1, enemy3_remaining],
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
            "remaining": 6,
            "has_two_clean_hands": False,
            "has_bomb": True,
            "should_sprint": should_sprint,
        },
        "finished": [],
    }


def call_q0(gs, ec, action_list=None):
    d = EndgameDecider()
    return d._q0_self_sprint(gs, action_list or list(REPRO_ACTION_LIST), ec)


def test_repro_keep_bomb_play_level2_single():
    """复现局：手牌 Bomb/5+D2+SJ，敌 Single/Q → 出 D2 保留 Bomb（非直接炸）。"""
    gs = build_state()
    ec = build_ec()
    result = call_q0(gs, ec)
    assert result is not None
    idx, act = result
    assert act[0] == "Single", f"应先用级牌单压；实际出 {act}"
    assert act[1] == "2", f"应用级牌 2 压；实际出 {act}"
    assert act[2] == ["D2"], f"应出 D2；实际出 {act}"


def test_pair_greater_keep_bomb_play_pair():
    """greater=Pair，手牌 Bomb + Pair + 单 → 出 Pair 保留炸弹。"""
    gs = build_state(
        hand_cards=["D5", "H5", "H5", "C5", "D9", "H9", "SJ"],
        greater_action=["Pair", "8", ["D8", "H8"]],
    )
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Pair", "9", ["D9", "H9"]],
        ["Bomb", "5", ["D5", "H5", "H5", "C5"]],
    ]
    ec = build_ec(enemy1_remaining=8, enemy3_remaining=7)
    result = call_q0(gs, ec, action_list)
    assert result is not None
    idx, act = result
    assert act[0] == "Pair", f"应出对子压并保留炸；实际出 {act}"
    assert act[2] == ["D9", "H9"], f"应出 99；实际出 {act}"


def test_keep_bomb_not_applicable_when_enemy_baoshu():
    """敌报单（remaining==1）→ 不适用保留炸，落回出炸（返回非散牌或 None）。"""
    gs = build_state(enemy1_remaining=1)
    ec = build_ec(enemy1_remaining=1)
    result = call_q0(gs, ec)
    # 敌报单：不应先用散牌试探（会被直接接走），要么出炸要么 None
    if result is not None:
        idx, act = result
        assert act[0] in ("Bomb", "StraightFlush", "PASS"), \
            f"敌报单时应出炸/不越权；实际出 {act}"


def test_no_playable_scatter_returns_bomb():
    """无散牌能压 greater（仅炸弹）→ 落回出炸弹。"""
    gs = build_state(
        hand_cards=["D5", "H5", "H5", "C5", "SJ", "S9"],
        greater_action=["Single", "T", ["HT"]],
    )
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Bomb", "5", ["D5", "H5", "H5", "C5"]],
    ]
    ec = build_ec(enemy1_remaining=6, enemy3_remaining=5)
    result = call_q0(gs, ec, action_list)
    assert result is not None
    idx, act = result
    assert act[0] == "Bomb", f"SJ/S9 压不过 T，应出炸弹；实际出 {act}"


def test_greater_not_scatter_type_skipped():
    """greater 为整牌型（如 ThreeWithTwo）→ 不触发保留炸，落回两手冲刺/出炸。"""
    gs = build_state(
        hand_cards=["D5", "H5", "H5", "C5", "D2", "SJ"],
        greater_action=["ThreeWithTwo", "4", ["C4", "D4", "H4", "C7", "S7"]],
    )
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "2", ["D2"]],
        ["Bomb", "5", ["D5", "H5", "H5", "C5"]],
    ]
    ec = build_ec(enemy1_remaining=6, enemy3_remaining=5)
    result = call_q0(gs, ec, action_list)
    # greater 非散牌型 → 保留炸分支不触发；两手冲刺失败 → 落回出炸
    assert result is not None
    idx, act = result
    assert act[0] == "Bomb", f"非散牌型 greater 应落回出炸；实际出 {act}"
