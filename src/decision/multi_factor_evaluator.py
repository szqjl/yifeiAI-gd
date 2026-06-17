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
        
        # 评估权重配置 - 决策质量提升版本
        # 增加对手建模和策略组合因子，提升决策质量
        self.weights = {
            "grouping_strategy": 0.25,    # 战术规则核心
            "remaining_cards": 0.20,      # 出牌积极性
            "card_type_value": 0.20,      # 牌型价值
            "cooperation": 0.10,          # 配合度
            "risk": 0.08,                 # 风险评估
            "timing": 0.07,               # 时机评估
            "opponent_modeling": 0.05,    # 新增：对手建模
            "strategy_combination": 0.05  # 新增：策略组合
        }
    
    def evaluate_all_actions(self, action_list: List[List],
                            target_action: Optional[List] = None,
                            game_context: Optional[Dict] = None) -> List[Tuple[int, float]]:
        """
        评估所有可选动作

        Args:
            action_list: 动作列表
            target_action: 目标动作（被动出牌时）
            game_context: 游戏上下文信息

        Returns:
            评估结果列表 [(索引, 分数), ...]，按分数降序排列
        """
        evaluations = []

        # 分析游戏阶段
        game_phase = self._analyze_game_phase(game_context)

        for idx, action in enumerate(action_list):
            if action[0] == "PASS":
                score = 0.0
            else:
                # 使用动态评估，根据游戏阶段调整
                score = self._dynamic_evaluation(action, target_action, game_phase)
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
        player_remain_cards = self.state.get_player_cards()
        game_stage = self.game_stage_analyzer.get_game_stage(player_remain_cards)
        cur_rank = self.state.get_current_rank()
        
        # 判断是否有王和级牌
        my_hand_cards = self.state.hand_cards
        has_king = any('B' in card or 'R' in card for card in my_hand_cards)
        has_level_card = any(cur_rank in card for card in my_hand_cards)
        
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
            hand_cards=my_hand_cards,  # 修复：使用正确的变量名
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
                # 进一步优化：使用原始分数，除以50进行温和归一化，保留更多战术信息
                raw_score = suggestions[0]["score"]
                grouping_score = raw_score / 50.0  # 更温和的归一化，保留战术强度
        
        # 添加组牌策略评分
        scores["grouping_strategy"] = grouping_score

        # 9. 对手建模评估（新增）
        scores["opponent_modeling"] = self._evaluate_opponent_modeling(action, target_action)

        # 10. 策略组合评估（新增）
        scores["strategy_combination"] = self._evaluate_strategy_combination(action)

        # 确保所有评分因子都有对应的权重
        for factor in scores:
            if factor not in self.weights:
                print(f"Warning: Missing weight for factor: {factor}, using default 0.1")
                self.weights[factor] = 0.1

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

    def _analyze_game_phase(self, game_context: Optional[Dict]) -> str:
        """分析游戏阶段

        Args:
            game_context: 游戏上下文信息

        Returns:
            游戏阶段: 'early', 'mid', 'late'
        """
        if not game_context:
            return 'mid'  # 默认中期

        # 基于剩余牌数判断游戏阶段
        player_cards = game_context.get('player_cards', [])
        remaining_count = len(player_cards)

        if remaining_count >= 15:
            return 'early'  # 早期：15张以上
        elif remaining_count >= 8:
            return 'mid'    # 中期：8-14张
        else:
            return 'late'   # 后期：7张以下

    def _dynamic_evaluation(self, action: List, target_action: Optional[List], game_phase: str) -> float:
        """动态评估：根据游戏阶段调整评估策略

        Args:
            action: 动作
            target_action: 目标动作
            game_phase: 游戏阶段 ('early', 'mid', 'late')

        Returns:
            动态评估分数
        """
        # 基础评估
        base_score = self._evaluate_action(action, target_action)

        # 根据游戏阶段调整权重
        phase_adjustments = {
            'early': {
                # 早期：强调减少轮次，积极出牌
                'grouping_strategy': 1.2,  # 提高战术权重
                'remaining_cards': 1.1,    # 鼓励出牌
                'card_type_value': 0.9,    # 降低牌型权重
            },
            'mid': {
                # 中期：平衡发展
                'grouping_strategy': 1.0,  # 标准权重
                'remaining_cards': 1.0,
                'card_type_value': 1.0,
                'opponent_modeling': 1.1,  # 提高对手建模权重
            },
            'late': {
                # 后期：全力以赴，重视牌型价值
                'grouping_strategy': 0.9,  # 降低战术权重
                'remaining_cards': 1.2,    # 强烈鼓励出牌
                'card_type_value': 1.1,    # 提高牌型权重
                'strategy_combination': 1.1,  # 重视策略组合
            }
        }

        adjustments = phase_adjustments.get(game_phase, {})

        # 应用阶段调整
        adjusted_score = base_score
        for factor, adjustment in adjustments.items():
            if factor in self.weights:
                # 直接调整基础得分中的对应因子权重
                # 这是一个简化的实现，通过调整权重来影响决策
                weight_diff = (adjustment - 1.0) * self.weights[factor]
                adjusted_score += (base_score * 0.1 * weight_diff)  # 小幅调整

        return adjusted_score

    def _evaluate_opponent_modeling(self, action: List, target_action: Optional[List]) -> float:
        """评估对手建模因子

        基于对手历史行为预测，评估当前动作的对抗价值

        Args:
            action: 当前动作
            target_action: 目标动作（被动出牌时）

        Returns:
            对手建模评分 (0-1)
        """
        if not action or action[0] == "PASS":
            return 0.5  # PASS的中性评分

        # 基础评估：根据动作类型判断对抗价值
        action_type = action[0]

        # 强力动作在对抗中更有价值
        if action_type == "Bomb":
            return 0.8  # 炸弹具有最高对抗价值
        elif action_type in ["Straight", "StraightFlush"]:
            return 0.7  # 顺子具有较强控制力
        elif action_type in ["ThreeWithTwo", "ThreePair"]:
            return 0.6  # 组合牌有一定对抗价值
        elif action_type in ["Three", "TwoTrips"]:
            return 0.5  # 中等对抗价值
        elif action_type in ["Pair", "Single"]:
            return 0.3  # 基础牌型，对抗价值较低
        else:
            return 0.4  # 其他类型，中性评估

    def _evaluate_strategy_combination(self, action: List) -> float:
        """评估策略组合因子

        考虑动作在整体策略中的作用和多回合价值

        Args:
            action: 当前动作

        Returns:
            策略组合评分 (0-1)
        """
        if not action or action[0] == "PASS":
            return 0.3  # PASS在策略组合中价值较低

        action_type = action[0]

        # 评估策略组合价值
        if action_type == "Bomb":
            return 0.6  # 炸弹在策略组合中很重要，但不是首选
        elif action_type in ["StraightFlush", "Straight"]:
            return 0.8  # 长牌型在策略组合中价值很高
        elif action_type == "ThreeWithTwo":
            return 0.7  # 带牌组合在策略中很灵活
        elif action_type in ["ThreePair", "TwoTrips"]:
            return 0.5  # 多牌组合有一定策略价值
        elif action_type == "Three":
            return 0.4  # 基础三张，中等策略价值
        elif action_type in ["Pair", "Single"]:
            return 0.2  # 基础牌型，策略价值较低
        else:
            return 0.4  # 其他类型，中性评估



