"""
服务器子进程 stdout 实时读取。

单线程独占 PIPE，避免 executor 内重复 for-line 读取导致 Windows 下日志延迟（GUA-048）。
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, List, Optional

import subprocess


class ServerStdoutReader:
    """在后台线程中持续 drain 服务器 stdout，并即时写入 logger。"""

    GAME_START_KEYWORDS = (
        "游戏开始",
        "gamestart",
        "game start",
        "开始游戏",
        "round",
        "ready",
        "all players connected",
    )
    COMPLETION_FRAGMENTS = (
        "达到设定游戏次数",
        "若想再次训练请按照使用说明重新运行",
    )

    def __init__(
        self,
        process: subprocess.Popen,
        logger: logging.Logger,
        *,
        on_line: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._process = process
        self._logger = logger
        self._on_line = on_line
        self._lines: List[str] = []
        self._lock = threading.Lock()
        self._game_started = threading.Event()
        self._game_completed = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """启动读取线程；无 stdout 时返回 False。"""
        if self._process.stdout is None:
            return False
        if self._thread is not None and self._thread.is_alive():
            return True
        self._thread = threading.Thread(target=self._read_loop, name="server-stdout", daemon=True)
        self._thread.start()
        return True

    def _read_loop(self) -> None:
        stream = self._process.stdout
        if stream is None:
            return
        try:
            for line in stream:
                line_stripped = line.strip()
                with self._lock:
                    self._lines.append(line_stripped)
                if not line_stripped:
                    continue
                self._logger.info("[服务器] %s", line_stripped)
                self._flush_log_handlers()
                if self._on_line is not None:
                    try:
                        self._on_line(line_stripped)
                    except Exception:
                        pass
                lower = line_stripped.lower()
                if any(keyword in lower for keyword in self.GAME_START_KEYWORDS):
                    self._game_started.set()
                if any(frag in line_stripped for frag in self.COMPLETION_FRAGMENTS):
                    self._game_completed.set()
        except Exception as exc:
            self._logger.debug("服务器 stdout 读取结束: %s", exc)

    @staticmethod
    def _flush_log_handlers() -> None:
        for handler in logging.root.handlers:
            try:
                handler.flush()
            except Exception:
                pass

    def wait_game_started(self, timeout: float) -> bool:
        return self._game_started.wait(timeout)

    def is_game_started(self) -> bool:
        return self._game_started.is_set()

    def is_game_completed(self) -> bool:
        return self._game_completed.is_set()

    def get_lines(self) -> List[str]:
        with self._lock:
            return list(self._lines)
