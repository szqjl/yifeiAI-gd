# -*- coding: utf-8 -*-
"""
策略应用器 - 通用策略处理框架
将knowledge中的策略建议转换为动作评分，避免硬编码if...else

设计思路：
1. 策略函数返回标准格式的建议
2. 策略应用器根据建议类型和动作类型，自动匹配并评分
3. 使用规则映射表，而不是硬编码if...else
"""

from typing import Dict, List, Any, Optional, Callable
import re


class StrategyApplicator:
    """
    通用策略应用器
    
    将knowledge策略函数的返回值转换为动作评分
    支持：
    - 单牌策略 (single_card_strategy)
    - 炸弹策略 (bomb_strategy)
    - 残局策略 (endgame_strategy)
    - 组牌策略 (grouping_strategy)
    """
    
    def __init__(self):
        """初始化策略应用器"""
        # 策略评分规则映射表
        # 格式: (策略类型, 动作类型, 匹配模式) -> (评分函数, 优先级)
        self.strategy_rules = self._init_strategy_rules()
    
    def _init_strategy_rules(self) -> List[Dict]:
        """
        初始化策略规则映射表
        
        返回规则列表，每个规则包含：
        - strategy_type: 策略类型 ('single', 'bomb', 'endgame', 'grouping')
        - action_type: 动作类型 ('Single', 'Pair', 'Bomb', 'PASS', '*')
        - pattern: 匹配模式（正则表达式或字符串）
        - score_func: 评分函数
        - priority: 优先级（数字越大优先级越高）
        """
        rules = []
        
        # ========== 单牌策略规则 ==========
        
        # 1. 对手剩1张时的特殊处理（最高优先级）
        rules.append({
            'strategy_type': 'single',
            'action_type': 'Single',
            'pattern': r'出第二小的单',
            'score_func': self._score_second_smallest_single,
            'priority': 100
        })
        rules.append({
            'strategy_type': 'single',
            'action_type': 'Single',
            'pattern': r'出第二大的单',
            'score_func': self._score_second_largest_single,
            'priority': 100
        })
        
        # 2. 出单相关建议
        rules.append({
            'strategy_type': 'single',
            'action_type': 'Single',
            'pattern': r'出高单',
            'score_func': lambda action, sugg, game_state: self._score_by_card_rank(
                action, sugg, game_state, ['Q', 'K', 'A', '2', 'B', 'R'], 45.0
            ),
            'priority': 50
        })
        rules.append({
            'strategy_type': 'single',
            'action_type': 'Single',
            'pattern': r'出中单',
            'score_func': lambda action, sugg, game_state: self._score_by_card_rank(
                action, sugg, game_state, ['J', 'T', '9'], 35.0
            ),
            'priority': 50
        })
        rules.append({
            'strategy_type': 'single',
            'action_type': 'Single',
            'pattern': r'出低单',
            'score_func': lambda action, sugg, game_state: self._score_by_card_rank(
                action, sugg, game_state, ['3', '4', '5', '6', '7', '8'], 30.0
            ),
            'priority': 50
        })
        
        # 3. 不出单相关建议
        rules.append({
            'strategy_type': 'single',
            'action_type': 'Single',
            'pattern': r'不出小单|不出单|不打单',
            'score_func': lambda action, sugg, game_state: (-25.0, sugg.get('reason', '')),
            'priority': 60
        })
        
        # 4. 一般出单建议（默认）
        rules.append({
            'strategy_type': 'single',
            'action_type': 'Single',
            'pattern': r'出单|打一张',
            'score_func': lambda action, sugg, game_state: (30.0, sugg.get('reason', '')),
            'priority': 10
        })
        
        # ========== 炸弹策略规则 ==========
        
        rules.append({
            'strategy_type': 'bomb',
            'action_type': 'Bomb',
            'pattern': r'不炸',
            'score_func': lambda action, sugg, game_state: (-200.0, sugg.get('reason', '')),
            'priority': 80
        })
        rules.append({
            'strategy_type': 'bomb',
            'action_type': 'Bomb',
            'pattern': r'炸',
            'score_func': lambda action, sugg, game_state: (40.0, sugg.get('reason', '')),
            'priority': 70
        })
        
        # ========== 残局策略规则 ==========
        
        rules.append({
            'strategy_type': 'endgame',
            'action_type': '*',
            'pattern': r'一手出完',
            'score_func': lambda action, sugg, game_state: (100.0, sugg.get('reason', '')),
            'priority': 90
        })
        rules.append({
            'strategy_type': 'endgame',
            'action_type': 'Single',
            'pattern': r'不出小单|忌给下家顺牌',
            'score_func': lambda action, sugg, game_state: self._score_small_single_penalty(
                action, sugg, game_state
            ),
            'priority': 70
        })
        
        return rules
    
    def apply_strategy(
        self,
        strategy_type: str,
        strategy_suggestion: Dict,
        action: List,
        action_index: int,
        game_state: Dict
    ) -> tuple[float, str]:
        """
        应用策略建议，返回评分调整和原因
        
        Args:
            strategy_type: 策略类型 ('single', 'bomb', 'endgame', 'grouping')
            strategy_suggestion: 策略建议字典
            action: 当前动作
            action_index: 动作索引
            game_state: 游戏状态
            
        Returns:
            (score_adjustment, reason): 评分调整和原因
        """
        action_type = action[0] if isinstance(action, list) else str(action)
        
        # 获取策略建议的action和reason
        if strategy_type == 'grouping':
            # grouping策略返回的是suggestions列表
            suggestions = strategy_suggestion.get('suggestions', [])
            for sugg in suggestions:
                if sugg.get('action_index') == action_index:
                    return (sugg.get('score', 0.0), sugg.get('reasons', [''])[0] if sugg.get('reasons') else '')
            return (0.0, '')
        elif strategy_type == 'bomb':
            # bomb策略返回的是suggestions列表
            suggestions = strategy_suggestion.get('suggestions', [])
            # 按优先级匹配规则
            matched_rules = []
            for sugg in suggestions:
                action_text = sugg.get('action', '')
                reason_text = sugg.get('reason', '')
                
                # 匹配规则
                for rule in self.strategy_rules:
                    if (rule['strategy_type'] == strategy_type and
                        (rule['action_type'] == action_type or rule['action_type'] == '*') and
                        re.search(rule['pattern'], action_text + reason_text)):
                        matched_rules.append((rule, sugg))
            
            # 选择优先级最高的规则
            if matched_rules:
                matched_rules.sort(key=lambda x: x[0]['priority'], reverse=True)
                rule, sugg = matched_rules[0]
                score, reason = rule['score_func'](action, sugg, game_state)
                return (score, reason)
            return (0.0, '')
        else:
            # single和endgame策略返回的是单个字典
            action_text = strategy_suggestion.get('action', '')
            reason_text = strategy_suggestion.get('reason', '')
            
            # 匹配规则
            matched_rules = []
            for rule in self.strategy_rules:
                if (rule['strategy_type'] == strategy_type and
                    (rule['action_type'] == action_type or rule['action_type'] == '*') and
                    re.search(rule['pattern'], action_text + reason_text)):
                    matched_rules.append((rule, strategy_suggestion))
            
            # 选择优先级最高的规则
            if matched_rules:
                matched_rules.sort(key=lambda x: x[0]['priority'], reverse=True)
                rule, sugg = matched_rules[0]
                score, reason = rule['score_func'](action, sugg, game_state)
                return (score, reason)
            
            return (0.0, '')
    
    def _score_second_smallest_single(self, action: List, sugg: Dict, game_state: Dict) -> tuple[float, str]:
        """评分：出第二小的单"""
        # 实现逻辑（与yf1_v5.py中的逻辑相同）
        # 这里简化处理，实际需要从game_state中获取hand_cards和rank_count
        return (100.0, sugg.get('reason', ''))
    
    def _score_second_largest_single(self, action: List, sugg: Dict, game_state: Dict) -> tuple[float, str]:
        """评分：出第二大的单"""
        # 实现逻辑（与yf1_v5.py中的逻辑相同）
        return (100.0, sugg.get('reason', ''))
    
    def _score_by_card_rank(
        self,
        action: List,
        sugg: Dict,
        game_state: Dict,
        valid_ranks: List[str],
        base_score: float
    ) -> tuple[float, str]:
        """根据牌点评分"""
        action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
        if action_cards and len(action_cards) > 0:
            card_rank = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
            if card_rank in valid_ranks:
                return (base_score, sugg.get('reason', ''))
        return (0.0, '')
    
    def _score_small_single_penalty(self, action: List, sugg: Dict, game_state: Dict) -> tuple[float, str]:
        """评分：不出小单的惩罚"""
        action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
        if action_cards and len(action_cards) > 0:
            card_rank = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
            if card_rank in ['3', '4', '5', '6', '7', '8', '9']:
                return (-30.0, sugg.get('reason', ''))
        return (0.0, '')


# 全局实例
_strategy_applicator = None

def get_strategy_applicator() -> StrategyApplicator:
    """获取策略应用器单例"""
    global _strategy_applicator
    if _strategy_applicator is None:
        _strategy_applicator = StrategyApplicator()
    return _strategy_applicator