# ==================== 动态优先级系统 ====================
# 根据 YF掼蛋硬编码优化规范实现
# 需求: 3.1-3.5, 属性: 11-15

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PriorityContext:
    """优先级调整上下文"""
    my_remain: int = 27
    teammate_remain: int = 27
    next_player_remain: int = 27
    opponent_remain: List[int] = None
    pass_count: int = 0
    game_stage: str = "early"
    is_endgame: bool = False
    endgame_type: str = "normal"
    teammate_is_leading: bool = False
    
    def __post_init__(self):
        if self.opponent_remain is None:
            self.opponent_remain = [27, 27]


class ContextAdjuster(ABC):
    """
    上下文调整器抽象基类
    
    实现需求3的优先级调整框架
    """
    
    def __init__(self, weight: float = 1.0):
        """
        初始化调整器
        
        Args:
            weight: 调整器权重
        """
        self.weight = weight
        self.name = self.__class__.__name__
    
    @abstractmethod
    def adjust(self, base_scores: List[float], action_list: List[List], 
               context: PriorityContext) -> List[float]:
        """
        调整优先级分数
        
        Args:
            base_scores: 基础分数列表
            action_list: 动作列表
            context: 优先级上下文
            
        Returns:
            调整后的分数列表
        """
        pass
    
    def get_adjustment_info(self) -> Dict:
        """获取调整信息"""
        return {"name": self.name, "weight": self.weight}


