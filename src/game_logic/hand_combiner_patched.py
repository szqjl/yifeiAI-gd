# -*- coding: utf-8 -*-
"""
手牌组合器 (Hand Combiner)
功能说明：
- 将玩家手牌按照单张、对子、三条、炸弹等进行分类
- 根据牌面值和rank检测顺子
"""

from typing import Dict, List, Tuple, Optional


class HandCombiner:
    """手牌组合器类"""
    
    def __init__(self):
        """初始化手牌组合器"""
        pass
    


def combine_handcards(self, handcards, rank, card_val):
        cards = {}
        cards["Single"] = []
        cards["Pair"] = []
        cards["Trips"] = []
        cards["Bomb"] = []
        bomb_info = {}
        
        handcards = sorted(handcards, key=lambda item: card_val[item[1]])
        start = 0
        for i in range(1, len(handcards) + 1):
            if i == len(handcards) or handcards[i][-1] != handcards[i - 1][-1]:
                if (i - start == 1):
                    cards["Single"].append(handcards[i - 1])
                elif (i - start == 2):
                    cards["Pair"].append(handcards[start:i])
                elif (i - start) == 3:
                    cards["Trips"].append(handcards[start:i])
                else:
                    cards["Bomb"].append(handcards[start:i])
                    bomb_info[handcards[start][-1]] = i - start
                start = i

        return cards, bomb_info
_get_card_value(self, card: str, card_val: Dict[str, int]) -> int:
        """
        Get the value of a card.
        
        Args:
            card: Card string like 'S2', 'HA'
            card_val: Dictionary mapping card ranks to values
            
        Returns:
            Card value integer
        """
        if len(card) < 2:
            return 0
        
        card_value = card[1] if len(card) > 1 else card[0]
        return card_val.get(card_value, 0)
    
    def get_combinations(self, handcards: List[str], rank: str, card_val: Dict[str, int]) -> Dict:
        """
        Get all possible combinations from handcards.
        
        Args:
            handcards: List of card strings
            rank: Rank card to consider
            card_val: Dictionary mapping card ranks to values
            
        Returns:
            Dictionary with sorted cards and bomb info
        """
        sorted_cards, bomb_info = self.combine_handcards(handcards, rank, card_val)
        return {
            "sorted": sorted_cards,
            "bombs": bomb_info
        }