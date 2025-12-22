# -*- coding: utf-8 -*-
"""
阶段路由器 (Stage Router)
功能：
- 根据游戏状态和剩余牌数，路由到对应的阶段处理器
- 实现5阶段细分路由（开局、中局前期、中局后期、残局前期、残局后期）
- 支持主动/被动出牌路由
- 支持特殊阶段处理（进贡/还贡）
"""

from typing import Dict, Optional
from abc import ABC, abstractmethod


class BasePhaseHandler(ABC):
    """阶段处理器基类（优化：统一接口，减少代码重复）"""
    
    def __init__(self, config: Dict):
        self.config = config
        # 初始化策略引擎（延迟导入，避免循环依赖）
        self._init_strategy_engine()
    
    def _init_strategy_engine(self):
        """初始化策略引擎"""
        try:
            from .strategy_engine import (
                TeammateProtectionStrategy,
                PrioritySystem,
                CardValueSystem
            )
            from .hand_structure_analyzer import HandStructureAnalyzer
            from .optimal_combination_scanner import OptimalCombinationScanner
            self.teammate_protection = TeammateProtectionStrategy(self.config)
            self.priority_system = PrioritySystem(self.config)
            self.card_value_system = CardValueSystem(
                self.config.get("curRank", "2")
            )
            self.hand_analyzer = HandStructureAnalyzer()
            self.combination_scanner = OptimalCombinationScanner()
        except ImportError as e:
            # 如果导入失败，设置为None，后续可以优雅降级
            self.teammate_protection = None
            self.priority_system = None
            self.card_value_system = None
            self.hand_analyzer = None
            self.combination_scanner = None
    
    @abstractmethod
    def handle(self, message: Dict) -> int:
        """处理出牌（子类实现）"""
        pass
    
    def _check_one_hand_complete(self, action_list: list, handcards: list) -> Optional[int]:
        """检查一手出完（所有阶段都可能需要，但实现可能不同）"""
        for i, action in enumerate(action_list):
            if len(action) > 2 and len(action[2]) == len(handcards):
                return i
        return None
    
    def _validate_action_cards(self, action: List, handcards: List) -> bool:
        """
        验证动作中的卡牌是否在手牌中（卡牌一致性检查）
        
        Args:
            action: 动作列表，格式为 [action_type, rank, cards]
            handcards: 当前手牌列表
            
        Returns:
            True: 动作中的所有卡牌都在手牌中
            False: 动作中有卡牌不在手牌中
        """
        import logging
        logger = logging.getLogger("BasePhaseHandler")
        
        if not action or not isinstance(action, list):
            return True  # 无法验证，默认通过
        
        # 提取动作中的卡牌
        action_cards = []
        if len(action) >= 3 and isinstance(action[2], list):
            action_cards = action[2]
        elif len(action) == 2 and isinstance(action[1], list):
            action_cards = action[1]
        elif all(isinstance(card, str) for card in action):
            # 如果action本身就是卡牌列表
            action_cards = action
        
        if not action_cards:
            # 如果没有卡牌（如PASS），直接通过
            return True
        
        # 统计手牌中每张卡牌的数量
        from collections import Counter
        handcard_counts = Counter(handcards)
        action_card_counts = Counter(action_cards)
        
        # 检查动作中的每张卡牌是否都在手牌中
        for card, count in action_card_counts.items():
            if card not in handcard_counts:
                logger.warning(f"卡牌一致性检查失败：动作中的卡牌 {card} 不在手牌中")
                logger.debug(f"动作: {action}, 手牌: {handcards}")
                return False
            if handcard_counts[card] < count:
                logger.warning(f"卡牌一致性检查失败：动作中需要 {count} 张 {card}，但手牌中只有 {handcard_counts[card]} 张")
                logger.debug(f"动作: {action}, 手牌: {handcards}")
                return False
        
        return True
    
    def _build_context(self, message: Dict) -> Dict:
        """构建上下文信息（供策略引擎使用）"""
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        cur_rank = message.get("curRank", "2")
        
        # 计算剩余牌数
        my_remain = len(handcards) if handcards else 27
        cards_left = {}
        opponent_rest_cards_list = []
        teammate_rest_cards = 27
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                rest = info.get("rest", 27)
                cards_left[i] = rest
                if i != my_pos:
                    opponent_rest_cards_list.append(rest)
                    # 队友位置：第1个和第3个为一队，第2个和第4个为一队
                    if (my_pos in [0, 2] and i in [0, 2]) or (my_pos in [1, 3] and i in [1, 3]):
                        teammate_rest_cards = rest
        
        # 判断游戏阶段
        game_phase = "opening"
        if my_remain > 20:
            game_phase = "opening"
        elif my_remain > 15:
            game_phase = "mid_early"
        elif my_remain > 10:
            game_phase = "mid_late"
        elif my_remain > 5:
            game_phase = "endgame_early"
        else:
            game_phase = "endgame_late"
        
        # 判断是否被动出牌
        is_passive = message.get("curAction") is not None and len(message.get("curAction", [])) > 0
        
        return {
            'my_remain': my_remain,
            'cards_left': cards_left,
            'opponent_rest_cards_list': opponent_rest_cards_list,
            'teammate_rest_cards': teammate_rest_cards,
            'cur_rank': cur_rank,
            'my_pos': my_pos,
            'game_phase': game_phase,
            'is_endgame': game_phase in ["endgame_early", "endgame_late"],
            'is_active': not is_passive,
            'handcards': handcards,
            'max_remain_value': max(opponent_rest_cards_list) if opponent_rest_cards_list else 15,
            'next_player_remain': cards_left.get((my_pos + 1) % 4, 27),
            'pass_count': message.get("pass_count", 0),
        }


