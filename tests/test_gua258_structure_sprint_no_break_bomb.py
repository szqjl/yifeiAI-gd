# -*- coding: utf-8 -*-
"""
GUA-258: GUA-142 自由领出 ThreePair 冲刺不应拆炸弹。

背景（match `6a87081b0fbd680d7c7c77b9`，`logs/v8_vs_botzone_20260820_214746.log`
L591-642，scores=[0,2,0,2] V8 队负）：
  V8=player0 接风领出轮，手牌 15 = 炸6666 + 炸8888 + 顺9-K + 对7。
  GUA-142 free_lead structure_sprint 选 `ThreePair/8 (667788)`，
  拆了双炸（GUA-154 事后标记 broken=['Bomb','Bomb']）。后续剩
  对6+对8+顺9-K 无炸弹，先顺9-K、对6、单8 被压，V8 队 0 分。
  正确打法：保留双炸，先出顺9-K 用炸弹收尾。

根因：`_q1_free_lead_structure_sprint`（endgame_decide.py L2494）候选过滤
  只调 `_has_structure_sprint_path(remainder)`——对打出后剩余牌
  `C6,C6,H8,C8,H9,ST,CJ,SQ,DK` 经 `_find_high_straight_cards`（L2428）按点数
  集合凑出「8-J 高顺」误判仍有冲刺路径，未检查打出动作本身是否拆炸弹。

修复：GUA-142 候选过滤排除「拆 ≥4 同点炸弹」的 ThreePair/TwoTrips 动作
  （拆炸后无炸弹回手 = 假冲刺路径），保留不拆炸的正常路径（如 GUA-142
  从 SF 组拆 2 张凑 ThreePair，SF 留作冲刺尾牌）。
"""
import pytest

from src.v.nn.endgame.endgame_decide import EndgameDecider


def build_gs():
    """复现场景：双炸 6666/8888 + 顺9-K + 对7，接风领出轮。"""
    return {
        "curRank": "2",
        "handCards": [
            "H6", "S6", "C6", "C6",
            "S8", "H8", "H8", "C8",
            "H9", "ST", "CJ", "SQ", "DK",
            "H7", "H7",
        ],
        "myPos": 0,
        "curPos": 0,
        "greaterPos": -1,
        "greaterAction": None,
        "curAction": None,
        "numofplayers": [15, 9, 0, 2],
        "publicInfo": [
            {"rest": 15}, {"rest": 9}, {"rest": 0}, {"rest": 2},
        ],
        "done": [3, 2],
        "stage": "play",
        "selfRank": "2",
        "oppoRank": "2",
        "_botzone_mode": True,
        "_group_type_map": {
            "Bomb": 2, "straight": 1, "pair": 1,
        },
    }


def build_ec():
    return {
        "my_pos": 0,
        "cur_pos": 0,
        "cur_rank": "2",
        "numofplayers": [15, 9, 0, 2],
        "enemies": {
            1: {"remaining": 9, "danger_level": "低", "recommended_types": [],
                "banned_types": [], "baoshu": {}},
            3: {"remaining": 2, "danger_level": "低", "recommended_types": [],
                "banned_types": [], "baoshu": {}},
        },
        "teammate": {"remaining": 0, "is_close": True, "assist_prefer": []},
        "self": {"remaining": 15, "has_two_clean_hands": False,
                 "has_bomb": True, "should_sprint": False},
        "finished": [3, 2],
    }


def build_action_list():
    """本局 actionList：含 667788（拆双炸）与不拆炸的顺子/炸/对等。"""
    return [
        ["PASS", "PASS", "PASS"],
        ["Pair", "6", ["C6", "C6"]],
        ["Pair", "7", ["H7", "H7"]],
        ["Pair", "8", ["H8", "C8"]],
        ["Straight", "9", ["H9", "ST", "CJ", "SQ", "DK"]],
        ["Bomb", "6", ["H6", "S6", "C6", "C6"]],
        ["Bomb", "8", ["S8", "H8", "H8", "C8"]],
        ["ThreePair", "6", ["H6", "S6", "H7", "H7", "S8", "H8"]],
        ["ThreePair", "6", ["C6", "C6", "H7", "H7", "H8", "C8"]],
    ]


