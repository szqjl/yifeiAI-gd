#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标准掼蛋客户端 - 位置1（使用websockets库）
用于自动化测试，不做任何复杂的决策
"""

import asyncio
import websockets
import json
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('StdClient1')

async def play_game():
    """连接到游戏并自动出牌"""
    uri = "ws://127.0.0.1:23456/game/client1"

    try:
        async with websockets.connect(uri, ping_interval=30) as websocket:
            logger.info(f"✓ 已连接到服务器: {uri}")

            while True:
                message = await websocket.recv()
                msg_data = json.loads(message)
                msg_type = msg_data.get("type")

                if msg_type == "notify":
                    stage = msg_data.get("stage", "unknown")
                    logger.info(f"收到通知: stage={stage}")

                elif msg_type == "act":
                    stage = msg_data.get("stage", "unknown")
                    action_list = msg_data.get("actionList", [])
                    logger.info(f"需要出牌: stage={stage}, 可选动作数={len(action_list)}")

                    # 简单策略：始终选择第一个动作（PASS或最弱的牌）
                    act_index = 0
                    logger.info(f"选择动作索引: {act_index}")

                    response = {"actIndex": act_index}
                    await websocket.send(json.dumps(response))

    except websockets.exceptions.ConnectionClosedOK:
        logger.info("游戏结束，连接正常关闭")
    except KeyboardInterrupt:
        logger.info("客户端被中断")
    except Exception as e:
        logger.error(f"错误: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(play_game())
