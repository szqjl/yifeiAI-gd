# -*- coding: utf-8 -*-
"""
閸愬磭鐡ュ鏇熸惛濡鈥虫健 (Decision Engine)
閸旂喕鍏橀敍
- 娑撹插З/鐞氶崝銊ュ枀缁涙牕鍨庣粋
- 鐠嬪啰鏁ら柊宥呮値缁涙牜鏆
- 缂佺厧鎮庣拠鍕鍙婇崪灞藉枀缁
- 闂嗗棙鍨氶悧灞界锋稉鎾绘，婢跺嫮鎮
- 闂嗗棙鍨氭径姘娲滅槐鐘虹槑娴
- 闂嗗棙鍨氶弮鍫曟？閹貉冨煑
"""

import random
import sys
from typing import Dict, List, Optional
from pathlib import Path

# 濞ｈ插瀞rc閻╄ぐ鏇炲煂鐠哄板嫸绱欐俊鍌涚亯鏉╂ɑ鐥呴張澶涚礆
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from game_logic.enhanced_state import EnhancedGameStateManager
from game_logic.hand_combiner import HandCombiner
from decision.cooperation import CooperationStrategy
from decision.card_type_handlers import CardTypeHandlerFactory
from decision.multi_factor_evaluator import MultiFactorEvaluator
from decision.decision_timer import DecisionTimer