class NextPlayerAdjuster(ContextAdjuster):
    """
    下家牌数调整器
    
    实现需求3.1和属性11：根据下家牌数调整单张优先级
    """
    
    def __init__(self, weight: float = 1.0):
        super().__init__(weight)
    
    def adjust(self, base_scores: List[float], action_list: List[List], 
               context: PriorityContext) -> List[float]:
        """
        调整优先级
        
        **属性 11: 下家单张优先级调整**
        *对于任何* 下家剩余牌数为1张的情况，系统应该降低单张出牌优先级
        **验证: 需求 3.1**
        """
        adjusted = base_scores.copy()
        
        # 下家只剩1张牌时，降低单张优先级
        if context.next_player_remain == 1:
            for i, action in enumerate(action_list):
                if action[0] == "Single":
                    # 大幅降低单张优先级，避免送牌
                    adjusted[i] *= 0.3 * self.weight
        
        # 下家牌少时（<=3张），也要谨慎出单张
        elif context.next_player_remain <= 3:
            for i, action in enumerate(action_list):
                if action[0] == "Single":
                    adjusted[i] *= 0.6 * self.weight
        
        return adjusted


class PassCountAdjuster(ContextAdjuster):
    """
    PASS次数调整器
    
    实现需求3.2和属性12：根据连续PASS次数调整出牌优先级
    """
    
    def __init__(self, weight: float = 1.0, threshold: int = 5):
        super().__init__(weight)
        self.threshold = threshold
    
    def adjust(self, base_scores: List[float], action_list: List[List], 
               context: PriorityContext) -> List[float]:
        """
        调整优先级
        
        **属性 12: PASS次数优先级调整**
        *对于任何* 连续PASS次数超过5次的情况，系统应该提高出牌动作优先级
        **验证: 需求 3.2**
        """
        adjusted = base_scores.copy()
        
        if context.pass_count >= self.threshold:
            # 连续PASS太多，提高出牌优先级
            boost_factor = 1.0 + (context.pass_count - self.threshold + 1) * 0.1 * self.weight
            boost_factor = min(boost_factor, 1.5)  # 最多提升50%
            
            for i, action in enumerate(action_list):
                if action[0] != "PASS":
                    adjusted[i] *= boost_factor
        
        return adjusted


