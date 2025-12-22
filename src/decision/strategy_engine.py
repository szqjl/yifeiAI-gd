# -*- coding: utf-8 -*-
"""
策略引擎 (Strategy Engine)
功能：
- 实现核心策略系统（队友保护、优先级系统、牌值系统）
- 提供统一的策略接口
- 支持策略配置和动态调整
- M1版本：独立的策略引擎模块
"""

from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
import logging


class ProtectionRule(ABC):
    """保护规则基类"""
    
    @abstractmethod
    def evaluate(self, message: Dict, context: Dict) -> float:
        """评估保护需求，返回0.0-1.0的分数"""
        pass


class HighValueProtectionRule(ProtectionRule):
    """高牌值保护规则（学习lalala）"""
    
    def evaluate(self, message: Dict, context: Dict) -> float:
        """评估保护需求"""
        cur_action = message.get("curAction", [])
        greater_pos = message.get("greaterPos", -1)
        my_pos = message.get("myPos", 0)
        teammate_pos = (my_pos + 2) % 4
        
        # 如果队友是最大动作者
        if greater_pos == teammate_pos and cur_action:
            cur_val = self._get_card_value(cur_action, context)
            max_val = context.get("max_card_value", 15)
            
            # 当前牌值很大，需要保护
            if cur_val >= max_val or cur_val >= 15:
                return 1.0  # 高保护需求
            elif cur_val >= max_val - 2:
                return 0.5  # 中等保护需求
        
        return 0.0
    
    def _get_card_value(self, cur_action: List, context: Dict) -> int:
        """获取牌值"""
        if not cur_action or len(cur_action) < 2:
            return 0
        
        # 简单的牌值计算（后续可以集成CardValueSystem）
        card = cur_action[1] if isinstance(cur_action[1], str) else str(cur_action[1])
        rank = context.get("curRank", "2")
        
        # 基础牌值映射
        value_map = {
            '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
            '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14,
            '2': 15, 'R': 16, 'B': 17  # R=大王, B=小王
        }
        
        # 提取牌值（去掉花色）
        card_rank = card[-1] if len(card) > 1 else card
        if card_rank in value_map:
            return value_map[card_rank]
        
        # 等级牌特殊处理
        if card.endswith(rank):
            return 15
        
        return 0


class LowCardCountProtectionRule(ProtectionRule):
    """低牌数保护规则"""
    
    def evaluate(self, message: Dict, context: Dict) -> float:
        """评估保护需求"""
        greater_pos = message.get("greaterPos", -1)
        my_pos = message.get("myPos", 0)
        teammate_pos = (my_pos + 2) % 4
        
        # 如果队友是最大动作者
        if greater_pos == teammate_pos:
            cards_left = context.get("cards_left", {})
            teammate_cards = cards_left.get(teammate_pos, 27)
            
            # 队友牌数越少，保护需求越高
            if teammate_cards <= 2:
                return 1.0  # 极高保护需求
            elif teammate_cards <= 3:
                return 0.9
            elif teammate_cards <= 5:
                return 0.7
            elif teammate_cards <= 8:
                return 0.4
        
        return 0.0


class CriticalStageProtectionRule(ProtectionRule):
    """关键阶段保护规则"""
    
    def evaluate(self, message: Dict, context: Dict) -> float:
        """评估保护需求"""
        greater_pos = message.get("greaterPos", -1)
        my_pos = message.get("myPos", 0)
        teammate_pos = (my_pos + 2) % 4
        
        # 如果队友是最大动作者
        if greater_pos == teammate_pos:
            game_phase = context.get("game_phase", "opening")
            
            # 残局阶段保护需求更高
            if game_phase in ["endgame_early", "endgame_late"]:
                return 0.8
            elif game_phase == "mid_late":
                return 0.5
        
        return 0.0


