# -*- coding: utf-8 -*-
"""
手牌最优组合扫描器 (Optimal Combination Scanner)

功能：
1. 扫描手牌的所有可能组合方案
2. 识别"多余单张"（不在任何组合中的单张）
3. 评估不同组合方案的优劣
4. 选择最优组合方案
"""

from typing import Dict, List, Tuple, Optional, Set
from collections import Counter
import sys
from pathlib import Path

# 将 src 目录添加到系统路径
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from game_logic.hand_combiner import HandCombiner


class OptimalCombinationScanner:
    """手牌最优组合扫描器"""
    
    def __init__(self):
        self.combiner = HandCombiner()
    
    def scan_optimal_combination(self, handcards: List[str], rank: str) -> Dict:
        """
        扫描手牌的最优组合方案
        
        Args:
            handcards: 手牌列表
            rank: 等级牌
            
        Returns:
            最优组合信息字典，包含：
            - optimal_combination: 最优组合方案
            - excess_singles: 多余单张列表（不在任何组合中的单张）
            - alternative_combinations: 备选组合方案
            - combination_score: 组合评分
        """
        if not handcards:
            return {
                'optimal_combination': {},
                'excess_singles': [],
                'alternative_combinations': [],
                'combination_score': 0.0
            }
        
        # 构建牌值映射
        card_val = self._build_card_value_map(rank)
        
        # 1. 扫描所有可能的组合方案
        all_combinations = self._scan_all_combinations(handcards, rank, card_val)
        
        # 2. 评估每个组合方案
        evaluated_combinations = []
        for combo in all_combinations:
            score = self._evaluate_combination(combo, handcards, rank, card_val)
            evaluated_combinations.append({
                'combination': combo,
                'score': score
            })
        
        # 3. 选择最优组合方案（评分最高）
        if evaluated_combinations:
            evaluated_combinations.sort(key=lambda x: x['score'], reverse=True)
            optimal = evaluated_combinations[0]
        else:
            optimal = {'combination': {}, 'score': 0.0}
        
        # 4. 识别多余单张（不在最优组合中的单张）
        excess_singles = self._identify_excess_singles(handcards, optimal['combination'], rank, card_val)
        
        # 5. 备选组合方案（评分前3的方案）
        alternative_combinations = evaluated_combinations[1:4] if len(evaluated_combinations) > 1 else []
        
        return {
            'optimal_combination': optimal['combination'],
            'excess_singles': excess_singles,
            'alternative_combinations': alternative_combinations,
            'combination_score': optimal['score']
        }
    
    def _scan_all_combinations(self, handcards: List[str], rank: str, card_val: Dict[str, int]) -> List[Dict]:
        """
        扫描所有可能的组合方案
        
        策略：
        1. 优先保留炸弹（不拆炸弹）
        2. 优先组成同花顺（如果可能）
        3. 优先组成顺子
        4. 优先组成三带二、三连对、钢板
        5. 最后处理单张、对子、三张
        """
        combinations = []
        
        # 方案1：优先同花顺（如果可能）
        combo1 = self._try_straight_flush_first(handcards, rank, card_val)
        if combo1:
            combinations.append(combo1)
        
        # 方案2：优先炸弹（保留所有炸弹）
        combo2 = self._try_bomb_first(handcards, rank, card_val)
        if combo2:
            combinations.append(combo2)
        
        # 方案3：平衡方案（同花顺+顺子+炸弹）
        combo3 = self._try_balanced(handcards, rank, card_val)
        if combo3:
            combinations.append(combo3)
        
        # 如果没有找到任何组合，使用基础组合
        if not combinations:
            combo_base = self._get_base_combination(handcards, rank, card_val)
            combinations.append(combo_base)
        
        return combinations
    
    def _try_straight_flush_first(self, handcards: List[str], rank: str, card_val: Dict[str, int]) -> Dict:
        """尝试优先组成同花顺的方案"""
        # 使用HandCombiner组合手牌
        sorted_cards, bomb_info = self.combiner.combine_handcards(handcards, rank, card_val)
        
        # 检查是否有同花顺
        straight_flush = sorted_cards.get("StraightFlush", [])
        if straight_flush:
            # 优先保留同花顺
            return {
                'strategy': 'straight_flush_first',
                'sorted_cards': sorted_cards,
                'bomb_info': bomb_info
            }
        
        return {}
    
    def _try_bomb_first(self, handcards: List[str], rank: str, card_val: Dict[str, int]) -> Dict:
        """尝试优先保留炸弹的方案"""
        sorted_cards, bomb_info = self.combiner.combine_handcards(handcards, rank, card_val)
        
        # 检查是否有炸弹
        bombs = sorted_cards.get("Bomb", [])
        if bombs:
            # 优先保留炸弹
            return {
                'strategy': 'bomb_first',
                'sorted_cards': sorted_cards,
                'bomb_info': bomb_info
            }
        
        return {}
    
    def _try_balanced(self, handcards: List[str], rank: str, card_val: Dict[str, int]) -> Dict:
        """尝试平衡方案（同花顺+顺子+炸弹）"""
        sorted_cards, bomb_info = self.combiner.combine_handcards(handcards, rank, card_val)
        
        return {
            'strategy': 'balanced',
            'sorted_cards': sorted_cards,
            'bomb_info': bomb_info
        }
    
    def _get_base_combination(self, handcards: List[str], rank: str, card_val: Dict[str, int]) -> Dict:
        """获取基础组合（默认方案）"""
        sorted_cards, bomb_info = self.combiner.combine_handcards(handcards, rank, card_val)
        
        return {
            'strategy': 'base',
            'sorted_cards': sorted_cards,
            'bomb_info': bomb_info
        }
    
    def _evaluate_combination(self, combo: Dict, handcards: List[str], rank: str, card_val: Dict[str, int]) -> float:
        """
        评估组合方案的优劣
        
        评分标准：
        1. 手数越少越好（减少轮次）
        2. 单张越少越好
        3. 炸弹越多越好
        4. 同花顺优先
        5. 顺子优先
        """
        if not combo or 'sorted_cards' not in combo:
            return 0.0
        
        sorted_cards = combo['sorted_cards']
        score = 0.0
        
        # 1. 计算手数（每种牌型算一手）
        hand_count = 0
        for card_type in ['Single', 'Pair', 'Trips', 'ThreeWithTwo', 'ThreePair', 'TwoTrips', 'Straight', 'StraightFlush', 'Bomb']:
            cards = sorted_cards.get(card_type, [])
            if cards:
                if card_type in ['Pair', 'Trips']:
                    # 对子和三张需要展平
                    flat_cards = self._flatten(cards)
                    hand_count += len(flat_cards) // (2 if card_type == 'Pair' else 3)
                else:
                    hand_count += len(cards)
        
        # 手数越少，评分越高（每减少一手+50分）
        score += (27 - hand_count) * 50
        
        # 2. 单张越少越好（每个单张-10分）
        singles = sorted_cards.get("Single", [])
        score -= len(singles) * 10
        
        # 3. 炸弹越多越好（每个炸弹+100分）
        bombs = sorted_cards.get("Bomb", [])
        score += len(bombs) * 100
        
        # 4. 同花顺优先（每个同花顺+80分）
        straight_flush = sorted_cards.get("StraightFlush", [])
        score += len(straight_flush) * 80
        
        # 5. 顺子优先（每个顺子+40分）
        straights = sorted_cards.get("Straight", [])
        score += len(straights) * 40
        
        # 6. 三带二、三连对、钢板优先（每个+30分）
        three_with_two = sorted_cards.get("ThreeWithTwo", [])
        three_pair = sorted_cards.get("ThreePair", [])
        two_trips = sorted_cards.get("TwoTrips", [])
        score += (len(three_with_two) + len(three_pair) + len(two_trips)) * 30
        
        return score
    
    def _identify_excess_singles(self, handcards: List[str], optimal_combo: Dict, rank: str, card_val: Dict[str, int]) -> List[str]:
        """
        识别多余单张（不在任何组合中的单张）
        
        多余单张的定义：
        - 不在同花顺中
        - 不在顺子中
        - 不在炸弹中
        - 不在三带二中
        - 不在三连对中
        - 不在钢板中
        - 不在对子中（如果是对子的一部分，不算多余）
        - 不在三张中（如果是三张的一部分，不算多余）
        """
        if not optimal_combo or 'sorted_cards' not in optimal_combo:
            # 如果没有最优组合，使用基础组合
            sorted_cards, _ = self.combiner.combine_handcards(handcards, rank, card_val)
        else:
            sorted_cards = optimal_combo['sorted_cards']
        
        # 收集所有在组合中的卡牌
        used_cards = set()
        
        # 同花顺中的卡牌
        for sf in sorted_cards.get("StraightFlush", []):
            if isinstance(sf, list):
                used_cards.update(sf)
            else:
                used_cards.add(sf)
        
        # 顺子中的卡牌
        for st in sorted_cards.get("Straight", []):
            if isinstance(st, list):
                used_cards.update(st)
            else:
                used_cards.add(st)
        
        # 炸弹中的卡牌
        for bomb in sorted_cards.get("Bomb", []):
            if isinstance(bomb, list):
                used_cards.update(bomb)
            else:
                used_cards.add(bomb)
        
        # 三带二中的卡牌
        for tw in sorted_cards.get("ThreeWithTwo", []):
            if isinstance(tw, list):
                used_cards.update(tw)
            else:
                used_cards.add(tw)
        
        # 三连对中的卡牌
        for tp in sorted_cards.get("ThreePair", []):
            if isinstance(tp, list):
                used_cards.update(tp)
            else:
                used_cards.add(tp)
        
        # 钢板中的卡牌
        for tt in sorted_cards.get("TwoTrips", []):
            if isinstance(tt, list):
                used_cards.update(tt)
            else:
                used_cards.add(tt)
        
        # 对子中的卡牌
        for pair in sorted_cards.get("Pair", []):
            if isinstance(pair, list):
                used_cards.update(pair)
            else:
                used_cards.add(pair)
        
        # 三张中的卡牌
        for trip in sorted_cards.get("Trips", []):
            if isinstance(trip, list):
                used_cards.update(trip)
            else:
                used_cards.add(trip)
        
        # 找出不在任何组合中的单张（多余单张）
        excess_singles = []
        for card in handcards:
            if card not in used_cards:
                excess_singles.append(card)
        
        return excess_singles
    
    def _flatten(self, nested_list: List) -> List:
        """展平嵌套列表"""
        result = []
        for item in nested_list:
            if isinstance(item, list):
                result.extend(item)
            else:
                result.append(item)
        return result
    
    def _build_card_value_map(self, rank: str) -> Dict[str, int]:
        """构建牌值映射"""
        card_val = {
            '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
            '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14,
            '2': 15, 'R': 16, 'B': 17  # R=大王, B=小王
        }
        # 等级牌特殊处理
        if rank in card_val:
            card_val[rank] = 15
        return card_val


def find_excess_singles_for_passive_play(handcards: List[str], rank: str, cur_action_rank: str) -> List[str]:
    """
    在被动出牌时，找出可以顺走的多余单张
    
    Args:
        handcards: 当前手牌
        rank: 等级牌
        cur_action_rank: 当前动作的牌值（如"3"、"4"等）
        
    Returns:
        可以顺走的多余单张列表（牌值大于cur_action_rank的单张）
    """
    scanner = OptimalCombinationScanner()
    
    # 扫描最优组合
    result = scanner.scan_optimal_combination(handcards, rank)
    excess_singles = result.get('excess_singles', [])
    
    # 构建牌值映射
    card_val = scanner._build_card_value_map(rank)
    cur_rank_val = card_val.get(cur_action_rank, 0)
    
    # 找出牌值大于cur_action_rank的多余单张
    playable_singles = []
    for card in excess_singles:
        if len(card) >= 2:
            card_rank = card[1] if len(card) == 2 else card[1:]
            card_val_num = card_val.get(card_rank, 0)
            if card_val_num > cur_rank_val:
                playable_singles.append(card)
    
    return playable_singles