class EndgameAdjuster(ContextAdjuster):
    """
    残局调整器
    
    实现需求3.3和属性13：根据残局类型调整各牌型优先级
    """
    
    def __init__(self, weight: float = 1.2):
        super().__init__(weight)
    
    def adjust(self, base_scores: List[float], action_list: List[List], 
               context: PriorityContext) -> List[float]:
        """
        调整优先级
        
        **属性 13: 残局优先级调整**
        *对于任何* 处于残局阶段的情况，系统应该根据残局类型调整各牌型优先级
        **验证: 需求 3.3**
        """
        adjusted = base_scores.copy()
        
        if not context.is_endgame:
            return adjusted
        
        # 根据残局类型调整
        if context.endgame_type == "rush":
            # 冲刺型：提高大牌型优先级
            for i, action in enumerate(action_list):
                if action[0] in ["Bomb", "StraightFlush"]:
                    adjusted[i] *= 1.3 * self.weight
                elif action[0] in ["Straight", "ThreeWithTwo"]:
                    adjusted[i] *= 1.2 * self.weight
        
        elif context.endgame_type == "defend":
            # 防守型：提高PASS和小牌优先级
            for i, action in enumerate(action_list):
                if action[0] == "PASS":
                    adjusted[i] = 0.8 * self.weight  # 给PASS一个较高的分数
                elif action[0] == "Single":
                    # 检查是否是小牌
                    rank = action[1] if len(action) > 1 else ""
                    if rank in ["3", "4", "5", "6", "7"]:
                        adjusted[i] *= 1.2 * self.weight
        
        elif context.endgame_type == "cooperate":
            # 配合型：提高配合动作优先级
            for i, action in enumerate(action_list):
                if action[0] == "PASS":
                    adjusted[i] = 0.6 * self.weight
        
        elif context.endgame_type == "control":
            # 控制型：平衡调整
            for i, action in enumerate(action_list):
                if action[0] in ["Pair", "Trips"]:
                    adjusted[i] *= 1.1 * self.weight
        
        return adjusted


class TeammateAdjuster(ContextAdjuster):
    """
    队友状态调整器
    
    实现需求3.4和属性14：根据队友状态调整PASS优先级
    """
    
    def __init__(self, weight: float = 1.3):
        super().__init__(weight)
    
    def adjust(self, base_scores: List[float], action_list: List[List], 
               context: PriorityContext) -> List[float]:
        """
        调整优先级
        
        **属性 14: 队友领先优先级调整**
        *对于任何* 队友处于领先状态且牌数少的情况，系统应该大幅提高PASS优先级
        **验证: 需求 3.4**
        """
        adjusted = base_scores.copy()
        
        # 队友领先且牌少
        if context.teammate_is_leading and context.teammate_remain <= 5:
            for i, action in enumerate(action_list):
                if action[0] == "PASS":
                    # 大幅提高PASS优先级
                    adjusted[i] = 1.0 * self.weight
                else:
                    # 降低其他动作优先级
                    adjusted[i] *= 0.5
        
        # 队友牌很少（<=3张），即使不领先也要配合
        elif context.teammate_remain <= 3:
            for i, action in enumerate(action_list):
                if action[0] == "PASS":
                    adjusted[i] = 0.7 * self.weight
        
        return adjusted


