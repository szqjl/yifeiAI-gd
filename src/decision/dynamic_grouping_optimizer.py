"""
动态组牌优化模块
在行牌过程中根据游戏状态动态调整组牌策略

核心原理：
1. 组牌切忌一开始就把牌配死，应根据牌局形势灵活调整
2. 在行牌过程中，根据剩余手牌、对手出牌情况等动态重新评估组牌
3. 根据游戏阶段、牌力变化、对手行为等调整组牌策略
"""
from typing import Dict, List, Tuple, Optional
from collections import Counter
from src.decision.card_grouping_strategy import evaluate_grouping_effect, grouping_strategy
from src.decision.card_power_evaluator import calculate_card_power


class DynamicGroupingOptimizer:
    """
    动态组牌优化器
    
    在行牌过程中动态调整组牌策略，避免"把牌配死"
    """
    
    def __init__(self):
        self.last_hand_count = 27  # 上次手牌数
        self.last_power = 0.0  # 上次牌力
        self.grouping_history = []  # 组牌历史记录
        self.opponent_behavior = {}  # 对手行为记录
        
    def should_reoptimize(self, game_state: Dict) -> bool:
        """
        判断是否需要重新优化组牌
        
        触发条件：
        1. 手牌数发生显著变化（减少3张以上）
        2. 游戏阶段变化（开局->中局->残局）
        3. 牌力发生显著变化
        4. 对手出牌后（需要重新评估组牌策略）
        5. 剩余手牌数进入关键区间（如10张以下）
        
        Returns:
            bool: 是否需要重新优化
        """
        hand_cards = game_state.get("hand", [])
        current_hand_count = len(hand_cards)
        
        # 条件1：手牌数显著减少
        hand_count_change = self.last_hand_count - current_hand_count
        if hand_count_change >= 3:
            return True
        
        # 条件2：进入关键区间（残局）
        if current_hand_count <= 10 and self.last_hand_count > 10:
            return True
        
        # 条件3：游戏阶段变化
        game_phase = game_state.get("game_phase", "opening")
        opponent_rest_cards = game_state.get("opponent_rest_cards", 27)
        
        # 判断阶段变化
        if opponent_rest_cards >= 20:
            new_phase = "opening"
        elif opponent_rest_cards >= 10:
            new_phase = "mid"
        else:
            new_phase = "endgame"
        
        if game_phase != new_phase:
            return True
        
        # 条件4：对手出牌后（通过greater_action判断）
        greater_action = game_state.get("greater_action", [])
        if greater_action and len(greater_action) > 0:
            # 记录对手出牌行为
            action_type = greater_action[0] if isinstance(greater_action, list) else str(greater_action)
            if action_type not in ["PASS", "pass"]:
                return True
        
        return False
    
    def optimize_grouping(self, hand_cards: List[str], action_list: List, 
                         game_state: Dict) -> Dict:
        """
        动态优化组牌策略
        
        根据当前游戏状态，重新评估和优化组牌策略
        
        Args:
            hand_cards: 当前手牌
            action_list: 可用动作列表
            game_state: 游戏状态
            
        Returns:
            {
                'optimized_suggestions': 优化后的组牌建议,
                'adjustments': 调整说明,
                'reasons': 优化原因
            }
        """
        if not hand_cards or not action_list:
            return {'optimized_suggestions': [], 'adjustments': [], 'reasons': []}
        
        # 获取游戏状态信息
        game_phase = game_state.get("game_phase", "opening")
        cur_rank = game_state.get("cur_rank", "2")
        opponent_rest_cards = game_state.get("opponent_rest_cards", 27)
        my_rest_cards = len(hand_cards)
        
        # 计算当前牌力
        power_result = calculate_card_power(
            hand_cards,
            game_phase=game_phase,
            opponent_rest_cards=opponent_rest_cards,
            cur_level_rank=int(cur_rank) if cur_rank.isdigit() else 10
        )
        current_power = power_result['total_power']
        
        # 判断游戏阶段
        if opponent_rest_cards >= 20:
            actual_phase = "opening"
        elif opponent_rest_cards >= 10:
            actual_phase = "mid"
        else:
            actual_phase = "endgame"
        
        # 获取对手出牌信息
        greater_action = game_state.get("greater_action", [])
        opponent_action_type = None
        if greater_action and len(greater_action) > 0:
            opponent_action_type = greater_action[0] if isinstance(greater_action, list) else str(greater_action)
        
        # 调用组牌策略评估
        grouping_result = grouping_strategy(
            hand_cards=hand_cards,
            action_list=action_list,
            game_phase=actual_phase,
            power=current_power,
            cur_rank=cur_rank
        )
        
        suggestions = grouping_result.get('suggestions', [])
        
        # 根据游戏状态动态调整评分
        adjustments = []
        reasons = []
        
        # 调整1：残局阶段，优先减少手数
        if actual_phase == "endgame":
            for sugg in suggestions:
                if sugg.get('rounds_reduced', 0) > 0:
                    sugg['score'] += 30.0  # 残局阶段，减少轮次更重要
                    adjustments.append(f"残局阶段，减少轮次加分+30")
                    reasons.append("残局阶段优先减少手数")
        
        # 调整2：根据对手出牌行为调整
        if opponent_action_type:
            # 如果对手不吃某种牌型，可以调整组牌策略
            if opponent_action_type not in ["PASS", "pass"]:
                # 记录对手行为
                if opponent_action_type not in self.opponent_behavior:
                    self.opponent_behavior[opponent_action_type] = 0
                self.opponent_behavior[opponent_action_type] += 1
                
                # 如果对手多次不吃某种牌型，可以调整组牌
                if self.opponent_behavior.get(opponent_action_type, 0) >= 2:
                    # 对手不吃这种牌型，可以拆成这种牌型打出
                    for sugg in suggestions:
                        action_idx = sugg.get('action_index', -1)
                        if action_idx >= 0 and action_idx < len(action_list):
                            action = action_list[action_idx]
                            action_type = action[0] if isinstance(action, list) else str(action)
                            if action_type == opponent_action_type:
                                sugg['score'] += 20.0
                                adjustments.append(f"对手不吃{opponent_action_type}，调整组牌策略")
                                reasons.append(f"根据对手行为调整：对手不吃{opponent_action_type}")
        
        # 调整3：手牌数较少时，优先减少单牌
        if my_rest_cards <= 10:
            for sugg in suggestions:
                if sugg.get('singles_reduced', 0) > 0:
                    sugg['score'] += 25.0
                    adjustments.append(f"手牌较少({my_rest_cards}张)，减少单牌加分+25")
                    reasons.append("手牌较少时优先减少单牌")
        
        # 调整4：牌力变化时调整策略
        power_change = current_power - self.last_power
        if abs(power_change) >= 2.0:
            if power_change > 0:
                # 牌力增强，可以更激进
                for sugg in suggestions:
                    if sugg.get('rounds_reduced', 0) > 0:
                        sugg['score'] += 15.0
                        adjustments.append("牌力增强，更激进组牌")
                        reasons.append("牌力增强，优先减少轮次")
            else:
                # 牌力减弱，需要保守
                for sugg in suggestions:
                    # 保留炸弹更重要
                    action_idx = sugg.get('action_index', -1)
                    if action_idx >= 0 and action_idx < len(action_list):
                        action = action_list[action_idx]
                        action_type = action[0] if isinstance(action, list) else str(action)
                        if action_type in ["Bomb", "BOMB"]:
                            sugg['score'] += 20.0
                            adjustments.append("牌力减弱，保留炸弹")
                            reasons.append("牌力减弱，优先保留炸弹")
        
        # 调整5：根据剩余手牌数调整组牌策略
        if my_rest_cards <= 5:
            # 残局最后阶段，优先出能走完的牌型
            for sugg in suggestions:
                action_idx = sugg.get('action_index', -1)
                if action_idx >= 0 and action_idx < len(action_list):
                    action = action_list[action_idx]
                    action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
                    if len(action_cards) >= my_rest_cards * 0.6:  # 能出大部分手牌
                        sugg['score'] += 40.0
                        adjustments.append(f"残局最后阶段，优先出能走完的牌型")
                        reasons.append("残局最后阶段，优先减少手数")
        
        # 更新状态
        self.last_hand_count = my_rest_cards
        self.last_power = current_power
        
        return {
            'optimized_suggestions': suggestions,
            'adjustments': adjustments,
            'reasons': reasons,
            'current_phase': actual_phase,
            'current_power': current_power,
            'hand_count': my_rest_cards
        }
    
    def get_grouping_recommendation(self, hand_cards: List[str], action_list: List,
                                   game_state: Dict) -> Optional[Dict]:
        """
        获取组牌推荐
        
        根据动态优化结果，返回最佳组牌建议
        
        Returns:
            {
                'best_action_index': 最佳动作索引,
                'score': 评分,
                'reason': 推荐原因,
                'grouping_analysis': 组牌分析
            }
        """
        # 检查是否需要重新优化
        if not self.should_reoptimize(game_state):
            return None
        
        # 执行动态优化
        optimization_result = self.optimize_grouping(hand_cards, action_list, game_state)
        
        suggestions = optimization_result.get('optimized_suggestions', [])
        
        if not suggestions:
            return None
        
        # 找到评分最高的建议
        best_suggestion = max(suggestions, key=lambda x: x.get('score', 0))
        
        return {
            'best_action_index': best_suggestion.get('action_index', -1),
            'score': best_suggestion.get('score', 0),
            'reason': ', '.join(best_suggestion.get('reasons', [])),
            'grouping_analysis': {
                'rounds_reduced': best_suggestion.get('rounds_reduced', 0),
                'singles_reduced': best_suggestion.get('singles_reduced', 0),
                'adjustments': optimization_result.get('adjustments', []),
                'optimization_reasons': optimization_result.get('reasons', [])
            }
        }
    
    def reset(self):
        """重置优化器状态"""
        self.last_hand_count = 27
        self.last_power = 0.0
        self.grouping_history = []
        self.opponent_behavior = {}

