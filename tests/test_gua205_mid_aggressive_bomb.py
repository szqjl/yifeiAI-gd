# -*- coding: utf-8 -*-
"""GUA-205: 超强手牌（bombs>=3 或 role=超强主攻）中局主动开炸抢攻。

支线1：队友已持 great（greaterPos==teammate）→ 一律让道不炸，
       无论队友出什么牌型（含大小王/炸弹高控），用炸弹抢队友控制权
       都是损己利敌，不依赖队友剩牌或所出牌型。
支线2：敌方出普通牌型 + 敌方非报单临界 + 队友接不住 → 按开炸价值主动炸。
"""

import logging

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _make_engine(*, role="主攻"):
    eng = UltimateWinRateEngineV7.__new__(UltimateWinRateEngineV7)
    eng.logger = logging.getLogger("test_gua205")
    eng.player_id = 0
    eng._card_mask = {}
    eng._group_type_map = {"Bomb": 2, "StraightFlush": 1}
    eng._group_members = {}
    eng._current_role = role
    eng._dynamic_regroup_enabled = False
    eng._match_fail_type_mismatch = 0
    eng._match_fail_rank_mismatch = 0
    eng._match_fail_cards_mismatch = 0
    return eng


def _build_action_list(*actions):
    result = [[a_type, a_rank, cards] for a_type, a_rank, cards in actions]
    result.append(["PASS", "PASS", "PASS"])
    return result


