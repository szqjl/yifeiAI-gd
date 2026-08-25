# -*- coding: utf-8 -*-
"""GUA-273：三自然张+配子+单 → 敌报单 TWT 一手清；敌>1 先探单留炸。

match=6a8d2762：手牌 H4,C4,D4,H2,DT 误 Q0 配子炸只剩 DT 末游。
"""

from __future__ import annotations

from src.communication.botzone_adapter import ActionListGenerator
from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker

HAND = ["DT", "H4", "C4", "D4", "H2"]
CUR = "2"
TWT = ["ThreeWithTwo", "4", ["H4", "C4", "D4", "H2", "DT"]]
BOMB = ["Bomb", "4", ["H4", "C4", "D4", "H2"]]
PASS = ["PASS", "PASS", "PASS"]


def _gs(hand, action_list, numofplayers, my_pos=2):
    tracker = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(hand)
    tracker.set_level_rank(CUR)
    tracker.hand_counts = {i: numofplayers[i] for i in range(4)}
    gs = {
        "myPos": my_pos,
        "curPos": my_pos,
        "greaterPos": -1,
        "greaterAction": PASS,
        "handCards": list(hand),
        "actionList": action_list,
        "curRank": CUR,
        "selfRank": CUR,
        "oppoRank": CUR,
        "numofplayers": list(numofplayers),
        "done": [0],
        "_memory_tracker": tracker,
        "_belief": {
            "hand_counts": {i: numofplayers[i] for i in range(4)},
            "opp_bomb_risks": {1: 0.0, 3: 0.0},
        },
        "_role": "主攻",
    }
    EndgamePreprocessor().preprocess(gs)
    return gs


def _lead_actions():
    return ActionListGenerator(cur_rank=CUR).generate_lead_actions(HAND)


def test_adapter_has_trips_wild_single_twt():
    acts = _lead_actions()
    assert TWT in acts


def test_enemy_one_leads_twt_finish():
    """任一敌 remaining==1 → ThreeWithTwo 一手清。"""
    acts = _lead_actions()
    gs = _gs(HAND, acts, [0, 1, 5, 3], my_pos=2)
    idx, act = EndgameDecider()._q0_trips_wild_single_sprint_lead(
        gs, acts, gs["_endgame_context"], [(i, a) for i, a in enumerate(acts) if a[0] != "Bomb"],
    )
    assert act is not None
    assert act[0] == "ThreeWithTwo"
    assert set(act[2]) == set(HAND)


def test_enemy_gt_one_leads_single_not_bomb():
    """敌均 >1 → 先出最小天然单 DT，不先配子炸。"""
    acts = _lead_actions()
    gs = _gs(HAND, acts, [0, 5, 5, 4], my_pos=2)
    non_bombs = [(i, a) for i, a in enumerate(acts) if a[0] != "Bomb"]
    idx, act = EndgameDecider()._q0_trips_wild_single_sprint_lead(
        gs, acts, gs["_endgame_context"], non_bombs,
    )
    assert act is not None
    assert act[0] == "Single" and act[2] == ["DT"]


def test_q0_self_sprint_skips_bomb_when_enemy_gt_one():
    acts = _lead_actions()
    gs = _gs(HAND, acts, [0, 5, 5, 4], my_pos=2)
    idx, act = EndgameDecider()._q0_self_sprint(gs, acts, gs["_endgame_context"])
    assert act is not None
    assert act[0] == "Single"
    assert act[2] == ["DT"]
