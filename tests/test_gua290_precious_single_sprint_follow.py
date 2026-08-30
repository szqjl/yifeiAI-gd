# -*- coding: utf-8 -*-
"""
GUA-290: GUA-266 「只剩贵单且无干净回手 → PASS」欠「残局一手冲刺」豁免。

锚点：match=6a942e2d1b27100f38da1595（logs/v8_vs_botzone_20260830_...log 21:21:03）
  V8 手 3 张 = 小王 SB + 对级牌 S2,D2（curRank=2），上家敌 player3 出 Single/Q 冲刺在即。
  唯一够压是贵单 SB（S2 因 rank 在手 2 张被判拆对不算天然单）；_has_clean_followup_stopper
  认定「打出后剩 S2,D2 无再拦回手」→ dump-precious-no-stopper → PASS。
  实际上打出 SB 拿回领出权后，剩一对级牌 2 = 最大对，一手直推即可冲刺，根本不需要「回手」。
  同类：残局剩 对A/对级牌 + 小王 时应开贵单抢权冲刺，而非让敌免费放走。

用户定音（2026-08-30）：打出贵单后若剩余为「可一手冲刺的封顶结构」→ 应出贵单，不 PASS。
"""
from src.v.nn.endgame.endgame_decide import EndgameDecider


def _gs(hand):
    return {
        "handCards": hand,
        "curRank": "2",
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Single", "Q", ["SQ"]],
        "numofplayers": [3, 7, 14, 7],
        "publicInfo": [{"rest": n} for n in [3, 7, 14, 7]],
        "_botzone_mode": True,
        "_group_members": {
            -1: [c for c in hand if c not in ("S2", "D2", "SA", "DA")],
            0: [c for c in hand if c in ("S2", "D2")] or
               [c for c in hand if c in ("SA", "DA")],
        },
        "_group_gid_type_map": {0: "pair" if len(hand) == 3 else "pair"},
    }


def _candidates():
    return [
        ["PASS", "PASS", "PASS"],
        ["Single", "B", ["SB"]],
        ["Single", "2", ["S2"]],
        ["Single", "2", ["D2"]],
    ]


class TestGua290PreciousSingleSprintFollow:
    def test_sb_pair_level_two_follow_sprint(self):
        """手 SB+对2，上家敌出 Q → 出小王抢权，剩余对级牌直推，不前手 PASS。"""
        gs = _gs(["SB", "S2", "D2"])
        d = EndgameDecider()
        picked = d._q1_follow_no_dump_precious_single(
            gs, list(enumerate(_candidates())), ["Single", "Q", ["SQ"]],
        )
        assert picked is not None, "打出小王后对级牌可一手冲刺，不应 PASS"
        assert picked[1][0] == "Single" and picked[1][1] == "B", f"应出小王 SB，实际 {picked[1]}"

    def test_sb_pair_ace_follow_sprint(self):
        """手 SB+对A，同样残局冲刺态 → 出小王，剩余对A 直推。"""
        gs = _gs(["SB", "SA", "DA"])
        gs["_group_members"] = {-1: ["SB"], 0: ["SA", "DA"]}
        acts = [
            ["PASS", "PASS", "PASS"],
            ["Single", "B", ["SB"]],
            ["Single", "A", ["SA"]],
            ["Single", "A", ["DA"]],
        ]
        d = EndgameDecider()
        picked = d._q1_follow_no_dump_precious_single(
            gs, list(enumerate(acts)), ["Single", "Q", ["SQ"]],
        )
        assert picked is not None, "打出小王后对A 可一手冲刺，不应 PASS"
        assert picked[1][0] == "Single" and picked[1][1] == "B", f"应出小王 SB，实际 {picked[1]}"

    def test_sb_low_pair_keeps_pass(self):
        """打出贵单后剩余仅对低小牌（如对3）非冲刺态 → 保持原 GUA-266 PASS。"""
        gs = _gs(["SB", "S3", "D3"])
        gs["_group_members"] = {-1: ["SB"], 0: ["S3", "D3"]}
        acts = [
            ["PASS", "PASS", "PASS"],
            ["Single", "B", ["SB"]],
            ["Single", "3", ["S3"]],
            ["Single", "3", ["D3"]],
        ]
        d = EndgameDecider()
        picked = d._q1_follow_no_dump_precious_single(
            gs, list(enumerate(acts)), ["Single", "Q", ["SQ"]],
        )
        assert picked is not None and picked[1][0] == "PASS", f"对低小牌不应动用小王，实际 {picked[1]}"

    def test_no_natural_single_still_keeps_original_anchor(self):
        """原 GUA-266 锚点（唯一贵单 HR、剩一大把散/结构，无一手冲刺）→ 仍 PASS。"""
        hand = ["S7", "HR", "C4", "S4", "S8", "C8", "ST", "CT",
                "DA", "CA", "C2", "D2", "C2", "H3", "H3"]
        gs = {
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
        acts = [
            ["PASS", "PASS", "PASS"],
            ["Single", "7", ["S7"]],
            ["Single", "R", ["HR"]],
            ["Single", "A", ["DA"]],
            ["Single", "2", ["C2"]],
            ["Single", "T", ["ST"]],
            ["Single", "4", ["C4"]],
            ["Single", "8", ["S8"]],
        ]
        d = EndgameDecider()
        picked = d._q1_follow_no_dump_precious_single(
            gs, list(enumerate(acts)), ["Single", "8", ["H8"]],
        )
        assert picked is not None and picked[1][0] == "PASS", \
            f"原锚点无一手冲刺仍应 PASS，实际 {picked[1]}"