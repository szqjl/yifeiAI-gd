# -*- coding: utf-8 -*-
"""
yf2_v4 - YiFei AI V4 Client (Player 2)
Uses HybridDecisionEngineV4 with 4-layer fallback protection

.. deprecated:: 2026-05-29
    V4 客户端已归档，不再作为日常入口。M 主迭代请用 ``yf1_m1.py`` / ``yf2_m1.py``（``m-dev``）；
    V-learn 实验请用 ``yf1_v5.py`` / ``yf2_v5.py``。本文件仅保留供历史 replay 与对照实验。
"""
import warnings

warnings.warn(
    "yf2_v4.py is deprecated (archived V-learn). Use yf2_m1.py for M×lalala or yf2_v5.py for V-learn.",
    DeprecationWarning,
    stacklevel=1,
)

import asyncio
import websockets
import json
import sys
import logging
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))

from v.learn import HybridDecisionEngineV4
from communication.game_recorder import (
    GameRecorder,
    normalize_cards_to_string_list,
    normalize_action_list,
    ensure_my_pos_int,
)

# Configure logging
import os
from datetime import datetime

# 创建日志目录
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# 日志文件名：yf2_v4_YYYYMMDD_HHMMSS.log
log_filename = log_dir / f"yf2_v4_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# 配置日志：同时输出到控制台和文件
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),  # 文件输出
        logging.StreamHandler()  # 控制台输出
    ]
)


