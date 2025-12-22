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
        
        logger.info(f"OpeningActiveHandler: actionList size={len(action_list)}")
        if action_list:
            logger.info(f"First 3 actions: {action_list[:3]}")
            # 统计actionList中的动作类型
            action_types = {}
            for action in action_list[:10]:
                if isinstance(action, list) and len(action) > 0:
                    action_type = action[0]
                    action_types[action_type] = action_types.get(action_type, 0) + 1
            logger.info(f"Action types in first 10: {action_types}")
        
        if not action_list:
            logger.warning("Empty actionList, returning 0")
            return 0
        
        # 开局不需要检查"一手出完"（优化：避免不必要的检查）
        # 开局策略：建立牌型结构
        result = self._build_structure_strategy(message, action_list, handcards)
        logger.info(f"Selected action index: {result}, action: {action_list[result] if result < len(action_list) else 'INVALID'}")
        return result
    
    def _extract_game_state(self, message: Dict) -> Dict:
        """提取游戏状态信息"""
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        cur_rank = message.get("curRank", "2")
        
        # 计算剩余牌数
        my_rest = len(handcards) if handcards else 27
        opponent_rest_cards_list = [27, 27, 27, 27]  # 修复：初始化为4个元素（对应4个玩家）
        teammate_rest_cards = 27
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", 27)
                    if i < len(opponent_rest_cards_list):  # 添加边界检查，防止索引越界
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
        
        # 构建上下文信息
        context = self._build_context(message)
        
        # ⭐ 使用优先级系统（提升：动态优先级）
        if self.priority_system:
            # 获取手牌结构（简化实现）
            hand_structure = {}
            # 过滤PASS动作，同时记录原始索引
            candidates = []
            candidate_indices = []
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0:
                    if action[0] != "PASS":
                        candidates.append(action)
                        candidate_indices.append(i)
                elif action != "PASS":
                    candidates.append(action)
                    candidate_indices.append(i)
            
            logger.debug(f"Filtered {len(candidates)} candidates from {len(action_list)} actions")
            
            if candidates:
                try:
                    selected_candidate_idx = self.priority_system.select(candidates, hand_structure, context)
                    if 0 <= selected_candidate_idx < len(candidate_indices):
                        original_idx = candidate_indices[selected_candidate_idx]
                        logger.info(f"PrioritySystem selected: candidate_idx={selected_candidate_idx}, original_idx={original_idx}, action={candidates[selected_candidate_idx]}")
                        return original_idx
                    else:
                        logger.warning(f"PrioritySystem returned invalid index: {selected_candidate_idx}, max={len(candidate_indices)-1}")
                except Exception as e:
                    logger.error(f"PrioritySystem.select() error: {e}", exc_info=True)
            else:
                logger.warning("No candidates after filtering PASS actions")
        
        # 提取游戏状态（降级方案）
        state = self._extract_game_state(message)
        power = state['power']
        
        # 根据开局策略文档，优先级策略：
        # 1. 牌力强（有王/级牌）：优先出天然单张
        # 2. 牌力中下：情况不明对子先行
        # 3. 牌力弱：助攻定位，不出单，保留牌型组合
        
        # 检查是否有王或级牌
        has_king = any('R' in card or 'B' in card for card in handcards)
        has_level_card = any(state['cur_rank'] in card for card in handcards)
        
        # 策略1：牌力强，有王/级牌，优先出天然单张
        if (power >= 6 or has_king or has_level_card) and self.single_strategy:
            # 使用单张策略
            single_sugg = self.single_strategy(
                game_phase='opening',
                power=power,
                opponent_rest_cards=min(state['opponent_rest_cards_list']),
                has_king=has_king,
                has_level_card=has_level_card,
                is_active=True,
                my_rest_cards=state['my_rest'],
                teammate_rest_cards=state['teammate_rest_cards']
            )
            
            if '出单' in single_sugg.get('action', '') or '出天然单' in single_sugg.get('action', ''):
                # 选择最小的单张
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                        return i
        
        # 策略2：牌力中下，情况不明对子先行
        if power < 6 and self.pair_strategy:
            pair_sugg = self.pair_strategy(
                game_phase='opening',
                power=power,
                opponent_rest_cards=min(state['opponent_rest_cards_list']),
                is_active=True,
                my_rest_cards=state['my_rest']
            )
            
            if '对子先行' in pair_sugg.get('action', '') or '出对' in pair_sugg.get('action', ''):
                # 选择最小的对子
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == 'Pair':
                        return i
        
        # 策略3：牌力弱，助攻定位，优先保留牌型组合
        if power < 5:
            # 优先出三连对/钢板（对手难管）
            priority_order = ['TwoTrips', 'ThreePair', 'Straight', 'ThreeWithTwo', 'Trips']
        for card_type in priority_order:
            for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == card_type:
                        return i
            # 如果没有组合牌型，再考虑对子
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Pair':
                    return i
            # 最后才考虑单张
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    return i
        else:
            # 牌力正常，按常规优先级：小单张 → 三连对/钢板 → 顺子 → 三带二 → 三张 → 对子
            priority_order = ['Single', 'TwoTrips', 'ThreePair', 'Straight', 
                             'ThreeWithTwo', 'Trips', 'Pair']
            for card_type in priority_order:
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == card_type:
                        # 单张选择最小的
                    if card_type == 'Single':
                        return i
                    return i
        
        return 0


