# -*- coding: utf-8 -*-
"""
yf2_v5_stage5 - YiFei AI V5 Stage5 Client (Player 2)
Enhanced version with Stage5 advanced AI capabilities
阶段5升级版本：集成策略模式识别、对手建模、动态策略调整
"""
import asyncio
import json
import sys
import logging
from pathlib import Path
import time  # Add at top if not present

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent)) # Add project root
from decision.hybrid_decision_engine_v5 import HybridDecisionEngineV5
from decision.rl_decision_engine import RLDecisionEngine
from communication.game_recorder import GameRecorder
from communication.websocket_manager import WebSocketManager
from decision.card_power_evaluator import calculate_card_power
from decision.single_card_strategy import single_card_strategy
from decision.bomb_strategy import bomb_strategy
from decision.endgame_strategy import endgame_strategy
from decision.main_decision import main_decision
from decision.card_grouping_strategy import grouping_strategy
from decision.dynamic_grouping_optimizer import DynamicGroupingOptimizer
from decision.bomb_selector import select_bomb_priority, should_use_bomb
from decision.pair_strategy import pair_strategy
from decision.straight_strategy import straight_strategy
from decision.trips_strategy import trips_strategy
from decision.three_with_two_strategy import three_with_two_strategy
from decision.two_trips_strategy import two_trips_strategy
from decision.three_pair_strategy import three_pair_strategy
from communication.utils import combine_handcards, is_inStraight

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

