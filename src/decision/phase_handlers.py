# -*- coding: utf-8 -*-
"""
阶段处理器 (Phase Handlers)
功能：
- 实现各阶段的专门处理器（开局、中局前期、中局后期、残局前期、残局后期）
- 每个阶段有主动和被动两个处理器
- 每个处理器专注于该阶段的策略优化
- M1版本：整合策略函数和知识库文档，实现完善的策略逻辑
"""

from typing import Dict, List, Optional, Tuple
import sys
from pathlib import Path

# 添加路径以导入策略函数
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from .stage_router import BasePhaseHandler
from .card_power_evaluator import calculate_card_power
from .single_card_strategy import single_card_strategy
from .pair_strategy import pair_strategy
from .endgame_strategy import endgame_strategy, check_one_hand_finish
from .cooperation import CooperationStrategy


class OpeningActiveHandler(BasePhaseHandler):
    """开局主动出牌处理器（优化：专注于建立牌型结构）"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self._init_helpers()
    
    def _init_helpers(self):
        """初始化辅助工具"""
        # 延迟导入，避免循环依赖
        try:
            from .card_power_evaluator import calculate_card_power
            from .single_card_strategy import single_card_strategy
            from .pair_strategy import pair_strategy
            self.calculate_power = calculate_card_power
            self.single_strategy = single_card_strategy
            self.pair_strategy = pair_strategy
        except ImportError:
            self.calculate_power = None
            self.single_strategy = None
            self.pair_strategy = None
    
    def handle(self, message: Dict) -> int:
        """开局策略：专注于建立牌型结构，不考虑快速出完"""
        import logging
        logger = logging.getLogger("OpeningActiveHandler")
        
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        
        if not action_list:
            logger.warning("动作列表为空，返回PASS")
            return 0
        
        # 如果只有一个动作（通常是PASS），直接返回
        if len(action_list) == 1:
            logger.warning("只有一个动作（PASS），返回0")
            return 0
        
        # 过滤掉PASS动作
        valid_actions = [(i, action) for i, action in enumerate(action_list) 
                        if len(action) > 0 and action[0] != "PASS"]
        
        if not valid_actions:
            logger.error("没有有效动作，返回PASS")
            return 0
        
        logger.info(f"开局主动出牌: 有效动作数={len(valid_actions)}, 手牌数={len(handcards)}")
        
        # 开局策略：建立牌型结构
        result = self._build_structure_strategy(message, action_list, handcards)
        
        # 如果返回0（PASS），强制选择一个有效动作（避免一直PASS）
        if result == 0:
            logger.warning(f"策略返回PASS，但存在{len(valid_actions)}个有效动作，强制选择第一个: {valid_actions[0][1][0]}")
            return valid_actions[0][0]
        
        logger.info(f"策略选择: 索引{result}, 动作类型={action_list[result][0] if result < len(action_list) else '无效'}")
        return result
    
    def _extract_game_state(self, message: Dict) -> Dict:
        """提取游戏状态信息"""
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        cur_rank = message.get("curRank", "2")
        
        # 计算剩余牌数
        my_rest = len(handcards) if handcards else 27
        # 初始化4个玩家的剩余牌数（0, 1, 2, 3号位）
        opponent_rest_cards_list = [27, 27, 27, 27]
        teammate_rest_cards = 27
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", 27)
                    opponent_rest_cards_list[i] = rest
                    # 队友位置：第1个和第3个为一队，第2个和第4个为一队
                    if (my_pos in [0, 2] and i in [0, 2]) or (my_pos in [1, 3] and i in [1, 3]):
                        teammate_rest_cards = rest
        
        # 计算牌力
        power = 5.0
        if self.calculate_power and handcards:
            power_result = self.calculate_power(handcards, game_phase='opening', opponent_rest_cards=min(opponent_rest_cards_list))
            power = power_result.get('total_power', 5.0)
        
        return {
            'my_rest': my_rest,
            'opponent_rest_cards_list': opponent_rest_cards_list,
            'teammate_rest_cards': teammate_rest_cards,
            'power': power,
            'cur_rank': cur_rank,
            'my_pos': my_pos
        }
    
    def _build_structure_strategy(self, message: Dict, action_list: List, handcards: List) -> int:
        """建立牌型结构策略（开局专用）"""
        import logging
        logger = logging.getLogger("OpeningActiveHandler")
        
        # 提取游戏状态
        state = self._extract_game_state(message)
        power = state['power']
        
        # 过滤掉PASS动作，只考虑实际出牌动作
        valid_actions = [(i, action) for i, action in enumerate(action_list) 
                        if len(action) > 0 and action[0] != "PASS"]
        
        if not valid_actions:
            # 如果没有有效动作，只能PASS
            logger.warning("没有有效动作，返回PASS")
            return 0
        
        logger.debug(f"有效动作数: {len(valid_actions)}, 牌力: {power:.2f}")
        if valid_actions:
            logger.debug(f"有效动作类型: {[a[1][0] for a in valid_actions[:5]]}")
        
        # 根据开局策略文档，优先级策略：
        # 1. 牌力强（有王/级牌）：优先出天然单张
        # 2. 牌力中下：情况不明对子先行
        # 3. 牌力弱：助攻定位，不出单，保留牌型组合
        
        # 检查是否有王或级牌
        has_king = any('R' in str(card) or 'B' in str(card) for card in handcards)
        has_level_card = any(str(state['cur_rank']) in str(card) for card in handcards)
        
        # 简化策略：不依赖策略函数的建议，直接根据牌力和牌型选择
        # 策略1：牌力强，有王/级牌，优先出天然单张
        if power >= 6 or has_king or has_level_card:
            # 直接选择最小的单张（不依赖策略函数建议）
            for i, action in valid_actions:
                if action[0] == 'Single':
                    logger.info(f"牌力强，选择单张: {action[1] if len(action) > 1 else '?'} (索引{i})")
                    return i
        
        # 策略2：牌力中下，情况不明对子先行
        if power < 6:
            # 优先选择对子
            for i, action in valid_actions:
                if action[0] == 'Pair':
                    logger.info(f"牌力中下，选择对子: {action[1] if len(action) > 1 else '?'} (索引{i})")
                    return i
        
        # 策略3：牌力弱，助攻定位，优先保留牌型组合
        if power < 5:
            # 优先出三连对/钢板（对手难管）
            priority_order = ['TwoTrips', 'ThreePair', 'Straight', 'ThreeWithTwo', 'Trips']
            for card_type in priority_order:
                for i, action in valid_actions:
                    if action[0] == card_type:
                        return i
            # 如果没有组合牌型，再考虑对子
            for i, action in valid_actions:
                if action[0] == 'Pair':
                    return i
            # 最后才考虑单张
            for i, action in valid_actions:
                if action[0] == 'Single':
                    return i
        else:
            # 牌力正常，按常规优先级：小单张 → 三连对/钢板 → 顺子 → 三带二 → 三张 → 对子
            priority_order = ['Single', 'TwoTrips', 'ThreePair', 'Straight', 
                             'ThreeWithTwo', 'Trips', 'Pair']
            for card_type in priority_order:
                for i, action in valid_actions:
                    if action[0] == card_type:
                        # 单张选择最小的
                        if card_type == 'Single':
                            return i
                        return i
        
        # 如果所有策略都不匹配，至少选择第一个非PASS动作（避免一直PASS）
        import logging
        logger = logging.getLogger("OpeningActiveHandler")
        if valid_actions:
            selected_idx = valid_actions[0][0]
            selected_action = valid_actions[0][1]
            logger.warning(f"所有策略都不匹配，选择第一个有效动作: 索引{selected_idx}, 类型{selected_action[0] if len(selected_action) > 0 else 'UNKNOWN'}")
            return selected_idx
        
        logger.error("没有找到任何有效动作，返回PASS")
        return 0


class OpeningPassiveHandler(BasePhaseHandler):
    """开局被动出牌处理器"""
    
    # 牌点大小顺序：3 < 4 < 5 < 6 < 7 < 8 < 9 < T < J < Q < K < A < 2 < B < R
    RANK_ORDER = ['3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A', '2', 'B', 'R']
    
    @classmethod
    def _compare_rank(cls, rank1: str, rank2: str) -> int:
        """比较两张牌的大小，返回-1表示rank1<rank2，0表示相等，1表示rank1>rank2"""
        try:
            idx1 = cls.RANK_ORDER.index(str(rank1)) if str(rank1) in cls.RANK_ORDER else -1
            idx2 = cls.RANK_ORDER.index(str(rank2)) if str(rank2) in cls.RANK_ORDER else -1
            if idx1 < 0 or idx2 < 0:
                return 0  # 无法比较
            if idx1 < idx2:
                return -1
            elif idx1 > idx2:
                return 1
            else:
                return 0
        except (ValueError, IndexError):
            return 0
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self._init_helpers()
    
    def _init_helpers(self):
        """初始化辅助工具"""
        try:
            from .card_power_evaluator import calculate_card_power
            from .single_card_strategy import single_card_strategy
            from .pair_strategy import pair_strategy
            from .cooperation import CooperationStrategy
            self.calculate_power = calculate_card_power
            self.single_strategy = single_card_strategy
            self.pair_strategy = pair_strategy
        except ImportError:
            self.calculate_power = None
            self.single_strategy = None
            self.pair_strategy = None
    
    def handle(self, message: Dict) -> int:
        """开局被动出牌策略：顺队友、控对手
        
        注意：
        - 队友：0和2是队友，1和3是队友（队友位置 = (my_pos + 2) % 4）
        - 上家和下家都是对手，不是队友
        - 队友出牌：让过（顺队友）
        - 对手出牌：尽量压制（控对手）
        """
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        cur_action = message.get("curAction")
        
        if not action_list:
            return 0
        
        # 如果没有当前动作，说明是主动出牌，不应该到这里
        if not cur_action:
            return 0
        
        # 提取游戏状态
        state = self._extract_game_state(message)
        cur_action_type = cur_action[0] if isinstance(cur_action, list) and len(cur_action) > 0 else ""
        greater_pos = message.get("greaterPos", -1)
        my_pos = state['my_pos']
        
        # 判断是否是队友出牌
        is_teammate = self._is_teammate(greater_pos, my_pos)
        
        # 开局被动策略：队友出牌让过，对手出牌根据位置决定
        if is_teammate:
            # 队友出牌，开局阶段让过
            return 0  # PASS
        
        # 对手出牌，根据位置决定策略
        if cur_action_type == 'Single':
            return self._handle_single_passive(message, action_list, state, greater_pos, my_pos)
        elif cur_action_type == 'Pair':
            return self._handle_pair_passive(message, action_list, state, greater_pos, my_pos)
        else:
            # 其他牌型，根据牌力决定是否压制
            return self._handle_other_passive(message, action_list, state)
    
    def _extract_game_state(self, message: Dict) -> Dict:
        """提取游戏状态信息"""
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        cur_rank = message.get("curRank", "2")
        
        my_rest = len(handcards) if handcards else 27
        # 初始化4个玩家的剩余牌数（0, 1, 2, 3号位）
        opponent_rest_cards_list = [27, 27, 27, 27]
        teammate_rest_cards = 27
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", 27)
                    # 确保索引在范围内
                    if 0 <= i < len(opponent_rest_cards_list):
                        opponent_rest_cards_list[i] = rest
                    if (my_pos in [0, 2] and i in [0, 2]) or (my_pos in [1, 3] and i in [1, 3]):
                        teammate_rest_cards = rest
        
        power = 5.0
        if self.calculate_power and handcards:
            power_result = self.calculate_power(handcards, game_phase='opening', opponent_rest_cards=min(opponent_rest_cards_list))
            power = power_result.get('total_power', 5.0)
        
        return {
            'my_rest': my_rest,
            'opponent_rest_cards_list': opponent_rest_cards_list,
            'teammate_rest_cards': teammate_rest_cards,
            'power': power,
            'cur_rank': cur_rank,
            'my_pos': my_pos
        }
    
    def _is_teammate(self, pos: int, my_pos: int) -> bool:
        """
        判断是否是队友
        
        掼蛋队友关系：
        - 0号位和2号位是一队（队友）
        - 1号位和3号位是一队（队友）
        """
        if pos == -1 or my_pos == -1:
            return False
        # 0和2是队友，1和3是队友
        is_teammate = (my_pos in [0, 2] and pos in [0, 2]) or (my_pos in [1, 3] and pos in [1, 3])
        return is_teammate
    
    def _handle_single_passive(self, message: Dict, action_list: List, state: Dict, greater_pos: int, my_pos: int) -> int:
        """处理单张被动出牌"""
        import logging
        logger = logging.getLogger("OpeningPassiveHandler")
        
        # 过滤掉PASS动作
        valid_actions = [(i, action) for i, action in enumerate(action_list) 
                        if len(action) > 0 and action[0] != "PASS"]
        
        if not valid_actions:
            logger.warning("没有有效动作，返回PASS")
            return 0
        
        cur_action = message.get("curAction", [])
        action_rank = cur_action[1] if len(cur_action) > 1 else ""
        
        # 判断出牌者是否是队友
        is_opponent_teammate = self._is_teammate(greater_pos, my_pos)
        
        # 开局被动策略：
        # - 队友出单：让过（顺队友）
        # - 对手出单：尽量压制（控对手）
        if is_opponent_teammate:
            # 队友出单，开局阶段让过
            logger.info(f"队友（位置{greater_pos}）出单，开局让过。我的位置: {my_pos}")
            return 0
        
        # 对手出单，尽量压制
        logger.info(f"对手（位置{greater_pos}）出单，我的位置: {my_pos}，尽量压制。当前牌点: {action_rank}")
        logger.info(f"有效动作数: {len(valid_actions)}, 单张动作: {[a[1][0] for a in valid_actions if a[1][0] == 'Single'][:5]}")
        
        # 选择能压制的最小单张
        for i, action in valid_actions:
            if action[0] == 'Single':
                if len(action) > 1:
                    card_rank = str(action[1])
                    logger.debug(f"检查单张: {card_rank} vs {action_rank}")
                    # 使用正确的牌点比较
                    if self._compare_rank(card_rank, str(action_rank)) > 0:
                        logger.info(f"✓ 选择压制单张: {card_rank} (索引{i})")
                        return i
        
        # 如果没有能压制的，也选择最小的单张（至少跟牌，避免一直PASS）
        for i, action in valid_actions:
            if action[0] == 'Single':
                card_rank = action[1] if len(action) > 1 else '?'
                logger.warning(f"⚠ 没有能压制的单张，但选择单张避免PASS: {card_rank} (索引{i})")
                return i
        
        # 如果连单张都没有，至少选择第一个有效动作（避免一直PASS）
        if valid_actions:
            logger.error(f"❌ 没有单张动作，强制选择第一个有效动作避免PASS: {valid_actions[0][1][0]} (索引{valid_actions[0][0]})")
            return valid_actions[0][0]
        
        logger.error("❌ 没有找到任何有效动作，返回PASS")
        return 0
    
    def _handle_pair_passive(self, message: Dict, action_list: List, state: Dict, greater_pos: int, my_pos: int) -> int:
        """处理对子被动出牌"""
        if not self.pair_strategy:
            return self._default_passive_action(action_list)
        
        cur_action = message.get("curAction", [])
        action_rank = cur_action[1] if len(cur_action) > 1 else ""
        is_teammate = self._is_teammate(greater_pos, my_pos)
        
        # 使用对子策略
        pair_sugg = self.pair_strategy(
            game_phase='opening',
            power=state['power'],
            opponent_rest_cards=min(state['opponent_rest_cards_list']),
            is_active=False,
            is_teammate_action=is_teammate,
            greater_pos=greater_pos,
            my_pos=my_pos,
            action_type='Pair',
            action_rank=action_rank
        )
        
        # 如果策略建议让对子，则PASS
        if '让对子' in pair_sugg.get('action', ''):
            return 0
        
        # 过滤掉PASS动作
        valid_actions = [(i, action) for i, action in enumerate(action_list) 
                        if len(action) > 0 and action[0] != "PASS"]
        
        if not valid_actions:
            return 0
        
        # 选择能压制的最小对子
        for i, action in valid_actions:
            if action[0] == 'Pair':
                if len(action) > 1:
                    card_rank = str(action[1])
                    if self._compare_rank(card_rank, str(action_rank)) > 0:
                        return i
        
        # 如果没有能压制的，也选择最小的对子（避免一直PASS）
        for i, action in valid_actions:
            if action[0] == 'Pair':
                return i
        
        # 如果连对子都没有，至少选择第一个有效动作（避免一直PASS）
        if valid_actions:
            return valid_actions[0][0]
        
        return 0
    
    def _handle_other_passive(self, message: Dict, action_list: List, state: Dict) -> int:
        """处理其他牌型被动出牌"""
        # 开局阶段，牌力弱时让过，牌力强时压制
        if state['power'] < 5:
            return 0  # PASS
        
        # 过滤掉PASS动作
        valid_actions = [(i, action) for i, action in enumerate(action_list) 
                        if len(action) > 0 and action[0] != "PASS"]
        
        if not valid_actions:
            return 0
        
        # 选择能压制的最小动作
        cur_action = message.get("curAction", [])
        cur_type = cur_action[0] if len(cur_action) > 0 else ""
        cur_rank = cur_action[1] if len(cur_action) > 1 else ""
        
        for i, action in valid_actions:
            if action[0] == cur_type:
                if len(action) > 1:
                    card_rank = str(action[1])
                    if self._compare_rank(card_rank, str(cur_rank)) > 0:
                        return i
        
        # 如果没有能压制的，也选择同类型的动作（避免一直PASS）
        for i, action in valid_actions:
            if action[0] == cur_type:
                return i
        
        # 如果连同类型都没有，至少选择第一个有效动作（避免一直PASS）
        if valid_actions:
            return valid_actions[0][0]
        
        return 0
    
    def _default_passive_action(self, action_list: List) -> int:
        """默认被动动作选择"""
        # 选择第一个非PASS动作
        for i, action in enumerate(action_list):
            if action[0] != "PASS":
                return i
        return 0


class MidEarlyActiveHandler(BasePhaseHandler):
    """中局前期主动出牌处理器（剩余牌数 15-20）"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self._init_helpers()
    
    def _init_helpers(self):
        """初始化辅助工具"""
        try:
            from .card_power_evaluator import calculate_card_power
            from .pair_strategy import pair_strategy
            self.calculate_power = calculate_card_power
            self.pair_strategy = pair_strategy
        except ImportError:
            self.calculate_power = None
            self.pair_strategy = None
    
    def handle(self, message: Dict) -> int:
        """中局前期策略：控制节奏，配合队友，开始考虑出完"""
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        
        if not action_list:
            return 0
        
        # 检查两手出完
        two_hand_idx = self._check_two_hand_complete(action_list, handcards)
        if two_hand_idx is not None:
            return two_hand_idx
        
        # 中局前期策略：控制节奏，配合队友
        # 优先级：对子 → 三张 → 单张 → 其他
        state = self._extract_game_state(message)
        
        # 如果牌力中下，优先出对子试探
        if state['power'] < 6 and self.pair_strategy:
            pair_sugg = self.pair_strategy(
                game_phase='mid',
                power=state['power'],
                opponent_rest_cards=min(state['opponent_rest_cards_list']),
                is_active=True,
                my_rest_cards=state['my_rest']
            )
            if '出对' in pair_sugg.get('action', ''):
                for i, action in enumerate(action_list):
                    if action[0] == 'Pair' and action[0] != "PASS":
                        return i
        
        # 常规优先级：对子 → 三张 → 单张 → 其他
        priority_order = ['Pair', 'Trips', 'Single', 'ThreeWithTwo', 
                         'ThreePair', 'TwoTrips', 'Straight']
        
        for card_type in priority_order:
            for i, action in enumerate(action_list):
                if action[0] == card_type and action[0] != "PASS":
                    return i
        
        return 0
    
    def _extract_game_state(self, message: Dict) -> Dict:
        """提取游戏状态信息"""
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        
        my_rest = len(handcards) if handcards else 27
        # 初始化4个玩家的剩余牌数（0, 1, 2, 3号位）
        opponent_rest_cards_list = [27, 27, 27, 27]
        teammate_rest_cards = 27
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", 27)
                    # 确保索引在范围内
                    if 0 <= i < len(opponent_rest_cards_list):
                        opponent_rest_cards_list[i] = rest
                    if (my_pos in [0, 2] and i in [0, 2]) or (my_pos in [1, 3] and i in [1, 3]):
                        teammate_rest_cards = rest
        
        power = 5.0
        if self.calculate_power and handcards:
            power_result = self.calculate_power(handcards, game_phase='mid', opponent_rest_cards=min(opponent_rest_cards_list))
            power = power_result.get('total_power', 5.0)
        
        return {
            'my_rest': my_rest,
            'opponent_rest_cards_list': opponent_rest_cards_list,
            'teammate_rest_cards': teammate_rest_cards,
            'power': power,
            'my_pos': my_pos
        }
    
    def _check_two_hand_complete(self, action_list: List, handcards: List) -> Optional[int]:
        """检查两手出完（M1增强：实现完整的两手出完逻辑）"""
        if not handcards or len(handcards) > 10:
            return None
        
        hand_count = len(handcards)
        
        # 尝试找到两个动作，使得它们的牌数之和等于剩余牌数
        for i, action1 in enumerate(action_list):
            if not action1 or action1[0] == "PASS":
                continue
            cards1 = action1[2] if len(action1) > 2 else []
            count1 = len(cards1) if isinstance(cards1, list) else 0
            
            if count1 == 0:
                continue
            
            # 如果第一个动作已经出完所有牌，返回它
            if count1 == hand_count:
                return i
            
            # 尝试找第二个动作
            remaining = hand_count - count1
            if remaining <= 0:
                continue
            
            for j, action2 in enumerate(action_list):
                if i == j or not action2 or action2[0] == "PASS":
                    continue
                cards2 = action2[2] if len(action2) > 2 else []
                count2 = len(cards2) if isinstance(cards2, list) else 0
                
                # 检查两个动作的牌是否不重叠
                if count2 == remaining:
                    # 简单检查：如果两个动作的牌数之和等于手牌数，且牌不重叠
                    if isinstance(cards1, list) and isinstance(cards2, list):
                        # 检查是否有重叠
                        if not set(cards1) & set(cards2):
                            # 找到两手出完的组合，返回第一个动作
                            return i
        
        return None


