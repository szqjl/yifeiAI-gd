# -*- coding: utf-8 -*-
"""GUA-287 手多禁领出甩炸（A 修复 `_remainder_is_one_structure` 连续性 + B Q0 领出护栏）。

真源：match `6a927cbd1b27100f38d87a27`（`logs/v8_vs_botzone_20260829_142042.log` 14:31:41-42）。
V8 手牌 15 = 5×7炸 + 4×5炸 + 对6 + 对T + 王对。`_hand_has_sprint_capability` 判 True——
剥双炸后剩 6 张 counts=[2,2,2]，ranks 6/T/HR **不连续**，却被 `_remainder_is_one_structure`
当成三连对（ThreePair）一手 → should_sprint → Q0 领出连续甩 Bomb/5、Bomb/7，空甩成散单连输。

用户口径（2026-08-29）：有炸 + 手多（非两手清）→ 炸**不出**领出轮；先整牌锁窗（GUA-107）
→ 单诱拆（GUA-220 Tier 2）。下家剩 2 + 我方一手清 / 两手整牌，才走 Q0 冲刺且先结构后炸。

A 修复：`_remainder_is_one_structure` 对 [3,3]/[2,2,2] 校验 rank 连续性（钢板/三连对须连续）。
B 护栏：`_q0_self_sprint` 领出轮手牌>5 且语义手数>2（非两手清）→ 禁冲刺甩炸，落回 Q1。
"""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.endgame.endgame_decide import EndgameDecider

logging.getLogger("endgame_decider").setLevel(logging.CRITICAL)

# 复现局 14:31:41 时 V8 手牌（req history 重建）：
# 5×7炸 + 4×5炸 + 对6(C6,D6) + 对T(DT,HT) + 王对(HR,HR)
HAND_REPRO_15 = [
    "C5", "C6", "C7", "C7", "D6", "D7", "DT", "H5",
    "H5", "H7", "HR", "HR", "HT", "S5", "S7",
]

HAND_REPRO_11 = [
    "C6", "C7", "C7", "D6", "D7", "DT", "H7", "HR", "HR", "HT", "S7",
]


# ───────────────────────── A：_remainder_is_one_structure 连续性 ─────────────────────────

class TestGua287RemainderIsOneStructureConsecutive:
    """6 张剥炸剩余牌，必须 rank 连续才算整手一手（三连对/钢板）。"""

    def test_non_consecutive_222_not_three_pair(self):
        """对6+对T+王对（6/T/HR 非连续）→ 非三连对一手 → False"""
        cards = ["C6", "D6", "DT", "HT", "HR", "HR"]
        assert EndgameDecider._remainder_is_one_structure(cards) is False

    def test_consecutive_222_is_three_pair(self):
        """对6+对7+对8 连续 → 三连对一手 → True"""
        cards = ["C6", "D6", "C7", "D7", "C8", "D8"]
        assert EndgameDecider._remainder_is_one_structure(cards) is True

    def test_non_consecutive_33_not_steel_plate(self):
        """三4+三K（非连续）→ 非钢板一手 → False"""
        cards = ["C4", "H4", "S4", "CK", "HK", "SK"]
        assert EndgameDecider._remainder_is_one_structure(cards) is False

    def test_consecutive_33_is_steel_plate(self):
        """三7+三8 连续 → 钢板一手 → True"""
        cards = ["C7", "H7", "S7", "C8", "H8", "S8"]
        assert EndgameDecider._remainder_is_one_structure(cards) is True

    def test_six_same_rank_bomb(self):
        """6 星炸（6 张同点）→ True"""
        cards = ["C4", "D4", "H4", "S4", "C4", "D4"]
        assert EndgameDecider._remainder_is_one_structure(cards) is True


class TestGua287SprintCapabilityRegression:
    """修复后 `_hand_has_sprint_capability`：手多（对6+对T+王对）不再误判冲刺。"""

    def test_hand15_not_sprint_capable(self):
        """复现局 15 张：5×7炸+4×5炸+对6+对T+王对 → 非两手清 → 不判冲刺"""
        assert EndgameDecider._hand_has_sprint_capability(list(HAND_REPRO_15)) is False

    def test_hand11_not_sprint_capable(self):
        """复现局 11 张（出 SB 后）：5×7炸+对6+对T+王对 → 不判冲刺"""
        assert EndgameDecider._hand_has_sprint_capability(list(HAND_REPRO_11)) is False

    def test_two_clean_bomb_plus_straight_still_sprint(self):
        """不误伤：炸(Bomb/K)+单手顺(8-Q) → 仍判冲刺（两手整牌清）"""
        hand = ["SK", "HK", "CK", "DK", "H8", "H9", "HT", "HJ", "SQ"]
        assert EndgameDecider._hand_has_sprint_capability(hand) is True

    def test_three_consecutive_pairs_still_sprint(self):
        """不误伤：炸+连续三连对（对6/7/8）→ 仍判冲刺"""
        hand = ["SK", "HK", "CK", "DK", "C6", "D6", "C7", "D7", "C8", "D8"]
        assert EndgameDecider._hand_has_sprint_capability(hand) is True


