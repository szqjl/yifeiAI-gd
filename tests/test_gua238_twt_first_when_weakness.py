# -*- coding: utf-8 -*-
"""GUA-238 回归：残局两手 = 整牌 TWT(5) + 单张，且对手已对 ThreeWithTwo PASS（接不住 TWT）
时，Q0 冲刺应「先出 TWT 冲刺」，而非「保留 TWT 后出单」被对手压单卡死。

真源：match=6a7dcf310fbd680d7c72cc5e（logs/v8_vs_botzone_20260813_215541.log 22:05:38~22:06:03，
scores=[0,3,0,3] V8 队负）。V8=player2：
  22:05:55 领出 TWT/6（['H6','D6','S6','DQ','DQ']）对手全 PASS；
  22:05:55 领出 TWT/9（['S9','C9','D9','DJ','CJ']）对手全 PASS；
  22:05:56 手牌 6 = 一手 TWT + 单 S3，Q0 冲刺 `_select_two_turn_sprint_structure`：
    TWT 候选残手=S3 判为风险单（residue_bucket=2），S3 候选残手=TWT 整牌（residue_bucket=0）排前
    → 决策 Single/3（保留 TWT 后出）；22:05:57 对手 Single/2 压 S3 → V8 失领出权，TWT 卡死至输。
修复：对手 memory_tracker.get_type_weakness(对手座) 含 "ThreeWithTwo"（本局已对 TWT 全 PASS）
→ 残局两手该 TWT 候选优先（先出 TWT 冲刺，残单后续单走）。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.features.memory_tracker import MemoryTracker

# 22:05:56 手牌 6 = TWT 整手 + 单 S3
HAND_TWT_PLUS_S3 = ["S9", "C9", "D9", "DJ", "CJ", "S3"]


def build_tracker(opponents_passed_twt: bool = False):
    """真实 MemoryTracker：card_state 全 unknown；可记录对手对 ThreeWithTwo 的 PASS 弱点。"""
    tracker = MemoryTracker(my_pos=0, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(list(HAND_TWT_PLUS_S3))
    if opponents_passed_twt:
        tracker.record_pass(1, "ThreeWithTwo")
        tracker.record_pass(1, "ThreeWithTwo")
        tracker.record_pass(3, "ThreeWithTwo")
        tracker.record_pass(3, "ThreeWithTwo")
    return tracker


def build_state(tracker=None):
    """构造 Q0 冲刺场景：领出轮（我 pos=0）、hand=6、对手剩 5 张。"""
    game_state = {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": -1,
        "greaterAction": [],
        "curRank": "2",
        "handCards": list(HAND_TWT_PLUS_S3),
        "actionList": [list(a) for a in build_action_list()],
        "numofplayers": [6, 5, 12, 9],
        "_botzone_mode": True,
    }
    if tracker is not None:
        game_state["_memory_tracker"] = tracker
    ec = {
        "my_pos": 0,
        "cur_pos": 0,
        "cur_rank": "2",
        "numofplayers": [6, 5, 12, 9],
        "enemies": {
            1: {"remaining": 5, "danger_level": "残局"},
            3: {"remaining": 9, "danger_level": "中"},
        },
        "teammate": {"remaining": 12, "is_close": False},
        "self": {"remaining": 6, "should_sprint": True},
        "finished": [],
    }
    return game_state, ec


def build_action_list():
    """22:05:56 actionList 摘要 len=10 types={'Single':5,'Pair':3,'Trips':1,'ThreeWithTwo':1}。"""
    return [
        ["PASS", "PASS", "PASS"],                                        # 0
        ["Single", "3", ["S3"]],                                         # 1: 单 S3（保留 TWT 后出）
        ["Single", "9", ["S9"]],                                         # 2
        ["Single", "9", ["C9"]],                                         # 3
        ["Single", "J", ["DJ"]],                                         # 4
        ["Single", "J", ["CJ"]],                                         # 5
        ["Pair", "9", ["S9", "C9"]],                                     # 6
        ["Pair", "J", ["DJ", "CJ"]],                                     # 7
        ["Trips", "9", ["S9", "C9", "D9"]],                              # 8
        ["ThreeWithTwo", "9", ["S9", "C9", "D9", "DJ", "CJ"]],           # 9: TWT 整手
    ]


class TestGua238TwtFirstWhenOpponentWeakness:
    def test_twt_first_when_opponent_passed_twt(self):
        """对手已对 ThreeWithTwo 有 weakness（本局连续 PASS 两个 TWT）→ Q0 冲刺先出 TWT。"""
        gs, ec = build_state(build_tracker(opponents_passed_twt=True))
        d = EndgameDecider()
        res = d._q0_self_sprint(gs, gs["actionList"], ec)
        assert res is not None, "两手残局冲刺应有候选"
        idx, act = res
        assert act[0] == "ThreeWithTwo", (
            f"对手已接不住 TWT → 应先出 TWT 冲刺，实际 {act}"
        )
        assert sorted(act[2]) == sorted(HAND_TWT_PLUS_S3[:5])

    def test_no_weakness_keeps_original_single_first(self):
        """对手无 TWT 弱点（可能接得住）→ 维持原逻辑：先出单 S3 保留 TWT 后出。"""
        gs, ec = build_state(build_tracker(opponents_passed_twt=False))
        d = EndgameDecider()
        res = d._q0_self_sprint(gs, gs["actionList"], ec)
        assert res is not None
        idx, act = res
        assert act[0] == "Single", (
            f"无弱点证据时维持原行为（先出单保留 TWT），实际 {act}"
        )

    def test_no_tracker_keeps_original_single_first(self):
        """无 memory_tracker → 维持原逻辑（先出单保留 TWT 后出）。"""
        gs, ec = build_state(tracker=None)
        d = EndgameDecider()
        res = d._q0_self_sprint(gs, gs["actionList"], ec)
        assert res is not None
        idx, act = res
        assert act[0] == "Single"

    def test_enemy_not_endgame_but_weakness_still_twt_first(self):
        """对手非残局（剩牌多）但 TWT 弱点证据仍在 → 仍先出 TWT（冲刺与残局判定解耦）。"""
        gs, ec = build_state(build_tracker(opponents_passed_twt=True))
        ec["enemies"] = {1: {"remaining": 15}, 3: {"remaining": 18}}
        d = EndgameDecider()
        res = d._q0_self_sprint(gs, gs["actionList"], ec)
        assert res is not None
        idx, act = res
        assert act[0] == "ThreeWithTwo"
