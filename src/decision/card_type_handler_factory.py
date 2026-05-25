# -*- coding: utf-8 -*-
"""
牌型处理器工厂 (Card Type Handler Factory)
功能：
- 为每种牌型创建专门的处理方法
- 支持策略注入
- 统一接口，易于扩展
"""

from typing import Dict, Optional
from abc import ABC, abstractmethod
import sys
from pathlib import Path

# 将 src 目录添加到系统路径
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from game_logic.guandan_constants import DEFAULT_REST_CARDS
except ImportError:
    DEFAULT_REST_CARDS = 27

from game_logic.enhanced_state import EnhancedGameStateManager
from game_logic.hand_combiner import HandCombiner
from .hand_structure_analyzer import HandStructureAnalyzer


class CardTypeHandler(ABC):
    """牌型处理器基类（提升：统一接口，支持策略注入）"""
    
    def __init__(self, config: Dict):
        self.config = config
        # ⭐ 初始化策略引擎（延迟导入，避免循环依赖）
        self._init_strategy_engine()
    
    def _init_strategy_engine(self):
        """初始化策略引擎"""
        try:
            from .strategy_engine import (
                TeammateProtectionStrategy,
                PrioritySystem,
                CardValueSystem
            )
            self.teammate_protection = TeammateProtectionStrategy(self.config)
            self.priority_system = PrioritySystem(self.config)
            self.card_value_system = CardValueSystem(
                self.config.get("curRank", "2")
            )
            self.hand_analyzer = HandStructureAnalyzer()
        except ImportError as e:
            # 如果导入失败，设置为None，后续可以优雅降级
            self.teammate_protection = None
            self.priority_system = None
            self.card_value_system = None
            self.hand_analyzer = None
    
    @abstractmethod
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理被动出牌"""
        pass
    
    def handle_active(self, message: Dict, context: Dict) -> int:
        """处理主动出牌（可选）"""
        pass
    
    def analyze_structure(self, handcards: list, rank: str) -> Dict:
        """分析手牌结构（提升：统一的手牌分析接口）"""
        if self.hand_analyzer:
            return self.hand_analyzer.analyze(handcards, rank)
        return {}


class SingleHandler(CardTypeHandler):
    """单张处理器（学习lalala，但增强）"""
    
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理单张被动出牌（提升：更完善的逻辑，利用扫描结果）"""
        action_list = message.get("actionList", [])
        cur_action = message.get("curAction")
        
        if not action_list or not cur_action:
            return 0
        
        # ⭐ 1. 手牌结构分析（lalala有，YF增强：更详细）
        hand_structure = {}
        if self.hand_analyzer:
            handcards = message.get("handCards", [])
            rank = message.get("curRank", "2")
            hand_structure = self.hand_analyzer.analyze(handcards, rank)
        
        # ⭐ 2. 队友保护判断（lalala有，YF增强：多策略）
        if self.teammate_protection:
            protection_action = self.teammate_protection.get_protection_action(message, context)
            if protection_action is not None:
                return protection_action
        
        # ⭐ 3. 利用扫描结果优化候选动作（新增：优先多余单张，避免破坏受保护组合）
        candidates = self._get_candidates(message)
        filtered_candidates = self._filter_by_scan_result(candidates, context)
        
        # ⭐ 4. 优先级选择（lalala有，YF提升：动态优先级）
        if self.priority_system and filtered_candidates:
            return self.priority_system.select(filtered_candidates, hand_structure, context)
        
        # 降级方案：选择第一个非PASS动作
        for i, action in enumerate(action_list):
            if action[0] != "PASS" and action[0] == "Single":
                return i
        
        return 0
    
    def _filter_by_scan_result(self, candidates: List, context: Dict) -> List:
        """
        根据扫描结果过滤候选动作（新增：优先多余单张，避免破坏受保护组合）
        
        Args:
            candidates: 候选动作列表
            context: 上下文信息（包含扫描结果）
            
        Returns:
            过滤后的候选动作列表（优先多余单张）
        """
        if not candidates:
            return candidates
        
        scan_result = context.get('scan_result', {})
        excess_singles = context.get('excess_singles', [])
        protected_combinations = scan_result.get('protected_combinations', [])
        
        # 如果没有扫描结果，返回原候选列表
        if not excess_singles and not protected_combinations:
            return candidates
        
        # 提取动作中的卡牌
        def get_action_cards(action):
            """从动作中提取卡牌列表"""
            if isinstance(action, list) and len(action) > 2:
                if isinstance(action[2], list):
                    return action[2]
            return []
        
        # 检查动作是否会破坏受保护组合
        def would_break_protected(action_cards, protected_combinations):
            """检查动作是否会破坏受保护组合"""
            if not action_cards or not protected_combinations:
                return False
            action_cards_set = set(action_cards)
            for protected in protected_combinations:
                protected_set = set(protected)
                # 如果动作中的卡牌与受保护组合有交集，可能破坏组合
                if action_cards_set & protected_set:
                    # 检查是否是完整使用（不是破坏）
                    if not action_cards_set.issubset(protected_set):
                        return True
            return False
        
        # 分离多余单张和其他动作
        excess_candidates = []
        other_candidates = []
        
        for candidate in candidates:
            action_cards = get_action_cards(candidate)
            if not action_cards:
                other_candidates.append(candidate)
                continue
            
            # 检查是否是多余单张
            is_excess_single = len(action_cards) == 1 and action_cards[0] in excess_singles
            
            # 检查是否会破坏受保护组合
            would_break = would_break_protected(action_cards, protected_combinations)
            
            if is_excess_single and not would_break:
                excess_candidates.append(candidate)
            elif not would_break:
                other_candidates.append(candidate)
            # 如果会破坏受保护组合，跳过该候选动作
        
        # 优先返回多余单张，然后是其他不破坏组合的动作
        return excess_candidates + other_candidates
    
    def _get_candidates(self, message: Dict) -> list:
        """获取候选动作"""
        action_list = message.get("actionList", [])
        return [a for a in action_list if a[0] == "Single" and a[0] != "PASS"]


