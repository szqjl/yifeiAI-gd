# -*- coding: utf-8 -*-
"""
配合策略模块 (Cooperation Strategy)
功能：
- 评估队友出牌的配合机会
- 判断是否PASS配合队友
- 判断是否接管队友出牌权
"""

from typing import Dict, List, Optional, Any
import sys
from pathlib import Path

# 添加src到路径
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from game_logic.enhanced_state import EnhancedGameStateManager


class CooperationStrategy:
    """配合策略类"""
    
    def __init__(self, state_manager: EnhancedGameStateManager):
        """
        初始化配合策略
        
        Args:
            state_manager: 游戏状态管理器
        """
        self.state = state_manager
        
        # 添加logger
        import logging
        self.logger = logging.getLogger("CooperationStrategy")
        
        # 配置阈值
        self.support_threshold = 15  # 队友出牌价值超过此阈值时优先PASS配合
        self.danger_threshold = 4    # 危险阈值，队友剩余牌数低于此值时提高保护
        self.max_val_threshold = 14  # 最大价值阈值
    
    def get_cooperation_strategy(self, action_list: List[List], 
                                cur_action: Optional[List],
                                greater_action: Optional[List],
                                game_stage: str = "early",
                                teammate_passed: bool = False,
                                my_rest_cards: int = 27,
                                teammate_rest_cards: int = 27,
                                opponent_rest_cards: int = 27,
                                my_power: float = 10.0,
                                teammate_power: float = 10.0) -> Dict[str, Any]:
        """
        获取配合策略
        
        配合策略原则：
        1、上家出单，我牌力足够，跟自己天然单
        2、牌力不够，直接上大单压制。如果获得出牌权，改出其他牌型
        3、中后期，如果没有能压制对方的单了，我方的任何一方都要直接炸
        4、防守责任原则：对手下家的防守责任一般由上家负责，尤其是在开局和中期
        5、助攻角色原则：当自身牌力弱（power < 5），是助攻角色时，必须全力配合队友，让队友主导
        6、队友保护原则：永远不要压制队友的出牌，尤其是队友刚获得出牌权时
        
        Args:
            action_list: 可选动作列表
            cur_action: 当前动作
            greater_action: 最大动作
            game_stage: 游戏阶段 (early, mid, late, endgame)
            teammate_passed: 队友是否刚刚pass
            my_rest_cards: 我方剩余牌数
            teammate_rest_cards: 队友剩余牌数
            opponent_rest_cards: 对手剩余牌数
            my_power: 我方牌力评分（用于判断是否是助攻角色）
            teammate_power: 队友牌力评分
        
        Returns:
            配合策略结果字典:
            - should_pass: 是否应该PASS配合
            - should_take_over: 是否应该接管出牌
            - best_action_index: 最佳动作索引
        """
        result = {
            "should_pass": False,
            "should_take_over": False,
            "best_action_index": None
        }
        
        # 如果当前动作为空或PASS，不需要配合
        if not cur_action or cur_action[0] == "PASS":
            return result
        
        # 检查当前玩家是否是防守责任人
        is_defender = self.state.is_responsible_defender()
        
        # 关键判断：自身是否是助攻角色
        is_assist_role = my_power < 5.0
        is_strong_teammate = teammate_power > 7.0
        
        # 核心规则1：助攻角色必须全力配合队友，让队友主导
        if is_assist_role and is_strong_teammate:
            self.logger.debug(f"助攻角色策略：自身牌力弱({my_power:.1f})，队友牌力强({teammate_power:.1f})，优先pass")
            result["should_pass"] = True
            return result
        
        # 核心规则：如果当前出牌者是队友，慎重接牌
        if greater_action and greater_action[0] != "PASS":
            # 评估队友动作价值
            teammate_value = self._calculate_action_value(greater_action)
            teammate_action_type = greater_action[0]
            
            # 1. 助攻角色永远不要压制队友的出牌
            if is_assist_role:
                self.logger.debug(f"助攻角色策略：队友获得出牌权，助攻角色必须pass")
                result["should_pass"] = True
                return result
            
            # 2. 队友先发的牌，接牌要慎重
            if game_stage in ["early", "mid"]:
                self.logger.debug(f"队友获得控牌权，开局/中期不轻易接回，让队友主导")
                result["should_pass"] = True
                return result
            
            # 3. 牌不好时不要接队友的牌
            if my_power < 8:
                self.logger.debug(f"牌力一般/弱({my_power:.1f})，不接队友的牌")
                result["should_pass"] = True
                return result
            
            # 4. 剩余牌数多时不接队友的牌
            if my_rest_cards > 10:
                self.logger.debug(f"剩余牌数多({my_rest_cards}张)，不是争上游阶段，不接队友的牌")
                result["should_pass"] = True
                return result
            
            # 5. 队友出的牌值较高时，不要压制
            if teammate_value >= self.support_threshold:
                self.logger.debug(f"队友牌值较高({teammate_value:.1f})，不压制队友")
                result["should_pass"] = True
                return result
            
            # 6. 队友出的牌值中等时，慎重接管
            if teammate_value >= 8:
                best_idx = self._find_best_takeover_action(action_list, greater_action)
                if best_idx is not None:
                    if self._will_break_hand_structure(action_list[best_idx]):
                        self.logger.debug(f"接管队友出牌会破坏牌型，选择pass")
                        result["should_pass"] = True
                        return result
                    result["should_take_over"] = True
                    result["best_action_index"] = best_idx
                    return result
        
        # 核心逻辑：如果队友刚刚pass，我方必须积极应对
        if teammate_passed:
            self.logger.debug("队友刚刚pass，我方必须积极应对")
            take_over_action = self._find_best_takeover_action(action_list, cur_action)
            if take_over_action is not None:
                result["should_take_over"] = True
                result["best_action_index"] = take_over_action
                return result
            
            # 找炸弹作为最后手段
            bomb_action = self._find_bomb_action(action_list)
            if bomb_action is not None:
                result["should_take_over"] = True
                result["best_action_index"] = bomb_action
                return result
            
            result["should_pass"] = True
            return result
        
        # 防守责任判断
        if not is_defender and game_stage in ["early", "mid"]:
            if my_power < 7:
                self.logger.debug("不是防守责任人，且牌力弱，优先pass让队友处理")
                result["should_pass"] = True
                return result
            else:
                if greater_action and greater_action[0] != "PASS":
                    self.logger.debug("不是防守责任人，但牌力强，但队友刚获得出牌权，优先pass让队友控牌")
                    result["should_pass"] = True
                    return result
                self.logger.debug("不是防守责任人，但牌力强（主攻角色），可以考虑接管")
        
        # 初期跟牌逻辑
        if game_stage == "early" or game_stage == "opening":
            if cur_action and cur_action[0] == "Single":
                take_over_action = self._find_best_takeover_action(action_list, cur_action)
                if take_over_action is not None:
                    action_value = self._calculate_action_value(action_list[take_over_action])
                    cur_value = self._calculate_action_value(cur_action)
                    if action_value - cur_value < 8:
                        result["should_take_over"] = True
                        result["best_action_index"] = take_over_action
                        return result
        
        # 中后期策略
        if game_stage in ["late", "endgame"]:
            take_over_action = self._find_best_takeover_action(action_list, cur_action)
            if take_over_action is not None:
                result["should_take_over"] = True
                result["best_action_index"] = take_over_action
            else:
                bomb_action = self._find_bomb_action(action_list)
                if bomb_action is not None:
                    result["should_take_over"] = True
                    result["best_action_index"] = bomb_action
        
        return result
        
    def _find_bomb_action(self, action_list: List[List]) -> Optional[int]:
        """
        查找炸弹动作
        
        Args:
            action_list: 动作列表
        
        Returns:
            炸弹动作索引，无则返回None
        """
        for idx, action in enumerate(action_list):
            if action[0] == "Bomb":
                return idx
        return None
    
    def _calculate_action_value(self, action: List) -> float:
        """
        计算动作价值

        Args:
            action: 动作格式 [card_type, rank, cards]

        Returns:
            动作价值分数，用于比较动作优劣
        """
        if not action or action[0] == "PASS":
            return 0.0
        
        card_type = action[0]
        rank = action[1] if len(action) > 1 else ""
        cards = action[2] if len(action) > 2 else []
        
        # 基础牌型价值
        type_values = {
            "Bomb": 20.0,
            "StraightFlush": 18.0,
            "TwoTrips": 15.0,
            "ThreePair": 12.0,
            "Straight": 10.0,
            "ThreeWithTwo": 8.0,
            "Trips": 6.0,
            "Pair": 4.0,
            "Single": 4.0
        }
        
        base_value = type_values.get(card_type, 1.0)
        
        # 根据牌数添加额外价值
        card_count = len(cards) if isinstance(cards, list) else 1
        count_bonus = card_count * 0.5
        
        # 单牌额外添加点数价值
        if card_type == "Single":
            rank_values = {
                "3": 1.0, "4": 1.5, "5": 2.0, "6": 2.5, "7": 3.0,
                "8": 3.5, "9": 4.0, "10": 4.5, "J": 5.0, "Q": 5.5,
                "K": 6.0, "A": 6.5, "2": 7.0, "B": 8.0, "R": 9.0
            }
            rank_bonus = rank_values.get(rank, 1.0)
            return base_value + count_bonus + rank_bonus
        
        return base_value + count_bonus
    
    def _find_best_takeover_action(self, action_list: List[List], 
                                   target_action: List) -> Optional[int]:
        """
        查找最佳接管动作
        
        Args:
            action_list: 可选动作列表
            target_action: 目标动作（需要压制的动作）
        
        Returns:
            最佳动作索引，无合适动作返回None
        """
        if not action_list or not target_action:
            return None
        
        target_value = self._calculate_action_value(target_action)
        best_idx = None
        best_value = 0.0
        
        # 跳过PASS（索引0）
        for idx in range(1, len(action_list)):
            action = action_list[idx]
            if action[0] == "PASS":
                continue
            
            action_value = self._calculate_action_value(action)
            
            # 查找能压制且价值最小的动作
            if action_value > target_value:
                if best_idx is None or action_value < best_value:
                    best_idx = idx
                    best_value = action_value
        
        return best_idx
    
    def should_support_teammate(self, teammate_action_value: float) -> bool:
        """
        判断是否应该支持队友
        
        Args:
            teammate_action_value: 队友动作价值
        
        Returns:
            是否应该支持
        """
        return teammate_action_value >= self.support_threshold
    
    def should_take_over(self, teammate_value: float, my_value: float) -> bool:
        """
        判断是否应该接管出牌
        
        Args:
            teammate_value: 队友动作价值
            my_value: 我方动作价值
        
        Returns:
            是否应该接管
        """
        if 8 <= teammate_value < self.support_threshold:
            return my_value > teammate_value
        return False
    
    def _will_break_hand_structure(self, action: List) -> bool:
        """
        检查接管队友出牌是否会破坏牌型
        
        Args:
            action: 要执行的动作
        
        Returns:
            是否会破坏牌型
        """
        if not action or len(action) < 3:
            return False
        
        action_type = action[0]
        action_cards = action[2] if isinstance(action[2], list) else []
        
        # 顺子可能导致牌型变得单一
        if action_type in ["Straight", "StraightFlush"]:
            return True
        
        return False
    
    def evaluate_cooperation_opportunity(self, action_list: List[List], 
                                        cur_action: Optional[List]) -> Dict[str, Any]:
        """
        评估配合机会
        
        Args:
            action_list: 可选动作列表
            cur_action: 当前动作
        
        Returns:
            配合机会评估结果
        """
        if not cur_action or cur_action[0] == "PASS":
            return {"has_opportunity": False}
        
        cur_value = self._calculate_action_value(cur_action)
        
        # 评估是否有更好的动作
        better_actions = []
        for idx, action in enumerate(action_list[1:], 1):  # 跳过PASS
            if action[0] == "PASS":
                continue
            action_value = self._calculate_action_value(action)
            if action_value > cur_value:
                better_actions.append((idx, action_value))
        
        return {
            "has_opportunity": len(better_actions) > 0,
            "current_value": cur_value,
            "better_actions": better_actions
        }



