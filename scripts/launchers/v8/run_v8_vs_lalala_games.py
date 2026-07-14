#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 vs lalala 批跑（BatchExecutor）— OpenGuanDan 新平台。
从 run_v7_vs_lalala_games.py 复制而来，适配新平台。

默认 3 局；可用 --games 指定目标局数（须为 3 的倍数，推荐 3 / 9 / 12）。
新增 --platform v1006|openguandan 切换新旧平台。
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
from src.utils.v7_paths import get_server_exe, get_v7_client_scripts

log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"v8_vs_lalala_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


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

logger = logging.getLogger("v8_vs_lalala")

DEFAULT_GAMES = 3
RECOMMENDED_GAMES = (3, 9, 12)
ENDGAME_ANOMALY_SCAN = project_root / "scripts" / "checks" / "check_endgame_anomalies.py"

# V8: OpenGuanDan 服务器默认路径
_V8_SERVER_EXE = project_root / "offline_platform" / "openguandan_latest" / "guandan.exe"


def _resolve_server_exe(platform: str) -> Path:
    """根据平台选择服务器可执行文件"""
    if platform == "openguandan":
        if _V8_SERVER_EXE.exists():
            return _V8_SERVER_EXE
        jar = project_root / "offline_platform" / "openguandan_latest" / "guandan-java-1.0.0.jar"
        if jar.exists():
            return jar
        raise SystemExit(f"V8 服务器未找到: {_V8_SERVER_EXE} 或 {jar}")
    return get_server_exe(project_root)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="V8 vs lalala 批跑（BatchExecutor，队胜率 KPI 入口）",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=DEFAULT_GAMES,
        help=f"目标局数，须为 3 的倍数（推荐 {', '.join(map(str, RECOMMENDED_GAMES))}）",
    )
    parser.add_argument(
        "--platform",
        choices=["v1006", "openguandan"],
        default="openguandan",
        help="平台类型：v1006（旧）或 openguandan（新，默认）",
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
    platform = args.platform

    logger.info("=" * 60)
    logger.info("🎮 V8 vs lalala - %d 局对战 (platform=%s)", games, platform)
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

    server_exe = _resolve_server_exe(platform)
    # V8: 用 v8 客户端脚本
    client_scripts = get_v7_client_scripts(project_root)
    # 如果 v7_paths 返回的是 v7 脚本路径，替换为 v8
    # 后续可扩展 v8_paths
    _v8_client_dir = project_root / "src" / "communication"
    client_scripts = [
        str(_v8_client_dir / "yf1_v8.py"),
        str(_v8_client_dir / "v8_lalala_adapter.py"),
        str(_v8_client_dir / "yf2_v8.py"),
        str(_v8_client_dir / "v8_lalala_adapter.py"),  # client4 uses same script
    ]

    # V8: 专用状态文件和战绩文件
    state_file = str(project_root / "v8_vs_lalala_state.json")
    score_file = str(project_root / "v8_vs_lalala_scores.json")

    executor = BatchExecutor(
        target_games=games,
        server_path=server_exe,
        client_scripts=client_scripts,
        platform=platform,
        diagnose_only=False,
        state_file=state_file,
        score_file=score_file,
        enable_signal_handler=True,
        visible_server=visible_server,
    )

    try:
        executor.run()
        state = executor.get_state()
        if state and state.completed_games >= state.target_games:
            _run_endgame_anomaly_scan(
                logger=logger,
                scan_dir=project_root / "game_records_v8",
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
