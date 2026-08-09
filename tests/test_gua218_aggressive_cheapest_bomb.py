# -*- coding: utf-8 -*-
"""GUA-218: GUA-205 抢攻选炸最廉优先。

场景复现：match v8_14_online_6a7772fb 回合11，2号出大王（Single/R），
V8 role=超强主攻，手牌含 Bomb/K + SF/D8-Q + SF/C3-C6。
修复前 GUA-205 mid_aggressive_bomb 走 _recommend_bomb_from_mask
（-strength 排序，同花顺永远第一）→ 用同花顺压单牌大王，浪费高价值火力。
修复后：先从 actionList 选最廉炸（Bomb/K 即可赢回合），保留同花顺。

注意：不带入 GUA-172 主路径的「单张王 PASS 优先」——抢攻意图下仍要炸。
"""

import logging

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _make_engine(*, role="超强主攻"):
    eng = UltimateWinRateEngineV7.__new__(UltimateWinRateEngineV7)
    eng.logger = logging.getLogger("test_gua218")
    eng.player_id = 0
    eng._card_mask = {}
    eng._group_type_map = {"Bomb": 1, "StraightFlush": 2}
    eng._group_members = {}
    eng._current_role = role
    eng._match_fail_type_mismatch = 0
    eng._match_fail_rank_mismatch = 0
    eng._match_fail_cards_mismatch = 0
    return eng


def _dispatch(engine, gs, *, greater_type="Single", greater_rank="R",
              is_teammate=False, is_upper=False, is_lower=False,
              teammate_pos=2):
    return engine._stage_mid_dispatch(
        gs,
        engine._card_mask,
        gs["handCards"],
        "2",
        greater_action=gs["greaterAction"],
        greater_type=greater_type,
        greater_rank=greater_rank,
        is_lead=False,
        is_teammate=is_teammate,
        is_upper=is_upper,
        is_lower=is_lower,
        teammate_pos=teammate_pos,
    )


class TestBranch2CheapestBomb:
    _ACTION_LIST = [
        ["Bomb", "K", ["SK", "CK", "DK", "HK"]],
        ["StraightFlush", "8", ["D8", "D9", "DT", "DJ", "DQ"]],
        ["StraightFlush", "9", ["D9", "DJ", "DK", "DQ", "DT"]],
    ]

    def _engine(self):
        engine = _make_engine()
        engine._recommend_min_press_impl = lambda *a, **k: None
        engine._recommend_max_press_impl = lambda *a, **k: None
        engine._r11_bomb_throttle_check = lambda *a, **k: (True, "critical_enemy")
        return engine

    def _gs(self, *, enemy_rem=6, cover=0.2, bomb_risk=0.1, greater_pos=1):
        return {
            "_current_stage": "stage_2",
            "_belief": {"hand_counts": {0: 19, 1: enemy_rem, 2: 12, 3: 8}},
            "_phase_relation": {
                "critical_enemy_seat": 1,
                "enemy_shape_hint": "structured",
                "teammate_cover_confidence": cover,
                "same_type_suppressor_outside": False,
                "enemy_bomb_risk_max": bomb_risk,
                "sprint_fire_ready": False,
            },
            "myPos": 0,
            "curPos": 1,
            "greaterPos": greater_pos,
            "greaterAction": ["Single", "R", ["HR"]],
            "actionList": [list(a) for a in self._ACTION_LIST],
            "handCards": ["SK", "CK", "DK", "HK",
                          "D8", "D9", "DT", "DJ", "DQ",
                          "C3", "C4", "C5", "C6", "H2",
                          "HA", "D2", "D4", "S5", "SB"],
            "curRank": "2",
        }

    def test_aggressive_bomb_uses_cheapest_bomb(self):
        """抢攻炸单牌大王 → 选最廉炸（Bomb/K），不用同花顺"""
        engine = self._engine()
        gs = self._gs()
        rec = _dispatch(engine, gs, greater_type="Single", is_lower=True)
        assert rec is not None
        assert rec["type"] == "Bomb"
        assert rec["rank"] == "K"
        assert rec["intent"] == "mid_aggressive_bomb"

    def test_aggressive_bomb_uses_cheapest_bomb_upper(self):
        """is_upper 分支同样最廉优先"""
        engine = self._engine()
        gs = self._gs(greater_pos=3)
        rec = _dispatch(engine, gs, greater_type="Single", is_upper=True)
        assert rec is not None
        assert rec["type"] == "Bomb"
        assert rec["rank"] == "K"
        assert rec["intent"] == "mid_aggressive_bomb"

    def test_fallback_to_strongest_when_no_action_list(self):
        """actionList 缺失 → 回退 _recommend_bomb_from_mask（拿权最大化）"""
        engine = self._engine()
        engine._recommend_bomb_from_mask = lambda *a, **k: {
            "type": "StraightFlush",
            "rank": "8",
            "cards": ["D8", "D9", "DT", "DJ", "DQ"],
        }
        gs = self._gs()
        gs["actionList"] = []
        rec = _dispatch(engine, gs, greater_type="Single", is_lower=True)
        assert rec is not None
        assert rec["type"] == "StraightFlush"
        assert rec["intent"] == "mid_aggressive_bomb"


class TestCheapestBombSelection:
    """_recommend_cheapest_bomb_from_action_list 选择口径（GUA-172 原型）"""

    def _engine(self):
        return _make_engine()

    def test_bomb_beats_sf_in_cheapest_order(self):
        """最廉排序：4星炸(4) < 同花顺(9) → 选 Bomb/K"""
        eng = self._engine()
        action_list = [
            ["Bomb", "K", ["SK", "CK", "DK", "HK"]],
            ["StraightFlush", "8", ["D8", "D9", "DT", "DJ", "DQ"]],
            ["StraightFlush", "9", ["D9", "DJ", "DK", "DQ", "DT"]],
        ]
        rec = eng._recommend_cheapest_bomb_from_action_list(action_list, "2")
        assert rec["type"] == "Bomb"
        assert rec["rank"] == "K"

    def test_lowest_rank_bomb_preferred(self):
        """多个 4 星炸 → 选 rank 最低者"""
        eng = self._engine()
        action_list = [
            ["Bomb", "K", ["SK", "CK", "DK", "HK"]],
            ["Bomb", "7", ["S7", "H7", "D7", "C7"]],
        ]
        rec = eng._recommend_cheapest_bomb_from_action_list(action_list, "2")
        assert rec["type"] == "Bomb"
        assert rec["rank"] == "7"
