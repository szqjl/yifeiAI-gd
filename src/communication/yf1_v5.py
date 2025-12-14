# -*- coding: utf-8 -*-
"""
yf1_v5_stage5 - YiFei AI V5 Stage5 Client (Player 0)
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

from decision.yf_v5_stage5_decision_engine import YF_V5_Stage5_DecisionEngine
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
from communication.utils import combine_handcards, is_inStraight

# Configure logging
import os
from datetime import datetime

# 创建日志目录
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# 日志文件名：yf1_v5_YYYYMMDD_HHMMSS.log
log_filename = log_dir / f"yf1_v5_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

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

# Add after imports, around line 10-20:
DELAY_BEFORE_CONNECT = 3  # seconds, to ensure sequential connection order


class YF1_V5_Client:
    """
    YiFei AI V5 Client - Player 0
    Enhanced version with:
    - Improved RL integration (智能RL决策)
    - Enhanced knowledge base application (增强知识库应用)
    - Better decision fusion (更好的决策融合)
    """
    
    def __init__(self, player_id=0, use_local_websocket=True):
        self.player_id = player_id
        self.user_info = "yf1_v5"
        self.logger = logging.getLogger(f"yf1_v5")
        
        # 初始化 WebSocket 管理器（从配置文件读取设置）
        self.ws_manager = WebSocketManager(self.user_info, use_local=use_local_websocket)
        self.websocket = None  # 保持向后兼容
        
        # Initialize YF_V5_Stage5_DecisionEngine (阶段5增强决策引擎)
        self.logger.info("🎯 Initializing YF_V5 Stage5 Enhanced Decision Engine")
        self.decision_engine = YF_V5_Stage5_DecisionEngine(player_id)
        
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
        self.game_recorder = GameRecorder(player_id, "yf1_v5")
        
        self.logger.info(f"✓ yf1_v5 initialized (Player {player_id})")
        self.logger.info(f"  - RL Engine: {'Available' if self.rl_available else 'Not Available'}")
        self.logger.info(f"  - Hybrid Decision: {self.use_hybrid_decision}")
        self.logger.info(f"  - Strategy Integration: Enabled (牌力评估、单牌策略、炸弹策略、残局策略)")
    
    async def connect(self):
        """Connect to game server using configured WebSocket manager"""
        try:
            # 使用 WebSocket 管理器连接
            self.logger.info(f"[yf1_v5] 等待连接延迟 {DELAY_BEFORE_CONNECT} 秒，确保第一个位置...")
            time.sleep(DELAY_BEFORE_CONNECT)
            self.logger.info(f"[yf1_v5] 开始连接 ws://127.0.0.1:23456/game/yf1_v5")
            connected = await self.ws_manager.connect()
            if not connected:
                self.logger.error("Failed to connect to server")
                return
            
            # 设置 websocket 引用以保持向后兼容
            self.websocket = self.ws_manager.websocket
            
            # 显示连接成功和期望位置信息
            print(f"[yf1_v5] 连接成功！期望位置：{self.player_id}号位（实际位置将在游戏开始时由服务器分配）")
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
            grouping_sugg = grouping_strategy(
                hand_cards=hand_cards,
                action_list=action_list,
                game_phase=game_phase,
                power=5.0,  # 先用默认牌力，后续会更新
                cur_rank=game_state.get("cur_rank", "2")  # 传递级牌信息
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
                    # 主动出牌时，大牌型（顺子、三带二等）大幅加分
                    if action_type in ["Straight", "STRAIGHT", "THREE_WITH_TWO", "ThreeWithTwo"]:
                        score_adjustment += 50.0
                        strategy_reason = "主动出牌：优先大牌型"
                    # 主动出牌时，对子、三张等中等牌型加分
                    elif action_type in ["Pair", "PAIR", "Trips", "TRIPS"]:
                        score_adjustment += 30.0
                        strategy_reason = "主动出牌：中等牌型"
                    # 主动出牌时，单张减分（除非是级牌、大王等）
                    elif action_type in ["Single", "SINGLE"]:
                        if action_cards:
                            card_rank = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                            if card_rank not in ['2', 'B', 'R']:  # 不是级牌、大王
                                score_adjustment -= 20.0
                                strategy_reason = "主动出牌：避免小单张"
                
                # 策略应用顺序（按优先级）：
                # 0. 保护队友机制（最高优先级：当队友已经压制对手时，不应该再次压制）
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
                
                # 核心规则：如果当前出牌的是队友（cur_pos == teammate_pos），必须PASS
                if cur_pos == teammate_pos and action_type != "PASS":
                    score_adjustment -= 1000.0  # 极大减分，强制PASS
                    strategy_reason = f"核心规则：队友（位置{cur_pos}）正在出牌，必须PASS，不能压制队友"
                
                # 如果队友已经压制了对手（greater_pos == teammate_pos），且当前动作也是压制动作
                elif greater_pos == teammate_pos and action_type != "PASS":
                    # 检查是否与队友的牌型相同或相似
                    if greater_action and len(greater_action) > 0:
                        greater_type = greater_action[0] if isinstance(greater_action, list) else str(greater_action)
                        # 如果当前动作与队友的牌型相同，大幅减分（不应该重复压制）
                        if action_type == greater_type:
                            score_adjustment -= 100.0  # 大幅减分，避免重复压制
                            strategy_reason = f"保护队友：队友已用{greater_type}压制，不应重复压制"
                        # 如果当前动作是更大的牌型（如炸弹压制顺子），也减分（队友已经压制，不需要再压制）
                        elif action_type in ["Bomb", "BOMB", "StraightFlush"] and greater_type not in ["Bomb", "BOMB", "StraightFlush"]:
                            score_adjustment -= 80.0  # 减分，避免浪费炸弹
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
                
                # 主动出牌策略（基于优先级和阈值）
                # 优先级：对子 > 三张 > 三带二 > 顺子 > 三连对/钢板 > 单张
                # cur = [9,10,9,8,10,10,2] 对应 [单张, 三连对1, 三连对2, 三带二, 顺子, 三带二2, 其他]
                if is_active and action_type != "PASS":
                    active_cur = [9, 10, 9, 8, 10, 10, 2]  # 固定阈值
                    
                    # 获取动作的牌值（用于判断是否小于阈值）
                    action_rank_val_for_active = action_rank_val if 'action_rank_val' in locals() else 0
                    if not action_rank_val_for_active and action_cards:
                        action_card = action_cards[0]
                        action_rank_str = action_card[1] if len(action_card) >= 2 else ""
                        action_rank_val_for_active = card_val.get(action_rank_str, 0)
                    
                    # 检查是否有王或级牌（用于单张策略优先级调整）
                    has_king_or_level = has_king or has_level_card
                    
                    # 有王或级牌保护时，单张策略优先级提升
                    if action_type == "Single" or action_type == "SINGLE" and has_king_or_level:
                        # 有王/级牌保护，单张能回收，提升优先级至对子级别
                        score_adjustment += 80.0
                        strategy_reason = "主动出牌策略：有王/级牌保护，单张优先级提升至对子级别"
                    # 1. 对子优先级最高（+80分）
                    elif action_type == "Pair" or action_type == "PAIR":
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
                    elif action_type == "Single" or action_type == "SINGLE":
                        if action_rank_val_for_active < active_cur[0]:  # cur[0] = 9
                            score_adjustment += 20.0
                            strategy_reason = "主动出牌策略：单张优先级最低（满足阈值）"
                        else:
                            score_adjustment -= 30.0  # 不满足阈值，大幅减分
                            strategy_reason = "主动出牌策略：单张（不满足阈值，避免出大单）"
                
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
                        # 核心规则：检查是否拆小对出单（禁止拆小对）
                        if action_card_count == 1 and action_cards:
                            card_rank_str = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                            # rank_map和rank_count在_apply_strategy_suggestions函数中已定义（第400-406行）
                            card_rank = rank_map.get(card_rank_str, 0)
                            # 检查手牌中这个点数是否有对子（说明是拆对）
                            if card_rank in rank_count and rank_count[card_rank] >= 2:
                                # 这是拆对，检查是否是小对（4以下，即3和4）
                                if card_rank <= 4:  # 3, 4 是小对
                                    score_adjustment -= 50.0  # 大幅减分，禁止拆小对
                                    strategy_reason = f"核心规则：禁止拆小对（对{card_rank_str}）出单，应保留对子"
                        
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
                    # 检查炸弹策略建议
                    bomb_suggestions = bomb_sugg.get("suggestions", [])
                    should_bomb = False
                    should_not_bomb = False
                    
                    # 先检查是否有"不炸"的建议，优先级更高
                    for sugg in bomb_suggestions:
                        if "不炸" in sugg.get("action", ""):
                            should_not_bomb = True
                            strategy_reason = sugg.get("reason", "")
                            break
                    
                    # 如果没有"不炸"建议，再检查是否有"炸"的建议
                    if not should_not_bomb:
                        for sugg in bomb_suggestions:
                            if "炸" in sugg.get("action", "") and "不炸" not in sugg.get("action", ""):
                                should_bomb = True
                                score_adjustment += 40.0
                                strategy_reason = sugg.get("reason", "")
                                break
                    
                    # 如果没有明确的建议，检查当前牌型是否值得炸
                    if not should_bomb and not should_not_bomb:
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
                    
                    # 如果不应该炸，大幅减分（直接抵消基础分）
                    if should_not_bomb:
                        score_adjustment -= 200.0  # 大幅减分，确保不会被选中
                        strategy_reason = f"炸弹策略：{strategy_reason}"
                
                # 根据牌力调整（增强）
                if power >= 8:
                    # 强牌，非PASS动作大幅加分
                    if action_type != "PASS":
                        score_adjustment += 25.0
                elif power < 5:
                    # 弱牌，PASS或保守动作加分
                    if action_type == "PASS" or action_card_count <= 2:
                        score_adjustment += 20.0
                
                # 5. 残局策略（最后应用：根据残局情况，集成单张技巧残局规则）
                endgame_action = endgame_sugg.get("action", "")
                endgame_reason = endgame_sugg.get("reason", "")
                
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
                    
                    # 原有残局逻辑
                    else:
                        if action_type != "PASS":
                            score_adjustment += 15.0
                            strategy_reason = "残局策略：残局阶段出牌"
                
                # 1. 组牌策略（优先应用：减少轮次、减少单牌）
                for grouping_item in grouping_sugg.get("suggestions", []):
                    if grouping_item["action_index"] == idx:
                        grouping_score = grouping_item["score"]
                        score_adjustment += grouping_score
                        if grouping_item["reasons"]:
                            strategy_reason = f"组牌策略: {', '.join(grouping_item['reasons'])}"
                        break
                
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
                data_with_hand = data.copy()
                data_with_hand['handCards'] = self.hand_cards
                
                rl_action = self.rl_engine.decide(data_with_hand)
                if rl_action is not None and 0 <= rl_action < len(action_list):
                    # RL决策评分（使用权重，降低RL影响力）
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
            my_pos = data.get("myPos", self.player_id)
            
            # 更新实际位置（服务器根据连接顺序分配）
            # 第1个连接 → 位置0，第2个连接 → 位置1，第3个连接 → 位置2，第4个连接 → 位置3
            if my_pos != self.player_id:
                print(f"[yf1_v5] 位置更新：期望位置{self.player_id} → 实际位置{my_pos}号位（服务器根据连接顺序分配）")
                self.logger.info(f"Position updated: {self.player_id} -> {my_pos} (服务器根据连接顺序分配)")
                old_player_id = self.player_id
                self.player_id = my_pos
                
                # 重新初始化YF_V5阶段5决策引擎（使用新的 player_id）
                self.logger.info(f"Reinitializing YF_V5 Stage5 decision engine with player_id={my_pos}")
                self.decision_engine = YF_V5_Stage5_DecisionEngine(my_pos)
                self.logger.info(f"YF_V5 Stage5 decision engine reinitialized for position {my_pos}")
            else:
                # 位置与期望一致，也显示一下
                print(f"[yf1_v5] 我在{my_pos}号位（与期望位置一致）")
            
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
    
    client = YF1_V5_Client(player_id=0)
    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())

