# -*- coding: utf-8 -*-
"""M3 客户端：进贡/还贡 notify 写入 my_decisions（yf1_m3 / yf2_m3）。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from communication.yf1_m3 import YF1_M3_Client  # noqa: E402
from communication.yf2_m3 import YF2_M3_Client  # noqa: E402

M3_CLIENTS = [YF1_M3_Client, YF2_M3_Client]


@pytest.fixture(params=M3_CLIENTS)
def client(request):
    Client = request.param
    c = Client(player_id=0, use_local_websocket=True)
    c.game_recorder.start_game(
        ["C9", "DA"],
        0,
        {"selfRank": "2", "oppoRank": "Q", "curRank": "A"},
        {"0": ["C9", "DA"]},
    )
    c.game_recorder.record_decision(
        0,
        ["tribute", "tribute", ["S2"]],
        context={"version": "m3", "source": "act", "stage": "tribute"},
    )
    return c


@pytest.fixture(params=M3_CLIENTS)
def winner_client(request):
    Client = request.param
    c = Client(player_id=0, use_local_websocket=True)
    c.game_recorder.start_game(
        ["C9", "DA"],
        0,
        {"selfRank": "A", "oppoRank": "2", "curRank": "A"},
        {"0": ["C9", "DA"]},
    )
    return c


@pytest.mark.unit
def test_tribute_notify_records_received_card(winner_client):
    winner_client._handle_tribute_notification(
        {"type": "notify", "stage": "tribute", "result": [[3, 0, "s2"]]}
    )
    tributes = [
        md for md in winner_client.game_recorder.current_game["my_decisions"]
        if str((md.get("action") or [""])[0]).lower() == "tribute"
    ]
    assert len(tributes) == 1
    assert tributes[0]["action"] == ["tribute", "tribute", ["S2"]]
    assert tributes[0]["context"]["source"] == "notify"
    assert tributes[0]["context"]["tribute_pos"] == 3
    assert tributes[0]["context"]["receive_tribute_pos"] == 0


@pytest.mark.unit
def test_tribute_notify_skips_outgoing_when_act_already_recorded(client):
    """进贡方：notify 中 tribute_pos==me 时不重复录（act 已录 outgoing）。"""
    client._handle_tribute_notification(
        {"type": "notify", "stage": "tribute", "result": [[0, 3, "S2"]]}
    )
    tributes = [
        md for md in client.game_recorder.current_game["my_decisions"]
        if str((md.get("action") or [""])[0]).lower() == "tribute"
    ]
    assert len(tributes) == 1
    assert tributes[0]["context"].get("source") == "act"


@pytest.mark.unit
def test_tribute_notify_skips_when_not_receiver(winner_client):
    winner_client._handle_tribute_notification(
        {"type": "notify", "stage": "tribute", "result": [[0, 3, "S2"]]}
    )
    assert winner_client.game_recorder.current_game["my_decisions"] == []


@pytest.mark.unit
def test_back_notify_records_received_card(client):
    client._handle_back_notification(
        {"type": "notify", "stage": "back", "result": [[3, 0, "H4"]]}
    )
    backs = [
        md for md in client.game_recorder.current_game["my_decisions"]
        if str((md.get("action") or [""])[0]).lower() == "back"
    ]
    assert len(backs) == 1
    assert backs[0]["action"] == ["back", "back", ["H4"]]
    assert backs[0]["context"]["source"] == "notify"


@pytest.mark.unit
def test_back_notify_skips_when_not_receiver(client):
    client._handle_back_notification(
        {"type": "notify", "stage": "back", "result": [[0, 2, "H9"]]}
    )
    backs = [
        md for md in client.game_recorder.current_game["my_decisions"]
        if str((md.get("action") or [""])[0]).lower() == "back"
    ]
    assert backs == []


@pytest.mark.unit
def test_back_notify_normalizes_lowercase_card(client):
    client._handle_back_notification(
        {"type": "notify", "stage": "back", "result": [[3, 0, "h4"]]}
    )
    backs = [
        md for md in client.game_recorder.current_game["my_decisions"]
        if str((md.get("action") or [""])[0]).lower() == "back"
    ]
    assert backs[0]["action"] == ["back", "back", ["H4"]]


@pytest.mark.unit
def test_decision_context_from_act_marks_source_and_stage(client):
    ctx = client._decision_context_from_act(
        {"stage": "back", "actionList": [["back", "back", ["H9"]]] * 3}
    )
    assert ctx["source"] == "act"
    assert ctx["stage"] == "back"
    assert ctx["actionList_size"] == 3


@pytest.mark.unit
def test_back_notify_skips_duplicate(client):
    client._handle_back_notification(
        {"type": "notify", "stage": "back", "result": [[3, 0, "H4"]]}
    )
    client._handle_back_notification(
        {"type": "notify", "stage": "back", "result": [[3, 0, "H4"]]}
    )
    backs = [
        md for md in client.game_recorder.current_game["my_decisions"]
        if str((md.get("action") or [""])[0]).lower() == "back"
    ]
    assert len(backs) == 1
