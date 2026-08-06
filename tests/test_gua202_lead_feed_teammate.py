# -*- coding: utf-8 -*-
"""GUA-202 我方领出轮 + 队友 is_close → 优先按 assist_prefer 送牌（防整牌锁敌抢跑）。

场景：match 6a73e53d27e7bf01db12c646（2026-08-06 09:37:43，日志[255] 领出轮），
V8 手牌 11 = S3 + 888 + 99 + TTT + AA（可出 6 种 Pair），队友 player2 剩 2 张，
敌方 player1 剩 9 张、player3 剩 1 张（报单）。
修复前 Q1 `_q1_enemy_critical_lead_special` 整牌锁敌 → 出 ThreeWithTwo 888+99，未送对子。
修复后 `_q1_lead_feed_teammate_special`（插在 critical_lead_special 之前）→ 出 Pair 送队友。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.endgame.endgame_decide import EndgameDecider


def build_action_list():
    # 复现局 actionList（真实 29 项的子集，覆盖各牌型即可）：
    # 0=PASS, 1-6=Single, 7-12=Pair, 13-14=Trips, 15-22=ThreeWithTwo, 23-24=ThreePair
    return [
        ["PASS", "PASS", "PASS"],
        ["Single", "3", ["S3"]],
        ["Single", "8", ["S8"]],
        ["Single", "9", ["D9"]],
        ["Single", "T", ["DT"]],
        ["Single", "A", ["HA"]],
        ["Single", "A", ["SA"]],
        ["Pair", "8", ["S8", "C8"]],
        ["Pair", "8", ["C8", "C8"]],
        ["Pair", "9", ["D9", "H9"]],        # idx=9: 99
        ["Pair", "T", ["DT", "ST"]],
        ["Pair", "A", ["HA", "SA"]],        # idx=11: AA
        ["Pair", "T", ["DT", "DT"]],
        ["Trips", "8", ["S8", "C8", "C8"]],
        ["Trips", "T", ["DT", "DT", "ST"]],
        ["ThreeWithTwo", "8", ["S8", "C8", "C8", "D9", "H9"]],   # idx=15: 888+99（旧决策）
        ["ThreeWithTwo", "8", ["S8", "C8", "C8", "HA", "SA"]],
        ["ThreeWithTwo", "T", ["DT", "DT", "ST", "D9", "H9"]],
        ["ThreeWithTwo", "T", ["DT", "DT", "ST", "HA", "SA"]],
        ["ThreeWithTwo", "A", ["HA", "SA", "S3", "D9", "H9"]],
        ["ThreePair", "8", ["S8", "C8", "C8", "D9", "H9", "HA", "SA"]],
        ["ThreePair", "T", ["DT", "DT", "ST", "D9", "H9", "HA", "SA"]],
    ]


HAND_REPRO = [
    "S3", "S8", "C8", "C8", "D9", "H9",
    "DT", "DT", "ST", "HA", "SA",
]


def build_state(hand_cards=None, greater_action="LEAD", teammate_remaining=2, enemy1_remaining=9, enemy3_remaining=1):
    """构造复现局。greater_action="LEAD" 表示自由领出（无 greater）。

    _group_members/_group_gid_type_map 按复现局组牌注入（日志 259-263 行）：
      G-1(scatter): S3；G0(trip): S8,C8,C8；G1(pair_in_twt): D9,H9；
      G2(trip): DT,DT,ST；G3(pair_in_twt): HA,SA
    """
    hand_cards = list(hand_cards or HAND_REPRO)
    if greater_action == "LEAD":
        g_action = []
        g_pos = -1
        cur_pos = 0
    else:
        g_action = greater_action
        g_pos = 3
        cur_pos = 0
    game_state = {
        "myPos": 0,
        "curPos": cur_pos,
        "greaterPos": g_pos,
        "greaterAction": g_action,
        "curRank": "2",
        "handCards": hand_cards,
        "numofplayers": [len(hand_cards), enemy1_remaining, teammate_remaining, enemy3_remaining],
        "_botzone_mode": True,
        "_group_members": {
            -1: ["S3"],
            0: ["S8", "C8", "C8"],
            1: ["D9", "H9"],
            2: ["DT", "DT", "ST"],
            3: ["HA", "SA"],
        },
        "_group_gid_type_map": {
            -1: "scatter",
            0: "trip_in_three_with_two",
            1: "pair_in_three_with_two",
            2: "trip_in_three_with_two",
            3: "pair_in_three_with_two",
        },
    }
    ec = {
        "my_pos": 0,
        "cur_pos": cur_pos,
        "cur_rank": "2",
        "numofplayers": [len(hand_cards), enemy1_remaining, teammate_remaining, enemy3_remaining],
        "enemies": {
            1: {
                "remaining": enemy1_remaining,
                "danger_level": "低",
                "recommended_types": ["Straight", "ThreePair", "TwoTrips"],
                "banned_types": [],
                "baoshu": {},
            },
            3: {
                "remaining": enemy3_remaining,
                "danger_level": "极高",
                "recommended_types": ["最大单张"],
                "banned_types": [],
                "baoshu": {
                    "likely_hand": "单张(听牌)",
                    "block_with": ["ThreeWithTwo", "TwoTrips", "ThreePair", "Straight", "Bomb"],
                    "never_play": [],
                },
            },
        },
        "teammate": {
            "remaining": teammate_remaining,
            "is_close": 1 <= teammate_remaining <= 5,
            "assist_prefer": {
                1: ["Single"],
                2: ["Pair"],
                3: ["Trips", "Pair", "Single"],
                4: ["Pair", "Single"],
                5: ["Straight", "ThreeWithTwo", "Single"],
            }.get(teammate_remaining, []),
        },
        "self": {
            "remaining": len(hand_cards),
            "has_two_clean_hands": False,
            "has_bomb": False,
            "should_sprint": False,
        },
        "finished": [],
    }
    return game_state, ec


class TestGua202Repro:
    def test_repro_feed_pair_to_teammate(self):
        """复现局：领出 + 队友 2 张 + 手含 6 Pair → 送最小安全对子 99（非 ThreeWithTwo）"""
        gs, ec = build_state()
        d = EndgameDecider()
        result = d._q1_block_enemy(gs, build_action_list(), ec)
        assert result is not None
        idx, act = result
        assert act[0] == "Pair", f"队友 2 张领出应送对子；实际出 {act}"
        assert act[1] == "9", f"应送最小安全对子 99（不拆 TTT/888 core）；实际出 {act}"

    def test_teammate_not_close_falls_back_to_lock(self):
        """队友 6 张（非 close）→ 不送牌，回退整牌锁敌（ThreeWithTwo 888+99）"""
        gs, ec = build_state(teammate_remaining=6)
        d = EndgameDecider()
        result = d._q1_block_enemy(gs, build_action_list(), ec)
        assert result is not None
        idx, act = result
        assert act[0] == "ThreeWithTwo", f"队友非 close 应回退锁敌；实际出 {act}"
        assert act[1] == "8", f"应出 888+99 锁敌；实际出 {act}"

    def test_follow_turn_not_lead_no_feed(self):
        """跟牌轮（非领出）队友 2 张 → 不触发送牌特判"""
        gs, ec = build_state(greater_action=["Single", "8", ["S8"]])
        d = EndgameDecider()
        # 直接调特判方法：跟牌轮应返回 None
        candidates = [(i, a) for i, a in enumerate(build_action_list())]
        result = d._q1_lead_feed_teammate_special(gs, candidates, ec)
        assert result is None, f"跟牌轮不应触发送牌；实际 {result}"

    def test_no_assist_prefer_no_feed(self):
        """队友 close 但 assist_prefer 为空（如剩 0/6+）→ 不送"""
        gs, ec = build_state(teammate_remaining=0)
        d = EndgameDecider()
        candidates = [(i, a) for i, a in enumerate(build_action_list())]
        result = d._q1_lead_feed_teammate_special(gs, candidates, ec)
        assert result is None, f"队友剩 0 张无 prefer 不应送；实际 {result}"


class TestGua202Safety:
    def test_teammate_one_feeds_safe_single(self):
        """队友报单(1张) + 手含安全小单（外部无压制）→ 送安全单"""
        from src.v.nn.features.memory_tracker import MemoryTracker
        hand = ["S3", "S4", "S8", "H8", "D9", "S9", "DJ"]
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Single", "3", ["S3"]],
            ["Single", "4", ["S4"]],
            ["Single", "8", ["S8"]],
            ["Single", "9", ["D9"]],
            ["Pair", "9", ["D9", "S9"]],
        ]
        gs, ec = build_state(hand_cards=hand, teammate_remaining=1)
        gs["numofplayers"] = [len(hand), 9, 1, 1]
        # 构造 tracker：所有能压过 Single/3 的牌均标记为已打出（4）→ S3 成为安全单
        tracker = MemoryTracker(my_pos=0)
        tracker.init_from_hand(hand)
        above_ranks = ["4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A", "2", "R", "B"]
        for rank in above_ranks:
            for suit in ("S", "H", "D", "C"):
                ct = f"{suit}{rank}"
                if ct in tracker.card_state:
                    tracker.card_state[ct] = [4, 4]
            for joker in ("HR", "SB"):
                tracker.card_state[joker] = [4, 4]
        gs["_memory_tracker"] = tracker
        d = EndgameDecider()
        candidates = [(i, a) for i, a in enumerate(action_list)]
        result = d._q1_lead_feed_teammate_special(gs, candidates, ec)
        assert result is not None
        idx, act = result
        assert act[0] == "Single", f"队友报单应送单张；实际出 {act}"
        assert act[1] == "3", f"应送最小安全单 S3；实际出 {act}"

    def test_feed_does_not_break_bomb_core(self):
        """送牌候选拆炸弹核心（手牌某 rank≥4）→ 不送，回退"""
        hand = ["S8", "H8", "C8", "D8", "D9", "H9", "S3"]  # 4×8 = 炸弹 core
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Single", "3", ["S3"]],
            ["Single", "8", ["S8"]],
            ["Single", "9", ["D9"]],
            ["Pair", "8", ["S8", "H8"]],   # 拆炸弹 core → 应被排除
            ["Pair", "9", ["D9", "H9"]],   # 非拆核 → 可送
        ]
        gs, ec = build_state(hand_cards=hand, teammate_remaining=2)
        gs["numofplayers"] = [len(hand), 9, 2, 1]
        ec["numofplayers"] = [len(hand), 9, 2, 1]
        d = EndgameDecider()
        candidates = [(i, a) for i, a in enumerate(action_list)]
        result = d._q1_lead_feed_teammate_special(gs, candidates, ec)
        assert result is not None
        idx, act = result
        assert act == ["Pair", "9", ["D9", "H9"]], f"拆核 Pair/8 应排除，送非拆核 99；实际 {act}"

    def test_gua190_regression_still_fires_bomb(self):
        """回归：GUA-190 跟牌压单开炸场景仍开炸"""
        from tests.test_gua190_enemy_one_bomb_lock import (
            build_state as gua190_build_state,
            build_action_list as gua190_action_list,
        )
        gs, ec = gua190_build_state()
        d = EndgameDecider()
        result = d._q1_block_enemy(gs, gua190_action_list(), ec)
        assert result is not None
        idx, act = result
        assert act[0] == "Bomb", f"GUA-190 场景应仍开炸；实际出 {act}"