class ThreatAssessmentRule(ProtectionRule):
    """威胁评估保护规则"""
    
    def evaluate(self, message: Dict, context: Dict) -> float:
        """评估保护需求"""
        greater_pos = message.get("greaterPos", -1)
        my_pos = message.get("myPos", 0)
        teammate_pos = (my_pos + 2) % 4
        
        # 如果队友是最大动作者
        if greater_pos == teammate_pos:
            cards_left = context.get("cards_left", {})
            opponents_cards = [
                cards_left.get(i, 27) 
                for i in range(4) 
                if i != my_pos and i != teammate_pos
            ]
            
            # 对手牌数越少，威胁越大，保护需求越高
            min_opponent_cards = min(opponents_cards) if opponents_cards else 27
            if min_opponent_cards <= 3:
                return 0.9  # 对手快走完，需要保护队友
            elif min_opponent_cards <= 5:
                return 0.6
        
        return 0.0


class TeammateProtectionStrategy:
    """队友保护策略（提升：多策略组合）"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = logging.getLogger("TeammateProtectionStrategy")
        
        # 初始化保护规则
        self.protection_rules = [
            HighValueProtectionRule(),      # 高牌值保护
            LowCardCountProtectionRule(),   # 低牌数保护
            CriticalStageProtectionRule(),  # 关键阶段保护
            ThreatAssessmentRule(),         # 威胁评估保护
        ]
    
    def should_protect(self, message: Dict, context: Dict) -> bool:
        """判断是否应该保护队友（提升：多规则组合）"""
        protection_score = 0.0
        
        # 综合所有保护规则
        for rule in self.protection_rules:
            try:
                score = rule.evaluate(message, context)
                protection_score += score
            except Exception as e:
                self.logger.warning(f"Protection rule evaluation error: {e}")
        
        # 动态阈值（提升：根据情况调整）
        threshold = self._get_dynamic_threshold(message, context)
        
        return protection_score >= threshold
    
    def get_protection_action(self, message: Dict, context: Dict) -> Optional[int]:
        """获取保护动作（提升：智能选择保护方式）"""
        if not self.should_protect(message, context):
            return None
        
        # 保护方式1: PASS（完全保护）
        if self._should_full_protect(message, context):
            return 0
        
        # 保护方式2: 出最小管牌（部分保护）
        if self._should_partial_protect(message, context):
            return self._find_minimal_action(message)
        
        return None
    
    def _get_dynamic_threshold(self, message: Dict, context: Dict) -> float:
        """获取动态阈值（提升：根据情况调整）"""
        base_threshold = self.config.get("protection_threshold", 1.5)
        
        # 根据游戏阶段调整阈值
        game_phase = context.get("game_phase", "opening")
        if game_phase in ["endgame_early", "endgame_late"]:
            return base_threshold * 0.8  # 残局降低阈值，更容易触发保护
        elif game_phase == "mid_late":
            return base_threshold * 0.9
        
        return base_threshold
    
    def _should_full_protect(self, message: Dict, context: Dict) -> bool:
        """判断是否应该完全保护（PASS）"""
        cards_left = context.get("cards_left", {})
        my_pos = message.get("myPos", 0)
        teammate_pos = (my_pos + 2) % 4
        teammate_cards = cards_left.get(teammate_pos, 27)
        
        # 队友牌数很少，完全保护
        if teammate_cards <= 2:
            return True
        
        # 队友出炸弹，完全保护
        cur_action = message.get("curAction", [])
        if cur_action and len(cur_action) > 0:
            action_type = cur_action[0] if isinstance(cur_action, list) else str(cur_action)
            if action_type == "Bomb":
                return True
        
        return False
    
    def _should_partial_protect(self, message: Dict, context: Dict) -> bool:
        """判断是否应该部分保护（出最小管牌）"""
        # 不完全保护的情况下，可以考虑部分保护
        return not self._should_full_protect(message, context)
    
    def _find_minimal_action(self, message: Dict) -> Optional[int]:
        """找到最小管牌动作"""
        action_list = message.get("actionList", [])
        cur_action = message.get("curAction", [])
        
        if not action_list or not cur_action:
            return None
        
        # 找到能管住当前动作的最小动作
        candidates = []
        for i, action in enumerate(action_list):
            if action[0] != "PASS" and self._can_beat(action, cur_action):
                candidates.append((i, action))
        
        if not candidates:
            return None
        
        # 选择最小的动作（这里简化处理，实际应该比较牌值）
        return candidates[0][0]
    
    def _can_beat(self, action: List, cur_action: List) -> bool:
        """判断动作是否能管住当前动作"""
        # 简化实现，实际应该根据牌型规则判断
        if not action or not cur_action:
            return False
        
        action_type = action[0] if isinstance(action, list) else str(action)
        cur_type = cur_action[0] if isinstance(cur_action, list) else str(cur_action)
        
        # 同类型且更大，或炸弹
        if action_type == cur_type:
            return True
        elif action_type == "Bomb":
            return True
        
        return False


class ContextPriorityAdjuster:
    """上下文优先级调整器（YF新增：动态调整）"""
    
    def adjust(self, base_scores: List[float], context: Dict) -> List[float]:
        """根据上下文调整优先级"""
        adjusted = base_scores.copy()
        
        # 调整因子1: 下家牌数
        next_player_remain = context.get("next_player_remain", 27)
        if next_player_remain == 1:
            # 下家只剩1张，降低单张优先级
            adjusted = self._reduce_single_priority(adjusted, context)
        
        # 调整因子2: PASS次数
        pass_count = context.get("pass_count", 0)
        if pass_count >= 5:
            # PASS次数过多，提高出牌优先级
            adjusted = self._increase_play_priority(adjusted, context)
        
        # 调整因子3: 残局阶段
        is_endgame = context.get("is_endgame", False)
        if is_endgame:
            # 残局，调整优先级
            adjusted = self._adjust_endgame_priority(adjusted, context)
        
        return adjusted
    
    def _reduce_single_priority(self, scores: List[float], context: Dict) -> List[float]:
        """降低单张优先级"""
        # 简化实现，实际应该根据动作类型调整
        return scores
    
    def _increase_play_priority(self, scores: List[float], context: Dict) -> List[float]:
        """提高出牌优先级"""
        # 简化实现
        return [s + 50 for s in scores]
    
    def _adjust_endgame_priority(self, scores: List[float], context: Dict) -> List[float]:
        """调整残局优先级"""
        # 简化实现
        return scores


class PrioritySystem:
    """优先级系统（提升：动态优先级）"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.base_priority = self._load_base_priority(config)
        self.context_adjuster = ContextPriorityAdjuster()
        self.logger = logging.getLogger("PrioritySystem")
    
    def select(self, candidates: List, hand_structure: Dict, context: Dict) -> int:
        """选择最佳动作（提升：动态优先级）"""
        if not candidates:
            return 0
        
        # 1. 获取基础优先级
        base_scores = self._calculate_base_scores(candidates, hand_structure, context)
        
        # 2. 根据上下文调整（提升：动态调整）
        adjusted_scores = self.context_adjuster.adjust(base_scores, context)
        
        # 3. 选择最高分
        best_idx = max(range(len(adjusted_scores)), 
                      key=lambda i: adjusted_scores[i])
        return best_idx
    
    def _load_base_priority(self, config: Dict) -> Dict:
        """加载基础优先级（提升：可配置）"""
        # 从配置文件加载，支持动态调整
        return config.get("priority_rules", {
            'active': {
                'one_hand_complete': 1000,
                'two_hand_complete': 900,
                'small_single': 800,
                'threepair': 700,
                'straight': 600,
                'three_with_two': 500,
                'trips': 400,
                'pair': 300,
                'single': 200,
            },
            'passive': {
                'single_member_large': 1000,
                'non_bomb_large': 900,
                'relaxed_condition': 800,
                'use_level_card': 700,
                'use_bomb': 600,
            }
        })
    
    def _calculate_base_scores(self, candidates: List, hand_structure: Dict, context: Dict) -> List[float]:
        """计算基础分数（提升：支持所有动作类型）"""
        scores = []
        is_active = context.get("is_active", True)
        priority_map = self.base_priority.get('active' if is_active else 'passive', {})
        
        # 动作类型到优先级键的映射（处理大小写和特殊名称）
        action_type_mapping = {
            'single': 'single',
            'pair': 'pair',
            'trips': 'trips',
            'threewithtwo': 'three_with_two',
            'threepair': 'threepair',
            'twotrips': 'threepair',  # 钢板和三连对优先级相同
            'straight': 'straight',
            'straightflush': 'straight',
            'bomb': 'use_bomb' if not is_active else 1000,  # 炸弹优先级最高
        }
        
        for candidate in candidates:
            if not candidate or len(candidate) < 1:
                scores.append(0.0)
                continue
            
            action_type = candidate[0] if isinstance(candidate, list) else str(candidate)
            action_type_lower = action_type.lower() if isinstance(action_type, str) else str(action_type).lower()
            
            # 检查一手出完
            handcards = context.get("handcards", [])
            if len(candidate) > 2 and isinstance(candidate[2], list) and len(candidate[2]) == len(handcards):
                scores.append(float(priority_map.get('one_hand_complete', 1000)))
                continue
            
            # 检查两手出完（主动出牌时）
            if is_active and len(candidate) > 2 and isinstance(candidate[2], list):
                card_count = len(candidate[2])
                if card_count >= len(handcards) * 0.7:  # 出牌数超过70%手牌
                    scores.append(float(priority_map.get('two_hand_complete', 900)))
                    continue
            
            # 根据动作类型获取优先级
            priority_key = action_type_mapping.get(action_type_lower, action_type_lower)
            score = priority_map.get(priority_key, 100)
            
            # 特殊处理：单张的优先级根据牌值调整
            if action_type_lower == 'single' and is_active:
                # 小单张优先级更高
                if len(candidate) > 1:
                    card_rank = candidate[1] if isinstance(candidate[1], str) else str(candidate[1])
                    # 提取牌值（去掉花色）
                    rank_char = card_rank[-1] if len(card_rank) > 1 else card_rank
                    small_ranks = ['3', '4', '5', '6', '7']
                    if rank_char in small_ranks:
                        score = priority_map.get('small_single', 800)
            
            scores.append(float(score))
        
        return scores


