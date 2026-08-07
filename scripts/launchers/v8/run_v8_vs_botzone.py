#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 vs Botzone — 通过 Botzone Local AI HTTP API 对战 DanLM 或其他 Botzone Bot。

使用方式:
  1. 在 https://www.botzone.org.cn 注册账号
  2. "My Bots" → "Local AI Config" → 设置 secret，复制 API URL
  3. 从 API URL 中提取 user_id 和 api_key
  4. 运行本脚本:
     python scripts/launchers/v8/run_v8_vs_botzone.py \\
         --user-id YOUR_USER_ID \\
         --api-key YOUR_API_KEY \\
         --opponent-bot-id <DanLM_bot_id> \\
         --games 3

Botzone 对局说明:
  - 自动创建 2v2 对局，V8 (席位 0) + 另一个 V8 (席位 2) vs 对手 bot × 2
  - 对手热门 bot: DanLM (掼蛋大模型，Botzone 排名 #1)
  - 更多 bot 列表: https://www.botzone.org.cn/games/GuanDan
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from src.communication.botzone_adapter import BotzoneAdapter

# Windows 下 stdout/stderr 默认 GBK，nohup 重定向后 StreamHandler 会写成乱码；
# 统一为 UTF-8，保证脚本自身 FileHandler 与重定向日志编码一致。
for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream is not None and hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"v8_vs_botzone_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8", mode="w"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("v8_vs_botzone")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="V8 vs Botzone — Local AI 模式",
    )
    parser.add_argument("--user-id", required=True, help="Botzone 用户 ID")
    parser.add_argument("--api-key", required=True, help="Botzone API 密钥")
    parser.add_argument("--base-url", default="https://www.botzone.org.cn/api",
                        help="Botzone API 基础 URL（默认 https://www.botzone.org.cn/api）")
    parser.add_argument("--opponent-bot-id", default=None,
                        help="对手 Bot ID（不指定则只监听手动创建的对局）")
    parser.add_argument("--teammate-bot-id", default=None,
                        help="队友 Bot ID（默认同对手 bot，不推荐；推荐 Joker: 686264afa4349e61674f526a）")
    parser.add_argument("--games", type=int, default=3,
                        help="对局数（仅对手 bot 模式有效，默认 3）")
    parser.add_argument("--player-id", type=int, default=0,
                        help="V8 座位（默认 0）。手动创建对局时 V8 可能是 0 或 2；"
                             "决策引擎以 deal 的 your_id 为准动态适配，本参数仅作初始默认。")
    return parser.parse_args(argv)


async def main_async(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    logger.info("=" * 60)
    logger.info("V8 vs Botzone (Local AI)")
    logger.info("  user_id: %s", args.user_id)
    logger.info("  opponent_bot_id: %s", args.opponent_bot_id or "（手动创建对局）")
    logger.info("=" * 60)

    # Import V8 decision engine
    try:
        from src.v.nn import UltimateWinRateEngineV7
        logger.info("加载 V8 决策引擎...")
        engine = UltimateWinRateEngineV7(
            player_id=args.player_id, use_grouping_engine=True)
        logger.info("V8 决策引擎加载完成")
    except ImportError as e:
        logger.error("加载 V8 决策引擎失败: %s", e)
        logger.error("请确保在仓库根目录运行")
        sys.exit(1)
    except Exception as e:
        logger.error("V8 引擎初始化失败: %s", e, exc_info=True)
        sys.exit(1)

    adapter = BotzoneAdapter(
        user_id=args.user_id,
        api_key=args.api_key,
        base_url=args.base_url,
        decision_engine=engine,
        player_id=args.player_id,
    )

    # Start listening FIRST (background task), then create matches
    listen_task = asyncio.create_task(adapter.run())

    # Small delay to ensure listener is ready
    await asyncio.sleep(2)

    # Create matches while listener is running
    if args.opponent_bot_id:
        logger.info("即将创建 %d 局对局 vs %s...", args.games, args.opponent_bot_id)
        for i in range(args.games):
            logger.info("创建对局 %d/%d...", i + 1, args.games)
            match_id = await adapter.create_match(
                game_name="GuanDan",
                opponent_bot_id=args.opponent_bot_id,
                teammate_bot_id=args.teammate_bot_id,
            )
            if match_id:
                logger.info("对局创建成功: %s", match_id)
            else:
                logger.error("对局创建失败")
            await asyncio.sleep(2)

    # Keep listening (block forever)
    await listen_task


def main(argv: list[str] | None = None) -> None:
    asyncio.run(main_async(argv))


if __name__ == "__main__":
    main()
