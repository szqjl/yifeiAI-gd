# -*- coding: utf-8 -*-
"""
Test1 - 使用lalala策略的客户端
直接使用lalala的决策引擎
"""
import asyncio
import websockets
import json
import sys
from pathlib import Path

# 添加lalala路径
LALALA_PATH = r"D:\NYGD\lalala"
if LALALA_PATH not in sys.path:
    sys.path.insert(0, LALALA_PATH)

# 导入lalala的核心模块
from state import State
from action import Action

class LalalaGuandanClient:
    def __init__(self, user_info):
        self.user_info = user_info
        self.websocket = None
        
        # 使用lalala的State和Action
        self.state = State(user_info)
        self.action = Action(user_info)
        
        print(f"[{user_info}] 使用lalala决策引擎")
    
    async def connect(self):
        uri = f"ws://127.0.0.1:23456/game/{self.user_info}"
        try:
            self.websocket = await websockets.connect(uri)
            print(f"[{self.user_info}] 连接成功!")
            await self.handle_messages()
        except Exception as e:
            print(f"[{self.user_info}] 连接错误: {e}")
    
    async def handle_messages(self):
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    
                    # 预处理：解析字符串形式的列表
                    import ast
                    for field in ['curAction', 'greaterAction', 'handCards']:
                        if field in data and isinstance(data[field], str):
                            try:
                                data[field] = ast.literal_eval(data[field])
                            except:
                                pass
                    
                    # 转换牌格式：'H3' -> ['H', '3']
                    data = self._convert_card_format(data)
                    
                    # 使用lalala的状态解析
                    self.state.parse(data)
                    
                    # 如果需要做出动作选择
                    if "actionList" in data:
                        # 使用lalala的决策逻辑
                        act_index = self.action.rule_parse(
                            data,
                            self.state._myPos,
                            self.state.remain_cards,
                            self.state.history,
                            self.state.remain_cards_classbynum,
                            self.state.pass_num,
                            self.state.my_pass_num,
                            self.state.tribute_result
                        )
                        
                        print(f"[{self.user_info}] 选择动作: {act_index}")
                        response = json.dumps({"actIndex": act_index})
                        await self.websocket.send(response)
                        
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
        finally:
            print(f"[{self.user_info}] 断开连接")
    
    def _convert_card_format(self, data):
        """转换牌格式以兼容lalala"""
        def convert_card(card):
            if isinstance(card, str):
                if len(card) == 1:
                    return [card, card]
                elif len(card) >= 2:
                    suit = card[0]
                    rank = card[1:].replace('10', 'T')
                    return [suit, rank]
            elif isinstance(card, list) and len(card) == 2:
                return [card[0], str(card[1]).replace('10', 'T')]
            return card
        
        def convert_cards_list(cards):
            if isinstance(cards, list):
                return [convert_card(c) for c in cards]
            return cards
        
        # 转换各字段
        if "handCards" in data:
            data["handCards"] = convert_cards_list(data["handCards"])
        
        if "curAction" in data and isinstance(data["curAction"], list):
            if len(data["curAction"]) > 2 and data["curAction"][2] != "PASS":
                data["curAction"] = [
                    data["curAction"][0],
                    data["curAction"][1],
                    convert_cards_list(data["curAction"][2])
                ]
        
        if "greaterAction" in data and isinstance(data["greaterAction"], list):
            if len(data["greaterAction"]) > 2 and data["greaterAction"][2] != "PASS":
                data["greaterAction"] = [
                    data["greaterAction"][0],
                    data["greaterAction"][1],
                    convert_cards_list(data["greaterAction"][2])
                ]
        
        if "actionList" in data:
            new_action_list = []
            for action in data["actionList"]:
                if len(action) > 2 and action[2] != "PASS":
                    new_action_list.append([
                        action[0],
                        action[1],
                        convert_cards_list(action[2])
                    ])
                else:
                    new_action_list.append(action)
            data["actionList"] = new_action_list
        
        if "publicInfo" in data:
            for i, player_info in enumerate(data["publicInfo"]):
                if "playArea" in player_info and player_info["playArea"] is not None:
                    play_area = player_info["playArea"]
                    if isinstance(play_area, dict):
                        if "actIndex" in play_area and "type" not in play_area:
                            data["publicInfo"][i]["playArea"] = ["PASS", "", "PASS"]
                        else:
                            card_type = play_area.get("type", "PASS")
                            rank = play_area.get("rank", "")
                            actions = play_area.get("actions", [])
                            if actions and actions != "PASS":
                                data["publicInfo"][i]["playArea"] = [
                                    card_type,
                                    rank,
                                    convert_cards_list(actions)
                                ]
                            else:
                                data["publicInfo"][i]["playArea"] = [card_type, rank, "PASS"]
                    elif isinstance(play_area, list) and len(play_area) > 2:
                        if play_area[2] != "PASS":
                            data["publicInfo"][i]["playArea"] = [
                                play_area[0],
                                play_area[1],
                                convert_cards_list(play_area[2])
                            ]
        
        return data


async def main():
    client = LalalaGuandanClient("Test2")
    await client.connect()

if __name__ == "__main__":
    asyncio.run(main())