class YF2_V4_Client:
    """
    YiFei AI V4 Client - Player 2
    Uses HybridDecisionEngineV4 for robust decision making
    """
    
    def __init__(self, player_id=2):
        self.player_id = player_id
        self.user_info = "yf2_v4"
        self.websocket = None
        self.logger = logging.getLogger(f"yf2_v4")
        
        # Initialize HybridDecisionEngineV4
        config = {
            "enable_lalala": True,
            "enable_fallback": True,
            "log_level": "INFO",
            "performance_threshold": 1.0
        }
        self.decision_engine = HybridDecisionEngineV4(player_id, config)
        
        # Statistics
        self.decision_count = 0
        self.game_count = 0
        
        # Initialize game recorder
        self.game_recorder = GameRecorder(player_id, "yf2_v4")
        
        self.logger.info(f"✓ yf2_v4 initialized (Player {player_id})")
    
    async def connect(self):
        """Connect to game server"""
        uri = f"ws://127.0.0.1:23456/game/{self.user_info}"
        try:
            self.websocket = await websockets.connect(
                uri,
                ping_timeout=None,  # Disable ping timeout
                close_timeout=10
            )
            self.logger.info(f"✓ Connected to server: {uri}")
            await self.handle_messages()
        except Exception as e:
            self.logger.error(f"✗ Connection error: {e}")
    
    async def handle_messages(self):
        """Handle incoming messages from server"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.process_message(data)
                
                except json.JSONDecodeError as e:
                    self.logger.error(f"✗ Invalid JSON: {e}")
                except Exception as e:
                    self.logger.error(f"✗ Message processing error: {e}", exc_info=True)
        
        except websockets.ConnectionClosed as e:
            self.logger.info(f"Connection closed: {e}")
        except Exception as e:
            self.logger.error(f"✗ Connection error: {e}", exc_info=True)
        finally:
            self.logger.info("Disconnected from server")
    
    async def process_message(self, data: dict):
        """Process a message from the server"""
        message_type = data.get("type", "")
        
        if message_type == "act":
            await self.handle_action_request(data)
        
        elif message_type == "notify":
            self.handle_notification(data)
    
    async def handle_action_request(self, data: dict):
        """Handle action request from server"""
        self.decision_count += 1
        action_list = data.get("actionList", [])
        
        if not action_list:
            self.logger.warning("Empty action list, sending 0")
            await self.send_action(0)
            return
        
        try:
            if "handCards" in data and data["handCards"]:
                data["handCards"] = normalize_cards_to_string_list(data["handCards"])
            if "actionList" in data and data["actionList"]:
                data["actionList"] = normalize_action_list(data["actionList"])
            data["myPos"] = self.player_id
            act_index = self.decision_engine.decide(data)
            
            # Get decision details for recording
            decision_context = {
                "myPos": data.get("myPos", self.player_id),
                "curPos": data.get("curPos", -1),
                "greaterPos": data.get("greaterPos", -1),
                "actionList_size": len(action_list)
            }
            
            # Record decision (简化版，实际可以从decision_engine获取更多信息)
            selected_action = action_list[act_index] if act_index < len(action_list) else []
            self.game_recorder.record_decision(act_index, selected_action, context=decision_context)
            
            # Validate action index
            if not self.validate_action(act_index, action_list):
                self.logger.error(f"Invalid action index: {act_index}, using 0")
                act_index = 0
            
            await self.send_action(act_index)
        
        except Exception as e:
            self.logger.error(f"✗ Decision error: {e}", exc_info=True)
            # Emergency fallback: send PASS (0)
            await self.send_action(0)
    
    def handle_notification(self, data: dict):
        """Handle notification from server"""
        stage = data.get("stage", "")
        
        if stage == "beginning":
            hand_cards = normalize_cards_to_string_list(data.get("handCards", []))
            self.hand_cards = hand_cards
            my_pos = ensure_my_pos_int(data, self.player_id)
            if my_pos != self.player_id:
                self.logger.info(f"Position updated: {self.player_id} -> {my_pos} (server myPos)")
                self.player_id = my_pos
            self.logger.info(
                "[座位排查] 来源=yf2_v4.beginning, 原始myPos=%s, 原始playerPosition=%s, 同步后player_id=%s",
                data.get("myPos"), data.get("playerPosition"), self.player_id
            )

            # 打印手牌信息
            print(f"游戏开始, 我是{my_pos}号位，手牌：{hand_cards}")
            self.logger.info(f"游戏开始, 我是{my_pos}号位，手牌：{hand_cards}")
            
            # 打印等级信息（用于调试）
            self_rank = data.get("selfRank", "?")
            oppo_rank = data.get("oppoRank", "?")
            cur_rank = data.get("curRank", "?")
            print(f"我方等级：{self_rank}， 对方等级：{oppo_rank}， 当前等级{cur_rank}")
            
            # 尝试获取所有玩家的手牌信息
            all_players_hands = {}
            all_players_hands[my_pos] = hand_cards  # 自己的手牌
            
            # 从publicInfo中获取其他玩家的剩余牌数（如果有）
            public_info = data.get("publicInfo", [])
            if public_info:
                for i, player_info in enumerate(public_info):
                    if isinstance(player_info, dict) and "rest" in player_info:
                        # publicInfo中只有剩余牌数，没有完整手牌
                        # 但我们可以记录剩余牌数信息
                        pass
            
            # 从restCards中获取其他玩家的手牌（如果有）
            rest_cards = data.get("restCards", [])
            if rest_cards:
                for rest_info in rest_cards:
                    if isinstance(rest_info, list) and len(rest_info) >= 2:
                        pos = rest_info[0]
                        # 确保pos是整数
                        if isinstance(pos, str):
                            try:
                                pos = int(pos)
                            except:
                                continue
                        cards = rest_info[1]
                        # 转换手牌格式：如果是列表格式 [['S', '3'], ...]，转换为字符串格式
                        if cards and isinstance(cards, list) and len(cards) > 0:
                            cards = normalize_cards_to_string_list(cards)
                        if pos != my_pos:
                            all_players_hands[pos] = cards
                            self.logger.info(f"记录{pos}号位手牌: {len(cards)}张")
            
            # 确保my_pos也是整数键
            if isinstance(my_pos, str):
                try:
                    my_pos = int(my_pos)
                except:
                    pass
            # 如果my_pos是字符串键，转换为整数键
            if my_pos in all_players_hands and isinstance(my_pos, str):
                all_players_hands[int(my_pos)] = all_players_hands.pop(my_pos)
            elif not isinstance(my_pos, str):
                all_players_hands[my_pos] = hand_cards
            
            # 记录所有玩家的手牌信息（用于调试）
            if len(all_players_hands) > 1:
                self.logger.info(f"已记录{len(all_players_hands)}个玩家的手牌: {list(all_players_hands.keys())}")
            
            # 开始记录游戏
            game_info = {
                "selfRank": data.get("selfRank"),
                "oppoRank": data.get("oppoRank"),
                "curRank": data.get("curRank")
            }
            self.game_recorder.start_game(hand_cards, my_pos, game_info, all_players_hands)
        
        elif stage == "play":
            # 记录每个玩家的出牌信息（用于回放）
            cur_pos = data.get("curPos", -1)
            cur_action = data.get("curAction", [])
            greater_pos = data.get("greaterPos", -1)
            greater_action = data.get("greaterAction", [])
            
            # 如果是第一个play消息，尝试从restCards中获取所有玩家的手牌
            if not hasattr(self, '_first_play_processed'):
                rest_cards = data.get("restCards", [])
                if rest_cards and self.game_recorder:
                    # 获取当前的all_players_hands
                    current_hands = getattr(self.game_recorder, 'all_players_hands', {})
                    for rest_info in rest_cards:
                        if isinstance(rest_info, list) and len(rest_info) >= 2:
                            pos = rest_info[0]
                            # 确保pos是整数
                            if isinstance(pos, str):
                                try:
                                    pos = int(pos)
                                except:
                                    continue
                            cards = rest_info[1]
                            if cards and isinstance(cards, list) and len(cards) > 0:
                                cards = normalize_cards_to_string_list(cards)
                            if pos not in current_hands:
                                current_hands[pos] = cards
                                self.logger.info(f"从第一个play消息中记录{pos}号位手牌: {len(cards)}张")
                    # 更新game_recorder的all_players_hands
                    if hasattr(self.game_recorder, 'all_players_hands'):
                        self.game_recorder.all_players_hands.update(current_hands)
                self._first_play_processed = True
            
            # 格式化出牌信息
            if cur_action and len(cur_action) > 0 and cur_action[0] != "PASS":
                action_str = f"{cur_pos}号位打出{cur_action}"
                greater_str = f"最大动作为{greater_pos}号位打出的{greater_action}" if greater_action else ""
                self.logger.info(f"{action_str}， {greater_str}")
            
            # 记录到游戏记录器
            context = {
                "publicInfo": data.get("publicInfo", []),
                "selfRank": data.get("selfRank"),
                "oppoRank": data.get("oppoRank"),
                "curRank": data.get("curRank"),
                "restCards": data.get("restCards", [])  # 添加restCards到context
            }
            self.game_recorder.record_action(cur_pos, cur_action, greater_pos, greater_action, context)
        
        elif stage == "gameResult":
            self.game_count += 1
            victory_num = data.get("victoryNum", [])
            draws = data.get("draws", [])
            
            result = {
                "victoryNum": victory_num,
                "draws": draws,
                "total_decisions": self.decision_count,
                "game_count": self.game_count
            }
            
            self.logger.info("=" * 60)
            self.logger.info("GAME RESULT")
            self.logger.info("=" * 60)
            self.logger.info(f"Victory counts: {victory_num}")
            self.logger.info(f"Total decisions this game: {self.decision_count}")
            self.logger.info(f"Total games played: {self.game_count}")
            
            # Get statistics from decision engine
            stats = self.decision_engine.get_statistics()
            self.logger.info(f"Layer usage statistics:")
            for layer, layer_data in stats["layer_usage"].items():
                success = layer_data["success"]
                failure = layer_data["failure"]
                total = success + failure
                if total > 0:
                    rate = success / total * 100
                    self.logger.info(f"  {layer}: {success}/{total} ({rate:.1f}%)")
            
            self.logger.info("=" * 60)
            
            # 保存游戏记录
            result["layer_stats"] = stats["layer_usage"]
            self.game_recorder.end_game(result)
            
            # Reset for next game
            self.decision_count = 0
            self.decision_engine.reset_statistics()
    
    def validate_action(self, act_index: int, action_list: list) -> bool:
        """Validate that action index is in valid range"""
        return 0 <= act_index < len(action_list)
    
    async def send_action(self, act_index: int):
        """Send action to server"""
        response = json.dumps({"actIndex": act_index})
        await self.websocket.send(response)
        self.logger.debug(f"Sent action: {act_index}")


async def main():
    """Main entry point"""
    client = YF2_V4_Client(player_id=2)
    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main())

