# -*- coding: utf-8
"""batch_executor 台账计数（方案 A + C）回归。"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from batch_executor.executor import (
    BatchExecutor,
    ExecutionState,
    GameRecordsStats,
    _calculate_batch_games,
    _count_new_paired_games,
    _increment_completed_after_batch,
    _increment_v8_completed_after_batch,
    _scan_game_records_stats,
)


def _touch(records_dir: Path, name: str) -> None:
    (records_dir / name).write_text("{}", encoding="utf-8")


def _m3_pair(
    records_dir: Path,
    *,
    ts1: str,
    ts2: str,
    opponent: str = "opponent_1_3",
    round_num: str = "1",
    level: str = "2",
) -> None:
    _touch(records_dir, f"{ts1} [yf1_m3]-[{opponent}]-[{round_num}]-[{level}].json")
    _touch(records_dir, f"{ts2} [yf2_m3]-[{opponent}]-[{round_num}]-[{level}].json")


def _v8_record(
    records_dir: Path,
    *,
    timestamp: str,
    round_num: int,
    game_count: int,
    head_pos: int,
) -> None:
    name = (
        f"{timestamp} [yf1_v8]-[opponent_1_3]-"
        f"[{round_num}]-[2].json"
    )
    payload = {
        "result": {
            "game_count": game_count,
            "order": [head_pos] + [pos for pos in range(4) if pos != head_pos],
        }
    }
    (records_dir / name).write_text(json.dumps(payload), encoding="utf-8")


@pytest.mark.unit
def test_legacy_max_round_count_is_high_but_must_not_drive_progress(tmp_path):
    """39 个 legacy round 对、0 game_id：旧 max 口径很高，台账仍只按 batch 累加。"""
    rd = tmp_path / "game_records"
    rd.mkdir()
    baseline: set = set()
    for i in range(1, 40):
        _touch(rd, f"2026053114000000000{i:02d} [yf1_m3]-[opponent_1_3]-[{i}]-[2].json")
        _touch(rd, f"2026053114000000010{i:02d} [yf2_m3]-[opponent_1_3]-[{i}]-[2].json")
    stats = _scan_game_records_stats(rd, baseline)
    assert stats.paired_game_id == 0
    assert stats.paired_match_key == 39
    assert stats.legacy_round_only_pairs == 39
    assert _count_new_paired_games(rd, baseline) == 39

    state = ExecutionState(
        target_games=12,
        completed_games=0,
        restart_count=0,
        current_batch=1,
        start_time=datetime.now(),
        last_update=datetime.now(),
    )
    added = _increment_completed_after_batch(state, batch_games=3, server_terminated_by_kill=False)
    assert added == 3
    assert state.completed_games == 3
    assert state.completed_games != min(_count_new_paired_games(rd, baseline), 12)


@pytest.mark.unit
def test_match_key_aligns_with_gua025_parse(tmp_path):
    """match key = (opponent, round, level)，与 game_recorder GUA-025 一致。"""
    rd = tmp_path / "game_records"
    rd.mkdir()
    _m3_pair(rd, ts1="20260529223719987048", ts2="20260529223719968305", round_num="19", level="K")
    _m3_pair(rd, ts1="20260529223715483407", ts2="20260529223715499999", round_num="12", level="Q")
    stats = _scan_game_records_stats(rd, set())
    assert stats.paired_match_key == 2
    assert stats.paired_game_id == 0


@pytest.mark.unit
def test_same_round_different_level_counts_as_two_match_keys(tmp_path):
    rd = tmp_path / "game_records"
    rd.mkdir()
    _m3_pair(rd, ts1="20260531111111111111", ts2="20260531111111111112", round_num="5", level="2")
    _m3_pair(rd, ts1="20260531111111111113", ts2="20260531111111111114", round_num="5", level="3")
    stats = _scan_game_records_stats(rd, set())
    assert stats.paired_match_key == 2
    assert stats.legacy_round_only_pairs == 1


@pytest.mark.unit
def test_killed_batch_does_not_increment_completed():
    state = ExecutionState(
        target_games=10,
        completed_games=3,
        restart_count=1,
        current_batch=2,
        start_time=datetime.now(),
        last_update=datetime.now(),
    )
    added = _increment_completed_after_batch(state, batch_games=3, server_terminated_by_kill=True)
    assert added == 0
    assert state.completed_games == 3


@pytest.mark.unit
def test_increment_respects_target_cap():
    state = ExecutionState(
        target_games=12,
        completed_games=11,
        restart_count=3,
        current_batch=4,
        start_time=datetime.now(),
        last_update=datetime.now(),
    )
    added = _increment_completed_after_batch(state, batch_games=3, server_terminated_by_kill=False)
    assert added == 1
    assert state.completed_games == 12


@pytest.mark.unit
def test_v8_progress_uses_actual_game_results_not_requested_batch_size():
    state = ExecutionState(
        target_games=3,
        completed_games=0,
        restart_count=0,
        current_batch=1,
        start_time=datetime.now(),
        last_update=datetime.now(),
    )

    added = _increment_v8_completed_after_batch(
        state,
        (1, 0, 0),
        server_terminated_by_kill=False,
    )

    assert added == 1
    assert state.completed_games == 1


@pytest.mark.unit
def test_v8_server_session_runs_exactly_one_game():
    assert _calculate_batch_games(3, 3, "openguandan") == 1
    assert _calculate_batch_games(2, 3, "openguandan") == 1
    assert _calculate_batch_games(3, 3, "v1006") == 3


@pytest.mark.unit
def test_v8_game_result_rebuild_is_incremental_and_ignores_baseline(tmp_path):
    records_dir = tmp_path / "game_records_v8"
    records_dir.mkdir()
    baseline_name = "20260721080000000000 [yf1_v8]-[opponent_1_3]-[1]-[2].json"
    _touch(records_dir, baseline_name)

    executor = BatchExecutor(
        target_games=3,
        server_path=str(tmp_path / "guandan.exe"),
        client_scripts=[],
        platform="openguandan",
        state_file=str(tmp_path / "state.json"),
        score_file=str(tmp_path / "scores.json"),
        enable_signal_handler=False,
    )
    executor.project_root = tmp_path
    executor._game_records_files_baseline = {baseline_name}

    _v8_record(
        records_dir,
        timestamp="20260721090000000001",
        round_num=1,
        game_count=1,
        head_pos=0,
    )
    _v8_record(
        records_dir,
        timestamp="20260721090000000002",
        round_num=2,
        game_count=2,
        head_pos=2,
    )
    assert executor._compute_v8_game_wins_from_records() == (1, 0, 0)

    _v8_record(
        records_dir,
        timestamp="20260721090100000001",
        round_num=1,
        game_count=1,
        head_pos=1,
    )
    assert executor._compute_v8_game_wins_from_records() == (0, 1, 0)
