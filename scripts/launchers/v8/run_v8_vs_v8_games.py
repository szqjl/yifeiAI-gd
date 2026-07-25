#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 vs V8 自对弈批跑（BatchExecutor）— OpenGuanDan 新平台。
用 V8 引擎替代 lalala 担任对手，获得最强对手压力测试。
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from batch_executor.executor import BatchExecutor
from batch_executor.subprocess_utils import run_text_capture

log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"v8_vs_v8_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


class _FlushingStreamHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8", mode="w", delay=False),
        _FlushingStreamHandler(),
    ],
)

logger = logging.getLogger("v8_vs_v8")

DEFAULT_GAMES = 3
ENDGAME_ANOMALY_SCAN = project_root / "scripts" / "checks" / "check_endgame_anomalies.py"

_V8_SERVER_EXE = project_root / "offline_platform" / "openguandan_latest" / "guandan.exe"


def _resolve_server_exe() -> Path:
    if _V8_SERVER_EXE.exists():
        return _V8_SERVER_EXE
    jar = project_root / "offline_platform" / "openguandan_latest" / "guandan-java-1.0.0.jar"
    if jar.exists():
        return jar
    raise SystemExit(f"V8 服务器未找到: {_V8_SERVER_EXE} 或 {jar}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="V8 vs V8 自对弈批跑（最强对手压力测试）",
    )
    parser.add_argument("--games", type=int, default=DEFAULT_GAMES, help="目标局数")
    parser.add_argument("--visible-server", action="store_true", help="弹出服务端窗口")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    games = args.games
    if games <= 0:
        raise SystemExit(f"错误: --games 须为正整数，得到 {games}")

    logger.info("=" * 60)
    logger.info("V8 vs V8 自对弈 - %d 局", games)
    logger.info("=" * 60)

    server_exe = _resolve_server_exe()
    _v8_client_dir = project_root / "src" / "communication"

    client_scripts = [
        str(_v8_client_dir / "yf1_v8.py"),   # 席位 0: V8 Team A seat 0 (creator)
        str(_v8_client_dir / "yf3_v8.py"),   # 席位 1: V8 Team B seat 1 (joiner)
        str(_v8_client_dir / "yf2_v8.py"),   # 席位 2: V8 Team A seat 2 (joiner)
        str(_v8_client_dir / "yf4_v8.py"),   # 席位 3: V8 Team B seat 3 (joiner)
    ]

    state_file = str(project_root / "v8_vs_v8_state.json")
    score_file = str(project_root / "v8_vs_v8_scores.json")

    executor = BatchExecutor(
        target_games=games,
        server_path=server_exe,
        client_scripts=client_scripts,
        platform="openguandan",
        diagnose_only=False,
        state_file=state_file,
        score_file=score_file,
        enable_signal_handler=True,
        visible_server=args.visible_server,
    )

    try:
        executor.run()
        state = executor.get_state()
        if state and state.completed_games >= state.target_games:
            if ENDGAME_ANOMALY_SCAN.exists():
                cmd = [sys.executable, str(ENDGAME_ANOMALY_SCAN), "--scan-dir",
                       str(project_root / "game_records_v8"), "--limit", "20"]
                logger.info("残局异常扫描: %s", " ".join(cmd))
                try:
                    result = run_text_capture(cmd, cwd=str(project_root))
                    for line in (result.stdout or "").splitlines():
                        logger.info("[残局扫描] %s", line)
                except Exception as exc:
                    logger.warning("残局扫描失败: %s", exc)
        else:
            logger.info("批跑未完整结束（%s/%s）", getattr(state, "completed_games", None),
                        getattr(state, "target_games", None))
    except KeyboardInterrupt:
        logger.info("用户中断执行")
    except Exception as e:
        logger.error("执行出错: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
