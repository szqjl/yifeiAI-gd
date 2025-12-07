# -*- coding: utf-8 -*-
"""
策略编码器（增强版）
计算组牌、顺牌、跟牌、控牌策略的shaping reward
"""
from typing import List, Dict
from collections import Counter
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.decision.card_grouping_strategy import evaluate_grouping_effect
from src.decision.card_power_evaluator import calculate_card_power


class StrategyEncoder:
    def __init__(self):
        self.last_hand_count = 27
        self.last_action_type = None
        
    def calculate_shaping_reward(self, state_dict: dict, action_cards: List, 
                                 action_type: str = None, game_phase: str = "mid",
                                 cur_rank: str = "2") -> float:
        """
        计算shaping reward（增强版：包含组牌、顺牌、跟牌、控牌策略奖励）
        
        Args:
            state_dict: 游戏状态字典
            action_cards: 动作卡牌列表（卡牌代码，如['H2', 'D3']）
            action_type: 动作类型（如'Single', 'Pair', 'Straight'等）
            game_phase: 游戏阶段（'opening', 'mid', 'endgame'）
            cur_rank: 当前级牌
        
        Returns:
            shaping reward值
        """
        reward = 0.0
        
        # 获取当前玩家手牌
        current_player = state_dict.get('current_player', 0)
        hands = state_dict.get('hands', {})
        hand_cards = hands.get(current_player, [])
        
        if not hand_cards:
            return reward
        
        # 1. 基础奖励：完成手牌
        if len(action_cards) == len(hand_cards):
            reward += 5.0
        
        # 2. 组牌策略奖励
        if action_cards and action_type:
            grouping_result = evaluate_grouping_effect(
                hand_cards=hand_cards,
                action_cards=action_cards,
                action_type=action_type,
                game_phase=game_phase,
                power=5.0,  # 简化：使用默认牌力
                cur_rank=cur_rank
            )
            
            # 轮次减少奖励
            if grouping_result.get('rounds_reduced', 0) > 0:
                reward += 5.0  # 减少轮次，大幅奖励
            
            # 单牌减少奖励
            if grouping_result.get('singles_reduced', 0) > 0:
                reward += 3.0  # 减少单牌，奖励
            
            # 组牌评分奖励（归一化）
            grouping_score = grouping_result.get('score', 0)
            reward += grouping_score / 100.0  # 归一化到合理范围
        
        # 3. 顺牌策略奖励
        if action_type == "Single" or action_type == "SINGLE":
            # 判断是否是顺牌（上家出单，自己跟单）
            last_action = state_dict.get('last_action', {})
            if last_action and last_action.get('type') == 'Single':
                # 成功顺牌
                reward += 5.0
                
                # 顺牌大小合适奖励
                if action_cards and last_action.get('cards'):
                    action_rank = self._get_card_rank(action_cards[0])
                    last_rank = self._get_card_rank(last_action['cards'][0])
                    # 顺牌大小合适（不要太大，不要太小）
                    if action_rank > last_rank and action_rank <= last_rank + 3:
                        reward += 2.0
        
        # 4. 跟牌策略奖励
        if action_type and action_type != "PASS":
            last_action = state_dict.get('last_action', {})
            if last_action and last_action.get('type') != "PASS":
                # 成功跟牌（能压制对手）
                reward += 3.0
                
                # 跟牌时机奖励
                if game_phase == "opening" or game_phase == "early":
                    # 初期跟牌，时机好
                    reward += 2.0
                elif game_phase == "endgame" or game_phase == "late":
                    # 残局跟牌，必须压制
                    reward += 5.0
        
        # 5. 控牌策略奖励
        # 判断是否需要控牌（对手快走完）
        opponent_rest_cards = []
        for i in range(4):
            if i != current_player:
                opponent_rest_cards.append(len(hands.get(i, [])))
        min_opponent_cards = min(opponent_rest_cards) if opponent_rest_cards else 27
        
        if min_opponent_cards <= 5:
            # 对手快走完，需要控牌
            if action_type == "Bomb" or action_type == "BOMB":
                # 使用炸弹控牌
                reward += 10.0  # 成功控牌
                reward += 5.0   # 控牌必要
            elif action_type and action_type != "PASS":
                # 使用其他牌型控牌
                reward += 5.0   # 成功控牌
        
        # 6. 策略奖励：帮助队友/阻止对手
        # 简化判断：如果动作能帮助队友或阻止对手
        if action_type and action_type != "PASS":
            # 帮助队友（简化：出牌就是帮助）
            reward += 2.0
            # 阻止对手（简化：出牌就是阻止）
            reward += 1.0
        
        return reward
    
    def _get_card_rank(self, card_code: str) -> int:
        """获取卡牌点数（用于比较大小）"""
        rank_map = {
            '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7,
            'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12,
            'B': 13, 'R': 14
        }
        if len(card_code) >= 2:
            rank = card_code[1] if len(card_code) == 2 else card_code[1:2]
            return rank_map.get(rank, 0)
        return 0

    def analyze_hand_structure(self, hand: List[str]):
        """
        分析手牌结构（用于检测炸弹等）
        """
        rank_count = Counter()
        for card in hand:
            if len(card) >= 2:
                rank = card[1] if len(card) == 2 else card[1:2]
                rank_count[rank] += 1
        
        # 检测炸弹（4张或以上相同点数）
        bombs = [rank for rank, count in rank_count.items() if count >= 4]
        return {'bombs': bombs, 'rank_count': rank_count}
