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
    """
    手牌最优组合扫描器（增强版：支持动态调整）
    
    新增功能：
    - 动态调整机制：根据游戏状态动态调整扫描策略
    - 实际动作评估：评估每个动作的组牌效果
    - 对手行为分析：根据对手行为调整策略
    - 游戏阶段感知：根据游戏阶段调整策略
    - 牌力变化感知：根据牌力变化调整策略
    """
    
    def __init__(self):
        self.combiner = HandCombiner()
        # 动态调整状态跟踪
        self.last_hand_count = 27  # 上次手牌数（用于牌力变化感知）
        self.last_power = 0.0  # 上次牌力（用于牌力变化感知）
    
    def scan_optimal_combination(self, handcards: List[str], rank: str, 
                                game_state: Dict = None, action_list: List = None) -> Dict:
        """
        扫描手牌的最优组合方案（增强版：支持动态调整和实际动作评估）
        
        Args:
            handcards: 手牌列表
            rank: 等级牌
            game_state: 游戏状态（可选，用于动态调整）
            action_list: 可用动作列表（可选，用于实际动作评估）
            
        Returns:
            最优组合信息字典，包含：
            - optimal_combination: 最优组合方案
            - excess_singles: 多余单张列表
            - alternative_combinations: 备选组合方案
            - combination_score: 组合评分
            - complex_types: 复杂牌型信息
            - protected_combinations: 受保护组合
            - action_evaluations: 实际动作评估（新增）
            - should_reoptimize: 是否需要重新优化（新增）
        """
        if not handcards:
            return {
                'optimal_combination': {},
                'excess_singles': [],
                'alternative_combinations': [],
                'combination_score': 0.0,
                'complex_types': {},  # 新增
                'protected_combinations': []  # 新增
            }
        
        # 构建牌值映射
        card_val = self._build_card_value_map(rank)
        
        # ⚠️ 动态调整：根据游戏状态调整扫描策略
        game_phase = 'opening'
        opponent_rest_cards = 27
        my_rest_cards = len(handcards) if handcards else 27
        
        if game_state:
            opponent_rest_cards = game_state.get('opponent_rest_cards', 27)
            if opponent_rest_cards >= 20:
                game_phase = 'opening'
            elif opponent_rest_cards >= 10:
                game_phase = 'mid'
            else:
                game_phase = 'endgame'
        
        # 1. 扫描所有可能的组合方案（根据游戏阶段调整策略）
        all_combinations = self._scan_all_combinations(handcards, rank, card_val, game_phase)
        
        # 2. 评估每个组合方案（根据游戏阶段和牌力调整评分）
        evaluated_combinations = []
        current_power = self._calculate_power(handcards, rank, game_phase, opponent_rest_cards)
        
        for combo in all_combinations:
            base_score = self._evaluate_combination(combo, handcards, rank, card_val)
            # 根据游戏阶段和牌力调整评分
            adjusted_score = self._adjust_score_by_game_state(
                base_score, combo, game_phase, current_power, my_rest_cards, opponent_rest_cards
            )
            evaluated_combinations.append({
                'combination': combo,
                'score': adjusted_score,
                'base_score': base_score
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
        
        # 6. 识别复杂牌型信息（新增：供牌型处理器使用）
        complex_types = self._extract_complex_types(optimal['combination'], handcards, rank, card_val)
        
        # 7. 识别受保护组合（新增：不应拆开的组合）
        protected_combinations = self._identify_protected_combinations(optimal['combination'], handcards, rank, card_val)
        
        # 8. 实际动作评估（简化版：仅评估关键动作）
        action_evaluations = {}
        if action_list and len(action_list) <= 50:  # 只评估动作数较少的情况，避免性能问题
            action_evaluations = self._evaluate_actions(
                handcards, action_list, optimal['combination'], rank, card_val, 
                game_phase, current_power, my_rest_cards, opponent_rest_cards
            )
        
        # 9. 更新状态（简化：只更新关键状态）
        self.last_hand_count = my_rest_cards
        self.last_power = current_power
        self.last_phase = game_phase
        
        return {
            'optimal_combination': optimal['combination'],
            'excess_singles': excess_singles,
            'alternative_combinations': alternative_combinations,
            'combination_score': optimal['score'],
            'complex_types': complex_types,
            'protected_combinations': protected_combinations,
            'action_evaluations': action_evaluations,  # 实际动作评估（仅在动作数少时计算）
            'game_phase': game_phase,  # 当前游戏阶段
            'current_power': current_power  # 当前牌力
        }
    
    def _scan_all_combinations(self, handcards: List[str], rank: str, card_val: Dict[str, int], 
                              game_phase: str = 'opening') -> List[Dict]:
        """
        扫描所有可能的组合方案（增强版：根据游戏阶段调整策略）
        
        策略（根据游戏阶段调整）：
        - 开局阶段：优先保留炸弹，优先使用红桃配配炸
        - 中局阶段：优先组成复杂牌型（三带二、三连对、钢板），优先减少手数
        - 残局阶段：优先减少手数，优先出能走完的牌型
        
        Args:
            game_phase: 游戏阶段（'opening', 'mid', 'endgame'）
        """
        combinations = []
        
        # 根据游戏阶段调整扫描策略
        if game_phase == 'opening':
            # 开局阶段：优先保留炸弹，优先使用红桃配配炸
            # 方案1：优先炸弹（保留所有炸弹）
            combo2 = self._try_bomb_first(handcards, rank, card_val)
            if combo2:
                combinations.append(combo2)
            
            # 方案2：优先使用红桃配（级牌红桃配策略，优先配炸）
            red_heart_combo = self._try_red_heart_wildcard_first(handcards, rank, card_val)
            if red_heart_combo:
                combinations.append(red_heart_combo)
            
            # 方案3：平衡方案
            combo3 = self._try_balanced(handcards, rank, card_val)
            if combo3:
                combinations.append(combo3)
        
        elif game_phase == 'mid':
            # 中局阶段：优先组成复杂牌型，优先减少手数
            # 方案1：优先复杂牌型（三带二、三连对、钢板）
            complex_combo = self._try_complex_types_first(handcards, rank, card_val)
            if complex_combo:
                combinations.append(complex_combo)
            
            # 方案2：优先使用红桃配（配复杂牌型）
            red_heart_combo = self._try_red_heart_wildcard_first(handcards, rank, card_val)
            if red_heart_combo:
                combinations.append(red_heart_combo)
            
            # 方案3：平衡方案
            combo3 = self._try_balanced(handcards, rank, card_val)
            if combo3:
                combinations.append(combo3)
        
        else:  # endgame
            # 残局阶段：优先减少手数，优先出能走完的牌型
            # 方案1：优先减少手数（优先复杂牌型）
            complex_combo = self._try_complex_types_first(handcards, rank, card_val)
            if complex_combo:
                combinations.append(complex_combo)
            
            # 方案2：优先同花顺（如果可能，残局同花顺是利器）
            combo1 = self._try_straight_flush_first(handcards, rank, card_val)
            if combo1:
                combinations.append(combo1)
            
            # 方案3：平衡方案
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
    
    def _try_complex_types_first(self, handcards: List[str], rank: str, card_val: Dict[str, int]) -> Dict:
        """尝试优先组成复杂牌型的方案（三带二、三连对、钢板）"""
        sorted_cards, bomb_info = self.combiner.combine_handcards(handcards, rank, card_val)
        
        # 检查是否有复杂牌型
        three_with_two = sorted_cards.get("ThreeWithTwo", [])
        three_pair = sorted_cards.get("ThreePair", [])
        two_trips = sorted_cards.get("TwoTrips", [])
        
        if three_with_two or three_pair or two_trips:
            return {
                'strategy': 'complex_types_first',
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
    
    def _has_red_heart_wildcard(self, handcards: List[str], rank: str) -> bool:
        """
        检查手牌中是否有红桃配（红心级牌）
        
        Args:
            handcards: 手牌列表
            rank: 级牌
            
        Returns:
            True: 有红桃配，False: 没有
        """
        red_heart_card = f'H{rank}'  # 红桃配格式：H + rank
        return red_heart_card in handcards
    
    def _try_red_heart_wildcard_first(self, handcards: List[str], rank: str, card_val: Dict[str, int]) -> Dict:
        """
        尝试优先使用红桃配的策略
        
        红桃配使用优先级（根据实战统计）：
        1. 配炸弹（85%）：特别是配4头炸（51%），配6头炸（5%），忌配5头炸（1%）
        2. 配同花顺（28%）
        3. 补缺（12%）：配顺子、配木板、配钢板
        4. 残局运用：配小对子、配顺子、配三带二
        """
        # 检查是否有红桃配
        if not self._has_red_heart_wildcard(handcards, rank):
            return {}
        
        red_heart_card = f'H{rank}'
        
        # 使用基础组合作为起点
        sorted_cards, bomb_info = self.combiner.combine_handcards(handcards, rank, card_val)
        
        # 尝试用红桃配优化组合
        optimized_sorted_cards = self._optimize_with_red_heart(handcards, sorted_cards, rank, card_val, red_heart_card)
        
        return {
            'strategy': 'red_heart_wildcard_first',
            'sorted_cards': optimized_sorted_cards,
            'bomb_info': bomb_info,
            'red_heart_used': True
        }
    
    def _optimize_with_red_heart(self, handcards: List[str], sorted_cards: Dict, rank: str, 
                              card_val: Dict[str, int], red_heart_card: str) -> Dict:
        """
        使用红桃配优化组合
        
        策略优先级（根据实战统计）：
        1. 配4头炸（最优先，51%使用率）- 特别是和小3头成炸弹，称为"麻雀变凤凰"
        2. 配6头炸（5%使用率）
        3. 配同花顺（28%使用率）
        4. 配顺子补缺（12%使用率）
        5. 配木板、钢板
        6. 配三带二
        """
        import copy
        optimized = copy.deepcopy(sorted_cards)
        red_heart_used = False
        
        # 统计各种牌型的数量，用于判断红桃配的最佳用途
        trips = optimized.get("Trips", [])
        pairs = optimized.get("Pair", [])
        singles = optimized.get("Single", [])
        
        # 统计手牌中每张牌的数量（排除红桃配）
        card_count = {}
        for card in handcards:
            if card != red_heart_card:  # 排除红桃配本身
                card_value = card[1] if len(card) > 1 else card[0]
                if card_value not in card_count:
                    card_count[card_value] = []
                card_count[card_value].append(card)
        
        # 策略1：配4头炸（最优先，51%使用率）
        # 如果有3张相同点数的牌，可以用红桃配组成4头炸
        for value, cards in card_count.items():
            if len(cards) == 3 and not red_heart_used:
                # 可以用红桃配组成4头炸
                bomb_cards = cards + [red_heart_card]
                if "Bomb" not in optimized:
                    optimized["Bomb"] = []
                optimized["Bomb"].append(bomb_cards)
                # 从Trips中移除这3张牌
                if "Trips" in optimized:
                    for trip in list(optimized["Trips"]):
                        if isinstance(trip, list) and set(trip) == set(cards):
                            optimized["Trips"].remove(trip)
                            break
                        elif trip == cards[0] and len(trips) == 1:
                            # 处理单张三张的情况
                            optimized["Trips"].remove(trip)
                            break
                red_heart_used = True
                break
        
        # 策略2：配6头炸（如果有5张相同点数的牌，5%使用率）
        if not red_heart_used:
            for value, cards in card_count.items():
                if len(cards) == 5:
                    # 可以用红桃配组成6头炸
                    bomb_cards = cards + [red_heart_card]
                    if "Bomb" not in optimized:
                        optimized["Bomb"] = []
                    optimized["Bomb"].append(bomb_cards)
                    # 从Bomb中移除原来的5头炸（如果存在）
                    if "Bomb" in optimized:
                        for bomb in list(optimized["Bomb"]):
                            if isinstance(bomb, list) and set(bomb) == set(cards):
                                optimized["Bomb"].remove(bomb)
                                break
                    red_heart_used = True
                    break
        
        # 策略3：配同花顺（28%使用率）
        # 注意：这里简化处理，实际需要更复杂的同花顺检测逻辑
        # 如果有4张同花顺的牌，缺1张，可以用红桃配补缺
        
        # 策略4：配顺子补缺（12%使用率）
        # 如果有单张可以组成顺子，用红桃配补缺
        # 注意：这里简化处理，实际需要更复杂的顺子检测逻辑
        
        # 策略5：配木板（三连对）
        # 如果有2个对子，可以用红桃配组成三连对
        # 注意：这里简化处理，实际需要更复杂的检测逻辑
        
        # 策略6：配三带二
        # 如果有1个三张和1个对子，可以用红桃配组成三带二
        # 注意：这里简化处理，实际需要更复杂的检测逻辑
        
        return optimized
    
    def _evaluate_combination(self, combo: Dict, handcards: List[str], rank: str, card_val: Dict[str, int]) -> float:
        """
        评估组合方案的优劣
        
        评分标准（优先级从高到低）：
        1. 手数越少越好（减少轮次）- 最重要原则
        2. 减少<10的单张（小单张）- 第二重要原则
        3. 炸弹越多越好
        4. 同花顺优先
        5. 顺子优先
        """
        if not combo or 'sorted_cards' not in combo:
            return 0.0
        
        sorted_cards = combo['sorted_cards']
        score = 0.0
        
        # ⚠️ 原则1：减少轮次（手数）- 最重要，权重最高
        # 计算手数（每种牌型算一手）
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
        
        # 手数越少，评分越高（每减少一手+100分，提高权重确保这是最重要的原则）
        rounds_reduced = 27 - hand_count
        score += rounds_reduced * 100
        
        # ⚠️ 原则2：减少<10的单张（小单张）- 第二重要原则
        singles = sorted_cards.get("Single", [])
        small_singles_count = 0  # <10的单张数量
        large_singles_count = 0   # >=10的单张数量
        
        # 小单张的牌值：3, 4, 5, 6, 7, 8, 9（对应牌值3-9）
        small_ranks = ['3', '4', '5', '6', '7', '8', '9']
        
        for single in singles:
            # 单张可能是字符串（如'S7'）或列表（如['S7']）
            if isinstance(single, list):
                # 如果是列表，取第一个元素
                card = single[0] if single else ""
            else:
                card = single
            
            if card and isinstance(card, str) and len(card) >= 2:
                card_rank = card[1:]  # 提取牌值（去掉花色，如'S7' -> '7'）
                # 检查是否是级牌（级牌不算小单张）
                if card_rank == rank:
                    large_singles_count += 1  # 级牌不算小单张
                elif card_rank in small_ranks:
                    small_singles_count += 1
                else:
                    large_singles_count += 1
        
        # 小单张（<10）惩罚更重：每个-30分
        score -= small_singles_count * 30
        # 大单张（>=10）惩罚较轻：每个-10分
        score -= large_singles_count * 10
        
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
        
        # 7. 红桃配使用奖励（如果使用了红桃配策略）
        if combo.get('red_heart_used', False):
            # 红桃配配成炸弹额外奖励
            bombs = sorted_cards.get("Bomb", [])
            red_heart_bombs = [bomb for bomb in bombs if any(card.startswith('H') and card[1:] == rank for card in bomb)]
            if red_heart_bombs:
                # 配成4头炸奖励最高（+150分）
                for bomb in red_heart_bombs:
                    if len(bomb) == 4:
                        score += 150
                    elif len(bomb) == 6:
                        score += 120  # 配成6头炸奖励次之
                    else:
                        score += 100  # 其他炸弹奖励
            
            # 红桃配配成同花顺额外奖励（+100分）
            straight_flush = sorted_cards.get("StraightFlush", [])
            red_heart_sf = [sf for sf in straight_flush if any(card.startswith('H') and card[1:] == rank for card in (sf if isinstance(sf, list) else [sf]))]
            if red_heart_sf:
                score += len(red_heart_sf) * 100
        
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
    
    def _extract_complex_types(self, optimal_combo: Dict, handcards: List[str], rank: str, card_val: Dict[str, int]) -> Dict[str, List]:
        """
        提取复杂牌型信息（供牌型处理器使用）
        
        Returns:
            复杂牌型字典，格式：
            {
                'TwoTrips': [['444', '555']],  # 可用的钢板
                'ThreePair': [['223344']],      # 可用的三连对
                'ThreeWithTwo': [['44422', '55533']]  # 可用的三带二
            }
        """
        complex_types = {
            'TwoTrips': [],
            'ThreePair': [],
            'ThreeWithTwo': []
        }
        
        if not optimal_combo or 'sorted_cards' not in optimal_combo:
            return complex_types
        
        sorted_cards = optimal_combo['sorted_cards']
        
        # 提取钢板（TwoTrips）
        two_trips = sorted_cards.get("TwoTrips", [])
        for tt in two_trips:
            if isinstance(tt, list):
                complex_types['TwoTrips'].append(tt)
        
        # 提取三连对（ThreePair）
        three_pair = sorted_cards.get("ThreePair", [])
        for tp in three_pair:
            if isinstance(tp, list):
                complex_types['ThreePair'].append(tp)
        
        # 提取三带二（ThreeWithTwo）
        three_with_two = sorted_cards.get("ThreeWithTwo", [])
        for tw in three_with_two:
            if isinstance(tw, list):
                complex_types['ThreeWithTwo'].append(tw)
        
        return complex_types
    
    def _identify_protected_combinations(self, optimal_combo: Dict, handcards: List[str], rank: str, card_val: Dict[str, int]) -> List[List[str]]:
        """
        识别受保护组合（不应拆开的组合）
        
        受保护组合包括：
        - 炸弹（Bomb）
        - 同花顺（StraightFlush）
        - 钢板（TwoTrips）
        - 三连对（ThreePair）
        - 三带二（ThreeWithTwo）
        - 顺子（Straight）
        
        Returns:
            受保护组合列表，每个组合是一个卡牌列表
        """
        protected = []
        
        if not optimal_combo or 'sorted_cards' not in optimal_combo:
            return protected
        
        sorted_cards = optimal_combo['sorted_cards']
        
        # 炸弹（最高优先级保护）
        bombs = sorted_cards.get("Bomb", [])
        for bomb in bombs:
            if isinstance(bomb, list):
                protected.append(bomb)
        
        # 同花顺（高优先级保护）
        straight_flush = sorted_cards.get("StraightFlush", [])
        for sf in straight_flush:
            if isinstance(sf, list):
                protected.append(sf)
        
        # 钢板（高优先级保护）
        two_trips = sorted_cards.get("TwoTrips", [])
        for tt in two_trips:
            if isinstance(tt, list):
                protected.append(tt)
        
        # 三连对（高优先级保护）
        three_pair = sorted_cards.get("ThreePair", [])
        for tp in three_pair:
            if isinstance(tp, list):
                protected.append(tp)
        
        # 三带二（中优先级保护）
        three_with_two = sorted_cards.get("ThreeWithTwo", [])
        for tw in three_with_two:
            if isinstance(tw, list):
                protected.append(tw)
        
        # 顺子（中优先级保护）
        straights = sorted_cards.get("Straight", [])
        for st in straights:
            if isinstance(st, list):
                protected.append(st)
        
        return protected
    
    def _calculate_power(self, handcards: List[str], rank: str, game_phase: str, 
                        opponent_rest_cards: int) -> float:
        """
        计算当前牌力（用于牌力变化感知）
        
        Args:
            handcards: 手牌列表
            rank: 等级牌
            game_phase: 游戏阶段
            opponent_rest_cards: 对手剩余牌数
            
        Returns:
            牌力值（0-10）
        """
        try:
            from .card_power_evaluator import calculate_card_power
            cur_level_rank = int(rank) if rank.isdigit() else 10
            power_result = calculate_card_power(
                handcards,
                game_phase=game_phase,
                opponent_rest_cards=opponent_rest_cards,
                cur_level_rank=cur_level_rank
            )
            return power_result.get('total_power', 5.0)
        except Exception:
            # 降级：简单估算
            my_rest_cards = len(handcards) if handcards else 27
            # 牌数越少，牌力越强（简化估算）
            return max(0.0, min(10.0, (27 - my_rest_cards) / 2.7))
    
    def _adjust_score_by_game_state(self, base_score: float, combo: Dict, game_phase: str,
                                   current_power: float, my_rest_cards: int, 
                                   opponent_rest_cards: int) -> float:
        """
        根据游戏状态调整评分（游戏阶段感知和牌力变化感知）
        
        Args:
            base_score: 基础评分
            combo: 组合方案
            game_phase: 游戏阶段
            current_power: 当前牌力
            my_rest_cards: 我方剩余牌数
            opponent_rest_cards: 对手剩余牌数
            
        Returns:
            调整后的评分
        """
        adjusted_score = base_score
        
        # 调整1：残局阶段，优先减少手数
        if game_phase == 'endgame':
            sorted_cards = combo.get('sorted_cards', {})
            # 计算手数
            hand_count = 0
            for card_type in ['Single', 'Pair', 'Trips', 'ThreeWithTwo', 'ThreePair', 
                            'TwoTrips', 'Straight', 'StraightFlush', 'Bomb']:
                cards = sorted_cards.get(card_type, [])
                if cards:
                    if card_type in ['Pair', 'Trips']:
                        flat_cards = self._flatten(cards)
                        hand_count += len(flat_cards) // (2 if card_type == 'Pair' else 3)
                    else:
                        hand_count += len(cards)
            
            # 残局阶段，手数越少越好
            rounds_reduced = 27 - hand_count
            adjusted_score += rounds_reduced * 30.0  # 每减少一手+30分
        
        # 调整2：手牌较少时，优先减少单牌
        if my_rest_cards <= 10:
            sorted_cards = combo.get('sorted_cards', {})
            singles = sorted_cards.get("Single", [])
            singles_reduced = 10 - len(singles)  # 假设原来有10个单张
            adjusted_score += singles_reduced * 25.0  # 每减少一个单张+25分
        
        # 调整3：残局最后阶段，优先出能走完的牌型
        if my_rest_cards <= 5:
            sorted_cards = combo.get('sorted_cards', {})
            # 检查是否有能走完的牌型（手数≤2）
            hand_count = 0
            for card_type in ['Single', 'Pair', 'Trips', 'ThreeWithTwo', 'ThreePair', 
                            'TwoTrips', 'Straight', 'StraightFlush', 'Bomb']:
                cards = sorted_cards.get(card_type, [])
                if cards:
                    if card_type in ['Pair', 'Trips']:
                        flat_cards = self._flatten(cards)
                        hand_count += len(flat_cards) // (2 if card_type == 'Pair' else 3)
                    else:
                        hand_count += len(cards)
            
            if hand_count <= 2:
                adjusted_score += 40.0  # 能走完的牌型+40分
        
        # 调整4：牌力变化感知
        power_change = current_power - self.last_power
        if abs(power_change) >= 2.0:
            if power_change > 0:
                # 牌力增强，更激进组牌
                sorted_cards = combo.get('sorted_cards', {})
                # 检查是否能减少轮次
                hand_count = 0
                for card_type in ['Single', 'Pair', 'Trips', 'ThreeWithTwo', 'ThreePair', 
                                'TwoTrips', 'Straight', 'StraightFlush', 'Bomb']:
                    cards = sorted_cards.get(card_type, [])
                    if cards:
                        if card_type in ['Pair', 'Trips']:
                            flat_cards = self._flatten(cards)
                            hand_count += len(flat_cards) // (2 if card_type == 'Pair' else 3)
                        else:
                            hand_count += len(cards)
                
                rounds_reduced = 27 - hand_count
                adjusted_score += rounds_reduced * 15.0  # 牌力增强，优先减少轮次
            else:
                # 牌力减弱，保守组牌，保留炸弹
                sorted_cards = combo.get('sorted_cards', {})
                bombs = sorted_cards.get("Bomb", [])
                adjusted_score += len(bombs) * 20.0  # 牌力减弱，优先保留炸弹
        
        return adjusted_score
    
    def _evaluate_actions(self, handcards: List[str], action_list: List, optimal_combo: Dict,
                         rank: str, card_val: Dict[str, int], game_phase: str,
                         current_power: float, my_rest_cards: int, opponent_rest_cards: int) -> Dict:
        """
        评估每个动作的组牌效果（实际动作评估）
        
        Args:
            handcards: 当前手牌
            action_list: 可用动作列表
            optimal_combo: 最优组合方案
            rank: 等级牌
            card_val: 牌值映射
            game_phase: 游戏阶段
            current_power: 当前牌力
            my_rest_cards: 我方剩余牌数
            opponent_rest_cards: 对手剩余牌数
            
        Returns:
            动作评估字典，格式：
            {
                action_index: {
                    'rounds_reduced': 减少的轮次数,
                    'singles_reduced': 减少的单牌数,
                    'score': 综合评分,
                    'reasons': [原因列表]
                }
            }
        """
        action_evaluations = {}
        
        if not action_list or not handcards:
            return action_evaluations
        
        # 获取最优组合的手牌结构
        sorted_cards = optimal_combo.get('sorted_cards', {}) if optimal_combo else {}
        
        for idx, action in enumerate(action_list):
            if not isinstance(action, list) or len(action) < 1:
                continue
            
            action_type = action[0]
            if action_type == "PASS":
                continue
            
            action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
            if not action_cards:
                continue
            
            # 计算剩余手牌
            remaining_cards = handcards.copy()
            for card in action_cards:
                if card in remaining_cards:
                    remaining_cards.remove(card)
            
            # 统计剩余手牌的单牌数
            from collections import Counter
            rank_count = Counter()
            for card in remaining_cards:
                if len(card) >= 2:
                    card_rank = card[1] if len(card) == 2 else card[1:]
                    rank_count[card_rank] += 1
            
            remaining_singles = sum(1 for count in rank_count.values() if count == 1)
            
            # 统计原始单牌数（估算）
            original_rank_count = Counter()
            for card in handcards:
                if len(card) >= 2:
                    card_rank = card[1] if len(card) == 2 else card[1:]
                    original_rank_count[card_rank] += 1
            original_singles = sum(1 for count in original_rank_count.values() if count == 1)
            
            # 计算减少的单牌数
            singles_reduced = max(0, original_singles - remaining_singles)
            
            # 计算减少的轮次数（简化：根据动作类型估算）
            rounds_reduced = 0
            if action_type in ["ThreeWithTwo", "ThreePair", "TwoTrips", "Straight"]:
                if len(action_cards) >= 5:
                    rounds_reduced = 1
            elif action_type == "StraightFlush":
                if len(action_cards) >= 5:
                    rounds_reduced = 1
            
            # 计算综合评分
            score = 0.0
            reasons = []
            
            # 轮次减少加分（胜负规则优先）
            if rounds_reduced > 0:
                score += rounds_reduced * 45.0
                reasons.append(f"减少{rounds_reduced}轮次（胜负规则优先）")
            
            # 单牌减少加分
            if singles_reduced > 0:
                score += singles_reduced * 20.0
                reasons.append(f"减少{singles_reduced}个单牌")
            
            # 根据游戏阶段调整
            if game_phase == 'endgame':
                if rounds_reduced > 0:
                    score += 30.0
                    reasons.append("残局阶段，减少轮次更重要")
                if singles_reduced > 0:
                    score += 25.0
                    reasons.append("残局阶段，减少单牌更重要")
            
            # 根据牌力调整
            power_change = current_power - self.last_power
            if power_change > 0:
                if rounds_reduced > 0:
                    score += 15.0
                    reasons.append("牌力增强，优先减少轮次")
            else:
                # 牌力减弱，保留炸弹更重要
                if action_type not in ["Bomb", "BOMB"]:
                    # 检查是否保留了炸弹
                    remaining_rank_count = Counter()
                    for card in remaining_cards:
                        if len(card) >= 2:
                            card_rank = card[1] if len(card) == 2 else card[1:]
                            remaining_rank_count[card_rank] += 1
                    
                    bombs_kept = sum(1 for count in remaining_rank_count.values() if count >= 4)
                    if bombs_kept > 0:
                        score += 20.0
                        reasons.append(f"牌力减弱，保留{bombs_kept}个炸弹")
            
            action_evaluations[idx] = {
                'rounds_reduced': rounds_reduced,
                'singles_reduced': singles_reduced,
                'score': score,
                'reasons': reasons,
                'action_type': action_type
            }
        
        return action_evaluations
    
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
        """
        构建牌值映射
        
        牌值大小关系：
        - 3-9, T, J, Q, K, A: 3-14
        - 级牌: 15 (可压制A及以下)
        - 小王(B): 16 (可压制级牌及以下)
        - 大王(R): 17 (可压制小王及以下)
        """
        card_val = {
            '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
            '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14,
            'B': 16,  # 小王（可压制级牌及以下）
            'R': 17   # 大王（可压制小王及以下）
        }
        # 等级牌特殊处理：级牌值为15（可压制A及以下）
        if rank in ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']:
            card_val[rank] = 15
        # 如果级牌是2，也需要设置
        if rank == '2':
            card_val['2'] = 15
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
    
    # 扫描最优组合（使用默认参数，保持向后兼容）
    result = scanner.scan_optimal_combination(handcards, rank, game_state=None, action_list=None)
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

