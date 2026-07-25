# -*- coding: utf-8 -*-
"""analyze_v7_rounds 副级去重（yf1/yf2 双录）单元测试。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import analyze_v7_rounds as analyzer  # noqa: E402
from analyze_v7_rounds import (  # noqa: E402
    dedupe_session_records,
    match_key_from_filename,
    v8_game_result_from_head_dist,
)


def test_match_key_from_filename():
    name = "20260628085549791651 [yf2_v7]-[opponent_1_3]-[8]-[2].json"
    assert match_key_from_filename(name) == ("8", "2")


def test_dedupe_prefers_yf1():
    recs = [
        {"_file": "t [yf2_v7]-[opponent_1_3]-[1]-[2].json", "game_round": 1},
        {"_file": "t [yf1_v7]-[opponent_1_3]-[1]-[2].json", "game_round": 1},
        {"_file": "t [yf1_v7]-[opponent_1_3]-[2]-[2].json", "game_round": 2},
    ]
    out = dedupe_session_records(recs)
    assert len(out) == 2
    assert "yf1_v7" in out[0]["_file"]
    assert "yf1_v7" in out[1]["_file"]


def test_v8_game_result_uses_team_head_counts():
    assert v8_game_result_from_head_dist([15, 0, 16, 5]) == (1, 0, 0)
    assert v8_game_result_from_head_dist([1, 2, 2, 1]) == (0, 0, 1)


def test_v8_session_does_not_treat_victory_num_as_game_wins(monkeypatch, capsys):
    monkeypatch.setattr(analyzer, "_PLATFORM_TAG", "V8")
    monkeypatch.setattr(analyzer, "_TEAM_A_LABEL", "V8")
    monkeypatch.setattr(analyzer, "_TEAM_B_LABEL", "Lalala")
    monkeypatch.setattr(analyzer, "GAMES_PER_SESSION", 1)
    records = [
        {
            "_file": f"2026072109000000000{idx} [yf1_v8]-[opponent_1_3]-[{idx}]-[2].json",
            "result": {
                "game_count": idx,
                "order": order,
                "curRank": "A",
                "victoryNum": [14, 0, 14, 5],
            },
        }
        for idx, order in enumerate(
            ([0, 2, 1, 3], [2, 0, 1, 3], [1, 3, 0, 2]),
            start=1,
        )
    ]

    result = analyzer.analyze_session(records, 1)
    output = capsys.readouterr().out

    assert result["v7_game_wins"] == 1
    assert result["lalala_game_wins"] == 0
    assert result["draws"] == 0
    assert "V8 1/1局胜" in output
    assert "V8 14/1局胜" not in output
    assert "victoryNum（升级值，仅诊断）" in output


def test_v7_session_keeps_victory_num_game_wins(monkeypatch, capsys):
    monkeypatch.setattr(analyzer, "_PLATFORM_TAG", "V7")
    monkeypatch.setattr(analyzer, "GAMES_PER_SESSION", 3)
    records = [
        {
            "_file": "20260721090000000001 [yf1_v7]-[opponent_1_3]-[1]-[2].json",
            "result": {
                "order": [0, 2, 1, 3],
                "curRank": "A",
                "victoryNum": [2, 1, 2, 1],
            },
        }
    ]

    result = analyzer.analyze_session(records, 1)
    output = capsys.readouterr().out

    assert result["v7_game_wins"] == 2
    assert result["lalala_game_wins"] == 1
    assert result["draws"] == 0
    assert "V7 2/3局胜" in output
