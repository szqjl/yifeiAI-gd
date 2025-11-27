# -*- coding: utf-8 -*-
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
                    # Print game state
                    self.print_game_state(data)
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

    def print_game_state(self, data):
        """Print game state information"""
        if data.get("type") == "notify":
            stage = data.get("stage", "")
            if stage == "beginning":
                print(f"[{self.user_info}] Game start, hand cards: {data.get('handCards', [])}")
            elif stage == "episodeOver":
                order = data.get("order", [])
                cur_rank = data.get("curRank", "")
                rest_cards = data.get("restCards", [])
                print(f"[{self.user_info}] Episode over, order: {order}, rank: {cur_rank}, rest: {rest_cards}")
            elif stage == "gameResult":
                victory_num = data.get("victoryNum", [])
                print(f"[{self.user_info}] Game result, victory: {victory_num}")

        elif data.get("type") == "act":
            # Print action info
            public_info = data.get("publicInfo", [])
            self_rank = data.get("selfRank", "")
            oppo_rank = data.get("oppoRank", "")
            cur_rank = data.get("curRank", "")
            stage = data.get("stage", "")
            cur_pos = data.get("curPos", -1)
            cur_action = data.get("curAction", [None, None, None])
            greater_pos = data.get("greaterPos", -1)
            greater_action = data.get("greaterAction", [None, None, None])
            action_list = data.get("actionList", [])
            index_range = data.get("indexRange", 0)

            # Print decision info
            print(f"Self rank: {self_rank}, Oppo rank: {oppo_rank}, Current rank: {cur_rank}")
            print(f"Current pos: {cur_pos} - action: {cur_action}, Greater pos: {greater_pos} - action: {greater_action}")
            print(f"Action list: {action_list}")
            print(f"Index range: 0-{index_range}")

            # Save action list to log file
            with open(f"Testscore/{self.user_info}", "a", encoding="utf-8") as f:
                f.write(json.dumps(action_list, ensure_ascii=False) + "\n")
    
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

async def main():
    client = BasicGuandanClient("Test4")
    await client.connect()

if __name__ == "__main__":
    asyncio.run(main())
