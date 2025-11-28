"""
适配器：将lalala的决策逻辑移植到websockets客户端
"""
import asyncio
import websockets
import json
import ast
import sys
import os

# 添加lalala目录到路径
LALALA_PATH = r"D:\NYGD\lalala"
if LALALA_PATH not in sys.path:
    sys.path.insert(0, LALALA_PATH)

# 导入lalala的核心逻辑
try:
    from state import State
    from action import Action
    print("✓ 成功导入lalala核心模块")
except ImportError as e:
    print(f"✗ 导入lalala模块失败: {e}")
    print(f"请确保 {LALALA_PATH} 存在且包含state.py和action.py")
    sys.exit(1)


class LalalaWebsocketsClient:
    """使用websockets库的lalala客户端"""
    
    def __init__(self, user_info):
        self.user_info = user_info
        self.websocket = None
        
        # 使用lalala的State和Action
        self.state = State(user_info)
        self.action = Action(user_info)
    
    async def connect(self):
        uri = f"ws://127.0.0.1:23456/game/{self.user_info}"
        try:
            self.websocket = await websockets.connect(uri)
            print(f"[{self.user_info}] 连接成功!")
            await self.handle_messages()
        except Exception as e:
            print(f"[{self.user_info}] 连接错误: {e}")
    
    def convert_card_format(self, data):
        """
        转换牌的格式：从 'H3' 转换为 ['H', '3']
        lalala期望的格式是列表，而不是字符串
        """
        def convert_card(card):
            if isinstance(card, str):
                if len(card) == 1:
                    # 大小王: 'R' -> ['R', 'R'], 'B' -> ['B', 'B']
                    return [card, card]
                elif len(card) >= 2:
                    # 'H3' -> ['H', '3']
                    # 'HT' -> ['H', 'T']
                    # 'H10' -> ['H', 'T'] (10用T表示)
                    suit = card[0]
                    rank = card[1:].replace('10', 'T')
                    return [suit, rank]
            elif isinstance(card, list) and len(card) == 2:
                # 已经是正确格式，但检查是否需要转换10
                return [card[0], str(card[1]).replace('10', 'T')]
            return card
        
        def convert_cards_list(cards):
            if isinstance(cards, list):
                return [convert_card(c) for c in cards]
            elif isinstance(cards, str) and cards != "PASS":
                # 单个牌字符串也转换
                return convert_card(cards)
            return cards
        
        # 转换各种可能包含牌的字段
        if "handCards" in data:
            data["handCards"] = convert_cards_list(data["handCards"])
        
        if "curAction" in data:
            cur_action = data["curAction"]
            # 如果是字符串，尝试解析为JSON
            if isinstance(cur_action, str):
                try:
                    cur_action = json.loads(cur_action)
                except:
                    pass
            
            if isinstance(cur_action, list) and len(cur_action) > 2:
                cards = cur_action[2]
                # 如果cards是字符串，尝试解析
                if isinstance(cards, str) and cards != "PASS":
                    try:
                        # 先尝试JSON
                        cards = json.loads(cards)
                    except Exception as e1:
                        try:
                            # 再尝试Python字面量（支持单引号）
                            cards = ast.literal_eval(cards)
                        except Exception as e2:
                            print(f"[DEBUG] Failed to parse cards: {cards}")
                            print(f"[DEBUG] JSON error: {e1}")
                            print(f"[DEBUG] AST error: {e2}")
                            pass
                
                if cards != "PASS":
                    data["curAction"] = [
                        cur_action[0],
                        cur_action[1],
                        convert_cards_list(cards)
                    ]
                else:
                    data["curAction"] = cur_action
            else:
                data["curAction"] = cur_action
        
        if "greaterAction" in data:
            greater_action = data["greaterAction"]
            # 如果是字符串，尝试解析为JSON
            if isinstance(greater_action, str):
                try:
                    greater_action = json.loads(greater_action)
                except:
                    pass
            
            if isinstance(greater_action, list) and len(greater_action) > 2:
                cards = greater_action[2]
                # 如果cards是字符串，尝试解析
                if isinstance(cards, str) and cards != "PASS":
                    try:
                        # 先尝试JSON
                        cards = json.loads(cards)
                    except:
                        try:
                            # 再尝试Python字面量（支持单引号）
                            cards = ast.literal_eval(cards)
                        except:
                            pass
                
                if cards != "PASS":
                    data["greaterAction"] = [
                        greater_action[0],
                        greater_action[1],
                        convert_cards_list(cards)
                    ]
                else:
                    data["greaterAction"] = greater_action
            else:
                data["greaterAction"] = greater_action
        
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
        
        # 转换publicInfo中的playArea
        if "publicInfo" in data:
            for i, player_info in enumerate(data["publicInfo"]):
                if "playArea" in player_info and player_info["playArea"] is not None:
                    play_area = player_info["playArea"]
                    
                    # 如果是字典格式
                    if isinstance(play_area, dict):
                        # 如果只有actIndex，说明还没有出牌信息，设置为空
                        if "actIndex" in play_area and "type" not in play_area:
                            data["publicInfo"][i]["playArea"] = ["PASS", "", "PASS"]
                        else:
                            # 正常的牌型信息
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
                    
                    # 如果是列表格式，转换牌
                    elif isinstance(play_area, list) and len(play_area) > 2:
                        if play_area[2] != "PASS":
                            data["publicInfo"][i]["playArea"] = [
                                play_area[0],
                                play_area[1],
                                convert_cards_list(play_area[2])
                            ]
        
        return data
    
    async def handle_messages(self):
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    
                    # 转换牌的格式
                    data = self.convert_card_format(data)
                    
                    # 使用lalala的状态解析
                    try:
                        self.state.parse(data)
                    except IndexError as e:
                        print(f"[ERROR] IndexError in state.parse: {e}")
                        print(f"[ERROR] curAction: {data.get('curAction')}")
                        if data.get('curAction') and len(data['curAction']) > 2:
                            print(f"[ERROR] curAction[2] type: {type(data['curAction'][2])}")
                            if isinstance(data['curAction'][2], list) and len(data['curAction'][2]) > 0:
                                print(f"[ERROR] curAction[2][0]: {data['curAction'][2][0]}, type: {type(data['curAction'][2][0])}")
                        print(f"[ERROR] greaterAction: {data.get('greaterAction')}")
                        if data.get('greaterAction') and len(data['greaterAction']) > 2:
                            print(f"[ERROR] greaterAction[2] type: {type(data['greaterAction'][2])}")
                            if isinstance(data['greaterAction'][2], list) and len(data['greaterAction'][2]) > 0:
                                print(f"[ERROR] greaterAction[2][0]: {data['greaterAction'][2][0]}, type: {type(data['greaterAction'][2][0])}")
                        raise
                    
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
            import traceback
            traceback.print_exc()
        finally:
            print(f"[{self.user_info}] 断开连接")


def run_lalala_client(client_name: str):
    """
    运行lalala客户端（使用websockets）
    
    Args:
        client_name: 客户端名称 (client1, client2, client3, client4)
    """
    print(f"[{client_name}] 启动lalala客户端（websockets版本）")
    
    client = LalalaWebsocketsClient(client_name)
    asyncio.run(client.connect())


if __name__ == "__main__":
    # 从命令行参数获取客户端名称
    if len(sys.argv) < 2:
        print("用法: python lalala_adapter.py <client_name>")
        print("示例: python lalala_adapter.py client1")
        sys.exit(1)
    
    client_name = sys.argv[1]
    run_lalala_client(client_name)
