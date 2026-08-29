# -*- coding: utf-8 -*-
"""GUA-289：上家敌本局已用过炸弹（historical）且进残局 → GUA-270 不让道，Q1 开炸截断。

锚点：match=6a92e4aa1b27100f38d8bd94（logs/v8_vs_botzone_20260829_170634.log）
第 52 回合（21:55:13）：上家 player3 已出 `Bomb/4`（21:55:09）又出 `Bomb/3`，剩 3 张；
V8 手 14 = 6星J炸 + 唯一核心 SF[H5,H6,H7,H2,H9] + trips[CT,ST,ST]（6 星 J 炸可压 Bomb/3），
却命中 `_q1_yield_upper_endgame_to_teammate`（GUA-270「上家残局 + 队友剩14>5 → PASS 交由
队友」）直接 PASS → 放走上家/敌方冲刺，scores=[0,3,0,3] V8 队负。

用户定音（2026-08-29）：上家已用炸（本手之前的 historical 计数 ≥1）且剩 N 张冲刺在即，
不该再按「普通残局交队友」让道 → GUA-270 失效，Q1 通用路径开炸截断。
不算本手刚出的炸（口径：historical，21:55:09 那轮上家第一把 Bomb/4 刚落地仍保持让道）。
"""

import pytest

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor

J_CORE_6 = ["CJ", "DJ", "HJ", "HJ", "SJ", "SJ"]
SF_5_9 = ["H5", "H6", "H7", "H2", "H9"]
TRIPS_T = ["CT", "ST", "ST"]
BOMB_3 = ["H3", "S3", "C3", "D3"]
BOMB_4 = ["H4", "S4", "C4", "D4"]
PAIR_A = ["HA", "DA"]


class _MockTracker:
    """替换 MemoryTracker：只暴露 GUA-289 需要的 bombs_played。"""

    def __init__(self, bombs_played=None):
        self.bombs_played = dict(bombs_played or {})
        self.play_history = []


def _state(*, hand_cards, action_list, greater_pos, upper_remaining, tracker=None, greater_cards=None):
    """21:55:13 残局帧骨架：V8=pos0，上家(3) 炸，队友(2) 剩 >5。"""
    gs = {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": greater_pos,
        "greaterAction": ["Bomb", "3", list(greater_cards or BOMB_3)],
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
    }
    if tracker is not None:
        gs["_memory_tracker"] = tracker
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


class TestGua289UpperEnemyBombedOpenFire:
    def test_upper_enemy_used_bomb_before_fires(self):
        """上家 historical 已用炸（Bomb/4 之前出过）+ 剩 3 张 → 不再 PASS，出炸截断。"""
        hand_cards, action_list = _hand_and_actions()
        tracker = _MockTracker(bombs_played={3: 2})  # Bomb/4 + 本手 Bomb/3
        gs = _state(
            hand_cards=hand_cards, action_list=action_list,
            greater_pos=3, upper_remaining=3, tracker=tracker,
        )
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert act[0] == "Bomb", f"上家已用炸+残局应开炸，实际 act={act}"

    def test_upper_enemy_first_bomb_still_yields(self):
        """上家刚出第一把炸（Bomb/4 就是本手）→ historical=0，保持 GUA-270 让道 PASS。"""
        hand_cards, action_list = _hand_and_actions()
        tracker = _MockTracker(bombs_played={3: 1})  # 仅本手
        gs = _state(
            hand_cards=hand_cards, action_list=action_list,
            greater_pos=3, upper_remaining=7,
            tracker=tracker, greater_cards=BOMB_4,
        )
        gs["greaterAction"] = ["Bomb", "4", list(BOMB_4)]
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert act[0] == "PASS", f"第一把炸刚落地仍让道，实际 act={act}"

    def test_no_tracker_keeps_gua270_pass(self):
        """无 _memory_tracker（单测/降级态）→ 修复不触发，保持旧让道行为。"""
        hand_cards, action_list = _hand_and_actions()
        gs = _state(
            hand_cards=hand_cards, action_list=action_list,
            greater_pos=3, upper_remaining=3, tracker=None,
        )
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert act[0] == "PASS", "无记忆证据不强行开炸，实际 act=%s" % (act,)

    def test_teammate_small_remaining_ignored_scope(self):
        """队友剩 ≤5 时 GUA-270 本就不生效（不在 scope），维持开炸路径。"""
        hand_cards, action_list = _hand_and_actions()
        tracker = _MockTracker(bombs_played={3: 2})
        gs = _state(
            hand_cards=hand_cards, action_list=action_list,
            greater_pos=3, upper_remaining=3, tracker=tracker,
        )
        gs["numofplayers"] = [14, 8, 4, 3]
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert act[0] == "Bomb", f"队友已短牌本不在让道 scope，实际 act={act}"