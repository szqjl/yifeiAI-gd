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
        
        # 添加logger
        import logging
        self.logger = logging.getLogger("CooperationStrategy")
        
        # 闁板秶鐤嗛崣鍌涙殶
        self.support_threshold = 15  # 闂冪喎寮搁悧灞界烽崐濂告囬崐纭风礄婢堆傜艾濮濄倕鐓庣安鐠嘝ASS闁板秴鎮庨敍
        self.danger_threshold = 4    # 鐎佃勫滈崜鈺缍戦悧灞炬殶閸楅亶娅撻梼鍫濈》绱欑亸蹇庣艾濮濄倕鐓庣安鐠囥儵鍘ら崥鍫绱
        self.max_val_threshold = 14  # 閺堟径褏澧濋崐濂告囬崐
    
    def get_cooperation_strategy(self, action_list: List[List], 
                                cur_action: Optional[List],
                                greater_action: Optional[List],
                                game_stage: str = "early",
                                teammate_passed: bool = False,
                                my_rest_cards: int = 27,
                                teammate_rest_cards: int = 27,
                                opponent_rest_cards: int = 27) -> Dict[str, Any]:
        """
        閼惧嘲褰囬柊宥呮値缁涙牜鏆
        
        配合策略原则：
        1、上家出单，我牌力足够，跟自己天然单
        2、牌力不够，直接上大单压制。如果获得出牌权，改出其他牌型
        3、中后期，如果没有能压制对方的单了，我方的任何一方都要直接炸
        4、防守责任原则：对手下家的防守责任一般由上家负责，尤其是在开局和中期
        
        Args:
            action_list: 閸欓柅澶婂З娴ｆ粌鍨鐞
            cur_action: 瑜版挸澧犻崝銊ょ稊
            greater_action: 閺堟径褍濮╂担
            game_stage: 游戏阶段 (early, mid, late, endgame)
            teammate_passed: 队友是否刚刚pass
            my_rest_cards: 我方剩余牌数
            teammate_rest_cards: 队友剩余牌数
            opponent_rest_cards: 对手剩余牌数
        
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
        
        # 检查当前玩家是否是防守责任人
        is_defender = self.state.is_responsible_defender()
        
        # 核心逻辑：如果队友刚刚pass，我方必须积极应对
        if teammate_passed:
            # 队友pass意味着他没有合适的牌，我方必须承担起压制责任
            self.logger.debug("队友刚刚pass，我方必须积极应对")
            # 优先找能压制的牌，而不是只有炸弹
            take_over_action = self._find_best_takeover_action(action_list, cur_action)
            if take_over_action is not None:
                result["should_take_over"] = True
                result["best_action_index"] = take_over_action
                return result
            
            # 找炸弹作为最后手段
            bomb_action = self._find_bomb_action(action_list)
            if bomb_action is not None:
                # 任何阶段，队友pass后都可以炸
                result["should_take_over"] = True
                result["best_action_index"] = bomb_action
                return result
            
            # 最后，如果没有任何牌能压制，只能pass
            result["should_pass"] = True
            return result
        
        # 防守责任判断：如果不是防守责任人，优先pass
        if not is_defender and game_stage in ["early", "mid"]:
            # 不是防守责任人，且在开局或中期，应该pass让队友处理
            self.logger.debug("不是防守责任人，优先pass让队友处理")
            result["should_pass"] = True
            return result
        
        # 初期跟牌逻辑：如果是初期且对手出单，应该积极跟牌
        if game_stage == "early" or game_stage == "opening":
            # 初期对手出单，优先跟天然小单
            if cur_action and cur_action[0] == "Single":
                # 查找能压制的单牌动作
                take_over_action = self._find_best_takeover_action(action_list, cur_action)
                if take_over_action is not None:
                    # 计算动作价值差异
                    action_value = self._calculate_action_value(action_list[take_over_action])
                    cur_value = self._calculate_action_value(cur_action)
                    
                    # 价值差异不大时，积极跟牌
                    if action_value - cur_value < 8:
                        result["should_take_over"] = True
                        result["best_action_index"] = take_over_action
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
        
        # 中后期策略：如果对手出单，我方必须压制
        if game_stage in ["late", "endgame"]:
            # 中后期，对手出单必须压制
            take_over_action = self._find_best_takeover_action(action_list, cur_action)
            if take_over_action is not None:
                result["should_take_over"] = True
                result["best_action_index"] = take_over_action
            else:
                # 没有能压制的单，找炸弹
                bomb_action = self._find_bomb_action(action_list)
                if bomb_action is not None:
                    result["should_take_over"] = True
                    result["best_action_index"] = bomb_action
        
        return result
        
    def _find_bomb_action(self, action_list: List[List]) -> Optional[int]:
        """
        查找炸弹动作
        
        Args:
            action_list: 动作列表
        
        Returns:
            炸弹动作索引，无则返回None
        """
        for idx, action in enumerate(action_list):
            if action[0] == "Bomb":
                return idx
        return None
    
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
        rank = action[1] if len(action) > 1 else ""
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
            "Single": 4.0  # 提高单牌基础价值
        }
        
        base_value = type_values.get(card_type, 1.0)
        
        # 閺嶈勫祦閻楀瞼娈戦弫浼村櫤鐠嬪啯鏆ｉ敍鍫㈠濈搾濠傛矮鐜閸婅壈绉烘傛﹫绱
        card_count = len(cards) if isinstance(cards, list) else 1
        count_bonus = card_count * 0.5
        
        # 单牌额外添加点数价值
        if card_type == "Single":
            # 计算单牌点数价值（3-A，2，王）
            rank_values = {
                "3": 1.0,
                "4": 1.5,
                "5": 2.0,
                "6": 2.5,
                "7": 3.0,
                "8": 3.5,
                "9": 4.0,
                "10": 4.5,
                "J": 5.0,
                "Q": 5.5,
                "K": 6.0,
                "A": 6.5,
                "2": 7.0,
                "B": 8.0,  # 小王
                "R": 9.0   # 大王
            }
            rank_bonus = rank_values.get(rank, 1.0)
            return base_value + count_bonus + rank_bonus
        
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

