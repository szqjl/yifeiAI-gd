# -*- coding: utf-8 -*-
"""
yf1_m1 - YiFei AI M1 Client (Player 0)
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

# 日志文件名：yf1_m1_YYYYMMDD_HHMMSS.log
log_filename = log_dir / f"yf1_m1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

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
DELAY_BEFORE_CONNECT = 3  # seconds, to ensure sequential connection order


class YF1_M1_Client:
    """
    YiFei AI M1 Client - Player 0
    M1版本：全新的硬编码规则引擎
    
    特性：
    - 基于阶段一架构重构
    - 5阶段细分路由
    - 专注硬编码规则优化
    - 完全独立于V5版本
    - M系列：硬编码规则引擎系列（与V系列区分）
    """
    
    def __init__(self, player_id=0, use_local_websocket=True):
        self.player_id = player_id
        self.user_info = "yf1_m1"
        self.logger = logging.getLogger(f"yf1_m1")
        
        # 初始化 WebSocket 管理器
        self.ws_manager = WebSocketManager(self.user_info, use_local=use_local_websocket)
        self.websocket = None  # 保持向后兼容
        
        # Initialize RuleBasedDecisionEngineM1 (M1硬编码决策引擎)
        self.logger.info("🎯 Initializing RuleBasedDecisionEngineM1")
        config = {
            "max_decision_time": 0.8,  # 最大决策时间（秒）
            "enable_logging": True,     # 启用日志
            
            # 第一阶段优化功能开关（基于 Agentic Design Patterns）
            "use_intelligent_router": True,      # 启用智能路由器（路由优化）
            "route_cache_size": 1000,            # 路由缓存大小
            "use_enhanced_priority": True,        # 启用增强优先级系统（优先级系统增强）
            "priority_history_size": 1000,        # 优先级历史记录大小
            "use_enhanced_collaboration": True,   # 启用增强协作策略（协作策略优化）
        }
        self.decision_engine = RuleBasedDecisionEngineM1(player_id, config)
        
        self.hand_cards = []  # Track current hand
        
        # Statistics
        self.decision_count = 0
        self.game_count = 0
        
        # Initialize game recorder
        self.game_recorder = GameRecorder(player_id, "yf1_m1")
        
        self.logger.info(f"✓ yf1_m1 initialized (Player {player_id})")
        self.logger.info(f"  - Decision Engine: RuleBasedDecisionEngineM1")
        self.logger.info(f"  - Version: M1 (Hardcoded Rules)")
        self.logger.info(f"  - Series: M (Hardcoded Rules Engine)")
        self.logger.info(f"  - Architecture: Stage Router with 5 Phases")
    
    async def connect(self):
        """Connect to game server using configured WebSocket manager"""
        try:
            # 使用 WebSocket 管理器连接
            self.logger.info(f"[yf1_m1] 等待连接延迟 {DELAY_BEFORE_CONNECT} 秒，确保第一个位置...")
            time.sleep(DELAY_BEFORE_CONNECT)
            self.logger.info(f"[yf1_m1] 开始连接 ws://127.0.0.1:23456/game/yf1_m1")
            connected = await self.ws_manager.connect()
            if not connected:
                self.logger.error("Failed to connect to server")
                return
            
            # 设置 websocket 引用以保持向后兼容
            self.websocket = self.ws_manager.websocket
            
            # 显示连接成功和期望位置信息
            print(f"[yf1_m1] 连接成功！期望位置：{self.player_id}号位（实际位置将在游戏开始时由服务器分配）")
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
        
        # 检查是否是游戏开始（如果还没有开始记录）
        # 有些服务器可能在第一个action请求时发送handCards
        if not self.game_recorder.current_game:
            hand_cards = data.get("handCards", [])
            if hand_cards and len(hand_cards) == 27:
                self.logger.info("在action请求中检测到初始手牌，触发游戏开始")
                my_pos = data.get("myPos", self.player_id)
                
                # ⚠️ 重要：尝试从publicInfo获取所有玩家的手牌信息
                all_players_hands = {}
                public_info = data.get("publicInfo", [])
                if public_info and isinstance(public_info, list):
                    for i, info in enumerate(public_info):
                        if isinstance(info, dict) and "handCards" in info:
                            player_hand = info["handCards"]
                            if isinstance(player_hand, list) and len(player_hand) > 0:
                                all_players_hands[i] = player_hand
                                self.logger.info(f"从publicInfo获取玩家{i}的手牌: {len(player_hand)}张")
                
                # 确保自己的手牌被记录
                all_players_hands[my_pos] = hand_cards
                
                game_info = {
                    "selfRank": data.get("selfRank"),
                    "oppoRank": data.get("oppoRank"),
                    "curRank": data.get("curRank", "2")
                }
                self.game_recorder.start_game(hand_cards, my_pos, game_info, all_players_hands)
                self.game_count += 1
                self.logger.info(f"✓ 游戏记录已开始（从action请求）: game_count={self.game_count}, 记录了{len(all_players_hands)}个玩家的手牌")
        
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
            
            # 获取阶段信息（用于日志）
            phase_info = self.decision_engine.get_phase_info(data)
            self.logger.info(f"Phase: {phase_info['game_phase']}, Handler: {phase_info['handler_key']}, 剩余牌数: {phase_info['my_remain']}")
            
            # 显示选择的动作（类似lalala客户端）
            selected_action = action_list[act_index] if act_index < len(action_list) else []
            print(f"[yf1_m1] 选择动作: {act_index}")
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
            
            # ⚠️ 重要：更新手牌（如果出牌）
            if selected_action and len(selected_action) >= 3 and isinstance(selected_action[2], list):
                played_cards = selected_action[2]
                
                # 规范化卡牌格式
                normalized_played_cards = []
                for card in played_cards:
                    if isinstance(card, str) and len(card) >= 2:
                        normalized_played_cards.append(card)
                    elif isinstance(card, list) and len(card) >= 2:
                        # 处理["C", "8"]格式，转换为"C8"
                        suit = str(card[0])
                        rank = str(card[1])
                        normalized_played_cards.append(f"{suit}{rank}")
                
                old_hand_size = len(self.hand_cards)
                removed_count = 0
                for card in normalized_played_cards:
                    if card in self.hand_cards:
                        self.hand_cards.remove(card)
                        removed_count += 1
                    else:
                        self.logger.warning(f"⚠ 尝试移除不存在的卡牌: {card}，当前手牌: {self.hand_cards[:10]}...")
                
                new_hand_size = len(self.hand_cards)
                if removed_count != len(normalized_played_cards):
                    self.logger.warning(f"⚠ 手牌移除不完整: 期望移除{len(normalized_played_cards)}张，实际移除{removed_count}张，手牌从{old_hand_size}变为{new_hand_size}")
                elif old_hand_size != new_hand_size + len(normalized_played_cards):
                    self.logger.warning(f"⚠ 手牌数量不匹配: 移除了{len(normalized_played_cards)}张牌，手牌从{old_hand_size}变为{new_hand_size}")
                else:
                    self.logger.debug(f"✓ 手牌更新成功: 移除了{len(normalized_played_cards)}张牌，剩余{new_hand_size}张")
            
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
        # 兼容两种格式：notifyType 和 stage
        notify_type = data.get("notifyType", "")
        stage = data.get("stage", "")
        
        # 调试日志：记录收到的通知
        self.logger.debug(f"收到通知: notifyType={notify_type}, stage={stage}, keys={list(data.keys())[:5]}")
        
        # 优先使用notifyType，如果没有则使用stage
        if notify_type:
            notification_key = notify_type
        elif stage:
            notification_key = stage
        else:
            notification_key = ""
        
        self.logger.debug(f"通知键: {notification_key}")
        
        # 处理游戏开始（兼容多种格式）
        if notification_key in ["gameStart", "beginning"]:
            self.logger.info(f"✓ 识别到游戏开始通知: notification_key={notification_key}")
            self._handle_game_start(data)
        # 处理游戏结束（兼容多种格式：gameOver, gameResult, episodeOver）
        elif notification_key in ["gameOver", "gameResult", "episodeOver"]:
            self.logger.info(f"✓ 识别到游戏结束通知: notification_key={notification_key}")
            self._handle_game_over(data)
        # 处理进贡
        elif notification_key == "tribute":
            self._handle_tribute_notification(data)
        # 处理还贡
        elif notification_key == "back":
            self._handle_back_notification(data)
        # 处理出牌通知
        elif notification_key == "act" or (stage == "play" and notify_type == ""):
            # 记录其他玩家的出牌
            self._handle_act_notification(data)
        else:
            # 如果都没有匹配，检查是否有其他游戏结束相关的字段
            # 有些服务器可能使用不同的字段名（如episodeOver在stage中，但notifyType为空）
            if "gameOver" in data or "gameResult" in data or "episodeOver" in data or data.get("result"):
                self.logger.info(f"✓ 从其他字段识别到游戏结束: notifyType={notify_type}, stage={stage}")
                self._handle_game_over(data)
            # 特殊处理：如果消息中有handCards但没有stage，可能是游戏开始
            elif "handCards" in data and not self.game_recorder.current_game:
                self.logger.info("检测到handCards但无stage，尝试作为游戏开始处理")
                self._handle_game_start(data)
            else:
                # 如果都没有匹配，记录警告
                self.logger.warning(f"⚠ 未识别的通知类型: notifyType={notify_type}, stage={stage}, notification_key={notification_key}")
    
    def _handle_game_start(self, data: dict):
        """处理游戏开始通知（兼容多种格式）"""
        # 兼容多种格式：handCards字段或playerPosition字段
        hand_cards = data.get("handCards", [])
        if not hand_cards:
            # 尝试从其他字段获取
            hand_cards = data.get("initial_hand", [])
        
        # 兼容多种格式：myPos字段或playerPosition字段
        my_pos = data.get("myPos", self.player_id)
        if my_pos == self.player_id:
            my_pos = data.get("playerPosition", my_pos)
        
        # 更新player_id（如果服务器分配的位置不同）
        if my_pos != self.player_id:
            self.logger.info(f"Position updated: {self.player_id} -> {my_pos}")
            self.player_id = my_pos
            # 重新初始化决策引擎（使用新的 player_id）
            config = {
                "max_decision_time": 0.8,
                "enable_logging": True,
                "curRank": data.get("curRank", "2"),
                # 第一阶段优化功能开关（基于 Agentic Design Patterns）
                "use_intelligent_router": True,      # 启用智能路由器（路由优化）
                "route_cache_size": 1000,            # 路由缓存大小
                "use_enhanced_priority": True,        # 启用增强优先级系统（优先级系统增强）
                "priority_history_size": 1000,        # 优先级历史记录大小
                "use_enhanced_collaboration": True,   # 启用增强协作策略（协作策略优化）
            }
            self.decision_engine = RuleBasedDecisionEngineM1(my_pos, config)
        
        self.hand_cards = hand_cards
        print(f"游戏开始, 我是{my_pos}号位，手牌：{hand_cards}")
        self.logger.info(f"游戏开始, 我是{my_pos}号位，手牌数：{len(hand_cards)}")
        
        # 显示等级信息
        self_rank = data.get("selfRank", "?")
        oppo_rank = data.get("oppoRank", "?")
        cur_rank = data.get("curRank", "?")
        print(f"我方等级：{self_rank}， 对方等级：{oppo_rank}， 当前等级{cur_rank}")
        
        # ⚠️ 重要：尝试从publicInfo获取所有玩家的手牌信息
        all_players_hands = {}
        public_info = data.get("publicInfo", [])
        if public_info and isinstance(public_info, list):
            for i, info in enumerate(public_info):
                if isinstance(info, dict) and "handCards" in info:
                    player_hand = info["handCards"]
                    if isinstance(player_hand, list) and len(player_hand) > 0:
                        all_players_hands[i] = player_hand
                        self.logger.info(f"从publicInfo获取玩家{i}的手牌: {len(player_hand)}张")
        
        # 确保自己的手牌被记录
        all_players_hands[my_pos] = hand_cards
        
        # 开始记录游戏
        game_info = {
            "selfRank": self_rank if self_rank != "?" else None,
            "oppoRank": oppo_rank if oppo_rank != "?" else None,
            "curRank": cur_rank if cur_rank != "?" else None
        }
        
        # start_game() 内部已经处理了当前游戏记录的保存，这里不需要重复处理
        self.game_recorder.start_game(hand_cards, my_pos, game_info, all_players_hands)
        self.game_count += 1
        self.logger.info(f"✓ 游戏记录已开始: game_count={self.game_count}, 记录了{len(all_players_hands)}个玩家的手牌")
    
    def _handle_game_over(self, data: dict):
        """处理游戏结束通知"""
        # 兼容两种格式：result字段和gameResult格式
        result = data.get("result", {})
        
        # 如果是gameResult格式，提取victoryNum和draws
        if not result and data.get("stage") == "gameResult":
            result = {
                "victoryNum": data.get("victoryNum", []),
                "draws": data.get("draws", []),
                "total_decisions": self.decision_count,
                "game_count": self.game_count
            }
        
        self.logger.info(f"游戏结束: {result}, current_game={self.game_recorder.current_game is not None}")
        print(f"游戏结束: {result}")
        
        # 检查是否已经有游戏记录
        if not self.game_recorder.current_game:
            self.logger.warning(f"⚠ 游戏结束通知收到，但current_game为None，可能已经保存过了")
            return
        
        # 记录游戏结束
        filepath = self.game_recorder.end_game(result)
        if filepath:
            self.logger.info(f"✓ 游戏记录已保存: {filepath}")
        else:
            self.logger.warning(f"⚠ 游戏记录保存失败，可能原因：start_game()未被调用")
    
    def _handle_act_notification(self, data: dict):
        """处理其他玩家出牌通知"""
        # ⚠️ 重要：优先使用服务器发送的最新handCards（服务器的手牌信息最准确）
        hand_cards = data.get("handCards", [])
        if hand_cards:
            # 验证手牌数量合理性
            if len(hand_cards) <= 27:
                # 验证卡牌格式
                valid_cards = []
                for card in hand_cards:
                    if isinstance(card, str) and len(card) >= 2:
                        valid_cards.append(card)
                    elif isinstance(card, list) and len(card) >= 2:
                        # 处理["C", "8"]格式，转换为"C8"
                        suit = str(card[0])
                        rank = str(card[1])
                        valid_cards.append(f"{suit}{rank}")
                
                if len(valid_cards) != len(hand_cards):
                    self.logger.warning(f"⚠ 手牌格式验证：原始{len(hand_cards)}张，有效{len(valid_cards)}张")
                
                old_hand_size = len(self.hand_cards)
                self.hand_cards = valid_cards
                self.logger.debug(f"✓ 从服务器更新手牌: {old_hand_size} -> {len(valid_cards)}张")
            else:
                self.logger.warning(f"⚠ 服务器发送的手牌数量异常: {len(hand_cards)}张，忽略更新")
        
        # 显示其他玩家出牌信息（类似lalala客户端）
        cur_pos = data.get("curPos", -1)
        cur_action = data.get("curAction", [])
        greater_pos = data.get("greaterPos", -1)
        greater_action = data.get("greaterAction", [])
        
        if cur_pos != -1 and cur_action and cur_action[0] != "PASS":
            print(f"{cur_pos}号位打出{cur_action}， 最大动作为{greater_pos}号位打出的{greater_action} 连续pass数目： 0")
        
        # ⚠️ 重要：记录所有玩家的出牌动作到游戏记录器
        if cur_pos != -1 and cur_action:
            # 解析curAction（可能是字符串格式）
            if isinstance(cur_action, str):
                try:
                    import ast
                    cur_action = ast.literal_eval(cur_action)
                except:
                    pass
            
            # 解析greaterAction（可能是字符串格式）
            if isinstance(greater_action, str):
                try:
                    import ast
                    greater_action = ast.literal_eval(greater_action)
                except:
                    pass
            
            # 构建上下文信息
            context = {
                "publicInfo": data.get("publicInfo", []),
                "selfRank": data.get("selfRank"),
                "oppoRank": data.get("oppoRank"),
                "curRank": data.get("curRank"),
                "restCards": data.get("restCards", [])
            }
            
            # 记录动作
            self.game_recorder.record_action(cur_pos, cur_action, greater_pos, greater_action, context)


async def main():
    """Main entry point"""
    client = YF1_M1_Client(player_id=0, use_local_websocket=True)
    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())

