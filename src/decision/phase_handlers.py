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
try:
    from game_logic.guandan_constants import CARDS_PER_PLAYER, DEFAULT_REST_CARDS, DEFAULT_ALL_REST_LIST
except ImportError:
    CARDS_PER_PLAYER = 27
    DEFAULT_REST_CARDS = 27
    DEFAULT_ALL_REST_LIST = [27, 27, 27, 27]

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
        my_rest = len(handcards) if handcards else CARDS_PER_PLAYER
        opponent_rest_cards_list = list(DEFAULT_ALL_REST_LIST)
        teammate_rest_cards = DEFAULT_REST_CARDS
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", DEFAULT_REST_CARDS)
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
        context['is_passive'] = False  # 主动出牌
        
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
            # ⚠️ 关键修复：先获取扫描结果，作为硬约束
            scan_result = context.get('scan_result', {})
            protected_combinations = scan_result.get('protected_combinations', [])
            excess_singles = context.get('excess_singles', [])
            
            # 过滤PASS动作，同时记录原始索引，并验证卡牌一致性
            # ⚠️ 硬约束：禁止破坏受保护组合
            candidates = []
            candidate_indices = []
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0:
                    if action[0] != "PASS":
                        # 1. 卡牌一致性检查（opening阶段：即使验证失败也保留，让路由层做最终决定）
                        validation_passed = self._validate_action_cards(action, handcards)
                        if not validation_passed:
                            logger.warning(f"Action {i} failed card validation, but in opening phase, will still consider it: {action}")
                            # ⚠️ opening阶段：放宽验证，避免过度过滤导致所有动作被拒绝
                        
                        # 2. ⚠️ 硬约束：检查是否会破坏受保护组合（但只在验证通过时检查）
                        action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
                        if action_cards and protected_combinations and validation_passed:
                            # ⚠️ 修复：展平嵌套列表，确保所有元素都是字符串（可哈希）
                            def flatten_cards(cards):
                                """展平卡牌列表，处理嵌套列表"""
                                result = []
                                for card in cards:
                                    if isinstance(card, list):
                                        result.extend(flatten_cards(card))
                                    elif isinstance(card, str):
                                        result.append(card)
                                return result
                            
                            action_cards_flat = flatten_cards(action_cards)
                            action_cards_set = set(action_cards_flat)
                            would_break = False
                            for protected in protected_combinations:
                                if isinstance(protected, list):
                                    protected_flat = flatten_cards(protected)
                                    protected_set = set(protected_flat)
                                    # 如果动作中的卡牌与受保护组合有交集，且不是完整使用，就是破坏
                                    if action_cards_set & protected_set:
                                        if not action_cards_set.issubset(protected_set):
                                            would_break = True
                                            logger.warning(f"Action {i} would break protected combination, skipping: {action}")
                                            break
                            if would_break:
                                continue
                        
                        # ⚠️ 即使验证失败，也添加到候选列表（opening阶段更宽松）
                        candidates.append(action)
                        candidate_indices.append(i)
                elif action != "PASS":
                    candidates.append(action)
                    candidate_indices.append(i)
            
            logger.debug(f"Filtered {len(candidates)} candidates from {len(action_list)} actions (opening phase: relaxed validation)")
            
            # ⚠️ 关键修复：如果有excess_singles，优先选择它们
            if excess_singles and candidates:
                excess_candidates = []
                excess_indices = []
                other_candidates = []
                other_indices = []
                
                for idx, candidate in enumerate(candidates):
                    action_cards = candidate[2] if isinstance(candidate, list) and len(candidate) > 2 and isinstance(candidate[2], list) else []
                    if action_cards and len(action_cards) == 1 and action_cards[0] in excess_singles:
                        excess_candidates.append(candidate)
                        excess_indices.append(candidate_indices[idx])
                    else:
                        other_candidates.append(candidate)
                        other_indices.append(candidate_indices[idx])
                
                # 优先使用excess_singles
                if excess_candidates:
                    candidates = excess_candidates + other_candidates
                    candidate_indices = excess_indices + other_indices
                    logger.info(f"Prioritized {len(excess_candidates)} excess_singles candidates")
            
            if candidates:
                try:
                    selected_candidate_idx = self.priority_system.select(candidates, hand_structure, context)
                    if 0 <= selected_candidate_idx < len(candidate_indices):
                        original_idx = candidate_indices[selected_candidate_idx]
                        logger.info(f"PrioritySystem selected: candidate_idx={selected_candidate_idx}, original_idx={original_idx}, action={candidates[selected_candidate_idx]}")
                        return original_idx
                    else:
                        logger.warning(f"PrioritySystem returned invalid index: {selected_candidate_idx}, max={len(candidate_indices)-1}, falling back to first candidate")
                        # 降级：返回第一个候选动作
                        if candidate_indices:
                            return candidate_indices[0]
                except Exception as e:
                    logger.error(f"PrioritySystem.select() error: {e}", exc_info=True)
                    # 降级：返回第一个候选动作
                    if candidate_indices:
                        logger.warning(f"Falling back to first candidate after PrioritySystem error")
                        return candidate_indices[0]
            else:
                logger.warning(f"No candidates after filtering PASS actions (total actions: {len(action_list)})")
                # ⚠️ 关键修复：即使candidates为空，也要尝试返回第一个非PASS动作
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                        logger.warning(f"Fallback: returning first non-PASS action at index {i} (card validation may have been too strict)")
                        return i
                    elif action != "PASS":
                        logger.warning(f"Fallback: returning first non-PASS action at index {i} (card validation may have been too strict)")
                        return i
        
        # ⚠️ 关键修复：在降级方案之前，再次尝试返回第一个非PASS动作
        # 如果candidates为空，说明所有动作都被过滤了，但actionList中可能有非PASS动作
        logger.warning(f"All candidates filtered, but actionList has {len(action_list)} actions, trying to return first non-PASS action before strategy fallback")
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                logger.warning(f"Pre-fallback: returning first non-PASS action at index {i} before strategy fallback: {action[0]}")
                return i
            elif action != "PASS":
                logger.warning(f"Pre-fallback: returning first non-PASS action at index {i} before strategy fallback: {action}")
                return i
        
        # 提取游戏状态（降级方案）
        state = self._extract_game_state(message)
        power = state['power']
        
        # ⚠️ 关键修复：确保scan_result和context在降级方案中也可用
        scan_result = context.get('scan_result', {}) if 'context' in locals() else {}
        protected_combinations = scan_result.get('protected_combinations', [])
        excess_singles = context.get('excess_singles', []) if 'context' in locals() else []
        
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
                # ⚠️ 优先选择excess_singles中的单张
                
                # 先找excess_singles
                if excess_singles:
                    for excess_card in excess_singles:
                        for i, action in enumerate(action_list):
                            if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                                action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
                                if action_cards and excess_card in action_cards:
                                    if self._validate_action_cards(action, handcards):
                                        # 检查是否破坏受保护组合（修复：展平嵌套列表）
                                        action_cards_flat = self._flatten_cards(action_cards)
                                        action_cards_set = set(action_cards_flat)
                                        would_break = False
                                        for prot in protected_combinations:
                                            if isinstance(prot, list):
                                                prot_flat = self._flatten_cards(prot)
                                                prot_set = set(prot_flat)
                                                if action_cards_set & prot_set and not action_cards_set.issubset(prot_set):
                                                    would_break = True
                                                    break
                                        if not would_break:
                                            return i
                
                # 降级：选择最小的单张（验证卡牌一致性，不破坏受保护组合）
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                        if self._validate_action_cards(action, handcards):
                            action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
                            # 检查是否破坏受保护组合（修复：展平嵌套列表）
                            action_cards_flat = self._flatten_cards(action_cards)
                            action_cards_set = set(action_cards_flat)
                            would_break = False
                            for prot in protected_combinations:
                                if isinstance(prot, list):
                                    prot_flat = self._flatten_cards(prot)
                                    prot_set = set(prot_flat)
                                    if action_cards_set & prot_set and not action_cards_set.issubset(prot_set):
                                        would_break = True
                                        break
                            if not would_break:
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
        
        # ⚠️ 关键修复：在返回0（PASS）之前，确保至少尝试返回第一个非PASS动作
        # 这可以防止在有可选动作时仍然PASS的问题
        import logging
        logger = logging.getLogger("OpeningActiveHandler")
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                logger.warning(f"Final fallback: returning first non-PASS action at index {i} (all strategies failed to find suitable action)")
                return i
        
        # 只有真的没有可选动作时才PASS
        logger.warning(f"No non-PASS actions available, returning PASS (index 0)")
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
            # ⚠️ 关键修复：如果第一个元素是"PASS"，说明上家已经PASS，这是主动出牌，不应该走被动出牌逻辑
            if cur_action[0] == "PASS":
                logger.warning(f"curAction is PASS: {cur_action}, this should be active play, not passive. Returning _default_passive_action to find first non-PASS action")
                # 即使curAction是PASS，如果actionList中有非PASS动作，也应该返回第一个非PASS动作
                return self._default_passive_action(action_list, message)
        
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
        
        # ⚠️ 关键修复：开局被动策略：队友出牌让过，但必须确保actionList中只有PASS动作时才PASS
        # 如果actionList中有非PASS动作，即使队友出牌，也应该考虑是否要出牌（比如队友出小牌，我们可以顺走）
        if is_teammate:
            # 检查actionList中是否有非PASS动作
            has_non_pass = False
            for action in action_list:
                if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                    has_non_pass = True
                    break
                elif action != "PASS":
                    has_non_pass = True
                    break
            
            if not has_non_pass:
                # 如果actionList中只有PASS，说明真的没有可选动作，让过
                logger.info("Teammate played, and actionList has only PASS actions, passing in opening phase")
                return 0  # PASS
            else:
                # 如果actionList中有非PASS动作，即使队友出牌，也应该考虑是否要出牌
                # 但开局阶段，如果队友出牌，通常让过（除非是特殊情况）
                logger.info(f"Teammate played, but actionList has {len(action_list)} actions (including non-PASS), will check if should play")
                # 继续执行后续逻辑，但可以降低优先级
        
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
        
        my_rest = len(handcards) if handcards else CARDS_PER_PLAYER
        opponent_rest_cards_list = list(DEFAULT_ALL_REST_LIST)
        teammate_rest_cards = DEFAULT_REST_CARDS
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", DEFAULT_REST_CARDS)
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
            return self._default_passive_action(action_list, message)
        
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
        
        # ⚠️ 关键修复：如果greater_pos是队友，不应该压制，直接PASS
        is_teammate = self._is_teammate(greater_pos, my_pos)
        if is_teammate:
            logger.info(f"Teammate (pos {greater_pos}) played single, should not suppress, passing")
            return 0  # PASS，不压制队友
        
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
        my_rest = len(handcards) if handcards else CARDS_PER_PLAYER
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
                            # ⚠️ 修复：即使没有cur_action_rank，也应该返回（Opening阶段更积极）
                            logger.info(f"Found valid Single action at index {i}: {action}")
                            return i
            elif isinstance(action, str) and action == 'Single':
                single_count += 1
                logger.info(f"Found Single action (string) at index {i}")
                return i
        
        logger.warning(f"No valid Single action found in actionList (checked {len(action_list)} actions, found {single_count} Single actions)")
        logger.info(f"First 10 actions in actionList: {action_list[:10] if len(action_list) >= 10 else action_list}")
        
        # ⚠️ 关键修复：即使找不到合适的单张，也应该尝试其他能压制的牌型，而不是直接PASS
        # 检查是否有其他能压制的牌型（对子、三张等）
        cur_action = message.get("curAction", [])
        cur_type = cur_action[0] if isinstance(cur_action, list) and len(cur_action) > 0 else ""
        cur_rank = cur_action[1] if isinstance(cur_action, list) and len(cur_action) > 1 else ""
        
        # ⚠️ 如果找不到单张，尝试找其他能压制的牌型
        if cur_type == 'Single' and cur_rank:
            cur_rank_value = self._get_rank_value(cur_rank, state['cur_rank'])
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                    if action[0] == cur_type:  # 同类型
                        action_rank = action[1] if len(action) > 1 else ""
                        if action_rank:
                            action_rank_value = self._get_rank_value(action_rank, state['cur_rank'])
                            if action_rank_value > cur_rank_value:
                                if self._validate_action_cards(action, handcards):
                                    logger.info(f"Found {action[0]} action to beat opponent: index={i}, rank={action_rank} > {cur_rank}")
                                    return i
        
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
        
        # ⚠️ 关键修复：Opening阶段，如果对手出高牌（R、B、A等）而我们只有小牌，也应该尝试出牌
        # 检查对手是否出的是高牌（R、B、A、K等）
        if cur_action_rank:
            high_ranks = ['R', 'B', 'A', 'K', 'Q']
            is_opponent_high_card = cur_action_rank in high_ranks
            
            if is_opponent_high_card:
                logger.info(f"Opponent played high card {cur_action_rank}, trying to find any valid action")
                # 尝试返回第一个有效的非PASS动作（即使不能压制）
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                        if self._validate_action_cards(action, handcards):
                            logger.info(f"Opponent high card, returning first valid action at index {i}: {action[0]}")
                            return i
        
        # 最后尝试默认动作（选择第一个有效的非PASS动作）
        result = self._default_passive_action(action_list, message)
        logger.info(f"_default_passive_action returned: {result}")
        return result
    
    def _handle_pair_passive(self, message: Dict, action_list: List, state: Dict, greater_pos: int, my_pos: int) -> int:
        """处理对子被动出牌"""
        if not self.pair_strategy:
            return self._default_passive_action(action_list, message)
        
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
        
        # ⚠️ 修复：即使策略建议让对子，也应该尝试其他方式，而不是直接PASS
        if '让对子' in pair_sugg.get('action', ''):
            import logging
            logger = logging.getLogger("OpeningPassiveHandler")
            handcards = message.get("handCards", [])
            logger.debug(f"Strategy suggests letting pair, but trying fallback")
            # 尝试返回第一个有效的非PASS动作（降级方案）
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                    # ⚠️ 修复：验证卡牌一致性，确保返回的动作是有效的
                    if self._validate_action_cards(action, handcards):
                        logger.debug(f"Strategy suggests letting but found valid non-PASS action at index {i}: {action[0]}")
                        return i
                    else:
                        logger.debug(f"Strategy suggests letting but action at index {i} failed card validation: {action[0]}")
            # 只有真的没有可选动作时才PASS
            logger.warning(f"Strategy suggests letting and no valid non-PASS actions available, returning PASS")
            return 0
        
        # 选择能压制的最小对子
        handcards = message.get("handCards", [])
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == 'Pair':
                if len(action) > 1 and action[1] > action_rank:
                    # ⚠️ 验证卡牌一致性
                    if self._validate_action_cards(action, handcards):
                        return i
        
        # ⚠️ 关键修复：在返回0（PASS）之前，确保至少尝试返回第一个有效的非PASS动作
        import logging
        logger = logging.getLogger("OpeningPassiveHandler")
        logger.warning(f"Cannot suppress Pair {action_rank}, trying fallback")
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                # ⚠️ 修复：验证卡牌一致性，确保返回的动作是有效的
                if self._validate_action_cards(action, handcards):
                    logger.warning(f"_handle_pair_passive fallback: returning first valid non-PASS action at index {i}: {action[0]}")
                    return i
                else:
                    logger.debug(f"_handle_pair_passive fallback: action at index {i} failed card validation: {action[0]}")
        
        # 只有真的没有可选动作时才PASS
        logger.warning(f"_handle_pair_passive: No valid non-PASS actions available, returning PASS (index 0)")
        return 0
    
    def _handle_other_passive(self, message: Dict, action_list: List, state: Dict) -> int:
        """处理其他牌型被动出牌（优化：增强ThreeWithTwo和Bomb处理）"""
        import logging
        logger = logging.getLogger("OpeningPassiveHandler")
        
        cur_action = message.get("curAction", [])
        cur_type = cur_action[0] if len(cur_action) > 0 else ""
        cur_rank = cur_action[1] if len(cur_action) > 1 else ""
        handcards = message.get("handCards", [])
        cur_rank_param = message.get("curRank", "2")
        
        # ⚠️ 优化1：针对ThreeWithTwo的特殊处理
        if cur_type == 'ThreeWithTwo':
            logger.info(f"Handling ThreeWithTwo passive: cur_rank={cur_rank}")
            # 优先寻找能压制的ThreeWithTwo
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'ThreeWithTwo':
                    if len(action) > 1:
                        # 比较牌值（考虑级牌）
                        action_rank_val = self._get_rank_value(action[1], cur_rank_param) if hasattr(self, '_get_rank_value') else 0
                        cur_rank_val = self._get_rank_value(cur_rank, cur_rank_param) if hasattr(self, '_get_rank_value') else 0
                        if action_rank_val > cur_rank_val:
                            if self._validate_action_cards(action, handcards):
                                logger.info(f"Found suppressing ThreeWithTwo at index {i}: {action[1]}")
                                return i
            
            # 如果找不到能压制的ThreeWithTwo，尝试其他牌型（降级方案）
            logger.warning(f"Cannot suppress ThreeWithTwo {cur_rank}, trying other card types")
            # 优先尝试其他复杂牌型
            fallback_types = ['Trips', 'ThreePair', 'TwoTrips', 'Straight', 'Pair', 'Single']
            for fallback_type in fallback_types:
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == fallback_type:
                        if self._validate_action_cards(action, handcards):
                            logger.info(f"ThreeWithTwo fallback: using {fallback_type} at index {i}")
                            return i
        
        # ⚠️ 优化2：针对Bomb的特殊处理
        elif cur_type == 'Bomb':
            logger.info(f"Handling Bomb passive: cur_rank={cur_rank}")
            # 优先寻找更大的Bomb
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Bomb':
                    if len(action) > 1:
                        action_rank_val = self._get_rank_value(action[1], cur_rank_param) if hasattr(self, '_get_rank_value') else 0
                        cur_rank_val = self._get_rank_value(cur_rank, cur_rank_param) if hasattr(self, '_get_rank_value') else 0
                        if action_rank_val > cur_rank_val:
                            if self._validate_action_cards(action, handcards):
                                logger.info(f"Found larger Bomb at index {i}: {action[1]}")
                                return i
            
            # 如果没有更大的Bomb，尝试其他牌型（降级方案）
            logger.warning(f"No larger Bomb available, trying other card types")
            fallback_types = ['ThreeWithTwo', 'Trips', 'ThreePair', 'TwoTrips', 'Straight', 'Pair', 'Single']
            for fallback_type in fallback_types:
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == fallback_type:
                        if self._validate_action_cards(action, handcards):
                            logger.info(f"Bomb fallback: using {fallback_type} at index {i}")
                            return i
        
        # ⚠️ 修复：即使牌力弱，也应该尝试出牌，而不是直接PASS
        # 开局阶段，牌力弱时仍然尝试出牌（降级方案）
        if state['power'] < 5:
            logger.debug(f"Power < 5, but still trying to find non-PASS action")
            # 尝试返回第一个非PASS动作
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                    if self._validate_action_cards(action, handcards):
                        logger.debug(f"Power weak but found valid non-PASS action at index {i}: {action[0]}")
                        return i
            # 只有真的没有可选动作时才PASS
            logger.warning(f"Power < 5 and no valid non-PASS actions available, returning PASS")
            return 0
        
        # 选择能压制的最小动作（通用处理）
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == cur_type:
                if len(action) > 1:
                    # 比较牌值（考虑级牌）
                    action_rank_val = self._get_rank_value(action[1], cur_rank_param) if hasattr(self, '_get_rank_value') else 0
                    cur_rank_val = self._get_rank_value(cur_rank, cur_rank_param) if hasattr(self, '_get_rank_value') else 0
                    if action_rank_val > cur_rank_val:
                        # ⚠️ 验证卡牌一致性
                        if self._validate_action_cards(action, handcards):
                            logger.info(f"Found suppressing {cur_type} at index {i}: {action[1]}")
                            return i
        
        # ⚠️ 关键修复：在返回0（PASS）之前，确保至少尝试返回第一个有效的非PASS动作
        logger.warning(f"Cannot suppress {cur_type} {cur_rank}, trying fallback")
        # 降级方案：尝试所有其他牌型
        fallback_types = ['Trips', 'ThreeWithTwo', 'ThreePair', 'TwoTrips', 'Straight', 'Pair', 'Single']
        for fallback_type in fallback_types:
            if fallback_type != cur_type:  # 跳过当前牌型
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == fallback_type:
                        if self._validate_action_cards(action, handcards):
                            logger.warning(f"_handle_other_passive fallback: returning {fallback_type} at index {i}")
                            return i
                        else:
                            # ⚠️ Opening阶段：即使验证失败也尝试（放宽验证）
                            logger.warning(f"_handle_other_passive fallback: returning {fallback_type} at index {i} despite validation failure (opening phase)")
                            return i
        
        # 最后降级：返回第一个有效的非PASS动作（即使验证失败也返回）
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                if self._validate_action_cards(action, handcards):
                    logger.warning(f"_handle_other_passive final fallback: returning first valid non-PASS action at index {i}: {action[0]}")
                    return i
                else:
                    # ⚠️ Opening阶段：即使验证失败也返回（放宽验证）
                    logger.warning(f"_handle_other_passive final fallback: returning first non-PASS action at index {i} despite validation failure (opening phase): {action[0]}")
                    return i
        
        # 只有真的没有可选动作时才PASS
        logger.warning(f"_handle_other_passive: No valid non-PASS actions available, returning PASS (index 0)")
        return 0
    
    def _default_passive_action(self, action_list: List, message: Dict = None) -> int:
        """默认被动动作选择：选择第一个有效的非PASS动作"""
        import logging
        logger = logging.getLogger("OpeningPassiveHandler")
        
        logger.info(f"_default_passive_action: actionList size={len(action_list)}")
        if action_list:
            logger.info(f"First 5 actions: {action_list[:5]}")
        
        # ⚠️ 修复：验证卡牌一致性，确保返回的动作是有效的
        handcards = message.get("handCards", []) if message else []
        
        # 选择第一个有效的非PASS动作
        non_pass_count = 0
        valid_count = 0
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0:
                if action[0] != "PASS":
                    non_pass_count += 1
                    # ⚠️ 验证卡牌一致性
                    if handcards and hasattr(self, '_validate_action_cards'):
                        if self._validate_action_cards(action, handcards):
                            valid_count += 1
                            logger.info(f"Found valid non-PASS action at index {i}: {action[0]} - {action}")
                            return i
                        else:
                            logger.debug(f"Non-PASS action at index {i} failed card validation: {action[0]}")
                    else:
                        # 如果没有handcards或没有验证方法，直接返回
                        valid_count += 1
                        logger.info(f"Found non-PASS action at index {i}: {action[0]} (no validation)")
                        return i
            elif action != "PASS":
                non_pass_count += 1
                valid_count += 1
                logger.info(f"Found non-PASS action at index {i}: {action}")
                return i
        
        # ⚠️ 关键修复：即使所有动作验证失败，也要返回第一个非PASS动作（而不是PASS）
        if non_pass_count > 0:
            logger.warning(f"No valid non-PASS actions found after validation (checked {len(action_list)} actions, found {non_pass_count} non-PASS, {valid_count} valid), but returning first non-PASS action anyway")
            # 返回第一个非PASS动作（即使验证失败）
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                    logger.warning(f"Returning first non-PASS action at index {i} despite validation failure: {action}")
                    return i
                elif action != "PASS":
                    logger.warning(f"Returning first non-PASS action at index {i} despite validation failure: {action}")
                    return i
        
        logger.warning(f"No non-PASS actions found at all (checked {len(action_list)} actions), returning 0 (PASS)")
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
        
        # ⚠️ 关键修复：在返回0（PASS）之前，确保至少尝试返回第一个非PASS动作
        import logging
        logger = logging.getLogger("MidEarlyActiveHandler")
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                logger.warning(f"Final fallback: returning first non-PASS action at index {i} (all strategies failed to find suitable action)")
                return i
        
        # 只有真的没有可选动作时才PASS
        logger.warning(f"No non-PASS actions available, returning PASS (index 0)")
        return 0
    
    def _extract_game_state(self, message: Dict) -> Dict:
        """提取游戏状态信息"""
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        
        my_rest = len(handcards) if handcards else CARDS_PER_PLAYER
        opponent_rest_cards_list = list(DEFAULT_ALL_REST_LIST)
        teammate_rest_cards = DEFAULT_REST_CARDS
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", DEFAULT_REST_CARDS)
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
        
        my_rest = len(handcards) if handcards else CARDS_PER_PLAYER
        opponent_rest_cards_list = list(DEFAULT_ALL_REST_LIST)
        teammate_rest_cards = DEFAULT_REST_CARDS
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", DEFAULT_REST_CARDS)
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
        """处理单张被动出牌（中期：更积极压制对手，集成lalala策略）"""
        import logging
        logger = logging.getLogger("MidEarlyPassiveHandler")
        
        cur_action = message.get("curAction", [])
        action_rank = cur_action[1] if len(cur_action) > 1 else ""
        
        # 获取当前级牌和手牌
        cur_rank = message.get("curRank", "2")
        handcards = message.get("handCards", [])
        rank_card = 'H' + cur_rank  # 等级牌（如'H2'）
        
        # 提取PASS次数（学习lalala）
        pass_num = message.get("pass_num", 0)
        my_pass_num = message.get("my_pass_num", 0)
        
        # 提取玩家剩余牌数信息（学习lalala）
        public_info = message.get("publicInfo", [])
        numofplayers = list(DEFAULT_ALL_REST_LIST)
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                numofplayers[i] = info.get("rest", DEFAULT_REST_CARDS)
        
        numofnext = numofplayers[(my_pos + 1) % 4]  # 下家剩余牌数
        numofpre = numofplayers[(my_pos - 1) % 4]  # 上家剩余牌数
        numoffri = numofplayers[(my_pos + 2) % 4]  # 队友剩余牌数
        numofgreaterPos = numofplayers[greater_pos] if greater_pos >= 0 else DEFAULT_REST_CARDS
        
        # 计算当前牌值和最大牌值（学习lalala）
        cur_rank_val = self._get_rank_value(action_rank, cur_rank)
        # 估算最大牌值（使用剩余牌库的最后一张，如果没有则使用A）
        max_val = 14  # 默认A
        rest_cards = message.get("remainCards", [])
        if rest_cards and len(rest_cards) > 0:
            last_card = rest_cards[-1] if isinstance(rest_cards[-1], list) else rest_cards[-1]
            if isinstance(last_card, list) and len(last_card) > 0:
                last_card_str = last_card[0] if isinstance(last_card[0], str) else str(last_card[0])
                if len(last_card_str) >= 2:
                    max_val = self._get_rank_value(last_card_str[1], cur_rank)
        
        # 构建牌值映射（学习lalala）
        card_val = self._build_card_value_map(cur_rank)
        
        # 详细分析手牌结构（学习lalala）
        hand_structure = self._analyze_hand_structure_detailed(handcards, cur_rank)
        single_member = hand_structure['single_member']
        pair_member = hand_structure['pair_member']
        trip_member = hand_structure['trip_member']
        bomb_member = hand_structure['bomb_member']
        straight_member = hand_structure['straight_member']
        sorted_cards = hand_structure['sorted_cards']
        bomb_info = hand_structure['bomb_info']
        
        # 分离单张动作和炸弹动作（学习lalala）
        single_action_list = []
        bomb_action_list = []
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0:
                if action[0] == 'Single':
                    single_action_list.append((i, action))
                elif action[0] == 'Bomb':
                    bomb_action_list.append((i, action))
        
        # ⭐ 残局/关键阶段处理（下家≤4或上家≤3）（学习lalala）
        if numofnext <= 4 or (numofpre <= 3 and numofpre >= 1):
            # 5.1 保护队友（关键策略）
            if (my_pos + 2) % 4 == greater_pos and cur_rank_val >= max_val:
                logger.debug("残局保护队友：PASS")
                return 0
            if (my_pos + 2) % 4 == greater_pos and cur_rank_val >= 15 and numofnext != 1:
                logger.debug("残局保护队友：PASS")
                return 0
            
            # 5.2 优先选择：单张成员 + 大牌值 + 非等级牌
            for i, action in single_action_list:
                if len(action) > 1:
                    action_rank_str = action[1]
                    action_cards = action[2] if len(action) > 2 else []
                    if action_cards and len(action_cards) > 0:
                        first_card = action_cards[0] if isinstance(action_cards[0], str) else str(action_cards[0])
                        action_rank_val = card_val.get(action_rank_str, 0)
                        if action_rank_val >= max_val and first_card in single_member and rank_card not in action_cards:
                            if self._validate_action_cards(action, handcards):
                                logger.debug(f"残局选择单张成员+大牌值: {action_rank_str}")
                                return i
            
            # 5.3 次优选择：非炸弹成员 + 大牌值 + 非等级牌 + 不在顺子中
            for i, action in single_action_list:
                if len(action) > 1:
                    action_rank_str = action[1]
                    action_cards = action[2] if len(action) > 2 else []
                    if action_cards and len(action_cards) > 0:
                        first_card = action_cards[0] if isinstance(action_cards[0], str) else str(action_cards[0])
                        action_rank_val = card_val.get(action_rank_str, 0)
                        if action_rank_val >= max_val and first_card not in bomb_member and rank_card not in action_cards:
                            if not self._is_in_straight(action, straight_member):
                                if self._validate_action_cards(action, handcards):
                                    logger.debug(f"残局选择非炸弹成员+大牌值: {action_rank_str}")
                                    return i
            
            # 5.4 考虑使用炸弹
            bomb_index = self._choose_bomb(bomb_action_list, handcards, sorted_cards, bomb_info, rank_card, card_val, action_list)
            if bomb_index != -1:
                logger.debug(f"残局选择炸弹: index={bomb_index}")
                return bomb_index
            
            # 5.5 放宽条件：牌值 >= max_val-2
            for i, action in single_action_list:
                if len(action) > 1:
                    action_rank_str = action[1]
                    action_cards = action[2] if len(action) > 2 else []
                    if action_cards and len(action_cards) > 0:
                        first_card = action_cards[0] if isinstance(action_cards[0], str) else str(action_cards[0])
                        action_rank_val = card_val.get(action_rank_str, 0)
                        if action_rank_val >= max_val - 2 and first_card not in bomb_member and rank_card not in action_cards:
                            if not self._is_in_straight(action, straight_member):
                                if self._validate_action_cards(action, handcards):
                                    logger.debug(f"残局放宽条件选择: {action_rank_str}")
                                    return i
        
        # ⭐ 队友是最大动作者的处理（学习lalala）
        if (my_pos + 2) % 4 == greater_pos:
            # 6.1 如果当前牌值很大，PASS
            if cur_rank_val >= 14 or cur_rank_val >= max_val - 2:
                logger.debug("队友出牌，当前牌值很大：PASS")
                return 0
            
            # 6.2 如果队友剩余牌数≤4
            if numoffri <= 4:
                index = self._normal_strategy(single_action_list, single_member, rank_card, card_val, action_list)
                if index == -1:
                    return 0
                if cur_rank_val <= 10:
                    return index
                else:
                    # 只出比当前牌大1的牌
                    selected_action = action_list[index] if index < len(action_list) else None
                    if selected_action and len(selected_action) > 1:
                        selected_rank_val = card_val.get(selected_action[1], 0)
                        if selected_rank_val == cur_rank_val + 1:
                            return index
            
            # 6.3 队友剩余牌数>4
            else:
                index = self._normal_strategy(single_action_list, single_member, rank_card, card_val, action_list)
                if index != -1:
                    return index
                else:
                    return 0
        
        # ⭐ 对手是最大动作者的处理（学习lalala）
        else:
            # 7.1 优先使用normal策略
            index = self._normal_strategy(single_action_list, single_member, rank_card, card_val, action_list)
            if index != -1:
                logger.debug(f"normal策略选择: index={index}")
                return index
            
            # 7.2 如果PASS次数过多，使用special策略
            if pass_num >= 5 or my_pass_num >= 3:
                index = self._special_strategy(single_action_list, bomb_member, straight_member, rank_card, card_val, action_list)
                if index != -1:
                    logger.debug(f"special策略选择: index={index}")
                    return index
            
            # 7.3 考虑使用炸弹
            cur_bomb_num = self._cal_bomb_num(sorted_cards, handcards, rank_card)
            if cur_rank_val >= max_val and numofgreaterPos >= 15 and cur_bomb_num > 1:
                import random
                p = random.random()
                bomb_index = self._choose_bomb(bomb_action_list, handcards, sorted_cards, bomb_info, rank_card, card_val, action_list)
                if p > 0.5:  # 50%概率使用炸弹
                    if bomb_index != -1:
                        logger.debug(f"50%概率使用炸弹: index={bomb_index}")
                        return bomb_index
            elif ((cur_rank_val >= 15 or cur_rank_val >= max_val - 2) and numofgreaterPos <= 15) or pass_num >= 7 or my_pass_num >= 5:
                bomb_index = self._choose_bomb(bomb_action_list, handcards, sorted_cards, bomb_info, rank_card, card_val, action_list)
                if bomb_index != -1:
                    logger.debug(f"强制使用炸弹: index={bomb_index}")
                    return bomb_index
                else:
                    return 0
        
        # ⚠️ 优先级1：使用多余单张（最高优先级）（保留原有逻辑作为降级方案）
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
        my_rest = len(handcards) if handcards else CARDS_PER_PLAYER
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
        return self._default_passive_action(action_list, message)
    
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
        return self._default_passive_action(action_list, message)
    
    def _handle_other_passive(self, message: Dict, action_list: List, state: Dict) -> int:
        """处理其他牌型被动出牌（中期：更积极压制，优化ThreeWithTwo和Bomb处理）"""
        import logging
        logger = logging.getLogger("MidEarlyPassiveHandler")
        
        cur_action = message.get("curAction", [])
        cur_type = cur_action[0] if len(cur_action) > 0 else ""
        cur_rank = cur_action[1] if len(cur_action) > 1 else ""
        cur_rank_param = message.get("curRank", "2")
        handcards = message.get("handCards", [])
        
        # ⚠️ 优化1：针对ThreeWithTwo的特殊处理
        if cur_type == 'ThreeWithTwo':
            logger.info(f"Handling ThreeWithTwo passive: cur_rank={cur_rank}")
            # 优先寻找能压制的ThreeWithTwo
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'ThreeWithTwo':
                    if len(action) > 1:
                        action_rank_val = self._get_rank_value(action[1], cur_rank_param)
                        cur_rank_val = self._get_rank_value(cur_rank, cur_rank_param)
                        if action_rank_val > cur_rank_val:
                            if self._validate_action_cards(action, handcards):
                                logger.info(f"Found suppressing ThreeWithTwo at index {i}: {action[1]}")
                                return i
            
            # 如果找不到能压制的ThreeWithTwo，尝试其他牌型（降级方案）
            logger.warning(f"Cannot suppress ThreeWithTwo {cur_rank}, trying other card types")
            fallback_types = ['Trips', 'ThreePair', 'TwoTrips', 'Straight', 'Pair', 'Single']
            for fallback_type in fallback_types:
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == fallback_type:
                        if self._validate_action_cards(action, handcards):
                            logger.info(f"ThreeWithTwo fallback: using {fallback_type} at index {i}")
                            return i
        
        # ⚠️ 优化2：针对Bomb的特殊处理
        elif cur_type == 'Bomb':
            logger.info(f"Handling Bomb passive: cur_rank={cur_rank}")
            # 优先寻找更大的Bomb
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Bomb':
                    if len(action) > 1:
                        action_rank_val = self._get_rank_value(action[1], cur_rank_param)
                        cur_rank_val = self._get_rank_value(cur_rank, cur_rank_param)
                        if action_rank_val > cur_rank_val:
                            if self._validate_action_cards(action, handcards):
                                logger.info(f"Found larger Bomb at index {i}: {action[1]}")
                                return i
            
            # 如果没有更大的Bomb，尝试其他牌型（降级方案）
            logger.warning(f"No larger Bomb available, trying other card types")
            fallback_types = ['ThreeWithTwo', 'Trips', 'ThreePair', 'TwoTrips', 'Straight', 'Pair', 'Single']
            for fallback_type in fallback_types:
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == fallback_type:
                        if self._validate_action_cards(action, handcards):
                            logger.info(f"Bomb fallback: using {fallback_type} at index {i}")
                            return i
        
        # 中期阶段：降低牌力阈值，更积极压制
        # ⚠️ 修复：即使牌力弱，也应该尝试出牌，而不是直接PASS
        # 只有在真的没有可选动作时才PASS
        if state['power'] < 3:
            # 牌力弱时，仍然尝试返回第一个非PASS动作（降级方案）
            logger.debug(f"Power < 3, but still trying to find non-PASS action")
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                    if self._validate_action_cards(action, handcards):
                        logger.debug(f"Power weak but found valid non-PASS action at index {i}: {action[0]}")
                        return i
            # 只有真的没有可选动作时才PASS
            logger.warning(f"Power < 3 and no valid non-PASS actions available, returning PASS")
            return 0
        
        # 优先寻找能压制的同类型动作
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == cur_type:
                if len(action) > 1:
                    # 比较牌值（考虑级牌）
                    action_rank_val = self._get_rank_value(action[1], cur_rank_param)
                    cur_rank_val = self._get_rank_value(cur_rank, cur_rank_param)
                    if action_rank_val > cur_rank_val:
                        # ⚠️ 验证卡牌一致性
                        if self._validate_action_cards(action, handcards):
                            logger.info(f"Found suppressing {cur_type} at index {i}: {action[1]}")
                            return i
        
        # 如果没有同类型能压制的，考虑使用炸弹（中期谨慎使用）
        if state['power'] >= 6:
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Bomb':
                    if self._validate_action_cards(action, handcards):
                        # 中期阶段：只有在牌力较强且对手威胁大时才用炸弹
                        logger.info(f"Using Bomb at index {i} (power >= 6)")
                        return i
        
        # 降级：选择第一个非PASS动作
        return self._default_passive_action(action_list, message)
    
    def _default_passive_action(self, action_list: List, message: Dict = None) -> int:
        """默认被动动作选择（选择第一个有效的非PASS动作）"""
        import logging
        logger = logging.getLogger("MidEarlyPassiveHandler")
        
        logger.info(f"_default_passive_action: actionList size={len(action_list)}")
        if action_list:
            logger.info(f"First 5 actions: {action_list[:5]}")
        
        # ⚠️ 修复：验证卡牌一致性，确保返回的动作是有效的
        handcards = message.get("handCards", []) if message else []
        
        # 选择第一个有效的非PASS动作（中期阶段应该更积极）
        non_pass_count = 0
        valid_count = 0
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0:
                if action[0] != "PASS":
                    non_pass_count += 1
                    # ⚠️ 验证卡牌一致性
                    if handcards and hasattr(self, '_validate_action_cards'):
                        if self._validate_action_cards(action, handcards):
                            valid_count += 1
                            logger.info(f"Found valid non-PASS action at index {i}: {action[0]} - {action}")
                            return i
                        else:
                            logger.debug(f"Non-PASS action at index {i} failed card validation: {action[0]}")
                    else:
                        # 如果没有handcards或没有验证方法，直接返回
                        valid_count += 1
                        logger.info(f"Found non-PASS action at index {i}: {action[0]} (no validation)")
                        return i
            elif action != "PASS":
                non_pass_count += 1
                valid_count += 1
                logger.info(f"Found non-PASS action at index {i}: {action}")
                return i
        
        # ⚠️ 关键修复：即使所有动作验证失败，也要返回第一个非PASS动作（而不是PASS）
        if non_pass_count > 0:
            logger.warning(f"No valid non-PASS actions found after validation (checked {len(action_list)} actions, found {non_pass_count} non-PASS, {valid_count} valid), but returning first non-PASS action anyway")
            # 返回第一个非PASS动作（即使验证失败）
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                    logger.warning(f"Returning first non-PASS action at index {i} despite validation failure: {action}")
                    return i
                elif action != "PASS":
                    logger.warning(f"Returning first non-PASS action at index {i} despite validation failure: {action}")
                    return i
        
        logger.warning(f"No non-PASS actions found at all (checked {len(action_list)} actions), returning 0 (PASS)")
        if action_list:
            logger.warning(f"All actions in actionList: {action_list}")
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
                try:
                    selected_candidate_idx = self.priority_system.select(candidates, hand_structure, context)
                    if 0 <= selected_candidate_idx < len(candidate_indices):
                        return candidate_indices[selected_candidate_idx]
                    else:
                        logger.warning(f"PrioritySystem returned invalid index: {selected_candidate_idx}, max={len(candidate_indices)-1}, falling back to first candidate")
                        if candidate_indices:
                            return candidate_indices[0]
                except Exception as e:
                    logger.error(f"PrioritySystem.select() error: {e}", exc_info=True)
                    if candidate_indices:
                        logger.warning(f"Falling back to first candidate after PrioritySystem error")
                        return candidate_indices[0]
            else:
                logger.warning(f"No candidates after filtering PASS actions (total actions: {len(action_list)})")
                # ⚠️ 关键修复：即使candidates为空，也要尝试返回第一个非PASS动作
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                        logger.warning(f"Fallback: returning first non-PASS action at index {i} (card validation may have been too strict)")
                        return i
        
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
        
        # ⚠️ 关键修复：在返回0（PASS）之前，确保至少尝试返回第一个非PASS动作
        import logging
        logger = logging.getLogger("MidLateActiveHandler")
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                logger.warning(f"Final fallback: returning first non-PASS action at index {i} (all strategies failed to find suitable action)")
                return i
        
        # 只有真的没有可选动作时才PASS
        logger.warning(f"No non-PASS actions available, returning PASS (index 0)")
        return 0
    
    def _extract_game_state(self, message: Dict) -> Dict:
        """提取游戏状态信息"""
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        
        my_rest = len(handcards) if handcards else CARDS_PER_PLAYER
        opponent_rest_cards_list = list(DEFAULT_ALL_REST_LIST)
        teammate_rest_cards = DEFAULT_REST_CARDS
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", DEFAULT_REST_CARDS)
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
            # ⚠️ 修复：即使牌力非常弱（< 3），也应该尝试返回第一个有效的非PASS动作
            import logging
            logger = logging.getLogger("MidLatePassiveHandler")
            handcards = message.get("handCards", [])
            logger.debug(f"Power < 3, but still trying to find valid non-PASS action")
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                    # ⚠️ 验证卡牌一致性，确保返回的动作是有效的
                    if self._validate_action_cards(action, handcards):
                        logger.debug(f"Power weak but found valid non-PASS action at index {i}: {action[0]}")
                        return i
                    else:
                        logger.debug(f"Power weak but action at index {i} failed card validation: {action[0]}")
            # 只有真的没有可选动作时才PASS
            logger.warning(f"Power < 3 and no valid non-PASS actions available, returning PASS")
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
        
        my_rest = len(handcards) if handcards else CARDS_PER_PLAYER
        
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
        # ⚠️ 修复：检查一手出完（无论是否有excess_singles）
        one_hand_idx = self._check_one_hand_complete(action_list, handcards)
        if one_hand_idx is not None:
            return one_hand_idx
        
        # ⭐ 使用优先级系统（提升：动态优先级，残局阶段）
        if self.priority_system:
            import logging
            logger = logging.getLogger("EndgameEarlyActiveHandler")
            
            # 获取手牌结构（使用HandStructureAnalyzer）
            hand_structure = {}
            if hasattr(self, 'hand_analyzer') and self.hand_analyzer:
                handcards = message.get("handCards", [])
                rank = message.get("curRank", "2")
                hand_structure = self.hand_analyzer.analyze(handcards, rank)
            
            # ⚠️ 关键修复：过滤PASS动作，同时记录原始索引，并验证卡牌一致性
            scan_result = context.get('scan_result', {})
            protected_combinations = scan_result.get('protected_combinations', [])
            
            candidates = []
            candidate_indices = []
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0:
                    if action[0] != "PASS":
                        # 1. 卡牌一致性检查（endgame阶段放宽验证）
                        validation_passed = self._validate_action_cards(action, handcards)
                        if not validation_passed:
                            logger.warning(f"Action {i} failed card validation, but in endgame phase, will still consider it: {action}")
                            # ⚠️ endgame阶段：放宽验证，避免过度过滤
                        
                        # 2. ⚠️ 硬约束：检查是否会破坏受保护组合（但只在验证通过时检查）
                        action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
                        if action_cards and protected_combinations and validation_passed:
                            # ⚠️ 修复：展平嵌套列表，确保所有元素都是字符串（可哈希）
                            action_cards_flat = self._flatten_cards(action_cards)
                            action_cards_set = set(action_cards_flat)
                            would_break = False
                            for protected in protected_combinations:
                                if isinstance(protected, list):
                                    protected_flat = self._flatten_cards(protected)
                                    protected_set = set(protected_flat)
                                    # 如果动作中的卡牌与受保护组合有交集，且不是完整使用，就是破坏
                                    if action_cards_set & protected_set:
                                        if not action_cards_set.issubset(protected_set):
                                            would_break = True
                                            logger.warning(f"Action {i} would break protected combination, skipping: {action}")
                                            break
                            if would_break:
                                continue
                        
                        # ⚠️ 即使验证失败，也添加到候选列表（endgame阶段更宽松）
                        candidates.append(action)
                        candidate_indices.append(i)
                elif action != "PASS":
                    candidates.append(action)
                    candidate_indices.append(i)
            
            logger.debug(f"Filtered {len(candidates)} candidates from {len(action_list)} actions (endgame phase: relaxed validation)")
            
            # ⚠️ 关键修复：如果有excess_singles，优先选择它们
            if excess_singles and candidates:
                excess_candidates = []
                excess_indices = []
                other_candidates = []
                other_indices = []
                
                for idx, candidate in enumerate(candidates):
                    action_cards = candidate[2] if isinstance(candidate, list) and len(candidate) > 2 and isinstance(candidate[2], list) else []
                    if action_cards and len(action_cards) == 1 and action_cards[0] in excess_singles:
                        excess_candidates.append(candidate)
                        excess_indices.append(candidate_indices[idx])
                    else:
                        other_candidates.append(candidate)
                        other_indices.append(candidate_indices[idx])
                
                # 优先使用excess_singles
                if excess_candidates:
                    candidates = excess_candidates + other_candidates
                    candidate_indices = excess_indices + other_indices
                    logger.info(f"Prioritized {len(excess_candidates)} excess_singles candidates")
            
            if candidates:
                try:
                    selected_candidate_idx = self.priority_system.select(candidates, hand_structure, context)
                    if 0 <= selected_candidate_idx < len(candidate_indices):
                        original_idx = candidate_indices[selected_candidate_idx]
                        logger.info(f"PrioritySystem selected: candidate_idx={selected_candidate_idx}, original_idx={original_idx}, action={candidates[selected_candidate_idx]}")
                        return original_idx
                    else:
                        logger.warning(f"PrioritySystem returned invalid index: {selected_candidate_idx}, max={len(candidate_indices)-1}, falling back to first candidate")
                        if candidate_indices:
                            return candidate_indices[0]
                except Exception as e:
                    logger.error(f"PrioritySystem.select() error: {e}", exc_info=True)
                    if candidate_indices:
                        logger.warning(f"Falling back to first candidate after PrioritySystem error")
                        return candidate_indices[0]
            else:
                logger.warning(f"No candidates after filtering PASS actions (total actions: {len(action_list)})")
                # ⚠️ 关键修复：即使candidates为空，也要尝试返回第一个非PASS动作
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                        logger.warning(f"Fallback: returning first non-PASS action at index {i} (card validation may have been too strict)")
                        return i
        
        # 优先级2: 使用残局策略类（提升：智能策略选择）
        context = self._build_context(message)
        context.update({
            'my_remain': my_rest,
            'teammate_rest_cards': state.get('teammate_rest_cards', DEFAULT_REST_CARDS),
            'opponent_rest_cards_list': state.get('opponent_rest_cards_list', list(DEFAULT_ALL_REST_LIST))
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
        
        my_rest = len(handcards) if handcards else CARDS_PER_PLAYER
        opponent_rest_cards_list = list(DEFAULT_ALL_REST_LIST)
        teammate_rest_cards = DEFAULT_REST_CARDS
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", DEFAULT_REST_CARDS)
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
        found_valid = False
        
        for i, action in enumerate(action_list):
            if not action or (isinstance(action, list) and len(action) > 0 and action[0] == "PASS"):
                continue
            action_size = len(action[2]) if isinstance(action, list) and len(action) > 2 else 1
            if action_size > largest_size:
                largest_size = action_size
                largest_idx = i
                found_valid = True
        
        # ⚠️ 关键修复：如果没有找到有效动作，返回0（PASS）
        if not found_valid:
            return 0
        
        # ⚠️ 关键修复：确保返回的索引在有效范围内
        if largest_idx < 0 or largest_idx >= len(action_list):
            return 0
        
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
            
            # ⭐ 集成lalala策略（残局阶段）
            cur_rank_str = message.get("curRank", "2")
            rank_card = 'H' + cur_rank_str
            pass_num = message.get("pass_num", 0)
            my_pass_num = message.get("my_pass_num", 0)
            
            # 提取玩家剩余牌数信息
            public_info = message.get("publicInfo", [])
            numofplayers = list(DEFAULT_ALL_REST_LIST)
            if public_info and len(public_info) == 4:
                for i, info in enumerate(public_info):
                    numofplayers[i] = info.get("rest", DEFAULT_REST_CARDS)
            
            my_pos = message.get("myPos", 0)
            greater_pos = message.get("greaterPos", -1)
            numofnext = numofplayers[(my_pos + 1) % 4]
            numofpre = numofplayers[(my_pos - 1) % 4]
            numoffri = numofplayers[(my_pos + 2) % 4]
            numofgreaterPos = numofplayers[greater_pos] if greater_pos >= 0 else DEFAULT_REST_CARDS
            
            # 计算最大牌值
            max_val = 14
            rest_cards = message.get("remainCards", [])
            if rest_cards and len(rest_cards) > 0:
                last_card = rest_cards[-1] if isinstance(rest_cards[-1], list) else rest_cards[-1]
                if isinstance(last_card, list) and len(last_card) > 0:
                    last_card_str = last_card[0] if isinstance(last_card[0], str) else str(last_card[0])
                    if len(last_card_str) >= 2:
                        max_val = self._get_rank_value(last_card_str[1], cur_rank_str)
            
            # 构建牌值映射和手牌结构
            card_val = self._build_card_value_map(cur_rank_str)
            hand_structure = self._analyze_hand_structure_detailed(handcards, cur_rank_str)
            single_member = hand_structure['single_member']
            bomb_member = hand_structure['bomb_member']
            straight_member = hand_structure['straight_member']
            sorted_cards = hand_structure['sorted_cards']
            bomb_info = hand_structure['bomb_info']
            
            # 分离单张动作和炸弹动作
            single_action_list = []
            bomb_action_list = []
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0:
                    if action[0] == 'Single':
                        single_action_list.append((i, action))
                    elif action[0] == 'Bomb':
                        bomb_action_list.append((i, action))
            
            # ⭐ 残局/关键阶段处理（下家≤4或上家≤3）
            if numofnext <= 4 or (numofpre <= 3 and numofpre >= 1):
                # 保护队友
                if (my_pos + 2) % 4 == greater_pos and cur_rank_val >= max_val:
                    logger.debug("残局保护队友：PASS")
                    return 0
                if (my_pos + 2) % 4 == greater_pos and cur_rank_val >= 15 and numofnext != 1:
                    logger.debug("残局保护队友：PASS")
                    return 0
                
                # 优先选择：单张成员 + 大牌值 + 非等级牌
                for i, action in single_action_list:
                    if len(action) > 1:
                        action_rank_str = action[1]
                        action_cards = action[2] if len(action) > 2 else []
                        if action_cards and len(action_cards) > 0:
                            first_card = action_cards[0] if isinstance(action_cards[0], str) else str(action_cards[0])
                            action_rank_val = card_val.get(action_rank_str, 0)
                            if action_rank_val >= max_val and first_card in single_member and rank_card not in action_cards:
                                if self._validate_action_cards(action, handcards):
                                    logger.debug(f"残局选择单张成员+大牌值: {action_rank_str}")
                                    return i
                
                # 次优选择：非炸弹成员 + 大牌值
                for i, action in single_action_list:
                    if len(action) > 1:
                        action_rank_str = action[1]
                        action_cards = action[2] if len(action) > 2 else []
                        if action_cards and len(action_cards) > 0:
                            first_card = action_cards[0] if isinstance(action_cards[0], str) else str(action_cards[0])
                            action_rank_val = card_val.get(action_rank_str, 0)
                            if action_rank_val >= max_val and first_card not in bomb_member and rank_card not in action_cards:
                                if not self._is_in_straight(action, straight_member):
                                    if self._validate_action_cards(action, handcards):
                                        logger.debug(f"残局选择非炸弹成员+大牌值: {action_rank_str}")
                                        return i
                
                # 考虑使用炸弹
                bomb_index = self._choose_bomb(bomb_action_list, handcards, sorted_cards, bomb_info, rank_card, card_val, action_list)
                if bomb_index != -1:
                    logger.debug(f"残局选择炸弹: index={bomb_index}")
                    return bomb_index
            
            # ⭐ 队友是最大动作者的处理
            if (my_pos + 2) % 4 == greater_pos:
                if cur_rank_val >= 14 or cur_rank_val >= max_val - 2:
                    logger.debug("队友出牌，当前牌值很大：PASS")
                    return 0
                if numoffri <= 4:
                    index = self._normal_strategy(single_action_list, single_member, rank_card, card_val, action_list)
                    if index == -1:
                        return 0
                    if cur_rank_val <= 10:
                        return index
                    else:
                        selected_action = action_list[index] if index < len(action_list) else None
                        if selected_action and len(selected_action) > 1:
                            selected_rank_val = card_val.get(selected_action[1], 0)
                            if selected_rank_val == cur_rank_val + 1:
                                return index
                else:
                    index = self._normal_strategy(single_action_list, single_member, rank_card, card_val, action_list)
                    if index != -1:
                        return index
                    else:
                        return 0
            
            # ⭐ 对手是最大动作者的处理
            else:
                # 优先使用normal策略
                index = self._normal_strategy(single_action_list, single_member, rank_card, card_val, action_list)
                if index != -1:
                    logger.debug(f"normal策略选择: index={index}")
                    return index
                
                # 如果PASS次数过多，使用special策略
                if pass_num >= 5 or my_pass_num >= 3:
                    index = self._special_strategy(single_action_list, bomb_member, straight_member, rank_card, card_val, action_list)
                    if index != -1:
                        logger.debug(f"special策略选择: index={index}")
                        return index
                
                # 考虑使用炸弹
                cur_bomb_num = self._cal_bomb_num(sorted_cards, handcards, rank_card)
                if cur_rank_val >= max_val and numofgreaterPos >= 15 and cur_bomb_num > 1:
                    import random
                    p = random.random()
                    bomb_index = self._choose_bomb(bomb_action_list, handcards, sorted_cards, bomb_info, rank_card, card_val, action_list)
                    if p > 0.5:
                        if bomb_index != -1:
                            logger.debug(f"50%概率使用炸弹: index={bomb_index}")
                            return bomb_index
                elif ((cur_rank_val >= 15 or cur_rank_val >= max_val - 2) and numofgreaterPos <= 15) or pass_num >= 7 or my_pass_num >= 5:
                    bomb_index = self._choose_bomb(bomb_action_list, handcards, sorted_cards, bomb_info, rank_card, card_val, action_list)
                    if bomb_index != -1:
                        logger.debug(f"强制使用炸弹: index={bomb_index}")
                        return bomb_index
                    else:
                        return 0
            
            # ⚠️ 优先级1：使用多余单张（最高优先级）（保留原有逻辑作为降级方案）
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
            
            # ⚠️ 优先级4：其他能压制的单张（降级方案）
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    if len(action) > 1:
                        action_rank_str = action[1]
                        action_rank_val = self._get_rank_value(action_rank_str, message.get("curRank", "2")) if hasattr(self, '_get_rank_value') else 0
                        if action_rank_val > cur_rank_val:
                            if self._validate_action_cards(action, handcards):
                                logger.debug(f"残局使用其他单张压制: {action_rank_str}")
                                return i
            
            # ⚠️ 优先级5：任何能压制的单张（进一步降级，放宽条件）
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    if len(action) > 1:
                        action_rank_str = action[1]
                        action_rank_val = self._get_rank_value(action_rank_str, message.get("curRank", "2")) if hasattr(self, '_get_rank_value') else 0
                        # 即使不能压制，也尝试使用（残局阶段更积极）
                        if self._validate_action_cards(action, handcards):
                            logger.debug(f"残局使用单张（即使不能压制）: {action_rank_str}")
                            return i
            
            # ⚠️ 关键修复：如果所有优先级都失败，尝试返回第一个有效的非PASS动作
            logger.warning(f"All Single priorities failed, trying fallback")
            # 先尝试其他牌型
            fallback_types = ['Pair', 'Trips', 'ThreeWithTwo', 'ThreePair', 'TwoTrips', 'Straight']
            for fallback_type in fallback_types:
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == fallback_type:
                        validation_passed = self._validate_action_cards(action, handcards)
                        if validation_passed:
                            logger.warning(f"EndgameEarlyPassiveHandler Single fallback: using {fallback_type} at index {i}")
                            return i
            
            # 最后降级：返回第一个有效的非PASS动作
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                    validation_passed = self._validate_action_cards(action, handcards)
                    if validation_passed:
                        logger.warning(f"EndgameEarlyPassiveHandler Single fallback: returning first valid non-PASS action at index {i}")
                        return i
                    else:
                        # ⚠️ endgame阶段：即使验证失败也返回（放宽验证）
                        logger.warning(f"EndgameEarlyPassiveHandler Single fallback: returning first non-PASS action at index {i} despite validation failure (endgame phase)")
                        return i
        
        # 构建上下文信息
        context = self._build_context(message)
        
        # ⭐ 使用队友保护策略（提升：多策略组合，残局阶段更重要）
        if self.teammate_protection:
            protection_action = self.teammate_protection.get_protection_action(message, context)
            if protection_action is not None:
                return protection_action
        
        my_rest = len(handcards) if handcards else CARDS_PER_PLAYER
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
                    # ⚠️ 验证卡牌一致性
                    if self._validate_action_cards(action, handcards):
                        return i
        
        # ⚠️ 关键修复：在返回0（PASS）之前，确保至少尝试返回第一个非PASS动作
        import logging
        logger = logging.getLogger("EndgameEarlyPassiveHandler")
        logger.warning(f"Cannot suppress {cur_action_type} {cur_rank}, trying fallback")
        
        # 先尝试找能压制的同类型动作
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == cur_action_type:
                if len(action) > 1:
                    action_rank = action[1]
                    # 使用_get_rank_value比较牌点大小
                    cur_rank_value = self._get_rank_value(cur_rank, message.get("curRank", "2"))
                    action_rank_value = self._get_rank_value(action_rank, message.get("curRank", "2"))
                    if action_rank_value > cur_rank_value:
                        validation_passed = self._validate_action_cards(action, handcards)
                        if validation_passed:
                            logger.warning(f"EndgameEarlyPassiveHandler fallback: returning suppressing action at index {i}: {action}")
                            return i
                        else:
                            # ⚠️ endgame阶段：即使验证失败也返回（放宽验证）
                            logger.warning(f"EndgameEarlyPassiveHandler fallback: returning suppressing action at index {i} despite validation failure (endgame phase): {action}")
                            return i
        
        # 如果找不到能压制的，返回第一个有效的非PASS动作
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                # ⚠️ endgame阶段：即使验证失败也返回（放宽验证）
                validation_passed = self._validate_action_cards(action, handcards)
                if validation_passed:
                    logger.warning(f"EndgameEarlyPassiveHandler fallback: returning first valid non-PASS action at index {i}")
                    return i
                else:
                    logger.warning(f"EndgameEarlyPassiveHandler fallback: returning first non-PASS action at index {i} despite validation failure (endgame phase)")
                    return i
        
        # 只有真的没有可选动作时才PASS
        logger.warning(f"EndgameEarlyPassiveHandler: No non-PASS actions available, returning PASS (index 0)")
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
        
        my_rest = len(handcards) if handcards else CARDS_PER_PLAYER
        
        # 优先级1: 一手出完（残局最重要）
        one_hand_idx = self._check_one_hand_complete(action_list, handcards)
        if one_hand_idx is not None:
            return one_hand_idx
        
        # 如果有多余单张，优先考虑出单张（残局后期快速减少牌数）
        if excess_singles:
            import logging
            logger = logging.getLogger("EndgameLateActiveHandler")
            logger.debug(f"检测到{len(excess_singles)}张多余单张，优先考虑出单张: {excess_singles}")
            protected_combinations = scan_result.get('protected_combinations', [])
            
            # 优先选择多余单张动作（不破坏受保护组合）
            for excess_card in excess_singles:
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                        action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
                        if action_cards and excess_card in action_cards:
                            if self._validate_action_cards(action, handcards):
                                # 检查是否破坏受保护组合（修复：展平嵌套列表）
                                action_cards_flat = self._flatten_cards(action_cards)
                                action_cards_set = set(action_cards_flat)
                                would_break = False
                                for prot in protected_combinations:
                                    if isinstance(prot, list):
                                        prot_flat = self._flatten_cards(prot)
                                        prot_set = set(prot_flat)
                                        if action_cards_set & prot_set and not action_cards_set.issubset(prot_set):
                                            would_break = True
                                            break
                                if not would_break:
                                    logger.debug(f"选择多余单张: {excess_card}")
                                    return i
            
            # 如果没有匹配的多余单张，至少优先出单张（不破坏受保护组合）
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    if self._validate_action_cards(action, handcards):
                        action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
                        # 检查是否破坏受保护组合（修复：展平嵌套列表）
                        action_cards_flat = self._flatten_cards(action_cards)
                        action_cards_set = set(action_cards_flat)
                        would_break = False
                        for prot in protected_combinations:
                            if isinstance(prot, list):
                                prot_flat = self._flatten_cards(prot)
                                prot_set = set(prot_flat)
                                if action_cards_set & prot_set and not action_cards_set.issubset(prot_set):
                                    would_break = True
                                    break
                        if not would_break:
                            return i
        
        # ⭐ 使用优先级系统（提升：动态优先级，残局后期优先一手出完）
        if self.priority_system:
            import logging
            logger = logging.getLogger("EndgameLateActiveHandler")
            
            # 获取手牌结构（简化实现）
            hand_structure = {}
            if hasattr(self, 'hand_analyzer') and self.hand_analyzer:
                rank = message.get("curRank", "2")
                hand_structure = self.hand_analyzer.analyze(handcards, rank)
            
            # ⚠️ 关键修复：过滤PASS动作，同时记录原始索引，并验证卡牌一致性
            candidates = []
            candidate_indices = []
            scan_result = context.get('scan_result', {})
            protected_combinations = scan_result.get('protected_combinations', [])
            excess_singles = context.get('excess_singles', [])
            
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0:
                    if action[0] != "PASS":
                        # 1. 卡牌一致性检查
                        if not self._validate_action_cards(action, handcards):
                            logger.debug(f"Action {i} failed card validation, skipping: {action}")
                            continue
                        
                        # 2. ⚠️ 硬约束：检查是否会破坏受保护组合
                        action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
                        if action_cards and protected_combinations:
                            # ⚠️ 修复：展平嵌套列表，确保所有元素都是字符串（可哈希）
                            action_cards_flat = self._flatten_cards(action_cards)
                            action_cards_set = set(action_cards_flat)
                            would_break = False
                            for protected in protected_combinations:
                                if isinstance(protected, list):
                                    protected_flat = self._flatten_cards(protected)
                                    protected_set = set(protected_flat)
                                    if action_cards_set & protected_set:
                                        if not action_cards_set.issubset(protected_set):
                                            would_break = True
                                            logger.warning(f"Action {i} would break protected combination, skipping: {action}")
                                            break
                            if would_break:
                                continue
                        
                        candidates.append(action)
                        candidate_indices.append(i)
                elif action != "PASS":
                    candidates.append(action)
                    candidate_indices.append(i)
            
            logger.debug(f"Filtered {len(candidates)} candidates from {len(action_list)} actions")
            
            # ⚠️ 关键修复：如果有excess_singles，优先选择它们
            if excess_singles and candidates:
                excess_candidates = []
                excess_indices = []
                other_candidates = []
                other_indices = []
                
                for idx, candidate in enumerate(candidates):
                    action_cards = candidate[2] if isinstance(candidate, list) and len(candidate) > 2 and isinstance(candidate[2], list) else []
                    if action_cards and len(action_cards) == 1 and action_cards[0] in excess_singles:
                        excess_candidates.append(candidate)
                        excess_indices.append(candidate_indices[idx])
                    else:
                        other_candidates.append(candidate)
                        other_indices.append(candidate_indices[idx])
                
                # 优先使用excess_singles
                if excess_candidates:
                    candidates = excess_candidates + other_candidates
                    candidate_indices = excess_indices + other_indices
                    logger.info(f"Prioritized {len(excess_candidates)} excess_singles candidates")
            
            if candidates:
                try:
                    selected_candidate_idx = self.priority_system.select(candidates, hand_structure, context)
                    if 0 <= selected_candidate_idx < len(candidate_indices):
                        original_idx = candidate_indices[selected_candidate_idx]
                        logger.info(f"PrioritySystem selected: candidate_idx={selected_candidate_idx}, original_idx={original_idx}, action={candidates[selected_candidate_idx]}")
                        return original_idx
                    else:
                        logger.warning(f"PrioritySystem returned invalid index: {selected_candidate_idx}, max={len(candidate_indices)-1}, falling back to first candidate")
                        if candidate_indices:
                            return candidate_indices[0]
                except Exception as e:
                    logger.error(f"PrioritySystem.select() error: {e}", exc_info=True)
                    if candidate_indices:
                        logger.warning(f"Falling back to first candidate after PrioritySystem error")
                        return candidate_indices[0]
            else:
                logger.warning(f"No candidates after filtering PASS actions (total actions: {len(action_list)})")
                # ⚠️ 关键修复：即使candidates为空，也要尝试返回第一个非PASS动作
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                        logger.warning(f"Fallback: returning first non-PASS action at index {i}")
                        return i
        
        # 优先级2: 使用残局策略类（提升：智能策略选择，残局后期更激进）
        context = self._build_context(message)
        state = self._extract_game_state(message)
        context.update({
            'my_remain': my_rest,
            'teammate_rest_cards': state.get('teammate_rest_cards', DEFAULT_REST_CARDS),
            'opponent_rest_cards_list': state.get('opponent_rest_cards_list', list(DEFAULT_ALL_REST_LIST))
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
        
        my_rest = len(handcards) if handcards else CARDS_PER_PLAYER
        opponent_rest_cards_list = list(DEFAULT_ALL_REST_LIST)
        teammate_rest_cards = DEFAULT_REST_CARDS
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", DEFAULT_REST_CARDS)
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
        found_valid = False
        
        for i, action in enumerate(action_list):
            if not action or (isinstance(action, list) and len(action) > 0 and action[0] == "PASS"):
                continue
            action_size = len(action[2]) if isinstance(action, list) and len(action) > 2 else 1
            if action_size > largest_size:
                largest_size = action_size
                largest_idx = i
                found_valid = True
        
        # ⚠️ 关键修复：如果没有找到有效动作，返回0（PASS）
        if not found_valid:
            return 0
        
        # ⚠️ 关键修复：确保返回的索引在有效范围内
        if largest_idx < 0 or largest_idx >= len(action_list):
            return 0
        
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
        
        my_rest = len(handcards) if handcards else CARDS_PER_PLAYER
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
        
        # ⚠️ 关键修复：选择能压制的最小动作（更激进，但遵循扫描结果）
        cur_action_type = cur_action[0] if isinstance(cur_action, list) and len(cur_action) > 0 else ""
        cur_rank = cur_action[1] if len(cur_action) > 1 else ""
        
        scan_result = context.get('scan_result', {})
        protected_combinations = scan_result.get('protected_combinations', [])
        excess_singles = context.get('excess_singles', [])
        
        # 优先使用excess_singles
        if excess_singles and cur_action_type == 'Single':
            for excess_card in excess_singles:
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                        action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
                        if action_cards and excess_card in action_cards:
                            if self._validate_action_cards(action, handcards):
                                # 检查是否破坏受保护组合（修复：展平嵌套列表）
                                action_cards_flat = self._flatten_cards(action_cards)
                                action_cards_set = set(action_cards_flat)
                                would_break = False
                                for prot in protected_combinations:
                                    if isinstance(prot, list):
                                        prot_flat = self._flatten_cards(prot)
                                        prot_set = set(prot_flat)
                                        if action_cards_set & prot_set and not action_cards_set.issubset(prot_set):
                                            would_break = True
                                            break
                                if not would_break:
                                    # 确保能压制
                                    action_rank = action[1] if len(action) > 1 else ""
                                    if action_rank and self._get_rank_value(action_rank, context.get('cur_rank', '2')) > self._get_rank_value(cur_rank, context.get('cur_rank', '2')):
                                        return i
        
        # 选择能压制的最小动作（不破坏受保护组合）
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == cur_action_type:
                if len(action) > 1:
                    action_rank = action[1]
                    # 使用_get_rank_value比较牌点大小
                    cur_rank_value = self._get_rank_value(cur_rank, context.get('cur_rank', '2'))
                    action_rank_value = self._get_rank_value(action_rank, context.get('cur_rank', '2'))
                    if action_rank_value > cur_rank_value:
                        if self._validate_action_cards(action, handcards):
                            action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
                            # ⚠️ 检查是否破坏受保护组合（修复：展平嵌套列表）
                            action_cards_flat = self._flatten_cards(action_cards)
                            action_cards_set = set(action_cards_flat)
                            would_break = False
                            for prot in protected_combinations:
                                if isinstance(prot, list):
                                    prot_flat = self._flatten_cards(prot)
                                    prot_set = set(prot_flat)
                                    if action_cards_set & prot_set and not action_cards_set.issubset(prot_set):
                                        would_break = True
                                        break
                            if not would_break:
                                return i
        
        # ⚠️ 最后尝试：返回第一个有效的非PASS动作（即使不能压制）
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                if self._validate_action_cards(action, handcards):
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

