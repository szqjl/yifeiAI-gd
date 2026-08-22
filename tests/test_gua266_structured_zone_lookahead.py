# -*- coding: utf-8 -*-
"""
GUA-266: 敌方 6/7/8 张结构区 — 拦截看可能牌型与拦完能否再拦，禁止机械最大单。

锚点：
  match=6a890699 10:17:13 跟上家 Single/8 出 HR（手有对/TWT 无炸，拦完无回手）
  match=6a890546 10:11:38 领出有 Straight 却打级牌 Single/C2
"""
from src.v.nn.endgame.endgame_decide import EndgameDecider


def _ec(*, down=7, other=12, my=15):
    rec7 = ["Straight", "TwoTrips", "ThreePair"]
    return {
        "is_active": True,
        "my_pos": 0,
        "cur_pos": 0,
        "cur_rank": "2",
        "numofplayers": [my, down, 14, other],
        "enemies": {
            1: {"remaining": down, "danger_level": "低",
                "recommended_types": rec7, "banned_types": [], "baoshu": {}},
            3: {"remaining": other, "danger_level": "低",
                "recommended_types": rec7 if other in (6, 7, 8) else [],
                "banned_types": [], "baoshu": {}},
        },
        "teammate": {"remaining": 14, "is_close": False, "assist_prefer": []},
        "self": {"remaining": my, "has_two_clean_hands": False,
                 "has_bomb": False, "should_sprint": False},
        "finished": [],
    }


def _lead_gs():
    hand = ["H3", "D8", "DQ", "C2", "C9", "DT", "CJ", "SQ"]
    return {
        "handCards": hand,
        "curRank": "2",
        "myPos": 0,
        "curPos": 0,
        "greaterPos": -1,
        "greaterAction": [],
        "numofplayers": [8, 7, 14, 10],
        "publicInfo": [{"rest": n} for n in [8, 7, 14, 10]],
        "_botzone_mode": True,
        "_group_members": {
            -1: ["H3", "DQ", "C2"],
            0: ["D8", "C9", "DT", "CJ", "SQ"],
        },
        "_group_gid_type_map": {0: "straight"},
    }


def _lead_actions():
    return [
        ["Single", "3", ["H3"]],
        ["Single", "8", ["D8"]],
        ["Single", "Q", ["DQ"]],
        ["Single", "2", ["C2"]],
        ["Straight", "8", ["D8", "C9", "DT", "CJ", "SQ"]],
    ]


def _follow_gs():
    hand = ["S7", "HR", "C4", "S4", "S8", "C8", "ST", "CT",
            "DA", "CA", "C2", "D2", "C2", "H3", "H3"]
    return {
        "handCards": hand,
        "curRank": "2",
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Single", "8", ["H8"]],
        "numofplayers": [15, 7, 14, 8],
        "publicInfo": [{"rest": n} for n in [15, 7, 14, 8]],
        "_botzone_mode": True,
        "_group_members": {
            -1: ["S7", "HR"],
            0: ["C4", "S4"],
            1: ["S8", "C8"],
            2: ["ST", "CT"],
            3: ["DA", "CA"],
            4: ["C2", "D2", "C2"],
            5: ["H3", "H3"],
        },
        "_group_gid_type_map": {
            0: "pair", 1: "pair", 2: "pair", 3: "pair",
            4: "trip_in_three_with_two", 5: "pair_in_three_with_two",
        },
    }


def _follow_actions():
    return [
        ["PASS", "PASS", "PASS"],
        ["Single", "7", ["S7"]],
        ["Single", "R", ["HR"]],
        ["Single", "A", ["DA"]],
        ["Single", "2", ["C2"]],
        ["Single", "T", ["ST"]],
        ["Single", "4", ["C4"]],
        ["Single", "8", ["S8"]],
    ]


class TestGua266StructuredZoneLookahead:
    def test_lead_with_straight_not_level_single(self):
        """锚点 6a890546：下家 7 + 手有顺 → 出 Straight，不出 C2。"""
        gs = _lead_gs()
        gs["_endgame_context"] = _ec(down=7, other=10, my=8)
        d = EndgameDecider()
        idx, act = d.decide(gs, _lead_actions())
        assert act[0] == "Straight", f"应出顺锁 7 张结构区，实际 {act}"

    def test_follow_only_precious_beats_then_pass(self):
        """锚点 6a890699：压 Single/8 只有 HR/拆对 A/拆级牌 能压，无干净回手 → PASS。"""
        gs = _follow_gs()
        gs["_endgame_context"] = _ec(down=7, other=8, my=15)
        d = EndgameDecider()
        cands = list(enumerate(_follow_actions()))
        filtered = d._filter_q1_core_break_candidates(cands, gs)
        hit = d._q1_structured_zone_lookahead(
            gs, filtered, gs["_endgame_context"], 1,
            gs["_endgame_context"]["enemies"][1],
        )
        assert hit is not None
        assert hit[1][0] == "PASS", f"无回手不应甩大王，实际 {hit[1]}"

    def test_follow_scatter_beats_uses_min_not_joker(self):
        """结构区跟压：有普通散单 9 能压 8 → 出 9，不出 HR。"""
        gs = _follow_gs()
        gs["handCards"] = gs["handCards"] + ["H9"]
        gs["_group_members"][-1] = ["S7", "HR", "H9"]
        gs["_endgame_context"] = _ec(down=7, other=8, my=16)
        actions = _follow_actions() + [["Single", "9", ["H9"]]]
        d = EndgameDecider()
        hit = d._q1_structured_zone_lookahead(
            gs, list(enumerate(actions)), gs["_endgame_context"], 1,
            gs["_endgame_context"]["enemies"][1],
        )
        assert hit is not None
        assert hit[1][0] == "Single" and hit[1][1] == "9", f"应最小够压 9，实际 {hit[1]}"

    def test_enemy_one_does_not_pass(self):
        """报单剩 1 不介入，交给 GUA-222 最大单。"""
        gs = _follow_gs()
        ec = _ec(down=1, other=8, my=15)
        ec["enemies"][1]["remaining"] = 1
        ec["enemies"][1]["recommended_types"] = ["最大单张"]
        gs["_endgame_context"] = ec
        gs["numofplayers"] = [15, 1, 14, 8]
        d = EndgameDecider()
        hit = d._q1_structured_zone_lookahead(
            gs, list(enumerate(_follow_actions())), ec, 1, ec["enemies"][1],
        )
        assert hit is None
