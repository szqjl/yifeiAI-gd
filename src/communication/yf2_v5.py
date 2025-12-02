# -*- coding: utf-8 -*-
"""
yf2_v5 - YiFei AI V5 Client (Player 2)
Enhanced version with improved RL integration and knowledge base
升级版本：增强的RL集成和知识库应用
"""
import asyncio
import json
import sys
import logging
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent)) # Add project root

from decision.hybrid_decision_engine_v4 import HybridDecisionEngineV4
from decision.rl_decision_engine import RLDecisionEngine
from communication.game_recorder import GameRecorder
from communication.websocket_manager import WebSocketManager
from decision.card_power_evaluator import calculate_card_power
from decision.single_card_strategy import single_card_strategy
from decision.bomb_strategy import bomb_strategy
from decision.endgame_strategy import endgame_strategy
from decision.main_decision import main_decision
from decision.card_grouping_strategy import grouping_strategy

# Configure logging
import os
from datetime import datetime

# 创建日志目录
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# 日志文件名：yf2_v5_YYYYMMDD_HHMMSS.log
log_filename = log_dir / f"yf2_v5_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

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


class YF2_V5_Client:
    """
    YiFei AI V5 Client - Player 2
    Enhanced version with:
    - Improved RL integration (智能RL决策)
    - Enhanced knowledge base application (增强知识库应用)
    - Better decision fusion (更好的决策融合)
    """
    
    def __init__(self, player_id=2, use_local_websocket=True):
        self.player_id = player_id
        self.user_info = "yf2_v5"
        self.logger = logging.getLogger(f"yf2_v5")
        
        # 初始化 WebSocket 管理器（从配置文件读取设置）
        self.ws_manager = WebSocketManager(self.user_info, use_local=use_local_websocket)
        self.websocket = None  # 保持向后兼容
        
        # Initialize HybridDecisionEngineV4 (基础决策引擎)
        config = {
            "enable_lalala": True,
            "enable_fallback": True,
            "log_level": "INFO",
            "performance_threshold": 1.0
        }
        self.decision_engine = HybridDecisionEngineV4(player_id, config)
        
        # Initialize RL Engine (V5增强：更智能的RL集成)
        try:
            self.rl_engine = RLDecisionEngine()
            self.rl_available = True
            self.logger.info("✓ RL Engine initialized")
        except Exception as e:
            self.logger.warning(f"⚠ RL Engine not available: {e}")
            self.rl_engine = None
            self.rl_available = False
        
        # V5特性：智能决策融合
        self.use_hybrid_decision = True  # 使用混合决策（RL + Knowledge + Rule-based）
        self.rl_weight = 0.25  # RL决策权重（降低）
        self.knowledge_weight = 0.4  # 知识库权重（降低）
        self.rule_weight = 0.35  # 规则引擎权重（提高，优先策略建议）
        
        self.hand_cards = [] # Track current hand
        
        # Statistics
        self.decision_count = 0
        self.game_count = 0
        self.rl_decision_count = 0
        self.knowledge_decision_count = 0
        self.strategy_decision_count = 0  # 新增策略决策计数
        
        # Initialize game recorder
        self.game_recorder = GameRecorder(player_id, "yf2_v5")
        
        self.logger.info(f"✓ yf2_v5 initialized (Player {player_id})")
        self.logger.info(f"  - RL Engine: {'Available' if self.rl_available else 'Not Available'}")
        self.logger.info(f"  - Hybrid Decision: {self.use_hybrid_decision}")
        self.logger.info(f"  - Strategy Integration: Enabled (牌力评估、单牌策略、炸弹策略、残局策略)")
    
    async def connect(self):
        """Connect to game server using configured WebSocket manager"""
        try:
            # 使用 WebSocket 管理器连接
            connected = await self.ws_manager.connect()
            if not connected:
                self.logger.error("Failed to connect to server")
                return
            
            # 设置 websocket 引用以保持向后兼容
            self.websocket = self.ws_manager.websocket
            
            # 设置消息处理回调
            self.ws_manager.set_message_handler(self.process_message)
            
            # 开始处理消息
            await self.ws_manager.handle_messages()
        except Exception as e:
            self.logger.error(f"✗ Connection error: {e}", exc_info=True)
    
    async def handle_messages(self):
        """Handle incoming messages from server (deprecated, use ws_manager.handle_messages)"""
        # 此方法已被 ws_manager.handle_messages 替代
        # 保留此方法以保持向后兼容
        await self.ws_manager.handle_messages(self.process_message)
    
    async def process_message(self, data: dict):
        """Process a message from the server"""
        message_type = data.get("type", "")
        
        if message_type == "act":
            await self.handle_action_request(data)
        
        elif message_type == "notify":
            self.handle_notification(data)
    
    async def handle_action_request(self, data: dict):
        """Handle action request from server (V5增强决策)"""
        self.decision_count += 1
        action_list = data.get("actionList", [])
        
        if not action_list:
            self.logger.warning("Empty action list, sending 0")
            await self.send_action(0)
            return
        
        try:
            # V5增强：智能混合决策
            if self.use_hybrid_decision:
                act_index = self._hybrid_decision(data, action_list)
            else:
                # 回退到V4决策
                act_index = self.decision_engine.decide(data)
            
            # Get decision details for recording
            decision_context = {
                "myPos": data.get("myPos", self.player_id),
                "curPos": data.get("curPos", -1),
                "greaterPos": data.get("greaterPos", -1),
                "actionList_size": len(action_list),
                "version": "v5",
                "decision_type": "hybrid" if self.use_hybrid_decision else "v4_fallback"
            }
            
            # Record decision
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
    
    def _extract_game_state(self, data: dict) -> dict:
        """
        从游戏状态中提取信息，用于策略决策
        
        Returns:
            包含游戏状态信息的字典
        """
        # 获取手牌
        hand_cards = self.hand_cards if self.hand_cards else data.get("handCards", [])
        
        # 获取对手剩余牌数
        public_info = data.get("publicInfo", [])
        opponent_rest_cards = 27  # 默认值
        my_pos = data.get("myPos", self.player_id)
        
        if public_info and isinstance(public_info, list):
            # 计算对手（非队友）的平均剩余牌数
            opponent_cards = []
            for i, info in enumerate(public_info):
                if isinstance(info, dict):
                    rest = info.get("rest", 27)
                    # 对手是 (my_pos+1)%4 和 (my_pos+3)%4
                    if i != my_pos and i != (my_pos + 2) % 4:
                        opponent_cards.append(rest)
            
            if opponent_cards:
                opponent_rest_cards = sum(opponent_cards) // len(opponent_cards)
        
        # 判断游戏阶段
        total_cards = len(hand_cards)
        if opponent_rest_cards <= 10:
            game_phase = "endgame"
        elif total_cards >= 20:
            game_phase = "opening"
        else:
            game_phase = "mid"
        
        # 获取当前动作信息
        cur_action = data.get("curAction", [])
        greater_action = data.get("greaterAction", [])
        cur_pos = data.get("curPos", -1)
        greater_pos = data.get("greaterPos", -1)
        
        # 判断是否为主动出牌
        is_active = (cur_pos == -1 or greater_pos == -1)
        
        return {
            "hand_cards": hand_cards,
            "game_phase": game_phase,
            "opponent_rest_cards": opponent_rest_cards,
            "cur_action": cur_action,
            "greater_action": greater_action,
            "cur_pos": cur_pos,
            "greater_pos": greater_pos,
            "is_active": is_active,
            "cur_rank": data.get("curRank", "2")
        }
    
    def _apply_strategy_suggestions(self, game_state: dict, action_list: list) -> list:
        """
        应用策略建议，将策略建议转换为动作评分
        
        Returns:
            候选动作列表 [(action_index, score, source), ...]
        """
        candidates = []
        hand_cards = game_state["hand_cards"]
        game_phase = game_state["game_phase"]
        opponent_rest_cards = game_state["opponent_rest_cards"]
        
        if not hand_cards:
            return candidates
        
        try:
            # 策略应用顺序（按优先级）：
            # 1. 组牌策略 - 优先考虑组牌效果（减少轮次、减少单牌）
            # 2. 牌力评估 - 评估当前牌力
            # 3. 单牌策略 - 根据牌力给出单牌建议
            # 4. 炸弹策略 - 根据牌力给出炸弹建议
            # 5. 残局策略 - 根据残局情况给出建议
            
            # 1. 组牌策略（优先：减少轮次、减少单牌）
            grouping_sugg = grouping_strategy(
                hand_cards=hand_cards,
                action_list=action_list,
                game_phase=game_phase,
                power=5.0  # 先用默认牌力，后续会更新
            )
            
            # 2. 计算牌力（基于组牌后的手牌评估）
            power_result = calculate_card_power(
                hand_cards,
                game_phase=game_phase,
                opponent_rest_cards=opponent_rest_cards,
                cur_level_rank=int(game_state["cur_rank"]) if game_state["cur_rank"].isdigit() else 10
            )
            power = power_result['total_power']
            has_bomb = (power_result['details']['bomb_super_high'] + 
                       power_result['details']['bomb_mid'] + 
                       power_result['details']['bomb_normal'] > 0)
            
            # 3. 单牌策略（基于牌力评估结果）
            # 检查手牌中是否有王、级牌、大对子等
            has_king = any('B' in card or 'b' in card for card in hand_cards)  # 王
            has_level_card = any(game_state["cur_rank"] in card for card in hand_cards)  # 级牌
            # 检查是否有Q以上的对子
            rank_map = {'3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'T':10, 'J':11, 'Q':12, 'K':13, 'A':14, '2':15, 'B':16}
            rank_count = {}
            for card in hand_cards:
                if len(card) >= 2:
                    rank_str = card[1] if len(card) == 2 else card[1:2]
                    rank = rank_map.get(rank_str, 0)
                    rank_count[rank] = rank_count.get(rank, 0) + 1
            has_pair_above_q = any(count >= 2 and rank >= 12 for rank, count in rank_count.items())
            
            single_sugg = single_card_strategy(
                game_phase=game_phase,
                power=power,
                opponent_rest_cards=opponent_rest_cards,
                has_bomb=has_bomb,
                has_king=has_king,
                has_level_card=has_level_card,
                has_pair_above_q=has_pair_above_q
            )
            
            # 4. 炸弹策略（基于牌力评估结果）
            bomb_sugg = bomb_strategy(
                game_phase=game_phase,
                power=power,
                opponent_rest_cards=opponent_rest_cards
            )
            
            # 5. 残局策略（基于牌力评估结果）
            endgame_sugg = endgame_strategy(
                opponent_rest_cards=opponent_rest_cards,
                power=power,
                has_bomb=has_bomb
            )
            
            # 3. 根据策略建议调整动作评分
            # 分析动作列表，为所有动作生成策略评分
            for idx, action in enumerate(action_list):
                if not action or len(action) == 0:
                    continue
                
                action_type = action[0] if isinstance(action, list) else str(action)
                score_adjustment = 0.0
                strategy_reason = "基础策略评分"
                
                # 获取动作牌数（用于后续判断）
                action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
                action_card_count = len(action_cards)
                
                # 基础策略评分：所有动作都有基础评分
                base_strategy_score = 20.0
                
                # 策略应用顺序（按优先级）：
                # 1. 组牌策略（优先：减少轮次、减少单牌）
                # 2. 牌力评估（用于后续策略判断）
                # 3. 单牌策略
                # 4. 炸弹策略
                # 5. 残局策略
                
                # 1. 组牌策略（优先应用：减少轮次、减少单牌）
                for grouping_item in grouping_sugg.get("suggestions", []):
                    if grouping_item["action_index"] == idx:
                        grouping_score = grouping_item["score"]
                        score_adjustment += grouping_score
                        if grouping_item["reasons"]:
                            strategy_reason = f"组牌策略: {', '.join(grouping_item['reasons'])}"
                        break
                
                # 2. 牌力评估（已计算，用于后续策略判断）
                # power, has_bomb 已在上面计算
                
                # 3. 单牌策略（基于牌力评估结果）
                # 根据动作类型应用策略
                if action_type == "PASS":
                    # 单牌策略：不出小单
                    if single_sugg.get("action", "").startswith("不出"):
                        score_adjustment += 30.0
                        strategy_reason = single_sugg.get("reason", "")
                else:
                    # 非PASS动作
                    
                    # 单牌策略：全面应用所有建议
                    single_action = single_sugg.get("action", "")
                    single_reason = single_sugg.get("reason", "")
                    
                    # 1. 出单相关建议
                    if action_type == "Single" or action_type == "SINGLE":
                        if "出单" in single_action or "打一张" in single_action:
                            if "起始出单" in single_action or "有保护" in single_reason:
                                # 有保护出单，大幅加分
                                score_adjustment += 40.0
                                strategy_reason = "单牌策略：有保护出单"
                            elif "多炸保护" in single_reason:
                                # 多炸保护出单，加分
                                score_adjustment += 35.0
                                strategy_reason = "单牌策略：多炸保护出单"
                            elif "进贡大王" in single_reason:
                                # 进贡大王后出单，加分
                                score_adjustment += 30.0
                                strategy_reason = "单牌策略：进贡后出单"
                            elif "控下家单" in single_action or "卡小" in single_reason:
                                # 控下家单，对小单张加分
                                if action_card_count == 1:
                                    # 检查是否是小单张（3-9）
                                    card_rank = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                    if card_rank in ['3', '4', '5', '6', '7', '8', '9']:
                                        score_adjustment += 35.0
                                        strategy_reason = "单牌策略：控下家小单"
                            elif "送小单" in single_action or "让对家" in single_action:
                                # 让对家出单，对小单张加分
                                if action_card_count == 1:
                                    card_rank = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                    if card_rank in ['3', '4', '5', '6', '7', '8', '9']:
                                        score_adjustment += 30.0
                                        strategy_reason = "单牌策略：送对家小单"
                            elif "顺子出中间" in single_action:
                                # 顺子出中间单，加分
                                score_adjustment += 25.0
                                strategy_reason = "单牌策略：顺子出中间"
                            else:
                                # 一般出单建议
                                score_adjustment += 30.0
                                strategy_reason = "单牌策略：出单"
                        elif "不出小单" in single_action or "不出单" in single_action:
                            # 不建议出单，对单张动作减分
                            score_adjustment -= 25.0
                            strategy_reason = "单牌策略：不出单"
                        elif "不出" in single_action and "小单" in single_action:
                            # 不出小单，对小单张减分
                            if action_card_count == 1:
                                card_rank = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                if card_rank in ['3', '4', '5', '6', '7', '8', '9']:
                                    score_adjustment -= 30.0
                                    strategy_reason = "单牌策略：不出小单"
                    
                    # 2. 出对相关建议
                    elif action_type == "Pair" or action_type == "PAIR":
                        if "出对" in single_action or "打两张" in single_action:
                            score_adjustment += 30.0
                            strategy_reason = "单牌策略：出对"
                        elif "拆大对出单" in single_action:
                            # 建议拆大对出单，对拆对动作减分
                            score_adjustment -= 20.0
                            strategy_reason = "单牌策略：不拆大对"
                        elif "无单拆大对" in single_action or "不出" in single_action:
                            # 不建议拆大对，对拆对动作减分
                            score_adjustment -= 15.0
                            strategy_reason = "单牌策略：不拆大对"
                    
                    # 3. 出三张相关建议
                    elif action_type == "Trips" or action_type == "TRIPS":
                        if "打三张" in single_action:
                            score_adjustment += 30.0
                            strategy_reason = "单牌策略：出三张"
                    
                    # 4. 三带二相关建议
                    elif action_type == "THREE_WITH_TWO":
                        if "打三带二" in single_action:
                            score_adjustment += 30.0
                            strategy_reason = "单牌策略：出三带二"
                    
                    # 5. 顺子相关建议
                    elif action_type == "Straight" or action_type == "STRAIGHT":
                        if "打顺" in single_action:
                            score_adjustment += 30.0
                            strategy_reason = "单牌策略：出顺"
                        elif "顺子出中间" in single_action:
                            # 顺子出中间单，对顺子动作加分
                            score_adjustment += 25.0
                            strategy_reason = "单牌策略：顺子出中间"
                
                # 根据牌力调整（增强）
                if power >= 8:
                    # 强牌，非PASS动作大幅加分
                    if action_type != "PASS":
                        score_adjustment += 25.0
                elif power < 5:
                    # 弱牌，PASS或保守动作加分
                    if action_type == "PASS" or action_card_count <= 2:
                        score_adjustment += 20.0
                
                # 5. 残局策略（最后应用：根据残局情况）
                if game_phase == "endgame":
                    if action_type != "PASS":
                        score_adjustment += 15.0
                
                # 为所有动作生成策略评分（即使没有特殊调整）
                # 提高基础评分，让策略建议更有竞争力
                base_score = 100.0 * self.rule_weight  # 提高基础规则评分到100
                final_score = base_score + score_adjustment + base_strategy_score
                # 确保评分不为负数，至少保持基础评分
                if final_score < 0:
                    final_score = base_score * 0.5  # 即使建议不炸，也保持一定评分
                
                candidates.append((idx, final_score, f"Strategy-{strategy_reason[:20]}"))
                self.strategy_decision_count += 1
                
                # 只在有重要调整时记录详细日志
                if abs(score_adjustment) > 10.0:
                    self.logger.info(
                        f"Strategy suggestion: action={idx}, type={action_type}, "
                        f"score={final_score:.1f}, adjustment={score_adjustment:.1f}, reason={strategy_reason}"
                    )
        
        except Exception as e:
            self.logger.warning(f"Strategy application failed: {e}", exc_info=True)
        
        return candidates
    
    def _hybrid_decision(self, data: dict, action_list: list) -> int:
        """
        V5增强：智能混合决策
        
        融合多种决策源：
        1. RL决策（如果可用）
        2. 知识库增强决策（HybridDecisionEngineV4）
        3. 规则引擎决策（新增策略：牌力评估、单牌策略、炸弹策略、残局策略）
        
        Args:
            data: 游戏状态消息
            action_list: 可用动作列表
            
        Returns:
            最优动作索引
        """
        candidates = []
        
        # 1. 获取基础决策引擎的候选（包含知识库增强）
        try:
            # 使用V4引擎生成候选（已经包含知识库增强）
            base_candidates = self.decision_engine._generate_candidates(data)
            if base_candidates:
                # 增强候选（知识库已应用）
                enhanced_candidates = self.decision_engine._enhance_candidates(base_candidates, data)
                for idx, score, layer in enhanced_candidates:
                    # 应用知识库权重
                    weighted_score = score * self.knowledge_weight
                    candidates.append((idx, weighted_score, "Knowledge"))
                    self.knowledge_decision_count += 1
        except Exception as e:
            self.logger.warning(f"Base decision engine failed: {e}")
        
        # 2. 获取RL决策（如果可用）
        if self.rl_available and self.rl_engine:
            try:
                # 注入手牌信息
                data_with_hand = data.copy()
                data_with_hand['handCards'] = self.hand_cards
                
                rl_action = self.rl_engine.decide(data_with_hand)
                if rl_action is not None and 0 <= rl_action < len(action_list):
                    # RL决策评分（使用权重）
                    rl_score = 100.0 * self.rl_weight  # 基础RL评分
                    candidates.append((rl_action, rl_score, "RL"))
                    self.rl_decision_count += 1
                    self.logger.debug(f"RL decision: action={rl_action}, score={rl_score:.1f}")
            except Exception as e:
                self.logger.warning(f"RL decision failed: {e}")
        
        # 3. 应用新增策略（牌力评估、单牌策略、炸弹策略、残局策略）
        try:
            game_state = self._extract_game_state(data)
            strategy_candidates = self._apply_strategy_suggestions(game_state, action_list)
            candidates.extend(strategy_candidates)
        except Exception as e:
            self.logger.warning(f"Strategy decision failed: {e}", exc_info=True)
        
        # 4. 如果没有候选，使用V4引擎的decide方法
        if not candidates:
            self.logger.warning("No candidates from hybrid decision, using V4 fallback")
            return self.decision_engine.decide(data)
        
        # 5. 选择最优动作（按加权评分排序）
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_action, best_score, best_source = candidates[0]
        
        self.logger.debug(
            f"Hybrid decision: action={best_action}, score={best_score:.1f}, "
            f"source={best_source}, candidates={len(candidates)}"
        )
        
        return best_action
    
    def handle_notification(self, data: dict):
        """Handle notification from server"""
        stage = data.get("stage", "")
        
        if stage == "beginning":
            # 获取初始手牌信息
            hand_cards = data.get("handCards", [])
            self.hand_cards = hand_cards # Store for RL engine
            my_pos = data.get("myPos", self.player_id)
            
            # 更新实际位置（服务器分配的）
            if my_pos != self.player_id:
                self.logger.info(f"Position updated: {self.player_id} -> {my_pos}")
                self.player_id = my_pos
            
            # 打印手牌信息（与lalala客户端格式一致）
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
                        pass
            
            # 从restCards中获取其他玩家的手牌（如果有）
            rest_cards = data.get("restCards", [])
            if rest_cards:
                for rest_info in rest_cards:
                    if isinstance(rest_info, list) and len(rest_info) >= 2:
                        pos = rest_info[0]
                        if isinstance(pos, str):
                            try:
                                pos = int(pos)
                            except:
                                continue
                        cards = rest_info[1]
                        if cards and isinstance(cards, list) and len(cards) > 0:
                            if isinstance(cards[0], list):
                                normalized_cards = [f"{c[0]}{c[1]}" if isinstance(c, list) and len(c) >= 2 else str(c) for c in cards]
                                cards = normalized_cards
                        if pos != my_pos:
                            all_players_hands[pos] = cards
                            self.logger.info(f"记录{pos}号位手牌: {len(cards)}张")
            
            # 确保my_pos也是整数键
            if isinstance(my_pos, str):
                try:
                    my_pos = int(my_pos)
                except:
                    pass
            if my_pos in all_players_hands and isinstance(my_pos, str):
                all_players_hands[int(my_pos)] = all_players_hands.pop(my_pos)
            elif not isinstance(my_pos, str):
                all_players_hands[my_pos] = hand_cards
            
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
            
            # 格式化出牌信息
            if cur_action and len(cur_action) > 0 and cur_action[0] != "PASS":
                action_str = f"{cur_pos}号位打出{cur_action}"
                greater_str = f"最大动作为{greater_pos}号位打出的{greater_action}" if greater_action else ""
                self.logger.info(f"{action_str}， {greater_str}")
                
                # Update my hand cards if I played
                if cur_pos == self.player_id:
                    if len(cur_action) >= 3 and isinstance(cur_action[2], list):
                        played_cards = cur_action[2]
                        for card in played_cards:
                            if card in self.hand_cards:
                                self.hand_cards.remove(card)
            
            # 记录到游戏记录器
            context = {
                "publicInfo": data.get("publicInfo", []),
                "selfRank": data.get("selfRank"),
                "oppoRank": data.get("oppoRank"),
                "curRank": data.get("curRank"),
                "restCards": data.get("restCards", [])
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
                "game_count": self.game_count,
                "rl_decisions": self.rl_decision_count,
                "knowledge_decisions": self.knowledge_decision_count,
                "strategy_decisions": self.strategy_decision_count
            }
            
            self.logger.info("=" * 60)
            self.logger.info("GAME RESULT (V5)")
            self.logger.info("=" * 60)
            self.logger.info(f"Victory counts: {victory_num}")
            self.logger.info(f"Total decisions: {self.decision_count}")
            self.logger.info(f"  - RL decisions: {self.rl_decision_count}")
            self.logger.info(f"  - Knowledge decisions: {self.knowledge_decision_count}")
            self.logger.info(f"  - Strategy decisions: {self.strategy_decision_count}")
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
            
            # 保存战绩到 game_scores.json（用于GUI显示）
            self._save_game_scores(victory_num)
            
            # Reset for next game
            self.decision_count = 0
            self.rl_decision_count = 0
            self.knowledge_decision_count = 0
            self.strategy_decision_count = 0
            self.decision_engine.reset_statistics()
    
    def validate_action(self, act_index: int, action_list: list) -> bool:
        """Validate that action index is in valid range"""
        return 0 <= act_index < len(action_list)
    
    def _save_game_scores(self, victory_num: list):
        """
        保存战绩到 game_scores.json（用于GUI显示）
        
        注意：位置是服务器动态分配的，需要根据实际 myPos 判断队友
        
        Args:
            victory_num: 胜利次数列表 [pos0_wins, pos1_wins, pos2_wins, pos3_wins]
        """
        import json
        from pathlib import Path
        
        score_file = Path("game_scores.json")
        
        # 读取现有战绩
        if score_file.exists():
            try:
                with open(score_file, 'r', encoding='utf-8') as f:
                    scores = json.load(f)
            except:
                scores = {"team_a_wins": 0, "team_b_wins": 0, "total_games": 0, "my_pos": None, "teammate_pos": None}
        else:
            scores = {"team_a_wins": 0, "team_b_wins": 0, "total_games": 0, "my_pos": None, "teammate_pos": None}
        
        # 记录位置信息（用于调试）
        if scores.get("my_pos") is None:
            scores["my_pos"] = self.player_id
            teammate_pos = (self.player_id + 2) % 4
            scores["teammate_pos"] = teammate_pos
            self.logger.info(f"Position info saved: my_pos={self.player_id}, teammate_pos={teammate_pos}")
        
        # 判断获胜队伍
        # 在掼蛋中，0和2是队友，1和3是队友
        # 但实际位置是服务器分配的，所以用 self.player_id 来判断
        if len(victory_num) >= 4:
            my_pos = self.player_id
            teammate_pos = (my_pos + 2) % 4
            opponent1_pos = (my_pos + 1) % 4
            opponent2_pos = (my_pos + 3) % 4
            
            # Team A: yf1_v5 + yf2_v5 (我方)
            team_a_score = victory_num[my_pos] + victory_num[teammate_pos]
            # Team B: 对手
            team_b_score = victory_num[opponent1_pos] + victory_num[opponent2_pos]
            
            # 更新战绩
            if team_a_score > team_b_score:
                scores["team_a_wins"] += 1
                self.logger.info(f"YF Team wins! (pos {my_pos}+{teammate_pos}: {team_a_score} vs pos {opponent1_pos}+{opponent2_pos}: {team_b_score})")
            elif team_b_score > team_a_score:
                scores["team_b_wins"] += 1
                self.logger.info(f"Opponent Team wins! (pos {opponent1_pos}+{opponent2_pos}: {team_b_score} vs pos {my_pos}+{teammate_pos}: {team_a_score})")
            else:
                # 平局，不增加胜场
                self.logger.info(f"Draw! ({team_a_score} vs {team_b_score})")
            
            scores["total_games"] += 1
        
        # 保存到文件
        try:
            with open(score_file, 'w', encoding='utf-8') as f:
                json.dump(scores, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Game scores saved: YF Team {scores['team_a_wins']}/{scores['total_games']}, Opponent Team {scores['team_b_wins']}/{scores['total_games']}")
        except Exception as e:
            self.logger.error(f"Failed to save game scores: {e}")
    
    async def send_action(self, act_index: int):
        """Send action to server using WebSocket manager"""
        response = {"actIndex": act_index}
        await self.ws_manager.send_json(response)
        self.logger.debug(f"Sent action: {act_index}")


async def main():
    """Main entry point"""
    # 设置stdout编码为UTF-8，避免Windows下的编码问题
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    client = YF2_V5_Client(player_id=2)
    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())

