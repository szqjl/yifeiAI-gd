# -*- coding: utf-8 -*-
"""GUA-100 / PB-002：残局异常扫描器。"""

from unittest.mock import patch

from src.v.nn.endgame.endgame_anomaly_scanner import scan_endgame_snapshot


def test_enemy_critical_pass_with_legal_beater_is_flagged_when_current_replay_still_passes():
    snapshot = {
        "my_pos": 2,
        "chosen_action": ["PASS", "PASS", "PASS"],
        "layer": "残局管线",
        "action_list_size": 5,
        "action_list_sample": [
            ["PASS", "PASS", []],
            ["Pair", "J", ["CJ", "H2"]],
            ["Pair", "Q", ["SQ", "H2"]],
            ["Pair", "K", ["SK", "H2"]],
            ["Pair", "2", ["S2", "H2"]],
        ],
        "action_list_is_complete": True,
        "hand_cards": ["C6", "D6", "S7", "H7", "S8", "S9", "CT", "CJ", "SQ", "SK", "S2", "H2"],
        "cur_rank": "2",
        "cur_pos": 1,
        "greater_pos": 3,
        "greater_action": ["Pair", "T", ["DT", "DT"]],
        "numofplayers": [11, 7, 12, 1],
    }

    with patch("src.v.nn.endgame.endgame_anomaly_scanner.EndgameDecider.decide", return_value=(0, ["PASS", "PASS", "PASS"])):
        findings = scan_endgame_snapshot(snapshot)
    codes = {finding["code"] for finding in findings}

    assert "enemy_critical_pass_with_legal_beater" in codes


def test_recommended_filtered_to_pass_only_is_not_flagged_after_q1_banned_protection_fix():
    snapshot = {
        "my_pos": 0,
        "chosen_action": ["PASS", "PASS", "PASS"],
        "layer": "残局管线",
        "action_list_size": 7,
        "action_list_sample": [
            ["PASS", "PASS", []],
            ["Single", "8", ["D8"]],
            ["Single", "T", ["HT"]],
            ["Single", "T", ["DT"]],
            ["Single", "J", ["CJ"]],
            ["Single", "K", ["HK"]],
            ["Single", "K", ["CK"]],
        ],
        "action_list_is_complete": True,
        "hand_cards": ["S2", "C3", "D3", "S4", "H4", "H5", "H5", "C5", "D5", "D5", "H6", "C6", "C6", "C7", "D8", "HT", "DT", "CJ", "HK", "CK"],
        "cur_rank": "2",
        "cur_pos": 0,
        "greater_pos": 3,
        "greater_action": ["Single", "5", ["S5"]],
        "numofplayers": [8, 6, 15, 16],
    }

    findings = scan_endgame_snapshot(snapshot)

    assert all(
        finding["code"] != "recommended_filtered_to_pass_only"
        for finding in findings
    )
