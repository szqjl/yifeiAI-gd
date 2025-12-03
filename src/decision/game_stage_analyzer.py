# -*- coding: utf-8 -*-
"""
游戏阶段分析器 (Game Stage Analyzer)
功能：
- 识别游戏当前阶段（初期、中期、后期、残局）
- 分析玩家出牌节奏和牌力分布
- 为决策提供时机评估支持
"""

from typing import Dict, List, Optional


class GameStageAnalyzer:
    """游戏阶段分析器类"""
    
    def __init__(self):
        self.early_stage_threshold = 20  # 初期：剩余牌数 > 20
        self.mid_stage_threshold = 15    # 中期：15 < 剩余牌数 <= 20
        self.late_stage_threshold = 10   # 后期：10 < 剩余牌数 <= 15
        # 残局：剩余牌数 <= 10
    
    def get_game_stage(self, player_cards: Dict[int, int]) -> str:
        """
        根据玩家剩余牌数判断游戏阶段
        
        Args:
            player_cards: 各玩家剩余牌数 {位置: 剩余牌数}
        
        Returns:
            游戏阶段："early" | "mid" | "late" | "endgame"
        """
        avg_cards = sum(player_cards.values()) / len(player_cards)
        
        if avg_cards > self.early_stage_threshold:
            return "early"
        elif avg_cards > self.mid_stage_threshold:
            return "mid"
        elif avg_cards > self.late_stage_threshold:
            return "late"
        else:
            return "endgame"
    
    def is_first_round(self, actions: List) -> bool:
        """
        判断是否为游戏第一轮
        
        Args:
            actions: 已出牌记录列表
        
        Returns:
            是否为第一轮
        """
        # 第一轮：只有少数几个动作，无论是否有复杂牌型
        # 即使有强牌，只要动作数量少，仍视为第一轮
        return len(actions) <= 5
    
    def should_reserve_strong_cards(self, game_stage: str, action_type: str) -> bool:
        """
        判断是否应该保留强牌
        
        Args:
            game_stage: 游戏阶段
            action_type: 当前动作类型
        
        Returns:
            是否应该保留强牌
        """
        # 初期应该保留强牌
        if game_stage == "early":
            return action_type in ["Bomb", "StraightFlush"]
        return False
    
    def evaluate_timing_value(self, game_stage: str, 
                             action_type: str, 
                             target_action_type: str, 
                             is_first_round: bool) -> float:
        """
        评估动作时机价值
        
        Args:
            game_stage: 游戏阶段
            action_type: 当前动作类型
            target_action_type: 目标动作类型
            is_first_round: 是否为第一轮
        
        Returns:
            时机价值（0.0-1.0）
        """
        # 第一轮用强牌炸弱牌，时机价值很低
        if is_first_round:
            if action_type in ["Bomb", "StraightFlush"] and target_action_type in ["Single", "Pair"]:
                return 0.1
        
        # 残局用强牌，时机价值很高
        if game_stage == "endgame" and action_type in ["Bomb", "StraightFlush"]:
            return 0.9
        
        # 强牌类型
        strong_types = ["Bomb", "StraightFlush"]
        
        # 弱牌类型
        weak_types = ["Single", "Pair"]
        
        # 强牌炸强牌，时机价值中等
        if action_type in strong_types and target_action_type in strong_types:
            return 0.7
        
        # 强牌炸中等牌型，时机价值较低
        if action_type in strong_types and target_action_type not in weak_types + strong_types:
            return 0.5
        
        # 普通时机
        return 0.6
    
    def analyze_action_necessity(self, action: List, 
                               target_action: List, 
                               game_stage: str, 
                               is_first_round: bool) -> Dict:
        """
        分析动作的必要性
        
        Args:
            action: 当前考虑的动作
            target_action: 目标动作
            game_stage: 游戏阶段
            is_first_round: 是否为第一轮
        
        Returns:
            动作必要性分析结果
        """
        action_type = action[0]
        target_type = target_action[0] if target_action else ""
        
        result = {
            "is_necessary": True,
            "reason": "",
            "suggestion": ""
        }
        
        # 第一轮用强牌炸弱牌，不必要
        if is_first_round:
            if action_type in ["Bomb", "StraightFlush"] and target_type in ["Single", "Pair"]:
                result["is_necessary"] = False
                result["reason"] = "第一轮用强牌炸弱牌，浪费资源"
                result["suggestion"] = "建议PASS，让队友尝试压制"
                return result
        
        # 初期用强牌炸弱牌，不必要
        if game_stage == "early":
            if action_type in ["Bomb", "StraightFlush"] and target_type in ["Single", "Pair"]:
                result["is_necessary"] = False
                result["reason"] = "游戏初期用强牌炸弱牌，浪费资源"
                result["suggestion"] = "建议PASS，保留强牌到后期"
                return result
        
        return result