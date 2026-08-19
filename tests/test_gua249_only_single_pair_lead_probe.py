# -*- coding: utf-8 -*-
"""
GUA-249: 残局敌剩 6/7 张 + 本方仅单/对 → 先探后克（对子克 5 张）单元测试

背景（用户 2026-08-19 定音，本地 demo 实测）：
  敌方剩 6/7 张时 `endgame_rule` 推荐全是整牌型（6 → `[ThreePair,TwoTrips,Straight,Trips]`；
  7 → `[Straight,TwoTrips,ThreePair]`），本方仅单/对（候选只有 Single/Pair/PASS）时
  ④ recommended 过滤空 → ⑤ baoshu 无 → ⑥ 任意 non_banned 回收优先兜底。
  实测：敌7 领出全对四手（`33 44 88 99`）拆对 `Single/8`（留 8 回收）——拆散对子结构、
  非对子克 5 张起点。

修复（GUA-249，`_q1_only_single_pair_lead_probe`，插 GUA-239 之后）：
  触发：① `_is_my_q1_lead_turn`（自由领出）+ ② 下家 `(my_pos+1)%4` 敌方且剩 6 或 7 张
  + ③ 本方候选仅 Single/Pair/PASS（无炸/无整牌结构）+ ④ 对子 ≥1 →
  若有天然单 → 出最小天然单试探（保留对子回手，先探后克）；
  无天然单（全对）→ 直接出最小对子（对子克 5 张起点）。
"""
import pytest

from src.v.nn.endgame.endgame_decide import EndgameDecider


def build_gs():
    """敌7（下家 P1）领出 + 本方全对四手（33 44 88 99）→ 应出最小对子 Pair/3。"""
    return {
        "curRank": "2",
        "handCards": ["C3", "D3", "H4", "S4", "H8", "S8", "D9", "C9"],
        "myPos": 0,
        "curPos": 0,
        "greaterPos": -1,
        "greaterAction": None,
        "curAction": None,
        "numofplayers": [8, 7, 15, 13],
        "publicInfo": [
            {"rest": 8}, {"rest": 7}, {"rest": 15}, {"rest": 13},
        ],
        "done": [],
        "stage": "play",
        "selfRank": "2",
        "oppoRank": "2",
        "_botzone_mode": True,
        "_group_members": {
            0: ["C3", "D3"],
            1: ["H4", "S4"],
            2: ["H8", "S8"],
            3: ["D9", "C9"],
        },
        "_group_gid_type_map": {0: "pair", 1: "pair", 2: "pair", 3: "pair"},
    }


def build_ec(enemy_rem=7):
    return {
        "my_pos": 0,
        "cur_pos": 0,
        "cur_rank": "2",
        "numofplayers": [8, enemy_rem, 15, 13],
        "enemies": {
            1: {"remaining": enemy_rem, "danger_level": "低",
                "recommended_types": ["Straight", "TwoTrips", "ThreePair"],
                "banned_types": [], "baoshu": {}},
            3: {"remaining": 13, "danger_level": "低",
                "recommended_types": [], "banned_types": [], "baoshu": {}},
        },
        "teammate": {"remaining": 15, "is_close": False, "assist_prefer": []},
        "self": {"remaining": 8, "has_two_clean_hands": False,
                 "has_bomb": False, "should_sprint": False},
        "finished": [],
    }


def build_action_list():
    return [
        ["PASS", "PASS", "PASS"],
        ["Single", "3", ["C3"]],
        ["Single", "4", ["H4"]],
        ["Single", "8", ["H8"]],
        ["Single", "9", ["D9"]],
        ["Pair", "3", ["C3", "D3"]],
        ["Pair", "4", ["H4", "S4"]],
        ["Pair", "8", ["H8", "S8"]],
        ["Pair", "9", ["D9", "C9"]],
    ]


def test_full_pair_hand_picks_min_pair():
    """复现场景：敌7 领出 + 本方全对（无天然单）→ 出最小对子 Pair/3，非拆对 Single/8。"""
    gs = build_gs()
    d = EndgameDecider()
    result = d._q1_only_single_pair_lead_probe(
        gs, list(enumerate(build_action_list())), build_ec(7),
    )
    assert result is not None, "GUA-249 应命中（返回 None 表示未命中）"
    idx, act = result
    assert act[0] == "Pair", f"全对应出最小对子；实际 {act}"
    assert act[1] == "3", f"应出最小对子 3；实际 {act}"


