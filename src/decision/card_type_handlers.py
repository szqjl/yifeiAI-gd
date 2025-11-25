# -*- coding: utf-8 -*-
"""
牌型专门处理模块 (Card Type Handlers)
为每种牌型创建专门的处理类，实现针对性的决策逻辑
"""

from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
from ..game_logic.enhanced_state import EnhancedGameStateManager
from ..game_logic.hand_combiner import HandCombiner


class BaseCardTypeHandler(ABC):
    """牌型处理基类"""
    
    def __init__(self, state_manager: EnhancedGameStateManager, hand_combiner: HandCombiner):
        self.state = state_manager
        self.combiner = hand_combiner
        
        # 卡牌值映射
        self.card_value = {
            "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
            "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
            "B": 16, "R": 17
        }
    
    @abstractmethod
    def handle_passive(self, action_list: List[List], cur_action: List,
                      handcards: List[str], rank: str) -> int:
        """
        处理被动出牌（需要压制）
        
        Args:
            action_list: 可选动作列表
            cur_action: 当前需要压制的动作
            handcards: 手牌
            rank: 主牌级别
        
        Returns:
            选择的动作索引，-1表示应该PASS
        """
        pass
    
    @abstractmethod
    def handle_active(self, action_list: List[List], handcards: List[str],
                     rank: str) -> int:
        """
        处理主动出牌
        
        Args:
            action_list: 可选动作列表
            handcards: 手牌
            rank: 主牌级别
        
        Returns:
            选择的动作索引
        """
        pass
    
    def calculate_action_value(self, action: List) -> float:
        """计算动作值"""
        if action[0] == "PASS":
            return 0
        
        rank = action[1]
        base_value = self.card_value.get(rank, 0)
        
        # 根据牌型调整
        if action[0] == "Bomb":
            base_value += (len(action[2]) - 4) * 16
        elif action[0] == "StraightFlush":
            base_value += 32
        elif action[0] in ["ThreeWithTwo", "TwoTrips"]:
            base_value += 5
        elif action[0] == "ThreePair":
            base_value += 3
        
        return base_value


class SingleHandler(BaseCardTypeHandler):
    """单张处理"""
    
    def handle_passive(self, action_list: List[List], cur_action: List,
                      handcards: List[str], rank: str) -> int:
        """处理单张被动出牌"""
        # 获取手牌组合
        sorted_cards, bomb_info = self.combiner.combine_handcards(handcards, rank)
        
        # 提取单张动作
        single_actions = []
        bomb_actions = []
        for i, action in enumerate(action_list[1:], 1):
            if action[0] == 'Single':
                single_actions.append((i, action))
            elif action[0] in ['Bomb', 'StraightFlush']:
                bomb_actions.append((i, action))
        
        cur_value = self.calculate_action_value(cur_action)
        rank_card = f"H{rank}"
        
        # 获取单张成员
        single_member = sorted_cards["Single"]
        bomb_member = []
        for bomb in sorted_cards["Bomb"]:
            bomb_member.extend(bomb)
        
        straight_member = []
        if sorted_cards.get("Straight"):
            straight_member.extend(sorted_cards["Straight"][0])
        if sorted_cards.get("StraightFlush"):
            straight_member.extend(sorted_cards["StraightFlush"][0])
        
        # 获取玩家剩余牌数
        numofplayers = [
            self.state.get_player_remain_cards(0),
            self.state.get_player_remain_cards(1),
            self.state.get_player_remain_cards(2),
            self.state.get_player_remain_cards(3),
        ]
        my_pos = self.state.my_pos
        greater_pos = self.state.greater_pos
        teammate_pos = self.state.teammate_pos
        
        numofnext = numofplayers[(my_pos + 1) % 4]
        if numofnext == 0:
            numofnext = numofplayers[(my_pos - 1) % 4]
        
        # 如果是队友出的牌，考虑配合
        if greater_pos == teammate_pos:
            if cur_value >= 15:  # 队友出大牌
                return -1  # PASS
            if cur_value >= 14 and numofnext != 1:
                return -1  # PASS
        
        # 寻找可以压制的最小单张
        for idx, action in single_actions:
            action_value = self.calculate_action_value(action)
            if action_value > cur_value:
                # 优先选择单张成员，且不是主牌
                if action[2][0] in single_member and rank_card not in action[2]:
                    return idx
                # 其次选择不在炸弹中的牌，且不在顺子中
                elif (action[2][0] not in bomb_member and 
                      rank_card not in action[2] and
                      not self.combiner.is_in_straight(action, straight_member)):
                    return idx
        
        # 如果无法压制，返回PASS
        return -1
    
    def handle_active(self, action_list: List[List], handcards: List[str],
                     rank: str) -> int:
        """处理单张主动出牌"""
        sorted_cards, _ = self.combiner.combine_handcards(handcards, rank)
        single_member = sorted_cards["Single"]
        rank_card = f"H{rank}"
        
        # 优先选择单张成员中的小牌
        for i, action in enumerate(action_list[1:], 1):
            if action[0] == 'Single':
                if action[2][0] in single_member and rank_card not in action[2]:
                    return i
        
        # 如果没有合适的，选择第一个单张
        for i, action in enumerate(action_list[1:], 1):
            if action[0] == 'Single':
                return i
        
        return 0  # PASS


