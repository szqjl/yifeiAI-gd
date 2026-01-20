"""启动lalala client3"""
import time
import logging
from lalala_adapter import run_lalala_client

# Add delay before connection
logger = logging.getLogger("client3")
logger.info("[client3] 等待连接延迟 10 秒，确保第二个位置(1号位)...")
time.sleep(10)
logger.info("[client3] 开始连接 ws://127.0.0.1:23456/game/client3")

# Ensure URI is correct (search for websocket uri and replace if needed)
uri = "ws://127.0.0.1:23456/game/client3"

if __name__ == "__main__":
    run_lalala_client("client3")
