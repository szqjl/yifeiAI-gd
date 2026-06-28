# -*- coding: utf-8 -*-
"""analyze_v7_rounds 副级去重（yf1/yf2 双录）单元测试。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from analyze_v7_rounds import (  # noqa: E402
    dedupe_session_records,
    match_key_from_filename,
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
