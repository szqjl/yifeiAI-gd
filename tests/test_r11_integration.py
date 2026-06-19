"""测试 V7-R11 全局抑制牌检查 + 节流规则。
注意：live game_state 的 actionList / greaterAction 是纯牌面列表格式
（如 ["S8"], ["S2","S2","H2","D2"]），不是录制 JSON 的 [type, rank, cards] 三元组。
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v.nn.guards.v7_guards import filter_action_list, _compute_pass_num
from src.v.nn.features.memory_tracker import MemoryTracker


def test_r11_filters_bomb_when_jokers_remain():
    """抑制牌充足（大王小王全未出）→ 过滤炸弹，只留 PASS。"""
    gs = {
        "myPos": 2, "greaterPos": 1,
        "greaterAction": ["S8"],
        "curPos": 2, "curRank": "8",
        "handCards": ["S2","S2","H2","D2","S4","S4","C4","C5","D5",
                      "S6","S9","H9","C9","HJ","DJ","CQ","DQ",
                      "HK","DK","HA","CA","CA","DA","S8","C8","D8","D8","D4"],
        "actionList": [
            ["PASS"],
            ["S2","S2","H2","D2"],
            ["HA","CA","CA","DA"],
        ],
        "recentPlays": [{"pos": 1, "cards": ["S8"]}],
        "numofplayers": [27, 26, 27, 27],
    }
    tracker = MemoryTracker(my_pos=2)
    tracker.init_from_hand(gs["handCards"])
    tracker.set_level_rank("8")
    tracker.record_play(1, ["Single", "8", ["S8"]])
    gs["_memory_tracker"] = tracker

    filtered, _ = filter_action_list(gs)
    print(f"抑制牌=4: {len(gs['actionList'])} → {len(filtered)}")
    for a in filtered:
        print(f"  {'PASS' if a[0]=='PASS' else 'Bomb'}: {a}")
    assert len(filtered) == 1 and filtered[0][0] == "PASS"
    print("✓ PASS")


def test_r11_suppressor_one_pass0():
    """仅剩 1 张抑制牌 + 还没人 PASS → 过滤炸弹，等队友。"""
    gs = {
        "myPos": 2, "greaterPos": 1,
        "greaterAction": ["S8"],
        "curPos": 2, "curRank": "8",
        "handCards": ["S2","S2","H2","D2"],
        "actionList": [
            ["PASS"],
            ["S2","S2","H2","D2"],
        ],
        "recentPlays": [{"pos": 1, "cards": ["S8"]}],
        "numofplayers": [27, 26, 25, 27],
    }
    tracker = MemoryTracker(my_pos=2)
    tracker.init_from_hand(gs["handCards"])
    tracker.set_level_rank("8")
    # 出了 2HR + 1SB → 剩 1SB（只有1张抑制牌）
    tracker.record_play(0, ["Single", "", ["HR"]])
    tracker.record_play(3, ["Single", "", ["HR"]])
    tracker.record_play(0, ["Single", "", ["SB"]])
    tracker.record_play(1, ["Single", "8", ["S8"]])
    gs["_memory_tracker"] = tracker

    filtered, _ = filter_action_list(gs)
    print(f"抑制牌=1 pass=0: {len(gs['actionList'])} → {len(filtered)}")
    for a in filtered:
        print(f"  {'PASS' if a[0]=='PASS' else 'Bomb'}: {a}")
    assert len(filtered) == 1 and filtered[0][0] == "PASS"
    print("✓ PASS")


def test_r11_suppressor_one_pass1():
    """仅剩 1 张抑制牌 + 已有人 PASS → 允许炸弹。"""
    gs = {
        "myPos": 2, "greaterPos": 1,
        "greaterAction": ["S8"],
        "curPos": 2, "curRank": "8",
        "handCards": ["S2","S2","H2","D2"],
        "actionList": [
            ["PASS"],
            ["S2","S2","H2","D2"],
        ],
        "recentPlays": [
            {"pos": 1, "cards": ["S8"]},
            {"pos": 3, "cards": []},
        ],
        "numofplayers": [27, 26, 25, 27],
    }
    tracker = MemoryTracker(my_pos=2)
    tracker.init_from_hand(gs["handCards"])
    tracker.set_level_rank("8")
    tracker.record_play(0, ["Single", "", ["HR"]])
    tracker.record_play(3, ["Single", "", ["SB"]])
    tracker.record_play(0, ["Single", "", ["HR"]])
    tracker.record_play(1, ["Single", "8", ["S8"]])
    gs["_memory_tracker"] = tracker

    filtered, _ = filter_action_list(gs)
    print(f"抑制牌=1 pass=1: {len(gs['actionList'])} → {len(filtered)}")
    for a in filtered:
        print(f"  {'PASS' if a[0]=='PASS' else 'Bomb'}: {a}")
    has_bomb = any(a[0] not in ("PASS",) for a in filtered)
    assert has_bomb
    print("✓ PASS")


def test_r11_suppressor_zero():
    """抑制牌全无 → 允许炸弹（真正无人能压）。"""
    gs = {
        "myPos": 2, "greaterPos": 1,
        "greaterAction": ["S8"],
        "curPos": 2, "curRank": "8",
        "handCards": ["S2","S2","H2","D2"],
        "actionList": [
            ["PASS"],
            ["S2","S2","H2","D2"],
        ],
        "recentPlays": [{"pos": 1, "cards": ["S8"]}],
        "numofplayers": [27, 26, 25, 27],
    }
    tracker = MemoryTracker(my_pos=2)
    tracker.init_from_hand(gs["handCards"])
    tracker.set_level_rank("8")
    # 全出完
    for seat, joker in [(0, "HR"), (3, "HR"), (1, "SB"), (3, "SB")]:
        tracker.record_play(seat, ["Single", "", [joker]])
    tracker.record_play(1, ["Single", "8", ["S8"]])
    gs["_memory_tracker"] = tracker

    filtered, _ = filter_action_list(gs)
    print(f"抑制牌=0: {len(gs['actionList'])} → {len(filtered)}")
    for a in filtered:
        print(f"  {'PASS' if a[0]=='PASS' else 'Bomb'}: {a}")
    has_bomb = any(a[0] not in ("PASS",) for a in filtered)
    assert has_bomb, "抑制牌全无应允许炸弹"
    print("✓ PASS")


def test_r11_normal_counter_no_interference():
    """有普通牌可压时 R11 不干预。"""
    gs = {
        "myPos": 2, "greaterPos": 1,
        "greaterAction": ["S7"],
        "curPos": 2, "curRank": "8",
        "handCards": ["SA","S2","S2","H2","D2"],
        "actionList": [
            ["PASS"],
            ["SA"],
            ["S2","S2","H2","D2"],
        ],
        "recentPlays": [{"pos": 1, "cards": ["S7"]}],
        "numofplayers": [27, 27, 27, 27],
    }
    tracker = MemoryTracker(my_pos=2)
    tracker.init_from_hand(gs["handCards"])
    tracker.set_level_rank("8")
    tracker.record_play(1, ["Single", "7", ["S7"]])
    gs["_memory_tracker"] = tracker

    filtered, _ = filter_action_list(gs)
    types = [a[0] for a in filtered]
    print(f"有普通牌: {types}")
    # R01 可能已过滤炸弹，但至少应有非 PASS 的普通牌
    non_pass = [a for a in filtered if a[0] != "PASS"]
    assert len(non_pass) >= 1, "应有非PASS选项"
    print("✓ PASS")


def test_compute_pass_num():
    """pass_num 计算。"""
    s = {"recentPlays": [
        {"pos": 1, "cards": ["S8"]},
        {"pos": 3, "cards": []},
        {"pos": 0, "cards": []},
    ]}
    t, m = _compute_pass_num(s, 2)
    assert t == 2 and m == 0, f"t={t} m={m}"
    print(f"✓ pass_num=2 my=0")

    s2 = {"recentPlays": [{"pos": 1, "cards": ["S8"]}]}
    t2, m2 = _compute_pass_num(s2, 2)
    assert t2 == 0
    print(f"✓ pass_num=0")


if __name__ == "__main__":
    test_compute_pass_num()
    test_r11_filters_bomb_when_jokers_remain()
    test_r11_suppressor_one_pass0()
    test_r11_suppressor_one_pass1()
    test_r11_suppressor_zero()
    test_r11_normal_counter_no_interference()
    print("\n全部集成测试通过!")