class DecisionEngine:
    """閸愬磭鐡ュ鏇熸惛閿涘牅瀵岄崝/鐞氶崝銊ュ瀻缁備紮绱"""
    
    def __init__(self, state_manager: EnhancedGameStateManager, max_decision_time: float = 0.8):
        self.state = state_manager
        self.combiner = HandCombiner()
        self.cooperation = CooperationStrategy(state_manager)
        self.evaluator = MultiFactorEvaluator(state_manager, self.combiner, self.cooperation)
        self.timer = DecisionTimer(max_decision_time)
    
    def decide(self, message: Dict) -> int:
        """
        娑撹插枀缁涙牕鍤遍弫甯绱欑敮锔芥傞梻瀛樺付閸掕圭礆
        
        Args:
            message: 楠炲啿褰撮崣鎴︿胶娈慳ct濞戝牊浼
        
        Returns:
            闁澶嬪ㄩ惃鍕濮╂担婊呭偍瀵
        """
        # 瀵婵瀣鈩冩
        self.timer.start()
        
        action_list = message.get("actionList", [])
        if not action_list:
            return 0
        
        # 婵″倹鐏夐崣閺堝夌存稉閸斻劋缍旈敍宀娲块幒銉ㄧ箲閸
        if len(action_list) == 1:
            return 0
        
        # 閺嶈勫祦濞撳憡鍨欓梼鑸电敻澶嬪ㄩ崘宕囩摜閺傜懓绱
        stage = message.get("stage", "play")
        
        try:
            if stage == "play":
                if self.state.is_passive_play():
                    # 鐞氶崝銊ュ毉閻楀矉绱欓棁鐟曚礁甯囬崚璁圭礆
                    return self.passive_decision(message, action_list)
                else:
                    # 娑撹插З閸戣櫣澧濋敍鍫㈠芳閸忓牆鍤閻楀本鍨ㄩ幒銉╁函绱
                    return self.active_decision(message, action_list)
            elif stage == "tribute":
                return self.tribute_decision(message, action_list)
            elif stage == "back":
                return self.back_decision(message, action_list)
            else:
                # 閸忔湹绮閹鍛鍠岄梾蹇旀簚闁澶嬪
                index_range = message.get("indexRange", len(action_list) - 1)
                return random.randint(0, index_range)
        finally:
            # 鐠佹澘缍嶉崘宕囩摜閺冨爼妫
            elapsed = self.timer.get_elapsed_time()
            if elapsed > self.timer.max_time * 0.8:
                print(f"Warning: Decision took {elapsed:.3f}s (閹恒儴绻庣搾鍛妞 {self.timer.max_time}s")
    
    def active_decision(self, message: Dict, action_list: List[List]) -> int:
        """
        娑撹插З閸戣櫣澧濋崘宕囩摜閿涘牏宸奸崗鍫濆毉閻楀本鍨ㄩ幒銉╁函绱
        
        Args:
            message: 楠炲啿褰村☉鍫熶紖
            action_list: 閸欓柅澶婂З娴ｆ粌鍨鐞
        
        Returns:
            闁澶嬪ㄩ惃鍕濮╂担婊呭偍瀵
        """
        handcards = message.get("handCards", [])
        rank = message.get("curRank", "2")
        
        # 娴ｈ法鏁ゆ径姘娲滅槐鐘虹槑娴兼壆閮寸紒
        evaluations = self.evaluator.evaluate_all_actions(action_list, None)
        
        # 濡閺屻儲妞傞梻杈剧礉婵″倹鐏夐弮鍫曟？娑撳秴鐕傜礉閻╁瓨甯存潻鏂挎礀閺堟担鍐插З娴
        if self.timer.check_timeout():
            if evaluations:
                return evaluations[0][0]
            return 0
        
        # 娴兼ê鍘涢柅澶嬪ㄧ拠鍕鍨庢傛兼畱閸斻劋缍
        for idx, score in evaluations:
            action = action_list[idx]
            if action[0] != "PASS":
                # 濡閺屻儲妞傞梻
                if self.timer.check_timeout():
                    return idx
                return idx
        
        return 0
    
    def passive_decision(self, message: Dict, action_list: List[List]) -> int:
        """
        鐞氶崝銊ュ毉閻楀苯鍠呯粵鏍电礄闂囩憰浣稿竾閸掕圭礆
        
        Args:
            message: 楠炲啿褰村☉鍫熶紖
            action_list: 閸欓柅澶婂З娴ｆ粌鍨鐞
        
        Returns:
            闁澶嬪ㄩ惃鍕濮╂担婊呭偍瀵
        """
        cur_action = message.get("curAction")
        greater_action = message.get("greaterAction")
        handcards = message.get("handCards", [])
        rank = message.get("curRank", "2")
        
        target_action = greater_action if greater_action else cur_action
        
        # 1. 鐠囧嫪鍙婇柊宥呮値閺堣桨绱
        cooperation_result = self.cooperation.get_cooperation_strategy(
            action_list, cur_action, greater_action
        )
        
        # 2. 婵″倹鐏夋惔鏃囥儵鍘ら崥鍫ユЕ閸欏剁礉鏉╂柨娲朠ASS
        if cooperation_result.get("should_pass"):
            return 0
        
        # 3. 婵″倹鐏夐棁鐟曚焦甯撮弴鍧楁Е閸欏剁礉闁澶嬪ㄩ張娴ｅ啿濮╂担
        if cooperation_result.get("should_take_over"):
            best_index = cooperation_result.get("best_action_index")
            if best_index is not None:
                return best_index
        
        # 4. 娴ｈ法鏁ら悧灞界锋稉鎾绘，婢跺嫮鎮婇崳
        if target_action and target_action[0] != "PASS":
            card_type = target_action[0]
            handler = CardTypeHandlerFactory.get_handler(
                card_type, self.state, self.combiner
            )
            
            if handler:
                # 濡閺屻儲妞傞梻
                if self.timer.check_timeout():
                    # 鐡掑懏妞傞敍灞煎▏閻銊ユ彥闁鐔峰枀缁
                    return self._quick_decision(action_list, target_action)
                
                result = handler.handle_passive(
                    action_list, target_action, handcards, rank
                )
                
                if result != -1:
                    return result
        
        # 5. 娴ｈ法鏁ゆ径姘娲滅槐鐘虹槑娴兼壆閮寸紒鐔剁稊娑撳搫鍥
        if not self.timer.check_timeout():
            evaluations = self.evaluator.evaluate_all_actions(action_list, target_action)
            for idx, score in evaluations:
                if action_list[idx][0] != "PASS":
                    return idx
        
        # 6. 婵″倹鐏夐弮鐘崇《閸樺鍩楅幋鏍绉撮弮璁圭礉鏉╂柨娲朠ASS
        return 0
    
    def _quick_decision(self, action_list: List[List], target_action: List) -> int:
        """
        韫囬柅鐔峰枀缁涙牭绱欑搾鍛妞傞弮鍓佹畱婢跺洭澶嬫煙濡楀牞绱
        
        Args:
            action_list: 閸欓柅澶婂З娴ｆ粌鍨鐞
            target_action: 閻╅弽鍥уЗ娴
        
        Returns:
            閸斻劋缍旂槐銏犵穿
        """
        if not target_action or target_action[0] == "PASS":
            # 娑撹插З閸戣櫣澧濋敍宀勫嬪ㄧ粭娑撴稉闂堟扛ASS閸斻劋缍
            for i, action in enumerate(action_list[1:], 1):
                if action[0] != "PASS":
                    return i
            return 0
        
        # 鐞氶崝銊ュ毉閻楀矉绱濊箛闁鐔风粯澹橀崣娴犮儱甯囬崚鍓佹畱閸斻劋缍
        target_value = self.cooperation._calculate_action_value(target_action)
        for i, action in enumerate(action_list[1:], 1):
            if action[0] == "PASS":
                continue
            action_value = self.cooperation._calculate_action_value(action)
            if action_value > target_value:
                return i
        
        return 0
    
    def tribute_decision(self, message: Dict, action_list: List[List]) -> int:
        """
        鏉╂稖纭閸愬磭鐡
        
        Args:
            message: 楠炲啿褰村☉鍫熶紖
            action_list: 閸欓柅澶婂З娴ｆ粌鍨鐞
        
        Returns:
            闁澶嬪ㄩ惃鍕濮╂担婊呭偍瀵
        """
        # 缁涙牜鏆愰敍姘朵缉閸忓秷绻樼拹鈥插瘜閻
        cur_rank = message.get("curRank", "2")
        rank_card = f"H{cur_rank}"  # 娑撹崵澧濋柅姘鐖堕弰缁俱垺
        
        # 濡閺屻儳娑撴稉閸斻劋缍旈弰閸氾箑瀵橀崥娑撹崵澧
        if len(action_list) > 0:
            first_action = action_list[0]
            if isinstance(first_action, list) and len(first_action) > 2:
                if rank_card in first_action[2]:
                    # 婵″倹鐏夐張澶屾禍灞奸嚋閸斻劋缍旈敍宀勫嬪ㄧ粭娴滃奔閲
                    if len(action_list) > 1:
                        return 1
        
        return 0
    
    def back_decision(self, message: Dict, action_list: List[List]) -> int:
        """
        鏉╂跨閸愬磭鐡
        
        Args:
            message: 楠炲啿褰村☉鍫熶紖
            action_list: 閸欓柅澶婂З娴ｆ粌鍨鐞
        
        Returns:
            闁澶嬪ㄩ惃鍕濮╂担婊呭偍瀵
        """
        # 缁涙牜鏆愰敍姘崇箷鐠愨崇毈閻
        # TODO: 鐎圭偟骞囬弴瀛樻ら懗鐣屾畱鏉╂跨缁涙牜鏆
        
        # 娑撳瓨妞傜圭偟骞囬敍姘跺嬪ㄧ粭娑撴稉閸斻劋缍
        return 0

