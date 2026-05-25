# -*- coding: utf-8 -*-
"""
增强协作策略 (Enhanced Collaboration Strategy)
基于 Agentic Design Patterns 多智能体协作模式优化

功能：
- 协作协议设计
- 增强协作策略
- 协作效果评估
"""

from typing import Dict, List, Optional
import logging
from datetime import datetime
try:
    from game_logic.guandan_constants import DEFAULT_REST_CARDS
except ImportError:
    DEFAULT_REST_CARDS = 27


class CollaborationProtocol:
    """协作协议（基于 Agentic Design Patterns）"""
    
    def __init__(self):
        self.protocol_state = {
            'teammate_intent': None,      # 队友意图
            'my_intent': None,            # 我的意图
            'collaboration_mode': 'auto', # 协作模式
            'sync_count': 0,              # 同步次数
        }
        self.logger = logging.getLogger("CollaborationProtocol")
    
    def send_intent(self, intent: Dict):
        """
        发送协作意图（通过游戏状态间接传递）
        
        在掼蛋中，通过出牌行为传递意图：
        - 出小牌表示"需要保护"
        - 出大牌表示"可以配合"
        """
        self.protocol_state['my_intent'] = intent
        self.logger.debug(f"Sent intent: {intent.get('type', 'unknown')}")
    
    def receive_intent(self, teammate_action: Dict) -> Dict:
        """
        接收队友意图（从队友出牌行为推断）
        
        Args:
            teammate_action: 队友的出牌动作
            
        Returns:
            推断的队友意图
        """
        intent = self._infer_intent(teammate_action)
        self.protocol_state['teammate_intent'] = intent
        self.protocol_state['sync_count'] += 1
        return intent
    
    def _infer_intent(self, action: Dict) -> Dict:
        """
        从出牌行为推断意图
        
        Args:
            action: 出牌动作
            
        Returns:
            推断的意图字典
        """
        intent = {
            'type': 'unknown',
            'confidence': 0.0,
        }
        
        # 推断逻辑
        card_value = action.get('card_value', 0)
        action_type = action.get('action_type', '')
        
        if card_value < 8:
            intent['type'] = 'need_protection'
            intent['confidence'] = 0.8
        elif card_value > 12:
            intent['type'] = 'can_cooperate'
            intent['confidence'] = 0.7
        elif action_type == 'Bomb':
            intent['type'] = 'urgent_need'
            intent['confidence'] = 0.9
        
        return intent
    
    def get_collaboration_mode(self) -> str:
        """获取当前协作模式"""
        return self.protocol_state.get('collaboration_mode', 'auto')
    
    def set_collaboration_mode(self, mode: str):
        """设置协作模式"""
        self.protocol_state['collaboration_mode'] = mode


