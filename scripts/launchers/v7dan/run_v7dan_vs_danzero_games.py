#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v7Dan vs DanZero 批跑（BatchExecutor）。

队 A：yf1_v7dan + yf2_v7dan（v7 引擎的 v7Dan 身份，牌谱 game_records_v7dan/）
队 B：client3 + client4（DanZero 侧，danzero_policy 占位策略）

默认 3 局；可用 --games 指定目标局数（v1006 每会话 3 局，须为 3 的倍数）。
DanZero 模型未接入前，本骨架即可跑通全流程（对手恒选 actionList[0]）。
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
from batch_executor.subprocess_utils import run_text_capture
from src.utils.v7_paths import get_server_exe

log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"v7dan_vs_danzero_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


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

logger = logging.getLogger("v7dan_vs_danzero")

DEFAULT_GAMES = 3
RECOMMENDED_GAMES = (3, 9, 12)
ENDGAME_ANOMALY_SCAN = project_root / "scripts" / "checks" / "check_endgame_anomalies.py"

CLIENT_SCRIPTS = [
    project_root / "src" / "communication" / "yf1_v7dan.py",
    project_root / "src" / "communication" / "run_danzero_client3.py",
    project_root / "src" / "communication" / "yf2_v7dan.py",
    project_root / "src" / "communication" / "run_danzero_client4.py",
]

RECORD_DIR = project_root / "game_records_v7dan"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="v7Dan vs DanZero 批跑（BatchExecutor，队胜率 KPI 入口）",
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


def _run_endgame_anomaly_scan(
    *,
    logger: logging.Logger,
    scan_dir: Path,
    limit: int = 20,
) -> bool:
    """批跑完成后自动执行残局异常扫描；失败仅告警，不阻断主流程。"""
    if not ENDGAME_ANOMALY_SCAN.exists():
        logger.warning("残局异常扫描脚本不存在，跳过: %s", ENDGAME_ANOMALY_SCAN)
        return False

    cmd = [
        sys.executable,
        str(ENDGAME_ANOMALY_SCAN),
        "--scan-dir",
        str(scan_dir),
        "--limit",
        str(limit),
    ]
    logger.info("开始批后残局异常扫描: %s", " ".join(cmd))
    try:
        result = run_text_capture(cmd, cwd=str(project_root))
    except Exception as exc:
        logger.warning("残局异常扫描执行失败: %s", exc)
        return False

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    if stdout:
        for line in stdout.splitlines():
            logger.info("[残局扫描] %s", line)
    if stderr:
        for line in stderr.splitlines():
            logger.warning("[残局扫描] %s", line)

    if result.returncode != 0:
        logger.warning("残局异常扫描返回非 0: %d", result.returncode)
        return False
    return True


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    games = validate_games(args.games)

    logger.info("=" * 60)
    logger.info("🎮 v7Dan vs DanZero - %d 局对战", games)
    logger.info("   队A: yf1_v7dan + yf2_v7dan   队B: client3 + client4 (DanZero)")
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
        client_scripts=[str(p) for p in CLIENT_SCRIPTS],
        diagnose_only=False,
        state_file=str(project_root / "v7dan_vs_danzero_state.json"),
        score_file=str(project_root / "v7dan_vs_danzero_scores.json"),
        enable_signal_handler=True,
        visible_server=visible_server,
    )

    try:
        executor.run()
        state = executor.get_state()
        if state and state.completed_games >= state.target_games:
            _run_endgame_anomaly_scan(
                logger=logger,
                scan_dir=RECORD_DIR,
            )
        else:
            logger.info(
                "批跑未完整结束（completed_games=%s/%s），跳过残局异常扫描",
                getattr(state, "completed_games", None),
                getattr(state, "target_games", None),
            )
    except KeyboardInterrupt:
        logger.info("用户中断执行")
    except Exception as e:
        logger.error("执行出错: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