class MidEarlyPassiveHandler(BasePhaseHandler):
    """中局前期被动出牌处理器"""
    
    # 牌点大小顺序：3 < 4 < 5 < 6 < 7 < 8 < 9 < T < J < Q < K < A < 2 < B < R
    RANK_ORDER = ['3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A', '2', 'B', 'R']
    
    @classmethod
    def _compare_rank(cls, rank1: str, rank2: str) -> int:
        """比较两张牌的大小，返回-1表示rank1<rank2，0表示相等，1表示rank1>rank2"""
        try:
            idx1 = cls.RANK_ORDER.index(str(rank1)) if str(rank1) in cls.RANK_ORDER else -1
            idx2 = cls.RANK_ORDER.index(str(rank2)) if str(rank2) in cls.RANK_ORDER else -1
            if idx1 < 0 or idx2 < 0:
                return 0  # 无法比较
            if idx1 < idx2:
                return -1
            elif idx1 > idx2:
                return 1
            else:
                return 0
        except (ValueError, IndexError):
            return 0
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self._init_helpers()
    
    def _init_helpers(self):
        """初始化辅助工具"""
        try:
            from .card_power_evaluator import calculate_card_power
            from .single_card_strategy import single_card_strategy
            from .pair_strategy import pair_strategy
            self.calculate_power = calculate_card_power
            self.single_strategy = single_card_strategy
            self.pair_strategy = pair_strategy
        except ImportError:
            self.calculate_power = None
            self.single_strategy = None
            self.pair_strategy = None
    
    def handle(self, message: Dict) -> int:
        """中局前期被动出牌策略：配合队友，控制节奏"""
        action_list = message.get("actionList", [])
        cur_action = message.get("curAction")
        
        if not action_list or not cur_action:
            return 0
        
        state = self._extract_game_state(message)
        cur_action_type = cur_action[0] if isinstance(cur_action, list) and len(cur_action) > 0 else ""
        greater_pos = message.get("greaterPos", -1)
        my_pos = state['my_pos']
        is_teammate = self._is_teammate(greater_pos, my_pos)
        
        # 队友出牌，中局前期让过
        if is_teammate:
            return 0
        
        # 对手出牌，根据牌型处理
        if cur_action_type == 'Single':
            return self._handle_single_passive(message, action_list, state, greater_pos, my_pos)
        elif cur_action_type == 'Pair':
            return self._handle_pair_passive(message, action_list, state, greater_pos, my_pos)
        else:
            return self._handle_other_passive(message, action_list, state)
    
    def _extract_game_state(self, message: Dict) -> Dict:
        """提取游戏状态信息"""
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        
        my_rest = len(handcards) if handcards else 27
        # 初始化4个玩家的剩余牌数（0, 1, 2, 3号位）
        opponent_rest_cards_list = [27, 27, 27, 27]
        teammate_rest_cards = 27
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", 27)
                    # 确保索引在范围内
                    if 0 <= i < len(opponent_rest_cards_list):
                        opponent_rest_cards_list[i] = rest
                    if (my_pos in [0, 2] and i in [0, 2]) or (my_pos in [1, 3] and i in [1, 3]):
                        teammate_rest_cards = rest
        
        power = 5.0
        if self.calculate_power and handcards:
            power_result = self.calculate_power(handcards, game_phase='mid', opponent_rest_cards=min(opponent_rest_cards_list))
            power = power_result.get('total_power', 5.0)
        
        return {
            'my_rest': my_rest,
            'opponent_rest_cards_list': opponent_rest_cards_list,
            'teammate_rest_cards': teammate_rest_cards,
            'power': power,
            'my_pos': my_pos
        }
    
    def _is_teammate(self, pos: int, my_pos: int) -> bool:
        """判断是否是队友"""
        if pos == -1 or my_pos == -1:
            return False
        return (my_pos in [0, 2] and pos in [0, 2]) or (my_pos in [1, 3] and pos in [1, 3])
    
    def _handle_single_passive(self, message: Dict, action_list: List, state: Dict, greater_pos: int, my_pos: int) -> int:
        """处理单张被动出牌"""
        if not self.single_strategy:
            return self._default_passive_action(action_list)
        
        cur_action = message.get("curAction", [])
        action_rank = cur_action[1] if len(cur_action) > 1 else ""
        is_upper_hand = (greater_pos == (my_pos - 1) % 4) or (greater_pos == (my_pos + 3) % 4)
        
        single_sugg = self.single_strategy(
            game_phase='mid',
            power=state['power'],
            opponent_rest_cards=min(state['opponent_rest_cards_list']),
            is_active=False,
            is_upper_hand=is_upper_hand,
            my_rest_cards=state['my_rest']
        )
        
        if '不出单' in single_sugg.get('action', ''):
            return 0
        
        # 过滤掉PASS动作
        valid_actions = [(i, action) for i, action in enumerate(action_list) 
                        if len(action) > 0 and action[0] != "PASS"]
        
        if not valid_actions:
            return 0
        
        # 选择能压制的最小单张
        for i, action in valid_actions:
            if action[0] == 'Single':
                if len(action) > 1:
                    card_rank = str(action[1])
                    if self._compare_rank(card_rank, str(action_rank)) > 0:
                        return i
        
        # 如果没有能压制的，也选择最小的单张（避免一直PASS）
        for i, action in valid_actions:
            if action[0] == 'Single':
                return i
        
        # 如果连单张都没有，至少选择第一个有效动作（避免一直PASS）
        if valid_actions:
            return valid_actions[0][0]
        
        return 0
    
    def _handle_pair_passive(self, message: Dict, action_list: List, state: Dict, greater_pos: int, my_pos: int) -> int:
        """处理对子被动出牌"""
        if not self.pair_strategy:
            return self._default_passive_action(action_list)
        
        cur_action = message.get("curAction", [])
        action_rank = cur_action[1] if len(cur_action) > 1 else ""
        is_teammate = self._is_teammate(greater_pos, my_pos)
        
        pair_sugg = self.pair_strategy(
            game_phase='mid',
            power=state['power'],
            opponent_rest_cards=min(state['opponent_rest_cards_list']),
            is_active=False,
            is_teammate_action=is_teammate,
            action_type='Pair',
            action_rank=action_rank
        )
        
        if '让对子' in pair_sugg.get('action', ''):
            return 0
        
        # 过滤掉PASS动作
        valid_actions = [(i, action) for i, action in enumerate(action_list) 
                        if len(action) > 0 and action[0] != "PASS"]
        
        if not valid_actions:
            return 0
        
        # 选择能压制的最小对子
        for i, action in valid_actions:
            if action[0] == 'Pair':
                if len(action) > 1:
                    card_rank = str(action[1])
                    if self._compare_rank(card_rank, str(action_rank)) > 0:
                        return i
        
        # 如果没有能压制的，也选择最小的对子（避免一直PASS）
        for i, action in valid_actions:
            if action[0] == 'Pair':
                return i
        
        # 如果连对子都没有，至少选择第一个有效动作（避免一直PASS）
        if valid_actions:
            return valid_actions[0][0]
        
        return 0
    
    def _handle_other_passive(self, message: Dict, action_list: List, state: Dict) -> int:
        """处理其他牌型被动出牌"""
        if state['power'] < 5:
            return 0
        
        cur_action = message.get("curAction", [])
        cur_type = cur_action[0] if len(cur_action) > 0 else ""
        cur_rank = cur_action[1] if len(cur_action) > 1 else ""
        
        # 过滤掉PASS动作
        valid_actions = [(i, action) for i, action in enumerate(action_list) 
                        if len(action) > 0 and action[0] != "PASS"]
        
        if not valid_actions:
            return 0
        
        # 选择能压制的最小动作
        for i, action in valid_actions:
            if action[0] == cur_type:
                if len(action) > 1:
                    card_rank = str(action[1])
                    if self._compare_rank(card_rank, str(cur_rank)) > 0:
                        return i
        
        # 如果没有能压制的，也选择同类型的动作（避免一直PASS）
        for i, action in valid_actions:
            if action[0] == cur_type:
                return i
        
        # 如果连同类型都没有，至少选择第一个有效动作（避免一直PASS）
        if valid_actions:
            return valid_actions[0][0]
        
        return 0
    
    def _default_passive_action(self, action_list: List) -> int:
        """默认被动动作选择"""
        for i, action in enumerate(action_list):
            if action[0] != "PASS":
                return i
        return 0


