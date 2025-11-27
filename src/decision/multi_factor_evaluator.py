# -*- coding: utf-8 -*-
"""
婢舵艾娲滅槐鐘虹槑娴兼澘娅掑Ο鈥虫健 (Multi Factor Evaluator)
閸旂喕鍏橀敍
- 缂佺厧鎮庨懓鍐妾绘径姘閲滈崶鐘电岀拠鍕鍙婇崝銊ょ稊
- 閹绘劒绶电紒鐓庢値鐠囧嫬鍨
"""

from typing import Dict, List, Optional, Tuple
import sys
from pathlib import Path

# 濞ｈ插瀞rc閻╄ぐ鏇炲煂鐠哄
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from game_logic.enhanced_state import EnhancedGameStateManager
from game_logic.hand_combiner import HandCombiner
from decision.cooperation import CooperationStrategy


class MultiFactorEvaluator:
    """婢舵艾娲滅槐鐘虹槑娴兼澘娅"""
    
    def __init__(self, state_manager: EnhancedGameStateManager, 
                 combiner: HandCombiner,
                 cooperation: CooperationStrategy):
        """
        閸掓繂瀣瀵叉径姘娲滅槐鐘虹槑娴兼澘娅
        
        Args:
            state_manager: 閻樿埖浣猴紕鎮婇崳
            combiner: 閹靛澧濈紒鍕鎮庨崳
            cooperation: 闁板秴鎮庣粵鏍鏆
        """
        self.state = state_manager
        self.combiner = combiner
        self.cooperation = cooperation
        
        # 閺夊啴鍣搁柊宥囩枂
        self.weights = {
            "remaining_cards": 0.25,
            "card_type_value": 0.20,
            "cooperation": 0.20,
            "risk": 0.15,
            "timing": 0.10,
            "hand_structure": 0.10
        }
    
    def evaluate_all_actions(self, action_list: List[List], 
                            target_action: Optional[List] = None) -> List[Tuple[int, float]]:
        """
        鐠囧嫪鍙婇幍閺堝婂З娴
        
        Args:
            action_list: 閸斻劋缍旈崚妤勩
            target_action: 閻╅弽鍥уЗ娴ｆ粣绱欑悮閸斻劌鍤閻楀本妞傞棁鐟曚礁甯囬崚璁圭礆
        
        Returns:
            鐠囧嫪鍙婄紒鎾寸亯閸掓勩冮敍灞剧壐瀵蹇庤礋 [(缁便垹绱, 鐠囧嫬鍨), ...]閿涘本瀵滅拠鍕鍨庨梽宥呯碍閹烘帒鍨
        """
        evaluations = []
        
        for idx, action in enumerate(action_list):
            if action[0] == "PASS":
                score = 0.0
            else:
                score = self._evaluate_action(action, target_action)
            evaluations.append((idx, score))
        
        # 閹稿庣槑閸掑棝妾锋惔蹇斿笓鎼
        evaluations.sort(key=lambda x: x[1], reverse=True)
        return evaluations
    
    def _evaluate_action(self, action: List, target_action: Optional[List]) -> float:
        """
        鐠囧嫪鍙婇崡鏇氶嚋閸斻劋缍
        
        Args:
            action: 閸斻劋缍
            target_action: 閻╅弽鍥уЗ娴
        
        Returns:
            缂佺厧鎮庣拠鍕鍨
        """
        scores = {}
        
        # 1. 閻楀苯鐎锋禒宄
        scores["card_type_value"] = self._evaluate_card_type_value(action)
        
        # 2. 閸撯晙缍戦悧灞炬殶閸ョ姷绀
        scores["remaining_cards"] = self._evaluate_remaining_cards(action)
        
        # 3. 闁板秴鎮庨崶鐘电
        scores["cooperation"] = self._evaluate_cooperation(action, target_action)
        
        # 4. 妞嬪酣娅撻崶鐘电
        scores["risk"] = self._evaluate_risk(action)
        
        # 5. 閺冭埖婧閸ョ姷绀
        scores["timing"] = self._evaluate_timing(action, target_action)
        
        # 6. 閹靛澧濈紒鎾寸閸ョ姷绀
        scores["hand_structure"] = self._evaluate_hand_structure(action)
        
        # 缂佺厧鎮庣拠鍕鍨
        total_score = sum(scores[factor] * self.weights[factor] 
                         for factor in scores)
        
        return total_score
    
    def _evaluate_card_type_value(self, action: List) -> float:
        """鐠囧嫪鍙婇悧灞界锋禒宄"""
        if not action or action[0] == "PASS":
            return 0.0
        
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
        
        base_value = type_values.get(action[0], 1.0)
        
        # 瑜版帊绔撮崠鏍у煂0-1閼煎啫娲
        return min(base_value / 20.0, 1.0)
    
    def _evaluate_remaining_cards(self, action: List) -> float:
        """鐠囧嫪鍙婇崜鈺缍戦悧灞炬殶閸ョ姷绀"""
        # 缁犻崠鏍х杽閻滃府绱伴悧灞炬殶鐡掑﹤鐨鐡掑﹤銈
        cards = action[2] if len(action) > 2 else []
        card_count = len(cards) if isinstance(cards, list) else 1
        
        # 瑜版帊绔撮崠鏍电窗閸嬪洩鐐娓舵径27瀵鐘靛
        return 1.0 - (card_count / 27.0)
    
    def _evaluate_cooperation(self, action: List, target_action: Optional[List]) -> float:
        """鐠囧嫪鍙婇柊宥呮値閸ョ姷绀"""
        if not target_action:
            return 0.5  # 娑撹插З閸戣櫣澧濋敍宀勫帳閸氬牆娲滅槐鐘辫厬缁
        
        # 婵″倹鐏夐惄閺嶅洤濮╂担婊勬Ц闂冪喎寮搁惃鍕剁礉鐠囧嫪鍙婇柊宥呮値娴犲嘲
        action_value = self.cooperation._calculate_action_value(action)
        target_value = self.cooperation._calculate_action_value(target_action)
        
        # 婵″倹鐏夐懗钘夊竾閸掓湹绲炬稉宥堢箖鎼达讣绱濋柊宥呮値娴犲嘲濂哥彯
        if action_value > target_value:
            diff = action_value - target_value
            if diff < 5:  # 闁鍌氬抽崢瀣鍩
                return 0.8
            else:  # 鏉╁洤瀹抽崢瀣鍩
                return 0.4
        
        return 0.2  # 閺冪姵纭堕崢瀣鍩
    
    def _evaluate_risk(self, action: List) -> float:
        """鐠囧嫪鍙婃嬪酣娅撻崶鐘电"""
        # 缁犻崠鏍х杽閻滃府绱伴悙绋胯剨妞嬪酣娅撴担搴绱濈亸蹇曞濇嬪酣娅撴
        if action[0] == "Bomb":
            return 0.9  # 娴ｅ酣搴ㄦ珦
        elif action[0] in ["Single", "Pair"]:
            return 0.3  # 妤傛﹢搴ㄦ珦
        else:
            return 0.6  # 娑撶粵澶愬酣娅
    
    def _evaluate_timing(self, action: List, target_action: Optional[List]) -> float:
        """鐠囧嫪鍙婇弮鑸垫簚閸ョ姷绀"""
        # 缁犻崠鏍х杽閻
        return 0.5
    
    def _evaluate_hand_structure(self, action: List) -> float:
        """鐠囧嫪鍙婇幍瀣澧濈紒鎾寸閸ョ姷绀"""
        # 缁犻崠鏍х杽閻
        return 0.5