def test_structure_sprint_excludes_breaking_two_bombs():
    """GUA-142 定向：拆双炸的 667788 候选应被过滤，不命中冲刺。"""
    gs = build_gs()
    gs["_endgame_context"] = build_ec()
    d = EndgameDecider()
    acts = build_action_list()
    # 只留 ThreePair 候选，验证候选被过滤后不命中
    only_tp = [(i, a) for i, a in enumerate(acts) if a[0] == "ThreePair"]
    assert len(only_tp) == 2
    # 两次（两种 667788 组法）都应拆炸被过滤
    result = d._q1_free_lead_structure_sprint(gs, only_tp, build_ec())
    assert result is None, f"拆双炸的 ThreePair 不应被 GUA-142 选中；实际 {result}"


def test_action_breaks_bomb_detector():
    """定向：667788 从 6666/8888 各拆 2 张 → 判拆炸；纯对子/顺不判。"""
    hand = [
        "H6", "S6", "C6", "C6",
        "S8", "H8", "H8", "C8",
        "H9", "ST", "CJ", "SQ", "DK",
        "H7", "H7",
    ]
    three_pair = ["ThreePair", "6", ["H6", "S6", "H7", "H7", "S8", "H8"]]
    assert EndgameDecider._action_breaks_bomb_family(three_pair, hand) is True
    straight = ["Straight", "9", ["H9", "ST", "CJ", "SQ", "DK"]]
    assert EndgameDecider._action_breaks_bomb_family(straight, hand) is False
    pair = ["Pair", "7", ["H7", "H7"]]
    assert EndgameDecider._action_breaks_bomb_family(pair, hand) is False


def test_gua142_normal_path_still_works():
    """
    回归保护：GUA-142 正常用例——ThreePair 从 SF 组拆 2 张凑（非拆炸弹），
    出完后仍剩 SF 冲刺 → 应继续命中 ThreePair。
    """
    hand = [
        "H5", "C5", "S8", "D8", "S9", "S9", "D9",
        "ST", "HT", "CT", "SQ", "SK", "SJ", "SB", "HR",
    ]
    gs = {
        "curRank": "J",
        "handCards": list(hand),
        "myPos": 0,
        "curPos": -1,
        "greaterPos": -1,
        "greaterAction": None,
        "curAction": None,
        "numofplayers": [15, 9, 9, 9],
        "publicInfo": [{"rest": 15}, {"rest": 9}, {"rest": 9}, {"rest": 9}],
        "done": [],
        "stage": "play",
        "selfRank": "A",
        "oppoRank": "J",
        "_botzone_mode": True,
    }
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Pair", "5", ["H5", "C5"]],
        ["Pair", "8", ["S8", "D8"]],
        ["Trips", "9", ["S9", "S9", "D9"]],
        ["ThreePair", "T", ["S8", "D8", "S9", "D9", "HT", "CT"]],
        ["StraightFlush", "9", ["S9", "ST", "SJ", "SQ", "SK"]],
        ["Single", "B", ["SB"]],
        ["Single", "R", ["HR"]],
    ]
    d = EndgameDecider()
    ec = {
        "my_pos": 0,
        "cur_pos": -1,
        "cur_rank": "J",
        "numofplayers": [15, 9, 9, 9],
        "enemies": {
            1: {"remaining": 9, "danger_level": "低", "recommended_types": [],
                "banned_types": [], "baoshu": {}},
            3: {"remaining": 9, "danger_level": "低", "recommended_types": [],
                "banned_types": [], "baoshu": {}},
        },
        "teammate": {"remaining": 9, "is_close": False, "assist_prefer": []},
        "self": {"remaining": 15, "has_two_clean_hands": False,
                 "has_bomb": False, "should_sprint": False},
        "finished": [],
    }
    idx, act = d._q1_free_lead_structure_sprint(gs, action_list, ec)
    assert idx is not None, "GUA-142 正常路径（不拆炸）仍应命中"
    assert act[0] == "ThreePair", f"应保留 ThreePair 冲刺；实际 {act}"


def test_decide_integration_no_break_bomb():
    """decide() 集成：本局双炸手牌 → 不出拆双炸的 ThreePair/667788。"""
    gs = build_gs()
    gs["_endgame_context"] = build_ec()
    gs["_endgame_context"]["is_active"] = True
    d = EndgameDecider()
    idx, act = d.decide(gs, build_action_list())
    assert act is not None, "decide 应命中决策"
    assert act[0] != "ThreePair", f"拆双炸的 ThreePair 不应被出；实际 {act}"