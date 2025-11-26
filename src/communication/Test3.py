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
                    # 打印详细的游戏状态信息（模仿原示例客户端）
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
        """打印游戏状态信息（中文格式，与原示例客户端完全对齐）"""
        if data.get("type") == "notify":
            stage = data.get("stage", "")
            if stage == "beginning":
                print(f"[{self.user_info}] 游戏开始，收到手牌: {data.get('handCards', [])}")
            elif stage == "episodeOver":
                order = data.get("order", [])
                cur_rank = data.get("curRank", "")
                rest_cards = data.get("restCards", [])
                print(f"[{self.user_info}] 小局结束，顺序: {order}，当前等级: {cur_rank}，剩余牌: {rest_cards}")
            elif stage == "gameResult":
                victory_num = data.get("victoryNum", [])
                print(f"[{self.user_info}] 游戏结果，胜利次数: {victory_num}")

        elif data.get("type") == "act":
            # 完全对齐原始客户端的输出格式
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

            # 输出格式与原始客户端完全一致（去掉用户前缀以匹配原格式）
            print(f"我方等级：{self_rank}，对方等级：{oppo_rank}，当前等级{cur_rank}")
            print(f"当前动作为{cur_pos}号-动作{cur_action}，最大动作为{greater_pos}号-动作{greater_action}，目前可选动作如下：")
            print(f"{action_list}")
            print(f"可选动作范围为：0至{index_range}")

            # 保存actionList到单独的日志文件（用于分析）
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
    client = BasicGuandanClient("Test3")
    await client.connect()

if __name__ == "__main__":
    asyncio.run(main())
