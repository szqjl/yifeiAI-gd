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
from .optimal_combination_scanner import OptimalCombinationScanner, find_excess_singles_for_passive_play


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
        
        # ⚠️ 先构建上下文信息（包含手牌信息）
        context = self._build_context(message)
        
        # ⚠️ 出牌前扫描手牌最优组合 - 使用context中的手牌信息
        scan_result = self._scan_hand_combination(message, context)
        excess_singles = scan_result.get('excess_singles', [])
        combination_score = scan_result.get('combination_score', 0.0)
        
        # 将扫描结果添加到context中，供优先级系统使用
        context['scan_result'] = scan_result
        context['excess_singles'] = excess_singles
        context['combination_score'] = combination_score
        
        if excess_singles:
            logger.debug(f"多余单张列表: {excess_singles}")
        
        # ⭐ 使用优先级系统（提升：动态优先级）
        if self.priority_system:
            # 获取手牌结构（使用HandStructureAnalyzer）
            hand_structure = {}
            if hasattr(self, 'hand_analyzer') and self.hand_analyzer:
                handcards = message.get("handCards", [])
                rank = message.get("curRank", "2")
                hand_structure = self.hand_analyzer.analyze(handcards, rank)
            # 过滤PASS动作，同时记录原始索引，并验证卡牌一致性
            candidates = []
            candidate_indices = []
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0:
                    if action[0] != "PASS":
                        # ⚠️ 卡牌一致性检查：验证动作中的卡牌是否在手牌中
                        if self._validate_action_cards(action, handcards):
                            candidates.append(action)
                            candidate_indices.append(i)
                        else:
                            logger.warning(f"Action {i} contains cards not in handcards, skipping: {action}")
                elif action != "PASS":
                    candidates.append(action)
                    candidate_indices.append(i)
            
            logger.debug(f"Filtered {len(candidates)} candidates from {len(action_list)} actions (after card validation)")
            
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
                # 选择最小的单张（验证卡牌一致性）
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                        if self._validate_action_cards(action, handcards):
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
        
        # ⚠️ 修复：即使策略建议"不出单"，也应该尝试找能压制的单张
        # 策略建议只是参考，实际决策应该基于手牌和actionList
        strategy_suggests_no_single = '不出单' in single_sugg.get('action', '')
        if strategy_suggests_no_single:
            logger.info("Strategy suggests not playing single, but will still try to find valid actions")
        
        # ⚠️ 优先级1：使用多余单张（最高优先级）
        handcards = message.get("handCards", [])
        rank = message.get("curRank", "2")
        cur_action_rank = action_rank if action_rank else ""
        
        if cur_action_rank and hasattr(self, 'combination_scanner') and self.combination_scanner:
            try:
                excess_singles = find_excess_singles_for_passive_play(handcards, rank, cur_action_rank)
                if excess_singles:
                    logger.info(f"发现多余单张，可以顺走: {excess_singles}")
                    # 在actionList中查找这些多余单张
                    for excess_card in excess_singles:
                        for i, action in enumerate(action_list):
                            if isinstance(action, list) and len(action) > 0:
                                if action[0] == 'Single':
                                    # 检查是否是多余单张
                                    if len(action) >= 3 and isinstance(action[2], list):
                                        if excess_card in action[2]:
                                            # 验证卡牌一致性
                                            if self._validate_action_cards(action, handcards):
                                                logger.info(f"选择多余单张 {excess_card} 顺走: action={action}")
                                                return i
            except Exception as e:
                logger.warning(f"扫描多余单张时出错: {e}")
        
        # ⚠️ 优先级2：如果10以上没有极差的对子较多，则拆对子，压制对手的单张
        # 检查手牌中是否有10以上的对子（T=10, J, Q, K, A）
        from collections import Counter
        handcard_counts = Counter(handcards)
        
        # 10以上的牌值：T(10), J(11), Q(12), K(13), A(14)
        high_ranks = ['T', 'J', 'Q', 'K', 'A']
        high_pairs = []  # 存储10以上的对子
        
        for rank_char in high_ranks:
            # 统计该点数的牌数
            rank_count = sum(1 for card in handcards if len(card) >= 2 and card[1] == rank_char)
            if rank_count >= 2:  # 有对子
                high_pairs.append(rank_char)
        
        # 如果有10以上的对子，可以拆对子来压制
        if high_pairs:
            logger.info(f"发现10以上的对子: {high_pairs}")
            # 优先拆J、K对子（中等大小，不会太浪费）
            preferred_ranks = ['J', 'K', 'Q', 'T', 'A']  # 优先级：J > K > Q > T > A
            
            for preferred_rank in preferred_ranks:
                if preferred_rank in high_pairs:
                    # 在actionList中查找拆该对子的单张动作，并确保能压制对手
                    for i, action in enumerate(action_list):
                        if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                            if len(action) > 1:
                                action_rank_str = action[1]
                                # 检查是否是拆该对子的单张，并且能压制对手
                                if action_rank_str == preferred_rank:
                                    # 验证卡牌一致性
                                    if self._validate_action_cards(action, handcards):
                                        # 确保能压制对手的牌
                                        if cur_action_rank:
                                            cur_rank_value = self._get_rank_value(cur_action_rank, state['cur_rank'])
                                            action_rank_value = self._get_rank_value(action_rank_str, state['cur_rank'])
                                            if action_rank_value > cur_rank_value:
                                                logger.info(f"拆{preferred_rank}对子压制: {action_rank_str} > {cur_action_rank}")
                                                return i
                                        else:
                                            logger.info(f"拆{preferred_rank}对子压制: {action_rank_str}")
                                            return i
        
        # ⚠️ 优先级3：使用级牌/王压制（后期阻击对手或者自己冲刺）
        # 只在后期阶段（endgame）使用级牌/王
        my_rest = len(handcards) if handcards else 27
        is_endgame = my_rest <= 10  # 剩余牌数≤10认为是后期
        
        if is_endgame:
            level_card_rank = rank
            joker_small = 'B'
            joker_big = 'R'
            
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    if len(action) > 1:
                        action_rank_str = action[1]
                        # 检查是否是级牌、小王、大王
                        if action_rank_str == level_card_rank or action_rank_str == joker_small or action_rank_str == joker_big:
                            # 验证卡牌一致性
                            if self._validate_action_cards(action, handcards):
                                logger.info(f"后期使用级牌/王压制: {action_rank_str}")
                                return i
        
        # ⚠️ 优先级4：其他能压制的单张（避免拆三张或拆炸弹）
        logger.info("Searching for Single actions in actionList")
        single_count = 0
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0:
                if action[0] == 'Single':
                    single_count += 1
                    # 验证卡牌一致性
                    if not self._validate_action_cards(action, handcards):
                        logger.warning(f"Single action at index {i} failed card validation: {action}")
                        continue
                    
                    # ⚠️ 检查是否是拆牌（如果是拆三张或拆炸弹，跳过）
                    action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
                    is_split = False
                    for card in action_cards:
                        if len(card) >= 2:
                            # 统计该点数（rank）的牌数，而不是单张卡牌的数量
                            card_rank = card[1] if len(card) == 2 else card[1:]
                            # 统计手牌中该点数的牌数
                            rank_count = sum(1 for hc in handcards if len(hc) >= 2 and hc[1] == card_rank)
                            if rank_count >= 3:  # 拆三张或拆炸弹
                                is_split = True
                                logger.warning(f"Single action at index {i} would split trips/bomb (rank {card_rank} has {rank_count} cards): {action}")
                                break
                    
                    if not is_split:  # 不是拆三张或拆炸弹，可以使用
                        # ⚠️ 额外检查：确保能压制对手的牌
                        if cur_action_rank:
                            action_rank = action[1] if len(action) > 1 else ""
                            if action_rank:
                                cur_rank_value = self._get_rank_value(cur_action_rank, state['cur_rank'])
                                action_rank_value = self._get_rank_value(action_rank, state['cur_rank'])
                                if action_rank_value > cur_rank_value:
                                    logger.info(f"Found valid Single action to beat opponent: index={i}, action={action}, rank={action_rank} > {cur_action_rank}")
                                    return i
                                else:
                                    logger.debug(f"Single action at index {i} cannot beat opponent: {action_rank} <= {cur_action_rank}")
                        else:
                            # 如果没有cur_action_rank，直接返回（可能是主动出牌场景）
                            logger.info(f"Found valid Single action at index {i}: {action}")
                            return i
            elif isinstance(action, str) and action == 'Single':
                single_count += 1
                logger.info(f"Found Single action (string) at index {i}")
                return i
        
        logger.warning(f"No valid Single action found in actionList (checked {len(action_list)} actions, found {single_count} Single actions)")
        logger.info(f"First 10 actions in actionList: {action_list[:10] if len(action_list) >= 10 else action_list}")
        
        # ⚠️ 修复：即使找不到合适的单张，也应该尝试其他能压制的牌型，而不是直接PASS
        # 检查是否有其他能压制的牌型（对子、三张等）
        cur_action = message.get("curAction", [])
        cur_type = cur_action[0] if isinstance(cur_action, list) and len(cur_action) > 0 else ""
        cur_rank = cur_action[1] if isinstance(cur_action, list) and len(cur_action) > 1 else ""
        
        # 尝试找能压制的其他牌型（同类型但更大的牌）
        if cur_type and cur_rank and cur_type != "PASS":
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0:
                    if action[0] == cur_type and action[0] != "PASS":
                        if len(action) > 1:
                            action_rank = action[1]
                            # 使用_get_rank_value比较牌点大小
                            cur_rank_value = self._get_rank_value(cur_rank, state['cur_rank'])
                            action_rank_value = self._get_rank_value(action_rank, state['cur_rank'])
                            if action_rank_value > cur_rank_value:
                                if self._validate_action_cards(action, handcards):
                                    logger.info(f"Found valid {cur_type} action to beat opponent: index={i}, action={action}")
                                    return i
        
        # 最后尝试默认动作（选择第一个非PASS动作）
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
        
        # ⚠️ 先构建上下文信息（包含手牌信息）
        context = self._build_context(message)
        
        # ⚠️ 出牌前扫描手牌最优组合（中期阶段）- 使用context中的手牌信息
        scan_result = self._scan_hand_combination(message, context)
        excess_singles = scan_result.get('excess_singles', [])
        combination_score = scan_result.get('combination_score', 0.0)
        
        # 将扫描结果添加到context中，供优先级系统使用
        context['scan_result'] = scan_result
        context['excess_singles'] = excess_singles
        context['combination_score'] = combination_score
        
        # 检查两手出完
        two_hand_idx = self._check_two_hand_complete(action_list, handcards)
        if two_hand_idx is not None:
            return two_hand_idx
        
        # 如果有多余单张，优先考虑出单张（顺走多余单张）
        if excess_singles:
            import logging
            logger = logging.getLogger("MidEarlyActiveHandler")
            logger.debug(f"检测到{len(excess_singles)}张多余单张，优先考虑出单张: {excess_singles}")
            # 优先选择单张动作
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    if len(action) > 1 and action[1] in excess_singles:
                        logger.debug(f"选择多余单张: {action[1]}")
                        return i
            # 如果没有匹配的多余单张，至少优先出单张
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    return i
        
        # ⭐ 使用优先级系统（提升：动态优先级）
        if self.priority_system:
            # 获取手牌结构（使用HandStructureAnalyzer）
            hand_structure = {}
            if hasattr(self, 'hand_analyzer') and self.hand_analyzer:
                handcards = message.get("handCards", [])
                rank = message.get("curRank", "2")
                hand_structure = self.hand_analyzer.analyze(handcards, rank)
            # 过滤PASS动作，同时记录原始索引，并验证卡牌一致性
            candidates = []
            candidate_indices = []
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0:
                    if action[0] != "PASS":
                        # ⚠️ 卡牌一致性检查：验证动作中的卡牌是否在手牌中
                        if self._validate_action_cards(action, handcards):
                            candidates.append(action)
                            candidate_indices.append(i)
                        else:
                            logger.warning(f"Action {i} contains cards not in handcards, skipping: {action}")
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
                        # ⚠️ 验证卡牌一致性
                        if self._validate_action_cards(action, handcards):
                            return i
        
        # 常规优先级：对子 → 三张 → 单张 → 其他
        priority_order = ['Pair', 'Trips', 'Single', 'ThreeWithTwo', 
                         'ThreePair', 'TwoTrips', 'Straight']
        
        for card_type in priority_order:
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == card_type:
                    # ⚠️ 验证卡牌一致性
                    if self._validate_action_cards(action, handcards):
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
        """处理单张被动出牌（中期：更积极压制对手）"""
        import logging
        logger = logging.getLogger("MidEarlyPassiveHandler")
        
        cur_action = message.get("curAction", [])
        action_rank = cur_action[1] if len(cur_action) > 1 else ""
        
        # 获取当前级牌
        cur_rank = message.get("curRank", "2")
        handcards = message.get("handCards", [])
        
        # ⚠️ 优先级1：使用多余单张（最高优先级）
        suitable_singles = self._find_excess_singles_for_action(message, action_rank)
        if suitable_singles:
            logger.debug(f"找到{len(suitable_singles)}张可顺走的多余单张: {suitable_singles}")
            # 优先选择多余单张中能压制的
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    if len(action) > 1 and action[1] in suitable_singles:
                        # 验证卡牌一致性
                        if self._validate_action_cards(action, handcards):
                            logger.debug(f"选择多余单张压制: {action[1]}")
                            return i
        
        # ⚠️ 优先级2：如果10以上没有极差的对子较多，则拆对子，压制对手的单张
        # 检查手牌中是否有10以上的对子（T=10, J, Q, K, A）
        from collections import Counter
        handcard_counts = Counter(handcards)
        
        # 10以上的牌值：T(10), J(11), Q(12), K(13), A(14)
        high_ranks = ['T', 'J', 'Q', 'K', 'A']
        high_pairs = []  # 存储10以上的对子
        
        for rank_char in high_ranks:
            # 统计该点数的牌数
            rank_count = sum(1 for card in handcards if len(card) >= 2 and card[1] == rank_char)
            if rank_count >= 2:  # 有对子
                high_pairs.append(rank_char)
        
        # 如果有10以上的对子，可以拆对子来压制
        if high_pairs:
            logger.debug(f"发现10以上的对子: {high_pairs}")
            # 优先拆J、K对子（中等大小，不会太浪费）
            preferred_ranks = ['J', 'K', 'Q', 'T', 'A']  # 优先级：J > K > Q > T > A
            
            for preferred_rank in preferred_ranks:
                if preferred_rank in high_pairs:
                    # 在actionList中查找拆该对子的单张动作
                    for i, action in enumerate(action_list):
                        if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                            if len(action) > 1:
                                action_rank_str = action[1]
                                # 检查是否是拆该对子的单张
                                if action_rank_str == preferred_rank:
                                    # 验证是否能压制
                                    action_rank_val = self._get_rank_value(action_rank_str, cur_rank)
                                    cur_rank_val = self._get_rank_value(action_rank, cur_rank)
                                    if action_rank_val > cur_rank_val:
                                        # 验证卡牌一致性
                                        if self._validate_action_cards(action, handcards):
                                            logger.debug(f"拆{preferred_rank}对子压制: {action_rank_str}")
                                            return i
        
        # ⚠️ 优先级3：使用级牌/王压制（后期阻击对手或者自己冲刺）
        # 只在后期阶段（endgame）使用级牌/王
        my_rest = len(handcards) if handcards else 27
        is_endgame = my_rest <= 10  # 剩余牌数≤10认为是后期
        
        if is_endgame:
            level_card_rank = cur_rank
            joker_small = 'B'
            joker_big = 'R'
            
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    if len(action) > 1:
                        action_rank_str = action[1]
                        # 检查是否是级牌、小王、大王
                        if action_rank_str == level_card_rank or action_rank_str == joker_small or action_rank_str == joker_big:
                            # 验证是否能压制
                            action_rank_val = self._get_rank_value(action_rank_str, cur_rank)
                            cur_rank_val = self._get_rank_value(action_rank, cur_rank)
                            if action_rank_val > cur_rank_val:
                                # 验证卡牌一致性
                                if self._validate_action_cards(action, handcards):
                                    logger.debug(f"后期使用级牌/王压制: {action_rank_str}")
                                    return i
        
        # ⚠️ 优先级4：其他能压制的单张（避免拆三张或拆炸弹）
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                if len(action) > 1:
                    # 验证卡牌一致性
                    if not self._validate_action_cards(action, handcards):
                        continue
                    # 比较牌值（支持字符串和数字比较，考虑级牌）
                    action_rank_val = self._get_rank_value(action[1], cur_rank)
                    cur_rank_val = self._get_rank_value(action_rank, cur_rank)
                    if action_rank_val > cur_rank_val:
                        # ⚠️ 检查是否是拆牌（如果是拆三张或拆炸弹，降低优先级）
                        action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
                        is_split = False
                        for card in action_cards:
                            if len(card) >= 2:
                                card_rank = card[1] if len(card) == 2 else card[1:]
                                card_count = handcard_counts.get(card, 0)
                                if card_count >= 3:  # 拆三张或拆炸弹
                                    is_split = True
                                    logger.warning(f"Single action at index {i} would split trips/bomb: {action}")
                                    break
                        
                        if not is_split:  # 不是拆三张或拆炸弹，可以使用
                            return i
        
        # 如果没有能压制的单张，再考虑策略建议
        if self.single_strategy:
            is_upper_hand = (greater_pos == (my_pos - 1) % 4) or (greater_pos == (my_pos + 3) % 4)
            single_sugg = self.single_strategy(
                game_phase='mid',
                power=state['power'],
                opponent_rest_cards=min(state['opponent_rest_cards_list']),
                is_active=False,
                is_upper_hand=is_upper_hand,
                my_rest_cards=state['my_rest']
            )
            
            # 如果策略明确建议不出单，且没有能压制的动作，才PASS
            if '不出单' in single_sugg.get('action', '') and '主动时不出小单' in single_sugg.get('action', ''):
                return 0
        
        # 降级：选择第一个能压制的动作（即使不是最优）
        return self._default_passive_action(action_list)
    
    def _get_rank_value(self, rank: str, cur_rank: str = None) -> int:
        """
        获取牌值（用于比较）
        
        牌值大小关系：
        - 3-9, T, J, Q, K, A: 3-14
        - 级牌: 15 (可压制A及以下)
        - 小王(B): 16 (可压制级牌及以下)
        - 大王(R): 17 (可压制小王及以下)
        
        Args:
            rank: 牌值字符串（如"A"、"9"、"B"、"R"等，或带花色的如"S9"、"HA"等）
            cur_rank: 当前级牌（如"2"、"9"等），如果提供则用于识别级牌
        """
        rank_map = {
            '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
            '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14,
            'B': 16,  # 小王（可压制级牌及以下）
            'R': 17   # 大王（可压制小王及以下）
        }
        if isinstance(rank, str):
            # 提取最后一位字符（去掉花色）
            rank_char = rank[-1] if len(rank) > 1 else rank
            
            # 如果提供了cur_rank，检查是否是级牌
            if cur_rank and rank_char == cur_rank:
                return 15  # 级牌值（可压制A及以下）
            
            # 检查是否在映射中
            if rank_char in rank_map:
                return rank_map[rank_char]
            
            # 如果不在映射中，可能是级牌（但cur_rank未提供），默认返回15
            # 注意：这里假设如果cur_rank未提供，可能是级牌2
            if not cur_rank and rank_char == '2':
                return 15
            
            return 0
        return int(rank) if isinstance(rank, (int, float)) else 0
    
    def _handle_pair_passive(self, message: Dict, action_list: List, state: Dict, greater_pos: int, my_pos: int) -> int:
        """处理对子被动出牌（中期：对手出牌时积极压制）"""
        cur_action = message.get("curAction", [])
        action_rank = cur_action[1] if len(cur_action) > 1 else ""
        is_teammate = self._is_teammate(greater_pos, my_pos)
        
        # 如果是队友出对子，让过
        if is_teammate:
            return 0
        
        # 获取当前级牌
        cur_rank = message.get("curRank", "2")
        
        # 对手出对子：中期阶段应该积极压制
        # 先检查是否有能压制的对子
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == 'Pair':
                if len(action) > 1:
                    # 比较牌值（考虑级牌）
                    action_rank_val = self._get_rank_value(action[1], cur_rank)
                    cur_rank_val = self._get_rank_value(action_rank, cur_rank)
                    if action_rank_val > cur_rank_val:
                        # 中期阶段：有能压制的对子就压制
                        return i
        
        # 如果没有能压制的对子，再考虑策略建议
        if self.pair_strategy:
            pair_sugg = self.pair_strategy(
                game_phase='mid',
                power=state['power'],
                opponent_rest_cards=min(state['opponent_rest_cards_list']),
                is_active=False,
                is_teammate_action=is_teammate,
                action_type='Pair',
                action_rank=action_rank
            )
            
            # 策略建议"封对手对子"时，即使没有能压制的对子，也要尝试其他方式
            if '封对手对子' in pair_sugg.get('action', ''):
                # 尝试使用炸弹或其他方式压制
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0:
                        if action[0] == 'Bomb':
                            # 中期阶段谨慎使用炸弹，但必要时可以使用
                            if state['power'] >= 6:
                                return i
        
        # 降级：选择第一个非PASS动作
        return self._default_passive_action(action_list)
    
    def _handle_other_passive(self, message: Dict, action_list: List, state: Dict) -> int:
        """处理其他牌型被动出牌（中期：更积极压制）"""
        cur_action = message.get("curAction", [])
        cur_type = cur_action[0] if len(cur_action) > 0 else ""
        cur_rank = cur_action[1] if len(cur_action) > 1 else ""
        
        # 中期阶段：降低牌力阈值，更积极压制
        # 如果牌力非常弱（< 3），才考虑PASS
        if state['power'] < 3:
            return 0
        
        # 获取当前级牌
        cur_rank_param = message.get("curRank", "2")
        
        # 优先寻找能压制的同类型动作
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == cur_type:
                if len(action) > 1:
                    # 比较牌值（考虑级牌）
                    action_rank_val = self._get_rank_value(action[1], cur_rank_param)
                    cur_rank_val = self._get_rank_value(cur_rank, cur_rank_param)
                    if action_rank_val > cur_rank_val:
                        return i
        
        # 如果没有同类型能压制的，考虑使用炸弹（中期谨慎使用）
        if state['power'] >= 6:
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Bomb':
                    # 中期阶段：只有在牌力较强且对手威胁大时才用炸弹
                    return i
        
        # 降级：选择第一个非PASS动作
        return self._default_passive_action(action_list)
    
    def _default_passive_action(self, action_list: List) -> int:
        """默认被动动作选择（选择第一个非PASS动作）"""
        import logging
        logger = logging.getLogger("MidEarlyPassiveHandler")
        
        # 选择第一个非PASS动作（中期阶段应该更积极）
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0:
                if action[0] != "PASS":
                    logger.debug(f"Found non-PASS action at index {i}: {action[0]}")
                    return i
            elif action != "PASS":
                logger.debug(f"Found non-PASS action at index {i}: {action}")
                return i
        
        logger.warning(f"No non-PASS actions found, returning 0 (PASS)")
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
        
        # ⚠️ 先构建上下文信息（包含手牌信息）
        context = self._build_context(message)
        
        # ⚠️ 出牌前扫描手牌最优组合（中期后期阶段）- 使用context中的手牌信息
        scan_result = self._scan_hand_combination(message, context)
        excess_singles = scan_result.get('excess_singles', [])
        combination_score = scan_result.get('combination_score', 0.0)
        
        # 将扫描结果添加到context中，供优先级系统使用
        context['scan_result'] = scan_result
        context['excess_singles'] = excess_singles
        context['combination_score'] = combination_score
        
        # 检查一手出完
        one_hand_idx = self._check_one_hand_complete(action_list, handcards)
        if one_hand_idx is not None:
            return one_hand_idx
        
        # 检查两手出完
        two_hand_idx = self._check_two_hand_complete(action_list, handcards)
        if two_hand_idx is not None:
            return two_hand_idx
        
        # 如果有多余单张，优先考虑出单张（顺走多余单张）
        if excess_singles:
            import logging
            logger = logging.getLogger("MidLateActiveHandler")
            logger.debug(f"检测到{len(excess_singles)}张多余单张，优先考虑出单张: {excess_singles}")
            # 优先选择单张动作
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    if len(action) > 1 and action[1] in excess_singles:
                        logger.debug(f"选择多余单张: {action[1]}")
                        return i
            # 如果没有匹配的多余单张，至少优先出单张
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    return i
        
        # ⭐ 使用优先级系统（提升：动态优先级）
        if self.priority_system:
            # 获取手牌结构（使用HandStructureAnalyzer）
            hand_structure = {}
            if hasattr(self, 'hand_analyzer') and self.hand_analyzer:
                handcards = message.get("handCards", [])
                rank = message.get("curRank", "2")
                hand_structure = self.hand_analyzer.analyze(handcards, rank)
            # 过滤PASS动作，同时记录原始索引，并验证卡牌一致性
            candidates = []
            candidate_indices = []
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0:
                    if action[0] != "PASS":
                        # ⚠️ 卡牌一致性检查：验证动作中的卡牌是否在手牌中
                        if self._validate_action_cards(action, handcards):
                            candidates.append(action)
                            candidate_indices.append(i)
                        else:
                            logger.warning(f"Action {i} contains cards not in handcards, skipping: {action}")
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
        
        # 中局后期更积极：降低牌力阈值，更倾向于压制
        # 牌力阈值从5降低到3，更积极压制对手
        if state['power'] >= 3:
            # 调用父类方法，但更倾向于压制
            return super().handle(message)
        else:
            # 牌力非常弱（< 3），才让过
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
        
        # ⚠️ 先构建上下文信息（包含手牌信息）
        context = self._build_context(message)
        
        # ⚠️ 出牌前扫描手牌最优组合（残局前期阶段）- 使用context中的手牌信息
        scan_result = self._scan_hand_combination(message, context)
        excess_singles = scan_result.get('excess_singles', [])
        combination_score = scan_result.get('combination_score', 0.0)
        
        # 将扫描结果添加到context中，供优先级系统使用
        context['scan_result'] = scan_result
        context['excess_singles'] = excess_singles
        context['combination_score'] = combination_score
        
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
        
        # 如果有多余单张，优先考虑出单张（残局阶段快速减少牌数）
        if excess_singles:
            import logging
            logger = logging.getLogger("EndgameEarlyActiveHandler")
            logger.debug(f"检测到{len(excess_singles)}张多余单张，优先考虑出单张: {excess_singles}")
            # 优先选择单张动作
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    if len(action) > 1 and action[1] in excess_singles:
                        logger.debug(f"选择多余单张: {action[1]}")
                        return i
            # 如果没有匹配的多余单张，至少优先出单张
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    return i
        else:
            # 回退到基类方法
            one_hand_idx = self._check_one_hand_complete(action_list, handcards)
        if one_hand_idx is not None:
            return one_hand_idx
        
        # ⭐ 使用优先级系统（提升：动态优先级，残局阶段）
        context = self._build_context(message)
        if self.priority_system:
            # 获取手牌结构（使用HandStructureAnalyzer）
            hand_structure = {}
            if hasattr(self, 'hand_analyzer') and self.hand_analyzer:
                handcards = message.get("handCards", [])
                rank = message.get("curRank", "2")
                hand_structure = self.hand_analyzer.analyze(handcards, rank)
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
        
        # ⚠️ 如果是单张，按照新的优先级顺序处理
        cur_action_type = cur_action[0] if isinstance(cur_action, list) and len(cur_action) > 0 else ""
        cur_rank = cur_action[1] if len(cur_action) > 1 else ""
        
        if cur_action_type == 'Single':
            import logging
            logger = logging.getLogger("EndgameEarlyPassiveHandler")
            cur_rank_val = self._get_rank_value(cur_rank, message.get("curRank", "2")) if hasattr(self, '_get_rank_value') else 0
            
            # ⚠️ 优先级1：使用多余单张（最高优先级）
            suitable_singles = self._find_excess_singles_for_action(message, cur_rank)
            if suitable_singles:
                logger.debug(f"找到{len(suitable_singles)}张可顺走的多余单张: {suitable_singles}")
                # 优先选择多余单张中能压制的
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                        if len(action) > 1 and action[1] in suitable_singles:
                            if self._validate_action_cards(action, handcards):
                                logger.debug(f"选择多余单张压制: {action[1]}")
                                return i
            
            # ⚠️ 优先级2：如果10以上没有极差的对子较多，则拆对子，压制对手的单张
            from collections import Counter
            handcard_counts = Counter(handcards)
            high_ranks = ['T', 'J', 'Q', 'K', 'A']
            high_pairs = []
            
            for rank_char in high_ranks:
                rank_count = sum(1 for card in handcards if len(card) >= 2 and card[1] == rank_char)
                if rank_count >= 2:
                    high_pairs.append(rank_char)
            
            if high_pairs:
                logger.debug(f"发现10以上的对子: {high_pairs}")
                preferred_ranks = ['J', 'K', 'Q', 'T', 'A']
                
                for preferred_rank in preferred_ranks:
                    if preferred_rank in high_pairs:
                        for i, action in enumerate(action_list):
                            if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                                if len(action) > 1:
                                    action_rank_str = action[1]
                                    if action_rank_str == preferred_rank:
                                        action_rank_val = self._get_rank_value(action_rank_str, message.get("curRank", "2")) if hasattr(self, '_get_rank_value') else 0
                                        if action_rank_val > cur_rank_val:
                                            if self._validate_action_cards(action, handcards):
                                                logger.debug(f"拆{preferred_rank}对子压制: {action_rank_str}")
                                                return i
            
            # ⚠️ 优先级3：使用级牌/王压制（残局阶段，可以直接用级牌或王压制）
            level_card_rank = message.get("curRank", "2")
            joker_small = 'B'
            joker_big = 'R'
            
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    if len(action) > 1:
                        action_rank_str = action[1]
                        if action_rank_str == level_card_rank or action_rank_str == joker_small or action_rank_str == joker_big:
                            action_rank_val = self._get_rank_value(action_rank_str, level_card_rank) if hasattr(self, '_get_rank_value') else 0
                            if action_rank_val > cur_rank_val:
                                if self._validate_action_cards(action, handcards):
                                    logger.debug(f"残局使用级牌/王压制: {action_rank_str}")
                                    return i
        
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
        
        # ⚠️ 先构建上下文信息（包含手牌信息）
        context = self._build_context(message)
        
        # ⚠️ 出牌前扫描手牌最优组合（残局后期阶段）- 使用context中的手牌信息
        scan_result = self._scan_hand_combination(message, context)
        excess_singles = scan_result.get('excess_singles', [])
        combination_score = scan_result.get('combination_score', 0.0)
        
        # 将扫描结果添加到context中，供优先级系统使用
        context['scan_result'] = scan_result
        context['excess_singles'] = excess_singles
        context['combination_score'] = combination_score
        
        my_rest = len(handcards) if handcards else 27
        
        # 优先级1: 一手出完（残局最重要）
        one_hand_idx = self._check_one_hand_complete(action_list, handcards)
        if one_hand_idx is not None:
            return one_hand_idx
        
        # 如果有多余单张，优先考虑出单张（残局后期快速减少牌数）
        if excess_singles:
            import logging
            logger = logging.getLogger("EndgameLateActiveHandler")
            logger.debug(f"检测到{len(excess_singles)}张多余单张，优先考虑出单张: {excess_singles}")
            # 优先选择单张动作
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    if len(action) > 1 and action[1] in excess_singles:
                        logger.debug(f"选择多余单张: {action[1]}")
                        return i
            # 如果没有匹配的多余单张，至少优先出单张
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    return i
        
        # ⭐ 使用优先级系统（提升：动态优先级，残局后期优先一手出完）
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