class MidLateActiveHandler(BasePhaseHandler):
    """中局后期主动出牌处理器（剩余牌数 10-15）"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self._init_helpers()
    
    def _init_helpers(self):
        """初始化辅助工具"""
        try:
            from .card_power_evaluator import calculate_card_power
            from .single_card_strategy import single_card_strategy
            self.calculate_power = calculate_card_power
            self.single_strategy = single_card_strategy
        except ImportError:
            self.calculate_power = None
            self.single_strategy = None
    
    def handle(self, message: Dict) -> int:
        """中局后期策略：积极出牌，配合队友，准备冲刺"""
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        
        if not action_list:
            return 0
        
        # 检查一手出完
        one_hand_idx = self._check_one_hand_complete(action_list, handcards)
        if one_hand_idx is not None:
            return one_hand_idx
        
        # 检查两手出完
        two_hand_idx = self._check_two_hand_complete(action_list, handcards)
        if two_hand_idx is not None:
            return two_hand_idx
        
        # 中局后期策略：积极出牌，准备冲刺
        # 优先级：单张 → 对子 → 三张 → 其他
        state = self._extract_game_state(message)
        
        # 如果有天然单张，优先出单
        if self.single_strategy:
            single_sugg = self.single_strategy(
                game_phase='mid',
                power=state['power'],
                opponent_rest_cards=min(state['opponent_rest_cards_list']),
                is_active=True,
                my_rest_cards=state['my_rest'],
                has_natural_single=True
            )
            if '出单' in single_sugg.get('action', '') or '出天然单' in single_sugg.get('action', ''):
                for i, action in enumerate(action_list):
                    if action[0] == 'Single' and action[0] != "PASS":
                        return i
        
        # 常规优先级：单张 → 对子 → 三张 → 其他
        priority_order = ['Single', 'Pair', 'Trips', 'ThreeWithTwo', 
                         'ThreePair', 'TwoTrips', 'Straight']
        
        for card_type in priority_order:
            for i, action in enumerate(action_list):
                if action[0] == card_type and action[0] != "PASS":
                    return i
        
        return 0
    
    def _extract_game_state(self, message: Dict) -> Dict:
        """提取游戏状态信息"""
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        
        my_rest = len(handcards) if handcards else 27
        # 初始化4个玩家的剩余牌数（0, 1, 2, 3号位）
        opponent_rest_cards_list = [27, 27, 27, 27]
        teammate_rest_cards = 27
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", 27)
                    # 确保索引在范围内
                    if 0 <= i < len(opponent_rest_cards_list):
                        opponent_rest_cards_list[i] = rest
                    if (my_pos in [0, 2] and i in [0, 2]) or (my_pos in [1, 3] and i in [1, 3]):
                        teammate_rest_cards = rest
        
        power = 5.0
        if self.calculate_power and handcards:
            power_result = self.calculate_power(handcards, game_phase='mid', opponent_rest_cards=min(opponent_rest_cards_list))
            power = power_result.get('total_power', 5.0)
        
        return {
            'my_rest': my_rest,
            'opponent_rest_cards_list': opponent_rest_cards_list,
            'teammate_rest_cards': teammate_rest_cards,
            'power': power,
            'my_pos': my_pos
        }
    
    def _check_two_hand_complete(self, action_list: List, handcards: List) -> Optional[int]:
        """检查两手出完（M1增强：实现完整的两手出完逻辑）"""
        if not handcards or len(handcards) > 10:
            return None
        
        hand_count = len(handcards)
        
        # 尝试找到两个动作，使得它们的牌数之和等于剩余牌数
        for i, action1 in enumerate(action_list):
            if not action1 or action1[0] == "PASS":
                continue
            cards1 = action1[2] if len(action1) > 2 else []
            count1 = len(cards1) if isinstance(cards1, list) else 0
            
            if count1 == 0:
                continue
            
            # 如果第一个动作已经出完所有牌，返回它
            if count1 == hand_count:
                return i
            
            # 尝试找第二个动作
            remaining = hand_count - count1
            if remaining <= 0:
                continue
            
            for j, action2 in enumerate(action_list):
                if i == j or not action2 or action2[0] == "PASS":
                    continue
                cards2 = action2[2] if len(action2) > 2 else []
                count2 = len(cards2) if isinstance(cards2, list) else 0
                
                # 检查两个动作的牌是否不重叠
                if count2 == remaining:
                    # 简单检查：如果两个动作的牌数之和等于手牌数，且牌不重叠
                    if isinstance(cards1, list) and isinstance(cards2, list):
                        # 检查是否有重叠
                        if not set(cards1) & set(cards2):
                            # 找到两手出完的组合，返回第一个动作
                            return i
        
        return None


class MidLatePassiveHandler(MidEarlyPassiveHandler):
    """中局后期被动出牌处理器（继承中局前期逻辑，但更积极）"""
    
    def handle(self, message: Dict) -> int:
        """中局后期被动出牌策略：更积极压制，准备冲刺"""
        action_list = message.get("actionList", [])
        cur_action = message.get("curAction")
        
        if not action_list or not cur_action:
            return 0
        
        state = self._extract_game_state(message)
        greater_pos = message.get("greaterPos", -1)
        my_pos = state['my_pos']
        is_teammate = self._is_teammate(greater_pos, my_pos)
        
        # 队友出牌，中局后期仍然让过
        if is_teammate:
            return 0
        
        # 中局后期更积极，牌力足够时压制
        if state['power'] >= 5:
            # 调用父类方法，但更倾向于压制
            return super().handle(message)
        else:
            # 牌力弱，让过
            return 0


class EndgameEarlyActiveHandler(BasePhaseHandler):
    """残局前期主动出牌处理器（剩余牌数 5-10）"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self._init_helpers()
    
    def _init_helpers(self):
        """初始化辅助工具"""
        try:
            from .card_power_evaluator import calculate_card_power
            from .endgame_strategy import endgame_strategy, check_one_hand_finish
            self.calculate_power = calculate_card_power
            self.endgame_strategy = endgame_strategy
            self.check_one_hand = check_one_hand_finish
        except ImportError:
            self.calculate_power = None
            self.endgame_strategy = None
            self.check_one_hand = None
    
    def handle(self, message: Dict) -> int:
        """残局前期策略：快速出牌，保护队友，争取先手"""
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        
        if not action_list:
            return 0
        
        my_rest = len(handcards) if handcards else 27
        
        # 优先级1: 一手出完（使用endgame_strategy的check_one_hand_finish）
        if self.check_one_hand:
            one_hand_result = self.check_one_hand(
                my_rest_cards=my_rest,
                action_list=action_list,
                hand_cards=handcards
            )
            if one_hand_result.get('can_finish', False):
                return one_hand_result.get('best_action_index', 0)
        else:
            # 回退到基类方法
            one_hand_idx = self._check_one_hand_complete(action_list, handcards)
            if one_hand_idx is not None:
                return one_hand_idx
        
        # 优先级2: 使用残局策略
        state = self._extract_game_state(message)
        if self.endgame_strategy:
            endgame_sugg = self.endgame_strategy(
                opponent_rest_cards=min(state['opponent_rest_cards_list']),
                power=state['power'],
                my_rest_cards=my_rest,
                action_list=action_list,
                hand_cards=handcards
            )
            # 如果策略建议了一手出完的索引，使用它
            if 'one_hand_index' in endgame_sugg:
                idx = endgame_sugg['one_hand_index']
                if 0 <= idx < len(action_list):
                    return idx
        
        # 优先级3: 出最大牌型（快速减少牌数）
        return self._select_largest_action(action_list)
    
    def _extract_game_state(self, message: Dict) -> Dict:
        """提取游戏状态信息"""
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        
        my_rest = len(handcards) if handcards else 27
        # 初始化4个玩家的剩余牌数（0, 1, 2, 3号位）
        opponent_rest_cards_list = [27, 27, 27, 27]
        teammate_rest_cards = 27
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", 27)
                    # 确保索引在范围内
                    if 0 <= i < len(opponent_rest_cards_list):
                        opponent_rest_cards_list[i] = rest
                    if (my_pos in [0, 2] and i in [0, 2]) or (my_pos in [1, 3] and i in [1, 3]):
                        teammate_rest_cards = rest
        
        power = 5.0
        if self.calculate_power and handcards:
            power_result = self.calculate_power(handcards, game_phase='endgame', opponent_rest_cards=min(opponent_rest_cards_list))
            power = power_result.get('total_power', 5.0)
        
        return {
            'my_rest': my_rest,
            'opponent_rest_cards_list': opponent_rest_cards_list,
            'teammate_rest_cards': teammate_rest_cards,
            'power': power,
            'my_pos': my_pos
        }
    
    def _select_largest_action(self, action_list: List) -> int:
        """选择最大牌型（残局专用）"""
        largest_idx = 0
        largest_size = 0
        
        for i, action in enumerate(action_list):
            if not action or action[0] == "PASS":
                continue
            action_size = len(action[2]) if len(action) > 2 else 1
            if action_size > largest_size:
                largest_size = action_size
                largest_idx = i
        
        return largest_idx


