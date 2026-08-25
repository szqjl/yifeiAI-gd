# -*- coding: utf-8 -*-
"""GUA-272：GUA-161 双上清散单须队友真头游（done[0]==队友），非仅 remaining=0。

match=6a8d222d：done=[3,0] 敌 player3 头游、队友 player0 二游接风 → 不得 GUA-161。
"""

from __future__ import annotations

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker

# 钢板 333444 + 散单 H4/S5/H6（组牌后 scatter 非钢板成员）
HAND_MATCH = [
    "H4", "S5", "H6",
    "D3", "H3", "C3", "C4", "D4", "S4",
]
ACTIONS_MATCH = [
    ["Single", "4", ["H4"]],
    ["Single", "5", ["S5"]],
    ["Single", "6", ["H6"]],
    ["TwoTrips", "4", ["D3", "H3", "C3", "C4", "D4", "S4"]],
]

# 组牌语义：H4/S5/H6 散单；D3H3C3 + C4D4S4 钢板（与 preprocessor 解耦，直测 GUA-161 候选）
CARD_MASK_MATCH = {
    "H4": (-1, 0.0, 1),
    "S5": (-1, 0.0, 1),
    "H6": (-1, 0.0, 1),
    "D3": (0, 1.0, 3),
    "H3": (0, 1.0, 3),
    "C3": (0, 1.0, 3),
    "C4": (1, 1.0, 3),
    "D4": (1, 1.0, 3),
    "S4": (1, 1.0, 3),
}


def _gs(
    hand,
    action_list,
    numofplayers,
    done,
    my_pos=2,
):
    tracker = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(hand)
    tracker.set_level_rank("2")
    tracker.hand_counts = {i: numofplayers[i] for i in range(4)}
    gs = {
        "myPos": my_pos,
        "curPos": my_pos,
        "greaterPos": -1,
        "greaterAction": ["PASS", "PASS", "PASS"],
        "handCards": list(hand),
        "actionList": action_list,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "numofplayers": list(numofplayers),
        "done": list(done),
        "_memory_tracker": tracker,
        "_belief": {
            "hand_counts": {i: numofplayers[i] for i in range(4)},
            "opp_bomb_risks": {1: 0.0, 3: 0.0},
        },
        "_role": "主攻",
    }
    EndgamePreprocessor().preprocess(gs)
    gs["_card_mask"] = dict(CARD_MASK_MATCH)
    return gs


def test_done_3_0_teammate_second_does_not_trigger_gua161():
    """done=[3,0]：敌头游 + 队友二游 → pick_double_second_small_single 返回 None。"""
    gs = _gs(
        HAND_MATCH,
        ACTIONS_MATCH,
        [0, 12, 10, 0],
        [3, 0],
        my_pos=2,
    )
    idx, act = EndgameDecider().pick_double_second_small_single(gs, ACTIONS_MATCH)
    assert idx is None and act is None


def test_done_0_first_teammate_head_triggers_gua161():
    """done=[0]：队友头游 → 清最小自然散单 H4。"""
    gs = _gs(
        HAND_MATCH,
        ACTIONS_MATCH,
        [0, 14, 10, 12],
        [0],
        my_pos=2,
    )
    idx, act = EndgameDecider().pick_double_second_small_single(gs, ACTIONS_MATCH)
    assert act is not None
    assert act[0] == "Single" and act[2] == ["H4"]


def test_done_0_3_teammate_first_still_triggers():
    """done=[0,3]：队友先完、敌后完 → 仍算队友头游。"""
    gs = _gs(
        HAND_MATCH,
        ACTIONS_MATCH,
        [0, 14, 10, 0],
        [0, 3],
        my_pos=2,
    )
    idx, act = EndgameDecider().pick_double_second_small_single(gs, ACTIONS_MATCH)
    assert act is not None
    assert act[2] == ["H4"]


def test_done_empty_does_not_trigger():
    """无 done 信息 → 不得把 remaining=0 当已头游。"""
    gs = _gs(
        HAND_MATCH,
        ACTIONS_MATCH,
        [0, 14, 10, 12],
        [],
        my_pos=2,
    )
    idx, act = EndgameDecider().pick_double_second_small_single(gs, ACTIONS_MATCH)
    assert idx is None and act is None


def test_teammate_is_head_finisher_helper():
    assert EndgameDecider._teammate_is_head_finisher({"done": [3, 0]}, 0) is False
    assert EndgameDecider._teammate_is_head_finisher({"done": [0, 3]}, 0) is True
    assert EndgameDecider._teammate_is_head_finisher({"done": [0]}, 0) is True
    assert EndgameDecider._teammate_is_head_finisher({}, 0) is False
