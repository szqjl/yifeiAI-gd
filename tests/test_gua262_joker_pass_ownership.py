# -*- coding: utf-8 -*-
"""
GUA-262: 队友对敌控「该压不压」→ 大小王归属推断（PASS 负证据）。

用户定音 3 条：
  ① 敌出级牌单，队友未用小王压，我无 SB → SB 归敌侧
  ② 敌出小王，队友未用大王压，我无 HR → 两张 HR 归敌侧
  ③ 敌出小王，队友未用大王压，我有 1 张 HR → 剩 1 张 HR 归敌侧
"""
from src.v.nn.features.memory_tracker import MemoryTracker


def _tracker(my_pos=0, hand=None, cur_rank="2"):
    t = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
    t.init_from_hand(hand or [])
    t.set_level_rank(cur_rank)
    t.sync_my_jokers(hand or [])
    return t


def test_gua262_enemy_level_single_partner_pass_sb_to_opponents():
    """① 敌出级牌单 + 队友 PASS + 我无 SB → SB with_opponents。"""
    t = _tracker(my_pos=0, hand=["HT", "S5"], cur_rank="2")
    # 敌 seat=1 出 Single/2（级牌）
    t.record_play(1, ["Single", "2", ["S2"]])
    # 队友 seat=2 PASS（未用小王压）
    t.record_pass(
        2, "Single",
        greater_action=["Single", "2", ["S2"]],
        greater_pos=1,
    )
    sb = t.get_joker_tracking()["SB"]
    assert sb["in_my_hand"] == 0
    assert sb["with_opponents"] >= 1
    assert sb["unknown"] == 0 or sb["with_opponents"] == sb["remain"]


def test_gua262_enemy_sb_partner_pass_both_hr_to_opponents():
    """② 敌出 SB + 队友 PASS + 我无 HR → 两张 HR 归敌。"""
    t = _tracker(my_pos=0, hand=["HT", "S5"], cur_rank="2")
    t.record_play(1, ["Single", "B", ["SB"]])
    t.record_pass(
        2, "Single",
        greater_action=["Single", "B", ["SB"]],
        greater_pos=1,
    )
    hr = t.get_joker_tracking()["HR"]
    assert hr["in_my_hand"] == 0
    assert hr["with_opponents"] == 2
    assert hr["unknown"] == 0


def test_gua262_enemy_sb_partner_pass_one_hr_mine_one_opp():
    """③ 敌出 SB + 队友 PASS + 我有 1 HR → 剩 1 HR 归敌。"""
    t = _tracker(my_pos=0, hand=["HR", "HT"], cur_rank="2")
    t.record_play(1, ["Single", "B", ["SB"]])
    t.record_pass(
        2, "Single",
        greater_action=["Single", "B", ["SB"]],
        greater_pos=1,
    )
    hr = t.get_joker_tracking()["HR"]
    assert hr["in_my_hand"] == 1
    assert hr["with_opponents"] == 1
    assert hr["unknown"] == 0


def test_gua262_i_have_sb_no_force_on_level_pass():
    """我有 SB 时，队友对敌级牌 PASS 不强制把 SB 归敌。"""
    t = _tracker(my_pos=0, hand=["SB", "HT"], cur_rank="2")
    t.record_play(1, ["Single", "2", ["C2"]])
    t.record_pass(
        2, "Single",
        greater_action=["Single", "2", ["C2"]],
        greater_pos=1,
    )
    sb = t.get_joker_tracking()["SB"]
    assert sb["in_my_hand"] == 1
    assert sb["with_opponents"] == 0


def test_gua262_my_pass_does_not_infer():
    """自己 PASS 不触发（只看队友该压不压）。"""
    t = _tracker(my_pos=0, hand=["HT"], cur_rank="2")
    t.record_play(1, ["Single", "B", ["SB"]])
    t.record_pass(
        0, "Single",
        greater_action=["Single", "B", ["SB"]],
        greater_pos=1,
    )
    hr = t.get_joker_tracking()["HR"]
    assert hr["with_opponents"] == 0
    assert hr["unknown"] == 2


def test_gua262_partner_played_greater_no_infer():
    """greater 来自队友时，不因我/他人 PASS 把王归敌。"""
    t = _tracker(my_pos=0, hand=["HT"], cur_rank="2")
    t.record_play(2, ["Single", "2", ["S2"]])
    t.record_pass(
        3, "Single",
        greater_action=["Single", "2", ["S2"]],
        greater_pos=2,
    )
    sb = t.get_joker_tracking()["SB"]
    assert sb["with_opponents"] == 0