class EndgameEarlyPassiveHandler(BasePhaseHandler):
    """残局前期被动出牌处理器"""
    
    # 牌点大小顺序：3 < 4 < 5 < 6 < 7 < 8 < 9 < T < J < Q < K < A < 2 < B < R
    RANK_ORDER = ['3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A', '2', 'B', 'R']
    
    @classmethod
    def _compare_rank(cls, rank1: str, rank2: str) -> int:
        """比较两张牌的大小，返回-1表示rank1<rank2，0表示相等，1表示rank1>rank2"""
        try:
            idx1 = cls.RANK_ORDER.index(str(rank1)) if str(rank1) in cls.RANK_ORDER else -1
            idx2 = cls.RANK_ORDER.index(str(rank2)) if str(rank2) in cls.RANK_ORDER else -1
            if idx1 < 0 or idx2 < 0:
                return 0  # 无法比较
            if idx1 < idx2:
                return -1
            elif idx1 > idx2:
                return 1
            else:
                return 0
        except (ValueError, IndexError):
            return 0
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self._init_helpers()
    
    def _init_helpers(self):
        """初始化辅助工具"""
        try:
            from .endgame_strategy import endgame_strategy
            self.endgame_strategy = endgame_strategy
        except ImportError:
            self.endgame_strategy = None
    
    def handle(self, message: Dict) -> int:
        """残局前期被动出牌策略：快速压制，保护队友"""
        action_list = message.get("actionList", [])
        cur_action = message.get("curAction")
        handcards = message.get("handCards", [])
        
        if not action_list or not cur_action:
            return 0
        
        my_rest = len(handcards) if handcards else 27
        greater_pos = message.get("greaterPos", -1)
        my_pos = message.get("myPos", 0)
        is_teammate = self._is_teammate(greater_pos, my_pos)
        
        # 队友出牌，残局前期让过
        if is_teammate:
            return 0
        
        # 残局前期：快速压制，优先一手出完
        one_hand_idx = self._check_one_hand_complete(action_list, handcards)
        if one_hand_idx is not None:
            return one_hand_idx
        
        # 选择能压制的最小动作
        cur_action_type = cur_action[0] if isinstance(cur_action, list) and len(cur_action) > 0 else ""
        cur_rank = cur_action[1] if len(cur_action) > 1 else ""
        
        for i, action in enumerate(action_list):
            if action[0] == cur_action_type and action[0] != "PASS":
                if len(action) > 1 and action[1] > cur_rank:
                    return i
        
        return 0
    
    def _is_teammate(self, pos: int, my_pos: int) -> bool:
        """判断是否是队友"""
        if pos == -1 or my_pos == -1:
            return False
        return (my_pos in [0, 2] and pos in [0, 2]) or (my_pos in [1, 3] and pos in [1, 3])