class PairHandler(BaseCardTypeHandler):
    """对子处理"""
    
    def handle_passive(self, action_list: List[List], cur_action: List,
                      handcards: List[str], rank: str) -> int:
        """处理对子被动出牌"""
        sorted_cards, bomb_info = self.combiner.combine_handcards(handcards, rank)
        
        pair_actions = []
        bomb_actions = []
        for i, action in enumerate(action_list[1:], 1):
            if action[0] == 'Pair':
                pair_actions.append((i, action))
            elif action[0] in ['Bomb', 'StraightFlush']:
                bomb_actions.append((i, action))
        
        cur_value = self.calculate_action_value(cur_action)
        rank_card = f"H{rank}"
        
        pair_member = []
        for pair in sorted_cards["Pair"]:
            pair_member.extend(pair)
        
        bomb_member = []
        for bomb in sorted_cards["Bomb"]:
            bomb_member.extend(bomb)
        
        straight_member = []
        if sorted_cards.get("Straight"):
            straight_member.extend(sorted_cards["Straight"][0])
        if sorted_cards.get("StraightFlush"):
            straight_member.extend(sorted_cards["StraightFlush"][0])
        
        # 如果是队友出的牌
        if self.state.greater_pos == self.state.teammate_pos:
            if cur_value >= 13:  # 队友出大对子
                return -1  # PASS
        
        # 寻找可以压制的对子
        for idx, action in pair_actions:
            action_value = self.calculate_action_value(action)
            if action_value > cur_value:
                # 优先选择对子成员
                if action[2][0] in pair_member and rank_card not in action[2]:
                    return idx
                # 其次选择不在炸弹中的牌
                elif (action[2][0] not in bomb_member and 
                      rank_card not in action[2] and
                      not self.combiner.is_in_straight(action, straight_member)):
                    return idx
        
        return -1
    
    def handle_active(self, action_list: List[List], handcards: List[str],
                     rank: str) -> int:
        """处理对子主动出牌"""
        sorted_cards, _ = self.combiner.combine_handcards(handcards, rank)
        pair_member = []
        for pair in sorted_cards["Pair"]:
            pair_member.extend(pair)
        rank_card = f"H{rank}"
        
        # 优先选择对子成员中的小对子
        for i, action in enumerate(action_list[1:], 1):
            if action[0] == 'Pair':
                if action[2][0] in pair_member and rank_card not in action[2]:
                    return i
        
        return 0


class TripsHandler(BaseCardTypeHandler):
    """三张处理"""
    
    def handle_passive(self, action_list: List[List], cur_action: List,
                      handcards: List[str], rank: str) -> int:
        """处理三张被动出牌"""
        sorted_cards, _ = self.combiner.combine_handcards(handcards, rank)
        
        trips_actions = []
        bomb_actions = []
        for i, action in enumerate(action_list[1:], 1):
            if action[0] == 'Trips':
                trips_actions.append((i, action))
            elif action[0] in ['Bomb', 'StraightFlush']:
                bomb_actions.append((i, action))
        
        cur_value = self.calculate_action_value(cur_action)
        rank_card = f"H{rank}"
        
        trip_member = []
        for trip in sorted_cards["Trips"]:
            trip_member.extend(trip)
        
        # 如果是队友出的牌
        if self.state.greater_pos == self.state.teammate_pos:
            if cur_value >= 12:  # 队友出大三张
                return -1  # PASS
        
        # 寻找可以压制的三张
        for idx, action in trips_actions:
            action_value = self.calculate_action_value(action)
            if action_value > cur_value:
                if action[2][0] in trip_member and rank_card not in action[2]:
                    return idx
        
        return -1
    
    def handle_active(self, action_list: List[List], handcards: List[str],
                     rank: str) -> int:
        """处理三张主动出牌"""
        sorted_cards, _ = self.combiner.combine_handcards(handcards, rank)
        trip_member = []
        for trip in sorted_cards["Trips"]:
            trip_member.extend(trip)
        rank_card = f"H{rank}"
        
        for i, action in enumerate(action_list[1:], 1):
            if action[0] == 'Trips':
                if action[2][0] in trip_member and rank_card not in action[2]:
                    return i
        
        return 0


