# -*- coding: utf-8 -*-
"""GUA-288：残局 Q1 炸弹选择纳入「借核心组牌凑炸」代价。

锚点：match=6a92e4aa1b27100f38d8bd94（logs/v8_vs_botzone_20260829_170634.log
21:55:16）：上家敌出 Pair/A 后剩 2 张，V8 手 14 张 = 6星J炸 + 唯一核心
StraightFlush[H5,H6,H7,H2,H9] + trips[CT,ST,ST]。Q1 排序 `_bomb_min_sufficient_key`
按「张数少优先」选中 Bomb/T=[CT,ST,ST,H2]——H2 是配子，从唯一同花顺借走凑 4 头炸；
`_action_breaks_core_structure` 对 bomb-like 一律豁免（GUA-206 完整炸=压制）
→ 放行。H2 出手后同花顺只剩 5/6/7/9 四张散单 → 输（scores=[0,3,0,3]）。

用户定音（2026-08-29，方案 A）：把「借配子/拆唯一核心」代价纳入 Q1 炸弹排序
（有整核炸时优先于借核凑炸），而非绝对禁用（GUA-278 危急截断仍可用）。
"""

import pytest

from src.v.nn.endgame.endgame_decide import (
    EndgameDecider,
    _bomb_disrupts_core_group,
    _sort_q1_block_candidates,
)
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor

J_CORE_6 = ["CJ", "DJ", "HJ", "HJ", "SJ", "SJ"]
SF_5_9 = ["H5", "H6", "H7", "H2", "H9"]
TRIPS_T = ["CT", "ST", "ST"]
BOMB_T_BORROW = ["CT", "ST", "ST", "H2"]  # 借 H2（红桃配子）凑 4 头 10 炸
PAIR_A = ["HA", "DA"]


def _state(*, hand_cards, action_list, greater_pos=3):
    """21:55:16 残局帧骨架：V8=pos0，上家敌(3) 跟压 Pair/A。"""
    return {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": greater_pos,
        "greaterAction": ["Pair", "A", PAIR_A],
        "handCards": list(hand_cards),
        "actionList": action_list,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "numofplayers": [9, 11, 6, 2],
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


class TestDisruptsCoreGroup:
    def test_borrow_wild_from_sf_flagged(self):
        """Bomb/T=[CT,ST,ST,H2] 借 H2（属核心 StraightFlush）且 SF 未整组消耗 → True。"""
        gs = _state(hand_cards=J_CORE_6 + SF_5_9 + TRIPS_T, action_list=[])
        assert _bomb_disrupts_core_group(gs, ["Bomb", "T", BOMB_T_BORROW]) is True

    def test_intact_core_bomb_not_flagged(self):
        """6 星 J 炸整组消耗 g0（Bomb）→ 完整核心整牌，False。"""
        gs = _state(hand_cards=J_CORE_6 + SF_5_9 + TRIPS_T, action_list=[])
        assert _bomb_disrupts_core_group(gs, ["Bomb", "J", J_CORE_6]) is False

    def test_no_group_members_no_flag(self):
        """无 _group_members（单元态）→ 不误伤，False。"""
        gs = _state(hand_cards=J_CORE_6 + SF_5_9 + TRIPS_T, action_list=[])
        gs.pop("_group_members")
        assert _bomb_disrupts_core_group(gs, ["Bomb", "T", BOMB_T_BORROW]) is False

    def test_non_bomb_action_false(self):
        """非炸弹动作不进作用域。"""
        gs = _state(hand_cards=J_CORE_6 + SF_5_9 + TRIPS_T, action_list=[])
        assert _bomb_disrupts_core_group(gs, ["Pair", "A", PAIR_A]) is False


class TestSortOrder:
    def test_intact_bomb_before_borrowing_bomb(self):
        """21:55:16 态：整核 6 星 J 炸必须排在借配炸 Bomb/T 之前。"""
        gs = _state(hand_cards=J_CORE_6 + SF_5_9 + TRIPS_T, action_list=[])
        items = [
            (0, ["PASS", "PASS", "PASS"]),
            (1, ["Bomb", "J", J_CORE_6]),
            (2, ["Bomb", "T", BOMB_T_BORROW]),
            (3, ["StraightFlush", "5", SF_5_9]),
        ]
        out = _sort_q1_block_candidates(
            list(items), gs["handCards"], gs,
        )
        bombs = [a for _, a in out if a[0] == "Bomb"]
        assert bombs[0][1] == "J", f"整核炸应优先，实际首个炸弹={bombs[0]}"

    def test_no_groups_keeps_cheapest_first(self):
        """无组牌态：保留旧行为（最省炸优先，张数少在前），GUA-288 不引入回归。"""
        gs = _state(hand_cards=J_CORE_6 + SF_5_9 + TRIPS_T, action_list=[])
        gs.pop("_group_members")
        gs.pop("_group_gid_type_map")
        items = [
            (1, ["Bomb", "J", J_CORE_6]),
            (2, ["Bomb", "T", BOMB_T_BORROW]),
        ]
        out = _sort_q1_block_candidates(list(items), gs["handCards"], gs)
        bombs = [a for _, a in out if a[0] == "Bomb"]
        assert bombs[0][1] == "T", "无组态下保持原最省炸排序（T 炸 4 张 < J 炸 6 张）"


class TestQ1BombChoice:
    def test_q1_does_not_choose_borrowing_bomb(self):
        """端到端：复现 21:55:16 帧 → Q1 不再选中 Bomb/T（借配炸）。"""
        hand_cards = J_CORE_6 + SF_5_9 + TRIPS_T
        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Bomb", "J", [c for c in J_CORE_6]],
            ["Bomb", "T", [c for c in BOMB_T_BORROW]],
            ["StraightFlush", "5", [c for c in SF_5_9]],
        ]
        gs = _state(hand_cards=hand_cards, action_list=action_list)
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert act[0] != "Bomb" or act[1] != "T" or act[2] != BOMB_T_BORROW, (
            f"借配炸被选中: act={act}"
        )