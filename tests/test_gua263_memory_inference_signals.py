# -*- coding: utf-8 -*-
"""
GUA-263: 记牌推理信号（头条文第六～九节）
  §六 外面 5/10 打光 → 对手组不出依赖骨架的顺 → 我方更应出顺（安全窗优先）
  §七 断张 + 邻点散单 → 外炸风险
  §八 A/K 剩余与登基
  §九 牌路：连出单≈缺对；队友送小≈求大单
"""
from src.v.nn.endgame.endgame_decide import EndgameDecider
from src.v.nn.features.memory_tracker import MemoryTracker
from src.v.nn.features.rule_card_counter import RuleCardCounter


def _counter(my_pos=0, hand=None):
    t = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    t.init_from_hand(hand or [])
    t.set_level_rank("2")
    t.sync_my_jokers(hand or [])
    return RuleCardCounter(t), t


def _mark_outside_rank_played(t: MemoryTracker, rank: str):
    """把该 rank 所有非我手副本标为已出 → outside_my_hand==0。"""
    for suit in ("S", "H", "D", "C"):
        copies = t.card_state[f"{suit}{rank}"]
        for i in range(2):
            if copies[i] != t.MY_HAND:
                copies[i] = t.PLAYED


# ── §六 5/10：外面打光 → 安全顺优先 ─────────────────────

def test_gua263_outside_five_gone_marks_safe_windows():
    """我手仍有 5，外面 5 打光 → 依赖 5 的顺窗标为安全。"""
    c, t = _counter(hand=["S5", "H5"])
    _mark_outside_rank_played(t, "5")
    sig = c.get_straight_skeleton_signal()
    assert sig["five_outside_depleted"] is True
    assert sig["five_outside"] == 0
    assert sig["five_remain"] == 2  # 仍在我手
    for w in ("A", "2", "3", "4", "5"):
        assert w in sig["safe_straight_windows"]
        assert c.is_straight_window_outside_safe(w)
    assert not c.is_straight_window_outside_safe("T")


def test_gua263_outside_ten_gone_marks_ten_windows_safe():
    c, t = _counter(hand=["ST"])
    _mark_outside_rank_played(t, "T")
    sig = c.get_straight_skeleton_signal()
    assert sig["ten_outside_depleted"] is True
    for w in ("6", "7", "8", "9", "T"):
        assert w in sig["safe_straight_windows"]


def test_gua263_locking_prefers_safe_straight_when_outside_five_gone():
    """锁敌：外面无 5 时优先 Straight/3，而非 Trips。"""
    c, t = _counter(hand=["S3", "H4", "D5", "C6", "S7", "H8", "H8", "H8"])
    _mark_outside_rank_played(t, "5")
    belief = c.get_belief()
    assert "3" in belief["straight_skeleton"]["safe_straight_windows"]

    candidates = [
        (0, ["Trips", "8", ["H8", "H8", "H8"]]),
        (1, ["Straight", "3", ["S3", "H4", "D5", "C6", "S7"]]),
    ]
    gs = {
        "handCards": ["S3", "H4", "D5", "C6", "S7", "H8", "H8", "H8"],
        "curRank": "2",
        "_belief": belief,
        "_group_members": {},
        "_group_gid_type_map": {},
    }
    picked = EndgameDecider()._select_enemy_one_locking_structure(candidates, gs)
    assert picked is not None
    assert picked[1][0] == "Straight" and picked[1][1] == "3"


# ── §七 断张炸 ──────────────────────────────────────────

def test_gua263_gap_with_neighbor_singles_raises_bomb_risk():
    c, t = _counter(hand=["S3", "H3", "D4"])
    for _ in range(3):
        t.record_play(1, ["Single", "7", ["S7"]])
        t.record_play(3, ["Single", "9", ["H9"]])
    sig = c.get_gap_bomb_risk_signal()
    assert "8" in sig["gap_ranks"]
    assert sig["gap_bomb_risk_max"] >= 0.7
    assert "8" in sig["high_bomb_gap_ranks"]
    belief = c.get_belief()
    assert max(belief["opp_bomb_risks"].values()) >= 0.5


def test_gua263_no_gap_when_i_hold_rank():
    c, t = _counter(hand=["S8", "H8"])
    for _ in range(4):
        t.record_play(1, ["Single", "7", ["S7"]])
    sig = c.get_gap_bomb_risk_signal()
    assert "8" not in sig["gap_ranks"]


# ── §八 A/K ─────────────────────────────────────────────

def test_gua263_ak_power_crowns_when_outside_zero():
    c, t = _counter(hand=["SA", "HA"])
    for suit in ("S", "H", "D", "C"):
        copies = t.card_state[f"{suit}A"]
        for i in range(2):
            if copies[i] == -1:
                copies[i] = t.PLAYED
    sig = c.get_ak_power_signal()
    assert sig["a_in_my_hand"] == 2
    assert sig["a_outside"] == 0
    assert sig["my_a_crowns"] is True
    assert sig["k_outside"] == 8


# ── §九 牌路 ────────────────────────────────────────────

def test_gua263_line_read_downseat_short_pair():
    c, t = _counter(my_pos=0, hand=["S5"])
    t.record_play(1, ["Single", "3", ["S3"]])
    t.record_play(1, ["Single", "4", ["H4"]])
    t.record_play(1, ["Single", "6", ["D6"]])
    sig = c.get_line_read_signal()
    assert sig["downseat_short_pair"] is True
    assert sig["seats"][1]["likely_short_pair"] is True


def test_gua263_line_read_teammate_wants_big_single():
    c, t = _counter(my_pos=0, hand=["SA"])
    t.record_play(2, ["Single", "3", ["S3"]])
    t.record_play(2, ["Single", "5", ["H5"]])
    sig = c.get_line_read_signal()
    assert sig["teammate_wants_big_single"] is True


def test_gua263_belief_contains_all_four_signals():
    c, _ = _counter(hand=["S2"])
    b = c.get_belief()
    assert "straight_skeleton" in b
    assert "gap_bomb_risk" in b
    assert "ak_power" in b
    assert "line_read" in b
    assert "safe_straight_windows" in b["straight_skeleton"]
