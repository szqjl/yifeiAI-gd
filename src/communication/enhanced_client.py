# -*- coding: utf-8 -*-
"""
增强的掼蛋AI客户端
集成了记牌、状态管理、决策引擎和配合策略
"""

import asyncio
import websockets
import json
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from game_logic.enhanced_state import EnhancedGameStateManager
from decision.decision_engine import DecisionEngine


class EnhancedGuandanClient:
    """增强的掼蛋AI客户端"""
    
    def __init__(self, user_info: str):
        self.user_info = user_info
        self.websocket = None
        
        # 初始化状态管理器
        self.state_manager = EnhancedGameStateManager()
        
        # 初始化决策引擎
        self.decision_engine = DecisionEngine(self.state_manager)
    
    async def connect(self):
        """连接WebSocket服务器"""
        uri = f"ws://127.0.0.1:23456/game/{self.user_info}"
        try:
            self.websocket = await websockets.connect(uri)
            print(f"[{self.user_info}] Connected successfully!")
            await self.handle_messages()
        except Exception as e:
            print(f"[{self.user_info}] Connection error: {e}")
    
    async def handle_messages(self):
        """处理WebSocket消息"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    print(f"[{self.user_info}] Received: type={data.get('type')}, stage={data.get('stage')}")
                    
                    # 更新状态
                    self.state_manager.update_from_message(data)
                    
                    # 如果是act消息，需要做出决策
                    if data.get("type") == "act":
                        act_index = self.decision_engine.decide(data)
                        response = json.dumps({"actIndex": act_index})
                        await self.websocket.send(response)
                        print(f"[{self.user_info}] Sent: {response}")
                        
                        # 打印状态摘要
                        summary = self.state_manager.get_state_summary()
                        print(f"[{self.user_info}] State: {summary}")
                    
                except json.JSONDecodeError as e:
                    print(f"[{self.user_info}] Invalid JSON: {e}")
                except Exception as e:
                    print(f"[{self.user_info}] Error processing message: {e}")
                    
        except websockets.ConnectionClosed as e:
            print(f"[{self.user_info}] Connection closed: {e}")
        finally:
            print(f"[{self.user_info}] Disconnected")
    
    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()


async def main(user_info: str):
    """主函数"""
    client = EnhancedGuandanClient(user_info)
    try:
        await client.connect()
    except KeyboardInterrupt:
        print(f"\n[{user_info}] Interrupted by user")
        await client.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_info = sys.argv[1]
    else:
        user_info = "EnhancedClient"
    
    asyncio.run(main(user_info))

