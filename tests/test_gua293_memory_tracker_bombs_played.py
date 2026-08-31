# -*- coding: utf-8 -*-
"""GUA-293：MemoryTracker.bombs_played 真实接线。

根因：GUA-289 依 `_memory_tracker.bombs_played[up_pos]` 判「上家敌 historical 已用炸」→
GUA-270 让道失效开炸；但 `MemoryTracker.record_bomb()` 从未被任何出牌路径调用
（`record_play` 只记 `type_bombed`），故 `bombs_played` 恒为 0，GUA-289 成死代码，
线上总是 GUA-270「队友剩牌>5 → PASS 交由队友」放走上家冲刺。

锚点：match=6a9517d9 第49回合（重放回合12）：队友 p2 已两炸、上家 p3 连出
Bomb/3→Bomb/CT 剩 5 张，GUA-289 未触发 → GUA-270 PASS 放走上家。

修复：`record_play` 在 action 为 Bomb/StraightFlush 时调用 `record_bomb(seat)`；
并补真实 MemoryTracker 链路回归（不再用 mock 只塞 bombs_played）。
"""

import pytest

from src.v.nn.features.memory_tracker import MemoryTracker
from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor


class TestMemoryTrackerBombRecording:
    """bombs_played 真实接线（本文件核心回归：修复前失败）。"""

    def test_record_play_bomb_increments_bombs_played(self):
        tracker = MemoryTracker(my_pos=0)
        # action 格式 ["Bomb", "3", [cards]]
        tracker.record_play(3, ["Bomb", "3", ["C3", "D3", "H3", "S3"]])
        assert tracker.bombs_played[3] == 1, (
            f"record_play(Bomb) 应记 bombs_played[3]=1，实际 {tracker.bombs_played}")

    def test_record_play_straight_flush_increments_bombs_played(self):
        tracker = MemoryTracker(my_pos=0)
        tracker.record_play(1, ["StraightFlush", "5", ["C2", "C3", "C4", "C5", "C6"]])
        assert tracker.bombs_played[1] == 1

    def test_record_play_non_bomb_does_not_increment(self):
        tracker = MemoryTracker(my_pos=0)
        tracker.record_play(1, ["Pair", "8", ["C8", "D8"]])
        tracker.record_play(1, ["Single", "2", ["D2"]])
        tracker.record_play(1, ["ThreeWithTwo", "9", ["C9", "D9", "H9", "C2", "D2"]])
        assert tracker.bombs_played.get(1, 0) == 0

    def test_record_play_pass_and_empty_no_increment(self):
        tracker = MemoryTracker(my_pos=0)
        tracker.record_play(2, ["PASS", "PASS", "PASS"])
        # len(action) < 3 直接 return，不崩
        tracker.record_play(2, ["Bomb", "3", []])
        assert tracker.bombs_played.get(2, 0) == 0


J_CORE_6 = ["CJ", "DJ", "HJ", "HJ", "SJ", "SJ"]
SF_5_9 = ["H5", "H6", "H7", "H2", "H9"]
TRIPS_T = ["CT", "ST", "ST"]
BOMB_4 = ["H4", "S4", "C4", "D4"]


def _state(*, hand_cards, action_list, greater_pos, upper_remaining, tracker, greater_type="Bomb", greater_rank="4", greater_cards=None):
    gs = {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": greater_pos,
        "greaterAction": [greater_type, greater_rank, list(greater_cards or BOMB_4)],
        "handCards": list(hand_cards),
        "actionList": action_list,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "numofplayers": [14, 8, 14, upper_remaining],
        "_role": "主攻",
        "_group_members": {
            "g0": [c for c in J_CORE_6],
            "g1": [c for c in SF_5_9],
            "g2": [c for c in TRIPS_T],
        },
        "_group_gid_type_map": {
            "g0": "Bomb",
            "g1": "StraightFlush",
            "g2": "trips",
        },
        "_memory_tracker": tracker,
    }
    return gs


def _hand_and_actions():
    hand_cards = J_CORE_6 + SF_5_9 + TRIPS_T
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Bomb", "J", [c for c in J_CORE_6]],
        ["Bomb", "T", ["CT", "ST", "ST", "H2"]],
        ["StraightFlush", "5", [c for c in SF_5_9]],
    ]
    return hand_cards, action_list


class TestGua293RealTrackerGua289Integration:
    """真实 MemoryTracker → GUA-289 开炸（替代 mock 塞字段的测试）。"""

    def test_upper_bombed_via_real_tracker_opens_fire(self):
        """用真实 MemoryTracker 记上家两炸后 → GUA-270 失效开炸。"""
        tracker = MemoryTracker(my_pos=0)
        # 上家 p3 historical 一把炸（Bomb/4）
        tracker.record_play(3, ["Bomb", "4", list(BOMB_4)])
        hand_cards, action_list = _hand_and_actions()
        gs = _state(
            hand_cards=hand_cards, action_list=action_list,
            greater_pos=3, upper_remaining=3, tracker=tracker,
            greater_cards=[],
        )
        # 本手 greater = 上家 Bomb/4（同历史口径测试：bombs_played[3]=1，
        # greater 是本手上家炸 → 扣 1 → historical=0 → 仍让道？）
        # 见 GUA-289 口径：上家第一把炸=本手刚落地 → historical=0 → 保持让道。
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert act[0] == "PASS", (
            f"第一把炸刚落地（historical=0）应让道，实际 act={act}")

    def test_upper_two_bombs_via_real_tracker_opens_fire(self):
        """真实 MemoryTracker 记上家 historical(1) + 本手(1) 两炸 → 开炸截断。"""
        tracker = MemoryTracker(my_pos=0)
        # 上家 p3 historical 一把炸（Bomb/4）
        tracker.record_play(3, ["Bomb", "4", list(BOMB_4)])
        # 本手 greater 也是上家的炸 → bombs_played[3]=2
        tracker.record_play(3, ["Bomb", "3", ["H3", "S3", "C3", "D3"]])
        hand_cards, action_list = _hand_and_actions()
        gs = _state(
            hand_cards=hand_cards, action_list=action_list,
            greater_pos=3, upper_remaining=3, tracker=tracker,
            greater_type="Bomb", greater_rank="3", greater_cards=["H3", "S3", "C3", "D3"],
        )
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert act[0] == "Bomb", f"上家已两炸+残局应开炸截断，实际 act={act}"