class CooperationStrategy:
    """主动配合策略"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = logging.getLogger("CooperationStrategy")
    
    def should_cooperate(self, message: Dict, context: Dict) -> bool:
        """判断是否应该主动配合"""
        # 检查是否有配合机会
        teammate_pos = context.get('teammate_pos', -1)
        greater_pos = message.get('greaterPos', -1)
        
        # 如果队友是最大动作者，可以考虑配合
        if greater_pos == teammate_pos:
            return True
        
        # 如果队友牌数很少，主动配合
        teammate_rest_cards = context.get('teammate_rest_cards', DEFAULT_REST_CARDS)
        if teammate_rest_cards <= 5:
            return True
        
        return False
    
    def get_cooperation_action(self, message: Dict, context: Dict) -> Optional[int]:
        """获取配合动作"""
        action_list = message.get('actionList', [])
        if not action_list:
            return None
        
        # 寻找能配合队友的动作
        # 简化实现：选择较大的动作
        for i, action in enumerate(action_list):
            if action[0] != 'PASS':
                # 检查是否适合配合
                if self._is_suitable_for_cooperation(action, context):
                    return i
        
        return None
    
    def _is_suitable_for_cooperation(self, action: List, context: Dict) -> bool:
        """判断动作是否适合配合"""
        # 简化实现
        action_type = action[0] if isinstance(action, list) else str(action)
        
        # 炸弹不适合配合（应该保留）
        if action_type == 'Bomb':
            return False
        
        return True


class SignalStrategy:
    """信号策略（通过出牌传递信号）"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = logging.getLogger("SignalStrategy")
    
    def should_signal(self, message: Dict, context: Dict) -> bool:
        """判断是否应该发送信号"""
        # 在特定情况下发送信号
        my_remain = context.get('my_remain', DEFAULT_REST_CARDS)
        teammate_rest_cards = context.get('teammate_rest_cards', DEFAULT_REST_CARDS)
        
        # 如果我的牌数很多，队友牌数很少，发送"可以配合"信号
        if my_remain > 15 and teammate_rest_cards <= 5:
            return True
        
        # 如果我的牌数很少，发送"需要保护"信号
        if my_remain <= 5:
            return True
        
        return False
    
    def get_signal_action(self, message: Dict, context: Dict) -> Optional[int]:
        """获取信号动作"""
        action_list = message.get('actionList', [])
        if not action_list:
            return None
        
        my_remain = context.get('my_remain', DEFAULT_REST_CARDS)
        teammate_rest_cards = context.get('teammate_rest_cards', DEFAULT_REST_CARDS)
        
        # 发送"可以配合"信号：出较大的牌
        if my_remain > 15 and teammate_rest_cards <= 5:
            # 选择较大的动作（但不是最大的）
            for i in range(len(action_list) - 1, -1, -1):
                action = action_list[i]
                if action[0] != 'PASS' and action[0] != 'Bomb':
                    return i
        
        # 发送"需要保护"信号：出小牌
        if my_remain <= 5:
            # 选择较小的动作
            for i, action in enumerate(action_list):
                if action[0] != 'PASS':
                    return i
        
        return None


class EnhancedCollaborationStrategy:
    """增强协作策略（基于 Agentic Design Patterns）"""
    
    def __init__(self, config: Dict = None, base_protection_strategy=None):
        """
        初始化增强协作策略
        
        Args:
            config: 配置字典
            base_protection_strategy: 基础保护策略（TeammateProtectionStrategy实例）
        """
        self.config = config or {}
        self.base_protection_strategy = base_protection_strategy
        self.protocol = CollaborationProtocol()
        self.cooperation_strategy = CooperationStrategy(config)
        self.signal_strategy = SignalStrategy(config)
        self.logger = logging.getLogger("EnhancedCollaborationStrategy")
    
    def decide_collaboration(self, message: Dict, context: Dict) -> Dict:
        """
        决定协作方式
        
        Args:
            message: 游戏状态消息
            context: 上下文信息
            
        Returns:
            协作决策字典
        """
        collaboration = {
            'action': None,
            'type': None,  # 'protect', 'cooperate', 'signal', 'none'
            'confidence': 0.0,
        }
        
        # 策略1: 保护队友
        if self.base_protection_strategy and self.base_protection_strategy.should_protect(message, context):
            protection_action = self.base_protection_strategy.get_protection_action(message, context)
            if protection_action is not None:
                collaboration['action'] = protection_action
                collaboration['type'] = 'protect'
                collaboration['confidence'] = 0.9
                return collaboration
        
        # 策略2: 主动配合
        if self.cooperation_strategy.should_cooperate(message, context):
            cooperation_action = self.cooperation_strategy.get_cooperation_action(message, context)
            if cooperation_action is not None:
                collaboration['action'] = cooperation_action
                collaboration['type'] = 'cooperate'
                collaboration['confidence'] = 0.8
                return collaboration
        
        # 策略3: 发送信号
        if self.signal_strategy.should_signal(message, context):
            signal_action = self.signal_strategy.get_signal_action(message, context)
            if signal_action is not None:
                collaboration['action'] = signal_action
                collaboration['type'] = 'signal'
                collaboration['confidence'] = 0.6
                return collaboration
        
        return collaboration
    
    def should_protect(self, message: Dict, context: Dict) -> bool:
        """
        判断是否应该保护队友（兼容接口）
        
        Args:
            message: 游戏状态消息
            context: 上下文信息
            
        Returns:
            是否应该保护队友
        """
        if self.base_protection_strategy:
            return self.base_protection_strategy.should_protect(message, context)
        return False
    
    def get_protection_action(self, message: Dict, context: Dict) -> Optional[int]:
        """
        获取保护动作（兼容接口）
        
        Args:
            message: 游戏状态消息
            context: 上下文信息
            
        Returns:
            保护动作索引，如果不需要保护返回None
        """
        # 使用 decide_collaboration 来决定协作方式
        collaboration = self.decide_collaboration(message, context)
        
        # 如果是保护类型，返回动作
        if collaboration.get('type') == 'protect':
            return collaboration.get('action')
        
        # 如果不是保护类型，返回None（让调用者使用其他策略）
        return None


