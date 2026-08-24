# -*- coding: utf-8 -*-
"""GUA-072 续：记忆模块 M3–M5（牌路 / 5-10 关键张 / 头炸 / 贡牌 / NN 向量）。"""

import pytest

from src.v.nn.features.memory_tracker import MemoryTracker
from src.v.nn.features.rule_card_counter import (
    RULE_MEMORY_DIM,
    RuleCardCounter,
    extract_rule_memory_features,
)


def _make_tracker(my_pos=0, hand=None):
    t = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    t.init_from_hand(hand or [])
    return t


def _play(tracker, seat, action_type, cards):
    tracker.record_play(seat, [action_type, "?", cards])


class TestMemM03TypeRoute:
    """M3：牌路弱项 + 首发缓存。"""

    def test_type_route_downseat_short_pair(self):
        t = _make_tracker(my_pos=0)
        for c in ["S3", "H4", "D6"]:
            _play(t, 1, "Single", [c])
        c = RuleCardCounter(t)
        route = c.get_type_route_signal()
        assert route["downseat_short_pair"] is True
        assert "Pair" in route["downseat"]["unlikely_form_types"]
        assert c.seat_unlikely_form_type(1, "Pair") is True

    def test_type_route_weakness_blocks_form_type(self):
        t = _make_tracker()
        t.record_pass(3, "Trips")
        t.record_pass(3, "Trips")
        c = RuleCardCounter(t)
        assert c.can_opponent_form_type(3, "Trips", "5") is False

    def test_first_lead_type_cached(self):
        t = _make_tracker()
        _play(t, 3, "ThreeWithTwo", ["S3", "H3", "D3", "C4", "H4"])
        c = RuleCardCounter(t)
        route = c.get_type_route_signal()
        assert route["seats"][3]["first_lead_type"] == "ThreeWithTwo"


class TestMemM04KeyCard:
    """M4：5/10 关键张（MEM-M03）。"""

    def test_key_card_signal_matches_skeleton(self):
        t = _make_tracker(hand=["S5"])
        for suit in ["S", "H", "D", "C"]:
            for i in range(2):
                ct = f"{suit}5"
                if t.card_state[ct][i] != t.MY_HAND:
                    t.card_state[ct][i] = t.PLAYED
        c = RuleCardCounter(t)
        key = c.get_key_card_signal()
        assert key["five_outside_depleted"] is True
        assert "3" in key["safe_straight_windows"]
        b = c.get_belief()
        assert b["key_card_signal"]["five_outside"] == 0


class TestMemM04HeadBomb:
    """MEM-M04：成头炸 rank → 三带二主三张↓。"""

    def test_head_bomb_depleted_skips_trip_rank(self):
        t = _make_tracker()
        for suit in ["S", "H", "D", "C"]:
            _play(t, 0, "Single", [f"{suit}A"])
            _play(t, 1, "Single", [f"{suit}A"])
        c = RuleCardCounter(t)
        head = c.get_head_bomb_signal()
        assert "A" in head["head_bomb_ranks"]
        assert c._is_head_rank_depleted("A") is True
        # 仅 A 成头炸耗尽；K 等仍可组三带二 → 全局仍可能压
        assert c.can_opponent_form_type(1, "ThreeWithTwo", "7") is True


class TestMemM05TributeAndNN:
    """M5：贡牌信号 + NN 侧车向量。"""

    def test_tribute_signal_from_history(self):
        t = _make_tracker()
        t.record_tribute_transfer(1, 0, "HA")
        t.record_back_transfer(0, 1, "C3")
        c = RuleCardCounter(t)
        sig = c.get_tribute_signal()
        assert sig["tribute_count"] == 1
        assert sig["back_count"] == 1
        assert sig["latest_tribute_rank"] == "A"

    def test_rule_memory_vec_dim(self):
        t = _make_tracker()
        c = RuleCardCounter(t)
        b = c.get_belief()
        vec = extract_rule_memory_features(b)
        assert len(vec) == RULE_MEMORY_DIM
        assert all(0.0 <= x <= 1.0 for x in vec)

    def test_belief_contains_m3_m5_fields(self):
        t = _make_tracker()
        c = RuleCardCounter(t)
        b = c.get_belief()
        assert "type_route" in b
        assert "key_card_signal" in b
        assert "head_bomb_signal" in b
        assert "tribute_signal" in b
