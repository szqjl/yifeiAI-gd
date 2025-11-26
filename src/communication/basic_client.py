import asyncio
import websockets
import json
import random

class BasicGuandanClient:
    def __init__(self, user_info):
        self.user_info = user_info
        self.websocket = None
        self.game_state = {
            "handCards": [],
            "myPos": None,
            "curPos": None,
            "stage": None,
            "curRank": "2"
        }
    
    async def connect(self):
        uri = f"ws://127.0.0.1:23456/game/{self.user_info}"
        try:
            self.websocket = await websockets.connect(uri)
            print(f"[{self.user_info}] Connected successfully!")
            await self.handle_messages()
        except Exception as e:
            print(f"[{self.user_info}] Connection error: {e}")
    
    async def handle_messages(self):
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    print(f"[{self.user_info}] Received message: {json.dumps(data, indent=2)}")
                    self.update_game_state(data)
                    
                    if data.get("type") == "act":
                        act_index = self.make_decision(data)
                        response = json.dumps({"actIndex": act_index})
                        await self.websocket.send(response)
                        print(f"[{self.user_info}] Sent response: {response}")
                except json.JSONDecodeError:
                    print(f"[{self.user_info}] Invalid JSON received")
        except websockets.ConnectionClosed as e:
            print(f"[{self.user_info}] Connection closed: {e}")
        finally:
            print(f"[{self.user_info}] Disconnected")
    
    def update_game_state(self, data):
        self.game_state["handCards"] = data.get("handCards", self.game_state["handCards"])
        self.game_state["myPos"] = data.get("myPos", self.game_state["myPos"])
        self.game_state["curPos"] = data.get("curPos", self.game_state["curPos"])
        self.game_state["stage"] = data.get("stage", self.game_state["stage"])
        self.game_state["curRank"] = data.get("curRank", self.game_state["curRank"])
    
    def make_decision(self, data):
        # Placeholder: Random decision from actionList
        action_list = data.get("actionList", [])
        if not action_list:
            return 0
        return random.randint(0, len(action_list) - 1)

async def main(user_info):
    client = BasicGuandanClient(user_info)
    await client.connect()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        user_info = sys.argv[1]
    else:
        user_info = "TestClient"
    asyncio.run(main(user_info))
