# -*- coding: utf-8 -*-
"""GUA-222 敌方报单剩 1 张 + 跟牌压单 → 用最大牌力单张压（忽略回收优先）。

场景：对局 match 6a782bde 第 78 回合，玩家1（下家）剩 1 张报单，
V8（手 SJ+H7,S7+D9,D9 共 5 张）跟牌压敌方 Single/5(S5)。
修复前 _sort_by_recapture_first 回收优先：出 D9 后 J 可回收、出 SJ 无可回收
→ 选拆对 D9（idx=Single/9），被下家最后一张压过 done。
修复后 GUA-222 特判优先 → 取最大牌力单张 SJ 压。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.endgame.endgame_decide import EndgameDecider

# hand = SJ + H7,S7 + D9,D9（5 张）
HAND_J_99_77 = ["SJ", "H7", "S7", "D9", "D9"]


def build_action_list():
    # idx: 0=PASS, 1=Single/J(SJ), 2=Single/9(D9 拆对), 3=Single/7(S7), 4=Single/7(H7)
    return [
        ["PASS", "PASS", "PASS"],
        ["Single", "J", ["SJ"]],
        ["Single", "9", ["D9"]],
        ["Single", "7", ["S7"]],
        ["Single", "7", ["H7"]],
    ]


def build_state(hand_cards=None, greater_action=None, enemy_remaining=1):
    hand_cards = list(hand_cards or HAND_J_99_77)
    if greater_action is None:
        greater_action = ["Single", "5", ["S5"]]
    elif greater_action == "LEAD":
        greater_action = []
    game_state = {
        "myPos": 0,
        "curPos": 0,              # 轮到 V8 跟牌
        "greaterPos": 3,          # 敌方 player3 领出 Single/5
        "greaterAction": greater_action,
        "curRank": "2",
        "handCards": hand_cards,
        "numofplayers": [len(hand_cards), enemy_remaining, 4, 8],
    }
    ec = {
        "my_pos": 0,
        "cur_pos": 0,
        "cur_rank": "2",
        "numofplayers": [len(hand_cards), enemy_remaining, 4, 8],
        "enemies": {
            1: {
                "remaining": enemy_remaining,
                "danger_level": "极高",
                "recommended_types": ["最大单张"],
                "banned_types": [],
                "baoshu": {"never_play": [], "block_with": ["ThreeWithTwo", "TwoTrips", "ThreePair", "Straight", "Bomb"]},
            },
            3: {
                "remaining": 8,
                "danger_level": "中",
                "recommended_types": ["Straight", "TwoTrips", "ThreePair"],
                "banned_types": [],
                "baoshu": {},
            },
        },
        "teammate": {
            2: {"remaining": 4, "danger_level": "低", "recommended_types": [], "banned_types": [], "baoshu": {}},
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


class TestGua222Hit:
    def test_enemy_one_press_uses_max_single(self):
        """下家剩 1 张 + 压 Single/5 → 用最大单 SJ 压（不拆对出 9）"""
        gs, ec = build_state()
        d = EndgameDecider()
        result = d._q1_block_enemy(gs, build_action_list(), ec)
        assert result is not None
        idx, act = result
        assert act[0] == "Single", f"应出单；实际出 {act}"
        assert act[1] == "J", f"应出最大单 J；实际出 {act}（idx={idx}）"
        assert idx == 1, f"应命中 idx=1(SJ)；实际 idx={idx}"

    def test_enemy_not_one_keeps_recapture_sort(self):
        """敌方非报单（剩 2 张）→ 不触发特判，走回收优先（拆对 9 在前）"""
        gs, ec = build_state(enemy_remaining=2)
        d = EndgameDecider()
        result = d._q1_block_enemy(gs, build_action_list(), ec)
        assert result is not None
        idx, act = result
        assert act[0] == "Single", f"非报单场景仍应出单；实际出 {act}"
        assert act[1] == "9", f"非报单场景应保留回收优先选 9；实际出 {act}"

    def test_lead_turn_no_intervention(self):
        """我方领出（无 greaterAction）→ 特判不触发"""
        gs, ec = build_state(greater_action="LEAD")
        d = EndgameDecider()
        candidates = [(i, a) for i, a in enumerate(build_action_list())]
        result = d._q1_enemy_one_single_press_max(gs, candidates, ec, 1, ec["enemies"][1])
        assert result is None, f"领出场景特判不应触发；实际 {result}"

    def test_greater_not_single_no_intervention(self):
        """greaterAction 是 Pair 非 Single → 特判不触发"""
        gs, ec = build_state(greater_action=["Pair", "5", ["S5", "H5"]])
        d = EndgameDecider()
        candidates = [(i, a) for i, a in enumerate(build_action_list())]
        result = d._q1_enemy_one_single_press_max(gs, candidates, ec, 1, ec["enemies"][1])
        assert result is None, f"非单张 greater 特判不应触发；实际 {result}"

    def test_no_enemy_one_no_intervention(self):
        """无任何敌方剩 1 张 → 特判不触发"""
        gs, ec = build_state(enemy_remaining=3)
        d = EndgameDecider()
        candidates = [(i, a) for i, a in enumerate(build_action_list())]
        result = d._q1_enemy_one_single_press_max(gs, candidates, ec, 1, ec["enemies"][1])
        assert result is None, f"无报单敌方特判不应触发；实际 {result}"

    def test_no_single_candidate_no_intervention(self):
        """无 Single 候选 → 特判返回 None"""
        gs, ec = build_state()
        d = EndgameDecider()
        candidates = [(i, a) for i, a in enumerate(build_action_list()) if a[0] != "Single"]
        result = d._q1_enemy_one_single_press_max(gs, candidates, ec, 1, ec["enemies"][1])
        assert result is None, f"无 Single 候选特判不应返回；实际 {result}"
