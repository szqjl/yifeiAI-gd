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
    from batch_executor.client_ready import mark_client_ready, mark_game_ready, wait_for_connect_turn
except ImportError:
    def mark_client_ready(_client_id: str) -> None:
        pass

    def mark_game_ready(_client_id: str) -> None:
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
    """使用websockets库的lalala客户端（V8: 支持 OpenGuanDan 新平台）"""
    
    def __init__(self, user_info, platform: str = "v1006",
                 v8_role: str = None, v8_round_count: int = 1):
        self.user_info = user_info
        self.platform = platform
        self.v8_role = v8_role  # "creator" 或 "joiner"（仅 openguandan）
        self.v8_round_count = v8_round_count
        self.websocket = None
        self._game_ready_marked = False
        self.room_id = None
        
        # 使用lalala的State和Action
        self.state = State(user_info)
        self.action = Action(user_info)
        
        # V8: 缓存上一个 actionList 和 stage
        self._last_action_list = []
        self._last_stage = ""
        self._last_tribute_pos = None
        self._last_tribute_card = None
    
    async def _v8_room_handshake(self):
        """V8: CREATE_ROOM 或 JOIN_ROOM 握手"""
        from pathlib import Path as _Path
        room_file = _Path(__file__).resolve().parents[2] / "tmp" / ".v8_room_id"
        
        if self.v8_role == "creator":
            msg = {
                "type": "CREATE_ROOM",
                "data": {
                    "userId": self.user_info,
                    "round": self.v8_round_count,
                    "seatNum": 1,  # lalala3 坐 1 号位
                }
            }
            await self.websocket.send(json.dumps(msg))
            resp = json.loads(await asyncio.wait_for(self.websocket.recv(), timeout=10))
            self.room_id = resp.get("data", {}).get("roomId")
            room_file.parent.mkdir(parents=True, exist_ok=True)
            room_file.write_text(str(self.room_id), encoding="utf-8")
            print(f"[{self.user_info}] CREATE_ROOM → roomId={self.room_id}")
        else:
            import time as _time
            deadline = _time.monotonic() + 30
            while _time.monotonic() < deadline:
                if room_file.exists():
                    self.room_id = int(room_file.read_text(encoding="utf-8").strip())
                    break
                await asyncio.sleep(0.5)
            if not self.room_id:
                raise RuntimeError(f"[{self.user_info}] 等待 roomId 超时")
            msg = {
                "type": "JOIN_ROOM",
                "data": {
                    "userId": self.user_info,
                    "roomId": self.room_id,
                    "seatNum": 1 if "client3" in self.user_info else 3,
                }
            }
            await self.websocket.send(json.dumps(msg))
            await asyncio.wait_for(self.websocket.recv(), timeout=10)
            print(f"[{self.user_info}] JOIN_ROOM → roomId={self.room_id}")
    
    async def connect(self):
        port = "8181" if self.platform == "openguandan" else "23456"
        if self.platform == "openguandan":
            uri = f"ws://127.0.0.1:{port}"
        else:
            uri = f"ws://127.0.0.1:{port}/game/{self.user_info}"
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
            print(f"[{self.user_info}] 连接成功! port={port}")
            
            # V8: 房间握手
            if self.platform == "openguandan":
                await self._v8_room_handshake()
            
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
                    # 首次收到消息时登记 game_ready
                    if not self._game_ready_marked:
                        self._game_ready_marked = True
                        mark_game_ready(self.user_info)
                        print(f"[{self.user_info}] ✓ 首条消息到达，game_ready")
                    data = self._preprocess_message(data)
                    msg_type = data.get("type", "")

                    if msg_type == "notify":
                        await asyncio.to_thread(self._sync_parse_only, data)
                        continue

                    if msg_type != "act":
                        continue

                    # V8: 缓存 actionList/stage
                    al = data.get("actionList", [])
                    self._last_action_list = al
                    stage = data.get("stage", "")
                    self._last_stage = stage
                    if stage == "back":
                        self._last_tribute_pos = data.get("tributePos")
                        self._last_tribute_card = data.get("tribute")

                    try:
                        act_index = await asyncio.to_thread(self._decide_sync, data)
                    except IndexError as e:
                        print(f"[ERROR] IndexError in state.parse: {e}")
                        if data.get("curAction") and len(data["curAction"]) > 2:
                            print(f"[ERROR] curAction[2] type: {type(data['curAction'][2])}")
                        raise

                    if act_index is None:
                        print(f"[{self.user_info}] actionList 缺失，回退 actIndex=0")
                        act_index = 0

                    print(f"[{self.user_info}] 选择动作: {act_index}")
                    
                    # V8: 发送完整 action 三元组
                    if self.platform == "openguandan":
                        act_tuple = al[act_index] if act_index < len(al) else ["PASS", "PASS", ["PASS"]]
                        if stage == "tribute":
                            msg_out = {
                                "type": "TRIBUTE",
                                "data": {"roomId": self.room_id, "player": 1 if "client3" in self.user_info else 3, "act": act_tuple}
                            }
                        elif stage == "back":
                            msg_out = {
                                "type": "PAYTRIBUTE",
                                "data": {
                                    "roomId": self.room_id,
                                    "player": 1 if "client3" in self.user_info else 3,
                                    "tributePos": self._last_tribute_pos or 0,
                                    "tribute": self._last_tribute_card or "",
                                    "act": act_tuple,
                                }
                            }
                        else:
                            msg_out = {
                                "type": "PLAY",
                                "data": {"roomId": self.room_id, "player": 1 if "client3" in self.user_info else 3, "act": act_tuple}
                            }
                        await self.websocket.send(json.dumps(msg_out))
                    else:
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


def run_lalala_client(client_name: str, platform: str = "v1006",
                       v8_role: str = "joiner", v8_round_count: int = 1):
    """
    运行lalala客户端（使用websockets）
    
    Args:
        client_name: 客户端名称 (client1, client2, client3, client4)
        platform: 平台 "v1006" 或 "openguandan"
        v8_role: V8 房间角色
        v8_round_count: 局数
    """
    print(f"[{client_name}] 启动lalala客户端（websockets版本，platform={platform}）")
    
    client = LalalaWebsocketsClient(
        client_name, platform=platform,
        v8_role=v8_role, v8_round_count=v8_round_count,
    )
    asyncio.run(client.connect())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="lalala client (V8)")
    parser.add_argument("client_name", nargs="?", default="client3")
    parser.add_argument("--platform", choices=["v1006", "openguandan"], default="v1006")
    parser.add_argument("--role", choices=["creator", "joiner"], default="joiner")
    parser.add_argument("--games", type=int, default=1)
    args = parser.parse_args()
    
    run_lalala_client(
        args.client_name, platform=args.platform,
        v8_role=args.role, v8_round_count=args.games,
    )