class CollaborationEvaluator:
    """协作效果评估器（基于 Agentic Design Patterns）"""
    
    def __init__(self):
        self.collaboration_history = []
        self.effectiveness_metrics = {
            'protection_success_rate': 0.0,
            'cooperation_success_rate': 0.0,
            'signal_success_rate': 0.0,
            'overall_win_rate': 0.0,
        }
        self.logger = logging.getLogger("CollaborationEvaluator")
    
    def evaluate_collaboration(self, collaboration: Dict, outcome: str):
        """
        评估协作效果
        
        Args:
            collaboration: 协作决策
            outcome: 对局结果 ('win', 'lose', 'draw')
        """
        self.collaboration_history.append({
            'collaboration': collaboration,
            'outcome': outcome,
            'timestamp': datetime.now()
        })
        
        # 更新指标
        self._update_metrics()
    
    def _update_metrics(self):
        """更新协作效果指标"""
        if not self.collaboration_history:
            return
        
        # 计算保护成功率
        protection_actions = [
            h for h in self.collaboration_history 
            if h['collaboration'].get('type') == 'protect'
        ]
        if protection_actions:
            wins = [h for h in protection_actions if h['outcome'] == 'win']
            self.effectiveness_metrics['protection_success_rate'] = len(wins) / len(protection_actions)
        
        # 计算配合成功率
        cooperation_actions = [
            h for h in self.collaboration_history 
            if h['collaboration'].get('type') == 'cooperate'
        ]
        if cooperation_actions:
            wins = [h for h in cooperation_actions if h['outcome'] == 'win']
            self.effectiveness_metrics['cooperation_success_rate'] = len(wins) / len(cooperation_actions)
        
        # 计算信号成功率
        signal_actions = [
            h for h in self.collaboration_history 
            if h['collaboration'].get('type') == 'signal'
        ]
        if signal_actions:
            wins = [h for h in signal_actions if h['outcome'] == 'win']
            self.effectiveness_metrics['signal_success_rate'] = len(wins) / len(signal_actions)
        
        # 计算总体胜率
        total_wins = [h for h in self.collaboration_history if h['outcome'] == 'win']
        self.effectiveness_metrics['overall_win_rate'] = len(total_wins) / len(self.collaboration_history)
    
    def get_metrics(self) -> Dict:
        """获取协作效果指标"""
        return self.effectiveness_metrics.copy()
    
    def get_recommendations(self) -> List[str]:
        """获取优化建议"""
        recommendations = []
        
        if self.effectiveness_metrics['protection_success_rate'] < 0.5:
            recommendations.append("保护策略成功率较低，建议优化保护规则")
        
        if self.effectiveness_metrics['cooperation_success_rate'] < 0.5:
            recommendations.append("配合策略成功率较低，建议优化配合逻辑")
        
        if self.effectiveness_metrics['signal_success_rate'] < 0.4:
            recommendations.append("信号策略成功率较低，建议优化信号传递机制")
        
        return recommendations

