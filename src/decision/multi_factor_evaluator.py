# -*- coding: utf-8 -*-
"""
多因素评估器 (Multi Factor Evaluator)
功能：
- 综合评估出牌动作的价值
- 结合牌型、剩余牌、配合、风险等因素
"""

from typing import Dict, List, Optional, Tuple
import sys
from pathlib import Path

# 将 src 目录添加到系统路径
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from game_logic.enhanced_state import EnhancedGameStateManager
from game_logic.hand_combiner import HandCombiner
from decision.cooperation import CooperationStrategy
from decision.game_stage_analyzer import GameStageAnalyzer
from decision.card_grouping_strategy import grouping_strategy


class MultiFactorEvaluator:
    """多因素评估器类"""
    
    def __init__(self, state_manager: EnhancedGameStateManager, 
                 combiner: HandCombiner,
                 cooperation: CooperationStrategy):
        """
        初始化多因素评估器
        
        Args:
            state_manager: 游戏状态管理器
            combiner: 手牌组合器
            cooperation: 配合策略
        """
        self.state = state_manager
        self.combiner = combiner
        self.cooperation = cooperation
        
        # 添加游戏阶段分析器
        self.game_stage_analyzer = GameStageAnalyzer()
        
        # 评估权重配置
        self.weights = {
            "remaining_cards": 0.20,
            "card_type_value": 0.20,
            "cooperation": 0.20,
            "risk": 0.15,
            "timing": 0.15,  # 增加时机评估权重
            "grouping_strategy": 0.07,  # 增加组牌策略权重（包含单张策略）
            "hand_structure": 0.03
        }
    
    def evaluate_all_actions(self, action_list: List[List], 
                            target_action: Optional[List] = None) -> List[Tuple[int, float]]:
        """
        评估所有可选动作
        
        Args:
            action_list: 动作列表
            target_action: 目标动作（被动出牌时）
        
        Returns:
            评估结果列表 [(索引, 分数), ...]，按分数降序排列
        """
        evaluations = []
        
        for idx, action in enumerate(action_list):
            if action[0] == "PASS":
                score = 0.0
            else:
                score = self._evaluate_action(action, target_action)
            evaluations.append((idx, score))
        
        # 按分数降序排序
        evaluations.sort(key=lambda x: x[1], reverse=True)
        return evaluations
    
    def _evaluate_action(self, action: List, target_action: Optional[List]) -> float:
        """
        评估单个动作
        
        Args:
            action: 动作
            target_action: 目标动作
        
        Returns:
            评估分数
        """
        scores = {}
        
        # 1. 获取游戏状态信息
        hand_cards = self.state.get_player_cards()
        game_stage = self.game_stage_analyzer.get_game_stage(hand_cards)
        cur_rank = self.state.get_current_rank()
        
        # 判断是否有王和级牌
        has_king = any('B' in card or 'R' in card for card in hand_cards)
        has_level_card = any(cur_rank in card for card in hand_cards)
        
        # 2. 牌型价值
        scores["card_type_value"] = self._evaluate_card_type_value(action)
        
        # 3. 剩余牌数影响
        scores["remaining_cards"] = self._evaluate_remaining_cards(action)
        
        # 4. 配合度
        scores["cooperation"] = self._evaluate_cooperation(action, target_action)
        
        # 5. 风险评估
        scores["risk"] = self._evaluate_risk(action, has_king, has_level_card)
        
        # 6. 时机评估
        scores["timing"] = self._evaluate_timing(action, target_action)
        
        # 7. 手牌结构影响
        scores["hand_structure"] = self._evaluate_hand_structure(action)
        
        # 8. 组牌策略评估（新增）
        # 获取当前动作的卡牌
        action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
        action_type = action[0] if len(action) > 0 else "PASS"
        
        # 调用组牌策略
        grouping_result = grouping_strategy(
            hand_cards=hand_cards,
            action_list=[action],  # 只评估当前动作
            game_phase=game_stage,
            power=5.0,  # 临时使用默认值，后续可以从state中获取实际牌力
            cur_rank=cur_rank
        )
        
        # 从组牌策略结果中获取评分
        grouping_score = 0.0
        if grouping_result and "suggestions" in grouping_result:
            suggestions = grouping_result["suggestions"]
            if suggestions:
                # 取第一个建议的分数（因为我们只传递了一个动作）
                grouping_score = suggestions[0]["score"] / 100.0  # 归一化到 0-1 范围
        
        # 添加组牌策略评分
        scores["grouping_strategy"] = grouping_score
        
        # 更新权重配置，添加组牌策略权重
        if "grouping_strategy" not in self.weights:
            # 重新分配权重，确保总和为1.0
            # 将hand_structure的权重部分转移给grouping_strategy
            self.weights["hand_structure"] = 0.02
            self.weights["grouping_strategy"] = 0.03
        
        # 计算加权总分
        total_score = sum(scores[factor] * self.weights[factor] 
                         for factor in scores)
        
        return total_score
    
    def _evaluate_card_type_value(self, action: List) -> float:
        """评估牌型价值"""
        if not action or action[0] == "PASS":
            return 0.0
        
        type_values = {
            "Bomb": 20.0,
            "StraightFlush": 18.0,
            "TwoTrips": 15.0,
            "ThreePair": 12.0,
            "Straight": 10.0,
            "ThreeWithTwo": 8.0,
            "Trips": 6.0,
            "Pair": 4.0,
            "Single": 4.0  # 提高单牌基础价值，与合作策略保持一致
        }
        
        base_value = type_values.get(action[0], 1.0)
        
        # 归一化到 0-1
        return min(base_value / 20.0, 1.0)
    
    def _evaluate_remaining_cards(self, action: List) -> float:
        """评估剩余牌数影响"""
        # 出牌越多，剩余越少，分数越高
        cards = action[2] if len(action) > 2 else []
        card_count = len(cards) if isinstance(cards, list) else 1
        
        # 计算出牌数量占当前手牌的比例（假设当前手牌27张为初始值）
        # 出牌数量越多，剩余越少，分数越高
        return min(card_count / 27.0, 1.0)
    
    def _evaluate_cooperation(self, action: List, target_action: Optional[List]) -> float:
        """评估配合度"""
        if not target_action:
            return 0.5  # 主动出牌，默认配合度
        
        # 计算动作价值
        action_value = self.cooperation._calculate_action_value(action)
        target_value = self.cooperation._calculate_action_value(target_action)
        
        # 如果动作价值大于目标价值
        if action_value > target_value:
            diff = action_value - target_value
            if diff < 3:  # 价值差异很小，完美配合
                return 0.9
            elif diff < 8:  # 价值差异适中，良好配合
                return 0.7
            elif diff < 15:  # 价值差异较大，一般配合
                return 0.5
            else:  # 价值差异很大，过度压制
                return 0.3
        
        return 0.2  # 无法管上
    
    def _evaluate_risk(self, action: List, has_king: bool = False, has_level_card: bool = False) -> float:
        """
        评估风险
        """
        # 炸弹风险低（强大），高价值单张风险高，小牌风险低
        if action[0] == "Bomb":
            return 0.2  # 低风险（强大的牌型）
        elif action[0] in ["Single", "SINGLE"]:
            # 获取牌值
            rank = action[1] if len(action) > 1 else ""
            # 有王或级牌保护时，降低单张风险
            if has_king or has_level_card:
                # 有王/级牌保护，即使是高价值单张，风险也降低
                if rank in ["2", "A", "K", "B", "R"]:  # 高价值牌，风险降低
                    return 0.3  # 风险降低到低风险
                elif rank in ["Q", "J", "T", "9"]:  # 中价值牌，风险降低
                    return 0.25  # 风险降低到很低
                else:  # 低价值牌，风险很低
                    return 0.2
            # 没有保护时，正常评估风险
            if rank in ["2", "A", "K", "B", "R"]:  # 高价值牌，风险高
                return 0.7
            elif rank in ["Q", "J", "T", "9"]:  # 中价值牌，风险中
                return 0.5
            else:  # 低价值牌，风险低
                return 0.3
        elif action[0] in ["Pair", "PAIR"]:
            # 获取牌值
            rank = action[1] if len(action) > 1 else ""
            if rank in ["2", "A", "K", "B", "R"]:  # 高价值牌，风险高
                return 0.7
            elif rank in ["Q", "J", "T", "9"]:  # 中价值牌，风险中
                return 0.5
            else:  # 低价值牌，风险低
                return 0.3
        elif action[0] in ["Straight", "ThreePair", "TwoTrips"]:  # 复杂牌型，风险中
            return 0.6
        else:  # 其他牌型，风险中
            return 0.5
    
    def _evaluate_timing(self, action: List, target_action: Optional[List]) -> float:
        """
        评估时机
        """
        # 获取游戏阶段信息
        player_cards = self.state.get_player_cards()
        game_stage = self.game_stage_analyzer.get_game_stage(player_cards)
        
        # 获取已出牌记录
        actions = self.state.get_action_history()
        is_first_round = self.game_stage_analyzer.is_first_round(actions)
        
        # 获取动作类型
        action_type = action[0]
        target_action_type = target_action[0] if target_action else "PASS"
        
        # 强牌和弱牌类型定义
        strong_types = ["Bomb", "StraightFlush"]
        weak_types = ["Single", "Pair"]
        
        # 直接评估时机价值，不需要调用外部函数
        timing_value = 0.6  # 默认时机价值
        
        # 特殊情况1：第一轮强牌炸弱牌，时机价值极低
        if is_first_round:
            if action_type in strong_types and target_action_type in weak_types:
                timing_value = 0.05
                return timing_value
        
        # 特殊情况2：初期强牌炸弱牌，时机价值很低
        if game_stage == "early":
            if action_type in strong_types and target_action_type in weak_types:
                timing_value = 0.1
                return timing_value
        
        # 特殊情况3：残局用强牌，时机价值很高
        if game_stage == "endgame" and action_type in strong_types:
            timing_value = 0.9
            return timing_value
        
        # 特殊情况4：强牌炸强牌，时机价值中等
        if action_type in strong_types and target_action_type in strong_types:
            timing_value = 0.7
            return timing_value
        
        # 特殊情况5：强牌炸中等牌型，时机价值较低
        if action_type in strong_types and target_action_type not in weak_types + strong_types:
            timing_value = 0.5
            return timing_value
        
        # 特殊情况6：普通时机
        return timing_value
    
    def _evaluate_hand_structure(self, action: List) -> float:
        """评估手牌结构影响"""
        # 简单的结构评估
        if action[0] == "Bomb":
            return 0.7  # 炸弹通常改善手牌结构
        elif action[0] in ["Single", "Pair"]:  # 单张对子可能破坏结构
            return 0.4
        else:  # 其他牌型，中性影响
            return 0.5

