#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V7 vs lalala 批跑（BatchExecutor）。

默认 3 局；可用 --games 指定目标局数（须为 3 的倍数，推荐 3 / 9 / 12）。
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]  # repo root
sys.path.insert(0, str(project_root))

from batch_executor.executor import BatchExecutor
from src.utils.v7_paths import get_server_exe, get_v7_client_scripts

log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"v7_vs_lalala_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


class _FlushingStreamHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(
            log_file,
            encoding="utf-8",
            mode="w",
            delay=False,
        ),
        _FlushingStreamHandler(),
    ],
)

logger = logging.getLogger("v7_vs_lalala")

DEFAULT_GAMES = 3
RECOMMENDED_GAMES = (3, 9, 12)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="V7 vs lalala 批跑（BatchExecutor，队胜率 KPI 入口）",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=DEFAULT_GAMES,
        help=f"目标局数，须为 3 的倍数（推荐 {', '.join(map(str, RECOMMENDED_GAMES))}）",
    )
    parser.add_argument(
        "--visible-server",
        action="store_true",
        help="弹出服务端窗口（调试用）；默认隐藏窗口以保证主日志实时输出",
    )
    return parser.parse_args(argv)


def validate_games(games: int) -> int:
    if games <= 0:
        raise SystemExit(f"错误: --games 须为正整数，得到 {games}")
    if games % 3 != 0:
        raise SystemExit(
            f"错误: --games 须为 3 的倍数（exe 每会话 3 局），得到 {games}"
        )
    return games


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    games = validate_games(args.games)

    logger.info("=" * 60)
    logger.info("🎮 V7 vs lalala - %d 局对战", games)
    logger.info("=" * 60)
    if games not in RECOMMENDED_GAMES:
        logger.warning(
            "局数 %d 不在推荐档位 %s；尾批 batch_games=1 时 victoryNum 可能对账困难",
            games,
            RECOMMENDED_GAMES,
        )

    visible_server = args.visible_server
    if visible_server:
        logger.warning(
            "已启用 --visible-server：主日志可能无法实时镜像服务端输出，"
            "进度以「批跑进行中…」心跳与 victoryNum 为准"
        )

    executor = BatchExecutor(
        target_games=games,
        server_path=get_server_exe(project_root),
        client_scripts=get_v7_client_scripts(project_root),
        diagnose_only=False,
        state_file=str(project_root / "v7_vs_lalala_state.json"),
        score_file=str(project_root / "v7_vs_lalala_scores.json"),
        enable_signal_handler=True,
        visible_server=visible_server,
    )

    try:
        executor.run()
    except KeyboardInterrupt:
        logger.info("用户中断执行")
    except Exception as e:
        logger.error("执行出错: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