# Add after imports:
DELAY_BEFORE_CONNECT = 9  # seconds, longer than yf1 to ensure position order


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
        
        # Initialize HybridDecisionEngineV5 (V5混合决策引擎)
        self.logger.info("🎯 Initializing HybridDecisionEngineV5")
        config = {"performance_threshold": 1.0}
        self.decision_engine = HybridDecisionEngineV5(player_id, config)
        
        # Initialize Dynamic Grouping Optimizer (动态组牌优化器)
        self.grouping_optimizer = DynamicGroupingOptimizer()
        
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
        self.rl_weight = 0.15  # RL决策权重（进一步降低）
        self.knowledge_weight = 0.25  # 知识库权重（进一步降低）
        self.rule_weight = 0.6  # 规则引擎权重（进一步提高，优先策略建议）
        
        self.hand_cards = [] # Track current hand
        
        # Statistics
        self.decision_count = 0
        self.game_count = 0
        self.rl_decision_count = 0
        self.knowledge_decision_count = 0
        self.strategy_decision_count = 0  # 新增策略决策计数
        
        # 维护连续PASS计数（用于special模式）
        self.pass_num = 0  # 全局连续PASS次数
        self.my_pass_num = 0  # 自己连续PASS次数
        
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
            self.logger.info(f"[yf2_v5] 等待连接延迟 {DELAY_BEFORE_CONNECT} 秒，确保第三个位置...")
            time.sleep(DELAY_BEFORE_CONNECT)
            self.logger.info(f"[yf2_v5] 开始连接 ws://127.0.0.1:23456/game/yf2_v5")
            connected = await self.ws_manager.connect()
            if not connected:
                self.logger.error("Failed to connect to server")
                return
            
            # 设置 websocket 引用以保持向后兼容
            self.websocket = self.ws_manager.websocket
            
            # 显示连接成功和期望位置信息
            print(f"[yf2_v5] 连接成功！期望位置：{self.player_id}号位（实际位置将在游戏开始时由服务器分配）")
            self.logger.info(f"✓ Connected to server. Expected position: {self.player_id} (actual position will be assigned by server at game start)")
            
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
                # 回退到默认决策
                act_index = self.decision_engine.decide(data)
            
            # Get decision details for recording
            decision_context = {
                "myPos": data.get("myPos", self.player_id),
                "curPos": data.get("curPos", -1),
                "greaterPos": data.get("greaterPos", -1),
                "actionList_size": len(action_list),
                "version": "v5",
                "decision_type": "hybrid" if self.use_hybrid_decision else "default_fallback"
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
        
        # 计算队友位置（0和2是队友，1和3是队友）
        teammate_pos = (my_pos + 2) % 4
        
        # 获取连续PASS次数（从data中获取，如果没有则使用维护的值）
        pass_num = data.get("pass_num", self.pass_num)
        my_pass_num = data.get("my_pass_num", self.my_pass_num)
        
        # 获取对手剩余牌数列表（用于判断残局）
        opponent_rest_cards_list = [27, 27, 27]
        if public_info and isinstance(public_info, list):
            for i, info in enumerate(public_info):
                if isinstance(info, dict):
                    rest = info.get("rest", 27)
                    if i < len(opponent_rest_cards_list):
                        opponent_rest_cards_list[i] = rest
        
        return {
            "hand_cards": hand_cards,
            "game_phase": game_phase,
            "opponent_rest_cards": opponent_rest_cards,
            "cur_action": cur_action,
            "greater_action": greater_action,
            "cur_pos": cur_pos,
            "greater_pos": greater_pos,
            "is_active": is_active,
            "cur_rank": data.get("curRank", "2"),
            "my_pos": self.player_id,
            "teammate_pos": teammate_pos,
            "pass_num": pass_num,
            "my_pass_num": my_pass_num,
            "opponent_rest_cards_list": opponent_rest_cards_list
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
        pass_num = game_state.get("pass_num", 0)
        my_pass_num = game_state.get("my_pass_num", 0)
        cur_rank = game_state.get("cur_rank", "2")
        
        if not hand_cards:
            return candidates
        
        # 准备手牌组合信息（用于normal/special模式判断）
        # 获取牌值映射
        rank_map = {'3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'T':10, 'J':11, 'Q':12, 'K':13, 'A':14, '2':15, 'B':16, 'R':17}
        card_val = rank_map.copy()
        card_val[cur_rank] = 15
        
        # 组合手牌，获取天然单张、炸弹、顺子等信息
        sorted_cards, bomb_info = combine_handcards(hand_cards, cur_rank, card_val)
        single_member = sorted_cards.get("Single", [])
        bomb_member = []
        for bomb in sorted_cards.get("Bomb", []):
            bomb_member.extend(bomb)
        straight_member = []
        if sorted_cards.get("Straight"):
            straight_member.extend(sorted_cards["Straight"][0] if sorted_cards["Straight"] else [])
        if sorted_cards.get("StraightFlush"):
            straight_member.extend(sorted_cards["StraightFlush"][0] if sorted_cards["StraightFlush"] else [])
        
        # 获取当前牌型的最大值（用于残局判断）
        greater_action = game_state.get("greater_action", [])
        max_val = 0
        if greater_action and len(greater_action) > 0:
            greater_cards = greater_action[2] if len(greater_action) > 2 and isinstance(greater_action[2], list) else []
            if greater_cards:
                greater_rank = greater_cards[0][1] if len(greater_cards[0]) >= 2 else ""
                max_val = card_val.get(greater_rank, 0)
        
        # 获取下家剩余牌数（用于残局判断）
        opponent_rest_cards_list = game_state.get("opponent_rest_cards_list", [27, 27, 27])
        numofnext = opponent_rest_cards_list[1] if len(opponent_rest_cards_list) > 1 else 27
        
        try:
            # 策略应用顺序（按优先级）：
            # 1. 组牌策略 - 优先考虑组牌效果（减少轮次、减少单牌）
            # 2. 牌力评估 - 评估当前牌力
            # 3. 单牌策略 - 根据牌力给出单牌建议
            # 4. 炸弹策略 - 根据牌力给出炸弹建议
            # 5. 残局策略 - 根据残局情况给出建议
            
            # 1. 组牌策略（优先：减少轮次、减少单牌）
            # 获取剩余牌数信息（用于红心配策略判断）
            my_rest_cards = len(hand_cards)
            opponent_rest_cards = game_state.get("opponent_rest_cards", 27)
            
            # 先计算牌力（用于grouping_strategy中的红心配策略判断）
            power_result = calculate_card_power(
                hand_cards,
                game_phase=game_phase,
                opponent_rest_cards=opponent_rest_cards,
                cur_level_rank=int(game_state["cur_rank"]) if game_state["cur_rank"].isdigit() else 10
            )
            power = power_result['total_power']
            
            # 判断是否是队友出牌（在调用grouping_strategy之前）
            my_pos = game_state.get("my_pos", self.player_id)
            teammate_pos = (my_pos + 2) % 4
            greater_pos = game_state.get("greater_pos", -1)
            is_teammate_action = (greater_pos == teammate_pos)
            
            grouping_sugg = grouping_strategy(
                hand_cards=hand_cards,
                action_list=action_list,
                game_phase=game_phase,
                power=power,  # 使用实际计算的牌力
                cur_rank=game_state.get("cur_rank", "2"),  # 传递级牌信息
                my_rest_cards=my_rest_cards,  # 传递自己剩余牌数
                opponent_rest_cards=opponent_rest_cards,  # 传递对手剩余牌数
                is_teammate_action=is_teammate_action  # 传递是否是队友出牌
            )
            
            # 1.1. 动态组牌优化（在行牌过程中动态调整组牌策略）
            dynamic_grouping_rec = self.grouping_optimizer.get_grouping_recommendation(
                hand_cards=hand_cards,
                action_list=action_list,
                game_state=game_state
            )
            
            # 如果动态优化器建议调整，应用动态优化结果
            if dynamic_grouping_rec:
                best_idx = dynamic_grouping_rec.get('best_action_index', -1)
                dynamic_score = dynamic_grouping_rec.get('score', 0)
                dynamic_reason = dynamic_grouping_rec.get('reason', '')
                grouping_analysis = dynamic_grouping_rec.get('grouping_analysis', {})
                
                # 更新grouping_sugg中的对应建议
                if best_idx >= 0 and best_idx < len(grouping_sugg.get("suggestions", [])):
                    for sugg in grouping_sugg["suggestions"]:
                        if sugg["action_index"] == best_idx:
                            # 应用动态优化评分调整
                            sugg["score"] = dynamic_score
                            if dynamic_reason:
                                sugg["reasons"].insert(0, f"[动态优化] {dynamic_reason}")
                            if grouping_analysis.get('adjustments'):
                                sugg["reasons"].extend([f"[调整] {adj}" for adj in grouping_analysis['adjustments']])
                            break
                
                # 记录动态优化信息
                self.logger.info(f"[动态组牌优化] 建议动作索引: {best_idx}, 评分: {dynamic_score:.2f}, 原因: {dynamic_reason}")
                if grouping_analysis.get('optimization_reasons'):
                    self.logger.info(f"[动态组牌优化] 优化原因: {', '.join(grouping_analysis['optimization_reasons'])}")
            has_bomb = (power_result['details']['bomb_super_high'] + 
                       power_result['details']['bomb_mid'] + 
                       power_result['details']['bomb_normal'] > 0)
            
            # 3. 单牌策略（基于牌力评估结果）
            # 检查手牌中是否有王、级牌、大对子等
            has_king = any('B' in card or 'b' in card for card in hand_cards)  # 王
            has_level_card = any(game_state["cur_rank"] in card for card in hand_cards)  # 级牌
            # 检查是否有Q以上的对子
            rank_map = {'3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'T':10, 'J':11, 'Q':12, 'K':13, 'A':14, '2':15, 'B':16, 'R':17}
            rank_count = {}
            for card in hand_cards:
                if len(card) >= 2:
                    rank_str = card[1] if len(card) == 2 else card[1:2]
                    rank = rank_map.get(rank_str, 0)
                    rank_count[rank] = rank_count.get(rank, 0) + 1
            has_pair_above_q = any(count >= 2 and rank >= 12 for rank, count in rank_count.items())
            
            # 统计单张数量
            single_card_count = sum(1 for count in rank_count.values() if count == 1)
            
            # 统计炸弹数量（从power_result中获取）
            bomb_count = (power_result['details'].get('bomb_super_high', 0) + 
                         power_result['details'].get('bomb_mid', 0) + 
                         power_result['details'].get('bomb_normal', 0))
            
            # 判断是否有顺子或三带二（从action_list中判断）
            has_straight_or_three_with_two = any(
                action[0] in ["Straight", "STRAIGHT", "THREE_WITH_TWO", "ThreeWithTwo"] 
                for action in action_list if action and len(action) > 0
            )
            
            # 判断是否上家出单（顺上家）
            cur_pos = game_state.get("cur_pos", -1)
            greater_pos = game_state.get("greater_pos", -1)
            my_pos = game_state.get("my_pos", self.player_id)
            is_upper_hand = False
            if greater_pos != -1:
                # 上家位置 = (my_pos - 1) % 4
                upper_hand_pos = (my_pos - 1) % 4
                if greater_pos == upper_hand_pos:
                    greater_action = game_state.get("greater_action", [])
                    if greater_action and len(greater_action) > 0:
                        greater_type = greater_action[0] if isinstance(greater_action, list) else str(greater_action)
                        if greater_type in ["Single", "SINGLE"]:
                            is_upper_hand = True
            
            # 判断对手是否不接小单牌（简化：需要历史记录，这里暂时设为False）
            opponent_not_accept_small_single = False  # TODO: 需要从历史记录中判断
            
            # 获取队友剩余牌数（简化：从game_state中获取，如果没有则用默认值）
            teammate_rest_cards = game_state.get("teammate_rest_cards", 27)
            
            # 判断是否主动出牌
            is_active = game_state.get("is_active", False)
            
            # 判断是否双贡（简化：根据游戏阶段判断）
            is_double_tribute = (game_phase == "opening" and opponent_rest_cards >= 25)
            
            # 判断队友是否需要单牌（简化：需要从历史记录中判断）
            teammate_needs_single = False  # TODO: 需要从历史记录中判断
            
            # 判断对手是否需要单牌（简化：需要从历史记录中判断）
            opponent_needs_single = False  # TODO: 需要从历史记录中判断
            
            # 判断是否刚炸过（简化：需要从历史记录中判断）
            just_bombed = False  # TODO: 需要从历史记录中判断
            
            # 判断是否有顺子（从action_list中判断）
            has_straight = any(
                action[0] in ["Straight", "STRAIGHT"] 
                for action in action_list if action and len(action) > 0
            )
            
            # 提取单张牌点列表（用于判断高单/中单/低单）
            single_card_ranks = []
            for card in hand_cards:
                if len(card) >= 2:
                    rank_str = card[1] if len(card) == 2 else card[1:2]
                    if rank_count.get(rank_map.get(rank_str, 0), 0) == 1:  # 是单张
                        single_card_ranks.append(rank_str)
            
            # 获取对手剩余牌数列表（简化：需要从game_state中获取）
            opponent_rest_cards_list = game_state.get("opponent_rest_cards_list", [27, 27, 27])
            
            # 获取队友剩余牌数详情
            teammate_rest_cards_detail = game_state.get("teammate_rest_cards", 27)
            
            # 判断对手是否有单张（简化：需要从历史记录中判断）
            opponent_has_single = False  # TODO: 需要从历史记录中判断
            
            # 获取对手出顺子历史（简化：需要从历史记录中获取）
            opponent_straight_history = game_state.get("opponent_straight_history", [])
            
            # 获取队友出顺子历史（简化：需要从历史记录中获取）
            teammate_straight_history = game_state.get("teammate_straight_history", [])
            
            # 判断头游是否已跑（简化：需要从game_state中获取）
            is_first_place_finished = game_state.get("is_first_place_finished", False)
            
            # 获取自己剩余牌数
            my_rest_cards = len(hand_cards)
            
            # 判断是否报双/报单（简化：需要从game_state中获取）
            is_reported_double = game_state.get("is_reported_double", False)
            is_reported_single = game_state.get("is_reported_single", False)
            
            # 计算天然单张数量和是否有天然单张
            # 天然单张定义：
            # 1. 整幅手牌只有唯一的一张
            # 2. 级牌、小王、大王不要列入天然单张
            cur_rank = game_state.get("cur_rank", "2")
            
            # 筛选天然单张：排除级牌、小王、大王
            natural_singles = []
            for card in single_member:
                # 检查是否是级牌、小王、大王
                if card[-1] == cur_rank or card[-1] == 'B' or card[-1] == 'R':
                    continue
                natural_singles.append(card)
            
            natural_single_count = len(natural_singles)
            has_natural_single = natural_single_count > 0
            
            single_sugg = single_card_strategy(
                game_phase=game_phase,
                power=power,
                opponent_rest_cards=opponent_rest_cards,
                has_bomb=has_bomb,
                has_king=has_king,
                has_level_card=has_level_card,
                has_pair_above_q=has_pair_above_q,
                has_straight=has_straight,
                is_double_tribute=is_double_tribute,
                teammate_needs_single=teammate_needs_single,
                opponent_needs_single=opponent_needs_single,
                just_bombed=just_bombed,
                single_card_count=single_card_count,
                bomb_count=bomb_count,
                has_straight_or_three_with_two=has_straight_or_three_with_two,
                is_upper_hand=is_upper_hand,
                opponent_not_accept_small_single=opponent_not_accept_small_single,
                teammate_rest_cards=teammate_rest_cards,
                is_active=is_active,
                single_card_ranks=single_card_ranks,
                opponent_rest_cards_list=opponent_rest_cards_list,
                teammate_rest_cards_detail=teammate_rest_cards_detail,
                opponent_has_single=opponent_has_single,
                opponent_straight_history=opponent_straight_history,
                teammate_straight_history=teammate_straight_history,
                is_first_place_finished=is_first_place_finished,
                my_rest_cards=my_rest_cards,
                is_reported_double=is_reported_double,
                is_reported_single=is_reported_single,
                has_natural_single=has_natural_single,
                natural_single_count=natural_single_count
            )
            
            # 4. 炸弹策略（基于牌力评估结果，应用完整知识体系）
            # 提取对手动作信息
            greater_action = game_state.get("greater_action", [])
            opponent_action_type = 'none'
            opponent_action_rank = 0
            opponent_action_cards = []
            if greater_action and len(greater_action) > 0:
                opponent_action_type = greater_action[0] if isinstance(greater_action, list) else str(greater_action)
                opponent_action_cards = greater_action[2] if len(greater_action) > 2 and isinstance(greater_action[2], list) else []
                # 计算牌点（简化：根据牌型判断）
                if opponent_action_type in ["Single", "SINGLE"]:
                    if opponent_action_cards:
                        rank_str = opponent_action_cards[0][1] if len(opponent_action_cards[0]) >= 2 else ""
                        rank_map = {'3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'T':10, 'J':11, 'Q':12, 'K':13, 'A':14, '2':15, 'B':16, 'R':17}
                        opponent_action_rank = rank_map.get(rank_str, 0)
                elif opponent_action_type in ["Pair", "PAIR"]:
                    if opponent_action_cards:
                        rank_str = opponent_action_cards[0][1] if len(opponent_action_cards[0]) >= 2 else ""
                        rank_map = {'3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'T':10, 'J':11, 'Q':12, 'K':13, 'A':14, '2':15, 'B':16, 'R':17}
                        opponent_action_rank = rank_map.get(rank_str, 0)
            
            # 判断是否为最后一家
            cur_pos = game_state.get("cur_pos", -1)
            greater_pos = game_state.get("greater_pos", -1)
            my_pos = game_state.get("my_pos", self.player_id)
            is_last_player = (cur_pos == 3) or (greater_pos != -1 and (greater_pos + 1) % 4 == my_pos)
            
            # 判断能否改变牌型（简化：如果对手出的是我方没有的牌型）
            can_change_card_type = opponent_action_type not in ["PASS", "none"] and opponent_action_type not in ["Single", "SINGLE", "Pair", "PAIR"]
            
            # 判断牌型是否明朗（简化：根据游戏阶段）
            card_type_clear = game_phase != "opening"
            
            bomb_sugg = bomb_strategy(
                game_phase=game_phase,
                power=power,
                opponent_rest_cards=opponent_rest_cards,
                opponent_action_type=opponent_action_type.lower() if opponent_action_type else 'none',
                opponent_action_rank=opponent_action_rank,
                opponent_action_cards=opponent_action_cards,
                cur_pos=cur_pos,
                greater_pos=greater_pos,
                my_pos=my_pos,
                teammate_pos=(my_pos + 2) % 4,  # 队友位置
                can_change_card_type=can_change_card_type,
                is_last_player=is_last_player,
                has_clear_next_action=True,  # 简化：假设有明确出牌
                card_type_clear=card_type_clear
            )
            
            # 5. 残局策略（基于牌力评估结果，集成单张技巧残局规则）
            # 获取对手剩余牌数列表（简化：需要从game_state中获取）
            opponent_rest_cards_list = game_state.get("opponent_rest_cards_list", [27, 27, 27])
            
            # 判断头游是否已跑（简化：需要从game_state中获取）
            is_first_place_finished = game_state.get("is_first_place_finished", False)
            
            # 获取自己剩余牌数
            my_rest_cards = len(hand_cards)
            
            # 判断是否报双/报单（简化：需要从game_state中获取）
            is_reported_double = game_state.get("is_reported_double", False)
            is_reported_single = game_state.get("is_reported_single", False)
            
            # 获取下家剩余牌数
            lower_hand_rest_cards = opponent_rest_cards_list[1] if len(opponent_rest_cards_list) > 1 else 27
            
            # 获取级牌
            cur_rank = game_state.get("cur_rank", "2")
            rank_card = f"H{cur_rank}"
            
            # 准备 sorted_cards 和 bomb_info（需要从手牌组合中获取）
            # 由于 calculate_card_power 不返回 sorted_cards，我们需要从 grouping_strategy 或重新计算
            # 简化处理：使用空字典，bomb_selector 会处理这种情况
            sorted_cards_dict = {}
            bomb_info_dict = {}
            # 尝试从 grouping_sugg 中获取（如果有的话）
            # 如果没有，bomb_selector 会根据 action_list 和 hand_cards 进行判断
            
            endgame_sugg = endgame_strategy(
                opponent_rest_cards=opponent_rest_cards,
                power=power,
                has_bomb=has_bomb,
                opponent_rest_cards_list=opponent_rest_cards_list,
                is_reported_double=is_reported_double,
                is_reported_single=is_reported_single,
                is_first_place_finished=is_first_place_finished,
                my_rest_cards=my_rest_cards,
                lower_hand_rest_cards=lower_hand_rest_cards,
                action_list=action_list,  # 传入动作列表，用于判断能否一手出完
                hand_cards=hand_cards,  # 传入手牌，用于判断能否一手出完
                sorted_cards=sorted_cards_dict,  # 传入已组合的手牌
                bomb_info=bomb_info_dict,  # 传入炸弹信息
                rank_card=rank_card  # 传入级牌
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
                
                # 主动出牌时，优先选择优势牌型（顺子、三带二等）
                is_active = game_state.get("is_active", False)
                if is_active and action_type != "PASS":
                    # 检查是否有王或级牌（用于单张策略优先级调整）
                    has_king_or_level = has_king or has_level_card
                    
                    # 主动出牌时，大牌型（顺子、三带二等）大幅加分
                    if action_type in ["Straight", "STRAIGHT", "THREE_WITH_TWO", "ThreeWithTwo"]:
                        score_adjustment += 50.0
                        strategy_reason = "主动出牌：优先大牌型"
                    # 主动出牌时，对子、三张等中等牌型加分
                    elif action_type in ["Pair", "PAIR", "Trips", "TRIPS"]:
                        score_adjustment += 30.0
                        strategy_reason = "主动出牌：中等牌型"
                    # 主动出牌时，单张策略调整
                    elif action_type in ["Single", "SINGLE"]:
                        if action_cards:
                            card_rank = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                            # 有王或级牌保护时，单张不应该减分，而是加分
                            if has_king_or_level:
                                # 有王/级牌保护，单张能回收，加分
                                score_adjustment += 30.0
                                strategy_reason = "主动出牌：有王/级牌保护，单张能回收"
                            # 级牌、大王等本身就有较高价值，加分
                            elif card_rank in ['2', 'B', 'R']:
                                score_adjustment += 25.0
                                strategy_reason = "主动出牌：级牌/大王单张，有价值"
                            # 其他单张，根据牌力情况调整减分幅度
                            elif power >= 7:  # 牌力强时，单张减分幅度降低
                                score_adjustment -= 10.0
                                strategy_reason = "主动出牌：牌力强，单张减分幅度降低"
                            else:
                                score_adjustment -= 20.0
                                strategy_reason = "主动出牌：避免小单张"
                
                # 策略应用顺序（按优先级）：
                # 0. 保护队友机制（最高优先级：当队友已经压制对手时，不应该再次压制）
                # 0.5. 对手剩1张时的紧急处理（极高优先级：禁止出小单张，必须用大牌压制或PASS）
                # 1. 组牌策略（优先：减少轮次、减少单牌）
                # 2. 牌力评估（用于后续策略判断）
                # 3. 单牌策略
                # 4. 炸弹策略
                # 5. 残局策略
                
                # 0. 保护队友机制：核心规则 - 队友出牌时必须PASS
                teammate_pos = game_state.get("teammate_pos", -1)
                cur_pos = game_state.get("cur_pos", -1)
                greater_pos = game_state.get("greater_pos", -1)
                greater_action = game_state.get("greater_action", [])
                
                # 0.5. **核心规则**：对手剩1张时的紧急处理
                # 获取所有对手的剩余牌数
                opponent_rest_cards_list = game_state.get("opponent_rest_cards_list", [27, 27, 27])
                my_pos = game_state.get("my_pos", 0)
                
                # **新增**：用王压制级牌/小王的逻辑
                # 检查对手是否出了级牌或小王，如果有王应该压制
                if greater_action and len(greater_action) > 2:
                    greater_cards = greater_action[2] if isinstance(greater_action[2], list) else []
                    if greater_cards and len(greater_cards) == 1:
                        # 对手出的是单张
                        greater_card = greater_cards[0]
                        greater_rank = greater_card[1] if len(greater_card) >= 2 else ""
                        cur_rank = game_state.get("cur_rank", "2")
                        
                        # 检查手牌中是否有王
                        has_small_king = any('B' in card for card in hand_cards)
                        has_big_king = any('R' in card for card in hand_cards)
                        
                        # 检查当前动作是否是单张
                        if action_type == "Single" or action_type == "SINGLE":
                            if action_card_count == 1 and action_cards:
                                action_card = action_cards[0]
                                action_rank = action_card[1] if len(action_card) >= 2 else ""
                                
                                # 如果对手出的是级牌（cur_rank），应该用小王(B)或大王(R)压制
                                if greater_rank == cur_rank:
                                    if action_rank == "B":  # 用小王压制级牌
                                        score_adjustment += 120.0  # 大幅加分
                                        strategy_reason = f"核心规则：对手出级牌({cur_rank})，用小王(B)压制"
                                    elif action_rank == "R":  # 用大王压制级牌
                                        score_adjustment += 150.0  # 大幅加分
                                        strategy_reason = f"核心规则：对手出级牌({cur_rank})，用大王(R)压制"
                                
                                # 如果对手出的是小王(B)，应该用大王(R)压制
                                elif greater_rank == "B":
                                    if action_rank == "R":  # 用大王压制小王
                                        score_adjustment += 130.0  # 大幅加分
                                        strategy_reason = "核心规则：对手出小王(B)，用大王(R)压制"
                        
                        # **关键修复**：PASS时也要检查，如果有王应该压制
                        if action_type == "PASS":
                            # 如果对手出的是级牌（cur_rank），且有王，应该压制
                            if greater_rank == cur_rank:
                                if has_small_king or has_big_king:
                                    score_adjustment -= 100.0  # 大幅减分，强制要求压制
                                    strategy_reason = f"核心规则：对手出级牌({cur_rank})，有王应该压制，不应PASS"
                            
                            # 如果对手出的是小王(B)，且有大王，应该压制
                            elif greater_rank == "B":
                                if has_big_king:
                                    score_adjustment -= 120.0  # 大幅减分，强制要求压制
                                    strategy_reason = "核心规则：对手出小王(B)，有大王应该压制，不应PASS"
                
                # 检查是否有对手只剩1张牌
                has_opponent_with_1_card = False
                opponent_with_1_card_pos = -1
                for i, rest_cards in enumerate(opponent_rest_cards_list):
                    # 对手位置：不是自己，也不是队友
                    if i != my_pos and i != (my_pos + 2) % 4:
                        if rest_cards == 1:
                            has_opponent_with_1_card = True
                            opponent_with_1_card_pos = i
                            break
                
                # 如果有对手剩1张，且当前动作是单张
                if has_opponent_with_1_card and (action_type == "Single" or action_type == "SINGLE"):
                    if action_card_count == 1 and action_cards:
                        card_rank_str = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                        rank_map = {'3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'T':10, 'J':11, 'Q':12, 'K':13, 'A':14, '2':15, 'B':16, 'R':17}
                        card_rank = rank_map.get(card_rank_str, 0)
                        
                        # **核心规则**：对手剩1张时，禁止出小单张（3-9），必须用大牌（Q/K/A/2/B/R）或PASS
                        if card_rank <= 9:  # 3-9 是小单张
                            score_adjustment -= 200.0  # 极大减分，强制禁止
                            strategy_reason = f"核心规则：对手（位置{opponent_with_1_card_pos}）剩1张，禁止出小单张（{card_rank_str}），必须用大牌压制或PASS"
                        elif card_rank >= 12:  # Q/K/A/2/B/R 是大牌
                            score_adjustment += 100.0  # 大幅加分，鼓励用大牌压制
                            strategy_reason = f"核心规则：对手（位置{opponent_with_1_card_pos}）剩1张，使用大牌（{card_rank_str}）压制"
                
                # 如果有对手剩1张，且当前动作不是PASS也不是大牌单张，建议PASS
                if has_opponent_with_1_card and action_type != "PASS":
                    if action_type == "Single" or action_type == "SINGLE":
                        if action_card_count == 1 and action_cards:
                            card_rank_str = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                            rank_map = {'3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'T':10, 'J':11, 'Q':12, 'K':13, 'A':14, '2':15, 'B':16, 'R':17}
                            card_rank = rank_map.get(card_rank_str, 0)
                            # 如果不是大牌，建议PASS
                            if card_rank < 12:  # 小于Q
                                # PASS动作会得到加分（在后续逻辑中处理）
                                pass
                    # 对于非单张动作，如果不是炸弹，也建议PASS让队友处理
                    elif action_type not in ["Bomb", "BOMB", "StraightFlush"]:
                        score_adjustment -= 50.0  # 减分，建议PASS让队友处理
                        strategy_reason = f"核心规则：对手（位置{opponent_with_1_card_pos}）剩1张，建议PASS让队友处理，避免浪费牌型"
                
                # **核心规则1**：如果当前出牌的是队友（cur_pos == teammate_pos），必须PASS
                if cur_pos == teammate_pos and action_type != "PASS":
                    score_adjustment -= 1000.0  # 极大减分，强制PASS
                    strategy_reason = f"核心规则：队友（位置{cur_pos}）正在出牌，必须PASS，不能压制队友"
                
                # **核心规则2**：如果队友已经出牌（greater_pos == teammate_pos），必须PASS
                # 这是最重要的规则：队友出牌后，无论对手是否PASS，队友都不应该压制队友
                elif greater_pos == teammate_pos and action_type != "PASS":
                    score_adjustment -= 2000.0  # 极大减分，强制PASS（比规则1更严格）
                    strategy_reason = f"核心规则：队友（位置{greater_pos}）已经出牌，必须PASS，绝对不能压制队友"
                
                # **核心规则3**：如果队友已经压制了对手，且对手都PASS了，队友不应该再压制
                # 这个规则已经被规则2覆盖，但保留作为额外检查
                elif greater_pos == teammate_pos and action_type != "PASS":
                    # 检查是否与队友的牌型相同或相似
                    if greater_action and len(greater_action) > 0:
                        greater_type = greater_action[0] if isinstance(greater_action, list) else str(greater_action)
                        # 如果当前动作与队友的牌型相同，大幅减分（不应该重复压制）
                        if action_type == greater_type:
                            score_adjustment -= 500.0  # 大幅减分，避免重复压制
                            strategy_reason = f"保护队友：队友已用{greater_type}压制，不应重复压制"
                        # 如果当前动作是更大的牌型（如炸弹压制顺子），也减分（队友已经压制，不需要再压制）
                        elif action_type in ["Bomb", "BOMB", "StraightFlush"] and greater_type not in ["Bomb", "BOMB", "StraightFlush"]:
                            score_adjustment -= 400.0  # 减分，避免浪费炸弹
                            strategy_reason = f"保护队友：队友已用{greater_type}压制，不应再用炸弹压制"
                
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
                
                # 通用规则：单张在开始阶段和中期，不要越过三级超打
                # 规则：在opening和mid阶段，单张出牌时，不应该超过当前牌型三级以上
                if action_type == "Single" or action_type == "SINGLE":
                    if game_phase in ["opening", "mid"]:
                        # 检查是否有当前牌型（greater_action）
                        greater_action = game_state.get("greater_action", [])
                        if greater_action and len(greater_action) > 0:
                            greater_type = greater_action[0] if isinstance(greater_action, list) else str(greater_action)
                            # 如果当前牌型也是单张，检查是否超过三级
                            if greater_type in ["Single", "SINGLE"]:
                                greater_cards = greater_action[2] if len(greater_action) > 2 and isinstance(greater_action[2], list) else []
                                if greater_cards and action_cards:
                                    # 获取当前牌型和动作牌型的点数
                                    rank_map = {'3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'T':10, 'J':11, 'Q':12, 'K':13, 'A':14, '2':15, 'B':16, 'R':17}
                                    greater_rank_str = greater_cards[0][1] if len(greater_cards[0]) >= 2 else ""
                                    action_rank_str = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                    greater_rank = rank_map.get(greater_rank_str, 0)
                                    action_rank = rank_map.get(action_rank_str, 0)
                                    
                                    # 如果超过三级（action_rank > greater_rank + 3），减分
                                    if action_rank > greater_rank + 3:
                                        score_adjustment -= 40.0  # 大幅减分，避免超打
                                        strategy_reason = f"通用规则：单张在{game_phase}阶段，不应超过三级超打（当前{greater_rank_str}，出{action_rank_str}超过三级）"
                
                # 3. 单牌策略（基于牌力评估结果）
                # 3.0 单张模式判断（normal/special模式，残局大单张）
                if action_type == "Single" or action_type == "SINGLE":
                    if action_cards:
                        action_card = action_cards[0]
                        action_rank = action_card[1] if len(action_card) >= 2 else ""
                        action_rank_val = card_val.get(action_rank, 0)
                        
                        # 判断是否是天然单张
                        # 天然单张定义：
                        # 1. 整幅手牌只有唯一的一张
                        # 2. 级牌、小王、大王不要列入天然单张
                        is_natural_single = action_card in single_member and action_card[-1] != cur_rank and action_card[-1] != 'B' and action_card[-1] != 'R'
                        
                        # 判断是否在炸弹中
                        is_in_bomb = action_card in bomb_member
                        
                        # 判断是否在顺子中
                        is_in_straight = is_inStraight(action, straight_member) if straight_member else False
                        
                        # 判断是否是级牌
                        is_rank_card = action_rank == cur_rank
                        
                        # 3.0.1 Normal模式：优先使用天然单张
                        # **关键修复**：先检查是否在炸弹/顺子中，如果是则大幅减分，避免拆炸弹
                        if is_in_bomb or is_in_straight:
                            # 在炸弹或顺子中，大幅减分（normal模式严格避免拆炸弹/顺子）
                            score_adjustment -= 50.0  # 从-15改为-50，大幅增加拆炸弹的惩罚
                            strategy_reason = "单牌策略：normal模式，严格避免拆炸弹/顺子（拆炸弹代价高）"
                        elif is_natural_single and not is_rank_card:
                            score_adjustment += 40.0  # 天然单张大幅加分
                            strategy_reason = "单牌策略：normal模式，优先使用天然单张"
                        elif action_rank_val >= 15 and not is_rank_card:  # 牌值>=15（2、B、R）且不是级牌
                            score_adjustment += 35.0  # 大牌值单张加分
                            strategy_reason = "单牌策略：normal模式，使用大牌值单张"
                        elif is_rank_card:
                            # 级牌单张，根据情况判断
                            score_adjustment += 20.0  # 级牌单张中等加分
                            strategy_reason = "单牌策略：normal模式，级牌单张"
                        
                        # 3.0.2 Special模式：连续PASS过多时触发（pass_num >= 5 or my_pass_num >= 3）
                        if pass_num >= 5 or my_pass_num >= 3:
                            # special模式：从后往前遍历，不使用炸弹中的牌，不在顺子中
                            if is_in_bomb or is_in_straight:
                                # **关键修复**：special模式中，拆炸弹/顺子的惩罚更严格
                                score_adjustment -= 80.0  # 从-30改为-80，special模式严格禁止拆炸弹
                                strategy_reason = f"单牌策略：special模式（连续PASS {pass_num}/{my_pass_num}次），严格禁止拆炸弹/顺子"
                            elif not is_rank_card:
                                score_adjustment += 50.0  # special模式大幅加分
                                strategy_reason = f"单牌策略：special模式（连续PASS {pass_num}/{my_pass_num}次），不使用炸弹/顺子中的牌"
                        
                        # 3.0.3 残局时优先使用大单张（numofnext <= 4）
                        if numofnext <= 4:
                            # 残局：优先使用 >= max_val 且是天然单张的单张
                            if action_rank_val >= max_val and is_natural_single and not is_rank_card:
                                score_adjustment += 60.0  # 残局大单张大幅加分
                                strategy_reason = f"单牌策略：残局（下家剩{numofnext}张），优先使用大单张（天然单张，>=max_val）"
                            elif action_rank_val >= max_val and not is_in_bomb and not is_in_straight and not is_rank_card:
                                score_adjustment += 45.0  # 残局大单张（非天然但>=max_val）加分
                                strategy_reason = f"单牌策略：残局（下家剩{numofnext}张），使用大单张（>=max_val）"
                            elif action_rank_val >= max_val - 2 and not is_in_bomb and not is_in_straight and not is_rank_card:
                                score_adjustment += 35.0  # 残局接近大单张加分
                                strategy_reason = f"单牌策略：残局（下家剩{numofnext}张），使用接近大单张（>=max_val-2）"
                
                # 主动出牌策略（基于优先级和阈值）
                # 优先级：对子 > 三张 > 三带二 > 顺子 > 三连对/钢板 > 单张
                # cur = [9,10,9,8,10,10,2] 对应 [单张, 三连对1, 三连对2, 三带二, 顺子, 三带二2, 其他]
                if is_active and action_type != "PASS":
                    active_cur = [9, 10, 9, 8, 10, 10, 2]  # 固定阈值
                    
                    # 获取动作的牌值（用于判断是否小于阈值）
                    # 确保action_rank_val已定义，如果没有则使用默认值
                    if 'action_rank_val' not in locals():
                        action_rank_val = 0
                    action_rank_val_for_active = action_rank_val
                    
                    # 1. 对子优先级最高（+80分）
                    if action_type == "Pair" or action_type == "PAIR":
                        score_adjustment += 80.0
                        strategy_reason = "主动出牌策略：对子优先级最高"
                    
                    # 2. 三张优先级第二（+70分）
                    elif action_type == "Trips" or action_type == "TRIPS":
                        score_adjustment += 70.0
                        strategy_reason = "主动出牌策略：三张优先级第二"
                    
                    # 3. 三带二优先级第三（+60分，但需要满足阈值条件）
                    elif action_type == "ThreeWithTwo" or action_type == "THREE_WITH_TWO":
                        if action_rank_val_for_active < active_cur[3]:  # cur[3] = 8
                            score_adjustment += 60.0
                            strategy_reason = "主动出牌策略：三带二优先级第三（满足阈值）"
                        else:
                            score_adjustment += 40.0  # 不满足阈值，降低优先级
                            strategy_reason = "主动出牌策略：三带二（不满足阈值）"
                    
                    # 4. 顺子优先级第四（+50分，但需要满足阈值条件）
                    elif action_type == "Straight" or action_type == "STRAIGHT":
                        if action_rank_val_for_active < active_cur[4]:  # cur[4] = 10
                            score_adjustment += 50.0
                            strategy_reason = "主动出牌策略：顺子优先级第四（满足阈值）"
                        else:
                            score_adjustment += 30.0  # 不满足阈值，降低优先级
                            strategy_reason = "主动出牌策略：顺子（不满足阈值）"
                    
                    # 5. 三连对/钢板优先级第五（+40分）
                    elif action_type == "ThreePair" or action_type == "THREE_PAIR" or action_type == "TwoTrips" or action_type == "TWO_TRIPS":
                        score_adjustment += 40.0
                        strategy_reason = "主动出牌策略：三连对/钢板优先级第五"
                    
                    # 6. 单张优先级最低（+20分，但需要满足阈值条件）
                    # **关键修复**：如果单张在炸弹中，即使满足阈值也不加分，避免拆炸弹
                    elif action_type == "Single" or action_type == "SINGLE":
                        # 检查是否在炸弹中（需要重新获取is_in_bomb，因为可能不在单牌策略的if块内）
                        action_card_for_check = action_cards[0] if action_cards else ""
                        is_in_bomb_for_active = action_card_for_check in bomb_member if action_card_for_check else False
                        
                        if is_in_bomb_for_active:
                            # 拆炸弹的单张，即使满足阈值也不加分，反而减分
                            score_adjustment -= 30.0
                            strategy_reason = "主动出牌策略：单张在炸弹中，避免拆炸弹（即使满足阈值）"
                        elif action_rank_val_for_active < active_cur[0]:  # cur[0] = 9
                            score_adjustment += 20.0
                            strategy_reason = "主动出牌策略：单张优先级最低（满足阈值）"
                        else:
                            score_adjustment -= 30.0  # 不满足阈值，大幅减分
                            strategy_reason = "主动出牌策略：单张（不满足阈值，避免出大单）"
                
                # 根据动作类型应用策略
                if action_type == "PASS":
                    # 单牌策略：不出小单
                    if single_sugg.get("action", "").startswith("不出"):
                        score_adjustment += 30.0
                        strategy_reason = single_sugg.get("reason", "")
                    
                    # **新增**：对手剩1张时，PASS是优先选择
                    opponent_rest_cards_list = game_state.get("opponent_rest_cards_list", [27, 27, 27])
                    my_pos = game_state.get("my_pos", 0)
                    for i, rest_cards in enumerate(opponent_rest_cards_list):
                        if i != my_pos and i != (my_pos + 2) % 4:
                            if rest_cards == 1:
                                score_adjustment += 80.0  # 大幅加分，鼓励PASS让队友处理
                                strategy_reason = f"核心规则：对手（位置{i}）剩1张，PASS让队友处理是优先选择"
                                break
                else:
                    # 非PASS动作
                    
                    # 单牌策略：全面应用所有建议
                    single_action = single_sugg.get("action", "")
                    single_reason = single_sugg.get("reason", "")
                    
                    # 1. 出单相关建议
                    if action_type == "Single" or action_type == "SINGLE":
                        # 核心规则：检查是否拆小对出单（禁止拆小对）
                        if action_card_count == 1 and action_cards:
                            card_rank_str = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                            # rank_map和rank_count在_apply_strategy_suggestions函数中已定义
                            card_rank = rank_map.get(card_rank_str, 0)
                            
                            # **新增**：检查是否拆三张打单张（禁止拆三张）
                            if card_rank in rank_count and rank_count[card_rank] >= 3:
                                # 这是拆三张，大幅减分
                                score_adjustment -= 60.0  # 大幅减分，禁止拆三张
                                strategy_reason = f"核心规则：禁止拆三张（{card_rank_str}）打单张，应保留三张或三带二"
                            
                            # 检查手牌中这个点数是否有对子（说明是拆对）
                            elif card_rank in rank_count and rank_count[card_rank] >= 2:
                                # 这是拆对，检查是否是小对（4以下，即3和4）
                                if card_rank <= 4:  # 3, 4 是小对
                                    score_adjustment -= 50.0  # 大幅减分，禁止拆小对
                                    strategy_reason = f"核心规则：禁止拆小对（对{card_rank_str}）出单，应保留对子"
                            
                            # **新增**：优先使用天然单张（整副手牌只有唯一的一张）
                            # 检查是否是天然单张（不在炸弹、顺子、对子、三张中）
                            is_natural_single = (card_rank in rank_count and rank_count[card_rank] == 1 and 
                                                card_rank_str not in ['2', 'B', 'R'])  # 排除级牌、小王、大王
                            if is_natural_single:
                                score_adjustment += 50.0  # 天然单张大幅加分
                                strategy_reason = f"核心规则：优先使用天然单张（{card_rank_str}），避免拆三张/对子"
                        
                        if "出单" in single_action or "打一张" in single_action:
                            # **核心规则**：对手剩1张时的特殊处理（优先检查）
                            if "出第二小的单" in single_action:
                                # 对手剩1张，主攻/中等牌力：出第二小的单
                                # 需要找到手牌中第二小的单张
                                if action_card_count == 1 and action_cards:
                                    # 获取所有单张的牌值
                                    single_card_values = []
                                    rank_map = {'3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'T':10, 'J':11, 'Q':12, 'K':13, 'A':14, '2':15, 'B':16, 'R':17}
                                    for card in hand_cards:
                                        if len(card) >= 2:
                                            rank_str = card[1] if len(card) == 2 else card[1:2]
                                            if rank_str in rank_map:
                                                # 检查是否是单张（不在对子、三张中）
                                                if rank_count.get(rank_map[rank_str], 0) == 1:
                                                    single_card_values.append((rank_map[rank_str], card))
                                    
                                    if len(single_card_values) >= 2:
                                        # 排序，找到第二小的
                                        single_card_values.sort(key=lambda x: x[0])
                                        second_smallest_rank = single_card_values[1][0]
                                        action_rank = rank_map.get(action_cards[0][1] if len(action_cards[0]) >= 2 else "", 0)
                                        
                                        if action_rank == second_smallest_rank:
                                            score_adjustment += 100.0  # 大幅加分
                                            strategy_reason = f"单牌策略：{single_reason}（出第二小的单{action_cards[0]}）"
                                        else:
                                            score_adjustment -= 50.0  # 减分，不是第二小的
                                            strategy_reason = f"单牌策略：应出第二小的单，当前不是"
                                    else:
                                        # 单张不足2张，无法出第二小的，减分
                                        score_adjustment -= 30.0
                                        strategy_reason = "单牌策略：单张不足，无法出第二小的单"
                            elif "出第二大的单" in single_action:
                                # 对手剩1张，助攻角色：出第二大的单
                                if action_card_count == 1 and action_cards:
                                    # 获取所有单张的牌值
                                    single_card_values = []
                                    rank_map = {'3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'T':10, 'J':11, 'Q':12, 'K':13, 'A':14, '2':15, 'B':16, 'R':17}
                                    for card in hand_cards:
                                        if len(card) >= 2:
                                            rank_str = card[1] if len(card) == 2 else card[1:2]
                                            if rank_str in rank_map:
                                                # 检查是否是单张（不在对子、三张中）
                                                if rank_count.get(rank_map[rank_str], 0) == 1:
                                                    single_card_values.append((rank_map[rank_str], card))
                                    
                                    if len(single_card_values) >= 2:
                                        # 排序，找到第二大的
                                        single_card_values.sort(key=lambda x: x[0], reverse=True)
                                        second_largest_rank = single_card_values[1][0]
                                        action_rank = rank_map.get(action_cards[0][1] if len(action_cards[0]) >= 2 else "", 0)
                                        
                                        if action_rank == second_largest_rank:
                                            score_adjustment += 100.0  # 大幅加分
                                            strategy_reason = f"单牌策略：{single_reason}（出第二大的单{action_cards[0]}）"
                                        else:
                                            score_adjustment -= 50.0  # 减分，不是第二大的
                                            strategy_reason = f"单牌策略：应出第二大的单，当前不是"
                                    else:
                                        # 单张不足2张，无法出第二大的，减分
                                        score_adjustment -= 30.0
                                        strategy_reason = "单牌策略：单张不足，无法出第二大的单"
                            elif "起始出天然单" in single_action:
                                # 起始出天然单（有保护），大幅加分
                                if action_card_count == 1 and action_cards:
                                    # 检查是否是天然单张
                                    card_rank_str = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                    card_rank = rank_map.get(card_rank_str, 0)
                                    is_natural_single = (card_rank in rank_count and rank_count[card_rank] == 1 and 
                                                        card_rank_str not in ['2', 'B', 'R'])
                                    if is_natural_single:
                                        score_adjustment += 50.0  # 天然单张更高分
                                        strategy_reason = "单牌策略：起始出天然单（有保护）"
                                    else:
                                        score_adjustment += 40.0
                                        strategy_reason = "单牌策略：起始出单（有保护）"
                            elif "起始出单" in single_action or "有保护" in single_reason:
                                # 有保护出单，大幅加分
                                score_adjustment += 40.0
                                strategy_reason = "单牌策略：有保护出单"
                            elif "出小单（有王回收）" in single_action:
                                # 有王回收时出小单，加分
                                if action_card_count == 1 and action_cards:
                                    card_rank_str = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                    if card_rank_str in ['3', '4', '5', '6', '7', '8', '9']:
                                        score_adjustment += 45.0
                                        strategy_reason = "单牌策略：有王回收，先出小单再用王回收冲刺"
                            elif "出单（一炸一顺两单）" in single_action:
                                # 一炸一顺两单，先出一单，加分
                                if action_type == "Single" or action_type == "SINGLE":
                                    score_adjustment += 35.0
                                    strategy_reason = "单牌策略：一炸一顺两单，先出一单"
                            elif "顺上家出单" in single_action:
                                # 顺上家出单，加分
                                if action_type == "Single" or action_type == "SINGLE":
                                    score_adjustment += 30.0
                                    strategy_reason = "单牌策略：顺上家出单"
                            elif "出单（进贡大王）" in single_action:
                                # 进贡大王后出单，加分
                                if action_type == "Single" or action_type == "SINGLE":
                                    score_adjustment += 35.0
                                    strategy_reason = "单牌策略：进贡大王后出单"
                            elif "出单（双贡后）" in single_action:
                                # 双贡后出单，加分
                                if action_type == "Single" or action_type == "SINGLE":
                                    score_adjustment += 30.0
                                    strategy_reason = "单牌策略：双贡后出单"
                            elif "出单（单张多）" in single_action:
                                # 单张多时出单，加分
                                if action_type == "Single" or action_type == "SINGLE":
                                    score_adjustment += 30.0
                                    strategy_reason = "单牌策略：单张多，先出单"
                            elif "出天然单（有王/级牌保护）" in single_action:
                                # 有王/级牌保护出天然单，大幅加分
                                if action_card_count == 1 and action_cards:
                                    card_rank_str = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                    card_rank = rank_map.get(card_rank_str, 0)
                                    is_natural_single = (card_rank in rank_count and rank_count[card_rank] == 1 and 
                                                        card_rank_str not in ['2', 'B', 'R'])
                                    if is_natural_single:
                                        score_adjustment += 50.0
                                        strategy_reason = "单牌策略：有王/级牌保护，出天然单"
                                    else:
                                        score_adjustment += 40.0
                                        strategy_reason = "单牌策略：有王/级牌保护，出单"
                            elif "出单（有王/级牌保护）" in single_action:
                                # 有王/级牌保护出单，加分
                                if action_type == "Single" or action_type == "SINGLE":
                                    score_adjustment += 40.0
                                    strategy_reason = "单牌策略：有王/级牌保护，出单"
                            elif "送小单（队友剩一张）" in single_action or "出低单（队友剩一张）" in single_action:
                                # 队友剩一张时送小单，加分
                                if action_card_count == 1 and action_cards:
                                    card_rank_str = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                    if card_rank_str in ['3', '4', '5', '6', '7', '8', '9']:
                                        score_adjustment += 40.0
                                        strategy_reason = "单牌策略：队友剩一张，放心出小单"
                            elif "继续出小单" in single_action:
                                # 对手不接小单，继续出小单压迫，加分
                                if action_card_count == 1 and action_cards:
                                    card_rank_str = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                    if card_rank_str in ['3', '4', '5', '6', '7', '8', '9']:
                                        score_adjustment += 35.0
                                        strategy_reason = "单牌策略：对手不接小单，继续出小单压迫"
                            elif "跟出天然小单" in single_action or "跟出小单" in single_action:
                                # 被动跟牌时跟出小单，加分
                                if action_card_count == 1 and action_cards:
                                    card_rank_str = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                    if card_rank_str in ['3', '4', '5', '6', '7', '8', '9']:
                                        score_adjustment += 25.0
                                        strategy_reason = "单牌策略：被动跟牌，跟出小单"
                            elif "出单防守（大于顺子最大点）" in single_action:
                                # 根据对手顺子历史出单防守，加分
                                if action_type == "Single" or action_type == "SINGLE":
                                    score_adjustment += 30.0
                                    strategy_reason = "单牌策略：根据对手顺子历史，出单防守"
                            elif "送小单（队友顺子）" in single_action:
                                # 根据队友顺子历史送小单，加分
                                if action_card_count == 1 and action_cards:
                                    card_rank_str = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                    if card_rank_str in ['3', '4', '5', '6', '7', '8', '9']:
                                        score_adjustment += 30.0
                                        strategy_reason = "单牌策略：根据队友顺子历史，送小单"
                            elif "主动时不出小单" in single_action:
                                # 主动出牌时不出小单，对小单张减分
                                if action_card_count == 1 and action_cards:
                                    card_rank_str = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                    if card_rank_str in ['3', '4', '5', '6', '7', '8']:
                                        score_adjustment -= 30.0
                                        strategy_reason = "单牌策略：主动出牌时，牌力差，不出小单"
                            elif "不出单（保留牌型组合）" in single_action or "不出单（避免压制小单）" in single_action or "不出单（让队友发挥）" in single_action or "不出单（助攻定位）" in single_action:
                                # 助攻定位不出单，对单张动作减分
                                if action_type == "Single" or action_type == "SINGLE":
                                    score_adjustment -= 30.0
                                    strategy_reason = single_reason if single_reason else "单牌策略：助攻定位，不出单"
                            elif "让队友主导" in single_action or "主动不出单" in single_action:
                                # 让队友主导或主动不出单，对单张动作减分
                                if action_type == "Single" or action_type == "SINGLE":
                                    score_adjustment -= 25.0
                                    strategy_reason = single_reason if single_reason else "单牌策略：让队友主导，不出单"
                            elif "多炸保护" in single_reason:
                                # 多炸保护出单，加分
                                score_adjustment += 35.0
                                strategy_reason = "单牌策略：多炸保护出单"
                            elif "进贡大王" in single_reason:
                                # 进贡大王后出单，加分
                                score_adjustment += 30.0
                                strategy_reason = "单牌策略：进贡后出单"
                            elif "出高单" in single_action:
                                # 高单出牌，对高单张（Q、K、A、2、B、R）加分
                                if action_card_count == 1:
                                    card_rank = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                    if card_rank in ['Q', 'K', 'A', '2', 'B', 'R']:
                                        score_adjustment += 45.0
                                        strategy_reason = "单牌策略：出高单（挡住下家中低单）"
                            elif "出中单" in single_action:
                                # 中单出牌，对中单张（J、T、9）加分
                                if action_card_count == 1:
                                    card_rank = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                    if card_rank in ['J', 'T', '9']:
                                        score_adjustment += 35.0
                                        strategy_reason = "单牌策略：出中单（水闸试探）"
                            elif "出低单" in single_action:
                                # 低单出牌，对小单张（3-8）加分
                                if action_card_count == 1:
                                    card_rank = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                    if card_rank in ['3', '4', '5', '6', '7', '8']:
                                        score_adjustment += 30.0
                                        strategy_reason = "单牌策略：出低单（传牌给对家）"
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
                            elif "卡点出单" in single_action or "发级牌" in single_reason:
                                # 卡点出单，对级牌加分
                                if action_card_count == 1:
                                    card_rank = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                    if card_rank == game_state.get("cur_rank", "2"):
                                        score_adjustment += 50.0
                                        strategy_reason = "单牌策略：卡点出单（发级牌）"
                            elif "报双诱拆" in single_reason:
                                # 报双打单诱拆，加分
                                score_adjustment += 40.0
                                strategy_reason = "单牌策略：报双打单诱拆"
                            elif "倒着打" in single_action:
                                # 出单倒着打，对高单张加分
                                if action_card_count == 1:
                                    card_rank = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                    if card_rank in ['Q', 'K', 'A', '2', 'B', 'R']:
                                        score_adjustment += 35.0
                                        strategy_reason = "单牌策略：出单倒着打（从大往小）"
                            else:
                                # 一般出单建议
                                score_adjustment += 30.0
                                strategy_reason = "单牌策略：出单"
                        elif "不出小单" in single_action or "不出单" in single_action or "不打单" in single_action:
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
                        elif "报单打非单" in single_reason:
                            # 报单不打单，对单张动作减分
                            score_adjustment -= 30.0
                            strategy_reason = "单牌策略：报单不打单"
                    
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
                
                # 4. 炸弹策略（基于牌力评估结果）- 关键策略，防止浪费炸弹
                # 同花顺（StraightFlush）也是炸弹的一种，应该遵守炸弹使用规则
                if action_type == "BOMB" or "BOMB" in str(action_type).upper() or action_type == "Bomb" or action_type == "StraightFlush":
                    # **关键修复**：先检查对手剩余牌数，判断是否应该炸
                    # 获取所有对手的剩余牌数，检查是否有对手剩4张
                    has_opponent_with_4_cards = False
                    opponent_with_4_cards_pos = -1
                    for i, rest_cards in enumerate(opponent_rest_cards_list):
                        # 对手位置：不是自己，也不是队友
                        if i != my_pos and i != (my_pos + 2) % 4:
                            if rest_cards == 4:
                                has_opponent_with_4_cards = True
                                opponent_with_4_cards_pos = i
                                break
                    
                    # **核心规则**：炸不打四（火不打四）- 对手剩4张时，强制禁止用炸弹/同花顺
                    if has_opponent_with_4_cards:
                        score_adjustment -= 400.0  # 极大减分，强制禁止
                        strategy_reason = f"核心规则：炸不打四（对手位置{opponent_with_4_cards_pos}剩4张），强制禁止用炸弹/同花顺"
                    
                    # 检查炸弹策略建议
                    bomb_suggestions = bomb_sugg.get("suggestions", [])
                    should_bomb = False
                    should_not_bomb = False
                    
                    # 先检查是否有"不炸"的建议，优先级更高
                    for sugg in bomb_suggestions:
                        action_text = sugg.get("action", "")
                        reason_text = sugg.get("reason", "")
                        if "不炸" in action_text:
                            should_not_bomb = True
                            strategy_reason = reason_text
                            # 根据不同的"不炸"原因，给予不同的减分
                            if "炸不打四" in action_text:
                                # 炸不打四，特殊处理（如果对手剩4张）
                                if opponent_rest_cards == 4 or has_opponent_with_4_cards:
                                    score_adjustment -= 300.0  # 大幅减分，强制禁止（除非特殊情况）
                                    strategy_reason = f"炸弹策略：炸不打四（敌方剩4张，强制禁止）"
                                else:
                                    score_adjustment -= 200.0
                            elif "牌型不明" in action_text or "走不了" in action_text:
                                score_adjustment -= 180.0  # 牌型不明或走不了，较大减分
                            elif "经济" in action_text or "隐蔽" in action_text or "配合" in action_text:
                                score_adjustment -= 100.0  # 经济、隐蔽、配合等原因，中等减分
                            else:
                                score_adjustment -= 200.0  # 其他不炸原因，大幅减分
                            break
                    
                    # 检查是否有"炸"的建议
                    for sugg in bomb_suggestions:
                        action_text = sugg.get("action", "")
                        reason_text = sugg.get("reason", "")
                        if "炸" in action_text and "不炸" not in action_text:
                            should_bomb = True
                            strategy_reason = reason_text
                            # 根据不同的"炸"原因，给予不同的加分
                            if "剩7" in action_text or "判敌4+3" in action_text:
                                score_adjustment += 60.0  # 剩7要提前炸，大幅加分
                            elif "管压" in action_text or "压制" in action_text:
                                score_adjustment += 50.0  # 管压对手，加分
                            elif "改牌路" in action_text or "控牌" in action_text:
                                score_adjustment += 40.0  # 改牌路或控牌，加分
                            else:
                                score_adjustment += 30.0  # 其他炸的原因，中等加分
                            break
                
                # 4. 炸弹策略（基于牌力评估结果）- 关键策略，防止浪费炸弹
                # 同花顺（StraightFlush）也是炸弹的一种，应该遵守炸弹使用规则
                if action_type == "BOMB" or "BOMB" in str(action_type).upper() or action_type == "Bomb" or action_type == "StraightFlush":
                    # **关键修复**：先检查对手剩余牌数，判断是否应该炸
                    # 获取所有对手的剩余牌数，检查是否有对手剩4张
                    has_opponent_with_4_cards = False
                    opponent_with_4_cards_pos = -1
                    for i, rest_cards in enumerate(opponent_rest_cards_list):
                        # 对手位置：不是自己，也不是队友
                        if i != my_pos and i != (my_pos + 2) % 4:
                            if rest_cards == 4:
                                has_opponent_with_4_cards = True
                                opponent_with_4_cards_pos = i
                                break
                    
                    # **核心规则**：炸不打四（火不打四）- 对手剩4张时，强制禁止用炸弹/同花顺
                    if has_opponent_with_4_cards:
                        score_adjustment -= 400.0  # 极大减分，强制禁止
                        strategy_reason = f"核心规则：炸不打四（对手位置{opponent_with_4_cards_pos}剩4张），强制禁止用炸弹/同花顺"
                    
                    # 4.1 计算牌力等级
                    power_level = "medium"
                    if power < 5:
                        power_level = "weak"
                    elif power >= 7:
                        power_level = "strong"
                    
                    # 4.2 检查是否应该使用炸弹（根据炸弹数量和对手剩余牌数）
                    should_use, use_reason = should_use_bomb(
                        bomb_count=bomb_count,
                        opponent_rest_cards=opponent_rest_cards,
                        game_phase=game_phase,
                        my_rest_cards=my_rest_cards,
                        power=power,
                        my_pos=game_state.get("my_pos", self.player_id),
                        cur_pos=game_state.get("cur_pos", -1),
                        greater_pos=game_state.get("greater_pos", -1),
                        teammate_pos=game_state.get("teammate_pos", -1),
                        power_level=power_level
                    )
                    
                    # 4.2 检查炸弹策略建议
                    bomb_suggestions = bomb_sugg.get("suggestions", [])
                    should_not_bomb = False
                    for sugg in bomb_suggestions:
                        if "炸" in sugg.get("action", "") and "不炸" not in sugg.get("action", ""):
                            score_adjustment += 40.0
                            strategy_reason = sugg.get("reason", "")
                            break
                        elif "不炸" in sugg.get("action", ""):
                            should_not_bomb = True
                            strategy_reason = sugg.get("reason", "")
                    
                    # 4.3 如果没有明确的"应该炸"建议，检查是否不应该炸
                    if not should_not_bomb:
                        # 检查当前牌型：单张、对子、三张等小牌型不值得炸
                        greater_action = game_state.get("greater_action", [])
                        if greater_action and len(greater_action) > 0:
                            greater_type = greater_action[0] if isinstance(greater_action, list) else str(greater_action)
                            greater_cards = greater_action[2] if len(greater_action) > 2 and isinstance(greater_action[2], list) else []
                            greater_card_count = len(greater_cards)
                            
                            # 单张、对子、三张不值得炸（除非残局）
                            if greater_type in ["Single", "SINGLE", "Pair", "PAIR", "Trips", "TRIPS"]:
                                if opponent_rest_cards > 10:  # 非残局
                                    should_not_bomb = True
                                    strategy_reason = f"炸弹策略：{greater_type}不值得炸（非残局）"
                    
                    # 4.4 应用炸弹选择优先级（优先使用不灵活的炸弹）
                    # 收集所有炸弹动作
                    bomb_actions = []
                    for act_idx, act in enumerate(action_list):
                        act_type = act[0] if isinstance(act, list) and len(act) > 0 else str(act)
                        if act_type in ["Bomb", "BOMB", "StraightFlush"]:
                            bomb_actions.append((act_idx, act))
                    
                    # 如果当前动作是炸弹，检查优先级
                    if len(bomb_actions) > 1:
                        # 准备 sorted_cards 和 bomb_info
                        sorted_cards_dict = {}
                        bomb_info_dict = {}
                        if isinstance(power_result, dict):
                            sorted_cards_dict = power_result.get("sorted_cards", {})
                            bomb_info_dict = power_result.get("bomb_info", {})
                        
                        # 获取级牌
                        cur_rank = game_state.get("cur_rank", "2")
                        rank_card = f"H{cur_rank}"
                        
                        # 获取牌值映射
                        rank_map = {'3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'T':10, 'J':11, 'Q':12, 'K':13, 'A':14, '2':15, 'B':16, 'R':17}
                        card_val = rank_map.copy()
                        card_val[cur_rank] = 15
                        
                        # 选择最佳炸弹
                        best_bomb_idx, bomb_reason = select_bomb_priority(
                            bomb_actions, hand_cards, sorted_cards_dict, bomb_info_dict, rank_card, card_val
                        )
                        
                        # 如果当前动作是最佳炸弹，加分；否则减分
                        if best_bomb_idx == idx:
                            score_adjustment += 50.0  # 优先使用不灵活的炸弹
                            strategy_reason = f"炸弹选择：{bomb_reason}"
                        elif best_bomb_idx != -1:
                            score_adjustment -= 30.0  # 不是最佳炸弹，减分
                            strategy_reason = f"炸弹选择：不是最佳炸弹（{bomb_reason}）"
                    
                    # 4.5 如果不应该炸，大幅减分（直接抵消基础分）
                    if should_not_bomb or not should_use:
                        score_adjustment -= 200.0  # 大幅减分，确保不会被选中
                        strategy_reason = f"炸弹策略：{strategy_reason if should_not_bomb else use_reason}"
                
                # 根据牌力调整（增强）
                if power >= 8:
                    # 强牌，非PASS动作大幅加分
                    if action_type != "PASS":
                        score_adjustment += 25.0
                elif power < 5:
                    # 弱牌，PASS或保守动作加分
                    if action_type == "PASS" or action_card_count <= 2:
                        score_adjustment += 20.0
                
                # 4.5. 新增策略：对子、顺子、三张、三带二、钢板、三连对策略
                # 统计各种牌型数量（用于策略判断）
                pair_count = sum(1 for count in rank_count.values() if count >= 2)
                trips_count = sum(1 for count in rank_count.values() if count >= 3)
                pair_ranks = [rank_str for rank_str, rank_val in rank_map.items() 
                             if rank_count.get(rank_val, 0) >= 2]
                
                # 统计动作列表中的牌型
                straight_count = sum(1 for a in action_list if a and len(a) > 0 and a[0] in ["Straight", "STRAIGHT"])
                three_with_two_count = sum(1 for a in action_list if a and len(a) > 0 and a[0] in ["ThreeWithTwo", "THREE_WITH_TWO"])
                two_trips_count = sum(1 for a in action_list if a and len(a) > 0 and a[0] in ["TwoTrips", "TWO_TRIPS"])
                three_pair_count = sum(1 for a in action_list if a and len(a) > 0 and a[0] in ["ThreePair", "THREE_PAIR"])
                
                # 获取动作的牌点（用于策略判断）
                action_rank_str = ""
                if action_cards and len(action_cards) > 0:
                    first_card = action_cards[0]
                    if len(first_card) >= 2:
                        action_rank_str = first_card[1] if len(first_card) == 2 else first_card[1:2]
                
                # 判断是否是队友出牌
                is_teammate_action = (greater_pos == teammate_pos)
                
                # 判断是否有红心配
                cur_rank = game_state.get("cur_rank", "2")
                has_wild_card = any(f"H{cur_rank}" in card for card in hand_cards)
                
                # 4.5.1 对子策略
                if action_type == "Pair" or action_type == "PAIR":
                    pair_sugg = pair_strategy(
                        game_phase=game_phase,
                        power=power,
                        opponent_rest_cards=opponent_rest_cards,
                        opponent_rest_cards_list=opponent_rest_cards_list,
                        teammate_rest_cards=teammate_rest_cards,
                        my_rest_cards=my_rest_cards,
                        is_active=is_active,
                        is_teammate_action=is_teammate_action,
                        greater_pos=greater_pos,
                        my_pos=my_pos,
                        teammate_pos=teammate_pos,
                        action_type=action_type,
                        action_rank=action_rank_str,
                        has_three_with_two=has_straight_or_three_with_two,
                        has_straight=has_straight,
                        pair_count=pair_count,
                        pair_ranks=pair_ranks,
                        can_form_three_pair=False,  # TODO: 需要从组牌策略中获取
                        can_form_straight=False,  # TODO: 需要从组牌策略中获取
                        is_first_place_finished=is_first_place_finished
                    )
                    pair_action = pair_sugg.get("action", "")
                    pair_reason = pair_sugg.get("reason", "")
                    
                    # 根据对子策略建议调整评分
                    if "情况不明对子先行" in pair_action:
                        score_adjustment += 50.0
                        strategy_reason = f"对子策略：{pair_reason}"
                    elif "逢五出对" in pair_action:
                        score_adjustment += 60.0
                        strategy_reason = f"对子策略：{pair_reason}"
                    elif "逢10出对子" in pair_action:
                        score_adjustment += 50.0
                        strategy_reason = f"对子策略：{pair_reason}"
                    elif "顺下中对" in pair_action or "送对子" in pair_action:
                        score_adjustment += 40.0
                        strategy_reason = f"对子策略：{pair_reason}"
                    elif "顶大对子" in pair_action or "封对手对子" in pair_action:
                        score_adjustment += 45.0
                        strategy_reason = f"对子策略：{pair_reason}"
                    elif "让对子" in pair_action:
                        if action_type == "PASS":
                            score_adjustment += 30.0
                            strategy_reason = f"对子策略：{pair_reason}"
                        else:
                            score_adjustment -= 30.0
                            strategy_reason = f"对子策略：{pair_reason}"
                    elif "留对" in pair_action:
                        if action_type != "Pair" and action_type != "PAIR":
                            score_adjustment += 35.0
                            strategy_reason = f"对子策略：{pair_reason}"
                
                # 4.5.2 顺子策略
                elif action_type == "Straight" or action_type == "STRAIGHT":
                    # 获取顺子牌点列表（最小牌点）
                    straight_ranks = []
                    for a in action_list:
                        if a and len(a) > 0 and a[0] in ["Straight", "STRAIGHT"]:
                            if len(a) > 1:
                                straight_ranks.append(str(a[1]))
                    
                    straight_sugg = straight_strategy(
                        game_phase=game_phase,
                        power=power,
                        opponent_rest_cards=opponent_rest_cards,
                        opponent_rest_cards_list=opponent_rest_cards_list,
                        teammate_rest_cards=teammate_rest_cards,
                        my_rest_cards=my_rest_cards,
                        is_active=is_active,
                        is_teammate_action=is_teammate_action,
                        action_type=action_type,
                        action_rank=action_rank_str,
                        straight_count=straight_count,
                        straight_ranks=straight_ranks,
                        has_three_with_two=has_straight_or_three_with_two,
                        has_bomb=has_bomb,
                        single_card_count=single_card_count,
                        can_form_straight=False,  # TODO: 需要从组牌策略中获取
                        is_first_place_finished=is_first_place_finished,
                        has_king=has_king
                    )
                    straight_action = straight_sugg.get("action", "")
                    straight_reason = straight_sugg.get("reason", "")
                    
                    # 根据顺子策略建议调整评分
                    if "牌弱先出顺" in straight_action:
                        score_adjustment += 50.0
                        strategy_reason = f"顺子策略：{straight_reason}"
                    elif "小顺往前凑" in straight_action:
                        score_adjustment += 45.0
                        strategy_reason = f"顺子策略：{straight_reason}"
                    elif "大顺必殿后" in straight_action:
                        score_adjustment += 50.0
                        strategy_reason = f"顺子策略：{straight_reason}"
                    elif "谁打谁收" in straight_action:
                        if is_teammate_action and action_type == "PASS":
                            score_adjustment += 40.0
                            strategy_reason = f"顺子策略：{straight_reason}"
                        elif not is_teammate_action:
                            score_adjustment -= 30.0
                            strategy_reason = f"顺子策略：{straight_reason}"
                    elif "顺子管到头" in straight_action:
                        score_adjustment += 55.0
                        strategy_reason = f"顺子策略：{straight_reason}"
                    elif "七张八张，打顺打夯" in straight_action:
                        score_adjustment += 50.0
                        strategy_reason = f"顺子策略：{straight_reason}"
                    elif "九张十张，不出顺夯" in straight_action:
                        score_adjustment -= 40.0
                        strategy_reason = f"顺子策略：{straight_reason}"
                    elif "组顺生两单" in straight_action:
                        score_adjustment -= 60.0
                        strategy_reason = f"顺子策略：{straight_reason}"
                
                # 4.5.3 三张策略
                elif action_type == "Trips" or action_type == "TRIPS":
                    trips_ranks = [rank_str for rank_str, rank_val in rank_map.items() 
                                 if rank_count.get(rank_val, 0) >= 3]
                    
                    trips_sugg = trips_strategy(
                        game_phase=game_phase,
                        power=power,
                        opponent_rest_cards=opponent_rest_cards,
                        opponent_rest_cards_list=opponent_rest_cards_list,
                        teammate_rest_cards=teammate_rest_cards,
                        my_rest_cards=my_rest_cards,
                        is_active=is_active,
                        is_teammate_action=is_teammate_action,
                        action_type=action_type,
                        action_rank=action_rank_str,
                        has_pair=pair_count > 0,
                        has_straight=has_straight,
                        has_three_with_two=has_straight_or_three_with_two,
                        trips_count=trips_count,
                        trips_ranks=trips_ranks,
                        has_wild_card=has_wild_card
                    )
                    trips_action = trips_sugg.get("action", "")
                    trips_reason = trips_sugg.get("reason", "")
                    
                    # 根据三张策略建议调整评分
                    if "手中就是三张牌型" in trips_action:
                        score_adjustment += 50.0
                        strategy_reason = f"三张策略：{trips_reason}"
                    elif "三张小，对子大" in trips_action:
                        score_adjustment += 45.0
                        strategy_reason = f"三张策略：{trips_reason}"
                    elif "搅局" in trips_action:
                        score_adjustment += 40.0
                        strategy_reason = f"三张策略：{trips_reason}"
                    elif "送队友三张" in trips_action:
                        score_adjustment += 50.0
                        strategy_reason = f"三张策略：{trips_reason}"
                    elif "顶大牌拦截" in trips_action:
                        score_adjustment += 55.0
                        strategy_reason = f"三张策略：{trips_reason}"
                
                # 4.5.4 三带二策略
                elif action_type == "ThreeWithTwo" or action_type == "THREE_WITH_TWO":
                    three_with_two_ranks = []
                    for a in action_list:
                        if a and len(a) > 0 and a[0] in ["ThreeWithTwo", "THREE_WITH_TWO"]:
                            if len(a) > 1:
                                three_with_two_ranks.append(str(a[1]))
                    
                    three_with_two_sugg = three_with_two_strategy(
                        game_phase=game_phase,
                        power=power,
                        opponent_rest_cards=opponent_rest_cards,
                        opponent_rest_cards_list=opponent_rest_cards_list,
                        teammate_rest_cards=teammate_rest_cards,
                        my_rest_cards=my_rest_cards,
                        is_active=is_active,
                        is_teammate_action=is_teammate_action,
                        action_type=action_type,
                        action_rank=action_rank_str,
                        has_straight=has_straight,
                        has_bomb=has_bomb,
                        three_with_two_count=three_with_two_count,
                        three_with_two_ranks=three_with_two_ranks,
                        can_change_card_type=can_change_card_type,
                        is_first_place_finished=is_first_place_finished,
                        has_king=has_king
                    )
                    three_with_two_action = three_with_two_sugg.get("action", "")
                    three_with_two_reason = three_with_two_sugg.get("reason", "")
                    
                    # 根据三带二策略建议调整评分
                    if "有打有收" in three_with_two_action:
                        score_adjustment += 55.0
                        strategy_reason = f"三带二策略：{three_with_two_reason}"
                    elif "相生相克反打" in three_with_two_action:
                        score_adjustment += 50.0
                        strategy_reason = f"三带二策略：{three_with_two_reason}"
                    elif "先出大三带二夯" in three_with_two_action:
                        score_adjustment += 50.0
                        strategy_reason = f"三带二策略：{three_with_two_reason}"
                    elif "反手出三带二" in three_with_two_action:
                        score_adjustment += 45.0
                        strategy_reason = f"三带二策略：{three_with_two_reason}"
                    elif "对手七张八张，出夯" in three_with_two_action:
                        score_adjustment += 50.0
                        strategy_reason = f"三带二策略：{three_with_two_reason}"
                    elif "对手剩余5、9、10张，一般不出夯" in three_with_two_action:
                        score_adjustment -= 40.0
                        strategy_reason = f"三带二策略：{three_with_two_reason}"
                    elif "小夯尽快送" in three_with_two_action or "尽快要送夯" in three_with_two_action:
                        score_adjustment += 50.0
                        strategy_reason = f"三带二策略：{three_with_two_reason}"
                    elif "不接队友夯" in three_with_two_action:
                        if action_type == "PASS":
                            score_adjustment += 35.0
                            strategy_reason = f"三带二策略：{three_with_two_reason}"
                        else:
                            score_adjustment -= 30.0
                            strategy_reason = f"三带二策略：{three_with_two_reason}"
                
                # 4.5.5 钢板策略
                elif action_type == "TwoTrips" or action_type == "TWO_TRIPS":
                    two_trips_ranks = []
                    for a in action_list:
                        if a and len(a) > 0 and a[0] in ["TwoTrips", "TWO_TRIPS"]:
                            if len(a) > 1:
                                two_trips_ranks.append(str(a[1]))
                    
                    two_trips_sugg = two_trips_strategy(
                        game_phase=game_phase,
                        power=power,
                        opponent_rest_cards=opponent_rest_cards,
                        opponent_rest_cards_list=opponent_rest_cards_list,
                        teammate_rest_cards=teammate_rest_cards,
                        my_rest_cards=my_rest_cards,
                        is_active=is_active,
                        is_teammate_action=is_teammate_action,
                        action_type=action_type,
                        action_rank=action_rank_str,
                        has_three_with_two=has_straight_or_three_with_two,
                        has_bomb=has_bomb,
                        two_trips_count=two_trips_count,
                        two_trips_ranks=two_trips_ranks,
                        pair_count=pair_count,
                        trips_count=trips_count,
                        has_wild_card=has_wild_card
                    )
                    two_trips_action = two_trips_sugg.get("action", "")
                    two_trips_reason = two_trips_sugg.get("reason", "")
                    
                    # 根据钢板策略建议调整评分
                    if "牌力中等，小钢板先出" in two_trips_action:
                        score_adjustment += 50.0
                        strategy_reason = f"钢板策略：{two_trips_reason}"
                    elif "牌力很差，小钢板不出" in two_trips_action:
                        score_adjustment -= 40.0
                        strategy_reason = f"钢板策略：{two_trips_reason}"
                    elif "牌力强，小钢板后出" in two_trips_action:
                        score_adjustment += 45.0
                        strategy_reason = f"钢板策略：{two_trips_reason}"
                    elif "拆分小钢板，传牌给队友" in two_trips_action:
                        score_adjustment += 50.0
                        strategy_reason = f"钢板策略：{two_trips_reason}"
                    elif "引炸策略" in two_trips_action:
                        score_adjustment += 55.0
                        strategy_reason = f"钢板策略：{two_trips_reason}"
                    elif "放弃出钢板，组三带二" in two_trips_action:
                        score_adjustment -= 50.0
                        strategy_reason = f"钢板策略：{two_trips_reason}"
                    elif "不接队友钢板" in two_trips_action:
                        if action_type == "PASS":
                            score_adjustment += 35.0
                            strategy_reason = f"钢板策略：{two_trips_reason}"
                        else:
                            score_adjustment -= 30.0
                            strategy_reason = f"钢板策略：{two_trips_reason}"
                
                # 4.5.6 三连对策略
                elif action_type == "ThreePair" or action_type == "THREE_PAIR":
                    three_pair_ranks = []
                    for a in action_list:
                        if a and len(a) > 0 and a[0] in ["ThreePair", "THREE_PAIR"]:
                            if len(a) > 1:
                                three_pair_ranks.append(str(a[1]))
                    
                    three_pair_sugg = three_pair_strategy(
                        game_phase=game_phase,
                        power=power,
                        opponent_rest_cards=opponent_rest_cards,
                        opponent_rest_cards_list=opponent_rest_cards_list,
                        teammate_rest_cards=teammate_rest_cards,
                        my_rest_cards=my_rest_cards,
                        is_active=is_active,
                        is_teammate_action=is_teammate_action,
                        action_type=action_type,
                        action_rank=action_rank_str,
                        has_straight=has_straight,
                        has_bomb=has_bomb,
                        three_pair_count=three_pair_count,
                        three_pair_ranks=three_pair_ranks,
                        has_three_with_two=has_straight_or_three_with_two,
                        has_wild_card=has_wild_card,
                        is_first_place_finished=is_first_place_finished
                    )
                    three_pair_action = three_pair_sugg.get("action", "")
                    three_pair_reason = three_pair_sugg.get("reason", "")
                    
                    # 根据三连对策略建议调整评分
                    if "首引一般不轻易出木板" in three_pair_action:
                        if game_phase == "opening" and is_active:
                            score_adjustment -= 30.0
                            strategy_reason = f"三连对策略：{three_pair_reason}"
                    elif "不接队友木板" in three_pair_action:
                        if is_teammate_action:
                            if action_type == "PASS":
                                score_adjustment += 35.0
                                strategy_reason = f"三连对策略：{three_pair_reason}"
                            else:
                                score_adjustment -= 30.0
                                strategy_reason = f"三连对策略：{three_pair_reason}"
                    elif "木板直接封到顶" in three_pair_action:
                        score_adjustment += 55.0
                        strategy_reason = f"三连对策略：{three_pair_reason}"
                    elif "送队友木板" in three_pair_action:
                        score_adjustment += 50.0
                        strategy_reason = f"三连对策略：{three_pair_reason}"
                    elif "诱骗炸弹" in three_pair_action:
                        score_adjustment += 55.0
                        strategy_reason = f"三连对策略：{three_pair_reason}"
                    elif "利用特殊牌型摆尾" in three_pair_action:
                        score_adjustment += 50.0
                        strategy_reason = f"三连对策略：{three_pair_reason}"
                    elif "故意牌摆偷跑" in three_pair_action:
                        score_adjustment += 55.0
                        strategy_reason = f"三连对策略：{three_pair_reason}"
                
                # 5. 残局策略（最后应用：根据残局情况，集成单张技巧残局规则）
                endgame_action = endgame_sugg.get("action", "")
                endgame_reason = endgame_sugg.get("reason", "")
                
                # **关键修复**：先检查对手剩余牌数，判断是否有对手剩7张
                # 获取所有对手的剩余牌数，检查是否有对手剩7张
                has_opponent_with_7_cards = False
                opponent_with_7_cards_pos = -1
                for i, rest_cards in enumerate(opponent_rest_cards_list):
                    # 对手位置：不是自己，也不是队友
                    if i != my_pos and i != (my_pos + 2) % 4:
                        if rest_cards == 7:
                            has_opponent_with_7_cards = True
                            opponent_with_7_cards_pos = i
                            break
                
                # **核心规则**：对手剩7张时，应该出顺/三带二/炸，不应PASS
                if has_opponent_with_7_cards:
                    if action_type == "Straight" or action_type == "STRAIGHT":
                        score_adjustment += 80.0  # 大幅加分
                        strategy_reason = f"核心规则：对手（位置{opponent_with_7_cards_pos}）剩7张，打顺"
                    elif action_type == "ThreeWithTwo" or action_type == "THREE_WITH_TWO":
                        score_adjustment += 80.0  # 大幅加分
                        strategy_reason = f"核心规则：对手（位置{opponent_with_7_cards_pos}）剩7张，打三带二"
                    elif action_type == "Bomb" or action_type == "BOMB" or action_type == "StraightFlush":
                        score_adjustment += 70.0  # 大幅加分
                        strategy_reason = f"核心规则：对手（位置{opponent_with_7_cards_pos}）剩7张，判敌4+3要提前炸"
                    elif action_type == "PASS":
                        score_adjustment -= 100.0  # 大幅减分，强制要求出牌
                        strategy_reason = f"核心规则：对手（位置{opponent_with_7_cards_pos}）剩7张，不应PASS，应出顺/三带二/炸"
                    elif action_type == "Single" or action_type == "SINGLE":
                        # 对手剩7张，出单张也可以，但不如出顺/三带二/炸
                        score_adjustment += 30.0
                        strategy_reason = f"核心规则：对手（位置{opponent_with_7_cards_pos}）剩7张，出单可接受但不如出顺/三带二/炸"
                
                # 5.0 优先判断：能否一手出完（one_hand函数逻辑）
                if "一手出完" in endgame_action and "one_hand_index" in endgame_sugg:
                    one_hand_index = endgame_sugg.get("one_hand_index", -1)
                    if one_hand_index == idx:
                        # 当前动作可以一手出完，大幅加分
                        score_adjustment += 100.0  # 大幅加分，优先选择
                        strategy_reason = f"残局策略：{endgame_reason}"
                    elif one_hand_index != -1:
                        # 有其他动作可以一手出完，当前动作减分
                        score_adjustment -= 50.0
                        strategy_reason = f"残局策略：有其他动作可以一手出完，当前动作不是最优"
                
                if game_phase == "endgame" or opponent_rest_cards <= 10:
                    # 1. 残局忌给下家顺牌：下家剩一张，不出小单
                    if "忌给下家顺牌" in endgame_reason or "不出小单" in endgame_action:
                        if action_type == "Single" or action_type == "SINGLE":
                            if action_card_count == 1:
                                card_rank = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                if card_rank in ['3', '4', '5', '6', '7', '8', '9', 'T', 'J']:
                                    score_adjustment -= 50.0
                                    strategy_reason = "残局策略：忌给下家顺牌，不出小单"
                    
                    # 2. 报双.须打单诱其拆
                    elif "报双诱拆" in endgame_reason or "打单" in endgame_action:
                        if action_type == "Single" or action_type == "SINGLE":
                            score_adjustment += 40.0
                            strategy_reason = "残局策略：报双打单诱拆"
                    
                    # 3. 报单.只能打非单牌型
                    elif "报单打非单" in endgame_reason or "不打单" in endgame_action:
                        if action_type == "Single" or action_type == "SINGLE":
                            score_adjustment -= 30.0
                            strategy_reason = "残局策略：报单不打单"
                        elif action_type != "PASS":
                            # 非单牌型加分
                            score_adjustment += 35.0
                            strategy_reason = "残局策略：报单打非单牌型"
                    
                    # 4. 出单倒着打：从大往小打
                    elif "倒着打" in endgame_action or "从大往小" in endgame_reason:
                        if action_type == "Single" or action_type == "SINGLE":
                            if action_card_count == 1:
                                card_rank = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                                # 高单张加分，小单张减分
                                if card_rank in ['Q', 'K', 'A', '2', 'B', 'R']:
                                    score_adjustment += 35.0
                                    strategy_reason = "残局策略：出单倒着打（从大往小）"
                                elif card_rank in ['3', '4', '5', '6', '7', '8', '9']:
                                    score_adjustment -= 30.0
                                    strategy_reason = "残局策略：倒着打，不先打最小的"
                    
                    # 6. 残局其他建议（根据对手剩余牌数）
                    elif "不出/不炸" in endgame_action or "不出（火不打四）" in endgame_action:
                        # 火不打四，对非PASS动作减分
                        if action_type != "PASS":
                            score_adjustment -= 30.0
                            strategy_reason = "残局策略：火不打四，观察或放给对家"
                    elif "放过给对家" in endgame_action:
                        # 放过给对家，PASS加分
                        if action_type == "PASS":
                            score_adjustment += 40.0
                            strategy_reason = "残局策略：不能压，放给对家处理"
                        else:
                            score_adjustment -= 20.0
                            strategy_reason = "残局策略：应放过给对家"
                    elif "出两张" in endgame_action or "打两张（对子）" in endgame_action:
                        # 残局出对，对对子动作加分
                        if action_type == "Pair" or action_type == "PAIR":
                            score_adjustment += 35.0
                            strategy_reason = "残局策略：出对试探"
                        elif action_type == "Single" or action_type == "SINGLE":
                            score_adjustment -= 20.0
                            strategy_reason = "残局策略：应出对，不应出单"
                    elif "打一张" in endgame_action or "打一张（单张）" in endgame_action:
                        # 残局出单，对单张动作加分
                        if action_type == "Single" or action_type == "SINGLE":
                            score_adjustment += 35.0
                            strategy_reason = "残局策略：出单"
                        elif action_type != "PASS":
                            score_adjustment -= 20.0
                            strategy_reason = "残局策略：应出单，不应出其他牌型"
                    elif "打顺或三带二" in endgame_action or "打顺" in endgame_action:
                        # 残局出顺或三带二，对相应动作加分
                        if action_type == "Straight" or action_type == "STRAIGHT":
                            score_adjustment += 40.0
                            strategy_reason = "残局策略：出顺"
                        elif action_type == "THREE_WITH_TWO":
                            score_adjustment += 40.0
                            strategy_reason = "残局策略：出三带二"
                        elif action_type == "Bomb" or action_type == "BOMB":
                            # 残局7张时可以考虑炸
                            if opponent_rest_cards == 7:
                                score_adjustment += 30.0
                                strategy_reason = "残局策略：剩7可考虑炸"
                    
                    # 原有残局逻辑
                    else:
                        if action_type != "PASS":
                            score_adjustment += 15.0
                            strategy_reason = "残局策略：残局阶段出牌"
                
                # 为所有动作生成策略评分（即使没有特殊调整）
                # 大幅提高基础评分，让策略建议更有竞争力（不乘以权重，直接使用高分）
                base_score = 200.0  # 大幅提高基础规则评分到200（不乘以权重）
                
                # 主动出牌时，进一步提高基础评分，确保主动出牌优先
                if is_active and action_type != "PASS":
                    base_score += 50.0  # 主动出牌额外加分（提高）
                
                final_score = base_score + score_adjustment + base_strategy_score
                # 确保评分不为负数，至少保持基础评分
                if final_score < 0:
                    final_score = base_score * 0.5  # 即使建议不炸，也保持一定评分
                
                candidates.append((idx, final_score, f"Strategy-{strategy_reason[:20]}"))
                self.strategy_decision_count += 1
                
                # 记录所有策略建议（改为info级别，便于调试）
                if abs(score_adjustment) > 5.0 or "组牌策略" in strategy_reason:
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
        2. 知识库增强决策（HybridDecisionEngineV5）
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
            # 使用V5引擎生成候选（已经包含知识库增强）
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
                # 优先使用服务器发送的最新handCards，如果没有则使用自己维护的
                server_hand_cards = data.get("handCards", [])
                if server_hand_cards:
                    # 服务器发送了最新手牌，使用服务器的（更准确）
                    hand_cards_for_rl = server_hand_cards
                    if len(server_hand_cards) != len(self.hand_cards):
                        self.logger.debug(f"Server handCards ({len(server_hand_cards)}) differs from self.hand_cards ({len(self.hand_cards)}), using server's")
                else:
                    # 服务器没有发送，使用自己维护的
                    hand_cards_for_rl = self.hand_cards
                    self.logger.debug(f"No server handCards, using self.hand_cards ({len(hand_cards_for_rl)})")
                
                data_with_hand = data.copy()
                data_with_hand['handCards'] = hand_cards_for_rl
                
                rl_action = self.rl_engine.decide(data_with_hand)
                if rl_action is not None and 0 <= rl_action < len(action_list):
                    # RL决策评分（使用权重）
                    rl_score = 80.0 * self.rl_weight  # 降低基础RL评分到80
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
        
        # 4. 如果没有候选，使用V5引擎的decide方法
        if not candidates:
            self.logger.warning("No candidates from hybrid decision, using default fallback")
            return self.decision_engine.decide(data)
        
        # 5. 合并同一动作的多个候选（关键修复：避免策略建议被覆盖）
        # 同一动作可能有多个候选（知识库、RL、策略），需要合并取最高分
        merged_candidates = {}
        for idx, score, source in candidates:
            if idx not in merged_candidates:
                merged_candidates[idx] = (score, source)
            else:
                # 如果已有该动作的候选，取评分更高的
                existing_score, existing_source = merged_candidates[idx]
                if score > existing_score:
                    merged_candidates[idx] = (score, source)
                # 如果是策略建议，优先保留（策略评分通常更高）
                elif "Strategy" in source and "Strategy" not in existing_source:
                    merged_candidates[idx] = (score, source)
        
        # 转换为列表并排序
        merged_list = [(idx, score, source) for idx, (score, source) in merged_candidates.items()]
        merged_list.sort(key=lambda x: x[1], reverse=True)
        
        if not merged_list:
            self.logger.warning("No merged candidates, using V4 fallback")
            return self.decision_engine.decide(data)
        
        best_action, best_score, best_source = merged_list[0]
        
        # 记录前3个候选，便于调试
        top_candidates = merged_list[:3] if len(merged_list) >= 3 else merged_list
        self.logger.info(
            f"Hybrid decision: action={best_action}, score={best_score:.1f}, "
            f"source={best_source}, total_candidates={len(merged_list)} (merged from {len(candidates)} raw candidates)"
        )
        if len(top_candidates) > 1:
            self.logger.info(f"Top candidates: {[(idx, f'{score:.1f}', src) for idx, score, src in top_candidates]}")
        
        return best_action
    
    def handle_notification(self, data: dict):
        """Handle notification from server"""
        stage = data.get("stage", "")
        
        if stage == "beginning":
            # 获取初始手牌信息
            hand_cards = data.get("handCards", [])
            self.hand_cards = hand_cards # Store for RL engine
            
            # 调试：检查手牌中是否有重复卡牌
            from collections import Counter
            card_counts = Counter(hand_cards)
            duplicates = {card: count for card, count in card_counts.items() if count > 1}
            if duplicates:
                self.logger.info(f"Initial hand has duplicate cards (normal in 2-deck game): {duplicates}")
            else:
                self.logger.debug(f"Initial hand: {len(hand_cards)} cards, no duplicates")
            my_pos = data.get("myPos", self.player_id)
            
            # 更新实际位置（服务器根据连接顺序分配）
            # 第1个连接 → 位置0，第2个连接 → 位置1，第3个连接 → 位置2，第4个连接 → 位置3
            if my_pos != self.player_id:
                print(f"[yf2_v5] 位置更新：期望位置{self.player_id} → 实际位置{my_pos}号位（服务器根据连接顺序分配）")
                self.logger.info(f"Position updated: {self.player_id} -> {my_pos} (服务器根据连接顺序分配)")
                self.player_id = my_pos
            else:
                # 位置与期望一致，也显示一下
                print(f"[yf2_v5] 我在{my_pos}号位（与期望位置一致）")
            
            # 打印手牌信息
            print(f"游戏开始, 我是{my_pos}号位，手牌：{hand_cards}")
            self.logger.info(f"游戏开始, 我是{my_pos}号位，手牌：{hand_cards}")
            
            # 打印等级信息（用于调试）
            self_rank = data.get("selfRank") or data.get("self_rank") or data.get("myRank") or "?"
            oppo_rank = data.get("oppoRank") or data.get("oppo_rank") or data.get("opponentRank") or "?"
            cur_rank = data.get("curRank") or data.get("cur_rank") or data.get("currentRank") or "?"
            
            # 如果还是 "?"，打印可用的键以便调试
            if self_rank == "?" or oppo_rank == "?" or cur_rank == "?":
                available_keys = [k for k in data.keys() if 'rank' in k.lower() or 'level' in k.lower() or 'grade' in k.lower()]
                if available_keys:
                    print(f"[Debug] 等级信息未找到，但发现相关键: {available_keys}")
                # 打印所有键的前20个（避免输出过长）
                all_keys = list(data.keys())[:20]
                print(f"[Debug] 数据键（前20个）: {all_keys}")
            
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
            
            # 如果是第一个play消息，尝试从restCards中获取所有玩家的手牌
            if not hasattr(self, '_first_play_processed'):
                rest_cards = data.get("restCards", [])
                if rest_cards and self.game_recorder:
                    # 从restCards中提取所有玩家的手牌
                    all_hands = {}
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
                            all_hands[pos] = cards
                    
                    # 更新游戏记录中的all_players_hands
                    if all_hands:
                        # 加载当前游戏数据
                        if hasattr(self.game_recorder, 'current_game') and self.game_recorder.current_game:
                            # 更新all_players_hands
                            self.game_recorder.current_game['all_players_hands'] = all_hands
                            self.logger.info(f"从第一个play消息中获取所有玩家手牌: {list(all_hands.keys())}")
                self._first_play_processed = True
            
            # 更新连续PASS计数（用于special模式）
            if cur_action and len(cur_action) > 0:
                if cur_action[0] == "PASS":
                    # 有人PASS，全局PASS计数+1
                    self.pass_num += 1
                else:
                    # 有人出牌，重置全局PASS计数
                    self.pass_num = 0
                
                # 如果是自己PASS，自己的PASS计数+1
                if cur_pos == self.player_id:
                    if cur_action[0] == "PASS":
                        self.my_pass_num += 1
                    else:
                        self.my_pass_num = 0
            
            # 格式化出牌信息
            if cur_action and len(cur_action) > 0 and cur_action[0] != "PASS":
                action_str = f"{cur_pos}号位打出{cur_action}"
                greater_str = f"最大动作为{greater_pos}号位打出的{greater_action}" if greater_action else ""
                self.logger.info(f"{action_str}， {greater_str}")
                
                # Update my hand cards if I played
                if cur_pos == self.player_id:
                    if len(cur_action) >= 3 and isinstance(cur_action[2], list):
                        played_cards = cur_action[2]
                        old_hand_size = len(self.hand_cards)
                        for card in played_cards:
                            if card in self.hand_cards:
                                self.hand_cards.remove(card)
                            else:
                                self.logger.warning(f"Card {card} not found in hand_cards when trying to remove")
                        new_hand_size = len(self.hand_cards)
                        if old_hand_size != new_hand_size + len(played_cards):
                            self.logger.warning(f"Hand size mismatch: removed {len(played_cards)} cards, hand size changed from {old_hand_size} to {new_hand_size}")
            
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
        
        注意：服务器根据连接顺序来确定座位
        - 第1个连接 → 位置0
        - 第2个连接 → 位置1
        - 第3个连接 → 位置2
        - 第4个连接 → 位置3
        
        组队规则：
        - 第1个连接(位置0)和第3个连接(位置2)自动为一队
        - 第2个连接(位置1)和第4个连接(位置3)自动为一队
        
        标准启动顺序（确保yf1_v5和yf2_v5在同一队）：
        1. yf1_v5.py → 位置0 (Team A)
        2. run_lalala_client3.py → 位置1 (Team B)
        3. yf2_v5.py → 位置2 (Team A)
        4. run_lalala_client4.py → 位置3 (Team B)
        
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
        # 服务器根据连接顺序确定座位：
        # - 如果严格按照标准启动顺序，yf1_v5在位置0，yf2_v5在位置2，它们是队友
        # - 但如果启动顺序不一致，可能不在同一队
        # 解决方案：根据当前client的player_name判断
        # - 如果当前client是yf1_v5或yf2_v5，那么我的位置就是Team A的一部分
        # - 我的队友位置（根据掼蛋规则：0和2是队友，1和3是队友）也是Team A的一部分
        # - 其他两个位置是Team B
        if len(victory_num) >= 4:
            my_pos = self.player_id
            # 根据掼蛋规则：0和2是队友，1和3是队友
            teammate_pos = (my_pos + 2) % 4
            opponent1_pos = (my_pos + 1) % 4
            opponent2_pos = (my_pos + 3) % 4
            
            # 判断当前client是否是我们的AI（yf1_v5或yf2_v5）
            is_yf_ai = self.user_info in ["yf1_v5", "yf2_v5"]
            
            if is_yf_ai:
                # Team A: 当前AI的位置 + 队友位置
                team_a_score = victory_num[my_pos] + victory_num[teammate_pos]
                # Team B: 对手位置
                team_b_score = victory_num[opponent1_pos] + victory_num[opponent2_pos]
            else:
                # 如果当前client不是我们的AI，则反向计算
                # Team A: 对手位置（假设对手是yf1_v5和yf2_v5）
                team_a_score = victory_num[opponent1_pos] + victory_num[opponent2_pos]
                # Team B: 当前位置 + 队友位置
                team_b_score = victory_num[my_pos] + victory_num[teammate_pos]
            
            # 更新战绩
            if team_a_score > team_b_score:
                scores["team_a_wins"] += 1
                self.logger.info(f"YF Team wins! (pos {my_pos}+{teammate_pos}: {team_a_score} vs pos {opponent1_pos}+{opponent2_pos}: {team_b_score})")
            elif team_b_score > team_a_score:
                scores["team_b_wins"] += 1
                self.logger.info(f"Opponent Team wins! (pos {opponent1_pos}+{opponent2_pos}: {team_b_score} vs pos {my_pos}+{teammate_pos}: {team_a_score})")
            else:
                # 平局，不增加胜场
                self.logger.info(f"Draw! (pos {my_pos}+{teammate_pos}: {team_a_score} vs pos {opponent1_pos}+{opponent2_pos}: {team_b_score})")
            
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