class CardValueSystem:
    """牌值系统（提升：上下文相关）"""
    
    def __init__(self, rank: str = "2"):
        self.rank = rank
        self.base_values = self._init_base_values()
        self.rank_card_value = 15
    
    def get_value(self, card: str, context: Dict = None) -> float:
        """获取牌值（提升：上下文相关）"""
        # 基础值
        base_value = self.base_values.get(card, 0)
        
        # 等级牌特殊处理
        if card.endswith(self.rank):
            base_value = self.rank_card_value
        
        # 上下文调整（提升：动态调整）
        if context:
            base_value = self._adjust_by_context(base_value, card, context)
        
        return base_value
    
    def _init_base_values(self) -> Dict[str, int]:
        """初始化基础牌值"""
        return {
            '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
            '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14,
            '2': 15, 'R': 16, 'B': 17  # R=大王, B=小王
        }
    
    def _adjust_by_context(self, base_value: float, card: str, context: Dict) -> float:
        """根据上下文调整牌值（YF新增）"""
        # 调整因子1: 剩余牌库
        max_remain_value = context.get("max_remain_value", 15)
        if base_value >= max_remain_value:
            # 是最大牌，增加价值
            base_value += 0.5
        
        # 调整因子2: 游戏阶段
        if context.get("is_endgame", False):
            # 残局，大牌价值更高
            if base_value >= 12:
                base_value += 1.0
        
        return base_value

