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
        # TODO: 调用HandCombiner的方法
        # 这里先返回一个基本结构
        return {
            "Single": [],
            "Pair": [],
            "Trips": [],
            "Bomb": [],
            "Straight": [],
            "StraightFlush": [],
        }
    
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
        # TODO: 实现牌值分布分析
        return {}
    
    def _analyze_combo_potential(self, sorted_cards: Dict) -> Dict:
        """分析组合潜力（YF新增：预测未来可能的组合）"""
        potential = {
            'can_form_pair': [],      # 可以形成对子的单张
            'can_form_trip': [],      # 可以形成三张的对子
            'can_form_straight': [],  # 可以形成顺子的牌
        }
        # TODO: 实现组合潜力分析逻辑
        return potential
    
    def _find_destructible_combos(self, sorted_cards: Dict) -> List:
        """查找可破坏的组合（YF新增）"""
        # TODO: 实现可破坏组合查找
        return []
    
    def _find_protected_combos(self, sorted_cards: Dict) -> List:
        """查找受保护的组合（YF新增）"""
        # TODO: 实现受保护组合查找
        return []
    
    def _calculate_flexibility(self, structure: Dict) -> float:
        """计算灵活性评分（YF新增）"""
        # TODO: 实现灵活性评分计算
        return 0.0
    
    def _calculate_threat_level(self, structure: Dict) -> float:
        """计算威胁等级（YF新增）"""
        # TODO: 实现威胁等级计算
        return 0.0

