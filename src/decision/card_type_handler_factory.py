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

from game_logic.enhanced_state import EnhancedGameStateManager
from game_logic.hand_combiner import HandCombiner
from .hand_structure_analyzer import HandStructureAnalyzer


class CardTypeHandler(ABC):
    """牌型处理器基类（提升：统一接口，支持策略注入）"""
    
    def __init__(self, config: Dict):
        self.config = config
        # 这些将在后续实现
        # self.teammate_protection = TeammateProtectionStrategy(config)
        # self.hand_analyzer = HandStructureAnalyzer()
        # self.priority_system = PrioritySystem(config)
    
    @abstractmethod
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理被动出牌"""
        pass
    
    def handle_active(self, message: Dict, context: Dict) -> int:
        """处理主动出牌（可选）"""
        pass
    
    def analyze_structure(self, handcards: list, rank: str) -> Dict:
        """分析手牌结构（提升：统一的手牌分析接口）"""
        # TODO: 实现手牌结构分析
        return {}


class SingleHandler(CardTypeHandler):
    """单张处理器（学习lalala，但增强）"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        # TODO: 初始化策略
        # self.teammate_protection = TeammateProtectionStrategy(config)
        # self.hand_analyzer = HandStructureAnalyzer()
        # self.priority_system = PrioritySystem(config)
    
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理单张被动出牌（提升：更完善的逻辑）"""
        action_list = message.get("actionList", [])
        cur_action = message.get("curAction")
        
        if not action_list or not cur_action:
            return 0
        
        # TODO: 1. 手牌结构分析（lalala有，YF增强：更详细）
        # hand_structure = self.hand_analyzer.analyze(...)
        
        # TODO: 2. 队友保护判断（lalala有，YF增强：多策略）
        # if self.teammate_protection.should_protect(message, context):
        #     return 0  # PASS
        
        # TODO: 3. 优先级选择（lalala有，YF提升：动态优先级）
        # candidates = self._get_candidates(message)
        # return self.priority_system.select(candidates, hand_structure, context)
        
        # 临时实现：选择第一个非PASS动作
        for i, action in enumerate(action_list):
            if action[0] != "PASS" and action[0] == "Single":
                return i
        
        return 0
    
    def _get_candidates(self, message: Dict) -> list:
        """获取候选动作"""
        action_list = message.get("actionList", [])
        return [a for a in action_list if a[0] == "Single" and a[0] != "PASS"]


class PairHandler(CardTypeHandler):
    """对子处理器"""
    
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理对子被动出牌"""
        # TODO: 实现对子被动出牌逻辑
        action_list = message.get("actionList", [])
        for i, action in enumerate(action_list):
            if action[0] != "PASS" and action[0] == "Pair":
                return i
        return 0


class TripsHandler(CardTypeHandler):
    """三张处理器"""
    
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理三张被动出牌"""
        # TODO: 实现三张被动出牌逻辑
        action_list = message.get("actionList", [])
        for i, action in enumerate(action_list):
            if action[0] != "PASS" and action[0] == "Trips":
                return i
        return 0


class ThreeWithTwoHandler(CardTypeHandler):
    """三带二处理器"""
    
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理三带二被动出牌"""
        # TODO: 实现三带二被动出牌逻辑
        action_list = message.get("actionList", [])
        for i, action in enumerate(action_list):
            if action[0] != "PASS" and action[0] == "ThreeWithTwo":
                return i
        return 0


class ThreePairHandler(CardTypeHandler):
    """三连对处理器"""
    
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理三连对被动出牌"""
        # TODO: 实现三连对被动出牌逻辑
        action_list = message.get("actionList", [])
        for i, action in enumerate(action_list):
            if action[0] != "PASS" and action[0] == "ThreePair":
                return i
        return 0


class StraightHandler(CardTypeHandler):
    """顺子处理器"""
    
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理顺子被动出牌"""
        # TODO: 实现顺子被动出牌逻辑
        action_list = message.get("actionList", [])
        for i, action in enumerate(action_list):
            if action[0] != "PASS" and action[0] == "Straight":
                return i
        return 0


class TwoTripsHandler(CardTypeHandler):
    """钢板处理器"""
    
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理钢板被动出牌"""
        # TODO: 实现钢板被动出牌逻辑
        action_list = message.get("actionList", [])
        for i, action in enumerate(action_list):
            if action[0] != "PASS" and action[0] == "TwoTrips":
                return i
        return 0


class BombHandler(CardTypeHandler):
    """炸弹处理器"""
    
    def handle_passive(self, message: Dict, context: Dict) -> int:
        """处理炸弹被动出牌"""
        # TODO: 实现炸弹被动出牌逻辑
        action_list = message.get("actionList", [])
        for i, action in enumerate(action_list):
            if action[0] != "PASS" and action[0] == "Bomb":
                return i
        return 0


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