class StageRouter:
    """阶段路由器（优化：阶段细分路由，提升决策质量和速度）"""
    
    def __init__(self, config: Dict):
        self.config = config
        # 初始化各阶段处理器（优化：直接路由到专门处理器）
        self.handlers = {
            # 开局阶段（剩余牌数 > 20）
            'opening_active': None,  # 将在后续实现
            'opening_passive': None,
            # 中局前期（剩余牌数 15-20）
            'mid_early_active': None,
            'mid_early_passive': None,
            # 中局后期（剩余牌数 10-15）
            'mid_late_active': None,
            'mid_late_passive': None,
            # 残局前期（剩余牌数 5-10）
            'endgame_early_active': None,
            'endgame_early_passive': None,
            # 残局后期（剩余牌数 ≤ 5）
            'endgame_late_active': None,
            'endgame_late_passive': None,
        }
        # 特殊阶段处理器
        self.tribute_handler = None  # 将在后续实现
        self.back_handler = None
    
    def set_handlers(self, handlers: Dict[str, BasePhaseHandler]):
        """设置各阶段处理器"""
        self.handlers.update(handlers)
    
    def set_special_handlers(self, tribute_handler=None, back_handler=None):
        """设置特殊阶段处理器"""
        if tribute_handler:
            self.tribute_handler = tribute_handler
        if back_handler:
            self.back_handler = back_handler
    
    def route(self, message: Dict) -> int:
        """路由到对应阶段处理器（优化：直接路由，无额外判断）"""
        stage = message.get("stage", "play")
        handcards = message.get("handCards", [])
        my_remain = len(handcards) if handcards else 0
        
        # 特殊阶段处理（进贡/还贡）
        if stage == "tribute":
            if self.tribute_handler:
                return self.tribute_handler.handle(message)
            return 0
        elif stage == "back":
            if self.back_handler:
                return self.back_handler.handle(message)
            return 0
        
        # 打牌阶段：根据剩余牌数和出牌类型直接路由
        if stage == "play":
            # 判断游戏阶段（优化：在路由层直接判断）
            game_phase = self._get_game_phase(my_remain)
            
            # 判断主动/被动出牌
            is_passive = self._is_passive_play(message)
            
            # 直接路由到专门处理器（优化：一步到位，无额外判断）
            handler_key = f"{game_phase}_{'passive' if is_passive else 'active'}"
            handler = self.handlers.get(handler_key)
            
            if handler:
                return handler.handle(message)
        
        return 0
    
    def _get_game_phase(self, my_remain: int) -> str:
        """获取游戏阶段（优化：细分为5个阶段）"""
        if my_remain > 20:
            return "opening"        # 开局
        elif my_remain > 15:
            return "mid_early"      # 中局前期
        elif my_remain > 10:
            return "mid_late"       # 中局后期
        elif my_remain > 5:
            return "endgame_early"  # 残局前期
        else:
            return "endgame_late"   # 残局后期
    
    def _is_passive_play(self, message: Dict) -> bool:
        """判断是否为被动出牌"""
        cur_action = message.get("curAction")
        cur_pos = message.get("curPos", -1)
        greater_pos = message.get("greaterPos", -1)
        
        # 如果curAction是None或空，肯定是主动出牌
        if not cur_action:
            return False
        
        # 如果curAction是字符串，尝试解析
        if isinstance(cur_action, str):
            try:
                import ast
                cur_action = ast.literal_eval(cur_action)
            except (ValueError, SyntaxError):
                # 解析失败，可能是主动出牌
                return False
        
        # 如果curAction是列表，检查第一个元素
        if isinstance(cur_action, list) and len(cur_action) > 0:
            first_elem = cur_action[0]
            # 如果第一个元素是None或"PASS"，可能是主动出牌
            if first_elem is None or first_elem == "PASS":
                # 进一步检查：如果curPos=-1或greaterPos=-1，说明是主动出牌
                if cur_pos == -1 or greater_pos == -1:
                    return False
                # 如果actionList的第一个动作不是PASS，说明是主动出牌
                action_list = message.get("actionList", [])
                if action_list and len(action_list) > 0:
                    first_action = action_list[0]
                    if isinstance(first_action, list) and len(first_action) > 0:
                        if first_action[0] != "PASS":
                            return False
            # 如果第一个元素是有效的动作类型，说明是被动出牌
            elif isinstance(first_elem, str) and first_elem in ["Single", "Pair", "Trips", "ThreeWithTwo", "ThreePair", "TwoTrips", "Straight", "StraightFlush", "Bomb"]:
                return True
        
        # 默认：如果curPos != -1 且 greaterPos != -1，说明是被动出牌
        return cur_pos != -1 and greater_pos != -1