# ==================== 增强版队友保护系统 ====================
# 根据 YF掼蛋硬编码优化规范实现
# 需求: 2.1-2.5, 属性: 6-10

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple


@dataclass
class ProtectionContext:
    """保护决策上下文"""
    my_pos: int = 0
    teammate_pos: int = 2
    teammate_remain: int = 27
    opponent_remain: List[int] = None
    teammate_action: Optional[List] = None
    game_stage: str = "early"
    my_power: float = 10.0
    teammate_power: float = 10.0
    
    def __post_init__(self):
        if self.opponent_remain is None:
            self.opponent_remain = [27, 27]


class TeammateProtectionRule(ABC):
    """
    队友保护规则抽象基类
    
    实现需求2的保护规则框架
    """
    
    def __init__(self, weight: float = 1.0):
        """
        初始化保护规则
        
        Args:
            weight: 规则权重，用于多规则综合评估
        """
        self.weight = weight
        self.name = self.__class__.__name__
    
    @abstractmethod
    def evaluate(self, context: ProtectionContext) -> Tuple[bool, float, str]:
        """
        评估是否需要保护
        
        Args:
            context: 保护决策上下文
            
        Returns:
            (should_protect, protection_score, reason)
        """
        pass
    
    def get_weighted_score(self, context: ProtectionContext) -> float:
        """获取加权后的保护分数"""
        _, score, _ = self.evaluate(context)
        return score * self.weight


