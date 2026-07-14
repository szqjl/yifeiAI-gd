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

# Windows: 双 LALALA 进程同时启动会产生 .pyc 文件写入竞争，关掉字节码缓存 + 加重试
import time as _import_time
sys.dont_write_bytecode = True

_lalala_imported = False
_last_import_error = None
for _import_attempt in range(5):
    try:
        from state import State
        from action import Action
        _lalala_imported = True
        break
    except Exception as e:
        _last_import_error = e
        print(f"[lalala_adapter] 导入重试 {_import_attempt + 1}/5: {e}", flush=True)
        _import_time.sleep(1.0 + _import_attempt * 0.5)

if _lalala_imported:
    print("✓ 成功导入lalala核心模块", flush=True)
else:
    print(f"✗ 导入lalala模块失败: {_last_import_error}", flush=True)
    print(f"请确保 {LALALA_PATH} 存在且包含state.py和action.py", flush=True)
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
            print(f"[{self.user_info}] CREATE_ROOM → roomId={self.room_id}", flush=True)
        else:
            print(f"[{self.user_info}] joiner: 等待 roomId 文件...", flush=True)
            import time as _time
            deadline = _time.monotonic() + 30
            while _time.monotonic() < deadline:
                if room_file.exists():
                    self.room_id = int(room_file.read_text(encoding="utf-8").strip())
                    print(f"[{self.user_info}] 读到 roomId={self.room_id}", flush=True)
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
            print(f"[{self.user_info}] 发送 JOIN_ROOM: {json.dumps(msg, ensure_ascii=False)}", flush=True)
            await self.websocket.send(json.dumps(msg))
            resp = json.loads(await asyncio.wait_for(self.websocket.recv(), timeout=10))
            print(f"[{self.user_info}] JOIN_ROOM 响应: {json.dumps(resp, ensure_ascii=False)}", flush=True)
            print(f"[{self.user_info}] JOIN_ROOM → roomId={self.room_id}", flush=True)
    
    async def connect(self):
        port = "8181" if self.platform == "openguandan" else "23456"
        if self.platform == "openguandan":
            uri = f"ws://127.0.0.1:{port}"
        else:
            uri = f"ws://127.0.0.1:{port}/game/{self.user_info}"
        print(f"[{self.user_info}] 连接门闩开始，等待前序席位...", flush=True)
        try:
            gate_ok = await asyncio.to_thread(
                wait_for_connect_turn,
                self.user_info,
                timeout=120.0,
            )
            if not gate_ok:
                print(f"[{self.user_info}] 前序席位未就绪，放弃连接", flush=True)
                return

            print(f"[{self.user_info}] 门闩通过，开始 WebSocket 连接 {uri}...", flush=True)
            self.websocket = await websockets.connect(
                uri,
                ping_interval=None,
                ping_timeout=None,
            )
            mark_client_ready(self.user_info)
            print(f"[{self.user_info}] 连接成功! port={port}", flush=True)
            
            # V8: 房间握手
            if self.platform == "openguandan":
                await self._v8_room_handshake()
            
            await self.handle_messages()
        except Exception as e:
            print(f"[{self.user_info}] 连接错误: {type(e).__name__}: {e}", flush=True)
            import traceback as _tb2
            _tb2.print_exc()
            sys.stdout.flush()
            sys.stderr.flush()
    
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
        
        # V8: 新服务器 publicInfo 不含 playArea 字段，补上 None 避免 LALALA KeyError
        if "publicInfo" in data:
            for i, player_info in enumerate(data["publicInfo"]):
                if "playArea" not in player_info:
                    data["publicInfo"][i]["playArea"] = None
                if player_info["playArea"] is not None:
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
        # V8: OpenGuanDan 消息为 {"type":"act","data":{...}} 嵌套格式；
        #     LALALA state.parse() 期望所有字段在顶层，展开 data 到外层
        nested = data.get("data")
        if isinstance(nested, dict):
            for k, v in nested.items():
                if k != "type":  # 避免覆盖外层 type（act/notify）
                    data[k] = v

        for field in ("curAction", "greaterAction", "handCards"):
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = ast.literal_eval(data[field])
                except (ValueError, SyntaxError):
                    pass

        # V8: 新服务器 gameResult 格式兼容
        # ① victory (int 0/1) → victoryNum (list)，补 draws
        # ② victoryNum 已有但 draws 缺失（V8 服务端直发 victoryNum 不带 draws）
        if data.get("stage") == "gameResult":
            if "victory" in data and "victoryNum" not in data:
                vic = data["victory"]  # 0=team0(座0+2)胜, 1=team1(座1+3)胜
                data["victoryNum"] = [1, 0, 1, 0] if vic == 0 else [0, 1, 0, 1]
            if "draws" not in data:
                data["draws"] = [0, 0, 0, 0]

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
                        print(f"[{self.user_info}] ✓ 首条消息到达，game_ready", flush=True)
                    
                    # V8: 在 _preprocess_message 之前提取原始 actionList
                    #     （convert_card_format 会把 "SB"→["S","B"]，发给服务器的 PLAY 必须用原始格式）
                    #     同时兼容嵌套 {"type":"act","data":{"actionList":[...]}} 和扁平格式
                    _raw_nested = data.get("data")
                    if isinstance(_raw_nested, dict) and "actionList" in _raw_nested:
                        _orig_action_list = [list(a) if isinstance(a, list) else a for a in _raw_nested["actionList"]]
                    elif "actionList" in data:
                        _orig_action_list = [list(a) if isinstance(a, list) else a for a in data["actionList"]]
                    else:
                        _orig_action_list = []
                    
                    data = self._preprocess_message(data)
                    msg_type = data.get("type", "")

                    if msg_type == "notify":
                        stage = data.get("stage", "")
                        await asyncio.to_thread(self._sync_parse_only, data)
                        if stage == "beginning":
                            hand_size = len(data.get("handCards", []))
                            print(f"[{self.user_info}] 游戏开始，手牌={hand_size}张", flush=True)
                        elif stage == "play":
                            cur_pos = data.get("curPos", "?")
                            cur_act = data.get("curAction", [])
                            act_type = cur_act[0] if isinstance(cur_act, list) and cur_act else "?"
                            print(f"[{self.user_info}] 观战: {cur_pos}号位出 {act_type}", flush=True)
                        # epiodeOver/gameOver 等不打印，留到 act 消息再打印
                        continue

                    if msg_type != "act":
                        continue

                    # V8: 缓存 actionList/stage（用原始格式，不是 convert_card_format 后的）
                    al = _orig_action_list or data.get("actionList", [])
                    self._last_action_list = al
                    stage = data.get("stage", "")
                    self._last_stage = stage
                    if stage == "back":
                        self._last_tribute_pos = data.get("tributePos")
                        self._last_tribute_card = data.get("tribute")

                    try:
                        act_index = await asyncio.to_thread(self._decide_sync, data)
                    except Exception as e:
                        print(f"[{self.user_info}] _decide_sync 异常: {type(e).__name__}: {e}", flush=True)
                        act_index = None

                    if act_index is None:
                        print(f"[{self.user_info}] actionList 缺失或解析异常，回退 actIndex=0 (PASS)", flush=True)
                        act_index = 0

                    print(f"[{self.user_info}] 选择动作: {act_index}", flush=True)
                    
                    # V8: 发送完整 action 三元组
                    if self.platform == "openguandan":
                        act_tuple = al[act_index] if act_index < len(al) else ["PASS", "PASS", ["PASS"]]
                        # 诊断：打印卡牌格式（应为 "SB" 字符串，非 ["S","B"] 列表）
                        _cards = act_tuple[2] if len(act_tuple) > 2 and act_tuple[2] != "PASS" else None
                        if _cards:
                            print(f"[{self.user_info}] [V8 OUT] act={act_tuple[0]}/{act_tuple[1]} cards={_cards[:3]}", flush=True)
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
                    print(f"[{self.user_info}] 无效的JSON", flush=True)
                except Exception as e:
                    print(f"[{self.user_info}] 消息处理错误: {type(e).__name__}: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                    sys.stdout.flush()
                    
        except websockets.ConnectionClosed as e:
            print(f"[{self.user_info}] 连接关闭: {e}", flush=True)
        except Exception as e:
            print(f"[{self.user_info}] 连接错误: {type(e).__name__}: {e}", flush=True)
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
        finally:
            print(f"[{self.user_info}] 断开连接", flush=True)


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
    print(f"[{client_name}] 启动lalala客户端（websockets版本，platform={platform}）", flush=True)
    
    client = LalalaWebsocketsClient(
        client_name, platform=platform,
        v8_role=v8_role, v8_round_count=v8_round_count,
    )
    print(f"[{client_name}] LalalaWebsocketsClient 创建完毕，准备 asyncio.run(connect)...", flush=True)
    sys.stdout.flush()
    
    try:
        asyncio.run(client.connect())
    except KeyboardInterrupt:
        print(f"[{client_name}] 用户中断", flush=True)
    except Exception as e:
        print(f"\n{'='*60}", flush=True)
        print(f"[{client_name}] 致命异常: {type(e).__name__}: {e}", flush=True)
        import traceback as _tb
        _tb.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        # 记入日志文件
        _log_dir = Path(__file__).resolve().parents[2] / "logs"
        _log_dir.mkdir(exist_ok=True)
        _err_log = _log_dir / f"lalala_{client_name}_error.log"
        _err_log.write_text(
            f"{type(e).__name__}: {e}\n{_tb.format_exc()}",
            encoding="utf-8",
        )
        _import_time.sleep(10)  # 保持窗口打开 10 秒，方便查看错误
    finally:
        print(f"[{client_name}] 进程退出", flush=True)


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
