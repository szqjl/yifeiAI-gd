# -*- coding: utf-8 -*-
"""yf_replay：组牌显示中的散单与同点数组。"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "tools"))

from yf_replay import YiFeiReplayGUI  # noqa: E402


@pytest.mark.unit
def test_grouping_display_separates_singles_but_stacks_same_rank_cards():
    replay = YiFeiReplayGUI.__new__(YiFeiReplayGUI)
    replay.cur_rank = "4"
    cards = ["HT", "ST", "DT", "H9", "S8", "D7", "C6", "H5", "S5"]
    plan = {"Pair": [["H5", "S5"]]}

    columns = replay._organize_hand_by_grouping(cards, plan)

    assert columns == [
        ("对子", ["H5", "S5"]),
        ("T", ["HT", "ST", "DT"]),
        ("9", ["H9"]),
        ("8", ["S8"]),
        ("7", ["D7"]),
        ("6", ["C6"]),
    ]


@pytest.mark.unit
def test_horizontal_hand_draws_singles_in_separate_columns():
    replay = YiFeiReplayGUI.__new__(YiFeiReplayGUI)
    replay.cur_rank = "4"
    drawn = []
    replay._draw_card_normal = (
        lambda x, y, width, height, card, selected: drawn.append((card, x, y))
    )
    cards = ["HT", "ST", "DT", "H9", "S8", "D7"]

    replay._draw_hand_stacked(
        cards,
        {"orientation": "horizontal", "x": 500, "y": 100},
        plan={"Pair": []},
    )

    positions = {card: (x, y) for card, x, y in drawn}
    assert positions["HT"][0] == positions["ST"][0] == positions["DT"][0]
    assert len({positions[card][0] for card in ("H9", "S8", "D7")}) == 3
    assert {positions[card][1] for card in ("H9", "S8", "D7")} == {100}
