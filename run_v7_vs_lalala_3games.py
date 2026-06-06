#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行V7 vs lalala 3局对战
使用batch_executor模块
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from batch_executor.executor import BatchExecutor
from src.utils.v7_paths import get_server_exe, get_v7_client_scripts

log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"v7_vs_lalala_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("v7_vs_lalala")


def main():
    logger.info("=" * 60)
    logger.info("🎮 V7 vs lalala - 3局对战")
    logger.info("=" * 60)

    executor = BatchExecutor(
        target_games=3,
        server_path=get_server_exe(project_root),
        client_scripts=get_v7_client_scripts(project_root),
        diagnose_only=False,
        state_file=str(project_root / "v7_vs_lalala_state.json"),
        score_file=str(project_root / "v7_vs_lalala_scores.json"),
        enable_signal_handler=True,
        visible_server=True,
    )

    try:
        executor.run()
    except KeyboardInterrupt:
        logger.info("用户中断执行")
    except Exception as e:
        logger.error(f"执行出错: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