class PairHandler(CardTypeHandler):
    """对子处理器"""
    
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理对子被动出牌（提升：集成策略引擎，利用扫描结果）"""
        action_list = message.get("actionList", [])
        cur_action = message.get("curAction")
        
        if not action_list or not cur_action:
            return 0
        
        # ⭐ 1. 手牌结构分析
        hand_structure = {}
        if self.hand_analyzer:
            handcards = message.get("handCards", [])
            rank = message.get("curRank", "2")
            hand_structure = self.hand_analyzer.analyze(handcards, rank)
        
        # ⭐ 2. 队友保护判断
        if self.teammate_protection:
            protection_action = self.teammate_protection.get_protection_action(message, context)
            if protection_action is not None:
                return protection_action
        
        # ⭐ 3. 利用扫描结果优化候选动作（新增：避免破坏受保护组合）
        candidates = self._get_candidates(message)
        filtered_candidates = self._filter_by_scan_result(candidates, context)
        
        # ⭐ 4. 优先级选择
        if self.priority_system and filtered_candidates:
            return self.priority_system.select(filtered_candidates, hand_structure, context)
        
        # 降级方案：选择第一个非PASS动作
        for i, action in enumerate(action_list):
            if action[0] != "PASS" and action[0] == "Pair":
                return i
        return 0
    
    def _filter_by_scan_result(self, candidates: List, context: Dict) -> List:
        """根据扫描结果过滤候选动作（复用SingleHandler的逻辑）"""
        return SingleHandler._filter_by_scan_result(self, candidates, context)
    
    def _get_candidates(self, message: Dict) -> list:
        """获取候选动作"""
        action_list = message.get("actionList", [])
        return [a for a in action_list if a[0] == "Pair" and a[0] != "PASS"]


class TripsHandler(CardTypeHandler):
    """三张处理器"""
    
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理三张被动出牌（提升：集成策略引擎）"""
        action_list = message.get("actionList", [])
        cur_action = message.get("curAction")
        
        if not action_list or not cur_action:
            return 0
        
        # ⭐ 1. 手牌结构分析
        hand_structure = {}
        if self.hand_analyzer:
            handcards = message.get("handCards", [])
            rank = message.get("curRank", "2")
            hand_structure = self.hand_analyzer.analyze(handcards, rank)
        
        # ⭐ 2. 队友保护判断
        if self.teammate_protection:
            protection_action = self.teammate_protection.get_protection_action(message, context)
            if protection_action is not None:
                return protection_action
        
        # ⭐ 3. 优先级选择
        candidates = self._get_candidates(message)
        if self.priority_system and candidates:
            return self.priority_system.select(candidates, hand_structure, context)
        
        # 降级方案：选择第一个非PASS动作
        for i, action in enumerate(action_list):
            if action[0] != "PASS" and action[0] == "Trips":
                return i
        return 0
    
    def _get_candidates(self, message: Dict) -> list:
        """获取候选动作"""
        action_list = message.get("actionList", [])
        return [a for a in action_list if a[0] == "Trips" and a[0] != "PASS"]