class EndgameLateActiveHandler(BasePhaseHandler):
    """残局后期主动出牌处理器（剩余牌数 ≤ 5）"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self._init_helpers()
    
    def _init_helpers(self):
        """初始化辅助工具"""
        try:
            from .card_power_evaluator import calculate_card_power
            from .endgame_strategy import endgame_strategy, check_one_hand_finish
            self.calculate_power = calculate_card_power
            self.endgame_strategy = endgame_strategy
            self.check_one_hand = check_one_hand_finish
        except ImportError:
            self.calculate_power = None
            self.endgame_strategy = None
            self.check_one_hand = None
    
    def handle(self, message: Dict) -> int:
        """残局后期策略：全力冲刺，一手出完优先，快速结束"""
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        
        if not action_list:
            return 0
        
        my_rest = len(handcards) if handcards else 27
        
        # 优先级1: 一手出完（残局最重要）
        if self.check_one_hand:
            one_hand_result = self.check_one_hand(
                my_rest_cards=my_rest,
                action_list=action_list,
                hand_cards=handcards
            )
            if one_hand_result.get('can_finish', False):
                return one_hand_result.get('best_action_index', 0)
        else:
            one_hand_idx = self._check_one_hand_complete(action_list, handcards)
            if one_hand_idx is not None:
                return one_hand_idx
        
        # 优先级2: 使用残局策略（残局后期更激进）
        state = self._extract_game_state(message)
        if self.endgame_strategy:
            endgame_sugg = self.endgame_strategy(
                opponent_rest_cards=min(state['opponent_rest_cards_list']),
                power=state['power'],
                my_rest_cards=my_rest,
                action_list=action_list,
                hand_cards=handcards
            )
            if 'one_hand_index' in endgame_sugg:
                idx = endgame_sugg['one_hand_index']
                if 0 <= idx < len(action_list):
                    return idx
        
        # 优先级3: 出最大牌型（快速减少牌数）
        return self._select_largest_action(action_list)
    
    def _extract_game_state(self, message: Dict) -> Dict:
        """提取游戏状态信息"""
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        
        my_rest = len(handcards) if handcards else 27
        # 初始化4个玩家的剩余牌数（0, 1, 2, 3号位）
        opponent_rest_cards_list = [27, 27, 27, 27]
        teammate_rest_cards = 27
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", 27)
                    # 确保索引在范围内
                    if 0 <= i < len(opponent_rest_cards_list):
                        opponent_rest_cards_list[i] = rest
                    if (my_pos in [0, 2] and i in [0, 2]) or (my_pos in [1, 3] and i in [1, 3]):
                        teammate_rest_cards = rest
        
        power = 5.0
        if self.calculate_power and handcards:
            power_result = self.calculate_power(handcards, game_phase='endgame', opponent_rest_cards=min(opponent_rest_cards_list))
            power = power_result.get('total_power', 5.0)
        
        return {
            'my_rest': my_rest,
            'opponent_rest_cards_list': opponent_rest_cards_list,
            'teammate_rest_cards': teammate_rest_cards,
            'power': power,
            'my_pos': my_pos
        }
    
    def _select_largest_action(self, action_list: List) -> int:
        """选择最大牌型（残局专用）"""
        largest_idx = 0
        largest_size = 0
        
        for i, action in enumerate(action_list):
            if not action or action[0] == "PASS":
                continue
            action_size = len(action[2]) if len(action) > 2 else 1
            if action_size > largest_size:
                largest_size = action_size
                largest_idx = i
        
        return largest_idx


class EndgameLatePassiveHandler(EndgameEarlyPassiveHandler):
    """残局后期被动出牌处理器（继承残局前期逻辑，但更激进）"""
    
    def handle(self, message: Dict) -> int:
        """残局后期被动出牌策略：全力压制，争取先手"""
        action_list = message.get("actionList", [])
        cur_action = message.get("curAction")
        handcards = message.get("handCards", [])
        
        if not action_list or not cur_action:
            return 0
        
        my_rest = len(handcards) if handcards else 27
        greater_pos = message.get("greaterPos", -1)
        my_pos = message.get("myPos", 0)
        is_teammate = self._is_teammate(greater_pos, my_pos)
        
        # 队友出牌，残局后期让过
        if is_teammate:
            return 0
        
        # 残局后期：全力压制，优先一手出完
        one_hand_idx = self._check_one_hand_complete(action_list, handcards)
        if one_hand_idx is not None:
            return one_hand_idx
        
        # 选择能压制的最小动作（更激进）
        cur_action_type = cur_action[0] if isinstance(cur_action, list) and len(cur_action) > 0 else ""
        cur_rank = cur_action[1] if len(cur_action) > 1 else ""
        
        for i, action in enumerate(action_list):
            if action[0] == cur_action_type and action[0] != "PASS":
                if len(action) > 1 and action[1] > cur_rank:
                    return i
        
        return 0


class TributeHandler(BasePhaseHandler):
    """进贡处理器"""
    
    def handle(self, message: Dict) -> int:
        """进贡决策：选择最小的牌进贡"""
        action_list = message.get("actionList", [])
        
        if not action_list:
            return 0
        
        # 如果是字典格式（tribute: [cards]）
        if isinstance(action_list, dict) and "tribute" in action_list:
            tribute_cards = action_list["tribute"]
            if tribute_cards and len(tribute_cards) > 0:
                # 选择最小的牌（第一个）
                return 0
        
        # 如果是列表格式
        if isinstance(action_list, list) and len(action_list) > 0:
            # 选择第一个（通常是最小的）
            return 0
        
        return 0


class BackHandler(BasePhaseHandler):
    """还贡处理器"""
    
    def handle(self, message: Dict) -> int:
        """还贡决策：选择最小的牌还贡"""
        action_list = message.get("actionList", [])
        
        if not action_list:
            return 0
        
        # 如果是字典格式（back: [cards]）
        if isinstance(action_list, dict) and "back" in action_list:
            back_cards = action_list["back"]
            if back_cards and len(back_cards) > 0:
                # 选择最小的牌（第一个）
                return 0
        
        # 如果是列表格式
        if isinstance(action_list, list) and len(action_list) > 0:
            # 选择第一个（通常是最小的）
            return 0
        
        return 0

