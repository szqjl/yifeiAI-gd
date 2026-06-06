# -*- coding: utf-8 -*-
"""lalala WebSocket 客户端统一启动（供 run_lalala_client3/4 调用）。"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMM_DIR = Path(__file__).resolve().parent

# 连接前等待（秒）：仅需保证在 batch 顺序启动后错开连入，不必 10/20s
CONNECT_DELAY = {
    "client3": 3,
    "client4": 11,  # 批跑末席：进程启动后多等 5s 再进入连入门闩（原 6s）
}


def _bootstrap_paths() -> None:
    for path in (str(REPO_ROOT), str(COMM_DIR)):
        if path not in sys.path:
            sys.path.insert(0, path)


def launch_lalala_client(client_name: str, *, connect_delay: int | None = None) -> None:
    _bootstrap_paths()

    delay = CONNECT_DELAY.get(client_name, 3) if connect_delay is None else connect_delay
    print(f"[{client_name}] 启动 lalala 客户端，{delay}s 后连接 ws://127.0.0.1:23456/game/{client_name}", flush=True)

    if delay > 0:
        time.sleep(delay)

    from lalala_adapter import run_lalala_client

    run_lalala_client(client_name)