class OpeningPassiveHandler(BasePhaseHandler):
    """开局被动出牌处理器"""
    
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
        """开局被动出牌策略：顺上家、控下家、让对家"""
        import logging
        logger = logging.getLogger("OpeningPassiveHandler")
        
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        cur_action = message.get("curAction")
        
        logger.info(f"OpeningPassiveHandler: actionList size={len(action_list)}, curAction={cur_action}, curAction type={type(cur_action)}")
        if len(action_list) > 0:
            logger.info(f"First few actions: {action_list[:3]}")
        
        if not action_list:
            logger.warning("Empty actionList, returning 0")
            return 0
        
        # 如果没有当前动作，说明是主动出牌，不应该到这里
        if not cur_action:
            logger.warning("No curAction, this should be active play, returning 0")
            return 0
        
        # 修复：如果curAction是字符串，尝试解析为列表
        if isinstance(cur_action, str):
            try:
                import json
                # 尝试解析JSON字符串
                cur_action = json.loads(cur_action)
                logger.info(f"Parsed curAction from JSON string: {cur_action}")
            except (json.JSONDecodeError, ValueError):
                try:
                    # 如果不是JSON，尝试使用ast.literal_eval
                    import ast
                    cur_action = ast.literal_eval(cur_action)
                    logger.info(f"Parsed curAction using ast.literal_eval: {cur_action}")
                except (ValueError, SyntaxError):
                    logger.warning(f"Failed to parse curAction string: {cur_action}")
                    # 如果解析失败，尝试从字符串中提取类型
                    if cur_action.startswith("['") or cur_action.startswith('["'):
                        # 可能是列表的字符串表示，尝试提取第一个元素
                        start_idx = 2 if cur_action.startswith("['") else 2
                        quote_char = "'" if cur_action.startswith("['") else '"'
                        end_idx = cur_action.find(quote_char, start_idx)
                        if end_idx > start_idx:
                            action_type = cur_action[start_idx:end_idx]
                            cur_action = [action_type]  # 创建一个简化的列表
                            logger.info(f"Extracted action type from string: {action_type}, created simplified curAction: {cur_action}")
                    else:
                        logger.error(f"Cannot parse curAction: {cur_action}")
                        return 0
        
        # 检查curAction是否是有效的被动出牌动作
        # 如果curAction是[None, None, None]或第一个元素是None，说明是主动出牌，不应该到这里
        if isinstance(cur_action, list) and len(cur_action) > 0:
            if cur_action[0] is None:
                logger.warning(f"curAction first element is None: {cur_action}, this should be active play, returning 0")
                return 0
            # 如果第一个元素是"PASS"，检查actionList的第一个动作
            if cur_action[0] == "PASS":
                # 如果actionList的第一个动作不是PASS，说明是主动出牌
                if action_list and len(action_list) > 0:
                    first_action = action_list[0]
                    if isinstance(first_action, list) and len(first_action) > 0:
                        if first_action[0] != "PASS":
                            logger.warning(f"curAction is PASS but actionList first action is {first_action[0]}, this should be active play, returning 0")
                            return 0
        
        # 构建上下文信息
        context = self._build_context(message)
        
        # ⭐ 使用队友保护策略（提升：多策略组合）
        if self.teammate_protection:
            protection_action = self.teammate_protection.get_protection_action(message, context)
            if protection_action is not None:
                logger.info(f"Teammate protection returned action: {protection_action}")
                return protection_action
            else:
                logger.debug("Teammate protection returned None")
        
        # 提取游戏状态
        state = self._extract_game_state(message)
        
        # 详细调试：检查curAction的类型和内容
        logger.info(f"curAction type: {type(cur_action)}, value: {cur_action}")
        if isinstance(cur_action, list):
            logger.info(f"curAction is list, length: {len(cur_action)}, first element: {cur_action[0] if len(cur_action) > 0 else 'N/A'}")
        
        # 修复：更安全地提取curAction_type
        if isinstance(cur_action, list) and len(cur_action) > 0:
            cur_action_type = str(cur_action[0]) if cur_action[0] is not None else ""
        else:
            cur_action_type = ""
        
        greater_pos = message.get("greaterPos", -1)
        my_pos = state['my_pos']
        
        logger.info(f"curAction_type={cur_action_type}, greater_pos={greater_pos}, my_pos={my_pos}")
        
        # 判断是否是队友出牌
        is_teammate = self._is_teammate(greater_pos, my_pos)
        logger.info(f"is_teammate={is_teammate}")
        
        # 开局被动策略：队友出牌让过，对手出牌根据位置决定
        if is_teammate:
            # 队友出牌，开局阶段让过
            logger.info("Teammate played, passing in opening phase")
            return 0  # PASS
        
        # 对手出牌，根据位置决定策略
        # 如果curAction_type为空，尝试从curAction直接提取
        if not cur_action_type and isinstance(cur_action, list) and len(cur_action) > 0:
            # 再次尝试提取
            first_elem = cur_action[0]
            if isinstance(first_elem, str):
                cur_action_type = first_elem
            else:
                cur_action_type = str(first_elem) if first_elem is not None else ""
            logger.info(f"Retried curAction_type extraction: {cur_action_type}")
        
        # 根据动作类型路由到对应的处理方法
        if cur_action_type == 'Single':
            logger.info("Calling _handle_single_passive")
            return self._handle_single_passive(message, action_list, state, greater_pos, my_pos)
        elif cur_action_type == 'Pair':
            logger.info("Calling _handle_pair_passive")
            return self._handle_pair_passive(message, action_list, state, greater_pos, my_pos)
        elif cur_action_type in ['Trips', 'ThreeWithTwo', 'ThreePair', 'TwoTrips', 'Straight', 'StraightFlush', 'Bomb']:
            # 其他牌型，根据牌力决定是否压制
            logger.info(f"Handling {cur_action_type} passive play, calling _handle_other_passive")
            return self._handle_other_passive(message, action_list, state)
        else:
            # 未知牌型，使用默认处理
            logger.warning(f"Unknown curAction_type '{cur_action_type}', calling _handle_other_passive")
            return self._handle_other_passive(message, action_list, state)
    
    def _extract_game_state(self, message: Dict) -> Dict:
        """提取游戏状态信息"""
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        cur_rank = message.get("curRank", "2")
        
        my_rest = len(handcards) if handcards else 27
        opponent_rest_cards_list = [27, 27, 27, 27]  # 修复：初始化为4个元素（对应4个玩家）
        teammate_rest_cards = 27
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", 27)
                    if i < len(opponent_rest_cards_list):  # 添加边界检查，防止索引越界
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
        """判断是否是队友"""
        if pos == -1 or my_pos == -1:
            return False
        # 第1个和第3个为一队，第2个和第4个为一队
        return (my_pos in [0, 2] and pos in [0, 2]) or (my_pos in [1, 3] and pos in [1, 3])
    
    def _handle_single_passive(self, message: Dict, action_list: List, state: Dict, greater_pos: int, my_pos: int) -> int:
        """处理单张被动出牌"""
        import logging
        logger = logging.getLogger("OpeningPassiveHandler")
        
        logger.info(f"_handle_single_passive: actionList size={len(action_list)}")
        if action_list:
            logger.info(f"First 3 actions: {action_list[:3]}")
            # 统计actionList中的动作类型
            action_types = {}
            for i, action in enumerate(action_list[:10]):  # 只检查前10个
                if isinstance(action, list) and len(action) > 0:
                    action_type = action[0]
                    action_types[action_type] = action_types.get(action_type, 0) + 1
            logger.info(f"Action types in first 10 actions: {action_types}")
        
        if not self.single_strategy:
            logger.warning("No single_strategy, using default")
            return self._default_passive_action(action_list)
        
        # 获取curAction，如果之前已经解析过，直接使用；否则重新获取并解析
        cur_action = message.get("curAction", [])
        # 如果curAction是字符串，尝试解析
        if isinstance(cur_action, str):
            try:
                import ast
                cur_action = ast.literal_eval(cur_action)
                logger.info(f"Re-parsed curAction in _handle_single_passive: {cur_action}")
            except (ValueError, SyntaxError) as e:
                logger.warning(f"Failed to re-parse curAction in _handle_single_passive: {cur_action}, error: {e}")
                # 如果解析失败，尝试从字符串中提取类型
                if cur_action.startswith("['") or cur_action.startswith('["'):
                    start_idx = 2 if cur_action.startswith("['") else 2
                    quote_char = "'" if cur_action.startswith("['") else '"'
                    end_idx = cur_action.find(quote_char, start_idx)
                    if end_idx > start_idx:
                        action_type = cur_action[start_idx:end_idx]
                        cur_action = [action_type]
                        logger.info(f"Extracted action type from string: {action_type}")
        
        action_rank = cur_action[1] if isinstance(cur_action, list) and len(cur_action) > 1 else ""
        
        # 判断是否是上家出单（上家是朋友）
        is_upper_hand = (greater_pos == (my_pos - 1) % 4) or (greater_pos == (my_pos + 3) % 4)
        
        logger.info(f"curAction={cur_action}, action_rank={action_rank}, is_upper_hand={is_upper_hand}")
        
        # 使用单张策略
        single_sugg = self.single_strategy(
            game_phase='opening',
            power=state['power'],
            opponent_rest_cards=min(state['opponent_rest_cards_list']),
            is_active=False,
            is_upper_hand=is_upper_hand,
            my_rest_cards=state['my_rest'],
            teammate_rest_cards=state['teammate_rest_cards']
        )
        
        logger.info(f"single_strategy suggestion: {single_sugg}")
        
        # 如果策略建议不出单，则PASS
        if '不出单' in single_sugg.get('action', ''):
            logger.info("Strategy suggests not playing single, passing")
            return 0
        
        # 选择能压制的最小单张（简化：只要找到Single就出，不比较rank）
        # 注意：actionList中的动作都是能管上的，所以直接选择第一个Single即可
        logger.info("Searching for Single actions in actionList")
        single_count = 0
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0:
                if action[0] == 'Single':
                    single_count += 1
                    logger.info(f"Found Single action at index {i}: {action}")
                    # 选择第一个能管上的Single动作（actionList中的动作都是能管上的）
                    return i
            elif isinstance(action, str) and action == 'Single':
                single_count += 1
                logger.info(f"Found Single action (string) at index {i}")
                return i
        
        logger.warning(f"No Single action found in actionList (checked {len(action_list)} actions, found {single_count} Single actions), returning default")
        logger.info(f"First 5 actions in actionList: {action_list[:5] if len(action_list) >= 5 else action_list}")
        result = self._default_passive_action(action_list)
        logger.info(f"_default_passive_action returned: {result}")
        return result
    
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
        
        # 选择能压制的最小对子
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == 'Pair':
                if len(action) > 1 and action[1] > action_rank:
                    return i
        
        return 0
    
    def _handle_other_passive(self, message: Dict, action_list: List, state: Dict) -> int:
        """处理其他牌型被动出牌"""
        # 开局阶段，牌力弱时让过，牌力强时压制
        if state['power'] < 5:
            return 0  # PASS
        
        # 选择能压制的最小动作
        cur_action = message.get("curAction", [])
        cur_type = cur_action[0] if len(cur_action) > 0 else ""
        cur_rank = cur_action[1] if len(cur_action) > 1 else ""
        
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == cur_type:
                if len(action) > 1 and action[1] > cur_rank:
                    return i
        
        return 0
    
    def _default_passive_action(self, action_list: List) -> int:
        """默认被动动作选择：选择第一个非PASS动作"""
        import logging
        logger = logging.getLogger("OpeningPassiveHandler")
        
        logger.info(f"_default_passive_action: actionList size={len(action_list)}")
        if action_list:
            logger.info(f"First 5 actions: {action_list[:5]}")
        
        # 选择第一个非PASS动作
        non_pass_count = 0
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0:
                if action[0] != "PASS":
                    non_pass_count += 1
                    logger.info(f"Found non-PASS action at index {i}: {action[0]} - {action}")
                    # 选择第一个非PASS动作
                    return i
            elif action != "PASS":
                non_pass_count += 1
                logger.info(f"Found non-PASS action at index {i}: {action}")
                return i
        
        logger.warning(f"No non-PASS actions found (checked {len(action_list)} actions, found {non_pass_count} non-PASS), returning 0 (PASS)")
        if action_list:
            logger.warning(f"All actions in actionList: {action_list}")
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
        
        # ⭐ 使用优先级系统（提升：动态优先级）
        context = self._build_context(message)
        if self.priority_system:
            # 获取手牌结构（简化实现）
            hand_structure = {}
            # 过滤PASS动作，同时记录原始索引
            candidates = []
            candidate_indices = []
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0:
                    if action[0] != "PASS":
                        candidates.append(action)
                        candidate_indices.append(i)
                elif action != "PASS":
                    candidates.append(action)
                    candidate_indices.append(i)
            
            if candidates:
                selected_candidate_idx = self.priority_system.select(candidates, hand_structure, context)
                if 0 <= selected_candidate_idx < len(candidate_indices):
                    return candidate_indices[selected_candidate_idx]
        
        # 降级方案：使用原有逻辑
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
                    if isinstance(action, list) and len(action) > 0 and action[0] == 'Pair':
                        return i
        
        # 常规优先级：对子 → 三张 → 单张 → 其他
        priority_order = ['Pair', 'Trips', 'Single', 'ThreeWithTwo', 
                         'ThreePair', 'TwoTrips', 'Straight']
        
        for card_type in priority_order:
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == card_type:
                    return i
        
        return 0
    
    def _extract_game_state(self, message: Dict) -> Dict:
        """提取游戏状态信息"""
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        
        my_rest = len(handcards) if handcards else 27
        opponent_rest_cards_list = [27, 27, 27, 27]  # 修复：初始化为4个元素（对应4个玩家）
        teammate_rest_cards = 27
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", 27)
                    if i < len(opponent_rest_cards_list):  # 添加边界检查，防止索引越界
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
        
        # 构建上下文信息
        context = self._build_context(message)
        
        # ⭐ 使用队友保护策略（提升：多策略组合）
        if self.teammate_protection:
            protection_action = self.teammate_protection.get_protection_action(message, context)
            if protection_action is not None:
                return protection_action
        
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
        opponent_rest_cards_list = [27, 27, 27, 27]  # 修复：初始化为4个元素（对应4个玩家）
        teammate_rest_cards = 27
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", 27)
                    if i < len(opponent_rest_cards_list):  # 添加边界检查，防止索引越界
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
        
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                if len(action) > 1 and action[1] > action_rank:
                    return i
        
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
        
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == 'Pair':
                if len(action) > 1 and action[1] > action_rank:
                    return i
        
        return 0
    
    def _handle_other_passive(self, message: Dict, action_list: List, state: Dict) -> int:
        """处理其他牌型被动出牌"""
        if state['power'] < 5:
            return 0
        
        cur_action = message.get("curAction", [])
        cur_type = cur_action[0] if len(cur_action) > 0 else ""
        cur_rank = cur_action[1] if len(cur_action) > 1 else ""
        
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == cur_type:
                if len(action) > 1 and action[1] > cur_rank:
                    return i
        
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
        
        # ⭐ 使用优先级系统（提升：动态优先级）
        context = self._build_context(message)
        if self.priority_system:
            # 获取手牌结构（简化实现）
            hand_structure = {}
            # 过滤PASS动作，同时记录原始索引
            candidates = []
            candidate_indices = []
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0:
                    if action[0] != "PASS":
                        candidates.append(action)
                        candidate_indices.append(i)
                elif action != "PASS":
                    candidates.append(action)
                    candidate_indices.append(i)
            
            if candidates:
                selected_candidate_idx = self.priority_system.select(candidates, hand_structure, context)
                if 0 <= selected_candidate_idx < len(candidate_indices):
                    return candidate_indices[selected_candidate_idx]
        
        # 降级方案：使用原有逻辑
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
                    if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                        return i
        
        # 常规优先级：单张 → 对子 → 三张 → 其他
        priority_order = ['Single', 'Pair', 'Trips', 'ThreeWithTwo', 
                         'ThreePair', 'TwoTrips', 'Straight']
        
        for card_type in priority_order:
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == card_type:
                    return i
        
        return 0
    
    def _extract_game_state(self, message: Dict) -> Dict:
        """提取游戏状态信息"""
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        
        my_rest = len(handcards) if handcards else 27
        opponent_rest_cards_list = [27, 27, 27, 27]  # 修复：初始化为4个元素（对应4个玩家）
        teammate_rest_cards = 27
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", 27)
                    if i < len(opponent_rest_cards_list):  # 添加边界检查，防止索引越界
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
        
        # 构建上下文信息
        context = self._build_context(message)
        
        # ⭐ 使用队友保护策略（提升：多策略组合）
        if self.teammate_protection:
            protection_action = self.teammate_protection.get_protection_action(message, context)
            if protection_action is not None:
                return protection_action
        
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
        self._init_endgame_strategies()
    
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
    
    def _init_endgame_strategies(self):
        """初始化残局策略选择器（提升：整合残局策略类）"""
        try:
            from .endgame_strategies import EndgameStrategySelector
            self.strategy_selector = EndgameStrategySelector(self.config)
        except ImportError:
            self.strategy_selector = None
    
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
        
        # ⭐ 使用优先级系统（提升：动态优先级，残局阶段）
        context = self._build_context(message)
        if self.priority_system:
            # 获取手牌结构（简化实现）
            hand_structure = {}
            candidates = [a for a in action_list if a[0] != "PASS"]
            if candidates:
                return self.priority_system.select(candidates, hand_structure, context)
        
        # 优先级2: 使用残局策略类（提升：智能策略选择）
        context = self._build_context(message)
        context.update({
            'my_remain': my_rest,
            'teammate_rest_cards': state.get('teammate_rest_cards', 27),
            'opponent_rest_cards_list': state.get('opponent_rest_cards_list', [27, 27, 27, 27])
        })
        
        if self.strategy_selector:
            strategy = self.strategy_selector.select_strategy(message, context)
            strategy_result = strategy.execute(message, context)
            if strategy_result is not None and 0 <= strategy_result < len(action_list):
                return strategy_result
        
        # 降级方案：使用原有残局策略函数
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
        opponent_rest_cards_list = [27, 27, 27, 27]  # 修复：初始化为4个元素（对应4个玩家）
        teammate_rest_cards = 27
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", 27)
                    if i < len(opponent_rest_cards_list):  # 添加边界检查，防止索引越界
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
        
        # 构建上下文信息
        context = self._build_context(message)
        
        # ⭐ 使用队友保护策略（提升：多策略组合，残局阶段更重要）
        if self.teammate_protection:
            protection_action = self.teammate_protection.get_protection_action(message, context)
            if protection_action is not None:
                return protection_action
        
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
            if isinstance(action, list) and len(action) > 0 and action[0] == cur_action_type:
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
        self._init_endgame_strategies()
    
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
    
    def _init_endgame_strategies(self):
        """初始化残局策略选择器（提升：整合残局策略类）"""
        try:
            from .endgame_strategies import EndgameStrategySelector
            self.strategy_selector = EndgameStrategySelector(self.config)
        except ImportError:
            self.strategy_selector = None
    
    def handle(self, message: Dict) -> int:
        """残局后期策略：全力冲刺，一手出完优先，快速结束"""
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        
        if not action_list:
            return 0
        
        my_rest = len(handcards) if handcards else 27
        
        # 优先级1: 一手出完（残局最重要）
        one_hand_idx = self._check_one_hand_complete(action_list, handcards)
        if one_hand_idx is not None:
            return one_hand_idx
        
        # ⭐ 使用优先级系统（提升：动态优先级，残局后期优先一手出完）
        context = self._build_context(message)
        if self.priority_system:
            # 获取手牌结构（简化实现）
            hand_structure = {}
            candidates = [a for a in action_list if a[0] != "PASS"]
            if candidates:
                return self.priority_system.select(candidates, hand_structure, context)
        
        # 优先级2: 使用残局策略类（提升：智能策略选择，残局后期更激进）
        context = self._build_context(message)
        state = self._extract_game_state(message)
        context.update({
            'my_remain': my_rest,
            'teammate_rest_cards': state.get('teammate_rest_cards', 27),
            'opponent_rest_cards_list': state.get('opponent_rest_cards_list', [27, 27, 27, 27])
        })
        
        if self.strategy_selector:
            strategy = self.strategy_selector.select_strategy(message, context)
            strategy_result = strategy.execute(message, context)
            if strategy_result is not None and 0 <= strategy_result < len(action_list):
                return strategy_result
        
        # 降级方案：使用原有残局策略函数
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
        opponent_rest_cards_list = [27, 27, 27, 27]  # 修复：初始化为4个元素（对应4个玩家）
        teammate_rest_cards = 27
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", 27)
                    if i < len(opponent_rest_cards_list):  # 添加边界检查，防止索引越界
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
        
        # 构建上下文信息
        context = self._build_context(message)
        
        # ⭐ 使用队友保护策略（提升：多策略组合，残局后期最重要）
        if self.teammate_protection:
            protection_action = self.teammate_protection.get_protection_action(message, context)
            if protection_action is not None:
                return protection_action
        
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
            if isinstance(action, list) and len(action) > 0 and action[0] == cur_action_type:
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