class HighValueProtectionRule(TeammateProtectionRule):
    """
    高价值牌保护规则
    
    实现需求2.1和属性6：队友出A、2、王时的保护
    """
    
    HIGH_VALUE_RANKS = {'A', '2', 'B', 'R'}  # A, 2, 小王, 大王
    
    def __init__(self, weight: float = 1.5):
        super().__init__(weight)
    
    def evaluate(self, context: ProtectionContext) -> Tuple[bool, float, str]:
        """
        评估高价值牌保护需求
        
        **属性 6: 高价值牌保护**
        *对于任何* 队友出高价值牌（A、2、王）的情况，系统应该正确评估保护需求并选择PASS或最小管牌
        **验证: 需求 2.1**
        """
        if not context.teammate_action or len(context.teammate_action) < 2:
            return False, 0.0, "无队友动作"
        
        action_type = context.teammate_action[0]
        rank = context.teammate_action[1] if len(context.teammate_action) > 1 else ""
        
        # 检查是否是高价值牌
        if rank in self.HIGH_VALUE_RANKS:
            value_scores = {'A': 0.7, '2': 0.8, 'B': 0.9, 'R': 1.0}
            score = value_scores.get(rank, 0.5)
            return True, score, f"队友出高价值牌({rank})，需要保护"
        
        # 检查是否是炸弹
        if action_type == "Bomb":
            return True, 1.0, "队友出炸弹，绝对保护"
        
        return False, 0.0, "非高价值牌"


