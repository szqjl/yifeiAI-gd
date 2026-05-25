# -*- coding: utf-8 -*-
"""
增强优先级系统 (Enhanced Priority System)
基于 Agentic Design Patterns 优先级排序模式优化

功能：
- 多因素优先级计算
- 动态权重调整
- 优先级学习机制
"""

from typing import Dict, List, Optional
import logging
from datetime import datetime
import numpy as np
try:
    from game_logic.guandan_constants import DEFAULT_REST_CARDS, GAME_OBJECTIVE
except ImportError:
    DEFAULT_REST_CARDS = 27
    GAME_OBJECTIVE = ""


class DynamicWeightAdjuster:
    """动态权重调整器（基于 Agentic Design Patterns）"""
    
    def __init__(self):
        # 基础权重配置
        self.base_weights = {
            'base_priority': 0.2,
            'card_value': 0.12,
            'hand_structure': 0.12,
            'opponent_threat': 0.12,
            'teammate_cooperation': 0.08,
            'timing': 0.05,
            'risk': 0.05,
            'split_impact': 0.3,  # 拆牌影响因素权重（提高，确保不破坏受保护组合）
            'action_effect': 0.25,  # 实际动作效果权重（轮次减少、单牌减少等）- 提高权重以匹配client AI
            'win_awareness': 0.1,   # 赢意识：有局目标时整体向争头游/获胜倾斜
        }
        
        # 阶段权重调整因子
        self.phase_adjustments = {
            'opening': {
                'teammate_cooperation': 0.05,
                'risk': 0.1,
                'base_priority': -0.05
            },
            'mid_early': {
                'opponent_threat': 0.2,
                'timing': 0.1,
                'base_priority': -0.1
            },
            'mid_late': {
                'card_value': 0.25,
                'hand_structure': 0.2,
                'base_priority': -0.15
            },
            'endgame_early': {
                'timing': 0.15,
                'risk': 0.1,
                'base_priority': -0.1
            },
            'endgame_late': {
                'base_priority': 0.4,
                'timing': 0.2,
                'card_value': -0.1
            },
        }
    
    def get_weights(self, context: Dict) -> Dict[str, float]:
        """
        获取动态权重
        
        Args:
            context: 上下文信息
            
        Returns:
            归一化后的权重字典
        """
        weights = self.base_weights.copy()
        phase = context.get('game_phase', 'opening')
        
        # 应用阶段调整
        if phase in self.phase_adjustments:
            adjustments = self.phase_adjustments[phase]
            for factor, adjustment in adjustments.items():
                if factor in weights:
                    weights[factor] += adjustment
        
        # 确保权重非负
        weights = {k: max(0.0, v) for k, v in weights.items()}
        
        # 归一化
        total = sum(weights.values())
        if total > 0:
            weights = {k: v/total for k, v in weights.items()}
        
        return weights


