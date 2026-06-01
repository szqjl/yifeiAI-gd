# -*- coding: utf-8
"""GUA-033：M3 gameResult 解析、gameOver 早退、backfill 批级校验。"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from communication.game_recorder import GameRecorder
from communication.game_result_utils import (
    build_game_result_payload,
    build_latest_victory_num_payload,
    build_local_batch_victory_num,
    extract_victory_num_from_game_result,
    resolve_expected_batch_games,
    validate_batch_victory_num,
)
from communication.yf1_m3 import YF1_M3_Client
from communication.yf2_m3 import YF2_M3_Client


@pytest.mark.unit
def test_game_over_early_return_no_victory_num():
    """gameOver 早退：不解析 victoryNum、不 end_game。"""
    client = YF1_M3_Client(player_id=0)
    client.game_recorder.end_game = MagicMock(return_value=None)
    client._flush_pending_records = MagicMock()

    data = {
        "type": "notify",
        "stage": "gameOver",
        "curTimes": 1,
        "settingTimes": 3,
        "notification_key": "gameOver",
    }
    client._handle_game_over(data)

    assert client._batch_setting_times == 3
    client.game_recorder.end_game.assert_not_called()
    client._flush_pending_records.assert_not_called()


@pytest.mark.unit
def test_game_result_reads_final_field():
    """gameResult 优先读 v1006 ``final`` 字段。"""
    raw = {
        "type": "notify",
        "stage": "gameResult",
        "final": [1, 0, 1, 0],
    }
    assert extract_victory_num_from_game_result(raw) == [1, 0, 1, 0]
    payload = build_game_result_payload(raw)
    assert payload["victoryNum"] == [1, 0, 1, 0]


@pytest.mark.unit
def test_episode_over_does_not_use_result_list_index_four():
    """episodeOver 的 result[4] 不得当作批末 victoryNum。"""
    raw = {
        "type": "notify",
        "stage": "episodeOver",
        "notification_key": "episodeOver",
        "order": [0, 2, 1, 3],
        "result": [None, None, None, None, [2, 1, 2, 1]],
    }
    assert extract_victory_num_from_game_result(raw) == []


@pytest.mark.unit
def test_backfill_skipped_when_batch_games_mismatch(tmp_path):
    """backfill 前校验 [0]+[1]==batch_games，不一致则跳过并清空 pending。"""
    rec = GameRecorder(0, "test_m3")
    rec.record_dir = tmp_path
    pending_file = tmp_path / "pending.json"
    pending_file.write_text(
        json.dumps({"result": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    pending = [str(pending_file)]
    updated = rec.backfill_victory_num(
        [2, 1, 2, 1],
        pending,
        expected_batch_games=1,
    )
    assert updated == 0
    assert pending == []
    data = json.loads(pending_file.read_text(encoding="utf-8"))
    assert "victoryNum" not in data.get("result", {})


@pytest.mark.unit
def test_backfill_ok_when_batch_games_match(tmp_path):
    """校验通过时正常回填。"""
    rec = GameRecorder(0, "test_m3")
    rec.record_dir = tmp_path
    pending_file = tmp_path / "pending.json"
    pending_file.write_text(json.dumps({"result": {}}), encoding="utf-8")
    pending = [str(pending_file)]
    updated = rec.backfill_victory_num(
        [2, 1, 2, 1],
        pending,
        expected_batch_games=3,
    )
    assert updated == 1
    data = json.loads(pending_file.read_text(encoding="utf-8"))
    assert data["result"]["victoryNum"] == [2, 1, 2, 1]


@pytest.mark.unit
def test_validate_batch_victory_num_team_pairing():
    ok, _ = validate_batch_victory_num([2, 1, 2, 1], 3)
    assert ok
    ok, reason = validate_batch_victory_num([2, 1, 2, 1], 1)
    assert not ok
    assert "batch_games=1" in reason


@pytest.mark.unit
def test_game_result_handler_logs_raw_and_backfills(tmp_path):
    """gameResult 完整链路：RAW、校验、回填。"""
    client = YF1_M3_Client(player_id=0)
    client._batch_setting_times = 1
    client.game_recorder.record_dir = tmp_path

    pending_file = tmp_path / "ep.json"
    pending_file.write_text(json.dumps({"result": {}}), encoding="utf-8")
    client.pending_result_files = [str(pending_file)]

    data = {
        "type": "notify",
        "stage": "gameResult",
        "notification_key": "gameResult",
        "final": [1, 0, 1, 0],
    }
    with patch.object(client, "_save_victory_num_to_shared_file"):
        with patch(
            "communication.yf1_m3.resolve_expected_batch_games", return_value=1
        ):
            client._handle_game_over(data)

    saved = json.loads(pending_file.read_text(encoding="utf-8"))
    assert saved["result"]["victoryNum"] == [1, 0, 1, 0]
    assert client.pending_result_files == []


@pytest.mark.unit
def test_resolve_expected_batch_games_from_file(tmp_path):
    batch_dir = tmp_path / "batch_executor"
    batch_dir.mkdir()
    (batch_dir / "current_batch.json").write_text(
        json.dumps({"batch_games": 3}),
        encoding="utf-8",
    )
    assert resolve_expected_batch_games(None, tmp_path) == 3


@pytest.mark.unit
def test_resolve_expected_batch_games_prefers_batch_file(tmp_path):
    batch_dir = tmp_path / "batch_executor"
    batch_dir.mkdir()
    (batch_dir / "current_batch.json").write_text(
        json.dumps({"batch_games": 1}),
        encoding="utf-8",
    )
    assert resolve_expected_batch_games(setting_times=3, project_root=tmp_path) == 1


@pytest.mark.unit
def test_yf2_game_result_fallback_to_batch_wins(tmp_path):
    """yf2_m3 与 yf1 一致：服务器 vn 无效时 fallback 到 batch_wins。"""
    client = YF2_M3_Client(player_id=2)
    client.game_recorder.record_dir = tmp_path
    client._batch_platform_wins = [1, 0]
    batch_dir = tmp_path / "batch_executor"
    batch_dir.mkdir()
    (batch_dir / "current_batch.json").write_text(
        json.dumps({"batch_games": 1}), encoding="utf-8"
    )
    client._project_root = tmp_path

    pending_file = tmp_path / "ep2.json"
    pending_file.write_text(json.dumps({"result": {}}), encoding="utf-8")
    client.pending_result_files = [str(pending_file)]

    data = {
        "type": "notify",
        "stage": "gameResult",
        "notification_key": "gameResult",
        "victoryNum": [3, 0, 3, 0],
    }
    client._handle_game_over(data)

    saved = json.loads(pending_file.read_text(encoding="utf-8"))
    assert saved["result"]["victoryNum"] == [1, 0, 1, 0]
    assert client.pending_result_files == []


@pytest.mark.unit
def test_build_local_batch_victory_num():
    assert build_local_batch_victory_num(0, 1) == [0, 1, 0, 1]


@pytest.mark.unit
def test_build_latest_victory_num_payload():
    p = build_latest_victory_num_payload(
        [1, 0, 1, 0],
        batch_games=1,
        server_vn_raw=[3, 0, 3, 0],
        vn_source="fallback",
    )
    assert p["victoryNum"] == [1, 0, 1, 0]
    assert p["batch_games"] == 1
    assert p["server_vn_raw"] == [3, 0, 3, 0]
    assert p["vn_source"] == "fallback"
    assert p["player"] == "yf1_m3"
    assert "timestamp" in p


@pytest.mark.unit
def test_yf1_game_result_fallback_passes_server_vn_raw(tmp_path):
    """fallback 时 _save_victory_num_to_shared_file 携带 server_vn_raw / vn_source。"""
    client = YF1_M3_Client(player_id=0)
    client.game_recorder.record_dir = tmp_path
    client._batch_platform_wins = [1, 0]
    batch_dir = tmp_path / "batch_executor"
    batch_dir.mkdir()
    (batch_dir / "current_batch.json").write_text(
        json.dumps({"batch_games": 1}), encoding="utf-8"
    )
    client._project_root = tmp_path

    pending_file = tmp_path / "ep1.json"
    pending_file.write_text(json.dumps({"result": {}}), encoding="utf-8")
    client.pending_result_files = [str(pending_file)]

    saved_args = {}

    def capture_save(vn, bg, server_vn_raw=None, vn_source="server"):
        saved_args.update(
            {
                "victory_num": vn,
                "batch_games": bg,
                "server_vn_raw": server_vn_raw,
                "vn_source": vn_source,
            }
        )

    data = {
        "type": "notify",
        "stage": "gameResult",
        "notification_key": "gameResult",
        "victoryNum": [3, 0, 3, 0],
    }
    with patch.object(client, "_save_victory_num_to_shared_file", side_effect=capture_save):
        client._handle_game_over(data)

    assert saved_args["victory_num"] == [1, 0, 1, 0]
    assert saved_args["server_vn_raw"] == [3, 0, 3, 0]
    assert saved_args["vn_source"] == "fallback"
