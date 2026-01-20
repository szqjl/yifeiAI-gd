"""启动lalala client4"""
import time
import logging

# Add delay before connection
logger = logging.getLogger("client4")
logger.info("[client4] 等待连接延迟 20 秒，确保第四个位置(3号位)...")
time.sleep(20)
logger.info("[client4] 开始连接 ws://127.0.0.1:23456/game/client4")

# Ensure URI is correct
uri = "ws://127.0.0.1:23456/game/client4"

from lalala_adapter import run_lalala_client

if __name__ == "__main__":
    run_lalala_client("client4")