class EnhancedPrioritySystem:
    """增强优先级系统（基于 Agentic Design Patterns）"""
    
    def __init__(self, config: Dict = None, base_priority_system=None):
        """
        初始化增强优先级系统
        
        Args:
            config: 配置字典
            base_priority_system: 基础优先级系统（PrioritySystem实例）
        """
        self.config = config or {}
        self.base_priority_system = base_priority_system
        self.weight_adjuster = DynamicWeightAdjuster()
        self.logger = logging.getLogger("EnhancedPrioritySystem")
        
        # 优先级历史记录（用于学习）
        self.priority_history = []
        self.max_history_size = config.get('priority_history_size', 1000)
    
    def select(self, candidates: List, hand_structure: Dict, context: Dict) -> int:
        """
        选择最佳动作（多因素优先级计算）
        
        Args:
            candidates: 候选动作列表
            hand_structure: 手牌结构
            context: 上下文信息
            
        Returns:
            最佳动作索引
        """
        if not candidates:
            # ⚠️ 修复：如果candidates为空，不应该返回0（这会导致PASS）
            # 应该抛出异常或返回-1，让调用者处理
            import logging
            logger = logging.getLogger("EnhancedPrioritySystem")
            logger.error("select() called with empty candidates list!")
            raise ValueError("Cannot select from empty candidates list")
        
        # 1. 计算多因素优先级
        priority_factors = self._calculate_priority_factors(candidates, hand_structure, context)
        
        # 2. 获取动态权重
        weights = self.weight_adjuster.get_weights(context)
        
        # 3. 加权综合得分
        final_scores = self._calculate_weighted_scores(priority_factors, weights)
        
        # 4. 选择最高分
        best_idx = max(range(len(final_scores)), key=lambda i: final_scores[i])
        
        # 5. 记录决策（用于学习）
        self._record_decision(priority_factors, best_idx, context)
        
        return best_idx
    
    def _calculate_priority_factors(self, candidates: List, hand_structure: Dict, context: Dict) -> List[Dict]:
        """
        计算多维度优先级因素
        
        Args:
            candidates: 候选动作列表
            hand_structure: 手牌结构
            context: 上下文信息
            
        Returns:
            每个候选动作的优先级因素字典列表
        """
        factors_list = []
        
        # 获取实际动作评估结果（新增：利用扫描器的动作评估）
        scan_result = context.get('scan_result', {})
        action_evaluations = scan_result.get('action_evaluations', {})
        
        for idx, candidate in enumerate(candidates):
            factors = {
                # 因素1: 基础优先级（原有）
                'base_priority': self._calculate_base_priority_factor(candidate, context),
                
                # 因素2: 牌值因素
                'card_value': self._calculate_card_value_factor(candidate, context),
                
                # 因素3: 手牌结构因素
                'hand_structure': self._calculate_hand_structure_factor(candidate, hand_structure, context),
                
                # 因素4: 对手威胁因素
                'opponent_threat': self._calculate_opponent_threat_factor(candidate, context),
                
                # 因素5: 队友配合因素
                'teammate_cooperation': self._calculate_teammate_cooperation_factor(candidate, context),
                
                # 因素6: 时机因素
                'timing': self._calculate_timing_factor(candidate, context),
                
                # 因素7: 风险因素
                'risk': self._calculate_risk_factor(candidate, context),
                
                # 因素8: 拆牌影响因素（新增：避免不合理拆牌）
                'split_impact': self._calculate_split_impact_factor(candidate, context),
                
                # 因素9: 实际动作效果（新增：利用扫描器的动作评估）
                'action_effect': self._calculate_action_effect_factor(idx, candidate, action_evaluations, context),
                # 因素10: 赢意识（有局目标时所有候选均加分，强化争头游/获胜）
                'win_awareness': 1.0 if context.get('game_objective') else 0.0,
            }
            factors_list.append(factors)
        
        return factors_list
    
    def _calculate_action_effect_factor(self, action_idx: int, candidate: List, 
                                       action_evaluations: Dict, context: Dict) -> float:
        """
        计算实际动作效果因素（新增：利用扫描器的动作评估）
        
        Args:
            action_idx: 动作索引（在candidates中的位置）
            candidate: 候选动作
            action_evaluations: 动作评估字典（来自扫描器）
            context: 上下文信息
            
        Returns:
            动作效果评分（0-1范围）
        """
        # 如果扫描器提供了动作评估，使用它
        if action_idx in action_evaluations:
            action_eval = action_evaluations[action_idx]
            rounds_reduced = action_eval.get('rounds_reduced', 0)
            singles_reduced = action_eval.get('singles_reduced', 0)
            action_score = action_eval.get('score', 0.0)
            
            # 将动作评估结果转换为0-1范围的评分（与client AI对齐）
            # Client AI策略：轮次减少+45分，单牌减少+20分/个，残局+30/25分
            # 我们直接使用action_score（已包含所有调整），归一化到0-1
            # 但需要突出轮次减少的重要性（胜负规则优先）
            base_score = min(1.0, action_score / 150.0)  # 归一化（假设最高150分）
            
            # 轮次减少是最高优先级（胜负规则优先），额外加权
            if rounds_reduced > 0:
                base_score = min(1.0, base_score + 0.2)  # 轮次减少额外+0.2
            
            return base_score
        
        # 如果没有扫描器评估，返回默认值
        return 0.5
    
    def _calculate_base_priority_factor(self, candidate: List, context: Dict) -> float:
        """
        计算基础优先级因素
        
        ⚠️ 关键修复：优先使用excess_singles，开局时优先小单张(3-7)
        """
        action_type = candidate[0] if isinstance(candidate[0], str) else ""
        action_cards = candidate[2] if len(candidate) > 2 and isinstance(candidate[2], list) else []
        
        # ⚠️ 开局主动出牌时，优先小单张(3-7)
        game_phase = context.get('game_phase', 'opening')
        is_active = not context.get('is_passive', False)
        if game_phase == 'opening' and is_active and action_type == 'Single' and action_cards and len(action_cards) == 1:
            card = action_cards[0]
            if len(card) >= 2:
                card_rank = card[1] if len(card) == 2 else card[1:]
                # 小单张：3-7
                small_singles = ['3', '4', '5', '6', '7']
                if card_rank in small_singles:
                    # 检查是否是excess_singles
                    excess_singles = context.get('excess_singles', [])
                    if card in excess_singles:
                        return 1.0  # 小单张且是多余单张，最高优先级
                    else:
                        return 0.9  # 小单张但不是多余单张，次高优先级
        
        # ⚠️ 优先使用excess_singles（非开局或被动出牌时）
        excess_singles = context.get('excess_singles', [])
        if excess_singles:
            if action_type == 'Single' and action_cards and len(action_cards) == 1:
                if action_cards[0] in excess_singles:
                    return 0.95  # 是多余单张，高优先级（但低于开局小单张）
        
        if self.base_priority_system:
            # 使用基础优先级系统
            base_scores = self.base_priority_system._calculate_base_scores(
                [candidate], {}, context
            )
            if base_scores:
                # 归一化到0-1范围
                return min(1.0, base_scores[0] / 1000.0)
        
        # 降级：简单计算
        return 0.5
    
    def _calculate_card_value_factor(self, candidate: List, context: Dict) -> float:
        """计算牌值因素"""
        if not candidate or len(candidate) < 2:
            return 0.0
        
        # 获取牌值系统
        card_value_system = context.get('card_value_system')
        if not card_value_system:
            return 0.5
        
        # 提取卡牌
        cards = []
        if len(candidate) > 2 and isinstance(candidate[2], list):
            cards = candidate[2]
        elif len(candidate) > 1:
            cards = [candidate[1]] if isinstance(candidate[1], str) else []
        
        if not cards:
            return 0.0
        
        # 计算平均牌值
        total_value = 0.0
        for card in cards:
            value = card_value_system.get_value(card, context)
            total_value += value
        
        avg_value = total_value / len(cards) if cards else 0.0
        
        # 归一化到0-1范围（假设最大牌值为17）
        return min(1.0, avg_value / 17.0)
    
    def _calculate_hand_structure_factor(self, candidate: List, hand_structure: Dict, context: Dict) -> float:
        """
        计算手牌结构因素（优化：识别复杂牌型并应用评分策略）
        
        参考知识库：
        - 钢板（TwoTrips）：一次出6张，特殊牌型，对手难管
        - 三连对（ThreePair）：一次出6张，特殊牌型，不易管压，残局偷袭利器
        - 三带二（ThreeWithTwo）：一次出5张，可带走对子赘牌，有打有收策略
        """
        handcards = context.get("handcards", [])
        if not handcards:
            return 0.5
        
        # 检查是否一手出完
        if len(candidate) > 2 and isinstance(candidate[2], list):
            if len(candidate[2]) == len(handcards):
                return 1.0  # 一手出完，最高分
        
        # 检查是否两手出完
        if len(candidate) > 2 and isinstance(candidate[2], list):
            card_count = len(candidate[2])
            if card_count >= len(handcards) * 0.7:
                return 0.9  # 两手出完，高分
        
        # 提取动作类型
        action_type = candidate[0] if isinstance(candidate, list) and len(candidate) > 0 else ""
        action_cards = candidate[2] if len(candidate) > 2 and isinstance(candidate[2], list) else []
        
        # 识别复杂牌型并应用评分策略
        # ⚠️ 优化：利用扫描结果识别复杂牌型（如果候选动作在扫描结果的复杂牌型列表中，大幅加分）
        scan_result = context.get('scan_result', {})
        complex_types = scan_result.get('complex_types', {})
        
        # 检查候选动作是否是扫描结果中的复杂牌型
        if action_type in complex_types:
            available_complex = complex_types[action_type]
            action_cards = candidate[2] if len(candidate) > 2 and isinstance(candidate[2], list) else []
            if action_cards:
                action_cards_set = set(action_cards)
                for complex_cards in available_complex:
                    complex_set = set(complex_cards)
                    if action_cards_set == complex_set:
                        # 是扫描结果中的复杂牌型，大幅加分
                        if action_type == 'TwoTrips':
                            return min(1.0, self._calculate_two_trips_score(candidate, context) + 0.2)
                        elif action_type == 'ThreePair':
                            return min(1.0, self._calculate_three_pair_score(candidate, context) + 0.2)
                        elif action_type == 'ThreeWithTwo':
                            return min(1.0, self._calculate_three_with_two_score(candidate, context) + 0.2)
        
        # 原有逻辑
        if action_type == 'TwoTrips':
            # 钢板（三连三）
            return self._calculate_two_trips_score(candidate, context)
        elif action_type == 'ThreePair':
            # 三连对（木板）
            return self._calculate_three_pair_score(candidate, context)
        elif action_type == 'ThreeWithTwo':
            # 三带二（夯）
            return self._calculate_three_with_two_score(candidate, context)
        elif action_type == 'Trips':
            # 三张（特殊情况：对子较大时，宁肯只出三张）
            return self._calculate_trips_score(candidate, context)
        
        # 基于手牌结构分析（其他牌型）
        if len(candidate) > 2 and isinstance(candidate[2], list):
            card_count = len(candidate[2])
            ratio = card_count / len(handcards) if handcards else 0.0
            return min(1.0, ratio * 1.2)
        
        return 0.5
    
    def _calculate_opponent_threat_factor(self, candidate: List, context: Dict) -> float:
        """计算对手威胁因素"""
        opponent_rest_cards_list = context.get('opponent_rest_cards_list', [])
        if not opponent_rest_cards_list:
            return 0.5
        
        min_opponent_cards = min(opponent_rest_cards_list)
        
        # 对手牌数越少，威胁越大，需要更谨慎
        if min_opponent_cards <= 2:
            # 高威胁：优先出大牌或炸弹
            action_type = candidate[0] if isinstance(candidate, list) else str(candidate)
            if action_type == 'Bomb':
                return 1.0
            return 0.8
        elif min_opponent_cards <= 5:
            return 0.6
        else:
            return 0.4
    
    def _calculate_teammate_cooperation_factor(self, candidate: List, context: Dict) -> float:
        """计算队友配合因素"""
        teammate_rest_cards = context.get('teammate_rest_cards', DEFAULT_REST_CARDS)
        greater_pos = context.get('greater_pos', -1)
        my_pos = context.get('my_pos', 0)
        teammate_pos = (my_pos + 2) % 4
        
        # 如果队友是最大动作者，需要配合
        if greater_pos == teammate_pos:
            # 队友牌数很少，需要保护
            if teammate_rest_cards <= 3:
                return 1.0  # 高配合需求
            elif teammate_rest_cards <= 5:
                return 0.8
            elif teammate_rest_cards <= 10:
                return 0.6
            else:
                return 0.4
        
        return 0.5
    
    def _calculate_timing_factor(self, candidate: List, context: Dict) -> float:
        """计算时机因素"""
        game_phase = context.get('game_phase', 'opening')
        my_remain = context.get('my_remain', DEFAULT_REST_CARDS)
        pass_count = context.get('pass_count', 0)
        
        # 残局阶段，时机因素更重要
        if game_phase in ['endgame_early', 'endgame_late']:
            # 残局：优先出完
            if len(candidate) > 2 and isinstance(candidate[2], list):
                card_count = len(candidate[2])
                handcards = context.get("handcards", [])
                if card_count >= len(handcards) * 0.8:
                    return 1.0
            return 0.8
        
        # PASS次数过多，需要出牌
        if pass_count >= 5:
            return 0.9
        
        return 0.5
    
    def _calculate_risk_factor(self, candidate: List, context: Dict) -> float:
        """计算风险因素"""
        action_type = candidate[0] if isinstance(candidate, list) else str(candidate)
        
        # 炸弹风险较低（但价值高）
        if action_type == 'Bomb':
            return 0.3  # 低风险
        
        # 小牌风险较低
        if len(candidate) > 1:
            card_rank = candidate[1] if isinstance(candidate[1], str) else str(candidate[1])
            rank_char = card_rank[-1] if len(card_rank) > 1 else card_rank
            small_ranks = ['3', '4', '5', '6', '7']
            if rank_char in small_ranks:
                return 0.2  # 低风险
        
        return 0.5  # 中等风险
    
    def _calculate_split_impact_factor(self, candidate: List, context: Dict) -> float:
        """
        计算拆牌影响因素（新增：避免不合理拆牌）
        
        返回值：
        - 1.0: 不拆牌（最优）
        - 0.5: 拆牌但影响小（可接受）
        - 0.0: 拆牌且影响大（应避免）
        """
        if not candidate or len(candidate) < 3:
            return 1.0  # 无法判断，默认不拆牌
        
        action_type = candidate[0] if isinstance(candidate[0], str) else ""
        action_cards = candidate[2] if len(candidate) > 2 and isinstance(candidate[2], list) else []
        handcards = context.get('handcards', [])
        cur_rank = context.get('cur_rank') or context.get('curRank', '2')
        game_phase = context.get('game_phase', 'opening')
        
        if not action_cards or not handcards:
            return 1.0
        
        # ⚠️ 硬约束：检查是否会破坏受保护组合（区分主动/被动出牌）
        scan_result = context.get('scan_result', {})
        protected_combinations = scan_result.get('protected_combinations', [])
        is_passive = context.get('is_passive', False)  # 是否是被动出牌
        
        if protected_combinations and action_cards:
            action_cards_set = set(action_cards)
            for protected in protected_combinations:
                protected_set = set(protected)
                # 如果动作中的卡牌与受保护组合有交集，且不是完整使用，就是破坏
                if action_cards_set & protected_set:
                    if not action_cards_set.issubset(protected_set):
                        # 检查是否是炸弹（炸弹无论主动被动都严格保护）
                        if len(protected) >= 4:  # 炸弹
                            return 0.0  # 拆炸弹绝对禁止
                        
                        # 主动出牌：严格保护所有组合
                        if not is_passive:
                            return 0.0  # 主动出牌时，破坏任何组合都禁止
                        
                        # 被动出牌：允许拆对子/三张来压制，但需要后续评估
                        # 这里不直接返回0.0，而是继续评估拆牌的影响
                        # 如果是拆三张，影响更大；如果是拆对子，影响较小
        
        # ⚠️ 检查是否是多余单张（如果是多余单张，不认为是拆牌）
        excess_singles = context.get('excess_singles', [])
        if action_type == 'Single' and len(action_cards) == 1:
            card = action_cards[0]
            if card in excess_singles:
                return 1.0  # 是多余单张，不认为是拆牌，最优
        
        # 统计手牌中每张牌的数量
        from collections import Counter
        handcard_counts = Counter(handcards)
        
        # 检查是否是拆牌
        is_split = False
        split_type = None
        impact_score = 0.0
        
        for card in action_cards:
            if len(card) >= 2:
                card_rank = card[1] if len(card) == 2 else card[1:]
                card_count = handcard_counts.get(card, 0)
                
                # 如果手牌中有2张或更多相同点数的牌，出单张就是拆对
                if action_type == 'Single' and card_count >= 2:
                    is_split = True
                    split_type = 'pair'
                    # 被动出牌时，拆对子的惩罚可以减轻（因为需要压制对手）
                    if is_passive:
                        impact_score = -0.1  # 被动出牌时，拆对子惩罚很轻（可以接受）
                    else:
                        impact_score = -0.3  # 主动出牌时，拆对子惩罚更重
                    break
                
                # 如果手牌中有3张或更多相同点数的牌，出单张就是拆三张
                if action_type == 'Single' and card_count >= 3:
                    is_split = True
                    split_type = 'trips'
                    # 被动出牌时，拆三张的惩罚可以减轻（因为需要压制对手）
                    if is_passive:
                        impact_score = -0.4  # 被动出牌时，拆三张惩罚减轻
                    else:
                        impact_score = -0.6  # 主动出牌时，拆三张惩罚更重
                    break
                
                # 如果手牌中有4张或更多相同点数的牌，出单张就是拆炸弹
                if action_type == 'Single' and card_count >= 4:
                    is_split = True
                    split_type = 'bomb'
                    impact_score = -0.9  # 拆炸弹负面影响最大（从-0.8增加到-0.9）
                    break
        
        if not is_split:
            return 1.0  # 不拆牌，最优
        
        # ⚠️ 开局阶段，拆牌惩罚加倍
        if game_phase == 'opening':
            impact_score *= 1.5  # 开局阶段拆牌惩罚加倍
        
        # 拆牌影响评分转换为0-1范围
        # impact_score是负数，需要转换为0-1范围
        # -0.9 -> 0.0, -0.6 -> 0.3, -0.3 -> 0.5, 0 -> 1.0
        return max(0.0, 1.0 + impact_score)
    
    def _calculate_weighted_scores(self, priority_factors: List[Dict], weights: Dict[str, float]) -> List[float]:
        """
        计算加权综合得分
        
        Args:
            priority_factors: 优先级因素列表
            weights: 权重字典
            
        Returns:
            综合得分列表
        """
        scores = []
        
        for factors in priority_factors:
            score = 0.0
            for factor_name, factor_value in factors.items():
                weight = weights.get(factor_name, 0.0)
                score += factor_value * weight
            scores.append(score)
        
        return scores
    
    def _record_decision(self, priority_factors: List[Dict], selected_idx: int, context: Dict):
        """记录决策（用于学习）"""
        if len(self.priority_history) >= self.max_history_size:
            # 删除最旧的记录
            self.priority_history.pop(0)
        
        record = {
            'priority_factors': priority_factors,
            'selected_idx': selected_idx,
            'context': context.copy(),
            'timestamp': datetime.now()
        }
        self.priority_history.append(record)
    
    def learn_optimal_weights(self, outcomes: List[Dict]) -> Dict[str, float]:
        """
        学习最优权重（基于历史决策和结果）
        
        Args:
            outcomes: 决策结果列表，每个元素包含 {'decision_idx', 'outcome': 'win'/'lose'/'draw'}
            
        Returns:
            学习到的最优权重
        """
        if len(self.priority_history) < 10 or len(outcomes) < 10:
            # 数据不足，返回基础权重
            return self.weight_adjuster.base_weights
        
        # 匹配历史决策和结果
        win_decisions = []
        lose_decisions = []
        
        for i, outcome in enumerate(outcomes):
            if i < len(self.priority_history):
                record = self.priority_history[i]
                if outcome.get('outcome') == 'win':
                    win_decisions.append(record)
                elif outcome.get('outcome') == 'lose':
                    lose_decisions.append(record)
        
        if not win_decisions or not lose_decisions:
            return self.weight_adjuster.base_weights
        
        # 计算各因素在胜利决策中的平均贡献
        optimal_weights = {}
        for factor_name in self.weight_adjuster.base_weights.keys():
            win_avg = np.mean([
                factors.get(factor_name, 0.0)
                for record in win_decisions
                for factors in record.get('priority_factors', [])
            ])
            lose_avg = np.mean([
                factors.get(factor_name, 0.0)
                for record in lose_decisions
                for factors in record.get('priority_factors', [])
            ])
            
            # 如果该因素在胜利决策中贡献更大，增加权重
            if win_avg > lose_avg and win_avg > 0:
                optimal_weights[factor_name] = self.weight_adjuster.base_weights[factor_name] * 1.2
            else:
                optimal_weights[factor_name] = self.weight_adjuster.base_weights[factor_name] * 0.8
        
        # 归一化
        total = sum(optimal_weights.values())
        if total > 0:
            optimal_weights = {k: v/total for k, v in optimal_weights.items()}
        
        return optimal_weights
    
    def _get_rank_value(self, rank: str, cur_rank: str = None) -> int:
        """
        获取牌值（用于比较）
        
        牌值大小关系：
        - 3-9, T, J, Q, K, A: 3-14
        - 级牌: 15 (可压制A及以下)
        - 小王(B): 16 (可压制级牌及以下)
        - 大王(R): 17 (可压制小王及以下)
        """
        rank_map = {
            '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
            '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14,
            'B': 16,  # 小王
            'R': 17   # 大王
        }
        if isinstance(rank, str):
            rank_char = rank[-1] if len(rank) > 1 else rank
            if cur_rank and rank_char == cur_rank:
                return 15  # 级牌值
            if rank_char in rank_map:
                return rank_map[rank_char]
        return 0
    
    def _get_card_power(self, context: Dict) -> str:
        """
        获取牌力（中等、强、差）
        
        牌力划分：
        - 牌力中等（5-7）
        - 牌力强（≥7）
        - 牌力差（<5）
        """
        my_remain = context.get('my_remain', DEFAULT_REST_CARDS)
        if my_remain < 5:
            return 'strong'  # 牌力强
        elif my_remain <= 7:
            return 'medium'  # 牌力中等
        else:
            return 'weak'  # 牌力差
    
    def _has_small_and_large_three_with_two(self, handcards: List, cur_rank: str) -> bool:
        """
        判断"有打有收"：是否有小三带二且有大三带二可回收
        
        小三带二：三张≤9的三带二（如三张4+对子2）
        大三带二：三张≥Q的三带二（如三张Q+对子5，三张K+对子3，三张A+对子6等），包括三张级牌
        """
        from collections import Counter
        
        # 统计每张牌的数量（按点数）
        rank_counts = {}
        for card in handcards:
            if len(card) >= 2:
                rank_char = card[-1] if len(card) > 1 else card
                if rank_char not in ['B', 'R']:  # 排除大小王
                    # 级牌特殊处理
                    if rank_char == cur_rank:
                        rank_key = cur_rank
                    else:
                        rank_key = rank_char
                    rank_counts[rank_key] = rank_counts.get(rank_key, 0) + 1
        
        # 检查是否有小三带二（三张≤9）
        has_small_three_with_two = False
        for rank_char, count in rank_counts.items():
            if count >= 3:  # 有三张
                rank_value = self._get_rank_value(rank_char, cur_rank)
                if rank_value <= 9:  # 小三带二（≤9）
                    # 检查是否有其他对子可以带（不一定是同一张牌的对子）
                    # 三带二只需要三张+任意一对
                    has_pair = any(c >= 2 for r, c in rank_counts.items() if r != rank_char)
                    if has_pair:
                        has_small_three_with_two = True
                        break
        
        # 检查是否有大三带二（三张≥Q或级牌）
        has_large_three_with_two = False
        for rank_char, count in rank_counts.items():
            if count >= 3:  # 有三张
                rank_value = self._get_rank_value(rank_char, cur_rank)
                if rank_value >= 12 or rank_char == cur_rank:  # 大三带二（≥Q或级牌）
                    # 检查是否有其他对子可以带
                    has_pair = any(c >= 2 for r, c in rank_counts.items() if r != rank_char)
                    if has_pair:
                        has_large_three_with_two = True
                        break
        
        return has_small_three_with_two and has_large_three_with_two
    
    def _should_use_trips_instead_of_three_with_two(self, handcards: List, cur_rank: str) -> bool:
        """
        判断特殊情况：对子较大时，宁肯只出三张，而不出三带二
        
        条件：
        - 有小钢板+两个3同张+4个以上对子
        - 对子较大，大于10以上的对子较多
        - 三张没有大于10以上的三张
        """
        from collections import Counter
        handcard_counts = Counter(handcards)
        
        # 统计三张和对子的数量
        trips_counts = {}
        pairs_counts = {}
        
        for card in handcards:
            if len(card) >= 2:
                rank_char = card[-1] if len(card) > 1 else card
                if rank_char not in ['B', 'R']:
                    if rank_char == cur_rank:
                        rank_char = cur_rank
                    trips_counts[rank_char] = trips_counts.get(rank_char, 0) + 1
        
        for rank_char, count in trips_counts.items():
            if count >= 2:
                pairs_counts[rank_char] = count // 2
        
        # 检查是否有小钢板（两个3同张）
        has_two_trips = False
        trip_ranks = []
        for rank_char, count in trips_counts.items():
            if count >= 3:
                trip_ranks.append(rank_char)
                if len(trip_ranks) >= 2:
                    # 检查是否连续
                    trip_values = [self._get_rank_value(r, cur_rank) for r in trip_ranks]
                    trip_values.sort()
                    if len(trip_values) >= 2 and trip_values[1] - trip_values[0] == 1:
                        has_two_trips = True
                        break
        
        # 检查是否有4个以上对子
        total_pairs = sum(pairs_counts.values())
        has_four_plus_pairs = total_pairs >= 4
        
        # 检查对子是否较大（大于10以上的对子较多）
        large_pairs_count = 0
        for rank_char, count in pairs_counts.items():
            rank_value = self._get_rank_value(rank_char, cur_rank)
            if rank_value > 10:  # 大于10的对子
                large_pairs_count += count
        
        # 检查三张是否没有大于10以上的三张
        has_large_trips = False
        for rank_char, count in trips_counts.items():
            if count >= 3:
                rank_value = self._get_rank_value(rank_char, cur_rank)
                if rank_value > 10:  # 大于10的三张
                    has_large_trips = True
                    break
        
        # 判断条件
        if has_two_trips and has_four_plus_pairs:
            if large_pairs_count >= 2 and not has_large_trips:
                return True  # 对子较大且三张没有大于10的，宁肯只出三张
        
        return False
    
    def _calculate_two_trips_score(self, candidate: List, context: Dict) -> float:
        """
        计算钢板（TwoTrips）评分
        
        策略：
        - 牌力中等（5-7）：小钢板先出（+0.3）
        - 牌力强（≥7）：小钢板后出，但避免憋在手上（+0.2）
        - 牌力差（<5）：小钢板不出（-0.2）
        - 一次出6张，减少手数（+0.4）
        - 特殊牌型，对手难管（+0.3）
        - 残局阶段：偷袭利器（+0.3）
        """
        base_score = 0.7  # 基础评分
        game_phase = context.get('game_phase', 'opening')
        card_power = self._get_card_power(context)
        action_cards = candidate[2] if len(candidate) > 2 and isinstance(candidate[2], list) else []
        
        # 一次出6张，减少手数
        if len(action_cards) == 6:
            base_score += 0.4
        
        # 特殊牌型，对手难管
        base_score += 0.3
        
        # 根据牌力调整
        if card_power == 'medium':
            base_score += 0.3  # 牌力中等，小钢板先出
        elif card_power == 'strong':
            base_score += 0.2  # 牌力强，后出但避免憋在手上
        elif card_power == 'weak':
            base_score -= 0.2  # 牌力差，不出
        
        # 残局阶段：偷袭利器
        if game_phase in ['endgame_early', 'endgame_late']:
            base_score += 0.3
        
        # 开局阶段：可以首发，但要首发小三连三（钢板）而不是小三连对（木板）
        if game_phase == 'opening':
            # 检查是否是小钢板
            if len(action_cards) == 6:
                # 提取牌值判断是否是小钢板
                cur_rank = context.get('cur_rank', '2')
                rank_values = []
                for card in action_cards:
                    if len(card) >= 2:
                        rank_char = card[-1] if len(card) > 1 else card
                        rank_value = self._get_rank_value(rank_char, cur_rank)
                        if rank_value not in rank_values:
                            rank_values.append(rank_value)
                if len(rank_values) >= 2:
                    rank_values.sort()
                    if rank_values[1] - rank_values[0] == 1:
                        # 是小钢板，可以首发
                        base_score += 0.1
        
        return min(1.0, max(0.0, base_score))
    
    def _calculate_three_pair_score(self, candidate: List, context: Dict) -> float:
        """
        计算三连对（ThreePair，木板）评分
        
        策略：
        - 开局阶段：首引一般不轻易出木板（-0.2）
        - 中局及以后：优先出木板（+0.3）
        - 一次出6张，减少手数（+0.4）
        - 特殊牌型，不易管压（+0.3）
        - 残局阶段：偷袭利器（+0.5）
        """
        base_score = 0.7  # 基础评分
        game_phase = context.get('game_phase', 'opening')
        action_cards = candidate[2] if len(candidate) > 2 and isinstance(candidate[2], list) else []
        
        # 一次出6张，减少手数
        if len(action_cards) == 6:
            base_score += 0.4
        
        # 特殊牌型，不易管压
        base_score += 0.3
        
        # 根据游戏阶段调整
        if game_phase == 'opening':
            base_score -= 0.2  # 开局阶段，首引一般不轻易出木板
        elif game_phase in ['mid_early', 'mid_late']:
            base_score += 0.3  # 中局及以后，优先出木板
        
        # 残局阶段：偷袭利器
        if game_phase in ['endgame_early', 'endgame_late']:
            base_score += 0.5
        
        return min(1.0, max(0.0, base_score))
    
    def _calculate_three_with_two_score(self, candidate: List, context: Dict) -> float:
        """
        计算三带二（ThreeWithTwo，夯）评分
        
        策略：
        - 有打有收：有小三带二且有大三带二可回收（+0.4）
        - 强牌非常多：先处理不够大的三带二（+0.3）
        - 一次出5张，减少手数（+0.3）
        - 可带走对子赘牌（+0.2）
        - 情况不明，不宜先出（-0.1）
        """
        base_score = 0.6  # 基础评分
        game_phase = context.get('game_phase', 'opening')
        handcards = context.get('handcards', [])
        cur_rank = context.get('cur_rank') or context.get('curRank', '2')
        action_cards = candidate[2] if len(candidate) > 2 and isinstance(candidate[2], list) else []
        
        # 一次出5张，减少手数
        if len(action_cards) == 5:
            base_score += 0.3
        
        # 可带走对子赘牌
        base_score += 0.2
        
        # 判断"有打有收"
        if self._has_small_and_large_three_with_two(handcards, cur_rank):
            base_score += 0.4  # 有打有收，优先
        
        # 强牌非常多，先处理不够大的三带二
        card_power = self._get_card_power(context)
        if card_power == 'strong':
            # 检查是否是不够大的三带二
            if len(action_cards) == 5:
                # 提取三张的牌值
                from collections import Counter
                card_counts = Counter([c[-1] if len(c) > 1 else c for c in action_cards])
                trips_rank = None
                for rank_char, count in card_counts.items():
                    if count == 3:
                        trips_rank = rank_char
                        break
                if trips_rank:
                    trips_value = self._get_rank_value(trips_rank, cur_rank)
                    if trips_value < 12:  # 不够大的三带二（<Q）
                        base_score += 0.3
        
        # 情况不明，不宜先出（开局阶段）
        if game_phase == 'opening':
            base_score -= 0.1
        
        return min(1.0, max(0.0, base_score))
    
    def _calculate_trips_score(self, candidate: List, context: Dict) -> float:
        """
        计算三张（Trips）评分
        
        特殊情况：
        - 对子较大时，宁肯只出三张，而不出三带二
        - "三张"小，对子大：让对手误以为没有对子，引起对手用大的三个头压牌，打对后遭遇出牌人大对上手
        """
        base_score = 0.4  # 基础评分（三张的基础评分较低）
        handcards = context.get('handcards', [])
        cur_rank = context.get('cur_rank') or context.get('curRank', '2')
        
        # 特殊情况：对子较大时，宁肯只出三张
        if self._should_use_trips_instead_of_three_with_two(handcards, cur_rank):
            base_score += 0.3  # 提高三张的优先级
        
        return min(1.0, max(0.0, base_score))

