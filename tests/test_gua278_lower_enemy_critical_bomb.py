# -*- coding: utf-8 -*-
"""GUA-278：下家敌 remaining≤2 + actionList 有 Bomb/SF → 最廉炸截断。

锚点 match=6a8d4603：下家 ThreeWithTwo/K 后剩≈2，GUA-135 选 min TWT →
Q1 拆核转 PASS，放走下家头游。定音：有炸则禁拆核 PASS / 禁优先拆核 TWT。
"""

from __future__ import annotations

from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.features.memory_tracker import MemoryTracker

PASS = ["PASS", "PASS", "PASS"]
BOMB_3 = ["Bomb", "3", ["C3", "D3", "H3", "S3"]]
BOMB_5 = ["Bomb", "5", ["C5", "D5", "H5", "S5", "H2"]]  # 5星更贵
# 拆炸核：用 3 张 3 + 对 A 打 TWT（破坏 Bomb/3）
TWT_BREAK = ["ThreeWithTwo", "3", ["C3", "D3", "H3", "HA", "CA"]]
TWT_K = ["ThreeWithTwo", "K", ["CK", "SK", "HK", "HA", "CA"]]

HAND = ["C3", "D3", "H3", "S3", "C5", "D5", "H5", "S5", "H2", "HA", "CA", "C7"]


def _gs(
    hand,
    action_list,
    numofplayers,
    greater_pos,
    greater_action,
    my_pos=2,
):
    tracker = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    tracker.init_from_hand(hand)
    tracker.set_level_rank("2")
    tracker.hand_counts = {i: numofplayers[i] for i in range(4)}
    gs = {
        "myPos": my_pos,
        "curPos": my_pos,
        "greaterPos": greater_pos,
        "greaterAction": greater_action,
        "handCards": list(hand),
        "actionList": action_list,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "numofplayers": list(numofplayers),
        "publicInfo": [{"rest": n} for n in numofplayers],
        "_memory_tracker": tracker,
        "_belief": {
            "hand_counts": {i: numofplayers[i] for i in range(4)},
            "opp_bomb_risks": {(my_pos + 1) % 4: 0.0, (my_pos + 3) % 4: 0.0},
        },
        "_role": "主攻",
        "_group_members": {
            0: ["C3", "D3", "H3", "S3"],
            1: ["C5", "D5", "H5", "S5", "H2"],
            -1: [c for c in hand if c not in (
                "C3", "D3", "H3", "S3", "C5", "D5", "H5", "S5", "H2",
            )],
        },
        "_group_gid_type_map": {
            0: "Bomb",
            1: "Bomb",
            -1: "scatter",
        },
    }
    return gs


def _decide(gs):
    EndgamePreprocessor().preprocess(gs)
    return EndgameDecider().decide(gs, gs["actionList"])


def test_cheapest_bomb_prefers_four_over_five():
    """最廉炸：4星 Bomb/3 ≻ 5星 Bomb/5 ≻ SF。"""
    al = [
        PASS,
        BOMB_5,
        BOMB_3,
        ["StraightFlush", "A", ["SA", "S2", "S3", "S4", "S5"]],
    ]
    picked = EndgameDecider()._select_cheapest_bomb_or_sf(al, "2")
    assert picked is not None
    assert picked[1][0] == "Bomb"
    assert picked[1][1] == "3"


def test_match_lower_twt_rem2_bombs_not_pass():
    """构造态：下家 TWT/K 剩2 + 有炸 → 出最廉 Bomb，非 PASS。

    复现链：拆核 TWT 在候选 → 旧逻辑 Q1 拆核转 PASS。
    """
    my_pos = 2
    lower = 3
    # 下家剩2 → 残局 active；自己 12 张
    nums = [10, 10, 12, 2]
    al = [PASS, TWT_BREAK, BOMB_5, BOMB_3]
    gs = _gs(HAND, al, nums, lower, TWT_K, my_pos=my_pos)
    # 确认拆核判定成立（否则测不到本刀）
    assert EndgameDecider._action_breaks_core_structure(TWT_BREAK, gs) is True

    idx, act = _decide(gs)
    assert act is not None
    assert act[0] != "PASS", f"下家敌剩2应炸截断，实际 {act}"
    assert act[0] in ("Bomb", "StraightFlush"), f"应出炸族，实际 {act}"
    assert act[0] == "Bomb" and act[1] == "3", f"应最廉 Bomb/3，实际 {act}"


def test_lower_rem5_no_force_bomb_on_break():
    """下家剩5：GUA-278 不触发；拆核仍可转 PASS（不强制炸）。"""
    my_pos = 2
    lower = 3
    nums = [10, 10, 12, 5]
    al = [PASS, TWT_BREAK, BOMB_3]
    gs = _gs(HAND, al, nums, lower, TWT_K, my_pos=my_pos)
    assert EndgameDecider._action_breaks_core_structure(TWT_BREAK, gs) is True

    # 仅测 helper：rem>2 应返回 None
    EndgamePreprocessor().preprocess(gs)
    alt = EndgameDecider()._gua278_critical_lower_enemy_bomb(
        gs, al, gs.get("_endgame_context"),
    )
    assert alt is None


def test_upper_enemy_rem2_no_gua278():
    """上家敌剩2：本刀仅管下家，helper 不强制炸。"""
    my_pos = 2
    upper = 1  # (2+3)%4=1 上家
    nums = [10, 2, 12, 10]
    al = [PASS, TWT_BREAK, BOMB_3]
    gs = _gs(HAND, al, nums, upper, TWT_K, my_pos=my_pos)
    EndgamePreprocessor().preprocess(gs)
    alt = EndgameDecider()._gua278_critical_lower_enemy_bomb(
        gs, al, gs.get("_endgame_context"),
    )
    assert alt is None


def test_helper_picks_bomb_when_lower_rem2():
    """helper 直测：下家 greater + rem=2 → 返回最廉炸。"""
    my_pos = 2
    lower = 3
    nums = [8, 8, 12, 2]
    al = [PASS, TWT_BREAK, BOMB_5, BOMB_3]
    gs = _gs(HAND, al, nums, lower, TWT_K, my_pos=my_pos)
    EndgamePreprocessor().preprocess(gs)
    alt = EndgameDecider()._gua278_critical_lower_enemy_bomb(
        gs, al, gs.get("_endgame_context"),
    )
    assert alt is not None
    assert alt[1][0] == "Bomb" and alt[1][1] == "3"
