# -*- coding: utf-8 -*-
"""GUA-190 敌方剩 1 张 + 跟牌压单 + 手牌结构「≥2 炸 + 1 孤立大单(>K) + 其余 2 手整牌」→ 炸弹封死。

场景：对局 6a6f411b27e7bf01db0dc5a6 第 60 步（21:08:00），敌方 player1 剩 1 张报单，
V8 手牌 = 2 炸(8/9) + 2 手 TWT + 小王 SB（19 张），跟牌压敌方 Single/8。
修复前走 recommended ["最大单张"] 只筛 Single → 出 SB 被反压致 player1 头游。
修复后 GUA-190 特判优先 → 直接炸弹封死（最小足够 Bomb/8）。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.endgame.endgame_decide import EndgameDecider


def build_action_list():
    # idx: 0=PASS, 1-8=Single(含 TWT 成分牌与 SB), 9-10=Bomb
    return [
        ["PASS", "PASS", "PASS"],
        ["Single", "3", ["S3"]],
        ["Single", "4", ["S4"]],
        ["Single", "5", ["S5"]],
        ["Single", "6", ["S6"]],
        ["Single", "7", ["S7"]],
        ["Single", "8", ["S8"]],
        ["Single", "9", ["S9"]],
        ["Single", "B", ["SB"]],        # idx=8 小王 SB
        ["Bomb", "8", ["S8", "H8", "C8", "D8"]],
        ["Bomb", "9", ["S9", "H9", "C9", "D9"]],
    ]


HAND_2BOMB_2TWT_SB = [
    "S8", "H8", "C8", "D8",
    "S9", "H9", "C9", "D9",
    "S3", "H3", "C3", "S4", "H4",
    "S5", "H5", "C5", "S7", "H7",
    "SB",
]


def build_state(hand_cards=None, greater_action=None, enemy_remaining=1):
    hand_cards = list(hand_cards or HAND_2BOMB_2TWT_SB)
    if greater_action is None:
        greater_action = ["Single", "8", ["S8"]]
    elif greater_action == "LEAD":
        greater_action = []
    game_state = {
        "myPos": 0,
        "curPos": 0,              # 轮到 V8 跟牌
        "greaterPos": 3,          # 敌方 player3 领出 Single/8
        "greaterAction": greater_action,
        "curRank": "2",
        "handCards": hand_cards,
        "numofplayers": [len(hand_cards), enemy_remaining, 6, 7],
    }
    ec = {
        "my_pos": 0,
        "cur_pos": 0,
        "cur_rank": "2",
        "numofplayers": [len(hand_cards), enemy_remaining, 6, 7],
        "enemies": {
            1: {
                "remaining": enemy_remaining,
                "danger_level": "极高",
                "recommended_types": ["最大单张"],
                "banned_types": [],
                "baoshu": {"never_play": [], "block_with": ["ThreeWithTwo", "TwoTrips", "ThreePair", "Straight", "Bomb"]},
            },
            3: {
                "remaining": 7,
                "danger_level": "中",
                "recommended_types": ["Straight", "TwoTrips", "ThreePair"],
                "banned_types": [],
                "baoshu": {},
            },
        },
        "teammate": {
            2: {"remaining": 6, "danger_level": "低", "recommended_types": [], "banned_types": [], "baoshu": {}},
        },
        "self": {
            "remaining": len(hand_cards),
            "danger_level": "高",
            "recommended_types": ["最大单张"],
            "banned_types": [],
            "baoshu": {},
        },
        "finished": [],
    }
    return game_state, ec


class TestGua190Hit:
    def test_two_bomb_two_twt_sb_fires_bomb(self):
        """2 炸 + 2 手 TWT + 小王(>K) + 敌方剩 1 跟单 → 直接 Bomb/8 封死"""
        gs, ec = build_state()
        d = EndgameDecider()
        result = d._q1_block_enemy(gs, build_action_list(), ec)
        assert result is not None
        idx, act = result
        assert act[0] == "Bomb", f"应出 Bomb；实际出 {act}"
        assert act[1] == "8", f"应选最小足够 Bomb/8；实际出 {act}"

    def test_follow_single_but_enemy_not_one_no_fire(self):
        """敌方剩 2 张 → 不触发特判（走老逻辑）"""
        gs, ec = build_state(enemy_remaining=2)
        d = EndgameDecider()
        result = d._q1_block_enemy(gs, build_action_list(), ec)
        assert result is not None
        idx, act = result
        assert act[0] == "Single", f"非剩 1 场景不应开炸；实际出 {act}"

    def test_lead_turn_no_greater_no_fire(self):
        """我方领出（无 greaterAction）→ 特判直接不触发"""
        gs, ec = build_state(greater_action="LEAD")
        d = EndgameDecider()
        candidates = [(i, a) for i, a in enumerate(build_action_list())]
        result = d._q1_enemy_one_bomb_lock_special(gs, candidates, ec, 1, ec["enemies"][1])
        assert result is None, f"领出场景特判不应触发；实际 {result}"

    def test_greater_not_single_no_fire(self):
        """greaterAction 是 Pair 非 Single → 不触发"""
        gs, ec = build_state(greater_action=["Pair", "8", ["S8", "H8"]])
        d = EndgameDecider()
        result = d._q1_block_enemy(gs, build_action_list(), ec)
        assert result is not None
        idx, act = result
        assert act[0] != "Bomb", f"压单场景才开炸；实际出 {act}"


class TestGua190HandStructure:
    def test_no_solo_single_no_fire(self):
        """孤立单张不止 1 个 → 不触发"""
        hand = [
            "S8", "H8", "C8", "D8",
            "S9", "H9", "C9", "D9",
            "S3", "H3", "C3", "S4", "H4",
            "S5", "H5", "C5", "S7", "H7",
            "SK", "SB",                      # 两个孤立单张
        ]
        gs, ec = build_state(hand_cards=hand)
        d = EndgameDecider()
        result = d._q1_block_enemy(gs, build_action_list(), ec)
        assert result is not None
        idx, act = result
        assert act[0] != "Bomb", f"两个孤立单张不应开炸；实际出 {act}"

    def test_solo_single_not_above_k_no_fire(self):
        """孤立单张 ≤K → 不触发"""
        hand = [
            "S8", "H8", "C8", "D8",
            "S9", "H9", "C9", "D9",
            "S3", "H3", "C3", "S4", "H4",
            "S5", "H5", "C5", "S7", "H7",
            "SQ",                             # 孤立单张 Q(12)，不是 >K？Q=12>11，用 K 代替
        ]
        # 用 K 替换 Q：K 值 11 不 > K
        hand[-1] = "SK"
        gs, ec = build_state(hand_cards=hand)
        d = EndgameDecider()
        result = d._q1_block_enemy(gs, build_action_list(), ec)
        assert result is not None
        idx, act = result
        assert act[0] != "Bomb", f"孤立单张 ≤K 不应开炸；实际出 {act}"

    def test_only_one_bomb_no_fire(self):
        """只有 1 手炸 → 不触发"""
        hand = [
            "S8", "H8", "C8", "D8",           # 1 手炸
            "S3", "H3", "C3", "S4", "H4",     # TWT1
            "S5", "H5", "C5", "S7", "H7",     # TWT2
            "SB",
        ]
        gs, ec = build_state(hand_cards=hand)
        d = EndgameDecider()
        result = d._q1_block_enemy(gs, build_action_list(), ec)
        assert result is not None
        idx, act = result
        assert act[0] != "Bomb", f"仅 1 手炸不应开炸；实际出 {act}"

    def test_rest_not_two_hands_no_fire(self):
        """其余牌不是恰好 2 手整牌 → 不触发"""
        hand = [
            "S8", "H8", "C8", "D8",
            "S9", "H9", "C9", "D9",
            "S3", "H3", "C3", "S4", "H4",
            "S5", "H5", "C5", "S7", "SB",        # 7 只剩 1 张 → 结构不成 2 手
        ]
        gs, ec = build_state(hand_cards=hand)
        d = EndgameDecider()
        result = d._q1_block_enemy(gs, build_action_list(), ec)
        assert result is not None
        idx, act = result
        assert act[0] != "Bomb", f"其余牌不成 2 手不应开炸；实际出 {act}"

    def test_rest_two_trips_two_hands_fires(self):
        """2 炸 + 2 手 TwoTrips + 孤立 2 级牌(>K) → 触发"""
        hand = [
            "S8", "H8", "C8", "D8",
            "S9", "H9", "C9", "D9",
            "S3", "H3", "C3", "S4", "H4", "C4",
            "S5", "H5", "C5", "S6", "H6", "C6",
            "S2",
        ]
        gs, ec = build_state(hand_cards=hand)
        d = EndgameDecider()
        result = d._q1_block_enemy(gs, build_action_list(), ec)
        assert result is not None
        idx, act = result
        assert act[0] == "Bomb", f"2 手 TwoTrips + 孤立 2 级牌应开炸；实际出 {act}"