class BombHandler(BaseCardTypeHandler):
    """炸弹处理"""
    
    def handle_passive(self, action_list: List[List], cur_action: List,
                      handcards: List[str], rank: str) -> int:
        """处理炸弹被动出牌"""
        sorted_cards, bomb_info = self.combiner.combine_handcards(handcards, rank)
        
        bomb_actions = []
        for i, action in enumerate(action_list[1:], 1):
            if action[0] in ['Bomb', 'StraightFlush']:
                bomb_actions.append((i, action))
        
        cur_value = self.calculate_action_value(cur_action)
        rank_card = f"H{rank}"
        
        # 获取玩家剩余牌数
        numofplayers = [
            self.state.get_player_remain_cards(0),
            self.state.get_player_remain_cards(1),
            self.state.get_player_remain_cards(2),
            self.state.get_player_remain_cards(3),
        ]
        greater_pos = self.state.greater_pos
        numofgreaterPos = numofplayers[greater_pos]
        
        pass_num, my_pass_num = self.state.get_pass_count()
        
        # 判断是否应该使用炸弹
        should_use_bomb = False
        
        # 如果对手牌很少，应该使用炸弹
        if numofgreaterPos <= 15:
            should_use_bomb = True
        
        # 如果连续PASS次数过多，应该使用炸弹
        if pass_num >= 7 or my_pass_num >= 5:
            should_use_bomb = True
        
        # 如果当前牌很大，且对手牌很多，考虑使用炸弹
        if cur_value >= 15 and numofgreaterPos >= 15:
            # 随机决定是否使用炸弹
            import random
            if random.random() > 0.5:
                should_use_bomb = True
        
        if should_use_bomb:
            # 选择最小的可以压制的炸弹
            best_idx = -1
            best_value = float('inf')
            
            for idx, action in bomb_actions:
                action_value = self.calculate_action_value(action)
                if action_value > cur_value and action_value < best_value:
                    best_value = action_value
                    best_idx = idx
            
            if best_idx != -1:
                return best_idx
        
        return -1
    
    def handle_active(self, action_list: List[List], handcards: List[str],
                     rank: str) -> int:
        """处理炸弹主动出牌（通常不主动出炸弹）"""
        return 0  # 主动出牌时通常不出炸弹


class StraightHandler(BaseCardTypeHandler):
    """顺子处理"""
    
    def handle_passive(self, action_list: List[List], cur_action: List,
                      handcards: List[str], rank: str) -> int:
        """处理顺子被动出牌"""
        straight_actions = []
        bomb_actions = []
        for i, action in enumerate(action_list[1:], 1):
            if action[0] == 'Straight':
                straight_actions.append((i, action))
            elif action[0] in ['Bomb', 'StraightFlush']:
                bomb_actions.append((i, action))
        
        cur_value = self.calculate_action_value(cur_action)
        
        # 如果是队友出的牌
        if self.state.greater_pos == self.state.teammate_pos:
            return -1  # PASS，让队友继续
        
        # 寻找可以压制的顺子
        for idx, action in straight_actions:
            action_value = self.calculate_action_value(action)
            if action_value > cur_value:
                return idx
        
        return -1
    
    def handle_active(self, action_list: List[List], handcards: List[str],
                     rank: str) -> int:
        """处理顺子主动出牌"""
        sorted_cards, _ = self.combiner.combine_handcards(handcards, rank)
        
        # 如果有顺子，优先出顺子
        if sorted_cards.get("Straight"):
            for i, action in enumerate(action_list[1:], 1):
                if action[0] == 'Straight':
                    return i
        
        return 0


class CardTypeHandlerFactory:
    """牌型处理器工厂"""
    
    @staticmethod
    def get_handler(card_type: str, state_manager: EnhancedGameStateManager,
                   hand_combiner: HandCombiner) -> Optional[BaseCardTypeHandler]:
        """
        根据牌型获取对应的处理器
        
        Args:
            card_type: 牌型名称
            state_manager: 状态管理器
            hand_combiner: 手牌组合器
        
        Returns:
            对应的处理器实例
        """
        handlers = {
            "Single": SingleHandler,
            "Pair": PairHandler,
            "Trips": TripsHandler,
            "Bomb": BombHandler,
            "Straight": StraightHandler,
        }
        
        handler_class = handlers.get(card_type)
        if handler_class:
            return handler_class(state_manager, hand_combiner)
        
        return None