class LowCardCountProtectionRule(TeammateProtectionRule):
    """
    低牌数保护规则
    
    实现需求2.2和属性7：队友剩余牌数少时的保护
    """
    
    def __init__(self, weight: float = 1.3, threshold: int = 5):
        super().__init__(weight)
        self.threshold = threshold
    
    def evaluate(self, context: ProtectionContext) -> Tuple[bool, float, str]:
        """
        评估低牌数保护需求
        
        **属性 7: 低牌数保护**
        *对于任何* 队友剩余牌数少于等于5张的情况，系统应该提高保护优先级
        **验证: 需求 2.2**
        """
        if context.teammate_remain <= self.threshold:
            # 牌数越少，保护分数越高
            score = 1.0 - (context.teammate_remain - 1) * 0.1
            score = max(0.6, min(1.0, score))
            return True, score, f"队友剩余{context.teammate_remain}张牌，需要保护"
        
        return False, 0.0, f"队友剩余{context.teammate_remain}张牌，无需特殊保护"


class CriticalStageProtectionRule(TeammateProtectionRule):
    """
    关键阶段保护规则
    
    实现需求2.3和属性8：关键时刻的动态保护
    """
    
    def __init__(self, weight: float = 1.2):
        super().__init__(weight)
    
    def evaluate(self, context: ProtectionContext) -> Tuple[bool, float, str]:
        """
        评估关键阶段保护需求
        
        **属性 8: 动态保护强度**
        *对于任何* 处于关键阶段且对手牌数也很少的情况，系统应该动态调整保护强度
        **验证: 需求 2.3**
        """
        teammate_critical = context.teammate_remain <= 8
        opponent_critical = any(r <= 8 for r in context.opponent_remain)
        
        if teammate_critical and opponent_critical:
            min_opponent = min(context.opponent_remain)
            
            if context.teammate_remain <= min_opponent:
                score = 0.9
                return True, score, f"关键阶段：队友({context.teammate_remain}张)领先对手({min_opponent}张)，高强度保护"
            else:
                score = 0.6
                return True, score, f"关键阶段：队友({context.teammate_remain}张)落后对手({min_opponent}张)，中等保护"
        
        if teammate_critical:
            return True, 0.5, f"队友处于关键阶段({context.teammate_remain}张)，基础保护"
        
        return False, 0.0, "非关键阶段"


