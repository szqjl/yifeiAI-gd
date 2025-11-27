# -*- coding: utf-8 -*-
"""
闂佸綊娼у⒀勭箘缁辨帡宕熼柟鎼淬劌闂闁靛á缈犵窔瀹 (Hand Combiner)
闂佸憡姊婚崰鏇㈠礂濮楅弫
- 闁诲繐绻愬Λ娆愭櫠濠婂牊鍋嬬圭紒瀹ュ婅Е闁搁悢椋庝海闂佸憡鑹剧氱广儱娲ゅ┑瀣鍨
- 闂佸湱绮閸旀帞娆㈤悽鍛婂亱閻忕偟鏅妞嬪孩瀚氶柛鈩冮悞濂告煕濠婂啰鐏辩紒瀹ュ婅Е闁稿┑鍡樼洴閹
"""

from typing import Dict, List, Tuple, Optional


class HandCombiner:
    """闂佸綊娼у⒀勭箘缁辨帡宕熼柟鎼淬劌闂"""
    
    def __init__(self):
        """闂佸憡甯楃换鍌滐絿鍨鐓￠獮宥囷絾鏅跺┑鍫㈢＜闁告洟骞冩惔銊ラ棷"""
        pass
    
    def combine_handcards(self, handcards: List[str], rank: str, card_val: Dict[str, int]) -> Tuple[Dict, Dict]:
        """
        缂傚倷绀佺氶柟鎼淬劌绠ラ悗锝嗘櫠濠靛洨鈻旈柛婵嗗閸婃冪磼婢跺﹦肖濠⒀勭箞瀹
        
        Args:
            handcards: 闂佸綊娼у⒀勭箞瀹曟艾螖閸曗晛鍟撮弫宥囦沪 ['S2', 'H2', 'C3', ...]
            rank: 閻熸粎澧楅幐鍛婃櫠閻樼數椹冲㈣泛鐭傞悰鎾绘煥濞戞垮 '2'
            card_val: 闂佺粯閼婚柛蹇撳悑琛奸柣蹇撶箰鐎氶柣鈯欏洤绀
        
        Returns:
            (sorted_cards, bomb_info) 闂佺跨箰閸熸壆鍒
            - sorted_cards: 闂佸湱鍨鑻濠靛鍨傞悗锝夊垂鎼达絿灏甸柤濮愬栭悾閬嶆煟濡ら惌澶屾愬┑鍥︾箚 {"Single": [...], "Pair": [...], ...{}
            - bomb_info: 闂佺粯鍔楅懗閸撱劌菐閸ワ絽澧插ù
        """
        # 闂佸憡甯楃换鍌滐絿闈涘级濞煎氬棘閹稿海缂傚倷鐒﹂幐濠氭倵
        sorted_cards = {
            "Single": [],
            "Pair": [],
            "Trips": [],
            "ThreePair": [],
            "ThreeWithTwo": [],
            "TwoTrips": [],
            "Straight": [],
            "StraightFlush": [],
            "Bomb": []
        }
        
        bomb_info = {}
        
        # 缂傚倷鑳堕崰鏇㈠焺閸愬Σ銊х磼婢跺﹦肖濠⒀勭箞閹鍐宕熼柡鍡欏枛閺
        card_count = {}
        for card in handcards:
            card_value = card[1] if len(card) > 1 else card[0]
            if card_value not in card_count:
                card_count[card_value] = []
            card_count[card_value].append(card)
        
        # 闂佸憡甯掑Λ娑氭偖闂佺粯閼婚柣
        for value, cards in card_count.items():
            count = len(cards)
            if count == 1:
                sorted_cards["Single"].extend(cards)
            elif count == 2:
                sorted_cards["Pair"].extend(cards)
            elif count == 3:
                sorted_cards["Trips"].extend(cards)
            elif count == 4:
                # 闂佸憡鐟╅幊妤呮嚍閵壪锕傛煟閹伴懗閸撱劑鏌熺涙煎ⅹ婵炲弶鎸
                sorted_cards["Bomb"].append(cards)
                bomb_info[value] = cards
        
        # 闂佸湱鍎ょ敮鎺旇姳闂佸憡鑹剧氱广儱娲ゅ┑瀣鍨
        for card_type in sorted_cards:
            if sorted_cards[card_type]:
                sorted_cards[card_type].sort(key=lambda x: self._get_card_value(x, card_val))
        
        return sorted_cards, bomb_info
    
    def _get_card_value(self, card: str, card_val: Dict[str, int]) -> int:
        """
        闂佸吋鍎抽崲鑼躲亹閸ラ幃褍鐣濇繛鍫熷灴瀵闁
        
        Args:
            card: 闂佺粯閻澶屾愬┑鍥︾箚 'S2', 'HA'
            card_val: 闂佺粯閼婚柛蹇撳悑琛奸柣蹇撶箰鐎氶柣鈯欏洤绀
        
        Returns:
            闂佺粯閻鐓庘枔閹达箑鏋侀柡
        """
        if len(card) < 2:
            return 0
        
        card_value = card[1] if len(card) > 1 else card[0]
        return card_val.get(card_value, 0)
    
    def get_combinations(self, handcards: List[str], rank: str, card_val: Dict[str, int]) -> Dict:
        """
        闂佸吋鍎抽崲鑼躲亹閸ラ獮宥夋煛閸婵嗭工鐠佹煡鏌ゅ畷鍥ㄦ珪婵炲牊鍨块幃褏浠﹂悾宀勫海纾奸柛鏇㈠箖
        
        Args:
            handcards: 闂佸綊娼у⒀勭箞瀹曟艾螖閸
            rank: 閻熸粎澧楅幐鍛婃櫠閻樼數椹冲㈣泛鐭傞悰
            card_val: 闂佺粯閼婚柛蹇撳悑琛奸柣蹇撶箰鐎氶柣鈯欏洤绀
        
        Returns:
            缂傚倷绀佺氶柟鎼达絿纾奸柟鎯ч晲鍑介柣搴㈢⊕闁
        """
        sorted_cards, bomb_info = self.combine_handcards(handcards, rank, card_val)
        return {
            "sorted": sorted_cards,
            "bombs": bomb_info
        }

