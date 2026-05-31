# -*- coding: utf-8
"""batch_executor 台账计数（方案 A + C）回归。"""

from datetime import datetime
from pathlib import Path

import pytest

from batch_executor.executor import (
    ExecutionState,
    GameRecordsStats,
    _count_new_paired_games,
    _increment_completed_after_batch,
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
        target_games=10,
        completed_games=0,
        restart_count=0,
        current_batch=1,
        start_time=datetime.now(),
        last_update=datetime.now(),
    )
    added = _increment_completed_after_batch(state, batch_games=3, server_terminated_by_kill=False)
    assert added == 3
    assert state.completed_games == 3
    assert state.completed_games != min(_count_new_paired_games(rd, baseline), 10)


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
        target_games=10,
        completed_games=9,
        restart_count=3,
        current_batch=4,
        start_time=datetime.now(),
        last_update=datetime.now(),
    )
    added = _increment_completed_after_batch(state, batch_games=3, server_terminated_by_kill=False)
    assert added == 1
    assert state.completed_games == 10
