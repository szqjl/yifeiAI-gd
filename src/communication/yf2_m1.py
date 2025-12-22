# -*- coding: utf-8 -*-
"""
yf2_m1 - YiFei AI M1 Client (Player 2)
M1版本：全新的硬编码规则引擎，从新开始

特性：
- 基于阶段一架构重构的硬编码规则引擎
- 5阶段细分路由（开局、中局前期、中局后期、残局前期、残局后期）
- 主动/被动出牌分离
- 完全独立于V5版本
- M系列：硬编码规则引擎系列（与V系列区分）
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

from decision.rule_based_decision_engine_m1 import RuleBasedDecisionEngineM1
from communication.game_recorder import GameRecorder
from communication.websocket_manager import WebSocketManager

# Configure logging
import os
from datetime import datetime

# 创建日志目录
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# 日志文件名：yf2_m1_YYYYMMDD_HHMMSS.log
log_filename = log_dir / f"yf2_m1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

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

# 连接延迟
DELAY_BEFORE_CONNECT = 9  # seconds, longer than yf1 to ensure position order


class YF2_M1_Client:
    """
    YiFei AI M1 Client - Player 2
    M1版本：全新的硬编码规则引擎
    
    特性：
    - 基于阶段一架构重构
    - 5阶段细分路由
    - 专注硬编码规则优化
    - 完全独立于V5版本
    - M系列：硬编码规则引擎系列（与V系列区分）
    """
    
    def __init__(self, player_id=2, use_local_websocket=True):
        self.player_id = player_id
        self.user_info = "yf2_m1"
        self.logger = logging.getLogger(f"yf2_m1")
        
        # 初始化 WebSocket 管理器
        self.ws_manager = WebSocketManager(self.user_info, use_local=use_local_websocket)
        self.websocket = None  # 保持向后兼容
        
        # Initialize RuleBasedDecisionEngineM1 (M1硬编码决策引擎)
        self.logger.info("🎯 Initializing RuleBasedDecisionEngineM1")
        config = {
            "max_decision_time": 0.8,  # 最大决策时间（秒）
            "enable_logging": True,     # 启用日志
        }
        self.decision_engine = RuleBasedDecisionEngineM1(player_id, config)
        
        self.hand_cards = []  # Track current hand
        
        # Statistics
        self.decision_count = 0
        self.game_count = 0
        
        # Initialize game recorder
        self.game_recorder = GameRecorder(player_id, "yf2_m1")
        
        self.logger.info(f"✓ yf2_m1 initialized (Player {player_id})")
        self.logger.info(f"  - Decision Engine: RuleBasedDecisionEngineM1")
        self.logger.info(f"  - Version: M1 (Hardcoded Rules)")
        self.logger.info(f"  - Series: M (Hardcoded Rules Engine)")
        self.logger.info(f"  - Architecture: Stage Router with 5 Phases")
    
    async def connect(self):
        """Connect to game server using configured WebSocket manager"""
        try:
            # 使用 WebSocket 管理器连接
            self.logger.info(f"[yf2_m1] 等待连接延迟 {DELAY_BEFORE_CONNECT} 秒，确保第三个位置...")
            time.sleep(DELAY_BEFORE_CONNECT)
            self.logger.info(f"[yf2_m1] 开始连接 ws://127.0.0.1:23456/game/yf2_m1")
            connected = await self.ws_manager.connect()
            if not connected:
                self.logger.error("Failed to connect to server")
                return
            
            # 设置 websocket 引用以保持向后兼容
            self.websocket = self.ws_manager.websocket
            
            # 显示连接成功和期望位置信息
            print(f"[yf2_m1] 连接成功！期望位置：{self.player_id}号位（实际位置将在游戏开始时由服务器分配）")
            self.logger.info(f"✓ Connected to server. Expected position: {self.player_id} (actual position will be assigned by server at game start)")
            
            # 设置消息处理回调
            self.ws_manager.set_message_handler(self.process_message)
            
            # 开始处理消息
            await self.ws_manager.handle_messages()
        except Exception as e:
            self.logger.error(f"✗ Connection error: {e}", exc_info=True)
    
    async def handle_messages(self):
        """Handle incoming messages from server (deprecated, use ws_manager.handle_messages)"""
        await self.ws_manager.handle_messages(self.process_message)
    
    async def process_message(self, data: dict):
        """Process a message from the server"""
        message_type = data.get("type", "")
        
        if message_type == "act":
            await self.handle_action_request(data)
        elif message_type == "notify":
            self.handle_notification(data)
    
    def _handle_tribute_notification(self, data: dict):
        """处理贡牌通知"""
        result = data.get("result", [])
        if result:
            for tribute_result in result:
                if len(tribute_result) >= 3:
                    tribute_pos, receive_tribute_pos, card = tribute_result
                    print(f"{tribute_pos}号位进贡给{receive_tribute_pos}号位牌{card}")
    
    def _handle_back_notification(self, data: dict):
        """处理还牌通知"""
        result = data.get("result", [])
        if result:
            for back_result in result:
                if len(back_result) >= 3:
                    back_pos, receive_back_pos, card = back_result
                    print(f"{back_pos}号位还贡给{receive_back_pos}号位牌{card}")
    
    def _handle_tribute_action(self, data: dict):
        """处理轮到自己进贡"""
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
        """处理轮到自己还贡"""
        self_rank = data.get("selfRank", "?")
        oppo_rank = data.get("oppoRank", "?")
        cur_rank = data.get("curRank", "?")
        print(f"我方等级：{self_rank}， 对方等级：{oppo_rank}， 当前等级{cur_rank}")
        
        action_list = data.get("actionList", {})
        if "back" in action_list:
            back_cards = action_list["back"]
            print("轮到自己还贡，可以还贡的牌有:")
            print(back_cards)
    
    async def handle_action_request(self, data: dict):
        """Handle action request from server (M1硬编码决策)"""
        self.decision_count += 1
        
        # 检查是否是贡牌或还牌阶段
        stage = data.get("stage", "")
        if stage == "tribute":
            self._handle_tribute_action(data)
        elif stage == "back":
            self._handle_back_action(data)
        else:
            # 普通play阶段，显示等级信息
            self_rank = data.get("selfRank", "?")
            oppo_rank = data.get("oppoRank", "?")
            cur_rank = data.get("curRank", "?")
            
            if self_rank != "?" or oppo_rank != "?" or cur_rank != "?":
                print(f"我方等级：{self_rank}， 对方等级：{oppo_rank}， 当前等级{cur_rank}")
        
        action_list = data.get("actionList", [])
        
        # 调试：打印actionList信息
        if action_list:
            self.logger.info(f"actionList size: {len(action_list)}, first 3: {action_list[:3]}")
            # 统计actionList中的动作类型
            action_types = {}
            for action in action_list[:10]:
                if isinstance(action, list) and len(action) > 0:
                    action_type = action[0]
                    action_types[action_type] = action_types.get(action_type, 0) + 1
            self.logger.info(f"Action types in first 10: {action_types}")
        
        if not action_list:
            self.logger.warning("Empty action list, sending 0")
            await self.send_action(0)
            return
        
        try:
            # 显示当前游戏状态信息（类似lalala客户端）
            cur_pos = data.get("curPos", -1)
            cur_action = data.get("curAction", [])
            greater_pos = data.get("greaterPos", -1)
            greater_action = data.get("greaterAction", [])
            public_info = data.get("publicInfo", [])
            
            # 计算下家剩余牌数
            my_pos = data.get("myPos", self.player_id)
            lower_hand_pos = (my_pos + 1) % 4
            lower_hand_rest = 27
            if public_info and len(public_info) > lower_hand_pos:
                lower_hand_rest = public_info[lower_hand_pos].get("rest", 27)
            
            # 显示当前动作和最大动作
            print(f"当前动作为{cur_pos}号-动作{cur_action}， 最大动作为{greater_pos}号-动作{greater_action}")
            print(f"下家还有{lower_hand_rest}张牌")
            
            # 显示可用动作数量（调试用）
            valid_action_count = sum(1 for a in action_list if len(a) > 0 and a[0] != "PASS")
            print(f"可用动作数: {valid_action_count}/{len(action_list)}")
            if valid_action_count > 0:
                # 显示前几个有效动作的类型
                valid_types = [a[0] for a in action_list[:10] if len(a) > 0 and a[0] != "PASS"]
                print(f"有效动作类型: {valid_types[:5]}")
            
            # M1硬编码决策：直接使用RuleBasedDecisionEngineM1
            act_index = self.decision_engine.decide(data)
            self.logger.info(f"Decision engine returned action index: {act_index}, action: {action_list[act_index] if act_index < len(action_list) else 'INVALID'}")
            
            # 获取阶段信息（用于日志）
            phase_info = self.decision_engine.get_phase_info(data)
            self.logger.info(f"Phase: {phase_info['game_phase']}, Handler: {phase_info['handler_key']}, 剩余牌数: {phase_info['my_remain']}")
            
            # 显示选择的动作（类似lalala客户端）
            selected_action = action_list[act_index] if act_index < len(action_list) else []
            print(f"[yf2_m1] 选择动作: {act_index}")
            if selected_action:
                print(f"  动作类型: {selected_action[0] if len(selected_action) > 0 else 'PASS'}")
                if len(selected_action) > 1:
                    print(f"  动作牌点: {selected_action[1]}")
            else:
                print(f"  警告: 选择的动作索引 {act_index} 无效或为空")
            
            # Get decision details for recording
            decision_context = {
                "myPos": data.get("myPos", self.player_id),
                "curPos": data.get("curPos", -1),
                "greaterPos": data.get("greaterPos", -1),
                "actionList_size": len(action_list),
                "version": "m1",
                "series": "M",
                "decision_type": "hardcoded",
                "phase": phase_info.get("game_phase", "unknown"),
            }
            
            # Record decision
            self.game_recorder.record_decision(
                act_index, 
                selected_action, 
                context=decision_context
            )
            
            # Validate action index
            if not self.validate_action(act_index, action_list):
                self.logger.error(f"Invalid action index: {act_index}, using 0")
                act_index = 0
            
            await self.send_action(act_index)
        
        except Exception as e:
            self.logger.error(f"✗ Decision error: {e}", exc_info=True)
            # Emergency fallback: send PASS (0)
            await self.send_action(0)
    
    def validate_action(self, action_idx: int, action_list: list) -> bool:
        """Validate action index"""
        return 0 <= action_idx < len(action_list)
    
    async def send_action(self, action_idx: int):
        """Send action to server"""
        try:
            message = {"type": "act", "actIndex": action_idx}
            await self.ws_manager.send_json(message)  # 修复：使用 send_json 而不是 send_message
            self.logger.debug(f"Sent action: {action_idx}")
        except Exception as e:
            self.logger.error(f"Failed to send action: {e}", exc_info=True)
    
    def handle_notification(self, data: dict):
        """Handle notification from server"""
        notify_type = data.get("notifyType", "")
        
        if notify_type == "gameStart":
            self._handle_game_start(data)
        elif notify_type == "gameOver":
            self._handle_game_over(data)
        elif notify_type == "tribute":
            self._handle_tribute_notification(data)
        elif notify_type == "back":
            self._handle_back_notification(data)
        elif notify_type == "act":
            # 记录其他玩家的出牌
            self._handle_act_notification(data)
    
    def _handle_game_start(self, data: dict):
        """处理游戏开始通知"""
        hand_cards = data.get("handCards", [])
        my_pos = data.get("myPos", self.player_id)
        
        # 更新player_id（如果服务器分配的位置不同）
        if my_pos != self.player_id:
            self.logger.info(f"Position updated: {self.player_id} -> {my_pos}")
            self.player_id = my_pos
            # 重新初始化决策引擎（使用新的 player_id）
            config = {"max_decision_time": 0.8, "enable_logging": True}
            self.decision_engine = RuleBasedDecisionEngineM1(my_pos, config)
        
        self.hand_cards = hand_cards
        print(f"游戏开始, 我是{my_pos}号位，手牌：{hand_cards}")
        self.logger.info(f"游戏开始, 我是{my_pos}号位，手牌数：{len(hand_cards)}")
        
        # 显示等级信息
        self_rank = data.get("selfRank", "?")
        oppo_rank = data.get("oppoRank", "?")
        cur_rank = data.get("curRank", "?")
        print(f"我方等级：{self_rank}， 对方等级：{oppo_rank}， 当前等级{cur_rank}")
        
        # 开始记录游戏
        game_info = {
            "selfRank": self_rank if self_rank != "?" else None,
            "oppoRank": oppo_rank if oppo_rank != "?" else None,
            "curRank": cur_rank if cur_rank != "?" else None
        }
        self.game_recorder.start_game(hand_cards, my_pos, game_info)
        self.game_count += 1
    
    def _handle_game_over(self, data: dict):
        """处理游戏结束通知"""
        result = data.get("result", {})
        self.logger.info(f"游戏结束: {result}")
        print(f"游戏结束: {result}")
        
        # 记录游戏结束
        self.game_recorder.end_game(result)
    
    def _handle_act_notification(self, data: dict):
        """处理其他玩家出牌通知"""
        # 更新手牌（如果有）
        hand_cards = data.get("handCards", [])
        if hand_cards:
            self.hand_cards = hand_cards
        
        # 显示其他玩家出牌信息（类似lalala客户端）
        cur_pos = data.get("curPos", -1)
        cur_action = data.get("curAction", [])
        greater_pos = data.get("greaterPos", -1)
        greater_action = data.get("greaterAction", [])
        
        if cur_pos != -1 and cur_action and cur_action[0] != "PASS":
            print(f"{cur_pos}号位打出{cur_action}， 最大动作为{greater_pos}号位打出的{greater_action} 连续pass数目： 0")


async def main():
    """Main entry point"""
    client = YF2_M1_Client(player_id=2, use_local_websocket=True)
    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())

