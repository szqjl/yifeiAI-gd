# -*- coding: utf-8 -*-
"""
适配器：DanZero 客户端（v1006 websockets 版，席位 client3/client4）。
v7Dan vs DanZero 批跑中 DanZero 侧使用；决策走 danzero_policy（骨架恒选 0）。
"""
import asyncio
import websockets
import json
import sys
import logging
from pathlib import Path

# 设置控制台编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

_COMM_DIR = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_REPO_ROOT), str(_COMM_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
from datetime import datetime
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(
            log_dir / f"danzero_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding='utf-8',
        ),
        logging.StreamHandler(),
    ],
)

try:
    from batch_executor.client_ready import mark_client_ready, mark_game_ready, wait_for_connect_turn
except ImportError:
    def mark_client_ready(_client_id: str) -> None:
        pass

    def mark_game_ready(_client_id: str) -> None:
        pass

    def wait_for_connect_turn(_client_id: str, *, timeout: float = 120.0, poll_interval: float = 0.5) -> bool:
        return True

from danzero_policy import DanZeroPolicy


class DanZeroWebsocketsClient:
    """使用websockets库的DanZero客户端（队B席位 client3/client4）。"""

    def __init__(self, user_info: str):
        self.user_info = user_info
        self.logger = logging.getLogger(f"danzero_{user_info}")
        self.websocket = None
        self._game_ready_marked = False
        self.policy = DanZeroPolicy(user_info)

    async def connect(self):
        uri = f"ws://127.0.0.1:23456/game/{self.user_info}"
        try:
            gate_ok = await asyncio.to_thread(
                wait_for_connect_turn,
                self.user_info,
                timeout=120.0,
            )
            if not gate_ok:
                print(f"[{self.user_info}] 前序席位未就绪，放弃连接")
                return

            self.websocket = await websockets.connect(
                uri,
                ping_interval=None,
                ping_timeout=None,
            )
            mark_client_ready(self.user_info)
            print(f"[{self.user_info}] 连接成功! 已登记就绪")
            await self.handle_messages()
        except Exception as e:
            print(f"[{self.user_info}] 连接错误: {e}")

    async def handle_messages(self):
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    if not self._game_ready_marked:
                        self._game_ready_marked = True
                        mark_game_ready(self.user_info)
                        print(f"[{self.user_info}] ✓ 首条消息到达，game_ready")

                    data = self.policy.preprocess(data)
                    msg_type = data.get("type", "")
                    if msg_type != "act":
                        continue

                    action_list = data.get("actionList") or []
                    if not isinstance(action_list, list) or not action_list:
                        print(f"[{self.user_info}] actionList 缺失/空，回退 actIndex=0")
                        self.logger.info("actionList 缺失/空，回退 actIndex=0 stage=%s", data.get("stage"))
                        act_index = 0
                    else:
                        act_index = await asyncio.to_thread(self.policy.decide, data)
                        if not (0 <= act_index < len(action_list)):
                            print(f"[{self.user_info}] actIndex 越界: {act_index}，回退 0")
                            act_index = 0

                    _selected = action_list[act_index] if action_list else None
                    self.logger.info(
                        "选择动作: actIndex=%d action=%s stage=%s curAction=%s",
                        act_index,
                        _selected,
                        data.get("stage"),
                        data.get("curAction"),
                    )
                    print(f"[{self.user_info}] 选择动作: {act_index} {_selected}")
                    await self.websocket.send(json.dumps({"actIndex": act_index}))

                except json.JSONDecodeError:
                    print(f"[{self.user_info}] 无效的JSON")
                except Exception as e:
                    print(f"[{self.user_info}] 消息处理错误: {e}")
                    import traceback
                    traceback.print_exc()

        except websockets.ConnectionClosed as e:
            print(f"[{self.user_info}] 连接关闭: {e}")
        except Exception as e:
            print(f"[{self.user_info}] 连接错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print(f"[{self.user_info}] 断开连接")


def run_danzero_client(client_name: str):
    """运行DanZero客户端。Args: client_name: client3 / client4"""
    print(f"[{client_name}] 启动DanZero客户端（websockets版本，骨架策略）")
    client = DanZeroWebsocketsClient(client_name)
    asyncio.run(client.connect())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python danzero_adapter.py <client3|client4>")
        sys.exit(1)
    run_danzero_client(sys.argv[1])