# ───────────────────────── B：Q0 领出手多禁甩炸护栏 ─────────────────────────

def _lead_gs(hand_cards, action_list, gmap=None):
    """领出轮 game_state（GUA-221 同款）：上一手为 V8 自己 → is_my_turn=True。"""
    gs = {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": -1,
        "greaterAction": ["Single", "7", ["H7"]],
        "handCards": list(hand_cards),
        "actionList": [list(a) for a in action_list],
        "curRank": "5",
    }
    if gmap is not None:
        gs["_group_type_map"] = dict(gmap)
    return gs


def _ec(enemy1_remaining):
    return {
        "my_pos": 0,
        "enemies": {1: {"remaining": enemy1_remaining}, 3: {"remaining": 0}},
        "teammate": {},
    }


class TestGua287LeadBombGuardActive:
    """`_q0_lead_bomb_guard_active`：手牌>5 且语义手数>2 → 领出禁甩炸。"""

    def test_active_many_hands(self):
        """手 15 + 语义 5 手（双炸+3 对）→ 激活"""
        gs = _lead_gs(HAND_REPRO_15, [["PASS", "PASS", "PASS"]],
                      gmap={"Bomb": 2, "pair": 3})
        assert EndgameDecider()._q0_lead_bomb_guard_active(gs) is True

    def test_inactive_two_clean_hands(self):
        """手 9 = Bomb/K+顺（语义 2 手两手整牌）→ 不激活，冲刺保留"""
        gs = _lead_gs(
            ["SK", "HK", "CK", "DK", "H8", "H9", "HT", "HJ", "SQ"],
            [["PASS", "PASS", "PASS"]],
            gmap={"Bomb": 1, "straight": 1},
        )
        assert EndgameDecider()._q0_lead_bomb_guard_active(gs) is False

    def test_inactive_short_hand(self):
        """手 5（bomb+单）→ 不激活"""
        gs = _lead_gs(["SK", "HK", "CK", "DK", "H8"], [["PASS", "PASS", "PASS"]],
                      gmap={"Bomb": 1, "scatter": 1})
        assert EndgameDecider()._q0_lead_bomb_guard_active(gs) is False

    def test_inactive_without_group_map(self):
        """无 _group_type_map（单元测试构造）→ 不激活，保持旧行为"""
        assert EndgameDecider()._q0_lead_bomb_guard_active(_lead_gs(HAND_REPRO_15, [])) is False


class TestGua287Q0SelfSprintLeadGuard:
    """`_q0_self_sprint` 领出轮：手多非两手清 → 拦截甩炸（B 护栏）。"""

    def test_repro_hand_leads_returns_none_no_bomb(self):
        """复现局 15 张 + 语义>2 → 领出不甩 Bomb（护栏 return None，落回 Q1）"""
        gs = _lead_gs(
            HAND_REPRO_15,
            [
                ["PASS", "PASS", "PASS"],
                ["Bomb", "5", ["C5", "H5", "H5", "S5"]],
                ["Bomb", "7", ["C7", "C7", "D7", "H7", "S7"]],
                ["Pair", "6", ["C6", "D6"]],
                ["Pair", "T", ["DT", "HT"]],
                ["Pair", "R", ["HR", "HR"]],
            ],
            gmap={"Bomb": 2, "pair": 3},
        )
        res = EndgameDecider()._q0_self_sprint(gs, gs["actionList"], _ec(1))
        assert res is None, f"手多非两手清领出应禁甩炸落回 Q1；实际 {res}"

    def test_two_clean_bomb_first_still_led(self):
        """两手整牌（Bomb/K+顺）→ 护栏不拦，仍先炸领出（GUA-221 语义保持）"""
        gs = _lead_gs(
            ["SK", "HK", "CK", "DK", "H8", "H9", "HT", "HJ", "SQ"],
            [
                ["PASS", "PASS", "PASS"],
                ["Bomb", "K", ["SK", "HK", "CK", "DK"]],
                ["Single", "8", ["H8"]],
                ["Straight", "8", ["H8", "H9", "HT", "HJ", "SQ"]],
            ],
            gmap={"Bomb": 1, "straight": 1},
        )
        res = EndgameDecider()._q0_self_sprint(gs, gs["actionList"], _ec(5))
        assert res is not None
        idx, act = res
        assert act[0] == "Bomb", f"两手整牌应仍先炸领出；实际 {act}"