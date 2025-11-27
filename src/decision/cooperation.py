# -*- coding: utf-8 -*-
"""
闁板秴鎮庣粵鏍鏆愬Ο鈥虫健 (Cooperation Strategy)
閸旂喕鍏橀敍
- 鐠囧嫪鍙婇梼鐔峰几闁板秴鎮庨張杞扮窗
- 閸愬啿鐣鹃弰閸歅ASS闁板秴鎮庨梼鐔峰几
- 閸愬啿鐣鹃弰閸氾附甯撮弴鍧楁Е閸欏鍤閻
"""

from typing import Dict, List, Optional, Any
import sys
from pathlib import Path

# 濞ｈ插瀞rc閻╄ぐ鏇炲煂鐠哄
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from game_logic.enhanced_state import EnhancedGameStateManager


class CooperationStrategy:
    """闁板秴鎮庣粵鏍鏆愮猾"""
    
    def __init__(self, state_manager: EnhancedGameStateManager):
        """
        閸掓繂瀣瀵查柊宥呮値缁涙牜鏆
        
        Args:
            state_manager: 濞撳憡鍨欓悩鑸典胶锛勬倞閸
        """
        self.state = state_manager
        
        # 闁板秶鐤嗛崣鍌涙殶
        self.support_threshold = 15  # 闂冪喎寮搁悧灞界烽崐濂告囬崐纭风礄婢堆傜艾濮濄倕鐓庣安鐠嘝ASS闁板秴鎮庨敍
        self.danger_threshold = 4    # 鐎佃勫滈崜鈺缍戦悧灞炬殶閸楅亶娅撻梼鍫濈》绱欑亸蹇庣艾濮濄倕鐓庣安鐠囥儵鍘ら崥鍫绱
        self.max_val_threshold = 14  # 閺堟径褏澧濋崐濂告囬崐
    
    def get_cooperation_strategy(self, action_list: List[List], 
                                cur_action: Optional[List],
                                greater_action: Optional[List]) -> Dict[str, Any]:
        """
        閼惧嘲褰囬柊宥呮値缁涙牜鏆
        
        Args:
            action_list: 閸欓柅澶婂З娴ｆ粌鍨鐞
            cur_action: 瑜版挸澧犻崝銊ょ稊
            greater_action: 閺堟径褍濮╂担
        
        Returns:
            閸栧懎鎯堥柊宥呮値缁涙牜鏆愰惃鍕鐡ч崗:
            - should_pass: 閺勯崥锕绨茬拠PASS闁板秴鎮
            - should_take_over: 閺勯崥锕绨茬拠銉﹀复閺囧潡妲﹂崣
            - best_action_index: 閺堟担鍐插З娴ｆ粎鍌ㄥ
        """
        result = {
            "should_pass": False,
            "should_take_over": False,
            "best_action_index": None
        }
        
        # 婵″倹鐏夊▽鈩冩箒瑜版挸澧犻崝銊ょ稊閿涘奔绗夐棁鐟曚線鍘ら崥
        if not cur_action or cur_action[0] == "PASS":
            return result
        
        # 閸掋倖鏌囪ぐ鎾冲犻崝銊ょ稊閺勯崥锔芥Ц闂冪喎寮搁崙铏规畱
        # 鏉╂瑩鍣风粻閸栨牕鍕鎮婇敍灞界杽闂勫懎绨茬拠銉︾壌閹圭晣tate_manager閸掋倖鏌
        # 閸嬪洩绶俽eater_action閺勯梼鐔峰几閻ㄥ嫬濮╂担
        if greater_action and greater_action[0] != "PASS":
            # 鐠囧嫪鍙婇梼鐔峰几閸斻劋缍旈惃鍕鐜閸
            teammate_value = self._calculate_action_value(greater_action)
            
            # 婵″倹鐏夐梼鐔峰几閸斻劋缍旀禒宄板ジ鐝閿涘苯绨茬拠PASS闁板秴鎮
            if teammate_value >= self.support_threshold:
                result["should_pass"] = True
                return result
            
            # 婵″倹鐏夐梼鐔峰几閸斻劋缍旀禒宄伴棿鑵戠粵澶涚礉鐠囧嫪鍙婇弰閸氾箓娓剁憰浣瑰复閺
            if teammate_value >= 8:
                # 鐎电粯澹橀崣娴犮儲甯撮弴璺ㄦ畱閸斻劋缍
                best_idx = self._find_best_takeover_action(action_list, greater_action)
                if best_idx is not None:
                    result["should_take_over"] = True
                    result["best_action_index"] = best_idx
                    return result
        
        return result
    
    def _calculate_action_value(self, action: List) -> float:
        """
        鐠侊紕鐣婚崝銊ょ稊閻ㄥ嫪鐜閸
        
        Args:
            action: 閸斻劋缍旈敍灞剧壐瀵 [card_type, rank, cards]
        
        Returns:
            閸斻劋缍旀禒宄扮》绱欓弫鏉胯壈绉烘径褌鐜閸婅壈绉烘傛﹫绱
        """
        if not action or action[0] == "PASS":
            return 0.0
        
        card_type = action[0]
        cards = action[2] if len(action) > 2 else []
        
        # 閺嶈勫祦閻楀苯鐎风拋锛勭暬閸╄櫣娴犲嘲
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
        
        base_value = type_values.get(card_type, 1.0)
        
        # 閺嶈勫祦閻楀瞼娈戦弫浼村櫤鐠嬪啯鏆ｉ敍鍫㈠濈搾濠傛矮鐜閸婅壈绉烘傛﹫绱
        card_count = len(cards) if isinstance(cards, list) else 1
        count_bonus = card_count * 0.5
        
        return base_value + count_bonus
    
    def _find_best_takeover_action(self, action_list: List[List], 
                                   target_action: List) -> Optional[int]:
        """
        鐎电粯澹橀張娴ｈ櫕甯撮弴鍨濮╂担
        
        Args:
            action_list: 閸欓柅澶婂З娴ｆ粌鍨鐞
            target_action: 閻╅弽鍥уЗ娴ｆ粣绱欓梼鐔峰几閻ㄥ嫬濮╂担婊愮礆
        
        Returns:
            閺堟担鍐插З娴ｆ粎鍌ㄥ鏇绱濇俊鍌涚亯濞屸剝婀侀崚娆掔箲閸ユ慷one
        """
        if not action_list or not target_action:
            return None
        
        target_value = self._calculate_action_value(target_action)
        best_idx = None
        best_value = 0.0
        
        # 鐠哄疇绻働ASS閿涘牏鍌ㄥ0閿
        for idx in range(1, len(action_list)):
            action = action_list[idx]
            if action[0] == "PASS":
                continue
            
            action_value = self._calculate_action_value(action)
            
            # 鐎电粯澹樻禒宄板ジ鐝娴滃海娲伴弽鍥︾瑬鐏忚棄褰查懗钘夌毈閻ㄥ嫬濮╂担
            if action_value > target_value:
                if best_idx is None or action_value < best_value:
                    best_idx = idx
                    best_value = action_value
        
        return best_idx
    
    def should_support_teammate(self, teammate_action_value: float) -> bool:
        """
        閸掋倖鏌囬弰閸氾箑绨茬拠銉︽暜閹镐線妲﹂崣
        
        Args:
            teammate_action_value: 闂冪喎寮搁崝銊ょ稊娴犲嘲
        
        Returns:
            閺勯崥锕绨茬拠銉︽暜閹
        """
        return teammate_action_value >= self.support_threshold
    
    def should_take_over(self, teammate_value: float, my_value: float) -> bool:
        """
        閸掋倖鏌囬弰閸氾箑绨茬拠銉﹀复閺囧潡妲﹂崣
        
        Args:
            teammate_value: 闂冪喎寮搁崝銊ょ稊娴犲嘲
            my_value: 閹存垹娈戦崝銊ょ稊娴犲嘲
        
        Returns:
            閺勯崥锕绨茬拠銉﹀复閺
        """
        # 婵″倹鐏夐梼鐔峰几娴犲嘲闂磋厬缁涘涚礉娑撴梹鍨滈惃鍕鐜閸婂吋娲挎傛﹫绱濋崣娴犮儲甯撮弴
        if 8 <= teammate_value < self.support_threshold:
            return my_value > teammate_value
        return False
    
    def evaluate_cooperation_opportunity(self, action_list: List[List], 
                                        cur_action: Optional[List]) -> Dict[str, Any]:
        """
        鐠囧嫪鍙婇柊宥呮値閺堣桨绱
        
        Args:
            action_list: 閸欓柅澶婂З娴ｆ粌鍨鐞
            cur_action: 瑜版挸澧犻崝銊ょ稊
        
        Returns:
            闁板秴鎮庨張杞扮窗鐠囧嫪鍙婄紒鎾寸亯
        """
        if not cur_action or cur_action[0] == "PASS":
            return {"has_opportunity": False}
        
        cur_value = self._calculate_action_value(cur_action)
        
        # 鐠囧嫪鍙婇弰閸氾附婀侀弴鏉戙偨閻ㄥ嫰鍘ら崥鍫濆З娴
        better_actions = []
        for idx, action in enumerate(action_list[1:], 1):  # 鐠哄疇绻働ASS
            if action[0] == "PASS":
                continue
            action_value = self._calculate_action_value(action)
            if action_value > cur_value:
                better_actions.append((idx, action_value))
        
        return {
            "has_opportunity": len(better_actions) > 0,
            "current_value": cur_value,
            "better_actions": better_actions
        }

