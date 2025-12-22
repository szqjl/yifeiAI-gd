# -*- coding: utf-8 -*-
"""
手牌结构分析器 (Hand Structure Analyzer)
功能：
- 分析手牌结构，返回详细信息
- 比lalala更深入的分析（组合潜力、灵活性等）
"""

from typing import Dict, List
import sys
from pathlib import Path
from collections import Counter

# 将 src 目录添加到系统路径
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from game_logic.hand_combiner import HandCombiner


class HandStructureAnalyzer:
    """手牌结构分析器（提升：比lalala更深入）"""
    
    def __init__(self):
        self.combiner = HandCombiner()
    
    def analyze(self, handcards: List[str], rank: str) -> Dict:
        """
        分析手牌结构（提升：返回更详细的信息）
        
        Args:
            handcards: 手牌列表
            rank: 等级牌
        
        Returns:
            手牌结构信息字典
        """
        structure = {
            # 基础信息（lalala有）
            'single_member': [],      # 单张成员
            'pair_member': [],        # 对子成员
            'trip_member': [],        # 三张成员
            'bomb_member': [],        # 炸弹成员
            'straight_member': [],    # 顺子成员
            
            # 增强信息（YF新增）
            'card_value_distribution': {},  # 牌值分布
            'combo_potential': {},          # 组合潜力
            'destructible_combos': [],      # 可破坏的组合
            'protected_combos': [],         # 受保护的组合
            'flexibility_score': 0.0,       # 灵活性评分
            'threat_level': 0.0,           # 威胁等级
        }
        
        if not handcards:
            return structure
        
        # 分析各种牌型成员
        sorted_cards = self._combine_handcards(handcards, rank)
        structure['single_member'] = sorted_cards.get("Single", [])
        structure['pair_member'] = self._flatten(sorted_cards.get("Pair", []))
        structure['trip_member'] = self._flatten(sorted_cards.get("Trips", []))
        structure['bomb_member'] = self._flatten(sorted_cards.get("Bomb", []))
        structure['straight_member'] = self._extract_straight_members(sorted_cards)
        
        # 增强分析（YF新增）
        structure['card_value_distribution'] = self._analyze_value_distribution(handcards, rank)
        structure['combo_potential'] = self._analyze_combo_potential(sorted_cards)
        structure['destructible_combos'] = self._find_destructible_combos(sorted_cards)
        structure['protected_combos'] = self._find_protected_combos(sorted_cards)
        structure['flexibility_score'] = self._calculate_flexibility(structure)
        structure['threat_level'] = self._calculate_threat_level(structure)
        
        return structure
    
    def _combine_handcards(self, handcards: List[str], rank: str) -> Dict:
        """组合手牌（使用HandCombiner）"""
        # 构建牌值映射
        card_val = self._build_card_value_map(rank)
        
        # 调用HandCombiner的方法
        sorted_cards, bomb_info = self.combiner.combine_handcards(handcards, rank, card_val)
        
        return sorted_cards
    
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
    
    def _flatten(self, nested_list: List) -> List:
        """展平嵌套列表"""
        result = []
        for item in nested_list:
            if isinstance(item, list):
                result.extend(item)
            else:
                result.append(item)
        return result
    
    def _extract_straight_members(self, sorted_cards: Dict) -> List:
        """提取顺子成员"""
        straight_member = []
        if sorted_cards.get("Straight"):
            straight_member.extend(sorted_cards["Straight"][0] if sorted_cards["Straight"] else [])
        if sorted_cards.get("StraightFlush"):
            straight_member.extend(sorted_cards["StraightFlush"][0] if sorted_cards["StraightFlush"] else [])
        return straight_member
    
    def _analyze_value_distribution(self, handcards: List[str], rank: str) -> Dict:
        """分析牌值分布（YF新增）"""
        if not handcards:
            return {}
        
        # 统计牌值分布
        value_count = Counter()
        card_val = self._build_card_value_map(rank)
        
        for card in handcards:
            card_value = card[1] if len(card) > 1 else card[0]
            # 处理等级牌
            if card_value == rank:
                value = 15
            else:
                value = card_val.get(card_value, 0)
            value_count[value] += 1
        
        # 计算分布统计
        total_cards = len(handcards)
        distribution = {
            'value_count': dict(value_count),
            'high_value_ratio': sum(count for val, count in value_count.items() if val >= 12) / total_cards if total_cards > 0 else 0,
            'low_value_ratio': sum(count for val, count in value_count.items() if val <= 6) / total_cards if total_cards > 0 else 0,
            'max_value': max(value_count.keys()) if value_count else 0,
            'min_value': min(value_count.keys()) if value_count else 0,
        }
        
        return distribution
    
    def _analyze_combo_potential(self, sorted_cards: Dict) -> Dict:
        """分析组合潜力（YF新增：预测未来可能的组合）"""
        potential = {
            'can_form_pair': [],      # 可以形成对子的单张（需要等待另一张）
            'can_form_trip': [],      # 可以形成三张的对子（需要等待另一张）
            'can_form_straight': [],  # 可以形成顺子的牌
            'can_form_bomb': [],      # 可以形成炸弹的三张（需要等待另一张）
        }
        
        # 分析单张：如果有多个相同牌值的单张，可以形成对子
        single_cards = sorted_cards.get("Single", [])
        single_values = {}
        for card in single_cards:
            card_value = card[1] if len(card) > 1 else card[0]
            if card_value not in single_values:
                single_values[card_value] = []
            single_values[card_value].append(card)
        
        # 找出可以形成对子的单张（相同牌值的单张）
        for value, cards in single_values.items():
            if len(cards) >= 1:
                potential['can_form_pair'].extend(cards)
        
        # 分析对子：如果有多个相同牌值的对子，可以形成三张或炸弹
        pair_cards = sorted_cards.get("Pair", [])
        pair_values = {}
        for pair in pair_cards:
            if isinstance(pair, list) and len(pair) > 0:
                card_value = pair[0][1] if len(pair[0]) > 1 else pair[0][0]
                if card_value not in pair_values:
                    pair_values[card_value] = []
                pair_values[card_value].append(pair)
        
        # 找出可以形成三张的对子
        for value, pairs in pair_values.items():
            if len(pairs) >= 1:
                potential['can_form_trip'].extend(pairs)
        
        # 分析顺子潜力：找出可以形成顺子的单张序列
        all_cards = single_cards + self._flatten(pair_cards)
        potential['can_form_straight'] = self._find_straight_potential(all_cards)
        
        # 分析炸弹潜力：三张可以形成炸弹
        trips_cards = sorted_cards.get("Trips", [])
        for trip in trips_cards:
            if isinstance(trip, list) and len(trip) > 0:
                potential['can_form_bomb'].append(trip)
        
        return potential
    
    def _find_straight_potential(self, cards: List) -> List:
        """找出可以形成顺子的牌"""
        if len(cards) < 5:
            return []
        
        # 提取牌值并排序
        card_val = self._build_card_value_map("2")
        card_values = []
        for card in cards:
            if isinstance(card, str):
                card_value = card[1] if len(card) > 1 else card[0]
                value = card_val.get(card_value, 0)
                if value > 0:
                    card_values.append((value, card))
        
        card_values.sort(key=lambda x: x[0])
        
        # 找出连续5张以上的序列
        potential_straights = []
        for i in range(len(card_values) - 4):
            sequence = [card_values[i]]
            for j in range(i + 1, len(card_values)):
                if card_values[j][0] == sequence[-1][0] + 1:
                    sequence.append(card_values[j])
                    if len(sequence) >= 5:
                        potential_straights.extend([card for _, card in sequence])
                        break
        
        return potential_straights
    
    def _find_destructible_combos(self, sorted_cards: Dict) -> List:
        """查找可破坏的组合（YF新增：容易被拆散的组合）"""
        destructible = []
        
        # 三张可以拆成单张+对子
        trips = sorted_cards.get("Trips", [])
        for trip in trips:
            if isinstance(trip, list) and len(trip) >= 3:
                destructible.append({
                    'type': 'Trips',
                    'cards': trip,
                    'can_split_to': ['Single', 'Pair']
                })
        
        # 对子可以拆成两个单张
        pairs = sorted_cards.get("Pair", [])
        for pair in pairs:
            if isinstance(pair, list) and len(pair) >= 2:
                destructible.append({
                    'type': 'Pair',
                    'cards': pair,
                    'can_split_to': ['Single', 'Single']
                })
        
        # 顺子可以拆成多个单张或对子
        straights = sorted_cards.get("Straight", []) + sorted_cards.get("StraightFlush", [])
        for straight in straights:
            if isinstance(straight, list) and len(straight) >= 5:
                destructible.append({
                    'type': 'Straight',
                    'cards': straight,
                    'can_split_to': ['Multiple Singles']
                })
        
        return destructible
    
    def _find_protected_combos(self, sorted_cards: Dict) -> List:
        """查找受保护的组合（YF新增：不容易被拆散的组合）"""
        protected = []
        
        # 炸弹是受保护的（不能拆）
        bombs = sorted_cards.get("Bomb", [])
        for bomb in bombs:
            if isinstance(bomb, list) and len(bomb) >= 4:
                protected.append({
                    'type': 'Bomb',
                    'cards': bomb,
                    'protection_level': 'high'
                })
        
        # 三带二是受保护的（组合完整）
        three_with_two = sorted_cards.get("ThreeWithTwo", [])
        for combo in three_with_two:
            if isinstance(combo, list) and len(combo) >= 5:
                protected.append({
                    'type': 'ThreeWithTwo',
                    'cards': combo,
                    'protection_level': 'medium'
                })
        
        # 三连对是受保护的（组合完整）
        three_pair = sorted_cards.get("ThreePair", [])
        for combo in three_pair:
            if isinstance(combo, list) and len(combo) >= 6:
                protected.append({
                    'type': 'ThreePair',
                    'cards': combo,
                    'protection_level': 'medium'
                })
        
        return protected
    
    def _calculate_flexibility(self, structure: Dict) -> float:
        """计算灵活性评分（YF新增：手牌可以灵活组合的程度）"""
        flexibility = 0.0
        
        # 因子1: 单张数量（单张越多，灵活性越高）
        single_count = len(structure.get('single_member', []))
        flexibility += min(single_count * 0.1, 0.3)  # 最多0.3分
        
        # 因子2: 组合潜力（可以形成的组合越多，灵活性越高）
        combo_potential = structure.get('combo_potential', {})
        potential_count = (
            len(combo_potential.get('can_form_pair', [])) +
            len(combo_potential.get('can_form_trip', [])) +
            len(combo_potential.get('can_form_straight', []))
        )
        flexibility += min(potential_count * 0.05, 0.3)  # 最多0.3分
        
        # 因子3: 可破坏组合（可以拆分的组合越多，灵活性越高）
        destructible_count = len(structure.get('destructible_combos', []))
        flexibility += min(destructible_count * 0.1, 0.2)  # 最多0.2分
        
        # 因子4: 牌型多样性（牌型种类越多，灵活性越高）
        type_count = sum(1 for key in ['single_member', 'pair_member', 'trip_member', 
                                       'bomb_member', 'straight_member'] 
                        if structure.get(key))
        flexibility += min(type_count * 0.05, 0.2)  # 最多0.2分
        
        return min(flexibility, 1.0)  # 限制在0-1之间
    
    def _calculate_threat_level(self, structure: Dict) -> float:
        """计算威胁等级（YF新增：手牌对对手的威胁程度）"""
        threat = 0.0
        
        # 因子1: 炸弹数量（炸弹越多，威胁越大）
        bomb_count = len(structure.get('bomb_member', []))
        threat += min(bomb_count * 0.2, 0.4)  # 最多0.4分
        
        # 因子2: 高牌值比例（高牌值越多，威胁越大）
        value_dist = structure.get('card_value_distribution', {})
        high_value_ratio = value_dist.get('high_value_ratio', 0.0)
        threat += high_value_ratio * 0.3  # 最多0.3分
        
        # 因子3: 受保护组合（受保护组合越多，威胁越大）
        protected_count = len(structure.get('protected_combos', []))
        threat += min(protected_count * 0.1, 0.2)  # 最多0.2分
        
        # 因子4: 最大牌值（最大牌值越大，威胁越大）
        max_value = value_dist.get('max_value', 0)
        if max_value >= 15:  # 2或王
            threat += 0.1
        
        return min(threat, 1.0)  # 限制在0-1之间

