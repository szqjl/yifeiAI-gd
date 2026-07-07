# -*- coding: utf-8 -*-
"""GUA-123：敌 sprint 炸弹须反炸 + core-filter 豁免 + 平台 SF 枚举缺口诊断。"""

import logging

from src.v.nn.endgame.endgame_decide import (
    EndgameDecider,
    collect_counter_bomb_like_candidates,
    find_latent_bomb_like_beaters_not_in_action_list,
    should_allow_counter_bomb_core_exempt,
)
from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

BOMB_6 = ["S6", "H6", "C6", "C6", "D6"]
BOMB_J = ["SJ", "SJ", "HJ", "DJ", "H9"]
ANCHOR_HAND = [
    "C2", "D5", "D6", "C7", "C7", "D8", "ST", "CT",
    "SJ", "SJ", "HJ", "DJ", "H9", "D9",
]


def _anchor_action_list():
    return [
        ["PASS", "PASS", "PASS"],
        ["Bomb", "J", BOMB_J],
    ]


def _anchor_step76_state(*, action_list=None, hand_cards=None, numofplayers=None):
    return {
        "myPos": 0,
        "curPos": 0,
        "greaterPos": 1,
        "greaterAction": ["Bomb", "6", BOMB_6],
        "handCards": list(hand_cards or ANCHOR_HAND),
        "actionList": list(action_list or _anchor_action_list()),
        "curRank": "9",
        "selfRank": "9",
        "oppoRank": "9",
        "numofplayers": list(numofplayers or [14, 5, 10, 8]),
        "_role": "主攻",
    }


def _make_engine(*, role="主攻"):
    eng = UltimateWinRateEngineV7.__new__(UltimateWinRateEngineV7)
    eng.logger = logging.getLogger("test_gua123")
    eng.player_id = 0
    eng._card_mask = None
    eng._group_type_map = {}
    eng._group_members = {}
    eng._current_role = role
    eng._last_hand_hash = None
    eng._match_fail_type_mismatch = 0
    eng._match_fail_rank_mismatch = 0
    eng._match_fail_cards_mismatch = 0
    eng.group_filter_bypass_count = 0
    eng.group_filtered_count = 0
    eng._tracker = None
    return eng


class TestGua123CounterEnemyBomb:
    def test_q1_selects_j_bomb_over_pass(self):
        gs = _anchor_step76_state()
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert idx == 1
        assert act[0] == "Bomb"
        assert act[1] == "J"

    def test_wf12_anchor_multiset(self):
        gs = _anchor_step76_state()
        EndgamePreprocessor().preprocess(gs)
        picked = collect_counter_bomb_like_candidates(
            gs["actionList"], gs["greaterAction"], gs["curRank"],
        )
        assert len(picked) == 1
        assert picked[0][1][0] == "Bomb"

    def test_gua115_still_passes_on_enemy_four(self):
        hand = BOMB_J + ["S3", "H4", "C5", "D5", "S7", "H7", "C9", "D9", "ST", "CT"]
        gs = {
            "myPos": 0,
            "curPos": 0,
            "greaterPos": 3,
            "greaterAction": ["ThreeWithTwo", "6", ["S6", "S6", "D6", "C8", "C8"]],
            "handCards": hand,
            "actionList": [["PASS", "PASS", "PASS"], ["Bomb", "J", BOMB_J]],
            "curRank": "A",
            "numofplayers": [13, 6, 10, 4],
        }
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert idx == 0
        assert act[0] == "PASS"

    def test_teammate_bomb_control_still_passes(self):
        gs = _anchor_step76_state()
        gs["greaterPos"] = 2
        gs["greaterAction"] = ["Bomb", "A", ["SA", "HA", "CA", "DA", "H9"]]
        gs["numofplayers"] = [14, 8, 5, 10]
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert idx == 0
        assert act[0] == "PASS"

    def test_cannot_beat_enemy_bomb_passes(self):
        enemy_6_5 = ["S6", "H6", "C6", "C6", "D6"]
        my_j_4 = ["SJ", "HJ", "DJ", "H9"]
        gs = _anchor_step76_state(
            hand_cards=["C2", "D5", "D6", "C7", "C7", "D8", "ST", "CT", "SJ", "HJ", "DJ", "H9", "D9", "SQ"],
            action_list=[
                ["PASS", "PASS", "PASS"],
                ["Bomb", "J", my_j_4],
            ],
        )
        gs["greaterAction"] = ["Bomb", "6", enemy_6_5]
        EndgamePreprocessor().preprocess(gs)
        idx, act = EndgameDecider().decide(gs, gs["actionList"])
        assert idx == 0
        assert act[0] == "PASS"

    def test_core_filter_exempts_counter_bomb(self):
        gs = _anchor_step76_state()
        gs["publicInfo"] = [
            {"rest": 14}, {"rest": 5}, {"rest": 10}, {"rest": 8},
        ]
        engine = _make_engine()
        engine._run_grouping_engine(gs)
        actions = _anchor_action_list()
        filtered, fmap = engine._group_consistency_filter(actions, gs)
        assert fmap[1] >= 0, "反炸 J 炸应通过 core-filter"
        assert any(a[0] == "Bomb" for a in filtered)

    def test_stage_mid_dispatch_counter_enemy_bomb(self):
        engine = _make_engine()
        gs = _anchor_step76_state()
        gs["_current_stage"] = "stage_2"
        gs["_belief"] = {"hand_counts": {0: 14, 1: 5, 2: 10, 3: 8}}
        gs["_phase_relation"] = {
            "critical_enemy_seat": 1,
            "teammate_cover_confidence": 0.2,
            "teammate_rear_single_cover_confidence": 0.0,
            "same_type_suppressor_outside": False,
            "enemy_bomb_risk_max": 0.8,
            "sprint_fire_ready": False,
        }
        rec = engine._stage_mid_dispatch(
            gs,
            engine._card_mask,
            gs["handCards"],
            gs["curRank"],
            greater_action=gs["greaterAction"],
            greater_type="Bomb",
            greater_rank="6",
            is_lead=False,
            is_teammate=False,
            is_upper=False,
            is_lower=True,
            teammate_pos=2,
        )
        assert rec is not None
        assert rec["type"] == "Bomb"
        assert rec["rank"] == "J"
        assert rec.get("intent") == "mid_counter_enemy_bomb"

    def test_latent_sf_not_in_action_list(self):
        gs = _anchor_step76_state()
        latent = find_latent_bomb_like_beaters_not_in_action_list(
            gs["handCards"],
            gs["curRank"],
            gs["greaterAction"],
            gs["actionList"],
        )
        assert latent, "组牌应有方块 5-9 同花顺可压 6 炸但未在 actionList"
        assert any("D5" in sf and "D9" in sf for sf in latent)

    def test_should_allow_counter_exempt(self):
        gs = _anchor_step76_state()
        assert should_allow_counter_bomb_core_exempt(gs["actionList"][1], gs)
