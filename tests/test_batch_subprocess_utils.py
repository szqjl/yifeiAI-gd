"""batch_executor.subprocess_utils 单元测试。"""

from __future__ import annotations

import subprocess
import sys

from batch_executor.subprocess_utils import run_text_capture


def test_run_text_capture_decodes_gbk_child_output():
    """Windows 控制台默认 GBK 时，批后扫描不应触发 UTF-8 解码异常。"""
    script = "print('扫描目录: game_records_v7')"
    result = run_text_capture([sys.executable, "-c", script])
    assert result.returncode == 0
    assert "game_records_v7" in result.stdout


def test_run_text_capture_replaces_invalid_bytes():
    script = "import sys; sys.stdout.buffer.write(b'\\xc3\\x28')"
    result = run_text_capture([sys.executable, "-c", script])
    assert result.returncode == 0
    assert result.stdout