class ThreeWithTwoHandler(CardTypeHandler):
    """三带二处理器"""
    
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理三带二被动出牌（提升：集成策略引擎，优先选择复杂牌型）"""
        action_list = message.get("actionList", [])
        cur_action = message.get("curAction")
        
        if not action_list or not cur_action:
            return 0
        
        # ⭐ 1. 手牌结构分析
        hand_structure = {}
        if self.hand_analyzer:
            handcards = message.get("handCards", [])
            rank = message.get("curRank", "2")
            hand_structure = self.hand_analyzer.analyze(handcards, rank)
        
        # ⭐ 2. 队友保护判断
        if self.teammate_protection:
            protection_action = self.teammate_protection.get_protection_action(message, context)
            if protection_action is not None:
                return protection_action
        
        # ⭐ 3. 利用扫描结果优化候选动作（新增：优先复杂牌型）
        candidates = self._get_candidates(message)
        filtered_candidates = self._filter_by_scan_result(candidates, context, card_type='ThreeWithTwo')
        
        # ⭐ 4. 优先级选择
        if self.priority_system and filtered_candidates:
            return self.priority_system.select(filtered_candidates, hand_structure, context)
        
        # 降级方案：选择第一个非PASS动作
        for i, action in enumerate(action_list):
            if action[0] != "PASS" and action[0] == "ThreeWithTwo":
                return i
        return 0
    
    def _filter_by_scan_result(self, candidates: List, context: Dict, card_type: str = None) -> List:
        """根据扫描结果过滤候选动作（优先复杂牌型，复用TwoTripsHandler的逻辑）"""
        return TwoTripsHandler._filter_by_scan_result(self, candidates, context, card_type)
    
    def _get_candidates(self, message: Dict) -> list:
        """获取候选动作"""
        action_list = message.get("actionList", [])
        return [a for a in action_list if a[0] == "ThreeWithTwo" and a[0] != "PASS"]


class ThreePairHandler(CardTypeHandler):
    """三连对处理器"""
    
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理三连对被动出牌（提升：集成策略引擎，优先选择复杂牌型）"""
        action_list = message.get("actionList", [])
        cur_action = message.get("curAction")
        
        if not action_list or not cur_action:
            return 0
        
        # ⭐ 1. 手牌结构分析
        hand_structure = {}
        if self.hand_analyzer:
            handcards = message.get("handCards", [])
            rank = message.get("curRank", "2")
            hand_structure = self.hand_analyzer.analyze(handcards, rank)
        
        # ⭐ 2. 队友保护判断
        if self.teammate_protection:
            protection_action = self.teammate_protection.get_protection_action(message, context)
            if protection_action is not None:
                return protection_action
        
        # ⭐ 3. 利用扫描结果优化候选动作（新增：优先复杂牌型）
        candidates = self._get_candidates(message)
        filtered_candidates = self._filter_by_scan_result(candidates, context, card_type='ThreePair')
        
        # ⭐ 4. 优先级选择
        if self.priority_system and filtered_candidates:
            return self.priority_system.select(filtered_candidates, hand_structure, context)
        
        # 降级方案：选择第一个非PASS动作
        for i, action in enumerate(action_list):
            if action[0] != "PASS" and action[0] == "ThreePair":
                return i
        return 0
    
    def _filter_by_scan_result(self, candidates: List, context: Dict, card_type: str = None) -> List:
        """根据扫描结果过滤候选动作（优先复杂牌型，复用TwoTripsHandler的逻辑）"""
        return TwoTripsHandler._filter_by_scan_result(self, candidates, context, card_type)
    
    def _get_candidates(self, message: Dict) -> list:
        """获取候选动作"""
        action_list = message.get("actionList", [])
        return [a for a in action_list if a[0] == "ThreePair" and a[0] != "PASS"]


