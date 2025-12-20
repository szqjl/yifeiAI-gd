# -*- coding: utf-8 -*-
"""
閻楀苯鐎锋径鍕鎮婇崳銊δ侀崸 (Card Type Handlers)
閸旂喕鍏橀敍
- 娑撹桨绗夐崥宀澧濋崹瀣褰佹笟娑楃瑩闂傘劎娈戞径鍕鎮婇柅鏄忕帆
- 娴ｈ法鏁ゅ搞儱宸跺Ο鈥崇础閸掓稑缂撴径鍕鎮婇崳
"""

from typing import Dict, List, Optional, Any
import sys
from pathlib import Path

# 濞ｈ插瀞rc閻╄ぐ鏇炲煂鐠哄
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from game_logic.enhanced_state import EnhancedGameStateManager
from game_logic.hand_combiner import HandCombiner


class CardTypeHandler:
    """閻楀苯鐎锋径鍕鎮婇崳銊ョ唨缁"""
    
    def __init__(self, state_manager: EnhancedGameStateManager, combiner: HandCombiner):
        self.state = state_manager
        self.combiner = combiner
    
    def handle_passive(self, action_list: List[List], target_action: List, 
                      handcards: List[str], rank: str) -> int:
        """
        婢跺嫮鎮婄悮閸斻劌鍤閻楀矉绱欓棁鐟曚礁甯囬崚璁圭礆
        
        Args:
            action_list: 閸欓柅澶婂З娴ｆ粌鍨鐞
            target_action: 閻╅弽鍥уЗ娴ｆ粣绱欓棁鐟曚礁甯囬崚鍓佹畱閸斻劋缍旈敍
            handcards: 閹靛澧
            rank: 瑜版挸澧犵粵澶岄獓
        
        Returns:
            闁澶嬪ㄩ惃鍕濮╂担婊呭偍瀵鏇绱濇俊鍌涚亯閺冪姵纭堕崢瀣鍩楁潻鏂挎礀-1
        """
        # 姒涙裤倕鐤勯悳甯绱扮电粯澹橀崣娴犮儱甯囬崚鍓佹畱閸斻劋缍
        target_value = self._get_action_value(target_action)
        
        for idx, action in enumerate(action_list[1:], 1):  # 鐠哄疇绻働ASS
            if action[0] == "PASS":
                continue
            action_value = self._get_action_value(action)
            if action_value > target_value:
                return idx
        
        return -1
    
    def _get_action_value(self, action: List) -> float:
        """閼惧嘲褰囬崝銊ょ稊娴犲嘲"""
        if not action or action[0] == "PASS":
            return 0.0
        
        # 缁犻崠鏍娈戞禒宄拌壈锛勭暬
        type_values = {
            "Bomb": 20.0,
            "StraightFlush": 18.0,
            "TwoTrips": 15.0,
            "ThreePair": 12.0,
            "Straight": 10.0,
            "ThreeWithTwo": 8.0,
            "Trips": 6.0,
            "Pair": 4.0,
            "Single": 2.0
        }
        
        return type_values.get(action[0], 1.0)


class SingleHandler(CardTypeHandler):
    """閸楁洖绱舵径鍕鎮婇崳"""
    pass


class PairHandler(CardTypeHandler):
    """鐎电懓鐡欐径鍕鎮婇崳"""
    pass


class TripsHandler(CardTypeHandler):
    """娑撳婄炊婢跺嫮鎮婇崳"""
    pass


class CardTypeHandlerFactory:
    """閻楀苯鐎锋径鍕鎮婇崳銊ヤ紣閸"""
    
    _handlers = {
        "Single": SingleHandler,
        "Pair": PairHandler,
        "Trips": TripsHandler,
        "ThreePair": CardTypeHandler,
        "ThreeWithTwo": CardTypeHandler,
        "TwoTrips": CardTypeHandler,
        "Straight": CardTypeHandler,
        "StraightFlush": CardTypeHandler,
        "Bomb": CardTypeHandler
    }
    
    @staticmethod
    def get_handler(card_type: str, 
                   state_manager: EnhancedGameStateManager,
                   combiner: HandCombiner) -> Optional[CardTypeHandler]:
        """
        閼惧嘲褰囬悧灞界锋径鍕鎮婇崳
        
        Args:
            card_type: 閻楀苯鐎烽敍灞 "Single", "Pair" 缁
            state_manager: 閻樿埖浣猴紕鎮婇崳
            combiner: 閹靛澧濈紒鍕鎮庨崳
        
        Returns:
            婢跺嫮鎮婇崳銊ョ杽娓氬剁礉婵″倹鐏夋稉宥呯摠閸︺劌鍨鏉╂柨娲朜one
        """
        handler_class = CardTypeHandlerFactory._handlers.get(card_type)
        if handler_class:
            return handler_class(state_manager, combiner)
        return None

