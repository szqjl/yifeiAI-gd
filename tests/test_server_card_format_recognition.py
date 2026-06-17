# -*- coding: utf-8 -*-
"""
模拟服务器发两种卡牌格式，验证 M1/V7 入口规范化后识别是否完整、正确。
运行：在项目根目录执行  python tests/test_server_card_format_recognition.py
"""
import sys
from pathlib import Path
from collections import Counter

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from communication.game_recorder import (
    normalize_cards_to_string_list,
    normalize_action_list,
)


def test_hand_cards_string_format():
    """服务器发字符串格式 handCards"""
    hand = ["S2", "H3", "C8", "DT", "RJ", "BJ"]
    out = normalize_cards_to_string_list(hand)
    assert out == hand, f"string format: expected {hand}, got {out}"
    print("  [OK] handCards 纯字符串格式 -> 保持不变")


def test_hand_cards_list_format():
    """服务器发列表格式 handCards [["C","8"], ...]"""
    hand = [["S", "2"], ["H", "3"], ["C", "8"], ["D", "T"], ["R", "J"], ["B", "J"]]
    out = normalize_cards_to_string_list(hand)
    expect = ["S2", "H3", "C8", "DT", "RJ", "BJ"]
    assert out == expect, f"list format: expected {expect}, got {out}"
    print("  [OK] handCards 列表格式 -> 转为 S2/H3/C8/DT/RJ/BJ")


def test_hand_cards_mixed_format():
    """混合格式：部分字符串、部分列表"""
    hand = ["S2", ["H", "3"], "C8", ["D", "T"]]
    out = normalize_cards_to_string_list(hand)
    expect = ["S2", "H3", "C8", "DT"]
    assert out == expect, f"mixed: expected {expect}, got {out}"
    print("  [OK] handCards 混合格式 -> 统一为字符串列表")


def test_hand_cards_27_cards():
    """27 张牌（完整手牌）两种格式数量一致"""
    # 字符串
    strings = [f"{s}{r}" for s in "SHCD" for r in "23456789TJQKA"] + ["RJ", "BJ"]
    strings = strings[:27]
    out_s = normalize_cards_to_string_list(strings)
    assert len(out_s) == 27, f"string 27: got {len(out_s)}"
    # 列表
    lists = [[c[0], c[1]] for c in strings]
    out_l = normalize_cards_to_string_list(lists)
    assert len(out_l) == 27, f"list 27: got {len(out_l)}"
    assert out_s == out_l, "27 cards: string and list should normalize to same"
    print("  [OK] 27 张手牌两种格式 -> 数量一致、内容一致")


def test_action_list_format():
    """actionList 中动作的第三元（牌列表）两种格式"""
    # 服务器可能发 [["Single","4",[["H","4"]]], ...]
    action_list = [
        ["PASS", "PASS", "PASS"],
        ["Single", "4", [["H", "4"]]],
        ["Pair", "5", [["S", "5"], ["C", "5"]]],
    ]
    out = normalize_action_list(action_list)
    assert out[0] == ["PASS", "PASS", "PASS"]
    assert out[1] == ["Single", "4", ["H4"]]
    assert out[2] == ["Pair", "5", ["S5", "C5"]]
    print("  [OK] actionList 列表格式牌 -> 转为字符串列表")


def test_action_list_already_string():
    """actionList 已是字符串格式则不变"""
    action_list = [
        ["Single", "4", ["H4"]],
        ["Pair", "5", ["S5", "C5"]],
    ]
    out = normalize_action_list(action_list)
    assert out == action_list
    print("  [OK] actionList 已是字符串 -> 保持不变")


def test_normalized_handcards_consumable_by_decision():
    """规范化后的手牌可被决策层安全使用（Counter、王/级牌识别）"""
    # 服务器发列表格式，规范化后应能被 Counter 等逻辑使用
    raw = [["S", "2"], ["H", "2"], ["R", "J"], ["B", "J"], ["C", "9"]]
    hand = normalize_cards_to_string_list(raw)
    assert len(hand) == 5
    # 决策层常用：Counter(handcards)，列表格式会报 unhashable，字符串格式正常
    cnt = Counter(hand)
    assert cnt["S2"] == 1 and cnt["RJ"] == 1 and cnt["BJ"] == 1
    # 王识别（与 phase_handlers 等一致）
    has_king = any("R" in c or "B" in c for c in hand)
    assert has_king, "应识别到大小王"
    # 级牌识别（curRank=2 时 S2/H2 为级牌）
    cur_rank = "2"
    has_level = any(cur_rank in c for c in hand)
    assert has_level, "应识别到级牌"
    # 红桃配
    red_heart = f"H{cur_rank}"
    assert red_heart in hand, "应包含红桃配 H2"
    print("  [OK] 规范化后手牌可被决策层正确消费（Counter、王、级牌、红桃配）")


def test_full_message_normalize_then_consume():
    """模拟完整消息：服务器发混合格式，规范化后整条链路可识别"""
    # 模拟 act 消息里 handCards 为列表格式、actionList 里牌也为列表格式
    message = {
        "handCards": [["H", "2"], ["S", "9"], ["R", "J"], ["C", "3"], ["D", "5"]],
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["Single", "9", [["S", "9"]]],
            ["Single", "2", [["H", "2"]]],
        ],
        "curRank": "2",
    }
    message["handCards"] = normalize_cards_to_string_list(message["handCards"])
    message["actionList"] = normalize_action_list(message["actionList"])
    hand = message["handCards"]
    action_list = message["actionList"]
    assert len(hand) == 5
    assert action_list[1][2] == ["S9"] and action_list[2][2] == ["H2"]
    # 决策层可安全使用
    Counter(hand)
    has_king = any("R" in c or "B" in c for c in hand)
    has_level = any(message["curRank"] in c for c in hand)
    assert has_king and has_level
    print("  [OK] 完整消息规范化后整条链路可正确识别")


def run():
    print("服务器卡牌格式识别验证（入口规范化）")
    print("-" * 50)
    test_hand_cards_string_format()
    test_hand_cards_list_format()
    test_hand_cards_mixed_format()
    test_hand_cards_27_cards()
    test_action_list_format()
    test_action_list_already_string()
    test_normalized_handcards_consumable_by_decision()
    test_full_message_normalize_then_consume()
    print("-" * 50)
    print("全部通过：服务器发出的卡牌可被完整、正确识别（含决策层消费）。")


if __name__ == "__main__":
    run()