class BombProtectionRule(TeammateProtectionRule):
    """
    炸弹绝对保护规则
    
    实现需求2.4和属性9：队友出炸弹时的绝对保护
    """
    
    def __init__(self, weight: float = 2.0):
        super().__init__(weight)
    
    def evaluate(self, context: ProtectionContext) -> Tuple[bool, float, str]:
        """
        评估炸弹保护需求
        
        **属性 9: 炸弹绝对保护**
        *对于任何* 队友打出炸弹的情况，系统应该绝对不压制队友
        **验证: 需求 2.4**
        """
        if not context.teammate_action:
            return False, 0.0, "无队友动作"
        
        action_type = context.teammate_action[0]
        
        if action_type in ["Bomb", "StraightFlush"]:
            return True, 1.0, f"队友出{action_type}，绝对保护，必须PASS"
        
        return False, 0.0, "非炸弹牌型"


class TeammateProtectionStrategy:
    """
    队友保护策略管理器
    
    实现需求2.5和属性10：多规则综合评估
    """
    
    def __init__(self):
        """初始化保护策略管理器"""
        import logging
        self.logger = logging.getLogger("TeammateProtection")
        
        # 初始化所有保护规则
        self.rules: List[TeammateProtectionRule] = [
            BombProtectionRule(weight=2.0),
            HighValueProtectionRule(weight=1.5),
            LowCardCountProtectionRule(weight=1.3, threshold=5),
            CriticalStageProtectionRule(weight=1.2),
        ]
        
        self.protection_threshold = 0.5
    
    def should_protect(self, message: dict, teammate_action: Optional[List] = None) -> Tuple[bool, Dict]:
        """
        判断是否需要保护队友
        
        **属性 10: 多规则综合评估**
        *对于任何* 多个保护规则同时触发的情况，系统应该综合评估并选择最佳保护策略
        **验证: 需求 2.5**
        
        Args:
            message: 游戏状态消息
            teammate_action: 队友的动作
            
        Returns:
            (should_protect, details)
        """
        context = self._build_context(message, teammate_action)
        
        results = []
        total_weighted_score = 0.0
        triggered_rules = []
        
        for rule in self.rules:
            should_protect, score, reason = rule.evaluate(context)
            weighted_score = score * rule.weight
            
            results.append({
                'rule': rule.name,
                'triggered': should_protect,
                'score': score,
                'weighted_score': weighted_score,
                'reason': reason
            })
            
            if should_protect:
                total_weighted_score += weighted_score
                triggered_rules.append(rule.name)
        
        max_possible_score = sum(r.weight for r in self.rules)
        final_score = total_weighted_score / max_possible_score if max_possible_score > 0 else 0
        
        should_protect = final_score >= self.protection_threshold
        
        if 'BombProtectionRule' in triggered_rules:
            should_protect = True
            final_score = 1.0
        
        details = {
            'final_score': final_score,
            'triggered_rules': triggered_rules,
            'rule_results': results,
            'context': {
                'teammate_remain': context.teammate_remain,
                'opponent_remain': context.opponent_remain,
                'game_stage': context.game_stage
            }
        }
        
        self.logger.debug(f"保护评估: should_protect={should_protect}, score={final_score:.2f}, rules={triggered_rules}")
        
        return should_protect, details
    
    def get_protection_action(self, message: dict, action_list: List[List], 
                              teammate_action: Optional[List] = None) -> Optional[int]:
        """
        获取保护动作
        
        Args:
            message: 游戏状态消息
            action_list: 可选动作列表
            teammate_action: 队友的动作
            
        Returns:
            动作索引，None表示不需要特殊保护动作
        """
        should_protect, details = self.should_protect(message, teammate_action)
        
        if not should_protect:
            return None
        
        final_score = details['final_score']
        
        if final_score >= 0.8:
            return 0  # PASS
        
        if final_score >= 0.5:
            min_action_idx = self._find_minimum_takeover(action_list, teammate_action)
            if min_action_idx is not None:
                return min_action_idx
            return 0
        
        return None
    
    def _build_context(self, message: dict, teammate_action: Optional[List]) -> ProtectionContext:
        """构建保护决策上下文"""
        my_pos = message.get("myPos", 0)
        teammate_pos = (my_pos + 2) % 4
        
        public_info = message.get("publicInfo", [])
        teammate_remain = 27
        opponent_remain = [27, 27]
        
        if len(public_info) > teammate_pos and isinstance(public_info[teammate_pos], dict):
            teammate_remain = public_info[teammate_pos].get('rest', 27)
        
        opponent_positions = [(my_pos + 1) % 4, (my_pos + 3) % 4]
        for i, pos in enumerate(opponent_positions):
            if len(public_info) > pos and isinstance(public_info[pos], dict):
                opponent_remain[i] = public_info[pos].get('rest', 27)
        
        my_remain = len(message.get("handCards", []))
        total_remain = my_remain + teammate_remain + sum(opponent_remain)
        
        if total_remain > 80:
            game_stage = "early"
        elif total_remain > 50:
            game_stage = "mid"
        elif total_remain > 20:
            game_stage = "late"
        else:
            game_stage = "endgame"
        
        return ProtectionContext(
            my_pos=my_pos,
            teammate_pos=teammate_pos,
            teammate_remain=teammate_remain,
            opponent_remain=opponent_remain,
            teammate_action=teammate_action,
            game_stage=game_stage
        )
    
    def _find_minimum_takeover(self, action_list: List[List], 
                               target_action: Optional[List]) -> Optional[int]:
        """找到最小的能压制的动作"""
        if not action_list or not target_action:
            return None
        
        target_value = self._calculate_action_value(target_action)
        min_idx = None
        min_value = float('inf')
        
        for idx in range(1, len(action_list)):
            action = action_list[idx]
            if action[0] == "PASS":
                continue
            
            action_value = self._calculate_action_value(action)
            
            if action_value > target_value and action_value < min_value:
                min_idx = idx
                min_value = action_value
        
        return min_idx
    
    def _calculate_action_value(self, action: List) -> float:
        """计算动作价值"""
        if not action or action[0] == "PASS":
            return 0.0
        
        card_type = action[0]
        rank = action[1] if len(action) > 1 else ""
        cards = action[2] if len(action) > 2 else []
        
        type_values = {
            "Bomb": 20.0, "StraightFlush": 18.0, "TwoTrips": 15.0,
            "ThreePair": 12.0, "Straight": 10.0, "ThreeWithTwo": 8.0,
            "Trips": 6.0, "Pair": 4.0, "Single": 2.0
        }
        
        base_value = type_values.get(card_type, 1.0)
        card_count = len(cards) if isinstance(cards, list) else 1
        
        return base_value + card_count * 0.5


# 创建全局实例
_protection_strategy = TeammateProtectionStrategy()


def get_cooperation_strategy_enhanced(message: dict, action_list: List[List],
                                      cur_action: Optional[List] = None,
                                      greater_action: Optional[List] = None,
                                      teammate_action: Optional[List] = None) -> Dict[str, Any]:
    """
    增强版配合策略接口
    
    整合队友保护系统和原有配合策略
    
    Args:
        message: 游戏状态消息
        action_list: 可选动作列表
        cur_action: 当前动作
        greater_action: 最大动作
        teammate_action: 队友动作
        
    Returns:
        配合策略结果
    """
    result = {
        "should_pass": False,
        "should_take_over": False,
        "best_action_index": None,
        "protection_triggered": False,
        "protection_details": None
    }
    
    should_protect, protection_details = _protection_strategy.should_protect(message, teammate_action)
    
    if should_protect:
        result["protection_triggered"] = True
        result["protection_details"] = protection_details
        
        protection_action = _protection_strategy.get_protection_action(
            message, action_list, teammate_action
        )
        
        if protection_action is not None:
            if protection_action == 0:
                result["should_pass"] = True
            else:
                result["should_take_over"] = True
                result["best_action_index"] = protection_action
            return result
    
    return result