class StraightHandler(CardTypeHandler):
    """顺子处理器"""
    
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理顺子被动出牌（提升：集成策略引擎）"""
        action_list = message.get("actionList", [])
        cur_action = message.get("curAction")
        
        if not action_list or not cur_action:
            return 0
        
        # ⭐ 1. 手牌结构分析
        hand_structure = {}
        if self.hand_analyzer:
            handcards = message.get("handCards", [])
            rank = message.get("curRank", "2")
            hand_structure = self.hand_analyzer.analyze(handcards, rank)
        
        # ⭐ 2. 队友保护判断
        if self.teammate_protection:
            protection_action = self.teammate_protection.get_protection_action(message, context)
            if protection_action is not None:
                return protection_action
        
        # ⭐ 3. 优先级选择
        candidates = self._get_candidates(message)
        if self.priority_system and candidates:
            return self.priority_system.select(candidates, hand_structure, context)
        
        # 降级方案：选择第一个非PASS动作
        for i, action in enumerate(action_list):
            if action[0] != "PASS" and action[0] == "Straight":
                return i
        return 0
    
    def _get_candidates(self, message: Dict) -> list:
        """获取候选动作"""
        action_list = message.get("actionList", [])
        return [a for a in action_list if a[0] == "Straight" and a[0] != "PASS"]


class TwoTripsHandler(CardTypeHandler):
    """钢板处理器"""
    
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理钢板被动出牌（提升：集成策略引擎，优先选择复杂牌型）"""
        action_list = message.get("actionList", [])
        cur_action = message.get("curAction")
        
        if not action_list or not cur_action:
            return 0
        
        # ⭐ 1. 手牌结构分析
        hand_structure = {}
        if self.hand_analyzer:
            handcards = message.get("handCards", [])
            rank = message.get("curRank", "2")
            hand_structure = self.hand_analyzer.analyze(handcards, rank)
        
        # ⭐ 2. 队友保护判断
        if self.teammate_protection:
            protection_action = self.teammate_protection.get_protection_action(message, context)
            if protection_action is not None:
                return protection_action
        
        # ⭐ 3. 利用扫描结果优化候选动作（新增：优先复杂牌型）
        candidates = self._get_candidates(message)
        filtered_candidates = self._filter_by_scan_result(candidates, context, card_type='TwoTrips')
        
        # ⭐ 4. 优先级选择
        if self.priority_system and filtered_candidates:
            return self.priority_system.select(filtered_candidates, hand_structure, context)
        
        # 降级方案：选择第一个非PASS动作
        for i, action in enumerate(action_list):
            if action[0] != "PASS" and action[0] == "TwoTrips":
                return i
        return 0
    
    def _filter_by_scan_result(self, candidates: List, context: Dict, card_type: str = None) -> List:
        """根据扫描结果过滤候选动作（优先复杂牌型）"""
        if not candidates:
            return candidates
        
        scan_result = context.get('scan_result', {})
        complex_types = scan_result.get('complex_types', {})
        
        # 如果当前牌型是复杂牌型，优先选择在扫描结果中的动作
        if card_type and card_type in complex_types:
            available_complex = complex_types[card_type]
            
            # 提取动作中的卡牌
            def get_action_cards(action):
                if isinstance(action, list) and len(action) > 2:
                    if isinstance(action[2], list):
                        return set(action[2])
                return set()
            
            # 分离复杂牌型和其他动作
            complex_candidates = []
            other_candidates = []
            
            for candidate in candidates:
                action_cards = get_action_cards(candidate)
                # 检查是否匹配扫描结果中的复杂牌型
                is_complex = False
                for complex_cards in available_complex:
                    complex_set = set(complex_cards)
                    if action_cards == complex_set:
                        is_complex = True
                        break
                
                if is_complex:
                    complex_candidates.append(candidate)
                else:
                    other_candidates.append(candidate)
            
            # 优先返回复杂牌型
            return complex_candidates + other_candidates
        
        return candidates
    
    def _get_candidates(self, message: Dict) -> list:
        """获取候选动作"""
        action_list = message.get("actionList", [])
        return [a for a in action_list if a[0] == "TwoTrips" and a[0] != "PASS"]


