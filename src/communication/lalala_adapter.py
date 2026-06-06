"""
适配器：将lalala的决策逻辑移植到websockets客户端
"""
import asyncio
import websockets
import json
import ast
import sys
from pathlib import Path

# 设置控制台编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.utils.v7_paths import get_lalala_dir

try:
    from batch_executor.client_ready import mark_client_ready, wait_for_connect_turn
except ImportError:
    def mark_client_ready(_client_id: str) -> None:
        pass

    def wait_for_connect_turn(_client_id: str, *, timeout: float = 120.0, poll_interval: float = 0.5) -> bool:
        return True

LALALA_PATH = get_lalala_dir()
print(f"[lalala_adapter] LALALA_PATH={LALALA_PATH}", flush=True)
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
        
        # 处理curAction和greaterAction，确保它们不是None
        if "curAction" in data:
            if data["curAction"] is None:
                data["curAction"] = ["PASS", "PASS", "PASS"]
            elif isinstance(data["curAction"], list):
                # 检查是否有None值
                if len(data["curAction"]) < 3 or any(x is None for x in data["curAction"]):
                    data["curAction"] = ["PASS", "PASS", "PASS"]
                elif len(data["curAction"]) > 2 and data["curAction"][2] != "PASS":
                    data["curAction"] = [
                        data["curAction"][0],
                        data["curAction"][1],
                        convert_cards_list(data["curAction"][2])
                    ]
            else:
                data["curAction"] = ["PASS", "PASS", "PASS"]
        
        if "greaterAction" in data:
            if data["greaterAction"] is None:
                data["greaterAction"] = ["PASS", "PASS", "PASS"]
            elif isinstance(data["greaterAction"], list):
                # 检查是否有None值
                if len(data["greaterAction"]) < 3 or any(x is None for x in data["greaterAction"]):
                    data["greaterAction"] = ["PASS", "PASS", "PASS"]
                elif len(data["greaterAction"]) > 2 and data["greaterAction"][2] != "PASS":
                    data["greaterAction"] = [
                        data["greaterAction"][0],
                        data["greaterAction"][1],
                        convert_cards_list(data["greaterAction"][2])
                    ]
            else:
                data["greaterAction"] = ["PASS", "PASS", "PASS"]
        
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

    def _preprocess_message(self, data: dict) -> dict:
        for field in ("curAction", "greaterAction", "handCards"):
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = ast.literal_eval(data[field])
                except (ValueError, SyntaxError):
                    pass
        return self.convert_card_format(data)

    def _sync_parse_only(self, data: dict) -> None:
        """仅更新 state（notify），不做决策。"""
        self.state.parse(data)

    def _decide_sync(self, data: dict):
        """同步决策（在线程池运行，避免阻塞 asyncio 导致 ping 超时）。"""
        self.state.parse(data)
        if "actionList" not in data:
            return None
        return self.action.rule_parse(
            data,
            self.state._myPos,
            self.state.remain_cards,
            self.state.history,
            self.state.remain_cards_classbynum,
            self.state.pass_num,
            self.state.my_pass_num,
            self.state.tribute_result,
        )
    
    async def handle_messages(self):
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    data = self._preprocess_message(data)
                    msg_type = data.get("type", "")

                    if msg_type == "notify":
                        await asyncio.to_thread(self._sync_parse_only, data)
                        continue

                    if msg_type != "act":
                        continue

                    try:
                        act_index = await asyncio.to_thread(self._decide_sync, data)
                    except IndexError as e:
                        print(f"[ERROR] IndexError in state.parse: {e}")
                        print(f"[ERROR] curAction: {data.get('curAction')}")
                        if data.get("curAction") and len(data["curAction"]) > 2:
                            print(f"[ERROR] curAction[2] type: {type(data['curAction'][2])}")
                        print(f"[ERROR] greaterAction: {data.get('greaterAction')}")
                        raise

                    if act_index is None:
                        print(f"[{self.user_info}] actionList 缺失，回退 actIndex=0")
                        act_index = 0

                    print(f"[{self.user_info}] 选择动作: {act_index}")
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
