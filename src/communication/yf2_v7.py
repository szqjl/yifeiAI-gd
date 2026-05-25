# -*- coding: utf-8 -*-
"""
yf2_v7 - YiFei AI V7 Client (Player 2)
Ultimate Win Rate Oriented Version
终极胜率导向版本：使用终极胜率导向训练模型
"""
import asyncio
import json
import sys
import logging
from pathlib import Path
import time

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
from communication.game_recorder import (
    GameRecorder,
    normalize_cards_to_string_list,
    normalize_action_list,
    ensure_my_pos_int,
)
from communication.websocket_manager import WebSocketManager

# Configure logging
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

from datetime import datetime
log_filename = log_dir / f"yf2_v7_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Connection delay to ensure proper position assignment
DELAY_BEFORE_CONNECT = 9  # seconds, longer than yf1 to ensure position order


class YF2_V7_Client:
    """
    YiFei AI V7 Client - Player 2
    Ultimate Win Rate Oriented Version
    """
    
    def __init__(self, player_id=2, use_local_websocket=True):
        self.player_id = player_id
        self.user_info = "yf2_v7"
        self.logger = logging.getLogger(f"yf2_v7")
        
        # Initialize WebSocket manager
        self.ws_manager = WebSocketManager(self.user_info, use_local=use_local_websocket)
        self.websocket = None
        
        # Initialize Ultimate Win Rate Decision Engine V7
        self.logger.info("🎯 Initializing Ultimate Win Rate Engine V7")
        self.decision_engine = UltimateWinRateEngineV7(player_id)
        
        self.hand_cards = []
        
        # Statistics
        self.decision_count = 0
        self.game_count = 0
        
        # Initialize game recorder
        self.game_recorder = GameRecorder(player_id, "yf2_v7")
        
        self.logger.info(f"✓ yf2_v7 initialized (Player {player_id})")
        self.logger.info(f"  - Ultimate Win Rate Engine V7: Loaded")
    
    async def connect(self):
        """Connect to game server"""
        try:
            self.logger.info(f"[yf2_v7] 等待连接延迟 {DELAY_BEFORE_CONNECT} 秒，确保第三个位置...")
            time.sleep(DELAY_BEFORE_CONNECT)
            self.logger.info(f"[yf2_v7] 开始连接 ws://127.0.0.1:23456/game/yf2_v7")
            
            connected = await self.ws_manager.connect()
            if not connected:
                self.logger.error("Failed to connect to server")
                return
            
            self.websocket = self.ws_manager.websocket
            
            print(f"[yf2_v7] 连接成功！期望位置：{self.player_id}号位")
            self.logger.info(f"✓ Connected to server. Expected position: {self.player_id}")
            
            self.ws_manager.set_message_handler(self.process_message)
            await self.ws_manager.handle_messages()
            
        except Exception as e:
            self.logger.error(f"✗ Connection error: {e}", exc_info=True)
    
    async def process_message(self, data: dict):
        """Process a message from the server"""
        message_type = data.get("type", "")
        
        if message_type in ["notify", "act"]:
            import json
            print(f"\n[服务器消息调试] 收到 {message_type} 消息:")
            print(f"完整消息: {json.dumps(data, indent=2, ensure_ascii=False)[:1500]}...")
            print(f"[服务器消息调试] 消息类型: {message_type}")
            if "data" in data:
                print(f"[服务器消息调试] 数据字段: {list(data['data'].keys()) if isinstance(data['data'], dict) else type(data['data'])}")
        
        if message_type == "act":
            await self.handle_action_request(data)
        elif message_type == "notify":
            self.handle_notification(data)
    
    def handle_notification(self, data: dict):
        """Handle notification from server"""
        try:
            # Extract notification data
            notification_data = data.get("data", {})
            
            # Handle different notification types
            if "stage" in notification_data:
                stage = notification_data["stage"]
                if stage == "gameStart":
                    self.handle_game_start(notification_data)
                elif stage == "gameEnd":
                    self.handle_game_end(notification_data)
            
            # Update hand cards if provided
            if "handCards" in notification_data:
                self.hand_cards = normalize_cards_to_string_list(notification_data["handCards"])
                
        except Exception as e:
            self.logger.error(f"✗ Notification handling error: {e}", exc_info=True)
    
    def handle_game_start(self, data: dict):
        """Handle game start notification"""
        try:
            self.game_count += 1
            self.hand_cards = normalize_cards_to_string_list(data.get("handCards", []))
            my_pos = ensure_my_pos_int(data, self.player_id)
            if my_pos != self.player_id:
                self.logger.info(f"Position updated: {self.player_id} -> {my_pos} (server myPos)")
                self.player_id = my_pos
            self.logger.info(
                "[座位排查] 来源=yf2_v7.handle_game_start, 原始myPos=%s, 原始playerPosition=%s, 同步后player_id=%s",
                data.get("myPos"), data.get("playerPosition"), self.player_id
            )

            self.game_recorder.record_game_start(data)
            self.logger.info(f"🎮 游戏开始 #{self.game_count}: 手牌数={len(self.hand_cards)}, 座位={self.player_id}")
            
        except Exception as e:
            self.logger.error(f"✗ Game start handling error: {e}", exc_info=True)
    
    def handle_game_end(self, data: dict):
        """Handle game end notification"""
        try:
            result = data.get("result", {})
            
            # Save game record
            self.game_recorder.end_game(result)
            
            # Print statistics
            stats = self.decision_engine.get_statistics()
            self.logger.info(f"🏁 游戏结束 #{self.game_count}")
            self.logger.info(f"  - 总决策次数: {stats['total_decisions']}")
            self.logger.info(f"  - 模型决策: {stats['model_decisions']}")
            self.logger.info(f"  - 规则回退: {stats['fallback_decisions']}")
            self.logger.info(f"  - 模型使用率: {stats['model_usage_rate']:.1%}")
            
        except Exception as e:
            self.logger.error(f"✗ Game end handling error: {e}", exc_info=True)
    
    async def handle_action_request(self, data: dict):
        """Handle action request from server"""
        self.decision_count += 1
        
        # Extract action data
        action_data = data.get("data", {})
        
        # Check stage
        stage = action_data.get("stage", "")
        if stage == "tribute":
            self._handle_tribute_action(action_data)
        elif stage == "back":
            self._handle_back_action(action_data)
        else:
            # Normal play stage
            self_rank = action_data.get("selfRank", "?")
            oppo_rank = action_data.get("oppoRank", "?")
            cur_rank = action_data.get("curRank", "?")
            
            if self_rank != "?" or oppo_rank != "?" or cur_rank != "?":
                print(f"我方等级：{self_rank}， 对方等级：{oppo_rank}， 当前等级{cur_rank}")
        
        action_list = action_data.get("actionList", [])
        
        if not action_list:
            self.logger.warning("Empty action list, sending 0")
            await self.send_action(0)
            return
        
        try:
            my_pos = ensure_my_pos_int(action_data, self.player_id)
            if my_pos != self.player_id:
                self.logger.info(f"Position updated: {self.player_id} -> {my_pos} (from act myPos)")
                self.player_id = my_pos
            action_data["myPos"] = self.player_id
            self.logger.info(
                "[座位排查] 来源=yf2_v7.handle_action_request, 原始myPos=%s, 原始playerPosition=%s, 同步后player_id=%s",
                action_data.get("myPos"), action_data.get("playerPosition"), self.player_id
            )
            if "handCards" in action_data and action_data["handCards"]:
                action_data["handCards"] = normalize_cards_to_string_list(action_data["handCards"])
            if "actionList" in action_data and action_data["actionList"]:
                action_data["actionList"] = normalize_action_list(action_data["actionList"])
            act_index = self.decision_engine.decide(action_data)
            
            # Record decision
            selected_action = action_list[act_index] if act_index < len(action_list) else []
            self.game_recorder.record_decision(
                act_index, selected_action, 
                context={
                    "myPos": action_data.get("myPos", self.player_id),
                    "curPos": action_data.get("curPos", -1),
                    "greaterPos": action_data.get("greaterPos", -1),
                    "actionList_size": len(action_list),
                    "version": "v7",
                    "engine": "ultimate_win_rate"
                }
            )
            
            # Validate action index
            if not self.validate_action(act_index, action_list):
                self.logger.error(f"Invalid action index: {act_index}, using 0")
                act_index = 0
            
            await self.send_action(act_index)
            
        except Exception as e:
            self.logger.error(f"✗ Decision error: {e}", exc_info=True)
            await self.send_action(0)
    
    def _handle_tribute_action(self, data: dict):
        """Handle tribute action"""
        self_rank = data.get("selfRank", "?")
        oppo_rank = data.get("oppoRank", "?")
        cur_rank = data.get("curRank", "?")
        print(f"我方等级：{self_rank}， 对方等级：{oppo_rank}， 当前等级{cur_rank}")
        
        action_list = data.get("actionList", {})
        if "tribute" in action_list:
            tribute_cards = action_list["tribute"]
            print("轮到自己进贡，可以进贡的牌有:")
            print(tribute_cards)
    
    def _handle_back_action(self, data: dict):
        """Handle back action"""
        self_rank = data.get("selfRank", "?")
        oppo_rank = data.get("oppoRank", "?")
        cur_rank = data.get("curRank", "?")
        print(f"我方等级：{self_rank}， 对方等级：{oppo_rank}， 当前等级{cur_rank}")
        
        action_list = data.get("actionList", {})
        if "back" in action_list:
            back_cards = action_list["back"]
            print("轮到自己还贡，可以还贡的牌有:")
            print(back_cards)
    
    def validate_action(self, action_index: int, action_list: list) -> bool:
        """Validate action index"""
        return 0 <= action_index < len(action_list)
    
    async def send_action(self, action_index: int):
        """Send action to server"""
        try:
            message = {
                "type": "action",
                "data": {
                    "actIndex": action_index
                }
            }
            
            await self.ws_manager.send_json(message)
            self.logger.debug(f"发送动作: {action_index}")
            
        except Exception as e:
            self.logger.error(f"✗ Send action error: {e}", exc_info=True)


async def main():
    """Main function"""
    client = YF2_V7_Client()
    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())