class BombHandler(CardTypeHandler):
    """炸弹处理器"""
    
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理炸弹被动出牌（提升：集成策略引擎，炸弹需要谨慎使用）"""
        action_list = message.get("actionList", [])
        cur_action = message.get("curAction")
        
        if not action_list or not cur_action:
            return 0
        
        # ⭐ 1. 手牌结构分析
        hand_structure = {}
        if self.hand_analyzer:
            handcards = message.get("handCards", [])
            rank = message.get("curRank", "2")
            hand_structure = self.hand_analyzer.analyze(handcards, rank)
        
        # ⭐ 2. 队友保护判断（炸弹更谨慎）
        if self.teammate_protection:
            protection_action = self.teammate_protection.get_protection_action(message, context)
            if protection_action is not None:
                return protection_action
        
        # ⭐ 3. 炸弹特殊处理：只在关键时刻使用
        # 如果对手牌数很少，或者队友需要保护，才使用炸弹
        cards_left = context.get("cards_left", {})
        my_pos = message.get("myPos", 0)
        opponents_remain = [cards_left.get(i, DEFAULT_REST_CARDS) for i in range(4) if i != my_pos and (my_pos + 2) % 4 != i]
        min_opponent_remain = min(opponents_remain) if opponents_remain else DEFAULT_REST_CARDS
        
        # 对手牌数很少，需要压制，可以使用炸弹
        if min_opponent_remain <= 3:
            candidates = self._get_candidates(message)
            if candidates:
                return candidates[0]  # 使用第一个炸弹
        
        # 否则，优先PASS，保留炸弹
        return 0
    
    def _get_candidates(self, message: Dict) -> list:
        """获取候选动作"""
        action_list = message.get("actionList", [])
        return [a for a in action_list if a[0] == "Bomb" and a[0] != "PASS"]


class CardTypeHandlerFactory:
    """牌型处理器工厂（提升：统一接口，支持策略注入）"""
    
    _handler_classes = {
        "Single": SingleHandler,
        "Pair": PairHandler,
        "Trips": TripsHandler,
        "ThreeWithTwo": ThreeWithTwoHandler,
        "ThreePair": ThreePairHandler,
        "Straight": StraightHandler,
        "TwoTrips": TwoTripsHandler,
        "Bomb": BombHandler,
    }
    
    @staticmethod
    def get_handler(card_type: str, config: Dict = None) -> Optional[CardTypeHandler]:
        """
        获取牌型处理器
        
        Args:
            card_type: 牌型类型 "Single", "Pair" 等
            config: 配置字典
        
        Returns:
            对应的牌型处理器，如果不存在返回None
        """
        handler_class = CardTypeHandlerFactory._handler_classes.get(card_type)
        if handler_class:
            return handler_class(config or {})
        return None
    
    @staticmethod
    def register_handler(card_type: str, handler_class: type):
        """注册新的牌型处理器（提升：支持扩展）"""
        CardTypeHandlerFactory._handler_classes[card_type] = handler_class

