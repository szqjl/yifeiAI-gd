"""GUA-048：服务器 stdout 单读者实时落盘。"""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from pathlib import Path

import pytest

from batch_executor.server_stdout_reader import ServerStdoutReader


@pytest.fixture
def log_capture():
    records: list[logging.LogRecord] = []

    class _ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    logger = logging.getLogger("test_server_stdout")
    handler = _ListHandler()
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    yield logger, records
    logger.handlers.clear()


def test_server_stdout_reader_logs_lines_promptly(log_capture):
    """后台读者应在子进程写出行后数秒内可见，而非等进程结束才批量 dump。"""
    logger, records = log_capture
    script = (
        "import sys, time\n"
        "for i in range(5):\n"
        "    print(f'line-{i}', flush=True)\n"
        "    time.sleep(0.05)\n"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    reader = ServerStdoutReader(proc, logger)
    assert reader.start() is True

    deadline = time.time() + 3.0
    while time.time() < deadline:
        if any("line-0" in r.getMessage() for r in records):
            break
        time.sleep(0.05)

    proc.wait(timeout=5)
    messages = [r.getMessage() for r in records]
    assert any("line-0" in m for m in messages)
    assert reader.is_game_started() is False
    assert len(reader.get_lines()) >= 5