def test_single_pair_mix_picks_min_natural_single():
    """敌6 领出 + 本方两对+三单 → 有天然单 → 出最小天然单试探（先探后克）。"""
    gs = build_gs()
    gs["handCards"] = ["C3", "D3", "H4", "S4", "S6", "D7", "C9"]
    gs["_group_members"] = {
        0: ["C3", "D3"],
        1: ["H4", "S4"],
        -1: ["S6", "D7", "C9"],
    }
    gs["_group_gid_type_map"] = {0: "pair", 1: "pair"}
    gs["numofplayers"] = [7, 6, 15, 13]
    ec = build_ec(6)
    ec["numofplayers"] = [7, 6, 15, 13]
    ec["enemies"][1]["remaining"] = 6
    ec["enemies"][1]["danger_level"] = "中"
    ec["enemies"][1]["recommended_types"] = ["ThreePair", "TwoTrips", "Straight", "Trips"]
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "3", ["C3"]],
        ["Single", "4", ["H4"]],
        ["Single", "6", ["S6"]],
        ["Single", "7", ["D7"]],
        ["Single", "9", ["C9"]],
        ["Pair", "3", ["C3", "D3"]],
        ["Pair", "4", ["H4", "S4"]],
    ]
    d = EndgameDecider()
    result = d._q1_only_single_pair_lead_probe(gs, list(enumerate(action_list)), ec)
    assert result is not None, "GUA-249 应命中"
    idx, act = result
    assert act[0] == "Single", f"混合单对应先出最小天然单试探；实际 {act}"
    assert act[1] == "6", f"应出最小天然单 6（S6）；实际 {act}"


def test_downseat_not_six_or_seven_no_trigger():
    """下家剩 5 或 8 张 → 不触发。"""
    for rem in (5, 8):
        gs = build_gs()
        gs["numofplayers"] = [8, rem, 15, 13]
        ec = build_ec(rem)
        ec["numofplayers"] = [8, rem, 15, 13]
        ec["enemies"][1]["remaining"] = rem
        d = EndgameDecider()
        assert d._q1_only_single_pair_lead_probe(gs, build_action_list(), ec) is None


def test_not_lead_turn_no_trigger():
    """非自由领出（跟牌轮）→ 不触发。"""
    gs = build_gs()
    ec = build_ec(7)
    gs["curPos"] = 0
    gs["greaterPos"] = 1
    gs["greaterAction"] = ["Single", "5", ["S5"]]
    gs["curAction"] = ["Single", "5", ["S5"]]
    ec["cur_pos"] = 1
    d = EndgameDecider()
    assert d._q1_only_single_pair_lead_probe(gs, build_action_list(), ec) is None


def test_has_bomb_structure_no_trigger():
    """本方有整牌结构（Trips 三张）→ 不触发（GUA-239 等负责）。"""
    gs = build_gs()
    gs["handCards"] = ["C3", "D3", "H4", "S4", "H8", "S8", "C8", "D9", "C9"]
    gs["_group_members"] = {
        0: ["C3", "D3"], 1: ["H4", "S4"], 2: ["H8", "S8", "C8"], 3: ["D9", "C9"],
    }
    gs["_group_gid_type_map"] = {0: "pair", 1: "pair", 2: "trips", 3: "pair"}
    gs["numofplayers"] = [9, 7, 15, 13]
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "3", ["C3"]],
        ["Single", "4", ["H4"]],
        ["Single", "8", ["H8"]],
        ["Single", "9", ["D9"]],
        ["Pair", "3", ["C3", "D3"]],
        ["Pair", "4", ["H4", "S4"]],
        ["Pair", "8", ["H8", "S8"]],
        ["Pair", "9", ["D9", "C9"]],
        ["Trips", "8", ["H8", "S8", "C8"]],
    ]
    ec = build_ec(7)
    ec["numofplayers"] = [9, 7, 15, 13]
    d = EndgameDecider()
    # 候选含 Trips → 非「仅单/对」→ 不触发 GUA-249
    assert d._q1_only_single_pair_lead_probe(gs, list(enumerate(action_list)), ec) is None


def test_decide_returns_min_pair_not_pass():
    """decide() 集成：Q1 命中 GUA-249 出 Pair/3 → 不被转 PASS/不被拆对。"""
    gs = build_gs()
    gs["_endgame_context"] = build_ec(7)
    gs["_endgame_context"]["is_active"] = True
    d = EndgameDecider()
    idx, act = d.decide(gs, build_action_list())
    assert act is not None, "decide 应命中 Q1 GUA-249"
    assert act[0] == "Pair", f"应出对子；实际 {act}"
    assert act[1] == "3", f"应出最小对子 3；实际 {act}"