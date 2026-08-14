# -*- coding: utf-8 -*-
"""GUA-234：动态组牌门禁（A）+ 中期队友需求观测（B）pytest

设计真源：docs/guandan-brain/V8-中期压顺灵活性-组牌-动态重组方案.md §二 / §3.5.4 / §八
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.midgame_teammate_demand import (
    MidgameTeammateDemandTracker,
    TIER_STRONG,
    TIER_STRONG_MINUS,
    TIER_STRONG_PLUS,
    TIER_SUPER,
    TIER_WEAK,
    dynamic_regroup_enabled,
    resolve_power_gate_tier,
)


# ── A 门禁 ──────────────────────────────────────────────


class TestGua234PowerGate:
    def test_super_from_tianhu_or_role(self):
        assert resolve_power_gate_tier("天胡", "助攻") == TIER_SUPER
        assert resolve_power_gate_tier("偏弱", "超强主攻") == TIER_SUPER
        assert dynamic_regroup_enabled(TIER_SUPER) is False

    def test_conflict_takes_more_conservative(self):
        # 好牌 vs 超弱 → 更保守取超弱侧？超弱更靠后；保守=更不启用=靠前
        # 好牌=强牌+，超弱=超弱牌 → min by order → 强牌+ 更靠前 → 强牌+
        assert resolve_power_gate_tier("好牌", "超弱") == TIER_STRONG_PLUS
        # 天胡 vs 超弱 → 超强
        assert resolve_power_gate_tier("天胡", "超弱") == TIER_SUPER

    def test_non_super_enabled(self):
        for tier in (TIER_STRONG_PLUS, TIER_STRONG, TIER_STRONG_MINUS, TIER_WEAK):
            assert dynamic_regroup_enabled(tier) is True


# ── B 相位门 ────────────────────────────────────────────


def _twt(rank, trips_cards, pair_cards):
    return ["ThreeWithTwo", rank, list(trips_cards) + list(pair_cards)]


def _st(rank, cards):
    return ["Straight", rank, list(cards)]


class TestGua234PhaseGate:
    def test_pair_count_le3_same_type(self):
        tr = MidgameTeammateDemandTracker()
        my, mate, enemy = 0, 2, 1
        for _ in range(3):
            tr.observe(mate, ["Pair", "5", ["H5", "C5"]], my)
        p = tr.apply_phase_gate("Pair")
        assert p == {"Pair"}
        assert tr.play_count["Pair"] == 3

    def test_pair_count_gt3_switch_to_single(self):
        tr = MidgameTeammateDemandTracker()
        my, mate = 0, 2
        for _ in range(4):
            tr.observe(mate, ["Pair", "8", ["H8", "S8"]], my)
        p = tr.apply_phase_gate("Pair")
        assert p == {"Single"}
        feed = tr.compute_feed_P(teammate_remaining=12)
        assert feed == ["Single"]

    def test_straight_gt3_forbid_twt(self):
        tr = MidgameTeammateDemandTracker()
        my, mate = 0, 2
        for i in range(4):
            tr.observe(mate, _st("6", ["S2", "S3", "S4", "S5", "S6"]), my)
        p = tr.apply_phase_gate("Straight")
        assert p == {"Single", "Pair"}
        assert "ThreeWithTwo" not in p

    def test_twt_gt3_forbid_straight(self):
        tr = MidgameTeammateDemandTracker()
        my, mate = 0, 2
        for _ in range(4):
            tr.observe(
                mate,
                _twt("5", ["S5", "H5", "C5"], ["S3", "H3"]),
                my,
            )
        p = tr.apply_phase_gate("ThreeWithTwo")
        assert p == {"Trips", "Single", "Pair"}
        assert "Straight" not in p


# ── B 强信号 4.2 / 4.3 / 4.4 ─────────────────────────────


class TestGua234StrongSignals:
    def test_twt_top_reclaim_4_2(self):
        """333+44 → 敌 888+44 → AAA+55：到顶收回，忌优先 TWT。"""
        tr = MidgameTeammateDemandTracker()
        my, mate, enemy = 0, 2, 1
        tr.observe(
            mate,
            _twt("3", ["S3", "H3", "C3"], ["S4", "H4"]),
            my,
        )
        tr.observe(
            enemy,
            _twt("8", ["S8", "H8", "C8"], ["S4", "D4"]),
            my,
        )
        tr.observe(
            mate,
            _twt("A", ["SA", "HA", "CA"], ["S5", "H5"]),
            my,
        )
        assert tr.twt_topped_out is True
        assert tr.twt_pressed_unreclaimed is False
        feed = tr.compute_feed_P(12)
        assert feed is not None
        assert "ThreeWithTwo" not in feed
        assert "Straight" in feed

    def test_twt_unreclaimed_4_4(self):
        """333+44 → 敌压 → 队友 PASS：能打不能收，偏顺。"""
        tr = MidgameTeammateDemandTracker()
        my, mate, enemy = 0, 2, 1
        tr.observe(
            mate,
            _twt("3", ["S3", "H3", "C3"], ["S4", "H4"]),
            my,
        )
        tr.observe(
            enemy,
            _twt("8", ["S8", "H8", "C8"], ["S4", "D4"]),
            my,
        )
        tr.observe(mate, ["PASS", "PASS", "PASS"], my, is_pass=True)
        assert tr.twt_topped_out is False
        assert tr.twt_pressed_unreclaimed is True
        feed = tr.compute_feed_P(12)
        assert "ThreeWithTwo" not in feed
        assert "Straight" in feed

    def test_straight_unreclaimed_4_3(self):
        """23456 → 敌 34567 → PASS：抬 TWT/Trips。"""
        tr = MidgameTeammateDemandTracker()
        my, mate, enemy = 0, 2, 1
        tr.observe(mate, _st("6", ["S2", "S3", "S4", "S5", "S6"]), my)
        tr.observe(enemy, _st("7", ["H3", "H4", "H5", "H6", "H7"]), my)
        tr.observe(mate, ["PASS", "PASS", "PASS"], my, is_pass=True)
        assert tr.straight_pressed_unreclaimed is True
        feed = tr.compute_feed_P(12)
        assert feed is not None
        assert "ThreeWithTwo" in feed or "Trips" in feed

    def test_endgame_returns_none_for_assist_prefer(self):
        tr = MidgameTeammateDemandTracker()
        my, mate = 0, 2
        tr.observe(mate, ["Pair", "5", ["H5", "C5"]], my)
        assert tr.compute_feed_P(5) is None
        assert tr.compute_feed_P(1) is None


class TestGua234PassSuppression:
    def test_teammate_pass_twice_on_opp_streak(self):
        tr = MidgameTeammateDemandTracker()
        my, mate, enemy = 0, 2, 1
        tr.observe(enemy, ["Single", "5", ["S5"]], my)
        tr.observe(enemy, ["Single", "6", ["S6"]], my)  # streak=2
        tr.observe(mate, ["PASS", "PASS", "PASS"], my, is_pass=True)
        tr.observe(mate, ["PASS", "PASS", "PASS"], my, is_pass=True)
        assert tr.teammate_pass_on_sequence.get("Single", 0) >= 2
        assert tr.demand("Single") < tr.demand("Pair") or tr.demand("Single") <= 0