class DynamicPrioritySystem:
    """
    动态优先级系统
    
    实现需求3.5和属性15：实时优先级调整
    """
    
    def __init__(self):
        """初始化动态优先级系统"""
        import logging
        self.logger = logging.getLogger("DynamicPriority")
        
        # 初始化所有调整器
        self.adjusters: List[ContextAdjuster] = [
            NextPlayerAdjuster(weight=1.0),
            PassCountAdjuster(weight=1.0, threshold=5),
            EndgameAdjuster(weight=1.2),
            TeammateAdjuster(weight=1.3),
        ]
    
    def adjust_priorities(self, base_scores: List[float], action_list: List[List],
                         message: dict) -> List[float]:
        """
        调整优先级
        
        **属性 15: 实时优先级调整**
        *对于任何* 游戏上下文发生变化的情况，系统应该实时调整优先级权重
        **验证: 需求 3.5**
        
        Args:
            base_scores: 基础分数列表
            action_list: 动作列表
            message: 游戏状态消息
            
        Returns:
            调整后的分数列表
        """
        # 构建上下文
        context = self._build_context(message)
        
        # 依次应用所有调整器
        adjusted_scores = base_scores.copy()
        adjustment_log = []
        
        for adjuster in self.adjusters:
            before = adjusted_scores.copy()
            adjusted_scores = adjuster.adjust(adjusted_scores, action_list, context)
            
            # 记录调整信息
            changes = sum(1 for i in range(len(before)) if abs(before[i] - adjusted_scores[i]) > 0.01)
            if changes > 0:
                adjustment_log.append({
                    'adjuster': adjuster.name,
                    'changes': changes
                })
        
        self.logger.debug(f"优先级调整: {adjustment_log}")
        
        return adjusted_scores
    
    def _build_context(self, message: dict) -> PriorityContext:
        """构建优先级上下文"""
        my_pos = message.get("myPos", 0)
        my_remain = len(message.get("handCards", []))
        
        # 获取各玩家剩余牌数
        public_info = message.get("publicInfo", [])
        teammate_pos = (my_pos + 2) % 4
        next_player_pos = (my_pos + 1) % 4
        
        teammate_remain = 27
        next_player_remain = 27
        opponent_remain = [27, 27]
        
        if len(public_info) > teammate_pos and isinstance(public_info[teammate_pos], dict):
            teammate_remain = public_info[teammate_pos].get('rest', 27)
        
        if len(public_info) > next_player_pos and isinstance(public_info[next_player_pos], dict):
            next_player_remain = public_info[next_player_pos].get('rest', 27)
        
        opponent_positions = [(my_pos + 1) % 4, (my_pos + 3) % 4]
        for i, pos in enumerate(opponent_positions):
            if len(public_info) > pos and isinstance(public_info[pos], dict):
                opponent_remain[i] = public_info[pos].get('rest', 27)
        
        # 计算PASS次数
        action_history = message.get("actionHistory", [])
        pass_count = 0
        for action in reversed(action_history):
            if action and action[0] == "PASS":
                pass_count += 1
            else:
                break
        
        # 判断游戏阶段
        total_remain = my_remain + teammate_remain + sum(opponent_remain)
        if total_remain > 80:
            game_stage = "early"
        elif total_remain > 50:
            game_stage = "mid"
        elif total_remain > 20:
            game_stage = "late"
        else:
            game_stage = "endgame"
        
        # 判断残局
        is_endgame = my_remain <= 10 or teammate_remain <= 5
        endgame_type = "normal"
        if is_endgame:
            if my_remain <= 5 and max(opponent_remain) >= 10:
                endgame_type = "rush"
            elif teammate_remain <= 5 and my_remain <= 8:
                endgame_type = "defend"
            elif teammate_remain <= 8 and my_remain <= 10:
                endgame_type = "cooperate"
            elif my_remain <= 10 and sum(opponent_remain) <= 20:
                endgame_type = "control"
        
        # 判断队友是否领先
        teammate_is_leading = teammate_remain < min(opponent_remain)
        
        return PriorityContext(
            my_remain=my_remain,
            teammate_remain=teammate_remain,
            next_player_remain=next_player_remain,
            opponent_remain=opponent_remain,
            pass_count=pass_count,
            game_stage=game_stage,
            is_endgame=is_endgame,
            endgame_type=endgame_type,
            teammate_is_leading=teammate_is_leading
        )
    
    def get_adjusters_info(self) -> List[Dict]:
        """获取所有调整器信息"""
        return [adj.get_adjustment_info() for adj in self.adjusters]


# 创建全局实例
_dynamic_priority = DynamicPrioritySystem()


def evaluate_all_actions_enhanced(evaluator: MultiFactorEvaluator,
                                  action_list: List[List],
                                  message: dict,
                                  target_action: Optional[List] = None) -> List[Tuple[int, float]]:
    """
    增强版动作评估接口
    
    整合动态优先级系统和原有评估器
    
    Args:
        evaluator: 多因素评估器
        action_list: 动作列表
        message: 游戏状态消息
        target_action: 目标动作
        
    Returns:
        评估结果列表 [(索引, 分数), ...]
    """
    # 获取基础评估分数
    base_evaluations = evaluator.evaluate_all_actions(action_list, target_action)
    base_scores = [score for _, score in sorted(base_evaluations, key=lambda x: x[0])]
    
    # 应用动态优先级调整
    adjusted_scores = _dynamic_priority.adjust_priorities(base_scores, action_list, message)
    
    # 构建结果
    result = [(i, adjusted_scores[i]) for i in range(len(adjusted_scores))]
    result.sort(key=lambda x: x[1], reverse=True)
    
    return result
