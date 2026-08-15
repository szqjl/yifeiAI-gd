# -*- coding: utf-8 -*-
"""
GUA-241：残局冲刺判定纳入难压牌型——钢板(TwoTrips)/三连对(ThreePair)/8+顺子(Straight 起点≥8)。

关联：
  - GUA-142 `_has_structure_sprint_path`：剥掉「SF/≥4炸/钢板/三连对/8+顺子」后剩余点数组 ≤3 → 冲刺路径。
  - GUA-135 `_hand_has_sprint_capability`：无炸分支——整手恰好一手难压牌型（5 张 8+顺 / 6 张钢板或三连对）→ 冲刺能力。

match 6a7f2a3b0fbd680d7c743a3d（logs/v8_vs_botzone_20260814_224341.log）：
V8=player2 手牌 9 = 555666 钢板 + 99 + DA，Q1 未走 TwoTrips 冲刺而拆 666+55。
"""

from __future__ import annotations

from src.v.nn.endgame.endgame_decide import EndgameDecider


class TestFindHighRecoveryStructureCards:
    def test_two_trips_555666_found(self):
        hand = ["C5", "D5", "S5", "C6", "D6", "H6"]
        found = EndgameDecider._find_two_trips_cards(hand)
        assert found is not None
        assert len(found) == 6

    def test_two_trips_non_consecutive_none(self):
        """555 + 777（不连续三张）不是钢板。"""
        hand = ["C5", "D5", "S5", "C7", "D7", "H7"]
        assert EndgameDecider._find_two_trips_cards(hand) is None

    def test_three_pair_8899tt_found(self):
        hand = ["S8", "D8", "S9", "D9", "HT", "CT"]
        found = EndgameDecider._find_three_pair_cards(hand)
        assert found is not None
        assert len(found) == 6

    def test_three_pair_non_consecutive_none(self):
        """88 + JJ + QQ（不连续）不是三连对。"""
        hand = ["S8", "D8", "SJ", "DJ", "HQ", "CQ"]
        assert EndgameDecider._find_three_pair_cards(hand) is None

    def test_high_straight_8q_found(self):
        hand = ["S8", "C9", "HT", "DJ", "SQ"]
        found = EndgameDecider._find_high_straight_cards(hand)
        assert found is not None
        assert len(found) == 5

    def test_high_straight_9k_and_ta_found(self):
        assert EndgameDecider._find_high_straight_cards(
            ["C9", "CT", "HJ", "HQ", "DK"]
        ) is not None
        assert EndgameDecider._find_high_straight_cards(
            ["CT", "HJ", "HQ", "DK", "DA"]
        ) is not None

    def test_low_straight_7j_not_high(self):
        """7-J 顺起点 7<8，不算 8+ 顺。"""
        hand = ["S7", "S8", "S9", "ST", "SJ"]
        assert EndgameDecider._find_high_straight_cards(hand) is None


class TestHasStructureSprintPath:
    def test_steel_plate_plus_99_da_sprint_path(self):
        """match 真案：555666 钢板 + 99 + DA → 钢板冲刺路径成立。"""
        hand = ["C5", "D5", "S5", "C6", "D6", "H6", "H9", "C9", "DA"]
        assert EndgameDecider._has_structure_sprint_path(hand)

    def test_three_pair_plus_pair_sprint_path(self):
        """8899TT 三连对 + 对5 → 冲刺路径成立。"""
        hand = ["S8", "D8", "S9", "D9", "HT", "CT", "H5", "C5"]
        assert EndgameDecider._has_structure_sprint_path(hand)

    def test_high_straight_plus_da_sprint_path(self):
        """8-9-T-J-Q 顺 + DA → 冲刺路径成立。"""
        hand = ["S8", "C9", "HT", "DJ", "SQ", "DA"]
        assert EndgameDecider._has_structure_sprint_path(hand)

    def test_low_straight_7j_plus_pair_no_sprint_path(self):
        """7-J 顺（异花，非同花顺）起点 7<8 → 不成立。"""
        hand = ["S7", "H8", "C9", "DT", "SJ", "H5", "C5"]
        assert not EndgameDecider._has_structure_sprint_path(hand)

    def test_three_pair_plus_too_many_ranks_no_sprint_path(self):
        """剥 8899TT 后剩 4 种点（DA/HK/S2/C3）→ 不成立。"""
        hand = [
            "S8", "D8", "S9", "D9", "HT", "CT",
            "DA", "HK", "S2", "C3",
        ]
        assert not EndgameDecider._has_structure_sprint_path(hand)


class TestHandHasSprintCapability:
    def _has_sprint(self, hand):
        return EndgameDecider()._has_sprint_capability(hand)

    def test_high_straight_8q_has_sprint(self):
        """整手 5 张 8-Q 顺 = 一手难压尾牌 → 冲刺能力 ✓"""
        hand = ["S8", "C9", "HT", "DJ", "SQ"]
        assert self._has_sprint(hand) is True

    def test_high_straight_ta_has_sprint(self):
        hand = ["CT", "HJ", "HQ", "DK", "DA"]
        assert self._has_sprint(hand) is True

    def test_steel_plate_has_sprint(self):
        """整手 6 张钢板 555666 = 一手难压尾牌 → 冲刺能力 ✓"""
        hand = ["C5", "D5", "S5", "C6", "D6", "H6"]
        assert self._has_sprint(hand) is True

    def test_three_pair_has_sprint(self):
        """整手 6 张三连对 8899TT = 一手难压尾牌 → 冲刺能力 ✓"""
        hand = ["S8", "D8", "S9", "D9", "HT", "CT"]
        assert self._has_sprint(hand) is True

    def test_low_straight_7j_no_sprint(self):
        """7-J 顺起点 7<8 → 非冲刺（test_no_bomb_no_sprint 兼容）。"""
        hand = ["S7", "S8", "S9", "ST", "SJ"]
        assert self._has_sprint(hand) is False

    def test_non_consecutive_trips_no_sprint(self):
        """555+777 非连续三张 → 非冲刺。"""
        hand = ["C5", "D5", "S5", "C7", "D7", "H7"]
        assert self._has_sprint(hand) is False

    def test_steel_plate_plus_single_no_sprint(self):
        """钢板 + 散单 = 两手 → 非冲刺。"""
        hand = ["C5", "D5", "S5", "C6", "D6", "H6", "S2"]
        assert self._has_sprint(hand) is False