def _dispatch(engine, gs, *, greater_type="Pair", greater_rank="T",
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


# ════════════════════════════════════════════
#  支线1：队友持 great（greaterPos==teammate）→ 一律让道不炸
#  队友已获得控制权，无论出什么牌都不能用炸弹抢（防炸队友小王败招）
# ════════════════════════════════════════════

class TestBranch1TeammateAggressive:
    def _engine_with_bomb(self, role="超强主攻"):
        engine = _make_engine(role=role)
        engine._recommend_bomb_from_mask = lambda *a, **k: {
            "type": "Bomb",
            "rank": "7",
            "cards": ["S7", "H7", "D7", "C7"],
        }
        return engine

    def test_yield_when_teammate_holds_great_plain(self):
        """超强主攻 + 队友持 great 出普通牌（Pair/T，15 张不 close）→ 让道不炸"""
        engine = self._engine_with_bomb()
        gs = {
            "_current_stage": "stage_2",
            "_belief": {"hand_counts": {0: 20, 1: 10, 2: 15, 3: 12}},
            "_phase_relation": {
                "critical_enemy_seat": 1,
                "enemy_shape_hint": "unknown",
                "teammate_cover_confidence": 0.2,
                "same_type_suppressor_outside": False,
                "enemy_bomb_risk_max": 0.1,
            },
            "myPos": 0,
            "curPos": 2,
            "greaterPos": 2,
            "greaterAction": ["Pair", "T", ["ST", "HT"]],
            "handCards": ["S7", "H7", "D7", "C7", "S8", "H8", "D8", "C8",
                          "SK", "HK", "CK", "DK",
                          "SA", "S2", "H2", "S4", "S5", "S6", "S9", "H9"],
            "curRank": "2",
        }
        rec = _dispatch(engine, gs, is_teammate=True, teammate_pos=2)
        assert rec is not None
        assert rec["type"] == "PASS"
        assert rec["intent"] in ("mid_yield_teammate_control",
                                 "mid_preserve_teammate_lane")

    def test_pass_when_teammate_close(self):
        """超强主攻 + 队友出牌 + 队友 3 张（close）→ 仍让道 PASS"""
        engine = self._engine_with_bomb()
        gs = {
            "_current_stage": "stage_2",
            "_belief": {"hand_counts": {0: 20, 1: 10, 2: 3, 3: 12}},
            "_phase_relation": {
                "critical_enemy_seat": 1,
                "enemy_shape_hint": "unknown",
                "teammate_cover_confidence": 0.9,
                "same_type_suppressor_outside": False,
                "enemy_bomb_risk_max": 0.1,
            },
            "myPos": 0,
            "curPos": 2,
            "greaterPos": 2,
            "greaterAction": ["Pair", "T", ["ST", "HT"]],
            "handCards": ["S7", "H7", "D7", "C7", "S8", "H8", "D8", "C8",
                          "SK", "HK", "CK", "DK",
                          "SA", "S2", "H2", "S4", "S5", "S6", "S9", "H9"],
            "curRank": "2",
        }
        rec = _dispatch(engine, gs, is_teammate=True, teammate_pos=2)
        assert rec is not None
        assert rec["type"] == "PASS"
        assert rec["intent"] == "mid_yield_teammate_control"

    def test_pass_when_teammate_not_close_but_bombs_lt_3_and_role_attacker(self):
        """主攻 + bombs=1 + 队友 15 张 → 不炸，保持 PASS（非超强）"""
        engine = _make_engine(role="主攻")
        engine._group_type_map = {"Bomb": 1}
        engine._recommend_bomb_from_mask = lambda *a, **k: {
            "type": "Bomb",
            "rank": "7",
            "cards": ["S7", "H7", "D7", "C7"],
        }
        gs = {
            "_current_stage": "stage_2",
            "_belief": {"hand_counts": {0: 20, 1: 10, 2: 15, 3: 12}},
            "_phase_relation": {
                "critical_enemy_seat": 1,
                "enemy_shape_hint": "unknown",
                "teammate_cover_confidence": 0.2,
                "same_type_suppressor_outside": False,
                "enemy_bomb_risk_max": 0.1,
            },
            "myPos": 0,
            "curPos": 2,
            "greaterPos": 2,
            "greaterAction": ["Pair", "T", ["ST", "HT"]],
            "handCards": ["S7", "H7", "D7", "C7", "S8", "H8", "D8", "C8"],
            "curRank": "2",
        }
        rec = _dispatch(engine, gs, is_teammate=True, teammate_pos=2)
        assert rec is not None
        assert rec["type"] == "PASS"


# ════════════════════════════════════════════
#  支线1 通理覆盖：队友持 great，无论出什么牌型都让道
#  （含大小王/炸弹/同花顺等高控牌，Botzone match 6a759ae9 实证）
# ════════════════════════════════════════════

class TestBranch1TeammateHoldsGreatYield:
    _HAND = ["S7", "H7", "D7", "C7", "S8", "H8", "D8", "C8",
             "SK", "HK", "CK", "DK",
             "SA", "S2", "H2", "S4", "S5", "S6", "S9", "H9"]

    def _engine(self):
        engine = _make_engine(role="超强主攻")
        engine._recommend_bomb_from_mask = lambda *a, **k: {
            "type": "Bomb",
            "rank": "7",
            "cards": ["S7", "H7", "D7", "C7"],
        }
        return engine

    def _dispatch_with(self, greater_action, greater_type, greater_rank):
        gs = {
            "_current_stage": "stage_2",
            "_belief": {"hand_counts": {0: 20, 1: 10, 2: 15, 3: 12}},
            "_phase_relation": {
                "critical_enemy_seat": 1,
                "enemy_shape_hint": "unknown",
                "teammate_cover_confidence": 0.2,
                "same_type_suppressor_outside": False,
                "enemy_bomb_risk_max": 0.1,
            },
            "myPos": 0,
            "curPos": 2,
            "greaterPos": 2,
            "greaterAction": greater_action,
            "handCards": self._HAND,
            "curRank": "2",
        }
        return _dispatch(self._engine(), gs,
                         greater_type=greater_type, greater_rank=greater_rank,
                         is_teammate=True, teammate_pos=2)

    def test_yield_when_teammate_plays_small_joker(self):
        """超强主攻 + 队友持 great 出单张小王(SB) → 让道，不炸队友小王"""
        rec = self._dispatch_with(["Single", "B", ["SB"]], "Single", "B")
        assert rec is not None
        assert rec["type"] == "PASS"
        assert rec["intent"] in ("mid_yield_teammate_control",
                                 "mid_preserve_teammate_lane")

    def test_yield_when_teammate_plays_big_joker(self):
        """超强主攻 + 队友持 great 出单张大王(SR) → 让道"""
        rec = self._dispatch_with(["Single", "R", ["SR"]], "Single", "R")
        assert rec is not None
        assert rec["type"] == "PASS"

    def test_yield_when_teammate_plays_bomb(self):
        """超强主攻 + 队友持 great 出炸弹 → 让道，不用更大炸压队友"""
        rec = self._dispatch_with(["Bomb", "7", ["S7", "H7", "D7", "C7"]],
                                  "Bomb", "7")
        assert rec is not None
        assert rec["type"] == "PASS"

    def test_yield_when_teammate_plays_straight_flush(self):
        """超强主攻 + 队友持 great 出同花顺 → 让道"""
        rec = self._dispatch_with(
            ["StraightFlush", "9", ["S9", "H9", "C9", "D9", "S9"]],
            "StraightFlush", "9")
        assert rec is not None
        assert rec["type"] == "PASS"

    def test_yield_when_teammate_plays_single_ace(self):
        """超强主攻 + 队友持 great 出普通单张(Single/A) → 一律让道"""
        rec = self._dispatch_with(["Single", "A", ["SA"]], "Single", "A")
        assert rec is not None
        assert rec["type"] == "PASS"

class TestBranch2EnemyAggressive:
    def _engine(self, role="超强主攻"):
        engine = _make_engine(role=role)
        engine._recommend_min_press_impl = lambda *a, **k: None
        engine._recommend_max_press_impl = lambda *a, **k: None
        engine._r11_bomb_throttle_check = lambda *a, **k: (True, "critical_enemy")
        engine._recommend_bomb_from_mask = lambda *a, **k: {
            "type": "Bomb",
            "rank": "7",
            "cards": ["S7", "H7", "D7", "C7"],
        }
        return engine

    def _gs(self, *, enemy_rem=6, cover=0.2, bomb_risk=0.1, greater_pos=1):
        return {
            "_current_stage": "stage_2",
            "_belief": {"hand_counts": {0: 20, 1: enemy_rem, 2: 12, 3: 8}},
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
            "greaterAction": ["Pair", "T", ["ST", "HT"]],
            "handCards": ["S7", "H7", "D7", "C7", "S8", "H8", "D8", "C8",
                          "SK", "HK", "CK", "DK",
                          "SA", "S2", "H2", "S4", "S5", "S6", "S9", "H9"],
            "curRank": "2",
        }

    def test_aggressive_bomb_when_enemy_not_critical(self):
        """bombs=3 + 敌剩 6 张（非临界）+ 队友 cover 低 + greater=Pair → 主动炸"""
        engine = self._engine()
        gs = self._gs()
        rec = _dispatch(engine, gs, greater_type="Pair", is_lower=True)
        assert rec is not None
        assert rec["type"] == "Bomb"
        assert rec["intent"] == "mid_aggressive_bomb"

    def test_pass_when_enemy_critical(self):
        """敌剩 2 张（报单临界）→ 不触发特判，走原 mid_bomb_cutoff 路径"""
        engine = self._engine()
        gs = self._gs(enemy_rem=2)
        rec = _dispatch(engine, gs, greater_type="Pair", is_lower=True)
        # 原 mid_bomb_cutoff：critical<=3 + greater==critical + cover<0.5 → Bomb
        assert rec is not None
        assert rec["type"] == "Bomb"
        assert rec["intent"].startswith("mid_bomb_cutoff")

    def test_pass_when_teammate_can_cover(self):
        """teammate_cover_confidence=0.9（队友能接）→ 不炸"""
        engine = self._engine()
        gs = self._gs(cover=0.9)
        rec = _dispatch(engine, gs, greater_type="Pair", is_lower=True)
        assert rec is not None
        assert rec["type"] == "PASS"
        assert rec["intent"] == "mid_no_same_type_pass"

    def test_pass_when_enemy_bomb_risk_high(self):
        """enemy_bomb_risk_max=0.8（敌方反炸失控）→ 不炸"""
        engine = self._engine()
        gs = self._gs(bomb_risk=0.8)
        rec = _dispatch(engine, gs, greater_type="Pair", is_lower=True)
        assert rec is not None
        assert rec["type"] == "PASS"
        assert rec["intent"] == "mid_no_same_type_pass"

    def test_pass_when_not_super_strong(self):
        """bombs=1 + role=主攻 → 不炸（mid_no_same_type_pass）"""
        engine = self._engine(role="主攻")
        engine._group_type_map = {"Bomb": 1}
        gs = self._gs()
        rec = _dispatch(engine, gs, greater_type="Pair", is_lower=True)
        assert rec is not None
        assert rec["type"] == "PASS"
        assert rec["intent"] == "mid_no_same_type_pass"

    def test_aggressive_bomb_upper_branch(self):
        """is_upper（上家出普通牌型）+ 非临界 → 主动炸"""
        engine = self._engine()
        gs = self._gs(greater_pos=3)
        rec = _dispatch(engine, gs, greater_type="Pair", is_upper=True)
        assert rec is not None
        assert rec["type"] == "Bomb"
        assert rec["intent"] == "mid_aggressive_bomb"


# ════════════════════════════════════════════
#  回归：既有路径不受影响
# ════════════════════════════════════════════

class TestRegression:
    def test_sprint_fire_ready_still_uses_sprint_fire(self):
        """sprint_fire_ready=True + greater=Single → 走 _maybe_recommend_sprint_fire_bomb"""
        engine = _make_engine(role="超强主攻")
        engine._maybe_recommend_sprint_fire_bomb = lambda *a, **k: {
            "type": "Bomb",
            "rank": "5",
            "cards": ["S5", "H5", "D5", "C5"],
            "intent": "mid_sprint_fire_bomb",
        }
        engine._recommend_bomb_from_mask = lambda *a, **k: {
            "type": "Bomb",
            "rank": "5",
            "cards": ["S5", "H5", "D5", "C5"],
        }
        gs = {
            "_current_stage": "stage_2",
            "_belief": {"hand_counts": {0: 9, 1: 6, 2: 7, 3: 8}},
            "_phase_relation": {
                "critical_enemy_seat": 1,
                "enemy_shape_hint": "single_heavy",
                "teammate_cover_confidence": 0.25,
                "same_type_suppressor_outside": False,
                "enemy_bomb_risk_max": 0.1,
                "sprint_fire_ready": True,
            },
            "myPos": 0,
            "curPos": 3,
            "greaterPos": 3,
            "greaterAction": ["Single", "9", ["H9"]],
            "handCards": ["S4", "H4", "D4", "C4", "S5", "H5", "D5", "C5", "HK"],
            "curRank": "2",
        }
        rec = _dispatch(engine, gs, greater_type="Single", is_upper=True)
        assert rec is not None
        assert rec["type"] == "Bomb"
        assert rec["intent"] == "mid_sprint_fire_bomb"
