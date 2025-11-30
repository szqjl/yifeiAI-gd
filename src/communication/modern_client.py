# -*- coding: utf-8 -*-
import asyncio
import websockets
import json
import sys
from pathlib import Path

# Add src to path
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from game_logic.enhanced_state import EnhancedGameStateManager
from decision.decision_engine import DecisionEngine

class ModernGuandanClient:
    def __init__(self, user_info, server_url=None):
        self.user_info = user_info
        self.server_url = server_url or f"ws://127.0.0.1:23456/game/{user_info}"
        self.websocket = None
        
        # Initialize advanced components
        self.state_manager = EnhancedGameStateManager()
        self.decision_engine = DecisionEngine(self.state_manager)
        
    async def connect(self):
        try:
            print(f"[{self.user_info}] Connecting to {self.server_url}...")
            async with websockets.connect(self.server_url) as websocket:
                self.websocket = websocket
                print(f"[{self.user_info}] Connected successfully!")
                await self.handle_messages()
        except Exception as e:
            print(f"[{self.user_info}] Connection error: {e}")
            
    async def handle_messages(self):
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    # print(f"[{self.user_info}] Received: {data.get('type')}")
                    
                    # Update state
                    self.state_manager.update_from_message(data)
                    
                    # Handle action request
                    if data.get("type") == "act":
                        act_index = self.decision_engine.decide(data)
                        response = json.dumps({"actIndex": act_index})
                        await self.websocket.send(response)
                        print(f"[{self.user_info}] Sent action index: {act_index}")
                        
                except json.JSONDecodeError:
                    print(f"[{self.user_info}] Invalid JSON received")
                except Exception as e:
                    print(f"[{self.user_info}] Error processing message: {e}")
                    import traceback
                    traceback.print_exc()
                    
        except websockets.ConnectionClosed:
            print(f"[{self.user_info}] Connection closed")

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Modern Guandan AI Client")
    parser.add_argument("--user", default="ModernAI", help="User info/name")
    parser.add_argument("--url", help="WebSocket URL")
    args = parser.parse_args()
    
    client = ModernGuandanClient(args.user, args.url)
    await client.connect()

if __name__ == "__main__":
    asyncio.run(main())
